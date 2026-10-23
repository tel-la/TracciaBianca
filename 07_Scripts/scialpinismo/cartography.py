"""Progetti portabili e stili master: nessuna dipendenza da server o SVG esterni."""
import math
from pathlib import Path

from qgis.core import (
    Qgis, QgsProject, QgsMapLayer, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsPointXY,
    QgsRasterLayer, QgsVectorLayer, QgsRasterShader, QgsColorRampShader,
    QgsSingleBandPseudoColorRenderer, QgsSingleBandGrayRenderer, QgsContrastEnhancement,
    QgsLineSymbol, QgsFillSymbol, QgsMarkerSymbol, QgsRuleBasedRenderer,
    QgsPalLayerSettings, QgsTextFormat, QgsTextBufferSettings, QgsVectorLayerSimpleLabeling,
    QgsMapSettings, QgsRectangle, QgsReferencedRectangle, QgsPointPatternFillSymbolLayer,
)
from qgis.PyQt.QtGui import QColor, QFont, QPainter
from qgis.PyQt.QtCore import QSize

MASTER_STYLES = {
    'Ombreggiatura': 'auto_hillshade.qml',
    'Ombreggiatura — zoom 16+': 'auto_hillshade_dettaglio.qml',
    'Boschi e vegetazione': 'auto_vegetazione.qml',
    'Boschi — tipi ed essenze': 'auto_vegetazione_simboli.qml',
    'Centri abitati — aree OSM': 'auto_insediamenti.qml',
    'Acque e ghiacciai': 'auto_acque.qml',
    'Corsi d’acqua': 'auto_corsi_acqua.qml',
    'Curve ogni 100 m': 'auto_curve_100m.qml',
    'Curve ogni 20 m': 'auto_curve_20m.qml',
    'Curve ogni 10 m': 'auto_curve_10m.qml',
    'Strade': 'auto_strade.qml',
    'Viabilità principale': 'auto_strade_principali.qml',
    'Impianti': 'auto_impianti.qml',
    'Riferimenti e toponimi': 'auto_poi.qml',
    'Riferimenti principali': 'auto_poi_principali.qml',
    'Annotazioni personali': 'auto_annotazioni.qml',
    'Edifici, casolari e ruderi': 'auto_edifici.qml',
    'Case isolate e ruderi puntuali': 'auto_fabbricati_punti.qml',
    'Rifugi e bivacchi — icone e nomi multiscala': 'auto_rifugi.qml',
    'Stazioni degli impianti': 'auto_stazioni.qml',
}
STYLE_CATEGORIES = QgsMapLayer.Symbology | QgsMapLayer.Labeling
CODE_OWNED_STYLES = {
    'Strade', 'Viabilità principale', 'Riferimenti e toponimi',
    'Riferimenti principali', 'Rifugi e bivacchi — icone e nomi multiscala',
}


def layer_master(root, layer, refresh=False):
    name = MASTER_STYLES.get(layer.name())
    if not name:
        return
    path = Path(root)/'03_styles'/name
    if path.exists() and not refresh:
        message, ok = layer.loadNamedStyle(str(path), categories=STYLE_CATEGORIES)
    else:
        message, ok = layer.saveNamedStyle(str(path), categories=STYLE_CATEGORIES)
    if not ok:
        raise RuntimeError(f'Stile {name}: {message}')


def scale_at(z, lat):
    """Scala nominale di rendering QGIS per una tessera Mercator a 96 DPI."""
    point = QgsCoordinateTransform(QgsCoordinateReferenceSystem('EPSG:4326'), QgsCoordinateReferenceSystem('EPSG:3857'), QgsProject.instance()).transform(QgsPointXY(12, lat))
    span = 40075016.68557849 / (2**z)
    settings = QgsMapSettings()
    settings.setDestinationCrs(QgsCoordinateReferenceSystem('EPSG:3857'))
    settings.setOutputSize(QSize(256, 256))
    settings.setOutputDpi(96)
    settings.setExtent(QgsRectangle(point.x()-span/2, point.y()-span/2, point.x()+span/2, point.y()+span/2))
    return settings.scale()


def visible(layer, small=0, large=1e9):
    layer.setScaleBasedVisibility(True)
    layer.setMinimumScale(large)
    layer.setMaximumScale(small)


def vivid_color(color, factor=1.20):
    """Aumenta la saturazione HSV; conserva tinta, luminosità e trasparenza."""
    hue, saturation, value, alpha = color.getHsvF()
    return QColor.fromHsvF(max(0, hue), min(1, saturation*factor), value, alpha)


def contour_symbol(is_major, detail=False):
    color = QColor(99, 88, 75, 185)
    width = 0.19 if is_major else 0.09
    if detail:
        color = QColor(*(round(v*0.75) for v in (99, 88, 75)), 185)
        width *= 1.15
    return QgsLineSymbol.createSimple({'line_color': f'{color.red()},{color.green()},{color.blue()},{color.alpha()}', 'line_width': str(width)})


def slope_style(layer, overview=False):
    shader = QgsColorRampShader()
    if overview:
        shader.setColorRampType(QgsColorRampShader.Discrete)
        items = [(30, QColor(0, 0, 0, 0), '≤30°'), (50, QColor('#f8d523'), '30–50°'),
                 (float('inf'), QColor(104,104,104,191), '>50°')]
    else:
        shader.setColorRampType(QgsColorRampShader.Interpolated)
        items = [(0, QColor('#98d29e'), '0°'), (5, QColor('#98d29e'), '5°'),
                 (10, QColor(152, 210, 158, 0), '10°'), (29.999, QColor(255, 230, 60, 0), '<30°'),
                 (30, QColor('#ffe63c'), '30°'), (35, QColor('#ffb63c'), '35°'),
                 (40, QColor('#f36a32'), '40°'), (45, QColor('#df3030'), '45°'),
                 (50, QColor('#df3030'), '50°'), (50.001, QColor('#686868'), '>50°'), (90, QColor('#686868'), '90°')]
    if not overview:
        items = [(value, vivid_color(color), label) for value, color, label in items]
    shader.setColorRampItemList([QgsColorRampShader.ColorRampItem(value, color, label) for value, color, label in items])
    shader.setMinimumValue(0)
    shader.setMaximumValue(90)
    raster_shader = QgsRasterShader(0, 90)
    raster_shader.setRasterShaderFunction(shader)
    layer.setRenderer(QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, raster_shader))
    layer.setOpacity(0.60 if overview else 0.55)
    layer.setBlendMode(QPainter.CompositionMode_Multiply)


def paths_style(layer):
    rules = QgsRuleBasedRenderer.Rule(None)
    paths = "\"highway\" IN ('path','footway','bridleway','steps')"
    specs = [
        ('Carrareccia', '"highway" = \'track\'', 'solid', '#353535', 0.30),
        ('Sentiero T1–T3', paths + " AND \"sac_scale\" IN ('hiking','mountain_hiking','demanding_mountain_hiking')", 'dash', '#252525', 0.24),
        ('Sentiero T4–T6', paths + " AND \"sac_scale\" IN ('alpine_hiking','demanding_alpine_hiking','difficult_alpine_hiking')", 'dot', '#252525', 0.26),
        ('Classificazione assente o altra', paths + " AND coalesce(\"sac_scale\",'') NOT IN ('hiking','mountain_hiking','demanding_mountain_hiking','alpine_hiking','demanding_alpine_hiking','difficult_alpine_hiking')", 'dash', '#777777', 0.20),
    ]
    for label, expression, style, color, width in specs:
        symbol = QgsLineSymbol.createSimple({'line_color': color, 'line_width': str(width), 'line_style': style, 'capstyle': 'round'})
        rule = QgsRuleBasedRenderer.Rule(symbol)
        rule.setFilterExpression(expression)
        rule.setLabel(label)
        rules.appendChild(rule)
    layer.setRenderer(QgsRuleBasedRenderer(rules))


def labels(layer, expression, size, color='#303030', expression_field=False):
    settings = QgsPalLayerSettings()
    settings.fieldName = expression
    settings.isExpression = expression_field
    fmt = QgsTextFormat()
    fmt.setFont(QFont('Arial', size))
    fmt.setSize(size)
    fmt.setColor(QColor(color))
    buffer = QgsTextBufferSettings()
    buffer.setEnabled(True)
    buffer.setSize(0.7)
    buffer.setColor(QColor('#fffdf5'))
    fmt.setBuffer(buffer)
    settings.setFormat(fmt)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.setLabelsEnabled(True)


def create_styles(root):
    """Crea solo i master mancanti: successive personalizzazioni vengono conservate."""
    root = Path(root)
    folder = root / '03_styles'
    folder.mkdir(exist_ok=True)
    raster = next((root/'##_aree/01_Cortina/elaborati').glob('pendenza_gradi.tif'), None)
    if raster:
        for name, overview in [('auto_pendenza_dettaglio.qml', False), ('auto_pendenza_z15.qml', True)]:
            p = folder/name
            if not p.exists():
                layer = QgsRasterLayer(str(raster), name)
                slope_style(layer, overview)
                layer.saveNamedStyle(str(p))
    p = folder/'auto_percorsi.qml'
    if not p.exists():
        layer = QgsVectorLayer('MultiLineString?crs=EPSG:4326&field=highway:string&field=sac_scale:string', 'percorsi', 'memory')
        paths_style(layer)
        from .readability import path_labels
        path_labels(layer)
        layer.saveNamedStyle(str(p))


def create_template(root):
    root = Path(root)
    p = root/'00_template/scialpinismo_template.qgz'
    if p.exists():
        return
    project = QgsProject()
    project.setCrs(QgsCoordinateReferenceSystem('EPSG:32633'))
    project.setBackgroundColor(QColor('#fffdf5'))
    project.setTitle('Scialpinismo — template; creare la zona con Prepara area')
    project.setFilePathStorage(Qgis.FilePathType.Relative)
    if not project.write(str(p)):
        raise RuntimeError('Template non salvato')


def build_project(root, area, config, geometry):
    root, area = Path(root), Path(area)
    p = QgsProject()
    p.setFileName(str(area/config['project']))
    p.setCrs(QgsCoordinateReferenceSystem(config['processing_crs']))
    p.setFilePathStorage(Qgis.FilePathType.Relative)
    p.setBackgroundColor(QColor('#fffdf5'))
    p.setTitle(config['id'] + ' — carta scialpinistica offline')
    from .engine import geometry_in
    lat = geometry_in(geometry.centroid(), config['processing_crs'], 'EPSG:4326').asPoint().y()
    s1415 = math.sqrt(scale_at(14, lat)*scale_at(15, lat))
    s1516 = math.sqrt(scale_at(15, lat)*scale_at(16, lat))
    s1314 = math.sqrt(scale_at(13, lat)*scale_at(14, lat))
    from qgis.core import QgsExpressionContextUtils
    QgsExpressionContextUtils.setProjectVariable(p, 'scialpinismo_scale_12_13', 2*s1314)
    QgsExpressionContextUtils.setProjectVariable(p, 'scialpinismo_scale_13_14', s1314)
    QgsExpressionContextUtils.setProjectVariable(p, 'scialpinismo_scale_14_15', s1415)
    QgsExpressionContextUtils.setProjectVariable(p, 'scialpinismo_scale_15_16', s1516)
    QgsExpressionContextUtils.setProjectVariable(p, 'scialpinismo_scale_16_17', math.sqrt(scale_at(16,lat)*scale_at(17,lat)))
    group = p.layerTreeRoot().addGroup('Cartografia offline')
    def add(layer):
        if not layer.isValid():
            raise ValueError('Layer non valido: '+layer.source())
        p.addMapLayer(layer, False)
        group.insertLayer(0, layer)
        return layer
    shade = add(QgsRasterLayer(str(area/'elaborati/hillshade.tif'), 'Ombreggiatura'))
    renderer = QgsSingleBandGrayRenderer(shade.dataProvider(), 1)
    contrast = QgsContrastEnhancement(shade.dataProvider().dataType(1))
    contrast.setContrastEnhancementAlgorithm(QgsContrastEnhancement.StretchToMinimumMaximum)
    contrast.setMinimumValue(0)
    contrast.setMaximumValue(255)
    renderer.setContrastEnhancement(contrast)
    shade.setRenderer(renderer)
    shade.setOpacity(0.43)
    visible(shade, s1516, 1e9)
    shade_detail = shade.clone();shade_detail.setName('Ombreggiatura — zoom 16+');add(shade_detail)
    shade_detail.setOpacity(0.30);visible(shade_detail, 0, s1516)
    for name, overview, small, large, style in [
        ('Pendenza — zoom 14–15', True, s1516, s1314, 'auto_pendenza_z15.qml'),
        ('Pendenza — zoom 16+', False, 0, s1516, 'auto_pendenza_dettaglio.qml')]:
        layer = add(QgsRasterLayer(str(area/'elaborati/pendenza_gradi.tif'), name))
        path = root/'03_styles'/style
        if path.exists():
            message, ok = layer.loadNamedStyle(str(path))
            if not ok:
                raise RuntimeError(message)
        else:
            slope_style(layer, overview)
        visible(layer, small, large)
    gpkg = area/'vettori/dati_area.gpkg'
    def vector(table, title):
        return add(QgsVectorLayer(str(gpkg)+'|layername='+table, title, 'ogr'))
    forest = vector('vegetazione', 'Boschi e vegetazione')
    forest.renderer().setSymbol(QgsFillSymbol.createSimple({'color': '197,217,184,90', 'outline_style': 'no'}))
    # Simbolo generico: nessuna essenza dedotta in assenza di classificazione.
    forest_detail = vector('vegetazione', 'Boschi — tipi ed essenze')
    fill = QgsFillSymbol.createSimple({'color': '0,0,0,0', 'outline_style': 'no'})
    pattern = QgsPointPatternFillSymbolLayer()
    pattern.setSubSymbol(QgsMarkerSymbol.createSimple({'name': 'triangle', 'color': '#73936c', 'outline_style': 'no', 'size': '0.65'}))
    pattern.setDistanceX(4)
    pattern.setDistanceY(4)
    fill.appendSymbolLayer(pattern)
    forest_detail.renderer().setSymbol(fill)
    forest_detail.setOpacity(0.45)
    visible(forest_detail, 0, s1516)
    settlements = vector('insediamenti', 'Centri abitati — aree OSM')
    settlements.renderer().setSymbol(QgsFillSymbol.createSimple({
        'color': '211,192,169,72', 'outline_color': '177,150,121,90', 'outline_width': '0.10'}))
    # Quadro d'insieme fino allo zoom 15 incluso; oltre prevalgono le sagome edilizie.
    visible(settlements, s1516, 1e9)
    water = vector('acque', 'Acque e ghiacciai')
    water.renderer().setSymbol(QgsFillSymbol.createSimple({'color': '172,217,232,175', 'outline_color': '#71aabb', 'outline_width': '0.15'}))
    streams = vector('corsi_acqua', 'Corsi d’acqua')
    streams.renderer().setSymbol(QgsLineSymbol.createSimple({'line_color': '#80b8cd', 'line_width': '0.18'}))
    for interval, small, large in [(100, s1415, 1e9), (20, s1516, s1415), (10, 0, s1516)]:
        layer = vector('curve_10m', f'Curve ogni {interval} m')
        rules = QgsRuleBasedRenderer.Rule(None)
        for is_major, width in [(True, 0.19), (False, 0.09)]:
            rule = QgsRuleBasedRenderer.Rule(contour_symbol(is_major, detail=interval==10))
            rule.setFilterExpression(f'round("ELEV") % {interval} = 0 AND round("ELEV") % 100 '+('= 0' if is_major else '<> 0'))
            rule.setLabel('Direttrici' if is_major else 'Intermedie')
            rules.appendChild(rule)
        layer.setRenderer(QgsRuleBasedRenderer(rules))
        labels(layer, 'CASE WHEN round("ELEV") % 100 = 0 THEN to_string(round("ELEV")) END', 7, expression_field=True)
        visible(layer, small, large)
    roads = vector('strade', 'Strade')
    roads.renderer().setSymbol(QgsLineSymbol.createSimple({'line_color': '#a3907c', 'line_width': '0.35'}))
    visible(roads, 0, s1415)
    major_roads = vector('strade', 'Viabilità principale')
    rule = QgsRuleBasedRenderer.Rule(QgsLineSymbol.createSimple({'line_color': '#a3907c', 'line_width': '0.30'}))
    rule.setFilterExpression('"highway" IN (\'motorway\',\'trunk\',\'primary\',\'secondary\',\'tertiary\')')
    root_rule = QgsRuleBasedRenderer.Rule(None)
    root_rule.appendChild(rule)
    major_roads.setRenderer(QgsRuleBasedRenderer(root_rule))
    visible(major_roads, s1415, 1e9)
    paths = vector('percorsi', 'Percorsi — SAC estiva')
    path = root/'03_styles/auto_percorsi.qml'
    if path.exists():
        message, ok = paths.loadNamedStyle(str(path))
        if not ok:
            raise RuntimeError(message)
    else:
        paths_style(paths)
    visible(paths, 0, s1415)
    lifts = vector('impianti', 'Impianti')
    lifts.renderer().setSymbol(QgsLineSymbol.createSimple({'line_color': '#6e6481', 'line_width': '0.23', 'line_style': 'dash'}))
    pois = vector('poi', 'Riferimenti e toponimi')
    pois.renderer().setSymbol(QgsMarkerSymbol.createSimple({'name': 'triangle', 'color': '#905b45', 'outline_color': '#ffffff', 'outline_width': '0.2', 'size': '1.5'}))
    visible(pois, 0, s1415)
    labels(pois, 'coalesce(nullif("name",\'\'), nullif("ele",\'\'))', 8, expression_field=True)
    main_pois = vector('poi', 'Riferimenti principali')
    main_expression = '"natural" IN (\'peak\',\'saddle\') OR "tourism" IN (\'alpine_hut\',\'wilderness_hut\') OR "place" IN (\'town\',\'village\')'
    rule = QgsRuleBasedRenderer.Rule(QgsMarkerSymbol.createSimple({'name': 'triangle', 'color': '#905b45', 'size': '1.5'}))
    rule.setFilterExpression(main_expression)
    root_rule = QgsRuleBasedRenderer.Rule(None)
    root_rule.appendChild(rule)
    main_pois.setRenderer(QgsRuleBasedRenderer(root_rule))
    visible(main_pois, s1415, 1e9)
    labels(main_pois, 'CASE WHEN '+main_expression+' THEN "name" END', 8, expression_field=True)
    annotations = vector('annotazioni', 'Annotazioni personali')
    annotations.renderer().setSymbol(QgsMarkerSymbol.createSimple({'name': 'circle', 'color': '#e8475b', 'size': '1.8'}))
    labels(annotations, 'testo', 9)
    for file in sorted((area/'input/tracce_gpx').glob('*.gpx')):
        for table in ('tracks', 'routes'):
            track = QgsVectorLayer(str(file)+'|layername='+table, file.stem+' — '+table, 'ogr')
            if track.isValid() and track.featureCount():
                add(track)
                track.renderer().setSymbol(QgsLineSymbol.createSimple({'line_color': '#bb2c86', 'line_width': '0.6'}))
    work = QgsVectorLayer(str(gpkg)+'|layername=area_lavoro', 'Perimetro di lavoro', 'ogr')
    p.addMapLayer(work, False)
    node = p.layerTreeRoot().addLayer(work)
    node.setItemVisibilityChecked(False)
    work.renderer().setSymbol(QgsFillSymbol.createSimple({'color': '0,0,0,0', 'outline_color': '#bd3272', 'outline_width': '0.5'}))
    # Layer originali e servizi online non entrano nel progetto generato.
    p.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(geometry.boundingBox(), p.crs()))
    p.setMetadata(p.metadata())
    p.writeEntry('Scialpinismo', 'area_config', '../area.json')
    p.writeEntry('Scialpinismo', 'scale_14_15', str(s1415))
    p.writeEntry('Scialpinismo', 'scale_15_16', str(s1516))
    from .readability import apply_readability
    apply_readability(p, area, s1415, s1516, s1314)
    for name, filename in [('Pendenza — zoom 14–15','auto_pendenza_z15.qml'),
                           ('Pendenza — zoom 16+','auto_pendenza_dettaglio.qml')]:
        path = root/'03_styles'/filename
        if not path.exists():
            next(layer for layer in p.mapLayers().values() if layer.name()==name).saveNamedStyle(str(path))
    for layer in p.mapLayers().values():
        # Questi master sono definiti dal codice e vengono sincronizzati quando
        # cambia la gerarchia tipografica, evitando stili QML futuri incoerenti.
        layer_master(root, layer, refresh=layer.name() in CODE_OWNED_STYLES)
    path_master = root/'03_styles/auto_percorsi.qml'
    paths.saveNamedStyle(str(path_master), categories=STYLE_CATEGORIES) if not path_master.exists() else None
    for title in ('Boschi — tipi ed essenze', 'Boschi e vegetazione'):
        layer = next(l for l in p.mapLayers().values() if l.name()==title)
        node = group.findLayer(layer.id()); copy = node.clone(); group.removeChildNode(node)
        slope_node = group.findLayer(next(l.id() for l in p.mapLayers().values() if l.name()=='Pendenza — zoom 16+'))
        group.insertChildNode(group.children().index(slope_node), copy)
    # Variabili locali ai layer: il rendering Processing non dipende dal progetto attivo.
    for layer in p.mapLayers().values():
        if isinstance(layer, QgsVectorLayer):
            for key, value in [('scialpinismo_scale_12_13',2*s1314), ('scialpinismo_scale_13_14',s1314), ('scialpinismo_scale_14_15',s1415), ('scialpinismo_scale_15_16',s1516),
                               ('scialpinismo_scale_16_17',math.sqrt(scale_at(16,lat)*scale_at(17,lat)))]:
                QgsExpressionContextUtils.setLayerVariable(layer,key,value)
    if not p.write():
        raise RuntimeError('Progetto non salvato')


def check_project(path, area):
    p = QgsProject()
    if not p.read(str(path)):
        return {'ok': False, 'error': 'Progetto non leggibile'}
    invalid, remote, external = [], [], []
    area = Path(area).resolve()
    for layer in p.mapLayers().values():
        if not layer.isValid():
            invalid.append(layer.name())
        elif isinstance(layer, QgsVectorLayer) and layer.featureCount() < 0:
            invalid.append(layer.name()+' (lettura delle geometrie fallita)')
        if layer.providerType() not in ('gdal', 'ogr'):
            remote.append(layer.name())
        else:
            source = Path(layer.source().split('|')[0]).resolve()
            if not source.is_relative_to(area):
                external.append(str(source))
    return {'ok': not (invalid or remote or external), 'layers': len(p.mapLayers()), 'invalid': invalid, 'remote': remote, 'external': external, 'project_bytes': Path(path).stat().st_size}
