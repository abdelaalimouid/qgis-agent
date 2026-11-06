"""The PyQGIS recipes taught in references/pyqgis.md, run for real and compared with numpy."""
import numpy as np

from conftest import make_polygons, make_raster

CLASSES = [(-1.0, 0.0), (0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 1.0)]


def bands(tmp_path):
    rng = np.random.default_rng(42)
    red = rng.uniform(0.02, 0.35, size=(40, 50)).astype("float32")
    nir = rng.uniform(0.05, 0.55, size=(40, 50)).astype("float32")
    return make_raster(tmp_path / "B04.tif", red), make_raster(tmp_path / "B08.tif", nir), red, nir


def ndvi_with_raster_calculator(qgs, tmp_path):
    from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
    from qgis.core import QgsProject, QgsRasterLayer
    p_red, p_nir, red, nir = bands(tmp_path)
    b04, b08 = QgsRasterLayer(str(p_red), "B04"), QgsRasterLayer(str(p_nir), "B08")
    entries = []
    for name, lyr in (("B04", b04), ("B08", b08)):
        e = QgsRasterCalculatorEntry(); e.ref = f"{name}@1"; e.raster = lyr; e.bandNumber = 1; entries.append(e)
    out = tmp_path / "NDVI.tif"
    calc = QgsRasterCalculator('("B08@1" - "B04@1") / ("B08@1" + "B04@1")', str(out), "GTiff", b08.extent(),
                               b08.crs(), b08.width(), b08.height(), entries, QgsProject.instance().transformContext())
    assert calc.processCalculation() == 0, calc.lastError()
    return out, (nir - red) / (nir + red)


def test_raster_calculator_matches_numpy(qgs, tmp_path):
    from osgeo import gdal
    out, expected = ndvi_with_raster_calculator(qgs, tmp_path)
    np.testing.assert_allclose(gdal.Open(str(out)).ReadAsArray(), expected, atol=1e-6)


def test_discrete_symbology_uses_upper_bounds_and_saves_style(qgs, tmp_path):
    from qgis.core import QgsColorRampShader, QgsRasterLayer, QgsRasterShader, QgsSingleBandPseudoColorRenderer
    from qgis.PyQt.QtGui import QColor
    out, _ = ndvi_with_raster_calculator(qgs, tmp_path)
    lyr = QgsRasterLayer(str(out), "NDVI")
    sh = QgsColorRampShader(-1, 1); sh.setColorRampType(QgsColorRampShader.Discrete)
    sh.setColorRampItemList([QgsColorRampShader.ColorRampItem(hi, QColor("#336633"), f"{lo} to {hi}")
                             for lo, hi in CLASSES])
    rs = QgsRasterShader(-1, 1); rs.setRasterShaderFunction(sh)
    lyr.setRenderer(QgsSingleBandPseudoColorRenderer(lyr.dataProvider(), 1, rs))
    assert [i.value for i in lyr.renderer().shader().rasterShaderFunction().colorRampItemList()] == [hi for _, hi in CLASSES]
    lyr.saveNamedStyle(str(tmp_path / "NDVI.qml"))
    assert (tmp_path / "NDVI.qml").stat().st_size > 0


def test_reclassify_and_zonal_histogram_match_numpy(qgs, tmp_path):
    import processing
    from osgeo import gdal
    from qgis.core import QgsRasterLayer, QgsVectorLayer
    out, ndvi = ndvi_with_raster_calculator(qgs, tmp_path)
    table = []
    for k, (lo, hi) in enumerate(CLASSES, 1):
        table += [lo, hi, k]
    cls_path = tmp_path / "classes.tif"
    processing.run("native:reclassifybytable", {"INPUT_RASTER": str(out), "RASTER_BAND": 1, "TABLE": table,
                                                "NO_DATA": 0, "RANGE_BOUNDARIES": 0, "NODATA_FOR_MISSING": True,
                                                "DATA_TYPE": 0, "OUTPUT": str(cls_path)})
    got = gdal.Open(str(cls_path)).ReadAsArray()
    stored = gdal.Open(str(out)).ReadAsArray()                     # classify what QGIS stored (float32)
    expected = np.zeros(stored.shape, dtype="uint8")
    for k, (lo, hi) in enumerate(CLASSES, 1):
        expected[(stored > lo) & (stored <= hi)] = k              # RANGE_BOUNDARIES 0: min < v <= max
    assert np.array_equal(got, expected)

    ext = QgsRasterLayer(str(out), "x").extent()
    box = (f"POLYGON(({ext.xMinimum()} {ext.yMinimum()}, {ext.xMaximum()} {ext.yMinimum()}, {ext.xMaximum()} "
           f"{ext.yMaximum()}, {ext.xMinimum()} {ext.yMaximum()}, {ext.xMinimum()} {ext.yMinimum()}))")
    zones = make_polygons(tmp_path / "zone.gpkg", [box])
    zh = processing.run("native:zonalhistogram", {"INPUT_RASTER": str(cls_path), "RASTER_BAND": 1,
                                                  "INPUT_VECTOR": f"{zones}|layername=zones", "COLUMN_PREFIX": "HISTO_",
                                                  "OUTPUT": "TEMPORARY_OUTPUT"})["OUTPUT"]
    f = next(zh.getFeatures())
    counts = {k: int(f[f"HISTO_{k}"] or 0) for k in range(1, 6) if f"HISTO_{k}" in f.fields().names()}
    assert sum(counts.values()) == ndvi.size
    for k in counts:
        assert counts[k] == int((expected == k).sum())


def test_print_layout_with_clean_legend_exports(qgs, tmp_path):
    from qgis.core import (Qgis, QgsLayoutExporter, QgsLayoutItemLegend, QgsLayoutItemMap, QgsLayoutItemScaleBar,
                           QgsLayoutPoint, QgsLayoutSize, QgsPrintLayout, QgsProject, QgsRasterLayer)
    out, _ = ndvi_with_raster_calculator(qgs, tmp_path)
    prj = QgsProject.instance()
    lyr = QgsRasterLayer(str(out), "NDVI"); prj.addMapLayer(lyr)
    other = QgsRasterLayer(str(tmp_path / "B04.tif"), "B04"); prj.addMapLayer(other)
    lay = QgsPrintLayout(prj); lay.initializeDefaults(); lay.setName("NDVI map")
    mp = QgsLayoutItemMap(lay); lay.addLayoutItem(mp)
    mp.attemptMove(QgsLayoutPoint(10, 20)); mp.attemptResize(QgsLayoutSize(150, 120))
    mp.setLayers([lyr]); mp.setKeepLayerSet(True); mp.setExtent(lyr.extent())
    lg = QgsLayoutItemLegend(lay); lay.addLayoutItem(lg); lg.setLinkedMap(mp); lg.setAutoUpdateModel(False)
    tree = lg.model().rootGroup(); tree.removeAllChildren(); tree.addLayer(lyr)
    assert [n.name() for n in tree.findLayers()] == ["NDVI"]          # B04 stays out of the legend
    sb = QgsLayoutItemScaleBar(lay); lay.addLayoutItem(sb); sb.setLinkedMap(mp); sb.setStyle("Single Box")
    try:
        sb.setUnits(Qgis.DistanceUnit.Kilometers)
    except AttributeError:                                           # QGIS 3.28 and earlier
        from qgis.core import QgsUnitTypes
        sb.setUnits(QgsUnitTypes.DistanceKilometers)
    sb.setUnitLabel("km"); sb.setUnitsPerSegment(0.25); sb.setNumberOfSegments(2); sb.update()
    png = tmp_path / "map.png"
    settings = QgsLayoutExporter.ImageExportSettings(); settings.dpi = 50
    assert QgsLayoutExporter(lay).exportToImage(str(png), settings) == QgsLayoutExporter.Success
    assert png.stat().st_size > 1000
    prj.removeAllMapLayers()
