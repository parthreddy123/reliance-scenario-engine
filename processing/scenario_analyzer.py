"""LLM pipeline: reads articles, scores scenarios, aggregates weights."""

import json
import math
import logging
import time
from datetime import datetime

from config.secrets_helper import get_secret
from database import manager as db
from database.schema import init_db

logger = logging.getLogger(__name__)

SCENARIO_IDS = [
    "quick_ceasefire",
    "prolonged_standoff",
    "regional_conflagration",
    "regime_collapse",
    "negotiated_settlement",
]

SYSTEM_PROMPT = """You are a geopolitical risk analyst specializing in Iran/Middle East and its impact on Indian oil markets. Given a news article, assess how it relates to each of 5 predefined scenarios. Return a JSON object."""

USER_PROMPT_TEMPLATE = """Article: "{title}"
Summary: "{summary}"
Source: {source} | Date: {date}

Scenarios:
1. quick_ceasefire: Ceasefire in 2-4 weeks, Hormuz reopens
2. prolonged_standoff: Hormuz restricted 2-4 months, sporadic attacks
3. regional_conflagration: Full escalation, Hormuz mined, Gulf infrastructure hit
4. regime_collapse: IRGC fractures, Iran in civil instability, Hormuz eventually reopens
5. negotiated_settlement: Diplomatic breakthrough, sanctions eased

For each scenario, return signal_strength (-1.0 to +1.0, where positive = supports this scenario, negative = weakens it, 0 = irrelevant) and a one-line reasoning.

Return ONLY valid JSON:
{{
  "quick_ceasefire": {{"signal": 0.0, "reason": "..."}},
  "prolonged_standoff": {{"signal": 0.0, "reason": "..."}},
  "regional_conflagration": {{"signal": 0.0, "reason": "..."}},
  "regime_collapse": {{"signal": 0.0, "reason": "..."}},
  "negotiated_settlement": {{"signal": 0.0, "reason": "..."}}
}}"""


def _get_client():
    """Get Anthropic client."""
    import anthropic
    api_key = get_secret("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your_key_here":
        raise ValueError("ANTHROPIC_API_KEY not configured in .env")
    return anthropic.Anthropic(api_key=api_key)


def analyze_article(client, article):
    """Call Claude Haiku to extract scenario signals for one article.

    Returns dict: {scenario_id: {"signal": float, "reason": str}} or None on failure.
    """
    prompt = USER_PROMPT_TEMPLATE.format(
        title=article["title"],
        summary=(article["summary"] or "")[:500],
        source=article["source"],
        date=article["published_date"][:10] if article["published_date"] else "unknown",
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()

        # Extract JSON from response (handle markdown code blocks)
        if "```" in text:
            start = text.index("{")
            end = text.rindex("}") + 1
            text = text[start:end]

        data = json.loads(text)

        # Validate and normalize
        signals = {}
        for sid in SCENARIO_IDS:
            if sid in data:
                sig = float(data[sid].get("signal", 0))
                sig = max(-1.0, min(1.0, sig))  # Clamp
                reason = str(data[sid].get("reason", ""))[:200]
                signals[sid] = {"signal": sig, "reason": reason}
            else:
                signals[sid] = {"signal": 0.0, "reason": "Not assessed"}

        return signals

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error for article {article['id']}: {e}")
        return None
    except Exception as e:
        logger.error(f"LLM error for article {article['id']}: {e}")
        return None


def extract_signals(batch_size=50):
    """Process unanalyzed articles through the LLM. Returns count processed."""
    init_db()
    articles = db.get_unprocessed_articles(limit=batch_size)
    if not articles:
        logger.info("No unprocessed articles")
        return 0

    client = _get_client()
    processed = 0

    for article in articles:
        logger.info(f"Analyzing: {article['title'][:60]}...")
        signals = analyze_article(client, article)
        if signals:
            db.insert_signals(article["id"], signals)
            db.mark_article_processed(article["id"])
            processed += 1
        time.sleep(0.5)  # Rate limit courtesy

    logger.info(f"Processed {processed}/{len(articles)} articles")
    return processed


def compute_weights(horizon="3m"):
    """Aggregate signals into scenario probabilities using time-decay weighting.

    Args:
        horizon: '3m' or '6m'

    Returns:
        dict: {scenario_id: probability}
    """
    init_db()
    signals = db.get_all_signals_with_dates()
    if not signals:
        # Return uniform weights if no data
        uniform = 1.0 / len(SCENARIO_IDS)
        weights = {sid: uniform for sid in SCENARIO_IDS}
        db.upsert_weights(horizon, weights, 0)
        return weights

    now = datetime.now()

    # Time decay parameters
    if horizon == "3m":
        half_life_days = 7
    else:
        half_life_days = 21
    decay_lambda = math.log(2) / half_life_days

    # Accumulate weighted scores per scenario
    weighted_scores = {sid: 0.0 for sid in SCENARIO_IDS}
    total_decay = {sid: 0.0 for sid in SCENARIO_IDS}
    article_dates = set()

    for sig in signals:
        scenario_id = sig["scenario_id"]
        if scenario_id not in weighted_scores:
            continue

        try:
            pub_date = datetime.fromisoformat(sig["published_date"])
        except (ValueError, TypeError):
            continue

        days_old = max(0, (now - pub_date).total_seconds() / 86400)
        decay_weight = math.exp(-decay_lambda * days_old)

        weighted_scores[scenario_id] += sig["signal_strength"] * decay_weight
        total_decay[scenario_id] += abs(decay_weight)
        article_dates.add(sig["published_date"][:10])

    # Normalize: weighted average score per scenario
    avg_scores = {}
    for sid in SCENARIO_IDS:
        if total_decay[sid] > 0:
            avg_scores[sid] = weighted_scores[sid] / total_decay[sid]
        else:
            avg_scores[sid] = 0.0

    # Softmax to convert scores to probabilities
    # Shift for numerical stability
    max_score = max(avg_scores.values()) if avg_scores else 0
    exp_scores = {}
    for sid in SCENARIO_IDS:
        exp_scores[sid] = math.exp(avg_scores[sid] - max_score)

    total_exp = sum(exp_scores.values())
    weights = {}
    for sid in SCENARIO_IDS:
        weights[sid] = exp_scores[sid] / total_exp if total_exp > 0 else 1.0 / len(SCENARIO_IDS)

    article_count = len(article_dates)
    db.upsert_weights(horizon, weights, article_count)

    logger.info(f"Computed {horizon} weights from {article_count} article-days: {weights}")
    return weights


def run_full_pipeline(batch_size=50):
    """Run the complete pipeline: extract signals then compute weights."""
    processed = extract_signals(batch_size)
    weights_3m = compute_weights("3m")
    weights_6m = compute_weights("6m")
    return {
        "articles_processed": processed,
        "weights_3m": weights_3m,
        "weights_6m": weights_6m,
    }


def run():
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = run_full_pipeline()
    print(f"\nProcessed {result['articles_processed']} articles")
    print(f"\n3-month weights:")
    for sid, prob in result["weights_3m"].items():
        print(f"  {sid}: {prob:.1%}")
    print(f"\n6-month weights:")
    for sid, prob in result["weights_6m"].items():
        print(f"  {sid}: {prob:.1%}")


if __name__ == "__main__":
    run()
