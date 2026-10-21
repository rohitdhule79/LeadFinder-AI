# LeadFinder AI

A local-first PySide6 desktop workspace for public professional lead discovery and review. Dark glass-style panels, an optional light theme, guided targeting, durable SQLite deduplication, and CSV/Excel exports. There are no bundled profiles or fabricated statistics.

## Download or transfer this exact project

The current implementation is present in the cloud workspace but is not committed/pushed to GitHub. A GitHub **Code → Download ZIP** or `git clone` may therefore give you an empty or older project. Use the prepared **LeadFinder-AI-source.zip** supplied with the review report. Its cloud path is `/workspace/exports/LeadFinder-AI-source.zip`.

1. Download the source ZIP from the report's download link. If the client does not expose that link, use its workspace file-download facility for the exact path above, when available. No SSH server or public download service is configured here. If neither download route exists in your client, a file-transfer facility is still needed; copying a cloud path into Windows will not transfer files.
2. In Windows File Explorer, right-click the ZIP and choose **Extract All**. Do not run the app inside the ZIP.
3. Move the extracted inner `LeadFinder-AI` folder to your user folder, giving a path such as `C:\Users\YourName\LeadFinder-AI`. Confirm that `main.py`, `requirements.txt`, `run.bat`, `build_windows.bat`, `src` and `tests` are directly inside it.
4. The ZIP deliberately excludes `.git`, `.venv`, caches, local databases, credentials, and build outputs. It contains source, not a Windows executable. Create a fresh Windows virtual environment below; a Linux `.venv` cannot be transferred to Windows.

## Windows setup (beginner guide, Python 3.12 x64)

Target: Windows 10 (1809 or later) / Windows 11 on an Intel/AMD 64-bit PC, with the **64-bit CPython 3.12** installer from https://www.python.org/downloads/windows/ . Windows ARM64 and 32-bit Python are not validated targets. Allow the Python launcher to be installed; administrator access is not normally needed for a per-user installation. Internet access to PyPI is required for dependency installation, but not for local CSV import/review/export.

Open **Command Prompt** (Start → type `cmd` → Enter). These commands are for Command Prompt, not PowerShell. If you chose another project folder, change the first path accordingly. Run each line and stop if it reports an error:

```bat
cd /d "%USERPROFILE%\LeadFinder-AI"
py -3.12 --version
py -3.12 -c "import struct; print('Python bits:', struct.calcsize('P') * 8)"
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m pytest -q
run.bat
```

The version must be Python 3.12 and the bit count must be 64. No virtual-environment activation or PowerShell execution-policy change is needed. Wait for installation to finish. `pip check` should report no broken requirements, and tests must complete before claiming Windows validation. `run.bat` uses the environment's Python directly and keeps the error visible on failure. After setup, double-click `run.bat` for subsequent launches. Close the app before starting another instance against the same database.

No Docker, paid API, cloud account, password, or browser cookie is required. The `.env.example` documents an optional `LEADFINDER_DATA_DIR` override; `.env` files are not automatically loaded. Set the variable in your shell if needed. Default Windows storage is `%LOCALAPPDATA%\LeadFinderAI\data\leads.db`. Linux uses `~/.local/share/LeadFinderAI/data/leads.db`. Data stays local and is not uploaded. To move existing lead data separately, use Settings → Back up database and transfer that backup yourself; production data is not part of the source ZIP.

### Windows troubleshooting

- **`py` is not recognized:** repair the Python installation and install the launcher, reopen Command Prompt, then retry. If using `python` instead, first verify `python --version` is 3.12 and 64-bit; do not accidentally use a different interpreter.
- **`No matching distribution` / Qt installation errors:** check Python version and architecture. The pinned Qt wheels are intended here for Windows x64 and Python 3.12. Do not reuse the cloud `.venv`.
- **Connection/certificate errors installing dependencies:** check your network/proxy and system date. Use your organization's trusted certificate configuration where required; do not disable TLS verification.
- **`DLL load failed` importing PySide6:** confirm x64 Python and supported Windows, then check Microsoft's Visual C++ runtime guidance at https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist . Install/repair the supported x64 runtime if needed. Capture the complete error if it persists.
- **No visible window:** launch from Command Prompt with `.venv\Scripts\python.exe main.py`. Remove a manually configured `QT_QPA_PLATFORM=offscreen` setting for an interactive launch (`set QT_QPA_PLATFORM=`). Tests use offscreen rendering in their own process.
- **Browser does not open:** copy the generated review-page query into your browser. The app reports an unsuccessful browser-open request; opening a URL is not evidence that web search returned results.
- **Population refresh fails:** offline geography remains available. Confirm HTTPS access to `api.worldbank.org`, then retry. An allowlist entry alone does not prove live connectivity.

## First real workflow

1. Choose **Find Leads**, then geography, professional roles, and qualification rules. Continue to the review page.
2. **Open query in browser** opens a Google query for a human to use under Google's terms. It does not fetch results automatically. No free automated provider is represented as connected or approved.
3. On **Data Sources**, save a blank import template. Populate it only with records you are authorized to use. No logged-in LinkedIn scraping, CAPTCHA bypass, or cookie collection is implemented.
4. Return to the review page and choose **Import authorized CSV / Start**. Processing runs on a background thread and supports pause/resume/cancel. Partial successful inserts survive cancellation; rerunning is safe.
5. Inspect records in **Lead Database**. Double-click a row to read provenance, edit identity fields, add reviewer evidence, verify manually, or reject. Verification requires name, role, country, source and reviewer notes. Editing identity fields resets verification. Manual verification does not certify follower counts or profile currency.
6. Select rows or export matching, verified, or unexported records. Choose `.csv` or `.xlsx` explicitly in the filename. Existing files are rejected, not overwritten. Exports include provenance, preserve missing metrics, neutralize spreadsheet formulas, and mark records exported only after successful writes.

### Import schema and filtering

Required headers: `profile_url,source_url`. Recommended: `full_name,designation,country`. Optional: `company,industry,continent,division,city,followers,connections,metric_source,metric_observed_at,snippet,notes`.

Only HTTPS LinkedIn `/in/` profile URLs are accepted. Tracking parameters, fragments, trailing slashes and regional host aliases are normalized. Source URLs must be HTTPS. Imported identity and geography must be supplied; search criteria are never silently copied into evidence. Country, location, role, company and industry filters use case-insensitive textual matching, not independently verified semantic identity. All accepted records start as **Needs Review / Unverified**. Rejections and duplicate outcomes appear in history. Keep source snippets minimal and permitted.

Blank metrics or `Unknown` become SQL NULL, never zero. Numeric metrics require `metric_source` and an ISO observation date such as `2026-01-15`. AND requires every active threshold; OR and Independent accept either active threshold. A threshold of zero disables that metric filter. Unknown values fail active thresholds unless explicitly allowed. Unknown values can never independently demonstrate the requested minimum.

CSV imports are limited to 20 MB and 100,000 rows. New lead target stops processing when reached; no volume is guaranteed. Existing profiles always remain unique globally, even across countries, restarts, and exports. Country-first and global indexed lookups avoid scanning the whole database. Existing rows are preserved rather than overwritten by repeat imports. Permanent exclusion is intentionally always enabled. Use the database to review and re-export old records. Deleting a lead also deletes its deduplication identity, with a warning.

## Geography and population

Offline country/territory continent assignments come from GeoNames through `geonamescache`; each entry belongs to one of seven continent categories. Territories remain separate entries, so the list is not a claim of 195 sovereign states. Transcontinental assignments follow GeoNames, not inferred geography. ISO subdivisions and local types come from pycountry; official spellings may include accents. Missing subdivisions permit manual text entry rather than fabricated entries. Current subdivision data is tied to the pinned package release, not an automatic boundary update service.

**Refresh population** makes one user-triggered HTTPS request to `api.worldbank.org`, indicator `SP.POP.TOTL`. It caches the most recent non-null dated observation returned in the latest 20 observations. Displays include year, source, license and refresh timestamp. A failure keeps the last good cache; no population is displayed without metadata. The cloud environment configuration now contains the saved domain rule, but the latest live request still returned proxy 403. Runtime connectivity remains unresolved; the saved rule alone is not evidence of access. Source: https://data.worldbank.org/indicator/SP.POP.TOTL . No live population success is claimed.

## Backup, restore and deletion

Use **Settings → Back up database** to write a SQLite backup to a new filename. Restore validates SQLite integrity, schema version and expected core columns, creates a safety backup next to the live database, and then restores. Wait for background work to finish first. Do not restore arbitrary databases from untrusted senders. Lead deletion requires confirmation; **Delete all lead data** removes leads and result records while retaining search configurations and historical run counts. Use a fresh `LEADFINDER_DATA_DIR` for a completely separate workspace.

The schema is initialized transactionally at version 1 (`PRAGMA user_version`). Reopening preserves data; unknown future versions are rejected. Interrupted running searches are marked Interrupted at launch. Rerun their criteria and reselect the original authorized CSV to continue safely; there is no automatic provider cursor resume. Run statuses, counts and error summaries are stored in SQLite, without raw provider credentials or a separate personal-data log.

## Tests and cloud validation

```sh
python -m pytest -q
```

Linux without a display:

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
QT_QPA_PLATFORM=offscreen LEADFINDER_DATA_DIR=/tmp/leadfinder-smoke .venv/bin/python main.py --smoke-test
```

Tests use synthetic records in temporary databases only. They cover database initialization/reopening, schema-version protection, country/global deduplication, URL validation, NULL metrics, AND/OR rules, reruns and interrupted runs, cancel/pause mechanics, timeout/rate-limit outcomes, CSV import, CSV/XLSX output and formula neutralization, failed export status, manual verification, backup/restore, saved criteria, geography caching/failure and Qt navigation/import state. Provider error tests use mocks and do not establish a connection to a real automated search service. The app smoke command opens all nine pages before exiting. It does not replace manual Windows acceptance testing.

## Build the Windows executable

On Windows, after tests pass:

```bat
build_windows.bat
```

The script first checks for the Windows virtual environment, checks dependencies and runs tests. It stops on failures, installs pinned PyInstaller, then attempts to build `dist\LeadFinderAI\LeadFinderAI.exe` with its supporting files. Keep the entire directory together. The script includes README/license notices in the bundle. Test the generated executable on a clean Windows x64 machine before distribution: open every page, import authorized records, restart and check persistence/deduplication, export CSV/XLSX, and exercise backup/restore. A successful build alone does not establish that these workflows work. Packaging has **not** been run on Windows in this Linux cloud environment. No `.exe` is included or claimed ready.

## Architecture

- `src/ui/`: Qt shell, page controllers, portable gradient theme system.
- `src/database/store.py`: parameterized SQLite access, versioning, indexes, review and backup operations.
- `src/search/`: query generation, URL/metric validation and cancellable import orchestration.
- `src/providers/`: protocol, manual browser mode and authorized CSV provider.
- `src/geography/`: offline catalogs and dated optional population cache.
- `src/exports/`: exclusive safe writes and export accounting.
- `src/workers/`: Qt background task signals.
- `tests/`: temporary synthetic fixtures, no production seed data.

SQLite's standard library driver is used directly; SQLAlchemy is installed per the requested stack but is not required by the version 1 store. The Liquid Glass direction is implemented as static opaque gradient cards, rounded borders and dark/light color themes, not true translucent backdrop blur, animated glass, a custom vector icon set or a finished native Windows visual treatment. Light-theme control contrast is corrected, but Windows high-DPI/accessibility acceptance is still pending. No web server is needed.

## Current limits

This is an implemented initial desktop version, not a certified production release. Windows interaction, accessibility/high-DPI behavior and executable distribution still need Windows testing. No approved automatic free search provider is configured; browser search and authorized import are the working discovery route. No automated follower extraction or automatic profile verification exists. Provider pacing settings are unnecessary for the manual workflow; population requests have a timeout but no automatic retries. Geographic dataset refresh uses pinned-package updates; there is no boundary dataset import editor. No advanced fuzzy identity merging, automatic cursor recovery, customizable retention scheduler, export-column editor or dedicated rotating log viewer is implemented. Bulk verification/editing is not provided; review is per record. Database filtering/pagination is SQL-backed; each export is capped at 100,000 matching rows. Very large exports run on the UI thread and may temporarily block interaction. Only run one application instance per database to avoid cross-instance recovery status changes.

See [LICENSES.md](LICENSES.md) for third-party notices. Respect data licenses and each source's current access terms; import permission is the user's responsibility. No automated use of search-engine HTML endpoints is implemented or justified by this project.

## Validation and outstanding work

See [REVIEW.md](REVIEW.md) for this review's actual tests, Windows dependency-availability checks, verified fixes and remaining gaps. Test results from Linux are not Windows launch/packaging results. The provider interface and browser link do not implement automated public-web search: a future provider needs a permitted access method, current terms review, configuration, parsing and real request validation. The current timeout/rate-limit tests use mock providers.
