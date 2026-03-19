# Slice 3: Scheduled Automation + Operational Maturity — Design Spec

**Goal:** Add a recurring pipeline scheduler, CSV/JSON export, full settings page backed by a database settings table, data retention policy, and a Topic × Category heatmap on the analytics page.

**Depends on:** Slice 1 (Financial Intelligence Foundation) + Slice 2 (Sentiment & Signal Extraction) — both completed.

---

## 1. Settings Table + Repository

**New DB table: `settings`**

```sql
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

Add to `scripts/migrate.sql` before the views section (use `IF NOT EXISTS` for idempotency). For the running DB, run the same CREATE TABLE directly.

**Initial seed rows:**
- `pipeline_schedule_enabled` → `"false"`
- `pipeline_schedule_interval` → `"30"` (minutes)
- `retention_days` → `"0"` (0 = never delete)
- `default_topic` → `"all"`
- `default_sentiment` → `"all"`

**New class: `SettingsRepository`** in `services/nlp_py/repositories.py`:

```python
class SettingsRepository:
    @staticmethod
    def get(key: str) -> Optional[str]:
        """Get a single setting value by key."""
        with get_db_cursor() as cursor:
            cursor.execute("SELECT value FROM settings WHERE key = %s", (key,))
            row = cursor.fetchone()
            return row["value"] if row else None

    @staticmethod
    def set(key: str, value: str):
        """Upsert a setting."""
        with get_db_cursor() as cursor:
            cursor.execute(
                """INSERT INTO settings (key, value, updated_at) VALUES (%s, %s, NOW())
                   ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()""",
                (key, value),
            )

    @staticmethod
    def get_all() -> Dict[str, str]:
        """Get all settings as a dict."""
        with get_db_cursor() as cursor:
            cursor.execute("SELECT key, value FROM settings")
            return {r["key"]: r["value"] for r in cursor.fetchall()}
```

**Flask routes** in `services/nlp_py/api_server.py`:

```python
@app.route("/api/settings", methods=["GET"])
def get_settings():
    return jsonify(SettingsRepository.get_all())

@app.route("/api/settings", methods=["PUT"])
def update_settings():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400
    # Validate schedule interval
    if "pipeline_schedule_interval" in data:
        if str(data["pipeline_schedule_interval"]) not in ("15", "30", "60", "240"):
            return jsonify({"error": "interval must be 15, 30, 60, or 240"}), 400
    for key, value in data.items():
        SettingsRepository.set(key, str(value))
    # If schedule settings changed, restart the scheduler
    if "pipeline_schedule_enabled" in data or "pipeline_schedule_interval" in data:
        _restart_scheduler()
    return jsonify(SettingsRepository.get_all())
```

---

## 2. Pipeline Scheduler

**Implementation:** Use `threading.Timer` inside `api_server.py`. No new dependencies.

**Module-level state:**
```python
_scheduler_timer: Optional[threading.Timer] = None
_scheduler_lock = threading.Lock()
```

**Functions:**

```python
def _restart_scheduler():
    """Read schedule settings from DB and restart the timer."""
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
    """Execute a pipeline run, then reschedule."""
    if pipeline_status["status"] != "running":
        threading.Thread(target=_run_pipeline_body, daemon=True).start()
    # Reschedule regardless (note: next run starts from completion, not from schedule time — intentional drift-on-overlap)
    _restart_scheduler()
```

**CRITICAL: Extract pipeline body into standalone function.** The existing `run_full_pipeline` route handler defines the pipeline logic as an inner `_run()` closure. This must be refactored into a module-level `_run_pipeline_body()` function so it can be called from both the HTTP route and the scheduler. The route handler becomes:

```python
@app.route("/api/run", methods=["POST"])
def run_full_pipeline():
    if pipeline_status["status"] == "running":
        return jsonify({"error": "Pipeline already running"}), 409
    threading.Thread(target=_run_pipeline_body, daemon=True).start()
    return jsonify({"message": "Full pipeline started"})
```

**On app startup:** Call `_restart_scheduler()` after the Flask app is created so that if the schedule was enabled before a restart, it resumes.

**Guard:** The existing `pipeline_status["status"] == "running"` check prevents double-runs. If a scheduled run fires while a manual run is in progress, it skips and reschedules.

**Allowed intervals:** 15, 30, 60, 240 minutes. Validated in the PUT /api/settings endpoint (see Section 1).

---

## 3. Data Export

**New endpoint:** `GET /api/headlines/export`

Query params:
- `format`: `csv` or `json` (default: `csv`)
- `period`: `24h`, `7d`, `30d` (default: `24h`)
- `topic`: optional filter
- `sentiment`: optional filter
- `category`: optional filter

**CSV response:**
- `Content-Type: text/csv`
- `Content-Disposition: attachment; filename="headlines_24h.csv"`
- Columns: title, url, source_name, category, topic, topic_confidence, sentiment, sentiment_score, published_at

**JSON response:**
- Returns the full array of headline objects (same columns)

**Implementation:** New `HeadlineRepository.get_for_export(...)` method with a dedicated query:

```sql
SELECT h.title, h.url, h.topic, h.topic_confidence, h.sentiment, h.sentiment_score,
       h.published_at, s.name AS source_name, s.category
FROM headlines h
JOIN sources s ON h.source_id = s.id
WHERE h.created_at >= NOW() - %(interval)s::INTERVAL
  [AND h.topic = %(topic)s]
  [AND h.sentiment = %(sentiment)s]
  [AND s.category = %(category)s]
ORDER BY h.published_at DESC NULLS LAST
LIMIT 10000
```

Note: The existing `get_paginated` does not select `s.category`, so a new dedicated method is needed. Stream CSV using Python's `csv` module with `io.StringIO`, or return as JSON array. Limit to 10,000 rows max to prevent memory issues.

---

## 4. Data Retention

When `retention_days` > 0, the pipeline's gather stage should delete old headlines after each run.

**In the pipeline run handler** (api_server.py), after the pipeline completes successfully:

```python
retention = SettingsRepository.get("retention_days")
if retention and int(retention) > 0:
    with get_db_cursor() as cursor:
        cursor.execute(
            "DELETE FROM headlines WHERE created_at < NOW() - make_interval(days := %s)",
            (int(retention),)
        )
        deleted = cursor.rowcount
    if deleted:
        emit_log("info", f"Retention: deleted {deleted} headlines older than {retention} days")
```

CASCADE on `event_cluster_members.headline_id` handles member cleanup, but `event_clusters` rows become orphaned (zero members). Add a follow-up cleanup:

```python
    # Clean up empty event clusters
    with get_db_cursor() as cursor:
        cursor.execute(
            "DELETE FROM event_clusters WHERE id NOT IN (SELECT DISTINCT cluster_id FROM event_cluster_members)"
        )
```

---

## 5. Settings Page Overhaul

**Replace** the current localStorage-based settings page with a server-backed page.

### Layout

Four sections in order:

**Pipeline Schedule**
- Toggle switch: Enable/Disable
- Interval dropdown: 15 min / 30 min / 1 hour / 4 hours
- Status line: "Next run in X minutes" or "Disabled"
- Save button

**Default Filters**
- Default topic dropdown (All + 10 financial topics)
- Default sentiment dropdown (All / Bullish / Bearish / Neutral)
- Save button
- Note: "Applied when loading the feed page"

**Data Retention**
- Dropdown: Never / 7 days / 30 days / 90 days
- Warning text when a value is selected: "Headlines older than X days will be deleted after each pipeline run"
- Save button

**Export Data**
- Period selector: 24h / 7d / 30d
- Two buttons: "Download CSV" / "Download JSON"
- These trigger `GET /api/headlines/export?format=csv|json&period=X` and download the file

**About** section stays at the bottom.

### Data flow

On mount: `GET /api/settings` → populate all fields.
On save: `PUT /api/settings` with changed key-value pairs → update local state.
Default filters: stored in DB, read by the feed page on mount to set initial filter values.

### Frontend types

```typescript
// api.ts
export interface AppSettings {
  pipeline_schedule_enabled: string;
  pipeline_schedule_interval: string;
  retention_days: string;
  default_topic: string;
  default_sentiment: string;
}

// api object
settings: {
  get(): Promise<AppSettings> { return request("/api/settings"); },
  update(data: Partial<AppSettings>): Promise<AppSettings> {
    return request("/api/settings", { method: "PUT", body: JSON.stringify(data), headers: { "Content-Type": "application/json" } });
  },
},
```

### Feed page integration

On mount, fetch `GET /api/settings` and use `default_topic` and `default_sentiment` as initial values for the filter state. To avoid a double-fetch (first with "all", then with defaults), initialize `topic` and `sentiment` state as `null`, show a brief loading state until settings are fetched, then set both filter states atomically before the first headlines fetch:

```typescript
const [topic, setTopic] = useState<string | null>(null);
const [sentiment, setSentiment] = useState<string | null>(null);

useEffect(() => {
  api.settings.get().then((s) => {
    setTopic(s.default_topic || "all");
    setSentiment(s.default_sentiment || "all");
  }).catch(() => {
    setTopic("all");
    setSentiment("all");
  });
}, []);

// Only fetch headlines once topic/sentiment are loaded (non-null)
useEffect(() => {
  if (topic === null || sentiment === null) return;
  fetchHeadlines(1, true);
}, [topic, sentiment, ...]);
```

---

## 6. Topic × Category Heatmap

**Backend:** New query added inside the existing `try:` block in `AnalyticsRepository.get_analytics()` (before the `except`), using the same `params` dict:

```sql
SELECT h.topic, s.category, COUNT(*) AS count
FROM headlines h
JOIN sources s ON h.source_id = s.id
WHERE h.created_at >= NOW() - %(interval)s::INTERVAL
  AND h.topic IS NOT NULL
  AND s.category IS NOT NULL
GROUP BY h.topic, s.category
ORDER BY count DESC
```

Returns: `[{"topic": "markets", "category": "equities", "count": 150}, ...]`

Add to the result dict as `"topic_category_heatmap": []`.

**Performance index:**
```sql
CREATE INDEX idx_headlines_topic_source ON headlines(topic, source_id);
```

**Frontend:** New `HeatmapChart` component in `analytics/page.tsx`:

- CSS grid layout
- Rows = topics (10), Columns = categories (10)
- Each cell colored by count: white/transparent (0) → faint green → bright green (max)
- Row and column headers
- Tooltip on hover showing exact count
- Placed after the Sentiment Distribution chart

**AnalyticsData interface update:**
```typescript
topic_category_heatmap: { topic: string; category: string; count: number }[];
```

---

## Non-Goals (Deferred)

- User authentication / multi-user settings — single-user system
- Webhook/notification on pipeline completion
- Custom cron expressions — fixed intervals are sufficient
- S3/cloud export — local download only
