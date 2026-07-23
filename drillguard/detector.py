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


@dataclass
class DetectorConfig:
    baseline: BaselineConfig | None = None
    persistence: PersistenceConfig | None = None
    z_enter: float = 4.5
    z_exit: float = 3.0
    td_enter: float = 4.5
    adaptation_points: int = 20


def _propose(row: pd.Series, cfg: DetectorConfig) -> tuple[str | None, float, list[str]]:
    """Return (proposed_complication_or_None, heuristic_score, contributors)."""
    contributors: list[str] = []

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

    # Hysteresis uses enter thresholds for proposal
    if pz < -cfg.z_enter and fz < -cfg.z_enter * 0.6:
        contributors = [f"spp_z={pz:.2f}", f"flow_z={fz:.2f}"]
        return EventClass.POSSIBLE_LOST_CIRCULATION.value, 0.78, contributors
    if pz > cfg.z_enter and (fz > cfg.z_enter * 0.35 or pfz > cfg.z_enter * 0.45 or abs(float(row.get("delta_spp_kpa", 0))) > 150):
        contributors = [f"spp_z={pz:.2f}", f"flow_z={fz:.2f}", f"spp_q_z={pfz:.2f}"]
        return EventClass.POSSIBLE_PACKOFF.value, 0.80, contributors
    if pz < -cfg.z_enter and fz > cfg.z_enter * 0.7:
        contributors = [f"spp_z={pz:.2f}", f"flow_z={fz:.2f}"]
        return EventClass.POSSIBLE_INFLUX.value, 0.55, contributors
    if np.isfinite(td) and td > cfg.td_enter:
        contributors = [f"torque_drag_index={td:.2f}"]
        return EventClass.TORQUE_DRAG_ANOMALY.value, 0.74, contributors

    # Soft noise band
    if abs(pz) > cfg.z_exit or abs(fz) > cfg.z_exit:
        return None, 0.15, [f"soft_deviation spp_z={pz:.2f} flow_z={fz:.2f}"]

    return None, 0.05, []


ACTIONS = {
    EventClass.POSSIBLE_PACKOFF.value: (
        "Проверить циркуляцию, содержание шлама и признаки ухудшения очистки ствола "
        "(только проверка; без автоматических команд)."
    ),
    EventClass.POSSIBLE_LOST_CIRCULATION.value: (
        "Проверить баланс раствора и признаки поглощения по утверждённому регламенту."
    ),
    EventClass.POSSIBLE_INFLUX.value: (
        "Кандидат на проявление по SPP/flow-in только. Требуется проверка по регламенту; "
        "без pit/flow-out класс неполон (requires field validation)."
    ),
    EventClass.TORQUE_DRAG_ANOMALY.value: (
        "Проверить механическую нагрузку, траекторию и условия очистки."
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
    EventClass.POSSIBLE_INFLUX.value: (
        "Нет pit volume / flow-out; возможна путаница с ballooning; "
        "не полноценная well-control диагностика."
    ),
    EventClass.POSSIBLE_LOST_CIRCULATION.value: (
        "Нет модели ECD/реологии; не подтверждает объём поглощения."
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
    for i, row in frame.iterrows():
        proposed, score, contrib = _propose(row, cfg)
        # Informational classes bypass persistence complication path
        dt = float(row["dt_s"]) if pd.notna(row.get("dt_s")) else float(row.get("median_dt_s", 1.0))
        if proposed in {
            EventClass.SENSOR_QUALITY_ISSUE.value,
            EventClass.OPERATION_CHANGE.value,
            EventClass.INSUFFICIENT_HISTORY.value,
            EventClass.SIGNAL_CONFLICT.value,
        }:
            label = proposed
            phase = "informational"
            # Reset complication candidate on regime change
            if proposed == EventClass.OPERATION_CHANGE.value:
                state = PersistenceState(cooldown_remaining_s=state.cooldown_remaining_s)
        else:
            # Only persist complication proposals
            prop = proposed if proposed in COMPLICATION_CLASSES else None
            state, label, phase = step_persistence(state, prop, dt, pcfg)
            if label in COMPLICATION_CLASSES:
                score = max(score, 0.5)
            elif label in {EventClass.SHORT_TRANSIENT.value, EventClass.NORMAL_NOISE.value}:
                score = min(score, 0.25)

        elapsed = (row["timestamp"] - t0).total_seconds()
        rows.append(
            {
                "event": label,
                "heuristic_score": round(float(score), 3),
                "detector_phase": phase,
                "contributing_features": ";".join(contrib) if contrib else "",
                "recommended_action": ACTIONS.get(label, ACTIONS[EventClass.NONE.value]),
                "unknowns": UNKNOWNS.get(label, "Полевая точность не подтверждена."),
                "elapsed_s": elapsed,
            }
        )

    meta = pd.DataFrame(rows)
    out = pd.concat([frame.reset_index(drop=True), meta], axis=1)
    out.attrs["algorithm_version"] = ALGORITHM_VERSION
    out.attrs["source_id"] = frame.attrs.get("source_id", "<memory>")
    out.attrs["score_semantics"] = "heuristic_score_not_probability"
    out.attrs["data_origin"] = "unknown_until_marked"
    return out
