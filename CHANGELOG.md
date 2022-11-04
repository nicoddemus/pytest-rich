# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- Format of each entry is, with each section being optional:

```
## [Version] - YYYY-MM-DD
### Added
### Changed
### Deprecated
### Removed
### Fixed
### Security
``` -->

## [Unreleased]

### Added

- Added `CHANGELOG.md` file. ([#40])
- Confirmed Python 3.11 support. ([#39])
- Added test summary to the end of the test run. ([#31])
- Added support for `--no-header` and `--no-summary` command line options. ([#64])
- Added support for capturing terminal output using Rich's `Console` class, with command line option `--rich-capture`. ([#65])
- Added support for other plugins to add to test header, through invocation of `pytest_report_header` hook. ([#66])

## [0.1.1] - 2022-03-03

## [0.1.0] - 2022-03-02

Initial release!

<!-- Releases links -->

[unreleased]: https://github.com/nicoddemus/pytest-rich/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/nicoddemus/pytest-rich/releases/tag/v0.1.1
[0.1.0]: https://github.com/nicoddemus/pytest-rich/releases/tag/v0.1.0

<!-- PR links -->

[#31]: https://github.com/nicoddemus/pytest-rich/pull/31
[#39]: https://github.com/nicoddemus/pytest-rich/pull/39
[#40]: https://github.com/nicoddemus/pytest-rich/pull/40
[#64]: https://github.com/nicoddemus/pytest-rich/pull/64
[#65]: https://github.com/nicoddemus/pytest-rich/pull/65
[#66]: https://github.com/nicoddemus/pytest-rich/pull/66
