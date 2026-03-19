# SiftSignal — Financial News Intelligence

ML-powered financial news aggregation system. Collects 158 RSS feeds across 10 financial categories, classifies headlines by topic and sentiment, extracts entities, clusters related events, detects prediction market divergences, and serves everything through a REST API + WebSocket for real-time dashboards.

**Designed for AI agent consumption** — structured metadata (category/subcategory on every source and headline) enables future Claude agents to parse headlines, correlate cross-category signals, and draw financial conclusions.

## Architecture

```
RSS Feeds (64) → Gather → Translate → Classify + Extract (parallel) → Group Events → PostgreSQL → Flask API → Next.js Frontend
```

### Services
- **nlp_service** (Python 3.11, Flask + Flask-SocketIO, port 8081): Pipeline + API
- **PostgreSQL 15** (port 5432): Persistent storage
- **Redis 7** (port 6379): Translation cache
- **Frontend** (Next.js 15, port 3000): Dashboard UI

### Key Directories
```
data/                    # Feed configs, topic labels (JSON)
services/nlp_py/         # Python API server + ML pipeline
  pipeline/              # gather, translate, classify, extract, group_by_event
  repositories.py        # Data access layer
  api_server.py          # Flask routes + WebSocket
  database.py            # PostgreSQL connection pool
scripts/                 # migrate.sql, seed_sources.py
frontend/                # Next.js 15 app
```

## Feed System

64 financial RSS feeds in `data/feeds.json`, organized by category:

| Category | Count | Examples |
|----------|-------|---------|
| equities | 13 | CNBC, WSJ, MarketWatch, Seeking Alpha, Nasdaq, Zero Hedge |
| macro | 12 | Federal Reserve, BLS, FRED, Wolf Street, Economist |
| crypto | 7 | CoinDesk, CoinTelegraph, The Block, Decrypt |
| prediction_markets | 4 | Polymarket, Kalshi, Metaculus, Manifold |
| commodities | 6 | OilPrice, EIA, MINING.com, OPEC |
| real_estate | 4 | HousingWire, Redfin, Realtor.com, Zillow |
| regulation | 5 | SEC, CFTC, FDIC, American Banker |
| fintech | 4 | Finextra, TechCrunch Fintech, PYMNTS |
| earnings | 4 | CNBC Earnings, GlobeNewsWire, Investing.com |
| international | 5 | FT, Nikkei Asia, SCMP, WSJ World |

Each feed has `category` and `subcategory` fields for AI agent filtering.

## Topic Classification

10 financial topics in `data/topic_labels.json`:
markets, economy, earnings, crypto, commodities, real_estate, regulation, fintech, prediction_markets, mergers

Keyword-based classification (no heavy ML models). Each headline gets top-3 topic assignments with confidence scores.

## AI Agent Design

The system is structured for programmatic consumption by AI agents:

- **Source metadata**: Every source has `category` + `subcategory` fields
- **Headline enrichment**: Headlines carry source category, topic classification, entities, and event type
- **Event clusters**: Related headlines grouped with similarity scores and shared entities
- **Correlation hints**: `feeds.json` metadata includes cross-category signal patterns (e.g., "Fed policy → market reaction")
- **API filtering**: Filter headlines by topic, category, language, source — all via query params

### API Endpoints (port 8081)
- `GET /api/headlines` — paginated, filterable by topic/language/source/search
- `GET /api/events` — event clusters with member headlines
- `GET /api/analytics` — topic distribution, volume trends, source breakdown
- `GET /api/sources` — filterable by category/subcategory/language/active
- `POST /api/sources` — add new RSS source
- `POST /api/run` — trigger full pipeline
- WebSocket: `status_update`, `log_message`, `headlines_update`, `pipeline_complete`

## Development

```bash
# Start all services
docker compose up -d

# Run schema migration
docker compose exec postgres psql -U news_user -d news_ai -f /scripts/migrate.sql

# Seed feeds into DB
python scripts/seed_sources.py

# Frontend dev
cd frontend && npm run dev
```

## Database

PostgreSQL with tables: `sources`, `headlines`, `event_clusters`, `event_cluster_members`.
Sources table has `category` and `subcategory` columns for financial domain tagging.
Full-text search via `pg_trgm` extension.

## Conventions

- All config in JSON files under `data/` — no hardcoded feed URLs or topics in code
- Repository pattern for all DB access (`repositories.py`)
- Pipeline stages are independent modules in `services/nlp_py/pipeline/`
- Frontend uses `api.ts` typed client for all API calls
- WebSocket for real-time pipeline status and headline updates
