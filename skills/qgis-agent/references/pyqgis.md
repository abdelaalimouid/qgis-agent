# Tested PyQGIS recipes and known pitfalls

Code checked on QGIS 3.44 (macOS). Each recipe matches a menu tool, given in the heading, so the user can redo the step by hand.

## Contents

1. Headless start-up
2. Loading layers
3. Raster calculator
4. Discrete pseudocolour symbology and .qml style
5. Reclassify by table
6. Paletted classified raster
7. Zonal histogram and areas
8. Print layout: map, legend, scale bar, north arrow, export
9. Saving and reopening the project
10. Interface screenshots
11. Pitfalls met in practice
12. Differences between QGIS versions

## 1. Headless start-up

See `scripts/pyqgis_template.py`. The essentials:

```python
from qgis.core import QgsApplication
app = QgsApplication([], False); app.initQgis()
from processing.core.Processing import Processing   # import after initQgis
Processing.initialize()
import processing
...
app.exitQgis()
```

To get the exact parameters of an algorithm: `processing.algorithmHelp("native:zonalhistogram")`, or `qgis_process help native:zonalhistogram` from the command line.

## 2. Loading layers

```python
r = QgsRasterLayer("data/sentinel2/B08.tif", "B08")             # layer name = band name
v = QgsVectorLayer("data/area.gpkg|layername=boundary", "Boundary", "ogr")
assert r.isValid() and v.isValid()
project.addMapLayer(r, False); group = project.layerTreeRoot().addGroup("Sentinel-2"); group.addLayer(r)
```

Naming each band layer after its band (`B08`) lets you write raster calculator expressions exactly as in the assignment (`"B08@1"`).

## 3. Raster calculator (Raster > Raster Calculator)

```python
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
entries = []
for name, lyr in (("B08", b08), ("B12", b12)):
    e = QgsRasterCalculatorEntry(); e.ref = f"{name}@1"; e.raster = lyr; e.bandNumber = 1; entries.append(e)
expr = '("B08@1" - "B12@1") / ("B08@1" + "B12@1")'
calc = QgsRasterCalculator(expr, "rasters/_tmp.tif", "GTiff", extent, project.crs(),
                           b08.width(), b08.height(), entries, project.transformContext())
res = calc.processCalculation()
assert res == QgsRasterCalculator.Result.Success, calc.lastError()
gdal.Translate("rasters/NBR.tif", "rasters/_tmp.tif", creationOptions=["COMPRESS=DEFLATE", "PREDICTOR=3", "TILED=YES"])
```

`extent` is a `QgsRectangle` in the project CRS. The calculator writes an uncompressed GeoTIFF; the translation compresses it.

## 4. Discrete pseudocolour symbology (Properties > Symbology) and .qml style

```python
sh = QgsColorRampShader(-1, 1); sh.setColorRampType(QgsColorRampShader.Discrete)
# one entry per class: the VALUE is the class's UPPER BOUND
sh.setColorRampItemList([QgsColorRampShader.ColorRampItem(upper, QColor(colour), label)
                         for lower, upper, label, colour in classes])
rs = QgsRasterShader(-1, 1); rs.setRasterShaderFunction(sh)
ren = QgsSingleBandPseudoColorRenderer(lyr.dataProvider(), 1, rs)
ren.setClassificationMin(-1); ren.setClassificationMax(1)
lyr.setRenderer(ren)
lyr.saveNamedStyle("styles/NBR.qml")        # reusable: Properties > Style > Load Style
```

Colour map file that the dialog can load ("Load color map from file"):

```
# QGIS Generated Color Map Export File
INTERPOLATION:DISCRETE
-0.3,128,0,0,255,-1 to -0.30 very low
0,230,30,30,255,-0.30 to 0 low
```

## 5. Reclassify by table (Processing > Raster analysis > Reclassify by table)

```python
table = []
for k, (lower, upper, *_ ) in enumerate(classes, start=1):
    table += [lower, upper, k]
processing.run("native:reclassifybytable", {
    "INPUT_RASTER": lyr, "RASTER_BAND": 1, "TABLE": table, "NO_DATA": 0,
    "RANGE_BOUNDARIES": 2,          # 0: min < v <= max; 1: min <= v < max; 2: min <= v <= max; 3: min < v < max
    "NODATA_FOR_MISSING": True, "DATA_TYPE": 0, "OUTPUT": "rasters/classes/NBR_classes.tif"})
```

Choose `RANGE_BOUNDARIES` according to the assignment and state it in the work report. With 2, a value exactly on a bound goes to the first row that contains it.

Values exactly on a bound are common (bands are integers, so an index often lands exactly on 0.2 or 0.4). Depending on the precision of the calculation (32 or 64 bit), a few pixels switch class: a difference of about 0.02 % between two methods is normal. Report it in the checks, together with the bound rule used.

## 6. Paletted classified raster (Properties > Symbology > Paletted/Unique values)

```python
cl.setRenderer(QgsPalettedRasterRenderer(cl.dataProvider(), 1, [
    QgsPalettedRasterRenderer.Class(k, QColor(colour), f"{k}: {label}") for k, (colour, label) in enumerate(..., 1)]))
```

## 7. Zonal histogram and areas (Processing > Raster analysis > Zonal histogram)

```python
zh = processing.run("native:zonalhistogram", {"INPUT_RASTER": cl, "RASTER_BAND": 1, "INPUT_VECTOR": zones,
                                               "COLUMN_PREFIX": "HISTO_", "OUTPUT": "TEMPORARY_OUTPUT"})["OUTPUT"]
for f in zh.getFeatures():
    n = {k: int(f[f"HISTO_{k}"] or 0) for k in range(1, 7) if f"HISTO_{k}" in f.fields().names()}
    ha = {k: c * pixel_area_ha for k, c in n.items()}          # 20 m: 0.04 ha per pixel
```

A missing class column means zero pixels. Check: the pixel counts of all classes must add up to the number of valid pixels in the zone.

Writing tables: CSV for Excel in the user's locale (French Excel: `;` separator and decimal comma), encoded `utf-8-sig` so accents survive ("végétation", not "vegetation"); XLSX with `QgsVectorFileWriter` (driver `XLSX`, one geometry-less memory layer per sheet).

## 8. Print layout (Project > New Print Layout)

```python
layout = QgsPrintLayout(project); layout.initializeDefaults(); layout.setName("NBR map")
layout.pageCollection().page(0).setPageSize("A4", QgsLayoutItemPage.Landscape)

mp = QgsLayoutItemMap(layout); layout.addLayoutItem(mp)
mp.attemptMove(QgsLayoutPoint(10, 23)); mp.attemptResize(QgsLayoutSize(150, 168))
mp.setLayers([towns, boundary, nbr]); mp.setKeepLayerSet(True)        # layers frozen for this map
mp.setCrs(project.crs()); mp.setExtent(extent); mp.setFrameEnabled(True)

lg = QgsLayoutItemLegend(layout); layout.addLayoutItem(lg); lg.setLinkedMap(mp)
lg.setTitle("NBR classes"); lg.setAutoUpdateModel(False)
tree = lg.model().rootGroup(); tree.removeAllChildren()              # edit the legend's own layer tree
n_idx = tree.addLayer(nbr); tree.addLayer(boundary)
QgsLegendRenderer.setNodeLegendStyle(n_idx, QgsLegendStyle.Hidden)    # hides the layer name
names = [n.data(Qt.DisplayRole) for n in lg.model().layerLegendNodes(n_idx)]
first = 1 if len(names) == len(classes) + 1 else 0                    # skips the "Band 1 (Gray)" entry
QgsMapLayerLegendUtils.setLegendNodeOrder(n_idx, list(range(first, first + len(classes))))
lg.model().refreshLayerLegend(n_idx)
lg.setWrapString("|")                                                 # "0.20 to 0.40|moderate" on two lines

sb = QgsLayoutItemScaleBar(layout); layout.addLayoutItem(sb); sb.setLinkedMap(mp); sb.setStyle("Single Box")
sb.setUnits(Qgis.DistanceUnit.Kilometers); sb.setUnitLabel("km")
sb.setUnitsPerSegment(5); sb.setNumberOfSegments(4); sb.setNumberOfSegmentsLeft(0); sb.update()

na = QgsLayoutItemPicture(layout); layout.addLayoutItem(na)
na.setPicturePath(os.path.join(QgsApplication.pkgDataPath(), "svg", "arrows", "NorthArrow_02.svg"))
na.setLinkedMap(mp); na.setNorthMode(QgsLayoutItemPicture.TrueNorth)

project.layoutManager().addLayout(layout)
ex = QgsLayoutExporter(layout)
ps = QgsLayoutExporter.PdfExportSettings(); ps.dpi = 300; ex.exportToPdf("maps/NBR.pdf", ps)
im = QgsLayoutExporter.ImageExportSettings(); im.dpi = 120; ex.exportToImage("maps/previews/NBR.png", im)
```

Elements a map assignment almost always asks for: title, legend, scale bar, north arrow, image date, data source, CRS. Add a metadata text with `QgsLayoutItemLabel`.

## 9. Saving and reopening the project

```python
project.setFilePathStorage(Qgis.FilePathType.Relative)
project.write("project.qgz")
```

Then `bash qgis_python.sh scripts/check_project.py project.qgz`: valid layers, relative paths, the real content of the legends.

## 10. Interface screenshots

To show a tool pre-filled, start QGIS with a script:

- macOS: `/Applications/QGIS.app/Contents/MacOS/QGIS --project project.qgz --code capture.py`
- Windows and Linux: start the QGIS executable with the same `--project` and `--code` options

In `capture.py`, chain the actions with `QTimer.singleShot` (the interface needs time to draw):

- processing tool: `d = processing.createAlgorithmDialog("native:zonalhistogram", {...}); d.show()` then `d.grab().save("capture.png")`;
- raster calculator: trigger the `mActionShowRasterCalculator` action and fill it from a `QTimer` started beforehand (the window is modal), then `grab()`;
- map: wait for the `iface.mapCanvas().mapCanvasRefreshed` signal before capturing, otherwise the image is blank;
- close each window before opening the next, and quit with `iface.actionExit().trigger()` after `project.setDirty(False)`.

## 11. Pitfalls met in practice

| Symptom | Cause | Fix |
|---|---|---|
| Reopened project's legend lists every layer | legend set to auto-update | `setAutoUpdateModel(False)` and edit `lg.model().rootGroup()` |
| "Band 1 (Gray)" entry in the legend | the raster's band title node | `setLegendNodeOrder` without node 0 |
| Scale bar in metres or wrong | units not set | `setUnits(Kilometers)` and `setUnitLabel("km")`, nothing else |
| Classes shifted by one | lower bound entered in discrete symbology | enter the upper bound |
| Regression slope 0.13 instead of 0.92 | computed in float32 | convert to float64 before statistics |
| Indices outside [−1, 1] | raw values instead of reflectance | apply the product's scale and offset |
| Areas too large | computed on the whole rectangle, or zeros counted as data | mask with the study area, declare nodata |
| Sea or lake counted in a ring around an area | buffer spilling over water | remove water (SCL class 6 or an official outline) |
| `ModuleNotFoundError: processing` | plugins folder missing from PYTHONPATH | run through `qgis_python.sh` |
| Blank screenshot | map not drawn yet | wait for `mapCanvasRefreshed` |

## 12. Differences between QGIS versions

| 3.30 and later | 3.28 and earlier |
|---|---|
| `Qgis.DistanceUnit.Kilometers` | `QgsUnitTypes.DistanceKilometers` |
| `Qgis.FilePathType.Relative` | `project.writeEntryBool("Paths", "/Absolute", False)` |
| `QgsRasterCalculator.Result.Success` | `QgsRasterCalculator.Success` |
| `Qgis.RenderUnit.Points` | `QgsUnitTypes.RenderPoints` |

When in doubt, `help(object)` in QGIS's Python lists the available names.
