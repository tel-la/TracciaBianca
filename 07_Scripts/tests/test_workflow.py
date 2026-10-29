"""Test di invarianti reali: quote, copertura, portabilità e livelli offline."""
import io
import json
import math
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import numpy as np
from osgeo import gdal
from PIL import Image
from qgis.core import QgsApplication, QgsGeometry, QgsRectangle
from qgis.analysis import QgsNativeAlgorithms

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'07_Scripts'))
from scialpinismo.engine import (Workflow, save_json, cog_copy, geometry_in,
                                 dtm_nodata_policy, parse_bev_atom_index,
                                 parse_bev_atom_tif, parse_swisstopo_stac_page,
                                 osm_records, estimate_dem_coregistration,
                                 seam_fields, DTM_BLEND_MAX_M,
                                 multidirectional_hillshade,
                                 HILLSHADE_ALTITUDE_DEG,
                                 HILLSHADE_PRIMARY_AZIMUTH_DEG,
                                 HILLSHADE_PRIMARY_WEIGHT)
from scialpinismo.exporter import inspect_mbtiles, tile_bounds


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='scialpinismo_test_')
        self.root = Path(self.temp.name)
        self.w = Workflow(self.root)
        self.w.archive.mkdir(parents=True, exist_ok=True)
        self.config = {'schema_version': 1, 'id': 'test', 'perimeter_wkt': QgsGeometry.fromRect(QgsRectangle(12.11, 46.53, 12.12, 46.54)).asWkt(),
                       'perimeter_crs': 'EPSG:4326', 'processing_crs': 'EPSG:32633', 'source_ids': [], 'buffer_m': 100,
                       'contour_interval_m': 10, 'project': 'progetto/test.qgz',
                       'export': {'minzoom': 12, 'maxzoom': 16, 'mode': 'single',
                                  'jpeg_quality': 90, 'dpi': 96}}

    def tearDown(self):
        self.temp.cleanup()

    def source(self, native=10, verified=True, rect=None):
        file = self.w.archive/'source.tif'
        file.touch()
        coverage = QgsGeometry.fromRect(rect or QgsRectangle(11, 45, 13, 48))
        save_json(self.w.archive/'fonti.json', {'sources': [{'id': 'test', 'path': 'source.tif', 'grid_m': 5,
                  'native_resolution_m': native, 'verified': verified, 'coverage_wkt': coverage.asWkt()}]})

    def test_osm_records_accepts_legacy_and_multi_source_catalogs(self):
        legacy = {'path': 'osm/legacy.osm.pbf'}
        self.assertEqual(osm_records({'osm': legacy}), [legacy])
        current = [{'path': 'osm/a.osm.pbf'}, {'path': 'osm/b.osm.pbf'}]
        self.assertEqual(osm_records({'osm': legacy, 'osm_sources': current}), current)

    def test_osm_sources_are_selected_by_geographic_coverage(self):
        for name in ('west.osm.pbf', 'east.osm.pbf', 'far.osm.pbf'):
            (self.w.archive/name).touch()
        data = {'osm_sources': [
            {'id': 'west', 'path': 'west.osm.pbf', 'coverage_bbox': [9, 45, 11, 47]},
            {'id': 'east', 'path': 'east.osm.pbf', 'coverage_bbox': [10, 45, 13, 47]},
            {'id': 'far', 'path': 'far.osm.pbf', 'coverage_bbox': [14, 45, 16, 47]},
        ]}
        config = {**self.config, 'processing_crs': 'EPSG:4326', 'buffer_m': 0}
        area = QgsGeometry.fromRect(QgsRectangle(10.5, 46, 10.7, 46.2))
        selected = self.w.select_osm_sources(data, area, config)
        self.assertEqual([record['id'] for record, _ in selected], ['west', 'east'])

    def test_launcher_bootstrap_without_file_from_arbitrary_directory(self):
        import os,subprocess
        startup=ROOT/'07_Scripts/avvia_workflow_qgis.py'
        env={**os.environ,'SCIALPINISMO_SCRIPT':str(startup)}
        env.pop('SCIALPINISMO_ROOT',None)
        result=subprocess.run([sys.executable,str(ROOT/'07_Scripts/tests/avvio_probe.py'),str(startup),'env'],
                              cwd=self.root,env=env,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('AVVIO_OK',result.stdout)

    def test_launcher_bootstrap_after_move_with_spaces_using_code_argument(self):
        import os,subprocess,shutil
        scripts=self.root/"base con spazi e 'apostrofo"/'07_Scripts';scripts.mkdir(parents=True)
        shutil.copy2(ROOT/'07_Scripts/avvia_workflow_qgis.py',scripts/'avvia_workflow_qgis.py')
        shutil.copytree(ROOT/'07_Scripts/scialpinismo',scripts/'scialpinismo',ignore=shutil.ignore_patterns('__pycache__'))
        startup=scripts/'avvia_workflow_qgis.py';env=dict(os.environ)
        env.pop('SCIALPINISMO_SCRIPT',None);env.pop('SCIALPINISMO_ROOT',None)
        result=subprocess.run([sys.executable,str(ROOT/'07_Scripts/tests/avvio_probe.py'),str(startup),'argv'],
                              cwd=self.root,env=env,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('AVVIO_OK',result.stdout)

    def test_high_zoom_rejects_resampled_grid(self):
        self.source(native=10)
        self.config['export']['maxzoom'] = 18
        with self.assertRaisesRegex(ValueError, 'sotto i 5'):
            self.w.select_sources(self.config)

    def test_zoom17_is_graphic_detail_even_with_native10m(self):
        self.source(native=10)
        self.config['export']['maxzoom']=17
        self.assertEqual(len(self.w.select_sources(self.config)[0]),1)

    def test_fine_dtm_is_overlaid_on_base_even_when_its_footprint_covers_area(self):
        coverage = QgsGeometry.fromRect(QgsRectangle(11, 45, 13, 48)).asWkt()
        for name in ('base.tif', 'fine.tif'):
            (self.w.archive/name).touch()
        save_json(self.w.archive/'fonti.json', {'sources': [
            {'id':'base','path':'base.tif','crs':'EPSG:32633','grid_m':5,'native_resolution_m':10,
             'verified':True,'coverage_wkt':coverage},
            {'id':'fine','path':'fine.tif','crs':'EPSG:32633','grid_m':2.5,'native_resolution_m':2.5,
             'verified':True,'coverage_wkt':coverage},
        ]})
        selected,_ = self.w.select_sources(self.config)
        self.assertEqual([source['id'] for source in selected], ['base','fine'])

    def test_remote_arcgis_dtm_is_available_without_a_local_source_file(self):
        coverage = QgsGeometry.fromRect(QgsRectangle(11, 45, 13, 48)).asWkt()
        save_json(self.w.archive/'fonti.json', {'sources': [{
            'id':'remote','provider':'arcgis_imageserver','url':'https://example.test/ImageServer',
            'revision':'test','crs':'EPSG:3794','grid_m':5,'native_resolution_m':1,
            'verified':True,'vertical_units':'m','coverage_wkt':coverage,
        }]})
        selected,_ = self.w.select_sources(self.config)
        self.assertEqual([source['id'] for source in selected], ['remote'])
        self.assertEqual(self.w.source_fingerprint(selected[0]), {
            'provider':'arcgis_imageserver','url':'https://example.test/ImageServer','revision':'test'})

    def test_remote_bev_dtm_is_available_without_a_local_source_file(self):
        coverage = QgsGeometry.fromRect(QgsRectangle(11, 45, 13, 48)).asWkt()
        save_json(self.w.archive/'fonti.json', {'sources': [{
            'id':'bev','provider':'bev_atom_cog','url':'https://example.test/product',
            'atom_url':'https://example.test/atom','revision':'test','crs':'EPSG:3035',
            'grid_m':5,'native_resolution_m':1,'verified':True,'vertical_units':'m',
            'coverage_wkt':coverage,
        }]})
        selected,_ = self.w.select_sources(self.config)
        self.assertEqual([source['id'] for source in selected], ['bev'])
        self.assertEqual(self.w.source_fingerprint(selected[0])['atom_url'],
                         'https://example.test/atom')

    def test_bev_atom_parsers_choose_latest_dtm_and_geotiff(self):
        service = b'''<feed xmlns="http://www.w3.org/2005/Atom">
          <entry><title>ALS DTM CRS3035RES50000mN2600000E4500000 Stichtag 15.09.2024</title>
            <link type="application/atom+xml" href="https://example.test/old.xml"/></entry>
          <entry><title>ALS DTM CRS3035RES50000mN2600000E4500000 Stichtag 15.09.2025</title>
            <link type="application/atom+xml" href="https://example.test/new.xml"/></entry>
          <entry><title>ALS DSM CRS3035RES50000mN2600000E4500000 Stichtag 15.09.2026</title>
            <link type="application/atom+xml" href="https://example.test/dsm.xml"/></entry>
        </feed>'''
        self.assertEqual(parse_bev_atom_index(service), {
            '2600000_4500000':'https://example.test/new.xml'})
        dataset = b'''<feed xmlns="http://www.w3.org/2005/Atom">
          <link type="image/tiff" href="https://example.test/tile.tif"/>
        </feed>'''
        self.assertEqual(parse_bev_atom_tif(dataset), 'https://example.test/tile.tif')

    def test_remote_swisstopo_dtm_and_stac_parser(self):
        coverage = QgsGeometry.fromRect(QgsRectangle(7, 45, 13, 48)).asWkt()
        save_json(self.w.archive/'fonti.json', {'sources': [{
            'id':'swiss','provider':'swisstopo_stac_cog','url':'https://example.test/product',
            'stac_url':'https://example.test/collection','revision':'test','crs':'EPSG:2056',
            'grid_m':5,'native_resolution_m':2,'remote_resolution_m':2,
            'verified':True,'vertical_units':'m','coverage_wkt':coverage,
        }]})
        selected,_ = self.w.select_sources(self.config)
        self.assertEqual([source['id'] for source in selected], ['swiss'])
        self.assertEqual(self.w.source_fingerprint(selected[0])['stac_url'],
                         'https://example.test/collection')
        page = json.dumps({
            'features': [{'id':'swissalti3d_2025_2680-1120',
                          'properties':{'datetime':'2025-01-01T00:00:00Z'},
                          'assets': {
                              'fine': {'href':'https://example.test/fine.tif', 'gsd':0.5,
                                       'proj:epsg':2056, 'type':'image/tiff; profile=cloud-optimized'},
                              'work': {'href':'https://example.test/work.tif', 'gsd':2.0,
                                       'proj:epsg':2056, 'type':'image/tiff; profile=cloud-optimized'}}}],
            'links':[{'rel':'next','href':'https://example.test/page2'}],
        }).encode()
        records,next_url = parse_swisstopo_stac_page(page, 2)
        self.assertEqual(records, [{'key':'2680-1120','datetime':'2025-01-01T00:00:00Z',
                                    'url':'https://example.test/work.tif'}])
        self.assertEqual(next_url, 'https://example.test/page2')

    def test_remote_coverage_search_includes_nearby_common_tile(self):
        coverage = geometry_in(
            QgsGeometry.fromRect(QgsRectangle(600100, 5200100, 601000, 5201000)),
            'EPSG:32632', 'EPSG:4326').asWkt()
        source = {'id':'swiss','provider':'swisstopo_stac_cog','revision':'test',
                  'url':'https://example.test/product',
                  'stac_url':'https://example.test/collection','crs':'EPSG:2056',
                  'grid_m':5,'native_resolution_m':2,'remote_grid_m':1000,
                  'verified':True,'vertical_units':'m','coverage_wkt':coverage}
        extent = QgsGeometry.fromRect(QgsRectangle(599500, 5200000, 599900, 5200500))
        created = []
        def fake_download(source, rect, crs, resolution, destination):
            created.append((rect.xMinimum(), rect.yMinimum()))
            ds = gdal.GetDriverByName('GTiff').Create(str(destination), 2000, 2000, 1, gdal.GDT_Float32)
            ds.SetGeoTransform([rect.xMinimum(), 5, 0, rect.yMaximum(), 0, -5])
            ds.GetRasterBand(1).SetNoDataValue(-9999); ds.GetRasterBand(1).Fill(1000); ds = None
        with patch.object(self.w, 'download_swisstopo_cog_tile', side_effect=fake_download):
            self.w.cached_tiles(source, extent, 'EPSG:32632', 5)
        self.assertEqual(created, [(590000.0, 5200000.0)])

    def test_arcgis_tile_is_sampled_at_native_resolution_before_downsampling(self):
        from urllib.parse import parse_qs, urlparse
        source = {'id': 'arso', 'url': 'https://example.test/ImageServer',
                  'native_resolution_m': 1, 'nodata': -3,
                  'max_image_width': 15000, 'max_image_height': 4100}
        requests = []

        def fake_urlopen(request, timeout):
            params = parse_qs(urlparse(request.full_url).query)
            west, south, east, north = map(float, params['bbox'][0].split(','))
            width, height = map(int, params['size'][0].split(','))
            requests.append(params)
            ds = gdal.GetDriverByName('GTiff').Create(
                '/vsimem/arso_native_test.tif', width, height, 1, gdal.GDT_Float32)
            # Riproduce il servizio: a 5 m risponde solo NoData, a 1 m dà quote.
            values = np.full((height, width), 1234 if (east-west)/width <= 1 else -3,
                             dtype=np.float32)
            values[:, :width//2] = -1e10  # NoData LERC2 osservato nel servizio.
            ds.GetRasterBand(1).WriteArray(values)
            ds = None
            payload = bytes(gdal.VSIGetMemFileBuffer_unsafe('/vsimem/arso_native_test.tif'))
            gdal.Unlink('/vsimem/arso_native_test.tif')
            return io.BytesIO(payload)

        destination = self.root/'arso.tif'
        with patch('scialpinismo.engine.urlopen', side_effect=fake_urlopen):
            self.w.download_arcgis_tile(source, QgsRectangle(400000, 5130000, 400100, 5130100),
                                       'EPSG:32633', 5, destination)
        self.assertEqual(requests[0]['format'], ['lerc'])
        self.assertEqual(requests[0]['lercVersion'], ['2'])
        self.assertEqual(len(requests), 1)
        result = gdal.Open(str(destination)).ReadAsArray()
        self.assertEqual(result[10, 1], -9999)
        self.assertEqual(result[10, -2], 1234)
        self.assertTrue(np.all((result == -9999) | (result == 1234)))

    def test_remote_source_is_selected_in_simplified_border_margin(self):
        coverage = geometry_in(
            QgsGeometry.fromRect(QgsRectangle(600100, 5200100, 601000, 5201000)),
            'EPSG:32632', 'EPSG:4326').asWkt()
        source = {'id':'swiss','provider':'swisstopo_stac_cog',
                  'url':'https://example.test/product','stac_url':'https://example.test/collection',
                  'revision':'test','crs':'EPSG:2056','grid_m':5,'native_resolution_m':2,
                  'remote_grid_m':1000,'verified':True,'vertical_units':'m',
                  'coverage_wkt':coverage}
        save_json(self.w.archive/'fonti.json', {'sources':[source]})
        self.config.update({
            'processing_crs':'EPSG:32632', 'perimeter_crs':'EPSG:32632',
            'perimeter_wkt':QgsGeometry.fromRect(
                QgsRectangle(599500,5200200,599900,5200600)).asWkt()})
        selected,_ = self.w.select_sources(self.config)
        self.assertEqual([item['id'] for item in selected], ['swiss'])

    def test_partition_owns_distinct_tiles_at_every_zoom_in_tms(self):
        from scialpinismo.exporter import split_roots,prune_unowned_tiles,verify_disjoint_packages
        roots=split_roots((2300,1400,2301,1400));paths=[]
        for i,owned in enumerate(roots):
            path=self.root/f'part{i}.mbtiles';paths.append(path)
            with sqlite3.connect(str(path)) as con:
                con.execute('create table tiles(zoom_level integer,tile_column integer,tile_row integer)')
                for z in range(12,18):
                    factor=2**(z-12)
                    for x in range(2300*factor,2302*factor):
                        con.execute('insert into tiles values (?,?,?)',(z,x,2**z-1-1400*factor))
            prune_unowned_tiles(path,owned,12)
        report=verify_disjoint_packages(paths)
        self.assertEqual(report['duplicate_tile_keys'],0)
        self.assertEqual(report['unique_tiles_per_zoom'][17],64)
        with self.assertRaisesRegex(ValueError,'duplicata'):
            verify_disjoint_packages([paths[0],paths[0]])

    def test_v5_symbol_proportions_and_path_text(self):
        from scialpinismo.readability import forest_fill,bivouac_symbol,house_symbol,path_labels
        from scialpinismo.engine import memory_layer
        new,old=bivouac_symbol(),house_symbol()
        for i in range(old.symbolLayerCount()):
            self.assertAlmostEqual(new.symbolLayer(i).size(),old.symbolLayer(i).size()*0.55)
        self.assertEqual(new.symbolLayer(2).color().name(),'#ee870b')
        fill=forest_fill('conifere'); pattern=fill.symbolLayer(1)
        self.assertAlmostEqual(pattern.distanceX(),9)
        self.assertAlmostEqual(pattern.subSymbol().symbolLayer(0).size(),1.9*0.65)
        layer=memory_layer('paths','MultiLineString');path_labels(layer)
        self.assertAlmostEqual(layer.labeling().settings().format().size(),6.48)

    def test_refuge_size_and_contour_label_hierarchy(self):
        from scialpinismo.readability import refuge_symbol,house_symbol,contour_labels
        from scialpinismo.engine import memory_layer
        refuge,original=refuge_symbol(),house_symbol()
        for i in range(original.symbolLayerCount()):
            self.assertAlmostEqual(refuge.symbolLayer(i).size(),original.symbolLayer(i).size()*.65)
        layer=memory_layer('contours','MultiLineString');contour_labels(layer,10)
        rules=layer.labeling().rootRule().children()
        self.assertEqual(len(rules),2)
        self.assertAlmostEqual(rules[0].settings().format().size(),10.2)
        self.assertTrue(rules[0].settings().format().font().bold())
        self.assertAlmostEqual(rules[1].settings().format().size(),7.2)
        self.assertFalse(rules[1].settings().format().font().bold())
        self.assertGreater(rules[0].settings().priority,rules[1].settings().priority)

    def test_place_road_and_refuge_text_is_25_percent_larger_only_at_zoom_13_15(self):
        from qgis.core import QgsExpression,QgsExpressionContext,QgsExpressionContextScope
        from scialpinismo.readability import zoom_13_15_size
        expression=QgsExpression(zoom_13_15_size(9.8))
        scope=QgsExpressionContextScope()
        scope.setVariable('scialpinismo_scale_12_13',100000)
        scope.setVariable('scialpinismo_scale_15_16',12500)
        context=QgsExpressionContext();context.appendScope(scope)
        for scale,expected in ((120000,9.8),(50000,12.25),(12500,12.25),(10000,9.8)):
            scope.setVariable('map_scale',scale)
            self.assertAlmostEqual(expression.evaluate(context),expected)
            self.assertFalse(expression.hasEvalError(),expression.evalErrorString())

    def test_bivouac_name_starts_at_zoom_16_and_uses_icon_orange(self):
        from scialpinismo.readability import HUT_LABEL_EXPRESSION,HUT_LABEL_COLOR_EXPRESSION
        self.assertIn('@map_scale < @scialpinismo_scale_15_16',HUT_LABEL_EXPRESSION)
        self.assertNotIn('scialpinismo_scale_16_17',HUT_LABEL_EXPRESSION)
        self.assertIn("IN ('bivacco','riparo')",HUT_LABEL_EXPRESSION)
        self.assertIn("ELSE '#ee870b'",HUT_LABEL_COLOR_EXPRESSION)

    def test_contour_labels_follow_line_and_preserve_zoom_gates(self):
        from qgis.core import Qgis,QgsPalLayerSettings,QgsExpression,QgsExpressionContext,QgsExpressionContextScope
        from scialpinismo.readability import contour_labels
        from scialpinismo.engine import memory_layer
        layer=memory_layer('contours','MultiLineString')
        scope=QgsExpressionContextScope();scope.setVariable('scialpinismo_scale_15_16',20000)
        scope.setVariable('scialpinismo_scale_13_14',80000);scope.setVariable('scialpinismo_scale_14_15',40000)
        context=QgsExpressionContext();context.appendScope(scope)
        for interval in (100,20,10):
            contour_labels(layer,interval)
            master=self.root/f'contours_{interval}.qml'
            layer.saveNamedStyle(str(master))
            reloaded=memory_layer('reloaded','MultiLineString')
            message,ok=reloaded.loadNamedStyle(str(master));self.assertTrue(ok,message)
            for rule in reloaded.labeling().rootRule().children():
                settings=rule.settings()
                self.assertEqual(settings.placement,QgsPalLayerSettings.Curved)
                self.assertEqual(settings.lineSettings().placementFlags(),Qgis.LabelLinePlacementFlag.OnLine)
                self.assertEqual(settings.dist,0)
                # Anche forzando un layer visibile, nessuna quota appare prima della soglia.
                scope.setVariable('map_scale',60000)
                expr=QgsExpression(rule.filterExpression());value=expr.evaluate(context)
                self.assertFalse(value)
                self.assertFalse(expr.hasEvalError(),expr.evalErrorString())
                self.assertIn('@scialpinismo_scale_14_15' if interval==20 else '@scialpinismo_scale_15_16',rule.filterExpression())

    def test_v7_detail_strength_and_discrete_zoom15_labels(self):
        from qgis.PyQt.QtGui import QColor
        from scialpinismo.cartography import vivid_color,contour_symbol
        from scialpinismo.readability import contour_labels
        from scialpinismo.engine import memory_layer
        color=QColor('#98d29e');new=vivid_color(color)
        self.assertAlmostEqual(new.hsvSaturationF(),color.hsvSaturationF()*1.2,delta=0.001)
        self.assertAlmostEqual(new.valueF(),color.valueF(),delta=0.001)
        self.assertEqual(new.alpha(),color.alpha())
        for major in (False,True):
            old,new=contour_symbol(major),contour_symbol(major,True)
            self.assertAlmostEqual(new.width(),old.width()*1.15)
            for before,after in zip(old.color().getRgb()[:3],new.color().getRgb()[:3]):
                self.assertEqual(after,round(before*.75))
            self.assertEqual(old.color().alpha(),new.color().alpha())
        layer=memory_layer('contours','MultiLineString');contour_labels(layer,20)
        rules=layer.labeling().rootRule().children();self.assertEqual(len(rules),1)
        fmt=rules[0].settings().format()
        self.assertEqual(fmt.size(),9);self.assertFalse(fmt.font().bold())
        self.assertIn('% 100 = 0',rules[0].filterExpression())

    def test_real_export_has_no_shared_tiles_from12_to17(self):
        from qgis.core import QgsProject,QgsVectorLayer,QgsLineSymbol
        from scialpinismo.engine import memory_layer,add_feature,write_layer,fingerprint,digest
        self.source(native=10)
        config=dict(self.config)
        # Attraversa esattamente una frontiera XYZ dello zoom 12.
        config['perimeter_wkt']=QgsGeometry.fromRect(QgsRectangle(12.125,46.531,12.133,46.535)).asWkt()
        config['export']={**self.config['export'],'maxzoom':17,'mode':'split','max_bytes':3000000,
                          'metatile':4,'tile_format':'png','clip_to_perimeter':True,'compact_packages':False}
        save_json(self.root/'area.json',config)
        vector=memory_layer('line','MultiLineString')
        add_feature(vector,QgsGeometry.fromWkt('MULTILINESTRING((12.125 46.532,12.133 46.534))'),[])
        write_layer(vector,self.root/'vector.gpkg','line')
        layer=QgsVectorLayer(str(self.root/'vector.gpkg')+'|layername=line','line','ogr')
        from qgis.core import QgsCoordinateReferenceSystem
        project=QgsProject();project.setCrs(QgsCoordinateReferenceSystem('EPSG:3857'));project.addMapLayer(layer)
        (self.root/'progetto').mkdir()
        project.write(str(self.root/config['project']))
        save_json(self.root/'elaborati/stato.json',{'config_signature':digest(config)})
        save_json(self.root/'elaborati/rapporto.json',{'id':'test','source_fingerprints':{'test':fingerprint(self.w.archive/'source.tif')},'sources':[{'title':'test','url':''}],'osm':{}})
        report=self.w.export(self.root)
        self.assertEqual(len(report['packages']),2)
        self.assertEqual(report['partition']['duplicate_tile_keys'],0)
        rect=geometry_in(QgsGeometry.fromWkt(config['perimeter_wkt']),'EPSG:4326','EPSG:3857').boundingBox()
        for z in range(12,18):
            x0,y0,x1,y1=tile_bounds(rect,z)
            self.assertEqual(report['partition']['unique_tiles_per_zoom'][z],(x1-x0+1)*(y1-y0+1))
        for pack in report['packages']:
            self.assertEqual([z for z,n in pack['zoom_counts']],list(range(12,18)))
        from scialpinismo.exporter import compact_packages
        merged=compact_packages(self.root/'output/mbtiles',report['packages'],3000000,'test',12,17)
        self.assertEqual(len(merged),1)
        inspect_mbtiles(self.root/'output/mbtiles'/merged[0]['file'],12,17)

    def test_lock_prevents_second_job_and_is_released(self):
        with self.w.locked():
            with self.assertRaisesRegex(RuntimeError, 'in corso'):
                with self.w.locked():
                    self.fail('Lock acquisito due volte')
        with self.w.locked():
            pass

    def test_catalog_registers_and_replaces_area_with_real_gpkg_fid(self):
        self.w.refresh_catalog({'sources': []})
        path = self.w.areas/'test/area.json'
        self.w.register_area(path, self.config)
        self.w.register_area(path, self.config)
        with sqlite3.connect(str(self.w.archive/'catalogo.gpkg')) as con:
            rows = con.execute('select area_id,config from aree').fetchall()
        self.assertEqual(rows, [('test', '../test/area.json')])

    def test_project_cannot_escape_area(self):
        self.config['project'] = '../altro.qgz'
        with self.assertRaisesRegex(ValueError, 'relativo'):
            self.w.validate_config(self.config)

    def test_partial_dtm_policy_requires_a_bounded_percentage(self):
        self.config['dtm_nodata_policy'] = {'mode': 'allow_partial', 'max_missing_percent': 1.0}
        self.w.validate_config(self.config)
        self.config['dtm_nodata_policy']['max_missing_percent'] = 11
        with self.assertRaisesRegex(ValueError, 'non superiore al 10'):
            self.w.validate_config(self.config)

    def test_percentage_value_builds_the_json_policy(self):
        self.assertEqual(dtm_nodata_policy(0), {'mode': 'strict'})
        self.assertEqual(dtm_nodata_policy(0.75),
                         {'mode': 'allow_partial', 'max_missing_percent': 0.75})
        with self.assertRaisesRegex(ValueError, 'compresa tra 0 e 10'):
            dtm_nodata_policy(10.1)

    def test_unknown_dtm_policy_is_rejected(self):
        self.config['dtm_nodata_policy'] = {'mode': 'ignore'}
        with self.assertRaisesRegex(ValueError, 'strict oppure allow_partial'):
            self.w.validate_config(self.config)

    def test_partial_dtm_policy_accepts_only_nodata_within_threshold(self):
        raster_path = self.root/'partial.tif'
        raster = gdal.GetDriverByName('GTiff').Create(str(raster_path), 10, 10, 1, gdal.GDT_Float32)
        raster.SetGeoTransform([12, 0.001, 0, 47, 0, -0.001])
        from osgeo import osr
        srs = osr.SpatialReference(); srs.ImportFromEPSG(4326)
        raster.SetProjection(srs.ExportToWkt())
        values = np.full((10, 10), 1000, dtype=np.float32); values[5, 5] = -9999
        raster.GetRasterBand(1).SetNoDataValue(-9999)
        raster.GetRasterBand(1).WriteArray(values)
        raster = None
        perimeter = self.root/'perimeter.geojson'
        save_json(perimeter, {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'properties': {},
                  'geometry': {'type': 'Polygon', 'coordinates': [[[12, 47], [12.01, 47], [12.01, 46.99],
                                [12, 46.99], [12, 47]]]}}]})
        with self.assertRaisesRegex(ValueError, 'Export bloccato'):
            self.w.validate_dtm(raster_path, perimeter)
        result = self.w.validate_dtm(
            raster_path, perimeter, {'mode': 'allow_partial', 'max_missing_percent': 1.0})
        self.assertEqual(result['missing_cells'], 1)
        self.assertEqual(result['total_cells'], 100)
        self.assertFalse(result['complete'])
        with self.assertRaisesRegex(ValueError, 'soglia 0.5%'):
            self.w.validate_dtm(
                raster_path, perimeter, {'mode': 'allow_partial', 'max_missing_percent': 0.5})
        raster = gdal.Open(str(raster_path), gdal.GA_Update)
        values[5, 6] = -1e10  # Segnaposto LERC2 non dichiarato come NoData.
        raster.GetRasterBand(1).WriteArray(values)
        raster = None
        with self.assertRaisesRegex(ValueError, 'quote fuori intervallo plausibile'):
            self.w.validate_dtm(
                raster_path, perimeter, {'mode': 'allow_partial', 'max_missing_percent': 10})

    def test_unverified_source_not_automatic(self):
        self.source(native=2.5, verified=False)
        with self.assertRaisesRegex(ValueError, 'copertura mancante'):
            self.w.select_sources(self.config)

    def test_incomplete_buffer_is_rejected(self):
        self.source(rect=QgsRectangle(12.11, 46.53, 12.12, 46.54))
        with self.assertRaisesRegex(ValueError, 'copertura mancante'):
            self.w.select_sources(self.config)

    def test_numeric_slope_survives_lossless_cog(self):
        source = self.root/'plane.tif'
        ds = gdal.GetDriverByName('GTiff').Create(str(source), 128, 128, 1, gdal.GDT_Float32)
        ds.SetGeoTransform([300000, 5, 0, 5160000, 0, -5])
        from osgeo import osr
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(32633)
        ds.SetProjection(srs.ExportToWkt())
        plane = np.tile((np.arange(128)*5*np.tan(np.radians(35))).astype(np.float32), (128, 1))
        ds.GetRasterBand(1).WriteArray(plane)
        ds = None
        optimized = self.root/'plane_cog.tif'
        stale_stats = Path(str(optimized) + '.aux.xml')
        stale_stats.write_text('<PAMDataset><PAMRasterBand band="1"><Metadata>'
                               '<MDI key="STATISTICS_MINIMUM">-10000000000</MDI>'
                               '</Metadata></PAMRasterBand></PAMDataset>')
        cog_copy(source, optimized)
        self.assertFalse(stale_stats.exists())
        raster = gdal.Open(str(optimized))
        np.testing.assert_array_equal(raster.ReadAsArray(), plane)
        slope = gdal.DEMProcessing('', raster, 'slope', format='MEM', alg='Horn', scale=1)
        np.testing.assert_allclose(slope.ReadAsArray()[2:-2, 2:-2], 35, atol=0.001)

    def test_dem_coregistration_separates_horizontal_and_vertical_shift(self):
        from scipy.ndimage import shift
        pixel = 2.5
        y, x = np.mgrid[:400, :400] * pixel
        terrain = (1400 + 0.18*x + 0.11*y + 18*np.sin(x/85) +
                   11*np.cos(y/63) + 4*np.sin((x+y)/27)).astype(np.float32)
        # Il candidato è traslato di +5 m Est, -2,5 m Nord e più basso di 3 m.
        candidate = shift(terrain, (-1, 2), order=1, mode='nearest') - 3
        valid = np.ones(terrain.shape, dtype=bool)
        result = estimate_dem_coregistration(terrain, candidate, valid, valid, pixel, 10)
        self.assertTrue(result['accepted'], result)
        self.assertAlmostEqual(result['dx_m'], 5.0, delta=0.8)
        self.assertAlmostEqual(result['dy_m'], 2.5, delta=0.8)
        self.assertAlmostEqual(result['dz_m'], 3.0, delta=0.5)

    def test_seam_fields_keep_blend_short_and_reject_bad_sector(self):
        pixel = 5.0
        y, x = np.mgrid[:240, :320] * pixel
        base = (1200 + 0.08*x + 0.04*y).astype(np.float32)
        candidate = base - 2.0
        base_valid = np.ones(base.shape, dtype=bool)
        candidate_valid = np.zeros(base.shape, dtype=bool)
        candidate_valid[:, 80:] = True
        candidate[70:150, 80:145] += 20.0
        correction, low_weight, high_weight, diagnostics = seam_fields(
            base, candidate, base_valid, candidate_valid, pixel, 10, vertical_shift=2.0)
        self.assertLessEqual(diagnostics['blend_m'], DTM_BLEND_MAX_M)
        self.assertGreater(diagnostics['incompatible_cells'], 0)
        self.assertEqual(float(low_weight[:, :80].max()), 0.0)
        self.assertGreater(float(low_weight[:, 180:].min()), 0.99)
        self.assertGreater(float(high_weight[:, 180:].min()), 0.99)
        self.assertLess(float(np.max(np.abs(correction))), 8.01)

    def test_disk_mosaic_preserves_fine_detail_away_from_short_seam(self):
        from osgeo import osr
        size = 240
        pixel = 5.0
        y, x = np.mgrid[:size, :size] * pixel
        base_values = (1300 + 0.06*x + 0.03*y).astype(np.float32)
        fine_values = (base_values - 3 + 1.8*np.sin(x/8.0)*np.cos(y/11.0)).astype(np.float32)
        fine_values[:, :80] = -9999
        srs = osr.SpatialReference(); srs.ImportFromEPSG(32633)
        def create(path, values):
            dataset = gdal.GetDriverByName('GTiff').Create(
                str(path), size, size, 1, gdal.GDT_Float32,
                options=['TILED=YES', 'COMPRESS=DEFLATE'])
            dataset.SetGeoTransform([0, pixel, 0, size*pixel, 0, -pixel])
            dataset.SetProjection(srs.ExportToWkt())
            dataset.GetRasterBand(1).SetNoDataValue(-9999)
            dataset.GetRasterBand(1).WriteArray(values)
            dataset = None
        base_path=self.root/'base.tif'; fine_path=self.root/'fine.tif'
        output=self.root/'mosaic.tif'
        create(base_path, base_values); create(fine_path, fine_values)
        sources = [
            {'id':'base','grid_m':10,'native_resolution_m':10},
            {'id':'fine','grid_m':5,'native_resolution_m':5},
        ]
        diagnostics, provenance = self.w.compose_dtm_sources(
            [base_path, fine_path], sources, [0, 0, size*pixel, size*pixel],
            'EPSG:32633', pixel, output)
        result = gdal.Open(str(output)).ReadAsArray()
        interior = np.s_[:, 150:220]
        np.testing.assert_allclose(result[interior], fine_values[interior] + 3,
                                   atol=0.35)
        self.assertLessEqual(diagnostics[0]['blend_m'], DTM_BLEND_MAX_M)
        self.assertTrue(Path(provenance).exists())
        Path(provenance).unlink()

    def test_multidirectional_hillshade_keeps_315_degree_sun_dominant(self):
        self.assertEqual(HILLSHADE_ALTITUDE_DEG, 45.0)
        self.assertEqual(HILLSHADE_PRIMARY_AZIMUTH_DEG, 315.0)
        self.assertGreater(HILLSHADE_PRIMARY_WEIGHT, 0.5)
        # Una normale rivolta a Nord-Ovest deve ricevere più luce della normale opposta.
        northwest = multidirectional_hillshade(
            np.array([[1.0]], dtype=np.float32),
            np.array([[-1.0]], dtype=np.float32))
        southeast = multidirectional_hillshade(
            np.array([[-1.0]], dtype=np.float32),
            np.array([[1.0]], dtype=np.float32))
        self.assertGreater(int(northwest[0, 0]), int(southeast[0, 0]))

    def test_dtm_seam_repair_closes_narrow_join_but_not_real_gap(self):
        path = self.root/'seams.tif'
        ds = gdal.GetDriverByName('GTiff').Create(str(path), 80, 80, 1, gdal.GDT_Float32)
        values = np.full((80, 80), 1500, dtype=np.float32)
        values[:, 14:26] = -9999
        values[25:55, 40:70] = -9999
        band = ds.GetRasterBand(1); band.SetNoDataValue(-9999); band.WriteArray(values)
        band = None; ds = None
        self.w.repair_dtm_seams(path, resolution=5)
        raster = gdal.Open(str(path)); repaired = raster.GetRasterBand(1).ReadAsArray()
        self.assertTrue(np.all(repaired[:, 14:26] != -9999))
        self.assertEqual(repaired[40, 55], -9999)

    def test_oversampled_dtm_is_normalized_at_native_resolution(self):
        source = self.w.archive/'duplicated_grid.tif'
        ds = gdal.GetDriverByName('GTiff').Create(str(source), 40, 40, 1, gdal.GDT_Float32)
        ds.SetGeoTransform([0, 5, 0, 200, 0, -5])
        from osgeo import osr
        srs = osr.SpatialReference(); srs.ImportFromEPSG(32633); ds.SetProjection(srs.ExportToWkt())
        coarse = np.add.outer(np.arange(20, dtype=np.float32), np.arange(20, dtype=np.float32))
        duplicated = np.repeat(np.repeat(coarse, 2, axis=0), 2, axis=1)
        band = ds.GetRasterBand(1); band.SetNoDataValue(-9999); band.WriteArray(duplicated)
        band = None; ds = None
        record = {'id':'duplicated','path':'duplicated_grid.tif','crs':'EPSG:32633',
                  'grid_m':5,'native_resolution_m':10,'nodata':-9999}
        output = self.root/'normalized.tif'
        self.w.warp_local_dtm_tile(record, QgsRectangle(20, 20, 180, 180),
                                   'EPSG:32633', 2.5, output)
        raster = gdal.Open(str(output)); values = raster.GetRasterBand(1).ReadAsArray()[4:-4, 4:-4]
        self.assertLess(np.mean(np.diff(values, axis=1) == 0), 0.02)
        self.assertLess(np.mean(np.diff(values, axis=0) == 0), 0.02)

    def test_geographic_processing_crs_rejected(self):
        self.config['processing_crs'] = 'EPSG:4326'
        with self.assertRaisesRegex(ValueError, 'metrico'):
            self.w.validate_config(self.config)

    def test_incremental_stage_does_not_recalculate_unchanged(self):
        (self.root/'elaborati').mkdir()
        result = self.root/'result.txt'
        calls = []
        def run():
            calls.append(True)
            result.write_text('ok')
        state = {}
        self.w.stage('test', {'input': 1}, [result], state, self.root, run)
        self.w.stage('test', {'input': 1}, [result], state, self.root, run)
        self.assertEqual(len(calls), 1)
        result.write_text('alterato')
        self.w.stage('test', {'input': 1}, [result], state, self.root, run)
        self.assertEqual(len(calls), 2)

    def test_mbtiles_missing_zoom_and_bad_payload_rejected(self):
        path = self.root/'test.mbtiles'
        con = sqlite3.connect(str(path))
        con.executescript('create table metadata(name text,value text); create table tiles(zoom_level integer,tile_column integer,tile_row integer,tile_data blob);')
        con.execute('insert into metadata values (?,?)', ('format', 'jpg'))
        data = io.BytesIO()
        Image.new('RGB', (256, 256), 'white').save(data, format='JPEG')
        con.execute('insert into tiles values (12,0,0,?)', (data.getvalue(),))
        con.commit()
        with self.assertRaisesRegex(ValueError, 'mancanti'):
            inspect_mbtiles(path, 12, 13)
        con.execute('update tiles set tile_data=?', (b'invalid',))
        con.commit()
        con.close()
        with self.assertRaises(Exception):
            inspect_mbtiles(path, 12, 12)

    def test_provider_exposes_seven_valid_algorithms(self):
        from scialpinismo.provider import Provider
        provider = Provider()
        QgsApplication.processingRegistry().addProvider(provider)
        self.assertEqual({a.name() for a in provider.algorithms()}, {'prepare', 'update', 'export', 'grid', 'prepare_cells', 'rename_cell', 'atlas'})
        QgsApplication.processingRegistry().removeProvider(provider)

    def test_export_dialog_defaults_to_zoom_12_16(self):
        from scialpinismo.provider import AreaAlgorithm
        algorithm = AreaAlgorithm('export')
        algorithm.initAlgorithm()
        self.assertEqual(algorithm.parameterDefinition('MINZOOM').defaultValue(), 12)
        self.assertEqual(algorithm.parameterDefinition('MAXZOOM').defaultValue(), 16)
        self.assertEqual(algorithm.parameterDefinition('MODE').defaultValue(), 0)
        self.assertEqual(algorithm.parameterDefinition('MODE').options()[0], 'File unico (predefinito)')

    def test_single_export_needs_no_size_limit_but_split_does(self):
        self.config['export'].pop('max_bytes', None)
        self.config['export']['mode'] = 'single'
        self.w.validate_config(self.config)
        self.config['export']['mode'] = 'split'
        with self.assertRaisesRegex(ValueError, 'specificare un limite peso'):
            self.w.validate_config(self.config)

    def test_legacy_600mb_value_does_not_imply_split_mode(self):
        self.config['export'].pop('mode', None)
        self.config['export']['max_bytes'] = 600000000
        self.w.validate_config(self.config)
        self.assertEqual(self.config['export'].get('mode', 'single'), 'single')

    def test_area_dialogs_expose_dtm_nodata_percentage(self):
        from scialpinismo.provider import AreaAlgorithm, AtlasAlgorithm
        prepare = AreaAlgorithm('prepare'); prepare.initAlgorithm()
        update = AreaAlgorithm('update'); update.initAlgorithm()
        export = AreaAlgorithm('export'); export.initAlgorithm()
        self.assertEqual(prepare.parameterDefinition('MAX_MISSING_PERCENT').defaultValue(), 0.0)
        self.assertFalse(prepare.parameterDefinition('MAX_MISSING_PERCENT').flags()
                         & prepare.parameterDefinition('MAX_MISSING_PERCENT').FlagOptional)
        self.assertTrue(update.parameterDefinition('MAX_MISSING_PERCENT').flags()
                        & update.parameterDefinition('MAX_MISSING_PERCENT').FlagOptional)
        self.assertTrue(export.parameterDefinition('MAX_MISSING_PERCENT').flags()
                        & export.parameterDefinition('MAX_MISSING_PERCENT').FlagOptional)
        cells = AtlasAlgorithm('prepare_cells'); cells.initAlgorithm()
        self.assertEqual(cells.parameterDefinition('MAX_MISSING_PERCENT').defaultValue(), 0.01)

    def test_hut_building_is_included_as_footprint_and_icon(self):
        from scialpinismo.osm_rules import classify
        targets, category = classify({'building':'yes','tourism':'alpine_hut','name':'Rifugio di prova'}, 'multipolygons')
        self.assertIn('edifici', targets)
        self.assertIn('rifugi', targets)
        self.assertEqual(category, 'rifugio')
        self.assertNotIn('poi', targets)

    def test_bus_shelter_is_not_a_mountain_hut(self):
        from scialpinismo.osm_rules import classify
        targets, _ = classify({'highway':'bus_stop','shelter':'yes','amenity':'shelter','shelter_type':'public_transport'}, 'points')
        self.assertNotIn('rifugi', targets)

    def test_ruins_and_urban_buildings_are_not_dropped(self):
        from scialpinismo.osm_rules import classify
        self.assertIn('edifici', classify({'building':'apartments'}, 'multipolygons')[0])
        self.assertIn('edifici', classify({'building:part':'yes'}, 'multipolygons')[0])
        targets, category = classify({'historic':'ruins','name':'Casera vecchia'}, 'points')
        self.assertIn('fabbricati_punti', targets)
        self.assertEqual(category, 'rudere')

    def test_populated_landuse_is_available_for_overview_rendering(self):
        from scialpinismo.osm_rules import classify
        self.assertIn('insediamenti', classify({'landuse':'residential'}, 'multipolygons')[0])
        self.assertIn('insediamenti', classify({'landuse':'commercial'}, 'multipolygons')[0])
        self.assertNotIn('insediamenti', classify({'landuse':'forest'}, 'multipolygons')[0])

    def test_glacier_and_river_are_distinct_and_station_is_kept(self):
        from scialpinismo.osm_rules import classify
        self.assertEqual(classify({'natural':'glacier'}, 'multipolygons'), (['acque'], 'ghiacciaio'))
        self.assertEqual(classify({'waterway':'riverbank'}, 'multipolygons'), (['acque'], 'fiume'))
        self.assertIn('stazioni', classify({'aerialway':'station','building':'yes'}, 'multipolygons')[0])

    def test_road_classes_are_exclusive_and_widths_decrease(self):
        from scialpinismo.readability import ROAD_CLASS, ROAD_WIDTHS
        from scialpinismo.engine import memory_layer
        from qgis.core import QgsExpression, QgsExpressionContext, QgsFeature
        from qgis.PyQt.QtCore import QVariant
        layer = memory_layer('roads', 'MultiLineString', fields=[('highway',QVariant.String),('ref',QVariant.String)])
        context = QgsExpressionContext()
        expression = QgsExpression(ROAD_CLASS)
        self.assertFalse(expression.hasParserError(), expression.parserErrorString())
        for highway, ref, expected in [('motorway','A27','autostrada'),('primary','SS51','primaria'),
                                      ('secondary','SP638','secondaria'),('residential','','locale'),('service','','servizio')]:
            f = QgsFeature(layer.fields()); f.setAttributes([highway,ref])
            context.setFeature(f); context.setFields(layer.fields())
            self.assertEqual(expression.evaluate(context), expected, expression.evalErrorString())
        widths = [w for _,w in ROAD_WIDTHS]
        self.assertEqual(widths, sorted(widths, reverse=True))

    def test_red_house_renders_without_external_assets(self):
        from scialpinismo.engine import memory_layer, add_feature
        from scialpinismo.readability import house_symbol
        from qgis.core import QgsMapSettings, QgsMapRendererSequentialJob
        from qgis.PyQt.QtCore import QSize
        from qgis.PyQt.QtGui import QColor
        layer=memory_layer('hut','Point', 'EPSG:32633')
        add_feature(layer,QgsGeometry.fromWkt('POINT(10 10)'),[])
        layer.renderer().setSymbol(house_symbol())
        settings=QgsMapSettings();settings.setLayers([layer]);settings.setDestinationCrs(layer.crs())
        settings.setOutputSize(QSize(96,96));settings.setOutputDpi(96);settings.setBackgroundColor(QColor('white'))
        settings.setExtent(QgsRectangle(0,0,20,20))
        job=QgsMapRendererSequentialJob(settings);job.start();job.waitForFinished();img=job.renderedImage()
        red=sum(1 for y in range(img.height()) for x in range(img.width()) if img.pixelColor(x,y).red()>130 and img.pixelColor(x,y).green()<90)
        self.assertGreater(red,30)

    def test_parking_symbol_and_peak_elevation_are_multiscale(self):
        from scialpinismo.engine import memory_layer, add_feature
        from scialpinismo.readability import parking_symbol, poi_style, PEAK_LABEL_EXPRESSION
        from qgis.core import QgsExpression, QgsExpressionContext, QgsExpressionContextScope
        from qgis.PyQt.QtCore import QVariant
        symbol = parking_symbol(compact=False)
        compact = parking_symbol(compact=True)
        self.assertEqual(symbol.symbolLayer(0).color().name(), '#1769aa')
        self.assertEqual(symbol.symbolLayer(1).character(), 'P')
        self.assertLess(compact.symbolLayer(0).size(), symbol.symbolLayer(0).size())

        fields = [('amenity', QVariant.String), ('natural', QVariant.String),
                  ('place', QVariant.String), ('ele', QVariant.String),
                  ('label', QVariant.String)]
        layer = memory_layer('poi', 'Point', fields=fields)
        poi_style(layer)
        rules = layer.renderer().rootRule().children()
        self.assertIn('zoom 15', rules[2].label())
        self.assertIn('zoom 16+', rules[3].label())
        add_feature(layer, QgsGeometry.fromWkt('POINT(0 0)'), ['', 'peak', '', '3244', 'Vetta di prova'])
        feature = next(layer.getFeatures())
        context = QgsExpressionContext(); context.setFields(layer.fields()); context.setFeature(feature)
        scope = QgsExpressionContextScope(); scope.setVariable('scialpinismo_scale_15_16', 10000); scope.setVariable('map_scale', 9000); context.appendScope(scope)
        expression = QgsExpression(PEAK_LABEL_EXPRESSION)
        self.assertEqual(expression.evaluate(context), 'Vetta di prova · 3244 m')
        scope.setVariable('map_scale', 11000)
        self.assertEqual(expression.evaluate(context), 'Vetta di prova')

    def test_slope_style_is_multiply_translucent_and_keeps_uncolored_band(self):
        from qgis.core import QgsRasterLayer
        from qgis.PyQt.QtGui import QPainter
        from scialpinismo.cartography import slope_style
        path=self.root/'slope.tif'
        ds=gdal.GetDriverByName('GTiff').Create(str(path),8,8,1,gdal.GDT_Float32)
        ds.SetGeoTransform([300000,5,0,5160000,0,-5]);ds=None
        layer=QgsRasterLayer(str(path),'slope')
        slope_style(layer)
        self.assertEqual(layer.blendMode(),QPainter.CompositionMode_Multiply)
        self.assertAlmostEqual(layer.opacity(),0.55)
        items=layer.renderer().shader().rasterShaderFunction().colorRampItemList()
        self.assertEqual(next(i.color.alpha() for i in items if i.value==10),0)

    def test_named_mountain_shelter_is_kept_without_shelter_type(self):
        from scialpinismo.osm_rules import classify
        targets,category=classify({'amenity':'shelter','name':'Bivacco di prova'},'points')
        self.assertIn('rifugi',targets)
        self.assertEqual(category,'bivacco')

    def test_osm_import_preserves_elevation_used_for_overview_names(self):
        from scialpinismo.engine import osm_config_path
        source=self.root/'test.osm'
        source.write_text('<osm version="0.6" generator="test"><node id="1" version="1" lat="46.54" lon="12.13"><tag k="name" v="Vetta di prova"/><tag k="natural" v="peak"/><tag k="ele" v="3244"/></node></osm>')
        config=osm_config_path(self.w.archive)
        result=self.root/'osm.gpkg'
        ds=gdal.VectorTranslate(str(result),str(source),options=['-f','GPKG','-oo','CONFIG_FILE='+str(config)])
        points=ds.GetLayerByName('points')
        feature=points.GetNextFeature()
        self.assertIsNotNone(feature)
        self.assertEqual(str(feature.GetField('ele')),'3244')
        ds=None

    def test_sac_labels_are_six_hiking_grades_without_ski_conversion(self):
        from scialpinismo.readability import SAC_EXPRESSION
        from scialpinismo.engine import memory_layer
        from qgis.core import QgsExpression, QgsExpressionContext, QgsFeature
        from qgis.PyQt.QtCore import QVariant
        layer = memory_layer('trail', 'MultiLineString', fields=[('sac_scale', QVariant.String)])
        context = QgsExpressionContext(); context.setFields(layer.fields())
        expression = QgsExpression(SAC_EXPRESSION)
        for key, grade in [('hiking','T1'),('mountain_hiking','T2'),('demanding_mountain_hiking','T3'),
                           ('alpine_hiking','T4'),('demanding_alpine_hiking','T5'),('difficult_alpine_hiking','T6')]:
            feature = QgsFeature(layer.fields()); feature.setAttributes([key]); context.setFeature(feature); context.setFields(layer.fields())
            self.assertEqual(expression.evaluate(context), grade)
        feature.setAttributes(['PD']); context.setFeature(feature)
        self.assertNotIn(expression.evaluate(context), ['T1','T2','T3','T4','T5','T6'])

    def test_boundary_mask_preserves_holes_and_removes_outside(self):
        from scialpinismo.exporter import tile_coverage_mask, rect_tile
        bounds = rect_tile(0, 0, 0)
        w = bounds.width()
        geom = QgsGeometry.fromRect(QgsRectangle(-w/4, -w/4, w/4, w/4))
        hole = QgsGeometry.fromRect(QgsRectangle(-w/16, -w/16, w/16, w/16))
        mask = tile_coverage_mask(geom.difference(hole), 0, 0, 0)
        self.assertEqual(mask.getpixel((0,0)), 0)
        self.assertEqual(mask.getpixel((128,128)), 0)
        self.assertEqual(mask.getpixel((90,128)), 255)

    def test_png_clipping_preserves_white_inside_and_makes_outside_transparent(self):
        from scialpinismo.exporter import clip_mbtiles, rect_tile
        path = self.root/'clip.mbtiles'
        data = io.BytesIO(); Image.new('RGB', (256,256), 'white').save(data,format='PNG')
        with sqlite3.connect(str(path)) as con:
            con.executescript('create table metadata(name text,value text); create table tiles(zoom_level integer,tile_column integer,tile_row integer,tile_data blob);')
            con.execute('insert into metadata values (?,?)', ('format','png'))
            for x in (0,1): con.execute('insert into tiles values (12,?,4095,?)',(x,data.getvalue()))
        b = rect_tile(0,0,12); w=b.width()
        geom = QgsGeometry.fromRect(QgsRectangle(b.xMinimum()+w/4,b.yMinimum()+w/4,b.xMaximum()-w/4,b.yMaximum()-w/4))
        result = clip_mbtiles(path, geom)
        self.assertEqual(result['removed_tiles'],1)
        inspect_mbtiles(path,12,12)
        with sqlite3.connect(str(path)) as con:
            image = Image.open(io.BytesIO(con.execute('select tile_data from tiles').fetchone()[0]))
            self.assertEqual(image.getpixel((0,0))[3],0)
            self.assertEqual(image.getpixel((128,128)),(255,255,255,255))

    def test_clipped_jpeg_configuration_rejected(self):
        self.config['export'].update(clip_to_perimeter=True,tile_format='jpg')
        with self.assertRaisesRegex(ValueError, 'PNG'):
            self.w.validate_config(self.config)

    def test_osm_extraction_keeps_polygon_species_after_points_and_lines(self):
        from qgis.core import QgsVectorLayer
        source=self.root/'forest.osm'
        source.write_text('''<osm version="0.6" generator="test">
<node id="1" lat="46.531" lon="12.111"><tag k="natural" v="peak"/><tag k="ele" v="3000"/></node>
<node id="2" lat="46.533" lon="12.112"/>
<node id="10" lat="46.532" lon="12.113"/><node id="11" lat="46.536" lon="12.113"/>
<node id="12" lat="46.536" lon="12.117"/><node id="13" lat="46.532" lon="12.117"/>
<way id="20"><nd ref="1"/><nd ref="2"/><tag k="highway" v="path"/><tag k="sac_scale" v="hiking"/></way>
<way id="30"><nd ref="10"/><nd ref="11"/><nd ref="12"/><nd ref="13"/><nd ref="10"/>
<tag k="natural" v="wood"/><tag k="leaf_type" v="needleleaved"/><tag k="species" v="Larix decidua"/></way></osm>''')
        geometry=geometry_in(QgsGeometry.fromWkt(self.config['perimeter_wkt']),'EPSG:4326',self.config['processing_crs'])
        gpkg=self.root/'area.gpkg'
        self.w.extract_osm(source,geometry,self.config,gpkg,self.root/'osm.json')
        layer=QgsVectorLayer(str(gpkg)+'|layername=vegetazione','wood','ogr')
        features=list(layer.getFeatures());self.assertEqual(len(features),1)
        self.assertEqual(features[0]['leaf_type'],'needleleaved')
        self.assertEqual(features[0]['species'],'Larix decidua')

    def test_osm_source_without_polygons_is_valid_when_another_has_them(self):
        from qgis.core import QgsVectorLayer
        linear=self.root/'linear.osm'
        linear.write_text('''<osm version="0.6" generator="test">
<node id="1" lat="46.531" lon="12.111"><tag k="natural" v="peak"/></node>
<node id="2" lat="46.533" lon="12.112"/>
<way id="20"><nd ref="1"/><nd ref="2"/><tag k="highway" v="path"/></way></osm>''')
        polygon=self.root/'polygon.osm'
        polygon.write_text('''<osm version="0.6" generator="test">
<node id="10" lat="46.532" lon="12.113"/><node id="11" lat="46.536" lon="12.113"/>
<node id="12" lat="46.536" lon="12.117"/><node id="13" lat="46.532" lon="12.117"/>
<way id="30"><nd ref="10"/><nd ref="11"/><nd ref="12"/><nd ref="13"/><nd ref="10"/>
<tag k="natural" v="wood"/></way></osm>''')
        geometry=geometry_in(QgsGeometry.fromWkt(self.config['perimeter_wkt']),
                             'EPSG:4326',self.config['processing_crs'])
        gpkg=self.root/'combined.gpkg'
        self.w.extract_osm([linear,polygon],geometry,self.config,gpkg,self.root/'combined.json')
        self.assertEqual(QgsVectorLayer(
            str(gpkg)+'|layername=vegetazione','wood','ogr').featureCount(),1)


if __name__ == '__main__':
    app = QgsApplication([], False)
    app.setPrefixPath('/Applications/QGIS.app/Contents/Resources/qgis', True)
    app.initQgis()
    QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WorkflowTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    app.exitQgis()
    sys.exit(not result.wasSuccessful())
