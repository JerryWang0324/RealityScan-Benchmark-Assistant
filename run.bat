@echo off
setlocal

cd /d "%~dp0"

set "VENV_PYTHON=.venv\Scripts\python.exe"

if exist ".venv\" goto check_venv

echo No project virtual environment was found. Creating .venv...
call :find_python
if errorlevel 1 goto python_not_found

%PYTHON_CMD% -m venv ".venv"
if errorlevel 1 goto venv_create_failed

if not exist "%VENV_PYTHON%" goto venv_create_failed

echo Installing runtime dependencies...
"%VENV_PYTHON%" -m pip install -e .
if errorlevel 1 goto install_failed
goto verify_imports

:check_venv
if not exist "%VENV_PYTHON%" goto broken_venv
"%VENV_PYTHON%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1
if errorlevel 1 goto broken_venv

"%VENV_PYTHON%" -c "import PySide6, pandas, matplotlib, rs_benchmark" >nul 2>&1
if not errorlevel 1 goto imports_ready

echo Required packages are missing or unavailable. Installing runtime dependencies...
"%VENV_PYTHON%" -m pip install -e .
if errorlevel 1 goto install_failed

:verify_imports
"%VENV_PYTHON%" -c "import PySide6, pandas, matplotlib, rs_benchmark" >nul 2>&1
if errorlevel 1 goto import_failed

:imports_ready
if "%RS_BENCHMARK_SMOKE_TEST%"=="1" (
    echo Smoke test passed: Python, runtime dependencies, and rs_benchmark are available.
    exit /b 0
)

"%VENV_PYTHON%" -m rs_benchmark.main
if errorlevel 1 goto gui_failed
exit /b 0

:find_python
set "PYTHON_CMD="
where py >nul 2>&1
if errorlevel 1 goto try_python
py -3.12 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1
if errorlevel 1 goto try_python
set "PYTHON_CMD=py -3.12"
exit /b 0

:try_python
where python >nul 2>&1
if errorlevel 1 exit /b 1
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1
if errorlevel 1 exit /b 1
set "PYTHON_CMD=python"
exit /b 0

:python_not_found
echo.
echo ERROR: Python 3.12 or newer could not be found.
echo Install Python 3.12+ from https://www.python.org/ and try again.
goto fail

:venv_create_failed
echo.
echo ERROR: Failed to create the .venv virtual environment.
echo Check your Python installation and available disk space, then try again.
goto fail

:broken_venv
echo.
echo ERROR: The existing .venv is damaged, incompatible, or missing Scripts\python.exe.
echo Remove or rename .venv, then run this script again to recreate it.
goto fail

:install_failed
echo.
echo ERROR: Failed to install the project runtime dependencies.
echo Check your internet connection and the pip output above, then try again.
goto fail

:import_failed
echo.
echo ERROR: Dependencies were installed, but the required modules still cannot be imported.
echo Review the output above or recreate .venv, then try again.
goto fail

:gui_failed
echo.
echo ERROR: RealityScan Benchmark Assistant failed to start or exited with an error.
echo Review any error output above for details.
goto fail

:fail
echo.
pause
exit /b 1
