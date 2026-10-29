#!/usr/bin/env python3
"""Add the two regions outlined in the 2026-10-29 reference screenshots.

Run with qgis_python.sh. The outlines are planning guides, not surveyed borders:
select a 31 km core when at least 10% of it intersects the drawn region. Existing
cells and their publication metadata are preserved. No MBTiles are generated.
"""

import argparse
import json
import math
import os
from pathlib import Path

from qgis.core import QgsApplication, QgsGeometry, QgsPointXY

from scialpinismo import atlas
from scialpinismo.engine import geometry_in, load_json, save_json


ROOT = Path(__file__).resolve().parents[1]
WEST_IMAGE = 'Screenshot 2026-10-29 alle 19.25.32.png'
CENTRAL_IMAGE = 'Screenshot 2026-10-29 alle 19.26.12.png'

# Pixel coordinates in the original 2156 x 1440 screenshot. The existing
# ALP_E134_N083 core begins at x=690, y=293; each grid step is about 90 px.
WEST_PIXELS = [
    (675, 310), (690, 350), (690, 555), (680, 595), (645, 645),
    (615, 700), (610, 770), (630, 850), (700, 970), (750, 1060),
    (750, 1110), (700, 1150), (640, 1175), (530, 1165), (460, 1110),
    (400, 1030), (375, 965), (375, 850), (390, 700), (450, 500),
    (530, 390), (620, 330),
]

# Pixel coordinates in the original 2262 x 1484 screenshot. Registration
# anchors: Ascoli Piceno (900,83) = (13.576,42.853), Pescara (1500,515) =
# (14.215,42.461). Approximate outlines are rounded to complete map sheets.
CENTRAL_PIXELS = [
    (828, 103), (935, 175), (938, 420), (985, 480), (1090, 555),
    (1175, 800), (1395, 790), (1470, 850), (1510, 920), (1480, 1000),
    (1435, 1060), (1100, 1055), (1020, 975), (950, 930), (840, 810),
    (840, 735), (790, 680), (700, 675), (560, 600), (500, 425),
    (550, 320), (635, 235), (750, 165),
]

WEST_NAMES = [
    (7.30, 45.75, "Valle d'Aosta"), (7.23, 45.52, 'Gran Paradiso'),
    (6.76, 45.38, 'Vanoise'), (6.89, 45.22, 'Haute Maurienne'),
    (7.05, 45.15, 'Val di Susa'), (6.82, 44.77, 'Queyras'),
    (7.08, 44.67, 'Monviso'), (6.74, 44.46, 'Ubaye'),
    (7.43, 44.39, 'Cuneese'), (7.31, 44.22, 'Alpi Marittime'),
    (6.95, 44.12, 'Mercantour'),
    (7.55, 44.15, 'Colle di Tenda'), (7.80, 44.05, 'Alpi Liguri'),
    (7.55, 43.86, 'Alpi Liguri meridionali'),
]
CENTRAL_NAMES = [
    (13.40, 42.71, 'Monti della Laga'),
    (13.53, 42.45, 'Gran Sasso'),
    (13.64, 42.43, 'Campo Imperatore'),
    (13.38, 42.36, "Monti dell'Aquila"),
    (13.56, 42.17, 'Sirente – Velino'),
    (13.86, 42.20, 'Monti del Morrone'),
    (14.07, 42.09, 'Maiella'),
]

# Editorial exclusions are permanent: the reference outline can still intersect
# these cores, but regenerating the atlas must not restore them.
REMOVED_CELL_IDS = {
    'ALP_E134_N074', 'ALP_E133_N076', 'ALP_E133_N077',
    'ALP_E133_N078', 'ALP_E133_N079',
}
ADDED_CELL_IDS = {'APP_E149_N067'}

# Distinct, readable locality names for the western planning sheets. Existing
# published-sheet names are left untouched.
WEST_CELL_NAMES = {
    'ALP_E130_N076': 'Ubaye occidentale',
    'ALP_E130_N077': 'Queyras sud-occidentale',
    'ALP_E130_N078': 'Queyras nord-occidentale',
    'ALP_E130_N079': 'Vanoise occidentale',
    'ALP_E131_N074': 'Mercantour meridionale',
    'ALP_E131_N075': 'Mercantour settentrionale',
    'ALP_E131_N076': 'Ubaye orientale',
    'ALP_E131_N077': 'Queyras sud-orientale',
    'ALP_E131_N078': 'Queyras nord-orientale',
    'ALP_E131_N079': 'Haute Maurienne',
    'ALP_E131_N080': 'Vanoise orientale',
    'ALP_E131_N081': 'Monte Bianco – Chamonix',
    'ALP_E131_N082': 'Vallese occidentale',
    'ALP_E132_N074': 'Alpi Liguri sud-occidentali',
    'ALP_E132_N075': 'Alpi Marittime',
    'ALP_E132_N076': 'Cuneese occidentale',
    'ALP_E132_N077': 'Monviso',
    'ALP_E132_N078': 'Val di Susa meridionale',
    'ALP_E132_N079': 'Val di Susa settentrionale',
    'ALP_E132_N080': 'Gran Paradiso occidentale',
    'ALP_E132_N081': "Valle d'Aosta occidentale",
    'ALP_E132_N082': 'Vallese centrale',
    'ALP_E132_N083': 'Alpi Bernesi occidentali',
    'ALP_E133_N075': 'Alpi Liguri centrali',
    'ALP_E133_N080': 'Gran Paradiso orientale',
    'ALP_E133_N081': "Valle d'Aosta orientale",
    'ALP_E133_N082': 'Vallese sud-orientale',
    'ALP_E133_N083': 'Vallese nord-orientale',
    'ALP_E134_N075': 'Alpi Liguri orientali',
    'ALP_E134_N076': 'Alpi Liguri settentrionali',
}
CELL_NAMES = {**WEST_CELL_NAMES, 'APP_E149_N067': 'Monti Marsicani – Pescasseroli'}


def polygon(points):
    return QgsGeometry.fromPolygonXY([[QgsPointXY(x, y) for x, y in points + points[:1]]])


def west_geometry():
    step = atlas.STEP
    return polygon([(134 * step + (x - 690) * step / 90,
                     84 * step - (y - 293) * step / 90) for x, y in WEST_PIXELS])


def central_geometry():
    lon_per_px = (14.215 - 13.576) / (1500 - 900)
    lat_per_px = (42.461 - 42.853) / (515 - 83)
    geographic = polygon([(13.576 + (x - 900) * lon_per_px,
                           42.853 + (y - 83) * lat_per_px) for x, y in CENTRAL_PIXELS])
    return geometry_in(geographic, 'EPSG:4326', atlas.CRS)


def candidates(region, prefix, existing):
    bb = region.boundingBox()
    result = []
    for col in range(math.floor(bb.xMinimum() / atlas.STEP), math.ceil(bb.xMaximum() / atlas.STEP)):
        for row in range(math.floor(bb.yMinimum() / atlas.STEP), math.ceil(bb.yMaximum() / atlas.STEP)):
            key = atlas.cell_id(col, row, prefix)
            if key in existing or key in REMOVED_CELL_IDS or key in atlas.EXCLUDED_CELL_IDS:
                continue
            core = atlas.core_geometry(col, row)
            fraction = core.intersection(region).area() / (atlas.STEP ** 2)
            if fraction >= 0.10:
                result.append((key, col, row, fraction))
    return sorted(result)


def nearest_name(col, row, landmarks):
    center = geometry_in(atlas.core_geometry(col, row).centroid(), atlas.CRS, 'EPSG:4326').asPoint()
    lon, lat = center.x(), center.y()
    name = min(landmarks, key=lambda item: ((item[0] - lon) * math.cos(math.radians(lat))) ** 2
               + (item[1] - lat) ** 2)[2]
    return name, lon, lat


def feature_geometry(col, row, geometry_function):
    geometry = geometry_in(geometry_function(col, row).densifyByDistance(1000), atlas.CRS, 'EPSG:4326')
    return json.loads(geometry.asJson())


def run(root, dry_run):
    grid_file = root / '##_aree/_archivio_comune/atlante_griglia_v2.json'
    catalog_file = root / '08_Atlante/catalogo.json'
    catalog = load_json(catalog_file)
    data = load_json(grid_file) if grid_file.exists() else {
        'grid_id': atlas.GRID_ID, 'crs': atlas.CRS, 'origin': [0, 0],
        'cell_size_m': atlas.CELL_SIZE, 'step_m': atlas.STEP,
        'overlap_side_m': atlas.OVERLAP_SIDE,
        'cells': [{k: value for k, value in cell.items()
                   if k not in ('edition', 'zoom', 'status', 'reason', 'bytes', 'packages')}
                  for cell in catalog['cells']],
    }
    if data['grid_id'] != atlas.GRID_ID:
        raise ValueError('Incompatible atlas grid')
    original_ids = {cell['id'] for cell in data['cells']}
    data['cells'] = [cell for cell in data['cells'] if cell['id'] not in REMOVED_CELL_IDS]
    existing = {cell['id'] for cell in data['cells']}
    western = candidates(west_geometry(), 'ALP', existing)
    central = candidates(central_geometry(), 'APP', existing)
    for key in ADDED_CELL_IDS - existing - {row[0] for row in central}:
        _, east, north = key.split('_')
        central.append((key, int(east[1:]), int(north[1:]), 0.0))
    central.sort()
    report = {'western_alps': [r[0] for r in western],
              'central_apennines': [r[0] for r in central],
              'removed': sorted(original_ids & REMOVED_CELL_IDS),
              'existing_count': len(existing),
              'already_added': sorted(cell['id'] for cell in data['cells']
                                      if cell.get('planning_region') in ('western_alps', 'central_apennines'))}
    if dry_run:
        return report

    records = {record['id']: record for record in catalog['cells']
               if record['id'] not in REMOVED_CELL_IDS}
    if set(records) != existing:
        raise ValueError('Grid and catalogue differ; rebuild before extending')
    public_file = root / 'docs/data/atlas.json'
    if public_file.exists():
        for published in load_json(public_file).get('cells', []):
            if published.get('id') in records and published.get('status') == 'published':
                records[published['id']].update({
                    'status': 'published', 'edition': published.get('edition'),
                    'zoom': published.get('zoom'), 'bytes': published.get('bytes'),
                    'packages': published.get('packages', []),
                })
    for cell in data['cells']:
        if cell.get('planning_region') not in ('western_alps', 'central_apennines'):
            continue
        landmarks = WEST_NAMES if cell['id'].startswith('ALP_') else CENTRAL_NAMES
        fallback, lon, lat = nearest_name(cell['col'], cell['row'], landmarks)
        name = CELL_NAMES.get(cell['id'], fallback)
        cell['display_name'] = name
        cell['reference'].update({'name': name, 'lon': lon, 'lat': lat})
        records[cell['id']].update({'display_name': name, 'reference': cell['reference']})
    for region, rows, landmarks in [('western_alps', western, WEST_NAMES),
                                     ('central_apennines', central, CENTRAL_NAMES)]:
        for key, col, row, fraction in rows:
            fallback, lon, lat = nearest_name(col, row, landmarks)
            name = CELL_NAMES.get(key, fallback)
            reference = {'name': name, 'place': 'mountain_region', 'population': 0,
                         'lon': lon, 'lat': lat, 'source': 'manual_region_reference',
                         'sector': 'Western and Maritime Alps' if key.startswith('ALP_')
                                   else 'Central Apennines'}
            cell = {'id': key, 'col': col, 'row': row, 'display_name': name,
                    'name_source': 'manual', 'reference': reference,
                    'planning_region': region,
                    'planning_overlap_percent': round(fraction * 100, 1)}
            data['cells'].append(cell)
            records[key] = {**cell, 'edition': None, 'zoom': [12, 17],
                            'status': 'planned', 'reason': '', 'bytes': 0,
                            'packages': []}
    names = [cell['display_name'].casefold() for cell in data['cells']]
    if len(names) != len(set(names)):
        raise ValueError('Atlas display names must be unique')
    data['cells'].sort(key=lambda cell: cell['id'])
    catalog['cells'] = [records[key] for key in sorted(records)]
    out = root / '08_Atlante'
    grid_file.parent.mkdir(parents=True, exist_ok=True)
    save_json(grid_file, data)
    atlas.write_grid(type('WorkspacePaths', (), {'archive': grid_file.parent, 'root': root})(), data)
    save_json(out / 'catalogo.json', catalog)

    localities, cores = [], []
    for cell in data['cells']:
        key, col, row = cell['id'], cell['col'], cell['row']
        reference = cell['reference']
        localities.append({'type': 'Feature', 'properties': {
            'cell_id': key, 'name': reference['name'], 'area_name': cell['display_name'],
            'place': reference['place'], 'population': reference['population'],
            'sector': reference['sector'], 'source': reference['source']},
            'geometry': {'type': 'Point', 'coordinates': [reference['lon'], reference['lat']]}})
        cores.append({'type': 'Feature', 'properties': {
            'cell_id': key, 'name': cell['display_name'], 'status': records[key]['status'],
            'mountain_percent': cell.get('mountain_percent'),
            'max_elevation_m': cell.get('max_elevation_m')},
            'geometry': feature_geometry(col, row, atlas.core_geometry)})
    save_json(out / 'localita.geojson', {'type': 'FeatureCollection', 'features': localities})
    save_json(out / 'nuclei.geojson', {'type': 'FeatureCollection', 'features': cores})
    atlas.write_overview(type('WorkspacePaths', (), {'archive': grid_file.parent, 'root': root})(), out, data)
    report['total_count'] = len(data['cells'])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    app = QgsApplication([], False)
    app.setPrefixPath(os.environ.get('QGIS_PREFIX_PATH', '/Applications/QGIS.app/Contents/Resources/qgis'), True)
    app.initQgis()
    try:
        print(json.dumps(run(args.root.resolve(), args.dry_run), ensure_ascii=False, indent=2))
    finally:
        app.exitQgis()


if __name__ == '__main__':
    main()
