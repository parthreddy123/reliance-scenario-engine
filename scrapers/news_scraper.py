"""News scraper — fetches all 14 RSS feeds, deduplicates, stores in DB."""

import os
import logging
import time
import yaml
import feedparser
from datetime import datetime
from email.utils import parsedate_to_datetime

from scrapers.base_scraper import BaseScraper
from database.schema import init_db
from database import manager as db

logger = logging.getLogger(__name__)

FEEDS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "feeds.yaml")


class NewsScraper(BaseScraper):
    """Scrapes RSS feeds for geopolitical/oil/India-Reliance news."""

    def __init__(self):
        super().__init__(name="news", cache_expiry_hours=2, rate_limit_seconds=1)
        self.feeds = self._load_feeds()

    def _load_feeds(self):
        with open(FEEDS_PATH, "r") as f:
            config = yaml.safe_load(f)
        return config.get("feeds", [])

    def _parse_date(self, entry):
        """Extract published date from feed entry."""
        for field in ("published_parsed", "updated_parsed"):
            parsed = entry.get(field)
            if parsed:
                try:
                    return datetime(*parsed[:6]).isoformat()
                except Exception:
                    pass
        for field in ("published", "updated"):
            raw = entry.get(field)
            if raw:
                try:
                    return parsedate_to_datetime(raw).isoformat()
                except Exception:
                    pass
        return datetime.now().isoformat()

    def _get_summary(self, entry):
        """Extract summary text, stripping HTML tags."""
        summary = entry.get("summary", "") or entry.get("description", "") or ""
        # Simple HTML tag stripping
        import re
        summary = re.sub(r"<[^>]+>", "", summary)
        return summary[:1000]  # Truncate to 1000 chars

    def scrape(self):
        """Fetch all feeds and store new articles. Returns count of new articles."""
        init_db()
        total_added = 0
        feed_count = 0
        start = time.time()

        for feed_config in self.feeds:
            url = feed_config["url"]
            category = feed_config["category"]
            name = feed_config["name"]

            logger.info(f"Fetching feed: {name}")
            try:
                parsed = self.fetch_rss(url)
                if not parsed or not parsed.entries:
                    logger.warning(f"No entries from {name}")
                    continue

                feed_count += 1
                for entry in parsed.entries:
                    article_url = entry.get("link", "")
                    if not article_url:
                        continue

                    title = entry.get("title", "").strip()
                    if not title:
                        continue

                    summary = self._get_summary(entry)
                    published = self._parse_date(entry)

                    inserted = db.insert_article(
                        url=article_url,
                        title=title,
                        summary=summary,
                        source=name,
                        feed_category=category,
                        published_date=published,
                    )
                    if inserted:
                        total_added += 1

            except Exception as e:
                logger.error(f"Error fetching {name}: {e}")
                continue

        duration = time.time() - start
        db.insert_scrape_log(
            feed_count=feed_count,
            articles_added=total_added,
            articles_analyzed=0,
            duration_seconds=round(duration, 1),
        )

        logger.info(f"Scrape complete: {feed_count} feeds, {total_added} new articles in {duration:.1f}s")
        return total_added


def run():
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    scraper = NewsScraper()
    count = scraper.scrape()
    print(f"Done. {count} new articles added. Total: {db.get_total_article_count()}")


if __name__ == "__main__":
    run()
