"""Reproducible synthetic benchmark runner."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.metrics import aggregate_metrics, binary_detection  # noqa: E402
from benchmark.scenarios import CORE_SCENARIOS, iter_cases  # noqa: E402
from drillguard.detector import detect  # noqa: E402
from drillguard.report import write_html, write_json  # noqa: E402
from drillguard.schema import ALGORITHM_VERSION  # noqa: E402


def run(
    scenarios: list[str] | None = None,
    seeds: list[int] | None = None,
    output: str = "artifacts/benchmark_results.json",
) -> dict:
    scenarios = scenarios or CORE_SCENARIOS
    seeds = seeds or [0, 1, 2, 3, 4]
    rows = []
    normal_fa = []
    for case in iter_cases(scenarios, seeds):
        out = detect(case["df"])
        m = binary_detection(out, case["gt"])
        m.update({"scenario": case["name"], "seed": case["seed"], "synthetic": True})
        rows.append(m)
        if case["name"] == "normal":
            normal_fa.append(
                {
                    "seed": case["seed"],
                    "false_alarm_rows": m["false_alarm_rows"],
                    "false_alarms_per_hour": m["false_alarms_per_hour"],
                    "event_counts": out["event"].value_counts().to_dict(),
                    "latest_event": m["latest_event"],
                }
            )

    report = {
        "algorithm_version": ALGORITHM_VERSION,
        "claim_level": "synthetic_only",
        "requires_field_validation": True,
        "scenarios": scenarios,
        "seeds": seeds,
        "cases": rows,
        "aggregate": aggregate_metrics(rows),
        "normal_scenario_false_alarms": normal_fa,
        "gates": {
            "causal_baseline": True,
            "heuristic_score_not_probability": True,
            "no_control_side_effects": True,
            "synthetic_only": True,
        },
    }
    out_path = Path(output)
    write_json(report, out_path)
    html_path = out_path.with_suffix(".html")
    write_html(
        {
            "algorithm_version": ALGORITHM_VERSION,
            "data_origin": "synthetic",
            "source_id": "benchmark",
            "advisory_banner": "Synthetic benchmark only. Not field accuracy.",
            "score_semantics": "n/a",
            "summary": report["aggregate"],
            "event_cards": [
                {
                    "start_time": f"seed={r['seed']}",
                    "event_class": r["scenario"],
                    "heuristic_score": r["f1"],
                    "regime": r["truth_class"],
                    "recommended_check": f"hit={r['event_hit']} delay={r['detection_delay_s']}",
                    "unknowns": f"FA/h={r['false_alarms_per_hour']}",
                }
                for r in rows
            ],
        },
        html_path,
    )
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
    print(json.dumps({"aggregate": rep["aggregate"], "normal_fa": rep["normal_scenario_false_alarms"]}, indent=2))
