# SiftSignal

Financial news intelligence platform. 158 RSS feeds, 10 categories, keyword topic classification, Haiku-powered sentiment analysis, entity extraction, event clustering, prediction market divergence detection.

## Commands

```bash
# Start everything
docker compose up -d

# Rebuild after code changes (nlp_service has the pipeline + API)
docker compose up -d --build nlp_service

# Run DB migration (destructive — drops and recreates all tables)
docker compose exec -T postgres psql -U news_user -d news_ai -f /dev/stdin < scripts/migrate.sql

# Seed 158 feeds into sources table
python3 -c "
import json, subprocess
feeds = json.load(open('data/feeds.json'))['feeds']
values = []
for f in feeds:
    cat = f.get('category', '')
    values.append(f\"('{f[\"name\"].replace(chr(39),chr(39)*2)}', '{f[\"url\"].replace(chr(39),chr(39)*2)}', '{f.get(\"language\",\"en\")}', '{f.get(\"country\",\"\")}', '{cat}', '{cat}', '{f.get(\"subcategory\",\"\")}')\" )
sql = 'INSERT INTO sources (name, url, language, country, group_name, category, subcategory) VALUES ' + ','.join(values) + ' ON CONFLICT (url) DO NOTHING;'
subprocess.run(['docker', 'compose', 'exec', '-T', 'postgres', 'psql', '-U', 'news_user', '-d', 'news_ai', '-c', sql])
"

# Trigger pipeline manually
curl -X POST http://localhost:8081/api/run

# Frontend dev
cd frontend && npm install && npm run dev
```

## Environment Variables

```bash
# .env file in project root (gitignored)
ANTHROPIC_API_KEY=sk-ant-...  # Enables Haiku sentiment. Without it, falls back to keywords.
POSTGRES_USER=news_user       # Default: news_user
POSTGRES_PASSWORD=news_pass   # Default: news_pass
CORS_ORIGINS=http://localhost:3000
```

## Architecture

```
158 RSS Feeds → Gather → Translate → [Classify + Sentiment + Extract] (parallel) → Group Events → Store
                                         keywords    Haiku API     spaCy NER
```

| Service | Port | Stack |
|---------|------|-------|
| nlp_service | 8081 | Python 3.11, Flask, Flask-SocketIO |
| postgres | 5432 | PostgreSQL 15 |
| redis | 6379 | Redis 7 (translation cache) |
| frontend | 3000 | Next.js 15, TypeScript, Tailwind, Recharts |

## Key Files

```
data/feeds.json              # 158 feed definitions with category/subcategory
data/topic_labels.json       # 10 financial topic keyword lists
data/candidate_topics.json   # Active topic IDs
services/nlp_py/
  api_server.py              # Flask routes, WebSocket, pipeline orchestration, scheduler
  repositories.py            # All DB queries (Source, Headline, EventCluster, Analytics, Insights, PipelineRun, Settings repos)
  database.py                # psycopg2 connection pool
  pipeline/
    gather.py                # RSS fetching (ThreadPoolExecutor, 158 feeds)
    translate.py             # Non-English → English (deep-translator, Redis-cached)
    classify.py              # Keyword topic classification (550+ keywords, 10 topics)
    sentiment.py             # Hybrid: Haiku API batches of 20, keyword fallback
    event_extract.py         # spaCy NER + financial event type classification
    group_by_event.py        # Entity overlap + word similarity clustering
    parallel_pipeline.py     # Runs classify + sentiment + extract concurrently
scripts/
  migrate.sql                # Full schema (DROP + CREATE — destructive)
  seed_sources.py            # Load feeds.json into sources table
frontend/src/
  app/page.tsx               # Feed page (headlines, filters, URL-synced state)
  app/events/page.tsx        # Event clusters
  app/analytics/page.tsx     # Charts: topics, sentiment, categories, heatmap, volume
  app/insights/page.tsx      # AI summary: sentiment by category, clusters, health, predictions
  app/predictions/page.tsx   # Prediction market cross-references + divergences
  app/pipeline/page.tsx      # Pipeline control, logs, run history
  app/settings/page.tsx      # Schedule, defaults, retention, export
  lib/api.ts                 # Typed API client (all endpoints)
  hooks/use-socket.ts        # WebSocket with auto-reconnect
  components/sidebar-nav.tsx # macOS dark mode sidebar
```

## Database

Tables: `sources`, `headlines`, `event_clusters`, `event_cluster_members`, `pipeline_runs`, `settings`

Key columns on `headlines`: `topic`, `topic_confidence`, `sentiment`, `sentiment_score`, `entities` (JSONB), `event_type`, `source_id`

Key columns on `sources`: `category`, `subcategory`, `error_count`, `last_fetched_at`, `fetch_error`

## API Endpoints

**Headlines**: `GET /api/headlines` (filterable: topic, sentiment, language, source_id, q), `GET /api/headlines/export?format=csv&period=24h`

**Events**: `GET /api/events`, `GET /api/events/:id`

**Analytics**: `GET /api/analytics?period=24h` (topic_distribution, sentiment_distribution, category_breakdown, topic_category_heatmap, daily_volume, source_breakdown)

**Insights** (AI agent API): `GET /api/insights/summary?period=24h` (sentiment_breakdown, sentiment_by_category, top_headlines_by_category, top_clusters, feed_health), `GET /api/insights/category/:cat`, `GET /api/insights/predictions` (cross-references, divergences)

**Pipeline**: `POST /api/run`, `GET /api/pipeline/status`, `GET /api/pipeline/history`

**Settings**: `GET/PUT /api/settings` (schedule, defaults, retention)

**Sources**: Full CRUD at `/api/sources` with category/subcategory filtering

## Feed Categories (158 total)

equities (35), macro (28), international (25), crypto (14), commodities (14), regulation (10), real_estate (9), fintech (9), earnings (9), prediction_markets (5)

## Sentiment Pipeline

**With `ANTHROPIC_API_KEY` set**: Haiku processes headlines in batches of 20. ~$0.50/run, ~7 min for 2500 headlines. Falls back to keywords per-batch on API failure.

**Without API key**: Keyword matching (bullish/bearish/neutral). Free, instant, less accurate.

## Gotchas

- `migrate.sql` is destructive — it DROPs all tables. Don't run on a DB with data you want to keep.
- `published_at` is null for ~2% of headlines. Frontend falls back to `created_at`.
- The default headline feed filters to `language = 'en'` unless a language param is explicitly passed.
- Event cluster labels go through entity alias dedup (Fed = Federal Reserve = Federal Reserve Board) in `InsightsRepository`.
- The pipeline scheduler uses `threading.Timer` — interval drift occurs if a run takes longer than the schedule interval. Intentional: prevents overlap.
- `seed_sources.py` requires `psycopg2` which isn't installed on macOS by default. Use the inline Python seeder in Commands above instead.
- The `settings` table uses key-value pairs, not typed columns. All values are strings.
- Haiku batch size is 20 headlines. If a batch fails, only that batch falls back to keywords — others continue with Haiku.

## Conventions

- All feed/topic config in JSON under `data/` — no hardcoded URLs or keywords in application code
- Repository pattern for all DB access (`repositories.py`)
- Pipeline stages are independent modules in `pipeline/`
- Frontend `api.ts` typed client for all endpoints
- macOS Dark Mode UI: warm grays (#1c1c1e/#2c2c2e), Apple system colors, SF Pro font stack
- Topic badges use muted pastel-on-dark colors (rgba overlays)
- Sentiment: green #30d158 (bullish), red #ff453a (bearish), gray #636366 (neutral)
