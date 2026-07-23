"""Data-quality reasons and gating flags."""

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
                reasons[i] = f"nan:{c}"
                quality_ok[i] = False
            elif not np.isfinite(v):
                reasons[i] = f"nonfinite:{c}"
                quality_ok[i] = False

    # Physical range / negativity for channels that must be non-negative
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
                reasons[i] = f"negative:{c}"
                quality_ok[i] = False
            elif v < lo or v > hi:
                reasons[i] = f"out_of_range:{c}"
                quality_ok[i] = False

    if "duplicate_timestamp" in out.columns:
        for i in np.where(out["duplicate_timestamp"].to_numpy())[0]:
            if quality_ok[i]:
                reasons[i] = "duplicate_timestamp"
                quality_ok[i] = False

    if "gap_flag" in out.columns:
        for i in np.where(out["gap_flag"].fillna(False).to_numpy())[0]:
            if reasons[i] == "ok":
                reasons[i] = "gap_in_timeline"
            # gaps do not automatically invalidate quality_ok for the sample itself

    if "channel_desync_suspect" in out.columns:
        for i in np.where(out["channel_desync_suspect"].fillna(False).to_numpy())[0]:
            if reasons[i] == "ok":
                reasons[i] = "channel_desync_suspect"

    # Stuck / flatline detector (pressure) over short window
    spp = out["standpipe_pressure_kpa"].to_numpy(dtype=float)
    stuck = np.zeros(n, dtype=bool)
    win = 15
    for i in range(win, n):
        seg = spp[i - win : i + 1]
        if np.all(np.isfinite(seg)) and float(np.nanstd(seg)) < 1e-6:
            stuck[i] = True
            if quality_ok[i] and reasons[i] == "ok":
                reasons[i] = "stale_channel:standpipe_pressure_kpa"
                quality_ok[i] = False

    # Regime conflict placeholder filled later if operation string conflicts with pumps
    out["quality_ok"] = quality_ok
    out["quality_reason"] = reasons
    out["stale_pressure"] = stuck
    return out
