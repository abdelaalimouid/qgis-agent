"""check_data.py reports CRS, pixel area and areas, and warns on the classic mistakes."""
import numpy as np

from conftest import make_polygons, make_raster, run_script


def test_projected_index_raster(tmp_path):
    p = make_raster(tmp_path / "NDVI.tif", np.linspace(-0.5, 0.9, 200, dtype="float32").reshape(10, 20))
    out = run_script("check_data.py", p).stdout
    assert "EPSG:32630" in out
    assert "0.04 ha" in out
    assert "WARNING" not in out


def test_index_out_of_range_is_flagged(tmp_path):
    p = make_raster(tmp_path / "NDVI_raw.tif", np.full((5, 5), 4.2, dtype="float32"))
    assert "normalised index outside [-1, 1]" in run_script("check_data.py", p).stdout


def test_classified_raster_is_not_flagged_as_an_index(tmp_path):
    p = make_raster(tmp_path / "NDVI_classes.tif", np.arange(1, 7, dtype="uint8").reshape(2, 3), nodata=0)
    assert "normalised index" not in run_script("check_data.py", p).stdout


def test_geographic_crs_is_flagged(tmp_path):
    p = make_raster(tmp_path / "dem.tif", np.ones((4, 4), dtype="float32"), epsg=4326, origin=(-5.5, 33.5), res=0.001)
    assert "geographic CRS" in run_script("check_data.py", p).stdout


def test_vector_area_and_invalid_geometry(tmp_path):
    square = "POLYGON((300000 3700000, 301000 3700000, 301000 3701000, 300000 3701000, 300000 3700000))"
    bowtie = "POLYGON((300000 3700000, 301000 3701000, 301000 3700000, 300000 3701000, 300000 3700000))"
    out = run_script("check_data.py", make_polygons(tmp_path / "zones.gpkg", [square, bowtie])).stdout
    assert "features 2" in out
    assert "invalid 1" in out
    assert "fixgeometries" in out


def test_folder_inventory_survives_unreadable_file(tmp_path):
    make_raster(tmp_path / "ok.tif", np.ones((3, 3), dtype="float32"))
    (tmp_path / "broken.tif").write_text("not a raster")
    r = run_script("check_data.py", tmp_path)
    assert r.returncode == 0
    assert "[error]" in r.stdout and "ok.tif" in r.stdout
