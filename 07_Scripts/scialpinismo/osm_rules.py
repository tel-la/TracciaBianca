"""Classificazione cartografica esplicita; non deduce edifici o nomi assenti in OSM."""
TAGS = [
    'name', 'name:it', 'ref', 'highway', 'sac_scale', 'natural', 'waterway', 'water',
    'landuse', 'aerialway', 'amenity', 'tourism', 'place', 'ele', 'leaf_type',
    'species', 'species:it', 'genus', 'leaf_cycle', 'surface', 'tracktype', 'building', 'building:part', 'historic', 'ruins',
    'abandoned:building', 'disused:building', 'shelter_type', 'bridge', 'tunnel',
]
FIELDS = TAGS + ['label', 'categoria', 'source_uid']
THEMES = [
    ('percorsi', 'MultiLineString'), ('strade', 'MultiLineString'), ('acque', 'MultiPolygon'),
    ('corsi_acqua', 'MultiLineString'), ('vegetazione', 'MultiPolygon'),
    ('insediamenti', 'MultiPolygon'), ('impianti', 'MultiLineString'),
    ('poi', 'MultiPoint'), ('edifici', 'MultiPolygon'),
    ('rifugi', 'MultiPoint'), ('fabbricati_punti', 'MultiPoint'), ('stazioni', 'MultiPoint'),
]


def is_ruin(t):
    return (t.get('historic') == 'ruins' or t.get('ruins', '') not in ('', 'no') or
            t.get('building') in ('ruins', 'collapsed'))


def is_hut(t):
    name = (t.get('name:it') or t.get('name') or '').casefold()
    return (t.get('tourism') in ('alpine_hut', 'wilderness_hut') or
            (t.get('amenity') == 'shelter' and
             (t.get('shelter_type') in ('basic_hut', 'weather_shelter', 'lean_to') or
              any(word in name for word in ('bivacco', 'rifugio')))))


def classify(t, kind):
    """kind: points, lines o multipolygons. Un rifugio poligonale produce anche l'icona."""
    targets = []
    category = ''
    building = (t.get('building', '') not in ('', 'no') or
                t.get('building:part', '') not in ('', 'no') or
                bool(t.get('abandoned:building')) or bool(t.get('disused:building')))
    if kind == 'lines':
        if t.get('highway') in ('path', 'footway', 'bridleway', 'track', 'steps'):
            targets.append('percorsi')
        elif t.get('highway'):
            targets.append('strade')
        if t.get('waterway'):
            targets.append('corsi_acqua')
        if t.get('aerialway') and t['aerialway'] not in ('pylon', 'station', 'no'):
            targets.append('impianti')
    elif kind == 'multipolygons':
        if t.get('natural') in ('water', 'glacier') or t.get('landuse') in ('reservoir', 'basin') or t.get('waterway') == 'riverbank' or t.get('water') in ('lake', 'river', 'reservoir', 'pond'):
            targets.append('acque')
        if t.get('natural') in ('wood', 'scrub') or t.get('landuse') == 'forest':
            targets.append('vegetazione')
        if t.get('landuse') in ('residential', 'commercial', 'retail'):
            targets.append('insediamenti')
        if building or is_ruin(t):
            targets.append('edifici')
        if is_hut(t):
            targets.append('rifugi')
        if t.get('aerialway') == 'station':
            targets.append('stazioni')
    elif kind == 'points':
        if is_hut(t):
            targets.append('rifugi')
        elif building or is_ruin(t) or t.get('place') == 'isolated_dwelling':
            targets.append('fabbricati_punti')
        if t.get('aerialway') == 'station':
            targets.append('stazioni')
        if not is_hut(t) and (t.get('natural') in ('peak', 'saddle', 'spring') or
                             t.get('amenity') in ('parking', 'drinking_water') or
                             t.get('tourism') == 'viewpoint' or
                             t.get('place') in ('town', 'village', 'hamlet', 'locality')):
            targets.append('poi')
    if is_ruin(t):
        category = 'rudere'
    elif is_hut(t):
        category = ('rifugio' if t.get('tourism') == 'alpine_hut' else
                    'riparo' if t.get('shelter_type') in ('weather_shelter','lean_to') else 'bivacco')
    elif t.get('building') in ('cabin', 'hut', 'farm', 'farm_auxiliary', 'barn', 'shed') or t.get('place') == 'isolated_dwelling':
        category = 'fabbricato_rurale'
    elif building:
        category = 'edificio'
    if t.get('natural') == 'glacier':
        category = 'ghiacciaio'
    elif 'acque' in targets:
        category = 'fiume' if t.get('water') == 'river' or t.get('waterway') == 'riverbank' else 'lago'
    return targets, category
