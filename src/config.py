import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]

INPUT_DIR = ROOT_DIR / "input"
OUTPUT_DIR = ROOT_DIR / "data" / "output"
LOG_DIR = ROOT_DIR / "data" / "logs"
REPORTS_DIR = ROOT_DIR / "data" / "reports"
DASHBOARD_DIR = ROOT_DIR / "data" / "dashboard"

INPUT_FILE = INPUT_DIR / "input_scraping.xlsx"
OUTPUT_PARQUET = OUTPUT_DIR / "scraping_historico.parquet"
LOG_FILE = LOG_DIR / "scraping.log"
REPORT_EXCEL = REPORTS_DIR / "reporte_ultima_ejecucion.xlsx"
REPORT_CSV = REPORTS_DIR / "reporte_ultima_ejecucion.csv"
REPORT_JSON = REPORTS_DIR / "resumen_ultima_ejecucion.json"
DASHBOARD_HTML = DASHBOARD_DIR / "dashboard.html"

BASE_URL = "https://www.tcgplayer.com"

DEFAULT_CONDITION = "Near Mint"
DEFAULT_PRINTING = "Holofoil"
HEADLESS = os.getenv("TCGPLAYER_HEADLESS", "true").lower() not in {"0", "false", "no", "n", "visible"}
GENERATE_REPORT = True
GENERATE_DASHBOARD = True

MARGEN_MUY_BUENO = 0.30
MARGEN_BUENO = 0.15

PAGE_LOAD_TIMEOUT = 60000
WAIT_AFTER_GOTO_MS = 5000
WAIT_MARKET_PRICE_MS = 10000
DELAY_ENTRE_PAGINAS_SEG = 3

INPUT_COLUMNS = [
    "set_slug",
    "set_name",
    "rareza",
    "condicion",
    "printing",
    "precio_referencia",
    "activo",
    "observacion",
]

REQUIRED_INPUT_COLUMNS = ["set_slug", "set_name"]

DEFAULT_INPUT_ROWS = [
    {
        "set_slug": "sv09-journey-together",
        "set_name": "sv09-journey-together",
        "rareza": "",
        "condicion": DEFAULT_CONDITION,
        "printing": DEFAULT_PRINTING,
        "precio_referencia": "",
        "activo": "SI",
        "observacion": "Fila heredada desde a.py",
    },
    {
        "set_slug": "me01-mega-evolution",
        "set_name": "me01-mega-evolution",
        "rareza": "",
        "condicion": DEFAULT_CONDITION,
        "printing": DEFAULT_PRINTING,
        "precio_referencia": "",
        "activo": "SI",
        "observacion": "Fila heredada desde a.py",
    },
]

OUTPUT_COLUMNS = [
    "fecha_ejecucion",
    "hora_ejecucion",
    "timestamp_ejecucion",
    "fuente_input",
    "item_key",
    "set_slug",
    "set_name",
    "expansion",
    "nombre_carta",
    "numero_carta",
    "rareza",
    "rareza_buscada",
    "market_price_usd",
    "precio_referencia",
    "url_carta",
    "condicion",
    "printing",
    "estado_scraping",
    "mensaje_error",
    "observacion",
]
