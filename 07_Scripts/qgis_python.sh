#!/bin/zsh
set -eu
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
QGIS_BUNDLE="${SCIALPINISMO_QGIS_BUNDLE:-/Applications/QGIS.app/Contents}"
if [[ ! -x "$QGIS_BUNDLE/MacOS/python3.12" ]]; then
  print -u2 "QGIS non trovato. Impostare SCIALPINISMO_QGIS_BUNDLE alla directory Contents."
  exit 1
fi
export PYTHONHOME="$QGIS_BUNDLE/Resources"
export PYTHONPATH="$QGIS_BUNDLE/Resources/python3.11:$QGIS_BUNDLE/Resources/python3.11/lib-dynload:$QGIS_BUNDLE/Resources/python3.11/site-packages:$QGIS_BUNDLE/Resources/qgis/python:$QGIS_BUNDLE/Resources/qgis/python/plugins:$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}"
export PROJ_DATA="$QGIS_BUNDLE/Resources/qgis/proj"
export GDAL_DATA="$QGIS_BUNDLE/Resources/qgis/gdal"
export QGIS_PREFIX_PATH="$QGIS_BUNDLE/Resources/qgis"
export PATH="$QGIS_BUNDLE/MacOS:$PATH"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
mkdir -p "$SCRIPT_DIR/../.qgis_runtime/tmp"
export SQLITE_TMPDIR="$SCRIPT_DIR/../.qgis_runtime/tmp"
export CPL_TMPDIR="$SQLITE_TMPDIR"
export GDAL_CACHEMAX=256
export GDAL_NUM_THREADS=2
export OMP_NUM_THREADS=2
exec "$QGIS_BUNDLE/MacOS/python3.12" "$@"
