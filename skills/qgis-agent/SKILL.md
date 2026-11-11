---
name: qgis-agent
description: A working method for driving QGIS (PyQGIS, processing algorithms, GDAL) on any GIS or remote sensing task, from scoping the request to a factual work report and, on request, a written report or paper draft. Use it whenever a request involves QGIS or geographic data, in any language and even if QGIS is not named - .qgz or .qgs projects, rasters or vectors (GeoTIFF, GeoPackage, shapefile, GeoJSON), Sentinel-2 or Landsat imagery, spectral indices (NDVI, NDMI, NBR, MNDWI, NDBI, SAVI), reprojection, clipping, classification, class areas, zonal statistics, maps and print layouts, GIS or remote sensing coursework, research and professional work.
---

# Working in QGIS as an agent

You drive QGIS through its Python engine (PyQGIS and the processing algorithms), not by clicking. The user stays in charge: they ask the question, set the rules and judge the results. Your job is to do the hands-on work quickly, cleanly and verifiably, hand back the facts, and write up the results when they ask.

The cycle below has been proven on real projects. Scale it to the task: a single reprojection needs no written plan, a full processing chain does. Always answer in the user's language.

## 1. Get to know the project

- Read the project's rules file if there is one (`CLAUDE.md` for Claude Code, `AGENTS.md` for Codex and most other agents), then the assignment or instructions (often in `sources/`). Note the formulas, class intervals, units, required map elements and deliverables. These are constraints, not suggestions.
- If there is none, propose one based on `assets/project_rules_template.md`, saved under the name your agent reads (`CLAUDE.md` or `AGENTS.md`), filled in with what you already know (QGIS version, CRS, resolution), and get it approved. It saves repeating the same rules every session.
- If the request is vague (missing area, period or deliverables), offer to complete it with `assets/request_template.md` rather than guessing.
- Inventory the data with `scripts/check_data.py`: CRS, pixel size, extent, nodata and value range for rasters; CRS, geometry type, feature count and area for vectors. If satellite bands are already in the folder, also run `scripts/check_imagery.py` on them (see the imagery rules below).
- Never modify the original data (`data/raw/` or equivalent). Work on copies: if a step goes wrong, you restart from the source without downloading anything again.

Suggested layout for an empty folder:

```
project/
├── sources/     assignment, papers
├── data/raw/    original data
├── data/        prepared data
├── scripts/     numbered steps
├── outputs/     rasters, maps, tables
└── AGENTS.md    project rules (CLAUDE.md for Claude Code)
```

## 2. Find QGIS's Python

Scripts must run with the Python that ships with QGIS, otherwise `qgis.core` and `processing` cannot be found.

- macOS and Linux: `bash <skill>/scripts/qgis_python.sh --info` prints the QGIS and GDAL versions. `bash <skill>/scripts/qgis_python.sh my_script.py args` runs a script in the right environment, with no window.
- Windows: look for `python-qgis.bat` or `python-qgis-ltr.bat` in `C:\Program Files\QGIS *\bin\` or `C:\OSGeo4W\bin\`, and run scripts with it (`python-qgis-ltr.bat my_script.py args`). It sets up the environment, but leaves the Processing plugin off the Python path: `scripts/pyqgis_template.py` adds it from `QgsApplication.pkgDataPath()`, so start step scripts from the template.
- If your commands run in a sandbox (Codex, or Claude Code with sandboxing on), the download scripts need network access to the hosts listed in the README: ask the user to approve it rather than working around the block.
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
- If a bundled script fails, read its message: it says what to do. Fix the cause or tell the user. Do not swap in home-made code or another data source without checking its values against the reference ranges below; a quiet workaround can produce wrong results that look fine.

Satellite imagery rules, to apply in every plan (details in `references/remote_sensing.md`):

- Find and download Sentinel-2 with `scripts/s2_search.py` and `scripts/s2_download.py`: open catalogue, no account, only the needed extent, clouds and coverage measured over the area itself. Prefer them to sending the user to a download portal. If the user wants to download by hand, name the product (level 2A) and the bands.
- Use reflectance, not raw values: apply the scale and offset from the band metadata (usually value × 0.0001 − 0.1), unless the metadata says the offset is already applied (see imagery already in the folder, below).
- Indices that use B11 or B12 (NDMI, NBR, MNDWI, NDBI) are computed at 20 m: average the 10 m bands down to 20 m. Never resample the 20 m bands up to 10 m, which creates detail that is not in the data. Pixel area at 20 m: 0.04 ha.
- Take all tiles from the same pass (same date), and pick a date whose tiles cover the whole area.
- If the image files cannot be reached (network, firewall or sandbox), the scripts say so: rerun both with `--collection sentinel-2-l2a`, a mirror stored on another host. Never read that mirror with your own code: its values already include the −0.1 offset (`earthsearch:boa_offset_applied: true`) while its metadata still declares it, so subtracting it again makes every band 0.1 too low and skews every index. The scripts handle this.
- Imagery already in the folder (sent by the user or a classmate, downloaded by hand, from another tool or catalogue) never went through the download scripts, so their protections do not apply. Before any calculation, run `scripts/check_imagery.py <folder>` (with `--area` and the study area if there is one), and put the formula it prints and its evidence in the plan. The rules it applies, which hold even if you read the files yourself:
  - STAC item (`item.json`): read `earthsearch:boa_offset_applied` before `raster:bands`. If it is `true`, reflectance = value × 0.0001, whatever offset `raster:bands` declares.
  - ESA metadata (`MTD_MSIL2A.xml`): reflectance = (value + `BOA_ADD_OFFSET`) / `BOA_QUANTIFICATION_VALUE`; with no `BOA_ADD_OFFSET`, value / 10000.
  - No metadata: level 2A bands acquired after 25 January 2022 carry the −1000 offset. Assume it, say so in the plan and the report, and check the raw values: if more than 1 % of a visible band is below 1000, those pixels would come out negative, so the offset is already applied or absent; ask where the files come from. For older dates it depends on the processing (the reprocessed archive has the offset): the raw values may rule it out, otherwise ask.
- Sanity check before computing indices: with the chosen formula, almost no pixel of a visible band (B02, B03, B04) should be negative. Dark targets (vegetation in red and blue, water, shadow) go negative when the offset is subtracted twice. Bright ground hides the error: with no raw value below 1000, both formulas give plausible reflectance, the pixels cannot tell them apart, and only the metadata decides. A plausible result is not a check. A median visible reflectance below 0.03 over land also points to a double offset.
- A scene without a mask band (SCL or similar) is never averaged as it is. Measure the cloud share over the area (`check_imagery.py` estimates it from B02 and B04, as a lower bound), report it with the result, and mask the clouds before giving a mean or a share: with the SCL band if you can get it, otherwise with the estimate, saying so. Without a blue band, look at a composite of the scene and ask for the mask band.

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
- The reflectance formula comes from the metadata, or is stated as an assumption; the cloud share over the area is measured (from the mask band, or estimated) and reported.
- Discrete symbology: QGIS expects the upper bound of each class.
- Statistics and regressions computed in float64 (in float32 a slope can be wrong with no error message).
- Every surprising result looked at on a natural colour composite (B04, B03, B02).
- The `.qgz` project reopened from scratch: valid layers, styles and layouts present, legends limited to the intended layers.
- When a result matters, one step recomputed another way (numpy against the raster calculator, for example) and compared pixel by pixel.

End with the list of deviations from the assignment and unchecked assumptions. The user must know them before handing anything in.

## 7. Corrections

One remark at a time. If the user pastes an error message or a screenshot, reproduce the problem, fix the cause, then rerun the downstream scripts so all files stay consistent with each other.

## 8. Hand over a work report, then write more if asked

At the end, produce a factual work report, like a lab notebook, following `references/work_report.md`: purpose, data, processing and parameters, files produced, results in tables, checks, limits and open questions. It is the record every later document is built from, so it comes first even when the user wants more.

If the user asks for more (an interpretation, a written report, a paper draft, a presentation or a summary for a client), write it. Build it only from the results and checks of the work report: no figure, source or claim that the processing did not produce or that you cannot cite. Keep the limits and deviations visible in the text rather than smoothing them over, and point out what still needs the user's judgement or field knowledge. Match the format they ask for (their assignment's structure, a journal's sections, a report template).

Mention once, without insisting, the data credits (wording in `references/remote_sensing.md`) and that many schools and journals ask authors to declare AI assistance.

## Skill files

| File | When to use it |
|---|---|
| `scripts/qgis_python.sh` | Run a script with QGIS's Python (macOS, Linux) |
| `scripts/pyqgis_template.py` | Starting point for each step script |
| `scripts/check_data.py` | Data inventory and output checks |
| `scripts/check_project.py` | Reopen a .qgz from scratch and list what it contains |
| `scripts/check_imagery.py` | Imagery already in a folder: reflectance formula and evidence, clouds without a mask band |
| `scripts/s2_search.py` | Find clear Sentinel-2 dates over an area |
| `scripts/s2_download.py` | Download bands as reflectance, for the needed extent only |
| `references/pyqgis.md` | Before writing PyQGIS code |
| `references/remote_sensing.md` | As soon as satellite imagery is involved |
| `references/work_report.md` | For the final work report |
| `assets/project_rules_template.md` | Project rules to propose |
| `assets/request_template.md` | To complete a vague request |
