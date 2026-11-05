#!/usr/bin/env bash
# Runs a Python script with QGIS's own Python (macOS or Linux), with no window.
#   bash qgis_python.sh --info               QGIS, GDAL and Python versions
#   bash qgis_python.sh script.py [args...]  runs the script
# Optional variable: QGIS_APP=/Applications/QGIS-LTR.app to pick a specific installation.
set -euo pipefail

PY=""
case "$(uname -s)" in
  Darwin)
    APP="${QGIS_APP:-}"
    if [ -z "$APP" ]; then
      for a in /Applications/QGIS.app /Applications/QGIS-LTR.app /Applications/QGIS*.app "$HOME"/Applications/QGIS*.app; do
        [ -d "$a" ] && APP="$a" && break
      done
    fi
    [ -n "$APP" ] || { echo "QGIS not found in /Applications. Install it or set QGIS_APP." >&2; exit 1; }
    C="$APP/Contents"
    if [ -x "$C/MacOS/python" ]; then
      PY="$C/MacOS/python"                       # launcher shipped with QGIS (3.40 and later)
    elif [ -x "$C/MacOS/bin/python3" ]; then
      PY="$C/MacOS/bin/python3"                  # older versions
    else
      PY="$(ls "$C"/MacOS/python3* 2>/dev/null | head -1)"
      export PYTHONHOME="$C/Frameworks"
    fi
    export QGIS_PREFIX_PATH="$C/MacOS"
    # PROJ and GDAL data (without them, EPSG codes are not recognised)
    PROJDB="$(find "$C" -name proj.db -print -quit 2>/dev/null || true)"
    [ -n "$PROJDB" ] && export PROJ_DATA="$(dirname "$PROJDB")" PROJ_LIB="$(dirname "$PROJDB")"
    GDALD="$(find "$C/Resources" -maxdepth 3 -type d -name gdal -print -quit 2>/dev/null || true)"
    [ -n "$GDALD" ] && export GDAL_DATA="$GDALD"
    PLUGINS="$C/Resources/qgis/python/plugins"
    QGISPY="$C/Resources/qgis/python"
    ;;
  Linux)
    PY="$(command -v python3)"
    PREFIX="${QGIS_PREFIX_PATH:-/usr}"
    export QGIS_PREFIX_PATH="$PREFIX"
    PLUGINS="$PREFIX/share/qgis/python/plugins"
    QGISPY="$PREFIX/share/qgis/python"
    ;;
  *)
    echo "On Windows, use python-qgis.bat (or python-qgis-ltr.bat) from the QGIS bin folder." >&2; exit 1 ;;
esac

[ -n "$PY" ] && [ -x "$PY" ] || { echo "QGIS's Python not found." >&2; exit 1; }
export PYTHONPATH="$QGISPY:$PLUGINS${PYTHONPATH:+:$PYTHONPATH}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"

if [ "${1:-}" = "--info" ]; then
  exec "$PY" -c "
import sys
from qgis.core import Qgis, QgsApplication
app = QgsApplication([], False); app.initQgis()
from osgeo import gdal
import processing
print('QGIS', Qgis.version()); print('GDAL', gdal.__version__); print('Python', sys.version.split()[0]); print('QGIS Python:', sys.executable)"
fi
[ $# -ge 1 ] || { echo "Usage: bash qgis_python.sh script.py [args...] | --info" >&2; exit 1; }
exec "$PY" "$@"
