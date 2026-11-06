#!/usr/bin/env bash
# Runs a Python script with a Python that can import QGIS (PyQGIS), with no window.
#   bash qgis_python.sh --info               QGIS, GDAL and Python versions
#   bash qgis_python.sh script.py [args...]  runs the script
# Lookup order:
#   1. QGIS_PYTHON=/path/to/python           an explicit interpreter
#   2. the python3 on PATH, if it imports qgis.core (conda-forge or OSGeo4W environment, Linux packages)
#   3. macOS: the QGIS app in /Applications (QGIS_APP=/Applications/QGIS-LTR.app picks a specific one)
#   4. Linux: /usr/bin/python3 with the system QGIS
# On Windows, use python-qgis.bat (or python-qgis-ltr.bat) from the QGIS bin folder, or a conda environment.
set -euo pipefail

PY=""
PLUGIN_DIRS=()

add_prefix_dirs() {   # QGIS python and plugin folders under an install prefix
  local p="$1"
  for d in "$p/share/qgis/python" "$p/share/qgis/python/plugins" "$p/Library/python" "$p/Library/python/plugins"; do
    [ -d "$d" ] && PLUGIN_DIRS+=("$d")
  done
  return 0
}

if [ -n "${QGIS_PYTHON:-}" ]; then
  PY="$QGIS_PYTHON"
  [ -n "${CONDA_PREFIX:-}" ] && add_prefix_dirs "$CONDA_PREFIX"
elif command -v python3 >/dev/null 2>&1 && python3 -c "import qgis.core" >/dev/null 2>&1; then
  PY="$(command -v python3)"
  PREFIX="$(python3 -c 'import sys; print(sys.prefix)')"
  add_prefix_dirs "$PREFIX"
  export QGIS_PREFIX_PATH="${QGIS_PREFIX_PATH:-$PREFIX}"
else
  case "$(uname -s)" in
    Darwin)
      APP="${QGIS_APP:-}"
      if [ -z "$APP" ]; then
        for a in /Applications/QGIS.app /Applications/QGIS-LTR.app /Applications/QGIS*.app "$HOME"/Applications/QGIS*.app; do
          [ -d "$a" ] && APP="$a" && break
        done
      fi
      [ -n "$APP" ] || { echo "QGIS not found in /Applications. Install it, or set QGIS_APP or QGIS_PYTHON." >&2; exit 1; }
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
      PLUGIN_DIRS+=("$C/Resources/qgis/python" "$C/Resources/qgis/python/plugins")
      ;;
    Linux)
      PY="/usr/bin/python3"
      PREFIX="${QGIS_PREFIX_PATH:-/usr}"
      export QGIS_PREFIX_PATH="$PREFIX"
      add_prefix_dirs "$PREFIX"
      ;;
    *)
      echo "On Windows, use python-qgis.bat (or python-qgis-ltr.bat) from the QGIS bin folder, or a conda environment with qgis." >&2
      exit 1 ;;
  esac
fi

[ -n "$PY" ] && [ -x "$(command -v "$PY")" ] || { echo "No Python with QGIS found. Set QGIS_PYTHON." >&2; exit 1; }
for d in "${PLUGIN_DIRS[@]+"${PLUGIN_DIRS[@]}"}"; do
  PYTHONPATH="$d${PYTHONPATH:+:$PYTHONPATH}"
done
export PYTHONPATH="${PYTHONPATH:-}"
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
