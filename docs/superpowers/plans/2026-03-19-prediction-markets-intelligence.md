# Prediction Markets Intelligence — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cross-reference prediction market headlines with equities/macro/crypto to detect sentiment divergences, with a dedicated predictions page and structured API for AI agents.

**Architecture:** New `get_prediction_signals()` method fetches PM headlines and cross-references them with other categories via word overlap matching in Python. Divergences detected by comparing PM sentiment vs majority sentiment of related headlines. New `/predictions` page with three panels. Insights page gets a PM summary section.

**Tech Stack:** Python 3.11 (Flask), PostgreSQL 15, Next.js 15, TypeScript

**Spec:** `docs/superpowers/specs/2026-03-19-prediction-markets-intelligence-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `services/nlp_py/repositories.py` | Modify | get_prediction_signals method |
| `services/nlp_py/api_server.py` | Modify | /api/insights/predictions route |
| `frontend/src/lib/api.ts` | Modify | PredictionSignals type + API method |
| `frontend/src/app/predictions/page.tsx` | Create | Predictions page |
| `frontend/src/app/insights/page.tsx` | Modify | PM summary section |
| `frontend/src/components/sidebar-nav.tsx` | Modify | Add Predictions nav item |

---

### Task 1: Backend — get_prediction_signals + API route

**Files:**
- Modify: `services/nlp_py/repositories.py`
- Modify: `services/nlp_py/api_server.py`

- [ ] **Step 1: Add get_prediction_signals to InsightsRepository**

Add to the InsightsRepository class in repositories.py. This is a larger method that:
1. Fetches PM headlines from DB
2. Fetches all other headlines from DB
3. Does word-overlap cross-referencing in Python
4. Detects sentiment divergences

```python
    STOP_WORDS = {
        'the', 'and', 'for', 'with', 'from', 'that', 'this', 'have', 'will',
        'been', 'more', 'about', 'into', 'than', 'also', 'over', 'after',
        'its', 'are', 'was', 'were', 'has', 'had', 'but', 'not', 'what',
        'all', 'can', 'her', 'his', 'one', 'our', 'out', 'you', 'new',
        'could', 'would', 'should', 'their', 'there', 'when', 'who', 'how',
        'may', 'says', 'said', 'just', 'like', 'make', 'does',
    }

    @staticmethod
    def _significant_words(text: str) -> set:
        if not text:
            return set()
        return {
            w for w in text.lower().split()
            if len(w) > 3 and w not in InsightsRepository.STOP_WORDS
        }

    @staticmethod
    def get_prediction_signals(period: str = "24h") -> Dict[str, Any]:
        interval = InsightsRepository._PERIOD_MAP.get(period, "24 hours")
        params = {"interval": interval}
        result: Dict[str, Any] = {
            "period": period,
            "prediction_headlines": [],
            "cross_references": [],
            "divergences": [],
            "stats": {"pm_headline_count": 0, "cross_references_found": 0, "divergences_found": 0},
        }
        try:
            with get_db_cursor() as cursor:
                # Fetch PM headlines
                cursor.execute("""
                    SELECT h.title, h.url, h.sentiment, h.sentiment_score,
                           h.topic, s.name AS source_name
                    FROM headlines h
                    JOIN sources s ON h.source_id = s.id
                    WHERE s.category = 'prediction_markets'
                      AND h.created_at >= NOW() - %(interval)s::INTERVAL
                    ORDER BY h.created_at DESC
                """, params)
                pm_headlines = [dict(r) for r in cursor.fetchall()]
                result["prediction_headlines"] = pm_headlines
                result["stats"]["pm_headline_count"] = len(pm_headlines)

                if not pm_headlines:
                    return result

                # Fetch other category headlines
                cursor.execute("""
                    SELECT h.title, h.url, h.sentiment, h.sentiment_score,
                           h.topic, s.name AS source_name, s.category
                    FROM headlines h
                    JOIN sources s ON h.source_id = s.id
                    WHERE s.category != 'prediction_markets'
                      AND h.created_at >= NOW() - %(interval)s::INTERVAL
                      AND h.sentiment IS NOT NULL
                    ORDER BY h.created_at DESC
                """, params)
                other_headlines = [dict(r) for r in cursor.fetchall()]

            # Pre-compute significant words for other headlines
            other_with_words = []
            for oh in other_headlines:
                oh["_words"] = InsightsRepository._significant_words(oh["title"])
                other_with_words.append(oh)

            # Cross-reference each PM headline
            cross_refs = []
            divergences = []

            for pm in pm_headlines:
                pm_words = InsightsRepository._significant_words(pm["title"])
                if not pm_words:
                    continue

                # Find related headlines by word overlap
                matches = []
                for oh in other_with_words:
                    shared = pm_words & oh["_words"]
                    if len(shared) >= 2:
                        matches.append({
                            "title": oh["title"],
                            "url": oh["url"],
                            "sentiment": oh["sentiment"],
                            "source_name": oh["source_name"],
                            "category": oh["category"],
                            "shared_words": len(shared),
                        })

                # Sort by shared words, take top 3
                matches.sort(key=lambda m: m["shared_words"], reverse=True)
                top_matches = matches[:3]

                if top_matches:
                    cross_refs.append({
                        "pm_headline": {
                            "title": pm["title"],
                            "url": pm["url"],
                            "sentiment": pm["sentiment"],
                            "source_name": pm["source_name"],
                        },
                        "related": top_matches,
                    })

                    # Check for sentiment divergence
                    pm_sent = pm.get("sentiment")
                    if pm_sent and pm_sent != "neutral":
                        related_sentiments = [m["sentiment"] for m in top_matches if m.get("sentiment") and m["sentiment"] != "neutral"]
                        if related_sentiments:
                            from collections import Counter
                            majority = Counter(related_sentiments).most_common(1)[0][0]
                            if majority != pm_sent:
                                divergences.append({
                                    "pm_headline": {
                                        "title": pm["title"],
                                        "url": pm["url"],
                                        "sentiment": pm["sentiment"],
                                        "source_name": pm["source_name"],
                                    },
                                    "related_headlines": top_matches,
                                    "pm_sentiment": pm_sent,
                                    "market_sentiment": majority,
                                    "type": f"pm_{pm_sent}_market_{majority}",
                                })

            result["cross_references"] = cross_refs
            result["divergences"] = divergences
            result["stats"]["cross_references_found"] = len(cross_refs)
            result["stats"]["divergences_found"] = len(divergences)

        except Exception as e:
            print(f"Error fetching prediction signals: {e}")
            result["error"] = str(e)
        return result
```

- [ ] **Step 2: Add API route**

In api_server.py, add after the insights routes:

```python
@app.route("/api/insights/predictions")
def get_prediction_signals():
    period = request.args.get("period", "24h")
    if period not in ("24h", "7d", "30d"):
        period = "24h"
    return jsonify(InsightsRepository.get_prediction_signals(period))
```

- [ ] **Step 3: Commit**

```bash
git add services/nlp_py/repositories.py services/nlp_py/api_server.py
git commit -m "feat: prediction market cross-referencing and divergence detection API"
```

---

### Task 2: Frontend types + API method

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add PredictionSignals interface**

```typescript
export interface PredictionSignals {
  period: string;
  prediction_headlines: {
    title: string; url: string; sentiment: string;
    sentiment_score: number; source_name: string; topic: string;
  }[];
  cross_references: {
    pm_headline: { title: string; url: string; sentiment: string; source_name: string };
    related: { title: string; url: string; sentiment: string; source_name: string; category: string; shared_words: number }[];
  }[];
  divergences: {
    pm_headline: { title: string; url: string; sentiment: string; source_name: string };
    related_headlines: { title: string; url: string; sentiment: string; source_name: string; category: string }[];
    pm_sentiment: string; market_sentiment: string; type: string;
  }[];
  stats: { pm_headline_count: number; cross_references_found: number; divergences_found: number };
}
```

- [ ] **Step 2: Add API method**

In the api.insights object, add:
```typescript
    predictions(period: string = "24h"): Promise<PredictionSignals> {
      return request(`/api/insights/predictions?period=${period}`);
    },
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat: PredictionSignals type and API method"
```

---

### Task 3: Create Predictions page

**Files:**
- Create: `frontend/src/app/predictions/page.tsx`

- [ ] **Step 1: Create the predictions page**

Three sections:
1. **Divergence Alerts** (top, most prominent) — red/green split cards showing PM headline vs market headline with opposing sentiments. If none: "No sentiment divergences detected"
2. **Cross-References** — expandable cards showing PM headline + related headlines with category badges and shared word count
3. **Prediction Market Headlines** — simple list of all PM headlines with sentiment badges

Period tabs (24h/7d/30d) at top. Stats bar showing headline count, cross-references, divergences.

Use the existing dark terminal styling. Sentiment colors: bullish=#00ff88, bearish=#ff3333, neutral=#666.

Import TrendingUp, TrendingDown, Minus from lucide-react for sentiment arrows.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/predictions/page.tsx
git commit -m "feat: predictions page with divergence alerts and cross-references"
```

---

### Task 4: Add PM section to Insights page + sidebar nav

**Files:**
- Modify: `frontend/src/app/insights/page.tsx`
- Modify: `frontend/src/components/sidebar-nav.tsx`

- [ ] **Step 1: Add PredictionMarkets section to insights page**

Add a new component and fetch `/api/insights/predictions` separately on the insights page. Place it after the Top Clusters section:

- Stats line: "X prediction market headlines | Y cross-references | Z divergences"
- If divergences > 0: show top 3 divergences inline
- Link: "View all →" linking to /predictions

- [ ] **Step 2: Add Predictions to sidebar nav**

In sidebar-nav.tsx, add `{ label: "Predictions", href: "/predictions", icon: Crosshair }` between Insights and Pipeline. Import `Crosshair` from lucide-react.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/insights/page.tsx frontend/src/components/sidebar-nav.tsx
git commit -m "feat: prediction markets section on insights + sidebar nav"
```
