"""Reliance Geopolitical Scenario Engine — Streamlit entry point."""

import sys
import os
import time
import logging
import streamlit as st

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from database.schema import init_db
from database import manager as db
from components.theme import GLOBAL_CSS, TEXT_MUTED, TEAL, BG_CARD
from components.scenario_page import render_scenario_page

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

st.set_page_config(
    page_title="Reliance Geopolitical Scenario Engine",
    page_icon="\u26A0\uFE0F",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize DB on first run
init_db()

# ── Sidebar ───────────────────────────────────────────────────────────
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"""
    <div style="padding: 0.5rem 0 1rem 0;">
        <h2 style="color: {TEAL}; font-size: 1.1rem; margin: 0; border: none; padding: 0;">
            Reliance Scenario Engine
        </h2>
        <p style="color: {TEXT_MUTED}; font-size: 0.75rem; margin-top: 0.3rem;">
            Geopolitical Risk Analysis for Oil & Refining
        </p>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Horizon",
        ["3-Month Scenarios", "6-Month Scenarios"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Refresh button
    if st.button("Refresh Data", type="primary", use_container_width=True):
        with st.status("Running pipeline...", expanded=True) as status:
            st.write("Scraping RSS feeds...")
            try:
                from scrapers.news_scraper import NewsScraper
                scraper = NewsScraper()
                new_articles = scraper.scrape()
                st.write(f"Added {new_articles} new articles")
            except Exception as e:
                st.error(f"Scrape error: {e}")
                new_articles = 0

            st.write("Analyzing with LLM...")
            try:
                from processing.scenario_analyzer import extract_signals, compute_weights
                processed = extract_signals(batch_size=20)
                st.write(f"Analyzed {processed} articles")
            except ValueError as e:
                st.warning(f"LLM skipped: {e}")
                processed = 0
            except Exception as e:
                st.error(f"Analysis error: {e}")
                processed = 0

            st.write("Computing scenario weights...")
            try:
                from processing.scenario_analyzer import compute_weights
                w3 = compute_weights("3m")
                w6 = compute_weights("6m")
                st.write("Weights updated for both horizons")
            except Exception as e:
                st.error(f"Weight computation error: {e}")

            status.update(label="Pipeline complete!", state="complete")
        st.rerun()

    # Scrape-only button (no LLM needed)
    if st.button("Scrape Only (no LLM)", use_container_width=True):
        with st.spinner("Scraping feeds..."):
            try:
                from scrapers.news_scraper import NewsScraper
                scraper = NewsScraper()
                new_articles = scraper.scrape()
                st.success(f"Added {new_articles} articles")
            except Exception as e:
                st.error(f"Error: {e}")
        st.rerun()

    # Recompute weights only
    if st.button("Recompute Weights", use_container_width=True):
        with st.spinner("Computing..."):
            try:
                from processing.scenario_analyzer import compute_weights
                compute_weights("3m")
                compute_weights("6m")
                st.success("Weights updated")
            except Exception as e:
                st.error(f"Error: {e}")
        st.rerun()

    st.markdown("---")

    # Stats
    total = db.get_total_article_count()
    last = db.get_last_scrape()
    st.markdown(f"""
    <div style="color: {TEXT_MUTED}; font-size: 0.75rem;">
        <strong>Articles:</strong> {total}<br>
        <strong>Last scrape:</strong> {last['scraped_at'][:16] if last else 'Never'}<br>
        <strong>Last added:</strong> {last['articles_added'] if last else 0}
    </div>
    """, unsafe_allow_html=True)

# ── Main Content ──────────────────────────────────────────────────────
if page == "3-Month Scenarios":
    render_scenario_page("3m")
else:
    render_scenario_page("6m")
