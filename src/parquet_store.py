from pathlib import Path

import pandas as pd

from src.config import OUTPUT_COLUMNS, OUTPUT_PARQUET


def read_existing_parquet(path: Path = OUTPUT_PARQUET) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    return pd.read_parquet(path)


def _align_schema(df: pd.DataFrame) -> pd.DataFrame:
    aligned = df.copy()
    for col in OUTPUT_COLUMNS:
        if col not in aligned.columns:
            aligned[col] = None
    extra = [col for col in aligned.columns if col not in OUTPUT_COLUMNS]
    return aligned[OUTPUT_COLUMNS + extra]


def write_parquet(df: pd.DataFrame, path: Path = OUTPUT_PARQUET) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _align_schema(df).to_parquet(path, index=False)
    pd.read_parquet(path)


def append_to_parquet(df_new: pd.DataFrame, path: Path = OUTPUT_PARQUET) -> tuple[int, int]:
    existing = read_existing_parquet(path)
    before = len(existing)
    if existing.empty:
        combined = _align_schema(df_new)
    else:
        combined = pd.concat([_align_schema(existing), _align_schema(df_new)], ignore_index=True)
    combined = combined.drop_duplicates(ignore_index=True)
    write_parquet(combined, path)
    return len(combined) - before, len(combined)
