"""Esportazione multiscala con stima campionata, suddivisione e controllo finale."""
import io
import json
import math
import sqlite3
import datetime as dt
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageChops
from qgis.core import QgsApplication, Qgis, QgsProject, QgsRectangle, QgsGeometry, QgsProcessingContext, QgsProcessingFeedback
from qgis.PyQt.QtGui import QColor

from .engine import load_json, save_json, geometry_in, fingerprint

WORLD = 20037508.342789244


def root_rectangle(bounds, zoom):
    x0,y0,x1,y1 = bounds
    northwest, southeast = rect_tile(x0,y0,zoom), rect_tile(x1,y1,zoom)
    return QgsRectangle(northwest.xMinimum(), southeast.yMinimum(), southeast.xMaximum(), northwest.yMaximum())


def split_roots(bounds):
    """Divisione alla griglia del minimo zoom: nessun antenato condiviso."""
    x0,y0,x1,y1 = bounds
    if x1-x0 >= y1-y0 and x1>x0:
        mid=(x0+x1)//2
        return [(x0,y0,mid,y1),(mid+1,y0,x1,y1)]
    if y1>y0:
        mid=(y0+y1)//2
        return [(x0,y0,x1,mid),(x0,mid+1,x1,y1)]
    raise ValueError('Limite peso troppo basso per una singola radice dello zoom minimo; aumentare il limite o il minimo zoom')


def prune_unowned_tiles(path, roots, minzoom):
    """Rimuove anche tessere extra prodotte dal metatiling del renderer."""
    x0,y0,x1,y1 = roots
    with sqlite3.connect(str(path)) as con:
        levels=[row[0] for row in con.execute('select distinct zoom_level from tiles')]
        for z in levels:
            factor=2**(z-minzoom)
            left,right=x0*factor,(x1+1)*factor-1
            top,bottom=y0*factor,(y1+1)*factor-1
            con.execute('delete from tiles where zoom_level=? and (tile_column<? or tile_column>? or tile_row<? or tile_row>?)',
                        (z,left,right,2**z-1-bottom,2**z-1-top))


def verify_disjoint_packages(paths):
    seen=set();counts={}
    for path in paths:
        with sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True) as con:
            for key in con.execute('select zoom_level,tile_column,tile_row from tiles'):
                if key in seen:
                    raise ValueError(f'Tessera duplicata tra pacchetti: {key}')
                seen.add(key); counts[key[0]]=counts.get(key[0],0)+1
    return {'duplicate_tile_keys':0,'unique_tiles_per_zoom':counts,'method':'disjoint_minzoom_roots'}


def compact_packages(output, packages, max_bytes, area_id, minzoom, maxzoom, cancel=lambda:None):
    """Riunisce fratelli già verificati via SQLite, senza renderizzare o ricomprimere."""
    output=Path(output)
    items={pack['file'].split(f'{area_id}_',1)[1].split('_z',1)[0]:pack for pack in packages}
    changed=True
    while changed:
        changed=False
        for key in sorted(list(items), key=lambda k:(-len(k),k)):
            if not key.endswith('1') or key not in items:
                continue
            sibling=key[:-1]+'2'
            if sibling not in items:
                continue
            a,b=items[key],items[sibling]
            if a['bytes']+b['bytes']>max_bytes*.98:
                continue
            cancel();parent=key[:-1];name=f'{area_id}_{parent}_z{minzoom}-{maxzoom}.mbtiles'
            pending=output/(name+'.merge.partial')
            if pending.exists():pending.unlink()
            destination=sqlite3.connect(pending.resolve().as_uri(),uri=True)
            source=sqlite3.connect((output/a['file']).resolve().as_uri()+'?mode=ro',uri=True)
            try:
                source.backup(destination);source.close()
                destination.execute('attach database ? as other',((output/b['file']).resolve().as_uri()+'?mode=ro',))
                destination.execute('insert into tiles select * from other.tiles')
                roots=[min(a['minzoom_roots'][0],b['minzoom_roots'][0]),min(a['minzoom_roots'][1],b['minzoom_roots'][1]),
                       max(a['minzoom_roots'][2],b['minzoom_roots'][2]),max(a['minzoom_roots'][3],b['minzoom_roots'][3])]
                bounds=[list(map(float,p['metadata']['bounds'].split(','))) for p in (a,b)]
                meta=dict(a['metadata']);meta['name']=f'{area_id} {parent}'
                meta['bounds']=','.join(map(str,(min(v[0] for v in bounds),min(v[1] for v in bounds),max(v[2] for v in bounds),max(v[3] for v in bounds))))
                for field,value in meta.items():
                    destination.execute('delete from metadata where name=?',(field,));destination.execute('insert into metadata values (?,?)',(field,value))
                destination.commit();destination.execute('detach database other')
                assert destination.execute('pragma quick_check').fetchone()[0]=='ok'
                counts=destination.execute('select zoom_level,count(*) from tiles group by zoom_level order by zoom_level').fetchall()
                expected={z:n for z,n in a['zoom_counts']}
                for z,n in b['zoom_counts']:expected[z]=expected.get(z,0)+n
                if dict(counts)!=expected:raise ValueError('Conteggio tessere non coerente dopo la riunione')
            finally:
                source.close();destination.close()
            if pending.stat().st_size>max_bytes:
                pending.unlink();continue
            pending.replace(output/name)
            merged={**a,'file':name,'bytes':(output/name).stat().st_size,'zoom_counts':counts,'metadata':meta,
                    'minzoom_roots':roots,'merge_method':'sqlite_copy_verified_payloads',
                    'estimated_bytes':a['estimated_bytes']+b['estimated_bytes']}
            merged['coverage']={k:a['coverage'].get(k,0)+b['coverage'].get(k,0) for k in ('removed_tiles','masked_boundary_tiles')}
            merged['coverage']['method']='perimeter_alpha_png'
            for old in (a,b):(output/old['file']).unlink()
            del items[key];del items[sibling];items[parent]=merged;changed=True
    return [items[key] for key in sorted(items)]


def archive_obsolete_packages(output, packages, area_id, folder_name=None):
    output=Path(output);current={p['file'] for p in packages}
    obsolete=[p for p in output.glob(f'{area_id}_*_z*-*.mbtiles') if p.name not in current]
    if not obsolete:return None
    destination=output/'archivio'/(folder_name or dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    destination.mkdir(parents=True,exist_ok=True)
    for name in ('catalogo_mbtiles.json','copertura.geojson','LEGGIMI_PRODUZIONE_CORRENTE.txt'):
        if (output/name).exists() and not (destination/name).exists():shutil.copy2(output/name,destination/name)
    for path in obsolete:
        shutil.move(str(path),str(destination/path.name))
        sidecar=Path(str(path)+'.aux.xml')
        if sidecar.exists():shutil.move(str(sidecar),str(destination/sidecar.name))
    return str(destination.relative_to(output))


def tile_bounds(rect, z):
    n = 2**z
    span = 2*WORLD/n
    x0 = max(0, math.floor((rect.xMinimum()+WORLD)/span))
    x1 = min(n-1, math.ceil((rect.xMaximum()+WORLD)/span)-1)
    y0 = max(0, math.floor((WORLD-rect.yMaximum())/span))
    y1 = min(n-1, math.ceil((WORLD-rect.yMinimum())/span)-1)
    return x0, y0, x1, y1


def rect_tile(x, y, z):
    span = 2*WORLD/(2**z)
    return QgsRectangle(-WORLD+x*span, WORLD-(y+1)*span, -WORLD+(x+1)*span, WORLD-y*span)


def tile_coverage_mask(geometry, x, y, z):
    """None = tessera interna; maschera L per bordi, isole e fori, senza dedurre vuoti dal bianco."""
    bounds = rect_tile(x, y, z)
    tile = QgsGeometry.fromRect(bounds)
    if geometry.contains(tile):
        return None
    mask = Image.new('L', (512, 512), 0)
    if not geometry.intersects(tile):
        return mask.resize((256, 256))
    part = geometry.intersection(tile)
    part.convertToMultiType()
    scale = 512 / bounds.width()
    for polygon in part.asMultiPolygon():
        piece = Image.new('L', (512, 512), 0)
        draw = ImageDraw.Draw(piece)
        for i, ring in enumerate(polygon):
            points = [((p.x()-bounds.xMinimum())*scale, (bounds.yMaximum()-p.y())*scale) for p in ring]
            if len(points) >= 3:
                draw.polygon(points, fill=255 if i == 0 else 0)
        mask = ImageChops.lighter(mask, piece)
    return mask.resize((256, 256), Image.Resampling.LANCZOS)


def clip_mbtiles(path, geometry, cancel=lambda: None):
    """Modifica solo le tessere di bordo PNG; elimina quelle interamente esterne."""
    con = sqlite3.connect(str(path))
    removed = masked = 0
    try:
        cursor = con.execute('select zoom_level,tile_column,tile_row from tiles')
        while True:
            rows = cursor.fetchmany(128)
            if not rows:
                break
            for z, x, tms_y in rows:
                cancel()
                mask = tile_coverage_mask(geometry, x, 2**z-1-tms_y, z)
                if mask is None:
                    continue
                key = (z, x, tms_y)
                if mask.getbbox() is None:
                    con.execute('delete from tiles where zoom_level=? and tile_column=? and tile_row=?', key)
                    removed += 1
                    continue
                blob = con.execute('select tile_data from tiles where zoom_level=? and tile_column=? and tile_row=?', key).fetchone()[0]
                with Image.open(io.BytesIO(blob)) as source:
                    if source.format != 'PNG':
                        raise ValueError('Il ritaglio trasparente richiede PNG')
                    image = source.convert('RGBA')
                    image.putalpha(ImageChops.multiply(image.getchannel('A'), mask))
                    data = io.BytesIO(); image.save(data, format='PNG')
                con.execute('update tiles set tile_data=? where zoom_level=? and tile_column=? and tile_row=?', (data.getvalue(), *key))
                masked += 1
        con.commit()
        con.execute('VACUUM')
    finally:
        con.close()
    return {'removed_tiles': removed, 'masked_boundary_tiles': masked, 'method': 'perimeter_alpha_png'}


def inspect_mbtiles(path, minzoom, maxzoom, max_bytes=None):
    path = Path(path)
    connection = sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)
    try:
        if connection.execute('pragma quick_check').fetchone()[0] != 'ok':
            raise ValueError('Database MBTiles non integro')
        meta = dict(connection.execute('select name,value from metadata'))
        expected = {'jpg': 'JPEG', 'jpeg': 'JPEG', 'png': 'PNG'}.get(meta.get('format'))
        if expected is None:
            raise ValueError('Metadato formato PNG/JPEG mancante')
        counts = connection.execute('select zoom_level,count(*) from tiles group by zoom_level order by zoom_level').fetchall()
        if [z for z, _ in counts] != list(range(minzoom, maxzoom+1)):
            raise ValueError('Livelli zoom mancanti')
        for z, x, row, data in connection.execute('select zoom_level,tile_column,tile_row,tile_data from tiles'):
            if not 0 <= x < 2**z or not 0 <= row < 2**z:
                raise ValueError('Indici tessera non validi')
            with Image.open(io.BytesIO(data)) as img:
                if img.size != (256, 256) or img.format != expected:
                    raise ValueError('Formato o dimensioni tessera inattesi')
                img.load()
        size = path.stat().st_size
        if max_bytes and size > max_bytes:
            raise ValueError('Pacchetto oltre il limite di peso')
        return {'file': path.name, 'bytes': size, 'zoom_counts': counts, 'metadata': meta, 'all_images_decoded': True}
    finally:
        connection.close()



def missing_tile_keys(paths, geometry, minzoom, maxzoom, cancel=lambda: None):
    present = set()
    for path in paths:
        with sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro', uri=True) as con:
            present.update(con.execute('select zoom_level,tile_column,tile_row from tiles'))
    for z in range(minzoom,maxzoom+1):
        x0,y0,x1,y1 = tile_bounds(geometry.boundingBox(),z)
        for x in range(x0,x1+1):
            cancel()
            for y in range(y0,y1+1):
                key=(z,x,2**z-1-y)
                if key in present: continue
                mask=tile_coverage_mask(geometry,x,y,z)
                if mask is None or mask.getbbox(): yield key


def repair_missing_tiles(path, geometry, minzoom, maxzoom, render, cancel=lambda: None, clipping=True):
    """Un solo tentativo mirato dal progetto originale, mai riempimenti sintetici."""
    import itertools
    missing = list(itertools.islice(missing_tile_keys([path], geometry, minzoom, maxzoom, cancel), 17))
    if len(missing) > 16:
        raise ValueError('Copertura incompleta: oltre 16 tessere mancanti; ripetere la produzione')
    temporary = Path(str(path)+'.repair.mbtiles')
    try:
        for z,x,row in missing:
            cancel()
            rectangle=rect_tile(x,2**z-1-row,z); rectangle.scale(0.999999)
            render(rectangle,temporary,z,z)
            if clipping: clip_mbtiles(temporary,geometry,cancel)
            with sqlite3.connect(str(temporary)) as source:
                data=source.execute('select tile_data from tiles where zoom_level=? and tile_column=? and tile_row=?',(z,x,row)).fetchone()
            if data is None: raise ValueError(f'Recupero tessera fallito: {(z,x,row)}')
            with sqlite3.connect(str(path)) as destination:
                destination.execute('insert into tiles(zoom_level,tile_column,tile_row,tile_data) values (?,?,?,?)',(z,x,row,data[0]))
            temporary.unlink()
    finally:
        if temporary.exists(): temporary.unlink()
    verify_tile_coverage([path],geometry,minzoom,maxzoom,cancel)
    return missing


def verify_tile_coverage(paths, geometry, minzoom, maxzoom, cancel=lambda:None):
    """Confronta le tessere presenti con il perimetro, non con il solo conteggio."""
    missing=next(missing_tile_keys(paths,geometry,minzoom,maxzoom,cancel),None)
    if missing is not None: raise ValueError(f'Tessera mancante nella copertura: {missing}')
    count=0
    for path in paths:
        with sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True) as con:
            count+=con.execute('select count(*) from tiles').fetchone()[0]
    return {'expected_coverage_checked':True,'present_tiles':count}

def export_area(workflow, area, minzoom=None, maxzoom=None, maxbytes=None, mode=None, warning_bytes=None):
    import processing
    config_path = Path(area).resolve()
    if config_path.is_dir():
        config_path /= 'area.json'
    area = config_path.parent
    c = load_json(config_path)
    if minzoom is not None:
        c['export']['minzoom'] = minzoom
    if maxzoom is not None:
        c['export']['maxzoom'] = maxzoom
    if mode is not None:
        c['export']['mode'] = mode
    else:
        c['export'].setdefault('mode', 'single')
    if c['export']['mode'] == 'split':
        if maxbytes is not None:
            c['export']['max_bytes'] = maxbytes
    else:
        # Un vecchio max_bytes nel JSON non deve riattivare o simulare la suddivisione.
        c['export'].pop('max_bytes', None)
    if warning_bytes is not None:
        c['export']['warning_bytes'] = warning_bytes
    workflow.validate_config(c)
    workflow.select_sources(c)
    workflow.check(area)
    # L'esportazione deve usare risultati coerenti con la configurazione corrente.
    from .engine import digest, VERSION
    state = load_json(area/'elaborati/stato.json')
    report = load_json(area/'elaborati/rapporto.json')
    original = load_json(config_path)
    if original['perimeter_wkt'] != c['perimeter_wkt'] or report['id'] != c['id']:
        raise ValueError('Aggiornare prima il progetto')
    if state.get('config_signature') != digest(original):
        raise ValueError('Configurazione modificata: eseguire Aggiorna area prima dell’export')
    p = QgsProject()
    project_snapshot = fingerprint(area/c['project'])
    if not p.read(str(area/c['project'])):
        raise ValueError('Progetto non leggibile')
    if not p.crs().isValid():
        raise ValueError('CRS del progetto non valido: correggere prima dell’esportazione')
    context = QgsProcessingContext()
    context.setProject(p)
    context.setMaximumThreads(2)
    geometry = geometry_in(QgsGeometry.fromWkt(c['perimeter_wkt']), c['perimeter_crs'], 'EPSG:3857')
    rect = geometry.boundingBox()
    e = c['export']
    clipping = e.get('clip_to_perimeter', True)
    tile_format = e.get('tile_format', 'png' if clipping else 'jpg')
    import time
    from .atlas import sha256_file, slug
    started = time.monotonic()
    edition_base = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    edition = edition_base
    sequence = 2
    while (area/'output/mbtiles/edizioni'/edition).exists() or (area/'output/mbtiles'/('.staging-' + edition)).exists():
        edition = edition_base + f'-{sequence:02d}'
        sequence += 1
    base_output = area/'output/mbtiles'
    if 'atlas' in c:
        buffered = geometry_in(QgsGeometry.fromWkt(c['perimeter_wkt']), c['perimeter_crs'], c['processing_crs']).buffer(c['buffer_m'], 12)
        check_geometry = geometry_in(buffered, c['processing_crs'], 'EPSG:4326')
        check_file = area/'elaborati/margine_tecnico.geojson'
        save_json(check_file, {'type':'FeatureCollection','features':[{'type':'Feature','properties':{},'geometry':json.loads(check_geometry.asJson())}]})
        dtm_coverage = workflow.validate_dtm(
            area/'elaborati/dtm_ritagliato.tif', check_file, c.get('dtm_nodata_policy'))
    else:
        dtm_coverage = report.get('dtm_coverage', {'complete': True, 'missing_cells': 0, 'missing_percent': 0.0})
    output = base_output/('.staging-' + edition)
    output.mkdir(parents=True, exist_ok=False)
    split = e.get('mode', 'single') == 'split'
    limit = e['max_bytes'] if split else None
    package_id = c['id']
    if 'atlas' in c:
        package_id += '_' + slug(c['atlas']['display_name']) + '_' + edition
    samples = area/'elaborati/export_campioni'
    samples.mkdir(exist_ok=True)
    logs = []
    peak_working_bytes = [0]
    last_space_check = [0.0]
    def observe_space(*args):
        now = time.monotonic()
        if now-last_space_check[0] < 1: return
        last_space_check[0] = now
        total = 0
        for directory in (output, samples, workflow.root/'.qgis_runtime/tmp'):
            if not directory.exists(): continue
            for path in directory.rglob('*'):
                try:
                    if path.is_file(): total += path.stat().st_size
                except FileNotFoundError: pass
        peak_working_bytes[0] = max(peak_working_bytes[0], total)
    def render(rectangle, path, lo, hi):
        workflow.cancel()
        if path.exists():
            path.unlink()
        ext = f'{rectangle.xMinimum()},{rectangle.xMaximum()},{rectangle.yMinimum()},{rectangle.yMaximum()} [EPSG:3857]'
        from osgeo import gdal
        failures = []
        render_feedback = workflow.feedback or QgsProcessingFeedback()
        render_feedback.progressChanged.connect(observe_space)
        def capture_error(error_class, error_number, message):
            if error_class >= gdal.CE_Failure:
                failures.append(message); render_feedback.cancel()
        def capture_message(message, tag, level):
            if level == Qgis.Critical or 'unable to open database' in message.lower():
                failures.append(message); render_feedback.cancel()
        log = QgsApplication.messageLog()
        log.messageReceived.connect(capture_message)
        gdal.PushErrorHandler(capture_error)
        try:
            processing.run('native:tilesxyzmbtiles', {'EXTENT': ext, 'ZOOM_MIN': lo, 'ZOOM_MAX': hi,
                           'DPI': 96, 'BACKGROUND_COLOR': QColor('#fffdf5'), 'ANTIALIAS': True,
                           'TILE_FORMAT': 0 if tile_format == 'png' else 1, 'QUALITY': e['jpeg_quality'], 'METATILESIZE': 1 if path.name.endswith('.repair.mbtiles') else e['metatile'],
                           'OUTPUT_FILE': str(path)}, context=context, feedback=render_feedback)
        finally:
            gdal.PopErrorHandler()
            log.messageReceived.disconnect(capture_message)
            render_feedback.progressChanged.disconnect(observe_space)
            observe_space()
        if failures:
            raise RuntimeError('Rendering incompleto: ' + '; '.join(dict.fromkeys(failures)))
        workflow.cancel()
    # Campioni distribuiti, sempre renderizzati dal progetto alla scala effettiva.
    means = {}
    for z in range(e['minzoom'], e['maxzoom']+1):
        workflow.progress(2+(z-e['minzoom'])*3, f'Stima peso — zoom {z}')
        x0, y0, x1, y1 = tile_bounds(rect, z)
        probes = sorted(set([(x0, y0), ((x0+x1)//2, (y0+y1)//2), (x1, y1)]))
        sizes = []
        for i, (x, y) in enumerate(probes):
            path = samples/f'z{z}_{i}.mbtiles'
            sample = rect_tile(x, y, z)
            sample.scale(0.999999)  # Evita di includere tessere confinanti per arrotondamento.
            render(sample, path, z, z)
            con = sqlite3.connect(str(path))
            sizes.extend(row[0] for row in con.execute('select length(tile_data) from tiles'))
            con.close()
        means[z] = max(sum(sizes)/max(1, len(sizes)), 1024)
    def estimate(roots):
        count=(roots[2]-roots[0]+1)*(roots[3]-roots[1]+1)
        return int(65536+1.3*sum(count*4**(z-e['minzoom'])*(means[z]+100) for z in range(e['minzoom'],e['maxzoom']+1)))
    def package(roots, key, depth=0):
        r=root_rectangle(roots,e['minzoom'])
        if depth > 20:
            raise ValueError('Troppe suddivisioni: verificare il limite di peso')
        if geometry.intersection(QgsGeometry.fromRect(r)).area() <= 0:
            return
        if split and estimate(roots) > e['max_bytes']*0.90:
            for i, part in enumerate(split_roots(roots)):
                package(part, key+str(i+1), depth+1)
            return
        workflow.log(f'Export pacchetto {key}, stima {estimate(roots)/1e6:.1f} MB')
        name = f'{package_id}_{key}_z{e["minzoom"]}-{e["maxzoom"]}.mbtiles'
        pending = output/(name+'.partial')
        render_extent=QgsRectangle(max(r.xMinimum(),rect.xMinimum()), max(r.yMinimum(),rect.yMinimum()), min(r.xMaximum(),rect.xMaximum()), min(r.yMaximum(),rect.yMaximum()))
        render_extent.scale(0.999999999)
        render(render_extent, pending, e['minzoom'], e['maxzoom'])
        if fingerprint(area/c['project']) != project_snapshot:
            raise ValueError('Progetto modificato durante l’export: ripetere la produzione')
        prune_unowned_tiles(pending,roots,e['minzoom'])
        coverage = clip_mbtiles(pending, geometry, workflow.cancel) if clipping else {'method': 'rectangle_jpeg'}
        if split and pending.stat().st_size > e['max_bytes']:
            pending.unlink()
            for i, part in enumerate(split_roots(roots)):
                package(part, key+str(i+1), depth+1)
            return
        # Dichiarare il perimetro utile, non le tessere arrotondate oltre l’area.
        useful = geometry.intersection(QgsGeometry.fromRect(r))
        bb = geometry_in(useful, 'EPSG:3857', 'EPSG:4326').boundingBox()
        metadata = {'name': f'{c["id"]} {c.get("atlas", {}).get("display_name", "")} {edition} {key}', 'format': tile_format, 'minzoom': str(e['minzoom']), 'maxzoom': str(e['maxzoom']),
                    'bounds': ','.join(str(v) for v in (bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum())),
                    'type': 'baselayer', 'version': '1.3',
                    'description': f"Carta del terreno; zoom massimo {e['maxzoom']} renderizzato dal progetto, senza aumento del dettaglio altimetrico della fonte. Pendenza in gradi; SAC escursionistica estiva. Risoluzione nel catalogo.",
                    'attribution': '© OpenStreetMap contributors; ' + '; '.join(s['title']+' — '+s['url'] for s in report['sources'])}
        connection = sqlite3.connect(str(pending))
        for k, v in metadata.items():
            connection.execute('delete from metadata where name=?', (k,))
            connection.execute('insert into metadata(name,value) values (?,?)', (k, v))
        connection.commit()
        connection.close()
        repaired = repair_missing_tiles(pending, useful, e['minzoom'], e['maxzoom'], render, workflow.cancel, clipping)
        if fingerprint(area/c['project']) != project_snapshot:
            raise ValueError('Progetto modificato durante il recupero tessere')
        result = inspect_mbtiles(pending, e['minzoom'], e['maxzoom'], limit)
        result['repaired_tiles'] = repaired
        final = output/name
        pending.replace(final)
        result['file'] = name
        result['estimated_bytes'] = estimate(roots)
        result['coverage'] = coverage
        result['minzoom_roots'] = roots
        logs.append(result)
    package(tile_bounds(rect,e['minzoom']), '01')
    if split and e.get('compact_packages', True):
        logs=compact_packages(output,logs,e['max_bytes'],package_id,e['minzoom'],e['maxzoom'],workflow.cancel)
    partition=verify_disjoint_packages([output/pack['file'] for pack in logs])
    partition.update(verify_tile_coverage([output/pack['file'] for pack in logs], geometry, e['minzoom'], e['maxzoom'], workflow.cancel))
    catalog = {'area': c['id'], 'workflow_version': VERSION, 'project': fingerprint(area/c['project']),
               'settings': e, 'sources': report['sources'], 'osm': report['osm'], 'packages': logs, 'partition':partition}
    catalog.update(edition=edition, technical_validation='passed', elapsed_seconds=time.monotonic()-started,
                   publication_status='release_ready', atlas=c.get('atlas'))
    for pack in logs:
        pack['sha256'] = sha256_file(output/pack['file'])
    catalog['dtm_coverage'] = dtm_coverage
    catalog['warnings'] = [p['file'] + ': supera soglia avviso' for p in logs if p['bytes'] > e.get('warning_bytes', 2000000000)]
    if dtm_coverage.get('missing_cells'):
        catalog['warnings'].append(
            f"DTM parziale: {dtm_coverage['missing_cells']}/{dtm_coverage['total_cells']} celle NoData "
            f"({dtm_coverage['missing_percent']:.3f}%).")
    for message in catalog['warnings']: workflow.log(message)
    observe_space()
    catalog['peak_working_bytes_sampled'] = peak_working_bytes[0]
    catalog['staging_bytes'] = sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
    outline = geometry_in(geometry, 'EPSG:3857', 'EPSG:4326')
    coverage_label = ('perimetro con DTM completo' if dtm_coverage.get('complete', True) else
                      f"perimetro con DTM parziale ({dtm_coverage['missing_percent']:.3f}% NoData)")
    save_json(output/'copertura.geojson', {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'properties': {'area': c['id'], 'coverage': coverage_label}, 'geometry': json.loads(outline.asJson())}]})
    catalog['coverage_file'] = 'copertura.geojson'
    save_json(output/'catalogo_mbtiles.json', catalog)
    listing = ['PRODUZIONE CORRENTE', '===================',
               'Copiare tutti i pacchetti elencati; i file precedenti non elencati sono storici.',
               f"Formato: {tile_format.upper()}, zoom {e['minzoom']}–{e['maxzoom']}.", '']
    listing.extend(f"{pack['file']} — {pack['bytes']/1e6:.2f} MB" for pack in logs)
    listing.extend(['', 'Contorno: copertura.geojson.', 'Dettagli e attribuzioni: catalogo_mbtiles.json.',
                    'Export tecnicamente validato e pronto per una Release.'])
    (output/'LEGGIMI_PRODUZIONE_CORRENTE.txt').write_text('\n'.join(listing)+'\n', encoding='utf-8')
    # I campioni sono ricreabili; eliminare solo dopo una produzione completata.
    for f in samples.glob('*.mbtiles'):
        f.unlink()
    # Commit dell'edizione: il catalogo corrente cambia solo dopo tutti i controlli.
    editions = base_output/'edizioni'
    editions.mkdir(exist_ok=True)
    destination = editions/edition
    output.rename(destination)
    for pack in catalog['packages']:
        pack['file'] = str(Path('edizioni')/edition/pack['file'])
    catalog['coverage_file'] = str(Path('edizioni')/edition/'copertura.geojson')
    save_json(base_output/'catalogo_mbtiles.json', catalog)
    save_json(base_output/'copertura.geojson', load_json(destination/'copertura.geojson'))
    (base_output/'LEGGIMI_PRODUZIONE_CORRENTE.txt').write_text('PRODUZIONE CORRENTE\nCatalogo autorevole: catalogo_mbtiles.json\nEdizione: '+edition+'\n'+ '\n'.join(p['file'] for p in catalog['packages'])+'\nExport tecnicamente validato e pronto per una Release.\n', encoding='utf-8')
    if 'atlas' in c:
        from .atlas import record_export
        catalog['atlas_registry'] = record_export(workflow, c['id'], catalog)
        save_json(base_output/'catalogo_mbtiles.json', catalog)
    workflow.progress(100, 'MBTiles verificati e pronti per una Release')
    return catalog
