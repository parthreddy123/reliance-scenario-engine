"""Database schema — 4 tables for the scenario engine."""

import os
import sqlite3
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "oil_dashboard.db")


def get_connection():
    """Get a SQLite connection with WAL mode."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            title TEXT,
            summary TEXT,
            source TEXT,
            feed_category TEXT,
            published_date TEXT,
            scraped_at TEXT,
            llm_processed INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS article_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER REFERENCES articles(id),
            scenario_id TEXT,
            signal_strength REAL,
            reasoning TEXT,
            analyzed_at TEXT,
            UNIQUE(article_id, scenario_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scenario_weights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            computed_at TEXT,
            horizon TEXT,
            scenario_id TEXT,
            probability REAL,
            confidence TEXT,
            article_count INTEGER,
            UNIQUE(computed_at, horizon, scenario_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scrape_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scraped_at TEXT,
            feed_count INTEGER,
            articles_added INTEGER,
            articles_analyzed INTEGER,
            duration_seconds REAL
        )
    """)

    # Indexes for common queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_processed ON articles(llm_processed)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_article ON article_signals(article_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_scenario ON article_signals(scenario_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_weights_horizon ON scenario_weights(horizon, computed_at)")

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
    print(f"Database created at {DB_PATH}")
