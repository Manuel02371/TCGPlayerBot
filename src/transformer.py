from datetime import datetime

import pandas as pd

from src.config import OUTPUT_COLUMNS


def build_item_key(df: pd.DataFrame) -> pd.Series:
    def part(col: str) -> pd.Series:
        if col in df.columns:
            values = df[col]
        else:
            values = pd.Series([""] * len(df), index=df.index)
        return values.fillna("").astype(str).str.strip()

    primary = part("expansion") + "|" + part("rareza") + "|" + part("nombre_carta") + "|" + part("numero_carta")
    fallback = "input|" + part("set_slug") + "|" + part("set_name") + "|" + part("rareza_buscada")
    return primary.where(primary.ne("|||"), fallback)


def normalize_result(record: dict) -> dict:
    normalized = {column: record.get(column) for column in OUTPUT_COLUMNS}
    if normalized.get("estado_scraping") in (None, ""):
        normalized["estado_scraping"] = "OK"
    if normalized.get("mensaje_error") is None:
        normalized["mensaje_error"] = ""
    return normalized


def add_execution_metadata(
    df: pd.DataFrame,
    timestamp: datetime | None = None,
    source_input: str = "",
) -> pd.DataFrame:
    timestamp = timestamp or datetime.now()
    records = [normalize_result(row) for row in df.to_dict(orient="records")]
    output = pd.DataFrame(records, columns=OUTPUT_COLUMNS)

    output["fecha_ejecucion"] = timestamp.strftime("%Y-%m-%d")
    output["hora_ejecucion"] = timestamp.strftime("%H:%M:%S")
    output["timestamp_ejecucion"] = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    output["fuente_input"] = source_input
    output["item_key"] = build_item_key(output)

    for col in output.columns:
        if output[col].dtype == object:
            output[col] = output[col].map(lambda value: value.strip() if isinstance(value, str) else value)

    output["market_price_usd"] = pd.to_numeric(output["market_price_usd"], errors="coerce")
    output["precio_referencia"] = pd.to_numeric(output["precio_referencia"], errors="coerce")
    return output
