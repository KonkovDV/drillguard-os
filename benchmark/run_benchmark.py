"""Reproducible synthetic benchmark runner (Level A/B/C metrics)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.metrics import aggregate_report, evaluate_case  # noqa: E402
from benchmark.scenarios import CORE_SCENARIOS, iter_cases  # noqa: E402
from drillguard.detector import detect  # noqa: E402
from drillguard.schema import ALGORITHM_VERSION  # noqa: E402


def _write_html(report: dict, path: Path) -> None:
    import html as h

    lim = h.escape(str(report.get("limitations_banner", "")))
    agg = report.get("aggregate", {})
    rows = []
    for c in report.get("cases", []):
        la = c.get("level_a", {})
        rows.append(
            "<tr>"
            f"<td>{h.escape(str(c.get('scenario')))}</td>"
            f"<td>{c.get('seed')}</td>"
            f"<td>{h.escape(str(c.get('truth_class')))}</td>"
            f"<td>{la.get('f1')}</td>"
            f"<td>{la.get('precision')}</td>"
            f"<td>{la.get('recall')}</td>"
            f"<td>{la.get('detection_delay_s')}</td>"
            f"<td>{c.get('level_c', {}).get('false_alarms_per_hour')}</td>"
            f"<td>{h.escape(str(c.get('level_c', {}).get('latest_event')))}</td>"
            "</tr>"
        )
    body = f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"/>
<title>DrillGuard benchmark (synthetic)</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:24px}}
.banner{{background:#fff3cd;border:1px solid #856404;padding:12px;margin-bottom:16px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{border:1px solid #ccc;padding:6px}} th{{background:#f4f4f4}}
</style></head><body>
<div class="banner"><strong>LIMITATIONS FIRST.</strong> {lim}</div>
<p>algorithm={h.escape(ALGORITHM_VERSION)} · claim_level=synthetic_only · requires_field_validation=true</p>
<p>Primary metrics are Level A F1/delay/FA — not appearance rates.</p>
<pre>{h.escape(json.dumps(agg, ensure_ascii=False, indent=2))}</pre>
<table><thead><tr>
<th>scenario</th><th>seed</th><th>truth</th><th>A_f1</th><th>A_prec</th><th>A_rec</th><th>delay_s</th><th>FA/h</th><th>latest</th>
</tr></thead><tbody>{''.join(rows)}</tbody></table>
</body></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def run(
    scenarios: list[str] | None = None,
    seeds: list[int] | None = None,
    output: str = "artifacts/benchmark_results.json",
) -> dict:
    scenarios = scenarios or CORE_SCENARIOS
    seeds = seeds or [0, 1, 2, 3, 4]
    cases = []
    for case in iter_cases(scenarios, seeds):
        out = detect(case["df"])
        m = evaluate_case(out, case["gt"])
        cases.append(m)

    aggregate = aggregate_report(cases)
    limitations = (
        "SYNTHETIC ONLY. Not field accuracy. heuristic_score is not a probability. "
        "Event appearance rate is demoted and must not be used as the headline KPI. "
        "possible_influx_candidate is not well-control diagnosis. "
        "Requires labeled archive + temporal holdout for any field claim."
    )
    # Hard gates — computed from case/aggregate fields (not only banner self-check).
    gates = {
        "normal_zero_complication_fa": bool(
            aggregate.get("normal_scenario_gate", {}).get("all_zero_complication_fa")
        ),
        "heuristic_score_not_probability": all(
            str(c.get("score_semantics", "")).endswith("not_probability")
            or "not_probability" in str(c.get("score_semantics", ""))
            for c in cases
        ),
        "synthetic_only": all(c.get("claim_level") == "synthetic_only" for c in cases)
        and all(c.get("requires_field_validation") is True for c in cases),
        "event_appearance_rate_is_not_primary": (
            "compat_appearance_rate_demoted" in aggregate
            and "compat" in str(aggregate.get("primary_metrics_note", "")).lower()
        ),
    }
    report = {
        "algorithm_version": ALGORITHM_VERSION,
        "limitations_banner": limitations,
        "claim_level": "synthetic_only",
        "requires_field_validation": True,
        "scenarios": scenarios,
        "seeds": seeds,
        "n_scenarios": len(scenarios),
        "n_seeds": len(seeds),
        "n_cases": len(cases),
        "cases": cases,
        "aggregate": aggregate,
        "gates": gates,
        "claims_manifest_path": "artifacts/CLAIMS_MANIFEST.json",
    }
    # Keep top-level n_cases explicit for auditors
    assert report["n_cases"] == len(scenarios) * len(seeds)
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_html(report, out_path.with_suffix(".html"))

    # Fail CI if normal gate broken
    if not gates["normal_zero_complication_fa"]:
        print(json.dumps({"error": "normal_scenario_gate_failed", "aggregate": aggregate}, indent=2))
        sys.exit(1)
    return report


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--output", default="artifacts/benchmark_results.json")
    p.add_argument("--full", action="store_true")
    args = p.parse_args()
    scenarios = None
    if args.full:
        from benchmark.scenarios import FULL_SCENARIOS

        scenarios = FULL_SCENARIOS
    rep = run(scenarios=scenarios, output=args.output)
    print(
        json.dumps(
            {
                "algorithm_version": ALGORITHM_VERSION,
                "aggregate_summary": {
                    k: rep["aggregate"][k]
                    for k in (
                        "n_cases",
                        "primary_metrics_note",
                        "normal_scenario_gate",
                        "operation_change_interval_hit_rate",
                        "short_transient_no_escalation_rate",
                        "compat_appearance_rate_demoted",
                    )
                    if k in rep["aggregate"]
                },
                "per_class_keys": list(rep["aggregate"].get("per_class", {}).keys()),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
