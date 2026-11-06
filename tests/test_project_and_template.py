"""pyqgis_template.py saves a relative-path project; check_project.py catches what a saved project hides."""
import subprocess
import sys
import os

import numpy as np

from conftest import make_raster, run_script

BUILD = r'''
import sys
from qgis.core import (Qgis, QgsApplication, QgsProject, QgsRasterLayer, QgsPrintLayout, QgsLayoutItemMap,
                       QgsLayoutItemLegend)
app = QgsApplication([], False); app.initQgis()
folder, raster, relative, auto_legend = sys.argv[1], sys.argv[2], sys.argv[3] == "1", sys.argv[4] == "1"
prj = QgsProject.instance()
prj.setFileName(folder + "/p.qgz")
try:
    prj.setFilePathStorage(Qgis.FilePathType.Relative if relative else Qgis.FilePathType.Absolute)
except AttributeError:
    prj.writeEntryBool("Paths", "/Absolute", not relative)
lyr = QgsRasterLayer(raster, "ndvi"); assert lyr.isValid()
prj.setCrs(lyr.crs())
prj.addMapLayer(lyr)
lay = QgsPrintLayout(prj); lay.initializeDefaults(); lay.setName("map")
mp = QgsLayoutItemMap(lay); lay.addLayoutItem(mp); mp.setLayers([lyr])
lg = QgsLayoutItemLegend(lay); lay.addLayoutItem(lg); lg.setLinkedMap(mp); lg.setAutoUpdateModel(auto_legend)
prj.layoutManager().addLayout(lay)
assert prj.write()
app.exitQgis()
'''


def build_project(folder, relative, auto_legend):
    raster = make_raster(folder / "ndvi.tif", np.zeros((5, 5), dtype="float32"))
    subprocess.run([sys.executable, "-c", BUILD, str(folder), str(raster), "1" if relative else "0",
                    "1" if auto_legend else "0"], check=True, capture_output=True, env=os.environ.copy())
    return folder / "p.qgz"


def test_clean_project_has_no_warnings(tmp_path):
    out = run_script("check_project.py", build_project(tmp_path, relative=True, auto_legend=False)).stdout
    assert "paths relative" in out
    assert "[ok      ] ndvi" in out
    assert "no warnings" in out


def test_absolute_paths_and_auto_legend_are_flagged(tmp_path):
    out = run_script("check_project.py", build_project(tmp_path, relative=False, auto_legend=True)).stdout
    assert "absolute paths" in out
    assert "auto-updates" in out


def test_template_saves_a_relative_project(tmp_path):
    r = run_script("pyqgis_template.py", tmp_path)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "project.qgz").exists()
    assert "paths relative" in run_script("check_project.py", tmp_path / "project.qgz").stdout
