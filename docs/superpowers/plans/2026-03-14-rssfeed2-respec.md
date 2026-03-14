# RSSFeed2 Full Respec — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the RSSFeed2 news aggregator with Next.js 15 frontend on Vercel, optimized Python ML backend, simplified Docker infrastructure, and a hybrid editorial + data dashboard UI.

**Architecture:** Next.js 15 (App Router) deployed on Vercel proxies API requests to a Python Flask-SocketIO backend running in Docker alongside Postgres, Redis, and Qdrant. The Go API gateway is eliminated. The ML pipeline runs classify/extract/embed in parallel for ~40-50% speed improvement.

**Tech Stack:** Next.js 15, Tailwind CSS, shadcn/ui, Recharts, Socket.io, Flask, Flask-SocketIO, transformers, sentence-transformers, spaCy, HDBSCAN, PostgreSQL 15, Redis 7, Qdrant, Docker Compose

**Spec:** `docs/superpowers/specs/2026-03-14-rssfeed2-respec-design.md`

---

## Chunk 1: Cleanup & Database Migration (Phase 0 + Phase 1)

> **Agent 1** — Sequential, must complete before all other phases.
> Removes old Go/frontend code, rewrites Docker config, creates new DB schema, updates Python data layer.

---

### Task 1: Delete Old Services & Rewrite Docker Compose

**Files:**
- Delete: `services/api_go/` (entire directory)
- Delete: `services/ingester_go/` (if exists)
- Delete: `frontend/` (entire directory)
- Modify: `docker-compose.yml`
- Modify: `Makefile`

- [ ] **Step 1: Delete Go API gateway directory**

```bash
rm -rf services/api_go/
```

- [ ] **Step 2: Delete Go ingester directory (if exists)**

```bash
rm -rf services/ingester_go/ 2>/dev/null || true
```

- [ ] **Step 3: Delete old React frontend**

```bash
rm -rf frontend/
```

- [ ] **Step 4: Rewrite docker-compose.yml**

Replace the entire file with 4 services only: postgres, redis, qdrant, nlp_service.

```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: news_ai
      POSTGRES_USER: ${POSTGRES_USER:-news_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-news_pass}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-news_user}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/healthz"]
      interval: 10s
      timeout: 5s
      retries: 5

  nlp_service:
    build:
      context: ./services/nlp_py
      dockerfile: Dockerfile
    ports:
      - "8081:8081"
    environment:
      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
      - POSTGRES_DB=news_ai
      - POSTGRES_USER=${POSTGRES_USER:-news_user}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-news_pass}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
      - CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:3000}
      - LOG_LEVEL=${LOG_LEVEL:-info}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      qdrant:
        condition: service_healthy
    volumes:
      - model_cache:/app/models
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  model_cache:
```

- [ ] **Step 5: Update Makefile**

Replace Makefile with targets for the new architecture:

```makefile
.PHONY: build up down logs test lint migrate seed health

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

logs-nlp:
	docker compose logs -f nlp_service

migrate:
	docker compose exec postgres psql -U $${POSTGRES_USER:-news_user} -d news_ai -f /dev/stdin < scripts/migrate.sql

seed:
	docker compose exec nlp_service python scripts/seed_sources.py

health:
	@echo "Postgres:" && docker compose exec postgres pg_isready -U $${POSTGRES_USER:-news_user} 2>/dev/null && echo "OK" || echo "FAIL"
	@echo "Redis:" && docker compose exec redis redis-cli ping 2>/dev/null || echo "FAIL"
	@echo "Qdrant:" && curl -sf http://localhost:6333/healthz && echo " OK" || echo "FAIL"
	@echo "NLP:" && curl -sf http://localhost:8081/health && echo " OK" || echo "FAIL"

test:
	cd services/nlp_py && python -m pytest tests/ -v

restart-nlp:
	docker compose restart nlp_service
```

- [ ] **Step 6: Commit cleanup**

```bash
git add -A
git commit -m "chore: remove Go gateway, old frontend, and simplify Docker to 4 services"
```

---

### Task 2: Write New Database Migration

**Files:**
- Overwrite: `scripts/migrate.sql`

- [ ] **Step 1: Write the new clean-slate migration SQL**

Overwrite `scripts/migrate.sql` with the complete new schema from the spec:

```sql
-- RSSFeed2 Clean-Slate Schema
-- Drops all old tables and creates new simplified schema

-- Drop old schema (order matters for foreign keys)
DROP VIEW IF EXISTS v_topic_statistics CASCADE;
DROP VIEW IF EXISTS v_recent_headlines CASCADE;
DROP TABLE IF EXISTS event_group_members CASCADE;
DROP TABLE IF EXISTS event_groups CASCADE;
DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS topic_classifications CASCADE;
DROP TABLE IF EXISTS embeddings CASCADE;
DROP TABLE IF EXISTS processing_jobs CASCADE;
DROP TABLE IF EXISTS metrics CASCADE;
DROP TABLE IF EXISTS headlines CASCADE;
DROP TABLE IF EXISTS feeds CASCADE;

-- Drop old enum types
DROP TYPE IF EXISTS processing_status CASCADE;
DROP TYPE IF EXISTS event_type CASCADE;
DROP TYPE IF EXISTS news_category CASCADE;

-- Drop old extensions we no longer need
DROP EXTENSION IF EXISTS "uuid-ossp";
DROP EXTENSION IF EXISTS "btree_gin";

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Drop old trigger function if exists
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- Sources table (replaces feeds.json and old feeds table)
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

-- Headlines table (simplified)
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
    embedding_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(url, source_id)
);

CREATE INDEX idx_headlines_source_id ON headlines(source_id);
CREATE INDEX idx_headlines_published_at ON headlines(published_at);
CREATE INDEX idx_headlines_language ON headlines(language);
CREATE INDEX idx_headlines_topic ON headlines(topic);
CREATE INDEX idx_headlines_title_fts ON headlines USING gin(to_tsvector('simple', title));

-- Event clusters table
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

-- Event cluster members (junction)
CREATE TABLE event_cluster_members (
    cluster_id INTEGER REFERENCES event_clusters(id) ON DELETE CASCADE,
    headline_id INTEGER REFERENCES headlines(id) ON DELETE CASCADE,
    similarity_score FLOAT,
    PRIMARY KEY(cluster_id, headline_id)
);

CREATE INDEX idx_ecm_headline_id ON event_cluster_members(headline_id);

-- Views
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

-- Trigger for updated_at
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

- [ ] **Step 2: Commit migration**

```bash
git add scripts/migrate.sql
git commit -m "feat: rewrite DB schema — clean slate with sources, headlines, event_clusters"
```

---

### Task 3: Write Source Seeder Script

**Files:**
- Create: `scripts/seed_sources.py`

- [ ] **Step 1: Create the seeder script**

```python
#!/usr/bin/env python3
"""Seed the sources table from data/feeds.json."""
import json
import os
import sys

import psycopg2

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "dbname": os.getenv("POSTGRES_DB", "news_ai"),
    "user": os.getenv("POSTGRES_USER", "news_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "news_pass"),
}

FEEDS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "feeds.json")


def seed():
    with open(FEEDS_PATH) as f:
        feeds = json.load(f)

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    inserted = 0
    skipped = 0
    for feed in feeds:
        try:
            cur.execute(
                """INSERT INTO sources (name, url, language, country, group_name)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (url) DO NOTHING""",
                (
                    feed.get("name", ""),
                    feed["url"],
                    feed.get("language", "en"),
                    feed.get("country"),
                    feed.get("group"),
                ),
            )
            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"Error inserting {feed.get('name')}: {e}")
            conn.rollback()
            continue

    conn.commit()
    cur.close()
    conn.close()
    print(f"Seeded {inserted} sources ({skipped} already existed)")


if __name__ == "__main__":
    seed()
```

- [ ] **Step 2: Commit seeder**

```bash
git add scripts/seed_sources.py
git commit -m "feat: add source seeder script to populate sources from feeds.json"
```

---

### Task 4: Update Python Database Layer

**Files:**
- Modify: `services/nlp_py/database.py`
- Rewrite: `services/nlp_py/repositories.py`

- [ ] **Step 1: Update database.py — increase pool max to 20**

In `services/nlp_py/database.py`, the `init_connection_pool` function already accepts `max_conn=20` as default. Verify this is correct. The only change needed is ensuring the default matches:

```python
# In database.py, verify init_connection_pool signature:
def init_connection_pool(min_conn=2, max_conn=20):
```

No change needed if already `max_conn=20`. Read the file to confirm.

- [ ] **Step 2: Rewrite repositories.py for new schema**

Replace `services/nlp_py/repositories.py` entirely. The new schema uses SERIAL integer PKs instead of UUIDs, `sources` instead of `feeds`, and has different column names.

```python
"""Repository layer for database operations against the new schema."""
from typing import Any, Dict, List, Optional
from datetime import datetime

from database import get_db_cursor


class SourceRepository:
    """CRUD operations for the sources table."""

    @staticmethod
    def get_all(active_only: bool = True) -> List[Dict]:
        with get_db_cursor() as cur:
            if active_only:
                cur.execute("SELECT * FROM sources WHERE active = TRUE ORDER BY name")
            else:
                cur.execute("SELECT * FROM sources ORDER BY name")
            return cur.fetchall() or []

    @staticmethod
    def get_by_id(source_id: int) -> Optional[Dict]:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM sources WHERE id = %s", (source_id,))
            return cur.fetchone()

    @staticmethod
    def create(data: Dict[str, Any]) -> Optional[Dict]:
        with get_db_cursor() as cur:
            cur.execute(
                """INSERT INTO sources (name, url, language, country, group_name, active)
                   VALUES (%(name)s, %(url)s, %(language)s, %(country)s, %(group_name)s, %(active)s)
                   RETURNING *""",
                {
                    "name": data["name"],
                    "url": data["url"],
                    "language": data.get("language", "en"),
                    "country": data.get("country"),
                    "group_name": data.get("group_name"),
                    "active": data.get("active", True),
                },
            )
            return cur.fetchone()

    @staticmethod
    def update(source_id: int, data: Dict[str, Any]) -> Optional[Dict]:
        fields = []
        values = []
        for key in ("name", "url", "language", "country", "group_name", "active"):
            if key in data:
                fields.append(f"{key} = %s")
                values.append(data[key])
        if not fields:
            return SourceRepository.get_by_id(source_id)
        values.append(source_id)
        with get_db_cursor() as cur:
            cur.execute(
                f"UPDATE sources SET {', '.join(fields)} WHERE id = %s RETURNING *",
                values,
            )
            return cur.fetchone()

    @staticmethod
    def delete(source_id: int) -> bool:
        with get_db_cursor() as cur:
            cur.execute("DELETE FROM sources WHERE id = %s", (source_id,))
            return cur.rowcount > 0

    @staticmethod
    def update_last_fetched(source_id: int, error: Optional[str] = None) -> bool:
        with get_db_cursor() as cur:
            cur.execute(
                """UPDATE sources SET last_fetched_at = NOW(), fetch_error = %s
                   WHERE id = %s""",
                (error, source_id),
            )
            return cur.rowcount > 0

    @staticmethod
    def get_paginated(
        page: int = 1,
        limit: int = 50,
        active: Optional[bool] = None,
        language: Optional[str] = None,
        group_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        conditions = []
        params = []
        if active is not None:
            conditions.append("active = %s")
            params.append(active)
        if language:
            conditions.append("language = %s")
            params.append(language)
        if group_name:
            conditions.append("group_name = %s")
            params.append(group_name)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = (page - 1) * limit

        with get_db_cursor() as cur:
            cur.execute(f"SELECT COUNT(*) as count FROM sources {where}", params)
            total = cur.fetchone()["count"]

            cur.execute(
                f"SELECT * FROM sources {where} ORDER BY name LIMIT %s OFFSET %s",
                params + [limit, offset],
            )
            data = cur.fetchall() or []

        return {
            "data": data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": (total + limit - 1) // limit,
            },
        }


class HeadlineRepository:
    """CRUD operations for the headlines table."""

    @staticmethod
    def bulk_insert(headlines: List[Dict[str, Any]]) -> Dict[str, int]:
        inserted = 0
        skipped = 0
        with get_db_cursor() as cur:
            for h in headlines:
                try:
                    cur.execute(
                        """INSERT INTO headlines
                           (source_id, title, description, url, published_at, language)
                           VALUES (%s, %s, %s, %s, %s, %s)
                           ON CONFLICT (url, source_id) DO NOTHING""",
                        (
                            h.get("source_id"),
                            h["title"],
                            h.get("description"),
                            h["url"],
                            h.get("published_at"),
                            h.get("language"),
                        ),
                    )
                    if cur.rowcount > 0:
                        inserted += 1
                    else:
                        skipped += 1
                except Exception:
                    skipped += 1
        return {"inserted": inserted, "skipped": skipped}

    @staticmethod
    def get_paginated(
        page: int = 1,
        limit: int = 50,
        sort: str = "published_at",
        order: str = "desc",
        topic: Optional[str] = None,
        language: Optional[str] = None,
        source_id: Optional[int] = None,
        q: Optional[str] = None,
    ) -> Dict[str, Any]:
        allowed_sorts = {"published_at", "created_at", "title"}
        sort = sort if sort in allowed_sorts else "published_at"
        order = "ASC" if order.lower() == "asc" else "DESC"

        conditions = []
        params = []
        if topic:
            conditions.append("h.topic = %s")
            params.append(topic)
        if language:
            conditions.append("h.language = %s")
            params.append(language)
        if source_id:
            conditions.append("h.source_id = %s")
            params.append(source_id)
        if q:
            conditions.append("to_tsvector('simple', h.title) @@ plainto_tsquery('simple', %s)")
            params.append(q)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = (page - 1) * limit

        with get_db_cursor() as cur:
            cur.execute(
                f"""SELECT COUNT(*) as count FROM headlines h {where}""",
                params,
            )
            total = cur.fetchone()["count"]

            cur.execute(
                f"""SELECT h.*, s.name as source_name, s.country, s.group_name
                    FROM headlines h
                    JOIN sources s ON h.source_id = s.id
                    {where}
                    ORDER BY h.{sort} {order}
                    LIMIT %s OFFSET %s""",
                params + [limit, offset],
            )
            data = cur.fetchall() or []

        return {
            "data": data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": (total + limit - 1) // limit,
            },
        }

    @staticmethod
    def get_count() -> int:
        with get_db_cursor() as cur:
            cur.execute("SELECT COUNT(*) as count FROM headlines")
            return cur.fetchone()["count"]

    @staticmethod
    def update_topic(headline_id: int, topic: str, confidence: float) -> bool:
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE headlines SET topic = %s, topic_confidence = %s WHERE id = %s",
                (topic, confidence, headline_id),
            )
            return cur.rowcount > 0

    @staticmethod
    def update_translation(headline_id: int, translated_title: str) -> bool:
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE headlines SET translated_title = %s WHERE id = %s",
                (translated_title, headline_id),
            )
            return cur.rowcount > 0

    @staticmethod
    def update_entities(headline_id: int, entities: dict, event_type: str) -> bool:
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE headlines SET entities = %s, event_type = %s WHERE id = %s",
                (json.dumps(entities), event_type, headline_id),
            )
            return cur.rowcount > 0

    @staticmethod
    def update_embedding_id(headline_id: int, embedding_id: str) -> bool:
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE headlines SET embedding_id = %s WHERE id = %s",
                (embedding_id, headline_id),
            )
            return cur.rowcount > 0


class EventClusterRepository:
    """CRUD operations for event clusters."""

    @staticmethod
    def create_cluster(label: str, event_type: str, key_entities: dict,
                       summary: str, start_time, end_time,
                       headline_ids: List[int],
                       similarity_scores: List[float]) -> Optional[Dict]:
        with get_db_cursor() as cur:
            cur.execute(
                """INSERT INTO event_clusters (label, event_type, key_entities, summary, start_time, end_time)
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
                (label, event_type, json.dumps(key_entities), summary, start_time, end_time),
            )
            cluster = cur.fetchone()
            if not cluster:
                return None

            for hid, score in zip(headline_ids, similarity_scores):
                cur.execute(
                    """INSERT INTO event_cluster_members (cluster_id, headline_id, similarity_score)
                       VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
                    (cluster["id"], hid, score),
                )
            return cluster

    @staticmethod
    def get_paginated(
        page: int = 1,
        limit: int = 50,
        event_type: Optional[str] = None,
        since: Optional[str] = None,
    ) -> Dict[str, Any]:
        conditions = []
        params = []
        if event_type:
            conditions.append("ec.event_type = %s")
            params.append(event_type)
        if since:
            conditions.append("ec.start_time >= %s")
            params.append(since)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = (page - 1) * limit

        with get_db_cursor() as cur:
            cur.execute(f"SELECT COUNT(*) as count FROM event_clusters ec {where}", params)
            total = cur.fetchone()["count"]

            cur.execute(
                f"""SELECT ec.*,
                           (SELECT COUNT(*) FROM event_cluster_members WHERE cluster_id = ec.id) as headline_count
                    FROM event_clusters ec
                    {where}
                    ORDER BY ec.created_at DESC
                    LIMIT %s OFFSET %s""",
                params + [limit, offset],
            )
            data = cur.fetchall() or []

        return {
            "data": data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": (total + limit - 1) // limit,
            },
        }

    @staticmethod
    def get_by_id(cluster_id: int) -> Optional[Dict]:
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT ec.*,
                          (SELECT COUNT(*) FROM event_cluster_members WHERE cluster_id = ec.id) as headline_count
                   FROM event_clusters ec WHERE ec.id = %s""",
                (cluster_id,),
            )
            cluster = cur.fetchone()
            if not cluster:
                return None

            cur.execute(
                """SELECT h.*, s.name as source_name, ecm.similarity_score
                   FROM event_cluster_members ecm
                   JOIN headlines h ON ecm.headline_id = h.id
                   JOIN sources s ON h.source_id = s.id
                   WHERE ecm.cluster_id = %s
                   ORDER BY ecm.similarity_score DESC""",
                (cluster_id,),
            )
            cluster["headlines"] = cur.fetchall() or []
            return cluster


class AnalyticsRepository:
    """Aggregation queries for analytics."""

    @staticmethod
    def get_analytics(period: str = "7d") -> Dict[str, Any]:
        interval_map = {"24h": "24 hours", "7d": "7 days", "30d": "30 days"}
        interval = interval_map.get(period, "7 days")

        with get_db_cursor() as cur:
            # Topic distribution
            cur.execute(
                """SELECT topic, COUNT(*) as count, AVG(topic_confidence) as avg_confidence
                   FROM headlines
                   WHERE topic IS NOT NULL AND published_at > NOW() - INTERVAL %s
                   GROUP BY topic ORDER BY count DESC""",
                (interval,),
            )
            topic_distribution = cur.fetchall() or []

            # Source breakdown
            cur.execute(
                """SELECT s.id as source_id, s.name, COUNT(h.id) as count
                   FROM sources s
                   LEFT JOIN headlines h ON h.source_id = s.id
                     AND h.published_at > NOW() - INTERVAL %s
                   GROUP BY s.id, s.name ORDER BY count DESC""",
                (interval,),
            )
            source_breakdown = cur.fetchall() or []

            # Language breakdown
            cur.execute(
                """SELECT language, COUNT(*) as count
                   FROM headlines
                   WHERE published_at > NOW() - INTERVAL %s
                   GROUP BY language ORDER BY count DESC""",
                (interval,),
            )
            language_breakdown = cur.fetchall() or []

            # Daily volume
            cur.execute(
                """SELECT DATE(published_at) as date, COUNT(*) as count
                   FROM headlines
                   WHERE published_at > NOW() - INTERVAL %s
                   GROUP BY DATE(published_at) ORDER BY date""",
                (interval,),
            )
            daily_volume = cur.fetchall() or []

        return {
            "topic_distribution": topic_distribution,
            "source_breakdown": source_breakdown,
            "language_breakdown": language_breakdown,
            "daily_volume": daily_volume,
            "period": period,
        }
```

**Important:** The file must start with `import json` in the imports block:

```python
"""Repository layer for database operations against the new schema."""
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from database import get_db_cursor
```

- [ ] **Step 3: Verify database.py pool max is 20**

Read `services/nlp_py/database.py` and verify `init_connection_pool` defaults to `max_conn=20`. If not, update it.

- [ ] **Step 4: Commit data layer updates**

```bash
git add services/nlp_py/database.py services/nlp_py/repositories.py
git commit -m "feat: rewrite repositories for new schema — sources, headlines, event_clusters, analytics"
```

---

### Task 5: Update gather.py to Use Sources Table

**Files:**
- Modify: `services/nlp_py/pipeline/gather.py`

- [ ] **Step 1: Update gather.py to load feeds from database**

The `gather.py` module currently loads feeds from `data/feeds.json` at import time. Update it to optionally load from the `sources` table instead. Add a `load_feeds_from_db()` function and modify `gather()` to prefer DB sources when available.

Add near the top of `gather.py`, after existing imports:

```python
def load_feeds_from_db():
    """Load active feed sources from the database."""
    try:
        from repositories import SourceRepository
        sources = SourceRepository.get_all(active_only=True)
        return [
            {
                "id": s["id"],
                "name": s["name"],
                "url": s["url"],
                "language": s.get("language", "en"),
                "country": s.get("country", ""),
                "group": s.get("group_name", ""),
            }
            for s in sources
        ]
    except Exception:
        return None
```

Update the `gather()` function to try DB first, fall back to JSON:

```python
def gather(use_async=True, max_concurrent=20):
    db_feeds = load_feeds_from_db()
    feeds = db_feeds if db_feeds else feedList
    # ... rest of gather logic using feeds
```

- [ ] **Step 2: Update gather results to include source_id**

When returning headline dicts from `process_single_feed`, include the source's database ID if available:

```python
headline["source_id"] = feed_item.get("id")
```

- [ ] **Step 3: Commit gather updates**

```bash
git add services/nlp_py/pipeline/gather.py
git commit -m "feat: gather.py loads feeds from sources table, falls back to feeds.json"
```

---

## Chunk 2: Backend Speed Optimizations (Phase 2 — Agent 3)

> **Agent 3** — Runs in parallel with Agents 2 and 4.
> Model preloading, pipeline parallelism, batch processing, Redis caching.

---

### Task 6: Create Model Preloader

**Files:**
- Create: `services/nlp_py/model_loader.py`

- [ ] **Step 1: Create model_loader.py**

This module loads all ML models once at startup and provides accessors.

```python
"""Preload all ML models at startup. Import this module early to warm models."""
import logging
import time

logger = logging.getLogger(__name__)

_classifier = None
_embedder = None
_extractor = None


def preload_models():
    """Load all ML models into memory. Call once at startup."""
    global _classifier, _embedder, _extractor

    start = time.time()
    logger.info("Preloading ML models...")

    # 1. Topic classifier (BART-MNLI) — heaviest model
    from pipeline.classify import TopicClassifier
    _classifier = TopicClassifier()
    logger.info("  Classifier loaded (%.1fs)", time.time() - start)

    # 2. Text embedder (all-MiniLM-L6-v2)
    t = time.time()
    from pipeline.embed import TextEmbedder
    _embedder = TextEmbedder()
    logger.info("  Embedder loaded (%.1fs)", time.time() - t)

    # 3. Event extractor (spaCy en_core_web_sm)
    t = time.time()
    from pipeline.event_extract import EventExtractor
    _extractor = EventExtractor()
    logger.info("  Extractor loaded (%.1fs)", time.time() - t)

    logger.info("All models preloaded in %.1fs", time.time() - start)


def get_classifier():
    """Get the preloaded TopicClassifier instance."""
    global _classifier
    if _classifier is None:
        from pipeline.classify import TopicClassifier
        _classifier = TopicClassifier()
    return _classifier


def get_embedder():
    """Get the preloaded TextEmbedder instance."""
    global _embedder
    if _embedder is None:
        from pipeline.embed import TextEmbedder
        _embedder = TextEmbedder()
    return _embedder


def get_extractor():
    """Get the preloaded EventExtractor instance."""
    global _extractor
    if _extractor is None:
        from pipeline.event_extract import EventExtractor
        _extractor = EventExtractor()
    return _extractor
```

- [ ] **Step 2: Add preload call to api_server.py startup**

In `services/nlp_py/api_server.py`, add model preloading before the server starts. Add near the top after imports:

```python
from model_loader import preload_models
```

And before `socketio.run(app, ...)` at the bottom:

```python
preload_models()
```

- [ ] **Step 3: Update classify.py to use preloaded model**

Modify the module-level `get_classifier()` function in `classify.py` to check for a preloaded instance first:

```python
def get_classifier():
    try:
        from model_loader import get_classifier as get_preloaded
        return get_preloaded()
    except ImportError:
        return TopicClassifier()
```

Apply the same pattern to `embed.py` (`create_embedder`) and `event_extract.py` (`get_default_extractor`).

- [ ] **Step 4: Commit model preloader**

```bash
git add services/nlp_py/model_loader.py services/nlp_py/api_server.py services/nlp_py/pipeline/classify.py services/nlp_py/pipeline/embed.py services/nlp_py/pipeline/event_extract.py
git commit -m "feat: preload all ML models at startup — eliminates cold-start penalty"
```

---

### Task 7: Implement Parallel Pipeline Stage

**Files:**
- Create: `services/nlp_py/pipeline/parallel_pipeline.py`

- [ ] **Step 1: Create parallel_pipeline.py**

This module runs classify, extract, and embed concurrently for each headline batch.

```python
"""Parallel pipeline — runs classify, extract, embed concurrently."""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


def run_parallel_ml(
    headlines: List[Dict[str, Any]],
    classify_fn: Callable,
    extract_fn: Callable,
    embed_fn: Callable,
    progress_callback: Optional[Callable] = None,
) -> List[Dict[str, Any]]:
    """Run classify, extract, and embed in parallel on a batch of headlines.

    Each function receives the full headlines list and returns an updated list.
    They operate on different fields so there are no write conflicts.
    """
    results = {"classify": None, "extract": None, "embed": None}
    errors = {}

    def _run_stage(name, fn):
        try:
            start = time.time()
            result = fn(headlines)
            elapsed = time.time() - start
            logger.info("  %s completed in %.1fs (%d headlines)", name, elapsed, len(headlines))
            return name, result
        except Exception as e:
            logger.error("  %s failed: %s", name, e)
            return name, None

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(_run_stage, "classify", classify_fn): "classify",
            executor.submit(_run_stage, "extract", extract_fn): "extract",
            executor.submit(_run_stage, "embed", embed_fn): "embed",
        }

        completed = 0
        for future in as_completed(futures):
            name, result = future.result()
            results[name] = result
            completed += 1
            if progress_callback:
                progress_callback(stage="ml_parallel", progress=completed, total=3,
                                  message=f"Completed {name}")

    # Merge results back into headlines
    # Each stage returns a list aligned with the input
    for i, h in enumerate(headlines):
        if results["classify"] and i < len(results["classify"]):
            cr = results["classify"][i]
            h["topic"] = cr.get("topic")
            h["topic_confidence"] = cr.get("confidence")
        if results["extract"] and i < len(results["extract"]):
            er = results["extract"][i]
            h["entities"] = er.get("entities")
            h["event_type"] = er.get("event_type")
        if results["embed"] and i < len(results["embed"]):
            h["embedding_id"] = results["embed"][i].get("embedding_id")

    return headlines
```

- [ ] **Step 2: Create wrapper functions for each ML stage**

Add to `parallel_pipeline.py`:

```python
def classify_batch_wrapper(headlines: List[Dict]) -> List[Dict]:
    """Classify all headlines using the preloaded model."""
    from model_loader import get_classifier
    classifier = get_classifier()
    results = []
    texts = [h.get("translated_title") or h["title"] for h in headlines]
    for text in texts:
        result = classifier.classify_single(text)
        results.append({
            "topic": result.get("labels", ["other"])[0] if result.get("labels") else "other",
            "confidence": result.get("scores", [0.0])[0] if result.get("scores") else 0.0,
        })
    return results


def extract_batch_wrapper(headlines: List[Dict]) -> List[Dict]:
    """Extract entities from all headlines using the preloaded model."""
    from model_loader import get_extractor
    extractor = get_extractor()
    results = []
    for h in headlines:
        text = h.get("translated_title") or h["title"]
        entities = extractor.extract_entities(text)
        event_type, _ = extractor.classify_event_type(text, entities)
        results.append({"entities": entities, "event_type": event_type})
    return results


def embed_batch_wrapper(headlines: List[Dict]) -> List[Dict]:
    """Generate embeddings for all headlines using the preloaded model."""
    from model_loader import get_embedder
    embedder = get_embedder()
    texts = [h.get("translated_title") or h["title"] for h in headlines]
    embeddings = embedder.embed_texts(texts)
    results = []
    for i, emb in enumerate(embeddings):
        # Store embedding_id as a placeholder — actual Qdrant upsert happens in Store stage
        results.append({"embedding": emb, "embedding_id": f"emb_{i}"})
    return results
```

- [ ] **Step 3: Commit parallel pipeline**

```bash
git add services/nlp_py/pipeline/parallel_pipeline.py
git commit -m "feat: parallel ML pipeline — classify, extract, embed run concurrently"
```

---

### Task 8: Remove Classification Rate Limiting

**Files:**
- Modify: `services/nlp_py/pipeline/classify.py`

- [ ] **Step 1: Remove rate limiting from classify.py**

The current `classify.py` has `REQUESTS_PER_SECOND` throttling. Since models run locally, this is unnecessary. Find and remove any `asyncio.sleep` or rate-limiting logic in `classify_batch` and `_classify_async`.

Remove or comment out:
- `REQUESTS_PER_SECOND` constant
- Any `await asyncio.sleep(1.0 / REQUESTS_PER_SECOND)` calls
- Any throttle/rate-limit decorators

- [ ] **Step 2: Commit**

```bash
git add services/nlp_py/pipeline/classify.py
git commit -m "perf: remove artificial rate limiting from classifier — models are local"
```

---

### Task 9: Move Translation Cache to Redis

**Files:**
- Modify: `services/nlp_py/pipeline/translate.py`

- [ ] **Step 1: Add Redis-backed translation cache**

In `translate.py`, add Redis cache functions that wrap the existing translation logic. Translations are cached by `(text_hash, source_lang)` key in Redis with no expiry.

Add near the top of `translate.py`:

```python
import hashlib
import redis
import os

_redis = None

def _get_redis():
    global _redis
    if _redis is None:
        try:
            _redis = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                decode_responses=True,
            )
            _redis.ping()
        except Exception:
            _redis = None
    return _redis


def _cache_key(text: str, lang: str) -> str:
    h = hashlib.md5(f"{lang}:{text}".encode()).hexdigest()
    return f"trans:{h}"
```

Then update `Translator.translate_text` to check Redis before calling the API:

```python
def translate_text(self, text, source_lang):
    r = _get_redis()
    if r:
        cached = r.get(_cache_key(text, source_lang))
        if cached:
            return cached

    # ... existing translation logic ...
    result = translated_text  # the result from GoogleTranslator

    if r and result:
        r.set(_cache_key(text, source_lang), result)

    return result
```

- [ ] **Step 2: Commit**

```bash
git add services/nlp_py/pipeline/translate.py
git commit -m "perf: move translation cache to Redis for persistence across restarts"
```

---

## Chunk 3: Backend New Features (Phase 2 — Agent 4)

> **Agent 4** — Runs in parallel with Agents 2 and 3.
> New API endpoints: sources CRUD, analytics, events, search, pipeline control, WebSocket events.

---

### Task 10: Rewrite api_server.py with New Endpoints

**Files:**
- Rewrite: `services/nlp_py/api_server.py`

- [ ] **Step 1: Rewrite api_server.py**

Replace the entire `api_server.py` with the new version that includes all endpoints from the spec. This is a full rewrite — the old file had 359 lines; the new one will have all the new routes.

```python
"""RSSFeed2 API Server — Flask + Flask-SocketIO."""
import json
import logging
import os
import threading
import time
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit

from database import init_connection_pool
from model_loader import preload_models
from repositories import (
    AnalyticsRepository,
    EventClusterRepository,
    HeadlineRepository,
    SourceRepository,
)

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

app = Flask(__name__)
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
CORS(app, origins=cors_origins)
socketio = SocketIO(app, cors_allowed_origins=cors_origins, async_mode="threading")

# Pipeline state (in-memory)
pipeline_status = {
    "stage": None,
    "status": "idle",
    "progress": 0,
    "total": 0,
    "message": "",
    "last_run": None,
    "last_duration_ms": None,
}
log_buffer = []
MAX_LOG_BUFFER = 100


def emit_status(stage, status, progress=0, total=0, message=""):
    pipeline_status.update(stage=stage, status=status, progress=progress, total=total, message=message)
    socketio.emit("status_update", pipeline_status)


def emit_log(level, message):
    entry = {"level": level, "message": message, "timestamp": datetime.utcnow().isoformat()}
    log_buffer.append(entry)
    if len(log_buffer) > MAX_LOG_BUFFER:
        log_buffer.pop(0)
    socketio.emit("log_message", entry)


# --- Health ---

@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# --- Headlines ---

@app.route("/api/headlines")
def get_headlines():
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 50, type=int), 200)
    sort = request.args.get("sort", "published_at")
    order = request.args.get("order", "desc")
    topic = request.args.get("topic")
    language = request.args.get("language")
    source_id = request.args.get("source_id", type=int)
    q = request.args.get("q")
    result = HeadlineRepository.get_paginated(
        page=page, limit=limit, sort=sort, order=order,
        topic=topic, language=language, source_id=source_id, q=q,
    )
    return jsonify(result)


# --- Events ---

@app.route("/api/events")
def get_events():
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 50, type=int), 200)
    event_type = request.args.get("event_type")
    since = request.args.get("since")
    result = EventClusterRepository.get_paginated(
        page=page, limit=limit, event_type=event_type, since=since,
    )
    return jsonify(result)


@app.route("/api/events/<int:event_id>")
def get_event_detail(event_id):
    cluster = EventClusterRepository.get_by_id(event_id)
    if not cluster:
        return jsonify({"error": "Event cluster not found"}), 404
    return jsonify(cluster)


# --- Analytics ---

@app.route("/api/analytics")
def get_analytics():
    period = request.args.get("period", "7d")
    if period not in ("24h", "7d", "30d"):
        period = "7d"
    result = AnalyticsRepository.get_analytics(period)
    return jsonify(result)


# --- Sources CRUD ---

@app.route("/api/sources", methods=["GET"])
def list_sources():
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 50, type=int), 200)
    active = request.args.get("active", type=lambda v: v.lower() == "true") if "active" in request.args else None
    language = request.args.get("language")
    group_name = request.args.get("group_name")
    result = SourceRepository.get_paginated(
        page=page, limit=limit, active=active, language=language, group_name=group_name,
    )
    return jsonify(result)


@app.route("/api/sources", methods=["POST"])
def create_source():
    data = request.get_json()
    if not data or not data.get("name") or not data.get("url"):
        return jsonify({"error": "name and url are required"}), 400
    source = SourceRepository.create(data)
    if not source:
        return jsonify({"error": "Failed to create source"}), 500
    return jsonify(source), 201


@app.route("/api/sources/<int:source_id>", methods=["GET"])
def get_source(source_id):
    source = SourceRepository.get_by_id(source_id)
    if not source:
        return jsonify({"error": "Source not found"}), 404
    return jsonify(source)


@app.route("/api/sources/<int:source_id>", methods=["PUT"])
def update_source(source_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400
    source = SourceRepository.update(source_id, data)
    if not source:
        return jsonify({"error": "Source not found"}), 404
    return jsonify(source)


@app.route("/api/sources/<int:source_id>", methods=["DELETE"])
def delete_source(source_id):
    if SourceRepository.delete(source_id):
        return "", 204
    return jsonify({"error": "Source not found"}), 404


# --- Pipeline Control ---

@app.route("/api/pipeline/status")
def get_pipeline_status():
    return jsonify(pipeline_status)


@app.route("/api/gather", methods=["POST"])
def start_gather():
    if pipeline_status["status"] == "running":
        return jsonify({"error": "Pipeline already running"}), 409

    def _run():
        from pipeline.gather import gather
        start = time.time()
        emit_status("gather", "running", message="Gathering RSS feeds...")
        emit_log("info", "Starting RSS gathering")
        try:
            headlines = gather()
            emit_status("gather", "idle", progress=len(headlines), total=len(headlines),
                        message=f"Gathered {len(headlines)} headlines")
            emit_log("info", f"Gathered {len(headlines)} headlines")
            socketio.emit("headlines_update", {"count": len(headlines), "new_headlines": len(headlines)})

            # Persist to DB
            result = HeadlineRepository.bulk_insert(headlines)
            emit_log("info", f"Inserted {result['inserted']}, skipped {result['skipped']}")
        except Exception as e:
            emit_status("gather", "error", message=str(e))
            emit_log("error", f"Gather failed: {e}")
        finally:
            elapsed = int((time.time() - start) * 1000)
            pipeline_status["last_run"] = datetime.utcnow().isoformat()
            pipeline_status["last_duration_ms"] = elapsed

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"message": "Gathering started"})


@app.route("/api/translate", methods=["POST"])
def start_translate():
    if pipeline_status["status"] == "running":
        return jsonify({"error": "Pipeline already running"}), 409

    def _run():
        from pipeline.translate import Translator
        start = time.time()
        emit_status("translate", "running", message="Translating headlines...")
        emit_log("info", "Starting translation")
        try:
            translator = Translator()
            # Fetch untranslated non-English headlines from DB
            result = HeadlineRepository.get_paginated(limit=200, language=None)
            headlines = [h for h in result["data"] if h.get("language") != "en" and not h.get("translated_title")]
            emit_log("info", f"Found {len(headlines)} headlines to translate")

            for i, h in enumerate(headlines):
                translated = translator.translate_text(h["title"], h.get("language", "en"))
                if translated:
                    HeadlineRepository.update_translation(h["id"], translated)
                emit_status("translate", "running", progress=i + 1, total=len(headlines),
                            message=f"Translating {i + 1}/{len(headlines)}")

            emit_status("translate", "idle", progress=len(headlines), total=len(headlines),
                        message=f"Translated {len(headlines)} headlines")
            emit_log("info", f"Translation complete — {len(headlines)} headlines")
        except Exception as e:
            emit_status("translate", "error", message=str(e))
            emit_log("error", f"Translation failed: {e}")
        finally:
            elapsed = int((time.time() - start) * 1000)
            pipeline_status["last_run"] = datetime.utcnow().isoformat()
            pipeline_status["last_duration_ms"] = elapsed

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"message": "Translation started"})


@app.route("/api/classify", methods=["POST"])
def start_classify():
    if pipeline_status["status"] == "running":
        return jsonify({"error": "Pipeline already running"}), 409

    def _run():
        start = time.time()
        emit_status("classify", "running", message="Classifying headlines...")
        emit_log("info", "Starting classification")
        try:
            from model_loader import get_classifier
            classifier = get_classifier()
            # Fetch unclassified headlines from DB
            result = HeadlineRepository.get_paginated(limit=200)
            headlines = [h for h in result["data"] if not h.get("topic")]
            emit_log("info", f"Found {len(headlines)} headlines to classify")

            for i, h in enumerate(headlines):
                text = h.get("translated_title") or h["title"]
                classification = classifier.classify_single(text)
                topic = classification.get("labels", ["other"])[0] if classification.get("labels") else "other"
                confidence = classification.get("scores", [0.0])[0] if classification.get("scores") else 0.0
                HeadlineRepository.update_topic(h["id"], topic, confidence)
                emit_status("classify", "running", progress=i + 1, total=len(headlines),
                            message=f"Classifying {i + 1}/{len(headlines)}")

            emit_status("classify", "idle", progress=len(headlines), total=len(headlines),
                        message=f"Classified {len(headlines)} headlines")
            emit_log("info", f"Classification complete — {len(headlines)} headlines")
        except Exception as e:
            emit_status("classify", "error", message=str(e))
            emit_log("error", f"Classification failed: {e}")
        finally:
            elapsed = int((time.time() - start) * 1000)
            pipeline_status["last_run"] = datetime.utcnow().isoformat()
            pipeline_status["last_duration_ms"] = elapsed

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"message": "Classification started"})


@app.route("/api/run", methods=["POST"])
def run_full_pipeline():
    if pipeline_status["status"] == "running":
        return jsonify({"error": "Pipeline already running"}), 409

    def _run():
        from pipeline.gather import gather
        from pipeline.translate import Translator
        from pipeline.parallel_pipeline import (
            run_parallel_ml, classify_batch_wrapper,
            extract_batch_wrapper, embed_batch_wrapper,
        )

        start = time.time()
        emit_log("info", "Starting full pipeline")

        try:
            # Stage 1: Gather
            emit_status("gather", "running", message="Gathering RSS feeds...")
            headlines = gather()
            emit_log("info", f"Gathered {len(headlines)} headlines")

            # Persist gathered headlines
            result = HeadlineRepository.bulk_insert(headlines)
            emit_log("info", f"Inserted {result['inserted']}, skipped {result['skipped']}")

            # Stage 2: Translate
            emit_status("translate", "running", progress=0, total=len(headlines),
                        message="Translating...")
            translator = Translator()
            headlines = translator.translate_headlines(headlines)
            emit_log("info", "Translation complete")

            # Stage 3: Parallel ML (classify + extract + embed)
            emit_status("ml_parallel", "running", progress=0, total=3,
                        message="Running classify, extract, embed in parallel...")
            headlines = run_parallel_ml(
                headlines,
                classify_fn=classify_batch_wrapper,
                extract_fn=extract_batch_wrapper,
                embed_fn=embed_batch_wrapper,
                progress_callback=lambda **kw: emit_status(**kw),
            )
            emit_log("info", "Parallel ML stage complete")

            # Stage 4: Store ML results to DB
            emit_status("store", "running", message="Persisting ML results...")
            for h in headlines:
                hid = h.get("id")
                if not hid:
                    continue
                if h.get("topic"):
                    HeadlineRepository.update_topic(hid, h["topic"], h.get("topic_confidence", 0.0))
                if h.get("entities"):
                    HeadlineRepository.update_entities(hid, h["entities"], h.get("event_type", "other"))
                if h.get("embedding_id"):
                    HeadlineRepository.update_embedding_id(hid, h["embedding_id"])
            emit_log("info", "ML results persisted to DB")

            # Stage 5: Group events into clusters
            emit_status("group", "running", message="Clustering events...")
            try:
                from pipeline.group_by_event import EventGrouper
                from model_loader import get_extractor
                grouper = EventGrouper()
                texts = [h.get("translated_title") or h["title"] for h in headlines]
                h_ids = [str(h.get("id", i)) for i, h in enumerate(headlines)]
                grouping_result = grouper.create_event_groups(texts, headline_ids=h_ids)

                # Persist clusters to DB
                groups = grouping_result.get("groups", [])
                for g in groups:
                    member_ids = [int(mid) for mid in g.get("member_ids", []) if str(mid).isdigit()]
                    scores = g.get("similarity_scores", [0.5] * len(member_ids))
                    if member_ids:
                        EventClusterRepository.create_cluster(
                            label=g.get("summary", {}).get("keywords", ["Unknown"])[0] if isinstance(g.get("summary"), dict) else "Event cluster",
                            event_type=g.get("event_type", "other"),
                            key_entities=g.get("summary", {}).get("top_entities", {}),
                            summary=str(g.get("summary", "")),
                            start_time=g.get("time_span", {}).get("start"),
                            end_time=g.get("time_span", {}).get("end"),
                            headline_ids=member_ids,
                            similarity_scores=scores[:len(member_ids)],
                        )
                emit_log("info", f"Created {len(groups)} event clusters")
            except Exception as e:
                emit_log("warn", f"Event clustering failed (non-fatal): {e}")

            elapsed = int((time.time() - start) * 1000)
            pipeline_status["last_run"] = datetime.utcnow().isoformat()
            pipeline_status["last_duration_ms"] = elapsed

            emit_status(None, "idle", message="Pipeline complete")
            socketio.emit("pipeline_complete", {
                "duration_ms": elapsed,
                "headlines_gathered": len(headlines),
                "translated": sum(1 for h in headlines if h.get("translated_title")),
                "classified": sum(1 for h in headlines if h.get("topic")),
            })
            socketio.emit("headlines_update", {
                "count": len(headlines),
                "new_headlines": result["inserted"],
            })

        except Exception as e:
            emit_status(None, "error", message=str(e))
            emit_log("error", f"Pipeline failed: {e}")

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"message": "Full pipeline started"})


# --- Search ---

@app.route("/api/search")
def search():
    q = request.args.get("q", "")
    limit = min(request.args.get("limit", 20, type=int), 100)
    if not q:
        return jsonify({"error": "q parameter required"}), 400

    try:
        from model_loader import get_embedder
        embedder = get_embedder()
        query_embedding = embedder.embed_single_text(q)

        # Search Qdrant
        from qdrant_client import QdrantClient
        qdrant = QdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", 6333)),
        )
        results = qdrant.search(
            collection_name="headlines",
            query_vector=query_embedding.tolist(),
            limit=limit,
        )
        # Map Qdrant results back to full headline records
        from database import get_db_cursor
        data = []
        for r in results:
            headline_id = r.payload.get("headline_id") if r.payload else None
            if headline_id:
                with get_db_cursor() as cur:
                    cur.execute(
                        """SELECT h.*, s.name as source_name, s.country
                           FROM headlines h JOIN sources s ON h.source_id = s.id
                           WHERE h.id = %s""",
                        (headline_id,),
                    )
                    headline = cur.fetchone()
                if headline:
                    data.append({"headline": dict(headline), "score": r.score})
        return jsonify({"data": data, "query": q})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- WebSocket ---

@socketio.on("connect")
def handle_connect():
    emit_log("info", "Client connected")


@socketio.on("disconnect")
def handle_disconnect():
    emit_log("info", "Client disconnected")


@socketio.on("subscribe_status")
def handle_subscribe():
    emit("status_update", pipeline_status)


@socketio.on("unsubscribe_status")
def handle_unsubscribe():
    pass


# --- Startup ---

if __name__ == "__main__":
    logger.info("Initializing database connection pool...")
    init_connection_pool()

    logger.info("Preloading ML models...")
    preload_models()

    port = int(os.getenv("NLP_PORT", 8081))
    logger.info("Starting server on port %d", port)
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
```

- [ ] **Step 2: Commit rewritten api_server**

```bash
git add services/nlp_py/api_server.py
git commit -m "feat: rewrite api_server with all new endpoints — sources CRUD, analytics, events, search, pipeline control"
```

---

## Chunk 4: Frontend Core (Phase 2 — Agent 2)

> **Agent 2** — Runs in parallel with Agents 3 and 4.
> Scaffold Next.js 15 app, layout, sidebar, Socket.io hook, Vercel config.

---

### Task 11: Scaffold Next.js 15 App

**Files:**
- Create: `frontend/` (entire Next.js project)

- [ ] **Step 1: Create Next.js 15 app**

```bash
cd /Users/oliverb/RSSFeed2
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --no-turbopack
```

- [ ] **Step 2: Install dependencies**

```bash
cd frontend
npm install socket.io-client recharts lucide-react
npx shadcn@latest init -y
npx shadcn@latest add button card input select separator sheet badge tabs scroll-area
```

- [ ] **Step 3: Create environment files**

Create `frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8081
NEXT_PUBLIC_WS_URL=http://localhost:8081
```

Create `frontend/.env.production`:

```
NEXT_PUBLIC_API_URL=https://rssfeed-api.yourdomain.com
NEXT_PUBLIC_WS_URL=https://rssfeed-api.yourdomain.com
```

- [ ] **Step 4: Create vercel.json**

Create `frontend/vercel.json`:

```json
{
  "framework": "nextjs"
}
```

- [ ] **Step 5: Commit scaffold**

```bash
cd /Users/oliverb/RSSFeed2
git add frontend/
git commit -m "feat: scaffold Next.js 15 app with Tailwind, shadcn/ui, Socket.io, Recharts"
```

---

### Task 12: Create API Client & Socket.io Hook

**Files:**
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/hooks/use-socket.ts`
- Create: `frontend/src/hooks/use-pipeline-status.ts`

- [ ] **Step 1: Create API client**

Create `frontend/src/lib/api.ts`:

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8081";

interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    total_pages: number;
  };
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || res.statusText);
  }
  if (res.status === 204) return {} as T;
  return res.json();
}

export const api = {
  headlines: {
    list: (params?: Record<string, string>) => {
      const qs = new URLSearchParams(params).toString();
      return fetchApi<PaginatedResponse<any>>(`/api/headlines?${qs}`);
    },
  },
  events: {
    list: (params?: Record<string, string>) => {
      const qs = new URLSearchParams(params).toString();
      return fetchApi<PaginatedResponse<any>>(`/api/events?${qs}`);
    },
    get: (id: number) => fetchApi<any>(`/api/events/${id}`),
  },
  analytics: {
    get: (period = "7d") => fetchApi<any>(`/api/analytics?period=${period}`),
  },
  sources: {
    list: (params?: Record<string, string>) => {
      const qs = new URLSearchParams(params).toString();
      return fetchApi<PaginatedResponse<any>>(`/api/sources?${qs}`);
    },
    get: (id: number) => fetchApi<any>(`/api/sources/${id}`),
    create: (data: any) => fetchApi<any>("/api/sources", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: any) => fetchApi<any>(`/api/sources/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: number) => fetchApi<void>(`/api/sources/${id}`, { method: "DELETE" }),
  },
  pipeline: {
    status: () => fetchApi<any>("/api/pipeline/status"),
    gather: () => fetchApi<any>("/api/gather", { method: "POST" }),
    translate: () => fetchApi<any>("/api/translate", { method: "POST" }),
    classify: () => fetchApi<any>("/api/classify", { method: "POST" }),
    run: () => fetchApi<any>("/api/run", { method: "POST" }),
  },
  search: {
    query: (q: string, limit = 20) => fetchApi<any>(`/api/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  },
};
```

- [ ] **Step 2: Create Socket.io hook**

Create `frontend/src/hooks/use-socket.ts`:

```typescript
"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { io, Socket } from "socket.io-client";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "http://localhost:8081";

export interface PipelineStatus {
  stage: string | null;
  status: "idle" | "running" | "error";
  progress: number;
  total: number;
  message: string;
  last_run: string | null;
  last_duration_ms: number | null;
}

export interface LogMessage {
  level: "info" | "warn" | "error";
  message: string;
  timestamp: string;
}

interface UseSocketOptions {
  onHeadlinesUpdate?: (data: { count: number; new_headlines: number }) => void;
  onPipelineComplete?: (data: { duration_ms: number; headlines_gathered: number; translated: number; classified: number }) => void;
}

export function useSocket(options: UseSocketOptions = {}) {
  const socketRef = useRef<Socket | null>(null);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState<PipelineStatus>({
    stage: null, status: "idle", progress: 0, total: 0,
    message: "", last_run: null, last_duration_ms: null,
  });
  const [logs, setLogs] = useState<LogMessage[]>([]);

  useEffect(() => {
    const socket = io(WS_URL, {
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1000,
    });
    socketRef.current = socket;

    socket.on("connect", () => {
      setConnected(true);
      socket.emit("subscribe_status");
    });

    socket.on("disconnect", () => setConnected(false));

    socket.on("status_update", (data: PipelineStatus) => setStatus(data));

    socket.on("log_message", (data: LogMessage) => {
      setLogs((prev) => [...prev.slice(-99), data]);
    });

    socket.on("headlines_update", (data) => {
      optionsRef.current.onHeadlinesUpdate?.(data);
    });

    socket.on("pipeline_complete", (data) => {
      optionsRef.current.onPipelineComplete?.(data);
    });

    return () => {
      socket.emit("unsubscribe_status");
      socket.disconnect();
    };
  }, []);

  return { connected, status, logs, socket: socketRef.current };
}
```

- [ ] **Step 3: Commit hooks**

```bash
git add frontend/src/lib/api.ts frontend/src/hooks/
git commit -m "feat: add API client and Socket.io hook with pipeline status tracking"
```

---

### Task 13: Build Root Layout with Sidebar Navigation

**Files:**
- Modify: `frontend/src/app/layout.tsx`
- Create: `frontend/src/components/sidebar-nav.tsx`
- Create: `frontend/src/components/data-sidebar.tsx`
- Create: `frontend/src/components/providers.tsx`

- [ ] **Step 1: Create providers wrapper**

Create `frontend/src/components/providers.tsx`:

```typescript
"use client";
import { ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
```

- [ ] **Step 2: Create sidebar navigation**

Create `frontend/src/components/sidebar-nav.tsx`:

```typescript
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  Newspaper, Layers, BarChart3, Play, Rss, Settings, ChevronLeft, ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Feed", icon: Newspaper },
  { href: "/events", label: "Events", icon: Layers },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/pipeline", label: "Pipeline", icon: Play },
  { href: "/sources", label: "Sources", icon: Rss },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function SidebarNav() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "flex flex-col border-r border-zinc-800 bg-zinc-950 transition-all duration-200",
        collapsed ? "w-16" : "w-56"
      )}
    >
      <div className="flex items-center justify-between p-4 border-b border-zinc-800">
        {!collapsed && (
          <span className="text-lg font-semibold text-zinc-100">RSSFeed2</span>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1 rounded hover:bg-zinc-800 text-zinc-400"
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>
      <nav className="flex-1 py-4 space-y-1 px-2">
        {navItems.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                active
                  ? "bg-zinc-800 text-zinc-100"
                  : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900"
              )}
            >
              <item.icon size={18} />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
```

- [ ] **Step 3: Create data sidebar**

Create `frontend/src/components/data-sidebar.tsx`:

```typescript
"use client";
import { useSocket } from "@/hooks/use-socket";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function DataSidebar() {
  const { connected, status } = useSocket();

  const statusColor = {
    idle: "bg-green-500",
    running: "bg-blue-500 animate-pulse",
    error: "bg-red-500",
  }[status.status];

  return (
    <aside className="hidden lg:flex flex-col w-72 border-l border-zinc-800 bg-zinc-950 p-4 space-y-6">
      {/* Connection */}
      <div className="flex items-center gap-2 text-xs text-zinc-500">
        <div className={cn("w-2 h-2 rounded-full", connected ? "bg-green-500" : "bg-red-500")} />
        {connected ? "Connected" : "Reconnecting..."}
      </div>

      {/* Pipeline Status */}
      <div>
        <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
          Pipeline
        </h3>
        <div className="flex items-center gap-2">
          <div className={cn("w-2 h-2 rounded-full", statusColor)} />
          <span className="text-sm text-zinc-300 capitalize">{status.status}</span>
        </div>
        {status.stage && (
          <p className="text-xs text-zinc-500 mt-1">{status.message}</p>
        )}
        {status.status === "running" && status.total > 0 && (
          <div className="mt-2 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all duration-300"
              style={{ width: `${(status.progress / status.total) * 100}%` }}
            />
          </div>
        )}
        {status.last_run && (
          <p className="text-xs text-zinc-600 mt-2">
            Last run: {new Date(status.last_run).toLocaleTimeString()}
            {status.last_duration_ms && ` (${(status.last_duration_ms / 1000).toFixed(1)}s)`}
          </p>
        )}
      </div>

      {/* Quick Stats — populated by API calls in integration phase */}
      <div>
        <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
          Stats
        </h3>
        <div className="space-y-2 text-sm text-zinc-400">
          <p>Headlines: —</p>
          <p>Sources: —</p>
          <p>Topics: —</p>
        </div>
      </div>
    </aside>
  );
}
```

- [ ] **Step 4: Update root layout**

Replace `frontend/src/app/layout.tsx`:

```typescript
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { SidebarNav } from "@/components/sidebar-nav";
import { DataSidebar } from "@/components/data-sidebar";
import { Providers } from "@/components/providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "RSSFeed2 — News Aggregator",
  description: "ML-powered news aggregation and analysis",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-zinc-950 text-zinc-100 antialiased`}>
        <Providers>
          <div className="flex h-screen overflow-hidden">
            <SidebarNav />
            <main className="flex-1 overflow-y-auto">{children}</main>
            <DataSidebar />
          </div>
        </Providers>
      </body>
    </html>
  );
}
```

- [ ] **Step 5: Commit layout**

```bash
git add frontend/src/
git commit -m "feat: root layout with collapsible sidebar nav and persistent data sidebar"
```

---

## Chunk 5: Frontend Pages (Phase 3 — Agents 5 & 6)

> **Agent 5** builds Feed, Events, Pipeline pages.
> **Agent 6** builds Analytics, Sources, Settings pages.
> Both run in parallel after Phase 2 completes.

---

### Task 14: Feed Page

**Files:**
- Create: `frontend/src/app/page.tsx`

- [ ] **Step 1: Create Feed page**

Create `frontend/src/app/page.tsx` — editorial headline feed with search, filters, infinite scroll:

```typescript
"use client";
import { useEffect, useState, useCallback } from "react";
import { Search, Filter, ExternalLink } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";

const TOPICS = ["politics", "economy", "technology", "science", "environment", "entertainment", "world", "business", "education", "art"];

export default function FeedPage() {
  const [headlines, setHeadlines] = useState<any[]>([]);
  const [pagination, setPagination] = useState({ page: 1, total_pages: 1, total: 0 });
  const [search, setSearch] = useState("");
  const [topic, setTopic] = useState<string>("");
  const [language, setLanguage] = useState<string>("");
  const [loading, setLoading] = useState(true);

  const fetchHeadlines = useCallback(async (page = 1, append = false) => {
    setLoading(true);
    try {
      const params: Record<string, string> = { page: String(page), limit: "50" };
      if (search) params.q = search;
      if (topic) params.topic = topic;
      if (language) params.language = language;
      const res = await api.headlines.list(params);
      setHeadlines(append ? (prev) => [...prev, ...res.data] : res.data);
      setPagination(res.pagination);
    } catch (e) {
      console.error("Failed to fetch headlines:", e);
    } finally {
      setLoading(false);
    }
  }, [search, topic, language]);

  useEffect(() => { fetchHeadlines(1); }, [fetchHeadlines]);

  const loadMore = () => {
    if (pagination.page < pagination.total_pages) {
      fetchHeadlines(pagination.page + 1, true);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Headlines</h1>

      {/* Filters */}
      <div className="flex gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" size={16} />
          <Input
            placeholder="Search headlines..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && fetchHeadlines(1)}
            className="pl-10 bg-zinc-900 border-zinc-800"
          />
        </div>
        <Select value={topic} onValueChange={(v) => { setTopic(v === "all" ? "" : v); }}>
          <SelectTrigger className="w-40 bg-zinc-900 border-zinc-800">
            <SelectValue placeholder="Topic" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Topics</SelectItem>
            {TOPICS.map((t) => (
              <SelectItem key={t} value={t}>{t}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Results count */}
      <p className="text-sm text-zinc-500 mb-4">{pagination.total} headlines</p>

      {/* Headline list */}
      <div className="space-y-1">
        {headlines.map((h) => (
          <article key={h.id} className="py-4 border-b border-zinc-900">
            <div className="flex items-start gap-2 mb-1">
              {h.topic && (
                <Badge variant="secondary" className="text-xs shrink-0">
                  {h.topic}
                </Badge>
              )}
              {h.language && h.language !== "en" && (
                <Badge variant="outline" className="text-xs shrink-0">
                  {h.language}
                </Badge>
              )}
            </div>
            <a
              href={h.url}
              target="_blank"
              rel="noopener noreferrer"
              className="group"
            >
              <h2 className="text-base font-medium text-zinc-200 group-hover:text-zinc-50 transition-colors leading-snug">
                {h.translated_title || h.title}
                <ExternalLink size={14} className="inline ml-1.5 opacity-0 group-hover:opacity-50 transition-opacity" />
              </h2>
            </a>
            {h.description && (
              <p className="text-sm text-zinc-500 mt-1 line-clamp-2">{h.description}</p>
            )}
            <div className="flex items-center gap-2 mt-2 text-xs text-zinc-600">
              <span>{h.source_name}</span>
              {h.published_at && (
                <>
                  <span>·</span>
                  <span>{new Date(h.published_at).toLocaleDateString()}</span>
                </>
              )}
            </div>
          </article>
        ))}
      </div>

      {/* Load more */}
      {pagination.page < pagination.total_pages && (
        <button
          onClick={loadMore}
          disabled={loading}
          className="w-full mt-6 py-3 text-sm text-zinc-400 hover:text-zinc-200 border border-zinc-800 rounded-md hover:bg-zinc-900 transition-colors"
        >
          {loading ? "Loading..." : "Load more"}
        </button>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/page.tsx
git commit -m "feat: Feed page — editorial headline list with search, topic filter, infinite scroll"
```

---

### Task 15: Events Page

**Files:**
- Create: `frontend/src/app/events/page.tsx`

- [ ] **Step 1: Create Events page**

Create `frontend/src/app/events/page.tsx`:

```typescript
"use client";
import { useEffect, useState } from "react";
import { Layers, Clock, Users } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";

export default function EventsPage() {
  const [clusters, setClusters] = useState<any[]>([]);
  const [selectedCluster, setSelectedCluster] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.events.list({ limit: "50" })
      .then((res) => setClusters(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const openCluster = async (id: number) => {
    const detail = await api.events.get(id);
    setSelectedCluster(detail);
  };

  if (loading) return <div className="p-6 text-zinc-500">Loading events...</div>;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Event Clusters</h1>

      {selectedCluster ? (
        <div>
          <button
            onClick={() => setSelectedCluster(null)}
            className="text-sm text-zinc-400 hover:text-zinc-200 mb-4"
          >
            ← Back to clusters
          </button>
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-xl">{selectedCluster.label}</CardTitle>
              <div className="flex gap-2 mt-2">
                {selectedCluster.event_type && (
                  <Badge variant="secondary">{selectedCluster.event_type}</Badge>
                )}
                <Badge variant="outline">{selectedCluster.headline_count} articles</Badge>
              </div>
              {selectedCluster.summary && (
                <p className="text-sm text-zinc-400 mt-2">{selectedCluster.summary}</p>
              )}
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {selectedCluster.headlines?.map((h: any) => (
                  <a
                    key={h.id}
                    href={h.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block p-3 rounded border border-zinc-800 hover:bg-zinc-800/50 transition-colors"
                  >
                    <p className="text-sm text-zinc-200">{h.translated_title || h.title}</p>
                    <p className="text-xs text-zinc-500 mt-1">
                      {h.source_name} · Score: {h.similarity_score?.toFixed(2)}
                    </p>
                  </a>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {clusters.map((c) => (
            <Card
              key={c.id}
              onClick={() => openCluster(c.id)}
              className="bg-zinc-900 border-zinc-800 cursor-pointer hover:border-zinc-700 transition-colors"
            >
              <CardHeader className="pb-2">
                <CardTitle className="text-base">{c.label}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4 text-xs text-zinc-500">
                  {c.event_type && <Badge variant="secondary" className="text-xs">{c.event_type}</Badge>}
                  <span className="flex items-center gap-1">
                    <Layers size={12} /> {c.headline_count} articles
                  </span>
                  {c.start_time && (
                    <span className="flex items-center gap-1">
                      <Clock size={12} /> {new Date(c.start_time).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
          {clusters.length === 0 && (
            <p className="text-zinc-500 col-span-2">No event clusters yet. Run the pipeline to generate clusters.</p>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/events/
git commit -m "feat: Events page — clustered view with detail drill-down"
```

---

### Task 16: Pipeline Page

**Files:**
- Create: `frontend/src/app/pipeline/page.tsx`

- [ ] **Step 1: Create Pipeline page**

Create `frontend/src/app/pipeline/page.tsx`:

```typescript
"use client";
import { useState } from "react";
import { Play, RefreshCw, Languages, Brain, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useSocket } from "@/hooks/use-socket";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function PipelinePage() {
  const { status, logs } = useSocket();
  const [triggering, setTriggering] = useState<string | null>(null);

  const trigger = async (action: string, fn: () => Promise<any>) => {
    setTriggering(action);
    try {
      await fn();
    } catch (e: any) {
      console.error(e);
    } finally {
      setTriggering(null);
    }
  };

  const isRunning = status.status === "running";

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Pipeline Control</h1>

      {/* Status */}
      <Card className="bg-zinc-900 border-zinc-800 mb-6">
        <CardContent className="pt-6">
          <div className="flex items-center gap-3">
            <div className={cn(
              "w-3 h-3 rounded-full",
              status.status === "idle" && "bg-green-500",
              status.status === "running" && "bg-blue-500 animate-pulse",
              status.status === "error" && "bg-red-500",
            )} />
            <span className="text-lg font-medium capitalize">{status.status}</span>
            {status.stage && <span className="text-zinc-500">— {status.stage}</span>}
          </div>
          {status.message && <p className="text-sm text-zinc-400 mt-2">{status.message}</p>}
          {isRunning && status.total > 0 && (
            <div className="mt-3">
              <div className="flex justify-between text-xs text-zinc-500 mb-1">
                <span>{status.progress} / {status.total}</span>
                <span>{Math.round((status.progress / status.total) * 100)}%</span>
              </div>
              <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 transition-all duration-300"
                  style={{ width: `${(status.progress / status.total) * 100}%` }}
                />
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <Button
          onClick={() => trigger("run", api.pipeline.run)}
          disabled={isRunning}
          className="h-auto py-4 flex flex-col gap-2"
          variant="default"
        >
          <Zap size={20} />
          <span className="text-xs">Run Full Pipeline</span>
        </Button>
        <Button
          onClick={() => trigger("gather", api.pipeline.gather)}
          disabled={isRunning}
          className="h-auto py-4 flex flex-col gap-2"
          variant="outline"
        >
          <RefreshCw size={20} />
          <span className="text-xs">Gather</span>
        </Button>
        <Button
          onClick={() => trigger("translate", api.pipeline.translate)}
          disabled={isRunning}
          className="h-auto py-4 flex flex-col gap-2"
          variant="outline"
        >
          <Languages size={20} />
          <span className="text-xs">Translate</span>
        </Button>
        <Button
          onClick={() => trigger("classify", api.pipeline.classify)}
          disabled={isRunning}
          className="h-auto py-4 flex flex-col gap-2"
          variant="outline"
        >
          <Brain size={20} />
          <span className="text-xs">Classify</span>
        </Button>
      </div>

      {/* Logs */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-sm font-medium text-zinc-400">Pipeline Logs</CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-80">
            <div className="space-y-1 font-mono text-xs">
              {logs.length === 0 && <p className="text-zinc-600">No logs yet.</p>}
              {logs.map((log, i) => (
                <div key={i} className="flex gap-2">
                  <span className="text-zinc-600 shrink-0">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                  <span className={cn(
                    log.level === "error" && "text-red-400",
                    log.level === "warn" && "text-yellow-400",
                    log.level === "info" && "text-zinc-400",
                  )}>
                    {log.message}
                  </span>
                </div>
              ))}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/pipeline/
git commit -m "feat: Pipeline page — trigger buttons, progress bars, real-time log stream"
```

---

### Task 17: Analytics Page

**Files:**
- Create: `frontend/src/app/analytics/page.tsx`

- [ ] **Step 1: Create Analytics page**

Create `frontend/src/app/analytics/page.tsx`:

```typescript
"use client";
import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";

const COLORS = ["#3b82f6", "#22c55e", "#eab308", "#ef4444", "#a855f7", "#ec4899", "#14b8a6", "#f97316", "#6366f1", "#84cc16"];

export default function AnalyticsPage() {
  const [data, setData] = useState<any>(null);
  const [period, setPeriod] = useState("7d");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.analytics.get(period)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [period]);

  if (loading || !data) return <div className="p-6 text-zinc-500">Loading analytics...</div>;

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Analytics</h1>
        <Tabs value={period} onValueChange={setPeriod}>
          <TabsList className="bg-zinc-900">
            <TabsTrigger value="24h">24h</TabsTrigger>
            <TabsTrigger value="7d">7d</TabsTrigger>
            <TabsTrigger value="30d">30d</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Topic Distribution */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader><CardTitle className="text-sm text-zinc-400">Topic Distribution</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={data.topic_distribution}>
                <XAxis dataKey="topic" tick={{ fill: "#71717a", fontSize: 11 }} />
                <YAxis tick={{ fill: "#71717a", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #27272a", borderRadius: 8 }} />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Language Breakdown */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader><CardTitle className="text-sm text-zinc-400">Languages</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={data.language_breakdown} dataKey="count" nameKey="language" cx="50%" cy="50%" outerRadius={100} label={({ language }) => language}>
                  {data.language_breakdown.map((_: any, i: number) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #27272a", borderRadius: 8 }} />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Daily Volume */}
        <Card className="bg-zinc-900 border-zinc-800 md:col-span-2">
          <CardHeader><CardTitle className="text-sm text-zinc-400">Daily Volume</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={data.daily_volume}>
                <XAxis dataKey="date" tick={{ fill: "#71717a", fontSize: 11 }} />
                <YAxis tick={{ fill: "#71717a", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #27272a", borderRadius: 8 }} />
                <Line type="monotone" dataKey="count" stroke="#22c55e" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Source Breakdown */}
        <Card className="bg-zinc-900 border-zinc-800 md:col-span-2">
          <CardHeader><CardTitle className="text-sm text-zinc-400">Top Sources</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={data.source_breakdown.slice(0, 15)} layout="vertical">
                <XAxis type="number" tick={{ fill: "#71717a", fontSize: 11 }} />
                <YAxis type="category" dataKey="name" tick={{ fill: "#71717a", fontSize: 11 }} width={120} />
                <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #27272a", borderRadius: 8 }} />
                <Bar dataKey="count" fill="#a855f7" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/analytics/
git commit -m "feat: Analytics page — topic distribution, language pie, daily volume, source breakdown"
```

---

### Task 18: Sources Page

**Files:**
- Create: `frontend/src/app/sources/page.tsx`

- [ ] **Step 1: Create Sources page**

Create `frontend/src/app/sources/page.tsx`:

```typescript
"use client";
import { useEffect, useState } from "react";
import { Plus, Trash2, Edit, CheckCircle, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";

export default function SourcesPage() {
  const [sources, setSources] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [newSource, setNewSource] = useState({ name: "", url: "", language: "en", country: "", group_name: "" });

  const fetchSources = () => {
    setLoading(true);
    api.sources.list({ limit: "200" })
      .then((res) => setSources(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchSources(); }, []);

  const addSource = async () => {
    if (!newSource.name || !newSource.url) return;
    await api.sources.create(newSource);
    setNewSource({ name: "", url: "", language: "en", country: "", group_name: "" });
    setShowAdd(false);
    fetchSources();
  };

  const deleteSource = async (id: number) => {
    await api.sources.delete(id);
    fetchSources();
  };

  const toggleActive = async (source: any) => {
    await api.sources.update(source.id, { active: !source.active });
    fetchSources();
  };

  if (loading) return <div className="p-6 text-zinc-500">Loading sources...</div>;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">RSS Sources</h1>
        <Button onClick={() => setShowAdd(!showAdd)} variant="outline" size="sm">
          <Plus size={16} className="mr-1" /> Add Source
        </Button>
      </div>

      {showAdd && (
        <Card className="bg-zinc-900 border-zinc-800 mb-6">
          <CardContent className="pt-6">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              <Input placeholder="Name" value={newSource.name} onChange={(e) => setNewSource({ ...newSource, name: e.target.value })} className="bg-zinc-950 border-zinc-800" />
              <Input placeholder="RSS URL" value={newSource.url} onChange={(e) => setNewSource({ ...newSource, url: e.target.value })} className="bg-zinc-950 border-zinc-800 col-span-2 md:col-span-1" />
              <Input placeholder="Language (en)" value={newSource.language} onChange={(e) => setNewSource({ ...newSource, language: e.target.value })} className="bg-zinc-950 border-zinc-800" />
              <Input placeholder="Country" value={newSource.country} onChange={(e) => setNewSource({ ...newSource, country: e.target.value })} className="bg-zinc-950 border-zinc-800" />
              <Input placeholder="Group" value={newSource.group_name} onChange={(e) => setNewSource({ ...newSource, group_name: e.target.value })} className="bg-zinc-950 border-zinc-800" />
            </div>
            <div className="flex gap-2 mt-3">
              <Button onClick={addSource} size="sm">Add</Button>
              <Button onClick={() => setShowAdd(false)} variant="ghost" size="sm">Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="space-y-2">
        {sources.map((s) => (
          <div
            key={s.id}
            className="flex items-center gap-3 p-3 rounded-lg border border-zinc-800 bg-zinc-900/50"
          >
            <button onClick={() => toggleActive(s)} className="shrink-0">
              {s.active ? (
                <CheckCircle size={18} className="text-green-500" />
              ) : (
                <XCircle size={18} className="text-zinc-600" />
              )}
            </button>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-zinc-200 truncate">{s.name}</p>
              <p className="text-xs text-zinc-500 truncate">{s.url}</p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Badge variant="outline" className="text-xs">{s.language}</Badge>
              {s.country && <Badge variant="outline" className="text-xs">{s.country}</Badge>}
              {s.fetch_error && <Badge variant="destructive" className="text-xs">Error</Badge>}
              <Button
                onClick={() => deleteSource(s.id)}
                variant="ghost"
                size="sm"
                className="text-zinc-500 hover:text-red-400"
              >
                <Trash2 size={14} />
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/sources/
git commit -m "feat: Sources page — CRUD table with add, toggle active, delete"
```

---

### Task 19: Settings Page

**Files:**
- Create: `frontend/src/app/settings/page.tsx`

- [ ] **Step 1: Create Settings page**

Create `frontend/src/app/settings/page.tsx` — client-only, localStorage-based:

```typescript
"use client";
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface Settings {
  theme: "dark" | "light";
  refreshInterval: number;
  pageSize: number;
}

const DEFAULTS: Settings = { theme: "dark", refreshInterval: 0, pageSize: 50 };

function loadSettings(): Settings {
  if (typeof window === "undefined") return DEFAULTS;
  try {
    const stored = localStorage.getItem("rssfeed2-settings");
    return stored ? { ...DEFAULTS, ...JSON.parse(stored) } : DEFAULTS;
  } catch {
    return DEFAULTS;
  }
}

function saveSettings(settings: Settings) {
  localStorage.setItem("rssfeed2-settings", JSON.stringify(settings));
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>(DEFAULTS);
  const [saved, setSaved] = useState(false);

  useEffect(() => { setSettings(loadSettings()); }, []);

  const handleSave = () => {
    saveSettings(settings);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-sm text-zinc-400">Preferences</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm text-zinc-400 mb-1 block">Theme</label>
            <Select value={settings.theme} onValueChange={(v: "dark" | "light") => setSettings({ ...settings, theme: v })}>
              <SelectTrigger className="bg-zinc-950 border-zinc-800">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="dark">Dark</SelectItem>
                <SelectItem value="light">Light</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-sm text-zinc-400 mb-1 block">Auto-refresh interval (seconds, 0 = off)</label>
            <Input
              type="number"
              value={settings.refreshInterval}
              onChange={(e) => setSettings({ ...settings, refreshInterval: parseInt(e.target.value) || 0 })}
              className="bg-zinc-950 border-zinc-800"
            />
          </div>

          <div>
            <label className="text-sm text-zinc-400 mb-1 block">Default page size</label>
            <Input
              type="number"
              value={settings.pageSize}
              onChange={(e) => setSettings({ ...settings, pageSize: parseInt(e.target.value) || 50 })}
              className="bg-zinc-950 border-zinc-800"
            />
          </div>

          <Button onClick={handleSave}>
            {saved ? "Saved!" : "Save Settings"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/settings/
git commit -m "feat: Settings page — localStorage-based theme, refresh, page size config"
```

---

## Chunk 6: Integration & Review (Phase 4 + 5 — Agents 7 & 8)

> **Agent 7** — Wires everything together, error handling, responsive layout.
> **Agent 8** — Code review against spec.

---

### Task 20: Wire Data Sidebar with Real Stats

**Files:**
- Modify: `frontend/src/components/data-sidebar.tsx`

- [ ] **Step 1: Rewrite data-sidebar.tsx with real stats and shared content component**

Rewrite `frontend/src/components/data-sidebar.tsx` to extract a shared `DataSidebarContent` component (used by both desktop and mobile), fetch real stats, and use the `onPipelineComplete` callback from `useSocket`:

```typescript
"use client";
import { useEffect, useState, useCallback } from "react";
import { BarChart3 } from "lucide-react";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { useSocket } from "@/hooks/use-socket";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

function DataSidebarContent() {
  const [stats, setStats] = useState({ headlines: 0, sources: 0, topics: [] as any[] });

  const fetchStats = useCallback(async () => {
    try {
      const [headlines, sources, analytics] = await Promise.all([
        api.headlines.list({ limit: "1" }),
        api.sources.list({ limit: "1" }),
        api.analytics.get("7d"),
      ]);
      setStats({
        headlines: headlines.pagination.total,
        sources: sources.pagination.total,
        topics: analytics.topic_distribution?.slice(0, 5) || [],
      });
    } catch {}
  }, []);

  const { connected, status } = useSocket({
    onPipelineComplete: fetchStats,
    onHeadlinesUpdate: fetchStats,
  });

  useEffect(() => { fetchStats(); }, [fetchStats]);

  const statusColor = {
    idle: "bg-green-500",
    running: "bg-blue-500 animate-pulse",
    error: "bg-red-500",
  }[status.status];

  return (
    <div className="space-y-6">
      {/* Connection */}
      <div className="flex items-center gap-2 text-xs text-zinc-500">
        <div className={cn("w-2 h-2 rounded-full", connected ? "bg-green-500" : "bg-red-500")} />
        {connected ? "Connected" : "Reconnecting..."}
      </div>

      {/* Pipeline Status */}
      <div>
        <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">Pipeline</h3>
        <div className="flex items-center gap-2">
          <div className={cn("w-2 h-2 rounded-full", statusColor)} />
          <span className="text-sm text-zinc-300 capitalize">{status.status}</span>
        </div>
        {status.stage && <p className="text-xs text-zinc-500 mt-1">{status.message}</p>}
        {status.status === "running" && status.total > 0 && (
          <div className="mt-2 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
            <div className="h-full bg-blue-500 transition-all duration-300"
                 style={{ width: `${(status.progress / status.total) * 100}%` }} />
          </div>
        )}
        {status.last_run && (
          <p className="text-xs text-zinc-600 mt-2">
            Last: {new Date(status.last_run).toLocaleTimeString()}
            {status.last_duration_ms && ` (${(status.last_duration_ms / 1000).toFixed(1)}s)`}
          </p>
        )}
      </div>

      {/* Stats */}
      <div>
        <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">Stats</h3>
        <div className="space-y-2 text-sm text-zinc-400">
          <p>Headlines: {stats.headlines.toLocaleString()}</p>
          <p>Sources: {stats.sources}</p>
        </div>
      </div>

      {/* Top Topics */}
      {stats.topics.length > 0 && (
        <div>
          <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">Topics</h3>
          <div className="space-y-1">
            {stats.topics.map((t: any) => (
              <div key={t.topic} className="flex justify-between text-xs">
                <span className="text-zinc-400 capitalize">{t.topic}</span>
                <span className="text-zinc-600">{t.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function DataSidebar() {
  return (
    <aside className="hidden lg:flex flex-col w-72 border-l border-zinc-800 bg-zinc-950 p-4">
      <DataSidebarContent />
    </aside>
  );
}

export function MobileDataSidebar() {
  return (
    <div className="lg:hidden fixed bottom-4 right-4 z-50">
      <Sheet>
        <SheetTrigger asChild>
          <button className="p-3 bg-zinc-800 rounded-full border border-zinc-700 shadow-lg">
            <BarChart3 size={20} />
          </button>
        </SheetTrigger>
        <SheetContent side="right" className="bg-zinc-950 border-zinc-800 w-72">
          <DataSidebarContent />
        </SheetContent>
      </Sheet>
    </div>
  );
}
```

This replaces both the original Task 13 data-sidebar.tsx content AND the Task 22 mobile drawer work — they are now a single unified component.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/data-sidebar.tsx
git commit -m "feat: data sidebar shows real stats — headline count, sources, top topics"
```

---

### Task 21: Add Error Handling & Loading States

**Files:**
- Create: `frontend/src/components/error-boundary.tsx`
- Create: `frontend/src/components/loading.tsx`

- [ ] **Step 1: Create error boundary**

Create `frontend/src/components/error-boundary.tsx`:

```typescript
"use client";
import { Component, ReactNode } from "react";

interface Props { children: ReactNode; fallback?: ReactNode; }
interface State { hasError: boolean; error?: Error; }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="p-6 text-center">
          <p className="text-red-400 mb-2">Something went wrong</p>
          <p className="text-sm text-zinc-500">{this.state.error?.message}</p>
          <button
            onClick={() => this.setState({ hasError: false })}
            className="mt-4 text-sm text-blue-400 hover:underline"
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

- [ ] **Step 2: Create loading component**

Create `frontend/src/components/loading.tsx`:

```typescript
export function Loading({ message = "Loading..." }: { message?: string }) {
  return (
    <div className="flex items-center justify-center p-12">
      <div className="flex items-center gap-3 text-zinc-500">
        <div className="w-4 h-4 border-2 border-zinc-600 border-t-zinc-300 rounded-full animate-spin" />
        <span className="text-sm">{message}</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Wrap pages in error boundaries**

Update `frontend/src/app/layout.tsx` to wrap `{children}` in `<ErrorBoundary>`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/error-boundary.tsx frontend/src/components/loading.tsx frontend/src/app/layout.tsx
git commit -m "feat: add error boundary and loading states"
```

---

### Task 22: Add MobileDataSidebar to Layout

**Files:**
- Modify: `frontend/src/app/layout.tsx`

Note: The `MobileDataSidebar` component and `DataSidebarContent` extraction were already done in Task 20's data-sidebar.tsx rewrite.

- [ ] **Step 1: Add MobileDataSidebar to layout**

In `layout.tsx`, import and add `<MobileDataSidebar />` after `<DataSidebar />`:

```typescript
import { DataSidebar, MobileDataSidebar } from "@/components/data-sidebar";

// In the JSX:
<DataSidebar />
<MobileDataSidebar />
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/layout.tsx
git commit -m "feat: mobile responsive — data sidebar becomes sheet drawer below lg breakpoint"
```

---

### Task 23: Final Integration Verification

- [ ] **Step 1: Start Docker services**

```bash
make up
```

Wait for all services to be healthy:

```bash
make health
```

- [ ] **Step 2: Run database migration**

```bash
make migrate
```

- [ ] **Step 3: Seed sources**

```bash
make seed
```

- [ ] **Step 4: Start frontend dev server**

```bash
cd frontend && npm run dev
```

- [ ] **Step 5: Verify all pages load**

Open `http://localhost:3000` and check:
- [ ] Feed page loads, shows headlines after gathering
- [ ] Events page loads, shows clusters
- [ ] Analytics page loads with charts
- [ ] Pipeline page — trigger "Run Full Pipeline", verify progress + logs
- [ ] Sources page — list sources, add/delete works
- [ ] Settings page — save/load from localStorage
- [ ] Data sidebar shows real-time pipeline status
- [ ] Mobile responsive — sidebar becomes drawer below 1024px
- [ ] WebSocket reconnection — restart nlp_service (`make restart-nlp`), verify "Reconnecting..." indicator appears, then auto-reconnects and re-syncs status

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "chore: integration verification — all pages wired and functional"
```

---

### Task 24: Code Review

> **Agent 8** — Review everything against the spec.

- [ ] **Step 1: Review against spec checklist**

Verify each spec requirement is implemented:

- [ ] Architecture: Next.js on Vercel config, Docker with 4 services only, no Go gateway
- [ ] Frontend: 6 pages (Feed, Events, Analytics, Pipeline, Sources, Settings)
- [ ] Frontend: Hybrid layout (sidebar nav + data sidebar)
- [ ] Frontend: Dark theme, responsive at lg:1024px
- [ ] Backend: Model preloading at startup
- [ ] Backend: Parallel ML pipeline (classify + extract + embed concurrent)
- [ ] Backend: All API endpoints per contract (headlines, events, analytics, sources CRUD, pipeline control, search)
- [ ] Backend: Pagination envelope on list endpoints
- [ ] Backend: WebSocket events (status_update, headlines_update, log_message, pipeline_complete)
- [ ] Backend: CORS configured for direct WebSocket
- [ ] Database: New schema (sources, headlines, event_clusters, event_cluster_members)
- [ ] Database: Views, triggers, indexes
- [ ] Database: Seeder from feeds.json

- [ ] **Step 2: Report any issues found**

Document issues in a comment and fix before merging.
