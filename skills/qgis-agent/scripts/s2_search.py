# -*- coding: utf-8 -*-
"""Searches Sentinel-2 level 2A images over an area (open Earth Search STAC catalogue, no account needed).
Run:
  bash qgis_python.sh s2_search.py --bbox -5.40 33.20 -4.90 33.70 --start 2026-05-01 --end 2026-06-30 \
       [--clouds 20] [--scl 3] [--collection sentinel-2-c1-l2a]
--bbox        lon_min lat_min lon_max lat_max (WGS 84 degrees)
--clouds      maximum cloud cover of the tile, in %
--scl N       for the N best dates, measures clouds, shadows and snow over the area itself (SCL layer)
--collection  sentinel-2-c1-l2a (default) or sentinel-2-l2a, a mirror stored on another host. Use the mirror
              only if the default host cannot be reached, and pass the same --collection to s2_download.py.
Dates are grouped by day: take all tiles from the same day (same pass) for a mosaic."""
import argparse
import json
import urllib.parse
import urllib.request
from collections import defaultdict

API = "https://earth-search.aws.element84.com/v1"
COLLECTIONS = ("sentinel-2-c1-l2a", "sentinel-2-l2a")


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def search(bbox, start, end, clouds, collection):
    body = {"collections": [collection], "bbox": bbox, "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z",
            "query": {"eo:cloud_cover": {"lte": clouds}}, "limit": 100}
    items, url = [], f"{API}/search"
    while url:
        page = post(url, body)
        items += page["features"]
        nxt = [l for l in page.get("links", []) if l.get("rel") == "next"]
        url, body = (nxt[0]["href"], nxt[0].get("body", body)) if nxt else (None, None)
    return items


def scl_summary(a):
    """Shares (%) of an SCL array: coverage, clouds (8, 9, 10), shadows (3), snow (11), saturated (1)."""
    import numpy as np
    a = np.asarray(a)
    v = a[a > 0]
    if v.size == 0:
        return None
    pc = lambda codes: 100.0 * np.isin(v, codes).mean()
    return {"covered %": 100.0 * v.size / a.size, "clouds %": pc([8, 9, 10]), "shadows %": pc([3]),
            "snow %": pc([11]), "saturated %": pc([1])}


def scl_shares(items, bbox):
    """Shares of clouds, shadows and snow over the bbox, from the SCL layer (about 60 m)."""
    from osgeo import gdal
    gdal.UseExceptions()
    gdal.SetConfigOption("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
    hrefs = ["/vsicurl/" + it["assets"]["scl"]["href"] for it in items]
    ds = gdal.Warp("", hrefs, format="MEM", dstSRS="EPSG:4326", outputBounds=bbox, xRes=0.0006, yRes=0.0006,
                   resampleAlg="near", srcNodata=0, dstNodata=0)
    return scl_summary(ds.ReadAsArray())


def group_passes(items):
    """Groups tiles by pass (day, satellite), sorted by mean tile cloud cover."""
    days = defaultdict(list)
    for it in items:
        days[(it["properties"]["datetime"][:10], it["properties"].get("platform", "?"))].append(it)
    return sorted(days.items(), key=lambda kv: sum(i["properties"]["eo:cloud_cover"] for i in kv[1]) / len(kv[1]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bbox", nargs=4, type=float, required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--clouds", type=float, default=20)
    ap.add_argument("--scl", type=int, default=0)
    ap.add_argument("--collection", default=COLLECTIONS[0], choices=COLLECTIONS)
    a = ap.parse_args()
    items = search(a.bbox, a.start, a.end, a.clouds, a.collection)
    ranked = group_passes(items)
    print(f"collection {a.collection}: {len(items)} tiles, {len(ranked)} passes (sorted by mean tile cloud cover)\n")
    scl_ok = True
    for k, ((day, sat), its) in enumerate(ranked):
        cc = sum(i["properties"]["eo:cloud_cover"] for i in its) / len(its)
        tiles = ", ".join(sorted(i["properties"].get("s2:mgrs_tile", i["id"].split("_")[1]) for i in its))
        print(f"{day}  {sat:12}  tile clouds {cc:5.1f} %   {len(its)} tile(s): {tiles}")
        if k < a.scl and scl_ok:
            try:
                r = scl_shares(its, a.bbox)
            except RuntimeError as e:
                host = urllib.parse.urlparse(its[0]["assets"]["scl"]["href"]).netloc
                print(f"            WARNING cannot read the image files on {host}: {str(e).splitlines()[0]}")
                print("            The catalogue answers but the image storage does not: check network access to"
                      f" {host}. If it stays blocked, rerun with --collection "
                      f"{[c for c in COLLECTIONS if c != a.collection][0]}.")
                scl_ok = False
                r = None
            if r:
                print("            over the area: " + "  ".join(f"{n} {v:.2f}" for n, v in r.items()))
                if r["covered %"] < 99.5:
                    print("            WARNING these tiles do not fully cover the area")
        if k < 10 or k < a.scl:
            print("            ids: " + " ".join(i["id"] for i in its))
