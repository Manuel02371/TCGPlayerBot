@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  set "PYTHON_CMD=.venv\Scripts\python.exe"
) else (
  where py >nul 2>nul
  if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
  ) else (
    where python >nul 2>nul
    if not errorlevel 1 (
      set "PYTHON_CMD=python"
    ) else (
      echo ERROR: No se encontro Python.
      exit /b 1
    )
  )
)

echo.
echo Generando precios a modificar desde los Excel existentes...
echo No se ejecutara el scraper.
call %PYTHON_CMD% generar_precios_a_modificar.py
if errorlevel 1 (
  echo.
  echo ERROR: No se pudo generar data\output\precios_a_modificar.xlsx
  exit /b 1
)

echo Archivo listo: data\output\precios_a_modificar.xlsx
exit /b 0
