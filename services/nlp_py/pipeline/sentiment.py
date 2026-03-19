"""
Sentiment Analysis Module
Keyword-based bullish/bearish/neutral classification for financial headlines.
"""

import re
from typing import Dict, Any, List

BULLISH_KEYWORDS: List[str] = [
    # Price movement
    'surge', 'rally', 'gain', 'soar', 'jump', 'climb', 'spike', 'rebound',
    'recover', 'bounce', 'rise', 'advance', 'uptick', 'upswing',
    # Performance
    'beat', 'outperform', 'exceed', 'record high', 'all-time high', 'strong',
    'boom', 'robust', 'stellar', 'blowout', 'tops estimate', 'above forecast',
    # Ratings/actions
    'upgrade', 'buy rating', 'overweight', 'accumulate', 'bullish', 'optimistic',
    'positive', 'favorable', 'confident', 'upbeat',
    # Business
    'growth', 'profit', 'expansion', 'hiring', 'demand', 'breakthrough',
    'innovation', 'milestone', 'record revenue', 'raises guidance',
    'beats expectations', 'strong earnings', 'dividend hike', 'share buyback',
    # Market
    'risk-on', 'momentum', 'breakout', 'bid up', 'inflows', 'accumulation',
    'new high', 'green', 'lifts', 'boosts', 'fuels', 'powers',
]

BEARISH_KEYWORDS: List[str] = [
    # Price movement
    'crash', 'plunge', 'drop', 'fall', 'decline', 'tumble', 'sink', 'selloff',
    'sell-off', 'collapse', 'slump', 'slide', 'retreat', 'downturn', 'plummet',
    # Performance
    'miss', 'underperform', 'loss', 'weak', 'worst', 'lowest', 'record low',
    'disappointing', 'below estimate', 'misses expectations', 'shortfall',
    # Ratings/actions
    'downgrade', 'sell rating', 'underweight', 'bearish', 'pessimistic',
    'cautious', 'negative', 'warning', 'concern', 'risk',
    # Business
    'layoff', 'restructuring', 'bankruptcy', 'default', 'writedown', 'write-down',
    'impairment', 'shutdown', 'closes', 'cuts jobs', 'lowers guidance',
    'profit warning', 'revenue miss', 'cost overrun', 'debt crisis',
    # Market
    'risk-off', 'correction', 'bubble', 'contagion', 'panic', 'flight to safety',
    'margin call', 'liquidation', 'outflows', 'capitulation', 'fear',
    'red', 'drags', 'weighs on', 'pressures', 'threatens',
]

_BULLISH_PATTERNS = [re.compile(re.escape(kw.strip()), re.IGNORECASE) for kw in BULLISH_KEYWORDS]
_BEARISH_PATTERNS = [re.compile(re.escape(kw.strip()), re.IGNORECASE) for kw in BEARISH_KEYWORDS]


def analyze_sentiment(text: str) -> Dict[str, Any]:
    """
    Analyze sentiment of a financial headline.
    Returns {"sentiment": "bullish"|"bearish"|"neutral", "sentiment_score": float}
    Score range: 0.5 (weak) to 1.0 (strong). Label = direction, score = strength.
    """
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
