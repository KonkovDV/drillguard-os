"""Data-quality reasons and gating flags (machine-readable codes)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .schema import COLUMN_RANGES, GOOD_QUALITY_TOKENS, NUMERIC_REQUIRED


def add_quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    n = len(out)
    reasons: list[str] = ["ok"] * n
    quality_ok = np.ones(n, dtype=bool)

    dq = out["data_quality"].astype(str).str.lower()
    flagged = ~dq.isin(GOOD_QUALITY_TOKENS)
    for i in np.where(flagged.to_numpy())[0]:
        reasons[i] = "flagged_data_quality"
        quality_ok[i] = False

    for c in NUMERIC_REQUIRED:
        arr = out[c].to_numpy(dtype=float)
        for i, v in enumerate(arr):
            if not quality_ok[i]:
                continue
            if np.isnan(v):
                reasons[i] = "missing_value"
                quality_ok[i] = False
            elif not np.isfinite(v):
                reasons[i] = "nonfinite_value"
                quality_ok[i] = False

    nonneg = [
        "depth_m",
        "standpipe_pressure_kpa",
        "pump_flow_lpm",
        "hookload_kn",
        "torque_knm",
        "pump_rpm",
    ]
    for c in nonneg:
        lo, hi = COLUMN_RANGES[c]
        arr = out[c].to_numpy(dtype=float)
        for i, v in enumerate(arr):
            if not quality_ok[i] or not np.isfinite(v):
                continue
            if v < 0:
                reasons[i] = "negative_physical_value"
                quality_ok[i] = False
            elif v < lo or v > hi:
                reasons[i] = "out_of_range"
                quality_ok[i] = False

    if "duplicate_timestamp" in out.columns:
        for i in np.where(out["duplicate_timestamp"].to_numpy())[0]:
            if quality_ok[i]:
                reasons[i] = "duplicate_timestamp"
                quality_ok[i] = False

    if "gap_flag" in out.columns:
        for i in np.where(out["gap_flag"].fillna(False).to_numpy())[0]:
            if quality_ok[i]:
                reasons[i] = "gap_in_timeline"
                quality_ok[i] = False

    if "irregular_dt" in out.columns:
        for i in np.where(out["irregular_dt"].fillna(False).to_numpy())[0]:
            if quality_ok[i]:
                reasons[i] = "irregular_timebase"
                quality_ok[i] = False

    if "channel_desync_suspect" in out.columns:
        for i in np.where(out["channel_desync_suspect"].fillna(False).to_numpy())[0]:
            if quality_ok[i]:
                reasons[i] = "channel_desynchronized"
                quality_ok[i] = False

    spp = out["standpipe_pressure_kpa"].to_numpy(dtype=float)
    stuck = np.zeros(n, dtype=bool)
    win = 15
    for i in range(win, n):
        seg = spp[i - win : i + 1]
        if np.all(np.isfinite(seg)) and float(np.nanstd(seg)) < 1e-6:
            stuck[i] = True
            if quality_ok[i] and reasons[i] == "ok":
                reasons[i] = "stale_channel"
                quality_ok[i] = False

    out["quality_ok"] = quality_ok
    out["quality_reason"] = reasons
    out["stale_pressure"] = stuck
    return out


def quality_report(df: pd.DataFrame) -> dict:
    if "quality_reason" not in df.columns:
        df = add_quality_flags(df)
    vc = df["quality_reason"].value_counts().to_dict()
    return {
        "rows": int(len(df)),
        "quality_ok_pct": round(float(df["quality_ok"].mean() * 100), 2),
        "reason_counts": {str(k): int(v) for k, v in vc.items()},
    }
