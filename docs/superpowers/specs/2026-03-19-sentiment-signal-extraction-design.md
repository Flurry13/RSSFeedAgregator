# Slice 2: Sentiment & Signal Extraction — Design Spec

**Goal:** Add headline-level sentiment analysis (bullish/bearish/neutral) with keyword-based classification, exposing sentiment as a filterable dimension across the API, frontend, and Insights page for AI agent consumption.

**Depends on:** Slice 1 (Financial Intelligence Foundation) — completed.

---

## 1. Sentiment Classifier Module

**New file:** `services/nlp_py/pipeline/sentiment.py`

Follows the same pattern as `classify.py` — keyword dictionaries with regex pattern matching.

### Keyword Dictionaries

**BULLISH_KEYWORDS** (~60 terms): Financial headline words indicating positive market sentiment, price appreciation, or business strength.

Categories of bullish terms:
- Price movement: surge, rally, gain, soar, jump, climb, spike, rebound, recover, bounce
- Performance: beat, outperform, exceed, record high, all-time high, strong, boom, robust
- Ratings/actions: upgrade, buy, overweight, accumulate, bullish, optimistic
- Business: growth, profit, revenue up, expansion, hiring, demand, breakthrough
- Market: risk-on, momentum, breakout, support, bid up

**BEARISH_KEYWORDS** (~60 terms): Financial headline words indicating negative market sentiment, price depreciation, or business weakness.

Categories of bearish terms:
- Price movement: crash, plunge, drop, fall, decline, tumble, sink, selloff, collapse, slump
- Performance: miss, underperform, loss, weak, worst, lowest, record low, disappointing
- Ratings/actions: downgrade, sell, underweight, bearish, pessimistic, cautious
- Business: layoff, restructuring, bankruptcy, default, writedown, impairment, shutdown
- Market: risk-off, correction, bubble, contagion, panic, flight to safety, margin call

### Scoring Algorithm

```
bullish_hits = count of bullish keyword matches in headline text
bearish_hits = count of bearish keyword matches in headline text
total_hits = bullish_hits + bearish_hits

if total_hits == 0:
    sentiment = "neutral", score = 0.5
elif bullish_hits > bearish_hits:
    sentiment = "bullish", score = 0.5 + 0.5 * (bullish_hits - bearish_hits) / total_hits
elif bearish_hits > bullish_hits:
    sentiment = "bearish", score = 0.5 + 0.5 * (bearish_hits - bullish_hits) / total_hits
else:
    sentiment = "neutral", score = 0.5
```

Score range: 0.5 (weak signal) to 1.0 (strong signal). The label indicates direction; the score indicates strength.

### API

```python
def analyze_sentiment(text: str) -> Dict[str, Any]:
    """Returns {"sentiment": "bullish"|"bearish"|"neutral", "sentiment_score": float}"""
```

---

## 2. Database Schema Changes

**For the running database**, add columns via ALTER:
```sql
ALTER TABLE headlines ADD COLUMN IF NOT EXISTS sentiment TEXT;
ALTER TABLE headlines ADD COLUMN IF NOT EXISTS sentiment_score FLOAT;
CREATE INDEX IF NOT EXISTS idx_headlines_sentiment ON headlines(sentiment);
```

**For `scripts/migrate.sql`**, add the columns directly inside the `CREATE TABLE headlines` block (after `event_type TEXT,`):
```sql
    sentiment TEXT,
    sentiment_score FLOAT,
```
And add the index alongside existing `CREATE INDEX` statements:
```sql
CREATE INDEX idx_headlines_sentiment ON headlines(sentiment);
```

Note: `migrate.sql` is a destructive DROP/CREATE script, not incremental. ALTER TABLE statements must NOT be added to it — columns go in the CREATE TABLE definition.

---

## 3. Pipeline Integration

### parallel_pipeline.py — Add third concurrent stage

The `run_parallel_ml` function (lines 69-75) currently has a hardcoded 2-stage design with `classify_fn` and `extract_fn` parameters. It needs to be extended to 3 stages:

1. **Add `sentiment_fn` parameter** to `run_parallel_ml` signature (default: `sentiment_batch_wrapper`)
2. **Add `sentiment_batch_wrapper()` function** following the pattern of `classify_batch_wrapper` — iterates headlines, calls `analyze_sentiment(h["title"])`, and merges `sentiment` + `sentiment_score` into each headline dict
3. **Add third future** to the ThreadPoolExecutor futures dict: `"sentiment": executor.submit(sentiment_fn, headlines)`
4. **Add third fallback** in the error-recovery block (lines 112-119) for the `"sentiment"` stage

### repositories.py — Persist sentiment

Add `HeadlineRepository.update_sentiment(headline_id, sentiment, sentiment_score)`:
```python
@staticmethod
def update_sentiment(headline_id: int, sentiment: str, score: float):
    with get_db_cursor() as cursor:
        cursor.execute(
            "UPDATE headlines SET sentiment = %s, sentiment_score = %s WHERE id = %s",
            (sentiment, score, headline_id),
        )
```

### api_server.py — Stage 4 persist loop

In the persist loop (around lines 462-471), add a third conditional block after the existing topic and entities blocks:
```python
if h.get("sentiment"):
    HeadlineRepository.update_sentiment(db_id, h["sentiment"], h.get("sentiment_score", 0.5))
```

---

## 4. API Endpoints — Changes

### GET /api/headlines

Add `sentiment` as a filterable query parameter:
- `?sentiment=bullish` — only bullish headlines
- `?sentiment=bearish` — only bearish headlines
- `?sentiment=neutral` — only neutral headlines

Three changes needed:
1. **api_server.py** `get_headlines` route: add `sentiment = request.args.get("sentiment")` and pass to `get_paginated`
2. **repositories.py** `HeadlineRepository.get_paginated`: add `sentiment: Optional[str] = None` parameter, add WHERE clause `h.sentiment = %(sentiment)s` when set
3. **api.ts** `headlines.list()` params object: add `sentiment?: string`

The headline response objects include `sentiment` and `sentiment_score` fields (these come from the DB columns automatically via `SELECT *`).

### GET /api/analytics

Add `sentiment_distribution` to the analytics response:

```json
{
  "sentiment_distribution": [
    {"sentiment": "bullish", "count": 450},
    {"sentiment": "bearish", "count": 320},
    {"sentiment": "neutral", "count": 230}
  ]
}
```

### GET /api/insights/summary

Add two new fields to `InsightsRepository.get_summary()`:

**`sentiment_breakdown`** — simple GROUP BY:
```sql
SELECT sentiment, COUNT(*) as count
FROM headlines
WHERE created_at >= NOW() - %(interval)s::INTERVAL
  AND sentiment IS NOT NULL
GROUP BY sentiment
```
Then reshape in Python: `{"bullish": N, "bearish": N, "neutral": N}`

**`sentiment_by_category`** — two-dimensional GROUP BY:
```sql
SELECT s.category, h.sentiment, COUNT(*) as count
FROM headlines h
JOIN sources s ON h.source_id = s.id
WHERE h.created_at >= NOW() - %(interval)s::INTERVAL
  AND h.sentiment IS NOT NULL
GROUP BY s.category, h.sentiment
ORDER BY s.category
```
Then reshape in Python (similar to existing `top_headlines_by_category` dict-building pattern at lines 759-775):
```python
by_cat: Dict[str, Dict[str, int]] = {}
for row in rows:
    cat = row["category"]
    by_cat.setdefault(cat, {"bullish": 0, "bearish": 0, "neutral": 0})
    by_cat[cat][row["sentiment"]] = row["count"]
result["sentiment_by_category"] = by_cat
```

Output shape:
```json
{
  "sentiment_breakdown": {"bullish": 450, "bearish": 320, "neutral": 230},
  "sentiment_by_category": {
    "crypto": {"bullish": 80, "bearish": 95, "neutral": 36},
    "equities": {"bullish": 200, "bearish": 100, "neutral": 80}
  }
}
```

This is the key AI-agent signal — enables queries like "which categories are most bearish right now?"

---

## 5. Frontend — Feed Page Sentiment Badges

In `frontend/src/app/page.tsx`:

- Each headline card gets a sentiment arrow badge:
  - Bullish: green up-arrow icon
  - Bearish: red down-arrow icon
  - Neutral: gray dash icon
- Badge appears next to the topic badge
- Add sentiment filter alongside existing topic filter (All / Bullish / Bearish / Neutral)

### Headline interface update

In `frontend/src/lib/api.ts`, add to the Headline interface:
```typescript
sentiment?: string;
sentiment_score?: number;
```

---

## 6. Frontend — Analytics Sentiment Chart

In `frontend/src/app/analytics/page.tsx`:

- New `SentimentChart` component showing a horizontal stacked bar or pie chart:
  - Green segment = bullish count
  - Red segment = bearish count
  - Gray segment = neutral count
- Placed after the Topic Distribution chart
- Uses the `sentiment_distribution` field from the analytics API

### AnalyticsData interface update

```typescript
sentiment_distribution: { sentiment: string; count: number }[];
```

---

## 7. Frontend — Insights Sentiment Section

In `frontend/src/app/insights/page.tsx`:

- New "Market Sentiment" section at the top of the page (above Feed Health):
  - Horizontal bar showing overall sentiment ratio (green/red/gray proportional segments)
  - Overall label: "Bullish 450 | Bearish 320 | Neutral 230"
- Below: "Sentiment by Category" — table or list showing each source category with its bullish/bearish/neutral breakdown
  - Highlight the most bearish category with a red accent
  - Highlight the most bullish category with a green accent

### InsightsSummary interface update

```typescript
sentiment_breakdown: { bullish: number; bearish: number; neutral: number };
sentiment_by_category: Record<string, { bullish: number; bearish: number; neutral: number }>;
```

---

## Non-Goals (Deferred)

- ML-based sentiment (finBERT, etc.) — keyword-based is sufficient for v1
- Sentiment time-series / trends over time — can be added in a future slice
- Per-entity sentiment (e.g., "Apple sentiment is bearish") — too complex for now
- Sentiment alerts/notifications — requires scheduler infrastructure (Slice 3)
