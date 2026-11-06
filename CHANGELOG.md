# Changelog

All notable changes to this project are listed here. Versions follow [semantic versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/abdelaalimouid/qgis-agent/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/abdelaalimouid/qgis-agent/compare/v1.0.2...v1.1.0
[1.0.2]: https://github.com/abdelaalimouid/qgis-agent/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/abdelaalimouid/qgis-agent/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/abdelaalimouid/qgis-agent/releases/tag/v1.0.0
