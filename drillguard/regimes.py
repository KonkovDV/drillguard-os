"""Operation regime classification with adaptation windows."""

from __future__ import annotations

import pandas as pd

REGIME_LABELS = ("drilling", "circulation", "tripping", "connection", "other")


def classify_operation(op: str) -> str:
    s = str(op).lower()
    if any(x in s for x in ("drill", "rotate", "бур", "ротац")):
        return "drilling"
    if any(x in s for x in ("circul", "pump", "цирк")):
        return "circulation"
    if any(x in s for x in ("trip", "pull", "run", "спуск", "подъем", "подъём")):
        return "tripping"
    if any(x in s for x in ("connect", "connection", "наращ")):
        return "connection"
    return "other"


def add_regimes(df: pd.DataFrame, adaptation_points: int = 20) -> pd.DataFrame:
    out = df.copy()
    out["regime"] = out["operation"].map(classify_operation)
    prev = out["regime"].shift(1)
    # First row is NOT a regime change (no prior state) — fixes false operation_change@t0
    out["regime_change"] = prev.notna() & out["regime"].ne(prev)

    # Per-regime age / adaptation: points since regime start
    ages = []
    age = 0
    last = None
    for r in out["regime"]:
        if r != last:
            age = 0
            last = r
        else:
            age += 1
        ages.append(age)
    out["regime_age"] = ages
    out["regime_adapting"] = out["regime_age"] < adaptation_points

    # Conflict: connection/tripping but pumps still high, etc.
    conflict = []
    for _, row in out.iterrows():
        c = False
        if row["regime"] == "connection" and float(row["pump_flow_lpm"]) > 50:
            c = True
        if row["regime"] == "drilling" and float(row["pump_rpm"]) < 1 and float(row["pump_flow_lpm"]) < 1:
            c = True
        conflict.append(c)
    out["regime_conflict"] = conflict
    return out
