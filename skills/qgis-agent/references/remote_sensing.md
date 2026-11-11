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

Reflectance: the files hold integers. Since processing baseline 04.00 (25 January 2022), and in ESA's reprocessed archive (baseline 05.00 and later, back to 2015), reflectance = value × 0.0001 − 0.1; older original products have no offset. Read the scale and offset from each band's metadata (`raster:bands` in the catalogue) rather than assuming them, clamp the result to [0, 1], and treat 0 as nodata. `scripts/s2_download.py` does this.

Resolution: an index that uses B11 or B12 is computed at 20 m. Bring 10 m bands to 20 m by averaging, never the other way round. Pixel area: 10 m = 0.01 ha; 20 m = 0.04 ha; 30 m (Landsat) = 0.09 ha.

Mosaics: take all tiles from one pass (same day, same satellite). Mixing two dates creates seams and skews comparisons.

### Two Sentinel-2 collections on Earth Search

| Collection | Image host | Reflectance |
|---|---|---|
| `sentinel-2-c1-l2a` (default) | `e84-earth-search-sentinel-data.s3.us-west-2.amazonaws.com` | value × 0.0001 − 0.1 (offset from `raster:bands`) |
| `sentinel-2-l2a` (mirror) | `sentinel-cogs.s3.us-west-2.amazonaws.com` | value × 0.0001, no offset: the item property `earthsearch:boa_offset_applied` is `true` |

The same pixel differs by exactly 1,000 between the two collections, and the mirror's metadata still declares an offset of −0.1. Applying it makes every band 0.1 too low: in a test on Khénifra, the NDBI class above 0.2 grew from 0.2 % to 6 % of the area. `scripts/s2_download.py` reads the property and applies the right rule. Item ids also differ (`S2B_T30STB_20260726T110336_L2A` against `S2B_30STB_20260726_0_L2A`), so search and download with the same `--collection`.

### Imagery already in the folder

Bands that someone else downloaded or exported never went through `s2_download.py`, so its protections do not apply: the files carry whatever their source did. Run `scripts/check_imagery.py <folder> [--area zone.geojson]` before any calculation. It reads the evidence in this order and prints the formula, the evidence and what the pixels say:

| Evidence in the folder | Reflectance |
|---|---|
| STAC item with `earthsearch:boa_offset_applied: true` (the mirror) | value × 0.0001: the declared −0.1 is already in the values |
| STAC item without that property | scale and offset from `raster:bands` |
| `MTD_MSIL2A.xml` with `BOA_ADD_OFFSET` | (value + `BOA_ADD_OFFSET`) / `BOA_QUANTIFICATION_VALUE` |
| `MTD_MSIL2A.xml` without `BOA_ADD_OFFSET` (baseline before 04.00) | value / 10000 |
| File names like the mirror's item ids (`S2A_30SUB_20240830_0_L2A_B04.tif`) | value × 0.0001, likely: get the item to confirm |
| Product name with a baseline (`..._N0510_...`) | −1000 from 04.00 on, none before |
| No metadata, acquired after 25 January 2022 | value × 0.0001 − 0.1, assumed: say so |
| No metadata, older or undated | unknown: the raw values may rule the offset out, otherwise ask the source |
| Floats between 0 and 1 | already reflectance |

What the pixels can and cannot say. A raw value below 1000 is a reflectance below 0.1 without the offset, and a negative one with it. So if more than 1 % of a visible band is below 1000, the offset is not in the files as a raw post-2022 product would have it: either it is already applied, or there never was one. If almost no value is below 1000, the pixels cannot decide. Over a bright plain in late summer, a double offset left the red band at 0.19 on average and not one pixel below zero; even the blue band, the darkest over land, had only 1.7 % negative. There, only the metadata decides, and a plausible result proves nothing. Neither this check nor the median check catches an offset that was ignored: the values are 0.1 too high and still look normal.

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

No SCL band in the folder: never average the scene as it is. `check_imagery.py` estimates the cloud share with the haze test of Fmask (Zhu and Woodcock, 2012): blue − 0.5 × red − 0.08 > 0, on surface reflectance. On a cloudy forest scene it found 20 % cloud where the SCL band gave 30 % cloud and 7 % cloud shadow. It catches thick cloud with very few false alarms (98 % of the pixels it flagged were cloud in the SCL), misses thin cloud and every shadow, and also flags snow, salt flats and white roofs. Treat its figure as a lower bound and report it. Mask with the SCL band if you can get it (`s2_download.py --scl`); otherwise with the estimate (`--mask-out`), saying so. On that scene the estimate removed about two thirds of the cloud bias: mean NDVI 0.296 unmasked, 0.334 with the estimate, 0.354 with the SCL band.

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
