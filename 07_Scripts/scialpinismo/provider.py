"""Strumenti Processing per aree e atlante, disponibili anche senza installazione nel profilo utente."""
from pathlib import Path
import os

from qgis.core import (
    Qgis, QgsApplication, QgsProcessingProvider, QgsProcessingAlgorithm,
    QgsProcessingParameterString, QgsProcessingParameterExtent, QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFile, QgsProcessingParameterCrs, QgsProcessingParameterEnum,
    QgsProcessingOutputFile, QgsProcessingException, QgsProcessing, QgsGeometry,
    QgsCoordinateReferenceSystem, QgsProcessingParameterNumber, QgsProcessingParameterBoolean,
)
from qgis.PyQt.QtWidgets import QAction

ROOT = Path(os.environ.get('SCIALPINISMO_ROOT', str(Path(__file__).resolve().parents[2]))).resolve()


class AreaAlgorithm(QgsProcessingAlgorithm):
    def __init__(self, mode='prepare'):
        super().__init__()
        self.mode = mode

    def name(self):
        return self.mode

    def displayName(self):
        return {'prepare': '1 · Prepara area', 'update': '2 · Aggiorna area', 'export': '3 · Esporta offline'}[self.mode]

    def group(self):
        return 'Aree offline'

    def groupId(self):
        return 'aree_offline'

    def createInstance(self):
        return AreaAlgorithm(self.mode)

    def flags(self):
        # Progetti e simbologie QGIS: inizializzazione sul thread principale.
        return super().flags() | QgsProcessingAlgorithm.FlagNoThreading

    def shortHelpString(self):
        return ('Archivio condiviso: ' + str(ROOT/'##_aree/_archivio_comune') +
                '\nPrepara: scegli nome ed estensione (il selettore consente di disegnare sulla mappa), oppure un layer poligonale. '
                'Se il layer contiene più poligoni, vengono uniti tutti; esportare una selezione per limitarli. '
                'Aggiorna/Esporta: scegli area.json nella cartella della zona. '
                'La percentuale massima di NoData DTM viene salvata automaticamente: 0 richiede copertura completa; '
                'in Aggiorna, lasciare vuoto per conservare il valore già configurato. '
                'Esporta chiede il range di zoom, predefinito 12–16. '
                'Sorgenti selezionate dal catalogo. '
                'Il progetto aperto non viene sostituito: aprire il file QGZ restituito dopo la preparazione.')

    def initAlgorithm(self, config=None):
        if self.mode == 'prepare':
            self.addParameter(QgsProcessingParameterString('NAME', 'Nome cartella area', defaultValue='nuova_area'))
            self.addParameter(QgsProcessingParameterExtent('EXTENT', 'Estensione da disegnare o scegliere', optional=True))
            self.addParameter(QgsProcessingParameterFeatureSource('POLYGON', 'Oppure perimetro poligonale', [QgsProcessing.TypeVectorPolygon], optional=True))
            self.addParameter(QgsProcessingParameterCrs('CRS', 'CRS metrico di elaborazione', defaultValue='EPSG:32633'))
            self.addParameter(QgsProcessingParameterEnum('ZOOM', 'Profilo massimo', ['16 — compatto (default)', '17 — dettaglio grafico', '18 — richiede DTM nativo verificato <5 m'], defaultValue=0))
            self.addParameter(QgsProcessingParameterNumber(
                'MAX_MISSING_PERCENT', 'NoData DTM massimo (%) — 0 = copertura completa',
                type=QgsProcessingParameterNumber.Double, defaultValue=0.0, minValue=0.0, maxValue=10.0))
        else:
            self.addParameter(QgsProcessingParameterFile('CONFIG', 'Configurazione area.json', extension='json'))
        if self.mode == 'update':
            self.addParameter(QgsProcessingParameterNumber(
                'MAX_MISSING_PERCENT', 'NoData DTM massimo (%) — vuoto = mantieni; 0 = copertura completa',
                type=QgsProcessingParameterNumber.Double, optional=True, minValue=0.0, maxValue=10.0))
        if self.mode == 'export':
            self.addParameter(QgsProcessingParameterNumber(
                'MAX_MISSING_PERCENT', 'NoData DTM massimo (%) — vuoto = configurazione; 0 = copertura completa',
                type=QgsProcessingParameterNumber.Double, optional=True, minValue=0.0, maxValue=10.0))
            self.addParameter(QgsProcessingParameterNumber('MINZOOM', 'Zoom minimo', type=QgsProcessingParameterNumber.Integer, defaultValue=12, minValue=12, maxValue=18))
            self.addParameter(QgsProcessingParameterNumber('MAXZOOM', 'Zoom massimo', type=QgsProcessingParameterNumber.Integer, defaultValue=16, minValue=12, maxValue=18))
            self.addParameter(QgsProcessingParameterEnum(
                'MODE', 'Modalità', ['File unico (predefinito)', 'Suddividi per peso'], defaultValue=0))
            self.addParameter(QgsProcessingParameterNumber(
                'LIMIT', 'Limite suddivisione (MB decimali; obbligatorio solo se si suddivide)',
                type=QgsProcessingParameterNumber.Double, optional=True, minValue=0.1))
            self.addParameter(QgsProcessingParameterNumber('WARNING', 'Soglia avviso (MB decimali; vuoto = configurazione)', type=QgsProcessingParameterNumber.Double, optional=True, minValue=0.1))
        self.addOutput(QgsProcessingOutputFile('OUTPUT', 'Progetto QGIS' if self.mode != 'export' else 'Catalogo MBTiles'))

    def processAlgorithm(self, parameters, context, feedback):
        from .engine import Workflow
        workflow = Workflow(ROOT, feedback=feedback)
        try:
            if not (workflow.archive/'fonti.json').exists():
                workflow.initialize()
            if self.mode == 'prepare':
                source = self.parameterAsSource(parameters, 'POLYGON', context)
                if source:
                    geometries = [f.geometry() for f in source.getFeatures() if not f.geometry().isEmpty()]
                    if not geometries:
                        raise ValueError('Layer poligonale vuoto')
                    geometry = QgsGeometry.unaryUnion(geometries)
                    crs = source.sourceCrs().authid()
                else:
                    if not parameters.get('EXTENT'):
                        raise ValueError('Disegnare una estensione oppure scegliere un perimetro')
                    rect = self.parameterAsExtent(parameters, 'EXTENT', context, QgsCoordinateReferenceSystem('EPSG:4326'))
                    geometry = QgsGeometry.fromRect(rect)
                    crs = 'EPSG:4326'
                result = workflow.prepare(self.parameterAsString(parameters, 'NAME', context), geometry, crs,
                                          crs=self.parameterAsCrs(parameters, 'CRS', context).authid(),
                                          maxzoom=[16,17,18][self.parameterAsEnum(parameters, 'ZOOM', context)],
                                          max_missing_percent=self.parameterAsDouble(
                                              parameters, 'MAX_MISSING_PERCENT', context))
                return {'OUTPUT': result['project']}
            config_path = Path(self.parameterAsFile(parameters, 'CONFIG', context))
            if self.mode == 'update':
                max_missing = (self.parameterAsDouble(parameters, 'MAX_MISSING_PERCENT', context)
                               if parameters.get('MAX_MISSING_PERCENT') is not None else None)
                return {'OUTPUT': workflow.update(config_path, max_missing_percent=max_missing)['project']}
            if parameters.get('MAX_MISSING_PERCENT') is not None:
                # L'export deve usare DTM, derivati e progetto coerenti con la nuova soglia.
                workflow.update(
                    config_path,
                    max_missing_percent=self.parameterAsDouble(
                        parameters, 'MAX_MISSING_PERCENT', context))
            mode = ['single', 'split'][self.parameterAsEnum(parameters, 'MODE', context)]
            if mode == 'split' and parameters.get('LIMIT') is None:
                raise ValueError('Specificare il limite MB quando si sceglie Suddividi per peso')
            options = {'mode': mode}
            for param, key in [('LIMIT', 'maxbytes'), ('WARNING', 'warning_bytes')]:
                if parameters.get(param) is not None:
                    options[key] = int(self.parameterAsDouble(parameters, param, context)*1000000)
            workflow.export(config_path,
                            self.parameterAsInt(parameters, 'MINZOOM', context),
                            self.parameterAsInt(parameters, 'MAXZOOM', context),
                            **options)
            return {'OUTPUT': str(config_path.parent/'output/mbtiles/catalogo_mbtiles.json')}
        except Exception as exc:
            raise QgsProcessingException(str(exc)) from exc


class AtlasAlgorithm(QgsProcessingAlgorithm):
    TITLES = {'grid': '4 · Crea o estendi griglia atlante', 'prepare_cells': '5 · Prepara celle selezionate',
              'rename_cell': '6 · Assegna nome geografico', 'atlas': '7 · Genera catalogo e quadro di unione'}
    def __init__(self, mode='grid'):
        super().__init__(); self.mode = mode
    def name(self): return self.mode
    def displayName(self): return self.TITLES[self.mode]
    def group(self): return 'Atlante alpino'
    def groupId(self): return 'atlante'
    def createInstance(self): return AtlasAlgorithm(self.mode)
    def flags(self): return super().flags() | QgsProcessingAlgorithm.FlagNoThreading
    def shortHelpString(self):
        return ('Griglia EPSG:3035 con aree di analisi 35 x 35 km, nucleo 31 km e fascia di 2 km per lato. '
                'Senza estensione copre l’arco alpino dal Lago Maggiore al Friuli e conserva solo i settori montani. '
                'Aprire _archivio_comune/atlante_griglia_v2.gpkg, layer celle_analisi; selezionare i poligoni e attivare '
                'Solo elementi selezionati nel parametro Celle. Preparare una cella, oppure al massimo due celle adiacenti. '
                'Il campo cell_id identifica le celle. Le celle vengono elaborate in sequenza e non avviano export automatici. '
                'Gli stessi vettori sono esportati in 08_Atlante. Il catalogo non pubblica automaticamente i download.')
    def initAlgorithm(self, config=None):
        if self.mode == 'grid':
            self.addParameter(QgsProcessingParameterExtent(
                'EXTENT', 'Estensione opzionale (vuota = Lago Maggiore–Friuli)', optional=True))
            self.addParameter(QgsProcessingParameterBoolean(
                'MOUNTAIN_ONLY', 'Conserva solo riquadri con montagne rilevate dal DTM', defaultValue=True))
            self.addParameter(QgsProcessingParameterNumber(
                'MIN_ELEVATION', 'Quota minima considerata montagna (m)',
                type=QgsProcessingParameterNumber.Double, defaultValue=600, minValue=0, maxValue=5000))
            self.addParameter(QgsProcessingParameterNumber(
                'MIN_MOUNTAIN_PERCENT', 'Superficie minima sopra quota (%)',
                type=QgsProcessingParameterNumber.Double, defaultValue=1.0, minValue=0.1, maxValue=100))
        elif self.mode == 'prepare_cells':
            self.addParameter(QgsProcessingParameterFeatureSource('CELLS', 'Celle (usare solo elementi selezionati)', [QgsProcessing.TypeVectorPolygon]))
            self.addParameter(QgsProcessingParameterNumber(
                'MAX_MISSING_PERCENT', 'NoData DTM massimo (%) — 0 = copertura completa',
                type=QgsProcessingParameterNumber.Double, defaultValue=0.01,
                minValue=0.0, maxValue=10.0))
        elif self.mode == 'rename_cell':
            self.addParameter(QgsProcessingParameterString('CELL', 'Codice cella'))
            self.addParameter(QgsProcessingParameterString('NAME', 'Nome geografico pubblico'))
        self.addOutput(QgsProcessingOutputFile('OUTPUT', 'Griglia o quadro di unione'))
    def processAlgorithm(self, parameters, context, feedback):
        from .engine import Workflow
        from . import atlas
        w = Workflow(ROOT, feedback=feedback)
        try:
            if self.mode == 'prepare_cells':
                source = self.parameterAsSource(parameters, 'CELLS', context)
                if not source or source.fields().indexFromName('cell_id') < 0:
                    raise ValueError('Scegliere il layer celle con campo cell_id')
                atlas.prepare_cells(
                    w, [f['cell_id'] for f in source.getFeatures()],
                    max_missing_percent=self.parameterAsDouble(
                        parameters, 'MAX_MISSING_PERCENT', context))
            else:
                with w.locked():
                    if self.mode == 'grid':
                        bbox = None
                        if parameters.get('EXTENT'):
                            r = self.parameterAsExtent(parameters, 'EXTENT', context, QgsCoordinateReferenceSystem('EPSG:4326'))
                            bbox = [r.xMinimum(), r.yMinimum(), r.xMaximum(), r.yMaximum()]
                        atlas.make_grid(
                            w, bbox,
                            mountain_only=self.parameterAsBool(parameters, 'MOUNTAIN_ONLY', context),
                            min_elevation_m=self.parameterAsDouble(parameters, 'MIN_ELEVATION', context),
                            min_mountain_percent=self.parameterAsDouble(
                                parameters, 'MIN_MOUNTAIN_PERCENT', context))
                    elif self.mode == 'rename_cell':
                        atlas.rename_cell(w, self.parameterAsString(parameters, 'CELL', context), self.parameterAsString(parameters, 'NAME', context))
                    else:
                        atlas.build_catalog(w)
            return {'OUTPUT': str(w.root/'08_Atlante/quadro_unione.qgz' if self.mode == 'atlas'
                                  else atlas.grid_vector_path(w))}
        except Exception as exc:
            raise QgsProcessingException(str(exc)) from exc


class Provider(QgsProcessingProvider):
    def id(self):
        return 'scialpinismo'

    def name(self):
        return 'Scialpinismo locale'

    def longName(self):
        return 'Scialpinismo — archivio condiviso e aree offline'

    def loadAlgorithms(self):
        for mode in ('prepare', 'update', 'export'):
            self.addAlgorithm(AreaAlgorithm(mode))
        for mode in AtlasAlgorithm.TITLES:
            self.addAlgorithm(AtlasAlgorithm(mode))


class Plugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.actions = []

    def initGui(self):
        if QgsApplication.processingRegistry().providerById('scialpinismo'):
            return
        self.provider = Provider()
        QgsApplication.processingRegistry().addProvider(self.provider)
        import processing
        for mode, title in [('prepare', 'Prepara area…'), ('update', 'Aggiorna area…'), ('export', 'Esporta offline…'), *AtlasAlgorithm.TITLES.items()]:
            action = QAction(title, self.iface.mainWindow())
            action.triggered.connect(lambda checked=False, m=mode: processing.execAlgorithmDialog('scialpinismo:'+m, {}))
            self.iface.addPluginToMenu('Scialpinismo locale', action)
            self.actions.append(action)
        self.iface.messageBar().pushMessage('Scialpinismo locale', 'Sette strumenti pronti nella Toolbox e nel menu Plugin.', level=Qgis.Info, duration=8)

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu('Scialpinismo locale', action)
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
