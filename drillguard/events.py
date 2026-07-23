"""Aggregate contiguous detections into structured event cards."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .schema import ALGORITHM_VERSION, COMPLICATION_CLASSES, EventClass


def build_event_cards(
    out: pd.DataFrame,
    *,
    data_origin: str = "synthetic",
    source_id: str | None = None,
) -> list[dict[str, Any]]:
    source_id = source_id or out.attrs.get("source_id", "<memory>")
    cards: list[dict[str, Any]] = []
    if len(out) == 0:
        return cards

    # Group contiguous same-event runs for complication + key informational classes
    track = COMPLICATION_CLASSES | {
        EventClass.SENSOR_QUALITY_ISSUE.value,
        EventClass.OPERATION_CHANGE.value,
        EventClass.SHORT_TRANSIENT.value,
    }
    current = None
    start = 0
    for i, ev in enumerate(out["event"].tolist() + [None]):
        if ev != current:
            if current in track and current is not None:
                cards.append(_card(out, start, i - 1, current, data_origin, source_id))
            current = ev
            start = i
    return cards


def _card(
    out: pd.DataFrame,
    i0: int,
    i1: int,
    event: str,
    data_origin: str,
    source_id: str,
) -> dict[str, Any]:
    seg = out.iloc[i0 : i1 + 1]
    first = seg.iloc[0]
    last = seg.iloc[-1]
    confirm = seg[seg["detector_phase"].astype(str).str.upper() == "CONFIRMED"]
    confirm_time = (
        str(confirm.iloc[0]["timestamp"]) if len(confirm) else str(first["timestamp"])
    )
    duration_s = max(
        (last["timestamp"] - first["timestamp"]).total_seconds(),
        float(first.get("median_dt_s", 1.0)),
    )
    max_score = float(seg["heuristic_score"].max())
    # Overclaim only if an influx-like card is polished into a high-confidence diagnosis.
    well_control_overclaim = (
        event == EventClass.POSSIBLE_INFLUX_CANDIDATE.value and max_score > 0.55
    )
    return {
        "event_class": event,
        "display_label": str(last.get("display_label", event)),
        "well_control_overclaim": well_control_overclaim,
        "start_time": str(first["timestamp"]),
        "confirm_time": confirm_time,
        "end_time": str(last["timestamp"]),
        "duration_s": round(duration_s, 3),
        "depth_m": float(first["depth_m"]),
        "regime": str(first["regime"]),
        "heuristic_score": max_score,
        "score_semantics": "heuristic_rule_weight_not_calibrated_probability",
        "data_quality_ok_pct": round(float(seg["quality_ok"].mean() * 100), 2),
        "contributing_features": str(seg["contributing_features"].iloc[-1]),
        "baseline_interval": {
            "window_points": int(first.get("baseline_window", 0)),
            "min_history": int(first.get("baseline_min_history", 0)),
            "history_ok": bool(first.get("baseline_history_ok", False)),
            "note": "Causal past-only baseline within regime; frozen while candidate active.",
        },
        "observed_deviation": {
            "standpipe_pressure_kpa_z": _f(first.get("standpipe_pressure_kpa_z")),
            "pump_flow_lpm_z": _f(first.get("pump_flow_lpm_z")),
            "torque_drag_index": _f(first.get("torque_drag_index")),
            "pressure_per_flow_z": _f(first.get("pressure_per_flow_z")),
        },
        "unknowns": str(last["unknowns"]),
        "recommended_check": str(last["recommended_action"]),
        "prominent_warning": (
            "Кандидат сформирован по доступному сочетанию сигналов. "
            "Без pit volume, flow-out и экспертной проверки это не является диагностикой проявления."
            if event == EventClass.POSSIBLE_INFLUX_CANDIDATE.value
            else None
        ),
        "data_origin": data_origin,
        "algorithm_version": ALGORITHM_VERSION,
        "source_id": source_id,
        "advisory_only": True,
        "no_control_actions": True,
    }


def _f(v: Any) -> float | None:
    try:
        x = float(v)
        if x != x:  # noqa: PLR0124
            return None
        return round(x, 4)
    except (TypeError, ValueError):
        return None


def summarize(out: pd.DataFrame) -> dict[str, Any]:
    last = out.iloc[-1]
    counts = out["event"].value_counts().to_dict()
    return {
        "latest_event": str(last["event"]),
        "latest_heuristic_score": float(last["heuristic_score"]),
        "latest_action": str(last["recommended_action"]),
        "rows": int(len(out)),
        "quality_ok_pct": round(float(out["quality_ok"].mean() * 100), 2),
        "event_counts": {str(k): int(v) for k, v in counts.items()},
        "algorithm_version": ALGORITHM_VERSION,
        "score_semantics": "heuristic_score_not_probability",
    }
