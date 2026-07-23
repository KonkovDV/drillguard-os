"""Observed and physically-motivated features (not a full hydraulics model)."""

from __future__ import annotations

import pandas as pd

from .baseline import BaselineConfig, add_causal_baselines

FEATURE_CATALOG = {
    "standpipe_pressure_kpa_z": {
        "kind": "observed",
        "note": "Causal robust z of standpipe pressure vs regime baseline.",
    },
    "pump_flow_lpm_z": {
        "kind": "observed",
        "note": "Causal robust z of pump flow (flow-in).",
    },
    "pressure_per_flow": {
        "kind": "physically_motivated",
        "note": "SPP/Q proxy for hydraulic resistance; not ECD model.",
    },
    "pressure_per_flow_z": {
        "kind": "physically_motivated",
        "note": "Causal z of SPP/Q within regime.",
    },
    "torque_drag_index": {
        "kind": "physically_motivated",
        "note": "Empirical T&D screen; NOT the SPE open-source 4DOF T&D model.",
    },
    "delta_spp_kpa": {"kind": "observed", "note": "First difference of SPP."},
    "delta_flow_lpm": {"kind": "observed", "note": "First difference of flow-in."},
}


def add_features(df: pd.DataFrame, cfg: BaselineConfig | None = None) -> pd.DataFrame:
    cfg = cfg or BaselineConfig()
    out = add_causal_baselines(df, cfg=cfg)
    flow = out["pump_flow_lpm"].clip(lower=1.0)
    out["pressure_per_flow"] = out["standpipe_pressure_kpa"] / flow

    # Same regime-run keys + candidate freeze as primary channels (no future leakage).
    from .baseline import _regime_run_keys, causal_baseline_stats
    from .schema import NOISE_FLOOR

    regimes = _regime_run_keys(out["regime"].to_numpy())
    mask = (
        out["baseline_frozen"].to_numpy(dtype=bool)
        if cfg.freeze_on_candidate and "baseline_frozen" in out.columns
        else None
    )
    med, scale, z, hok = causal_baseline_stats(
        out["pressure_per_flow"].to_numpy(dtype=float),
        regimes,
        cfg=cfg,
        noise_floor=NOISE_FLOOR["standpipe_pressure_kpa"]
        / max(float(out["pump_flow_lpm"].median()), 1.0),
        candidate_mask=mask,
    )
    out["pressure_per_flow_baseline"] = med
    out["pressure_per_flow_z"] = z
    out["pressure_per_flow_history_ok"] = hok

    out["torque_drag_index"] = (
        out["torque_knm_z"].fillna(0)
        + 0.5 * out["hookload_kn_z"].fillna(0)
        - 0.25 * out["rate_of_penetration_m_h_z"].fillna(0)
    )
    out["delta_spp_kpa"] = out["standpipe_pressure_kpa"].diff().fillna(0.0)
    out["delta_flow_lpm"] = out["pump_flow_lpm"].diff().fillna(0.0)

    # Optional mud density channel if present
    if "mud_density_sg" in out.columns:
        dens = pd.to_numeric(out["mud_density_sg"], errors="coerce")
        out["mud_density_delta"] = dens.diff()

    out.attrs["feature_catalog"] = FEATURE_CATALOG
    out.attrs["physics_disclaimer"] = (
        "Features are observed or physically motivated screens. "
        "v0.2 does not implement multiphase hydraulics, rheology, ECD, or full T&D physics."
    )
    return out
