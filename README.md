# TCGPlayerBot

Bot de Python que consulta precios de cartas Pokémon en TCGPlayer y conserva un historial para comparar variaciones.

## Cómo funciona

```text
input/input_scraping.xlsx
        ↓
consulta directa al buscador de TCGPlayer
        ↓
datos crudos temporales en data/raw/
        ↓
histórico Parquet y reportes Excel/CSV/JSON
```

No abre un navegador ni visita una carta por vez. Solicita los datos paginados del buscador, guarda cada respuesta comprimida para auditoría y la transforma localmente.

## Carpetas importantes

```text
input/                         Excel que tú editas
data/output/                   Histórico y última ejecución
data/reports/                  Reportes finales
data/raw/                      Copias temporales para auditoría (no se suben a Git)
src/                           Código del proceso
tests/                         Pruebas automáticas
```

## Excel de entrada

Edita `input/input_scraping.xlsx`. Las columnas son:

```text
set_slug | set_name | rareza | condicion | printing | precio_referencia | activo | observacion
```

- `set_slug` y `set_name` son obligatorias.
- `activo` acepta `SI`, `SÍ`, `S`, `YES`, `TRUE`, `1` o `X`.
- Si `rareza` queda vacía, se usan las rarezas configuradas para la expansión.
- `precio_referencia` es opcional y habilita la clasificación de oportunidades.

## Ejecutar

```bash
pip install -r requirements.txt
python -m src.main
```

En Windows también puedes abrir `run_scraping.bat`.

## Resultados

| Archivo | Contenido |
| --- | --- |
| `data/output/scraping_historico.parquet` | Todas las ejecuciones acumuladas. |
| `data/output/scraping_ultima_ejecucion.xlsx` | Datos de la última ejecución. |
| `data/reports/reporte_ultima_ejecucion.xlsx` | Resumen, detalle, bajas, subidas y oportunidades. |
| `data/reports/reporte_ultima_ejecucion.csv` | El detalle en formato CSV. |
| `data/reports/resumen_ultima_ejecucion.json` | Totales para consumo automático. |

## Automatización

GitHub Actions lo ejecuta diariamente a las 10:00 a.m. y 4:00 p.m. de Perú. Al terminar, actualiza el histórico, la última ejecución y los reportes.

## Validar

```bash
python -m unittest tests.test_basic_flow
```
