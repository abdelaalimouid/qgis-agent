# Roadmap

The goal: an open toolkit for AI agents doing GIS and Earth observation, with a benchmark that measures whether their results are right, not just whether they run.

Ideas and help are welcome on every line below. Open an issue to discuss one before starting.

## Now: a solid base

- [x] The `qgis-agent` skill: approved plan, numbered PyQGIS scripts, checks, factual work report, write-up on request
- [x] Sentinel-2 search and download with a safe fallback when the image host is blocked
- [x] Automated tests on Linux, macOS and Windows
- [ ] Windows checked by hand by a first user (help wanted)
- [ ] Gallery website with reproducible examples

## Next: more skills and examples

- [ ] Change detection: burn scars (dNBR), floods, urban growth
- [ ] Land cover classification from training points, with an accuracy table
- [ ] Time series: one index over many dates (lake levels, vegetation seasons)
- [ ] Cartography: map series and atlases with consistent styling
- [ ] Reproducible case studies from Morocco (Ifrane, Azrou, Khénifra, Maâmora), each runnable with one command
- [ ] French and Arabic documentation
- [ ] Works alongside the QGIS MCP servers for live control of the QGIS window

## Later: a benchmark for GIS agents

- [ ] 20 to 30 GIS and remote sensing tasks with verified answers and automatic grading
- [ ] Tasks built around silent errors (double offsets, wrong UTM zone, mixed resolutions, area over the bounding box)
- [ ] Published scores for several AI agents, and a citable dataset (DOI)

## Always

- A small release every month, with a changelog
- Issues answered within a few days
