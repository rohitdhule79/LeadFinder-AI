# Existing-project review — 21 October 2026

## Environment and files

Inspected the complete application source, tests, README, licenses, configuration, requirements and Windows scripts before edits. Existing files were retained in `/workspace/LeadFinder-AI`; no replacement project or Git worktree was created. The Git branch is unborn and project files are untracked: there is no committed application snapshot to download from GitHub. No push or repository reset was performed.

Reading the environment configuration confirmed that `install_script`, `start_skill`, and the custom `api.worldbank.org` egress rule are present in the saved base configuration (no pending draft returned). These fields were preserved. This verifies configuration persistence, not successful restoration into a new task or runtime network access. Retrying World Bank population refresh still returned `ProxyError: 403 Forbidden`. No additional credentials are needed for the manual/import workflow. Publication/restoration was not independently tested in this review.

## Verified fixes

- Country selection: PySide6 editable `setCurrentText` could show India while retaining Afghanistan's underlying item data. Country codes now resolve from the exact visible supported entry, subdivision lists react to visible country changes, and saved criteria select the proper item.
- Manual administrative division: typed/custom division text was silently discarded because the combo retained a previous index. Criteria now preserve manual text and keep canonical names for listed divisions. Regression tests cover both paths and saved-search loading.
- Population: malformed/missing year or non-numeric values can no longer be cached as a dated population. The most recent valid year is selected even if the response is out of order. Errors preserve the last good cache. This is verified with mocked responses, not a successful live service response.
- Light theme: explicit button, dropdown, header, selection and progress colors fix dark inherited surfaces with dark text. Offscreen screenshots of dark/light pages were inspected. Native Windows appearance, accessibility and high-DPI behavior are untested.
- Browser launch now reports an unsuccessful operating-system URL-open request, rather than ignoring the returned failure. No real browser/search results were tested here.
- `run.bat`: quoted interpreter path, clear missing-venv guidance, preserved app exit code, visible errors when launched by double-click.
- `build_windows.bat`: missing-venv check, dependency/test checks before packaging, stop on failure, include README/license notices, check expected executable exists, clear reminder to test output. Both batch files use CRLF. These changes were statically reviewed, not executed under Windows Command Prompt.
- README: explicit download/extraction instructions, Windows x64/Python 3.12 requirements, Command Prompt commands without activation, troubleshooting, data locations, limitations and post-build acceptance steps.

## Validation results

- Baseline full suite: **37 passed**, 0 failed.
- Final full suite: **44 passed**, 0 failed, 0 skipped. Command: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q`. Seven added cases cover the geography regressions and malformed/out-of-order population data.
- Python: **3.12.14**, Linux x64. `pip check`: **No broken requirements found**.
- Application: `QT_QPA_PLATFORM=offscreen LEADFINDER_DATA_DIR=/tmp/leadfinder-final-smoke .venv/bin/python main.py --smoke-test` completed successfully (nine-page startup/navigation). This does not test a visible Windows window or opening the user's browser.
- Windows dependency availability: a pip dry-run for CPython 3.12 / win_amd64 resolved the pinned requirements and optional PyInstaller 6.12.0 to compatible wheel artifacts, including Qt/shiboken and greenlet. Windows-only dependencies (colorama, pefile, pywin32-ctypes) were included explicitly because cross-platform pip running on Linux does not fully evaluate Windows markers. The resolution also honors PyInstaller's Windows-specific `pefile!=2024.8.26,>=2022.5.30` constraint. Artifact availability and metadata resolution are not runtime or executable-build tests.
- No Windows host, `cmd.exe`, Windows launch, real automated search, or Windows executable packaging was tested. No executable is delivered.

## Feature audit

| Area | Implemented | Remaining / limitations |
| --- | --- | --- |
| Search | Query builder, manual browser link, authorized CSV import, provider protocol, background processing, pause/resume/cancel | **No automated public-web-search provider integration.** BrowserSearch deliberately raises explanatory guidance rather than returning invented results. No profile parser/fetcher, live search request, quota check or search-source authorization is implemented. |
| Geography | Offline GeoNames country/continent catalog, pycountry ISO subdivisions with local types, editable divisions, optional population cache with year/source/refresh metadata | Package datasets are static snapshots. No in-app country/boundary dataset refresh/import, continent reassignment editor, or reliable current population access in this cloud runtime. GeoNames territory list is not a sovereignty count. |
| Liquid Glass UI | Nine pages, sidebar, rounded gradient cards, dark/light themes, empty dashboard, Qt controls and selection states | Opaque gradients approximate the design direction. No true glass translucency/backdrop blur, custom vector icon set, animation system or toast system. Status messages use a bottom label and dialogs. Native Windows polish/accessibility/high-DPI testing remains. |
| Storage | Version 1 SQLite schema, indexes, persistent global URL uniqueness, country-first lookup, search history and saved criteria | No multi-version migration history; initialization/reopening/version protection are tested. One instance per database is advised. Interrupted runs can be rerun, but do not resume a provider cursor automatically. |
| Review/export | Per-lead evidence/notes/identity editing, manual verification, selected/matching/new/verified exports, formula protection, backup/restore | No bulk review editing, metric correction UI, configurable export columns/retention, or log viewer. Large exports may block the UI; maximum 100,000 matching records per export. History shows only the first 500 result details. |
| Settings | Theme, database health, backup/restore, folder access and data deletion | Several requested advanced settings are explanatory text rather than editable controls: no automated provider configuration/rate-limit controls, retention scheduler or export defaults editor. |
| Windows delivery | Source, `run.bat`, `build_windows.bat`, pinned dependencies and instructions | No tested installer/executable, signing, update channel or completed Qt redistribution compliance review. |

## Next steps

1. Transfer the source ZIP and create a fresh Windows x64 Python 3.12 virtual environment using README commands.
2. Run tests on Windows, then `run.bat`; inspect all pages and complete authorized import → review → export → restart/deduplication → backup/restore.
3. Try World Bank refresh on that PC and record the real result. A cloud proxy error does not establish that the Windows PC will fail.
4. Only after Windows launch passes, run `build_windows.bat` and test the entire output directory on a clean Windows machine.
5. For automated discovery, choose and verify a provider whose current terms permit the intended requests, then implement/configure and test it. Keep browser/import fallback until that is proven. UI refinement is separate from proving real search results.
