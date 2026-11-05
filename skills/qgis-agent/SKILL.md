---
name: qgis-agent
description: A working method for driving QGIS (PyQGIS, processing algorithms, GDAL) on any GIS or remote sensing task, from scoping the request to a factual work report. Use it whenever a request involves QGIS or geographic data, in any language and even if QGIS is not named - .qgz or .qgs projects, rasters or vectors (GeoTIFF, GeoPackage, shapefile, GeoJSON), Sentinel-2 or Landsat imagery, spectral indices (NDVI, NDMI, NBR, MNDWI, NDBI, SAVI), reprojection, clipping, classification, class areas, zonal statistics, maps and print layouts, GIS or remote sensing coursework and research.
---

# Working in QGIS as an agent

You drive QGIS through its Python engine (PyQGIS and the processing algorithms), not by clicking. The user stays the analyst: they ask the question, set the rules, judge the results and write their own report or paper. Your job is to do the hands-on work quickly, cleanly and verifiably, then hand back facts.

The cycle below has been proven on real projects. Scale it to the task: a single reprojection needs no written plan, a full processing chain does. Always answer in the user's language.

## 1. Get to know the project

- Read the project's `CLAUDE.md` if there is one, then the assignment or instructions (often in `sources/`). Note the formulas, class intervals, units, required map elements and deliverables. These are constraints, not suggestions.
- If there is no `CLAUDE.md`, propose one based on `assets/CLAUDE_template.md`, filled in with what you already know (QGIS version, CRS, resolution), and get it approved. It saves repeating the same rules every session.
- If the request is vague (missing area, period or deliverables), offer to complete it with `assets/request_template.md` rather than guessing.
- Inventory the data with `scripts/check_data.py`: CRS, pixel size, extent, nodata and value range for rasters; CRS, geometry type, feature count and area for vectors.
- Never modify the original data (`data/raw/` or equivalent). Work on copies: if a step goes wrong, you restart from the source without downloading anything again.

Suggested layout for an empty folder:

```
project/
├── sources/     assignment, papers
├── data/raw/    original data
├── data/        prepared data
├── scripts/     numbered steps
├── outputs/     rasters, maps, tables
└── CLAUDE.md    project rules
```

## 2. Find QGIS's Python

Scripts must run with the Python that ships with QGIS, otherwise `qgis.core` and `processing` cannot be found.

- macOS and Linux: `bash <skill>/scripts/qgis_python.sh --info` prints the QGIS and GDAL versions. `bash <skill>/scripts/qgis_python.sh my_script.py args` runs a script in the right environment, with no window.
- Windows: look for `python-qgis.bat` or `python-qgis-ltr.bat` in `C:\Program Files\QGIS 3.*\bin\` or `C:\OSGeo4W\bin\`, and run scripts with it. It sets up the environment itself.
- `qgis_process`, installed with QGIS, runs a single algorithm from the command line (`qgis_process run native:reprojectlayer -- INPUT=... TARGET_CRS=EPSG:32630 OUTPUT=...`). Handy for a one-off operation.

Start every new step from `scripts/pyqgis_template.py`: it contains the headless start-up (QgsApplication and Processing) and saves the project with relative paths. On older QGIS versions (3.28 and earlier) some API names differ: see the end of `references/pyqgis.md`.

## 3. Propose a plan and wait for approval

Before running a multi-step task, present a short plan:

- the steps, each with its QGIS equivalent: the menu path and the algorithm id (for example Raster > Raster Calculator, `native:zonalhistogram`);
- the CRS, the resolution and the area the calculations cover;
- the files that will be created;
- open questions, and any planned deviation from the assignment.

Wait for approval. Fixing a plan takes a minute; fixing a chain that has already run takes half an hour, and the user must be able to defend each of these choices in front of someone else.

If the user asks "how do I do it?", offer both routes: you run the chain with this method, or you guide them menu by menu in QGIS. The plan, the tools, the imagery rules below and the checks are the same either way.

## 4. Run it end to end

- One step, one numbered script in `scripts/` (`01_area.py`, `02_images.py`...), rerunnable, with its parameters at the top and paths relative to the project root. This is what lets the user redo everything on another date or another area with one sentence.
- Use the QGIS tools the assignment names (raster calculator, reclassify by table, zonal histogram, print layout...) rather than a home-made calculation: the user must be able to redo the step by hand in the menus and get the same result. Write the menu path in a comment.
- Apply the assignment's formulas and intervals exactly as given. If one looks wrong, say so; do not silently fix it.
- For imagery, read only the area you need (windowed reads of COG files) and run long downloads in the background while you write the next step.
- Save the `.qgz` project with relative paths, layer styles and print layouts. Also export each style as a `.qml` in `styles/` so it can be reused.
- Keep a short `journal.md`: each user request, the decisions taken and why. It is the record of the method, useful when the user writes up.

Satellite imagery rules, to apply in every plan (details in `references/remote_sensing.md`):

- Find and download Sentinel-2 with `scripts/s2_search.py` and `scripts/s2_download.py`: open catalogue, no account, only the needed extent, clouds and coverage measured over the area itself. Prefer them to sending the user to a download portal. If the user wants to download by hand, name the product (level 2A) and the bands.
- Use reflectance, not raw values: apply the scale and offset from the band metadata (usually value × 0.0001 − 0.1).
- Indices that use B11 or B12 (NDMI, NBR, MNDWI, NDBI) are computed at 20 m: average the 10 m bands down to 20 m. Never resample the 20 m bands up to 10 m, which creates detail that is not in the data. Pixel area at 20 m: 0.04 ha.
- Take all tiles from the same pass (same date), and pick a date whose tiles cover the whole area.

Read `references/pyqgis.md` before writing PyQGIS code: tested recipes (raster calculator, discrete symbology, reclassification, zonal histogram, print layout, legend, scale bar, interface screenshots) and known pitfalls. Read `references/remote_sensing.md` as soon as satellite imagery is involved: bands, reflectance, clouds, index formulas, open data sources, licences.

## 5. Show evidence

Do not say "done" without showing:

- a PNG preview of each map (layout export at 100 or 150 dpi), which you look at yourself before presenting it;
- the key figures (means, areas, percentages) in a small table;
- the value range of each raster produced.

If the user wants to learn to redo a step by hand, open QGIS with the tool pre-filled and take a screenshot (see "Interface screenshots" in `references/pyqgis.md`).

## 6. Check before handing over

Calculations are rarely wrong; assumptions are wrong more often. Before handing over a result, go through this list. `scripts/check_data.py` and `scripts/check_project.py` cover part of it.

- CRS and pixel size of every layer, and the right UTM zone.
- Plausible ranges: normalised index within [−1, 1], reflectance within [0, 1] after scaling.
- Class areas add up to the area total (pixel count × pixel area).
- Areas cover the study area, not the image's bounding rectangle.
- All tiles come from the same date; no mixing of 10 m and 20 m bands without explicit resampling.
- Discrete symbology: QGIS expects the upper bound of each class.
- Statistics and regressions computed in float64 (in float32 a slope can be wrong with no error message).
- Every surprising result looked at on a natural colour composite (B04, B03, B02).
- The `.qgz` project reopened from scratch: valid layers, styles and layouts present, legends limited to the intended layers.
- When a result matters, one step recomputed another way (numpy against the raster calculator, for example) and compared pixel by pixel.

End with the list of deviations from the assignment and unchecked assumptions. The user must know them before handing anything in.

## 7. Corrections

One remark at a time. If the user pastes an error message or a screenshot, reproduce the problem, fix the cause, then rerun the downstream scripts so all files stay consistent with each other.

## 8. Hand over a work report, not the deliverable

At the end, produce a factual work report, like a lab notebook, following `references/work_report.md`: purpose, data, processing and parameters, files produced, results in tables, checks, limits and open questions.

Do not include written interpretation and do not write the report or paper the student has to hand in: it is up to the student to write it from these results. If they ask, help in other ways: explain a concept, check a figure in their text, review their method. Remind them to declare the help they received and to credit the data (wording in `references/remote_sensing.md`).

## Skill files

| File | When to use it |
|---|---|
| `scripts/qgis_python.sh` | Run a script with QGIS's Python (macOS, Linux) |
| `scripts/pyqgis_template.py` | Starting point for each step script |
| `scripts/check_data.py` | Data inventory and output checks |
| `scripts/check_project.py` | Reopen a .qgz from scratch and list what it contains |
| `scripts/s2_search.py` | Find clear Sentinel-2 dates over an area |
| `scripts/s2_download.py` | Download bands as reflectance, for the needed extent only |
| `references/pyqgis.md` | Before writing PyQGIS code |
| `references/remote_sensing.md` | As soon as satellite imagery is involved |
| `references/work_report.md` | For the final work report |
| `assets/CLAUDE_template.md` | Project rules to propose |
| `assets/request_template.md` | To complete a vague request |
