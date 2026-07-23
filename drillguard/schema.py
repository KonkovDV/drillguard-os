"""Input schema, units, ranges, and event taxonomy for DrillGuard OS v0.2."""

from __future__ import annotations

from enum import Enum
from typing import Any

ALGORITHM_VERSION = "0.2.0"

REQUIRED_COLUMNS = [
    "timestamp",
    "depth_m",
    "standpipe_pressure_kpa",
    "pump_flow_lpm",
    "hookload_kn",
    "torque_knm",
    "rate_of_penetration_m_h",
    "pump_rpm",
    "operation",
    "data_quality",
]

OPTIONAL_COLUMNS = [
    "mud_density_sg",
    "plastic_viscosity_cp",
    "flow_out_lpm",
    "pit_volume_m3",
    "bit_depth_m",
]

# Physical envelopes used for quality gating (not SIL limits).
COLUMN_UNITS: dict[str, str] = {
    "timestamp": "ISO-8601 / pandas datetime",
    "depth_m": "m",
    "standpipe_pressure_kpa": "kPa",
    "pump_flow_lpm": "L/min",
    "hookload_kn": "kN",
    "torque_knm": "kN·m",
    "rate_of_penetration_m_h": "m/h",
    "pump_rpm": "rpm",
    "operation": "categorical string",
    "data_quality": "ok|good|1|true|bad|...",
    "mud_density_sg": "specific gravity",
    "plastic_viscosity_cp": "cP",
    "flow_out_lpm": "L/min",
    "pit_volume_m3": "m³",
    "bit_depth_m": "m",
}

COLUMN_RANGES: dict[str, tuple[float, float]] = {
    "depth_m": (0.0, 15_000.0),
    "standpipe_pressure_kpa": (0.0, 80_000.0),
    "pump_flow_lpm": (0.0, 5_000.0),
    "hookload_kn": (0.0, 5_000.0),
    "torque_knm": (0.0, 100.0),
    "rate_of_penetration_m_h": (-50.0, 200.0),
    "pump_rpm": (0.0, 400.0),
    "mud_density_sg": (0.8, 2.5),
    "plastic_viscosity_cp": (1.0, 120.0),
    "flow_out_lpm": (0.0, 5_000.0),
    "pit_volume_m3": (0.0, 500.0),
    "bit_depth_m": (0.0, 15_000.0),
}

# Minimum absolute scale for MAD (prevents hypersensitive z on low-noise synthetics).
NOISE_FLOOR: dict[str, float] = {
    "standpipe_pressure_kpa": 50.0,
    "pump_flow_lpm": 8.0,
    "hookload_kn": 1.0,
    "torque_knm": 0.4,
    "rate_of_penetration_m_h": 0.5,
}

NUMERIC_REQUIRED = REQUIRED_COLUMNS[1:8]
GOOD_QUALITY_TOKENS = frozenset({"ok", "good", "1", "true", "yes"})


class EventClass(str, Enum):
    NONE = "none"
    INSUFFICIENT_HISTORY = "insufficient_history"
    NORMAL_NOISE = "normal_noise"
    SHORT_TRANSIENT = "short_transient"
    OPERATION_CHANGE = "operation_change"
    SENSOR_QUALITY_ISSUE = "sensor_quality_issue"
    POSSIBLE_PACKOFF = "possible_packoff"
    POSSIBLE_LOST_CIRCULATION = "possible_lost_circulation"
    POSSIBLE_INFLUX = "possible_influx"
    TORQUE_DRAG_ANOMALY = "torque_drag_anomaly"
    SIGNAL_CONFLICT = "signal_conflict"


COMPLICATION_CLASSES = frozenset(
    {
        EventClass.POSSIBLE_PACKOFF.value,
        EventClass.POSSIBLE_LOST_CIRCULATION.value,
        EventClass.POSSIBLE_INFLUX.value,
        EventClass.TORQUE_DRAG_ANOMALY.value,
        EventClass.SIGNAL_CONFLICT.value,
    }
)

INFORMATIONAL_CLASSES = frozenset(
    {
        EventClass.OPERATION_CHANGE.value,
        EventClass.SENSOR_QUALITY_ISSUE.value,
        EventClass.SHORT_TRANSIENT.value,
        EventClass.NORMAL_NOISE.value,
        EventClass.INSUFFICIENT_HISTORY.value,
        EventClass.NONE.value,
    }
)

FEATURE_KIND = {
    "observed": "Direct sensor channel or simple transform of observed channels.",
    "physically_motivated": "Derived from hydraulic/mechanical intuition, not a full physics model.",
    "empirical_rule": "Transparent threshold / persistence heuristic.",
    "future_physics": "Reserved for multiphase / T&D / rheology models — not implemented in v0.2.",
}


def schema_manifest() -> dict[str, Any]:
    return {
        "algorithm_version": ALGORITHM_VERSION,
        "required_columns": REQUIRED_COLUMNS,
        "optional_columns": OPTIONAL_COLUMNS,
        "units": COLUMN_UNITS,
        "ranges": {k: {"min": v[0], "max": v[1]} for k, v in COLUMN_RANGES.items()},
        "noise_floor": NOISE_FLOOR,
        "event_classes": [e.value for e in EventClass],
        "score_semantics": (
            "heuristic_score is an expert rule weight in [0,1], NOT a calibrated probability. "
            "Field calibration requires labeled archive and temporal holdout."
        ),
        "feature_kinds": FEATURE_KIND,
        "claims_boundary": "synthetic_or_requires_field_validation",
    }
