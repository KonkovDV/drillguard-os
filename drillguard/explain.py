"""Explanation helpers for contributing features."""

from __future__ import annotations

from typing import Any

from .features import FEATURE_CATALOG


def explain_row(contributing: str, event: str) -> dict[str, Any]:
    parts = [p for p in contributing.split(";") if p]
    kinds = []
    for p in parts:
        key = p.split("=")[0].replace("spp_z", "standpipe_pressure_kpa_z").replace(
            "flow_z", "pump_flow_lpm_z"
        ).replace("spp_q_z", "pressure_per_flow_z")
        meta = FEATURE_CATALOG.get(key, {"kind": "empirical_rule", "note": p})
        kinds.append({"feature": key, "raw": p, **meta})
    return {
        "event": event,
        "contributors": kinds,
        "disclaimer": (
            "Explanation lists heuristic contributors only. "
            "Not a causal multiphase proof of the subsurface event."
        ),
    }
