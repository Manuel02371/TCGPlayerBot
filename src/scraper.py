"""Consulta el buscador de TCGPlayer y convierte su JSON en filas del proyecto."""

import gzip
import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd

from src.config import (
    BASE_URL,
    DEFAULT_CONDITION,
    DEFAULT_PRINTING,
    DELAY_ENTRE_PAGINAS_SEG,
    RAW_DIR,
    SEARCH_API_URL,
    SEARCH_PAGE_SIZE,
)


RAREZAS_BASE = [
    "Double Rare",
    "Illustration Rare",
    "Ultra Rare",
    "Special Illustration Rare",
]
RAREZA_HYPER_SV = "Hyper Rare"
RAREZA_HYPER_ME = "Mega Hyper Rare"


def obtener_rarezas_expansion(row: pd.Series) -> list[str]:
    """Devuelve las rarezas por defecto; las expansiones Mega usan una variante propia."""
    set_slug = str(row.get("set_slug", "")).lower()
    set_name = str(row.get("set_name", "")).lower()
    if set_slug.startswith("me") or set_name.startswith("me"):
        return RAREZAS_BASE + [RAREZA_HYPER_ME]
    return RAREZAS_BASE + [RAREZA_HYPER_SV]


def limpiar_espacios(texto: object) -> str:
    if texto is None or pd.isna(texto):
        return ""
    return re.sub(r"\s+", " ", str(texto)).strip()


def limpiar_nombre_carta(titulo: str) -> str:
    return re.sub(r"\s*-\s*#?\d{1,4}/\d{1,4}\s*$", "", limpiar_espacios(titulo)).strip()


def extraer_numero_carta(*textos: object) -> str:
    match = re.search(r"#?(\d{1,4}/\d{1,4})", " ".join(limpiar_espacios(text) for text in textos))
    return match.group(1) if match else ""


def _row_error(row: pd.Series, status: str, message: str) -> dict:
    return {
        "set_slug": limpiar_espacios(row.get("set_slug")),
        "set_name": limpiar_espacios(row.get("set_name")),
        "expansion": "",
        "nombre_carta": row.get("nombre_carta", ""),
        "numero_carta": row.get("numero_carta", ""),
        "rareza": "",
        "rareza_buscada": limpiar_espacios(row.get("rareza")),
        "market_price_usd": None,
        "precio_referencia": row.get("precio_referencia"),
        "url_carta": "",
        "condicion": limpiar_espacios(row.get("condicion")) or DEFAULT_CONDITION,
        "printing": limpiar_espacios(row.get("printing")) or DEFAULT_PRINTING,
        "estado_scraping": status,
        "mensaje_error": message,
        "observacion": row.get("observacion"),
    }


def build_search_payload(row: pd.Series, rareza: str, offset: int = 0) -> dict:
    """Construye la misma consulta paginada que usa el buscador web."""
    condition = limpiar_espacios(row.get("condicion")) or DEFAULT_CONDITION
    printing = limpiar_espacios(row.get("printing")) or DEFAULT_PRINTING
    return {
        "algorithm": "sales_dismax",
        "from": offset,
        "size": SEARCH_PAGE_SIZE,
        "filters": {
            "term": {
                "productLineName": ["pokemon"],
                "productTypeName": ["Cards"],
                "setName": [limpiar_espacios(row.get("set_name"))],
                "rarityName": [rareza],
            },
            "range": {},
            "match": {},
        },
        "listingSearch": {
            "context": {"cart": {"packages": {}}},
            "filters": {
                "term": {"sellerStatus": "Live", "channelId": 0, "printing": [printing], "condition": [condition]},
                "range": {"quantity": {"gte": 1}},
                "exclude": {"channelExclusion": 0},
            },
        },
        "context": {"cart": {"packages": {}}, "shippingCountry": "PE", "userProfile": {}},
        "settings": {"useFuzzySearch": True, "didYouMean": {}},
        "sort": {},
    }


def fetch_search_payload(payload: dict) -> dict:
    """Descarga una página de datos sin abrir un navegador."""
    request = Request(
        SEARCH_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"No se pudo consultar TCGPlayer: {exc}") from exc
    if payload.get("errors"):
        raise RuntimeError(f"TCGPlayer devolvio errores: {payload['errors']}")
    return payload


def _raw_filename(row: pd.Series, rareza: str, page: int) -> str:
    value = "-".join([limpiar_espacios(row.get("set_slug")), rareza, f"page-{page}"])
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") + ".json.gz"


def save_raw_payload(payload: dict, raw_run_dir: Path, row: pd.Series, rareza: str, page: int) -> None:
    """Guarda la respuesta para poder reprocesarla sin consultar TCGPlayer otra vez."""
    raw_run_dir.mkdir(parents=True, exist_ok=True)
    with gzip.open(raw_run_dir / _raw_filename(row, rareza, page), "wt", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False)


def parse_search_payload(payload: dict, row: pd.Series, rareza_buscada: str) -> tuple[list[dict], int]:
    """Reduce la respuesta externa a las columnas usadas por el histórico y reportes."""
    groups = payload.get("results", [])
    if not groups:
        return [], 0
    group = groups[0]
    records = []
    for product in group.get("results", []):
        product_id = product.get("productId")
        title = limpiar_espacios(product.get("productName"))
        number = limpiar_espacios(product.get("customAttributes", {}).get("number")) or extraer_numero_carta(title)
        if not product_id or not title:
            continue
        records.append(
            {
                "set_slug": limpiar_espacios(row.get("set_slug")),
                "set_name": limpiar_espacios(row.get("set_name")),
                "expansion": limpiar_espacios(product.get("setName")),
                "nombre_carta": limpiar_nombre_carta(title),
                "numero_carta": number,
                "rareza": limpiar_espacios(product.get("rarityName")),
                "rareza_buscada": rareza_buscada,
                "market_price_usd": product.get("marketPrice"),
                "precio_referencia": row.get("precio_referencia"),
                "url_carta": f"{BASE_URL}/product/{int(product_id)}",
                "condicion": limpiar_espacios(row.get("condicion")) or DEFAULT_CONDITION,
                "printing": limpiar_espacios(row.get("printing")) or DEFAULT_PRINTING,
                "estado_scraping": "OK",
                "mensaje_error": "",
                "observacion": row.get("observacion"),
            }
        )
    return records, int(group.get("totalResults", len(records)) or 0)


def _scrape_row(row: pd.Series, urls_vistas: set[str], raw_run_dir: Path) -> list[dict]:
    """Obtiene todas las páginas y rarezas de una fila del Excel."""
    rareza_input = limpiar_espacios(row.get("rareza"))
    rarezas = [rareza_input] if rareza_input else obtener_rarezas_expansion(row)
    resultados = []
    for rareza in rarezas:
        offset = 0
        page = 1
        while True:
            payload = fetch_search_payload(build_search_payload(row, rareza, offset))
            save_raw_payload(payload, raw_run_dir, row, rareza, page)
            cards, total = parse_search_payload(payload, row, rareza)
            for card in cards:
                if card["url_carta"] not in urls_vistas:
                    urls_vistas.add(card["url_carta"])
                    resultados.append(card)
            offset += SEARCH_PAGE_SIZE
            if offset >= total or not cards:
                break
            page += 1
            time.sleep(DELAY_ENTRE_PAGINAS_SEG)
    return resultados or [_row_error(row, "SIN_RESULTADO", "No se encontraron cards para la fila.")]


def run_scraping(df_input: pd.DataFrame) -> pd.DataFrame:
    """Procesa todas las filas activas y devuelve registros listos para el histórico."""
    resultados = []
    urls_vistas: set[str] = set()
    raw_run_dir = RAW_DIR / datetime.now().strftime("%Y%m%d_%H%M%S")
    total = len(df_input)
    for index, row in df_input.iterrows():
        print(f"Procesando fila {index + 1}/{total}...")
        try:
            resultados.extend(_scrape_row(row, urls_vistas, raw_run_dir))
        except Exception as exc:
            print(f"Error procesando fila {index + 1}: {exc}")
            resultados.append(_row_error(row, "ERROR", str(exc)))
    return pd.DataFrame(resultados)
