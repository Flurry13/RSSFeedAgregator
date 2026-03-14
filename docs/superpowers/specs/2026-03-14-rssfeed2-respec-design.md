# RSSFeed2 Full Respec — Design Specification

**Date:** 2026-03-14
**Status:** Approved
**Approach:** Full rewrite (Approach A)

---

## Overview

Full respec of the RSSFeed2 news aggregator. Replace the React + Vite frontend with Next.js 15 deployed on Vercel. Remove the Go API gateway. Optimize the Python ML pipeline for end-to-end speed. Redesign the UI as a hybrid editorial feed + data dashboard. Parallelize the rewrite using an 8-agent team across 5 phases.

### Goals

- Personal news monitoring tool that doubles as a portfolio piece
- Hybrid UI: editorial headline feed with a persistent ML data sidebar
- End-to-end pipeline speed improvement (~40-50% faster)
- Simpler architecture: eliminate Go gateway, reduce Docker to backend-only
- Six full pages: Feed, Events, Analytics, Pipeline, Sources, Settings

---

## Architecture

```
┌──────────────────────────────────────────────┐
│              Vercel (Free Tier)               │
│                                               │
│   Next.js 15 (App Router)                     │
│   ├── Server Components (pages, layouts)      │
│   ├── API Routes (/api/*) → proxy to Python   │
│   └── Socket.io client for real-time          │
└──────────────────┬───────────────────────────┘
                   │ HTTPS
                   ▼
┌──────────────────────────────────────────────┐
│   Server (Docker Compose on VPS/local)        │
│   Exposed via Cloudflare Tunnel or public IP  │
│                                               │
│   ┌─────────────┐  ┌──────────┐  ┌────────┐ │
│   │ Python NLP  │  │ Postgres │  │ Redis  │ │
│   │ (Flask +    │  │   15     │  │   7    │ │
│   │  SocketIO)  │  │          │  │        │ │
│   │  Port 8081  │  │  :5432   │  │ :6379  │ │
│   └─────────────┘  └──────────┘  └────────┘ │
│   ┌─────────────┐                            │
│   │   Qdrant    │                            │
│   │   :6333     │                            │
│   └─────────────┘                            │
└──────────────────────────────────────────────┘
```

### Key Decisions

- **No Go API gateway** — Next.js API routes handle CORS and proxying to Python
- **No frontend in Docker** — lives on Vercel
- **4 Docker services** (down from 7): postgres, redis, qdrant, nlp_service
- **WebSocket** via Socket.io for real-time pipeline status
- **Python NLP service runs on port 8081** — matches existing Docker config
- **Vercel → Backend connectivity**: Use Cloudflare Tunnel (free) to expose the Docker host. The tunnel gives a stable public URL (e.g., `rssfeed-api.yourdomain.com`) that Vercel API routes proxy to. For local dev, Next.js hits `localhost:8081` directly.

### Services Removed

- `api_go` (Go API gateway) — delete `services/api_go/` directory and remove service from `docker-compose.yml`
- `ingester_go` (Go background ingester) — remove service definition from `docker-compose.yml` (directory may not exist on disk; delete if present)
- `frontend` Docker service — moved to Vercel
- `jaeger` (tracing) — removed for simplicity

---

## Frontend

### Tech Stack

- Next.js 15 (App Router, Server Components)
- Tailwind CSS + shadcn/ui
- Socket.io client for real-time
- Recharts for analytics charts
- Deployed on Vercel (free tier)
- Responsive breakpoint: `lg:1024px` (sidebar collapses below this)

### Visual Direction

Hybrid editorial feed + data sidebar:
- Main content area: clean, typography-driven editorial feed
- Persistent right sidebar: pipeline status, topic breakdown, headline count
- Dark theme with light mode toggle
- Collapsible sidebar nav on the left
- Desktop: sidebar always visible. Below `lg:1024px`: data sidebar becomes a drawer.

### Pages

| Page | Route | Purpose |
|------|-------|---------|
| Feed | `/` | Main editorial headline feed — search, filter by topic/language/source, infinite scroll |
| Events | `/events` | Clustered event view — grouped articles, timeline, entity tags. ML showcase page. |
| Analytics | `/analytics` | Charts — topic distribution over time, source breakdown, language heatmap, daily volume |
| Pipeline | `/pipeline` | Control panel — trigger gather/translate/classify, real-time progress bars, log stream |
| Sources | `/sources` | Manage RSS feeds — add/remove/edit, per-source stats, health status, last fetched |
| Settings | `/settings` | Config — refresh intervals, theme toggle (client-only, stored in localStorage) |

### Navigation

- Left sidebar nav (collapsible) with icons + labels for all 6 pages
- Right data sidebar (persistent on desktop, drawer on mobile) showing:
  - Pipeline status indicator (idle/running/error)
  - Quick topic breakdown (top 5 topics with percentages)
  - Headline count + sources count
  - Last pipeline run timestamp

### Settings Storage

Settings page is **client-only** — no backend endpoint needed. All preferences (theme, refresh interval, notification prefs) are stored in `localStorage`. No `settings` table in the database.

---

## Backend — Speed Improvements

### Model Loading

- Load BART-MNLI, all-MiniLM-L6-v2, and spaCy en_core_web_sm once at startup
- Keep models warm in memory — no per-request initialization

### Pipeline Parallelism

Current (sequential):
```
Gather → Translate → Classify → Extract → Embed → Group → Store
```

New (parallel middle stage):
```
Gather → Translate → [Classify | Extract | Embed] (parallel) → Group → Store
```

- Classify, Extract, and Embed are independent per-headline and run concurrently
- Use `asyncio` + `concurrent.futures.ThreadPoolExecutor`

### Batch Processing

- Classify in batches (remove self-imposed rate limiting — models are local)
- Embeddings already batch at 128 — keep that
- Bulk insert to Postgres with `executemany`

### Caching

- Redis cache for classified headlines (skip re-classification on re-gather)
- Move translation LRU cache to Redis for persistence across restarts

### Connection Pooling

- Postgres pool: max 10 → 20
- Persistent Redis connections
- Qdrant client connection reuse

### Expected Improvement

- Parallel ML stage: ~40-50% time reduction
- Model preloading: eliminates cold-start penalty
- Batch classification: removes artificial rate limit

---

## WebSocket Event Contract

The Python backend emits Socket.io events. The Next.js frontend connects directly to the Python service's Socket.io endpoint (not proxied through API routes — WebSocket connections go direct to the backend URL).

### Events (Server → Client)

| Event | Payload | When |
|-------|---------|------|
| `status_update` | `{ stage: string, status: "running" \| "idle" \| "error", progress: number, total: number, message: string }` | During any pipeline stage |
| `headlines_update` | `{ count: number, new_headlines: number }` | After gather or full pipeline completes |
| `log_message` | `{ level: "info" \| "warn" \| "error", message: string, timestamp: string }` | Real-time log output (last 100 retained) |
| `pipeline_complete` | `{ duration_ms: number, headlines_gathered: number, translated: number, classified: number }` | Full pipeline run finishes |

### Events (Client → Server)

| Event | Payload | Purpose |
|-------|---------|---------|
| `subscribe_status` | `{}` | Start receiving status updates |
| `unsubscribe_status` | `{}` | Stop receiving status updates |

### Namespace

All events on the default namespace (`/`). No custom namespaces.

### Reconnection Strategy

- Socket.io client uses default reconnection (`reconnection: true`, `reconnectionAttempts: Infinity`, `reconnectionDelay: 1000`, exponential backoff)
- On disconnect, the data sidebar shows a "Reconnecting..." indicator
- On reconnect, client re-emits `subscribe_status` and fetches current status via `GET /api/pipeline/status` to resync state
- No fallback to long-polling — if WebSocket is down, status is stale until reconnected (the REST endpoint provides on-demand status)

### CORS for Direct WebSocket

Since the browser connects directly to the Python backend for WebSocket (not through Next.js proxy), Flask-SocketIO must be configured with CORS:
- Allow origin: Vercel deployment URL + `localhost:3000` (dev)
- Set via `CORS_ORIGINS` env var on the NLP service

---

## API Contract

### Next.js API Routes → Python Backend

| Next.js Route | Python Endpoint | Method | Purpose |
|---|---|---|---|
| `/api/headlines` | `/api/headlines` | GET | Paginated headlines with filters |
| `/api/events` | `/api/events` | GET | Event clusters with member articles |
| `/api/events/[id]` | `/api/events/:id` | GET | Single event cluster detail |
| `/api/analytics` | `/api/analytics` | GET | Aggregated stats |
| `/api/pipeline/gather` | `/api/gather` | POST | Trigger RSS gathering |
| `/api/pipeline/translate` | `/api/translate` | POST | Trigger translation |
| `/api/pipeline/classify` | `/api/classify` | POST | Trigger classification |
| `/api/pipeline/run` | `/api/run` | POST | Run full pipeline end-to-end |
| `/api/pipeline/status` | `/api/pipeline/status` | GET | Current pipeline status snapshot |
| `/api/sources` | `/api/sources` | GET | List all sources |
| `/api/sources` | `/api/sources` | POST | Create a new source |
| `/api/sources/[id]` | `/api/sources/:id` | GET | Get single source |
| `/api/sources/[id]` | `/api/sources/:id` | PUT | Update a source |
| `/api/sources/[id]` | `/api/sources/:id` | DELETE | Delete a source |
| `/api/search` | `/api/search` | GET | Semantic search via Qdrant vectors |

### Pagination & Response Envelope

All list endpoints (`/api/headlines`, `/api/events`, `/api/sources`) use the same pagination contract:

**Query Parameters:**
- `page` (int, default 1) — page number
- `limit` (int, default 50, max 200) — items per page
- `sort` (string, default `published_at`) — sort field
- `order` (string, default `desc`) — `asc` or `desc`

**Filter Parameters (endpoint-specific):**
- `/api/headlines`: `topic`, `language`, `source_id`, `q` (full-text search)
- `/api/events`: `event_type`, `since` (ISO timestamp)
- `/api/sources`: `active` (boolean), `language`, `group_name`

**Response Envelope:**
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 1247,
    "total_pages": 25
  }
}
```

Single-item endpoints (`/api/events/:id`, `/api/sources/:id`) return the object directly (no envelope).

**`/api/analytics` Response:**
```json
{
  "topic_distribution": [{ "topic": "politics", "count": 340, "avg_confidence": 0.87 }],
  "source_breakdown": [{ "source_id": 1, "name": "BBC", "count": 89 }],
  "language_breakdown": [{ "language": "en", "count": 800 }],
  "daily_volume": [{ "date": "2026-03-14", "count": 156 }],
  "period": "7d"
}
```
Query param: `period` (string, default `7d`) — one of `24h`, `7d`, `30d`.

**`/api/search` Request/Response:**
```
GET /api/search?q=semiconductor+supply+chain&limit=20
```
```json
{
  "data": [
    { "headline": {...}, "score": 0.92 }
  ],
  "query": "semiconductor supply chain"
}
```
Searches Qdrant by embedding the query text with all-MiniLM-L6-v2, then returns headlines sorted by cosine similarity.

**`GET /api/pipeline/status` Response:**
```json
{
  "stage": "classify",
  "status": "running",
  "progress": 45,
  "total": 120,
  "message": "Classifying headlines...",
  "last_run": "2026-03-14T10:30:00Z",
  "last_duration_ms": 34500
}
```

### New vs Current

- `/api/analytics` — new, aggregation queries on Postgres
- `/api/classify` — new, separate trigger (currently bundled)
- `/api/run` — new, one-click full pipeline
- `/api/pipeline/status` — new, REST endpoint for initial status fetch (supplements WebSocket)
- `/api/sources` — new, feed management with full CRUD (currently hardcoded in feeds.json → moves to Postgres)
- `/api/search` — new, semantic search leveraging Qdrant embeddings

---

## Database Schema

This is a **clean-slate schema** — the rewrite drops the existing database and starts fresh. The old schema (UUID PKs, separate `topic_classifications` table, `events` table, `embeddings` metadata table, `processing_jobs` queue, `metrics` table, enum types) is replaced with a simpler, flatter design. Data from the old database is not migrated — only the feed list from `feeds.json` is seeded.

**Rationale for clean slate:** The old schema was designed for a different architecture (Go ingester, separate job queue, multi-rank topic classifications). The rewrite simplifies: topics go inline on headlines, event extraction results go inline as JSONB, embedding metadata is just a Qdrant point ID. The `processing_jobs` and `metrics` tables are unnecessary — Redis handles job queuing and pipeline status is tracked in-memory.

### Extensions

```sql
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```

UUID-ossp and btree_gin are no longer needed (SERIAL PKs, simpler indexes).

### Sources Table (replaces feeds.json and old feeds table)

```sql
CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    language TEXT NOT NULL DEFAULT 'en',
    country TEXT,
    group_name TEXT,
    active BOOLEAN DEFAULT TRUE,
    last_fetched_at TIMESTAMPTZ,
    fetch_error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sources_active ON sources(active);
CREATE INDEX idx_sources_language ON sources(language);
```

**Columns intentionally dropped from old `feeds` table:** `category`, `leaning`, `weight`, `fetch_interval` — these were unused in the actual pipeline code. If needed later, they can be re-added.

### Headlines Table (simplified)

```sql
CREATE TABLE headlines (
    id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    title TEXT NOT NULL,
    description TEXT,
    url TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    language TEXT,
    translated_title TEXT,
    topic TEXT,
    topic_confidence FLOAT,
    entities JSONB,
    event_type TEXT,
    embedding_id TEXT,  -- Qdrant point ID
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(url, source_id)
);

CREATE INDEX idx_headlines_source_id ON headlines(source_id);
CREATE INDEX idx_headlines_published_at ON headlines(published_at);
CREATE INDEX idx_headlines_language ON headlines(language);
CREATE INDEX idx_headlines_topic ON headlines(topic);
CREATE INDEX idx_headlines_title_fts ON headlines USING gin(to_tsvector('simple', title));
-- Uses 'simple' dictionary instead of 'english' to support multilingual headlines
```

**Columns intentionally dropped from old schema:**
- `content`, `author`, `translated_description` — RSS feeds rarely provide these; the pipeline never used them
- `classification_status`, `embedding_status`, `event_extraction_status` — processing state tracked in-memory during pipeline runs, not persisted
- `processing_errors` — errors logged to stdout/Redis, not stored per-headline

**Column kept from old schema:**
- `description` — useful for display and search even if not always populated

### Event Clusters Table (replaces old event_groups)

```sql
CREATE TABLE event_clusters (
    id SERIAL PRIMARY KEY,
    label TEXT NOT NULL,
    event_type TEXT,
    key_entities JSONB,
    summary TEXT,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_event_clusters_start_time ON event_clusters(start_time);
```

Note: `headline_count` is derived via `COUNT(*)` on the junction table, not stored (avoids drift).

### Event Cluster Members (junction)

```sql
CREATE TABLE event_cluster_members (
    cluster_id INTEGER REFERENCES event_clusters(id) ON DELETE CASCADE,
    headline_id INTEGER REFERENCES headlines(id) ON DELETE CASCADE,
    similarity_score FLOAT,
    PRIMARY KEY(cluster_id, headline_id)
);
```

### Tables Dropped (not carried forward)

| Old Table | Reason |
|-----------|--------|
| `topic_classifications` | Topic + confidence now inline on `headlines` (single top-1 result, no multi-rank) |
| `events` | Event extraction results stored as `entities` JSONB + `event_type` on `headlines` |
| `embeddings` | Just a Qdrant point ID on `headlines.embedding_id` — no metadata table needed |
| `processing_jobs` | Pipeline orchestration handled in-memory + Redis, not a DB queue |
| `metrics` | System metrics not needed — use logs and Redis for operational stats |

### Enum Types Dropped

`processing_status`, `event_type`, `news_category` — replaced with plain TEXT columns for flexibility.

### Views

```sql
CREATE VIEW v_recent_headlines AS
SELECT
    h.id, h.title, h.description, h.url, h.published_at,
    h.translated_title, h.topic, h.topic_confidence, h.language,
    s.name as source_name, s.country, s.group_name
FROM headlines h
JOIN sources s ON h.source_id = s.id
WHERE h.published_at > NOW() - INTERVAL '24 hours'
ORDER BY h.published_at DESC;

CREATE VIEW v_topic_stats AS
SELECT
    topic,
    COUNT(*) as headline_count,
    AVG(topic_confidence) as avg_confidence,
    MAX(published_at) as latest_headline
FROM headlines
WHERE topic IS NOT NULL
  AND published_at > NOW() - INTERVAL '7 days'
GROUP BY topic
ORDER BY headline_count DESC;
```

### Triggers

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_headlines_updated_at BEFORE UPDATE ON headlines
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_sources_updated_at BEFORE UPDATE ON sources
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_event_clusters_updated_at BEFORE UPDATE ON event_clusters
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
```

### Seeding

Seed `sources` from `data/feeds.json`. Field mapping:
- `name` → `name`
- `url` → `url`
- `language` → `language`
- `country` → `country`
- `group` → `group_name` (renamed for clarity — `group` is a SQL reserved word)
- `id` → dropped (replaced by SERIAL auto-increment)

---

## Agent Team Deployment

### Phase 1 — Foundation (sequential)

**Agent 1: Database Migration**
- Drop existing schema (clean slate)
- Create new schema (sources, headlines, event_clusters, event_cluster_members, views, triggers, indexes)
- Write migration SQL to `scripts/migrate.sql`
- Seed sources table from `data/feeds.json`
- Update Python `database.py` and `repositories.py` for new schema (SERIAL PKs, new column names)

### Phase 2 — Parallel Build (3 agents simultaneously)

**Agent 2: Frontend Core**
- Scaffold Next.js 15 app with App Router in `frontend/`
- Tailwind CSS + shadcn/ui setup
- Root layout with collapsible sidebar nav (left) + persistent data sidebar (right)
- Socket.io client hook (connects direct to Python backend URL)
- Vercel deployment config (`vercel.json`, env vars: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_WS_URL`)
- Responsive breakpoint at `lg:1024px`

**Agent 3: Backend Speed**
- Model preloading at startup (BART-MNLI, all-MiniLM-L6-v2, spaCy)
- Pipeline parallelism (classify + extract + embed concurrent via ThreadPoolExecutor)
- Batch classification (remove rate limiting)
- Redis caching for classifications and translations
- Connection pool increases
- Standardize port to 8081

**Agent 4: Backend New Features**
- Sources CRUD endpoints (GET/POST/PUT/DELETE `/api/sources`)
- Analytics aggregation endpoint (`/api/analytics`)
- Event clusters endpoint (`/api/events`, `/api/events/:id`)
- Semantic search endpoint (`/api/search`)
- Full pipeline trigger endpoint (`/api/run`)
- Pipeline status REST endpoint (`GET /api/pipeline/status`)
- WebSocket events per the event contract (status_update, headlines_update, log_message, pipeline_complete)

### Phase 3 — Frontend Pages (2 agents simultaneously)

**Agent 5: Core Pages**
- Feed page (`/`, editorial layout, search/filter, infinite scroll)
- Events page (`/events`, clustered view, timeline, entity tags)
- Pipeline page (`/pipeline`, trigger buttons, progress bars, log stream via WebSocket)

**Agent 6: Secondary Pages**
- Analytics page (`/analytics`, Recharts charts, topic distribution, source breakdown)
- Sources page (`/sources`, CRUD table, health indicators)
- Settings page (`/settings`, localStorage-based config form, theme toggle)

### Phase 4 — Integration (sequential)

**Agent 7: Integration & Polish**
- Wire all pages to API routes
- WebSocket real-time updates across all pages (data sidebar, pipeline page)
- Error handling and loading states
- Responsive/mobile layout (drawer for data sidebar below lg breakpoint)
- Data sidebar real-time updates

### Phase 5 — Review

**Agent 8: Code Review**
- Full review against this spec
- Verify all endpoints work
- Test critical user flows
- Verify Vercel deployment config
- Verify WebSocket event contract matches frontend expectations

### Phase Diagram

```
Phase 1:  [Agent 1: DB Migration]
              │
Phase 2:  [Agent 2: FE Core] [Agent 3: BE Speed] [Agent 4: BE Features]
              │                    │                    │
Phase 3:  [Agent 5: Core Pages] [Agent 6: Secondary Pages]
              │                    │
Phase 4:  [Agent 7: Integration & Polish]
              │
Phase 5:  [Agent 8: Code Review]
```

---

## What Gets Deleted

- `services/api_go/` — entire Go API gateway directory
- `ingester` service definition from `docker-compose.yml` (directory `services/ingester_go/` may not exist on disk; delete if present)
- `frontend/` — entire React + Vite frontend (replaced by Next.js)
- `docker-compose.yml` — rewritten to only include postgres, redis, qdrant, nlp_service
- `Makefile` — update targets for new architecture

## What Gets Kept

- `services/nlp_py/` — refactored, not rewritten
- `data/feeds.json` — used to seed sources table, then deprecated
- `scripts/` — migration scripts updated

## What Gets Created

- `frontend/` — new Next.js 15 app
- `services/nlp_py/pipeline/` — refactored pipeline modules
- `scripts/migrate.sql` — new clean-slate migration
- `vercel.json` — Vercel deployment config
