# Work report: template

A work report is a factual record, like a lab notebook. It says what was done, with what, and what came out. It contains no interpretation and no conclusion. It is the base for any later write-up, whether the user writes it or asks you to.

Writing rules:

- short factual sentences, or tables;
- every figure with its unit and the area it applies to;
- every processing step with its QGIS tool (menu path and algorithm id) and its parameters;
- only the checks actually done, not the ones that could have been done;
- open questions phrased as questions, with no suggested answer.

Format: Markdown (`work_report.md`) at the project root, unless asked otherwise. Write it in the user's language.

---

```markdown
# Work report: [purpose], [area]
[date]

## Purpose
[The question addressed, in one or two sentences. Reference to the assignment.]

## Data
| Item | Details |
|---|---|
| Image | [sensor, level, date, tiles, ids, clouds and snow measured over the area] |
| Bands | [list, resolution, conversion to reflectance] |
| Area | [origin of the boundaries, area, CRS, pixel size and area] |
| Other | [reference layers, source, licence] |

## Processing
| # | Operation | QGIS tool | Parameters | Script |
|---|---|---|---|---|
| 1 | [e.g. NBR calculation] | [Raster > Raster Calculator] | [exact expression] | [scripts/03_indices.py] |

## Files produced
[List of rasters, maps, tables, styles and the .qgz project, with their paths.]

## Results
[Tables of figures, without comment: statistics per area, areas and percentages per class, comparisons.]

## Checks
- [e.g. pixel counts per class add up to the number of pixels in the area]
- [e.g. low-value patches inspected in natural colour]
- [e.g. project reopened: valid layers, correct legends]

## Deviations from the assignment and assumptions
- [e.g. study area different from the assignment's, and why]
- [e.g. park boundary taken from OpenStreetMap, not official]

## Limits and open questions
- [e.g. a single date, no ground truth]
- [e.g. are the negative NBR patches clearings or grassland?]
```
