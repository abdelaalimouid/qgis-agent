# Remote sensing: bands, reflectance, indices, sources

## Sentinel-2 level 2A (surface reflectance)

| Band | Domain | Resolution | Catalogue key |
|---|---|---|---|
| B02 | blue | 10 m | blue |
| B03 | green | 10 m | green |
| B04 | red | 10 m | red |
| B05, B06, B07 | red edge | 20 m | rededge1, 2, 3 |
| B08 | near infrared (NIR) | 10 m | nir |
| B8A | narrow NIR | 20 m | nir08 |
| B11 | shortwave infrared SWIR 1 (1.6 µm) | 20 m | swir16 |
| B12 | shortwave infrared SWIR 2 (2.2 µm) | 20 m | swir22 |
| SCL | scene classification | 20 m | scl |

Reflectance: the files hold integers. Since processing baseline 04.00 (January 2022), reflectance = value × 0.0001 − 0.1. Read the scale and offset from each band's metadata (`raster:bands` in the catalogue) rather than assuming them, clamp the result to [0, 1], and treat 0 as nodata. `scripts/s2_download.py` does this.

Resolution: an index that uses B11 or B12 is computed at 20 m. Bring 10 m bands to 20 m by averaging, never the other way round. Pixel area: 10 m = 0.01 ha; 20 m = 0.04 ha; 30 m (Landsat) = 0.09 ha.

Mosaics: take all tiles from one pass (same day, same satellite). Mixing two dates creates seams and skews comparisons.

### Clouds and snow: the SCL layer

| Code | Meaning | Code | Meaning |
|---|---|---|---|
| 0 | no data | 6 | water |
| 1 | saturated or defective | 7 | unclassified |
| 2 | dark area, terrain shadow | 8 | cloud, medium probability |
| 3 | cloud shadow | 9 | cloud, high probability |
| 4 | vegetation | 10 | thin cirrus |
| 5 | not vegetated | 11 | snow or ice |

The announced cloud cover is for the whole tile (110 km across). Measure the share of codes 3, 8, 9, 10 and 11 over the area itself (`s2_search.py --scl`). Also check that the chosen tiles cover the whole area: a date at the edge of a satellite swath can look clear and still miss part of it.

## Common indices

Always use the assignment's formula if it differs (some use B8A instead of B08).

| Index | Sentinel-2 formula | Measures |
|---|---|---|
| NDVI | (B08 − B04) / (B08 + B04) | vegetation vigour |
| SAVI | 1.5 × (B08 − B04) / (B08 + B04 + 0.5) | vegetation over sparse cover |
| NDMI | (B08 − B11) / (B08 + B11) | leaf water content |
| NBR | (B08 − B12) / (B08 + B12) | burn scars (dNBR = NBR before − NBR after) |
| NDWI | (B03 − B08) / (B03 + B08) | open water (McFeeters) |
| MNDWI | (B03 − B11) / (B03 + B11) | open water, less confused with built-up areas |
| NDBI | (B11 − B08) / (B11 + B08) | built-up areas and bare soil (equal to −NDMI) |

Useful relations for checks: NDBI = −NDMI exactly; NBR and NDMI are highly correlated; a positive MNDWI under forest is suspect (shadow, mask error).

Natural colour composite: B04, B03, B02 stretched from 0 to about 0.2. False colour infrared: B08, B04, B03. Look at one under every surprising result.

## Projection

UTM zone = integer part of ((longitude + 180) / 6) + 1. Northern hemisphere: EPSG 326xx (32629 for zone 29N, 32630 for zone 30N). Work in the area's UTM CRS for any area or distance. For an area spanning two zones, pick the one covering most of it and reproject the rest.

## Open data sources

| Data | Source | Note |
|---|---|---|
| Sentinel-2, Landsat | Earth Search, `https://earth-search.aws.element84.com/v1` (collections `sentinel-2-c1-l2a`, `landsat-c2-l2`) | no account, COG files readable by window |
| Sentinel-2, Landsat | Microsoft Planetary Computer | URLs must be signed before reading |
| Elevation | Copernicus DEM 30 m (collection `cop-dem-glo-30` on Earth Search) | |
| Boundaries, roads, buildings, water | OpenStreetMap through the Overpass API (`https://overpass-api.de/api/interpreter`) | retry on 502 or 504 errors |
| Rainfall | CHIRPS | time series |
| Climate | ERA5 (Copernicus Climate Data Store) | free account needed |

OpenStreetMap is not an official source: park, forest or municipality outlines can be very approximate. Whenever an area figure matters, record where each boundary comes from and compare it with a published value.

## Data credits

- Sentinel: "Contains modified Copernicus Sentinel data [year]".
- Landsat: "Landsat imagery courtesy of the U.S. Geological Survey".
- OpenStreetMap: "© OpenStreetMap contributors, ODbL licence".
- Copernicus DEM: use the wording supplied with the data ("produced using Copernicus WorldDEM-30", "provided under COPERNICUS by the European Union and ESA").
