@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Windows virtual environment not found.
  echo Follow the Windows setup steps in README.md. Do not copy the cloud .venv.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" main.py
set "app_exit=%errorlevel%"
if not "%app_exit%"=="0" (
  echo Application exited with error %app_exit%. Copy the error above for troubleshooting.
  pause
)
exit /b %app_exit%
