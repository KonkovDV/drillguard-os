"""Temporal integrity: parse, sort, duplicates, sampling rate, gaps."""

from __future__ import annotations

import numpy as np
import pandas as pd


def prepare_timebase(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    ts = pd.to_datetime(out["timestamp"], errors="coerce", utc=False)
    if ts.isna().any():
        bad = int(ts.isna().sum())
        raise ValueError(f"timestamp contains {bad} unparseable value(s)")

    out["timestamp"] = ts
    out = out.sort_values("timestamp", kind="mergesort").reset_index(drop=True)

    dup_mask = out["timestamp"].duplicated(keep=False)
    out["duplicate_timestamp"] = dup_mask
    # Keep first of duplicates for analysis continuity; flag all dups.
    keep = ~out["timestamp"].duplicated(keep="first")
    analysis = out.loc[keep].copy().reset_index(drop=True)

    dt = analysis["timestamp"].diff().dt.total_seconds()
    analysis["dt_s"] = dt
    positive = dt[dt > 0]
    if len(positive) == 0:
        median_dt = 1.0
    else:
        median_dt = float(positive.median())
    analysis["sampling_hz_est"] = 1.0 / max(median_dt, 1e-6)
    analysis["median_dt_s"] = median_dt
    # Gap if dt > 3x median (after first row)
    analysis["gap_flag"] = (dt > 3.0 * median_dt) & dt.notna()
    analysis["irregular_dt"] = (
        (dt < 0.25 * median_dt) | (dt > 2.0 * median_dt)
    ) & dt.notna()

    # Channel sync proxy: large simultaneous jumps across channels (heuristic)
    analysis["channel_desync_suspect"] = False
    if len(analysis) > 2:
        p = analysis["standpipe_pressure_kpa"].diff().abs()
        f = analysis["pump_flow_lpm"].diff().abs()
        # Extreme opposite moves without shared timing context
        analysis["channel_desync_suspect"] = (
            (p > p.median() * 20 + 500) & (f < f.median() * 2 + 5) & analysis["gap_flag"]
        )

    analysis.attrs.update(out.attrs)
    analysis.attrs["dropped_duplicate_rows"] = int((~keep).sum())
    analysis.attrs["median_dt_s"] = median_dt
    return analysis


def duration_hours(df: pd.DataFrame) -> float:
    if len(df) < 2:
        return 0.0
    sec = (df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]).total_seconds()
    return max(sec / 3600.0, 1e-9)


def elapsed_seconds(df: pd.DataFrame) -> np.ndarray:
    t0 = df["timestamp"].iloc[0]
    return (df["timestamp"] - t0).dt.total_seconds().to_numpy(dtype=float)
