"""Input schema, units, ranges, and event taxonomy for DrillGuard OS v0.2."""

from __future__ import annotations

from enum import Enum
from typing import Any

ALGORITHM_VERSION = "0.2.2"

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

QUALITY_REASON_CODES = [
    "ok",
    "flagged_data_quality",
    "missing_value",
    "nonfinite_value",
    "negative_physical_value",
    "out_of_range",
    "duplicate_timestamp",
    "irregular_timebase",
    "gap_in_timeline",
    "flatline",
    "stale_channel",
    "unit_unknown",
    "insufficient_history",
    "regime_conflict",
    "channel_desynchronized",
]

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
    # Strict naming: not a well-control diagnosis without pit/flow-out.
    POSSIBLE_INFLUX_CANDIDATE = "possible_influx_candidate"
    TORQUE_DRAG_ANOMALY = "torque_drag_anomaly"
    SIGNAL_CONFLICT = "signal_conflict"


# Level A — complication candidates only (not informational)
COMPLICATION_CLASSES = frozenset(
    {
        EventClass.POSSIBLE_PACKOFF.value,
        EventClass.POSSIBLE_LOST_CIRCULATION.value,
        EventClass.POSSIBLE_INFLUX_CANDIDATE.value,
        EventClass.TORQUE_DRAG_ANOMALY.value,
    }
)

INFORMATIONAL_LEVEL_B = frozenset(
    {
        EventClass.SENSOR_QUALITY_ISSUE.value,
        EventClass.OPERATION_CHANGE.value,
        EventClass.SIGNAL_CONFLICT.value,
        EventClass.INSUFFICIENT_HISTORY.value,
        EventClass.NORMAL_NOISE.value,
        EventClass.SHORT_TRANSIENT.value,
        EventClass.NONE.value,
    }
)

# Backward-compatible alias rejected as primary label
DEPRECATED_EVENT_ALIASES = {"possible_influx": EventClass.POSSIBLE_INFLUX_CANDIDATE.value}

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
