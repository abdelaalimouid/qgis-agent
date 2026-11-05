# -*- coding: utf-8 -*-
"""Reopens a QGIS project from scratch and lists what it really contains.
Run:  bash qgis_python.sh check_project.py <project.qgz>
Checks: valid layers, relative paths, CRS, symbology, print layouts and legend contents.
What is saved can differ from what was exported to PDF: this check reveals it."""
import os
import sys

from qgis.core import QgsApplication, QgsProject, QgsLayoutItemLegend, QgsLayoutItemMap, QgsMapLayer

if len(sys.argv) < 2:
    sys.exit("Usage: check_project.py <project.qgz>")
path = os.path.abspath(sys.argv[1])
app = QgsApplication([], False)
app.initQgis()
prj = QgsProject.instance()
if not prj.read(path):
    sys.exit(f"cannot read {path}")

warnings = []
absolute = prj.readBoolEntry("Paths", "/Absolute", False)[0]
print(f"project    {path}")
print(f"CRS        {prj.crs().authid()}   paths {'ABSOLUTE' if absolute else 'relative'}")
if absolute:
    warnings.append("absolute paths: the project will break if the folder is moved")

print("\nlayers")
root = os.path.dirname(path)
for lyr in prj.mapLayers().values():
    src = lyr.source().split("|")[0]
    outside = os.path.isabs(src) and os.path.exists(src) and not os.path.abspath(src).startswith(root)
    if lyr.type() in (QgsMapLayer.RasterLayer, QgsMapLayer.VectorLayer):
        rend = lyr.renderer().type() if lyr.renderer() else "none"
    else:
        rend = "-"
    state = "ok" if lyr.isValid() else "INVALID"
    print(f"  [{state:8}] {lyr.name():45.45}  {lyr.crs().authid():11}  {rend}")
    if not lyr.isValid():
        warnings.append(f"invalid layer: {lyr.name()} ({src})")
    if outside:
        warnings.append(f"file outside the project folder: {lyr.name()} ({src})")
    if lyr.type() == QgsMapLayer.RasterLayer and lyr.isValid() and lyr.crs() != prj.crs():
        warnings.append(f"CRS differs from the project: {lyr.name()} ({lyr.crs().authid()})")

layouts = prj.layoutManager().printLayouts()
print(f"\nprint layouts: {len(layouts)}")
for lay in layouts:
    maps = [i for i in lay.items() if isinstance(i, QgsLayoutItemMap)]
    legends = [i for i in lay.items() if isinstance(i, QgsLayoutItemLegend)]
    print(f"  {lay.name()}  ({lay.pageCollection().pageCount()} page, {len(maps)} map, {len(legends)} legend)")
    for lg in legends:
        names = [n.name() for n in lg.model().rootGroup().findLayers()]
        print(f"    legend \"{lg.title()}\": {len(names)} layer(s): {', '.join(names)}")
        if lg.autoUpdateModel():
            warnings.append(f"legend of \"{lay.name()}\" auto-updates: it will list every visible layer")

print("\nwarnings" if warnings else "\nno warnings")
for w in warnings:
    print("  WARNING", w)
app.exitQgis()
