# Extractor público de precios MasterSet

Extrae cartas desde el catálogo público visible de MasterSet usando Playwright. No consulta `/api` ni otros endpoints privados.

## Instalación

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

## Input

En `data/input/input_expansiones.xlsx`, cree o edite la hoja `Expansiones` con una columna obligatoria `Expansion`. Se ignoran celdas vacías y duplicados.

| Expansion |
| --- |
| Destined Rivals |
| Mega Evolution |

`data/input/input_alertas.xlsx` queda preparado para seleccionar cartas en el futuro, pero por ahora no filtra el reporte.

| Expansion | Card name | Number |
| --- | --- | --- |
| Destined Rivals | Team Rocket's Mewtwo ex 231/182 | 231/182 |

## Ejecución

```powershell
python main.py
```

En Windows tambien puede ejecutar `ejecutar_extractor.bat`. Antes de iniciar muestra las expansiones del Excel y los archivos que se generaran; durante el proceso muestra el avance por expansion y pagina.

Opcionalmente puede ajustar `MASTERSET_TIMEOUT_MS`, `MASTERSET_RETRIES` y `OUTPUT_DIR` como variables de entorno.

## Alertas por Telegram

Defina `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` como variables de entorno de Windows antes de ejecutar el bot. En una sesión de PowerShell:

```powershell
$env:TELEGRAM_BOT_TOKEN = 'su-token'
$env:TELEGRAM_CHAT_ID = 'su-chat-id'
python main.py
```

El bot envía un mensaje al iniciar con el número de expansiones a revisar, agrupa las cartas que bajaron de precio por expansión y termina con un resumen. Cada carta muestra número, precio anterior, precio actual, diferencia y el enlace `Ver carta`. Si una expansión excede el límite de Telegram, se divide en varios mensajes de la misma expansión. Si ejecuta `ejecutar_extractor.bat` con doble clic, configure ambas variables de forma permanente en las variables de entorno de Windows.

El proceso crea `data/output/precios_actuales.xlsx`, `data/output/variaciones_precios.xlsx` y `data/output/historico_precios.parquet`. El segundo contiene todas las cartas nuevas o con una baja frente a su último precio, revisando hasta los cinco cortes anteriores. El Parquet se conserva internamente para esta comparación. Cada nueva ejecución agrega una observación, incluso si es el mismo día. Si una expansión falla, guarda su diagnóstico en `logs/diagnostics/` y continúa con las demás.
