"""Live check against the Earth Search catalogue (needs internet). Run with QGIS_AGENT_LIVE=1.
Searches a known clear date over Khénifra, downloads a small patch from both collections and checks that
they give the same reflectance, with plausible visible values (no double offset)."""
import os

import numpy as np
import pytest

from conftest import run_script

pytestmark = [pytest.mark.network,
              pytest.mark.skipif(os.environ.get("QGIS_AGENT_LIVE") != "1", reason="set QGIS_AGENT_LIVE=1 to run")]

BBOX = ["-5.6997", "32.9064", "-5.6372", "32.9618"]
EXTENT = ["249500", "3646140", "251500", "3648140"]          # 2 km x 2 km in EPSG:32630
IDS = {"sentinel-2-c1-l2a": ["S2B_T29SQS_20260726T110336_L2A", "S2B_T30STB_20260726T110336_L2A"],
       "sentinel-2-l2a": ["S2B_29SQS_20260726_0_L2A", "S2B_30STB_20260726_0_L2A"]}


@pytest.mark.parametrize("collection", list(IDS))
def test_search_finds_the_clear_date(collection):
    r = run_script("s2_search.py", "--bbox", *BBOX, "--start", "2026-07-25", "--end", "2026-07-27", "--clouds", "30",
                   "--scl", "1", "--collection", collection)
    assert r.returncode == 0, r.stderr
    assert "2026-07-26" in r.stdout
    assert "covered % 100.00" in r.stdout


def test_both_collections_give_the_same_reflectance(tmp_path):
    from osgeo import gdal
    arrays = {}
    for collection, ids in IDS.items():
        out = tmp_path / collection
        r = run_script("s2_download.py", "--collection", collection, "--ids", *ids, "--extent", *EXTENT,
                       "--epsg", "32630", "--res", "20", "--bands", "B02", "B08", "--out", out)
        assert r.returncode == 0, r.stderr
        assert "WARNING median reflectance" not in r.stdout
        arrays[collection] = {b: gdal.Open(str(out / f"{b}.tif")).ReadAsArray() for b in ("B02", "B08")}
    for b in ("B02", "B08"):
        np.testing.assert_allclose(arrays["sentinel-2-c1-l2a"][b], arrays["sentinel-2-l2a"][b], atol=1e-6)
    assert np.median(arrays["sentinel-2-c1-l2a"]["B02"]) > 0.03
