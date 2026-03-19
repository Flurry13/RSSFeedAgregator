# Sentiment & Signal Extraction — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add keyword-based sentiment analysis (bullish/bearish/neutral) to every headline, with filtering in the API, sentiment charts in analytics, and sentiment breakdowns in the Insights page for AI agent consumption.

**Architecture:** New `sentiment.py` module follows the same keyword-matching pattern as `classify.py`. Sentiment runs as a third concurrent stage in `parallel_pipeline.py`. Results stored as two new columns on headlines, exposed via existing API endpoints with new filter params and aggregation fields.

**Tech Stack:** Python 3.11 (Flask), PostgreSQL 15, Next.js 15, TypeScript, Recharts

**Spec:** `docs/superpowers/specs/2026-03-19-sentiment-signal-extraction-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `services/nlp_py/pipeline/sentiment.py` | Create | Keyword-based sentiment classifier |
| `services/nlp_py/pipeline/parallel_pipeline.py` | Modify | Add 3rd concurrent stage |
| `services/nlp_py/repositories.py` | Modify | update_sentiment method, sentiment filter in get_paginated, sentiment queries in analytics + insights |
| `services/nlp_py/api_server.py` | Modify | Persist sentiment in pipeline, add sentiment filter param |
| `scripts/migrate.sql` | Modify | Add sentiment columns to headlines CREATE TABLE |
| `frontend/src/lib/api.ts` | Modify | Add sentiment fields to interfaces |
| `frontend/src/app/page.tsx` | Modify | Sentiment badges + filter |
| `frontend/src/app/analytics/page.tsx` | Modify | Sentiment chart |
| `frontend/src/app/insights/page.tsx` | Modify | Market Sentiment section |

---

## Chunk 1: Backend — Sentiment Module + Pipeline + Schema

### Task 1: Create sentiment.py module

**Files:**
- Create: `services/nlp_py/pipeline/sentiment.py`

- [ ] **Step 1: Create the sentiment analyzer module**

Create `services/nlp_py/pipeline/sentiment.py` with bullish/bearish keyword dicts and the `analyze_sentiment` function. Follow the exact pattern of `classify.py` — pre-compiled regex patterns, case-insensitive matching:

```python
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

# Pre-compile patterns
_BULLISH_PATTERNS = [re.compile(re.escape(kw.strip()), re.IGNORECASE) for kw in BULLISH_KEYWORDS]
_BEARISH_PATTERNS = [re.compile(re.escape(kw.strip()), re.IGNORECASE) for kw in BEARISH_KEYWORDS]


def analyze_sentiment(text: str) -> Dict[str, Any]:
    """
    Analyze sentiment of a financial headline.

    Returns:
        {"sentiment": "bullish"|"bearish"|"neutral", "sentiment_score": float}
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
```

- [ ] **Step 2: Commit**

```bash
git add services/nlp_py/pipeline/sentiment.py
git commit -m "feat: add keyword-based sentiment analyzer module"
```

---

### Task 2: Add sentiment columns to DB schema

**Files:**
- Modify: `scripts/migrate.sql`

- [ ] **Step 1: Add columns to running database**

```bash
docker compose exec -T postgres psql -U news_user -d news_ai -c "
ALTER TABLE headlines ADD COLUMN IF NOT EXISTS sentiment TEXT;
ALTER TABLE headlines ADD COLUMN IF NOT EXISTS sentiment_score FLOAT;
CREATE INDEX IF NOT EXISTS idx_headlines_sentiment ON headlines(sentiment);
"
```

- [ ] **Step 2: Update migrate.sql CREATE TABLE headlines**

Add `sentiment TEXT,` and `sentiment_score FLOAT,` after the `event_type TEXT,` line, and add `CREATE INDEX idx_headlines_sentiment ON headlines(sentiment);` with the other indexes.

- [ ] **Step 3: Commit**

```bash
git add scripts/migrate.sql
git commit -m "schema: add sentiment and sentiment_score columns to headlines"
```

---

### Task 3: Add sentiment to parallel pipeline

**Files:**
- Modify: `services/nlp_py/pipeline/parallel_pipeline.py`

- [ ] **Step 1: Add sentiment_batch_wrapper function**

Add after `extract_batch_wrapper` (after line 62):

```python
def sentiment_batch_wrapper(headlines: List[Dict]) -> List[Dict]:
    """Analyze sentiment for each headline."""
    from sentiment import analyze_sentiment

    results = []
    for h in headlines:
        text = h.get("title") or h.get("text") or ""
        try:
            result = analyze_sentiment(text)
            results.append(result)
        except Exception as e:
            logger.warning("sentiment_batch_wrapper error for %r: %s", text[:60], e)
            results.append({"sentiment": "neutral", "sentiment_score": 0.5})
    return results
```

- [ ] **Step 2: Update run_parallel_ml signature and executor**

Add `sentiment_fn` parameter, change `max_workers` from 2 to 3, add third future, add fallback:

```python
def run_parallel_ml(
    headlines: List[Dict],
    classify_fn: Callable[[List[Dict]], List[Dict]] = classify_batch_wrapper,
    extract_fn: Callable[[List[Dict]], List[Dict]] = extract_batch_wrapper,
    sentiment_fn: Callable[[List[Dict]], List[Dict]] = sentiment_batch_wrapper,
    progress_callback: Optional[Callable[..., None]] = None,
    **_kwargs,
) -> List[Dict]:
```

In the ThreadPoolExecutor, change `max_workers=2` to `max_workers=3` and add:
```python
        futures = {
            pool.submit(_run, "classify", classify_fn, headlines): "classify",
            pool.submit(_run, "extract", extract_fn, headlines): "extract",
            pool.submit(_run, "sentiment", sentiment_fn, headlines): "sentiment",
        }
```

Add fallback for sentiment in the exception handler:
```python
                elif stage_name == "sentiment":
                    stage_results["sentiment"] = [
                        {"sentiment": "neutral", "sentiment_score": 0.5} for _ in headlines
                    ]
```

Add sentiment to the merge block (after line 126):
```python
        merged.update(stage_results.get("sentiment", [{}] * len(headlines))[i])
```

- [ ] **Step 3: Commit**

```bash
git add services/nlp_py/pipeline/parallel_pipeline.py
git commit -m "feat: add sentiment as 3rd concurrent pipeline stage"
```

---

### Task 4: Persist sentiment + add API filter + analytics/insights queries

**Files:**
- Modify: `services/nlp_py/repositories.py`
- Modify: `services/nlp_py/api_server.py`

- [ ] **Step 1: Add HeadlineRepository.update_sentiment**

After `update_entities` method (around line 395), add:

```python
    @staticmethod
    def update_sentiment(headline_id: int, sentiment: str, score: float) -> bool:
        """Persist sentiment analysis result for a headline."""
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE headlines
                    SET sentiment = %(sentiment)s,
                        sentiment_score = %(score)s,
                        updated_at = NOW()
                    WHERE id = %(headline_id)s
                    """,
                    {"headline_id": headline_id, "sentiment": sentiment, "score": score},
                )
                return True
        except Exception as e:
            print(f"Error updating sentiment for headline {headline_id}: {e}")
            return False
```

- [ ] **Step 2: Add sentiment filter to HeadlineRepository.get_paginated**

In `get_paginated` (around line 253), add `sentiment: Optional[str] = None` to the parameter list. Add the filter condition:

```python
        if sentiment:
            conditions.append("h.sentiment = %(sentiment)s")
            params["sentiment"] = sentiment
```

- [ ] **Step 3: Add sentiment_distribution to AnalyticsRepository.get_analytics**

Add `"sentiment_distribution": []` to the initial result dict. After the daily volume query, add:

```python
                # Sentiment distribution
                cursor.execute(
                    """
                    SELECT sentiment, COUNT(*) AS count
                    FROM headlines
                    WHERE sentiment IS NOT NULL
                      AND created_at >= NOW() - %(interval)s::INTERVAL
                    GROUP BY sentiment
                    ORDER BY count DESC
                    """,
                    params,
                )
                result["sentiment_distribution"] = [dict(r) for r in cursor.fetchall()]
```

- [ ] **Step 4: Add sentiment fields to InsightsRepository.get_summary**

Add `"sentiment_breakdown": {}` and `"sentiment_by_category": {}` to the initial result dict. Add two queries inside the `with get_db_cursor()` block:

```python
                # Sentiment breakdown
                cursor.execute(
                    """
                    SELECT sentiment, COUNT(*) AS count
                    FROM headlines
                    WHERE sentiment IS NOT NULL
                      AND created_at >= NOW() - %(interval)s::INTERVAL
                    GROUP BY sentiment
                    """,
                    params,
                )
                senti_rows = cursor.fetchall()
                result["sentiment_breakdown"] = {
                    r["sentiment"]: r["count"] for r in senti_rows
                }

                # Sentiment by category
                cursor.execute(
                    """
                    SELECT s.category, h.sentiment, COUNT(*) AS count
                    FROM headlines h
                    JOIN sources s ON h.source_id = s.id
                    WHERE h.sentiment IS NOT NULL
                      AND h.created_at >= NOW() - %(interval)s::INTERVAL
                    GROUP BY s.category, h.sentiment
                    ORDER BY s.category
                    """,
                    params,
                )
                by_cat: Dict[str, Dict[str, int]] = {}
                for row in cursor.fetchall():
                    cat = row["category"]
                    by_cat.setdefault(cat, {"bullish": 0, "bearish": 0, "neutral": 0})
                    by_cat[cat][row["sentiment"]] = row["count"]
                result["sentiment_by_category"] = by_cat
```

- [ ] **Step 5: Persist sentiment in api_server.py pipeline loop**

In the Stage 4 persist loop (around line 467-471), after the `if h.get("entities"):` block, add:

```python
                if h.get("sentiment"):
                    HeadlineRepository.update_sentiment(
                        hid, h["sentiment"], h.get("sentiment_score", 0.5)
                    )
```

- [ ] **Step 6: Add sentiment param to headlines route**

In the `get_headlines` route handler (around line 87-96), add:
```python
    sentiment = request.args.get("sentiment")
```
And pass it to the `get_paginated` call:
```python
        sentiment=sentiment,
```

- [ ] **Step 7: Rebuild, run pipeline, verify**

```bash
docker compose up -d --build nlp_service
sleep 10
# Clear old data and re-run
docker compose exec -T postgres psql -U news_user -d news_ai -c "UPDATE headlines SET sentiment = NULL, sentiment_score = NULL;"
curl -s -X POST http://localhost:8081/api/run
sleep 45
# Check sentiment distribution
docker compose exec -T postgres psql -U news_user -d news_ai -c "SELECT sentiment, COUNT(*) FROM headlines WHERE sentiment IS NOT NULL GROUP BY sentiment ORDER BY count DESC;"
# Check insights
curl -s "http://localhost:8081/api/insights/summary?period=24h" | python3 -c "import json,sys; d=json.load(sys.stdin); print('Sentiment:', d.get('sentiment_breakdown')); print('By category:', list(d.get('sentiment_by_category',{}).keys())[:5])"
# Check filter
curl -s "http://localhost:8081/api/headlines?sentiment=bearish&limit=3" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Bearish headlines: {len(d.get(\"data\",[]))}')"
```

- [ ] **Step 8: Commit**

```bash
git add services/nlp_py/repositories.py services/nlp_py/api_server.py
git commit -m "feat: sentiment persistence, API filter, analytics + insights queries"
```

---

## Chunk 2: Frontend — Badges, Filter, Charts, Insights

### Task 5: Add sentiment to frontend types

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Update Headline interface**

Add to the Headline interface:
```typescript
  sentiment?: string;
  sentiment_score?: number;
```

- [ ] **Step 2: Update AnalyticsData interface**

Add:
```typescript
  sentiment_distribution: { sentiment: string; count: number }[];
```

- [ ] **Step 3: Update InsightsSummary interface**

Add:
```typescript
  sentiment_breakdown: Record<string, number>;
  sentiment_by_category: Record<string, { bullish: number; bearish: number; neutral: number }>;
```

- [ ] **Step 4: Add sentiment param to headlines.list**

In the `headlines.list` params, add `sentiment?: string` and include it in the query string builder.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat: add sentiment fields to frontend TypeScript interfaces"
```

---

### Task 6: Add sentiment badges and filter to Feed page

**Files:**
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Add sentiment badge helper and icons**

Import `TrendingUp`, `TrendingDown`, `Minus` from lucide-react. Add a helper:

```typescript
function sentimentBadge(sentiment?: string) {
  if (sentiment === "bullish")
    return <TrendingUp className="w-3.5 h-3.5 text-[#00ff88]" />;
  if (sentiment === "bearish")
    return <TrendingDown className="w-3.5 h-3.5 text-[#ff3333]" />;
  return <Minus className="w-3.5 h-3.5 text-[#555]" />;
}
```

- [ ] **Step 2: Add sentiment badge to headline cards**

In the headline card JSX, next to the topic badge, add:
```tsx
{sentimentBadge(headline.sentiment)}
```

- [ ] **Step 3: Add sentiment filter state and dropdown**

Add state: `const [sentiment, setSentiment] = useState("all");`

Add a Select dropdown for sentiment (All / Bullish / Bearish / Neutral) alongside the existing topic filter.

Pass `sentiment: sentiment !== "all" ? sentiment : undefined` to the `api.headlines.list()` call.

Include `sentiment` in the useEffect/useCallback dependency array for fetching.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/page.tsx
git commit -m "feat: sentiment arrow badges and filter on feed page"
```

---

### Task 7: Add Sentiment Distribution chart to Analytics

**Files:**
- Modify: `frontend/src/app/analytics/page.tsx`

- [ ] **Step 1: Add SentimentChart component**

Add after the existing chart components:

```typescript
const SENTIMENT_COLORS: Record<string, string> = {
  bullish: "#00ff88",
  bearish: "#ff3333",
  neutral: "#666",
};

function SentimentChart({ data }: { data: { sentiment: string; count: number }[] }) {
  const total = data.reduce((sum, d) => sum + d.count, 0);
  return (
    <div>
      <h2 className="font-mono text-[10px] uppercase tracking-widest text-[#555] mb-4">
        Sentiment Distribution
      </h2>
      {total === 0 ? (
        <p className="text-[#555] font-mono text-xs">No sentiment data yet.</p>
      ) : (
        <div>
          <div className="flex h-8 w-full overflow-hidden border-2 border-[#333]">
            {data.map((d) => (
              <div
                key={d.sentiment}
                style={{
                  width: `${(d.count / total) * 100}%`,
                  backgroundColor: SENTIMENT_COLORS[d.sentiment] ?? "#444",
                }}
              />
            ))}
          </div>
          <div className="flex gap-6 mt-3 font-mono text-[11px]">
            {data.map((d) => (
              <div key={d.sentiment} className="flex items-center gap-2">
                <span
                  className="w-2 h-2 shrink-0"
                  style={{ background: SENTIMENT_COLORS[d.sentiment] ?? "#444" }}
                />
                <span className="text-[#777] uppercase">{d.sentiment}</span>
                <span className="font-bold" style={{ color: SENTIMENT_COLORS[d.sentiment] ?? "#777" }}>
                  {d.count}
                </span>
                <span className="text-[#555]">({Math.round((d.count / total) * 100)}%)</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add SentimentChart to the render section**

After the TopicsChart card, add:
```tsx
<div className="border-2 border-[#333] bg-[#111] p-5 animate-fade-in-up" style={{ animationDelay: "30ms" }}>
  <SentimentChart data={data.sentiment_distribution ?? []} />
</div>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/analytics/page.tsx
git commit -m "feat: sentiment distribution chart on analytics page"
```

---

### Task 8: Add Market Sentiment section to Insights page

**Files:**
- Modify: `frontend/src/app/insights/page.tsx`

- [ ] **Step 1: Add MarketSentiment component**

Add a component that renders:
- Overall sentiment as a horizontal stacked bar (green=bullish, red=bearish, gray=neutral)
- Label: "Bullish X | Bearish Y | Neutral Z"
- Sentiment by Category: a list showing each source category with inline mini-bars for bullish/bearish/neutral counts
- Highlight most bullish category (green text) and most bearish category (red text)

```typescript
function MarketSentiment({
  breakdown,
  byCategory,
}: {
  breakdown: Record<string, number>;
  byCategory: Record<string, { bullish: number; bearish: number; neutral: number }>;
}) {
  const total = (breakdown.bullish ?? 0) + (breakdown.bearish ?? 0) + (breakdown.neutral ?? 0);

  return (
    <div className="border-2 border-[#333] bg-[#111] p-5 animate-fade-in-up">
      <h2 className="font-mono text-[10px] uppercase tracking-widest text-[#555] mb-4">
        Market Sentiment
      </h2>
      {total === 0 ? (
        <p className="text-[#555] font-mono text-xs">No sentiment data yet.</p>
      ) : (
        <>
          {/* Overall bar */}
          <div className="flex h-6 w-full overflow-hidden border border-[#333] mb-2">
            <div style={{ width: `${((breakdown.bullish ?? 0) / total) * 100}%`, backgroundColor: "#00ff88" }} />
            <div style={{ width: `${((breakdown.bearish ?? 0) / total) * 100}%`, backgroundColor: "#ff3333" }} />
            <div style={{ width: `${((breakdown.neutral ?? 0) / total) * 100}%`, backgroundColor: "#444" }} />
          </div>
          <div className="flex gap-4 font-mono text-[11px] mb-6">
            <span className="text-[#00ff88] font-bold">Bullish {breakdown.bullish ?? 0}</span>
            <span className="text-[#ff3333] font-bold">Bearish {breakdown.bearish ?? 0}</span>
            <span className="text-[#666] font-bold">Neutral {breakdown.neutral ?? 0}</span>
          </div>

          {/* By category */}
          <h3 className="font-mono text-[10px] uppercase tracking-widest text-[#555] mb-3">
            By Category
          </h3>
          <div className="space-y-2">
            {Object.entries(byCategory)
              .sort(([, a], [, b]) => (b.bullish + b.bearish + b.neutral) - (a.bullish + a.bearish + a.neutral))
              .map(([cat, counts]) => {
                const catTotal = counts.bullish + counts.bearish + counts.neutral;
                return (
                  <div key={cat} className="flex items-center gap-3 font-mono text-[11px]">
                    <span className="text-[#777] uppercase w-28 shrink-0">{cat.replace('_', ' ')}</span>
                    <div className="flex h-3 flex-1 overflow-hidden border border-[#333]">
                      <div style={{ width: `${(counts.bullish / catTotal) * 100}%`, backgroundColor: "#00ff88" }} />
                      <div style={{ width: `${(counts.bearish / catTotal) * 100}%`, backgroundColor: "#ff3333" }} />
                      <div style={{ width: `${(counts.neutral / catTotal) * 100}%`, backgroundColor: "#333" }} />
                    </div>
                    <span className="text-[#555] w-10 text-right">{catTotal}</span>
                  </div>
                );
              })}
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add MarketSentiment to the page render**

Place it above the Feed Health section:
```tsx
<MarketSentiment
  breakdown={data.sentiment_breakdown ?? {}}
  byCategory={data.sentiment_by_category ?? {}}
/>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/insights/page.tsx
git commit -m "feat: market sentiment section on insights page with per-category breakdown"
```
