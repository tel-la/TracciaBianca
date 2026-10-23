"""Verifica dipendenze dati, progetti e VRT senza modificare la cartella."""
import json
import sys
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from qgis.core import QgsApplication, QgsProject
from osgeo import gdal


def audit(root):
    root = Path(root).resolve()
    result = {'ok': True, 'external': [], 'missing': [], 'remote_layers': [],
              'projects': [], 'sources': [], 'vrts': [], 'symlinks': [], 'catalog_areas': [], 'models': []}
    def check(path, owner):
        path = path.resolve()
        if not path.is_relative_to(root):
            result['external'].append({'owner': owner, 'path': str(path)})
        if not path.exists():
            result['missing'].append({'owner': owner, 'path': str(path)})
    common = root/'##_aree/_archivio_comune'
    data = json.loads((common/'fonti.json').read_text())
    for source in data['sources']:
        if source.get('provider'):
            result['sources'].append({'id': source['id'], 'provider': source['provider'], 'url': source['url']})
        else:
            check(common/source['path'], source['id'])
            result['sources'].append({'id': source['id'], 'path': source['path']})
    osm_sources = data.get('osm_sources') or ([data['osm']] if data.get('osm') else [])
    if not osm_sources:
        result['missing'].append({'owner': 'OSM', 'path': 'nessuna sorgente registrata'})
    for source in osm_sources:
        check(common/source['path'], 'OSM '+source.get('id', source['path']))
    with sqlite3.connect((common/'catalogo.gpkg').resolve().as_uri()+'?mode=ro', uri=True) as con:
        for name, config in con.execute('SELECT area_id, config FROM aree'):
            check(common/config, 'catalogo area '+name)
            result['catalog_areas'].append(name)
    for asset in data.get('supplementary_assets', []):
        check(common/asset['path'], 'materiale supplementare')
    for path in sorted(root.rglob('*.qgz')):
        project = QgsProject()
        owner = str(path.relative_to(root))
        loaded = project.read(str(path))
        invalid = []
        if not loaded:result['missing'].append({'owner': owner, 'path': 'progetto non leggibile'})
        for layer in project.mapLayers().values():
            source = layer.source()
            if layer.providerType() in ('wms', 'wcs') or '://' in source:
                result['remote_layers'].append({'owner': owner, 'layer': layer.name()})
            else:
                check(Path(source.split('|')[0]), owner+': '+layer.name())
            if not layer.isValid():invalid.append(layer.name())
        result['projects'].append({'file': owner, 'layers': len(project.mapLayers()), 'invalid': invalid})
        project.clear()
    for path in sorted(common.rglob('*.vrt')):
        owner = str(path.relative_to(root)); relative = True
        for node in ET.parse(path).findall('.//SourceFilename'):
            local = node.get('relativeToVRT') == '1'
            relative &= local
            check(path.parent/node.text if local else Path(node.text), owner)
        dataset = gdal.Open(str(path))
        readable = dataset is not None and dataset.RasterCount > 0
        dataset = None
        result['vrts'].append({'file': owner, 'relative': relative, 'gdal_readable': readable})
    for path in root.rglob('*.model3'):
        absolute = [n.get('value') for n in ET.parse(path).iter() if n.get('value', '').startswith('/')]
        result['models'].append({'file': str(path.relative_to(root)), 'absolute_defaults': absolute})
    for path in root.rglob('*'):
        if path.is_symlink():
            check(path, str(path.relative_to(root)))
            result['symlinks'].append(str(path.relative_to(root)))
    result['ok'] = not (result['external'] or result['missing'] or result['remote_layers'] or
                        any(p['invalid'] for p in result['projects']) or
                        any(not v['relative'] or not v['gdal_readable'] for v in result['vrts']) or
                        any(m['absolute_defaults'] for m in result['models']))
    return result


if __name__ == '__main__':
    app = QgsApplication([], False);app.initQgis()
    result = audit(Path(__file__).resolve().parents[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    app.exitQgis()
    sys.exit(0 if result['ok'] else 1)
