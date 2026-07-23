"""Benchmark metrics with Level A / B / C separation (synthetic evaluation only)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd

from drillguard.schema import COMPLICATION_CLASSES, EventClass
from drillguard.timebase import duration_hours

LEVEL_A = frozenset(COMPLICATION_CLASSES)
LEVEL_B = frozenset(
    {
        EventClass.SENSOR_QUALITY_ISSUE.value,
        EventClass.OPERATION_CHANGE.value,
        EventClass.SIGNAL_CONFLICT.value,
        EventClass.INSUFFICIENT_HISTORY.value,
        EventClass.NORMAL_NOISE.value,
        EventClass.SHORT_TRANSIENT.value,
    }
)


def _intervals(mask: np.ndarray) -> list[tuple[int, int]]:
    out = []
    start = None
    for i, flag in enumerate(list(mask) + [False]):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            out.append((start, i - 1))
            start = None
    return out


def _prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": 0,
    }


def detection_delay_s(out: pd.DataFrame, gt: dict[str, Any], cls: str | None = None) -> float | None:
    truth = cls or gt.get("event_class")
    a = gt.get("event_start_idx")
    if truth in {None, "none"} or a is None:
        return None
    hits = [i for i in out.index[out["event"] == truth].tolist() if i >= a]
    if not hits:
        return None
    i = hits[0]
    return float((out.loc[i, "timestamp"] - out.loc[a, "timestamp"]).total_seconds())


def time_to_clear_s(out: pd.DataFrame, gt: dict[str, Any]) -> float | None:
    truth = gt.get("event_class")
    b = gt.get("event_end_idx")
    if truth not in LEVEL_A or b is None:
        return None
    after = out.index[(out.index > b) & (out["event"] == truth)]
    if len(after) == 0:
        # cleared at/before end
        return 0.0
    # still active past GT end — time from GT end to last contiguous end after b
    return float((out.loc[after[-1], "timestamp"] - out.loc[b, "timestamp"]).total_seconds())


def false_alarm_complication_stats(out: pd.DataFrame, gt: dict[str, Any]) -> dict[str, Any]:
    """Level A false alarms only."""
    hours = max(duration_hours(out), 1e-9)
    a, b = gt.get("event_start_idx"), gt.get("event_end_idx")
    truth = gt.get("event_class")
    scenario = gt.get("scenario")
    # Ballooning-like confound: possible_influx_candidate is an expected Level-B outcome,
    # not a Level-A false alarm against "none".
    if truth == "ballooning_like" or scenario == "ballooning_like":
        fa_classes = LEVEL_A - {EventClass.POSSIBLE_INFLUX_CANDIDATE.value}
        fa = out["event"].isin(fa_classes).to_numpy()
    else:
        fa = out["event"].isin(LEVEL_A).to_numpy()
        if truth in LEVEL_A and a is not None and b is not None:
            in_win = (out.index.to_numpy() >= a) & (out.index.to_numpy() <= b)
            match = out["event"].to_numpy() == truth
            fa = fa & ~(in_win & match)
    # informational truths: any Level A is FA (except ballooning handling above)
    durations = []
    for s, e in _intervals(fa):
        d = (out.loc[e, "timestamp"] - out.loc[s, "timestamp"]).total_seconds()
        durations.append(max(float(d), 0.0))
    return {
        "false_alarm_rows": int(fa.sum()),
        "false_alarms_per_hour": float(fa.sum()) / hours,
        "false_alarms_per_hour_definition": "level_a_false_alarm_rows_per_hour",
        "false_alarm_events": len(durations),
        "mean_false_alarm_duration_s": float(np.mean(durations)) if durations else 0.0,
        "false_alarm_durations_s": durations,
    }


def evaluate_case(out: pd.DataFrame, gt: dict[str, Any]) -> dict[str, Any]:
    truth = gt.get("event_class", "none")
    # Normalize deprecated alias
    if truth == "possible_influx":
        truth = EventClass.POSSIBLE_INFLUX_CANDIDATE.value
    a, b = gt.get("event_start_idx"), gt.get("event_end_idx")
    hours = max(duration_hours(out), 1e-9)

    # --- Level A window metrics (only when truth is Level A or none) ---
    level_a: dict[str, Any]
    if truth in LEVEL_A and a is not None and b is not None:
        y_true = np.zeros(len(out), dtype=int)
        y_true[a : b + 1] = 1
        y_pred = (out["event"] == truth).to_numpy().astype(int)
        tp = int(((y_true == 1) & (y_pred == 1)).sum())
        fp = int(((y_true == 0) & (y_pred == 1)).sum())
        fn = int(((y_true == 1) & (y_pred == 0)).sum())
        tn = int(((y_true == 0) & (y_pred == 0)).sum())
        prf = _prf(tp, fp, fn)
        prf["tn"] = tn
        # other Level A classes inside window count as confusion (not credit)
        other_a = out["event"].isin(LEVEL_A - {truth}) & (out.index >= a) & (out.index <= b)
        level_a = {
            **prf,
            "class": truth,
            "event_detected_in_window": bool((out.loc[a:b, "event"] == truth).any()),
            "latest_is_truth": str(out.iloc[-1]["event"]) == truth,
            "detection_delay_s": detection_delay_s(out, gt, truth),
            "event_fragments": len(_intervals((out["event"] == truth).to_numpy())),
            "time_to_clear_s": time_to_clear_s(out, {**gt, "event_class": truth}),
            "other_level_a_in_window_rows": int(other_a.sum()),
        }
    elif truth in {None, "none"} or truth in {
        "normal",
        "high_noise",
        "flow_change",
        "mud_density_change",
        "desync",
        "missing_gaps",
    }:
        # Normal-like: any Level A prediction is FP. Fix TN via boolean invert (not ~ on ints).
        y_pred = out["event"].isin(LEVEL_A).to_numpy()
        fp = int(y_pred.sum())
        tn = int((~y_pred).sum())
        level_a = {
            **_prf(0, fp, 0),
            "tn": tn,
            "class": "none",
            "event_detected_in_window": False,
            "gate_no_complication": fp == 0,
            "latest_is_truth": str(out.iloc[-1]["event"]) not in LEVEL_A,
            "detection_delay_s": None,
            "event_fragments": 0,
            "time_to_clear_s": None,
        }
    elif truth == "ballooning_like" or gt.get("scenario") == "ballooning_like":
        # Confound scenario: Level A F1/FA against "none" is not the primary metric.
        other_a = out["event"].isin(LEVEL_A - {EventClass.POSSIBLE_INFLUX_CANDIDATE.value})
        level_a = {
            "class": "n/a_confound_scenario",
            "note": (
                "ballooning_like is a Level B confound; do not read Level A F1/FA as failure. "
                "Red-team gate: possible_influx_candidate allowed with well_control_overclaim=false."
            ),
            "f1": None,
            "precision": None,
            "recall": None,
            "tp": 0,
            "fp": int(other_a.sum()),
            "fn": 0,
            "tn": int((~other_a.to_numpy()).sum()),
            "event_detected_in_window": False,
            "latest_is_truth": True,
            "detection_delay_s": None,
            "event_fragments": 0,
            "time_to_clear_s": None,
            "influx_candidate_rows": int(
                (out["event"] == EventClass.POSSIBLE_INFLUX_CANDIDATE.value).sum()
            ),
        }
    else:
        level_a = {
            "class": "n/a_truth_not_level_a",
            "note": "Level A point-F1 not applied; see Level B",
            "f1": None,
            "precision": None,
            "recall": None,
        }

    # --- Level B informational ---
    level_b: dict[str, Any] = {"class": truth if truth in LEVEL_B else "n/a"}
    if truth == EventClass.OPERATION_CHANGE.value and a is not None and b is not None:
        detected = bool((out.loc[a:b, "event"] == truth).any())
        # Do NOT require latest row to remain operation_change
        level_b.update(
            {
                "detected_in_interval": detected,
                "latest_is_truth_required": False,
                "latest_event": str(out.iloc[-1]["event"]),
                "interval_hit": detected,
                "f1_point_legacy": None,  # intentionally not primary
                "detection_delay_s": detection_delay_s(out, gt, truth),
            }
        )
    elif truth == EventClass.SHORT_TRANSIENT.value and a is not None:
        detected = bool((out["event"] == truth).any())
        escalated = bool(out["event"].isin(LEVEL_A).any())
        level_b.update(
            {
                "detected": detected,
                "escalated_to_complication": escalated,
                "pass_no_escalation": not escalated,
                "detection_delay_s": detection_delay_s(out, gt, truth),
                "duration_labeled_s": float(
                    (
                        out.loc[min(b if b is not None else a, len(out) - 1), "timestamp"]
                        - out.loc[a, "timestamp"]
                    ).total_seconds()
                ),
            }
        )
    elif truth == EventClass.SENSOR_QUALITY_ISSUE.value and a is not None and b is not None:
        detected = bool((out.loc[a:b, "event"] == truth).any())
        escalated = bool(out["event"].isin(LEVEL_A).any())
        level_b.update(
            {
                "detected_in_interval": detected,
                "escalated_to_complication": escalated,
                "pass": detected and not escalated,
                "detection_delay_s": detection_delay_s(out, gt, truth),
            }
        )
    elif truth == EventClass.POSSIBLE_INFLUX_CANDIDATE.value or gt.get("scenario") == "ballooning_like":
        level_b["influx_candidate_warning"] = (
            "Without pit/flow-out this is not well-control diagnosis; ballooning may look similar."
        )

    fa = false_alarm_complication_stats(out, {**gt, "event_class": truth})

    # --- Level C stream health ---
    level_c = {
        "hours": hours,
        "rows": int(len(out)),
        "quality_ok_pct": round(float(out["quality_ok"].mean() * 100), 2),
        "warmup_rows": int((out["event"] == EventClass.INSUFFICIENT_HISTORY.value).sum()),
        "latest_event": str(out.iloc[-1]["event"]),
        "stable_terminal_not_required_for_operation_change": truth
        == EventClass.OPERATION_CHANGE.value,
        **fa,
    }

    return {
        "scenario": gt.get("scenario"),
        "seed": gt.get("seed"),
        "synthetic": True,
        "claim_level": "synthetic_only",
        "requires_field_validation": True,
        "score_semantics": out.attrs.get("score_semantics", "heuristic_score_not_probability"),
        "truth_class": truth,
        "level_a": level_a,
        "level_b": level_b,
        "level_c": level_c,
        # Compatibility fields (NOT primary marketing metrics)
        "compat_event_appeared": bool((out["event"] == truth).any())
        if truth not in {None, "none"}
        else not bool(out["event"].isin(LEVEL_A).any()),
        "compat_latest_match": str(out.iloc[-1]["event"]) == truth
        if truth not in {None, "none"}
        else str(out.iloc[-1]["event"]) not in LEVEL_A,
    }


def _pct(vals: list[float], q: float) -> float | None:
    if not vals:
        return None
    return float(np.percentile(vals, q))


def aggregate_report(cases: list[dict[str, Any]]) -> dict[str, Any]:
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in cases:
        by_class[str(c["truth_class"])].append(c)

    per_class = {}
    for cls, rows in by_class.items():
        f1s = [r["level_a"]["f1"] for r in rows if r["level_a"].get("f1") is not None]
        delays = [
            r["level_a"]["detection_delay_s"]
            for r in rows
            if r["level_a"].get("detection_delay_s") is not None
        ]
        fah = [r["level_c"]["false_alarms_per_hour"] for r in rows]
        appeared = [1.0 if r["compat_event_appeared"] else 0.0 for r in rows]
        latest = [1.0 if r["compat_latest_match"] else 0.0 for r in rows]
        per_class[cls] = {
            "n": len(rows),
            "f1": {
                "mean": float(np.mean(f1s)) if f1s else None,
                "min": float(np.min(f1s)) if f1s else None,
                "median": _pct(f1s, 50),
                "max": float(np.max(f1s)) if f1s else None,
                "p05": _pct(f1s, 5),
                "p95": _pct(f1s, 95),
            },
            "detection_delay_s": {
                "mean": float(np.mean(delays)) if delays else None,
                "min": float(np.min(delays)) if delays else None,
                "median": _pct(delays, 50),
                "max": float(np.max(delays)) if delays else None,
            },
            "false_alarms_per_hour": {
                "mean": float(np.mean(fah)) if fah else None,
                "min": float(np.min(fah)) if fah else None,
                "median": _pct(fah, 50),
                "max": float(np.max(fah)) if fah else None,
            },
            "rate_expected_class_appeared": float(np.mean(appeared)) if appeared else None,
            "rate_latest_equals_truth": float(np.mean(latest)) if latest else None,
            "note": (
                "rate_expected_class_appeared is NOT a primary quality metric; "
                "prefer Level A F1/delay/FA for complications and Level B interval hits for informational."
            ),
        }

    # Normal gate: scenarios whose intended truth is no Level-A complication
    normals = [c for c in cases if c.get("scenario") in {"normal", "high_noise"}]
    none_like = [c for c in cases if c["truth_class"] in {"none"}]
    normal_gate = {
        "n": len(normals),
        "all_zero_complication_fa": all(
            c["level_c"]["false_alarm_rows"] == 0 for c in (normals or none_like)
        )
        if (normals or none_like)
        else None,
        "per_seed": [
            {
                "scenario": c.get("scenario"),
                "seed": c["seed"],
                "false_alarm_rows": c["level_c"]["false_alarm_rows"],
                "false_alarms_per_hour": c["level_c"]["false_alarms_per_hour"],
                "latest_event": c["level_c"]["latest_event"],
            }
            for c in normals
        ],
    }

    op = [c for c in cases if c["truth_class"] == EventClass.OPERATION_CHANGE.value]
    short = [c for c in cases if c["truth_class"] == EventClass.SHORT_TRANSIENT.value]

    return {
        "n_cases": len(cases),
        "claim_level": "synthetic_only",
        "requires_field_validation": True,
        "primary_metrics_note": (
            "Do not advertise compat event-appearance rates as readiness. "
            "Primary: Level A F1/precision/recall/delay/FA/h; Level B interval logic; Level C stream FA."
        ),
        "per_class": per_class,
        "normal_scenario_gate": normal_gate,
        "operation_change_interval_hit_rate": float(
            np.mean([1.0 if c["level_b"].get("detected_in_interval") else 0.0 for c in op])
        )
        if op
        else None,
        "short_transient_no_escalation_rate": float(
            np.mean([1.0 if c["level_b"].get("pass_no_escalation") else 0.0 for c in short])
        )
        if short
        else None,
        "compat_appearance_rate_demoted": float(
            np.mean([1.0 if c["compat_event_appeared"] else 0.0 for c in cases])
        ),
    }
