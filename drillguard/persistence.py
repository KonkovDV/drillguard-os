"""Persistence, hysteresis, and cooldown for event confirmation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PersistenceConfig:
    confirm_seconds: float = 8.0
    clear_seconds: float = 6.0
    transient_max_seconds: float = 5.0
    cooldown_seconds: float = 15.0
    min_points: int = 3


@dataclass
class PersistenceState:
    candidate_class: str | None = None
    candidate_accum_s: float = 0.0
    candidate_points: int = 0
    active_class: str | None = None
    active_accum_s: float = 0.0
    clear_accum_s: float = 0.0
    cooldown_remaining_s: float = 0.0
    last_confirm_time_s: float | None = None


def step_persistence(
    state: PersistenceState,
    proposed: str | None,
    dt_s: float,
    cfg: PersistenceConfig,
    *,
    elapsed_s: float | None = None,
) -> tuple[PersistenceState, str, str]:
    """
    Advance FSM.
    Returns (state, row_label, phase) where phase in
    idle|candidate|confirmed|clearing|cooldown|transient.

    Confirm requires both duration AND min_points so a single gap Δt cannot confirm.
    """
    # Cap credited Δt so timeline gaps cannot buy confirmation in one step.
    raw_dt = float(dt_s) if dt_s and dt_s > 0 else 1.0
    dt = max(min(raw_dt, 5.0), 1e-3)

    if state.cooldown_remaining_s > 0:
        state.cooldown_remaining_s = max(0.0, state.cooldown_remaining_s - dt)

    # Active event path
    if state.active_class is not None:
        if proposed == state.active_class:
            state.active_accum_s += dt
            state.clear_accum_s = 0.0
            return state, state.active_class, "confirmed"
        state.clear_accum_s += dt
        if state.clear_accum_s >= cfg.clear_seconds:
            state.active_class = None
            state.active_accum_s = 0.0
            state.clear_accum_s = 0.0
            state.candidate_class = None
            state.candidate_accum_s = 0.0
            state.candidate_points = 0
            state.cooldown_remaining_s = cfg.cooldown_seconds
            return state, "none", "cooldown"
        return state, state.active_class, "clearing"

    if state.cooldown_remaining_s > 0:
        return state, "none", "cooldown"

    if proposed is None:
        # Expire short candidate as transient
        if state.candidate_class and state.candidate_accum_s > 0:
            if state.candidate_accum_s < cfg.confirm_seconds:
                if state.candidate_accum_s <= cfg.transient_max_seconds:
                    label = "short_transient"
                else:
                    label = "normal_noise"
                state.candidate_class = None
                state.candidate_accum_s = 0.0
                state.candidate_points = 0
                return state, label, "transient"
        state.candidate_class = None
        state.candidate_accum_s = 0.0
        state.candidate_points = 0
        return state, "none", "idle"

    if state.candidate_class != proposed:
        state.candidate_class = proposed
        state.candidate_accum_s = dt
        state.candidate_points = 1
        return state, "normal_noise", "candidate"

    state.candidate_accum_s += dt
    state.candidate_points += 1
    if (
        state.candidate_accum_s >= cfg.confirm_seconds
        and state.candidate_points >= cfg.min_points
    ):
        state.active_class = proposed
        state.active_accum_s = state.candidate_accum_s
        state.last_confirm_time_s = elapsed_s
        state.candidate_class = None
        state.candidate_accum_s = 0.0
        state.candidate_points = 0
        return state, proposed, "confirmed"

    return state, "normal_noise", "candidate"
