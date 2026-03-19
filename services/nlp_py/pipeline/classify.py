"""
Topic Classification Module
Keyword-based text classification — no ML models required.
"""

import re
import time
from typing import List, Dict, Any, Optional

# Default topic labels — financial markets focus
DEFAULT_TOPICS = [
    'markets', 'economy', 'earnings', 'crypto', 'commodities',
    'real_estate', 'regulation', 'fintech', 'prediction_markets', 'mergers'
]

# Keyword rules: topic -> list of keywords/phrases (matched case-insensitively)
TOPIC_KEYWORDS: Dict[str, List[str]] = {
    'markets': [
        # original
        'stock', 'market', 's&p', 'nasdaq', 'dow jones', 'nyse', 'shares',
        'rally', 'selloff', 'sell-off', 'bull', 'bear', 'trading', 'index',
        'equities', 'wall street', 'futures', 'options', 'hedge fund',
        'etf', 'mutual fund', 'portfolio', 'volatility', 'vix',
        'blue chip', 'small cap', 'large cap', 'mid cap', 'penny stock',
        # expanded
        'investor', 'gain', 'loss', 'rise', 'fall', 'surge', 'plunge',
        'decline', 'advance', 'retreat', 'rebound', 'correction',
        'all-time high', 'record high', 'record low', 'outperform',
        'underperform', 'overweight', 'underweight', 'upgrade', 'downgrade',
        'buy rating', 'sell rating', 'hold rating', 'price target',
        'market cap', 'volume', 'turnover', 'momentum', 'breakout',
        'support level', 'resistance', 'moving average', 'rsi',
        'short selling', 'margin call', 'liquidation', 'sector rotation',
        'risk-on', 'risk-off', 'flight to safety',
    ],
    'economy': [
        # original
        'gdp', 'inflation', 'unemployment', 'jobs report', 'cpi', 'ppi',
        'interest rate', 'recession', 'federal reserve', 'fed ', ' fomc',
        'monetary policy', 'fiscal', 'deficit', 'debt ceiling', 'treasury',
        'yield curve', 'economic growth', 'consumer spending', 'retail sales',
        'trade deficit', 'tariff', 'labor market', 'payroll', 'wage',
        'central bank', 'quantitative', 'rate cut', 'rate hike', 'dovish',
        'hawkish', 'stagflation', 'disinflation',
        # expanded
        'nonfarm', 'jobless claims', 'consumer confidence', 'ism ',
        'manufacturing', 'services sector', 'housing starts', 'building permits',
        'durable goods', 'trade balance', 'current account', 'budget',
        'spending bill', 'stimulus', 'tightening', 'easing', 'pivot',
        'soft landing', 'hard landing', 'basis points', 'bps',
        'treasury yield', 'bond', 'note', 'auction', 'bid-to-cover',
        'real wages', 'core inflation', 'pce ', 'personal consumption',
        'beige book', 'dot plot', 'economic indicator', 'leading indicator',
        'lagging indicator',
    ],
    'earnings': [
        # original
        'earnings', 'revenue', 'profit', ' eps', 'guidance', 'quarterly',
        'annual report', 'dividend', 'buyback', 'beat expectations',
        'miss expectations', 'forecast', 'outlook', 'same-store sales',
        'operating income', 'net income', 'gross margin', 'ebitda',
        'analyst estimate', 'earnings call', 'earnings season',
        'top line', 'bottom line', 'year-over-year',
        # expanded
        'results', 'quarter', 'fiscal year', 'profit margin', 'operating margin',
        'free cash flow', 'cash flow', 'balance sheet', 'income statement',
        'backlog', 'order book', 'subscriber', 'user growth', 'arpu',
        'churn', 'retention', 'comp sales', 'organic growth',
        'adjusted earnings', 'non-gaap', 'gaap', 'write-down', 'impairment',
        'restructuring', 'cost cutting', 'shareholder', 'return on equity',
        'book value',
    ],
    'crypto': [
        # original
        'bitcoin', 'crypto', 'ethereum', 'blockchain', 'defi',
        'nft', 'token', 'mining', 'wallet', 'exchange', 'stablecoin',
        'altcoin', 'web3', 'solana', 'cardano', 'ripple', ' xrp',
        'binance', 'coinbase', 'decentralized', 'smart contract',
        'layer 2', 'halving', 'memecoin', 'airdrop',
        # expanded
        'satoshi', 'hash rate', 'proof of stake', 'proof of work',
        'validator', 'staking', 'yield farming', 'liquidity pool',
        'dex', 'cex', 'on-chain', 'off-chain', 'gas fee', 'whale',
        'hodl', 'btc', 'eth', 'usdt', 'usdc', 'dao', 'governance token',
        'tokenomics', 'tvl', 'total value locked', 'bridge', 'rollup',
        'sidechain', 'digital asset', 'virtual currency', 'cbdc',
    ],
    'commodities': [
        # original
        'oil', 'gold', 'silver', 'copper', 'natural gas', 'opec',
        'crude', 'commodity', 'energy', 'mining', 'wheat', 'corn',
        'lithium', 'uranium', 'platinum', 'palladium', 'iron ore',
        'brent', 'wti', 'barrel', 'refinery', 'pipeline', 'lng',
        'rare earth', 'cobalt', 'nickel',
        # expanded
        'aluminium', 'aluminum', 'zinc', 'tin', 'lead', 'soybean',
        'coffee', 'cocoa', 'sugar', 'cotton', 'lumber', 'timber',
        'cattle', 'hog', 'lean hog', 'precious metal', 'base metal',
        'industrial metal', 'spot price', 'futures contract', 'contango',
        'backwardation', 'drilling', 'fracking', 'shale', 'offshore',
        'renewable energy', 'solar', 'wind', 'nuclear', 'power grid',
        'electricity', 'utility', 'eia ', 'api inventory', 'stockpile',
        'reserve',
    ],
    'real_estate': [
        # original
        'housing', 'real estate', 'mortgage', 'reit', 'home sales',
        'rental', 'commercial property', 'construction', 'home prices',
        'foreclosure', 'homebuilder', 'housing starts', 'pending home',
        'existing home', 'new home', 'apartment', 'vacancy rate',
        'cap rate', 'property value', 'zoning',
        # expanded
        'mortgage rate', 'refinance', 'home equity', 'down payment',
        'closing', 'appraisal', 'listing', 'inventory', 'median home price',
        'case-shiller', 'zillow', 'redfin', 'realtor', 'broker', 'mls',
        'single family', 'multi-family', 'condo', 'townhouse', 'office space',
        'retail space', 'industrial property', 'warehouse', 'landlord',
        'tenant', 'lease', 'eviction', 'affordable housing', 'housing crisis',
        'housing bubble',
    ],
    'regulation': [
        # original
        'sec ', 'cftc', 'fdic', 'regulation', 'compliance', 'enforcement',
        'fine', 'sanction', 'legislation', 'antitrust', 'oversight',
        'investigation', 'subpoena', 'indictment', 'settlement',
        'dodd-frank', 'basel', 'aml', 'kyc', 'whistleblower',
        'insider trading', 'market manipulation', 'fraud',
        # expanded
        'regulator', 'regulatory', 'watchdog', 'probe', 'inquiry',
        'consent order', 'cease and desist', 'penalty', 'lawsuit',
        'class action', 'plaintiff', 'defendant', 'ruling', 'verdict',
        'injunction', 'fiduciary', 'suitability', 'disclosure', 'filing',
        'registration', 'license', 'charter', 'stress test',
        'capital requirement', 'reserve requirement', 'systemic risk',
        'too big to fail', 'bailout', 'congressional hearing', 'testimony',
        'gensler', 'warren',
    ],
    'fintech': [
        # original
        'fintech', 'payments', 'banking', 'neobank', 'digital banking',
        'mobile payments', 'stripe', 'paypal', 'visa', 'mastercard',
        'bnpl', 'buy now pay later', 'open banking', 'embedded finance',
        'robo-advisor', 'digital wallet', 'contactless', 'remittance',
        'insurtech', 'regtech', 'wealthtech',
        # expanded
        'payment processing', 'checkout', 'point of sale', 'pos',
        'acquiring', 'issuing', 'interchange', 'merchant',
        'cross-border payment', 'real-time payment', 'instant payment',
        'account-to-account', 'a2a', 'swift', 'ach',
        'banking as a service', 'baas', 'api banking', 'credit scoring',
        'underwriting', 'lending platform', 'peer-to-peer', 'crowdfunding',
        'revenue-based financing', 'super app', 'digital identity',
        'biometric',
    ],
    'prediction_markets': [
        # original
        'prediction market', 'polymarket', 'kalshi', 'metaculus',
        'manifold', 'forecast', 'betting', 'odds', 'probability',
        'prediction', 'wager', 'event contract', 'binary option',
        'information market', 'futarchy',
        # expanded
        'betting odds', 'implied probability', 'market odds',
        'prediction platform', 'event outcome', 'contract', 'yes shares',
        'no shares', 'resolution', 'market maker', 'liquidity', 'order book',
        'spread', 'bid', 'ask', 'election odds', 'political betting',
        'sports betting', 'prop bet', 'over under', 'moneyline',
        'forecasting tournament', 'superforecaster', 'brier score',
        'calibration', 'base rate', 'prior', 'posterior',
    ],
    'mergers': [
        # original
        'merger', 'acquisition', ' ipo', 'spac', 'venture capital',
        'private equity', 'deal', 'takeover', 'buyout', 'fundraising',
        'valuation', 'unicorn', 'series a', 'series b', 'seed round',
        'leveraged buyout', 'hostile takeover', 'divestiture', 'spinoff',
        'joint venture', 'strategic investment',
        # expanded
        'acquirer', 'target', 'bid', 'offer', 'premium', 'due diligence',
        'synergy', 'accretive', 'dilutive', 'shareholder approval',
        'regulatory approval', 'antitrust review', 'break-up fee',
        'go-shop', 'no-shop', 'fairness opinion', 'pipe deal',
        'secondary offering', 'follow-on', 'shelf registration',
        'direct listing', 'de-spac', 'blank check', 'growth equity',
        'mezzanine', 'bridge loan', 'exit', 'liquidity event',
        'portfolio company',
    ],
}

# Pre-compile patterns for each topic
_TOPIC_PATTERNS: Dict[str, List[re.Pattern]] = {}
for _topic, _keywords in TOPIC_KEYWORDS.items():
    _TOPIC_PATTERNS[_topic] = [
        re.compile(re.escape(kw.strip()), re.IGNORECASE) for kw in _keywords
    ]


class TopicClassifier:
    """Topic classification using keyword matching."""

    def __init__(self, topics: Optional[List[str]] = None):
        self.topics = topics or DEFAULT_TOPICS

    def classify_single(self, text: str, candidate_labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """Classify a single text into topics using keyword matching."""
        labels = candidate_labels or self.topics
        start_time = time.time()

        scores: Dict[str, float] = {}
        text_lower = f" {text.lower()} "

        for topic in labels:
            patterns = _TOPIC_PATTERNS.get(topic, [])
            hits = sum(1 for p in patterns if p.search(text_lower))
            scores[topic] = hits / max(len(patterns), 1)

        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_topics = [
            {'topic': t, 'confidence': round(s, 3)}
            for t, s in ranked[:3]
        ]

        # If no keywords matched at all, fall back to 'general'
        if ranked[0][1] == 0:
            return self._fallback_classification(text)

        processing_time = time.time() - start_time
        return {
            'text': text,
            'topics': [t for t, _ in ranked],
            'scores': [s for _, s in ranked],
            'topTopics': top_topics,
            'processing_time': processing_time,
            'model_version': 'keyword-v1',
        }

    def _fallback_classification(self, text: str) -> Dict[str, Any]:
        """Fallback when no keywords match."""
        return {
            'text': text,
            'topics': ['general'],
            'scores': [1.0],
            'topTopics': [{'topic': 'general', 'confidence': 1.0}],
            'processing_time': 0.0,
            'model_version': 'keyword-v1',
        }


# Global classifier instance
_classifier = None


def get_classifier() -> TopicClassifier:
    global _classifier
    if _classifier is None:
        _classifier = TopicClassifier()
    return _classifier


def classify(text: str, candidate_labels: Optional[List[str]] = None) -> Dict[str, Any]:
    return get_classifier().classify_single(text, candidate_labels)
