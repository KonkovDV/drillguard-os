from benchmark.metrics import aggregate_metrics, binary_detection
from benchmark.scenarios import CORE_SCENARIOS
from drillguard.detector import detect
from drillguard.synthetic import make_scenario

def test_metrics_have_delay_and_fa():
    df, gt = make_scenario("packoff", seed=0)
    m = binary_detection(detect(df), gt)
    assert "detection_delay_s" in m
    assert "false_alarms_per_hour" in m
    assert "f1" in m

def test_core_scenarios_run():
    rows = []
    for name in CORE_SCENARIOS:
        df, gt = make_scenario(name, seed=0)
        rows.append(binary_detection(detect(df), gt))
    agg = aggregate_metrics(rows)
    assert agg["n_cases"] == len(CORE_SCENARIOS)
    assert agg["claim_level"] == "synthetic_only"
