from drillguard.detector import detect
from drillguard.features import FEATURE_CATALOG, add_features
from drillguard.quality import add_quality_flags
from drillguard.regimes import add_regimes
from drillguard.synthetic import make_scenario
from drillguard.timebase import prepare_timebase

def test_feature_kinds_documented():
    assert "torque_drag_index" in FEATURE_CATALOG
    assert FEATURE_CATALOG["torque_drag_index"]["kind"] == "physically_motivated"

def test_features_have_z():
    df, _ = make_scenario("packoff", n=200, seed=0)
    out = add_features(add_regimes(add_quality_flags(prepare_timebase(df))))
    assert "standpipe_pressure_kpa_z" in out.columns
    assert out["baseline_history_ok"].iloc[-1]
