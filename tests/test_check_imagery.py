"""check_imagery.py on pre-staged Sentinel-2 folders: the formula comes from the metadata (the mirror's
earthsearch:boa_offset_applied before raster:bands), the pixels can rule an offset out but say when they cannot
decide, and a scene without a mask band gets a cloud estimate."""
import json

import numpy as np
import pytest

from conftest import load_script, make_polygons, make_raster, run_script

ci = load_script("check_imagery.py")
SHAPE = (40, 50)
MIRROR = "S2A_30SUB_20240830_0_L2A_{}.tif"


def bright(low=1150, high=4800, seed=0):
    """Raw values of a bright plain: none below 1000, so a double offset leaves no negative pixel."""
    return np.random.default_rng(seed).integers(low, high, SHAPE).astype("uint16")


def with_dark(share=0.1, seed=0):
    """Raw values where a share of pixels sits below 1000 (vegetation or water in a product with no offset)."""
    a = bright(1500, 4000, seed)
    a.flat[: int(share * a.size)] = 400
    return a


def item_json(folder, applied, date="2024-08-30", id_="S2A_30SUB_20240830_0_L2A"):
    band = {"nodata": 0, "data_type": "uint16", "scale": 0.0001, "offset": -0.1}
    props = {"datetime": f"{date}T11:12:05Z", "eo:cloud_cover": 0.8, "s2:processing_baseline": "05.11"}
    if applied is not None:
        props["earthsearch:boa_offset_applied"] = applied
    item = {"type": "Feature", "id": id_, "properties": props,
            "assets": {"aot": {"raster:bands": [{"scale": 0.001, "offset": 0}]},   # listed first, like the real items
                       "red": {"raster:bands": [band]}, "nir": {"raster:bands": [band]}}}
    (folder / "item.json").write_text(json.dumps(item), encoding="utf-8")


def mtd_xml(folder, date, baseline, offset=None, cloud=12.5):
    offsets = "" if offset is None else (
        "<BOA_ADD_OFFSET_VALUES_LIST>"
        + "".join(f'<BOA_ADD_OFFSET band_id="{i}">{offset}</BOA_ADD_OFFSET>' for i in range(13))
        + "</BOA_ADD_OFFSET_VALUES_LIST>")
    xml = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<n1:Level-2A_User_Product xmlns:n1="https://psd-14.sentinel2.eo.esa.int/PSD/User_Product_Level-2A.xsd">'
           f"<n1:General_Info><Product_Info><PRODUCT_START_TIME>{date}T10:56:21.024Z</PRODUCT_START_TIME>"
           f"<PROCESSING_BASELINE>{baseline}</PROCESSING_BASELINE></Product_Info>"
           f'<Product_Image_Characteristics><QUANTIFICATION_VALUES_LIST><BOA_QUANTIFICATION_VALUE unit="none">10000'
           f"</BOA_QUANTIFICATION_VALUE></QUANTIFICATION_VALUES_LIST>{offsets}</Product_Image_Characteristics>"
           f"</n1:General_Info><n1:Quality_Indicators_Info><Cloud_Coverage_Assessment>{cloud}"
           f"</Cloud_Coverage_Assessment></n1:Quality_Indicators_Info></n1:Level-2A_User_Product>")
    (folder / f"MTD_MSIL2A_{date.replace('-', '')}T105621.xml").write_text(xml, encoding="utf-8")


def check(folder, *args):
    r = run_script("check_imagery.py", folder, *args)
    assert r.returncode == 0, r.stderr
    return r.stdout


# ---------- the formula ----------

def test_mirror_item_wins_over_its_raster_bands(tmp_path):
    """Pilot failure 1: the item says the offset is applied while raster:bands still declares -0.1."""
    for b in ("B04", "B08"):
        make_raster(tmp_path / MIRROR.format(b), bright())
    item_json(tmp_path, applied=True)
    out = check(tmp_path)
    assert "reflectance = value x 0.0001   (documented)" in out
    assert "earthsearch:boa_offset_applied = true" in out
    assert "Do not subtract it again" in out
    assert "pixels cannot tell" in out          # bright ground: no pixel can show the double offset
    assert "WARNING" not in out


def test_item_without_the_property_uses_the_declared_offset(tmp_path):
    for b in ("B04", "B08"):
        make_raster(tmp_path / f"S2A_T30SUB_20240830T105621_L2A_{b}.tif", bright(2100, 5800))
    item_json(tmp_path, applied=None, id_="S2A_T30SUB_20240830T105621_L2A")
    out = check(tmp_path)
    assert "reflectance = value x 0.0001 - 0.1   (documented)" in out
    assert "WARNING" not in out


def test_declared_offset_contradicted_by_the_pixels(tmp_path):
    """An item that declares -0.1 for values that already include it: dark pixels turn negative."""
    make_raster(tmp_path / MIRROR.format("B04"), with_dark(0.1))
    item_json(tmp_path, applied=None)
    out = check(tmp_path)
    assert "(contradicted)" in out
    assert "WARNING 10.0 % of B04 is below 1000" in out


def test_mtd_files_give_one_formula_per_date(tmp_path):
    make_raster(tmp_path / "T30SUA_20190728T105621_B04_10m.tif", with_dark(0.09))
    make_raster(tmp_path / "T30SUA_20230727T105621_B04_10m.tif", bright(1775, 4900))
    mtd_xml(tmp_path, "2019-07-28", "02.12")
    mtd_xml(tmp_path, "2023-07-27", "05.10", offset=-1000)
    out = check(tmp_path)
    old, new = out.split("== Scene 2023-07-27")
    assert "reflectance = value x 0.0001   (documented)" in old and "gives no BOA_ADD_OFFSET" in old
    assert "which agrees with this formula" in old
    assert "reflectance = value x 0.0001 - 0.1   (documented)" in new
    assert "BOA_ADD_OFFSET -1000" in new
    assert "WARNING" not in out


def test_no_metadata_after_2022_assumes_the_offset(tmp_path):
    """Pilot failure 2 (handled by 1.1.1, kept): undocumented 2023 bands carry the -1000 offset."""
    make_raster(tmp_path / "errachidia_2023_B04.tif", bright(1775, 4900))
    out = check(tmp_path)
    assert "reflectance = value x 0.0001 - 0.1   (assumed)" in out
    assert "Ask where they come from" in out
    assert "rests on the assumption" in out


def test_no_metadata_values_below_1000_rule_the_offset_out(tmp_path):
    make_raster(tmp_path / "errachidia_2019_B04.tif", with_dark(0.09))
    out = check(tmp_path)
    assert "reflectance = value x 0.0001   (from the pixels)" in out
    assert "9.0 % of B04 is below 1000" in out


def test_assumed_offset_contradicted_by_the_pixels_is_undecided(tmp_path):
    make_raster(tmp_path / "classmate_2024_B04.tif", with_dark(0.2))
    out = check(tmp_path)
    assert "formula   UNDECIDED" in out
    assert "WARNING 20.0 % of B04 is below 1000" in out


def test_no_metadata_no_date_bright_ground_asks_for_the_source(tmp_path):
    make_raster(tmp_path / "red.tif", bright())
    make_raster(tmp_path / "nir.tif", bright())
    out = check(tmp_path)
    assert "formula   UNDECIDED" in out
    assert "WARNING no metadata and the pixels cannot decide" in out


def test_mirror_file_names_without_item(tmp_path):
    make_raster(tmp_path / MIRROR.format("B04"), bright())
    out = check(tmp_path)
    assert "reflectance = value x 0.0001   (likely)" in out
    assert "sentinel-2-l2a mirror" in out


def test_reflectance_written_by_s2_download_needs_no_formula(tmp_path):
    refl = (bright().astype("float32") * 0.0001)
    refl[0, :5] = -9999
    make_raster(tmp_path / "B04.tif", refl, nodata=-9999)
    (tmp_path / "s2_metadata.json").write_text("{}", encoding="utf-8")
    out = check(tmp_path)
    assert "already reflectance" in out and "s2_download.py" in out
    assert "WARNING" not in out


def test_reflectance_file_with_a_clamped_double_offset_is_flagged(tmp_path):
    refl = (bright().astype("float32") * 0.0001)
    refl.flat[: refl.size // 5] = 0.0             # negative values clamped to 0 by the writer
    make_raster(tmp_path / "ndvi_input_B04.tif", refl, nodata=-9999)
    assert "WARNING 20.0 % of B04 is zero or negative" in check(tmp_path)


def test_landsat_files_are_pointed_to_their_own_rule(tmp_path):
    make_raster(tmp_path / "LC08_L2SP_201039_20230830_02_T1_SR_B4.TIF", bright())
    out = check(tmp_path)
    assert "Landsat files (not checked here)" in out
    assert "0.0000275" in out


# ---------- clouds ----------

def cloudy_scene(folder, share_rows=12):
    """Blue and red of a dark forest (offset -1000) with thick cloud on the top rows (30 % of the scene)."""
    rng = np.random.default_rng(1)
    blue = rng.integers(1300, 1700, SHAPE).astype("uint16")
    red = rng.integers(1400, 1900, SHAPE).astype("uint16")
    blue[:share_rows], red[:share_rows] = 5500, 5400
    make_raster(folder / "T30STC_20240522T105621_B02_10m.tif", blue)
    make_raster(folder / "T30STC_20240522T105621_B04_10m.tif", red)
    mtd_xml(folder, "2024-05-22", "05.10", offset=-1000, cloud=43.7)


def test_cloudy_scene_without_mask_band_is_measured(tmp_path):
    """Pilot failure 3: without an SCL band the scene must not be averaged as it is."""
    cloudy_scene(tmp_path)
    out = check(tmp_path, "--mask-out", tmp_path / "cloud_estimate.tif")
    assert "WARNING no mask band (SCL or similar), and 30.0 % of the scene looks like cloud" in out
    assert "lower bound" in out and "Do not average this scene as it is" in out
    assert "43.7 % cloud for the whole tile" in out
    from osgeo import gdal
    m = gdal.Open(str(tmp_path / "cloud_estimate.tif")).ReadAsArray()
    assert m.shape == SHAPE
    assert (m == 1).mean() == pytest.approx(0.3)


def test_area_restricts_the_cloud_share(tmp_path):
    """The figures are measured inside the area, given here in degrees while the bands are in UTM."""
    from osgeo import ogr, osr
    cloudy_scene(tmp_path)
    utm, wgs = osr.SpatialReference(), osr.SpatialReference()
    utm.ImportFromEPSG(32630)
    wgs.ImportFromEPSG(4326)
    for s in (utm, wgs):
        s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    g = ogr.CreateGeometryFromWkt("POLYGON((300000 3699200, 301000 3699200, 301000 3699700, 300000 3699700, "
                                  "300000 3699200))")      # rows 15 to 39: no cloud
    g.Transform(osr.CoordinateTransformation(utm, wgs))
    area = make_polygons(tmp_path / "zone.gpkg", [g.ExportToWkt()], epsg=4326)
    out = check(tmp_path, "--area", area)
    assert "0.0 % of the area looks like cloud" in out
    assert "WARNING no mask band" not in out


def test_scl_band_is_used_when_present(tmp_path):
    cloudy_scene(tmp_path)
    scl = np.full(SHAPE, 4, dtype="uint8")
    scl[:10] = 9
    scl[10:14] = 3
    make_raster(tmp_path / "T30STC_20240522T105621_SCL_20m.tif", scl, nodata=0)
    out = check(tmp_path)
    assert "SCL band: clouds (8, 9, 10) 25.0 %, shadows (3) 10.0 %" in out
    assert "looks like cloud" not in out


# ---------- small rules ----------

@pytest.mark.parametrize("name, band", [
    ("T30SUA_20230727T105621_B04_10m.tif", "B04"), ("S2A_30SUB_20240830_0_L2A_B8A.tif", "B8A"),
    ("errachidia_2019_B8.tif", "B08"), ("nir08.tif", "B8A"), ("red.tif", "B04"), ("rededge1.tif", "B05"),
    ("T30STC_20240522T105621_SCL_20m.tif", "SCL"), ("MSK_CLDPRB_20m.jp2", "mask:MSK_CLDPRB_20m"),
    ("B04_masked.tif", "B04"), ("TCI_10m.tif", None)])
def test_band_names(name, band):
    assert ci.band_of(name) == band


def test_dates_and_baseline():
    assert ci.date_of("T30SUA_20230727T105621_B04_10m.tif") == "2023-07-27"
    assert ci.date_of("errachidia_2019_B04.tif") == "2019"
    assert ci.date_of("red.tif") is None
    assert ci.after_baseline_04("2022-01-25") is True and ci.after_baseline_04("2022-01-24") is False
    assert ci.after_baseline_04("2022") is None and ci.after_baseline_04("2023") is True
    assert ci.after_baseline_04("2023-02-30") is None
    assert ci.baseline_of(["S2A_MSIL2A_20240522T105621_N0510_R094_T30STC_20240522T181114.SAFE"]) == pytest.approx(5.1)


def test_haze_test_separates_cloud_from_forest_and_bright_soil():
    blue = np.array([0.45, 0.04, 0.16])       # thick cloud, conifer forest, bright soil
    red = np.array([0.44, 0.03, 0.29])
    assert ci.hot_clouds(blue, red).tolist() == [True, False, False]
