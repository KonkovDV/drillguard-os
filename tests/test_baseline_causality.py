import numpy as np
from drillguard.baseline import BaselineConfig, causal_baseline_stats

def test_no_future_leakage():
    n = 80
    values = np.concatenate([np.ones(40) * 100.0, np.ones(40) * 200.0])
    regimes = np.array(["drilling"] * n)
    cfg = BaselineConfig(window=30, min_history=10, slow_adapt_alpha=0.0)
    med, scale, z, hok = causal_baseline_stats(values, regimes, cfg=cfg, noise_floor=1.0)
    assert hok[39]
    assert abs(med[39] - 100) < 1e-6
    # After freeze, step to 200 must not pull median to 200
    assert hok[50]
    assert abs(med[50] - 100) < 1.0
    assert z[50] > 5

def test_min_history():
    values = np.arange(10, dtype=float)
    regimes = np.array(["drilling"] * 10)
    cfg = BaselineConfig(window=20, min_history=8)
    _, _, _, hok = causal_baseline_stats(values, regimes, cfg=cfg, noise_floor=1.0)
    assert not hok[5]
    assert hok[9]
