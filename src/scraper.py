import logging
import re
import time
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import pandas as pd
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from src.config import (
    BASE_URL,
    DEFAULT_CONDITION,
    DEFAULT_PRINTING,
    DELAY_ENTRE_PAGINAS_SEG,
    HEADLESS,
    PAGE_LOAD_TIMEOUT,
    WAIT_AFTER_GOTO_MS,
    WAIT_MARKET_PRICE_MS,
)


RAREZAS_BASE = [
    "Double Rare",
    "Illustration Rare",
    "Ultra Rare",
    "Special Illustration Rare",
]
RAREZA_HYPER_SV = "Hyper Rare"
RAREZA_HYPER_ME = "Mega Hyper Rare"
LOGGER = logging.getLogger("tcgplayer_scraping")


def obtener_rarezas_expansion(row: pd.Series) -> list[str]:
    set_slug = str(row.get("set_slug", "")).lower()
    set_name = str(row.get("set_name", "")).lower()
    if set_slug.startswith("me") or set_name.startswith("me"):
        return RAREZAS_BASE + [RAREZA_HYPER_ME]
    return RAREZAS_BASE + [RAREZA_HYPER_SV]


def limpiar_espacios(texto: object) -> str:
    if texto is None or pd.isna(texto):
        return ""
    return re.sub(r"\s+", " ", str(texto)).strip()


def money_to_float(texto: object):
    text = limpiar_espacios(texto)
    match = re.search(r"\$?\s*([\d,]+(?:\.\d{1,2})?)", text)
    return float(match.group(1).replace(",", "")) if match else None


def limpiar_nombre_carta(titulo: str) -> str:
    return re.sub(r"\s*-\s*#?\d{1,4}/\d{1,4}\s*$", "", limpiar_espacios(titulo)).strip()


def extraer_numero_carta(*textos) -> str:
    match = re.search(r"#?(\d{1,4}/\d{1,4})", " ".join([text for text in textos if text]))
    return match.group(1) if match else ""


def limpiar_rareza(texto_rareza: str) -> str:
    return re.sub(r"\s*,?\s*#?\d{1,4}/\d{1,4}\s*$", "", limpiar_espacios(texto_rareza)).strip(" ,")


def obtener_texto(locator, selector: str) -> str:
    try:
        elemento = locator.locator(selector)
        if elemento.count() == 0:
            return ""
        return limpiar_espacios(elemento.first.inner_text(timeout=5000))
    except Exception:
        return ""


def build_url(row: pd.Series, rareza: str, page_number: int) -> str:
    params = {
        "productLineName": "pokemon",
        "productTypeName": "Cards",
        "view": "grid",
        "Condition": limpiar_espacios(row.get("condicion")) or DEFAULT_CONDITION,
        "Printing": limpiar_espacios(row.get("printing")) or DEFAULT_PRINTING,
        "setName": limpiar_espacios(row.get("set_name")),
        "RarityName": rareza,
        "page": page_number,
    }
    return f"{BASE_URL}/search/pokemon/{limpiar_espacios(row.get('set_slug'))}?{urlencode(params)}"


def scroll_pagina(page) -> None:
    for _ in range(6):
        page.mouse.wheel(0, 900)
        page.wait_for_timeout(1000)
    page.mouse.wheel(0, -1800)
    page.wait_for_timeout(1200)


def esperar_carga_correcta(page) -> bool:
    try:
        page.wait_for_load_state("networkidle", timeout=30000)
    except Exception:
        pass

    page.wait_for_timeout(WAIT_AFTER_GOTO_MS)

    try:
        page.wait_for_selector(".product-card", timeout=30000)
    except PlaywrightTimeoutError:
        return False

    try:
        page.wait_for_selector(".product-card__market-price--value", timeout=WAIT_MARKET_PRICE_MS)
    except PlaywrightTimeoutError:
        pass

    scroll_pagina(page)
    page.wait_for_timeout(2000)
    return True


def existe_pagina_siguiente(page, numero_siguiente: int) -> bool:
    try:
        links = page.locator("a[href]").evaluate_all(
            """
            elements => elements.map(a => ({
                href: a.href || "",
                disabled: a.getAttribute("aria-disabled") || "",
                className: a.className || ""
            }))
            """
        )
    except Exception:
        return False

    for item in links:
        href = item.get("href", "")
        if not href:
            continue
        if str(item.get("disabled", "")).lower() == "true":
            continue
        if "disabled" in str(item.get("className", "")).lower():
            continue

        page_param = parse_qs(urlparse(href).query).get("page", [""])[0]
        if page_param == str(numero_siguiente):
            return True
    return False


def parsear_card(card, row: pd.Series, rareza_buscada: str) -> dict:
    titulo = obtener_texto(card, ".product-card__title")
    rareza_texto = obtener_texto(card, ".product-card__rarity__variant")
    href = ""
    try:
        href = card.locator("a").first.get_attribute("href")
    except Exception:
        pass

    return {
        "set_slug": limpiar_espacios(row.get("set_slug")),
        "set_name": limpiar_espacios(row.get("set_name")),
        "expansion": obtener_texto(card, ".product-card__set-name__variant"),
        "nombre_carta": limpiar_nombre_carta(titulo),
        "numero_carta": extraer_numero_carta(titulo, rareza_texto),
        "rareza": limpiar_rareza(rareza_texto),
        "rareza_buscada": rareza_buscada,
        "market_price_usd": money_to_float(obtener_texto(card, ".product-card__market-price--value")),
        "precio_referencia": row.get("precio_referencia"),
        "url_carta": urljoin(BASE_URL, href) if href else "",
        "condicion": limpiar_espacios(row.get("condicion")) or DEFAULT_CONDITION,
        "printing": limpiar_espacios(row.get("printing")) or DEFAULT_PRINTING,
        "estado_scraping": "OK",
        "mensaje_error": "",
        "observacion": row.get("observacion"),
    }


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


def _scrape_item_with_page(row: pd.Series, page, urls_vistas: set[str]) -> list[dict]:
    rareza_input = limpiar_espacios(row.get("rareza"))
    rarezas = [rareza_input] if rareza_input else obtener_rarezas_expansion(row)
    resultados = []

    for rareza_buscada in rarezas:
        pagina = 1
        while True:
            url = build_url(row, rareza_buscada, pagina)
            page.goto(url, wait_until="load", timeout=PAGE_LOAD_TIMEOUT)

            if not esperar_carga_correcta(page):
                break

            cards = page.locator(".product-card")
            cantidad_cards = cards.count()
            if cantidad_cards == 0:
                break

            for index in range(cantidad_cards):
                data = parsear_card(cards.nth(index), row, rareza_buscada)
                if not data["nombre_carta"] or not data["url_carta"]:
                    continue
                if data["url_carta"] in urls_vistas:
                    continue
                if data["rareza"] not in rarezas:
                    continue

                urls_vistas.add(data["url_carta"])
                resultados.append(data)

            siguiente_pagina = pagina + 1
            if not existe_pagina_siguiente(page, siguiente_pagina):
                break

            pagina = siguiente_pagina
            time.sleep(DELAY_ENTRE_PAGINAS_SEG)

    if not resultados:
        return [_row_error(row, "SIN_RESULTADO", "No se encontraron cards para la fila.")]
    return resultados


def scrape_item(row: pd.Series) -> list[dict]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, slow_mo=120)
        try:
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            return _scrape_item_with_page(row, page, set())
        finally:
            browser.close()


def run_scraping(df_input: pd.DataFrame) -> pd.DataFrame:
    resultados = []
    urls_vistas = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, slow_mo=120)
        try:
            page = browser.new_page(
                viewport={"width": 1400, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )

            total = len(df_input)
            for index, row in df_input.iterrows():
                print(f"Procesando fila {index + 1}/{total}...")
                try:
                    resultados.extend(_scrape_item_with_page(row, page, urls_vistas))
                except Exception as exc:
                    LOGGER.exception("Error procesando fila %s: %s", index + 1, exc)
                    resultados.append(_row_error(row, "ERROR", str(exc)))
        finally:
            browser.close()

    return pd.DataFrame(resultados)
