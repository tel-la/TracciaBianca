"""Griglia stabile, catalogo pubblico e quadro di unione dell'atlante."""
import hashlib
import json
import math
import re
import shutil
import unicodedata
from pathlib import Path
import numpy as np
from osgeo import gdal, ogr
from qgis.core import (QgsGeometry, QgsRectangle, QgsProject, QgsVectorLayer,
                       QgsFillSymbol, QgsMarkerSymbol, QgsPalLayerSettings, QgsTextFormat, QgsVectorLayerSimpleLabeling,
                       QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel, QgsLayoutPoint,
                       QgsLayoutSize, QgsLayoutExporter, QgsCoordinateReferenceSystem)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor, QFont
from .engine import save_json, load_json, geometry_in, memory_layer, add_feature, write_layer, osm_records

GRID_ID = 'ALP35_OVERLAP2_LAEA_v2'
CRS = 'EPSG:3035'
CELL_SIZE = 35000
OVERLAP_SIDE = 2000
STEP = CELL_SIZE - 2 * OVERLAP_SIDE
MARGIN = OVERLAP_SIDE  # Alias conservato nei metadati delle aree.
DEFAULT_ALPINE_BBOX = [8.25, 45.40, 13.90, 47.20]
DEFAULT_MIN_ELEVATION_M = 600
DEFAULT_MIN_MOUNTAIN_PERCENT = 1.0
# Composizione editoriale dell'atlante: queste eccezioni restano applicate anche
# quando la griglia viene rigenerata dal DTM.
EXCLUDED_CELL_IDS = {
    'ALP_E134_N080',
    'ALP_E135_N080',
    'ALP_E139_N080',
    'ALP_E140_N080',
    'ALP_E141_N080',
    'ALP_E142_N080',
    'ALP_E144_N086',
    'ALP_E146_N082',
    'ALP_E147_N082',
}
FORCED_CELL_IDS = {'ALP_E136_N083'}
FAMOUS_ALPINE_PLACES = {
    name.casefold() for name in (
        'Domodossola', 'Macugnaga', 'Verbania', 'Como', 'Lecco', 'Sondrio', 'Bormio', 'Livigno',
        'Edolo', 'Ponte di Legno', 'Madonna di Campiglio', 'Trento', 'Bolzano', 'Merano', 'Ortisei',
        'Canazei', 'Moena', 'San Martino di Castrozza', "Cortina d'Ampezzo", 'Belluno', 'Auronzo di Cadore',
        'San Candido', 'Brunico', 'Tolmezzo', 'Tarvisio', 'Pordenone', 'Udine')}
ALPINE_SECTORS = (
    (9.05, 'Lago Maggiore – Ossola'),
    (9.55, 'Lario – Valchiavenna'),
    (10.15, 'Valtellina – Orobie'),
    (10.75, 'Adamello – Garda'),
    (11.35, 'Trentino occidentale – Dolomiti di Brenta'),
    (11.95, 'Alto Adige – Dolomiti occidentali'),
    (12.55, 'Dolomiti – Cadore'),
    (13.20, 'Carnia – Dolomiti Friulane'),
    (180.0, 'Alpi Giulie – Friuli'))
# Riquadri alpini d'alta quota senza centri abitati nell'estratto OSM: il nome
# geografico esplicito evita etichette di settore ripetute e poco informative.
REFERENCE_OVERRIDES = {
    'ALP_E134_N081': 'Biellese – Valsesia',
    'ALP_E134_N082': 'Valsesia – Monte Rosa',
    'ALP_E134_N083': 'Monte Rosa – Vallese',
    'ALP_E136_N083': 'Ticino – Alpi Lepontine',
    'ALP_E139_N084': 'Engadina – Bernina',
    'ALP_E141_N085': 'Alpi Venoste – Ötztal',
    'ALP_E144_N086': 'Alpi Aurine – Zillertal',
    'ALP_E145_N085': 'Alti Tauri – Pusteria',
}
MAX_PREPARE_CELLS = 2
DEFAULT_ATLAS_MAX_MISSING_PERCENT = 0.01


def slug(value):
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', value).strip('-')[:70] or 'zona'


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def cell_id(col, row):
    return f'ALP_E{col:03d}_N{row:03d}'


def core_geometry(col, row):
    """Nucleo esclusivo 31 x 31 km; i nuclei tassellano il territorio senza vuoti."""
    return QgsGeometry.fromRect(QgsRectangle(col*STEP, row*STEP, (col+1)*STEP, (row+1)*STEP))


def cell_geometry(col, row):
    """Riquadro di analisi 35 x 35 km, esteso 2 km oltre ogni lato del nucleo."""
    return QgsGeometry.fromRect(QgsRectangle(col*STEP-OVERLAP_SIDE, row*STEP-OVERLAP_SIDE,
                                             (col+1)*STEP+OVERLAP_SIDE,
                                             (row+1)*STEP+OVERLAP_SIDE))


def validate_atlas_config(c):
    a = c['atlas']
    if (a['grid_id'] != GRID_ID or a['margin_m'] != OVERLAP_SIDE
            or a.get('cell_size_m') != CELL_SIZE or a.get('step_m') != STEP
            or c['id'] != cell_id(a['col'], a['row'])):
        raise ValueError('Configurazione griglia atlante incoerente')
    if not a['display_name'].strip():
        raise ValueError('Nome pubblico obbligatorio')
    actual = geometry_in(QgsGeometry.fromWkt(c['perimeter_wkt']), c['perimeter_crs'], CRS)
    if actual.symDifference(cell_geometry(a['col'], a['row'])).area() > 1:
        raise ValueError('Copertura atlante diversa da 35 x 35 km')


def grid_path(w):
    return w.archive/'atlante_griglia_v2.json'


def grid_vector_path(w):
    return w.archive/'atlante_griglia_v2.gpkg'


def _sector_name(longitude):
    return next(name for east, name in ALPINE_SECTORS if longitude < east)


def _population(tags):
    match = re.search(r'"population"=>"([0-9 .,_]+)"', tags or '')
    if not match:
        return 0
    try:
        return int(re.sub(r'\D', '', match.group(1)))
    except ValueError:
        return 0


def assign_reference_names(w, data):
    """Assegna una località OSM intuitiva a ogni nucleo, con fallback geografico."""
    cells = {c['id']: c for c in data['cells']}
    choices = {}
    manifest = w.archive/'fonti.json'
    registered = osm_records(load_json(manifest)) if manifest.exists() else []
    osm_dir = w.archive/'osm'
    pbfs = [p for p in ((w.archive/record['path']).resolve() for record in registered) if p.exists()]
    pbfs.extend(p for p in sorted({p.resolve() for p in osm_dir.glob('*.osm.pbf')}) if p not in pbfs)
    for pbf in pbfs:
        dataset = ogr.Open(str(pbf)); layer = dataset.GetLayerByName('points') if dataset else None
        if layer:
            layer.SetSpatialFilterRect(*DEFAULT_ALPINE_BBOX)
            layer.SetAttributeFilter("name IS NOT NULL AND place IN ('city','town','village','municipality')")
            priority = {'city': 5000, 'town': 4000, 'municipality': 3500, 'village': 3000}
            for feature in layer:
                w.cancel()
                name = (feature.GetField('name') or '').strip(); place = feature.GetField('place') or ''
                geometry = feature.GetGeometryRef()
                if not name or geometry is None:
                    continue
                lon, lat = geometry.GetX(), geometry.GetY()
                projected = geometry_in(QgsGeometry.fromWkt(f'POINT ({lon} {lat})'), 'EPSG:4326', CRS).asPoint()
                key = cell_id(math.floor(projected.x()/STEP), math.floor(projected.y()/STEP))
                if key not in cells:
                    continue
                population = _population(feature.GetField('other_tags'))
                score = priority.get(place, 0) + min(3000, math.log10(max(1, population))*600)
                if name.casefold() in FAMOUS_ALPINE_PLACES:
                    score += 10000
                candidate = {'name': name, 'place': place, 'population': population,
                             'lon': lon, 'lat': lat, 'score': score, 'source': 'OpenStreetMap'}
                if score > choices.get(key, {}).get('score', -1):
                    choices[key] = candidate
            layer.SetSpatialFilter(None)
        dataset = None
    features = []
    for cell in data['cells']:
        key = cell['id']; choice = choices.get(key)
        if choice:
            sector = _sector_name(choice['lon'])
            reference = {**choice, 'sector': sector}
            if cell.get('name_source') != 'manual':
                cell['display_name'] = f"{choice['name']} · {sector}"
                cell['name_source'] = 'osm_reference'
        else:
            center = geometry_in(core_geometry(cell['col'], cell['row']).centroid(), CRS, 'EPSG:4326').asPoint()
            sector = _sector_name(center.x())
            reference_name = REFERENCE_OVERRIDES.get(key, sector)
            source = 'area_montuosa' if key in REFERENCE_OVERRIDES else 'settore_geografico'
            reference = {'name': reference_name, 'place': 'mountain_region', 'population': 0,
                         'lon': center.x(), 'lat': center.y(), 'source': source,
                         'sector': sector}
            if cell.get('name_source') != 'manual':
                cell['display_name'] = reference_name
                cell['name_source'] = 'geographic_fallback'
        cell['reference'] = reference
        features.append({'type': 'Feature', 'properties': {
                         'cell_id': key, 'name': reference['name'], 'area_name': cell['display_name'],
                         'place': reference['place'], 'population': reference['population'],
                         'sector': reference['sector'], 'source': reference['source']},
                         'geometry': {'type': 'Point', 'coordinates': [reference['lon'], reference['lat']]}})
    return {'type': 'FeatureCollection', 'features': features}


def _mountain_source(w):
    available = [s for s in w.sources() if s.get('verified') and w.source_available(s)]
    if not available:
        raise ValueError('Filtro montagne: nessun DTM verificato disponibile')
    return next((s for s in available if s['id'] == 'hrdtm5m'),
                min(available, key=lambda s: s.get('native_resolution_m') or 9999))


def _mountain_metrics(w, candidates, min_elevation_m, min_mountain_percent):
    """Campiona il DTM a 500 m: include una cella se almeno la quota richiesta è montana."""
    source = _mountain_source(w)
    accepted = []
    for record in candidates:
        w.cancel()
        bb = cell_geometry(record['col'], record['row']).boundingBox()
        raster = gdal.Warp('', str(w.source_path(source)), format='MEM', srcSRS=source['crs'], dstSRS=CRS,
                           outputBounds=[bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()],
                           width=70, height=70, srcNodata=source.get('nodata', -9999), dstNodata=-9999,
                           outputType=gdal.GDT_Float32, resampleAlg='max', warpMemoryLimit=64)
        if raster is None:
            continue
        values = raster.ReadAsArray(); raster = None
        valid = np.isfinite(values) & (values != -9999)
        high = valid & (values >= min_elevation_m)
        percent = float(high.sum()) / values.size * 100
        if percent + 1e-9 < min_mountain_percent and record['id'] not in FORCED_CELL_IDS:
            continue
        record['mountain_percent'] = round(percent, 3)
        record['max_elevation_m'] = round(float(values[valid].max()), 1) if valid.any() else None
        accepted.append(record)
    return accepted


def make_grid(w, bbox=None, mountain_only=True, min_elevation_m=DEFAULT_MIN_ELEVATION_M,
              min_mountain_percent=DEFAULT_MIN_MOUNTAIN_PERCENT):
    """Crea/estende i riquadri alpini; senza bbox usa Lago Maggiore–Friuli."""
    if not 0 <= min_elevation_m <= 5000 or not 0 < min_mountain_percent <= 100:
        raise ValueError('Parametri del filtro montagne non validi')
    path = grid_path(w)
    data = load_json(path) if path.exists() else {
        'grid_id': GRID_ID, 'crs': CRS, 'origin': [0, 0], 'cell_size_m': CELL_SIZE,
        'step_m': STEP, 'overlap_side_m': OVERLAP_SIDE, 'cells': []}
    if data.get('grid_id') != GRID_ID:
        raise ValueError('Griglia atlante incompatibile: usare il nuovo archivio v2')
    cells = {c['id']: c for c in data['cells']}
    bbox = bbox or DEFAULT_ALPINE_BBOX
    if len(bbox) != 4 or not (-180 <= bbox[0] < bbox[2] <= 180 and -85 <= bbox[1] < bbox[3] <= 85):
        raise ValueError('BBOX WGS84 non valido')
    target = geometry_in(QgsGeometry.fromRect(QgsRectangle(*bbox)), 'EPSG:4326', CRS)
    bb = target.boundingBox(); candidates = []
    for col in range(math.floor(bb.xMinimum()/STEP)-1, math.ceil(bb.xMaximum()/STEP)+1):
        for row in range(math.floor(bb.yMinimum()/STEP)-1, math.ceil(bb.yMaximum()/STEP)+1):
            if cell_geometry(col, row).intersection(target).area() <= 0:
                continue
            key = cell_id(col, row)
            candidates.append({**cells.get(key, {}), 'id': key, 'col': col, 'row': row,
                               'display_name': cells.get(key, {}).get('display_name', 'Settore alpino '+key)})
    candidate_ids = {record['id'] for record in candidates}
    if mountain_only:
        candidates = _mountain_metrics(w, candidates, min_elevation_m, min_mountain_percent)
    candidates = [record for record in candidates if record['id'] not in EXCLUDED_CELL_IDS]
    # Ricalcola il dominio richiesto quando cambiano soglie o filtro, conservando
    # nomi e celle eventualmente create fuori dall'estensione corrente.
    for key in candidate_ids:
        cells.pop(key, None)
    for record in candidates:
        cells[record['id']] = record
    data['cells'] = [cells[k] for k in sorted(cells)]
    data['mountain_filter'] = {'enabled': bool(mountain_only), 'min_elevation_m': min_elevation_m,
                               'min_mountain_percent': min_mountain_percent,
                               'source': _mountain_source(w)['id'] if mountain_only else None}
    if not data['cells']: raise ValueError('Nessuna cella: specificare una estensione o preparare una area')
    places = assign_reference_names(w, data)
    save_json(path, data)
    write_grid(w, data)
    save_json(w.root/'08_Atlante/localita.geojson', places)
    return data


def write_grid(w, data):
    path = grid_vector_path(w); temporary = path.with_suffix('.partial.gpkg')
    temporary.unlink(missing_ok=True)
    for layer_name, geometry_function in [('celle_analisi', cell_geometry), ('nuclei', core_geometry)]:
        layer = memory_layer(layer_name, crs=CRS, fields=[('cell_id', QVariant.String), ('nome', QVariant.String),
                             ('lato_m', QVariant.Int), ('passo_m', QVariant.Int), ('sovrapp_m', QVariant.Int),
                             ('montagna_pct', QVariant.Double), ('quota_max_m', QVariant.Double)])
        for c in data['cells']:
            add_feature(layer, geometry_function(c['col'], c['row']),
                        [c['id'], c['display_name'], CELL_SIZE, STEP, OVERLAP_SIDE,
                         c.get('mountain_percent'), c.get('max_elevation_m')])
        write_layer(layer, temporary, layer_name)
    temporary.replace(path)
    out = w.root/'08_Atlante'; out.mkdir(exist_ok=True)
    shutil.copy2(path, out/'griglia.gpkg')
    features = []
    for c in data['cells']:
        geometry = geometry_in(cell_geometry(c['col'], c['row']).densifyByDistance(1000), CRS, 'EPSG:4326')
        features.append({'type': 'Feature', 'properties': {
                         'cell_id': c['id'], 'nome': c['display_name'],
                         'mountain_percent': c.get('mountain_percent'),
                         'max_elevation_m': c.get('max_elevation_m')},
                         'geometry': json.loads(geometry.asJson())})
    save_json(out/'celle_analisi.geojson', {'type': 'FeatureCollection', 'features': features})


def rename_cell(w, key, name):
    if not name.strip(): raise ValueError('Nome geografico obbligatorio')
    data = load_json(grid_path(w))
    cell = next(c for c in data['cells'] if c['id'] == key)
    cell['display_name'] = name.strip()
    cell['name_source'] = 'manual'
    save_json(grid_path(w), data)
    write_grid(w, data)
    config = w.areas/key/'area.json'
    if config.exists():
        c = load_json(config); c['atlas']['display_name'] = name.strip(); save_json(config, c)
    return cell


def prepare_cells(w, keys, max_missing_percent=DEFAULT_ATLAS_MAX_MISSING_PERCENT):
    data = load_json(grid_path(w)); cells = {c['id']: c for c in data['cells']}
    if not keys or any(k not in cells for k in keys): raise ValueError('Selezionare celle presenti nella griglia')
    keys = list(dict.fromkeys(keys))
    if len(keys) > MAX_PREPARE_CELLS:
        raise ValueError('Preparare al massimo due celle per volta; completare ed esportare le zone in sequenza')
    if len(keys) == 2:
        first, second = (cells[key] for key in keys)
        if abs(first['col']-second['col']) + abs(first['row']-second['row']) != 1:
            raise ValueError('Le due celle di prova devono essere adiacenti e condividere un lato')
    results = []
    for key in keys:
        w.cancel(); c = cells[key]; config = w.areas/key/'area.json'
        try:
            if config.exists():
                result = w.update(config, max_missing_percent=max_missing_percent)
            else:
                geometry = cell_geometry(c['col'], c['row'])
                center = geometry_in(geometry, CRS, 'EPSG:4326').centroid().asPoint()
                zone = min(60, max(1, math.floor((center.x()+180)/6)+1))
                result = w.prepare(key, geometry, CRS, crs=f'EPSG:{32600+zone}',
                    max_missing_percent=max_missing_percent, atlas={
                    'grid_id': GRID_ID, 'col': c['col'], 'row': c['row'], 'margin_m': OVERLAP_SIDE,
                    'cell_size_m': CELL_SIZE, 'step_m': STEP,
                    'core_wkt': core_geometry(c['col'], c['row']).asWkt(),
                    'display_name': c['display_name']})
            set_production_status(w, key, 'prepared', '')
            results.append(result)
        except Exception as exc:
            set_production_status(w, key, 'blocked', str(exc))
            raise

    return results



def set_production_status(w, key, status, reason):
    path = w.archive/'atlante_stato.json'
    states = load_json(path) if path.exists() else {}
    states[key] = {'status': status, 'reason': reason}
    save_json(path, states)


def record_export(w, key, catalog):
    """Aggiorna il registro leggero dell'atlante senza generare sito, PDF o altre celle."""
    import datetime as dt
    set_production_status(w, key, 'release_ready', '')
    path = w.archive/'atlante_produzioni.json'
    registry = load_json(path) if path.exists() else {}
    registry[key] = {
        'edition': catalog['edition'],
        'zoom': [catalog['settings']['minzoom'], catalog['settings']['maxzoom']],
        'packages': len(catalog['packages']),
        'bytes': sum(package['bytes'] for package in catalog['packages']),
        'catalog': str(Path('..')/key/'output/mbtiles/catalogo_mbtiles.json'),
        'status': 'release_ready',
        'updated': dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    save_json(path, registry)
    return registry[key]

def publication_ready(catalog):
    """Un export tecnicamente valido è pronto per essere inserito in una Release."""
    return catalog.get('technical_validation') == 'passed'


def publish_cell(w, key):
    path = w.areas/key/'output/mbtiles/catalogo_mbtiles.json'; c = load_json(path)
    if not publication_ready(c): raise ValueError('Validazione tecnica MBTiles non completata')
    for pack in c['packages']:
        file = path.parent/pack['file']
        if file.stat().st_size != pack['bytes'] or sha256_file(file) != pack['sha256']:
            raise ValueError('File modificato dopo la validazione')
    c['publication_status'] = 'release_ready'; save_json(path, c)
    return c['publication_status']



def build_catalog(w):
    data = load_json(grid_path(w)); out = w.root/'08_Atlante'; out.mkdir(exist_ok=True)
    places = assign_reference_names(w, data)
    save_json(grid_path(w), data)
    write_grid(w, data)
    save_json(out/'localita.geojson', places)
    states_path = w.archive/'atlante_stato.json'
    states = load_json(states_path) if states_path.exists() else {}
    records, cores, covers = [], [], []
    for cell in data['cells']:
        key = cell['id']; source = w.areas/key/'output/mbtiles/catalogo_mbtiles.json'
        cat = load_json(source) if source.exists() else {}
        published = (cat.get('publication_status') == 'published' and publication_ready(cat)
                     and cat.get('atlas', {}).get('display_name') == cell['display_name'])
        packs = []
        for pack in cat.get('packages', []):
            item = {k: pack[k] for k in ('bytes', 'sha256') if k in pack}
            item['file'] = Path(pack['file']).name
            if published:
                src = source.parent/pack['file']
                if src.stat().st_size != pack['bytes'] or sha256_file(src) != pack['sha256']:
                    raise ValueError('Checksum non valido: ' + key)
                relative = Path('downloads')/key/cat['edition']/item['file']
                dst = out/relative; dst.parent.mkdir(parents=True, exist_ok=True)
                if not dst.exists() or sha256_file(dst) != pack['sha256']: shutil.copy2(src, dst)
                item['url'] = relative.as_posix()
            packs.append(item)
        record = {**cell, 'edition': cat.get('edition'), 'zoom': [cat.get('settings', {}).get('minzoom', 12), cat.get('settings', {}).get('maxzoom', 17)],
                  'status': ('published' if published else
                             ('release_ready' if cat and publication_ready(cat) else
                              ('validation_pending' if cat else states.get(key, {}).get('status', 'planned')))),
                  'reason': states.get(key, {}).get('reason', ''),
                  'bytes': sum(p['bytes'] for p in packs), 'packages': packs}
        records.append(record)
        for features, geometry_function in [(cores, core_geometry), (covers, cell_geometry)]:
            # Densifica i bordi prima di riproiettarli: non sono rette in WGS84.
            geo = geometry_in(geometry_function(cell['col'], cell['row']).densifyByDistance(1000), CRS, 'EPSG:4326')
            features.append({'type': 'Feature', 'properties': {
                             'cell_id': key, 'name': cell['display_name'], 'status': record['status'],
                             'mountain_percent': cell.get('mountain_percent'),
                             'max_elevation_m': cell.get('max_elevation_m')},
                             'geometry': json.loads(geo.asJson())})
    manifest = {'grid_id': GRID_ID, 'cell_size_m': CELL_SIZE, 'step_m': STEP,
                'overlap_side_m': OVERLAP_SIDE, 'cells': records}
    core_collection = {'type': 'FeatureCollection', 'features': cores}
    cover_collection = {'type': 'FeatureCollection', 'features': covers}
    save_json(out/'catalogo.json', manifest)
    save_json(out/'nuclei.geojson', core_collection)
    save_json(out/'celle_analisi.geojson', cover_collection)
    write_overview(w, out, data)
    return {'directory': str(out), 'cells': len(records), 'published': sum(r['status']=='published' for r in records)}


def write_overview(w, out, data):
    project = QgsProject(); project.setCrs(QgsCoordinateReferenceSystem(CRS))
    # Copia autonoma per rendere il quadro trasferibile senza archivio sorgenti.
    shutil.copy2(grid_vector_path(w), out/'griglia.gpkg')
    core = QgsVectorLayer(str(out/'griglia.gpkg')+'|layername=nuclei', 'Nuclei 31 km', 'ogr')
    coverage = QgsVectorLayer(str(out/'griglia.gpkg')+'|layername=celle_analisi', 'Aree analisi 35 km', 'ogr')
    core.renderer().setSymbol(QgsFillSymbol.createSimple({'color': '223,235,229,100', 'outline_color': '#245b50', 'outline_width': '0.45'}))
    coverage.renderer().setSymbol(QgsFillSymbol.createSimple({'style': 'no', 'outline_color': '#b87528', 'outline_style': 'dash'}))
    labels = QgsPalLayerSettings(); labels.fieldName = '"cell_id" || \'\\n\' || "nome"'; labels.isExpression = True; labels.priority = 10; labels.displayAll = True
    fmt = QgsTextFormat(); fmt.setSize(8); fmt.setColor(QColor('#173e36')); labels.setFormat(fmt)
    core.setLabeling(QgsVectorLayerSimpleLabeling(labels)); core.setLabelsEnabled(True)
    project.addMapLayer(coverage); project.addMapLayer(core)
    places = QgsVectorLayer(str(out/'localita.geojson'), 'Localita OSM', 'ogr')
    map_layers = [core, coverage]
    if places.isValid() and places.featureCount():
        places.renderer().setSymbol(QgsMarkerSymbol.createSimple({'name':'circle','color':'#375e50','size':'1'}))
        pl = QgsPalLayerSettings(); pl.fieldName = 'name'; pl.priority = 1
        pf = QgsTextFormat(); pf.setSize(6); pl.setFormat(pf)
        places.setLabeling(QgsVectorLayerSimpleLabeling(pl)); places.setLabelsEnabled(True)
        project.addMapLayer(places); map_layers.insert(0, places)
    project.layerTreeRoot().findLayer(coverage.id()).setItemVisibilityChecked(False)
    project.viewSettings().setDefaultViewExtent(__import__('qgis.core', fromlist=['QgsReferencedRectangle']).QgsReferencedRectangle(core.extent(), project.crs()))
    layout = QgsPrintLayout(project); layout.initializeDefaults(); layout.setName('Quadro di unione')
    layout.pageCollection().pages()[0].setPageSize('A4', __import__('qgis.core', fromlist=['QgsLayoutItemPage']).QgsLayoutItemPage.Landscape)
    title = QgsLayoutItemLabel(layout); title.setText('ATLANTE ALPINO | Quadro di unione'); title.setFont(QFont('Arial', 18)); layout.addLayoutItem(title); title.attemptMove(QgsLayoutPoint(12, 9)); title.attemptResize(QgsLayoutSize(275, 14))
    item = QgsLayoutItemMap(layout); layout.addLayoutItem(item); item.attemptMove(QgsLayoutPoint(12, 30)); item.attemptResize(QgsLayoutSize(273, 150)); item.setCrs(project.crs()); item.setLayers(map_layers); item.setKeepLayerSet(True)
    extent = coverage.extent(); extent.scale(1.10); item.zoomToExtent(extent)
    foot = QgsLayoutItemLabel(layout); foot.setText('Tratteggio: area di analisi 35 x 35 km | Linea continua: nucleo 31 x 31 km\nFascia di 2 km per lato; sovrapposizione tra celle: 4 km. Griglia EPSG:3035. Localita: © OpenStreetMap contributors.'); foot.setFont(QFont('Arial', 9)); layout.addLayoutItem(foot); foot.attemptMove(QgsLayoutPoint(12, 185)); foot.attemptResize(QgsLayoutSize(273, 16))
    project.layoutManager().addLayout(layout); project.setFileName(str(out/'quadro_unione.qgz'))
    if not project.write(): raise RuntimeError('Salvataggio quadro QGIS fallito')
    exporter = QgsLayoutExporter(layout)
    if exporter.exportToPdf(str(out/'quadro_unione.pdf'), QgsLayoutExporter.PdfExportSettings()) != QgsLayoutExporter.Success:
        raise RuntimeError('Esportazione PDF fallita')
