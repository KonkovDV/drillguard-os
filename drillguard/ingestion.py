"""CSV / frame ingestion with size limits and validation errors."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .schema import OPTIONAL_COLUMNS, REQUIRED_COLUMNS

MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_ROWS = 500_000
MAX_COLUMNS = 64


class IngestionError(ValueError):
    """Raised when input cannot be safely loaded or validated."""


def load_csv(path: str | Path, *, max_bytes: int = MAX_FILE_BYTES) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise IngestionError(f"File not found: {p}")
    size = p.stat().st_size
    if size > max_bytes:
        raise IngestionError(f"File exceeds size limit ({size} > {max_bytes} bytes)")
    if size == 0:
        raise IngestionError("Empty file")
    try:
        df = pd.read_csv(p)
    except Exception as exc:  # noqa: BLE001 — surface as ingestion error
        raise IngestionError(f"Failed to parse CSV: {exc}") from exc
    return validate_frame(df, source=str(p))


def validate_frame(df: pd.DataFrame, *, source: str = "<memory>") -> pd.DataFrame:
    if df is None or len(df) == 0:
        raise IngestionError("Empty signal frame")
    if df.shape[1] > MAX_COLUMNS:
        raise IngestionError(f"Too many columns: {df.shape[1]} > {MAX_COLUMNS}")
    if len(df) > MAX_ROWS:
        raise IngestionError(f"Too many rows: {len(df)} > {MAX_ROWS}")

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise IngestionError(
            f"Missing required columns: {missing}. "
            f"Required: {REQUIRED_COLUMNS}. Source={source}"
        )

    out = df.copy()
    for c in OPTIONAL_COLUMNS:
        if c not in out.columns:
            out[c] = pd.NA

    # Coerce numeric required channels
    for c in REQUIRED_COLUMNS[1:8]:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    out.attrs["source_id"] = source
    return out


def example_validation_error() -> dict[str, Any]:
    return {
        "error": "Missing required columns: ['pump_flow_lpm']",
        "required_columns": REQUIRED_COLUMNS,
        "hint": "See docs/DATA_DICTIONARY.md and artifacts/schema_example.csv",
    }
