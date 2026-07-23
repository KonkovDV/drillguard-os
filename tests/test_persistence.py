from drillguard.persistence import PersistenceConfig, PersistenceState, step_persistence


def test_confirm_requires_duration():
    st = PersistenceState()
    cfg = PersistenceConfig(confirm_seconds=5, transient_max_seconds=3)
    labels = []
    for _ in range(3):
        st, lab, phase = step_persistence(st, "possible_packoff", 1.0, cfg)
        labels.append((lab, phase))
    assert labels[-1][1] == "candidate"
    st, lab, phase = step_persistence(st, "possible_packoff", 1.0, cfg)
    st, lab, phase = step_persistence(st, "possible_packoff", 1.0, cfg)
    assert lab == "possible_packoff"
    assert phase == "confirmed"

def test_short_candidate_becomes_transient():
    st = PersistenceState()
    cfg = PersistenceConfig(confirm_seconds=8, transient_max_seconds=5)
    st, _, _ = step_persistence(st, "possible_packoff", 1.0, cfg)
    st, _, _ = step_persistence(st, "possible_packoff", 1.0, cfg)
    st, lab, phase = step_persistence(st, None, 1.0, cfg)
    assert lab == "short_transient"
    assert phase == "transient"
