"""Grafica v2: gerarchia dei testi, viabilità bordata e riferimenti montani."""
from qgis.core import (
    QgsVectorLayer, QgsLineSymbol, QgsMarkerSymbol, QgsSimpleMarkerSymbolLayer,
    QgsFontMarkerSymbolLayer,
    QgsFillSymbol, QgsRuleBasedRenderer, QgsRuleBasedLabeling, QgsPalLayerSettings,
    QgsTextFormat, QgsTextBufferSettings, QgsVectorLayerSimpleLabeling,
    QgsLinePatternFillSymbolLayer,
    QgsPointPatternFillSymbolLayer, QgsProperty, Qgis,
)
from qgis.PyQt.QtGui import QColor, QFont, QPainter


ROAD_CLASS = '''CASE
 WHEN "highway" IN ('motorway','motorway_link') THEN 'autostrada'
 WHEN "highway" IN ('trunk','trunk_link') THEN 'principale_veloce'
 WHEN "highway" IN ('primary','primary_link') OR regexp_match(coalesce("ref",''),'^(SS|SR)\\s?[0-9]') THEN 'primaria'
 WHEN "highway" IN ('secondary','secondary_link') OR regexp_match(coalesce("ref",''),'^SP\\s?[0-9]') THEN 'secondaria'
 WHEN "highway" IN ('tertiary','tertiary_link') THEN 'terziaria'
 WHEN "highway" IN ('residential','unclassified','living_street','road') THEN 'locale'
 ELSE 'servizio' END'''
ROAD_WIDTHS = [('autostrada', 1.65), ('principale_veloce', 1.42), ('primaria', 1.18),
               ('secondaria', 1.00), ('terziaria', 0.83), ('locale', 0.64), ('servizio', 0.44)]

SAC_GRADES = {'hiking': 'T1', 'mountain_hiking': 'T2', 'demanding_mountain_hiking': 'T3',
              'alpine_hiking': 'T4', 'demanding_alpine_hiking': 'T5', 'difficult_alpine_hiking': 'T6'}
SAC_EXPRESSION = 'CASE ' + ' '.join(f"WHEN \"sac_scale\" = '{key}' THEN '{grade}'" for key, grade in SAC_GRADES.items()) + ' END'
HUT_LABEL_EXPRESSION = (
    'CASE WHEN "categoria" = \'rifugio\' THEN coalesce(nullif("label",\'\'),\'Rifugio\') '
    'WHEN "categoria" IN (\'bivacco\',\'riparo\') '
    'AND @map_scale < @scialpinismo_scale_15_16 THEN nullif("label",\'\') END'
)
HUT_LABEL_COLOR_EXPRESSION = (
    'CASE WHEN "categoria" = \'rifugio\' THEN \'#a1202b\' ELSE \'#ee870b\' END'
)
PARKING_EXPRESSION = '"amenity" = \'parking\''
PEAK_LABEL_EXPRESSION = (
    'CASE WHEN "natural" = \'peak\' '
    'AND @map_scale < @scialpinismo_scale_15_16 '
    'AND nullif(trim("ele"),\'\') IS NOT NULL '
    'THEN concat(coalesce(nullif("label",\'\'),\'\'), '
    'CASE WHEN nullif("label",\'\') IS NOT NULL THEN \' · \' ELSE \'\' END, '
    'regexp_replace(trim("ele"), \'\\\\s*m\\\\s*$\', \'\'), \' m\') '
    'ELSE "label" END'
)


def path_labels(layer):
    # Non convertire T1–T6 nei gradi sci F/PD/AD: sono valutazioni distinte.
    expression = f"concat(coalesce(nullif(\"ref\",''),''), CASE WHEN coalesce(\"ref\",'') <> '' AND ({SAC_EXPRESSION}) IS NOT NULL THEN ' · ' ELSE '' END, coalesce(({SAC_EXPRESSION}),''))"
    label(layer, expression, size=6.48, color='#51432f', bold=True, line=True, priority=6)
    settings = layer.labeling().settings()
    fmt = settings.format(); buffer = fmt.buffer(); buffer.setSize(0.5184); fmt.setBuffer(buffer); settings.setFormat(fmt)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))


def forest_marker(kind):
    symbol = QgsMarkerSymbol.createSimple({'name': 'line', 'size': '1.9', 'color': '#52764b',
                                          'outline_color': '#52764b', 'outline_width': '0.20', 'offset': '0,0.45'})
    for shape, size, offset in ([('triangle', 1.65, '0,-0.35'), ('triangle', 1.25, '0,-0.95')]
                                if kind == 'conifere' else [('circle', 1.85, '0,-0.65')]):
        symbol.appendSymbolLayer(QgsSimpleMarkerSymbolLayer.create({'name': shape, 'size': str(size),
                                     'color': '151,180,139,170', 'outline_color': '#52764b',
                                     'outline_width': '0.18', 'offset': offset}))
    return symbol


def forest_fill(kind):
    fill = QgsFillSymbol.createSimple({'color': '0,0,0,0', 'outline_style': 'no'})
    pattern = QgsPointPatternFillSymbolLayer()
    pattern.setDistanceX(9); pattern.setDistanceY(9)
    marker = forest_marker('conifere' if kind == 'conifere' else 'latifoglie')
    if kind == 'misto':
        marker = forest_marker('conifere')
        broad = forest_marker('latifoglie')
        for i in range(broad.symbolLayerCount()):
            sl = broad.symbolLayer(i).clone()
            offset = sl.offset(); offset.setX(offset.x()+2.2); sl.setOffset(offset)
            marker.appendSymbolLayer(sl)
    if kind == 'ignoto':
        marker = QgsMarkerSymbol.createSimple({'name':'cross2','size':'1.3','color':'#64815c','outline_width':'0.22'})
    scale_marker(marker, 0.65)
    pattern.setSubSymbol(marker);fill.appendSymbolLayer(pattern)
    return fill


def scale_marker(symbol, factor):
    for i in range(symbol.symbolLayerCount()):
        layer = symbol.symbolLayer(i)
        layer.setSize(layer.size()*factor)
        offset = layer.offset(); offset.setX(offset.x()*factor); offset.setY(offset.y()*factor); layer.setOffset(offset)
        layer.setStrokeWidth(layer.strokeWidth()*factor)


def bivouac_symbol():
    symbol = house_symbol()
    for i in (2,3):
        symbol.symbolLayer(i).setColor(QColor('#ee870b'))
    scale_marker(symbol, 0.55)
    return symbol


def refuge_symbol():
    symbol = house_symbol()
    scale_marker(symbol, 0.65)
    return symbol


def parking_symbol(compact=False):
    """Segnale di parcheggio autosufficiente, senza dipendenze SVG esterne."""
    size = 2.15 if compact else 3.05
    symbol = QgsMarkerSymbol.createSimple({
        'name': 'square', 'size': str(size), 'color': '#1769aa',
        'outline_color': '#ffffff', 'outline_width': '0.28' if compact else '0.34',
        'joinstyle': 'round',
    })
    letter = QgsFontMarkerSymbolLayer.create({
        'font': 'Arial', 'font_style': 'Bold', 'chr': 'P',
        'size': str(1.42 if compact else 2.05), 'color': '#ffffff',
    })
    symbol.appendSymbolLayer(letter)
    return symbol


def poi_style(layer, general=False):
    """Toponimi, vette e parcheggi alle soglie Web Mercator del progetto."""
    town = '"place" IN (\'town\',\'village\',\'hamlet\')'
    peak = '"natural" IN (\'peak\',\'saddle\')'
    if general:
        predicate = ('"place" IN (\'town\',\'village\') OR '
                     '("place" = \'hamlet\' AND @map_scale < @scialpinismo_scale_13_14) OR '
                     '("natural" = \'peak\' AND to_real("ele") >= CASE '
                     'WHEN @map_scale > 2 * @scialpinismo_scale_13_14 THEN 3000 ELSE 2600 END)')
        parking_specs = [
            ('Parcheggi — zoom 14',
             f'{PARKING_EXPRESSION} AND @map_scale < @scialpinismo_scale_13_14',
             parking_symbol()),
        ]
    else:
        predicate = 'TRUE'
        parking_specs = [
            ('Parcheggi — zoom 15',
             f'{PARKING_EXPRESSION} AND @map_scale >= @scialpinismo_scale_15_16',
             parking_symbol()),
            ('Parcheggi compatti — zoom 16+',
             f'{PARKING_EXPRESSION} AND @map_scale < @scialpinismo_scale_15_16',
             parking_symbol(compact=True)),
        ]
    layer.setRenderer(rules_renderer([
        ('Vette', f'({predicate}) AND "natural" = \'peak\'', QgsMarkerSymbol.createSimple({'name':'triangle','size':'2.0','color':'#66594d','outline_color':'#ffffff','outline_width':'0.25'})),
        ('Colli', f'({predicate}) AND "natural" = \'saddle\'', QgsMarkerSymbol.createSimple({'name':'triangle','size':'1.6','color':'#66594d','outline_color':'#ffffff','outline_width':'0.2'})),
        *parking_specs,
        ('Centri abitati e riferimenti', f'({predicate}) AND NOT ({peak}) AND NOT ({PARKING_EXPRESSION})', QgsMarkerSymbol.createSimple({'name':'circle','size':'0.7','color':'#605b55','outline_color':'#ffffff','outline_width':'0.15'})),
    ]))
    root = QgsRuleBasedLabeling.Rule(None)
    label_expression = '"label"' if general else PEAK_LABEL_EXPRESSION
    for expression, size, bold, priority in [(town, 12.5, True, 9), (f'NOT ({town})', 11, False, 7)]:
        settings = text_settings(label_expression, size=size, bold=bold, priority=priority)
        settings.dataDefinedProperties().setProperty(
            QgsPalLayerSettings.Size, QgsProperty.fromExpression(zoom_13_15_size(size)))
        rule = QgsRuleBasedLabeling.Rule(settings)
        rule.setFilterExpression(f'({predicate}) AND ({expression}) AND NOT ({PARKING_EXPRESSION})')
        root.appendChild(rule)
    layer.setLabeling(QgsRuleBasedLabeling(root))
    layer.setLabelsEnabled(True)


def contour_labels(layer, interval):
    major = 'round("ELEV") % 100 = 0'
    minor = ('@map_scale < @scialpinismo_scale_13_14 AND round("ELEV") % 50 = 0' if interval == 100
             else 'round("ELEV") % 20 = 0') + ' AND round("ELEV") % 100 <> 0'
    root = QgsRuleBasedLabeling.Rule(None)
    specs = [('Quote direttrici 100 m', major, 10.2, '#4f4235', True, 6, 0.8, 110),
             ('Quote intermedie 50 m' if interval == 100 else 'Quote intermedie 20 m', minor, 7.2, '#796c5c', False, 1, 0.5, 180)]
    if interval == 20:
        # Zoom 15: gerarchia v4, sole direttrici, testo normale più discreto.
        specs = [('Quote direttrici 100 m — zoom 15', major, 9, '#61564a', False, 5, 0.72, 100)]
    threshold = 'scialpinismo_scale_14_15' if interval == 20 else 'scialpinismo_scale_15_16'
    for title, predicate, size, color, bold, priority, halo, repeat in specs:
        settings = text_settings('to_string(round("ELEV"))', size=size, color=color, bold=bold, priority=priority, line=True)
        # Stessa soglia usata dalla visibilità delle curve di dettaglio.
        # Il filtro esplicito funziona anche nelle esportazioni Processing.
        predicate = f'@map_scale < @{threshold} AND ({predicate})'
        settings.placement = QgsPalLayerSettings.Curved
        line_settings = settings.lineSettings()
        line_settings.setPlacementFlags(Qgis.LabelLinePlacementFlag.OnLine)
        settings.setLineSettings(line_settings)
        settings.dist = 0
        settings.repeatDistance = repeat
        fmt=settings.format();buffer=fmt.buffer();buffer.setSize(halo);fmt.setBuffer(buffer);settings.setFormat(fmt)
        rule=QgsRuleBasedLabeling.Rule(settings);rule.setDescription(title);rule.setFilterExpression(predicate);root.appendChild(rule)
    layer.setLabeling(QgsRuleBasedLabeling(root));layer.setLabelsEnabled(True)


def forest_symbols(layer):
    woodland = '("natural" = \'wood\' OR "landuse" = \'forest\')'
    layer.setRenderer(rules_renderer([
        ('Conifere — dato OSM', woodland+' AND "leaf_type" = \'needleleaved\'', forest_fill('conifere')),
        ('Latifoglie — dato OSM', woodland+' AND "leaf_type" = \'broadleaved\'', forest_fill('latifoglie')),
        ('Bosco misto — dato OSM', woodland+' AND "leaf_type" = \'mixed\'', forest_fill('misto')),
        ('Bosco non classificato', woodland+' AND coalesce("leaf_type",\'\') NOT IN (\'needleleaved\',\'broadleaved\',\'mixed\')', forest_fill('ignoto')),
    ]))
    layer.setOpacity(0.8)
    label(layer, 'coalesce(nullif("species:it",\'\'), nullif("species",\'\'), nullif("genus",\'\'))',
          size=9, color='#44633c', italic=True, polygon=True, priority=2)


def text_settings(expression, size=11, color='#252525', bold=False, italic=False, priority=5, line=False, polygon=False):
    s = QgsPalLayerSettings()
    s.fieldName = expression
    s.isExpression = True
    s.priority = priority
    s.dist = 1.3 if not line else 1.0
    if line:
        s.placement = QgsPalLayerSettings.Line
        s.repeatDistance = 100
    elif polygon:
        s.placement = QgsPalLayerSettings.Horizontal
    else:
        s.placement = QgsPalLayerSettings.OrderedPositionsAroundPoint
    fmt = QgsTextFormat()
    font = QFont('Arial')
    font.setBold(bold)
    font.setItalic(italic)
    fmt.setFont(font)
    fmt.setSize(size)
    fmt.setColor(QColor(color))
    buffer = QgsTextBufferSettings()
    buffer.setEnabled(True)
    buffer.setSize(0.72)
    buffer.setColor(QColor('#fffefa'))
    fmt.setBuffer(buffer)
    s.setFormat(fmt)
    return s


def label(layer, expression='"label"', **kwargs):
    layer.setLabeling(QgsVectorLayerSimpleLabeling(text_settings(expression, **kwargs)))
    layer.setLabelsEnabled(True)


def zoom_13_15_size(base):
    """Aumenta del 25% soltanto alle scale degli zoom 13, 14 e 15."""
    return (f'CASE WHEN @map_scale < @scialpinismo_scale_12_13 '
            f'AND @map_scale >= @scialpinismo_scale_15_16 THEN {base * 1.25:g} ELSE {base:g} END')


def rules_renderer(specs, levels=False):
    root = QgsRuleBasedRenderer.Rule(None)
    for name, expression, symbol in specs:
        rule = QgsRuleBasedRenderer.Rule(symbol)
        rule.setLabel(name)
        rule.setFilterExpression(expression)
        root.appendChild(rule)
    r = QgsRuleBasedRenderer(root)
    if levels:
        r.setUsingSymbolLevels(True)
    return r


def cased_line(width, center='#ffffff', border='#252525', edge=0.22, dashed=False):
    outer = QgsLineSymbol.createSimple({'line_color': border, 'line_width': str(width+edge),
                                       'line_style': 'dash' if dashed else 'solid', 'capstyle': 'round', 'joinstyle': 'round'})
    inner = QgsLineSymbol.createSimple({'line_color': center, 'line_width': str(width),
                                       'line_style': 'dash' if dashed else 'solid', 'capstyle': 'round', 'joinstyle': 'round'})
    outer.symbolLayer(0).setRenderingPass(0)
    inner.symbolLayer(0).setRenderingPass(1)
    outer.appendSymbolLayer(inner.takeSymbolLayer(0))
    return outer


def house_symbol():
    # Soltanto primitive vettoriali incorporate: nessun SVG esterno necessario.
    symbol = QgsMarkerSymbol.createSimple({'name': 'square', 'size': '2.95', 'color': '#ffffff',
                                          'outline_style': 'no', 'offset': '0,0.45'})
    for shape, size, color, offset in [
        ('triangle', 3.9, '#ffffff', '0,-0.85'),
        ('square', 2.35, '#c52a35', '0,0.45'),
        ('triangle', 3.25, '#c52a35', '0,-0.85'),
        ('square', 0.60, '#ffffff', '0,0.95'),
    ]:
        symbol.appendSymbolLayer(QgsSimpleMarkerSymbolLayer.create({'name': shape, 'size': str(size),
                                  'color': color, 'outline_style': 'no', 'offset': offset}))
    return symbol


def roads(layer, overview=False):
    specs = []
    for category, width in ROAD_WIDTHS:
        if overview and category not in ('autostrada', 'principale_veloce', 'primaria', 'secondaria', 'terziaria'):
            continue
        width *= 0.70 if overview else 1
        specs.append((category, f"({ROAD_CLASS}) = '{category}'", cased_line(width)))
    layer.setRenderer(rules_renderer(specs, levels=True))
    if overview:
        expression = 'CASE WHEN "highway" IN (\'motorway\',\'trunk\',\'primary\',\'secondary\') THEN nullif("ref",\'\') END'
    else:
        expression = 'CASE WHEN @map_scale < 14000 OR "highway" IN (\'motorway\',\'trunk\',\'primary\',\'secondary\',\'tertiary\') THEN coalesce(nullif("ref",\'\'),nullif("label",\'\')) END'
    label(layer, expression, size=9.8, bold=True, priority=4, line=True)
    settings = layer.labeling().settings()
    settings.dataDefinedProperties().setProperty(
        QgsPalLayerSettings.Size, QgsProperty.fromExpression(zoom_13_15_size(9.8)))
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))


def hydro(areas, streams, detail_scale):
    water = QgsFillSymbol.createSimple({'color': '#bbdeef', 'outline_color': '#3e86ad', 'outline_width': '0.26'})
    glacier = QgsFillSymbol.createSimple({'color': '187,222,239,65', 'outline_color': '#72b4d0', 'outline_width': '0.22'})
    hatch = QgsLinePatternFillSymbolLayer()
    hatch.setLineAngle(135)
    hatch.setDistance(2.8)
    hatch.setSubSymbol(QgsLineSymbol.createSimple({'line_color': '101,170,201,120', 'line_width': '0.10'}))
    glacier.appendSymbolLayer(hatch)
    areas.setRenderer(rules_renderer([
        ('Laghi e specchi d’acqua', '"categoria" <> \'ghiacciaio\'', water),
        ('Ghiacciai', '"categoria" = \'ghiacciaio\'', glacier),
    ]))
    label(areas, f'CASE WHEN @map_scale < {detail_scale} OR $area > 35000 THEN "label" END',
          size=11, color='#24668f', italic=True, priority=8, polygon=True)
    streams.setRenderer(rules_renderer([
        ('Fiumi', '"waterway" = \'river\'', cased_line(0.48, '#418fbd', '#fffefa', 0.30)),
        ('Torrenti', '"waterway" = \'stream\'', cased_line(0.25, '#559fc6', '#fffefa', 0.18)),
        ('Canali e altri corsi', '"waterway" NOT IN (\'river\',\'stream\')', cased_line(0.19, '#73a6bd', '#fffefa', 0.14)),
    ], levels=True))
    label(streams, f'CASE WHEN "waterway" = \'river\' OR @map_scale < {detail_scale} THEN "label" END',
          size=10.2, color='#276b97', italic=True, priority=5, line=True)


def apply_readability(project, area, s1415, s1516, s1314):
    from .cartography import visible
    from .engine import geometry_in
    layers = {layer.name(): layer for layer in project.mapLayers().values()}
    group = project.layerTreeRoot().findGroup('Cartografia offline')

    def add(table, title, position=1):
        layer = QgsVectorLayer(str(area/'vettori/dati_area.gpkg')+'|layername='+table, title, 'ogr')
        if not layer.isValid():
            raise ValueError('Layer necessario non valido: '+table)
        project.addMapLayer(layer, False)
        group.insertLayer(position, layer)
        return layer

    layers['Ombreggiatura'].setOpacity(0.43)
    layers['Ombreggiatura — zoom 16+'].setOpacity(0.30)
    for name in ('Pendenza — zoom 14–15', 'Pendenza — zoom 16+'):
        layers[name].setBlendMode(QPainter.CompositionMode_Multiply)
        layers[name].setOpacity(0.60 if name.endswith('15') else 0.55)
    for interval in (100, 20, 10):
        contour_labels(layers[f'Curve ogni {interval} m'], interval)
    curve_overview=layers['Curve ogni 100 m']
    curve_overview.renderer().rootRule().appendChild(QgsRuleBasedRenderer.Rule(
        QgsLineSymbol.createSimple({'line_color':'99,88,75,110','line_width':'0.07'}),
        filterExp='@map_scale < @scialpinismo_scale_13_14 AND round("ELEV") % 50 = 0 AND round("ELEV") % 100 <> 0',
        label='Intermedie 50 m — zoom 14'))
    roads(layers['Strade'])
    roads(layers['Viabilità principale'], overview=True)
    hydro(layers['Acque e ghiacciai'], layers['Corsi d’acqua'], s1415)
    path_labels(layers['Percorsi — SAC estiva'])
    forest_symbols(layers['Boschi — tipi ed essenze'])
    visible(layers['Boschi — tipi ed essenze'], 0, s1415)
    layers['Boschi e vegetazione'].setRenderer(rules_renderer([
        ('Bosco — velo verde tutti gli zoom', 'TRUE', QgsFillSymbol.createSimple({'color':'197,217,184,60','outline_style':'no'})),
    ]))

    lifts = layers['Impianti']
    lifts.setRenderer(rules_renderer([
        ('Funivie e cabinovie', '"aerialway" IN (\'cable_car\',\'gondola\',\'mixed_lift\')', cased_line(0.36, '#685477', '#fffefa', 0.24)),
        ('Seggiovie e sciovie', '"aerialway" NOT IN (\'cable_car\',\'gondola\',\'mixed_lift\')', cased_line(0.27, '#756481', '#fffefa', 0.20, dashed=True)),
    ], levels=True))
    visible(lifts, 0, s1314)
    label(lifts, 'coalesce(nullif("label",\'\'),nullif("ref",\'\'))', size=10.2, color='#554061', bold=True, priority=7, line=True)

    # Gerarchia dei toponimi: testi più grandi, meno nomi secondari nelle viste generali.
    for title in ('Riferimenti e toponimi', 'Riferimenti principali'):
        layer = layers[title]
        general = title == 'Riferimenti principali'
        poi_style(layer, general=general)

    # Sagome sopra curve e vegetazione, sotto la viabilità: centri abitati leggibili.
    road_node = group.findLayer(layers['Strade'].id())
    buildings = add('edifici', 'Edifici, casolari e ruderi', group.children().index(road_node)+1)
    visible(buildings, 0, s1314)
    coarse = f'(@map_scale < {s1415} OR $area >= 200)'
    buildings.setRenderer(rules_renderer([
        ('Ruderi', f'{coarse} AND "categoria" = \'rudere\'', QgsFillSymbol.createSimple({'color':'220,204,186,145','outline_color':'#876b51','outline_style':'dash','outline_width':'0.20'})),
        ('Edifici rurali', f'{coarse} AND "categoria" = \'fabbricato_rurale\'', QgsFillSymbol.createSimple({'color':'#d4c7b6','outline_color':'#6b5e4e','outline_width':'0.15'})),
        ('Abitazioni e altri edifici', f'{coarse} AND "categoria" NOT IN (\'rudere\',\'fabbricato_rurale\')', QgsFillSymbol.createSimple({'color':'#cbc7c1','outline_color':'#68635c','outline_width':'0.13'})),
    ]))
    label(buildings, f'CASE WHEN @map_scale < {s1516} AND "categoria" NOT IN (\'rifugio\',\'bivacco\',\'riparo\') AND coalesce("tourism",\'\') NOT IN (\'hotel\',\'guest_house\') THEN "label" END',
          size=10, color='#655647', priority=3, polygon=True)

    rural = add('fabbricati_punti', 'Case isolate e ruderi puntuali')
    visible(rural, 0, s1415)
    rural.setRenderer(rules_renderer([
        ('Rudere', '"categoria" = \'rudere\'', QgsMarkerSymbol.createSimple({'name':'cross2','size':'2.2','color':'#876b51','outline_width':'0.3'})),
        ('Fabbricato', '"categoria" <> \'rudere\'', QgsMarkerSymbol.createSimple({'name':'square','size':'1.8','color':'#cfbfaa','outline_color':'#665849','outline_width':'0.22'})),
    ]))
    label(rural, size=10.5, color='#645747', priority=5)

    stations = add('stazioni', 'Stazioni degli impianti')
    visible(stations, 0, s1415)
    stations.renderer().setSymbol(QgsMarkerSymbol.createSimple({'name':'square','size':'1.8','color':'#776485','outline_color':'#ffffff','outline_width':'0.3'}))
    label(stations, size=10.5, color='#554061', priority=7)

    huts = add('rifugi', 'Rifugi e bivacchi — icone e nomi multiscala')
    huts.setRenderer(rules_renderer([
        ('Rifugi — casetta rossa 65% della v3', '"categoria" = \'rifugio\'', refuge_symbol()),
        ('Bivacchi e ripari — nome da zoom 16', '"categoria" IN (\'bivacco\',\'riparo\')', bivouac_symbol()),
    ]))
    label(huts, HUT_LABEL_EXPRESSION,
          size=11.5, color='#a1202b', bold=True, priority=10)
    # Rifugi: metà a z12, +25% a z13–15, dimensione ordinaria da z16.
    settings = huts.labeling().settings()
    settings.dataDefinedProperties().setProperty(QgsPalLayerSettings.Size, QgsProperty.fromExpression(
        'CASE WHEN "categoria" IN (\'bivacco\',\'riparo\') THEN 10 '
        'WHEN @map_scale >= @scialpinismo_scale_12_13 THEN 5.75 '
        'WHEN @map_scale >= @scialpinismo_scale_15_16 THEN 14.375 ELSE 11.5 END'))
    settings.dataDefinedProperties().setProperty(QgsPalLayerSettings.Color, QgsProperty.fromExpression(HUT_LABEL_COLOR_EXPRESSION))
    huts.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    label(layers['Annotazioni personali'], '"testo"', size=12, bold=True, priority=10)
