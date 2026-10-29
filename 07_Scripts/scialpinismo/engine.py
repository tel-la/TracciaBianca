"""Elaborazione su disco, catalogo e riuso incrementale dei dati."""
import datetime as dt
from contextlib import contextmanager
import hashlib
import json
import math
import os
import re
try:
    import resource
except ImportError:  # QGIS su Windows: dato RAM non disponibile tramite stdlib.
    resource = None
import shutil
import sqlite3
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

import numpy as np
from scipy.ndimage import binary_dilation, distance_transform_edt, gaussian_filter
from osgeo import gdal, ogr, osr
from qgis.core import (
    QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsFeature, QgsField,
    QgsGeometry, QgsProject, QgsRectangle, QgsVectorLayer, QgsVectorFileWriter,
    QgsExpression, QgsExpressionContext, QgsFeatureRequest,
)
from qgis.PyQt.QtCore import QVariant

gdal.UseExceptions()
ogr.UseExceptions()
gdal.SetCacheMax(256 * 1024 * 1024)
gdal.SetConfigOption('GDAL_NUM_THREADS', '2')
gdal.SetConfigOption('OSM_MAX_TMPFILE_SIZE', '128')
VERSION = '1.4.1'
OSM_EXTRACTOR_VERSION = 'osm-interleaved-v2'
COG_OPTIONS = ['COMPRESS=DEFLATE', 'PREDICTOR=YES', 'BLOCKSIZE=512', 'NUM_THREADS=2', 'BIGTIFF=IF_SAFER', 'RESAMPLING=AVERAGE']
DTM_COMPARISON_MIN_M = 20.0
DTM_CORRECTION_DEPTH_M = 500.0
DTM_BLEND_MIN_M = 20.0
DTM_BLEND_MAX_M = 60.0
DTM_MIN_COREG_SAMPLES = 200
DTM_MAX_VERTICAL_SHIFT_M = 15.0
DTM_MAX_RESIDUAL_M = 8.0
HILLSHADE_ALTITUDE_DEG = 45.0
HILLSHADE_PRIMARY_AZIMUTH_DEG = 315.0
HILLSHADE_PRIMARY_WEIGHT = 0.70
HILLSHADE_SECONDARY_AZIMUTHS_DEG = (225.0, 270.0, 360.0)
ATOM_NS = '{http://www.w3.org/2005/Atom}'
BEV_DTM_TITLE = re.compile(r'ALS\s+DTM\s+CRS3035RES\d+mN(\d+)E(\d+).*Stichtag\s+\d{2}\.\d{2}\.(\d{4})')
OSM_PBF_NAME = re.compile(r'^(?P<name>.+)-(?P<date>\d{6})\.osm\.pbf$')


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    tmp.replace(path)


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def fingerprint(path):
    p = Path(path)
    s = p.stat()
    return {'path': str(p.resolve()), 'size': s.st_size, 'mtime_ns': s.st_mtime_ns}


def osm_records(data):
    """Restituisce il catalogo OSM corrente, accettando anche il vecchio campo singolo."""
    records = data.get('osm_sources')
    if records is not None:
        return records
    legacy = data.get('osm')
    return [legacy] if legacy and legacy.get('path') else []


def osm_file_metadata(path, archive):
    """Costruisce metadati e ingombro WGS84 di un PBF locale Geofabrik."""
    path = Path(path)
    match = OSM_PBF_NAME.match(path.name)
    identifier = path.name.removesuffix('.osm.pbf')
    label = match.group('name') if match else identifier
    date = ''
    if match:
        parsed = dt.datetime.strptime(match.group('date'), '%y%m%d').date()
        date = parsed.isoformat()
    dataset = ogr.Open(str(path))
    if dataset is None:
        raise ValueError(f'PBF OSM non leggibile: {path}')
    extents = []
    for index in range(dataset.GetLayerCount()):
        layer = dataset.GetLayerByIndex(index)
        extent = layer.GetExtent(force=0)
        if extent:
            extents.append(extent)
    dataset = None
    coverage = None
    if extents:
        coverage = [min(e[0] for e in extents), min(e[2] for e in extents),
                    max(e[1] for e in extents), max(e[3] for e in extents)]
    return {
        'id': identifier,
        'title': label.replace('-', ' ').title(),
        'path': os.path.relpath(path, archive),
        'date': date or 'non ricavabile dal nome file',
        'url': 'https://download.geofabrik.de/index.html',
        'license': 'Data: ODbL 1.0; map tiles: CC BY-SA 2.0',
        'attribution': '© OpenStreetMap contributors; estratto Geofabrik',
        'coverage_bbox': coverage,
        'fingerprint': fingerprint(path),
    }


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def smoothstep(value):
    """Interpolazione C1 limitata all'intervallo 0..1."""
    value = np.clip(value, 0.0, 1.0)
    return value * value * (3.0 - 2.0 * value)


def normalized_gaussian(values, valid, sigma):
    """Filtro gaussiano che non propaga NoData oltre i pixel validi."""
    valid_float = valid.astype(np.float32)
    numerator = gaussian_filter(np.where(valid, values, 0.0).astype(np.float32), sigma, mode='nearest')
    denominator = gaussian_filter(valid_float, sigma, mode='constant', cval=0.0)
    result = np.full(values.shape, np.nan, dtype=np.float32)
    supported = denominator > 0.05
    result[supported] = numerator[supported] / denominator[supported]
    return result, supported


def robust_linear_model(matrix, values, minimum=DTM_MIN_COREG_SAMPLES):
    """Minimi quadrati iterativi con filtro NMAD; restituisce coefficienti e diagnostica."""
    finite = np.isfinite(values) & np.all(np.isfinite(matrix), axis=1)
    matrix = matrix[finite]
    values = values[finite]
    if values.size < minimum:
        return None
    keep = np.ones(values.size, dtype=bool)
    coefficients = None
    for _ in range(6):
        if keep.sum() < minimum:
            return None
        coefficients, _, _, _ = np.linalg.lstsq(matrix[keep], values[keep], rcond=None)
        residual = values - matrix @ coefficients
        centre = float(np.median(residual[keep]))
        nmad = 1.4826 * float(np.median(np.abs(residual[keep] - centre)))
        limit = max(0.25, 3.0 * nmad)
        updated = np.abs(residual - centre) <= limit
        if np.array_equal(updated, keep):
            break
        keep = updated
    residual = values - matrix @ coefficients
    centre = float(np.median(residual[keep]))
    nmad = 1.4826 * float(np.median(np.abs(residual[keep] - centre)))
    return coefficients, keep, {'samples': int(keep.sum()), 'nmad_m': nmad,
                                 'residual_median_m': centre}


def estimate_dem_coregistration(base, candidate, base_valid, candidate_valid,
                                pixel_size, worst_native_resolution):
    """Stima dx, dy e dz su superfici filtrate, senza confondere quota e spostamento."""
    comparison_m = max(DTM_COMPARISON_MIN_M, 2.0 * float(worst_native_resolution))
    sigma = max(0.8, comparison_m / (2.355 * float(pixel_size)))
    base_low, base_support = normalized_gaussian(base, base_valid, sigma)
    candidate_low, candidate_support = normalized_gaussian(candidate, candidate_valid, sigma)
    overlap = base_support & candidate_support & base_valid & candidate_valid
    if not np.any(overlap):
        return {'accepted': False, 'reason': 'no_overlap', 'comparison_m': comparison_m,
                'samples': 0, 'dx_m': 0.0, 'dy_m': 0.0, 'dz_m': 0.0}
    # Le righe raster crescono verso Sud: il passo Y è negativo nel sistema cartografico.
    gy, gx = np.gradient(candidate_low.astype(np.float64), -float(pixel_size), float(pixel_size))
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    usable = overlap & np.isfinite(slope) & (slope >= 2.0) & (slope <= 60.0)
    stride = max(1, int(round(comparison_m / float(pixel_size))))
    sampled = np.zeros(usable.shape, dtype=bool)
    sampled[::stride, ::stride] = True
    usable &= sampled
    rows, cols = np.nonzero(usable)
    if rows.size < DTM_MIN_COREG_SAMPLES:
        return {'accepted': False, 'reason': 'insufficient_samples',
                'comparison_m': comparison_m, 'samples': int(rows.size),
                'dx_m': 0.0, 'dy_m': 0.0, 'dz_m': 0.0}
    delta = (base_low[rows, cols] - candidate_low[rows, cols]).astype(np.float64)
    matrix = np.column_stack((gx[rows, cols], gy[rows, cols], np.ones(rows.size)))
    fitted = robust_linear_model(matrix, delta)
    if fitted is None:
        return {'accepted': False, 'reason': 'unstable_fit', 'comparison_m': comparison_m,
                'samples': int(rows.size), 'dx_m': 0.0, 'dy_m': 0.0, 'dz_m': 0.0}
    coefficients, _, diagnostics = fitted
    dx, dy, dz = map(float, coefficients)
    maximum_horizontal = max(5.0, 2.0 * float(worst_native_resolution))
    accepted = (math.hypot(dx, dy) <= maximum_horizontal and
                abs(dz) <= DTM_MAX_VERTICAL_SHIFT_M and
                diagnostics['nmad_m'] <= DTM_MAX_RESIDUAL_M)
    return {**diagnostics, 'accepted': accepted,
            'reason': 'accepted' if accepted else 'implausible_shift',
            'comparison_m': comparison_m, 'dx_m': dx, 'dy_m': dy, 'dz_m': dz,
            'max_horizontal_m': maximum_horizontal}


def seam_fields(base, candidate, base_valid, candidate_valid, pixel_size,
                worst_native_resolution, vertical_shift=0.0):
    """Crea correzione lenta e pesi della seamline su una griglia di confronto."""
    valid_overlap = base_valid & candidate_valid
    comparison_m = max(DTM_COMPARISON_MIN_M, 2.0 * float(worst_native_resolution))
    sigma = max(1.0, comparison_m / float(pixel_size))
    base_low, base_support = normalized_gaussian(base, base_valid, sigma)
    candidate_shifted = candidate.astype(np.float32) + float(vertical_shift)
    if np.all(candidate_valid):
        ones = np.ones(candidate.shape, dtype=np.float32)
        return np.zeros(candidate.shape, dtype=np.float32), ones, ones, {
            'comparison_m': comparison_m, 'correction_depth_m': DTM_CORRECTION_DEPTH_M,
            'blend_m': 0.0, 'overlap_cells': int(base_valid.sum()),
            'incompatible_cells': 0, 'residual_p95_m': None,
            'action': 'full_coverage',
        }
    candidate_low, candidate_support = normalized_gaussian(candidate_shifted, candidate_valid, sigma)
    supported = valid_overlap & base_support & candidate_support
    residual = np.where(supported, base_low - candidate_low, np.nan).astype(np.float32)
    residual_smooth, residual_support = normalized_gaussian(
        np.where(np.isfinite(residual), residual, 0.0), np.isfinite(residual),
        max(1.0, 100.0 / float(pixel_size)))
    edge_distance = distance_transform_edt(candidate_valid) * float(pixel_size)
    edge_influence = 1.0 - smoothstep(edge_distance / DTM_CORRECTION_DEPTH_M)
    correction = np.where(residual_support, residual_smooth, 0.0) * edge_influence
    correction = np.clip(correction, -DTM_MAX_RESIDUAL_M, DTM_MAX_RESIDUAL_M).astype(np.float32)
    corrected_low = candidate_low + correction
    corrected_residual = np.abs(base_low - corrected_low)
    incompatible = supported & (corrected_residual > DTM_MAX_RESIDUAL_M)
    if np.any(incompatible):
        incompatible = binary_dilation(incompatible, iterations=1)
    trust = candidate_valid & ~incompatible
    seam_distance = distance_transform_edt(trust) * float(pixel_size)
    blend_m = min(DTM_BLEND_MAX_M,
                  max(DTM_BLEND_MIN_M, 4.0 * float(worst_native_resolution)))
    low_weight = smoothstep(seam_distance / blend_m).astype(np.float32)
    low_weight[~candidate_valid] = 0.0
    low_weight[candidate_valid & ~base_valid] = 1.0
    # Il micro-rilievo cambia sorgente in una fascia molto più stretta del raccordo lento.
    high_weight = smoothstep((low_weight - 0.42) / 0.16).astype(np.float32)
    return correction, low_weight, high_weight, {
        'comparison_m': comparison_m, 'correction_depth_m': DTM_CORRECTION_DEPTH_M,
        'blend_m': blend_m, 'overlap_cells': int(valid_overlap.sum()),
        'incompatible_cells': int(incompatible.sum()),
        'residual_p95_m': (round(float(np.nanpercentile(corrected_residual[supported], 95)), 4)
                           if np.any(supported) else None),
        'action': 'coregistered_short_seam',
    }


def multidirectional_hillshade(gx, gy):
    """Ombreggiatura con sole dominante 45°/315° e riempimento secondario."""
    altitude = math.radians(HILLSHADE_ALTITUDE_DEG)
    normalization = np.sqrt(1.0 + gx*gx + gy*gy)
    def illumination(azimuth_degrees):
        azimuth = math.radians(azimuth_degrees)
        # Normale del terreno (-dz/dx, -dz/dy, 1) e azimut da Nord in senso orario.
        value = (math.sin(altitude) -
                 gx*math.cos(altitude)*math.sin(azimuth) -
                 gy*math.cos(altitude)*math.cos(azimuth)) / normalization
        return np.clip(value, 0.0, 1.0)
    principal = illumination(HILLSHADE_PRIMARY_AZIMUTH_DEG)
    secondary = np.mean(
        [illumination(value) for value in HILLSHADE_SECONDARY_AZIMUTHS_DEG], axis=0)
    combined = (HILLSHADE_PRIMARY_WEIGHT*principal +
                (1.0-HILLSHADE_PRIMARY_WEIGHT)*secondary)
    return np.rint(np.clip(combined, 0.0, 1.0)*255.0).astype(np.uint8)


def parse_bev_atom_index(content):
    """Restituisce il dataset feed più recente per ogni tassello ALS-DTM BEV."""
    root = ET.fromstring(content)
    best = {}
    for entry in root.findall(f'{ATOM_NS}entry'):
        match = BEV_DTM_TITLE.search(entry.findtext(f'{ATOM_NS}title') or '')
        if not match:
            continue
        feed = next((link.get('href') for link in entry.findall(f'{ATOM_NS}link')
                     if 'atom+xml' in (link.get('type') or '')), None)
        if not feed:
            continue
        key = f'{int(match.group(1))}_{int(match.group(2))}'
        year = int(match.group(3))
        if key not in best or year > best[key][0]:
            best[key] = (year, feed)
    return {key: feed for key, (_, feed) in best.items()}


def parse_bev_atom_tif(content):
    root = ET.fromstring(content)
    for link in root.iter(f'{ATOM_NS}link'):
        href = link.get('href') or ''
        if 'image/tiff' in (link.get('type') or '') or href.lower().endswith('.tif'):
            return href
    return None


def parse_swisstopo_stac_page(content, resolution=2.0):
    """Estrae i COG swissALTI3D alla risoluzione richiesta da una pagina STAC."""
    data = json.loads(content)
    records = []
    for feature in data.get('features', []):
        asset = next((candidate for candidate in feature.get('assets', {}).values()
                      if candidate.get('href', '').lower().endswith(('.tif', '.tiff'))
                      and 'cloud-optimized' in candidate.get('type', '')
                      and float(candidate.get('gsd', -1)) == float(resolution)
                      and int(candidate.get('proj:epsg', 0)) == 2056), None)
        if not asset:
            continue
        match = re.search(r'_(\d{4})-(\d{4})$', feature.get('id', ''))
        records.append({
            'key': '-'.join(match.groups()) if match else feature.get('id', asset['href']),
            'datetime': feature.get('properties', {}).get('datetime', ''),
            'url': asset['href'],
        })
    next_url = next((link.get('href') for link in data.get('links', [])
                     if link.get('rel') == 'next'), None)
    return records, next_url


def dtm_nodata_policy(max_missing_percent):
    if (not isinstance(max_missing_percent, (int, float)) or isinstance(max_missing_percent, bool)
            or not 0 <= max_missing_percent <= 10):
        raise ValueError('La percentuale massima di NoData deve essere compresa tra 0 e 10')
    value = float(max_missing_percent)
    if value == 0:
        return {'mode': 'strict'}
    return {'mode': 'allow_partial', 'max_missing_percent': value}


def geometry_in(geometry, src, dst):
    g = QgsGeometry(geometry)
    g.transform(QgsCoordinateTransform(QgsCoordinateReferenceSystem(src), QgsCoordinateReferenceSystem(dst), QgsProject.instance()))
    return g


def memory_layer(name, geom='Polygon', crs='EPSG:4326', fields=()):
    layer = QgsVectorLayer(f'{geom}?crs={crs}', name, 'memory')
    layer.dataProvider().addAttributes([QgsField(n, t) for n, t in fields])
    layer.updateFields()
    return layer


def write_layer(layer, path, name):
    opts = QgsVectorFileWriter.SaveVectorOptions()
    opts.driverName = 'GPKG'
    opts.layerName = name
    opts.fileEncoding = 'UTF-8'
    opts.actionOnExistingFile = (QgsVectorFileWriter.CreateOrOverwriteLayer if Path(path).exists() else QgsVectorFileWriter.CreateOrOverwriteFile)
    opts.layerOptions = ['SPATIAL_INDEX=YES']
    result = QgsVectorFileWriter.writeAsVectorFormatV3(layer, str(path), QgsProject.instance().transformContext(), opts)
    if result[0] != QgsVectorFileWriter.NoError:
        raise RuntimeError(f'Scrittura {name}: {result}')


def add_feature(layer, geometry, values):
    f = QgsFeature(layer.fields())
    f.setGeometry(geometry)
    f.setAttributes(values)
    if not layer.dataProvider().addFeatures([f])[0]:
        raise RuntimeError(f'Geometria non inserita in {layer.name()} (tipo {geometry.wkbType()}): {layer.dataProvider().lastError()}')


def has_layer(path, name):
    """Non aprire provider OGR prima di modificare lo schema dello stesso GeoPackage."""
    if not Path(path).exists():
        return False
    with sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro', uri=True) as con:
        return con.execute('select 1 from sqlite_master where type=\'table\' and name=?', (name,)).fetchone() is not None


def cog_copy(src, dst):
    temp = Path(str(dst) + '.partial.tif')
    gdal.Translate(str(temp), str(src), format='COG', creationOptions=COG_OPTIONS)
    temp.replace(dst)
    # Una statistica GDAL precedente non deve descrivere il nuovo raster.
    Path(str(dst) + '.aux.xml').unlink(missing_ok=True)


def osm_config_path(archive):
    """Conserva quote e riconosce come poligoni tutte le varianti edilizie usate."""
    path = Path(archive)/'osm/osmconf_scialpinismo.ini'
    if path.exists():
        lines = path.read_text().splitlines()
    else:
        default = gdal.FindFile('gdal','osmconf.ini')
        if not default:
            raise RuntimeError('osmconf.ini GDAL non trovato: verificare GDAL_DATA')
        lines = Path(default).read_text().splitlines()
    updated = []
    polygon_keys = ('ruins', 'waterway=riverbank', 'building:part', 'abandoned:building', 'disused:building')
    for line in lines:
        if line.startswith('ignore='):
            line='ignore='+','.join(t for t in line.split('=',1)[1].split(',') if t!='ele')
        elif line.startswith('attributes=') and 'ele' not in line.split('=',1)[1].split(','):
            line+=',ele'
        elif line.startswith('closed_ways_are_polygons='):
            present = line.split('=', 1)[1].split(',')
            line += ''.join(','+key for key in polygon_keys if key not in present)
        updated.append(line)
    content = '\n'.join(updated)+'\n'
    if not path.exists() or path.read_text() != content:
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(content)
    return path


class Workflow:
    def __init__(self, root, feedback=None, log=None):
        self.root = Path(root).resolve()
        temp = self.root/'.qgis_runtime/tmp'
        temp.mkdir(parents=True, exist_ok=True)
        os.environ['SQLITE_TMPDIR'] = str(temp)
        os.environ['CPL_TMPDIR'] = str(temp)
        gdal.SetConfigOption('CPL_TMPDIR', str(temp))
        self.areas = self.root / '##_aree'
        self.archive = self.areas / '_archivio_comune'
        self.feedback = feedback
        self._arcgis_unavailable_until = {}
        self._arcgis_fallback_reported = set()
        display = log or (lambda message: feedback.pushInfo(message) if feedback else None)
        log_dir = self.archive/'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        self.log_path = log_dir/f'{stamp}_workflow.log'
        sequence = 2
        while self.log_path.exists():
            self.log_path = log_dir/f'{stamp}_workflow_{sequence:02d}.log'
            sequence += 1
        def logger(message):
            with self.log_path.open('a', encoding='utf-8') as stream:
                stream.write(f'{dt.datetime.now(dt.timezone.utc).isoformat()} {message}\n')
            display(message)
        self.log = logger

    def cancel(self):
        if self.feedback and self.feedback.isCanceled():
            raise RuntimeError('Operazione annullata. Risultati completati conservati.')

    def gdal_callback(self, fraction, message, data):
        if self.feedback:
            from qgis.PyQt.QtCore import QCoreApplication
            QCoreApplication.processEvents()
            return not self.feedback.isCanceled()
        return True

    @contextmanager
    def locked(self):
        """Un lavoro per archivio: evita scritture mentre un export legge i dati."""
        lock = self.archive/'workflow.lock'
        for attempt in range(2):
            try:
                fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'w') as stream:
                    json.dump({'pid': os.getpid()}, stream)
                break
            except FileExistsError:
                try:
                    pid = load_json(lock)['pid']
                    os.kill(pid, 0)
                except ProcessLookupError:
                    lock.unlink()
                    continue
                except (ValueError, KeyError, json.JSONDecodeError):
                    raise RuntimeError('Lock non leggibile: verificare che non ci siano lavori attivi prima di rimuovere workflow.lock')
                raise RuntimeError('Un altro lavoro Scialpinismo è in corso. Attendere il completamento.')
        else:
            raise RuntimeError('Impossibile acquisire il lock del workflow')
        try:
            yield
        finally:
            lock.unlink(missing_ok=True)

    def progress(self, pct, message):
        self.cancel()
        self.log(message)
        if self.feedback:
            self.feedback.setProgress(pct)

    def sources(self):
        return load_json(self.archive / 'fonti.json')['sources']

    def select_osm_sources(self, data, geometry, config):
        """Seleziona tutti i PBF il cui ingombro interseca area e margine."""
        wanted = geometry_in(geometry.buffer(config['buffer_m'], 12),
                             config['processing_crs'], 'EPSG:4326').boundingBox()
        selected = []
        for record in osm_records(data):
            path = (self.archive/record['path']).resolve()
            if not path.exists():
                continue
            bounds = record.get('coverage_bbox')
            if bounds is None or QgsRectangle(*bounds).intersects(wanted):
                selected.append((record, path))
        return selected

    def source_path(self, record):
        if record.get('provider'):
            raise ValueError(f"{record['id']}: la sorgente remota non ha un percorso locale")
        return (self.archive / record['path']).resolve()

    def source_available(self, record):
        provider = record.get('provider')
        if provider == 'arcgis_imageserver':
            return bool(record.get('url'))
        if provider == 'bev_atom_cog':
            return bool(record.get('url') and record.get('atom_url'))
        if provider == 'swisstopo_stac_cog':
            return bool(record.get('url') and record.get('stac_url'))
        if provider:
            return False
        return self.source_path(record).exists()

    def source_fingerprint(self, record):
        """Identifica sia file locali sia revisioni dichiarate di servizi remoti."""
        if record.get('provider'):
            current = {'provider': record['provider'], 'url': record['url'],
                       'revision': record.get('revision', 'non specificata')}
            endpoint = {'bev_atom_cog': 'atom_url',
                        'swisstopo_stac_cog': 'stac_url'}.get(record['provider'])
            if endpoint:
                current[endpoint] = record[endpoint]
            return current
        return fingerprint(self.source_path(record))

    def initialize(self):
        with self.locked():
            return self._initialize()

    def _initialize(self):
        """Inizializza il catalogo usando soltanto sorgenti locali alla cartella."""
        for folder in ('dtm/originali', 'dtm/tasselli', 'mosaici', 'osm', 'logs'):
            (self.archive / folder).mkdir(parents=True, exist_ok=True)
        manifest = self.archive / 'fonti.json'
        data = load_json(manifest) if manifest.exists() else {'schema_version': 1, 'sources': [], 'osm': {}}
        known = {s['id'] for s in data['sources']}
        candidates = [
            ('hrdtm5m', self.archive / 'dtm/originali/hrdtm5m/HRDTM5m', 'EPSG:6875', 5, 10, True,
             'HR-DTM-5m nazionale, v1.2', 'https://zenodo.org/records/18921767',
             'Griglia 5 m; sorgenti eterogenee, anche TINITALY 10 m. Qualità locale non discriminata.'),
            ('altoadige_ritaglio_25m', self.archive / 'dtm/originali/AltoAdige/altoadige_ritaglio_2_5m.tif', 'EPSG:25832', 2.5, 2.5, True,
             'Ritaglio locale a circa 2,5 m', 'https://nature-territory.province.bz.it/it/modelli-digitali-di-elevazione',
             'Valori compatibili con quote; provenienza del ritaglio da confermare. Escluso dalla selezione automatica.'),
        ]
        # CRS conservati dalle proprietà del progetto originale, non dedotti dai nomi.
        external = [('veneto_029050', 'Veneto_HQ/029050.txt', 'EPSG:3003'),
                    ('veneto_12_2k_0137', 'Veneto_HQ/12_2K_0137.asc', 'EPSG:6876'),
                    ('veneto_12_2k_0165', 'Veneto_HQ/12_2K_0165.asc', 'EPSG:6876')]
        for sid, name, crs in external:
            local = self.archive / 'dtm/originali' / name
            if local.exists():
                candidates.append((sid, local, crs, 5, 5, True, Path(name).name,
                                   'https://idt2.regione.veneto.it/',
                                   'Controllo tecnico 2026-10-19: raster altimetrico, griglia 5 m e NoData -9999; CRS dichiarato dal catalogo perché assente nel file ASCII.'))
        for sid, path, crs, grid, effective, verified, title, url, notes in candidates:
            if sid in known or not path.exists():
                continue
            ds = gdal.Open(str(path))
            if ds.RasterCount != 1 or ds.GetRasterBand(1).DataType == gdal.GDT_Byte:
                raise ValueError(f'{path}: non è una sorgente altimetrica accettabile')
            gt = ds.GetGeoTransform()
            # I dati locali sono north-up; quattro bordi densificati per trasformazioni affidabili.
            ring = []
            for xa, ya, xb, yb in [(0, 0, ds.RasterXSize, 0), (ds.RasterXSize, 0, ds.RasterXSize, ds.RasterYSize),
                                   (ds.RasterXSize, ds.RasterYSize, 0, ds.RasterYSize), (0, ds.RasterYSize, 0, 0)]:
                for t in np.linspace(0, 1, 33):
                    x, y = xa + t * (xb - xa), ya + t * (yb - ya)
                    ring.append(f'{gt[0]+x*gt[1]+y*gt[2]} {gt[3]+x*gt[4]+y*gt[5]}')
            ring.append(ring[0])
            geom = geometry_in(QgsGeometry.fromWkt('POLYGON ((' + ','.join(ring) + '))'), crs, 'EPSG:4326')
            data['sources'].append({'id': sid, 'title': title, 'path': os.path.relpath(path, self.archive),
                                    'crs': crs, 'grid_m': grid, 'native_resolution_m': effective,
                                    'verified': verified, 'vertical_units': 'm', 'vertical_datum': 'da documentare per sorgente',
                                    'url': url, 'license': 'da verificare nei metadati della fonte', 'notes': notes,
                                    'coverage_wkt': geom.asWkt(), 'fingerprint': fingerprint(path)})
            ds = None
        # Migrazione trasparente dal precedente registro OSM singolo e scoperta di
        # tutti i pacchetti territoriali presenti nell'archivio comune.
        registered = {record['path']: record for record in osm_records(data)}
        osm_sources = []
        for pbf in sorted((self.archive/'osm').glob('*.osm.pbf')):
            relative = os.path.relpath(pbf, self.archive)
            previous = registered.get(relative)
            current_fingerprint = fingerprint(pbf)
            if (previous and previous.get('coverage_bbox') and
                    previous.get('fingerprint') == current_fingerprint):
                record = previous
            else:
                record = osm_file_metadata(pbf, self.archive)
            osm_sources.append(record)
        data['osm_sources'] = osm_sources
        # Alias conservato per lettori meno recenti; il workflow usa osm_sources.
        preferred = next((record for record in osm_sources if record['path'].startswith('osm/nord-est-')), None)
        data['osm'] = preferred or (osm_sources[0] if osm_sources else {})
        save_json(manifest, data)
        self.refresh_catalog(data)
        from .cartography import create_template, create_styles
        create_styles(self.root)
        create_template(self.root)
        return {'catalog': str(self.archive / 'catalogo.gpkg'), 'sources': len(data['sources']),
                'osm': data['osm'], 'osm_sources': data['osm_sources']}

    def refresh_catalog(self, data=None):
        data = data or load_json(self.archive / 'fonti.json')
        layer = memory_layer('Copertura DTM', fields=[('source_id', QVariant.String), ('titolo', QVariant.String),
                            ('grid_m', QVariant.Double), ('native_m', QVariant.Double), ('verificata', QVariant.Int), ('note', QVariant.String)])
        for s in data['sources']:
            add_feature(layer, QgsGeometry.fromWkt(s['coverage_wkt']), [s['id'], s['title'], s['grid_m'], s['native_resolution_m'], int(s['verified']), s['notes']])
        write_layer(layer, self.archive / 'catalogo.gpkg', 'copertura_dtm')
        if not has_layer(self.archive/'catalogo.gpkg', 'aree'):
            write_layer(memory_layer('Aree', fields=[('area_id', QVariant.String), ('config', QVariant.String)]), self.archive / 'catalogo.gpkg', 'aree')

    def register_area(self, config_path, config):
        layer = QgsVectorLayer(str(self.archive / 'catalogo.gpkg') + '|layername=aree', 'aree', 'ogr')
        if not layer.startEditing():
            raise RuntimeError('Catalogo aree non scrivibile')
        for f in layer.getFeatures():
            if f['area_id'] == config['id']:
                layer.deleteFeature(f.id())
        f = QgsFeature(layer.fields())
        f.setGeometry(geometry_in(QgsGeometry.fromWkt(config['perimeter_wkt']), config['perimeter_crs'], 'EPSG:4326'))
        # I GeoPackage espongono anche il campo FID: assegnare per nome, non per posizione.
        f.setAttribute('area_id', config['id'])
        f.setAttribute('config', os.path.relpath(config_path, self.archive))
        if not layer.addFeature(f):
            layer.rollBack()
            raise RuntimeError('Inserimento area nel catalogo fallito')
        if not layer.commitChanges():
            raise RuntimeError(str(layer.commitErrors()))

    def prepare_bbox(self, name, bbox, sources=(), crs='EPSG:32633', maxzoom=16, max_missing_percent=0):
        west, south, east, north = bbox
        if not (-180 <= west < east <= 180 and -85 < south < north < 85):
            raise ValueError('BBOX richiesta: ovest sud est nord, in longitudine/latitudine')
        geometry = QgsGeometry.fromRect(QgsRectangle(west, south, east, north))
        return self.prepare(name, geometry, 'EPSG:4326', sources, crs, maxzoom,
                            max_missing_percent=max_missing_percent)

    def prepare(self, name, geometry, perimeter_crs, sources=(), crs='EPSG:32633', maxzoom=16, atlas=None,
                max_missing_percent=0):
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}', name):
            raise ValueError('Nome area: lettere, numeri, trattino o underscore, massimo 80 caratteri')
        area = self.areas / name
        config_path = area / 'area.json'
        if config_path.exists():
            raise ValueError('Area già configurata: usare Aggiorna area per preservarne le scelte')
        if geometry.isEmpty() or not geometry.isGeosValid() or geometry.area() <= 0:
            raise ValueError('Perimetro vuoto o non valido')
        config = {'schema_version': 1, 'id': name, 'perimeter_wkt': geometry.asWkt(), 'perimeter_crs': perimeter_crs,
                  'processing_crs': crs, 'source_ids': list(sources), 'buffer_m': 100, 'contour_interval_m': 10,
                  'dtm_nodata_policy': dtm_nodata_policy(max_missing_percent),
                  'project': f'progetto/{name}.qgz', 'osm_required': True,
                  'export': {'minzoom': 12, 'maxzoom': maxzoom, 'mode': 'single',
                             'jpeg_quality': 90, 'dpi': 96, 'metatile': 4,
                             'clip_to_perimeter': True, 'tile_format': 'png'}}
        if atlas:
            config['atlas'] = atlas
            config['export'].update(mode='single', warning_bytes=2000000000)
        self.validate_config(config)
        self.select_sources(config)  # Controllo copertura prima di creare la zona.
        area.mkdir(parents=True, exist_ok=True)
        template = self.areas / '00_template-area'
        for source in template.rglob('*'):
            destination = area/source.relative_to(template)
            if source.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            elif source.name not in ('area.json', '.DS_Store') and source.suffix != '.qgz' and not destination.exists():
                shutil.copy2(source, destination)
        save_json(config_path, config)
        return self.update(config_path)

    def validate_config(self, c):
        if c.get('schema_version') != 1:
            raise ValueError('Versione area.json non supportata')
        crs = QgsCoordinateReferenceSystem(c['processing_crs'])
        from qgis.core import Qgis
        if not crs.isValid() or crs.isGeographic() or crs.mapUnits() != Qgis.DistanceUnit.Meters:
            raise ValueError('Il CRS di elaborazione deve essere proiettato e metrico')
        if not 0 < c['buffer_m'] <= 1000 or c['contour_interval_m'] <= 0:
            raise ValueError('Margine o intervallo curve non valido')
        nodata_policy = c.get('dtm_nodata_policy', {'mode': 'strict'})
        if not isinstance(nodata_policy, dict) or nodata_policy.get('mode', 'strict') not in ('strict', 'allow_partial'):
            raise ValueError('Politica NoData DTM: usare strict oppure allow_partial')
        if nodata_policy.get('mode', 'strict') == 'allow_partial':
            threshold = nodata_policy.get('max_missing_percent')
            if not isinstance(threshold, (int, float)) or isinstance(threshold, bool) or not 0 < threshold <= 10:
                raise ValueError('max_missing_percent deve essere maggiore di 0 e non superiore al 10%')
        e = c['export']
        if e.get('tile_format', 'png' if e.get('clip_to_perimeter', True) else 'jpg') not in ('png', 'jpg'):
            raise ValueError('Formato tessere consentito: png oppure jpg')
        if e.get('clip_to_perimeter', True) and e.get('tile_format', 'png') != 'png':
            raise ValueError('Il ritaglio trasparente richiede tessere PNG')
        project = Path(c['project'])
        if project.is_absolute() or '..' in project.parts or project.suffix != '.qgz':
            raise ValueError('Percorso progetto richiesto: relativo all’area, con estensione .qgz')
        if not 12 <= e['minzoom'] <= e['maxzoom'] <= 18 or not 1 <= e['jpeg_quality'] <= 100:
            raise ValueError('Zoom consentiti 12–18, qualità JPEG 1–100')
        mode = e.get('mode', 'single')
        if mode not in ('single', 'split'):
            raise ValueError('Modalità export: single oppure split')
        if e.get('warning_bytes', 2000000000) < 100000:
            raise ValueError('Soglia avviso troppo piccola')
        if 'atlas' in c:
            from .atlas import validate_atlas_config
            validate_atlas_config(c)
        if mode == 'split' and ('max_bytes' not in e or e['max_bytes'] < 100000):
            raise ValueError('Per suddividere, specificare un limite peso di almeno 0,1 MB')
        if e['dpi'] != 96:
            raise ValueError('Sono supportati solo i 96 DPI del profilo verificato')
        g = QgsGeometry.fromWkt(c['perimeter_wkt'])
        if g.isEmpty() or not g.isGeosValid():
            raise ValueError('Perimetro non valido')

    def select_sources(self, c):
        target = geometry_in(QgsGeometry.fromWkt(c['perimeter_wkt']), c['perimeter_crs'], c['processing_crs'])
        requested = c.get('source_ids', [])
        sources = self.sources()
        by_id = {s['id']: s for s in sources}
        if set(requested) - set(by_id):
            raise ValueError(f'Fonti sconosciute: {set(requested)-set(by_id)}')
        candidates = [by_id[i] for i in requested] if requested else [s for s in sources if s['verified']]
        candidates.sort(key=lambda s: s.get('native_resolution_m') or 999)
        remaining = target.buffer(c['buffer_m'], 12)
        selected = []
        for s in candidates:
            self.cancel()
            if s['grid_m'] <= 0 or s.get('vertical_units', 'm') != 'm':
                raise ValueError('Griglia e unità verticali non supportate per '+s['id'])
            if not self.source_available(s):
                continue
            coverage = self.source_coverage(s, c['processing_crs'], search_remote_edges=True)
            if coverage.isEmpty() or not coverage.isGeosValid():
                raise ValueError('Copertura non valida per '+s['id'])
            if coverage.intersects(remaining):
                selected.append(s)
                remaining = remaining.difference(coverage)
            elif coverage.intersects(target.buffer(c['buffer_m'], 12)):
                # Mantiene anche la sorgente di base sotto un ritaglio più fine:
                # i suoi pixel riempiono eventuali buchi NoData del dato locale.
                selected.append(s)
        if not remaining.isEmpty() and remaining.area() >= 1:
            raise ValueError(f'DTM: copertura mancante per {remaining.area()/1e6:.2f} km² (margine incluso). Registrare altre sorgenti in fonti.json.')
        if c['export']['maxzoom'] > 17 and any(not s['verified'] or not s.get('native_resolution_m') or s['native_resolution_m'] >= 5 for s in selected):
            raise ValueError('Zoom 18: necessaria copertura completa con sorgenti verificate native sotto i 5 m')
        # Le sorgenti più dettagliate devono essere le ultime nel mosaico.
        return list(reversed(selected)), target

    def source_coverage(self, source, crs, search_remote_edges=False):
        """Copertura di catalogo; per fonti remote include solo la prima fascia di ricerca."""
        footprint = geometry_in(QgsGeometry.fromWkt(source['coverage_wkt']), 'EPSG:4326', crs)
        if search_remote_edges and source.get('provider') in (
                'swisstopo_stac_cog', 'bev_atom_cog', 'arcgis_imageserver'):
            margin = min(1000.0, float(source.get('remote_grid_m', 1000)))
            footprint = footprint.buffer(margin, 8)
        return footprint

    def stage(self, name, signature, outputs, state, area, callback):
        self.cancel()
        sig = digest({'version': VERSION, 'inputs': signature})
        old = state.get(name, {})
        if old.get('signature') == sig and all(Path(p).exists() for p in outputs):
            current = [fingerprint(p) for p in outputs]
            if old.get('outputs') == current:
                self.log(f'{name}: già aggiornato')
                return False
        self.log(f'{name}: elaborazione')
        start = time.monotonic()
        callback()
        self.cancel()
        if not all(Path(p).exists() for p in outputs):
            raise RuntimeError(f'{name}: output non completati')
        state[name] = {'signature': sig, 'outputs': [fingerprint(p) for p in outputs], 'seconds': round(time.monotonic()-start, 3)}
        save_json(area / 'elaborati/stato.json', state)
        return True

    def warp_local_dtm_tile(self, source, rect, crs, resolution, destination):
        """Normalizza prima alla risoluzione reale i raster sovracampionati."""
        source_nodata = source.get('nodata', -9999)
        native = float(source.get('native_resolution_m') or source['grid_m'])
        stored = float(source['grid_m'])
        common = dict(format='GTiff', dstSRS=crs, outputType=gdal.GDT_Float32,
                      srcNodata=source_nodata, dstNodata=-9999, warpMemoryLimit=64,
                      multithread=False,
                      creationOptions=['TILED=YES', 'COMPRESS=DEFLATE', 'PREDICTOR=3'])
        if native <= stored * 1.01:
            warped = gdal.Warp(
                str(destination), str(self.source_path(source)), srcSRS=source['crs'],
                outputBounds=[rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum()],
                xRes=resolution, yRes=resolution, targetAlignedPixels=True,
                resampleAlg='bilinear', **common)
            if warped is None:
                raise RuntimeError(f"Riproiezione DTM {source['id']} fallita")
            warped = None
            return
        # Alcuni prodotti sono archiviati su una griglia più fitta del loro contenuto
        # reale (es. HR-DTM: celle 5 m duplicate da un dato nativo 10 m). Prima si
        # ricostruisce la griglia nativa con media, poi si interpola sul reticolo comune.
        padding = native * 2
        native_temp = Path(str(destination) + '.native.tif')
        native_temp.unlink(missing_ok=True)
        try:
            normalized = gdal.Warp(
                str(native_temp), str(self.source_path(source)), srcSRS=source['crs'],
                outputBounds=[rect.xMinimum()-padding, rect.yMinimum()-padding,
                              rect.xMaximum()+padding, rect.yMaximum()+padding],
                xRes=native, yRes=native, targetAlignedPixels=True,
                resampleAlg='average', **common)
            if normalized is None:
                raise RuntimeError(f"Normalizzazione nativa DTM {source['id']} fallita")
            normalized = None
            warped = gdal.Warp(
                str(destination), str(native_temp),
                outputBounds=[rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum()],
                xRes=resolution, yRes=resolution, targetAlignedPixels=True,
                resampleAlg='bilinear', **common)
            if warped is None:
                raise RuntimeError(f"Ricampionamento DTM {source['id']} fallito")
            warped = None
        finally:
            native_temp.unlink(missing_ok=True)

    def cached_tiles(self, source, extent, crs, resolution):
        bbox = extent.boundingBox()
        tiles = []
        crs_name = crs.lower().replace(':', '-')
        resolution_name = f'{resolution:g}'.replace('.', 'p')
        cache = self.archive / 'dtm/tasselli' / source['id'] / f'{crs_name}_r{resolution_name}m'
        cache.mkdir(parents=True, exist_ok=True)
        # I contorni nazionali nel catalogo sono semplificati. Per le sole fonti
        # remote interroghiamo anche la prima fascia esterna, al massimo 1 km:
        # il servizio ufficiale restituisce comunque soltanto i COG esistenti.
        footprint = self.source_coverage(source, crs, search_remote_edges=True)
        for ix in range(math.floor(bbox.xMinimum()/10000), math.ceil(bbox.xMaximum()/10000)):
            for iy in range(math.floor(bbox.yMinimum()/10000), math.ceil(bbox.yMaximum()/10000)):
                self.cancel()
                rect = QgsRectangle(ix*10000, iy*10000, (ix+1)*10000, (iy+1)*10000)
                if not footprint.intersects(QgsGeometry.fromRect(rect)):
                    continue
                tile = cache / f'{ix}_{iy}.tif'
                stamp = tile.with_suffix('.json')
                signature_data = {'source': self.source_fingerprint(source), 'crs': crs,
                                  'res': resolution, 'source_crs': source['crs']}
                if source.get('provider') == 'arcgis_imageserver':
                    # Il servizio ARSO restituisce -3 (NoData) se interrogato a 5 m:
                    # i tasselli salvati con il vecchio campionamento vanno rigenerati.
                    signature_data['sampling'] = 'native-lerc2-v2'
                if float(source.get('native_resolution_m') or source['grid_m']) > float(source['grid_m']) * 1.01:
                    signature_data['sampling'] = 'native-prefilter-v1'
                signature = digest(signature_data)
                saved = load_json(stamp) if stamp.exists() else {}
                valid_origins = {source['url'], source.get('fallback_url')} if source.get('provider') == 'arcgis_imageserver' else set()
                reusable = (tile.exists() and saved.get('signature') == signature and
                            (not saved.get('remote_origins') or
                             set(saved['remote_origins']).issubset(valid_origins)))
                if not reusable:
                    temp = cache / f'{ix}_{iy}.partial.tif'
                    source_nodata = source.get('nodata', -9999)
                    remote_origins = None
                    if source.get('provider') == 'arcgis_imageserver':
                        remote_origins = self.download_arcgis_tile(source, rect, crs, resolution, temp)
                    elif source.get('provider') == 'bev_atom_cog':
                        self.download_bev_cog_tile(source, rect, crs, resolution, temp)
                    elif source.get('provider') == 'swisstopo_stac_cog':
                        self.download_swisstopo_cog_tile(source, rect, crs, resolution, temp)
                    else:
                        self.warp_local_dtm_tile(source, rect, crs, resolution, temp)
                    cog_copy(temp, tile)
                    temp.unlink()
                    details = {'signature': signature, 'source_id': source['id'],
                               'crs': crs, 'resolution_m': resolution}
                    if remote_origins is not None:
                        details['remote_origins'] = remote_origins
                    save_json(stamp, details)
                    self.log(f'Tassello comune creato: {source["id"]}/{ix}_{iy}')
                else:
                    self.log(f'Tassello comune riutilizzato: {source["id"]}/{ix}_{iy}')
                tiles.append(str(tile))
        xs = [int(Path(tile).stem.split('_')[0]) for tile in tiles]
        ys = [int(Path(tile).stem.split('_')[1]) for tile in tiles]
        vrt = self.archive / 'mosaici' / (
            f'{source["id"]}_{crs_name}_r{resolution_name}m_'
            f'x{min(xs)}-{max(xs)}_y{min(ys)}-{max(ys)}.vrt')
        # L'intervallo min/max nel nome può restare invariato anche quando viene
        # aggiunto un tassello interno prima escluso dal contorno semplificato.
        vrt.parent.mkdir(parents=True, exist_ok=True)
        vrt.unlink(missing_ok=True)
        ds = gdal.BuildVRT(str(vrt), tiles, srcNodata=-9999, VRTNodata=-9999)
        if ds is None:
            raise RuntimeError('Mosaico virtuale non creato')
        ds = None
        # VRT portabili anche dopo lo spostamento dell'intera cartella.
        import xml.etree.ElementTree as ET
        tree = ET.parse(vrt); changed = False
        for node in tree.findall('.//SourceFilename'):
            if node.get('relativeToVRT') != '1' and Path(node.text).is_absolute():
                node.text = os.path.relpath(node.text, vrt.parent)
                node.set('relativeToVRT', '1'); changed = True
        if changed:
            tree.write(vrt, encoding='utf-8', xml_declaration=True)
        return vrt

    def download_arcgis_tile(self, source, rect, crs, resolution, destination):
        """Legge ARSO al passo nativo, poi ricampiona localmente alla griglia di lavoro.

        ARSO non serve piramidi affidabili: exportImage a 2–5 m può restituire
        un TIFF valido ma composto interamente dal valore -3, anche dove identify
        restituisce quote. LERC2 senza perdita evita di scaricare TIFF 1 m enormi.
        """
        width = int(round(rect.width()/resolution))
        height = int(round(rect.height()/resolution))
        max_width = int(source.get('max_image_width', 15000))
        max_height = int(source.get('max_image_height', 4100))
        native = min(float(source.get('native_resolution_m') or resolution), float(resolution))
        if width <= 0 or height <= 0 or native <= 0:
            raise ValueError(f"{source['id']}: dimensioni raster non valide")
        # Il margine copre i vicini necessari all'interpolazione ai bordi dei blocchi.
        halo = 2 * native
        # Blocchi LERC di circa 4 milioni di pixel per evitare il limite di
        # decodifica del driver MRF usato da GDAL per il formato LERC grezzo.
        block_pixels = max(1, int((min(2000, max_width, max_height)-4)*native/resolution))
        wkid = crs.split(':', 1)[-1]
        footprint = self.source_coverage(source, crs) if source.get('coverage_wkt') else None
        raw = Path(str(destination) + '.download.lerc')
        raw.unlink(missing_ok=True)
        output = None
        remote_origins = set()
        try:
            driver = gdal.GetDriverByName('GTiff')
            output = driver.Create(str(destination), width, height, 1, gdal.GDT_Float32,
                                   options=['TILED=YES', 'COMPRESS=DEFLATE', 'PREDICTOR=3'])
            output.SetGeoTransform((rect.xMinimum(), resolution, 0,
                                    rect.yMaximum(), 0, -resolution))
            spatial = osr.SpatialReference(); spatial.SetFromUserInput(crs)
            output.SetProjection(spatial.ExportToWkt())
            band = output.GetRasterBand(1)
            band.SetNoDataValue(-9999); band.Fill(-9999)
            for y in range(0, height, block_pixels):
                for x in range(0, width, block_pixels):
                    self.cancel()
                    w = min(block_pixels, width-x); h = min(block_pixels, height-y)
                    west = rect.xMinimum()+x*resolution
                    east = west+w*resolution
                    north = rect.yMaximum()-y*resolution
                    south = north-h*resolution
                    sample = (west-halo, south-halo, east+halo, north+halo)
                    if footprint is not None and not footprint.intersects(
                            QgsGeometry.fromRect(QgsRectangle(*sample))):
                        continue
                    sample_width = int(math.ceil((sample[2]-sample[0])/native))
                    sample_height = int(math.ceil((sample[3]-sample[1])/native))
                    if sample_width > max_width or sample_height > max_height:
                        raise ValueError(f"{source['id']}: blocco nativo oltre il limite del servizio")
                    params = {
                        'bbox': ','.join(f'{value:.12g}' for value in sample),
                        'bboxSR': wkid, 'imageSR': wkid,
                        'size': f'{sample_width},{sample_height}',
                        'format': 'lerc', 'lercVersion': '2',
                        'lercCompressionTolerance': '0',
                        'pixelType': 'F32', 'f': 'image',
                    }
                    url = source['url'].rstrip('/') + '/exportImage?' + urlencode(params)
                    dataset, origin = self.download_arcgis_lerc_block(source, url, raw)
                    remote_origins.add(origin)
                    # ARSO codifica il fuori-copertura LERC come -1e10, mentre il
                    # TIFF a bassa risoluzione usa -3. Normalizzare entrambi prima
                    # dell'interpolazione evita quote spurie ai bordi.
                    values = dataset.ReadAsArray()
                    invalid = (~np.isfinite(values) | (values == source.get('nodata', -9999)) |
                               (values <= -1e8))
                    values[invalid] = -9999
                    normalized = gdal.GetDriverByName('MEM').Create(
                        '', sample_width, sample_height, 1, gdal.GDT_Float32)
                    normalized.GetRasterBand(1).SetNoDataValue(-9999)
                    normalized.GetRasterBand(1).WriteArray(values)
                    georef = gdal.Translate('', normalized, format='VRT',
                                            outputBounds=[sample[0], sample[3], sample[2], sample[1]],
                                            outputSRS=crs)
                    values = normalized = dataset = None
                    warped = gdal.Warp('', georef, format='MEM',
                                       outputBounds=[west, south, east, north],
                                       width=w, height=h, srcNodata=-9999,
                                       dstNodata=-9999, outputType=gdal.GDT_Float32,
                                       resampleAlg='bilinear', warpMemoryLimit=64)
                    if warped is None:
                        raise RuntimeError('ricampionamento del blocco ARSO fallito')
                    band.WriteArray(warped.ReadAsArray(), x, y)
                    warped = georef = None
                    raw.unlink()
            band = None
            output = None
            return sorted(remote_origins)
        except Exception as exc:
            output = None
            Path(destination).unlink(missing_ok=True)
            raise RuntimeError(f"Download DTM remoto {source['id']} fallito: {exc}") from exc
        finally:
            raw.unlink(missing_ok=True)

    def download_arcgis_lerc_block(self, source, url, raw):
        """Legge LERC2 da ARSO o dal servizio ufficiale GeoHub di riserva."""
        last_error = None
        primary = source['url'].rstrip('/')
        suffix = url[len(primary):]
        endpoints = [primary]
        if source.get('fallback_url'):
            endpoints.append(source['fallback_url'].rstrip('/'))
        for endpoint in endpoints:
            if endpoint == primary and len(endpoints) > 1 and time.monotonic() < self._arcgis_unavailable_until.get(primary, 0):
                continue
            for attempt in range(3):
                self.cancel()
                if attempt:
                    time.sleep((1, 3)[attempt-1])
                raw.unlink(missing_ok=True)
                request = Request(endpoint + suffix,
                                  headers={'User-Agent': f'Scialpinismo-QGIS/{VERSION}'})
                try:
                    with urlopen(request, timeout=180) as response, raw.open('wb') as stream:
                        shutil.copyfileobj(response, stream, length=1024*1024)
                except (URLError, TimeoutError, ConnectionError) as exc:
                    last_error = f'errore di rete: {exc}'
                    self.log(f'{source["id"]} {endpoint}: tentativo {attempt+1}/3 fallito ({last_error})')
                    continue
                with raw.open('rb') as stream:
                    header = stream.read(1024).lstrip()
                if header.lower().startswith((b'<html', b'<!doctype html')):
                    last_error = 'pagina HTML al posto del raster LERC2 (portale GIS temporaneamente indisponibile)'
                    self.log(f'{source["id"]} {endpoint}: tentativo {attempt+1}/3 fallito ({last_error})')
                    continue
                if header.startswith(b'{'):
                    try:
                        response = json.loads(raw.read_text(encoding='utf-8'))
                        error = response.get('error', {})
                        last_error = f"errore ArcGIS {error.get('code', '?')}: {error.get('message', 'risposta JSON')}"
                    except (ValueError, AttributeError, UnicodeError):
                        last_error = 'risposta JSON non raster'
                    self.log(f'{source["id"]} {endpoint}: tentativo {attempt+1}/3 fallito ({last_error})')
                    continue
                try:
                    dataset = gdal.Open(str(raw))
                    if dataset is None or dataset.RasterCount != 1 or dataset.GetRasterBand(1).DataType != gdal.GDT_Float32:
                        raise RuntimeError('risposta LERC2 Float32 non valida')
                except RuntimeError as exc:
                    last_error = f'risposta non raster: {exc}'
                    self.log(f'{source["id"]} {endpoint}: tentativo {attempt+1}/3 fallito ({last_error})')
                    continue
                if endpoint != primary and endpoint not in self._arcgis_fallback_reported:
                    self.log(f'{source["id"]}: uso del DMR1 numerico GeoHub come sorgente di riserva')
                    self._arcgis_fallback_reported.add(endpoint)
                return dataset, endpoint
            if endpoint == primary and len(endpoints) > 1:
                self._arcgis_unavailable_until[primary] = time.monotonic() + 300
        raise RuntimeError(f'servizio DTM {source["id"]} temporaneamente non disponibile: '
                           f'{last_error}. Riprovare quando i servizi tornano online; '
                           'i tasselli già validi restano in cache')

    def bev_cogs_for_rect(self, source, rect, crs):
        """Risolve dall'indice ATOM i COG da 50 km che intersecano il tassello."""
        index_path = self.archive/'dtm/tasselli'/source['id']/'bev_atom_index.json'
        signature = self.source_fingerprint(source)
        cache = load_json(index_path) if index_path.exists() else {}
        if cache.get('signature') != signature or not cache.get('service'):
            request = Request(source['atom_url'], headers={'User-Agent': f'Scialpinismo-QGIS/{VERSION}'})
            try:
                with urlopen(request, timeout=120) as response:
                    service = parse_bev_atom_index(response.read())
            except Exception as exc:
                raise RuntimeError(f"Indice ATOM BEV non disponibile: {exc}") from exc
            if not service:
                raise RuntimeError('Indice ATOM BEV privo di tasselli ALS-DTM EPSG:3035')
            cache = {'signature': signature, 'service': service, 'resolved': {}}
            save_json(index_path, cache)
        footprint = geometry_in(QgsGeometry.fromRect(rect), crs, source['crs'])
        bbox = footprint.boundingBox()
        grid = int(source.get('remote_grid_m', 50000))
        resolved = cache.setdefault('resolved', {})
        urls = []
        changed = False
        for north in range(math.floor(bbox.yMinimum()/grid)*grid, math.ceil(bbox.yMaximum()/grid)*grid, grid):
            for east in range(math.floor(bbox.xMinimum()/grid)*grid, math.ceil(bbox.xMaximum()/grid)*grid, grid):
                key = f'{north}_{east}'
                feed = cache['service'].get(key)
                if not feed:
                    continue
                url = resolved.get(key)
                if not url:
                    request = Request(feed, headers={'User-Agent': f'Scialpinismo-QGIS/{VERSION}'})
                    try:
                        with urlopen(request, timeout=60) as response:
                            url = parse_bev_atom_tif(response.read())
                    except Exception as exc:
                        raise RuntimeError(f'Dataset feed BEV {key} non disponibile: {exc}') from exc
                    if not url:
                        raise RuntimeError(f'Dataset feed BEV {key} senza GeoTIFF')
                    resolved[key] = url
                    changed = True
                urls.append(url)
        if changed:
            save_json(index_path, cache)
        return urls

    def download_bev_cog_tile(self, source, rect, crs, resolution, destination):
        """Legge via HTTP Range solo la finestra utile dei COG BEV da circa 5 GB."""
        urls = self.bev_cogs_for_rect(source, rect, crs)
        if not urls:
            raise RuntimeError(f"{source['id']}: nessun tassello ALS-DTM BEV nell'area richiesta")
        for key, value in {
                'GDAL_DISABLE_READDIR_ON_OPEN': 'EMPTY_DIR',
                'CPL_VSIL_CURL_ALLOWED_EXTENSIONS': '.tif,.TIF',
                'GDAL_HTTP_MULTIRANGE': 'YES',
                'GDAL_HTTP_MERGE_CONSECUTIVE_RANGES': 'YES'}.items():
            gdal.SetConfigOption(key, value)
        remote = ['/vsicurl/' + url for url in urls]
        try:
            warped = gdal.Warp(
                str(destination), remote, format='GTiff', srcSRS=source['crs'], dstSRS=crs,
                outputBounds=[rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum()],
                xRes=resolution, yRes=resolution, targetAlignedPixels=True,
                srcNodata=source.get('nodata', -9999), dstNodata=-9999,
                outputType=gdal.GDT_Float32, resampleAlg='bilinear', warpMemoryLimit=64,
                multithread=False, creationOptions=['TILED=YES', 'COMPRESS=DEFLATE', 'PREDICTOR=3'])
            if warped is None:
                raise RuntimeError('lettura parziale COG fallita')
            warped = None
        except Exception as exc:
            Path(destination).unlink(missing_ok=True)
            raise RuntimeError(f"Download DTM remoto {source['id']} fallito: {exc}") from exc

    def swisstopo_cogs_for_rect(self, source, rect, crs):
        """Interroga STAC e restituisce il COG 2 m più recente per ogni tassello da 1 km."""
        footprint = geometry_in(QgsGeometry.fromRect(rect), crs, 'EPSG:4326')
        bbox = footprint.boundingBox()
        params = {'bbox': ','.join(f'{value:.8f}' for value in
                                   (bbox.xMinimum(), bbox.yMinimum(),
                                    bbox.xMaximum(), bbox.yMaximum())),
                  'limit': 100}
        next_url = source['stac_url'].rstrip('/') + '/items?' + urlencode(params)
        resolution = float(source.get('remote_resolution_m', 2))
        latest = {}
        pages = 0
        while next_url:
            pages += 1
            if pages > 50:
                raise RuntimeError('Risposta STAC swisstopo con paginazione eccessiva')
            request = Request(next_url, headers={'User-Agent': f'Scialpinismo-QGIS/{VERSION}'})
            try:
                with urlopen(request, timeout=120) as response:
                    records, next_url = parse_swisstopo_stac_page(response.read(), resolution)
            except Exception as exc:
                raise RuntimeError(f'Indice STAC swisstopo non disponibile: {exc}') from exc
            for record in records:
                old = latest.get(record['key'])
                if old is None or record['datetime'] > old['datetime']:
                    latest[record['key']] = record
        return [record['url'] for record in latest.values()]

    def download_swisstopo_cog_tile(self, source, rect, crs, resolution, destination):
        """Scarica una sola volta i piccoli COG 2 m da 1 km e crea il tassello di lavoro."""
        urls = self.swisstopo_cogs_for_rect(source, rect, crs)
        if not urls:
            raise RuntimeError(f"{source['id']}: nessun tassello swissALTI3D nell'area richiesta")
        raw_cache = (self.archive/source.get(
            'original_cache_path', f'dtm/originali/{source["id"]}')).resolve()
        if self.archive.resolve() not in raw_cache.parents:
            raise ValueError(f"{source['id']}: cartella degli originali esterna all'archivio comune")
        raw_cache.mkdir(parents=True, exist_ok=True)
        files = []
        try:
            for url in urls:
                self.cancel()
                name = Path(urlparse(url).path).name
                if not name.lower().endswith(('.tif', '.tiff')):
                    raise RuntimeError(f'Asset STAC non riconosciuto: {url}')
                local = raw_cache/name
                if not local.exists():
                    partial = local.with_suffix(local.suffix + '.partial')
                    partial.unlink(missing_ok=True)
                    request = Request(url, headers={'User-Agent': f'Scialpinismo-QGIS/{VERSION}'})
                    with urlopen(request, timeout=180) as response, partial.open('wb') as stream:
                        shutil.copyfileobj(response, stream, length=1024*1024)
                    dataset = gdal.Open(str(partial))
                    if dataset is None or dataset.RasterCount != 1:
                        raise RuntimeError(f'COG swisstopo non leggibile: {name}')
                    dataset = None
                    partial.replace(local)
                files.append(str(local))
            warped = gdal.Warp(
                str(destination), files, format='GTiff', srcSRS=source['crs'], dstSRS=crs,
                outputBounds=[rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum()],
                xRes=resolution, yRes=resolution, targetAlignedPixels=True,
                srcNodata=source.get('nodata', -9999), dstNodata=-9999,
                outputType=gdal.GDT_Float32, resampleAlg='bilinear', warpMemoryLimit=64,
                multithread=False, creationOptions=['TILED=YES', 'COMPRESS=DEFLATE', 'PREDICTOR=3'])
            if warped is None:
                raise RuntimeError('mosaico swissALTI3D fallito')
            warped = None
        except Exception as exc:
            Path(destination).unlink(missing_ok=True)
            for partial in raw_cache.glob('*.partial'):
                partial.unlink(missing_ok=True)
            raise RuntimeError(f"Download DTM remoto {source['id']} fallito: {exc}") from exc

    def repair_dtm_seams(self, path, resolution, max_distance_m=60):
        """Chiude solo micro-cuciture tra raster; i vuoti più ampi restano NoData."""
        dataset = gdal.Open(str(path), gdal.GA_Update)
        if dataset is None:
            raise RuntimeError(f'DTM non apribile per la correzione delle cuciture: {path}')
        band = dataset.GetRasterBand(1)
        distance_pixels = max(1, math.ceil(max_distance_m / resolution))
        result = gdal.FillNodata(band, None, distance_pixels, 0, callback=self.gdal_callback)
        band = None
        dataset = None
        if result != gdal.CE_None:
            raise RuntimeError('Correzione delle micro-cuciture DTM fallita')
        self.log(f'Micro-cuciture DTM corrette entro {max_distance_m:g} m; i vuoti maggiori restano NoData')

    def _coarse_dem(self, path, bounds, resolution):
        """Legge un DTM su una griglia fisica di confronto con antialiasing."""
        dataset = gdal.Warp(
            '', str(path), format='MEM', outputBounds=bounds,
            xRes=resolution, yRes=resolution, outputType=gdal.GDT_Float32,
            resampleAlg='average', srcNodata=-9999, dstNodata=-9999,
            warpMemoryLimit=128, multithread=False)
        if dataset is None:
            raise RuntimeError(f'Griglia di confronto non creata per {path}')
        values = dataset.GetRasterBand(1).ReadAsArray().astype(np.float32)
        valid = np.isfinite(values) & (values != -9999)
        return dataset, values, valid

    def _shift_aligned_dem(self, source, destination, dx, dy, bounds, width, height):
        """Applica una traslazione sub-pixel correggendo la georeferenziazione del candidato."""
        shifted_vrt = Path(str(destination) + '.shift.vrt')
        shifted_vrt.unlink(missing_ok=True)
        vrt = gdal.Translate(str(shifted_vrt), str(source), format='VRT')
        if vrt is None:
            raise RuntimeError('VRT temporaneo per la co-registrazione non creato')
        transform = list(vrt.GetGeoTransform())
        transform[0] -= float(dx)
        transform[3] -= float(dy)
        vrt.SetGeoTransform(transform)
        vrt = None
        try:
            output = gdal.Warp(
                str(destination), str(shifted_vrt), format='GTiff', outputBounds=bounds,
                width=width, height=height, outputType=gdal.GDT_Float32,
                resampleAlg='cubic', srcNodata=-9999, dstNodata=-9999,
                warpMemoryLimit=128, multithread=False,
                creationOptions=['TILED=YES', 'COMPRESS=DEFLATE', 'PREDICTOR=3', 'BIGTIFF=IF_SAFER'])
            if output is None:
                raise RuntimeError('Applicazione della co-registrazione DTM fallita')
            output = None
        finally:
            shifted_vrt.unlink(missing_ok=True)

    def _write_seam_grid(self, path, reference, correction, low_weight, high_weight):
        driver = gdal.GetDriverByName('GTiff')
        dataset = driver.Create(str(path), reference.RasterXSize, reference.RasterYSize, 3,
                                gdal.GDT_Float32,
                                options=['TILED=YES', 'COMPRESS=DEFLATE', 'PREDICTOR=3'])
        dataset.SetGeoTransform(reference.GetGeoTransform())
        dataset.SetProjection(reference.GetProjection())
        for index, values in enumerate((correction, low_weight, high_weight), 1):
            dataset.GetRasterBand(index).WriteArray(values)
        dataset = None

    def _compose_pair_blocks(self, base_path, candidate_path, seam_path, provenance_path,
                             output_path, source_index, resolution, worst_native):
        """Fonde due DTM a piena risoluzione per blocchi, preservando le alte frequenze."""
        base = gdal.Open(str(base_path))
        candidate = gdal.Open(str(candidate_path))
        seam = gdal.Open(str(seam_path))
        provenance = gdal.Open(str(provenance_path), gdal.GA_Update)
        driver = gdal.GetDriverByName('GTiff')
        output = driver.Create(
            str(output_path), base.RasterXSize, base.RasterYSize, 1, gdal.GDT_Float32,
            options=['TILED=YES', 'COMPRESS=DEFLATE', 'PREDICTOR=3', 'BIGTIFF=IF_SAFER'])
        output.SetGeoTransform(base.GetGeoTransform())
        output.SetProjection(base.GetProjection())
        output_band = output.GetRasterBand(1)
        output_band.SetNoDataValue(-9999)
        sigma = max(0.8, float(worst_native) / (2.0 * float(resolution)))
        halo = max(3, int(math.ceil(3.0 * sigma)))
        qa_rejected = 0
        for y in range(0, base.RasterYSize, 512):
            height = min(512, base.RasterYSize - y)
            for x in range(0, base.RasterXSize, 512):
                self.cancel()
                width = min(512, base.RasterXSize - x)
                x0 = max(0, x - halo); y0 = max(0, y - halo)
                x1 = min(base.RasterXSize, x + width + halo)
                y1 = min(base.RasterYSize, y + height + halo)
                expanded_width = x1 - x0; expanded_height = y1 - y0
                base_values = base.GetRasterBand(1).ReadAsArray(
                    x0, y0, expanded_width, expanded_height).astype(np.float32)
                candidate_values = candidate.GetRasterBand(1).ReadAsArray(
                    x0, y0, expanded_width, expanded_height).astype(np.float32)
                seam_values = seam.ReadAsArray(x0, y0, expanded_width, expanded_height)
                correction, low_weight, high_weight = seam_values
                base_valid = np.isfinite(base_values) & (base_values != -9999)
                candidate_valid = np.isfinite(candidate_values) & (candidate_values != -9999)
                corrected = candidate_values + correction
                base_low, _ = normalized_gaussian(base_values, base_valid, sigma)
                candidate_low, _ = normalized_gaussian(corrected, candidate_valid, sigma)
                base_low = np.where(np.isfinite(base_low), base_low, base_values)
                candidate_low = np.where(np.isfinite(candidate_low), candidate_low, corrected)
                merged = ((1.0-low_weight)*base_low + low_weight*candidate_low +
                          (1.0-high_weight)*(base_values-base_low) +
                          high_weight*(corrected-candidate_low))
                merged = np.where(base_valid & ~candidate_valid, base_values, merged)
                merged = np.where(candidate_valid & ~base_valid, corrected, merged)
                merged = np.where(base_valid | candidate_valid, merged, -9999).astype(np.float32)

                overlap = base_valid & candidate_valid & (low_weight > 0) & (low_weight < 1)
                if np.any(overlap):
                    def slope(values):
                        gy, gx = np.gradient(values.astype(np.float64),
                                             float(resolution), float(resolution))
                        return np.degrees(np.arctan(np.hypot(gx, gy)))
                    safe_base = np.where(base_valid, base_values, merged)
                    safe_candidate = np.where(candidate_valid, corrected, merged)
                    slope_base = slope(safe_base)
                    slope_candidate = slope(safe_candidate)
                    slope_merged = slope(merged)
                    invalid_slope = overlap & (
                        (slope_merged > np.maximum(slope_base, slope_candidate) + 5.0) |
                        ((slope_merged >= 30.0) & (slope_base < 25.0) &
                         (slope_candidate < 25.0)))
                    if np.any(invalid_slope):
                        invalid_slope = binary_dilation(invalid_slope, iterations=1) & overlap
                        qa_rejected += int(invalid_slope.sum())
                        merged[invalid_slope] = base_values[invalid_slope]
                        high_weight[invalid_slope] = 0.0

                crop_y = y-y0; crop_x = x-x0
                cropped = merged[crop_y:crop_y+height, crop_x:crop_x+width]
                output_band.WriteArray(cropped, x, y)
                provenance_values = provenance.GetRasterBand(1).ReadAsArray(x, y, width, height)
                candidate_choice = high_weight[crop_y:crop_y+height, crop_x:crop_x+width] >= 0.5
                candidate_only = (candidate_valid & ~base_valid)[
                    crop_y:crop_y+height, crop_x:crop_x+width]
                provenance_values[candidate_choice | candidate_only] = source_index
                provenance.GetRasterBand(1).WriteArray(provenance_values, x, y)
        output_band = None; output = None
        provenance = None; seam = None; candidate = None; base = None
        return qa_rejected

    def compose_dtm_sources(self, vrts, sources, bounds, crs, resolution, destination):
        """Mosaico gerarchico: co-registrazione, correzione lenta e seamline corta."""
        work = Path(destination).parent
        current = work/'dtm_mosaic.current.tif'
        candidate = work/'dtm_source.partial.tif'
        shifted = work/'dtm_source_shifted.partial.tif'
        seam_coarse = work/'dtm_seam_coarse.partial.tif'
        seam_fine = work/'dtm_seam_fine.partial.tif'
        following = work/'dtm_mosaic.next.tif'
        provenance_path = work/'dtm_provenance.partial.tif'
        temporaries = (current, candidate, shifted, seam_coarse, seam_fine, following,
                       provenance_path)
        for path in temporaries:
            path.unlink(missing_ok=True)
        diagnostics = []
        try:
            first = gdal.Warp(
                str(current), str(vrts[0]), format='GTiff', dstSRS=crs,
                outputBounds=bounds, xRes=resolution, yRes=resolution,
                targetAlignedPixels=True, outputType=gdal.GDT_Float32,
                resampleAlg='bilinear', srcNodata=-9999, dstNodata=-9999,
                warpMemoryLimit=128, multithread=False,
                creationOptions=['TILED=YES', 'COMPRESS=DEFLATE', 'PREDICTOR=3', 'BIGTIFF=IF_SAFER'])
            if first is None:
                raise RuntimeError('DTM di base non creato')
            transform = first.GetGeoTransform()
            width, height = first.RasterXSize, first.RasterYSize
            aligned_bounds = [transform[0], transform[3] + height*transform[5],
                              transform[0] + width*transform[1], transform[3]]
            projection = first.GetProjection()
            first = None
            provenance = gdal.GetDriverByName('GTiff').Create(
                str(provenance_path), width, height, 1, gdal.GDT_Byte,
                options=['TILED=YES', 'COMPRESS=DEFLATE'])
            provenance.SetGeoTransform(transform); provenance.SetProjection(projection)
            provenance.GetRasterBand(1).Fill(0)
            source_dataset = gdal.Open(str(current))
            for y in range(0, height, 512):
                block_height = min(512, height-y)
                for x in range(0, width, 512):
                    block_width = min(512, width-x)
                    values = source_dataset.GetRasterBand(1).ReadAsArray(
                        x, y, block_width, block_height)
                    provenance.GetRasterBand(1).WriteArray(
                        (np.isfinite(values) & (values != -9999)).astype(np.uint8), x, y)
            source_dataset = None
            provenance = None

            for source_index, (vrt, source) in enumerate(zip(vrts[1:], sources[1:]), 2):
                self.cancel()
                candidate.unlink(missing_ok=True)
                warped = gdal.Warp(
                    str(candidate), str(vrt), format='GTiff', outputBounds=aligned_bounds,
                    width=width, height=height, outputType=gdal.GDT_Float32,
                    resampleAlg='cubic', srcNodata=-9999, dstNodata=-9999,
                    warpMemoryLimit=128, multithread=False,
                    creationOptions=['TILED=YES', 'COMPRESS=DEFLATE', 'PREDICTOR=3', 'BIGTIFF=IF_SAFER'])
                if warped is None:
                    raise RuntimeError(f"Allineamento DTM {source['id']} fallito")
                warped = None
                worst_native = max(float(source.get('native_resolution_m') or source['grid_m']),
                                   max(float(s.get('native_resolution_m') or s['grid_m'])
                                       for s in sources[:source_index-1]))
                analysis_resolution = max(DTM_COMPARISON_MIN_M, 2.0*worst_native)
                base_coarse, base_values, base_valid = self._coarse_dem(
                    current, aligned_bounds, analysis_resolution)
                candidate_coarse, candidate_values, candidate_valid = self._coarse_dem(
                    candidate, aligned_bounds, analysis_resolution)
                coreg = estimate_dem_coregistration(
                    base_values, candidate_values, base_valid, candidate_valid,
                    analysis_resolution, worst_native)
                active_candidate = candidate
                if coreg['accepted'] and math.hypot(coreg['dx_m'], coreg['dy_m']) >= 0.05:
                    shifted.unlink(missing_ok=True)
                    self._shift_aligned_dem(candidate, shifted, coreg['dx_m'], coreg['dy_m'],
                                            aligned_bounds, width, height)
                    active_candidate = shifted
                    candidate_coarse = None
                    candidate_coarse, candidate_values, candidate_valid = self._coarse_dem(
                        active_candidate, aligned_bounds, analysis_resolution)
                vertical_shift = coreg['dz_m'] if coreg['accepted'] else 0.0
                correction, low_weight, high_weight, seam_diagnostics = seam_fields(
                    base_values, candidate_values, base_valid, candidate_valid,
                    analysis_resolution, worst_native, vertical_shift)
                # dz è una traslazione globale; la griglia contiene la sola correzione locale.
                correction += float(vertical_shift)
                self._write_seam_grid(seam_coarse, base_coarse, correction,
                                      low_weight, high_weight)
                base_coarse = None; candidate_coarse = None
                seam_dataset = gdal.Warp(
                    str(seam_fine), str(seam_coarse), format='GTiff',
                    outputBounds=aligned_bounds, width=width, height=height,
                    outputType=gdal.GDT_Float32, resampleAlg='bilinear',
                    warpMemoryLimit=128, multithread=False,
                    creationOptions=['TILED=YES', 'COMPRESS=DEFLATE', 'PREDICTOR=3', 'BIGTIFF=IF_SAFER'])
                if seam_dataset is None:
                    raise RuntimeError('Campi di cucitura non riportati alla griglia fine')
                seam_dataset = None
                following.unlink(missing_ok=True)
                qa_rejected = self._compose_pair_blocks(
                    current, active_candidate, seam_fine, provenance_path, following,
                    source_index, resolution, worst_native)
                current.unlink()
                following.replace(current)
                diagnostics.append({
                    'source_id': source['id'], **coreg, **seam_diagnostics,
                    'qa_rejected_cells': qa_rejected,
                })
                self.log(
                    f"Cucitura {source['id']}: dx={coreg['dx_m']:.2f} m, "
                    f"dy={coreg['dy_m']:.2f} m, dz={vertical_shift:.2f} m, "
                    f"raccordo={seam_diagnostics['blend_m']:.0f} m, "
                    f"settori incompatibili={seam_diagnostics['incompatible_cells']}")
                for path in (candidate, shifted, seam_coarse, seam_fine):
                    path.unlink(missing_ok=True)
            Path(destination).unlink(missing_ok=True)
            current.replace(destination)
            return diagnostics, provenance_path
        except Exception:
            for path in temporaries:
                path.unlink(missing_ok=True)
            raise

    def adaptive_terrain_derivatives(self, dtm_path, provenance_path, sources, resolution,
                                     slope_path, hillshade_path):
        """Derivati con supporto fisico legato alla risoluzione della sorgente scelta."""
        dtm = gdal.Open(str(dtm_path))
        provenance = gdal.Open(str(provenance_path))
        driver = gdal.GetDriverByName('GTiff')
        options = ['TILED=YES', 'COMPRESS=DEFLATE', 'PREDICTOR=3', 'BIGTIFF=IF_SAFER']
        slope_ds = driver.Create(str(slope_path), dtm.RasterXSize, dtm.RasterYSize, 1,
                                 gdal.GDT_Float32, options=options)
        shade_ds = driver.Create(str(hillshade_path), dtm.RasterXSize, dtm.RasterYSize, 1,
                                 gdal.GDT_Byte,
                                 options=['TILED=YES', 'COMPRESS=DEFLATE', 'BIGTIFF=IF_SAFER'])
        for output in (slope_ds, shade_ds):
            output.SetGeoTransform(dtm.GetGeoTransform())
            output.SetProjection(dtm.GetProjection())
        slope_ds.GetRasterBand(1).SetNoDataValue(-9999)
        shade_ds.GetRasterBand(1).SetNoDataValue(0)
        native = {index: float(source.get('native_resolution_m') or source['grid_m'])
                  for index, source in enumerate(sources, 1)}
        maximum_sigma = max(max(0.0, value/float(resolution)/2.0)
                            for value in native.values())
        halo = max(3, int(math.ceil(3.0*maximum_sigma)) + 1)
        for y in range(0, dtm.RasterYSize, 512):
            height = min(512, dtm.RasterYSize-y)
            for x in range(0, dtm.RasterXSize, 512):
                self.cancel()
                width = min(512, dtm.RasterXSize-x)
                x0=max(0, x-halo); y0=max(0, y-halo)
                x1=min(dtm.RasterXSize, x+width+halo)
                y1=min(dtm.RasterYSize, y+height+halo)
                values = dtm.GetRasterBand(1).ReadAsArray(
                    x0, y0, x1-x0, y1-y0).astype(np.float32)
                provenance_values = provenance.GetRasterBand(1).ReadAsArray(
                    x0, y0, x1-x0, y1-y0)
                valid = np.isfinite(values) & (values != -9999)
                if np.all(valid):
                    filled = values
                elif np.any(valid):
                    nearest = distance_transform_edt(~valid, return_distances=False,
                                                     return_indices=True)
                    filled = values[tuple(nearest)]
                else:
                    filled = np.zeros(values.shape, dtype=np.float32)
                gx = np.zeros(values.shape, dtype=np.float32)
                gy = np.zeros(values.shape, dtype=np.float32)
                for source_index in np.unique(provenance_values):
                    if source_index == 0 or int(source_index) not in native:
                        continue
                    native_resolution = native[int(source_index)]
                    ratio = native_resolution/float(resolution)
                    if ratio <= 1.05:
                        surface = filled
                    else:
                        surface = gaussian_filter(filled, max(0.8, ratio/2.0), mode='nearest')
                    row_gradient, source_gx = np.gradient(
                        surface.astype(np.float64), float(resolution), float(resolution))
                    source_gy = -row_gradient
                    mask = provenance_values == source_index
                    gx[mask] = source_gx[mask]
                    gy[mask] = source_gy[mask]
                slope_radians = np.arctan(np.hypot(gx, gy))
                slope_values = np.degrees(slope_radians).astype(np.float32)
                shade_values = multidirectional_hillshade(gx, gy)
                slope_values[~valid] = -9999
                shade_values[~valid] = 0
                crop_y=y-y0; crop_x=x-x0
                slope_ds.GetRasterBand(1).WriteArray(
                    slope_values[crop_y:crop_y+height, crop_x:crop_x+width], x, y)
                shade_ds.GetRasterBand(1).WriteArray(
                    shade_values[crop_y:crop_y+height, crop_x:crop_x+width], x, y)
        slope_ds = None; shade_ds = None; provenance = None; dtm = None

    def update(self, config_path, max_missing_percent=None):
        with self.locked():
            return self._update(config_path, max_missing_percent)

    def _update(self, config_path, max_missing_percent=None):
        config_path = Path(config_path).resolve()
        if config_path.is_dir():
            config_path /= 'area.json'
        c = load_json(config_path)
        migrated_export = False
        if c['export'].get('mode', 'single') == 'single':
            # Ripulisce al successivo Aggiorna area il vecchio limite automatico,
            # che comunque non viene più applicato durante l'export.
            if c['export'].get('mode') != 'single':
                c['export']['mode'] = 'single'
                migrated_export = True
            if 'max_bytes' in c['export']:
                c['export'].pop('max_bytes')
                migrated_export = True
        if max_missing_percent is not None:
            c['dtm_nodata_policy'] = dtm_nodata_policy(max_missing_percent)
        self.validate_config(c)
        if max_missing_percent is not None or migrated_export:
            save_json(config_path, c)
        area = config_path.parent
        for folder in ('elaborati', 'vettori', 'progetto', 'output/mbtiles', 'output/anteprime', 'output/pdf', 'output/geotiff', 'input/tracce_gpx', 'input/dtm_originale'):
            (area / folder).mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        selected, geometry = self.select_sources(c)
        self.progress(5, 'Sorgenti selezionate: ' + ', '.join(s['id'] for s in selected))
        gpkg = area / 'vettori/dati_area.gpkg'
        # Annota in un layer indipendente; le fasi successive non lo sovrascrivono.
        if not has_layer(gpkg, 'annotazioni'):
            write_layer(memory_layer('annotazioni', 'Point', c['processing_crs'], [('testo', QVariant.String)]), gpkg, 'annotazioni')
        perimeter = memory_layer('area_lavoro', crs=c['processing_crs'], fields=[('nome', QVariant.String)])
        add_feature(perimeter, geometry, [c['id']])
        # Scrivere il perimetro solo quando cambia: non invalida i vettori a ogni aggiornamento.
        perimeter_file = area / 'elaborati/perimetro.geojson'
        perimeter_signature = digest([c['perimeter_wkt'], c['perimeter_crs'], c['processing_crs']])
        state_path = area / 'elaborati/stato.json'
        state = load_json(state_path) if state_path.exists() else {}
        if state.get('perimeter') != perimeter_signature:
            write_layer(perimeter, gpkg, 'area_lavoro')
            pg = geometry_in(geometry, c['processing_crs'], 'EPSG:4326')
            save_json(perimeter_file, {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'properties': {}, 'geometry': json.loads(pg.asJson())}]})
            state['perimeter'] = perimeter_signature
        dtm = area / 'elaborati/dtm_ritagliato.tif'
        dtm_coverage = area / 'elaborati/dtm_copertura.json'
        slope = area / 'elaborati/pendenza_gradi.tif'
        shade = area / 'elaborati/hillshade.tif'
        resolution = min(s['grid_m'] for s in selected)
        raw_signature = {'sources': [{**s, 'current': self.source_fingerprint(s)} for s in selected],
                         'coverage_validation': 'native-detail-coregistration-v1',
                         'arcgis_sampling': 'native-lerc2-v2' if any(
                             s.get('provider') == 'arcgis_imageserver' for s in selected) else None,
                         'nodata_policy': c.get('dtm_nodata_policy', {'mode': 'strict'}),
                         'geometry': perimeter_signature, 'crs': c['processing_crs'], 'buffer': c['buffer_m'], 'res': resolution}
        previous_report_path = area / 'elaborati/rapporto.json'
        previous_report = load_json(previous_report_path) if previous_report_path.exists() else {}
        dtm_seams = list(previous_report.get('dtm_seams', []))
        def prepare_dtm():
            nonlocal dtm_seams
            buffered = geometry.buffer(c['buffer_m'], 12)
            bb = buffered.boundingBox()
            vrts = [self.cached_tiles(s, buffered, c['processing_crs'], resolution) for s in selected]
            temp = area / 'elaborati/dtm.partial.tif'
            slope_temp = area / 'elaborati/slope.partial.tif'
            shade_temp = area / 'elaborati/hillshade.partial.tif'
            for path in (temp, slope_temp, shade_temp):
                path.unlink(missing_ok=True)
            bounds = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
            provenance = None
            try:
                dtm_seams, provenance = self.compose_dtm_sources(
                    vrts, selected, bounds, c['processing_crs'], resolution, temp)
                self.repair_dtm_seams(temp, resolution)
                buffered_file = area/'elaborati/margine_tecnico.geojson'
                buffered_wgs = geometry_in(buffered, c['processing_crs'], 'EPSG:4326')
                save_json(buffered_file, {'type':'FeatureCollection', 'features':[{'type':'Feature','properties':{},'geometry':json.loads(buffered_wgs.asJson())}]})
                coverage = self.validate_dtm(temp, buffered_file, c.get('dtm_nodata_policy'))
                self.adaptive_terrain_derivatives(
                    temp, provenance, selected, resolution, slope_temp, shade_temp)
                cog_copy(temp, dtm)
                cog_copy(slope_temp, slope)
                cog_copy(shade_temp, shade)
                save_json(dtm_coverage, coverage)
            finally:
                for path in (temp, slope_temp, shade_temp, provenance):
                    if path is not None:
                        Path(path).unlink(missing_ok=True)
        self.stage('dtm', raw_signature, [dtm, dtm_coverage, slope, shade], state, area, prepare_dtm)
        state.pop('pendenza', None)
        state.pop('hillshade', None)
        self.progress(25, 'DTM locale pronto')
        contours_marker = area / 'elaborati/curve.json'
        def contours():
            temporary = area / 'elaborati/curve.partial.gpkg'
            if temporary.exists():
                temporary.unlink()
            ds = ogr.GetDriverByName('GPKG').CreateDataSource(str(temporary))
            srs = osr.SpatialReference()
            srs.SetFromUserInput(c['processing_crs'])
            layer = ds.CreateLayer('curve_10m', srs, ogr.wkbLineString, options=['SPATIAL_INDEX=YES'])
            layer.CreateField(ogr.FieldDefn('ID', ogr.OFTInteger))
            layer.CreateField(ogr.FieldDefn('ELEV', ogr.OFTReal))
            raster = gdal.Open(str(dtm))
            gdal.ContourGenerate(raster.GetRasterBand(1), c['contour_interval_m'], 0, [], 1, -9999, layer, 0, 1, callback=self.gdal_callback)
            raster = None
            layer = None
            ds = None
            simplified = area/'elaborati/curve_display.partial.gpkg'
            if simplified.exists():
                simplified.unlink()
            tolerance = min(1.0, resolution/4)
            gdal.VectorTranslate(str(simplified), str(temporary), options=['-f', 'GPKG', '-simplify', str(tolerance),
                                 '-nln', 'curve_10m', '-lco', 'SPATIAL_INDEX=YES'], callback=self.gdal_callback)
            v = QgsVectorLayer(str(simplified)+'|layername=curve_10m', 'curve_10m', 'ogr')
            write_layer(v, gpkg, 'curve_10m')
            del v
            temporary.unlink()
            simplified.unlink()
            # Recupera pagine libere lasciate dalla sostituzione della tabella delle curve.
            with sqlite3.connect(str(gpkg)) as connection:
                connection.execute('VACUUM')
            save_json(contours_marker, {'dtm': fingerprint(dtm), 'interval': c['contour_interval_m'], 'display_simplification_m': tolerance})
        missing_contours = not has_layer(gpkg, 'curve_10m')
        if missing_contours:
            state.pop('curve', None)
        self.stage('curve', [fingerprint(dtm), c['contour_interval_m'], 'display-simplify-v2'], [contours_marker], state, area, contours)
        self.progress(55, 'Derivati orografici pronti')
        data = load_json(self.archive / 'fonti.json')
        osm_selected = self.select_osm_sources(data, geometry, c)
        if not osm_selected and c.get('osm_required', True):
            raise ValueError('Nessuna sorgente OSM registrata in fonti.json')
        osm = [record for record, _ in osm_selected]
        if osm_selected:
            pbfs = [path for _, path in osm_selected]
            osm_marker = area / 'elaborati/osm.json'
            from .osm_rules import THEMES
            layers_ok = all(has_layer(gpkg, n) for n, _ in THEMES)
            if not layers_ok:
                state.pop('osm', None)
            osm_rules_signature = digest(Path(__file__).with_name('osm_rules.py').read_text())
            config_signature = digest(osm_config_path(self.archive).read_text())
            self.stage('osm', [[fingerprint(pbf) for pbf in pbfs], perimeter_signature,
                               OSM_EXTRACTOR_VERSION, osm_rules_signature, config_signature],
                       [osm_marker], state, area,
                       lambda: self.extract_osm(pbfs, geometry, c, gpkg, osm_marker))
        self.progress(80, 'Vettori locali pronti')
        from .cartography import build_project
        styles = {str(p.name): fingerprint(p) for p in (self.root/'03_styles').glob('auto_*.qml')}
        gpx = [fingerprint(p) for p in sorted((area/'input/tracce_gpx').glob('*.gpx'))]
        project = area / c['project']
        source_report = [{**{k: s[k] for k in ('id', 'title', 'grid_m', 'native_resolution_m',
                                               'verified', 'url', 'license', 'notes')},
                          **({'fallback_url': s['fallback_url']} if s.get('fallback_url') else {})}
                         for s in selected]
        # Non usare mtime del GPKG: le annotazioni possono cambiare senza richiedere una ricomposizione.
        self.stage('progetto', [c, styles, gpx, 'cartografia-v12-testi-z13-15', state['dtm']['signature'], state['curve']['signature'], state.get('osm', {}).get('signature')],
                   [project], state, area, lambda: build_project(self.root, area, c, geometry))
        state['config_signature'] = digest(c)
        save_json(state_path, state)
        self.register_area(config_path, c)
        coverage = load_json(dtm_coverage)
        warnings = ['Fonte altimetrica nazionale eterogenea: dettaglio locale non certificato.'] if any(s['id']=='hrdtm5m' for s in selected) else []
        if coverage['missing_cells']:
            warnings.append(
                f"DTM parziale accettato: {coverage['missing_cells']}/{coverage['total_cells']} celle NoData "
                f"({coverage['missing_percent']:.3f}%).")
        report = {'id': c['id'], 'project': str(project), 'resolution_m': resolution, 'sources': source_report,
                  'source_fingerprints': {s['id']: self.source_fingerprint(s) for s in selected},
                  'seconds_this_run': round(time.monotonic()-started, 3), 'updated': dt.datetime.now(dt.timezone.utc).isoformat(),
                  'peak_process_rss_mb': round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1e6 if sys.platform=='darwin' else 1000), 1) if resource else None,
                  'log': str(self.log_path),
                  'portable': True, 'dtm_coverage': coverage, 'dtm_seams': dtm_seams,
                  'warnings': warnings,
                  'osm': osm, 'stages': state}
        save_json(area / 'elaborati/rapporto.json', report)
        self.progress(100, 'Area pronta')
        return report

    def validate_dtm(self, path, perimeter_file, policy=None):
        policy = policy or {'mode': 'strict'}
        mode = policy.get('mode', 'strict')
        threshold = float(policy.get('max_missing_percent', 0)) if mode == 'allow_partial' else 0.0
        ds = gdal.Open(str(path))
        mask_path = Path(path).parent/'copertura.partial.tif'
        mask = gdal.GetDriverByName('GTiff').Create(str(mask_path), ds.RasterXSize, ds.RasterYSize, 1, gdal.GDT_Byte,
                                                    options=['TILED=YES', 'COMPRESS=DEFLATE'])
        mask.SetGeoTransform(ds.GetGeoTransform())
        mask.SetProjection(ds.GetProjection())
        shapes = ogr.Open(str(perimeter_file))
        # RasterizeLayer non riproietta implicitamente: trasformazione esplicita tramite VectorTranslate.
        shapes_projected = gdal.VectorTranslate('', shapes, format='MEM', dstSRS=ds.GetProjection())
        gdal.RasterizeLayer(mask, [1], shapes_projected.GetLayer(0), burn_values=[1])
        missing = total = impossible = 0
        for y in range(0, ds.RasterYSize, 512):
            for x in range(0, ds.RasterXSize, 512):
                self.cancel()
                h, w = min(512, ds.RasterYSize-y), min(512, ds.RasterXSize-x)
                values = ds.GetRasterBand(1).ReadAsArray(x, y, w, h)
                inside = mask.GetRasterBand(1).ReadAsArray(x, y, w, h) == 1
                total += int(inside.sum())
                missing += int((inside & ((values == -9999) | ~np.isfinite(values))).sum())
                impossible += int((inside & np.isfinite(values) & (values != -9999) &
                                   ((values < -1000) | (values > 9000))).sum())
        ds = mask = shapes_projected = shapes = None
        mask_path.unlink(missing_ok=True)
        if total == 0:
            raise ValueError('DTM senza celle dentro il perimetro. Export bloccato.')
        if impossible:
            raise ValueError(f'DTM con {impossible} quote fuori intervallo plausibile '
                             '(-1000–9000 m). Export bloccato.')
        missing_percent = missing / total * 100
        result = {'total_cells': total, 'missing_cells': missing, 'missing_percent': round(missing_percent, 6),
                  'complete': missing == 0, 'policy': mode,
                  'max_missing_percent': threshold if mode == 'allow_partial' else 0.0}
        if missing and (mode != 'allow_partial' or missing_percent > threshold):
            suffix = f' ({missing_percent:.3f}%, soglia {threshold:g}%)' if mode == 'allow_partial' else ''
            raise ValueError(f'DTM incompleto dentro il perimetro: {missing}/{total} celle mancanti{suffix}. Export bloccato.')
        if missing:
            self.log(f'DTM parziale accettato: {missing}/{total} celle NoData ({missing_percent:.3f}%, soglia {threshold:g}%).')
        return result

    def _cached_osm_extract(self, pbf, geometry, c, bbox, config_path):
        """Crea o riusa il ritaglio grezzo di un singolo pacchetto PBF."""
        pbf = Path(pbf)
        source_name = pbf.name.removesuffix('.osm.pbf')
        cache_dir = self.archive/'osm/estratti'/(
            f'{source_name}_schema-{OSM_EXTRACTOR_VERSION.replace(".", "-")}')
        cache_dir.mkdir(parents=True, exist_ok=True)
        index_path = cache_dir/'catalogo.json'
        index = load_json(index_path) if index_path.exists() else []
        reusable = [r for r in index if QgsRectangle(*r['bbox']).contains(bbox) and (cache_dir/r['file']).exists()]
        if reusable:
            record = min(reusable, key=lambda r: QgsRectangle(*r['bbox']).area())
            temporary = cache_dir/record['file']
            self.log('Estratto OSM comune riutilizzato: '+temporary.name)
        else:
            local = geometry.buffer(c['buffer_m'], 12).boundingBox()
            grid = QgsRectangle(math.floor(local.xMinimum()/10000)*10000, math.floor(local.yMinimum()/10000)*10000,
                                math.ceil(local.xMaximum()/10000)*10000, math.ceil(local.yMaximum()/10000)*10000)
            cover = geometry_in(QgsGeometry.fromRect(grid), c['processing_crs'], 'EPSG:4326').boundingBox()
            bounds = [cover.xMinimum(), cover.yMinimum(), cover.xMaximum(), cover.yMaximum()]
            bbox_name = '_'.join(f'{value:.5f}'.replace('-', 'm').replace('.', 'p') for value in bounds)
            temporary = cache_dir/f'bbox_{bbox_name}.gpkg'
            pending = temporary.with_suffix('.partial.gpkg')
            if pending.exists():
                pending.unlink()
            # Riparazione/ritaglio dopo l'estrazione, per non perdere poligoni OSM invalidi.
            options = ['-f', 'GPKG', '-oo', 'CONFIG_FILE='+str(config_path),
                       '-oo', 'INTERLEAVED_READING=YES', '-spat', *map(str, bounds),
                       '-nlt', 'PROMOTE_TO_MULTI', '-lco', 'SPATIAL_INDEX=YES']
            ds = gdal.VectorTranslate(str(pending), str(pbf), options=options, callback=self.gdal_callback)
            ds = None
            pending.replace(temporary)
            index.append({'file': temporary.name, 'bbox': bounds})
            save_json(index_path, index)
            self.log('Estratto OSM comune creato: '+temporary.name)
        return temporary

    def extract_osm(self, pbfs, geometry, c, gpkg, marker):
        if isinstance(pbfs, (str, Path)):
            pbfs = [Path(pbfs)]
        else:
            pbfs = [Path(pbf) for pbf in pbfs]
        bbox = geometry_in(geometry.buffer(c['buffer_m'], 12), c['processing_crs'], 'EPSG:4326').boundingBox()
        config_path = osm_config_path(self.archive)
        temporaries = [self._cached_osm_extract(pbf, geometry, c, bbox, config_path) for pbf in pbfs]
        raw_counts = {'points': 0, 'lines': 0, 'multipolygons': 0}
        for temporary in temporaries:
            with sqlite3.connect(str(temporary)) as connection:
                for name in raw_counts:
                    raw_counts[name] += connection.execute(
                        f'SELECT count(*) FROM "{name}"').fetchone()[0]
        if raw_counts['multipolygons'] == 0 and raw_counts['points'] + raw_counts['lines'] > 0:
            raise RuntimeError(
                'Estrazione OSM incompleta: poligoni assenti in tutte le fonti. '
                'Verificare la lettura interlacciata del driver OSM.')
        from .osm_rules import TAGS, FIELDS, THEMES, classify
        tags = TAGS
        themes = {n: memory_layer(n, geom, c['processing_crs'], [(tag, QVariant.String) for tag in FIELDS])
                  for n, geom in THEMES}
        context = QgsExpressionContext()
        clip = geometry.buffer(c['buffer_m'], 12)
        hut_seen = {}
        feature_seen = set()
        for temporary in temporaries:
            raw = ogr.Open(str(temporary))
            layer_names = [raw.GetLayerByIndex(i).GetName() for i in range(raw.GetLayerCount())]
            raw = None
            for ln in layer_names:
                if ln not in ('lines', 'points', 'multipolygons'):
                    continue
                layer = QgsVectorLayer(str(temporary)+'|layername='+ln, ln, 'ogr')
                fields = layer.fields().names()
                # Gli indici dei campi cambiano tra punti, linee e poligoni OGR.
                # Le espressioni riusate mantengono gli indici risolti al primo layer.
                expressions = {tag: QgsExpression(f"map_get(hstore_to_map(\"other_tags\"), '{tag}')") for tag in tags}
                context.setFields(layer.fields())
                for expression in expressions.values():
                    expression.prepare(context)
                for f in layer.getFeatures(QgsFeatureRequest().setFilterRect(bbox)):
                    self.cancel()
                    context.setFeature(f)
                    context.setFields(layer.fields())
                    values = {}
                    for tag in tags:
                        value = f[tag] if tag in fields else None
                        if value is None or str(value) in ('NULL', ''):
                            value = expressions[tag].evaluate(context) if 'other_tags' in fields else ''
                        values[tag] = '' if value is None or str(value) == 'NULL' else str(value)
                    targets, category = classify(values, ln)
                    values['label'] = values['name:it'] or values['name']
                    values['categoria'] = category
                    uid = next((str(f[k]) for k in ('osm_id', 'osm_way_id') if k in fields and f[k] is not None and str(f[k]) not in ('NULL', '')), str(f.id()))
                    values['source_uid'] = ln+':'+uid
                    if targets:
                        g = geometry_in(f.geometry(), layer.crs().authid(), c['processing_crs'])
                        if not g.isGeosValid():
                            g = g.makeValid()
                        g = g.intersection(clip)
                        if g.isEmpty():
                            continue
                        for target in targets:
                            unique = (target, values['source_uid'])
                            if unique in feature_seen:
                                continue
                            part = QgsGeometry(g)
                            if ln == 'multipolygons' and themes[target].geometryType() == 0:
                                part = part.pointOnSurface()
                            part.convertGeometryCollectionToSubclass(themes[target].geometryType())
                            if part.isEmpty() or part.type() != themes[target].geometryType():
                                continue  # Contatti puntuali di linee/poligoni sul bordo del ritaglio.
                            part.convertToMultiType()
                            if target == 'rifugi' and values['label']:
                                key = values['label'].strip().casefold()
                                if any(part.distance(other) < 75 for other in hut_seen.get(key, [])):
                                    continue  # Stesso rifugio taggato come punto e come edificio.
                                hut_seen.setdefault(key, []).append(QgsGeometry(part))
                            add_feature(themes[target], part, [values[t] for t in FIELDS])
                            feature_seen.add(unique)
                del layer
        counts = {}
        for name, layer in themes.items():
            write_layer(layer, gpkg, name)
            counts[name] = layer.featureCount()
        if c.get('osm_required', True) and sum(counts.values()) == 0:
            raise ValueError('Estratto OSM vuoto sulla zona. Registrare un PBF con copertura adatta.')
        save_json(marker, {'sources': [fingerprint(pbf) for pbf in pbfs], 'features': counts,
                           'shared_cache': [str(temporary) for temporary in temporaries],
                           'coverage_note': 'Estratto non vuoto; completezza tematica OSM da controllare sulla carta.'})

    def check(self, area):
        from .cartography import check_project
        path = Path(area).resolve()
        if path.is_dir():
            path /= 'area.json'
        c = load_json(path)
        self.validate_config(c)
        selected, _ = self.select_sources(c)
        report_file = path.parent/'elaborati/rapporto.json'
        if report_file.exists():
            previous = load_json(report_file).get('source_fingerprints')
            if previous != {s['id']: self.source_fingerprint(s) for s in selected}:
                raise ValueError('Sorgenti cambiate o rapporto precedente: eseguire Aggiorna area')
        result = check_project(path.parent / c['project'], path.parent)
        if not result['ok']:
            raise ValueError(str(result))
        return result

    def export(self, area, minzoom=None, maxzoom=None, **options):
        from .exporter import export_area
        with self.locked():
            return export_area(self, area, minzoom, maxzoom, **options)
