# Changelog

All notable changes to this project are listed here. Versions follow [semantic versioning](https://semver.org/).

## [Unreleased]

## [1.2.0] - 2026-11-11

Imagery that is already in the folder (sent by someone, downloaded by hand or with another tool) skipped the download scripts and their protections. With the skill installed, an agent could still subtract the Earth Search mirror's offset a second time, and average a cloudy scene that came without a mask band.

### Added
- `scripts/check_imagery.py` checks a folder of Sentinel-2 level 2A bands before any calculation. It reads the STAC item (`earthsearch:boa_offset_applied` before `raster:bands`) or ESA's `MTD_MSIL2A.xml`, falls back on the file names and the acquisition date, and prints the reflectance formula with its evidence. It tests the formula on the pixels, says when they cannot decide (bright ground), and estimates the cloud share when there is no mask band (Fmask haze test on B02 and B04, a lower bound), optionally inside a study area (`--area`) and as a mask (`--mask-out`).
- Imagery rules in `SKILL.md` and `references/remote_sensing.md` for imagery already in the folder: metadata first, a stated assumption when there is none (offset −1000 after 25 January 2022), and no average of a scene without a mask band before its cloud share is measured and reported.
- Tests for these rules, on synthetic rasters and offline.

### Changed
- The sanity check before computing indices: almost no pixel of a visible band should be negative with the chosen formula. The median check (below 0.03) stays, but over bright ground neither check can see a double offset: the rules now say so, and that only the metadata decides there.
- The reflectance rule mentions ESA's reprocessed archive (baseline 05.00 and later), which has the offset even before 2022.

## [1.1.1] - 2026-11-09

### Added
- Codex support. The same skill installs into `~/.agents/skills/` (or `.agents/skills/` in a project), and the README, website and guide explain how. The skill reads `AGENTS.md` (Codex) as well as `CLAUDE.md` (Claude Code), and asks the user to approve network access when its commands run in a sandbox.

### Changed
- The project rules template is now `assets/project_rules_template.md`, for any agent.

## [1.1.0] - 2026-11-06

### Added
- Automated tests (pytest) for the Sentinel-2 reflectance rules, the data and project checkers, the step template and the PyQGIS recipes taught in `references/pyqgis.md`. They run on every push: Linux and macOS with QGIS 4.2 from conda-forge, Windows with the official QGIS 3.44 installer.
- A weekly live check that downloads real Sentinel-2 data from both Earth Search collections and confirms they give the same reflectance.
- `qgis_python.sh` now uses `QGIS_PYTHON`, or any Python on the PATH that imports QGIS (conda-forge, OSGeo4W, Linux packages), before looking for the macOS app.
- Contributor guide, roadmap, code of conduct, issue and pull request templates.

### Fixed
- On Windows, `python-qgis-ltr.bat` leaves the Processing plugin off the Python path, so the step template failed there. The template, the recipe in `references/pyqgis.md` and the test setup now add it from `QgsApplication.pkgDataPath()`.

### Changed
- `s2_download.py` and `s2_search.py` are split into small functions that tests can check offline. Command-line use and outputs are unchanged.

## [1.0.2] - 2026-11-06

### Changed
- The skill writes up results when asked (interpretation, report, paper draft), built only from the processing results and with limits kept visible. The factual work report stays the default ending.
- Wording no longer assumes the user is a student.

## [1.0.1] - 2026-11-05

### Fixed
- Sentinel-2 downloads when the default image host is blocked: both scripts take `--collection sentinel-2-l2a` to use the mirror, and the download script no longer subtracts that mirror's offset twice (its values already include it, while its metadata still declares it).

### Added
- Clear errors on network failure or ids from the wrong collection, and a warning when visible reflectance is implausibly low.

## [1.0.0] - 2026-11-05

### Added
- First public release: the `qgis-agent` skill (method, references, templates), helper scripts for QGIS, Sentinel-2 search and download, data and project checks, the method guide and an example map.

[Unreleased]: https://github.com/abdelaalimouid/qgis-agent/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/abdelaalimouid/qgis-agent/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/abdelaalimouid/qgis-agent/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/abdelaalimouid/qgis-agent/compare/v1.0.2...v1.1.0
[1.0.2]: https://github.com/abdelaalimouid/qgis-agent/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/abdelaalimouid/qgis-agent/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/abdelaalimouid/qgis-agent/releases/tag/v1.0.0
