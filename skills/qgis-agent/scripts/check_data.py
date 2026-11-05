# -*- coding: utf-8 -*-
"""Quick inventory and check of geographic data (rasters and vectors).
Run:  bash qgis_python.sh check_data.py <file_or_folder> [...]
For each raster: CRS, pixel size, extent, nodata, min, max, mean (float64), nodata share.
For each vector: CRS, geometry type, feature count, invalid geometries, total area (ha).
Lines starting with "WARNING" point to something worth a look."""
import os
import re
import sys

import numpy as np
from osgeo import gdal, ogr, osr

gdal.UseExceptions()
ogr.UseExceptions()
EXT_R = {".tif", ".tiff", ".vrt", ".img", ".jp2", ".asc", ".nc"}
EXT_V = {".shp", ".geojson", ".kml", ".gml", ".fgb"}
INDEX = re.compile(r"(NDVI|NDMI|NBR|MNDWI|NDBI|SAVI|NDWI|EVI|BSI)", re.I)


def crs_text(wkt):
    if not wkt:
        return "no CRS", None
    s = osr.SpatialReference(wkt=wkt)
    try:
        s.AutoIdentifyEPSG()
    except RuntimeError:  # already identified or not recognised: keep the declared code
        pass
    code = s.GetAuthorityCode(None)
    name = s.GetName()
    return (f"EPSG:{code} ({name})" if code else name), s


def raster(path):
    ds = gdal.Open(path)
    gt = ds.GetGeoTransform()
    txt, s = crs_text(ds.GetProjection())
    px, py = gt[1], abs(gt[5])
    x0, y1 = gt[0], gt[3]
    x1, y0 = x0 + px * ds.RasterXSize, y1 - py * ds.RasterYSize
    print(f"\n[raster] {path}")
    print(f"  CRS       {txt}")
    print(f"  pixel     {px:g} x {py:g}   size {ds.RasterXSize} x {ds.RasterYSize}   bands {ds.RasterCount}")
    print(f"  extent    {x0:.2f} {y0:.2f} {x1:.2f} {y1:.2f}")
    if s is None:
        print("  WARNING no CRS defined")
    elif s.IsGeographic():
        print("  WARNING geographic CRS (degrees): areas and distances are wrong without reprojection")
    elif s.IsProjected():
        print(f"  pixel area  {px * py:g} m² = {px * py / 10000:g} ha")
    if abs(px - py) > 1e-6:
        print("  WARNING non-square pixels")
    for i in range(1, min(ds.RasterCount, 4) + 1):
        b = ds.GetRasterBand(i)
        a = b.ReadAsArray().astype("float64")
        nd = b.GetNoDataValue()
        ok = np.isfinite(a) if nd is None else (np.isfinite(a) & (a != nd))
        v = a[ok]
        nd_share = 100.0 * (1 - ok.mean())
        typ = gdal.GetDataTypeName(b.DataType)
        if v.size == 0:
            print(f"  band {i}  {typ}  nodata={nd}  WARNING no valid value")
            continue
        print(f"  band {i}  {typ}  nodata={nd}  min {v.min():.4f}  max {v.max():.4f}  mean {v.mean():.4f}  "
              f"distinct values {'>50' if np.unique(v[:200000]).size > 50 else np.unique(v).size}  nodata {nd_share:.1f} %")
        if typ.startswith("Float") and INDEX.search(os.path.basename(path)) and (v.min() < -1.0001 or v.max() > 1.0001):
            print("  WARNING normalised index outside [-1, 1]: reflectance not scaled?")
        if nd is None and nd_share == 0 and (v == 0).mean() > 0.05:
            print("  WARNING no nodata declared and many zeros: are the image borders counted as data?")


def vector(path):
    ds = ogr.Open(path)
    for li in range(ds.GetLayerCount()):
        lyr = ds.GetLayerByIndex(li)
        sref = lyr.GetSpatialRef()
        txt, s = crs_text(sref.ExportToWkt() if sref else None)
        n = lyr.GetFeatureCount()
        gtyp = ogr.GeometryTypeToName(lyr.GetGeomType())
        area, invalid = 0.0, 0
        for f in lyr:
            g = f.GetGeometryRef()
            if g is None:
                continue
            if not g.IsValid():
                invalid += 1
            if "Polygon" in gtyp:
                area += g.GetArea()
        lyr.ResetReading()
        print(f"\n[vector] {path} | layer {lyr.GetName()}")
        print(f"  CRS       {txt}")
        print(f"  geometry  {gtyp}   features {n}   invalid {invalid}")
        if "Polygon" in gtyp:
            if s is not None and s.IsProjected():
                print(f"  total area  {area / 10000:,.1f} ha")
            else:
                print("  area      not computed (geographic or missing CRS)")
        if invalid:
            print("  WARNING invalid geometries: repair with native:fixgeometries before any calculation")


def handle(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".gpkg":
        ds = gdal.OpenEx(path)
        if ds.GetLayerCount():
            vector(path)
        if ds.RasterCount or ds.GetSubDatasets():
            for sub, _ in (ds.GetSubDatasets() or [(path, "")]):
                raster(sub)
    elif ext in EXT_R:
        raster(path)
    elif ext in EXT_V:
        vector(path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: check_data.py <file_or_folder> [...]")
    for arg in sys.argv[1:]:
        if os.path.isdir(arg):
            for d, _, fs in sorted(os.walk(arg)):
                for fn in sorted(fs):
                    if os.path.splitext(fn)[1].lower() in EXT_R | EXT_V | {".gpkg"}:
                        try:
                            handle(os.path.join(d, fn))
                        except Exception as e:  # one unreadable file must not stop the inventory
                            print(f"\n[error] {os.path.join(d, fn)}: {e}")
        else:
            handle(arg)
