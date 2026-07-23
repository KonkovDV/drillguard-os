"""Event-level and stream-level benchmark metrics (synthetic evaluation only)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from drillguard.schema import COMPLICATION_CLASSES
from drillguard.timebase import duration_hours


def _event_intervals(events: pd.Series, target: str) -> list[tuple[int, int]]:
    intervals = []
    start = None
    for i, e in enumerate(events.tolist() + [None]):
        if e == target and start is None:
            start = i
        elif e != target and start is not None:
            intervals.append((start, i - 1))
            start = None
    return intervals


def detection_delay_s(out: pd.DataFrame, gt: dict[str, Any]) -> float | None:
    cls = gt.get("event_class")
    a = gt.get("event_start_idx")
    if cls in {None, "none"} or a is None:
        return None
    if cls not in COMPLICATION_CLASSES and cls != "sensor_quality_issue":
        # For operation_change / short_transient measure first match after start
        pass
    hits = out.index[out["event"] == cls].tolist()
    hits = [i for i in hits if i >= a]
    if not hits:
        return None
    i = hits[0]
    return float((out.loc[i, "timestamp"] - out.loc[a, "timestamp"]).total_seconds())


def false_alarm_stats(out: pd.DataFrame, gt: dict[str, Any]) -> dict[str, float]:
    """False complication alarms outside ground-truth window (or anywhere if none)."""
    a = gt.get("event_start_idx")
    b = gt.get("event_end_idx")
    truth = gt.get("event_class")
    hours = duration_hours(out)
    fa_mask = out["event"].isin(list(COMPLICATION_CLASSES))
    if truth in COMPLICATION_CLASSES and a is not None and b is not None:
        in_win = (out.index >= a) & (out.index <= b)
        # Allow matching class inside window; other complications or outside = FA
        fa_mask = fa_mask & (~(in_win & (out["event"] == truth)))
    elif truth == "none" or truth in {"short_transient", "operation_change", "sensor_quality_issue"}:
        # For non-complication truths, any complication is FA
        if truth == "sensor_quality_issue":
            fa_mask = out["event"].isin(list(COMPLICATION_CLASSES))
        elif truth in {"short_transient", "operation_change"}:
            fa_mask = out["event"].isin(list(COMPLICATION_CLASSES))
        else:
            fa_mask = out["event"].isin(list(COMPLICATION_CLASSES))

    fa_rows = int(fa_mask.sum())
    # Duration of FA runs
    durations = []
    start = None
    for i, flag in enumerate(fa_mask.tolist() + [False]):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            d = (out.loc[i - 1, "timestamp"] - out.loc[start, "timestamp"]).total_seconds()
            durations.append(max(d, 0.0))
            start = None
    return {
        "false_alarm_rows": fa_rows,
        "false_alarms_per_hour": fa_rows / hours if hours > 0 else float(fa_rows),
        "false_alarm_events": float(len(durations)),
        "mean_false_alarm_duration_s": float(np.mean(durations)) if durations else 0.0,
    }


def binary_detection(out: pd.DataFrame, gt: dict[str, Any]) -> dict[str, Any]:
    truth = gt.get("event_class", "none")
    detected_set = set(out["event"].tolist())
    latest = str(out.iloc[-1]["event"])

    # Point-level confusion vs truth window for complication classes
    y_true = np.zeros(len(out), dtype=int)
    y_pred = (out["event"] == truth).to_numpy().astype(int)
    a, b = gt.get("event_start_idx"), gt.get("event_end_idx")
    if truth not in {None, "none"} and a is not None and b is not None:
        y_true[a : b + 1] = 1
    elif truth == "none":
        y_true[:] = 0
        y_pred = out["event"].isin(list(COMPLICATION_CLASSES)).to_numpy().astype(int)

    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else (1.0 if truth in {None, "none"} and fp == 0 else 0.0)
    if truth in {None, "none"}:
        # For normal: success if no complication predictions
        prec = 1.0 if fp == 0 else 0.0
        rec = 1.0 if fp == 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0

    # Event-level hit: any detection of expected class after start
    if truth in {None, "none"}:
        event_hit = fp == 0
    else:
        event_hit = truth in detected_set

    delay = detection_delay_s(out, gt)
    fa = false_alarm_stats(out, gt)
    fragments = len(_event_intervals(out["event"], truth)) if truth not in {None, "none"} else 0

    return {
        "truth_class": truth,
        "latest_event": latest,
        "event_hit": bool(event_hit),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "detection_delay_s": delay,
        "event_fragments": fragments,
        **fa,
    }


def aggregate_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def collect(key: str) -> list[float]:
        vals = [r[key] for r in rows if r.get(key) is not None]
        return [float(v) for v in vals]

    def pct(vals: list[float], q: float) -> float | None:
        if not vals:
            return None
        return float(np.percentile(vals, q))

    f1s = collect("f1")
    delays = collect("detection_delay_s")
    fah = collect("false_alarms_per_hour")
    hits = [1.0 if r.get("event_hit") else 0.0 for r in rows]

    return {
        "n_cases": len(rows),
        "event_hit_rate": float(np.mean(hits)) if hits else 0.0,
        "f1": {
            "mean": float(np.mean(f1s)) if f1s else None,
            "p05": pct(f1s, 5),
            "median": pct(f1s, 50),
            "p95": pct(f1s, 95),
            "worst": float(np.min(f1s)) if f1s else None,
        },
        "detection_delay_s": {
            "mean": float(np.mean(delays)) if delays else None,
            "p05": pct(delays, 5),
            "median": pct(delays, 50),
            "p95": pct(delays, 95),
            "worst": float(np.max(delays)) if delays else None,
        },
        "false_alarms_per_hour": {
            "mean": float(np.mean(fah)) if fah else None,
            "p05": pct(fah, 5),
            "median": pct(fah, 50),
            "p95": pct(fah, 95),
            "worst": float(np.max(fah)) if fah else None,
        },
        "claim_level": "synthetic_only",
        "requires_field_validation": True,
    }
