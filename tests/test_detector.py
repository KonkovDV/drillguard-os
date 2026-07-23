from drillguard.detector import detect
from drillguard.schema import COMPLICATION_CLASSES
from drillguard.synthetic import make_scenario


def test_packoff():
    df, gt = make_scenario("packoff", seed=0)
    out = detect(df)
    assert "possible_packoff" in set(out["event"])

def test_lost():
    df, _ = make_scenario("lost_circulation", seed=0)
    assert "possible_lost_circulation" in set(detect(df)["event"])

def test_influx_candidate():
    df, _ = make_scenario("influx_like", seed=0)
    assert "possible_influx_candidate" in set(detect(df)["event"])
    assert "possible_influx" not in set(detect(df)["event"])

def test_torque():
    df, _ = make_scenario("torque", seed=0)
    assert "torque_drag_anomaly" in set(detect(df)["event"])

def test_normal_no_uncontrolled_complications():
    for seed in range(5):
        out = detect(make_scenario("normal", seed=seed)[0])
        comps = out["event"].isin(list(COMPLICATION_CLASSES))
        assert comps.sum() == 0, f"seed={seed} counts={out['event'].value_counts().to_dict()}"

def test_short_transient_not_packoff():
    out = detect(make_scenario("short_transient_only", seed=0)[0])
    assert "possible_packoff" not in set(out["event"])

def test_determinism():
    a = detect(make_scenario("packoff", seed=7)[0])["event"].tolist()
    b = detect(make_scenario("packoff", seed=7)[0])["event"].tolist()
    assert a == b

def test_no_confidence_probability_field():
    out = detect(make_scenario("normal", seed=0)[0])
    assert "confidence" not in out.columns
    assert "heuristic_score" in out.columns

def test_flatline_sensor():
    out = detect(make_scenario("sensor_fault_flatline", seed=0)[0])
    assert "sensor_quality_issue" in set(out["event"])
