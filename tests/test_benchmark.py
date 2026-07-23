from benchmark.metrics import aggregate_report, evaluate_case
from benchmark.scenarios import CORE_SCENARIOS
from drillguard.detector import detect
from drillguard.synthetic import make_scenario


def test_evaluate_has_levels():
    df, gt = make_scenario("packoff", seed=0)
    m = evaluate_case(detect(df), gt)
    assert "level_a" in m and "level_b" in m and "level_c" in m
    assert m["level_a"].get("f1") is not None
    assert "false_alarms_per_hour" in m["level_c"]


def test_normal_gate_zero_fa():
    rows = []
    for seed in range(3):
        df, gt = make_scenario("normal", seed=seed)
        rows.append(evaluate_case(detect(df), gt))
    agg = aggregate_report(rows)
    assert agg["normal_scenario_gate"]["all_zero_complication_fa"] is True


def test_operation_change_interval_not_latest():
    df, gt = make_scenario("connection", seed=0)
    m = evaluate_case(detect(df), gt)
    assert m["level_b"].get("latest_is_truth_required") is False
    assert m["level_b"].get("detected_in_interval") is True


def test_core_scenarios_run():
    rows = []
    for name in CORE_SCENARIOS:
        df, gt = make_scenario(name, seed=0)
        rows.append(evaluate_case(detect(df), gt))
    agg = aggregate_report(rows)
    assert agg["n_cases"] == len(CORE_SCENARIOS)
    assert "compat_appearance_rate_demoted" in agg
