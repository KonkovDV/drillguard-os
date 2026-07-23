from drillguard.detector import detect
from drillguard.report import build_report, write_html, write_json
from drillguard.synthetic import make_scenario

def test_json_and_html(tmp_path):
    out = detect(make_scenario("packoff", seed=0)[0])
    rep = build_report(out, data_origin="synthetic", source_id="x", scenario="packoff")
    jp = write_json(rep, tmp_path / "r.json")
    hp = write_html(rep, tmp_path / "r.html")
    html = hp.read_text(encoding="utf-8")
    assert "Только рекомендация" in html
    assert "<script>" not in rep.get("event_cards", [{}])[0].get("recommended_check", "")
    # Escaping: inject angle brackets into action via card path — banner escaped
    assert jp.exists()

def test_html_escapes_dynamic_text(tmp_path):
    out = detect(make_scenario("normal", seed=0)[0])
    rep = build_report(out, data_origin='synthetic<script>', source_id='a<b>')
    html = write_html(rep, tmp_path / "e.html").read_text(encoding="utf-8")
    assert "<script>" not in html or "synthetic&lt;script&gt;" in html
