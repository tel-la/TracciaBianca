"""Prova isolata: simula exec di --code senza __file__, poi esegue il callback Qt."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from qgis.core import QgsApplication
from qgis.PyQt.QtWidgets import QMainWindow
import qgis.utils
from qgis.PyQt.QtCore import QTimer

app = QgsApplication([], False);app.initQgis()
startup = Path(sys.argv[1]).resolve()
mode = sys.argv[2]
# Il wrapper di test aggiunge il package a PYTHONPATH: rimuoverlo per evitare falsi positivi.
sys.path[:] = [p for p in sys.path if not (Path(p or '.')/'scialpinismo/provider.py').is_file()]
callbacks = []
namespace = {}
if mode == 'argv':
    sys.argv = ['qgis', '--code', str(startup)]
else:
    sys.argv = ['qgis']
with patch.object(QTimer, 'singleShot', side_effect=lambda delay, callback: callbacks.append(callback)):
    exec(compile(startup.read_text(), '<string>', 'exec'), namespace)
assert namespace['_scialpinismo_script'] == startup
# Simula altre istruzioni della console tra esecuzione e callback.
namespace['script'] = Path('/percorso/non/pertinente')
window = QMainWindow()
iface = MagicMock();iface.mainWindow.return_value = window
with patch.object(qgis.utils, 'iface', iface):
    callbacks[0]()
provider = app.processingRegistry().providerById('scialpinismo')
assert provider is not None
assert sorted(a.id() for a in provider.algorithms()) == sorted('scialpinismo:'+n for n in ['export','prepare','update','grid','prepare_cells','rename_cell','atlas'])
assert iface.addPluginToMenu.call_count == 7
from scialpinismo import provider as module
assert Path(module.__file__).resolve().parent == startup.parent/'scialpinismo'
assert module.ROOT == startup.parent.parent
print('AVVIO_OK', mode, startup)
namespace['scialpinismo_plugin'].unload()
