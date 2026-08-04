from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

from src.export_excel import write_excel
from src.scraper import CatalogScraper, ScraperConfig, assert_catalog_allowed
from src.storage import HISTORY_COLUMNS, append_history, find_new_or_lower, load_history
from src.telegram import send_job_finished, send_job_started, send_price_drop_alerts

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
INPUT = DATA / "input" / "input_expansiones.xlsx"
OUTPUTS = ROOT / os.getenv("OUTPUT_DIR", "data/output")
LOGS = ROOT / "logs"
TIMEOUT_MS = int(os.getenv("MASTERSET_TIMEOUT_MS", "30000"))
RETRIES = int(os.getenv("MASTERSET_RETRIES", "2"))


def expansions_from_input() -> list[str]:
    if not INPUT.exists():
        raise FileNotFoundError(f"No existe {INPUT.name}.")
    frame = pd.read_excel(INPUT, sheet_name="Expansiones")
    if "Expansion" not in frame.columns:
        raise ValueError("La hoja Expansiones debe incluir la columna Expansion.")
    return list(dict.fromkeys(value.strip() for value in frame["Expansion"].dropna().astype(str) if value.strip()))


def main() -> None:
    LOGS.mkdir(exist_ok=True)
    logging.basicConfig(filename=LOGS / "masterset_catalog.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    expansions = expansions_from_input()
    assert_catalog_allowed()
    telegram_token, telegram_chat_id = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    send_job_started(len(expansions), telegram_token, telegram_chat_id)
    execution_id, extracted_at = str(uuid.uuid4()), datetime.now().astimezone().isoformat(timespec="seconds")
    rows, empty, errors = [], [], []
    config = ScraperConfig(TIMEOUT_MS, RETRIES, LOGS / "diagnostics")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        scraper = CatalogScraper(browser, config)
        for index, expansion in enumerate(expansions, start=1):
            print(f"[{index}/{len(expansions)}] Expansión: {expansion}")
            try:
                found, pages = scraper.scrape_expansion(expansion)
                if found:
                    for row in found:
                        row.update(execution_id=execution_id, extracted_at=extracted_at, execution_date=extracted_at[:10])
                    rows.extend(found)
                else:
                    empty.append(expansion)
                logging.info("%s: %s cartas en %s páginas", expansion, len(found), pages)
            except Exception as error:
                errors.append(expansion)
                logging.exception("Error en %s: %s", expansion, error)
                print(f"  ERROR: {error}")
        browser.close()
    current_columns = HISTORY_COLUMNS[:10]
    current = (pd.DataFrame(rows).reindex(columns=current_columns).sort_values(["expansion", "market_price"], ascending=[True, False], na_position="last")
               if rows else pd.DataFrame(columns=current_columns))
    write_excel(current, OUTPUTS / "precios_actuales.xlsx", "Precios actuales")
    history_path = OUTPUTS / "historico_precios.parquet"
    variations = find_new_or_lower(rows, load_history(history_path))
    write_excel(variations, OUTPUTS / "variaciones_precios.xlsx", "Nuevas y bajas")
    sent_alerts = send_price_drop_alerts(variations, telegram_token, telegram_chat_id)
    # ponytail: successful alerts can repeat after a later delivery failure; add an outbox only if outages become common.
    append_history(rows, history_path)
    send_job_finished(variations, telegram_token, telegram_chat_id)
    print(f"Variaciones detectadas: {len(variations)} (nuevas o con baja de precio)")
    print(f"Alertas Telegram enviadas: {sent_alerts}")
    print(f"Finalizado: {len(expansions)} expansiones, {len(rows)} cartas, sin resultados: {len(empty)}, con error: {len(errors)}")
    if empty: print("Sin resultados:", ", ".join(empty))
    if errors: print("Con error:", ", ".join(errors))


if __name__ == "__main__":
    main()
