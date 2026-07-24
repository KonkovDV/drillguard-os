"""Synthetic scenario generator with ground-truth metadata (not field data)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

SCENARIO_NAMES = [
    "normal",
    "packoff",
    "cuttings_accumulation",
    "bit_nozzle_packoff",
    "lost_circulation",
    "influx",
    "influx_like",
    "ballooning_like",
    "torque",
    "torque_drag",
    "hookload_rise",
    "pump_start_stop",
    "flow_change",
    "connection",
    "tripping",
    "sensor_pressure_drift",
    "sensor_flow_drift",
    "sensor_spikes",
    "sensor_fault_flatline",
    "missing_gaps",
    "desync",
    "mud_density_change",
    "mixed_packoff_torque",
    "short_transient_only",
    "low_intensity_packoff",
    "high_intensity_packoff",
    "high_noise",
    "low_rate_1hz",
]


def _hold_ramp(arr: np.ndarray, a: int, b: int, peak: float) -> None:
    """Ramp a→b to peak, then hold peak to series end (avoids end-of-window false opposites)."""
    L = max(b - a, 1)
    arr[a:b] += np.linspace(0, peak, L)
    if b < len(arr):
        arr[b:] += peak


def make_scenario(
    name: str = "normal",
    n: int = 400,
    seed: int = 0,
    freq: str = "1s",
    noise_scale: float = 1.0,
    intensity: float = 1.0,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return (frame, ground_truth). All results are synthetic."""
    if name in {"influx", "influx_like"}:
        name = "influx_like"
    elif name == "torque_drag":
        name = "torque"
    elif name == "operation_change":
        name = "connection"
    elif name not in SCENARIO_NAMES:
        raise ValueError(f"Unknown scenario: {name}")

    rng = np.random.default_rng(seed)
    if name == "low_rate_1hz":
        freq = "1s"
        n = max(n, 400)
    t = pd.date_range("2026-01-01", periods=n, freq=freq)
    depth = 3000 + np.linspace(0, 10, n)
    op = np.array(["drilling"] * n, dtype=object)
    flow = np.full(n, 900.0)
    pump = np.full(n, 120.0)
    pressure = 14000 + 0.2 * np.arange(n)
    hook = 120 + 0.3 * rng.normal(size=n) * noise_scale
    torque = 18 + 0.4 * rng.normal(size=n) * noise_scale
    rop = 12 + 0.4 * rng.normal(size=n) * noise_scale
    dens = np.full(n, 1.20)
    event_start = None
    event_end = None
    event_class = "none"
    channels: list[str] = []
    mid = int(n * 0.45)
    dur = int(n * 0.35)

    def inject(start: int, length: int) -> tuple[int, int]:
        a = max(0, start)
        b = min(n, start + length)
        return a, b

    if name == "normal":
        pass
    elif name in {
        "packoff",
        "cuttings_accumulation",
        "bit_nozzle_packoff",
        "high_intensity_packoff",
        "low_intensity_packoff",
    }:
        a, b = inject(mid, dur)
        event_start, event_end = a, n - 1
        event_class = "possible_packoff"
        channels = ["standpipe_pressure_kpa", "pump_flow_lpm", "torque_knm"]
        scale = intensity
        if name == "low_intensity_packoff":
            scale = 0.45 * intensity
        if name == "high_intensity_packoff":
            scale = 1.6 * intensity
        if name == "bit_nozzle_packoff":
            scale = 1.2 * intensity
        _hold_ramp(pressure, a, b, 2800 * scale)
        _hold_ramp(flow, a, b, 120 * scale)
        _hold_ramp(torque, a, b, 10 * scale)
        _hold_ramp(rop, a, b, -4 * scale)
    elif name == "lost_circulation":
        a, b = inject(mid, dur)
        event_start, event_end = a, n - 1
        event_class = "possible_lost_circulation"
        channels = ["standpipe_pressure_kpa", "pump_flow_lpm"]
        _hold_ramp(pressure, a, b, -2600 * intensity)
        _hold_ramp(flow, a, b, -200 * intensity)
    elif name == "influx_like":
        a, b = inject(mid, dur)
        event_start, event_end = a, n - 1
        event_class = "possible_influx_candidate"
        channels = ["standpipe_pressure_kpa", "pump_flow_lpm"]
        _hold_ramp(pressure, a, b, -2200 * intensity)
        _hold_ramp(flow, a, b, 160 * intensity)
    elif name == "ballooning_like":
        # Pressure drop with mild flow rise — known confound for influx-like screens
        a, b = inject(mid, dur)
        event_start, event_end = a, n - 1
        event_class = "ballooning_like"
        channels = ["standpipe_pressure_kpa", "pump_flow_lpm"]
        _hold_ramp(pressure, a, b, -1800 * intensity)
        _hold_ramp(flow, a, b, 40 * intensity)
    elif name == "torque":
        a, b = inject(mid, dur)
        event_start, event_end = a, n - 1
        event_class = "torque_drag_anomaly"
        channels = ["torque_knm", "hookload_kn", "rate_of_penetration_m_h"]
        _hold_ramp(torque, a, b, 18 * intensity)
        _hold_ramp(hook, a, b, 18 * intensity)
        _hold_ramp(rop, a, b, -5 * intensity)
    elif name == "hookload_rise":
        a, b = inject(mid, dur)
        event_start, event_end = a, n - 1
        event_class = "torque_drag_anomaly"
        channels = ["hookload_kn", "torque_knm"]
        _hold_ramp(hook, a, b, 25 * intensity)
        _hold_ramp(torque, a, b, 8 * intensity)
    elif name == "pump_start_stop":
        a, b = inject(mid, int(n * 0.15))
        event_start, event_end = a, b
        event_class = "operation_change"
        channels = ["pump_flow_lpm", "pump_rpm"]
        op[a:b] = "circulation"
        flow[a:b] = 0
        pump[a:b] = 0
    elif name == "flow_change":
        a, b = inject(mid, dur)
        event_start, event_end = a, b
        event_class = "none"
        channels = ["pump_flow_lpm"]
        flow[a:b] = 1050
    elif name == "connection":
        a, b = inject(mid, int(n * 0.2))
        event_start, event_end = a, b
        event_class = "operation_change"
        channels = ["operation"]
        op[a:b] = "connection"
        flow[a:b] = 0
        pump[a:b] = 0
    elif name == "tripping":
        a, b = inject(mid, dur)
        event_start, event_end = a, b
        event_class = "operation_change"
        channels = ["operation"]
        op[a:b] = "tripping"
        rop[a:b] = 0
    elif name == "sensor_pressure_drift":
        a, b = inject(mid, dur)
        event_start, event_end = a, n - 1
        event_class = "sensor_quality_issue"
        channels = ["standpipe_pressure_kpa"]
        _hold_ramp(pressure, a, b, 800)
    elif name == "sensor_flow_drift":
        a, b = inject(mid, dur)
        event_start, event_end = a, n - 1
        event_class = "sensor_quality_issue"
        channels = ["pump_flow_lpm"]
        _hold_ramp(flow, a, b, 60)
    elif name == "sensor_spikes":
        a = mid
        event_start, event_end = a, min(n, a + 3)
        event_class = "short_transient"
        channels = ["standpipe_pressure_kpa"]
        pressure[a : a + 2] += 4000
    elif name == "sensor_fault_flatline":
        a, b = inject(mid, dur)
        event_start, event_end = a, b
        event_class = "sensor_quality_issue"
        channels = ["standpipe_pressure_kpa"]
        pressure[a:b] = pressure[a - 1] if a > 0 else pressure[0]
    elif name == "missing_gaps":
        a = mid
        event_start, event_end = a, min(n, a + 5)
        event_class = "none"
        channels = ["timestamp"]
        t = pd.DatetimeIndex(list(t[:a]) + list(t[a:] + pd.Timedelta(seconds=120)))
    elif name == "desync":
        a, b = inject(mid, 20)
        event_start, event_end = a, b
        event_class = "none"
        channels = ["standpipe_pressure_kpa"]
        pressure[a:b] += 5000
    elif name == "mud_density_change":
        a, b = inject(mid, dur)
        event_start, event_end = a, b
        event_class = "none"
        channels = ["mud_density_sg"]
        dens[a:b] = 1.35
        # Small coupled SPP shift only — large bumps falsely look like packoff under GT=none.
        pressure[a:b] += 80
    elif name == "mixed_packoff_torque":
        a, b = inject(mid, dur)
        event_start, event_end = a, n - 1
        event_class = "possible_packoff"
        channels = ["standpipe_pressure_kpa", "torque_knm"]
        _hold_ramp(pressure, a, b, 2500)
        _hold_ramp(flow, a, b, 60)
        _hold_ramp(torque, a, b, 16)
    elif name == "short_transient_only":
        a = mid
        event_start, event_end = a, a + 2
        event_class = "short_transient"
        channels = ["standpipe_pressure_kpa", "pump_flow_lpm"]
        pressure[a : a + 2] += 3500
        flow[a : a + 2] += 200
    elif name == "high_noise":
        noise_scale = 4.0
        event_class = "none"
    elif name == "low_rate_1hz":
        event_class = "none"

    spp_noise = rng.normal(0, 25 * noise_scale, n)
    flow_noise = rng.normal(0, 6 * noise_scale, n)
    if name == "sensor_fault_flatline" and event_start is not None:
        spp_noise[event_start:event_end] = 0.0

    dq = ["ok"] * n
    if name == "desync" and event_start is not None and event_end is not None:
        # Desync injection is a quality/integrity episode, not a packoff truth.
        for i in range(event_start, min(event_end + 1, n)):
            dq[i] = "bad"
    if name in {"sensor_pressure_drift", "sensor_flow_drift"} and event_start is not None:
        # Drift scenarios are GT sensor_quality_issue — mark integrity for the held offset.
        end = event_end if event_end is not None else n - 1
        for i in range(event_start, min(end + 1, n)):
            dq[i] = "bad"

    df = pd.DataFrame(
        {
            "timestamp": t,
            "depth_m": depth,
            "standpipe_pressure_kpa": pressure + spp_noise,
            "pump_flow_lpm": np.clip(flow + flow_noise, 0, None),
            "hookload_kn": np.clip(hook, 0, None),
            "torque_knm": np.clip(torque, 0, None),
            "rate_of_penetration_m_h": rop,
            "pump_rpm": pump,
            "operation": op,
            "data_quality": dq,
            "mud_density_sg": dens,
            "plastic_viscosity_cp": np.full(n, 25.0),
        }
    )

    # Enrich GT with timestamps when indices known
    est = str(df.loc[event_start, "timestamp"]) if event_start is not None else None
    eet = str(df.loc[event_end, "timestamp"]) if event_end is not None else None

    gt = {
        "scenario": name,
        "synthetic": True,
        "data_origin": "synthetic",
        "seed": seed,
        "n": n,
        "freq": freq,
        "noise_scale": noise_scale,
        "intensity": intensity,
        "event_class": event_class,
        "event_start_idx": event_start,
        "event_end_idx": event_end,
        "event_start_timestamp": est,
        "event_end_timestamp": eet,
        "channels_affected": channels,
        "affected_channels": channels,
        "regime": "drilling",
        "operation": str(op[0]),
        "expected_action": "engineer_verification_only",
        "requires_field_validation": True,
        "claim_level": "synthetic_only",
    }
    return df, gt


SCENARIOS = SCENARIO_NAMES
