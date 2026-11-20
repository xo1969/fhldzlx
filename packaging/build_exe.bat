@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
echo [Firewheel Typing] building exe ...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "风火轮打字" --icon assets/icon.ico --version-file packaging/version_info.txt --add-data "assets;assets" run.py
if errorlevel 1 (
  echo Build failed. Check the log above.
  exit /b 1
)
echo.
for %%f in ("dist\风火轮打字.exe") do echo OK: %%~ff  (%%~zf bytes)
echo.
echo Done. Double-click dist\风火轮打字.exe to test.
pause
