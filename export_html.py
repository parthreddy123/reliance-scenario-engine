"""Export current scenario engine state as a standalone HTML file."""

import os
import sys
import yaml
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from database.schema import init_db
from database import manager as db


def load_scenarios():
    path = os.path.join(os.path.dirname(__file__), "config", "scenarios.yaml")
    with open(path) as f:
        return yaml.safe_load(f).get("scenarios", {})


def compute_ev(scenarios, weights, horizon):
    ev = {"oil_price": 0, "grm": 0, "stock": 0}
    ranges = {"oil_price": [999, -999], "grm": [999, -999], "stock": [999, -999]}
    for sid, sdef in scenarios.items():
        prob = weights.get(sid, {}).get("probability", 0.2)
        impacts = sdef.get("impacts", {}).get(horizon, {})
        for m in ("oil_price", "grm", "stock"):
            vals = impacts.get(m, {"low": 0, "mid": 0, "high": 0})
            ev[m] += prob * vals["mid"]
            ranges[m][0] = min(ranges[m][0], vals["low"])
            ranges[m][1] = max(ranges[m][1], vals["high"])
    return ev, ranges


def render_horizon(scenarios, horizon, weights):
    label = "3-Month" if horizon == "3m" else "6-Month"
    ev, ranges = compute_ev(scenarios, weights, horizon)

    sorted_scenarios = sorted(
        scenarios.items(),
        key=lambda x: weights.get(x[0], {}).get("probability", 0),
        reverse=True,
    )

    stock_sign = "+" if ev["stock"] > 0 else ""

    cards_html = ""
    for sid, sdef in sorted_scenarios:
        w = weights.get(sid, {"probability": 0.2, "confidence": "low", "article_count": 0})
        prob = w["probability"]
        confidence = w.get("confidence", "low")
        color = sdef.get("color", "#666")
        impacts = sdef.get("impacts", {}).get(horizon, {})
        oil = impacts.get("oil_price", {})
        grm = impacts.get("grm", {})
        stock = impacts.get("stock", {})
        bar_width = max(5, int(prob * 100))

        articles = db.get_articles_for_scenario(sid, horizon, limit=6)
        articles_html = ""
        for art in articles[:4]:
            sig = art["signal_strength"]
            sig_color = "#10B981" if sig > 0.5 else ("#F59E0B" if sig > 0.2 else "#6B7280")
            title_text = art["title"][:85]
            articles_html += f"""
            <div class="article-row">
                <span class="signal" style="color:{sig_color}">[{sig:+.2f}]</span>
                <span class="art-source">{art['source']}:</span>
                <span class="art-title">{title_text}</span>
            </div>"""

        remaining = len(articles) - 4
        if remaining > 0:
            articles_html += f'<div class="more-articles">+{remaining} more articles</div>'
        if not articles:
            articles_html = '<div class="more-articles">No supporting articles yet</div>'

        stock_mid_sign = "+" if stock.get("mid", 0) > 0 else ""
        stock_lo_sign = "+" if stock.get("low", 0) > 0 else ""
        stock_hi_sign = "+" if stock.get("high", 0) > 0 else ""

        cards_html += f"""
        <div class="scenario-card" style="border-left: 4px solid {color};">
            <div class="scenario-header">
                <span class="scenario-name" style="color:{color};">{sdef['name']}</span>
                <span class="scenario-prob">{prob:.0%}</span>
            </div>
            <div class="prob-bar-track">
                <div class="prob-bar-fill" style="width:{bar_width}%; background:{color};"></div>
            </div>
            <div class="scenario-desc">{sdef['description']}</div>
            <div class="scenario-body">
                <div class="scenario-articles">
                    {articles_html}
                </div>
                <div class="scenario-impact">
                    <div class="impact-main">
                        <strong>If this scenario:</strong>
                        Oil ${oil.get('mid',0)}/bbl &nbsp;|&nbsp;
                        GRM ${grm.get('mid',0)}/bbl &nbsp;|&nbsp;
                        Stock {stock_mid_sign}{stock.get('mid',0)}%
                    </div>
                    <div class="impact-range">
                        Oil: ${oil.get('low',0)} – ${oil.get('high',0)} &nbsp;|&nbsp;
                        GRM: ${grm.get('low',0)} – ${grm.get('high',0)} &nbsp;|&nbsp;
                        Stock: {stock_lo_sign}{stock.get('low',0)}% to {stock_hi_sign}{stock.get('high',0)}%
                    </div>
                    <div class="impact-conf">
                        Confidence: {confidence} &nbsp;|&nbsp; {w.get('article_count',0)} articles
                    </div>
                </div>
            </div>
        </div>"""

    return f"""
    <div class="horizon-section" id="horizon-{horizon}">
        <h2 class="horizon-title">{label} Horizon</h2>

        <div class="kpi-row">
            <div class="kpi-box">
                <div class="kpi-label">EXPECTED OIL PRICE</div>
                <div class="kpi-value">${ev['oil_price']:.1f}/bbl</div>
                <div class="kpi-range">range: ${ranges['oil_price'][0]:.0f} – ${ranges['oil_price'][1]:.0f}</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-label">EXPECTED GRM</div>
                <div class="kpi-value">${ev['grm']:.1f}/bbl</div>
                <div class="kpi-range">range: ${ranges['grm'][0]:.0f} – ${ranges['grm'][1]:.0f}</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-label">EXPECTED STOCK IMPACT</div>
                <div class="kpi-value">{stock_sign}{ev['stock']:.1f}%</div>
                <div class="kpi-range">range: {ranges['stock'][0]:+.0f}% to {ranges['stock'][1]:+.0f}%</div>
            </div>
        </div>

        {cards_html}
    </div>"""


def generate_html():
    init_db()
    scenarios = load_scenarios()
    weights_3m = db.get_latest_weights("3m")
    weights_6m = db.get_latest_weights("6m")

    if not weights_3m:
        u = 1.0 / len(scenarios)
        weights_3m = {s: {"probability": u, "confidence": "low", "article_count": 0} for s in scenarios}
    if not weights_6m:
        u = 1.0 / len(scenarios)
        weights_6m = {s: {"probability": u, "confidence": "low", "article_count": 0} for s in scenarios}

    total_articles = db.get_total_article_count()
    last_scrape = db.get_last_scrape()
    last_time = last_scrape["scraped_at"][:16] if last_scrape else "Never"
    w_meta = list(weights_3m.values())[0] if weights_3m else {}
    computed_at = w_meta.get("computed_at", "Never")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    horizon_3m = render_horizon(scenarios, "3m", weights_3m)
    horizon_6m = render_horizon(scenarios, "6m", weights_6m)

    prob_sum_3m = sum(w.get("probability", 0) for w in weights_3m.values())
    prob_sum_6m = sum(w.get("probability", 0) for w in weights_6m.values())

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Reliance Geopolitical Scenario Engine</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background: #0E1117;
    color: #F9FAFB;
    line-height: 1.5;
    padding: 0;
  }}

  .page-header {{
    background: linear-gradient(135deg, #0A0E1A 0%, #111827 60%, #1a1040 100%);
    border-bottom: 1px solid rgba(0,212,170,0.2);
    padding: 2rem 3rem;
    text-align: center;
  }}
  .page-header h1 {{
    font-size: 1.8rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: #F9FAFB;
    margin-bottom: 0.3rem;
  }}
  .page-header .subtitle {{
    color: #6B7280;
    font-size: 0.85rem;
  }}

  /* Tab nav */
  .tab-nav {{
    display: flex;
    justify-content: center;
    gap: 0;
    background: #111827;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    position: sticky;
    top: 0;
    z-index: 100;
  }}
  .tab-btn {{
    padding: 0.8rem 2rem;
    font-size: 0.9rem;
    font-weight: 600;
    color: #6B7280;
    background: none;
    border: none;
    border-bottom: 3px solid transparent;
    cursor: pointer;
    transition: all 0.2s;
  }}
  .tab-btn:hover {{ color: #9CA3AF; }}
  .tab-btn.active {{
    color: #00D4AA;
    border-bottom-color: #00D4AA;
  }}

  .container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 1.5rem 2rem;
  }}

  .horizon-section {{ display: none; }}
  .horizon-section.active {{ display: block; }}

  .horizon-title {{
    font-size: 1.3rem;
    font-weight: 700;
    color: #E5E7EB;
    border-bottom: 2px solid rgba(0,212,170,0.3);
    padding-bottom: 0.4rem;
    margin-bottom: 1.2rem;
  }}

  /* KPI row */
  .kpi-row {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin-bottom: 2rem;
  }}
  .kpi-box {{
    background: linear-gradient(135deg, #1A1F2E 0%, #151A28 100%);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    text-align: center;
  }}
  .kpi-box:hover {{
    border-color: rgba(0,212,170,0.2);
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
  }}
  .kpi-label {{
    color: #9CA3AF;
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-weight: 600;
    margin-bottom: 0.3rem;
  }}
  .kpi-value {{
    color: #F9FAFB;
    font-size: 1.7rem;
    font-weight: 800;
    font-variant-numeric: tabular-nums;
  }}
  .kpi-range {{
    color: #6B7280;
    font-size: 0.72rem;
    margin-top: 0.2rem;
  }}

  /* Scenario cards */
  .scenario-card {{
    background: linear-gradient(135deg, #1A1F2E 0%, #151A28 100%);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    padding: 1.3rem 1.5rem;
    margin-bottom: 1rem;
    transition: border-color 0.2s;
  }}
  .scenario-card:hover {{
    border-color: rgba(255,255,255,0.12);
  }}
  .scenario-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }}
  .scenario-name {{
    font-weight: 700;
    font-size: 1.1rem;
  }}
  .scenario-prob {{
    font-weight: 800;
    font-size: 1.25rem;
    color: #F9FAFB;
  }}
  .prob-bar-track {{
    background: rgba(255,255,255,0.04);
    border-radius: 6px;
    height: 8px;
    overflow: hidden;
    margin-bottom: 0.7rem;
  }}
  .prob-bar-fill {{
    height: 100%;
    border-radius: 6px;
    transition: width 0.5s ease;
  }}
  .scenario-desc {{
    color: #6B7280;
    font-size: 0.82rem;
    margin-bottom: 0.8rem;
  }}
  .scenario-body {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }}

  /* Articles column */
  .scenario-articles {{
    min-height: 60px;
  }}
  .article-row {{
    padding: 0.3rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    font-size: 0.82rem;
    line-height: 1.4;
  }}
  .signal {{
    font-size: 0.7rem;
    font-weight: 600;
    font-family: 'SF Mono', 'Fira Code', monospace;
  }}
  .art-source {{
    color: #9CA3AF;
  }}
  .art-title {{
    color: #E5E7EB;
  }}
  .more-articles {{
    color: #6B7280;
    font-size: 0.75rem;
    padding-top: 0.3rem;
  }}

  /* Impact column */
  .scenario-impact {{
    background: rgba(255,255,255,0.02);
    border-radius: 8px;
    padding: 0.8rem;
  }}
  .impact-main {{
    color: #9CA3AF;
    font-size: 0.82rem;
    margin-bottom: 0.5rem;
  }}
  .impact-main strong {{
    color: #F9FAFB;
  }}
  .impact-range {{
    color: #6B7280;
    font-size: 0.72rem;
  }}
  .impact-conf {{
    color: #6B7280;
    font-size: 0.72rem;
    margin-top: 0.4rem;
  }}

  /* Footer */
  .page-footer {{
    text-align: center;
    color: #4B5563;
    font-size: 0.72rem;
    padding: 1.5rem 2rem;
    border-top: 1px solid rgba(255,255,255,0.04);
    margin-top: 2rem;
  }}
  .page-footer span {{ color: #6B7280; }}

  /* Responsive */
  @media (max-width: 768px) {{
    .page-header {{ padding: 1.2rem 1rem; }}
    .page-header h1 {{ font-size: 1.3rem; }}
    .container {{ padding: 1rem; }}
    .kpi-row {{ grid-template-columns: 1fr; gap: 0.6rem; }}
    .kpi-value {{ font-size: 1.3rem; }}
    .scenario-body {{ grid-template-columns: 1fr; }}
    .scenario-card {{ padding: 1rem; }}
    .tab-btn {{ padding: 0.6rem 1.2rem; font-size: 0.8rem; }}
  }}
</style>
</head>
<body>

<div class="page-header">
    <h1>Reliance Geopolitical Scenario Engine</h1>
    <div class="subtitle">Iran / Middle East Risk Analysis for Oil &amp; Refining &nbsp;|&nbsp; Generated {now}</div>
</div>

<div class="tab-nav">
    <button class="tab-btn active" onclick="showTab('3m')">3-Month Horizon</button>
    <button class="tab-btn" onclick="showTab('6m')">6-Month Horizon</button>
</div>

<div class="container">
    {horizon_3m.replace('class="horizon-section"', 'class="horizon-section active"')}
    {horizon_6m}
</div>

<div class="page-footer">
    Last scraped: <span>{last_time}</span> &nbsp;|&nbsp;
    Weights computed: <span>{computed_at}</span> &nbsp;|&nbsp;
    <span>{total_articles}</span> articles &nbsp;|&nbsp;
    3M sum: <span>{prob_sum_3m:.2f}</span> &nbsp;|&nbsp;
    6M sum: <span>{prob_sum_6m:.2f}</span>
</div>

<script>
function showTab(horizon) {{
    document.querySelectorAll('.horizon-section').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById('horizon-' + horizon).classList.add('active');
    event.target.classList.add('active');
}}
</script>
</body>
</html>"""

    return html


if __name__ == "__main__":
    out_path = os.path.join(os.path.dirname(__file__), "scenario_report.html")
    html = generate_html()
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Exported to {out_path}")
