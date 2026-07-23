"""Adversarial / robustness probes — hard gates exit non-zero on failure."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from drillguard.detector import detect  # noqa: E402
from drillguard.ingestion import IngestionError, load_csv  # noqa: E402
from drillguard.report import build_report, write_html  # noqa: E402
from drillguard.schema import ALGORITHM_VERSION, COMPLICATION_CLASSES  # noqa: E402
from drillguard.synthetic import make_scenario  # noqa: E402


def probe_baseline_prefix_equals_full() -> dict:
    df, _ = make_scenario("packoff", seed=0, n=200)
    cut = 120
    full = detect(df)
    pref = detect(df.iloc[:cut].copy())
    cols = ["standpipe_pressure_kpa_z", "pump_flow_lpm_z"]
    ok = True
    for c in cols:
        a = pref[c].to_numpy(dtype=float)
        b = full[c].iloc[:cut].to_numpy(dtype=float)
        # Allow nan equality in warmup
        if not np.allclose(np.nan_to_num(a, nan=0.0), np.nan_to_num(b, nan=0.0), atol=1e-6):
            ok = False
    return {"name": "baseline_prefix_equals_full", "pass": ok, "hard": True}


def probe_future_mutation() -> dict:
    df, _ = make_scenario("normal", seed=1, n=150)
    base = detect(df)
    mutated = df.copy()
    mutated.loc[140:, "standpipe_pressure_kpa"] += 5000
    mut = detect(mutated)
    cut = 100
    ok = np.allclose(
        np.nan_to_num(base["standpipe_pressure_kpa_z"].iloc[:cut], nan=0.0),
        np.nan_to_num(mut["standpipe_pressure_kpa_z"].iloc[:cut], nan=0.0),
        atol=1e-6,
    )
    return {"name": "future_mutation_no_past_change", "pass": bool(ok), "hard": True}


def probe_negative_physics() -> dict:
    df, _ = make_scenario("normal", seed=1)
    df.loc[100:110, "pump_flow_lpm"] = -50
    out = detect(df)
    bad = out.loc[100:110]
    return {
        "name": "negative_flow_quality_gate",
        "pass": (not bool(bad["quality_ok"].any())),
        "hard": True,
    }


def probe_normal_no_complications() -> dict:
    fa = []
    for seed in range(5):
        out = detect(make_scenario("normal", seed=seed)[0])
        fa.append(int(out["event"].isin(list(COMPLICATION_CLASSES)).sum()))
    return {
        "name": "normal_complication_rows",
        "per_seed": fa,
        "pass": max(fa) == 0,
        "hard": True,
    }


def probe_flatline_not_packoff() -> dict:
    out = detect(make_scenario("sensor_fault_flatline", seed=0)[0])
    return {
        "name": "flatline_not_packoff",
        "pass": "possible_packoff" not in set(out["event"])
        and "sensor_quality_issue" in set(out["event"]),
        "hard": True,
    }


def probe_short_transient_no_escalation() -> dict:
    out = detect(make_scenario("short_transient_only", seed=0)[0])
    return {
        "name": "short_transient_no_level_a",
        "pass": not bool(out["event"].isin(list(COMPLICATION_CLASSES)).any()),
        "hard": True,
    }


def probe_ballooning_not_confirmed_kick() -> dict:
    out = detect(make_scenario("ballooning_like", seed=0)[0])
    events = set(out["event"])
    # Forbidden: legacy diagnosis name or any implication of confirmed kick
    forbidden = {"possible_influx", "confirmed_influx", "kick", "manifestation"}
    overclaim = bool(events & forbidden)
    # Candidate class may fire; must stay low score and carry warning unknowns
    if "possible_influx_candidate" in events:
        sub = out[out["event"] == "possible_influx_candidate"]
        overclaim = overclaim or bool((sub["heuristic_score"] > 0.55).any())
        has_warn = bool(
            sub["unknowns"]
            .astype(str)
            .str.contains("pit|ballooning|well-control|не является", case=False)
            .any()
        )
        if not has_warn:
            overclaim = True
    return {
        "name": "ballooning_like_not_confirmed_manifestation",
        "latest": str(out.iloc[-1]["event"]),
        "well_control_overclaim": overclaim,
        "pass": not overclaim,
        "hard": True,
        "note": (
            "Hard gate: ballooning_like must not produce confirmed manifestation / legacy "
            "possible_influx. possible_influx_candidate may appear with low score + warning."
        ),
    }


def probe_score_semantics() -> dict:
    out = detect(make_scenario("packoff", seed=0)[0])
    return {
        "name": "score_not_probability",
        "pass": "confidence" not in out.columns
        and "heuristic_score" in out.columns
        and out.attrs.get("score_semantics") == "heuristic_score_not_probability",
        "hard": True,
    }


def probe_report_has_version_source() -> dict:
    out = detect(make_scenario("normal", seed=0)[0])
    rep = build_report(out, data_origin="synthetic", source_id="probe")
    return {
        "name": "report_version_source",
        "pass": rep.get("algorithm_version") == ALGORITHM_VERSION and rep.get("source_id") == "probe",
        "hard": True,
    }


def probe_html_escape(tmp: Path) -> dict:
    out = detect(make_scenario("normal", seed=0)[0])
    rep = build_report(out, data_origin='synthetic<script>', source_id='x<y>')
    html = write_html(rep, tmp / "xss.html").read_text(encoding="utf-8")
    return {
        "name": "html_escapes_dynamic",
        "pass": "synthetic&lt;script&gt;" in html and "x&lt;y&gt;" in html and "<script>" not in html,
        "hard": True,
    }


def probe_empty_csv(tmp: Path) -> dict:
    p = tmp / "empty.csv"
    p.write_text("", encoding="utf-8")
    try:
        load_csv(p)
        ok = False
    except IngestionError:
        ok = True
    return {"name": "empty_csv_ingestion_error", "pass": ok, "hard": True}


def probe_no_network_side_effect_marker() -> dict:
    # Static assurance: API health declares network_side_effects False when importable
    try:
        from drillguard.api import create_app

        app = create_app()
        # call health via dependency-free check on description + route presence
        routes = [r.path for r in app.routes]
        ok = (
            "/health" in routes
            and "No SCADA" in app.description
            and "control" in app.description.lower()
        )
    except Exception as exc:
        ok = False
        return {
            "name": "api_declares_no_control_or_optional",
            "pass": ok,
            "hard": False,
            "note": f"API optional / unavailable: {type(exc).__name__}",
        }
    return {"name": "api_declares_no_control_or_optional", "pass": ok, "hard": False}


def main(output: str = "artifacts/redteam_results.json") -> dict:
    tmp = Path("artifacts/_redteam_tmp")
    tmp.mkdir(parents=True, exist_ok=True)
    probes = [
        probe_baseline_prefix_equals_full(),
        probe_future_mutation(),
        probe_negative_physics(),
        probe_normal_no_complications(),
        probe_flatline_not_packoff(),
        probe_short_transient_no_escalation(),
        probe_ballooning_not_confirmed_kick(),
        probe_score_semantics(),
        probe_report_has_version_source(),
        probe_html_escape(tmp),
        probe_empty_csv(tmp),
        probe_no_network_side_effect_marker(),
    ]
    hard = [p for p in probes if p.get("hard")]
    hard_pass = all(p["pass"] for p in hard)
    report = {
        "algorithm_version": ALGORITHM_VERSION,
        "claim_level": "synthetic_adversarial_probes",
        "scope": "local synthetic/robustness gates — not a full OT red-team",
        "n_probes": len(probes),
        "n_hard_gates": len(hard),
        "probes": probes,
        "all_hard_gates_pass": hard_pass,
        "well_control_overclaim": any(
            p.get("well_control_overclaim") for p in probes if "well_control_overclaim" in p
        ),
    }
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not hard_pass:
        sys.exit(1)
    return report


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--output", default="artifacts/redteam_results.json")
    args = p.parse_args()
    main(args.output)
