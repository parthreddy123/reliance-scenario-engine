"""Shared scenario page renderer — used by both 3m and 6m pages."""

import os
import yaml
import streamlit as st
from datetime import datetime

from database import manager as db
from components.theme import (
    GLOBAL_CSS, BG_CARD, BG_ELEVATED, BORDER_SUBTLE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, SCENARIO_COLORS,
)

SCENARIOS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "scenarios.yaml")


def _load_scenarios():
    """Load scenario definitions from YAML."""
    with open(SCENARIOS_PATH, "r") as f:
        config = yaml.safe_load(f)
    return config.get("scenarios", {})


def _compute_expected_values(scenarios, weights, horizon):
    """Compute risk-weighted expected values for oil price, GRM, stock impact."""
    ev = {"oil_price": 0, "grm": 0, "stock": 0}
    ranges = {"oil_price": [999, -999], "grm": [999, -999], "stock": [999, -999]}

    for sid, sdef in scenarios.items():
        prob = weights.get(sid, {}).get("probability", 0.2)
        impacts = sdef.get("impacts", {}).get(horizon, {})

        for metric in ("oil_price", "grm", "stock"):
            vals = impacts.get(metric, {"low": 0, "mid": 0, "high": 0})
            ev[metric] += prob * vals["mid"]
            ranges[metric][0] = min(ranges[metric][0], vals["low"])
            ranges[metric][1] = max(ranges[metric][1], vals["high"])

    return ev, ranges


def render_scenario_page(horizon):
    """Render the full scenario page for a given horizon ('3m' or '6m')."""
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    horizon_label = "3-Month" if horizon == "3m" else "6-Month"
    st.title(f"Reliance Geopolitical Scenario Engine  —  {horizon_label} Horizon")

    scenarios = _load_scenarios()
    weights = db.get_latest_weights(horizon)

    # If no weights computed yet, use uniform
    if not weights:
        uniform = 1.0 / len(scenarios)
        weights = {sid: {"probability": uniform, "confidence": "low", "article_count": 0}
                   for sid in scenarios}

    ev, ranges = _compute_expected_values(scenarios, weights, horizon)

    # ── Risk-Weighted Output (Top KPIs) ──────────────────────────────
    st.markdown("## Risk-Weighted Output")
    k1, k2, k3 = st.columns(3)

    with k1:
        st.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-title">Expected Oil Price</div>
            <div class="kpi-value">${ev['oil_price']:.1f}/bbl</div>
            <div class="kpi-range">range: ${ranges['oil_price'][0]:.0f} – ${ranges['oil_price'][1]:.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with k2:
        st.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-title">Expected GRM</div>
            <div class="kpi-value">${ev['grm']:.1f}/bbl</div>
            <div class="kpi-range">range: ${ranges['grm'][0]:.0f} – ${ranges['grm'][1]:.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with k3:
        stock_sign = "+" if ev["stock"] > 0 else ""
        st.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-title">Expected Stock Impact</div>
            <div class="kpi-value">{stock_sign}{ev['stock']:.1f}%</div>
            <div class="kpi-range">range: {ranges['stock'][0]:+.0f}% to {ranges['stock'][1]:+.0f}%</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Scenario Cards ────────────────────────────────────────────────
    # Sort by probability descending
    sorted_scenarios = sorted(
        scenarios.items(),
        key=lambda x: weights.get(x[0], {}).get("probability", 0),
        reverse=True,
    )

    for sid, sdef in sorted_scenarios:
        w = weights.get(sid, {"probability": 0.2, "confidence": "low", "article_count": 0})
        prob = w["probability"]
        confidence = w.get("confidence", "low")
        color = sdef.get("color", "#666")
        impacts = sdef.get("impacts", {}).get(horizon, {})

        # Probability bar (width proportional to probability)
        bar_width = max(5, int(prob * 100))
        bar_blocks = int(prob * 20)
        bar_str = "\u2588" * bar_blocks + "\u2591" * (20 - bar_blocks)

        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, {BG_CARD} 0%, {BG_ELEVATED} 100%);
            border: 1px solid {BORDER_SUBTLE};
            border-left: 4px solid {color};
            border-radius: 12px;
            padding: 1.2rem;
            margin-bottom: 0.8rem;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem;">
                <span style="color: {color}; font-weight: 700; font-size: 1.1rem;">
                    {sdef['name']}
                </span>
                <span style="color: {TEXT_PRIMARY}; font-weight: 800; font-size: 1.2rem;">
                    {prob:.0%}
                </span>
            </div>
            <div style="
                background: rgba(255,255,255,0.04);
                border-radius: 6px;
                height: 8px;
                overflow: hidden;
                margin-bottom: 0.8rem;
            ">
                <div style="
                    background: {color};
                    width: {bar_width}%;
                    height: 100%;
                    border-radius: 6px;
                    transition: width 0.5s ease;
                "></div>
            </div>
            <div style="color: {TEXT_MUTED}; font-size: 0.82rem; margin-bottom: 0.8rem;">
                {sdef['description']}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Two columns: Key Articles (left) | Assessment (right)
        col_left, col_right = st.columns([1, 1])

        with col_left:
            articles = db.get_articles_for_scenario(sid, horizon, limit=6)
            if articles:
                for art in articles[:4]:
                    sig = art["signal_strength"]
                    sig_color = "#10B981" if sig > 0.5 else ("#F59E0B" if sig > 0.2 else TEXT_MUTED)
                    st.markdown(f"""
                    <div style="padding: 0.3rem 0; border-bottom: 1px solid rgba(255,255,255,0.04);">
                        <span style="color: {sig_color}; font-size: 0.7rem; font-weight: 600;">
                            [{sig:+.2f}]
                        </span>
                        <span style="color: {TEXT_SECONDARY}; font-size: 0.82rem;">
                            {art['source']}:
                        </span>
                        <span style="color: {TEXT_PRIMARY}; font-size: 0.82rem;">
                            {art['title'][:80]}
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
                remaining = len(articles) - 4
                if remaining > 0:
                    st.markdown(f"<div style='color: {TEXT_MUTED}; font-size: 0.75rem; padding-top: 0.3rem;'>"
                                f"+{remaining} more articles</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='color: {TEXT_MUTED}; font-size: 0.82rem;'>"
                            f"No supporting articles yet</div>", unsafe_allow_html=True)

        with col_right:
            # Impact values
            oil = impacts.get("oil_price", {})
            grm = impacts.get("grm", {})
            stock = impacts.get("stock", {})

            st.markdown(f"""
            <div style="
                background: rgba(255,255,255,0.02);
                border-radius: 8px;
                padding: 0.8rem;
            ">
                <div style="color: {TEXT_SECONDARY}; font-size: 0.82rem; margin-bottom: 0.6rem;">
                    <strong style="color: {TEXT_PRIMARY};">If this scenario:</strong>
                    Oil ${oil.get('mid', 0)}/bbl &nbsp;|&nbsp;
                    GRM ${grm.get('mid', 0)}/bbl &nbsp;|&nbsp;
                    Stock {stock.get('mid', 0):+}%
                </div>
                <div style="color: {TEXT_MUTED}; font-size: 0.72rem;">
                    Oil range: ${oil.get('low', 0)} – ${oil.get('high', 0)} &nbsp;|&nbsp;
                    GRM range: ${grm.get('low', 0)} – ${grm.get('high', 0)} &nbsp;|&nbsp;
                    Stock range: {stock.get('low', 0):+}% to {stock.get('high', 0):+}%
                </div>
                <div style="color: {TEXT_MUTED}; font-size: 0.72rem; margin-top: 0.4rem;">
                    Confidence: {confidence} &nbsp;|&nbsp; {w.get('article_count', 0)} articles
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("")  # Spacer

    # ── Footer ────────────────────────────────────────────────────────
    st.markdown("---")
    total = db.get_total_article_count()
    last_scrape = db.get_last_scrape()
    last_time = last_scrape["scraped_at"][:16] if last_scrape else "Never"
    weight_meta = list(weights.values())[0] if weights else {}
    computed_at = weight_meta.get("computed_at", "Never")

    st.markdown(f"""
    <div style="color: {TEXT_MUTED}; font-size: 0.75rem; text-align: center;">
        Last scraped: {last_time} &nbsp;|&nbsp;
        Weights computed: {computed_at} &nbsp;|&nbsp;
        {total} total articles &nbsp;|&nbsp;
        Probabilities sum: {sum(w.get('probability', 0) for w in weights.values()):.2f}
    </div>
    """, unsafe_allow_html=True)
