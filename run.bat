@echo off
setlocal
set "VENV_PY=%~dp0.venv\Scripts\python.exe"
if exist "%VENV_PY%" (
  "%VENV_PY%" "%~dp0src\main.py"
) else (
  rem Fallback to python from PATH
  python "%~dp0src\main.py"
)
endlocal
