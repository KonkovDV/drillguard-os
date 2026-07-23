from drillguard.detector import detect
from drillguard.events import build_event_cards, summarize
from drillguard.synthetic import make_scenario

def test_cards_have_required_fields():
    out = detect(make_scenario("packoff", seed=0)[0])
    cards = build_event_cards(out, data_origin="synthetic", source_id="t")
    assert cards
    c = cards[0]
    for k in [
        "event_class",
        "start_time",
        "confirm_time",
        "heuristic_score",
        "score_semantics",
        "baseline_interval",
        "unknowns",
        "algorithm_version",
        "advisory_only",
    ]:
        assert k in c
    assert "not_calibrated" in c["score_semantics"]
    assert c["score_semantics"].startswith("heuristic")

def test_summarize():
    s = summarize(detect(make_scenario("normal", seed=0)[0]))
    assert s["rows"] > 0
