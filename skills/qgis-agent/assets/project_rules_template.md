# Project rules

## Software
- QGIS [version] installed in [path]. Use its Python (PyQGIS) for all processing.
- GDAL [version].

## Area and data
- Area: [place]. Origin of the boundaries: [source].
- Working CRS: EPSG:[code] ([name]).
- Images: [sensor, level, period]. Working resolution: [x] m.
- The original data is in data/raw/. Never modify it.

## Method
- Follow the formulas, intervals and units of the assignment (sources/) exactly.
- Use the QGIS tools named in the assignment, so I can redo each step by hand.
- Keep each step in a numbered script in scripts/, with relative paths.
- QGIS project with relative paths, styles exported as .qml in styles/.
- Record my requests and your decisions in journal.md.

## Before handing me a result
- Check the CRS, resolution and value ranges of every layer produced.
- Check that class areas add up to the area total.
- Show me a preview of each map and the key figures.
- List deviations from the assignment and unchecked assumptions.

## Language
- Answer in [language].
