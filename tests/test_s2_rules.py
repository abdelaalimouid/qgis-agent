"""Offline checks of the Sentinel-2 rules: reflectance, the mirror's offset trap, pass grouping, cloud shares."""
import numpy as np
import pytest

from conftest import load_script

dl = load_script("s2_download.py")
search = load_script("s2_search.py")


def item(boa_applied=None, scale=0.0001, offset=-0.1, res=10):
    props = {} if boa_applied is None else {"earthsearch:boa_offset_applied": boa_applied}
    band = {"nodata": 0, "scale": scale, "offset": offset, "spatial_resolution": res}
    return {"properties": props, "assets": {"red": {"raster:bands": [band]}}}


def test_reflectance_applies_scale_offset_clamp_and_nodata():
    dn = np.array([[0, 1000, 2000, 12000]], dtype="float32")
    r = dl.reflectance(dn, 0.0001, -0.1)
    assert r.dtype == np.float32
    assert r[0, 0] == dl.NODATA
    np.testing.assert_allclose(r[0, 1:], [0.0, 0.1, 1.0], atol=1e-6)


def test_default_collection_uses_catalogue_offset():
    assert dl.band_rule(item(), "red", dl.offset_already_applied([item()])) == (0.0001, -0.1, 10)


def test_mirror_offset_is_not_applied_twice():
    mirror = item(boa_applied=True)
    applied = dl.offset_already_applied([mirror])
    assert applied is True
    scale, offset, _ = dl.band_rule(mirror, "red", applied)
    assert offset == 0.0


def test_mirror_and_default_give_the_same_reflectance():
    """The same pixel is stored 1000 lower in the mirror, whose values already include the offset."""
    rng = np.random.default_rng(0)
    dn_default = rng.integers(1100, 6000, size=(30, 30)).astype("float32")
    dn_mirror = dn_default - 1000
    a = dl.reflectance(dn_default, *dl.band_rule(item(), "red", False)[:2])
    b = dl.reflectance(dn_mirror, *dl.band_rule(item(True), "red", True)[:2])
    np.testing.assert_allclose(a, b, atol=1e-6)
    wrong = dl.reflectance(dn_mirror, 0.0001, -0.1)          # the trap: offset subtracted twice
    assert np.median(a - wrong) == pytest.approx(0.1, abs=1e-6)


def test_low_visible_reflectance_is_flagged():
    assert dl.low_visible_bands({"B02": 0.017, "B03": 0.05, "B08": 0.2}) == ["B02"]
    assert dl.low_visible_bands({"B02": 0.11, "B03": 0.13, "B04": 0.18}) == []


def test_other_collection():
    assert dl.other_collection("sentinel-2-c1-l2a") == "sentinel-2-l2a"
    assert dl.other_collection("sentinel-2-l2a") == "sentinel-2-c1-l2a"


def test_passes_grouped_by_day_and_satellite_sorted_by_clouds():
    def it(day, sat, cc):
        return {"properties": {"datetime": f"{day}T11:00:00Z", "platform": sat, "eo:cloud_cover": cc}}
    items = [it("2026-07-03", "sentinel-2a", 40), it("2026-07-03", "sentinel-2a", 20),
             it("2026-07-26", "sentinel-2b", 0), it("2026-07-26", "sentinel-2b", 1)]
    ranked = search.group_passes(items)
    assert [k for k, _ in ranked] == [("2026-07-26", "sentinel-2b"), ("2026-07-03", "sentinel-2a")]
    assert [len(v) for _, v in ranked] == [2, 2]


def test_scl_summary_shares():
    a = np.array([[0, 4, 4, 4], [8, 9, 3, 11]])            # 1 no-data pixel, 7 valid
    s = search.scl_summary(a)
    assert s["covered %"] == pytest.approx(100 * 7 / 8)
    assert s["clouds %"] == pytest.approx(100 * 2 / 7)
    assert s["shadows %"] == pytest.approx(100 / 7)
    assert s["snow %"] == pytest.approx(100 / 7)
    assert search.scl_summary(np.zeros((3, 3))) is None
