"""Shared test setup: find QGIS's Python plugins (processing), run scripts, build small test datasets."""
import glob
import importlib.util
import os
import pathlib
import subprocess
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "qgis-agent" / "scripts"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _qgis_python_dirs():
    """QGIS python folders that hold the processing plugin, for conda, OSGeo4W, Linux packages and the macOS app."""
    prefixes = {sys.prefix, os.environ.get("CONDA_PREFIX", ""), os.environ.get("QGIS_PREFIX_PATH", "")}
    found = []
    for p in filter(None, prefixes):
        for sub in (("share", "qgis", "python"), ("share", "qgis", "python", "plugins"),
                    ("Library", "python"), ("Library", "python", "plugins")):
            d = os.path.join(p, *sub)
            if os.path.isdir(d):
                found.append(d)
    found += glob.glob("/Applications/QGIS*.app/Contents/Resources/qgis/python/plugins")
    return found


for _d in _qgis_python_dirs():
    if _d not in sys.path:
        sys.path.append(_d)
os.environ["PYTHONPATH"] = os.pathsep.join(
    [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p] + _qgis_python_dirs())


def load_script(name):
    """Imports a script from skills/qgis-agent/scripts as a module (its main() is not run)."""
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), SCRIPTS / name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_script(name, *args, timeout=600):
    """Runs a script with the current interpreter and returns the completed process (text output)."""
    return subprocess.run([sys.executable, str(SCRIPTS / name), *map(str, args)], capture_output=True, text=True,
                          env=os.environ.copy(), timeout=timeout)


def make_raster(path, array, epsg=32630, origin=(300000.0, 3700000.0), res=20.0, nodata=None):
    """Writes a single-band GeoTIFF; the data type follows the numpy array."""
    from osgeo import gdal, osr
    gdal.UseExceptions()
    array = np.asarray(array)
    types = {np.dtype("float32"): gdal.GDT_Float32, np.dtype("float64"): gdal.GDT_Float64,
             np.dtype("uint8"): gdal.GDT_Byte, np.dtype("uint16"): gdal.GDT_UInt16, np.dtype("int16"): gdal.GDT_Int16}
    ds = gdal.GetDriverByName("GTiff").Create(str(path), array.shape[1], array.shape[0], 1, types[array.dtype])
    ds.SetGeoTransform((origin[0], res, 0.0, origin[1], 0.0, -res))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg)
    ds.SetProjection(srs.ExportToWkt())
    band = ds.GetRasterBand(1)
    band.WriteArray(array)
    if nodata is not None:
        band.SetNoDataValue(nodata)
    ds = None
    return path


def make_polygons(path, wkts, epsg=32630, layer="zones"):
    """Writes polygons (WKT) to a GeoPackage layer with an integer 'id' field."""
    from osgeo import ogr, osr
    ogr.UseExceptions()
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg)
    drv = ogr.GetDriverByName("GPKG")
    ds = drv.CreateDataSource(str(path))
    lyr = ds.CreateLayer(layer, srs, ogr.wkbPolygon)
    lyr.CreateField(ogr.FieldDefn("id", ogr.OFTInteger))
    for i, w in enumerate(wkts, 1):
        f = ogr.Feature(lyr.GetLayerDefn())
        f.SetField("id", i)
        f.SetGeometry(ogr.CreateGeometryFromWkt(w))
        lyr.CreateFeature(f)
    ds = None
    return path


@pytest.fixture(scope="session")
def qgs():
    """A headless QGIS application with Processing, shared by the in-process tests."""
    from qgis.core import QgsApplication
    app = QgsApplication([], False)
    app.initQgis()
    plugins = os.path.join(QgsApplication.pkgDataPath(), "python", "plugins")   # same rule as pyqgis_template.py
    if os.path.isdir(plugins) and plugins not in sys.path:
        sys.path.append(plugins)
    from processing.core.Processing import Processing
    Processing.initialize()
    yield app
    app.exitQgis()
