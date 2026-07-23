"""Causal rolling baseline — past-only; freeze after warmup; no adapt on candidates."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .schema import NOISE_FLOOR


@dataclass
class BaselineConfig:
    window: int = 60
    min_history: int = 25
    freeze_on_candidate: bool = True
    candidate_z: float = 3.5
    # After warmup, freeze baseline; tiny EMA only for |z| < quiet_z AND not candidate
    slow_adapt_alpha: float = 0.01
    quiet_z: float = 2.0


def _mad(x: np.ndarray) -> float:
    med = float(np.median(x))
    return float(np.median(np.abs(x - med)))


def _regime_run_keys(regimes: np.ndarray) -> np.ndarray:
    run_keys: list[str] = []
    rid = 0
    prev = None
    for r in regimes:
        rs = str(r)
        if prev is not None and rs != prev:
            rid += 1
        prev = rs
        run_keys.append(f"{rs}#{rid}")
    return np.asarray(run_keys, dtype=object)


def causal_baseline_stats(
    values: np.ndarray,
    regimes: np.ndarray,
    *,
    cfg: BaselineConfig,
    noise_floor: float,
    candidate_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Past-only same-regime baseline.

    After warmup, (med, scale) are frozen. Micro-EMA is allowed only when
    |z| < quiet_z AND the row is not marked candidate (if freeze_on_candidate).
    """
    n = len(values)
    medians = np.full(n, np.nan)
    scales = np.full(n, np.nan)
    zs = np.full(n, np.nan)
    history_ok = np.zeros(n, dtype=bool)

    buffers: dict[str, list[float]] = {}
    frozen: dict[str, tuple[float, float]] = {}

    for i in range(n):
        reg = str(regimes[i])
        buf = buffers.setdefault(reg, [])
        v = float(values[i])
        is_cand = bool(candidate_mask[i]) if candidate_mask is not None else False

        if reg in frozen:
            med, scale = frozen[reg]
            history_ok[i] = True
            medians[i] = med
            scales[i] = scale
            zs[i] = (v - med) / scale if np.isfinite(v) else np.nan

            allow_adapt = (
                cfg.slow_adapt_alpha > 0
                and np.isfinite(v)
                and np.isfinite(zs[i])
                and abs(float(zs[i])) < cfg.quiet_z
            )
            if cfg.freeze_on_candidate and is_cand:
                allow_adapt = False
            if allow_adapt:
                med2 = (1 - cfg.slow_adapt_alpha) * med + cfg.slow_adapt_alpha * v
                frozen[reg] = (med2, scale)
            continue

        if len(buf) >= cfg.min_history:
            arr = np.asarray(buf[-cfg.window :], dtype=float)
            med = float(np.median(arr))
            scale = max(1.4826 * _mad(arr), noise_floor)
            frozen[reg] = (med, scale)
            history_ok[i] = True
            medians[i] = med
            scales[i] = scale
            zs[i] = (v - med) / scale if np.isfinite(v) else np.nan
            continue

        history_ok[i] = False
        if np.isfinite(v):
            buf.append(v)
            if len(buf) > cfg.window:
                del buf[0 : len(buf) - cfg.window]

    return medians, scales, zs, history_ok


def add_causal_baselines(df: pd.DataFrame, cfg: BaselineConfig | None = None) -> pd.DataFrame:
    cfg = cfg or BaselineConfig()
    out = df.copy()
    regimes = _regime_run_keys(out["regime"].to_numpy())
    channels = [
        "standpipe_pressure_kpa",
        "pump_flow_lpm",
        "hookload_kn",
        "torque_knm",
        "rate_of_penetration_m_h",
    ]

    # Pass 1: establish z without cross-channel candidate freeze
    prelim_z: dict[str, np.ndarray] = {}
    for c in channels:
        _, _, z, _ = causal_baseline_stats(
            out[c].to_numpy(dtype=float),
            regimes,
            cfg=cfg,
            noise_floor=NOISE_FLOOR[c],
            candidate_mask=None,
        )
        prelim_z[c] = z

    candidate = (
        (np.abs(prelim_z["standpipe_pressure_kpa"]) > cfg.candidate_z)
        | (np.abs(prelim_z["pump_flow_lpm"]) > cfg.candidate_z)
        | (np.abs(prelim_z["torque_knm"]) > cfg.candidate_z)
    )
    candidate = np.nan_to_num(candidate.astype(float), nan=0.0).astype(bool)
    mask = candidate if cfg.freeze_on_candidate else None

    # Pass 2: recompute with candidate_mask so quiet EMA cannot absorb events
    for c in channels:
        med, scale, z, hok = causal_baseline_stats(
            out[c].to_numpy(dtype=float),
            regimes,
            cfg=cfg,
            noise_floor=NOISE_FLOOR[c],
            candidate_mask=mask,
        )
        out[f"{c}_baseline"] = med
        out[f"{c}_scale"] = scale
        out[f"{c}_z"] = z
        out[f"{c}_history_ok"] = hok

    out["baseline_history_ok"] = (
        out["standpipe_pressure_kpa_history_ok"] & out["pump_flow_lpm_history_ok"]
    )
    out["baseline_frozen"] = candidate
    out["baseline_candidate_mask_applied"] = bool(cfg.freeze_on_candidate)
    out["baseline_window"] = cfg.window
    out["baseline_min_history"] = cfg.min_history
    return out
