"""Benchmark scenario catalog wrapping synthetic ground truth."""

from __future__ import annotations

from typing import Any

from drillguard.synthetic import SCENARIO_NAMES, make_scenario

# Core evaluation set for CI (fast)
CORE_SCENARIOS = [
    "normal",
    "packoff",
    "lost_circulation",
    "influx",
    "torque",
    "connection",
    "sensor_fault_flatline",
    "short_transient_only",
    "high_noise",
]

# Full red-team / stress set
FULL_SCENARIOS = list(SCENARIO_NAMES)


def iter_cases(
    scenarios: list[str] | None = None,
    seeds: list[int] | None = None,
) -> list[dict[str, Any]]:
    scenarios = scenarios or CORE_SCENARIOS
    seeds = seeds or [0, 1, 2, 3, 4]
    cases = []
    for seed in seeds:
        for name in scenarios:
            df, gt = make_scenario(name, seed=seed)
            cases.append({"df": df, "gt": gt, "name": name, "seed": seed})
    return cases
