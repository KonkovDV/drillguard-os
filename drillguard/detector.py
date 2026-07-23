"""Event proposal rules and row-level screening (heuristic, not ML)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .baseline import BaselineConfig
from .features import add_features
from .ingestion import validate_frame
from .persistence import PersistenceConfig, PersistenceState, step_persistence
from .quality import add_quality_flags
from .regimes import add_regimes
from .schema import ALGORITHM_VERSION, COMPLICATION_CLASSES, EventClass
from .timebase import prepare_timebase

# Public FSM labels (mapped from internal persistence phases)
PHASE_MAP = {
    "idle": "IDLE",
    "candidate": "CANDIDATE",
    "confirmed": "CONFIRMED",
    "clearing": "CONFIRMED",
    "cooldown": "COOLDOWN",
    "transient": "TRANSIENT",
    "informational": "IDLE",
}


@dataclass
class DetectorConfig:
    baseline: BaselineConfig | None = None
    persistence: PersistenceConfig | None = None
    z_enter: float = 4.5
    z_exit: float = 3.0
    td_enter: float = 4.5
    adaptation_points: int = 20


def _has_pit_or_flow_out(row: pd.Series) -> bool:
    for c in ("pit_volume_m3", "flow_out_lpm"):
        if c in row.index and pd.notna(row.get(c)):
            try:
                if np.isfinite(float(row.get(c))):
                    return True
            except (TypeError, ValueError):
                continue
    return False


def _propose(row: pd.Series, cfg: DetectorConfig) -> tuple[str | None, float, list[str]]:
    """Return (proposed_label_or_None, heuristic_score / rule_score, contributors)."""
    if not bool(row.get("quality_ok", True)):
        return EventClass.SENSOR_QUALITY_ISSUE.value, 0.55, ["quality_ok=False"]

    if bool(row.get("regime_conflict", False)):
        return EventClass.SIGNAL_CONFLICT.value, 0.45, ["regime_conflict"]

    if bool(row.get("regime_change", False)):
        return EventClass.OPERATION_CHANGE.value, 0.40, ["regime_change"]

    if bool(row.get("regime_adapting", False)) or not bool(row.get("baseline_history_ok", False)):
        return EventClass.INSUFFICIENT_HISTORY.value, 0.20, ["insufficient_baseline_history"]

    pz = float(row.get("standpipe_pressure_kpa_z", np.nan))
    fz = float(row.get("pump_flow_lpm_z", np.nan))
    pfz = float(row.get("pressure_per_flow_z", np.nan))
    td = float(row.get("torque_drag_index", np.nan))
    if not np.isfinite(pz) or not np.isfinite(fz):
        return EventClass.INSUFFICIENT_HISTORY.value, 0.20, ["nonfinite_z"]

    if pz < -cfg.z_enter and fz < -cfg.z_enter * 0.6:
        return (
            EventClass.POSSIBLE_LOST_CIRCULATION.value,
            0.72,
            [f"spp_z={pz:.2f}", f"flow_z={fz:.2f}"],
        )
    if pz > cfg.z_enter and (
        fz > cfg.z_enter * 0.35
        or pfz > cfg.z_enter * 0.45
        or abs(float(row.get("delta_spp_kpa", 0))) > 150
    ):
        return (
            EventClass.POSSIBLE_PACKOFF.value,
            0.80,
            [f"spp_z={pz:.2f}", f"flow_z={fz:.2f}", f"spp_q_z={pfz:.2f}"],
        )
    if pz < -cfg.z_enter and fz > cfg.z_enter * 0.7:
        # Strict: without pit/flow-out this is ONLY an influx-like candidate
        score = 0.48 if _has_pit_or_flow_out(row) else 0.35
        return (
            EventClass.POSSIBLE_INFLUX_CANDIDATE.value,
            score,
            [f"spp_z={pz:.2f}", f"flow_z={fz:.2f}", "missing_pit_flow_out_unless_present"],
        )
    if np.isfinite(td) and td > cfg.td_enter:
        return EventClass.TORQUE_DRAG_ANOMALY.value, 0.74, [f"torque_drag_index={td:.2f}"]

    if abs(pz) > cfg.z_exit or abs(fz) > cfg.z_exit:
        return None, 0.15, [f"soft_deviation spp_z={pz:.2f} flow_z={fz:.2f}"]

    return None, 0.05, []


DISPLAY_LABELS = {
    EventClass.POSSIBLE_INFLUX_CANDIDATE.value: (
        "Кандидат на поведение, похожее на проявление"
    ),
    EventClass.POSSIBLE_PACKOFF.value: (
        "Кандидат на ухудшение очистки ствола / ограничение циркуляции"
    ),
    EventClass.POSSIBLE_LOST_CIRCULATION.value: (
        "Кандидат на поглощение (по доступным сигналам)"
    ),
    EventClass.TORQUE_DRAG_ANOMALY.value: (
        "Упрощённый индекс аномалии момента и нагрузки"
    ),
}

ACTIONS = {
    EventClass.POSSIBLE_PACKOFF.value: (
        "Кандидат на ухудшение очистки ствола или ограничение циркуляции. "
        "Проверить циркуляцию и шлам (только проверка; без автоматических команд)."
    ),
    EventClass.POSSIBLE_LOST_CIRCULATION.value: (
        "Кандидат на поглощение по доступному сочетанию давления и расхода. "
        "Проверить по производственному регламенту; объём поглощения не оценивается."
    ),
    EventClass.POSSIBLE_INFLUX_CANDIDATE.value: (
        "Кандидат на поведение, похожее на проявление (не диагностика). "
        "Сформирован по доступному сочетанию сигналов. Без pit volume, flow-out и экспертной "
        "проверки это НЕ является диагностикой проявления / well-control."
    ),
    EventClass.TORQUE_DRAG_ANOMALY.value: (
        "Упрощённый индекс аномалии момента и нагрузки (не 4DOF T&D). "
        "Проверить механическую нагрузку и условия очистки."
    ),
    EventClass.SENSOR_QUALITY_ISSUE.value: (
        "Проверить качество измерений до технологического решения."
    ),
    EventClass.OPERATION_CHANGE.value: (
        "Смена операции: адаптация baseline; не интерпретировать как осложнение."
    ),
    EventClass.SHORT_TRANSIENT.value: "Короткий выброс; наблюдать без эскалации.",
    EventClass.NORMAL_NOISE.value: "Отклонение в зоне шума; наблюдать.",
    EventClass.INSUFFICIENT_HISTORY.value: "Недостаточно истории для режимной базовой линии.",
    EventClass.SIGNAL_CONFLICT.value: "Конфликт режима и сигналов насоса/операции.",
    EventClass.NONE.value: "Устойчивого кандидата на осложнение не выявлено.",
}


UNKNOWNS = {
    EventClass.POSSIBLE_INFLUX_CANDIDATE.value: (
        "Нет обязательных pit volume / flow-out для well-control; возможна путаница с ballooning; "
        "не ECD; это не является диагностикой проявления."
    ),
    EventClass.POSSIBLE_LOST_CIRCULATION.value: (
        "Нет модели ECD/реологии; нет оценки объёма; не подтверждённое поглощение."
    ),
    EventClass.POSSIBLE_PACKOFF.value: (
        "Не модель шламовой пробки; эмпирический гидравлический экран."
    ),
    EventClass.TORQUE_DRAG_ANOMALY.value: (
        "Не open-source 4DOF T&D (SPE-230785); упрощённый индекс."
    ),
}


def detect(df: pd.DataFrame, cfg: DetectorConfig | None = None) -> pd.DataFrame:
    cfg = cfg or DetectorConfig()
    pcfg = cfg.persistence or PersistenceConfig()
    bcfg = cfg.baseline or BaselineConfig()

    frame = validate_frame(df)
    frame = prepare_timebase(frame)
    frame = add_quality_flags(frame)
    frame = add_regimes(frame, adaptation_points=cfg.adaptation_points)
    frame = add_features(frame, cfg=bcfg)

    state = PersistenceState()
    rows: list[dict[str, Any]] = []
    t0 = frame["timestamp"].iloc[0]
    event_counter = 0
    active_event_id: str | None = None

    for _, row in frame.iterrows():
        proposed, score, contrib = _propose(row, cfg)
        dt = float(row["dt_s"]) if pd.notna(row.get("dt_s")) else float(row.get("median_dt_s", 1.0))

        if proposed == EventClass.SENSOR_QUALITY_ISSUE.value:
            label, phase = proposed, "QUALITY_BLOCKED"
            state = PersistenceState(cooldown_remaining_s=state.cooldown_remaining_s)
            active_event_id = None
        elif proposed == EventClass.OPERATION_CHANGE.value:
            label, phase = proposed, "REGIME_TRANSITION"
            state = PersistenceState(cooldown_remaining_s=state.cooldown_remaining_s)
            active_event_id = None
        elif proposed in {
            EventClass.INSUFFICIENT_HISTORY.value,
            EventClass.SIGNAL_CONFLICT.value,
        }:
            label = proposed
            phase = "WARMUP" if proposed == EventClass.INSUFFICIENT_HISTORY.value else "QUALITY_BLOCKED"
        else:
            prop = proposed if proposed in COMPLICATION_CLASSES else None
            state, label, raw_phase = step_persistence(
                state, prop, dt, pcfg, elapsed_s=float((row["timestamp"] - t0).total_seconds())
            )
            phase = PHASE_MAP.get(raw_phase, raw_phase.upper())
            if label in COMPLICATION_CLASSES and raw_phase == "confirmed":
                # Do not polish influx-candidate score upward — confound scenarios must stay honest.
                if label != EventClass.POSSIBLE_INFLUX_CANDIDATE.value:
                    score = max(score, 0.5)
                if active_event_id is None:
                    event_counter += 1
                    active_event_id = f"E{event_counter:04d}"
            elif label in {EventClass.SHORT_TRANSIENT.value, EventClass.NORMAL_NOISE.value}:
                score = min(score, 0.25)
                active_event_id = None
            elif label == EventClass.NONE.value:
                active_event_id = None

        if label == EventClass.INSUFFICIENT_HISTORY.value:
            phase = "WARMUP"

        elapsed = (row["timestamp"] - t0).total_seconds()
        rows.append(
            {
                "event": label,
                "display_label": DISPLAY_LABELS.get(label, label),
                "heuristic_score": round(float(score), 3),
                "rule_score": round(float(score), 3),
                "screening_score": round(float(score), 3),
                "detector_phase": phase,
                "event_id": active_event_id if label in COMPLICATION_CLASSES else None,
                "contributing_features": ";".join(contrib) if contrib else "",
                "recommended_action": ACTIONS.get(label, ACTIONS[EventClass.NONE.value]),
                "unknowns": UNKNOWNS.get(label, "Полевая точность не подтверждена (requires_field_validation)."),
                "elapsed_s": elapsed,
                "score_semantics": "heuristic_score_not_probability",
            }
        )

    meta = pd.DataFrame(rows)
    out = pd.concat([frame.reset_index(drop=True), meta], axis=1)
    out.attrs["algorithm_version"] = ALGORITHM_VERSION
    out.attrs["source_id"] = frame.attrs.get("source_id", "<memory>")
    out.attrs["score_semantics"] = "heuristic_score_not_probability"
    out.attrs["data_origin"] = "unknown_until_marked"
    return out
