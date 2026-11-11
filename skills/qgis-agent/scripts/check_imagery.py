# -*- coding: utf-8 -*-
"""Checks Sentinel-2 level 2A bands that are already in a folder (sent by someone, downloaded by hand or with another
tool) before any calculation: the reflectance formula to use and the evidence for it, what the pixels say about it,
and how cloudy the scene is when the folder has no mask band.
Run:  bash qgis_python.sh check_imagery.py <folder> [--area zone.geojson] [--mask-out cloud_estimate.tif]
--area      polygons of the study area (any vector format): pixel and cloud figures are measured inside them
--mask-out  when there is no mask band, also write the cloud estimate as a raster on the bands' grid
            (1 = likely cloud, 0 = clear, 255 = no data); with several dates, the date is added to the name
Metadata read when present: a STAC item (item.json, or any .json with "assets") and the ESA product metadata
(MTD_MSIL2A.xml). Bands are recognised by name (B04, B8A, red, nir...) and grouped by the date in the file name.
The formula comes from the metadata when there is some. The pixels can rule an offset out, but over bright ground
(no value below 1000) they cannot tell the two formulas apart: then only the metadata decides.
Lines starting with "WARNING" need an answer before computing anything."""
import argparse
import datetime
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s2_download import KEYS, offset_already_applied   # noqa: E402  same rule as the download script

RASTERS = {".tif", ".tiff", ".jp2", ".vrt"}
MTD_BANDS = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B10", "B11", "B12"]
NAMES = {v: k for k, v in KEYS.items()}            # catalogue key (red, nir...) -> band (B04, B08...)
VISIBLE = ("B01", "B02", "B03", "B04")
BASELINE_04 = datetime.date(2022, 1, 25)           # processing baseline 04.00: the -1000 offset starts
SCALE = 0.0001
OFFSET = -0.1
DARK_SHARE = 1.0      # % of values below 1000 (reflectance 0.1) needed to test the offset
LOW_VISIBLE = 0.03    # over land, median visible reflectance is rarely lower
CLOUD_SHARE = 1.0     # % of the area: above it, the scene must not be averaged as it is
MAX_PIXELS = 25_000_000

BAND_RE = re.compile(r"(?<![A-Za-z0-9])(B8A|B0?[1-9]|B1[0-2])(?![A-Za-z0-9])", re.I)
KEY_RE = re.compile(r"(?<![A-Za-z0-9])(coastal|blue|green|rededge[123]|red|nir0[89]|nir|swir16|swir22)(?![A-Za-z0-9])",
                    re.I)
MASK_RE = re.compile(r"(?<![A-Za-z0-9])(SCL|QA_PIXEL|CLM|FMASK|MSK_CLD\w*|CLD\w*|cloud\w*|mask\w*)(?![A-Za-z0-9])",
                     re.I)
DATE_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?!\d)")
YEAR_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
MIRROR_ID = re.compile(r"S2[A-D]_\d{1,2}[A-Z]{3}_\d{8}_\d+_L2A", re.I)   # Earth Search sentinel-2-l2a item ids
BASELINE_RE = re.compile(r"_N(\d{2})(\d{2})(?![0-9])")                   # ESA product names: ..._N0510_...
LANDSAT_RE = re.compile(r"(?<![A-Za-z0-9])L[CEOT]0[4-9]_|_MTL\.(txt|json|xml)$", re.I)


# ---------- names, dates, metadata ----------

def band_of(name):
    """Band id (B04, B8A...), 'SCL' or another mask name, or None, from a file name."""
    stem = os.path.splitext(os.path.basename(name))[0]
    m = MASK_RE.search(stem)
    if m and m.group(1).upper() == "SCL":
        return "SCL"
    b = BAND_RE.search(stem)
    if b:
        b = b.group(1).upper()
        return b if b == "B8A" else f"B{int(b[1:]):02d}"
    if m:
        return "mask:" + m.group(1)
    k = KEY_RE.search(stem)
    return NAMES.get(k.group(1).lower()) if k else None


def date_of(name):
    """Acquisition date (YYYY-MM-DD) or year (YYYY) found in a file name, else None."""
    m = DATE_RE.search(name)
    if m:
        return "-".join(m.groups())
    m = YEAR_RE.search(name)
    return m.group(1) if m else None


def same_date(a, b):
    """True when two dates agree as far as both are known (a year matches any day of that year)."""
    if not a or not b:
        return False
    return a[:len(b)] == b[:len(a)]


def read_item(path):
    """A STAC item (dict) from a .json file, or None."""
    try:
        with open(path, encoding="utf-8") as f:
            it = json.load(f)
    except (ValueError, OSError):
        return None
    if not (isinstance(it, dict) and "assets" in it and "properties" in it):
        return None
    it["file"] = os.path.basename(path)
    return it


def read_mtd(path):
    """The fields of an ESA MTD_MSIL2A.xml (or MTD_MSIL1C.xml) that decide the reflectance formula."""
    out = {"path": path, "offsets": {}, "date": None, "baseline": None, "quantification": None, "cloud": None,
           "level": "1C" if "1C" in os.path.basename(path).upper() else "2A", "uri": None}
    for el in ET.parse(path).iter():
        tag, text = el.tag.split("}")[-1], (el.text or "").strip()
        if tag == "PRODUCT_START_TIME" and text:
            out["date"] = text[:10]
        elif tag == "PROCESSING_BASELINE" and text:
            out["baseline"] = text
        elif tag in ("BOA_QUANTIFICATION_VALUE", "QUANTIFICATION_VALUE") and text:
            out["quantification"] = float(text)
        elif tag in ("BOA_ADD_OFFSET", "RADIO_ADD_OFFSET") and text:
            i = int(el.get("band_id", -1))
            if 0 <= i < len(MTD_BANDS):
                out["offsets"][MTD_BANDS[i]] = float(text)
        elif tag == "Cloud_Coverage_Assessment" and text:
            out["cloud"] = float(text)
        elif tag == "PRODUCT_URI" and text:
            out["uri"] = text
    return out


def baseline_of(names):
    """Processing baseline (as a float, 5.1 for N0510) found in ESA product names, else None."""
    for n in names:
        m = BASELINE_RE.search(n)
        if m:
            return int(m.group(1)) + int(m.group(2)) / 100
    return None


def after_baseline_04(date):
    """True if acquired on or after 25 January 2022, False if before, None if the date cannot tell."""
    if not date:
        return None
    if len(date) == 4:
        return True if int(date) >= 2023 else (False if int(date) <= 2021 else None)
    try:
        return datetime.date.fromisoformat(date) >= BASELINE_04
    except ValueError:                     # a number that looks like a date but is not one
        return None


# ---------- the formula ----------

def rule(scale, offset, status, evidence):
    return {"scale": scale, "offset": offset, "status": status, "evidence": evidence}


def formula_text(scale, offset):
    if offset == 0:
        return f"reflectance = value x {scale:g}"
    return f"reflectance = value x {scale:g} {'-' if offset < 0 else '+'} {abs(offset):g}"


def rule_from_item(item, bands):
    """Scale and offset for the bands of a STAC item, reading earthsearch:boa_offset_applied before raster:bands."""
    props = item["properties"]
    declared = None
    for b in sorted(bands) + ["B04"]:
        a = item["assets"].get(KEYS.get(b, b)) or item["assets"].get(b) or {}
        rb = (a.get("raster:bands") or [{}])[0]
        if "scale" in rb or "offset" in rb:
            declared = (rb.get("scale", SCALE), rb.get("offset", 0.0))
            break
    scale, offset = declared or (SCALE, 0.0)
    base = f"{item['file']} ({item.get('id', 'STAC item')}"
    base += f", processing baseline {props['s2:processing_baseline']})" if props.get("s2:processing_baseline") else ")"
    if offset_already_applied([item]):
        ev = [f"{base} says earthsearch:boa_offset_applied = true: the values already include the offset.",
              f"Its raster:bands still declares offset {offset:g}. Do not subtract it again: every band would be "
              f"{abs(offset):g} too low and every index skewed."]
        return rule(scale, 0.0, "documented", ev)
    if declared:
        ev = [f"{base}: raster:bands declares scale {scale:g} and offset {offset:g}, and the item does not say the "
              "offset is already applied."]
        return rule(scale, offset, "documented", ev)
    return None


def rule_from_mtd(mtd, bands):
    """Scale and offset from ESA's product metadata (BOA_ADD_OFFSET, BOA_QUANTIFICATION_VALUE)."""
    q = mtd["quantification"] or 10000.0
    name = os.path.basename(mtd["path"])
    base = f"{name} (processing baseline {mtd['baseline'] or 'not given'})"
    offs = {mtd["offsets"].get(b) for b in bands if b in mtd["offsets"]}
    ev = []
    if mtd["level"] == "1C":
        ev.append(f"{name} describes a level 1C product: top-of-atmosphere reflectance, not surface reflectance.")
    if not mtd["offsets"]:
        ev.insert(0, f"{base} gives no BOA_ADD_OFFSET: reflectance = value / {q:g}.")
        return rule(1 / q, 0.0, "documented", ev)
    if len(offs) > 1:
        ev.insert(0, f"{base} gives different offsets per band: {mtd['offsets']}.")
    off = sorted(offs)[0] if offs else sorted(set(mtd["offsets"].values()))[0]
    ev.insert(0, f"{base} gives BOA_ADD_OFFSET {off:g} and quantification {q:g}: "
                 f"reflectance = (value {'-' if off < 0 else '+'} {abs(off):g}) / {q:g}.")
    return rule(1 / q, off / q, "documented", ev)


def rule_from_names(names, date):
    """Best guess when the folder has no metadata: Earth Search mirror ids, baseline in the name, then the date."""
    if any(MIRROR_ID.search(n) for n in names):
        return rule(SCALE, 0.0, "likely", [
            "No metadata, but the file names follow the item ids of Earth Search's sentinel-2-l2a mirror "
            "(like S2A_30SUB_20240830_0_L2A), whose values already include the offset. Get the item (item.json) "
            "to confirm."])
    pb = baseline_of(names)
    if pb is not None:
        if pb >= 4:
            return rule(SCALE, OFFSET, "likely", [
                f"No metadata, but the product name gives processing baseline {pb:05.2f}: baselines 04.00 and later "
                "store reflectance + 0.1 (offset -1000)."])
        return rule(SCALE, 0.0, "likely", [
            f"No metadata, but the product name gives processing baseline {pb:05.2f}: before 04.00 there is no "
            "offset."])
    after = after_baseline_04(date)
    if after:
        return rule(SCALE, OFFSET, "assumed", [
            f"No metadata in the folder. Acquired {date}, after 25 January 2022: every level 2A product processed "
            "by ESA since then (baseline 04.00 or later) stores reflectance + 0.1, so offset -1000 is assumed.",
            "This is an assumption: if the files went through another tool or the Earth Search mirror, the offset "
            "may already be applied. Ask where they come from, and tell the user which rule you used."])
    when = f"Acquired {date}" if date else "No date in the file names"
    why = (", before 25 January 2022: the original products have no offset, but the reprocessed archive "
           "(baseline 05.00 and later) has one." if after is False else ": the date cannot tell whether there is an "
           "offset.")
    return rule(SCALE, None, "unknown", [f"No metadata in the folder. {when}{why}"])


# ---------- pixels ----------

def read_band(path, area=None):
    """Values of the first band as float64 with invalid pixels as NaN (0 counts as no data for integer bands),
    the grid (geotransform, projection, shape) and whether the values are floats. Large rasters are read
    decimated: the statistics stay valid, but no mask can be written."""
    from osgeo import gdal
    gdal.UseExceptions()
    ds = gdal.Open(path)
    b = ds.GetRasterBand(1)
    w, h = ds.RasterXSize, ds.RasterYSize
    f = max(1, int(np.ceil(np.sqrt(w * h / MAX_PIXELS))))
    bw, bh = w // f, h // f
    a = b.ReadAsArray(buf_xsize=bw, buf_ysize=bh).astype("float64")
    gt = list(ds.GetGeoTransform())
    gt[1], gt[2], gt[4], gt[5] = gt[1] * w / bw, gt[2] * w / bw, gt[4] * h / bh, gt[5] * h / bh
    is_float = gdal.GetDataTypeName(b.DataType).startswith("Float")
    nd = b.GetNoDataValue()
    bad = ~np.isfinite(a)
    if nd is not None:
        bad |= a == nd
    if not is_float:
        bad |= a <= 0
    if area:
        bad |= ~area_mask(area, gt, ds.GetProjection(), a.shape)
    a[bad] = np.nan
    return a, {"gt": tuple(gt), "wkt": ds.GetProjection(), "shape": a.shape, "decimated": f > 1}, is_float


def area_mask(vector_path, gt, wkt, shape):
    """True inside the polygons of a vector file, on a raster grid (pixel centres)."""
    from osgeo import gdal, ogr, osr
    gdal.UseExceptions()
    ogr.UseExceptions()
    dst = osr.SpatialReference(wkt=wkt)
    dst.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    drv = ogr.GetDriverByName("MEM") or ogr.GetDriverByName("Memory")
    mem = drv.CreateDataSource("area")
    out = mem.CreateLayer("area", dst, ogr.wkbMultiPolygon)
    src = ogr.Open(vector_path)
    for li in range(src.GetLayerCount()):
        lyr = src.GetLayerByIndex(li)
        sref = lyr.GetSpatialRef()
        tr = None
        if sref is not None:
            sref.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            if not sref.IsSame(dst):
                tr = osr.CoordinateTransformation(sref, dst)
        for feat in lyr:
            g = feat.GetGeometryRef()
            if g is None:
                continue
            g = g.Clone()
            if tr:
                g.Transform(tr)
            nf = ogr.Feature(out.GetLayerDefn())
            nf.SetGeometry(g)
            out.CreateFeature(nf)
    r = gdal.GetDriverByName("MEM").Create("", shape[1], shape[0], 1, gdal.GDT_Byte)
    r.SetGeoTransform(gt)
    r.SetProjection(wkt)
    gdal.RasterizeLayer(r, [1], out, burn_values=[1])
    return r.GetRasterBand(1).ReadAsArray() == 1


def band_stats(values, scale, offset, already):
    """For one band: share of values below reflectance 0.1 before any offset (the pixels that a -0.1 offset turns
    negative), and the median and negative share with the formula (offset None = undecided, taken as 0)."""
    v = values[np.isfinite(values)]
    if not already:
        v = v[v > 0]                         # 0 is no data in Sentinel-2 files
    if v.size == 0:
        return None
    if already:
        r = v
        dark = 100.0 * (r < -OFFSET).mean()
        neg = 100.0 * (r <= 0).mean()        # a writer that clamps to [0, 1] turns negative values into 0
    else:
        r0 = v * scale
        dark = 100.0 * (r0 < -OFFSET).mean()
        r = r0 + (offset or 0.0)
        neg = 100.0 * (r < 0).mean()
    return {"n": int(v.size), "dark %": dark, "negative %": neg, "median": float(np.median(r))}


def judge_offset(stats, offset, status):
    """What the pixels say about the offset: (status after the pixels, lines to print)."""
    vis = {b: s for b, s in stats.items() if b in VISIBLE} or stats
    dark_band = max(vis, key=lambda b: vis[b]["dark %"])
    dark = vis[dark_band]["dark %"]
    lines = []
    if dark <= DARK_SHARE:
        lines.append(f"Almost no value below 1000 (highest share: {dark_band}, {dark:.1f} %), so the pixels cannot "
                     "tell \"value x 0.0001\" from \"value x 0.0001 - 0.1\" here: raw values with the offset never "
                     "go below 1000, and ground with no dark pixel looks the same without it.")
        if status == "unknown":
            lines.append("WARNING no metadata and the pixels cannot decide: ask where the files come from (STAC item, "
                         "MTD_MSIL2A.xml or the product name) before computing anything.")
        elif status in ("assumed", "likely"):
            lines.append("The formula rests on the assumption above: say so in the plan and the report.")
        else:
            lines.append("The formula rests on the metadata above. A plausible-looking result is not a check.")
        return status, lines
    detail = f"{dark:.1f} % of {dark_band} is below 1000"
    if offset is None:
        lines.append(f"{detail}: an offset of -0.1 would make those pixels negative, so the values do not include "
                     "it. Use value x 0.0001.")
        return "from the pixels", lines
    if offset < 0:
        lines.append(f"WARNING {detail}: with this formula those pixels are negative reflectance. The offset seems "
                     "to be already in the values (Earth Search mirror, or an export that applied it). Check where "
                     "the files come from before computing anything.")
        return "contradicted", lines
    lines.append(f"{detail}: an offset of -0.1 would make those pixels negative, which agrees with this formula.")
    return status, lines


def hot_clouds(blue, red):
    """Bright, bluish pixels: the haze test of Fmask (Zhu and Woodcock 2012), blue - 0.5 x red - 0.08 > 0, on
    surface reflectance. It finds thick cloud with few false alarms, misses thin cloud and every shadow, and also
    counts snow, salt flats and white roofs."""
    return (blue - 0.5 * red - 0.08) > 0


def scl_shares(path, area):
    a = read_band(path, area)[0]
    v = a[np.isfinite(a)]
    if v.size == 0:
        return None
    pc = lambda codes: 100.0 * np.isin(v, codes).mean()   # noqa: E731
    return {"clouds %": pc([8, 9, 10]), "shadows %": pc([3]), "snow %": pc([11])}


def write_mask(path, cloud, valid, grid):
    from osgeo import gdal
    gdal.UseExceptions()
    out = np.where(valid, cloud.astype("uint8"), 255).astype("uint8")
    ds = gdal.GetDriverByName("GTiff").Create(path, out.shape[1], out.shape[0], 1, gdal.GDT_Byte,
                                              ["COMPRESS=DEFLATE", "TILED=YES"])
    ds.SetGeoTransform(grid["gt"])
    ds.SetProjection(grid["wkt"])
    b = ds.GetRasterBand(1)
    b.WriteArray(out)
    b.SetNoDataValue(255)
    b.SetDescription("cloud estimate (Fmask haze test): 1 likely cloud, 0 clear")
    ds = None


# ---------- one scene ----------

def check_scene(date, files, items, mtds, other_masks, area, mask_out, s2_meta):
    say = print
    bands = {b: p for p, b in files.items() if b and not b.startswith("mask:") and b != "SCL"}
    scl = [p for p, b in files.items() if b == "SCL"]
    names = [os.path.basename(p) for p in files]
    say(f"\n== Scene {date or '(no date in the names)'}: {', '.join(sorted(bands)) or 'no band'}"
        f"{' + SCL' if scl else ''}")
    for p in sorted(files):
        say(f"  file      {os.path.basename(p)}")
    if not bands:
        say("  no spectral band recognised in the file names (B02, B04, red, nir...)")
        return

    data = {b: read_band(p, area) for b, p in sorted(bands.items())}
    floats = [b for b, (_, _, f) in data.items() if f]
    reflectance_already = bool(floats) and all(
        np.nanpercentile(data[b][0], 99) <= 2 for b in floats if np.isfinite(data[b][0]).any())

    item = next((it for it in items if same_date(it["properties"].get("datetime", "")[:10], date)
                 or any(it.get("id", "\0") in n for n in names)), None)
    if item is None and len(items) == 1 and date is None:
        item = items[0]
    mtd = next((m for m in mtds if same_date(m["date"], date)), None)
    if mtd is None and len(mtds) == 1 and date is None:
        mtd = mtds[0]
    if items and item is None:
        say("  note      the STAC item(s) in the folder are for other dates: "
            + ", ".join(it["properties"].get("datetime", "?")[:10] for it in items))
    if mtds and mtd is None:
        say("  note      the MTD file(s) in the folder are for other dates: "
            + ", ".join(m["date"] or "?" for m in mtds))

    if reflectance_already:
        ev = ["The values are floats between 0 and 1: already reflectance, no scale or offset to apply."]
        if s2_meta:
            ev.append(f"{os.path.basename(s2_meta)}: written by s2_download.py, which handles the offset.")
        r = rule(1.0, 0.0, "already reflectance", ev)
    else:
        r = (rule_from_item(item, bands) if item else None) or (rule_from_mtd(mtd, bands) if mtd else None) \
            or rule_from_names(names, date)
        if item and mtd and r["evidence"][0].startswith(item["file"]):
            r["evidence"].append(f"{os.path.basename(mtd['path'])} describes ESA's original product; the item "
                                 "describes these files, so the item wins.")

    stats = {b: band_stats(a, r["scale"], r["offset"], reflectance_already) for b, (a, _, _) in data.items()}
    stats = {b: s for b, s in stats.items() if s}
    if not stats:
        say("  WARNING no valid pixel (inside the area)")
        return
    status, pixel_lines = judge_offset(stats, r["offset"], r["status"]) if not reflectance_already else (
        r["status"], [])
    if status == "from the pixels":
        r["offset"] = 0.0
        stats = {b: band_stats(data[b][0], r["scale"], 0.0, False) for b in stats}
    if status == "contradicted" and r["status"] == "assumed":
        status = "undecided"

    if status in ("unknown", "undecided"):
        say(f"  formula   UNDECIDED: {formula_text(SCALE, 0.0)}  or  {formula_text(SCALE, OFFSET)}")
    else:
        say(f"  formula   {formula_text(r['scale'], r['offset'])}   ({status})")
    for i, e in enumerate(r["evidence"]):
        say(f"  {'evidence' if i == 0 else '':9} - {e}")

    say(f"  pixels    {'band':5} {'<1000':>7} {'median':>7} {'negative':>9}   (median and negative share with "
        f"{'the formula above' if status not in ('unknown', 'undecided') else 'no offset'})")
    for b, s in stats.items():
        dark = f"{s['dark %']:.1f} %" if not reflectance_already else "-"
        say(f"            {b:5} {dark:>7} {s['median']:7.3f} {s['negative %']:7.1f} %")
    for line in pixel_lines:
        say(f"  {'':9} {line}")
    if reflectance_already:
        vis = {b: s for b, s in stats.items() if b in VISIBLE} or stats
        worst = max(vis, key=lambda b: vis[b]["negative %"])
        if vis[worst]["negative %"] > DARK_SHARE:
            say(f"  WARNING {vis[worst]['negative %']:.1f} % of {worst} is zero or negative: an offset may have "
                "been subtracted twice before these files were written.")
    low = [b for b in ("B02", "B03", "B04") if b in stats and stats[b]["median"] < LOW_VISIBLE]
    if low and status not in ("unknown", "undecided"):
        say(f"  WARNING median reflectance of {', '.join(low)} below {LOW_VISIBLE}: unless the area is mostly "
            "water, the offset may have been applied twice.")

    # clouds
    tile = []
    if item and item["properties"].get("eo:cloud_cover") is not None:
        tile.append(f"{item['file']} gives {item['properties']['eo:cloud_cover']:.1f} %")
    if mtd and mtd["cloud"] is not None:
        tile.append(f"{os.path.basename(mtd['path'])} gives {mtd['cloud']:.1f} %")
    tile_txt = (" and ".join(tile) + " cloud for the whole tile (about 110 km across), not for this area.") \
        if tile else ""
    if scl:
        s = scl_shares(scl[0], area)
        if s:
            say(f"  clouds    SCL band: clouds (8, 9, 10) {s['clouds %']:.1f} %, shadows (3) {s['shadows %']:.1f} %, "
                f"snow (11) {s['snow %']:.1f} %{' inside the area' if area else ''}. Mask these codes (and 0, 1) "
                "before averaging.")
        return
    if other_masks:
        say(f"  clouds    mask band found: {', '.join(os.path.basename(p) for p in other_masks)}. Use it to exclude "
            "clouds before averaging (codes in its product guide).")
        return
    if "B02" not in data or "B04" not in data or data["B02"][1]["shape"] != data["B04"][1]["shape"]:
        say("  clouds    No mask band (SCL or similar), and no blue band (B02) on the red band's grid (B04): no "
            "cloud estimate from these bands.")
        if tile_txt:
            say(f"  {'':9} {tile_txt}")
        say(f"  {'':9} Look at the scene, or get the SCL band, before averaging; report what you did.")
        return
    off = 0.0 if r["offset"] is None or reflectance_already else r["offset"]
    scale = 1.0 if reflectance_already else r["scale"]
    blue, red = data["B02"][0] * scale + off, data["B04"][0] * scale + off
    valid = np.isfinite(blue) & np.isfinite(red)
    cloud = np.zeros(blue.shape, bool)
    cloud[valid] = hot_clouds(blue[valid], red[valid])
    share = 100.0 * cloud[valid].mean() if valid.any() else 0.0
    where = "of the area" if area else "of the scene"
    if share > CLOUD_SHARE:
        say(f"  WARNING no mask band (SCL or similar), and {share:.1f} % {where} looks like cloud (Fmask haze test "
            "on B02 and B04).")
        say(f"  {'':9} This is a lower bound: thin cloud and cloud shadows are mostly missed. Do not average this "
            "scene as it is: mask it (with the SCL band if you can get it, or this estimate, saying so) and report "
            "the cloud share with the result.")
    else:
        say(f"  clouds    no mask band; {share:.1f} % {where} looks like cloud (Fmask haze test on B02 and B04). "
            "Thin cloud and shadows are not detected: look at a natural colour composite before averaging.")
    if tile_txt:
        say(f"  {'':9} {tile_txt}")
    if mask_out:
        if data["B02"][1]["decimated"]:
            say("  mask      not written: the bands are too large; clip them to the area first, then rerun.")
        else:
            write_mask(mask_out, cloud, valid, data["B02"][1])
            say(f"  mask      {mask_out} (1 = likely cloud, 0 = clear, 255 = no data)")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder")
    ap.add_argument("--area", help="polygons of the study area (any vector format)")
    ap.add_argument("--mask-out", help="write the cloud estimate here when there is no mask band")
    a = ap.parse_args(argv)
    if not os.path.isdir(a.folder):
        sys.exit(f"ERROR not a folder: {a.folder}")

    files, items, mtds, landsat, s2_meta = {}, [], [], [], None
    for d, _, fs in sorted(os.walk(a.folder)):
        for fn in sorted(fs):
            p = os.path.join(d, fn)
            ext = os.path.splitext(fn)[1].lower()
            if LANDSAT_RE.search(fn):
                landsat.append(p)
            elif ext in RASTERS:
                files[p] = band_of(fn)
            elif fn == "s2_metadata.json":
                s2_meta = p
            elif ext == ".json":
                it = read_item(p)
                if it:
                    items.append(it)
            elif ext == ".xml" and fn.upper().startswith(("MTD_MSIL2A", "MTD_MSIL1C")):
                mtds.append(read_mtd(p))

    print(f"Imagery check: {a.folder}")
    if a.area:
        print(f"Area: {a.area} (pixel and cloud figures are measured inside it)")
    if landsat:
        print("\nLandsat files (not checked here): " + ", ".join(os.path.basename(p) for p in landsat[:4]) +
              ("..." if len(landsat) > 4 else ""))
        print("  Collection 2 level 2: reflectance = value x 0.0000275 - 0.2, surface temperature (K) = value x "
              "0.00341802 + 149.0. Read the factors from the _MTL file.")
    unknown = [p for p, b in files.items() if b is None]
    if unknown:
        print("\nNot recognised as a band (ignored): " + ", ".join(os.path.basename(p) for p in unknown))

    groups = {}
    for p, b in files.items():
        if b is not None:
            groups.setdefault(date_of(os.path.basename(p)), {})[p] = b
    if not groups:
        print("\nNo Sentinel-2 band found.")
        return
    if len(groups) > 1 and None in groups:
        print("\nWARNING some files have a date in their name and others do not: check that they belong together.")
    for date in sorted(groups, key=lambda d: d or ""):
        files_d = groups[date]
        masks = [p for p, b in files_d.items() if b and b.startswith("mask:")]
        out = a.mask_out
        if out and len(groups) > 1:
            stem, ext = os.path.splitext(out)
            out = f"{stem}_{date or 'nodate'}{ext or '.tif'}"
        check_scene(date, files_d, items, mtds, masks, a.area, out, s2_meta)
    print("\nWrite the formula, its evidence and the cloud figure into the plan and the work report.")


if __name__ == "__main__":
    main()
