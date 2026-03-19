# Operational Maturity — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add DB-backed settings, pipeline scheduler, CSV/JSON export, data retention, settings page overhaul, and Topic × Category heatmap.

**Architecture:** New `settings` table for persistent config. `threading.Timer` for recurring pipeline runs. Pipeline body extracted from closure into module-level function. Export endpoint streams CSV/JSON. Heatmap uses 2D GROUP BY query rendered as a CSS grid.

**Tech Stack:** Python 3.11 (Flask), PostgreSQL 15, Next.js 15, TypeScript, Recharts

**Spec:** `docs/superpowers/specs/2026-03-19-operational-maturity-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `scripts/migrate.sql` | Modify | Add settings table |
| `services/nlp_py/repositories.py` | Modify | SettingsRepository, get_for_export, heatmap query |
| `services/nlp_py/api_server.py` | Modify | Extract pipeline body, scheduler, settings routes, export route, retention |
| `frontend/src/lib/api.ts` | Modify | AppSettings type, settings + export API methods, heatmap in AnalyticsData |
| `frontend/src/app/settings/page.tsx` | Rewrite | Full settings page (schedule, filters, retention, export) |
| `frontend/src/app/page.tsx` | Modify | Load default filters from settings |
| `frontend/src/app/analytics/page.tsx` | Modify | HeatmapChart component |

---

## Chunk 1: Backend — Settings, Scheduler, Export, Retention

### Task 1: Create settings table + SettingsRepository

**Files:**
- Modify: `scripts/migrate.sql`
- Modify: `services/nlp_py/repositories.py`

- [ ] **Step 1: Create settings table on live DB and seed defaults**

```bash
docker compose exec -T postgres psql -U news_user -d news_ai -c "
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
INSERT INTO settings (key, value) VALUES
    ('pipeline_schedule_enabled', 'false'),
    ('pipeline_schedule_interval', '30'),
    ('retention_days', '0'),
    ('default_topic', 'all'),
    ('default_sentiment', 'all')
ON CONFLICT (key) DO NOTHING;
"
```

- [ ] **Step 2: Add settings table to migrate.sql**

Add before the views section, using `CREATE TABLE IF NOT EXISTS`.

- [ ] **Step 3: Add SettingsRepository to repositories.py**

After `PipelineRunRepository`, add:

```python
class SettingsRepository:
    @staticmethod
    def get(key: str) -> Optional[str]:
        try:
            with get_db_cursor() as cursor:
                cursor.execute("SELECT value FROM settings WHERE key = %s", (key,))
                row = cursor.fetchone()
                return row["value"] if row else None
        except Exception as e:
            print(f"Error fetching setting {key}: {e}")
            return None

    @staticmethod
    def set(key: str, value: str):
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """INSERT INTO settings (key, value, updated_at) VALUES (%s, %s, NOW())
                       ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()""",
                    (key, value),
                )
        except Exception as e:
            print(f"Error setting {key}: {e}")

    @staticmethod
    def get_all() -> Dict[str, str]:
        try:
            with get_db_cursor() as cursor:
                cursor.execute("SELECT key, value FROM settings")
                return {r["key"]: r["value"] for r in cursor.fetchall()}
        except Exception as e:
            print(f"Error fetching settings: {e}")
            return {}
```

- [ ] **Step 4: Commit**

```bash
git add scripts/migrate.sql services/nlp_py/repositories.py
git commit -m "feat: add settings table and SettingsRepository"
```

---

### Task 2: Add settings API routes

**Files:**
- Modify: `services/nlp_py/api_server.py`

- [ ] **Step 1: Import SettingsRepository and add routes**

Add `SettingsRepository` to the imports from `repositories`. Add routes after the insights endpoints:

```python
@app.route("/api/settings", methods=["GET"])
def get_app_settings():
    return jsonify(SettingsRepository.get_all())

@app.route("/api/settings", methods=["PUT"])
def update_app_settings():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400
    if "pipeline_schedule_interval" in data:
        if str(data["pipeline_schedule_interval"]) not in ("15", "30", "60", "240"):
            return jsonify({"error": "interval must be 15, 30, 60, or 240"}), 400
    for key, value in data.items():
        SettingsRepository.set(key, str(value))
    if "pipeline_schedule_enabled" in data or "pipeline_schedule_interval" in data:
        _restart_scheduler()
    return jsonify(SettingsRepository.get_all())
```

Note: `_restart_scheduler` will be defined in Task 3. For now it can be a stub: `def _restart_scheduler(): pass`

- [ ] **Step 2: Commit**

```bash
git add services/nlp_py/api_server.py
git commit -m "feat: add GET/PUT /api/settings endpoints"
```

---

### Task 3: Extract pipeline body + add scheduler

**Files:**
- Modify: `services/nlp_py/api_server.py`

- [ ] **Step 1: Extract _run_pipeline_body from run_full_pipeline closure**

The `run_full_pipeline` route (line 380) contains an inner `_run()` closure with all the pipeline logic. Refactor:

1. Move the entire `_run()` function body to a module-level function `_run_pipeline_body()`
2. Replace the route handler to just: check status → start thread with `_run_pipeline_body` → return

```python
def _run_pipeline_body():
    """Full pipeline execution — called from route and scheduler."""
    from gather import gather
    from translate import Translator
    from parallel_pipeline import run_parallel_ml, classify_batch_wrapper, extract_batch_wrapper

    start = time.time()
    run_id = PipelineRunRepository.create_run()
    emit_log("info", "Starting full pipeline")
    # ... (entire existing _run() body) ...

@app.route("/api/run", methods=["POST"])
def run_full_pipeline():
    if pipeline_status["status"] == "running":
        return jsonify({"error": "Pipeline already running"}), 409
    threading.Thread(target=_run_pipeline_body, daemon=True).start()
    return jsonify({"message": "Full pipeline started"})
```

- [ ] **Step 2: Add scheduler state and functions**

At module level (near `pipeline_status`):

```python
_scheduler_timer: Optional[threading.Timer] = None
_scheduler_lock = threading.Lock()

def _restart_scheduler():
    global _scheduler_timer
    with _scheduler_lock:
        if _scheduler_timer:
            _scheduler_timer.cancel()
            _scheduler_timer = None
        enabled = SettingsRepository.get("pipeline_schedule_enabled")
        interval = SettingsRepository.get("pipeline_schedule_interval")
        if enabled == "true" and interval:
            minutes = int(interval)
            _scheduler_timer = threading.Timer(minutes * 60, _scheduled_run)
            _scheduler_timer.daemon = True
            _scheduler_timer.start()

def _scheduled_run():
    if pipeline_status["status"] != "running":
        threading.Thread(target=_run_pipeline_body, daemon=True).start()
    _restart_scheduler()
```

- [ ] **Step 3: Call _restart_scheduler on startup**

After the Flask app and socketio are created, before `if __name__ == "__main__":`, add:

```python
# Resume scheduler from saved settings on startup
try:
    _restart_scheduler()
except Exception:
    pass
```

- [ ] **Step 4: Add retention cleanup to pipeline body**

At the end of `_run_pipeline_body`, after pipeline_complete emit but inside the try block, add:

```python
            # Data retention cleanup
            try:
                retention = SettingsRepository.get("retention_days")
                if retention and int(retention) > 0:
                    with get_db_cursor() as cur:
                        cur.execute(
                            "DELETE FROM headlines WHERE created_at < NOW() - make_interval(days := %s)",
                            (int(retention),),
                        )
                        deleted = cur.rowcount
                    if deleted:
                        emit_log("info", f"Retention: deleted {deleted} headlines older than {retention} days")
                        with get_db_cursor() as cur:
                            cur.execute(
                                "DELETE FROM event_clusters WHERE id NOT IN (SELECT DISTINCT cluster_id FROM event_cluster_members)"
                            )
            except Exception as e:
                emit_log("warn", f"Retention cleanup failed: {e}")
```

- [ ] **Step 5: Verify**

```bash
docker compose up -d --build nlp_service
sleep 10
# Test settings
curl -s http://localhost:8081/api/settings | python3 -m json.tool
# Test schedule toggle
curl -s -X PUT http://localhost:8081/api/settings -H "Content-Type: application/json" -d '{"pipeline_schedule_enabled": "true", "pipeline_schedule_interval": "60"}' | python3 -m json.tool
# Disable it
curl -s -X PUT http://localhost:8081/api/settings -H "Content-Type: application/json" -d '{"pipeline_schedule_enabled": "false"}' | python3 -m json.tool
```

- [ ] **Step 6: Commit**

```bash
git add services/nlp_py/api_server.py
git commit -m "feat: pipeline scheduler with timer + retention cleanup"
```

---

### Task 4: Add export endpoint

**Files:**
- Modify: `services/nlp_py/repositories.py`
- Modify: `services/nlp_py/api_server.py`

- [ ] **Step 1: Add HeadlineRepository.get_for_export**

```python
    @staticmethod
    def get_for_export(
        period: str = "24h",
        topic: Optional[str] = None,
        sentiment: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10000,
    ) -> List[Dict]:
        interval_map = {"24h": "24 hours", "7d": "7 days", "30d": "30 days"}
        interval = interval_map.get(period, "24 hours")
        conditions = ["h.created_at >= NOW() - %(interval)s::INTERVAL"]
        params: Dict[str, Any] = {"interval": interval, "limit": limit}
        if topic:
            conditions.append("h.topic = %(topic)s")
            params["topic"] = topic
        if sentiment:
            conditions.append("h.sentiment = %(sentiment)s")
            params["sentiment"] = sentiment
        if category:
            conditions.append("s.category = %(category)s")
            params["category"] = category
        where = " AND ".join(conditions)
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    f"""SELECT h.title, h.url, h.topic, h.topic_confidence,
                               h.sentiment, h.sentiment_score, h.published_at,
                               s.name AS source_name, s.category
                        FROM headlines h
                        JOIN sources s ON h.source_id = s.id
                        WHERE {where}
                        ORDER BY h.published_at DESC NULLS LAST
                        LIMIT %(limit)s""",
                    params,
                )
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching export data: {e}")
            return []
```

- [ ] **Step 2: Add export Flask route**

```python
import csv
import io

@app.route("/api/headlines/export")
def export_headlines():
    fmt = request.args.get("format", "csv")
    period = request.args.get("period", "24h")
    if period not in ("24h", "7d", "30d"):
        period = "24h"
    topic = request.args.get("topic")
    sentiment = request.args.get("sentiment")
    category = request.args.get("category")

    rows = HeadlineRepository.get_for_export(period, topic, sentiment, category)

    if fmt == "json":
        return jsonify(rows)

    # CSV
    output = io.StringIO()
    fields = ["title", "url", "source_name", "category", "topic", "topic_confidence",
              "sentiment", "sentiment_score", "published_at"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    resp = app.make_response(output.getvalue())
    resp.headers["Content-Type"] = "text/csv"
    resp.headers["Content-Disposition"] = f'attachment; filename="headlines_{period}.csv"'
    return resp
```

- [ ] **Step 3: Commit**

```bash
git add services/nlp_py/repositories.py services/nlp_py/api_server.py
git commit -m "feat: CSV/JSON headline export endpoint"
```

---

### Task 5: Add heatmap query to analytics

**Files:**
- Modify: `services/nlp_py/repositories.py`
- Modify: `scripts/migrate.sql`

- [ ] **Step 1: Add compound index on live DB**

```bash
docker compose exec -T postgres psql -U news_user -d news_ai -c "
CREATE INDEX IF NOT EXISTS idx_headlines_topic_source ON headlines(topic, source_id);
"
```

Also add to `migrate.sql`.

- [ ] **Step 2: Add topic_category_heatmap query to AnalyticsRepository.get_analytics**

Add `"topic_category_heatmap": []` to the initial result dict. Inside the `try:` block, after the sentiment_distribution query, add:

```python
                # Topic x Category heatmap
                cursor.execute(
                    """
                    SELECT h.topic, s.category, COUNT(*) AS count
                    FROM headlines h
                    JOIN sources s ON h.source_id = s.id
                    WHERE h.created_at >= NOW() - %(interval)s::INTERVAL
                      AND h.topic IS NOT NULL
                      AND s.category IS NOT NULL
                    GROUP BY h.topic, s.category
                    ORDER BY count DESC
                    """,
                    params,
                )
                result["topic_category_heatmap"] = [dict(r) for r in cursor.fetchall()]
```

- [ ] **Step 3: Commit**

```bash
git add services/nlp_py/repositories.py scripts/migrate.sql
git commit -m "feat: topic x category heatmap query + compound index"
```

---

## Chunk 2: Frontend — Settings Page, Default Filters, Heatmap

### Task 6: Update frontend types

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add AppSettings interface and API methods**

```typescript
export interface AppSettings {
  pipeline_schedule_enabled: string;
  pipeline_schedule_interval: string;
  retention_days: string;
  default_topic: string;
  default_sentiment: string;
}
```

Add to api object:
```typescript
  settings: {
    get(): Promise<AppSettings> {
      return request("/api/settings");
    },
    update(data: Partial<AppSettings>): Promise<AppSettings> {
      return request("/api/settings", {
        method: "PUT",
        body: JSON.stringify(data),
        headers: { "Content-Type": "application/json" },
      });
    },
  },
```

- [ ] **Step 2: Add topic_category_heatmap to AnalyticsData**

```typescript
  topic_category_heatmap: { topic: string; category: string; count: number }[];
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat: add AppSettings type, settings API methods, heatmap type"
```

---

### Task 7: Rewrite settings page

**Files:**
- Rewrite: `frontend/src/app/settings/page.tsx`

- [ ] **Step 1: Rewrite settings page with server-backed settings**

Complete rewrite — replace the entire file. The new page has 4 sections:

1. **Pipeline Schedule** — toggle (enabled/disabled), interval dropdown (15m/30m/1h/4h), save button
2. **Default Filters** — default topic dropdown (all + 10 financial topics), default sentiment dropdown (all/bullish/bearish/neutral), save button
3. **Data Retention** — dropdown (never/7d/30d/90d), warning text, save button
4. **Export Data** — period selector, Download CSV / Download JSON buttons (these create `<a>` tags pointing to `/api/headlines/export?format=csv&period=X`)
5. **About** section at bottom

On mount: `api.settings.get()` to populate. On save: `api.settings.update({...})`. Each section has its own save button that only sends the keys for that section.

Use the same dark terminal styling as the existing page (border-2 border-[#333], bg-[#111], font-mono, etc.).

The financial topics list for the dropdown: `["all", "markets", "economy", "earnings", "crypto", "commodities", "real_estate", "regulation", "fintech", "prediction_markets", "mergers"]`

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/settings/page.tsx
git commit -m "feat: rewrite settings page with schedule, filters, retention, export"
```

---

### Task 8: Load default filters on feed page

**Files:**
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Load settings on mount and apply defaults**

Change the initial state from hardcoded "all" to null:
```typescript
const [topic, setTopic] = useState<string | null>(null);
const [sentiment, setSentiment] = useState<string | null>(null);
```

Add a useEffect to load settings on mount:
```typescript
useEffect(() => {
  api.settings.get().then((s) => {
    setTopic(s.default_topic || "all");
    setSentiment(s.default_sentiment || "all");
  }).catch(() => {
    setTopic("all");
    setSentiment("all");
  });
}, []);
```

Guard the headlines fetch to only run once filters are loaded:
```typescript
// In the fetchHeadlines useEffect:
if (topic === null || sentiment === null) return;
```

Show a brief loading indicator while filters are loading (topic === null).

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/page.tsx
git commit -m "feat: load default filters from server settings on feed page"
```

---

### Task 9: Add Topic × Category heatmap to analytics

**Files:**
- Modify: `frontend/src/app/analytics/page.tsx`

- [ ] **Step 1: Add HeatmapChart component**

A CSS grid with rows = topics, columns = categories. Each cell colored by intensity (transparent → green). Include row/column headers.

```typescript
function HeatmapChart({ data }: { data: { topic: string; category: string; count: number }[] }) {
  if (!data.length) return <p className="text-[#555] font-mono text-xs">No data yet.</p>;

  const topics = [...new Set(data.map((d) => d.topic))];
  const categories = [...new Set(data.map((d) => d.category))];
  const maxCount = Math.max(...data.map((d) => d.count));

  const lookup = new Map(data.map((d) => [`${d.topic}-${d.category}`, d.count]));

  return (
    <div>
      <h2 className="font-mono text-[10px] uppercase tracking-widest text-[#555] mb-4">
        Topic × Category
      </h2>
      <div className="overflow-x-auto">
        <div
          className="grid gap-[2px]"
          style={{
            gridTemplateColumns: `100px repeat(${categories.length}, 1fr)`,
            gridTemplateRows: `24px repeat(${topics.length}, 28px)`,
          }}
        >
          {/* Corner cell */}
          <div />
          {/* Column headers */}
          {categories.map((cat) => (
            <div key={cat} className="font-mono text-[8px] text-[#555] uppercase text-center truncate px-1">
              {cat.replace(/_/g, " ")}
            </div>
          ))}
          {/* Rows */}
          {topics.map((topic) => (
            <>
              <div key={`label-${topic}`} className="font-mono text-[9px] text-[#777] uppercase flex items-center truncate">
                {topic.replace(/_/g, " ")}
              </div>
              {categories.map((cat) => {
                const count = lookup.get(`${topic}-${cat}`) ?? 0;
                const intensity = maxCount > 0 ? count / maxCount : 0;
                return (
                  <div
                    key={`${topic}-${cat}`}
                    className="flex items-center justify-center font-mono text-[8px] border border-[#222]"
                    style={{
                      backgroundColor: count > 0
                        ? `rgba(0, 255, 136, ${0.1 + intensity * 0.8})`
                        : "transparent",
                      color: intensity > 0.5 ? "#000" : "#555",
                    }}
                    title={`${topic} × ${cat}: ${count}`}
                  >
                    {count > 0 ? count : ""}
                  </div>
                );
              })}
            </>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add HeatmapChart to render section**

After the SentimentChart card, add:
```tsx
<div className="border-2 border-[#333] bg-[#111] p-5 animate-fade-in-up" style={{ animationDelay: "60ms" }}>
  <HeatmapChart data={data.topic_category_heatmap ?? []} />
</div>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/analytics/page.tsx
git commit -m "feat: topic x category heatmap on analytics page"
```
