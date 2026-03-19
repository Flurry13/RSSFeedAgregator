# Slice 4: Prediction Markets Intelligence — Design Spec

**Goal:** Surface prediction market signals by cross-referencing prediction market headlines with equities/macro/crypto headlines, detecting sentiment divergences, and providing a dedicated browsing page plus structured API for AI agents.

**Depends on:** Slices 1-3 completed (financial feeds, sentiment, settings/scheduler).

---

## 1. Backend — Cross-Category Matching + Divergence Detection

**New method: `InsightsRepository.get_prediction_signals(period)`**

Located in `services/nlp_py/repositories.py`. The method:

1. **Fetch prediction market headlines** for the period — all headlines where the source category is `prediction_markets`, with sentiment, topic, title, url, source_name.

2. **Fetch related headlines from other categories** — for each prediction market headline, find headlines from other categories (equities, macro, crypto, etc.) within the same period that share significant words. Implementation:
   - Extract significant words from the PM headline (words > 3 chars, excluding common stop words like "the", "and", "for", "with", "from", "that", "this", "have", "will", "been", "more", "about")
   - Query headlines from non-prediction_markets sources
   - Score each by counting shared significant words with the PM headline
   - Return top 3 matches per PM headline (minimum 2 shared words to qualify)

   This matching happens in Python after fetching both sets from DB — not as a SQL join (word overlap matching is impractical in SQL without full-text search vectors).

3. **Detect sentiment divergences** — for each PM headline that has related headlines, compare:
   - PM headline sentiment vs majority sentiment of related headlines
   - If they disagree (e.g., PM = bearish, majority of related = bullish), flag as divergence
   - Divergence object: `{pm_headline, related_headlines, pm_sentiment, related_sentiment, divergence_type: "pm_bearish_market_bullish" | "pm_bullish_market_bearish"}`

**Return structure:**
```json
{
  "period": "24h",
  "prediction_headlines": [...],
  "cross_references": [
    {
      "pm_headline": {title, url, sentiment, source_name},
      "related": [{title, url, sentiment, source_name, category, shared_words}],
    }
  ],
  "divergences": [
    {
      "pm_headline": {title, url, sentiment, source_name},
      "related_headlines": [{title, url, sentiment, source_name, category}],
      "pm_sentiment": "bearish",
      "market_sentiment": "bullish",
      "type": "pm_bearish_market_bullish"
    }
  ],
  "stats": {
    "pm_headline_count": N,
    "cross_references_found": N,
    "divergences_found": N
  }
}
```

**New endpoint: `GET /api/insights/predictions?period=24h`**

In `services/nlp_py/api_server.py`, add:
```python
@app.route("/api/insights/predictions")
def get_prediction_signals():
    period = request.args.get("period", "24h")
    if period not in ("24h", "7d", "30d"):
        period = "24h"
    return jsonify(InsightsRepository.get_prediction_signals(period))
```

### Stop Words for Matching

```python
STOP_WORDS = {
    'the', 'and', 'for', 'with', 'from', 'that', 'this', 'have', 'will',
    'been', 'more', 'about', 'into', 'than', 'also', 'over', 'after',
    'its', 'are', 'was', 'were', 'has', 'had', 'but', 'not', 'what',
    'all', 'can', 'her', 'his', 'one', 'our', 'out', 'you', 'new',
    'could', 'would', 'should', 'their', 'there', 'when', 'who', 'how',
    'may', 'says', 'said', 'just', 'like', 'make', 'does',
}
```

### Performance Notes

- Prediction market sources are only 4 feeds (~50 headlines per run), so the cross-referencing loop is O(50 × 2000) word comparisons — fast enough without indexing
- Word extraction uses simple `split()` + lowercase + length filter, no NLP needed
- The method runs the matching in Python, not SQL, to keep it simple

---

## 2. Frontend — Predictions Page

**New file: `frontend/src/app/predictions/page.tsx`**

Three-panel layout:

### Panel 1: Prediction Market Headlines
- Paginated list of headlines from prediction_markets sources
- Each shows: title (linked), source name, sentiment badge, topic badge
- Same card styling as feed page

### Panel 2: Cross-References
- For each PM headline that has matches, show an expandable card:
  - PM headline at top (highlighted border)
  - Related headlines below with category badge, sentiment badge, shared word count
- Only show PM headlines that have at least 1 cross-reference

### Panel 3: Divergence Alerts
- Prominently styled section at the top of the page
- Each divergence shows:
  - PM headline (with sentiment arrow)
  - "vs" divider
  - Related headlines (with opposing sentiment arrows)
  - Divergence type badge: "PM BEARISH / MARKET BULLISH" (red/green) or vice versa
- If no divergences: "No sentiment divergences detected in this period"

### Layout
- Period tabs at top (24h / 7d / 30d)
- Divergence alerts panel first (most important)
- Then two-column layout: PM headlines on left, cross-references on right
- Or single column with all three sections stacked if simpler

### Data Flow
- On mount + period change: `GET /api/insights/predictions?period=X`
- Single API call returns all three datasets

---

## 3. Frontend Types

**New interface in `frontend/src/lib/api.ts`:**

```typescript
export interface PredictionSignals {
  period: string;
  prediction_headlines: {
    title: string;
    url: string;
    sentiment: string;
    sentiment_score: number;
    source_name: string;
    topic: string;
  }[];
  cross_references: {
    pm_headline: { title: string; url: string; sentiment: string; source_name: string };
    related: { title: string; url: string; sentiment: string; source_name: string; category: string; shared_words: number }[];
  }[];
  divergences: {
    pm_headline: { title: string; url: string; sentiment: string; source_name: string };
    related_headlines: { title: string; url: string; sentiment: string; source_name: string; category: string }[];
    pm_sentiment: string;
    market_sentiment: string;
    type: string;
  }[];
  stats: {
    pm_headline_count: number;
    cross_references_found: number;
    divergences_found: number;
  };
}
```

**New API method:**
```typescript
insights: {
  // ... existing methods ...
  predictions(period: string = "24h"): Promise<PredictionSignals> {
    return request(`/api/insights/predictions?period=${period}`);
  },
},
```

---

## 4. Insights Page — Prediction Markets Section

Add a "Prediction Markets" section to `frontend/src/app/insights/page.tsx`, placed after Top Clusters:

- Stats line: "X prediction market headlines | Y cross-references | Z divergences"
- If divergences > 0: show the top 3 divergences inline with PM headline vs market headline
- Link: "View all →" linking to `/predictions`

Uses `data.prediction_signals` if we add it to the insights summary, OR makes a separate fetch to `/api/insights/predictions`. Separate fetch is cleaner — avoids bloating the summary endpoint.

---

## 5. Sidebar Nav Update

In `frontend/src/components/sidebar-nav.tsx`:
- Add `{ label: "Predictions", href: "/predictions", icon: Crosshair }` between Insights and Pipeline
- Import `Crosshair` from lucide-react

---

## Non-Goals (Deferred)

- Real-time prediction market odds/prices (would require API integration with Polymarket/Kalshi APIs, not RSS)
- Historical divergence tracking over time
- Automated trading signals
- NLP-based semantic matching (word overlap is sufficient for v1)
