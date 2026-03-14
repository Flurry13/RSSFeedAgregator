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
│         Server (Docker Compose)               │
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

---

## Frontend

### Tech Stack

- Next.js 15 (App Router, Server Components)
- Tailwind CSS + shadcn/ui
- Socket.io client for real-time
- Recharts or Tremor for analytics charts
- Deployed on Vercel (free tier)

### Visual Direction

Hybrid editorial feed + data sidebar:
- Main content area: clean, typography-driven editorial feed
- Persistent right sidebar: pipeline status, topic breakdown, headline count
- Dark theme with light mode toggle
- Collapsible sidebar nav on the left
- Desktop sidebar, mobile drawer for the data panel

### Pages

| Page | Route | Purpose |
|------|-------|---------|
| Feed | `/` | Main editorial headline feed — search, filter by topic/language/source, infinite scroll |
| Events | `/events` | Clustered event view — grouped articles, timeline, entity tags. ML showcase page. |
| Analytics | `/analytics` | Charts — topic distribution over time, source breakdown, language heatmap, daily volume |
| Pipeline | `/pipeline` | Control panel — trigger gather/translate/classify, real-time progress bars, log stream |
| Sources | `/sources` | Manage RSS feeds — add/remove/edit, per-source stats, health status, last fetched |
| Settings | `/settings` | Config — refresh intervals, theme toggle, notification prefs |

### Navigation

- Left sidebar nav (collapsible) with icons + labels for all 6 pages
- Right data sidebar (persistent on desktop, drawer on mobile) showing:
  - Pipeline status indicator (idle/running/error)
  - Quick topic breakdown (top 5 topics with percentages)
  - Headline count + sources count
  - Last pipeline run timestamp

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

## API Contract

### Next.js API Routes → Python Backend

| Next.js Route | Python Endpoint | Method | Purpose |
|---|---|---|---|
| `/api/headlines` | `/api/headlines` | GET | Paginated headlines with filters (topic, language, source, search) |
| `/api/events` | `/api/events` | GET | Event clusters with member articles |
| `/api/events/[id]` | `/api/events/:id` | GET | Single event cluster detail |
| `/api/analytics` | `/api/analytics` | GET | Aggregated stats (topic dist, source counts, volume over time) |
| `/api/pipeline/gather` | `/api/gather` | POST | Trigger RSS gathering |
| `/api/pipeline/translate` | `/api/translate` | POST | Trigger translation |
| `/api/pipeline/classify` | `/api/classify` | POST | Trigger classification |
| `/api/pipeline/run` | `/api/run` | POST | Run full pipeline end-to-end |
| `/api/pipeline/status` | WebSocket | — | Real-time progress via Socket.io |
| `/api/sources` | `/api/sources` | GET/POST/PUT/DELETE | CRUD for RSS feed sources |
| `/api/search` | `/api/search` | GET | Semantic search via Qdrant vectors |

### New vs Current

- `/api/analytics` — new, aggregation queries on Postgres
- `/api/classify` — new, separate trigger (currently bundled)
- `/api/run` — new, one-click full pipeline
- `/api/sources` — new, feed management (currently hardcoded in feeds.json → moves to Postgres)
- `/api/search` — new, semantic search leveraging Qdrant embeddings

---

## Database Schema

### Sources Table (replaces feeds.json)

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
```

### Headlines Table (enhanced)

```sql
CREATE TABLE headlines (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id),
    title TEXT NOT NULL,
    translated_title TEXT,
    url TEXT NOT NULL,
    language TEXT,
    published_at TIMESTAMPTZ,
    topic TEXT,
    topic_confidence FLOAT,
    entities JSONB,
    event_type TEXT,
    embedding_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(url, source_id)
);
```

### Event Clusters Table (new)

```sql
CREATE TABLE event_clusters (
    id SERIAL PRIMARY KEY,
    label TEXT NOT NULL,
    event_type TEXT,
    headline_count INTEGER DEFAULT 0,
    key_entities JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Event Cluster Members (junction)

```sql
CREATE TABLE event_cluster_members (
    cluster_id INTEGER REFERENCES event_clusters(id) ON DELETE CASCADE,
    headline_id INTEGER REFERENCES headlines(id) ON DELETE CASCADE,
    similarity_score FLOAT,
    PRIMARY KEY(cluster_id, headline_id)
);
```

### Migration Plan

1. Create `sources` table, seed from `feeds.json`
2. Add `source_id` column to `headlines`, backfill from existing `feed_id` strings
3. Create `event_clusters` and `event_cluster_members` tables
4. Add new columns to `headlines` (topic_confidence, entities, event_type, embedding_id)
5. Drop deprecated columns

---

## Agent Team Deployment

### Phase 1 — Foundation (sequential)

**Agent 1: Database Migration**
- Create new schema (sources, event_clusters, event_cluster_members)
- Write migration SQL
- Seed sources table from feeds.json
- Update Python repositories and models

### Phase 2 — Parallel Build (3 agents simultaneously)

**Agent 2: Frontend Core**
- Scaffold Next.js 15 app with App Router
- Tailwind CSS + shadcn/ui setup
- Root layout with collapsible sidebar nav + persistent data sidebar
- Socket.io client hook
- Vercel deployment config (vercel.json, env vars)

**Agent 3: Backend Speed**
- Model preloading at startup (BART-MNLI, all-MiniLM-L6-v2, spaCy)
- Pipeline parallelism (classify + extract + embed concurrent via ThreadPoolExecutor)
- Batch classification (remove rate limiting)
- Redis caching for classifications and translations
- Connection pool increases

**Agent 4: Backend New Features**
- Sources CRUD endpoints (GET/POST/PUT/DELETE /api/sources)
- Analytics aggregation endpoint (/api/analytics)
- Event clusters endpoint (/api/events, /api/events/:id)
- Semantic search endpoint (/api/search)
- Full pipeline trigger endpoint (/api/run)

### Phase 3 — Frontend Pages (2 agents simultaneously)

**Agent 5: Core Pages**
- Feed page (/, editorial layout, search/filter, infinite scroll)
- Events page (/events, clustered view, timeline, entity tags)
- Pipeline page (/pipeline, trigger buttons, progress bars, log stream)

**Agent 6: Secondary Pages**
- Analytics page (/analytics, Recharts/Tremor charts, topic dist, source breakdown)
- Sources page (/sources, CRUD table, health indicators)
- Settings page (/settings, config form, theme toggle)

### Phase 4 — Integration (sequential)

**Agent 7: Integration & Polish**
- Wire all pages to API routes
- WebSocket real-time updates across all pages
- Error handling and loading states
- Responsive/mobile layout
- Data sidebar real-time updates

### Phase 5 — Review

**Agent 8: Code Review**
- Full review against this spec
- Verify all endpoints work
- Test critical user flows
- Verify Vercel deployment config

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

- `services/api_go/` — entire Go API gateway
- `frontend/` — entire React + Vite frontend
- `docker-compose.yml` — rewrite to remove go, frontend, ingester, jaeger services
- `Makefile` — update targets for new architecture

## What Gets Kept

- `services/nlp_py/` — refactored, not rewritten
- `data/feeds.json` — used to seed sources table, then deprecated
- `scripts/` — migration scripts updated

## What Gets Created

- `frontend/` — new Next.js 15 app (or top-level next.js project)
- `services/nlp_py/pipeline/` — refactored pipeline modules
- `scripts/migrate.sql` — new migration for schema changes
