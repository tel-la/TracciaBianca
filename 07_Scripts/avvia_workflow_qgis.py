"""Avvio da --code o console, senza dipendere da __file__ o dalla directory corrente."""
import os
import sys
from pathlib import Path
from qgis.PyQt.QtCore import QTimer


def _scialpinismo_resolve_script():
    candidates = [globals().get('SCIALPINISMO_SCRIPT'),
                  os.environ.get('SCIALPINISMO_SCRIPT'), globals().get('__file__')]
    for index, arg in enumerate(sys.argv[:-1]):
        if arg == '--code':
            candidates.append(sys.argv[index+1])
    candidates.append(Path.cwd()/'07_Scripts/avvia_workflow_qgis.py')
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser().resolve()
        if path.is_file() and (path.parent/'scialpinismo/provider.py').is_file():
            return path
    raise RuntimeError('Cartella Scialpinismo non individuata. Usare Avvia_Scialpinismo.command '
                       'oppure impostare SCIALPINISMO_SCRIPT al percorso completo di questo script.')


_scialpinismo_script = _scialpinismo_resolve_script()


def _scialpinismo_start(script_path=_scialpinismo_script):
    # La console QGIS condivide i globali e può modificare sys.path durante l'avvio.
    # Congela il percorso nel callback e aggiungilo quando serve effettivamente.
    script_dir = str(script_path.parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    from scialpinismo.provider import Plugin
    from qgis.utils import iface
    from qgis.core import QgsProject
    global scialpinismo_plugin
    scialpinismo_plugin = Plugin(iface)
    scialpinismo_plugin.initGui()
    project = script_path.parent.parent/'##_aree/01_Cortina/progetto/01_Cortina.qgz'
    if project.exists() and not QgsProject.instance().fileName() and not QgsProject.instance().isDirty():
        iface.addProject(str(project))


QTimer.singleShot(1000, _scialpinismo_start)
