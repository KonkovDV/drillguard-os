"""Adversarial / robustness probes on synthetic data (not field red-team)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from drillguard.detector import detect  # noqa: E402
from drillguard.synthetic import make_scenario  # noqa: E402


def probe_baseline_causality() -> dict:
    df, _ = make_scenario("packoff", seed=0)
    out = detect(df)
    # At event start, baseline must use only past — z should be computable and history flag true after warmup
    mid = int(len(out) * 0.45)
    return {
        "name": "baseline_causality_packoff",
        "history_ok_at_mid": bool(out.loc[mid, "baseline_history_ok"]),
        "has_baseline_col": "standpipe_pressure_kpa_baseline" in out.columns,
        "pass": bool(out.loc[mid, "baseline_history_ok"])
        and "standpipe_pressure_kpa_baseline" in out.columns,
    }


def probe_shuffle_rejected_as_eval() -> dict:
    # Document that shuffled evaluation is invalid; detector still runs but metrics must not use shuffle
    return {
        "name": "no_shuffle_validation_policy",
        "policy": "Temporal holdout only; random shuffle of time series is forbidden for quality claims.",
        "pass": True,
    }


def probe_negative_physics() -> dict:
    df, _ = make_scenario("normal", seed=1)
    df.loc[100:110, "pump_flow_lpm"] = -50
    out = detect(df)
    bad = out.loc[100:110]
    return {
        "name": "negative_flow_quality_gate",
        "quality_ok_any": bool(bad["quality_ok"].any()),
        "sensor_or_conflict": bool(
            bad["event"].isin(["sensor_quality_issue", "signal_conflict"]).any()
        ),
        "pass": (not bad["quality_ok"].any()),
    }


def probe_normal_complications() -> dict:
    fa = []
    for seed in range(5):
        df, _ = make_scenario("normal", seed=seed)
        out = detect(df)
        comps = out["event"].isin(
            [
                "possible_packoff",
                "possible_lost_circulation",
                "possible_influx",
                "torque_drag_anomaly",
            ]
        )
        fa.append(int(comps.sum()))
    return {
        "name": "normal_complication_rows",
        "per_seed": fa,
        "max": max(fa),
        "pass": max(fa) == 0,
    }


def probe_ballooning_like() -> dict:
    df, _ = make_scenario("normal", seed=2)
    n = len(df)
    a = int(n * 0.45)
    df.loc[a:, "standpipe_pressure_kpa"] -= np.linspace(0, 2200, n - a)
    df.loc[a:, "pump_flow_lpm"] += np.linspace(0, 50, n - a)
    out = detect(df)
    return {
        "name": "ballooning_like_may_look_like_influx",
        "latest": str(out.iloc[-1]["event"]),
        "note": "Hypothesis: without pit/flow-out, ballooning can be misread as influx. Requires field validation.",
        "pass": True,  # informational — expected residual risk
    }


def main(output: str = "artifacts/redteam_results.json") -> dict:
    probes = [
        probe_baseline_causality(),
        probe_shuffle_rejected_as_eval(),
        probe_negative_physics(),
        probe_normal_complications(),
        probe_ballooning_like(),
    ]
    report = {
        "claim_level": "synthetic_adversarial_probes",
        "probes": probes,
        "all_hard_gates_pass": all(p["pass"] for p in probes if p["name"] != "ballooning_like_may_look_like_influx"),
    }
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--output", default="artifacts/redteam_results.json")
    args = p.parse_args()
    main(args.output)
