@echo off
setlocal
pushd "%~dp0" || exit /b 1
if not exist ".venv\Scripts\python.exe" (
    echo PriVis needs its Python 3.13 virtual environment. See README.md for setup.
    popd
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -B app.py %*
set "result=%errorlevel%"
popd
if not "%result%"=="0" pause
exit /b %result%
