"""Minimal local dashboard (matplotlib HTML) — advisory only."""

from __future__ import annotations

import base64
import html
import io
from pathlib import Path
from typing import Any

import pandas as pd

from .detector import detect
from .events import build_event_cards
from .ingestion import load_csv
from .report import build_report, write_html
from .schema import ALGORITHM_VERSION


def _sparkline_png(out: pd.DataFrame) -> str:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover
        raise ImportError("Install dashboard extras: pip install 'drillguard-os[dashboard]'") from exc

    fig, axes = plt.subplots(3, 1, figsize=(10, 6), sharex=True)
    t = out["timestamp"]
    axes[0].plot(t, out["standpipe_pressure_kpa"], color="#1f4e79", lw=1)
    axes[0].set_ylabel("SPP kPa")
    axes[1].plot(t, out["pump_flow_lpm"], color="#2e7d32", lw=1)
    axes[1].set_ylabel("Flow L/min")
    axes[2].plot(t, out["torque_knm"], color="#6a1b9a", lw=1)
    axes[2].set_ylabel("Torque kN·m")
    # Highlight complication rows
    mask = out["event"].isin(
        [
            "possible_packoff",
            "possible_lost_circulation",
            "possible_influx_candidate",
            "torque_drag_anomaly",
        ]
    )
    for ax in axes:
        ymin, ymax = ax.get_ylim()
        ax.fill_between(t, ymin, ymax, where=mask, color="#f4c7c3", alpha=0.35, step="mid")
    axes[0].set_title(f"DrillGuard OS signals (v{ALGORITHM_VERSION}) — advisory only")
    fig.autofmt_xdate()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def render_dashboard(
    out: pd.DataFrame,
    *,
    data_origin: str,
    source_id: str,
    output_html: str | Path,
) -> Path:
    report = build_report(out, data_origin=data_origin, source_id=source_id)
    cards = build_event_cards(out, data_origin=data_origin, source_id=source_id)
    try:
        img = _sparkline_png(out)
        img_tag = f'<img alt="signals" src="data:image/png;base64,{img}" style="max-width:100%"/>'
    except ImportError:
        img_tag = "<p>matplotlib not installed; table-only view.</p>"

    # Class filter list
    classes = sorted(set(out["event"].tolist()))
    class_opts = "".join(f"<option value='{html.escape(c)}'>{html.escape(c)}</option>" for c in classes)

    rows = []
    for c in cards:
        rows.append(
            f"<tr data-class='{html.escape(c['event_class'])}'>"
            f"<td>{html.escape(c['start_time'])}</td>"
            f"<td>{html.escape(c['event_class'])}</td>"
            f"<td>{c['heuristic_score']}</td>"
            f"<td>{html.escape(c['regime'])}</td>"
            f"<td>{html.escape(str(c['data_quality_ok_pct']))}</td>"
            f"<td>{html.escape(c['recommended_check'])}</td>"
            f"</tr>"
        )

    page = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"/><title>DrillGuard Dashboard</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:20px;color:#122}}
.banner{{background:#fff3cd;border:1px solid #856404;padding:12px}}
table{{border-collapse:collapse;width:100%;margin-top:12px}}
th,td{{border:1px solid #ccc;padding:6px;font-size:13px}}
th{{background:#f4f4f4}}
</style>
<script>
function filterClass(){{
  const v=document.getElementById('cls').value;
  document.querySelectorAll('tr[data-class]').forEach(tr=>{{
    tr.style.display = (!v || tr.dataset.class===v) ? '' : 'none';
  }});
}}
</script>
</head><body>
<div class="banner"><strong>Только рекомендация.</strong> Нет управления буровой / АСУ ТП / SCADA.
 heuristic_score — не вероятность. origin={html.escape(data_origin)} source={html.escape(source_id)}</div>
<h1>DrillGuard OS Dashboard</h1>
{img_tag}
<p>Filter class: <select id="cls" onchange="filterClass()"><option value="">(all)</option>{class_opts}</select></p>
<table>
<thead><tr><th>Start</th><th>Class</th><th>Score</th><th>Regime</th><th>Quality%</th><th>Check</th></tr></thead>
<tbody>{''.join(rows) if rows else '<tr><td colspan="6">No cards</td></tr>'}</tbody>
</table>
<pre>{html.escape(str(report['summary']))}</pre>
</body></html>"""
    path = Path(output_html)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8")
    write_html(report, path.with_name(path.stem + "_cards.html"))
    return path


def run_from_csv(csv_path: str, output_html: str = "artifacts/dashboard.html", origin: str = "field_unvalidated") -> Path:
    df = load_csv(csv_path)
    out = detect(df)
    return render_dashboard(out, data_origin=origin, source_id=Path(csv_path).name, output_html=output_html)


def run_demo(scenario: str = "packoff", output_html: str = "artifacts/dashboard.html") -> Path:
    from .synthetic import make_scenario

    df, _ = make_scenario(scenario, seed=0)
    out = detect(df)
    return render_dashboard(
        out,
        data_origin="synthetic",
        source_id=f"synthetic:{scenario}",
        output_html=output_html,
    )
