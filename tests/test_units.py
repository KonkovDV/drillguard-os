from drillguard.schema import COLUMN_UNITS, NOISE_FLOOR


def test_units_documented_for_required_channels():
    for c in (
        "standpipe_pressure_kpa",
        "pump_flow_lpm",
        "hookload_kn",
        "torque_knm",
        "rate_of_penetration_m_h",
    ):
        assert c in COLUMN_UNITS
        assert c in NOISE_FLOOR
