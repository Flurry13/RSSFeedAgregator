# SiftSignal

Financial news intelligence platform. Aggregates 158 RSS feeds across 10 financial categories, classifies headlines by topic and sentiment, clusters related events, detects prediction market divergences, and serves structured data for both human browsing and AI agent consumption.

## What it does

- **Collects** headlines from 158 financial RSS feeds (CNBC, WSJ, Bloomberg, CoinDesk, Fed, SEC, Polymarket, and 150+ more)
- **Classifies** every headline into 10 financial topics (markets, economy, crypto, commodities, earnings, regulation, fintech, real estate, prediction markets, M&A)
- **Analyzes sentiment** as bullish, bearish, or neutral using keyword matching
- **Clusters** related headlines into event groups using entity extraction and similarity scoring
- **Detects divergences** between prediction market sentiment and broader market sentiment
- **Serves** everything through a REST API designed for AI agents to query programmatically

## Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS, Recharts, Socket.IO |
| API | Python 3.11, Flask, Flask-SocketIO |
| NLP | spaCy (NER), keyword-based classification and sentiment |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |
| Infrastructure | Docker Compose |

## Quick Start

```bash
# Start all services
docker compose up -d

# Run database migration
docker compose exec postgres psql -U news_user -d news_ai -f /scripts/migrate.sql

# Seed RSS feeds
python scripts/seed_sources.py

# Start frontend
cd frontend && npm install && npm run dev

# Trigger first pipeline run
curl -X POST http://localhost:8081/api/run
```

- Frontend: http://localhost:3000
- API: http://localhost:8081

## Pages

| Page | What it shows |
|------|---------------|
| Feed | Headline stream with topic/sentiment badges, search, filters. URL-synced filters. |
| Events | Entity-based event clusters with sentiment summaries and date ranges |
| Analytics | Topic distribution, sentiment distribution, category breakdown, Topic x Category heatmap, daily volume, top sources |
| Insights | AI-agent-friendly summary: market sentiment by category, feed health, top clusters, prediction market signals. Copy/download as JSON. |
| Predictions | Prediction market headlines cross-referenced with equities/macro/crypto. Sentiment divergence detection. |
| Pipeline | Run/schedule the pipeline, view logs, run history |
| Settings | Pipeline scheduler (15m/30m/1h/4h), default filters, data retention, CSV/JSON export |

## Pipeline

```
RSS Feeds (158) --> Gather --> Translate --> Classify + Sentiment + Extract (parallel) --> Group Events --> Store
```

Runs on demand or on a configurable schedule. Each run:
1. Fetches all 158 feeds concurrently (ThreadPoolExecutor, ~15s)
2. Translates non-English headlines
3. Classifies topic, analyzes sentiment, and extracts entities in parallel
4. Clusters related headlines by entity overlap and word similarity
5. Stores everything to PostgreSQL with structured metadata

## API

### Headlines
- `GET /api/headlines` — paginated, filterable by topic, sentiment, language, source, search
- `GET /api/headlines/export?format=csv&period=24h` — CSV/JSON export

### Events
- `GET /api/events` — event clusters with member headlines
- `GET /api/events/:id` — cluster detail with all headlines

### Analytics
- `GET /api/analytics?period=24h` — topic distribution, sentiment, category breakdown, heatmap, volume

### Insights (AI Agent API)
- `GET /api/insights/summary?period=24h` — structured financial intelligence: top headlines by category, sentiment breakdown per category, feed health, top clusters
- `GET /api/insights/category/:category?period=24h` — deep dive on one category
- `GET /api/insights/predictions?period=24h` — prediction market cross-references and sentiment divergences

### Sources & Pipeline
- `GET/POST/PUT/DELETE /api/sources` — CRUD with category/subcategory filtering
- `POST /api/run` — trigger full pipeline
- `GET /api/pipeline/status` — current pipeline state
- `GET /api/pipeline/history` — past run records

### Settings
- `GET/PUT /api/settings` — persistent key-value settings (schedule, defaults, retention)

### WebSocket
- `status_update` — pipeline stage changes
- `log_message` — pipeline logs
- `headlines_update` — new headlines available
- `pipeline_complete` — run finished

## Feed Categories

| Category | Feeds | Examples |
|----------|-------|---------|
| Equities | 35 | CNBC, WSJ, MarketWatch, Bloomberg, Benzinga, Seeking Alpha, Nasdaq |
| Macro | 28 | Federal Reserve, BLS, IMF, World Bank, ECB, FRED, Economist |
| International | 25 | FT, Nikkei Asia, SCMP, BBC Business, LiveMint, Straits Times |
| Crypto | 14 | CoinDesk, CoinTelegraph, The Block, Decrypt, Blockworks |
| Commodities | 14 | OilPrice, EIA, OPEC, MINING.com, USDA, S&P Commodity Insights |
| Regulation | 10 | SEC, CFTC, FDIC, OCC, DOJ Antitrust, FTC, ECB Supervision |
| Real Estate | 9 | HousingWire, Redfin, Zillow, Mortgage News Daily, Bisnow |
| Fintech | 9 | Finextra, TechCrunch, PYMNTS, Tearsheet, Sifted |
| Earnings | 9 | CNBC Earnings, GlobeNewsWire, PR Newswire, S&P Global |
| Prediction Markets | 5 | Polymarket, Kalshi, Metaculus, Manifold, PredictIt |

## For AI Agents

The API is designed for programmatic consumption. A Claude agent can:

```
GET /api/insights/summary?period=24h
```

Returns structured JSON with:
- Sentiment breakdown (bullish/bearish/neutral counts)
- Sentiment by category (which sectors are most bearish right now)
- Top headlines per category (highest confidence classifications)
- Top event clusters (what entities dominate the news)
- Feed health (how many sources are working)
- Prediction market divergences (where PM sentiment disagrees with market sentiment)

All sources and headlines carry `category` and `subcategory` metadata for filtering. The `correlation_hints` in `data/feeds.json` suggest cross-category signal patterns.

## License

MIT
