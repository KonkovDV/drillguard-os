"""Benchmark scenario catalog."""

from __future__ import annotations

from typing import Any

from drillguard.synthetic import SCENARIO_NAMES, make_scenario

CORE_SCENARIOS = [
    "normal",
    "packoff",
    "lost_circulation",
    "influx_like",
    "ballooning_like",
    "torque",
    "connection",
    "sensor_fault_flatline",
    "short_transient_only",
    "high_noise",
]

FULL_SCENARIOS = list(SCENARIO_NAMES)


def iter_cases(
    scenarios: list[str] | None = None,
    seeds: list[int] | None = None,
    intensities: list[float] | None = None,
) -> list[dict[str, Any]]:
    scenarios = scenarios or CORE_SCENARIOS
    seeds = seeds or [0, 1, 2, 3, 4]
    intensities = intensities or [1.0]
    cases = []
    for seed in seeds:
        for name in scenarios:
            for intensity in intensities:
                df, gt = make_scenario(name, seed=seed, intensity=intensity)
                cases.append(
                    {
                        "df": df,
                        "gt": gt,
                        "name": name,
                        "seed": seed,
                        "intensity": intensity,
                    }
                )
    return cases
