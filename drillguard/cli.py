"""CLI for demo, screen, dashboard, benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .detector import detect
from .ingestion import load_csv
from .report import build_report, write_html, write_json
from .schema import ALGORITHM_VERSION, ALLOWED_DATA_ORIGINS, schema_manifest
from .synthetic import SCENARIO_NAMES, make_scenario


def _validate_origin(origin: str) -> str:
    if origin not in ALLOWED_DATA_ORIGINS:
        raise SystemExit(
            f"Invalid --origin '{origin}'. Allowed: {sorted(ALLOWED_DATA_ORIGINS)}. "
            "field_validated is not accepted without an approved validation workflow."
        )
    return origin


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

    dash = sub.add_parser("dashboard")
    dash.add_argument("--csv", help="Input CSV path")
    dash.add_argument("--scenario", default="packoff", choices=SCENARIO_NAMES)
    dash.add_argument("--html", default="artifacts/dashboard.html")
    dash.add_argument("--origin", default="field_unvalidated")

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
        origin = _validate_origin(a.origin)
        df = load_csv(a.csv)
        out = detect(df)
        report = build_report(
            out,
            data_origin=origin,
            source_id=str(Path(a.csv).name),
            scenario=None,
        )
        write_json(report, a.output)
        write_html(report, a.html)
        print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
        return

    if a.cmd == "dashboard":
        from .dashboard import render_dashboard, run_from_csv

        origin = _validate_origin(a.origin)
        if a.csv:
            path = run_from_csv(a.csv, output_html=a.html, origin=origin)
        else:
            df, _ = make_scenario(a.scenario, seed=0)
            out = detect(df)
            path = render_dashboard(
                out,
                data_origin="synthetic",
                source_id=f"synthetic:{a.scenario}",
                output_html=a.html,
            )
        print(str(path))
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
