# -*- coding: utf-8 -*-
"""Headless PyQGIS step template.
Run:  bash qgis_python.sh scripts/NN_step.py <project_root>
Copy this file for each step, keep the parameters at the top and paths relative to the project root."""
import os
import sys

from qgis.core import Qgis, QgsApplication, QgsProject, QgsRasterLayer, QgsVectorLayer, QgsCoordinateReferenceSystem

# ---------------------------------------------------------------- step parameters
ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
PROJECT = "project.qgz"          # QGIS project, at the root
CRS = "EPSG:32630"               # working CRS (UTM zone of the area)


def P(*parts):
    """Absolute path from the project root."""
    return os.path.join(ROOT, *parts)


# ---------------------------------------------------------------- start QGIS with no window
app = QgsApplication([], False)
app.initQgis()
from processing.core.Processing import Processing  # noqa: E402  (after initQgis)
Processing.initialize()
import processing  # noqa: E402,F401

project = QgsProject.instance()
if os.path.exists(P(PROJECT)):
    project.read(P(PROJECT))
else:
    project.setCrs(QgsCoordinateReferenceSystem(CRS))
    project.setFileName(P(PROJECT))
# relative paths: the folder can be moved or zipped without breaking the project
try:
    project.setFilePathStorage(Qgis.FilePathType.Relative)
except AttributeError:  # QGIS 3.28 and earlier
    project.writeEntryBool("Paths", "/Absolute", False)


def load_raster(path, name):
    lyr = QgsRasterLayer(P(path), name)
    if not lyr.isValid():
        raise RuntimeError(f"invalid raster: {path}")
    return lyr


def load_vector(path, name, layer=None):
    src = P(path) + (f"|layername={layer}" if layer else "")
    lyr = QgsVectorLayer(src, name, "ogr")
    if not lyr.isValid():
        raise RuntimeError(f"invalid vector: {src}")
    return lyr


# ---------------------------------------------------------------- the step's processing
# Example: reprojection (Vector > Data Management Tools > Reproject Layer)
# res = processing.run("native:reprojectlayer", {"INPUT": P("data", "area.gpkg"), "TARGET_CRS": CRS,
#                                                "OUTPUT": P("data", "area_utm.gpkg")})
# lyr = load_vector("data/area_utm.gpkg", "Study area")
# project.addMapLayer(lyr)

# ---------------------------------------------------------------- save
if not project.write():
    raise RuntimeError("could not save the project")
print("project saved:", project.fileName())
app.exitQgis()
