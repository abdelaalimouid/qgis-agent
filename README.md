# qgis-agent

A Claude Code skill that teaches Claude a reliable way to work in QGIS: scope the request, get a plan approved, run each step as a numbered PyQGIS script, check the results, then hand back a factual work report. It is built for GIS and remote sensing coursework and projects: Sentinel-2 imagery, spectral indices, classification, class areas, maps.

![NDVI map produced by an agent using the skill](docs/example_ndvi_map_azrou.png)

*NDVI around Azrou (Morocco), produced end to end by an agent using the skill, from a plain student request.*

## Install

You need Claude Code on your computer (the Claude desktop app's Code tab, or the terminal) and QGIS 3. Claude on the web cannot drive a QGIS installed on your machine.

### Option 1: as a plugin

In Claude Code:

```
/plugin marketplace add abdelaalimouid/qgis-agent
/plugin install qgis-agent@qgis-agent
```

Or in a terminal:

```bash
claude plugin marketplace add abdelaalimouid/qgis-agent
claude plugin install qgis-agent@qgis-agent
```

To move to a newer version later:

```bash
claude plugin marketplace update qgis-agent
claude plugin update qgis-agent@qgis-agent
```

### Option 2: by hand

1. Download [qgis-agent.zip](https://github.com/abdelaalimouid/qgis-agent/releases/latest/download/qgis-agent.zip), the latest version.
2. Unzip it into `~/.claude/skills/` (on Windows: `C:\Users\<your name>\.claude\skills\`). The file should end up here: `~/.claude/skills/qgis-agent/SKILL.md`.
3. Start a new Claude Code session.

You can also ask Claude Code to do it:

> Download https://github.com/abdelaalimouid/qgis-agent/releases/latest/download/qgis-agent.zip and unzip it into ~/.claude/skills/

## First run

Open Claude Code on your project folder and type:

> Use the qgis-agent skill: check that QGIS is detected, then propose a CLAUDE.md file for this project.

After that, just ask for what you want to do. You don't need to name the skill: Claude opens it by itself whenever a task involves QGIS or geographic data. It answers in your language.

## What the skill does

- It reads the assignment and the project rules, then inventories the data.
- It proposes a plan (steps, equivalent QGIS tools, projection, resolution, files created) and waits for your approval.
- It writes each step as a numbered, rerunnable script using QGIS's own tools (raster calculator, reclassify by table, zonal histogram, print layout), so you can redo every step by hand.
- It shows evidence: map previews, key figures, value ranges.
- It checks before handing over: projection, resolution, ranges, area totals, the project reopened from scratch.
- It hands back a factual work report. The analysis and the write-up are yours.

By default it uses open data with no account: Sentinel-2 from the Earth Search catalogue, OpenStreetMap through the Overpass API.

## Contents

Everything is in [`skills/qgis-agent/`](skills/qgis-agent):

| File | Role |
|---|---|
| `SKILL.md` | The method, read by Claude |
| `scripts/qgis_python.sh` | Runs a script with QGIS's Python (macOS, Linux) |
| `scripts/pyqgis_template.py` | Headless PyQGIS step template |
| `scripts/s2_search.py` | Finds clear Sentinel-2 dates and measures clouds over the area itself |
| `scripts/s2_download.py` | Downloads bands as reflectance, for the needed extent only |
| `scripts/check_data.py` | Inventory and checks of rasters and vectors |
| `scripts/check_project.py` | Reopens a .qgz project from scratch and lists what it really contains |
| `references/` | Tested PyQGIS recipes, bands and indices, work report template |
| `assets/` | Project rules and request templates |

## Tested

- macOS, QGIS 3.44, GDAL 3.13.
- A fresh agent, told nothing about the skill, received a student's request: NDVI around Azrou, five classes, class areas, a map and a QGIS project. It opened the skill by itself, proposed a plan, waited for approval, then produced everything in four minutes. An independent recalculation gives an identical NDVI, class areas within 0.02 %, and a project that reopens with no warnings.
- A second fresh agent, given a request written in French (NDBI and MNDWI on Khénifra), opened the skill by itself, answered in French and planned with the imagery rules: bundled download, reflectance, 20 m for the SWIR indices, full coverage of the area.
- The Sentinel-2 bands downloaded by the skill match those of a reference project (Ifrane forest) pixel for pixel.
- Windows has not been tested yet. Feedback is welcome in the [Issues](https://github.com/abdelaalimouid/qgis-agent/issues).

## Guide

The guide [Working with an AI agent in QGIS](docs/qgis-agent-guide.pdf) (10 pages) explains the method behind the skill: setting up the project, writing the request, the work cycle, checking without redoing everything, and the work report. It ends with a real work report from a Sentinel-2 project on the Ifrane forest.

## Cite

If this skill helps with a report or a paper, please cite it ("Cite this repository" button on the right):

> Mouid, A. (2026). *qgis-agent: a Claude Code skill for working in QGIS* (version 1.0.0) [software]. https://github.com/abdelaalimouid/qgis-agent

## Author

Abdelaali Mouid, Master 2 Industrie X.0, Institut National des Postes et Télécommunications (INPT), Rabat.

## Licence

MIT. Sentinel-2 data remains subject to the Copernicus terms, and OpenStreetMap data to the ODbL licence.

