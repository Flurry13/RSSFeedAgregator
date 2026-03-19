# Financial Intelligence Foundation — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform RSSFeed2 from a generic news aggregator into a financial intelligence platform with accurate classification, clean event clusters, a financial-aware frontend, and AI-agent-facing insights API.

**Architecture:** Fix data quality first (classification + clustering), then build the insights API on top of clean data, then redesign the frontend to surface financial intelligence. Schema migrations add feed health tracking and pipeline run history.

**Tech Stack:** Python 3.11 (Flask), PostgreSQL 15, Next.js 15, TypeScript, Recharts, feedparser, spaCy

---

## Chunk 1: Bug Fixes & Classification

### Task 1: Fix Pre-existing Bugs

**Files:**
- Modify: `services/nlp_py/repositories.py:645-656`
- Modify: `services/nlp_py/repositories.py:620-630`

- [ ] **Step 1: Fix daily volume GROUP BY bug**

In `repositories.py`, the daily volume query uses `GROUP BY day` / `ORDER BY day` but the SELECT alias is `date`. Fix lines 651-652:

```python
# In AnalyticsRepository.get_analytics(), the daily volume query:
# Change:
#   GROUP BY day
#   ORDER BY day ASC
# To:
                    GROUP BY DATE(created_at)
                    ORDER BY DATE(created_at) ASC
```

- [ ] **Step 2: Fix source breakdown GROUP BY**

The source breakdown query at line 625 groups by `s.name` but selects `s.id`. Add `s.id` to GROUP BY:

```python
# Change line 625:
#   GROUP BY s.name
# To:
                    GROUP BY s.id, s.name
```

- [ ] **Step 3: Verify fixes**

```bash
docker compose up -d --build nlp_service
sleep 10
curl -s "http://localhost:8081/api/analytics?period=24h" | python3 -c "import json,sys; d=json.load(sys.stdin); print('daily_volume:', d['daily_volume'][:3]); print('source_breakdown:', d['source_breakdown'][:3])"
```

Expected: `daily_volume` and `source_breakdown` return non-empty arrays.

- [ ] **Step 4: Commit**

```bash
git add services/nlp_py/repositories.py
git commit -m "fix: daily volume GROUP BY bug and source breakdown GROUP BY"
```

---

### Task 2: Expand Classification Keywords

**Files:**
- Modify: `services/nlp_py/pipeline/classify.py:11-90`

- [ ] **Step 1: Replace TOPIC_KEYWORDS with expanded financial keywords**

Replace the entire `TOPIC_KEYWORDS` dict (lines 17-90) with heavily expanded keyword lists. Each topic should have ~60-80 keywords covering financial jargon, common headline phrases, ticker-adjacent terms, and abbreviations. Key expansions:

```python
TOPIC_KEYWORDS: Dict[str, List[str]] = {
    'markets': [
        'stock', 'market', 's&p', 'nasdaq', 'dow jones', 'nyse', 'shares',
        'rally', 'selloff', 'sell-off', 'bull', 'bear', 'trading', 'index',
        'equities', 'wall street', 'futures', 'options', 'hedge fund',
        'etf', 'mutual fund', 'portfolio', 'volatility', 'vix',
        'blue chip', 'small cap', 'large cap', 'mid cap',
        # ADD these new terms to catch more headlines:
        'investor', 'gain', 'loss', 'rise', 'fall', 'surge', 'plunge',
        'decline', 'advance', 'retreat', 'rebound', 'correction',
        'all-time high', 'record high', 'record low', 'outperform',
        'underperform', 'overweight', 'underweight', 'upgrade', 'downgrade',
        'buy rating', 'sell rating', 'hold rating', 'price target',
        'market cap', 'volume', 'turnover', 'momentum', 'breakout',
        'support level', 'resistance', 'moving average', 'rsi',
        'short selling', 'margin call', 'liquidation',
        'sector rotation', 'risk-on', 'risk-off', 'flight to safety',
    ],
    'economy': [
        'gdp', 'inflation', 'unemployment', 'jobs report', 'cpi', 'ppi',
        'interest rate', 'recession', 'federal reserve', 'fed ', ' fomc',
        'monetary policy', 'fiscal', 'deficit', 'debt ceiling', 'treasury',
        'yield curve', 'economic growth', 'consumer spending', 'retail sales',
        'trade deficit', 'tariff', 'labor market', 'payroll', 'wage',
        'central bank', 'quantitative', 'rate cut', 'rate hike', 'dovish',
        'hawkish', 'stagflation', 'disinflation',
        # ADD:
        'nonfarm', 'jobless claims', 'consumer confidence', 'ism ',
        'manufacturing', 'services sector', 'housing starts',
        'building permits', 'durable goods', 'trade balance',
        'current account', 'budget', 'spending bill', 'stimulus',
        'tightening', 'easing', 'pivot', 'soft landing', 'hard landing',
        'basis points', 'bps', 'treasury yield', 'bond', 'note',
        'auction', 'bid-to-cover', 'real wages', 'core inflation',
        'pce ', 'personal consumption', 'beige book', 'dot plot',
        'economic indicator', 'leading indicator', 'lagging indicator',
    ],
    'earnings': [
        'earnings', 'revenue', 'profit', ' eps', 'guidance', 'quarterly',
        'annual report', 'dividend', 'buyback', 'beat expectations',
        'miss expectations', 'forecast', 'outlook', 'same-store sales',
        'operating income', 'net income', 'gross margin', 'ebitda',
        'analyst estimate', 'earnings call', 'earnings season',
        'top line', 'bottom line', 'year-over-year',
        # ADD:
        'results', 'quarter', 'fiscal year', 'profit margin',
        'operating margin', 'free cash flow', 'cash flow',
        'balance sheet', 'income statement', 'backlog',
        'order book', 'subscriber', 'user growth', 'arpu',
        'churn', 'retention', 'comp sales', 'organic growth',
        'adjusted earnings', 'non-gaap', 'gaap', 'write-down',
        'impairment', 'restructuring', 'cost cutting',
        'shareholder', 'return on equity', 'book value',
    ],
    'crypto': [
        'bitcoin', 'crypto', 'ethereum', 'blockchain', 'defi',
        'nft', 'token', 'mining', 'wallet', 'exchange', 'stablecoin',
        'altcoin', 'web3', 'solana', 'cardano', 'ripple', ' xrp',
        'binance', 'coinbase', 'decentralized', 'smart contract',
        'layer 2', 'halving', 'memecoin', 'airdrop',
        # ADD:
        'satoshi', 'hash rate', 'proof of stake', 'proof of work',
        'validator', 'staking', 'yield farming', 'liquidity pool',
        'dex', 'cex', 'on-chain', 'off-chain', 'gas fee',
        'whale', 'hodl', 'btc', 'eth', 'usdt', 'usdc',
        'dao', 'governance token', 'tokenomics', 'tvl',
        'total value locked', 'bridge', 'rollup', 'sidechain',
        'digital asset', 'virtual currency', 'cbdc',
    ],
    'commodities': [
        'oil', 'gold', 'silver', 'copper', 'natural gas', 'opec',
        'crude', 'commodity', 'energy', 'mining', 'wheat', 'corn',
        'lithium', 'uranium', 'platinum', 'palladium', 'iron ore',
        'brent', 'wti', 'barrel', 'refinery', 'pipeline', 'lng',
        'rare earth', 'cobalt', 'nickel',
        # ADD:
        'aluminium', 'aluminum', 'zinc', 'tin', 'lead',
        'soybean', 'coffee', 'cocoa', 'sugar', 'cotton',
        'lumber', 'timber', 'cattle', 'hog', 'lean hog',
        'precious metal', 'base metal', 'industrial metal',
        'spot price', 'futures contract', 'contango', 'backwardation',
        'drilling', 'fracking', 'shale', 'offshore',
        'renewable energy', 'solar', 'wind', 'nuclear',
        'power grid', 'electricity', 'utility',
        'eia ', 'api inventory', 'stockpile', 'reserve',
    ],
    'real_estate': [
        'housing', 'real estate', 'mortgage', 'reit', 'home sales',
        'rental', 'commercial property', 'construction', 'home prices',
        'foreclosure', 'homebuilder', 'housing starts', 'pending home',
        'existing home', 'new home', 'apartment', 'vacancy rate',
        'cap rate', 'property value', 'zoning',
        # ADD:
        'mortgage rate', 'refinance', 'home equity', 'down payment',
        'closing', 'appraisal', 'listing', 'inventory',
        'median home price', 'case-shiller', 'zillow', 'redfin',
        'realtor', 'broker', 'mls', 'single family',
        'multi-family', 'condo', 'townhouse', 'office space',
        'retail space', 'industrial property', 'warehouse',
        'landlord', 'tenant', 'lease', 'eviction',
        'affordable housing', 'housing crisis', 'housing bubble',
    ],
    'regulation': [
        'sec ', 'cftc', 'fdic', 'regulation', 'compliance', 'enforcement',
        'fine', 'sanction', 'legislation', 'antitrust', 'oversight',
        'investigation', 'subpoena', 'indictment', 'settlement',
        'dodd-frank', 'basel', 'aml', 'kyc', 'whistleblower',
        'insider trading', 'market manipulation', 'fraud',
        # ADD:
        'regulator', 'regulatory', 'watchdog', 'probe', 'inquiry',
        'consent order', 'cease and desist', 'penalty', 'lawsuit',
        'class action', 'plaintiff', 'defendant', 'ruling', 'verdict',
        'injunction', 'fiduciary', 'suitability', 'disclosure',
        'filing', 'registration', 'license', 'charter',
        'stress test', 'capital requirement', 'reserve requirement',
        'systemic risk', 'too big to fail', 'bailout',
        'congressional hearing', 'testimony', 'gensler', 'warren',
    ],
    'fintech': [
        'fintech', 'payments', 'banking', 'neobank', 'digital banking',
        'mobile payments', 'stripe', 'paypal', 'visa', 'mastercard',
        'bnpl', 'buy now pay later', 'open banking', 'embedded finance',
        'robo-advisor', 'digital wallet', 'contactless', 'remittance',
        'insurtech', 'regtech', 'wealthtech',
        # ADD:
        'payment processing', 'checkout', 'point of sale', 'pos',
        'acquiring', 'issuing', 'interchange', 'merchant',
        'cross-border payment', 'real-time payment', 'instant payment',
        'account-to-account', 'a2a', 'swift', 'ach',
        'banking as a service', 'baas', 'api banking',
        'credit scoring', 'underwriting', 'lending platform',
        'peer-to-peer', 'crowdfunding', 'revenue-based financing',
        'super app', 'digital identity', 'biometric',
    ],
    'prediction_markets': [
        'prediction market', 'polymarket', 'kalshi', 'metaculus',
        'manifold', 'forecast', 'betting', 'odds', 'probability',
        'prediction', 'wager', 'event contract', 'binary option',
        'information market', 'futarchy',
        # ADD:
        'betting odds', 'implied probability', 'market odds',
        'prediction platform', 'event outcome', 'contract',
        'yes shares', 'no shares', 'resolution', 'market maker',
        'liquidity', 'order book', 'spread', 'bid', 'ask',
        'election odds', 'political betting', 'sports betting',
        'prop bet', 'over under', 'moneyline',
        'forecasting tournament', 'superforecaster', 'brier score',
        'calibration', 'base rate', 'prior', 'posterior',
    ],
    'mergers': [
        'merger', 'acquisition', ' ipo', 'spac', 'venture capital',
        'private equity', 'deal', 'takeover', 'buyout', 'fundraising',
        'valuation', 'unicorn', 'series a', 'series b', 'seed round',
        'leveraged buyout', 'hostile takeover', 'divestiture', 'spinoff',
        'joint venture', 'strategic investment',
        # ADD:
        'acquirer', 'target', 'bid', 'offer', 'premium',
        'due diligence', 'synergy', 'accretive', 'dilutive',
        'shareholder approval', 'regulatory approval', 'antitrust review',
        'break-up fee', 'go-shop', 'no-shop', 'fairness opinion',
        'pipe deal', 'secondary offering', 'follow-on', 'shelf registration',
        'direct listing', 'de-spac', 'blank check',
        'growth equity', 'mezzanine', 'bridge loan',
        'exit', 'liquidity event', 'portfolio company',
    ],
}
```

- [ ] **Step 2: Verify keyword expansion reduces "general" count**

```bash
docker compose up -d --build nlp_service
sleep 10
# Re-run classification on existing headlines
curl -s -X POST http://localhost:8081/api/classify
sleep 15
# Check topic distribution
docker compose exec -T postgres psql -U news_user -d news_ai -c "SELECT topic, COUNT(*) FROM headlines WHERE topic IS NOT NULL GROUP BY topic ORDER BY count DESC;"
```

Expected: `general` count drops significantly (target: under 500 from keyword expansion alone).

- [ ] **Step 3: Commit**

```bash
git add services/nlp_py/pipeline/classify.py
git commit -m "feat: expand financial keyword lists to ~70 terms per topic"
```

---

### Task 3: Add Source-Category Fallback to Classifier

**Files:**
- Modify: `services/nlp_py/pipeline/classify.py:11-14, 133-149`

- [ ] **Step 1: Add category-to-topic mapping and fallback method**

Add a mapping dict at module level (after DEFAULT_TOPICS) and modify `_fallback_classification`:

```python
# After DEFAULT_TOPICS (line 14), add:
CATEGORY_TO_TOPIC: Dict[str, str] = {
    'equities': 'markets',
    'macro': 'economy',
    'crypto': 'crypto',
    'prediction_markets': 'prediction_markets',
    'commodities': 'commodities',
    'real_estate': 'real_estate',
    'regulation': 'regulation',
    'fintech': 'fintech',
    'earnings': 'earnings',
    'international': 'markets',
}
```

- [ ] **Step 2: Update classify_single to accept source_category parameter**

```python
def classify_single(self, text: str, candidate_labels: Optional[List[str]] = None,
                    source_category: Optional[str] = None) -> Dict[str, Any]:
    # ... existing code ...
    # Change the fallback condition:
    if ranked[0][1] == 0:
        return self._fallback_classification(text, source_category)
    # ... rest unchanged ...

def _fallback_classification(self, text: str, source_category: Optional[str] = None) -> Dict[str, Any]:
    fallback_topic = CATEGORY_TO_TOPIC.get(source_category, 'general') if source_category else 'general'
    return {
        'text': text,
        'topics': [fallback_topic],
        'scores': [0.5],
        'topTopics': [{'topic': fallback_topic, 'confidence': 0.5}],
        'processing_time': 0.0,
        'model_version': 'keyword-v1-fallback',
    }
```

- [ ] **Step 3: Update the module-level classify() function**

```python
def classify(text: str, candidate_labels: Optional[List[str]] = None,
             source_category: Optional[str] = None) -> Dict[str, Any]:
    return get_classifier().classify_single(text, candidate_labels, source_category)
```

- [ ] **Step 4: Wire source_category through the pipeline**

In `api_server.py`, find where classify is called during the pipeline run. The classify stage processes headlines that have a `source_id`. Look up the source's category and pass it through. The exact wiring depends on how `parallel_pipeline.py` calls classify — check `classify_batch_wrapper()` and ensure `source_category` is passed from the headline's source metadata.

- [ ] **Step 5: Rebuild, re-run pipeline, verify**

```bash
docker compose up -d --build nlp_service
sleep 10
# Clear old topics and re-classify
docker compose exec -T postgres psql -U news_user -d news_ai -c "UPDATE headlines SET topic = NULL, topic_confidence = NULL;"
curl -s -X POST http://localhost:8081/api/run
sleep 40
docker compose exec -T postgres psql -U news_user -d news_ai -c "SELECT topic, COUNT(*) FROM headlines WHERE topic IS NOT NULL GROUP BY topic ORDER BY count DESC;"
```

Expected: `general` count under 200. All 10 financial topics have meaningful counts.

- [ ] **Step 6: Commit**

```bash
git add services/nlp_py/pipeline/classify.py services/nlp_py/api_server.py services/nlp_py/pipeline/parallel_pipeline.py
git commit -m "feat: source-category fallback for unmatched headlines"
```

---

## Chunk 2: Event Clustering & Insights API

### Task 4: Fix Event Clustering Quality

**Files:**
- Modify: `services/nlp_py/pipeline/group_by_event.py:139-157`
- Modify: `services/nlp_py/pipeline/event_extract.py:34-41`

- [ ] **Step 1: Add entity type filter to generate_group_summary**

In `group_by_event.py`, modify `generate_group_summary` (line 139) to filter out noisy entity types before ranking:

```python
def generate_group_summary(self, cluster: List[Dict]) -> Dict:
    if not cluster:
        return {}
    # Entity types that produce meaningful financial cluster labels
    LABEL_ENTITY_TYPES = {'PERSON', 'ORG', 'GPE', 'NORP', 'FAC', 'EVENT', 'PRODUCT', 'LAW'}
    # Words that should never be cluster labels
    STOP_LABELS = {'the', 'a', 'an', 'this', 'that', 'it', 'they', 'we', 'he', 'she',
                   'first', 'second', 'third', 'last', 'new', 'old', 'more', 'most',
                   'one', 'two', 'three', 'four', 'five', 'million', 'billion', 'trillion'}

    all_entities: List[Dict] = []
    for event in cluster:
        all_entities.extend(event.get("entities", []))

    # Filter to meaningful entity types only
    filtered = [e for e in all_entities
                if e.get("label") in LABEL_ENTITY_TYPES
                and e["text"].lower().strip() not in STOP_LABELS
                and len(e["text"].strip()) > 1
                and not e["text"].strip().replace('.', '').replace(',', '').isdigit()]

    entity_counts: Dict[tuple, int] = defaultdict(int)
    for ent in filtered:
        entity_counts[(ent["text"], ent["label"])] += 1
    common = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    event_types = [e.get("event_type", "other") for e in cluster]
    dominant = max(set(event_types), key=event_types.count)
    return {
        "size": len(cluster),
        "dominant_event_type": dominant,
        "common_entities": [{"text": t, "label": l, "count": c} for (t, l), c in common],
        "time_span": self._get_time_span(cluster),
        "cohesion_score": self.calculate_cohesion_score(cluster),
    }
```

- [ ] **Step 2: Update event type keywords for financial domain**

In `event_extract.py`, replace `self.event_type_keywords` (lines 34-41):

```python
self.event_type_keywords = {
    "earnings_report": ["earnings", "revenue", "profit", "quarterly", "results", "guidance", "eps", "dividend"],
    "policy_decision": ["fed", "federal reserve", "interest rate", "rate cut", "rate hike", "monetary", "fomc", "central bank"],
    "market_move": ["rally", "selloff", "crash", "surge", "plunge", "correction", "record high", "all-time", "volatility"],
    "deal": ["merger", "acquisition", "ipo", "buyout", "takeover", "deal", "venture", "fundraising"],
    "regulatory_action": ["sec", "cftc", "fdic", "fine", "enforcement", "investigation", "settlement", "lawsuit", "regulation"],
    "crypto_event": ["bitcoin", "crypto", "ethereum", "blockchain", "defi", "token", "exchange", "mining"],
    "other": []
}
```

- [ ] **Step 3: Rebuild, re-run pipeline, verify events page**

```bash
docker compose up -d --build nlp_service
sleep 10
# Clear old clusters and re-run
docker compose exec -T postgres psql -U news_user -d news_ai -c "DELETE FROM event_cluster_members; DELETE FROM event_clusters; UPDATE headlines SET entities = NULL, event_type = NULL;"
curl -s -X POST http://localhost:8081/api/run
sleep 40
# Check cluster quality
docker compose exec -T postgres psql -U news_user -d news_ai -c "SELECT ec.label, ec.event_type, COUNT(ecm.headline_id) as members FROM event_clusters ec JOIN event_cluster_members ecm ON ec.id = ecm.cluster_id GROUP BY ec.id, ec.label, ec.event_type ORDER BY members DESC LIMIT 15;"
```

Expected: Cluster labels are meaningful names (companies, people, countries) not numbers or stop words. Event types include financial types.

- [ ] **Step 4: Commit**

```bash
git add services/nlp_py/pipeline/group_by_event.py services/nlp_py/pipeline/event_extract.py
git commit -m "feat: filter noisy entities from clusters, add financial event types"
```

---

### Task 5: Build Insights API

**Files:**
- Modify: `services/nlp_py/repositories.py` (add InsightsRepository class after AnalyticsRepository)
- Modify: `services/nlp_py/api_server.py` (add /api/insights routes)
- Modify: `frontend/src/lib/api.ts` (add InsightsSummary type and api.insights methods)

- [ ] **Step 1: Add InsightsRepository to repositories.py**

After the AnalyticsRepository class, add:

```python
class InsightsRepository:
    """Structured financial insights for AI agent consumption."""

    _PERIOD_MAP = AnalyticsRepository._PERIOD_MAP

    @staticmethod
    def get_summary(period: str = "24h") -> Dict[str, Any]:
        interval = InsightsRepository._PERIOD_MAP.get(period, "24 hours")
        params = {"interval": interval}
        result: Dict[str, Any] = {"period": period}
        try:
            with get_db_cursor() as cursor:
                # Top headlines per category
                cursor.execute("""
                    SELECT s.category, h.title, h.url, h.topic, h.topic_confidence,
                           s.name as source_name
                    FROM headlines h
                    JOIN sources s ON h.source_id = s.id
                    WHERE h.created_at >= NOW() - %(interval)s::INTERVAL
                      AND h.topic IS NOT NULL AND h.topic != 'general'
                    ORDER BY h.topic_confidence DESC NULLS LAST
                """, params)
                rows = [dict(r) for r in cursor.fetchall()]
                by_cat: Dict[str, list] = {}
                for r in rows:
                    cat = r.pop("category") or "unknown"
                    by_cat.setdefault(cat, [])
                    if len(by_cat[cat]) < 5:
                        by_cat[cat].append(r)
                result["top_headlines_by_category"] = by_cat

                # Topic activity
                cursor.execute("""
                    SELECT topic, COUNT(*) as count
                    FROM headlines
                    WHERE created_at >= NOW() - %(interval)s::INTERVAL
                      AND topic IS NOT NULL
                    GROUP BY topic
                    ORDER BY count DESC
                """, params)
                result["topic_counts"] = [dict(r) for r in cursor.fetchall()]

                # Category volume
                cursor.execute("""
                    SELECT s.category, COUNT(h.id) as count
                    FROM headlines h
                    JOIN sources s ON h.source_id = s.id
                    WHERE h.created_at >= NOW() - %(interval)s::INTERVAL
                    GROUP BY s.category
                    ORDER BY count DESC
                """, params)
                result["category_volume"] = [dict(r) for r in cursor.fetchall()]

                # Top entities (from event clusters)
                cursor.execute("""
                    SELECT ec.label, ec.event_type,
                           COUNT(ecm.headline_id) as headline_count
                    FROM event_clusters ec
                    JOIN event_cluster_members ecm ON ec.id = ecm.cluster_id
                    WHERE ec.created_at >= NOW() - %(interval)s::INTERVAL
                    GROUP BY ec.id, ec.label, ec.event_type
                    ORDER BY headline_count DESC
                    LIMIT 10
                """, params)
                result["top_clusters"] = [dict(r) for r in cursor.fetchall()]

                # Feed health summary
                cursor.execute("""
                    SELECT COUNT(*) FILTER (WHERE active AND fetch_error IS NULL) as healthy,
                           COUNT(*) FILTER (WHERE active AND fetch_error IS NOT NULL) as erroring,
                           COUNT(*) FILTER (WHERE NOT active) as inactive
                    FROM sources
                """)
                result["feed_health"] = dict(cursor.fetchone())

        except Exception as e:
            print(f"Error fetching insights: {e}")
            result["error"] = str(e)
        return result

    @staticmethod
    def get_category_detail(category: str, period: str = "24h") -> Dict[str, Any]:
        interval = InsightsRepository._PERIOD_MAP.get(period, "24 hours")
        params = {"interval": interval, "category": category}
        result: Dict[str, Any] = {"category": category, "period": period}
        try:
            with get_db_cursor() as cursor:
                # Headlines for this category
                cursor.execute("""
                    SELECT h.title, h.url, h.topic, h.topic_confidence,
                           s.name as source_name, h.published_at
                    FROM headlines h
                    JOIN sources s ON h.source_id = s.id
                    WHERE h.created_at >= NOW() - %(interval)s::INTERVAL
                      AND s.category = %(category)s
                    ORDER BY h.topic_confidence DESC NULLS LAST
                    LIMIT 25
                """, params)
                result["headlines"] = [dict(r) for r in cursor.fetchall()]

                # Topic distribution within category
                cursor.execute("""
                    SELECT h.topic, COUNT(*) as count
                    FROM headlines h
                    JOIN sources s ON h.source_id = s.id
                    WHERE h.created_at >= NOW() - %(interval)s::INTERVAL
                      AND s.category = %(category)s
                      AND h.topic IS NOT NULL
                    GROUP BY h.topic
                    ORDER BY count DESC
                """, params)
                result["topic_distribution"] = [dict(r) for r in cursor.fetchall()]

                # Sources in this category
                cursor.execute("""
                    SELECT s.name, s.url, s.last_fetched_at, s.fetch_error,
                           COUNT(h.id) as headline_count
                    FROM sources s
                    LEFT JOIN headlines h ON s.id = h.source_id
                        AND h.created_at >= NOW() - %(interval)s::INTERVAL
                    WHERE s.category = %(category)s
                    GROUP BY s.id, s.name, s.url, s.last_fetched_at, s.fetch_error
                    ORDER BY headline_count DESC
                """, params)
                result["sources"] = [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching category detail: {e}")
            result["error"] = str(e)
        return result
```

- [ ] **Step 2: Add Flask routes for insights**

In `api_server.py`, add after the analytics endpoint:

```python
from repositories import SourceRepository, HeadlineRepository, EventClusterRepository, AnalyticsRepository, InsightsRepository

@app.route("/api/insights/summary")
def get_insights_summary():
    period = request.args.get("period", "24h")
    if period not in ("24h", "7d", "30d"):
        period = "24h"
    return jsonify(InsightsRepository.get_summary(period))

@app.route("/api/insights/category/<category>")
def get_insights_category(category):
    period = request.args.get("period", "24h")
    if period not in ("24h", "7d", "30d"):
        period = "24h"
    return jsonify(InsightsRepository.get_category_detail(category, period))
```

- [ ] **Step 3: Verify API returns structured data**

```bash
docker compose up -d --build nlp_service
sleep 10
curl -s "http://localhost:8081/api/insights/summary?period=24h" | python3 -m json.tool | head -40
curl -s "http://localhost:8081/api/insights/category/crypto?period=24h" | python3 -m json.tool | head -30
```

Expected: Both endpoints return structured JSON with meaningful financial data.

- [ ] **Step 4: Commit**

```bash
git add services/nlp_py/repositories.py services/nlp_py/api_server.py
git commit -m "feat: add /api/insights endpoints for AI agent consumption"
```

---

## Chunk 3: Frontend Redesign

### Task 6: Fix Frontend Topic Colors and Filters

**Files:**
- Modify: `frontend/src/app/page.tsx:18-59`
- Modify: `frontend/src/app/analytics/page.tsx:26-39`
- Modify: `frontend/src/app/events/page.tsx:11-17`

- [ ] **Step 1: Replace TOPICS, topicStyle, and topicBorderColor in page.tsx**

```typescript
// Replace TOPICS (line 18-28):
const TOPICS = [
  "all",
  "markets",
  "economy",
  "earnings",
  "crypto",
  "commodities",
  "real_estate",
  "regulation",
  "fintech",
  "prediction_markets",
  "mergers",
];

// Replace topicStyle (line 32-48):
function topicStyle(topic: string): { bg: string; fg: string; border: string } {
  const m: Record<string, { bg: string; fg: string; border: string }> = {
    markets:            { bg: "bg-[#00ff88]", fg: "text-black", border: "border-[#00ff88]" },
    economy:            { bg: "bg-[#ffd700]", fg: "text-black", border: "border-[#ffd700]" },
    earnings:           { bg: "bg-[#ff8800]", fg: "text-black", border: "border-[#ff8800]" },
    crypto:             { bg: "bg-[#aa77ff]", fg: "text-black", border: "border-[#aa77ff]" },
    commodities:        { bg: "bg-[#ff3333]", fg: "text-black", border: "border-[#ff3333]" },
    real_estate:        { bg: "bg-[#00dddd]", fg: "text-black", border: "border-[#00dddd]" },
    regulation:         { bg: "bg-[#4488ff]", fg: "text-black", border: "border-[#4488ff]" },
    fintech:            { bg: "bg-[#33ff99]", fg: "text-black", border: "border-[#33ff99]" },
    prediction_markets: { bg: "bg-[#ff69b4]", fg: "text-black", border: "border-[#ff69b4]" },
    mergers:            { bg: "bg-[#ff44aa]", fg: "text-black", border: "border-[#ff44aa]" },
    general:            { bg: "bg-[#666]",    fg: "text-black", border: "border-[#666]" },
  };
  return m[topic.toLowerCase()] ?? m.general;
}

// Replace topicBorderColor (line 51-58):
function topicBorderColor(topic: string): string {
  const m: Record<string, string> = {
    markets: "#00ff88", economy: "#ffd700", earnings: "#ff8800",
    crypto: "#aa77ff", commodities: "#ff3333", real_estate: "#00dddd",
    regulation: "#4488ff", fintech: "#33ff99", prediction_markets: "#ff69b4",
    mergers: "#ff44aa",
  };
  return m[topic.toLowerCase()] ?? "#333";
}
```

- [ ] **Step 2: Update TOPIC_COLORS in analytics/page.tsx**

```typescript
// Replace TOPIC_COLORS (line 26-39):
const TOPIC_COLORS: Record<string, string> = {
  markets: "#00ff88",
  economy: "#ffd700",
  earnings: "#ff8800",
  crypto: "#aa77ff",
  commodities: "#ff3333",
  real_estate: "#00dddd",
  regulation: "#4488ff",
  fintech: "#33ff99",
  prediction_markets: "#ff69b4",
  mergers: "#ff44aa",
  general: "#666666",
};
```

- [ ] **Step 3: Update EVENT_TYPE_COLORS in events/page.tsx**

```typescript
// Replace EVENT_TYPE_COLORS (line 11-17):
const EVENT_TYPE_COLORS: Record<string, string> = {
  earnings_report: "#ff8800",
  policy_decision: "#ffd700",
  market_move: "#00ff88",
  deal: "#ff44aa",
  regulatory_action: "#4488ff",
  crypto_event: "#aa77ff",
  other: "#666",
};
```

- [ ] **Step 4: Verify in browser**

Open http://localhost:3000 — topic badges should show correct financial colors. Analytics chart bars should have matching colors. Events page should show financial event type badges.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/page.tsx frontend/src/app/analytics/page.tsx frontend/src/app/events/page.tsx
git commit -m "feat: update frontend topic colors and filters for financial topics"
```

---

### Task 7: Replace Language Breakdown with Category Breakdown

**Files:**
- Modify: `services/nlp_py/repositories.py` (add category_breakdown to get_analytics)
- Modify: `frontend/src/lib/api.ts` (update AnalyticsData interface)
- Modify: `frontend/src/app/analytics/page.tsx` (replace LanguagesChart with CategoryChart)

- [ ] **Step 1: Add category_breakdown query to AnalyticsRepository.get_analytics**

After the language_breakdown query in `repositories.py`, add:

```python
                # Category breakdown
                cursor.execute(
                    """
                    SELECT s.category, COUNT(h.id) AS count
                    FROM headlines h
                    JOIN sources s ON h.source_id = s.id
                    WHERE h.created_at >= NOW() - %(interval)s::INTERVAL
                      AND s.category IS NOT NULL
                    GROUP BY s.category
                    ORDER BY count DESC
                    """,
                    params,
                )
                result["category_breakdown"] = [dict(r) for r in cursor.fetchall()]
```

Also add `"category_breakdown": []` to the initial `result` dict.

- [ ] **Step 2: Update AnalyticsData interface in api.ts**

```typescript
export interface AnalyticsData {
  period: string;
  topic_distribution: { topic: string; count: number }[];
  language_breakdown: { language: string; count: number }[];
  category_breakdown: { category: string; count: number }[];
  daily_volume: { date: string; count: number }[];
  source_breakdown: { source_id: number; name: string; count: number }[];
}
```

- [ ] **Step 3: Replace LanguagesChart with CategoryChart in analytics/page.tsx**

Replace the `LanguagesChart` component (lines 98-140) with:

```typescript
function CategoryChart({ data }: { data: { category: string; count: number }[] }) {
  return (
    <div>
      <h2 className="font-mono text-[10px] uppercase tracking-widest text-[#555] mb-4">
        Category Breakdown
      </h2>
      <div className="flex items-center gap-6">
        <ResponsiveContainer width="60%" height={200}>
          <PieChart>
            <Pie
              data={data}
              dataKey="count"
              nameKey="category"
              cx="50%"
              cy="50%"
              outerRadius={80}
              labelLine={false}
              strokeWidth={2}
              stroke="#050505"
            >
              {data.map((entry) => (
                <Cell
                  key={entry.category}
                  fill={TOPIC_COLORS[entry.category] ?? COLORS[0]}
                />
              ))}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} />
          </PieChart>
        </ResponsiveContainer>
        <div className="flex flex-col gap-2 font-mono text-[11px]">
          {data.map((d) => (
            <div key={d.category} className="flex items-center gap-2">
              <span
                className="w-2 h-2 shrink-0"
                style={{ background: TOPIC_COLORS[d.category] ?? "#555" }}
              />
              <span className="text-[#777] uppercase">{d.category.replace('_', ' ')}</span>
              <span className="text-[#00ff88] ml-1 font-bold">{d.count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

In the render section, replace `<LanguagesChart data={data.language_breakdown} />` with `<CategoryChart data={data.category_breakdown ?? []} />`.

- [ ] **Step 4: Verify in browser**

Open http://localhost:3000/analytics — the Language Breakdown chart should be replaced with a Category Breakdown pie chart showing equities, macro, crypto, etc.

- [ ] **Step 5: Commit**

```bash
git add services/nlp_py/repositories.py frontend/src/lib/api.ts frontend/src/app/analytics/page.tsx
git commit -m "feat: replace empty language chart with category breakdown"
```

---

## Chunk 4: Operations & Insights Page

### Task 8: Add Feed Health Monitoring

**Files:**
- Modify: `scripts/migrate.sql` (add error_count column to sources)
- Modify: `services/nlp_py/repositories.py` (update update_last_fetched)
- Modify: `services/nlp_py/pipeline/gather.py` (call update_last_fetched after each feed)
- Modify: `frontend/src/app/sources/page.tsx` (add health indicators)

- [ ] **Step 1: Add error_count column to sources table**

Add a migration SQL or alter the existing migrate.sql. For the running DB, run:

```bash
docker compose exec -T postgres psql -U news_user -d news_ai -c "
ALTER TABLE sources ADD COLUMN IF NOT EXISTS error_count INTEGER DEFAULT 0;
"
```

Also add to `migrate.sql` inside the sources table definition:

```sql
    error_count INTEGER DEFAULT 0,
```

- [ ] **Step 2: Update SourceRepository.update_last_fetched to track error_count**

In `repositories.py`, modify `update_last_fetched`:

```python
@staticmethod
def update_last_fetched(source_id: int, error: Optional[str] = None) -> bool:
    try:
        with get_db_cursor() as cursor:
            if error:
                cursor.execute(
                    """
                    UPDATE sources
                    SET last_fetched_at = NOW(),
                        fetch_error = %(error)s,
                        error_count = COALESCE(error_count, 0) + 1,
                        updated_at = NOW()
                    WHERE id = %(source_id)s
                    """,
                    {"source_id": source_id, "error": error},
                )
            else:
                cursor.execute(
                    """
                    UPDATE sources
                    SET last_fetched_at = NOW(),
                        fetch_error = NULL,
                        error_count = 0,
                        updated_at = NOW()
                    WHERE id = %(source_id)s
                    """,
                    {"source_id": source_id},
                )
            return True
    except Exception as e:
        print(f"Error updating last_fetched for source {source_id}: {e}")
        return False
```

- [ ] **Step 3: Call update_last_fetched from gather pipeline**

In `gather.py`, after `process_single_feed` returns, call `SourceRepository.update_last_fetched()` with the result. This wiring happens in the pipeline run handler in `api_server.py` — after the gather step, iterate over feed results and update each source's last_fetched_at.

- [ ] **Step 4: Add health indicators to Sources page**

In `frontend/src/app/sources/page.tsx`, update the source list item to show:
- Green dot: `fetch_error` is null
- Yellow dot: `fetch_error` is set but `error_count < 3`
- Red dot: `error_count >= 3`
- Show `last_fetched_at` as relative time ("2h ago")
- Show category badge

- [ ] **Step 5: Commit**

```bash
git add scripts/migrate.sql services/nlp_py/repositories.py services/nlp_py/pipeline/gather.py services/nlp_py/api_server.py frontend/src/app/sources/page.tsx
git commit -m "feat: feed health monitoring with error tracking and UI indicators"
```

---

### Task 9: Add Pipeline Run History

**Files:**
- Modify: `scripts/migrate.sql` (add pipeline_runs table)
- Modify: `services/nlp_py/repositories.py` (add PipelineRunRepository)
- Modify: `services/nlp_py/api_server.py` (log pipeline runs, add history endpoint)
- Modify: `frontend/src/app/pipeline/page.tsx` (show run history)

- [ ] **Step 1: Create pipeline_runs table**

```bash
docker compose exec -T postgres psql -U news_user -d news_ai -c "
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running',
    headlines_gathered INTEGER DEFAULT 0,
    headlines_inserted INTEGER DEFAULT 0,
    feeds_success INTEGER DEFAULT 0,
    feeds_failed INTEGER DEFAULT 0,
    duration_ms INTEGER,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at ON pipeline_runs(started_at);
"
```

Also add this to `scripts/migrate.sql`.

- [ ] **Step 2: Add PipelineRunRepository**

In `repositories.py`, add:

```python
class PipelineRunRepository:
    @staticmethod
    def create_run() -> Optional[int]:
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    "INSERT INTO pipeline_runs (started_at, status) VALUES (NOW(), 'running') RETURNING id"
                )
                row = cursor.fetchone()
                return row["id"] if row else None
        except Exception as e:
            print(f"Error creating pipeline run: {e}")
            return None

    @staticmethod
    def complete_run(run_id: int, stats: Dict[str, Any], error: Optional[str] = None):
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """UPDATE pipeline_runs
                       SET completed_at = NOW(),
                           status = %(status)s,
                           headlines_gathered = %(gathered)s,
                           headlines_inserted = %(inserted)s,
                           feeds_success = %(feeds_ok)s,
                           feeds_failed = %(feeds_err)s,
                           duration_ms = %(duration)s,
                           error = %(error)s
                       WHERE id = %(run_id)s""",
                    {
                        "run_id": run_id,
                        "status": "error" if error else "completed",
                        "gathered": stats.get("gathered", 0),
                        "inserted": stats.get("inserted", 0),
                        "feeds_ok": stats.get("feeds_success", 0),
                        "feeds_err": stats.get("feeds_failed", 0),
                        "duration": stats.get("duration_ms", 0),
                        "error": error,
                    },
                )
        except Exception as e:
            print(f"Error completing pipeline run: {e}")

    @staticmethod
    def get_recent(limit: int = 10) -> List[Dict]:
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT %s",
                    (limit,),
                )
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching pipeline runs: {e}")
            return []
```

- [ ] **Step 3: Wire pipeline run tracking into api_server.py**

In the full pipeline run handler, call `PipelineRunRepository.create_run()` at start and `complete_run()` at end with stats. Add a `GET /api/pipeline/history` endpoint.

- [ ] **Step 4: Show run history on Pipeline page**

Add a "Recent Runs" section below the logs panel showing the last 10 runs with timestamp, duration, headlines gathered, and status badge (completed/error).

- [ ] **Step 5: Commit**

```bash
git add scripts/migrate.sql services/nlp_py/repositories.py services/nlp_py/api_server.py frontend/src/app/pipeline/page.tsx
git commit -m "feat: pipeline run history with DB tracking and UI"
```

---

### Task 10: Build Frontend Insights Page

**Files:**
- Create: `frontend/src/app/insights/page.tsx`
- Modify: `frontend/src/lib/api.ts` (add InsightsSummary type + api.insights methods)
- Modify: `frontend/src/components/sidebar-nav.tsx` (add Insights nav item)

- [ ] **Step 1: Add types and API methods to api.ts**

```typescript
export interface InsightsSummary {
  period: string;
  top_headlines_by_category: Record<string, { title: string; url: string; topic: string; topic_confidence: number; source_name: string }[]>;
  topic_counts: { topic: string; count: number }[];
  category_volume: { category: string; count: number }[];
  top_clusters: { label: string; event_type: string; headline_count: number }[];
  feed_health: { healthy: number; erroring: number; inactive: number };
}

// In the api object, add:
  insights: {
    summary(period: string = "24h"): Promise<InsightsSummary> {
      return request(`/api/insights/summary?period=${period}`);
    },
    category(category: string, period: string = "24h"): Promise<any> {
      return request(`/api/insights/category/${category}?period=${period}`);
    },
  },
```

- [ ] **Step 2: Create insights/page.tsx**

Build a page that:
- Fetches `/api/insights/summary` for current period (24h default)
- Shows a "Feed Health" bar (X healthy, Y erroring, Z inactive)
- Shows "Top Clusters" as a ranked list
- Shows "Category Volume" as horizontal bars
- Shows "Top Headlines by Category" as expandable sections
- Has a "Copy as JSON" button that copies the raw API response to clipboard

- [ ] **Step 3: Add Insights to sidebar navigation**

In `sidebar-nav.tsx`, add a nav item for `/insights` between Analytics and Pipeline, with a Lightbulb or Brain icon from lucide-react.

- [ ] **Step 4: Verify in browser**

Open http://localhost:3000/insights — should show structured financial intelligence summary.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/insights/page.tsx frontend/src/lib/api.ts frontend/src/components/sidebar-nav.tsx
git commit -m "feat: add Insights page with AI-agent-friendly structured summary"
```
