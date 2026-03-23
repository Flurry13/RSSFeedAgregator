"""
Sentiment Analysis Module
=========================

Hybrid approach:
1. Try Claude Haiku API for accurate, context-aware sentiment (if API key configured)
2. Fall back to keyword matching if API unavailable or fails

Haiku processes headlines in batches of 20 for efficiency.
"""

import json
import logging
import os
import re
import time
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
HAIKU_MODEL = "claude-haiku-4-5-20251001"
HAIKU_BATCH_SIZE = 20
HAIKU_ENABLED = bool(ANTHROPIC_API_KEY)

# ---------------------------------------------------------------------------
# Haiku-based sentiment (primary)
# ---------------------------------------------------------------------------

_anthropic_client = None


def _get_client():
    """Lazy-init the Anthropic client."""
    global _anthropic_client
    if _anthropic_client is None:
        try:
            import anthropic
            _anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            logger.info("Anthropic client initialized (model: %s)", HAIKU_MODEL)
        except ImportError:
            logger.warning("anthropic package not installed — falling back to keyword sentiment")
            return None
        except Exception as e:
            logger.warning("Failed to init Anthropic client: %s", e)
            return None
    return _anthropic_client


def _haiku_batch_sentiment(headlines: List[str]) -> Optional[List[Dict[str, Any]]]:
    """
    Send a batch of headlines to Haiku for sentiment analysis.
    Returns list of {"sentiment": str, "sentiment_score": float} or None on failure.
    """
    client = _get_client()
    if not client:
        return None

    numbered = "\n".join(f"{i+1}. {h}" for i, h in enumerate(headlines))

    try:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": f"""Analyze the financial sentiment of each headline. For each, return:
- sentiment: "bullish", "bearish", or "neutral"
- score: confidence from 0.5 (weak) to 1.0 (strong)

Consider context, not just individual words. "Despite losses, company remains optimistic" is neutral/bullish, not bearish.

Headlines:
{numbered}

Respond with ONLY a JSON array, no other text:
[{{"sentiment": "bullish", "score": 0.8}}, ...]"""
            }],
        )

        text = response.content[0].text.strip()
        # Extract JSON array from response
        start = text.find("[")
        end = text.rfind("]") + 1
        if start == -1 or end == 0:
            logger.warning("Haiku response missing JSON array")
            return None

        results = json.loads(text[start:end])

        if len(results) != len(headlines):
            logger.warning("Haiku returned %d results for %d headlines", len(results), len(headlines))
            return None

        return [
            {
                "sentiment": r.get("sentiment", "neutral"),
                "sentiment_score": min(1.0, max(0.5, float(r.get("score", 0.5)))),
            }
            for r in results
        ]

    except Exception as e:
        logger.warning("Haiku sentiment batch failed: %s", e)
        return None


def analyze_sentiment_batch_haiku(headlines: List[str]) -> List[Dict[str, Any]]:
    """
    Analyze sentiment for a list of headlines using Haiku in batches.
    Falls back to keyword analysis for any failures.
    """
    results: List[Optional[Dict[str, Any]]] = [None] * len(headlines)

    # Process in batches
    for start in range(0, len(headlines), HAIKU_BATCH_SIZE):
        batch = headlines[start:start + HAIKU_BATCH_SIZE]
        batch_results = _haiku_batch_sentiment(batch)

        if batch_results:
            for i, result in enumerate(batch_results):
                results[start + i] = result
        else:
            # Batch failed — keyword fallback for this batch
            for i, text in enumerate(batch):
                results[start + i] = analyze_sentiment_keywords(text)

    # Fill any remaining Nones with keyword fallback
    for i, r in enumerate(results):
        if r is None:
            results[i] = analyze_sentiment_keywords(headlines[i] if i < len(headlines) else "")

    return results


# ---------------------------------------------------------------------------
# Keyword-based sentiment (fallback)
# ---------------------------------------------------------------------------

BULLISH_KEYWORDS: List[str] = [
    'surge', 'rally', 'gain', 'soar', 'jump', 'climb', 'spike', 'rebound',
    'recover', 'bounce', 'rise', 'advance', 'uptick', 'upswing',
    'beat', 'outperform', 'exceed', 'record high', 'all-time high', 'strong',
    'boom', 'robust', 'stellar', 'blowout', 'tops estimate', 'above forecast',
    'upgrade', 'buy rating', 'overweight', 'accumulate', 'bullish', 'optimistic',
    'positive', 'favorable', 'confident', 'upbeat',
    'growth', 'profit', 'expansion', 'hiring', 'demand', 'breakthrough',
    'innovation', 'milestone', 'record revenue', 'raises guidance',
    'beats expectations', 'strong earnings', 'dividend hike', 'share buyback',
    'risk-on', 'momentum', 'breakout', 'bid up', 'inflows', 'accumulation',
    'new high', 'green', 'lifts', 'boosts', 'fuels', 'powers',
]

BEARISH_KEYWORDS: List[str] = [
    'crash', 'plunge', 'drop', 'fall', 'decline', 'tumble', 'sink', 'selloff',
    'sell-off', 'collapse', 'slump', 'slide', 'retreat', 'downturn', 'plummet',
    'miss', 'underperform', 'loss', 'weak', 'worst', 'lowest', 'record low',
    'disappointing', 'below estimate', 'misses expectations', 'shortfall',
    'downgrade', 'sell rating', 'underweight', 'bearish', 'pessimistic',
    'cautious', 'negative', 'warning', 'concern', 'risk',
    'layoff', 'restructuring', 'bankruptcy', 'default', 'writedown', 'write-down',
    'impairment', 'shutdown', 'closes', 'cuts jobs', 'lowers guidance',
    'profit warning', 'revenue miss', 'cost overrun', 'debt crisis',
    'risk-off', 'correction', 'bubble', 'contagion', 'panic', 'flight to safety',
    'margin call', 'liquidation', 'outflows', 'capitulation', 'fear',
    'red', 'drags', 'weighs on', 'pressures', 'threatens',
]

_BULLISH_PATTERNS = [re.compile(re.escape(kw.strip()), re.IGNORECASE) for kw in BULLISH_KEYWORDS]
_BEARISH_PATTERNS = [re.compile(re.escape(kw.strip()), re.IGNORECASE) for kw in BEARISH_KEYWORDS]


def analyze_sentiment_keywords(text: str) -> Dict[str, Any]:
    """Keyword-based sentiment fallback."""
    if not text:
        return {"sentiment": "neutral", "sentiment_score": 0.5}

    padded = f" {text.lower()} "
    bullish_hits = sum(1 for p in _BULLISH_PATTERNS if p.search(padded))
    bearish_hits = sum(1 for p in _BEARISH_PATTERNS if p.search(padded))
    total = bullish_hits + bearish_hits

    if total == 0:
        return {"sentiment": "neutral", "sentiment_score": 0.5}
    elif bullish_hits > bearish_hits:
        score = 0.5 + 0.5 * (bullish_hits - bearish_hits) / total
        return {"sentiment": "bullish", "sentiment_score": round(score, 3)}
    elif bearish_hits > bullish_hits:
        score = 0.5 + 0.5 * (bearish_hits - bullish_hits) / total
        return {"sentiment": "bearish", "sentiment_score": round(score, 3)}
    else:
        return {"sentiment": "neutral", "sentiment_score": 0.5}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_sentiment(text: str) -> Dict[str, Any]:
    """
    Analyze sentiment of a single headline.
    Uses Haiku if available, otherwise keyword fallback.
    For batch processing, use analyze_sentiment_batch() instead.
    """
    if HAIKU_ENABLED:
        results = _haiku_batch_sentiment([text])
        if results:
            return results[0]
    return analyze_sentiment_keywords(text)


def analyze_sentiment_batch(headlines: List[str]) -> List[Dict[str, Any]]:
    """
    Analyze sentiment for a list of headlines.
    Uses Haiku batching if API key is set, otherwise keyword fallback.
    """
    if HAIKU_ENABLED:
        logger.info("Using Haiku for sentiment analysis (%d headlines)", len(headlines))
        return analyze_sentiment_batch_haiku(headlines)
    else:
        logger.info("Using keyword fallback for sentiment (%d headlines)", len(headlines))
        return [analyze_sentiment_keywords(h) for h in headlines]
