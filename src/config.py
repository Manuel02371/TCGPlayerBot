"""Rutas y reglas centrales del proceso."""

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]

INPUT_DIR = ROOT_DIR / "input"
OUTPUT_DIR = ROOT_DIR / "data" / "output"
REPORTS_DIR = ROOT_DIR / "data" / "reports"
RAW_DIR = ROOT_DIR / "data" / "raw"  # Copias temporales de las respuestas JSON.

INPUT_FILE = INPUT_DIR / "input_scraping.xlsx"
OUTPUT_PARQUET = OUTPUT_DIR / "scraping_historico.parquet"
LATEST_EXECUTION_EXCEL = OUTPUT_DIR / "scraping_ultima_ejecucion.xlsx"
REPORT_EXCEL = REPORTS_DIR / "reporte_ultima_ejecucion.xlsx"
REPORT_CSV = REPORTS_DIR / "reporte_ultima_ejecucion.csv"
REPORT_JSON = REPORTS_DIR / "resumen_ultima_ejecucion.json"

BASE_URL = "https://www.tcgplayer.com"
SEARCH_API_URL = "https://mp-search-api.tcgplayer.com/v1/search/request?isList=false"
SEARCH_PAGE_SIZE = 24

DEFAULT_CONDITION = "Near Mint"
DEFAULT_PRINTING = "Holofoil"
MARGEN_MUY_BUENO = 0.30
MARGEN_BUENO = 0.15

DELAY_ENTRE_PAGINAS_SEG = 0.25  # Pausa corta para no saturar la búsqueda remota.

REQUIRED_INPUT_COLUMNS = ["set_slug", "set_name"]

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
