"""CRUD operations for the scenario engine database."""

import logging
from datetime import datetime
from database.schema import get_connection

logger = logging.getLogger(__name__)


# ── Articles ──────────────────────────────────────────────────────────

def insert_article(url, title, summary, source, feed_category, published_date):
    """Insert an article, ignoring duplicates. Returns True if inserted."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR IGNORE INTO articles
               (url, title, summary, source, feed_category, published_date, scraped_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (url, title, summary, source, feed_category, published_date,
             datetime.now().isoformat())
        )
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def get_unprocessed_articles(limit=50):
    """Get articles not yet analyzed by the LLM."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT id, url, title, summary, source, feed_category, published_date
               FROM articles WHERE llm_processed = 0
               ORDER BY published_date DESC LIMIT ?""",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def mark_article_processed(article_id):
    """Mark an article as LLM-processed."""
    conn = get_connection()
    try:
        conn.execute("UPDATE articles SET llm_processed = 1 WHERE id = ?", (article_id,))
        conn.commit()
    finally:
        conn.close()


def get_total_article_count():
    """Get total number of articles in the database."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT COUNT(*) as cnt FROM articles").fetchone()
        return row["cnt"]
    finally:
        conn.close()


def get_articles_for_scenario(scenario_id, horizon, limit=10):
    """Get top articles supporting a scenario, ordered by signal strength."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT a.title, a.source, a.published_date, a.url,
                      s.signal_strength, s.reasoning
               FROM article_signals s
               JOIN articles a ON a.id = s.article_id
               WHERE s.scenario_id = ? AND s.signal_strength > 0.1
               ORDER BY s.signal_strength DESC
               LIMIT ?""",
            (scenario_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Article Signals ───────────────────────────────────────────────────

def insert_signals(article_id, signals):
    """Insert LLM signals for an article.

    signals: dict like {scenario_id: {"signal": float, "reason": str}}
    """
    conn = get_connection()
    now = datetime.now().isoformat()
    try:
        for scenario_id, data in signals.items():
            conn.execute(
                """INSERT OR REPLACE INTO article_signals
                   (article_id, scenario_id, signal_strength, reasoning, analyzed_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (article_id, scenario_id, data["signal"], data["reason"], now)
            )
        conn.commit()
    finally:
        conn.close()


def get_all_signals_with_dates():
    """Get all signals joined with article published dates for weight computation."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT s.scenario_id, s.signal_strength, a.published_date
               FROM article_signals s
               JOIN articles a ON a.id = s.article_id
               WHERE a.published_date IS NOT NULL
               ORDER BY a.published_date DESC"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Scenario Weights ──────────────────────────────────────────────────

def upsert_weights(horizon, weights, article_count):
    """Store computed scenario weights.

    weights: dict like {scenario_id: probability}
    """
    conn = get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    if article_count < 10:
        confidence = "low"
    elif article_count <= 30:
        confidence = "medium"
    else:
        confidence = "high"

    try:
        for scenario_id, prob in weights.items():
            conn.execute(
                """INSERT OR REPLACE INTO scenario_weights
                   (computed_at, horizon, scenario_id, probability, confidence, article_count)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (now, horizon, scenario_id, prob, confidence, article_count)
            )
        conn.commit()
    finally:
        conn.close()


def get_latest_weights(horizon):
    """Get the most recent scenario weights for a horizon.

    Returns dict: {scenario_id: {"probability": float, "confidence": str, "article_count": int}}
    """
    conn = get_connection()
    try:
        # Find latest computed_at for this horizon
        row = conn.execute(
            """SELECT computed_at FROM scenario_weights
               WHERE horizon = ? ORDER BY computed_at DESC LIMIT 1""",
            (horizon,)
        ).fetchone()
        if not row:
            return {}

        latest = row["computed_at"]
        rows = conn.execute(
            """SELECT scenario_id, probability, confidence, article_count
               FROM scenario_weights
               WHERE horizon = ? AND computed_at = ?""",
            (horizon, latest)
        ).fetchall()
        result = {}
        for r in rows:
            result[r["scenario_id"]] = {
                "probability": r["probability"],
                "confidence": r["confidence"],
                "article_count": r["article_count"],
                "computed_at": latest,
            }
        return result
    finally:
        conn.close()


# ── Scrape Log ────────────────────────────────────────────────────────

def insert_scrape_log(feed_count, articles_added, articles_analyzed, duration_seconds):
    """Log a scrape run."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO scrape_log
               (scraped_at, feed_count, articles_added, articles_analyzed, duration_seconds)
               VALUES (?, ?, ?, ?, ?)""",
            (datetime.now().isoformat(), feed_count, articles_added, articles_analyzed, duration_seconds)
        )
        conn.commit()
    finally:
        conn.close()


def get_last_scrape():
    """Get the most recent scrape log entry."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM scrape_log ORDER BY scraped_at DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
