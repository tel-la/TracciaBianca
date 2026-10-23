#!/bin/zsh
set -eu
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
QGIS_APP="${SCIALPINISMO_QGIS_APP:-/Applications/QGIS.app}"
# Una nuova finestra/processo evita di sostituire un progetto aperto con modifiche non salvate.
STARTUP_SCRIPT="$PROJECT_ROOT/07_Scripts/avvia_workflow_qgis.py"
ATLAS_TEMP="$PROJECT_ROOT/.qgis_runtime/tmp"
mkdir -p "$ATLAS_TEMP"
exec /usr/bin/open -na "$QGIS_APP" --env "SCIALPINISMO_SCRIPT=$STARTUP_SCRIPT" --env "SQLITE_TMPDIR=$ATLAS_TEMP" --env "CPL_TMPDIR=$ATLAS_TEMP" --args --code "$STARTUP_SCRIPT"
