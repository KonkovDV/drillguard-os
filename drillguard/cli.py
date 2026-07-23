"""CLI for demo, screen, benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .detector import detect
from .ingestion import load_csv
from .report import build_report, write_html, write_json
from .schema import ALGORITHM_VERSION, schema_manifest
from .synthetic import SCENARIO_NAMES, make_scenario


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        prog="drillguard",
        description="DrillGuard OS — local advisory screening (no control actions).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("demo")
    d.add_argument("--scenario", default="packoff", choices=SCENARIO_NAMES)
    d.add_argument("--seed", type=int, default=0)
    d.add_argument("--output", default="artifacts/demo_report.json")
    d.add_argument("--html", default="artifacts/demo_report.html")

    s = sub.add_parser("screen")
    s.add_argument("csv")
    s.add_argument("--output", default="artifacts/screen_report.json")
    s.add_argument("--html", default="artifacts/screen_report.html")
    s.add_argument("--origin", default="field_unvalidated")

    b = sub.add_parser("benchmark")
    b.add_argument("--output", default="artifacts/benchmark_results.json")
    b.add_argument("--full", action="store_true")

    sub.add_parser("schema")

    a = p.parse_args(argv)

    if a.cmd == "schema":
        print(json.dumps(schema_manifest(), ensure_ascii=False, indent=2))
        return

    if a.cmd == "demo":
        df, gt = make_scenario(a.scenario, seed=a.seed)
        out = detect(df)
        report = build_report(
            out,
            data_origin="synthetic",
            source_id=f"synthetic:{a.scenario}:seed={a.seed}",
            scenario=a.scenario,
        )
        report["ground_truth"] = gt
        write_json(report, a.output)
        write_html(report, a.html)
        print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
        return

    if a.cmd == "screen":
        df = load_csv(a.csv)
        out = detect(df)
        report = build_report(
            out,
            data_origin=a.origin,
            source_id=str(Path(a.csv).name),
            scenario=None,
        )
        write_json(report, a.output)
        write_html(report, a.html)
        print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
        return

    if a.cmd == "benchmark":
        import sys

        root = Path(__file__).resolve().parents[1]
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from benchmark.run_benchmark import run
        from benchmark.scenarios import FULL_SCENARIOS

        rep = run(output=a.output, scenarios=FULL_SCENARIOS if a.full else None)
        print(json.dumps({"version": ALGORITHM_VERSION, "aggregate": rep["aggregate"]}, indent=2))


if __name__ == "__main__":
    main()
