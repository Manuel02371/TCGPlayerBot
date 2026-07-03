import re
import unicodedata
from pathlib import Path

import pandas as pd

from src.config import DEFAULT_INPUT_ROWS, INPUT_COLUMNS, INPUT_FILE, REQUIRED_INPUT_COLUMNS


ACTIVE_VALUES = {"1", "s", "si", "sí", "true", "yes", "x"}


def normalize_column_name(value: object) -> str:
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized.columns = [normalize_column_name(col) for col in normalized.columns]
    return normalized


def validate_input_columns(df: pd.DataFrame) -> None:
    missing = [col for col in REQUIRED_INPUT_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas obligatorias en el Excel: {', '.join(missing)}")


def create_input_template(path: Path = INPUT_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(DEFAULT_INPUT_ROWS, columns=INPUT_COLUMNS).to_excel(path, index=False)


def _clean_strings(df: pd.DataFrame) -> pd.DataFrame:
    clean = df.copy()
    for col in clean.columns:
        clean[col] = clean[col].map(
            lambda value: "" if pd.isna(value) else value.strip() if isinstance(value, str) else value
        )
    return clean


def _filter_active_rows(df: pd.DataFrame) -> pd.DataFrame:
    if "activo" not in df.columns:
        return df

    active = df["activo"].fillna("").astype(str).str.strip().str.lower()
    return df[active.isin(ACTIVE_VALUES)]


def load_input_excel(path: Path = INPUT_FILE) -> pd.DataFrame:
    if not path.exists():
        create_input_template(path)

    df_raw = pd.read_excel(path, dtype=object)
    df = _clean_strings(normalize_columns(df_raw))
    validate_input_columns(df)

    rows_read = len(df)
    if rows_read == 0:
        raise ValueError(f"El Excel de entrada no tiene filas: {path}")

    df = _filter_active_rows(df).copy()
    for col in REQUIRED_INPUT_COLUMNS:
        empty = df[col].fillna("").astype(str).str.strip().eq("")
        if empty.any():
            raise ValueError(f"Hay filas activas sin valor en la columna obligatoria: {col}")

    df.attrs["rows_read"] = rows_read
    df.attrs["rows_active"] = len(df)
    return df.reset_index(drop=True)
