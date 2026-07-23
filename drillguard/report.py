"""JSON/HTML report generation with HTML escaping (no code execution)."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .events import build_event_cards, summarize
from .schema import ALGORITHM_VERSION


def build_report(
    out,
    *,
    data_origin: str = "synthetic",
    source_id: str | None = None,
    scenario: str | None = None,
) -> dict[str, Any]:
    cards = build_event_cards(out, data_origin=data_origin, source_id=source_id)
    return {
        "algorithm_version": ALGORITHM_VERSION,
        "scenario": scenario,
        "data_origin": data_origin,
        "source_id": source_id or out.attrs.get("source_id", "<memory>"),
        "claim_level": "synthetic_only",
        "requires_field_validation": True,
        "advisory_banner": (
            "Только рекомендация. Система не управляет буровой, не пишет в АСУ ТП/SCADA "
            "и не является противоаварийной защитой."
        ),
        "score_semantics": "heuristic_score is NOT a calibrated probability",
        "summary": summarize(out),
        "event_cards": cards,
        "physics_disclaimer": out.attrs.get(
            "physics_disclaimer",
            "Not a full hydraulics / T&D model.",
        ),
    }


def write_json(report: dict[str, Any], path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def write_html(report: dict[str, Any], path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    cards = report.get("event_cards", [])
    rows = []
    for c in cards:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(c.get('start_time')))}</td>"
            f"<td>{html.escape(str(c.get('event_class')))}</td>"
            f"<td>{html.escape(str(c.get('heuristic_score')))}</td>"
            f"<td>{html.escape(str(c.get('regime')))}</td>"
            f"<td>{html.escape(str(c.get('recommended_check')))}</td>"
            f"<td>{html.escape(str(c.get('unknowns')))}</td>"
            "</tr>"
        )
    body = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"/>
<title>DrillGuard OS report</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:24px;color:#122}}
.banner{{background:#fff3cd;border:1px solid #856404;padding:12px;margin-bottom:16px}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ccc;padding:6px;font-size:13px;vertical-align:top}}
th{{background:#f4f4f4;text-align:left}}
.meta{{color:#555;font-size:13px}}
</style></head><body>
<div class="banner"><strong>{html.escape(report.get('advisory_banner',''))}</strong></div>
<h1>DrillGuard OS — event cards</h1>
<p class="meta">version={html.escape(str(report.get('algorithm_version')))}
 | origin={html.escape(str(report.get('data_origin')))}
 | source={html.escape(str(report.get('source_id')))}
 | score={html.escape(str(report.get('score_semantics')))}</p>
<pre>{html.escape(json.dumps(report.get('summary',{}), ensure_ascii=False, indent=2))}</pre>
<table>
<thead><tr><th>Start</th><th>Class</th><th>Score</th><th>Regime</th><th>Check</th><th>Unknowns</th></tr></thead>
<tbody>
{''.join(rows) if rows else '<tr><td colspan="6">No tracked events</td></tr>'}
</tbody></table>
</body></html>"""
    p.write_text(body, encoding="utf-8")
    return p
