# -*- coding: utf-8 -*-
"""Downloads Sentinel-2 level 2A bands for the needed extent only, as surface reflectance.
Run:
  bash qgis_python.sh s2_download.py --ids <id1> [<id2> ...] --extent xmin ymin xmax ymax --epsg 32630 \
       --res 20 --bands B02 B03 B04 B08 B11 B12 --out data/sentinel2 [--scl] [--collection sentinel-2-c1-l2a]
--ids         ids of the tiles from one pass (given by s2_search.py, with the same --collection)
--extent      in the --epsg CRS, in metres; keep multiples of --res for a clean grid
--collection  sentinel-2-c1-l2a (default) or the mirror sentinel-2-l2a (only if the default host is unreachable)
Reflectance = value x scale + offset, clamped to [0, 1]; nodata = -9999. The scale and offset come from the
catalogue, except when the item says the offset is already applied to the values (the sentinel-2-l2a mirror):
then no offset is subtracted, because its metadata still declares -0.1 and applying it again makes every band
0.1 too low. Going from 10 m to 20 m averages the original pixels; a band is never resampled below its native
resolution."""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

import numpy as np

API = "https://earth-search.aws.element84.com/v1/collections/{}/items/"
COLLECTIONS = ("sentinel-2-c1-l2a", "sentinel-2-l2a")
KEYS = {"B01": "coastal", "B02": "blue", "B03": "green", "B04": "red", "B05": "rededge1", "B06": "rededge2",
        "B07": "rededge3", "B08": "nir", "B8A": "nir08", "B09": "nir09", "B11": "swir16", "B12": "swir22"}
CO = ["COMPRESS=DEFLATE", "PREDICTOR=3", "TILED=YES"]
NODATA = -9999.0
LOW_VISIBLE = 0.03   # over land, median visible reflectance is rarely lower


def offset_already_applied(items):
    """True when the items' values already include the offset (sentinel-2-l2a mirror)."""
    return any(it["properties"].get("earthsearch:boa_offset_applied") for it in items)


def band_rule(item, key, offset_applied):
    """Scale, offset to apply, and native resolution for one band of one item."""
    rb = (item["assets"][key].get("raster:bands") or [{}])[0]
    scale = rb.get("scale", 0.0001)
    offset = 0.0 if offset_applied else rb.get("offset", 0.0)
    native = rb.get("spatial_resolution") or item["assets"][key].get("gsd")
    return scale, offset, native


def reflectance(dn, scale, offset):
    """Raw values to reflectance clamped to [0, 1]; 0 (no data) becomes NODATA."""
    dn = np.asarray(dn)   # float32 from the warp: keep the same arithmetic as the published reference outputs
    return np.where(dn > 0, np.clip(dn * scale + offset, 0.0, 1.0), NODATA).astype("float32")


def low_visible_bands(medians):
    """Visible bands whose median reflectance is implausibly low (a sign of a double offset)."""
    return [b for b in ("B02", "B03", "B04") if b in medians and medians[b] < LOW_VISIBLE]


def other_collection(collection):
    return [c for c in COLLECTIONS if c != collection][0]


def main(argv=None):
    from osgeo import gdal
    gdal.UseExceptions()
    for k, v in {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
                 "GDAL_HTTP_MULTIRANGE": "YES", "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES": "YES",
                 "VSI_CACHE": "TRUE"}.items():
        gdal.SetConfigOption(k, v)

    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="+", required=True)
    ap.add_argument("--extent", nargs=4, type=float, required=True)
    ap.add_argument("--epsg", type=int, required=True)
    ap.add_argument("--res", type=float, default=20)
    ap.add_argument("--bands", nargs="+", default=["B02", "B03", "B04", "B08", "B11", "B12"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--scl", action="store_true", help="also download the scene classification (clouds, snow...)")
    ap.add_argument("--collection", default=COLLECTIONS[0], choices=COLLECTIONS)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)

    try:
        items = [json.load(urllib.request.urlopen(API.format(a.collection) + i, timeout=60)) for i in a.ids]
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR item not found in {a.collection} ({e}). Ids differ between collections: "
                 "take them from s2_search.py run with the same --collection.")
    days = {it["properties"]["datetime"][:10] for it in items}
    if len(days) > 1:
        print("WARNING tiles from different dates:", sorted(days))
    applied = offset_already_applied(items)
    meta = {"collection": a.collection, "ids": a.ids, "dates": sorted(days), "epsg": a.epsg, "res": a.res,
            "extent": a.extent, "offset_already_applied_in_values": applied, "bands": {}}
    if applied:
        print("note: these items already include the offset in their values; no offset is subtracted")

    medians = {}
    for b in a.bands:
        key = KEYS[b]
        scale, offset, native = band_rule(items[0], key, applied)
        native = native or a.res
        if a.res < native:
            print(f"WARNING {b}: native resolution {native} m, requested {a.res} m (nearest neighbour)")
        hrefs = ["/vsicurl/" + it["assets"][key]["href"] for it in items]
        try:
            ds = gdal.Warp("", hrefs, format="MEM", dstSRS=f"EPSG:{a.epsg}", outputBounds=a.extent, xRes=a.res,
                           yRes=a.res, resampleAlg="average" if a.res >= native else "near", srcNodata=0,
                           dstNodata=0, overviewLevel="NONE",   # average the original pixels, not the overviews
                           outputType=gdal.GDT_Float32)
        except RuntimeError as e:
            host = urllib.parse.urlparse(items[0]["assets"][key]["href"]).netloc
            sys.exit(f"ERROR cannot read the image files on {host}: {str(e).splitlines()[0]}\n"
                     f"Check network access to {host}. If it stays blocked, search again with --collection "
                     f"{other_collection(a.collection)} and download with the same --collection "
                     "(this script handles its offset correctly).")
        refl = reflectance(ds.GetRasterBand(1).ReadAsArray(), scale, offset)
        o = gdal.GetDriverByName("GTiff").Create(os.path.join(a.out, f"{b}.tif"), ds.RasterXSize, ds.RasterYSize, 1,
                                                 gdal.GDT_Float32, CO)
        o.SetGeoTransform(ds.GetGeoTransform())
        o.SetProjection(ds.GetProjection())
        bd = o.GetRasterBand(1)
        bd.WriteArray(refl)
        bd.SetNoDataValue(NODATA)
        bd.SetDescription(f"{b} reflectance")
        o = None
        v = refl[refl > NODATA]
        medians[b] = float(np.median(v))
        meta["bands"][b] = {"scale": scale, "offset_used": offset, "native_m": native}
        print(f"{b}  {ds.RasterXSize} x {ds.RasterYSize}  reflectance min {v.min():.4f}  median {np.median(v):.4f}  "
              f"max {v.max():.4f}  nodata {100 * (1 - v.size / refl.size):.2f} %", flush=True)

    low = low_visible_bands(medians)
    if low:
        print(f"WARNING median reflectance of {', '.join(low)} below {LOW_VISIBLE}: if the area is mostly land, the "
              "offset may have been applied twice. Check the values against the item's metadata before computing "
              "indices.")

    if a.scl:
        hrefs = ["/vsicurl/" + it["assets"]["scl"]["href"] for it in items]
        gdal.Warp(os.path.join(a.out, "SCL.tif"), hrefs, dstSRS=f"EPSG:{a.epsg}", outputBounds=a.extent,
                  xRes=a.res, yRes=a.res, resampleAlg="near", srcNodata=0, dstNodata=0,
                  creationOptions=["COMPRESS=DEFLATE", "TILED=YES"])
        print("SCL ok")

    if {"B02", "B03", "B04"} <= set(a.bands):
        gdal.BuildVRT(os.path.join(a.out, "natural_colour.vrt"),
                      [os.path.join(a.out, f"{b}.tif") for b in ("B04", "B03", "B02")], separate=True)
        print("natural colour composite: natural_colour.vrt (stretch from 0 to about 0.2)")
    json.dump(meta, open(os.path.join(a.out, "s2_metadata.json"), "w"), indent=1)
    print("done:", a.out)


if __name__ == "__main__":
    main()
