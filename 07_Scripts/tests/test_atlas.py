"""Invarianti dell'atlante e transazioni reali dell'export."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from qgis.core import QgsApplication, QgsGeometry
from qgis.analysis import QgsNativeAlgorithms
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scialpinismo import atlas
from scialpinismo.engine import Workflow, save_json, load_json
from test_workflow import WorkflowTests

class AtlasTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name); self.w = Workflow(self.root)
    def tearDown(self): self.tmp.cleanup()
    def test_grid_and_overlap(self):
        a = atlas.cell_geometry(127,73); core = atlas.core_geometry(127,73)
        adjacent = atlas.cell_geometry(128,73)
        self.assertEqual(a.area(), 35000**2); self.assertEqual(core.area(),31000**2)
        overlap = a.intersection(adjacent).boundingBox()
        self.assertEqual(overlap.width(),4000); self.assertEqual(overlap.height(),35000)
    def test_editorial_cell_exceptions_are_disjoint(self):
        self.assertFalse(atlas.EXCLUDED_CELL_IDS & atlas.FORCED_CELL_IDS)
        self.assertEqual(atlas.FORCED_CELL_IDS, {'ALP_E136_N083'})
        self.assertEqual(atlas.EXCLUDED_CELL_IDS, {
            'ALP_E134_N080', 'ALP_E135_N080', 'ALP_E139_N080',
            'ALP_E140_N080', 'ALP_E141_N080', 'ALP_E142_N080',
            'ALP_E144_N086', 'ALP_E146_N082', 'ALP_E147_N082'})
    def test_grid_extension_keeps_names_and_ids(self):
        first = atlas.make_grid(self.w, [12.1,46.5,12.2,46.6], mountain_only=False); key=first['cells'][0]['id']
        atlas.rename_cell(self.w,key,'Nome stabile')
        second=atlas.make_grid(self.w,[11.8,46.3,12.4,46.8], mountain_only=False)
        self.assertEqual(next(c for c in second['cells'] if c['id']==key)['display_name'],'Nome stabile')
        self.assertTrue(set(c['id'] for c in first['cells']) <= set(c['id'] for c in second['cells']))
        self.assertTrue(atlas.grid_vector_path(self.w).exists())
        geojson=json.loads((self.root/'08_Atlante/celle_analisi.geojson').read_text())
        self.assertIn('cell_id',geojson['features'][0]['properties'])
        places=json.loads((self.root/'08_Atlante/localita.geojson').read_text())
        self.assertEqual(len(places['features']),len(second['cells']))
        self.assertEqual(len({f['properties']['cell_id'] for f in places['features']}),len(second['cells']))
        self.assertTrue(all(f['properties']['name'] for f in places['features']))
    def test_preparation_is_limited_to_two_adjacent_cells(self):
        data={'grid_id':atlas.GRID_ID,'crs':atlas.CRS,'origin':[0,0],'cell_size_m':atlas.CELL_SIZE,
              'step_m':atlas.STEP,'overlap_side_m':atlas.OVERLAP_SIDE,
              'cells':[{'id':atlas.cell_id(1,1),'col':1,'row':1,'display_name':'A'},
                       {'id':atlas.cell_id(2,1),'col':2,'row':1,'display_name':'B'},
                       {'id':atlas.cell_id(3,1),'col':3,'row':1,'display_name':'C'}]}
        self.w.archive.mkdir(parents=True,exist_ok=True);save_json(atlas.grid_path(self.w),data)
        with self.assertRaisesRegex(ValueError,'massimo due'):
            atlas.prepare_cells(self.w,[c['id'] for c in data['cells']])
        with self.assertRaisesRegex(ValueError,'adiacenti'):
            atlas.prepare_cells(self.w,[data['cells'][0]['id'],data['cells'][2]['id']])
    def test_existing_cell_receives_nodata_threshold(self):
        key=atlas.cell_id(1,1)
        data={'grid_id':atlas.GRID_ID,'crs':atlas.CRS,'origin':[0,0],
              'cell_size_m':atlas.CELL_SIZE,'step_m':atlas.STEP,
              'overlap_side_m':atlas.OVERLAP_SIDE,
              'cells':[{'id':key,'col':1,'row':1,'display_name':'A'}]}
        self.w.archive.mkdir(parents=True,exist_ok=True);save_json(atlas.grid_path(self.w),data)
        config=self.w.areas/key/'area.json';config.parent.mkdir(parents=True);save_json(config,{})
        with patch.object(self.w,'update',return_value={'project':'x'}) as update:
            atlas.prepare_cells(self.w,[key],0.25)
        update.assert_called_once_with(config,max_missing_percent=0.25)
    def test_export_updates_lightweight_atlas_registry(self):
        key=atlas.cell_id(127,73);self.w.archive.mkdir(parents=True,exist_ok=True)
        record=atlas.record_export(self.w,key,{'edition':'test','settings':{'minzoom':12,'maxzoom':16},
                                              'packages':[{'bytes':123}]})
        self.assertEqual(record['status'],'release_ready')
        self.assertEqual(load_json(self.w.archive/'atlante_stato.json')[key]['status'],'release_ready')
        self.assertEqual(load_json(self.w.archive/'atlante_produzioni.json')[key]['zoom'],[12,16])
    def test_publication_requires_only_technical_validation(self):
        self.assertTrue(atlas.publication_ready({'technical_validation':'passed'}))
        self.assertFalse(atlas.publication_ready({'technical_validation':'failed'}))
    def test_unpublished_catalog_has_no_download(self):
        atlas.make_grid(self.w,[12.1,46.5,12.2,46.6],mountain_only=False);result=atlas.build_catalog(self.w)
        self.assertEqual(result['published'],0)
        self.assertNotIn('"url":', (self.root/'08_Atlante/catalogo.json').read_text())
        self.assertTrue((self.root/'08_Atlante/quadro_unione.pdf').stat().st_size>1000)
    def test_publish_rejects_modified_file(self):
        key='ALP_E127_N074'; base=self.w.areas/key/'output/mbtiles';base.mkdir(parents=True)
        file=base/'map.mbtiles';file.write_bytes(b'original')
        cat={'technical_validation':'passed',
             'packages':[{'file':file.name,'bytes':8,'sha256':atlas.sha256_file(file)}]}
        save_json(base/'catalogo_mbtiles.json',cat);file.write_bytes(b'modified')
        with self.assertRaisesRegex(ValueError,'modificato'):atlas.publish_cell(self.w,key)
    def test_missing_tile_is_detected(self):
        import sqlite3
        from scialpinismo.exporter import verify_tile_coverage, rect_tile
        path=self.root/'empty.mbtiles'
        with sqlite3.connect(path) as con:con.execute('create table tiles(zoom_level,tile_column,tile_row)')
        geometry=QgsGeometry.fromRect(rect_tile(2200,1400,12))
        with self.assertRaisesRegex(ValueError,'mancante'):verify_tile_coverage([path],geometry,12,12)
    def test_missing_tile_recovery_and_failed_retry(self):
        import sqlite3, io
        from PIL import Image
        from scialpinismo.exporter import repair_missing_tiles, verify_tile_coverage, rect_tile
        path=self.root/'repair.mbtiles'
        with sqlite3.connect(path) as con:
            con.execute('create table tiles(zoom_level,tile_column,tile_row,tile_data)')
        geometry=QgsGeometry.fromRect(rect_tile(2200,1400,12))
        data=io.BytesIO();Image.new('RGBA',(256,256),'green').save(data,format='PNG')
        calls=[]
        def render(rect, output, lo, hi):
            calls.append((lo,hi))
            with sqlite3.connect(output) as con:
                con.execute('create table tiles(zoom_level,tile_column,tile_row,tile_data)')
                con.execute('insert into tiles values (12,2200,2695,?)',(data.getvalue(),))
        self.assertEqual(repair_missing_tiles(path,geometry,12,12,render),[(12,2200,2695)])
        self.assertEqual(calls,[(12,12)])
        self.assertTrue(verify_tile_coverage([path],geometry,12,12)['expected_coverage_checked'])
        with sqlite3.connect(path) as con:con.execute('delete from tiles')
        def empty_render(rect, output, lo, hi):
            with sqlite3.connect(output) as con:con.execute('create table tiles(zoom_level,tile_column,tile_row,tile_data)')
        with self.assertRaisesRegex(ValueError,'Recupero tessera fallito'):
            repair_missing_tiles(path,geometry,12,12,empty_render)
        self.assertFalse(Path(str(path)+'.repair.mbtiles').exists())
    def test_single_ignores_split_limit_and_failure_preserves_current(self):
        fixture=WorkflowTests('test_real_export_has_no_shared_tiles_from12_to17');fixture.setUp()
        try:
            fixture.test_real_export_has_no_shared_tiles_from12_to17()
            report=fixture.w.export(fixture.root,mode='single',maxbytes=100000,warning_bytes=100000)
            self.assertEqual(len(report['packages']),1)
            path=fixture.root/'output/mbtiles/catalogo_mbtiles.json';before=path.read_bytes()
            file=path.parent/report['packages'][0]['file'];self.assertTrue(file.exists())
            self.assertEqual(atlas.sha256_file(file),report['packages'][0]['sha256'])
            with patch('scialpinismo.exporter.inspect_mbtiles',side_effect=ValueError('validazione fallita')):
                with self.assertRaisesRegex(ValueError,'validazione fallita'):
                    fixture.w.export(fixture.root,mode='single')
            self.assertEqual(path.read_bytes(),before);self.assertTrue(file.exists())
            from qgis.core import Qgis
            def rendering_error(*args, **kwargs):
                QgsApplication.messageLog().logMessage('unable to open database file', 'GDAL', Qgis.Critical)
            with patch('processing.run', side_effect=rendering_error):
                with self.assertRaisesRegex(RuntimeError, 'Rendering incompleto'):
                    fixture.w.export(fixture.root, mode='single')
            self.assertEqual(path.read_bytes(), before)

        finally:fixture.tearDown()

if __name__=='__main__':
    app=QgsApplication([],False);app.initQgis();app.processingRegistry().addProvider(QgsNativeAlgorithms())
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(AtlasTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    app.exitQgis();sys.exit(not result.wasSuccessful())
