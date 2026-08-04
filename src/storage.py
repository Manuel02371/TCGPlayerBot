from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

HISTORY_COLUMNS = [
    "expansion", "expansion_code", "card_name", "card_number", "language",
    "seller_count", "price_from", "market_price", "catalog_url", "card_url",
    "execution_id", "extracted_at", "execution_date", "observation_key",
]
CARD_KEY = ["expansion", "card_name", "card_number", "language", "card_url"]
VARIATION_COLUMNS = [
    "expansion", "expansion_code", "card_name", "card_number", "language", "seller_count",
    "price_from", "market_price", "previous_market_price", "change_amount", "change_percent",
    "status", "previous_extracted_at", "prior_cuts_used",
    "price_cut_1", "price_cut_2", "price_cut_3", "price_cut_4", "price_cut_5",
    "card_url", "extracted_at",
]


def observation_key(row: dict) -> str:
    """Identifica una observación dentro de una ejecución concreta."""
    fields = ("expansion", "card_name", "card_number", "language", "card_url",
              "execution_id", "seller_count", "price_from", "market_price")
    value = "|".join(str(row.get(field, "")).strip() for field in fields)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def append_history(rows: list[dict], history_path: Path) -> pd.DataFrame:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    current = pd.DataFrame(rows)
    if current.empty:
        current = pd.DataFrame(columns=HISTORY_COLUMNS)
    else:
        current["observation_key"] = current.apply(lambda row: observation_key(row.to_dict()), axis=1)
    existing = pd.read_parquet(history_path) if history_path.exists() else pd.DataFrame(columns=HISTORY_COLUMNS)
    frames = [frame for frame in (existing, current) if not frame.empty]
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=HISTORY_COLUMNS)
    combined = combined.reindex(columns=HISTORY_COLUMNS)
    combined.to_parquet(history_path, index=False)
    return combined


def load_history(history_path: Path) -> pd.DataFrame:
    return pd.read_parquet(history_path) if history_path.exists() else pd.DataFrame(columns=HISTORY_COLUMNS)


def find_new_or_lower(current_rows: list[dict], history: pd.DataFrame, cuts: int = 5) -> pd.DataFrame:
    current = pd.DataFrame(current_rows)
    if current.empty:
        return pd.DataFrame(columns=VARIATION_COLUMNS)
    executions = history[["execution_id", "extracted_at"]].drop_duplicates().sort_values("extracted_at").tail(cuts)
    previous = history[history["execution_id"].isin(executions["execution_id"])].copy()
    results = []
    for row in current.to_dict("records"):
        matches = previous
        for field in CARD_KEY:
            matches = matches[matches[field] == row[field]]
        matches = matches.sort_values("extracted_at", ascending=False).drop_duplicates("execution_id")
        prices = matches["market_price"].head(cuts).tolist()
        item = {key: row.get(key) for key in VARIATION_COLUMNS}
        item.update({"previous_market_price": None, "change_amount": None, "change_percent": None,
                     "previous_extracted_at": None, "prior_cuts_used": len(prices)})
        item.update({f"price_cut_{index}": prices[index - 1] if len(prices) >= index else None for index in range(1, cuts + 1)})
        if not prices:
            item["status"] = "Nueva carta"
            results.append(item)
            continue
        last = matches.iloc[0]
        current_price, previous_price = row.get("market_price"), last["market_price"]
        if pd.notna(current_price) and pd.notna(previous_price) and current_price < previous_price:
            item.update({"status": "Bajo precio", "previous_market_price": previous_price,
                         "change_amount": current_price - previous_price,
                         "change_percent": (current_price - previous_price) / previous_price if previous_price else None,
                         "previous_extracted_at": last["extracted_at"]})
            results.append(item)
    return pd.DataFrame(results, columns=VARIATION_COLUMNS)
