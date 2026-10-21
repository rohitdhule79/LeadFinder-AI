@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Windows virtual environment not found. Follow README.md first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install PyInstaller==6.12.0
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --windowed --name LeadFinderAI --collect-all geonamescache --collect-all pycountry --add-data "LICENSES.md;." --add-data "README.md;." main.py
if errorlevel 1 goto failed
if not exist "dist\LeadFinderAI\LeadFinderAI.exe" goto failed
echo Built dist\LeadFinderAI\LeadFinderAI.exe. Keep the entire LeadFinderAI directory together.
echo Test the executable on Windows before distributing. Build success does not prove launch success.
exit /b 0
:failed
echo Build stopped. Review the error above. No successful build is claimed.
pause
exit /b 1
