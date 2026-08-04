from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote
from urllib.robotparser import RobotFileParser

from playwright.sync_api import Browser

CARD_SELECTOR = "a[href^='/card/']"
NEXT_SELECTOR = "button:has(i[class*='mdi-chevron-right'])"
PAGE_CHANGE_RETRY_DELAYS_MS = (2_000, 5_000, 10_000)
MONEY_RE = re.compile(r"S/\s*([0-9][0-9,]*(?:\.\d+)?)")
NUMBER_RE = re.compile(r"(?:N[úu]mero|Number)\s*[:#]?\s*([A-Za-z0-9-]+(?:/[A-Za-z0-9-]+)?)|\b(\d{1,4}/\d{1,4})\b", re.I)


@dataclass(frozen=True)
class ScraperConfig:
    timeout_ms: int
    retries: int
    diagnostics_dir: Path


def catalog_url(expansion: str) -> str:
    return f"https://masterset.pe/catalog?expansion={quote(expansion, safe='')}&language=en"


def assert_catalog_allowed() -> None:
    robots = RobotFileParser("https://masterset.pe/robots.txt")
    robots.read()
    if not robots.can_fetch("MasterSetCatalogBot", "https://masterset.pe/catalog"):
        raise RuntimeError("robots.txt no permite consultar el catálogo público.")


def money(value: str) -> float | None:
    return float(value.replace(",", "")) if value else None


def card_from_anchor(anchor: dict, expansion: str, page_url: str) -> dict:
    text = " ".join(anchor["text"].split())
    prices = MONEY_RE.findall(text)
    code_match = re.search(r"\b([A-Za-z0-9]{2,8})\s*[\u00b7]", text)
    number_match = NUMBER_RE.search(text)
    number = next((part for part in number_match.groups() if part), "") if number_match else ""
    lines = [line.strip() for line in anchor["text"].splitlines() if line.strip()]
    name = anchor.get("alt") or (lines[1] if len(lines) > 1 else lines[0] if lines else "")
    seller_match = re.search(r"\b(\d+)\s+desde\b", text, re.I)
    return {
        "expansion": expansion, "expansion_code": code_match.group(1).upper() if code_match else "",
        "card_name": name, "card_number": number, "language": "English",
        "seller_count": int(seller_match.group(1)) if seller_match else 0,
        "price_from": money(prices[0]) if prices else None,
        "market_price": money(prices[1]) if len(prices) > 1 else None,
        "catalog_url": page_url, "card_url": f"https://masterset.pe{anchor['href']}",
    }


def wait_for_catalog_change(page, before: tuple[str, ...], timeout_ms: int, retry_click) -> None:
    for delay_ms in (0, *PAGE_CHANGE_RETRY_DELAYS_MS):
        if delay_ms:
            print(f"  La página aún no cambió; reintentando en {delay_ms // 1_000} s...")
            page.wait_for_timeout(delay_ms)
            retry_click()
        try:
            page.wait_for_function(
                "([selector, before]) => { const now = [...document.querySelectorAll(selector)].map(a => a.getAttribute('href')); return now.length > 0 && now.join('|') !== before.join('|'); }",
                arg=[CARD_SELECTOR, list(before)], timeout=timeout_ms,
            )
            return
        except Exception:
            if delay_ms == PAGE_CHANGE_RETRY_DELAYS_MS[-1]:
                raise


class CatalogScraper:
    def __init__(self, browser: Browser, config: ScraperConfig) -> None:
        self.browser, self.config = browser, config

    def scrape_expansion(self, expansion: str) -> tuple[list[dict], int]:
        page_url = catalog_url(expansion)
        for attempt in range(1, self.config.retries + 1):
            catalog = self.browser.new_page()
            try:
                catalog.goto(page_url, wait_until="domcontentloaded", timeout=self.config.timeout_ms)
                catalog.wait_for_function(
                    "() => document.querySelectorAll(\"a[href^='/card/']\").length > 0 || document.body.innerText.includes('No hay resultados')",
                    timeout=self.config.timeout_ms,
                )
                rows, seen, page_number = [], set(), 1
                while True:
                    catalog.wait_for_timeout(500)
                    anchors = catalog.locator(CARD_SELECTOR).evaluate_all("els => els.map(a => ({href: a.getAttribute('href'), text: a.innerText, alt: a.querySelector('img')?.alt || ''}))")
                    fresh = [card_from_anchor(anchor, expansion, page_url) for anchor in anchors if anchor["href"] not in seen]
                    seen.update(anchor["href"] for anchor in anchors)
                    rows.extend(fresh)
                    print(f"  Página {page_number}: {len(fresh)} cartas; total {len(rows)}")
                    next_button = catalog.locator(NEXT_SELECTOR).last
                    if next_button.count() == 0 or next_button.is_disabled():
                        return rows, page_number
                    before = tuple(anchor["href"] for anchor in anchors)
                    next_button.click()
                    wait_for_catalog_change(catalog, before, self.config.timeout_ms, next_button.click)
                    page_number += 1
            except Exception:
                if attempt == self.config.retries:
                    self._diagnostic(catalog, expansion)
                    raise
                time.sleep(attempt)
            finally:
                catalog.close()
        return [], 0

    def _diagnostic(self, page, expansion: str) -> None:
        safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", expansion).strip("_") or "expansion"
        self.config.diagnostics_dir.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=self.config.diagnostics_dir / f"{safe_name}.png", full_page=True)
        (self.config.diagnostics_dir / f"{safe_name}.html").write_text(page.content(), encoding="utf-8")
