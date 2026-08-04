@echo off
setlocal
cd /d "%~dp0"
set "EXIT_CODE=1"

if exist ".venv\Scripts\python.exe" (
  set "PYTHON_CMD=.venv\Scripts\python.exe"
) else (
  set "PYTHON_CMD=py -3"
)

echo.
echo ============================================================
echo   EXTRACTOR PUBLICO MASTERSET - PRECIOS POR EXPANSION
echo ============================================================
echo.
echo INPUT: data\input\input_expansiones.xlsx ^> hoja Expansiones ^> columna Expansion
call %PYTHON_CMD% -c "from main import expansions_from_input; print('Expansiones a procesar:'); [print(f'  {i}. {value}') for i, value in enumerate(expansions_from_input(), 1)]"
if errorlevel 1 goto :error
echo INPUT DE ALERTAS: data\input\input_alertas.xlsx ^> reservado para uso futuro

echo.
echo OUTPUTS QUE SE GENERARAN:
echo   - data\output\precios_actuales.xlsx
echo   - data\output\variaciones_precios.xlsx
echo   - data\output\historico_precios.parquet
echo.
echo AVANCE: se mostrara expansion, pagina, cartas y total acumulado.
echo ============================================================
echo.

call %PYTHON_CMD% main.py
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" goto :error
echo EJECUCION TERMINADA. Revise los archivos indicados arriba.
goto :end

:error
echo.
echo La ejecucion termino con error. Revise logs\masterset_catalog.log.

:end
exit /b %EXIT_CODE%
