"""Repository layer for database operations against the new schema."""
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from database import get_db_cursor


class SourceRepository:
    """Repository for CRUD operations on the sources table."""

    @staticmethod
    def get_all(active_only: bool = True) -> List[Dict]:
        """Return all sources, optionally filtering to active ones only."""
        try:
            with get_db_cursor() as cursor:
                if active_only:
                    cursor.execute(
                        "SELECT * FROM sources WHERE active = TRUE ORDER BY name"
                    )
                else:
                    cursor.execute("SELECT * FROM sources ORDER BY name")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching sources: {e}")
            return []

    @staticmethod
    def get_by_id(source_id: int) -> Optional[Dict]:
        """Return a single source by its SERIAL primary key."""
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM sources WHERE id = %s", (source_id,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error fetching source {source_id}: {e}")
            return None

    @staticmethod
    def create(data: Dict[str, Any]) -> Optional[Dict]:
        """Insert a new source and return the created row."""
        columns = list(data.keys())
        placeholders = [f"%({col})s" for col in columns]
        sql = (
            f"INSERT INTO sources ({', '.join(columns)}) "
            f"VALUES ({', '.join(placeholders)}) "
            f"RETURNING *"
        )
        try:
            with get_db_cursor() as cursor:
                cursor.execute(sql, data)
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error creating source: {e}")
            return None

    @staticmethod
    def update(source_id: int, data: Dict[str, Any]) -> Optional[Dict]:
        """Dynamically update a source and return the updated row."""
        if not data:
            return SourceRepository.get_by_id(source_id)
        set_clauses = [f"{col} = %({col})s" for col in data]
        sql = (
            f"UPDATE sources SET {', '.join(set_clauses)} "
            f"WHERE id = %(source_id)s "
            f"RETURNING *"
        )
        params = {**data, "source_id": source_id}
        try:
            with get_db_cursor() as cursor:
                cursor.execute(sql, params)
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error updating source {source_id}: {e}")
            return None

    @staticmethod
    def delete(source_id: int) -> bool:
        """Delete a source by ID. Returns True on success."""
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    "DELETE FROM sources WHERE id = %s", (source_id,)
                )
                return True
        except Exception as e:
            print(f"Error deleting source {source_id}: {e}")
            return False

    @staticmethod
    def update_last_fetched(source_id: int, error: Optional[str] = None) -> bool:
        """Stamp last_fetched_at for a source. On error, increments error_count;
        on success, resets error_count to 0 and clears fetch_error."""
        try:
            with get_db_cursor() as cursor:
                if error:
                    cursor.execute(
                        """UPDATE sources
                           SET last_fetched_at = NOW(),
                               fetch_error = %(error)s,
                               error_count = COALESCE(error_count, 0) + 1,
                               updated_at = NOW()
                           WHERE id = %(source_id)s""",
                        {"source_id": source_id, "error": error},
                    )
                else:
                    cursor.execute(
                        """UPDATE sources
                           SET last_fetched_at = NOW(),
                               fetch_error = NULL,
                               error_count = 0,
                               updated_at = NOW()
                           WHERE id = %(source_id)s""",
                        {"source_id": source_id},
                    )
                return True
        except Exception as e:
            print(f"Error updating last_fetched for source {source_id}: {e}")
            return False

    @staticmethod
    def get_paginated(
        page: int = 1,
        limit: int = 20,
        active: Optional[bool] = None,
        language: Optional[str] = None,
        group_name: Optional[str] = None,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return a paginated list of sources with optional filters.

        Returns a pagination envelope:
            {"data": [...], "pagination": {"page", "limit", "total", "pages"}}
        """
        conditions: List[str] = []
        params: Dict[str, Any] = {}

        if active is not None:
            conditions.append("active = %(active)s")
            params["active"] = active
        if language:
            conditions.append("language = %(language)s")
            params["language"] = language
        if group_name:
            conditions.append("group_name = %(group_name)s")
            params["group_name"] = group_name
        if category:
            conditions.append("category = %(category)s")
            params["category"] = category
        if subcategory:
            conditions.append("subcategory = %(subcategory)s")
            params["subcategory"] = subcategory

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = (page - 1) * limit
        params.update({"limit": limit, "offset": offset})

        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    f"SELECT COUNT(*) AS total FROM sources {where}", params
                )
                total = cursor.fetchone()["total"]

                cursor.execute(
                    f"SELECT * FROM sources {where} ORDER BY name "
                    f"LIMIT %(limit)s OFFSET %(offset)s",
                    params,
                )
                rows = [dict(r) for r in cursor.fetchall()]

            return {
                "data": rows,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "total_pages": max(1, -(-total // limit)),
                },
            }
        except Exception as e:
            print(f"Error fetching paginated sources: {e}")
            return {"data": [], "pagination": {"page": page, "limit": limit, "total": 0, "total_pages": 0}}


# ---------------------------------------------------------------------------


class HeadlineRepository:
    """Repository for CRUD operations on the headlines table."""

    _SORT_WHITELIST = {"published_at", "created_at", "title"}

    @staticmethod
    def bulk_insert(headlines: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Bulk-insert headlines with ON CONFLICT DO NOTHING.

        Each dict must contain at least: source_id, title, url.
        Returns {"inserted": N, "skipped": M}.
        """
        inserted = 0
        skipped = 0
        try:
            with get_db_cursor() as cursor:
                for h in headlines:
                    cursor.execute(
                        """
                        INSERT INTO headlines (
                            source_id, title, url, language, published_at,
                            created_at, updated_at
                        ) VALUES (
                            %(source_id)s, %(title)s, %(url)s,
                            %(language)s, %(published_at)s,
                            NOW(), NOW()
                        )
                        ON CONFLICT (url, source_id) DO NOTHING
                        RETURNING id
                        """,
                        {
                            "source_id": h.get("source_id"),
                            "title": h.get("title"),
                            "url": h.get("url") or h.get("link"),
                            "language": h.get("language", "en"),
                            "published_at": h.get("published_at") or h.get("published") or None,
                        },
                    )
                    if cursor.fetchone():
                        inserted += 1
                    else:
                        skipped += 1
        except Exception as e:
            print(f"Bulk insert failed: {e}")
        return {"inserted": inserted, "skipped": skipped}

    @staticmethod
    def get_paginated(
        page: int = 1,
        limit: int = 20,
        sort: str = "published_at",
        order: str = "desc",
        topic: Optional[str] = None,
        language: Optional[str] = None,
        source_id: Optional[int] = None,
        q: Optional[str] = None,
        sentiment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return paginated headlines joined with source name.

        Supports full-text search via to_tsvector('simple', ...) when q is set.
        Returns a pagination envelope.
        """
        # Sanitise sort / order to prevent SQL injection
        if sort not in HeadlineRepository._SORT_WHITELIST:
            sort = "published_at"
        order = "ASC" if order.lower() == "asc" else "DESC"

        conditions: List[str] = []
        params: Dict[str, Any] = {}

        if topic:
            conditions.append("h.topic = %(topic)s")
            params["topic"] = topic
        if language:
            conditions.append("h.language = %(language)s")
            params["language"] = language
        if source_id is not None:
            conditions.append("h.source_id = %(source_id)s")
            params["source_id"] = source_id
        if q:
            conditions.append(
                "to_tsvector('simple', h.title) @@ plainto_tsquery('simple', %(q)s)"
            )
            params["q"] = q
        if sentiment:
            conditions.append("h.sentiment = %(sentiment)s")
            params["sentiment"] = sentiment

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = (page - 1) * limit
        params.update({"limit": limit, "offset": offset})

        base_query = f"""
            FROM headlines h
            LEFT JOIN sources s ON h.source_id = s.id
            {where}
        """
        try:
            with get_db_cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) AS total {base_query}", params)
                total = cursor.fetchone()["total"]

                cursor.execute(
                    f"""
                    SELECT h.*, s.name AS source_name
                    {base_query}
                    ORDER BY h.{sort} {order}
                    LIMIT %(limit)s OFFSET %(offset)s
                    """,
                    params,
                )
                rows = [dict(r) for r in cursor.fetchall()]

            return {
                "data": rows,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "total_pages": max(1, -(-total // limit)),
                },
            }
        except Exception as e:
            print(f"Error fetching paginated headlines: {e}")
            return {"data": [], "pagination": {"page": page, "limit": limit, "total": 0, "total_pages": 0}}

    @staticmethod
    def get_count() -> int:
        """Return the total number of headlines stored."""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS count FROM headlines")
                return cursor.fetchone()["count"]
        except Exception as e:
            print(f"Error counting headlines: {e}")
            return 0

    @staticmethod
    def update_topic(
        headline_id: int, topic: str, confidence: float
    ) -> bool:
        """Persist the topic classification result for a headline."""
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE headlines
                    SET topic = %(topic)s,
                        topic_confidence = %(confidence)s,
                        updated_at = NOW()
                    WHERE id = %(id)s
                    """,
                    {"id": headline_id, "topic": topic, "confidence": confidence},
                )
                return True
        except Exception as e:
            print(f"Error updating topic for headline {headline_id}: {e}")
            return False

    @staticmethod
    def update_translation(headline_id: int, translated_title: str) -> bool:
        """Store the translated title for a headline."""
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE headlines
                    SET translated_title = %(translated_title)s,
                        updated_at = NOW()
                    WHERE id = %(id)s
                    """,
                    {"id": headline_id, "translated_title": translated_title},
                )
                return True
        except Exception as e:
            print(f"Error updating translation for headline {headline_id}: {e}")
            return False

    @staticmethod
    def update_entities(
        headline_id: int, entities: Any, event_type: Optional[str] = None
    ) -> bool:
        """Persist extracted entities (serialised as JSON) and optional event_type."""
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE headlines
                    SET entities = %(entities)s,
                        event_type = %(event_type)s,
                        updated_at = NOW()
                    WHERE id = %(id)s
                    """,
                    {
                        "id": headline_id,
                        "entities": json.dumps(entities),
                        "event_type": event_type,
                    },
                )
                return True
        except Exception as e:
            print(f"Error updating entities for headline {headline_id}: {e}")
            return False

    @staticmethod
    def update_sentiment(headline_id: int, sentiment: str, score: float) -> bool:
        """Persist sentiment analysis result for a headline."""
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE headlines
                    SET sentiment = %(sentiment)s,
                        sentiment_score = %(score)s,
                        updated_at = NOW()
                    WHERE id = %(headline_id)s
                    """,
                    {"headline_id": headline_id, "sentiment": sentiment, "score": score},
                )
                return True
        except Exception as e:
            print(f"Error updating sentiment for headline {headline_id}: {e}")
            return False

    @staticmethod
    def update_embedding_id(headline_id: int, embedding_id: str) -> bool:
        """Store the Qdrant point ID for a headline's embedding."""
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE headlines
                    SET embedding_id = %(embedding_id)s,
                        updated_at = NOW()
                    WHERE id = %(id)s
                    """,
                    {"id": headline_id, "embedding_id": embedding_id},
                )
                return True
        except Exception as e:
            print(f"Error updating embedding_id for headline {headline_id}: {e}")
            return False

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


# ---------------------------------------------------------------------------


class EventClusterRepository:
    """Repository for CRUD operations on event_clusters and cluster members."""

    @staticmethod
    def create_cluster(
        label: str,
        event_type: str,
        key_entities: Any,
        summary: Optional[str],
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        headline_ids: List[int],
        similarity_scores: Optional[List[float]] = None,
    ) -> Optional[Dict]:
        """
        Insert a new event cluster and its member headlines atomically.

        Returns the created cluster row, or None on failure.
        """
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO event_clusters (
                        label, event_type, key_entities, summary,
                        start_time, end_time, created_at, updated_at
                    ) VALUES (
                        %(label)s, %(event_type)s, %(key_entities)s, %(summary)s,
                        %(start_time)s, %(end_time)s, NOW(), NOW()
                    )
                    RETURNING *
                    """,
                    {
                        "label": label,
                        "event_type": event_type,
                        "key_entities": json.dumps(key_entities),
                        "summary": summary,
                        "start_time": start_time,
                        "end_time": end_time,
                    },
                )
                cluster = dict(cursor.fetchone())
                cluster_id = cluster["id"]

                scores = similarity_scores or []
                for i, hid in enumerate(headline_ids):
                    score = scores[i] if i < len(scores) else None
                    cursor.execute(
                        """
                        INSERT INTO event_cluster_members
                            (cluster_id, headline_id, similarity_score)
                        VALUES (%(cluster_id)s, %(headline_id)s, %(score)s)
                        ON CONFLICT DO NOTHING
                        """,
                        {"cluster_id": cluster_id, "headline_id": hid, "score": score},
                    )
                return cluster
        except Exception as e:
            print(f"Error creating event cluster: {e}")
            return None

    @staticmethod
    def get_paginated(
        page: int = 1,
        limit: int = 20,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Return paginated event clusters with member headline counts.

        Returns a pagination envelope.
        """
        conditions: List[str] = []
        params: Dict[str, Any] = {}

        if event_type:
            conditions.append("c.event_type = %(event_type)s")
            params["event_type"] = event_type
        if since:
            conditions.append("c.created_at >= %(since)s")
            params["since"] = since

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = (page - 1) * limit
        params.update({"limit": limit, "offset": offset})

        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    f"SELECT COUNT(*) AS total FROM event_clusters c {where}", params
                )
                total = cursor.fetchone()["total"]

                cursor.execute(
                    f"""
                    SELECT c.*,
                           (
                               SELECT COUNT(*)
                               FROM event_cluster_members m
                               WHERE m.cluster_id = c.id
                           ) AS headline_count
                    FROM event_clusters c
                    {where}
                    ORDER BY c.created_at DESC
                    LIMIT %(limit)s OFFSET %(offset)s
                    """,
                    params,
                )
                rows = [dict(r) for r in cursor.fetchall()]

            return {
                "data": rows,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "total_pages": max(1, -(-total // limit)),
                },
            }
        except Exception as e:
            print(f"Error fetching paginated clusters: {e}")
            return {"data": [], "pagination": {"page": page, "limit": limit, "total": 0, "total_pages": 0}}

    @staticmethod
    def get_by_id(cluster_id: int) -> Optional[Dict]:
        """
        Return a single cluster with its full list of member headlines
        (joined with source names).
        """
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM event_clusters WHERE id = %s", (cluster_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return None
                cluster = dict(row)

                cursor.execute(
                    """
                    SELECT h.*, s.name AS source_name, m.similarity_score
                    FROM event_cluster_members m
                    JOIN headlines h ON m.headline_id = h.id
                    LEFT JOIN sources s ON h.source_id = s.id
                    WHERE m.cluster_id = %s
                    ORDER BY h.published_at DESC
                    """,
                    (cluster_id,),
                )
                cluster["members"] = [dict(r) for r in cursor.fetchall()]
                return cluster
        except Exception as e:
            print(f"Error fetching cluster {cluster_id}: {e}")
            return None


# ---------------------------------------------------------------------------


class AnalyticsRepository:
    """Aggregation queries for dashboard analytics."""

    _PERIOD_MAP = {
        "24h": "24 hours",
        "7d": "7 days",
        "30d": "30 days",
    }

    @staticmethod
    def get_analytics(period: str = "7d") -> Dict[str, Any]:
        """
        Return aggregated analytics over the requested time window.

        Returned structure:
            {
                "topic_distribution": [{"topic": str, "count": int}, ...],
                "source_breakdown":   [{"source_name": str, "count": int}, ...],
                "language_breakdown": [{"language": str, "count": int}, ...],
                "daily_volume":       [{"day": date, "count": int}, ...],
            }
        """
        interval = AnalyticsRepository._PERIOD_MAP.get(period, "7 days")
        params = {"interval": interval}
        result: Dict[str, Any] = {
            "topic_distribution": [],
            "source_breakdown": [],
            "language_breakdown": [],
            "category_breakdown": [],
            "daily_volume": [],
            "sentiment_distribution": [],
            "topic_category_heatmap": [],
        }
        try:
            with get_db_cursor() as cursor:
                # Topic distribution
                cursor.execute(
                    """
                    SELECT topic, COUNT(*) AS count
                    FROM headlines
                    WHERE topic IS NOT NULL
                      AND created_at >= NOW() - %(interval)s::INTERVAL
                    GROUP BY topic
                    ORDER BY count DESC
                    """,
                    params,
                )
                result["topic_distribution"] = [dict(r) for r in cursor.fetchall()]

                # Source breakdown
                cursor.execute(
                    """
                    SELECT s.id AS source_id, s.name, COUNT(h.id) AS count
                    FROM headlines h
                    LEFT JOIN sources s ON h.source_id = s.id
                    WHERE h.created_at >= NOW() - %(interval)s::INTERVAL
                    GROUP BY s.id, s.name
                    ORDER BY count DESC
                    """,
                    params,
                )
                result["source_breakdown"] = [dict(r) for r in cursor.fetchall()]

                # Language breakdown
                cursor.execute(
                    """
                    SELECT language, COUNT(*) AS count
                    FROM headlines
                    WHERE created_at >= NOW() - %(interval)s::INTERVAL
                    GROUP BY language
                    ORDER BY count DESC
                    """,
                    params,
                )
                result["language_breakdown"] = [dict(r) for r in cursor.fetchall()]

                # Category breakdown
                cursor.execute(
                    """
                    SELECT s.category, COUNT(h.id) AS count
                    FROM headlines h
                    JOIN sources s ON h.source_id = s.id
                    WHERE h.created_at >= NOW() - %(interval)s::INTERVAL
                      AND s.category IS NOT NULL
                    GROUP BY s.category
                    ORDER BY count DESC
                    """,
                    params,
                )
                result["category_breakdown"] = [dict(r) for r in cursor.fetchall()]

                # Daily volume
                cursor.execute(
                    """
                    SELECT DATE(created_at) AS date, COUNT(*) AS count
                    FROM headlines
                    WHERE created_at >= NOW() - %(interval)s::INTERVAL
                    GROUP BY DATE(created_at)
                    ORDER BY DATE(created_at) ASC
                    """,
                    params,
                )
                result["daily_volume"] = [dict(r) for r in cursor.fetchall()]

                # Sentiment distribution
                cursor.execute(
                    """
                    SELECT sentiment, COUNT(*) AS count
                    FROM headlines
                    WHERE sentiment IS NOT NULL
                      AND created_at >= NOW() - %(interval)s::INTERVAL
                    GROUP BY sentiment
                    ORDER BY count DESC
                    """,
                    params,
                )
                result["sentiment_distribution"] = [dict(r) for r in cursor.fetchall()]

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

        except Exception as e:
            print(f"Error fetching analytics: {e}")

        result["period"] = period
        return result


# ---------------------------------------------------------------------------


class InsightsRepository:
    """Aggregation queries for AI agent consumption."""

    _PERIOD_MAP = {
        "24h": "24 hours",
        "7d": "7 days",
        "30d": "30 days",
    }

    @staticmethod
    def get_summary(period: str = "24h") -> Dict[str, Any]:
        """
        Return structured financial intelligence for the requested time window.

        Returned structure:
            {
                "top_headlines_by_category": {
                    "<category>": [
                        {"title", "url", "topic", "topic_confidence", "source_name"},
                        ...
                    ],
                    ...
                },
                "topic_counts":     [{"topic": str, "count": int}, ...],
                "category_volume":  [{"category": str, "count": int}, ...],
                "top_clusters":     [{"label", "event_type", "headline_count"}, ...],
                "feed_health":      {"healthy": int, "erroring": int, "inactive": int},
                "period":           str,
            }
        """
        interval = InsightsRepository._PERIOD_MAP.get(period, "24 hours")
        params = {"interval": interval}
        result: Dict[str, Any] = {
            "top_headlines_by_category": {},
            "topic_counts": [],
            "category_volume": [],
            "top_clusters": [],
            "feed_health": {"healthy": 0, "erroring": 0, "inactive": 0},
            "sentiment_breakdown": {},
            "sentiment_by_category": {},
        }
        try:
            with get_db_cursor() as cursor:
                # Top 5 headlines per source category (excluding "general" topic)
                cursor.execute(
                    """
                    SELECT s.category,
                           h.title,
                           h.url,
                           h.topic,
                           h.topic_confidence,
                           s.name AS source_name,
                           ROW_NUMBER() OVER (
                               PARTITION BY s.category
                               ORDER BY h.topic_confidence DESC
                           ) AS rn
                    FROM headlines h
                    JOIN sources s ON h.source_id = s.id
                    WHERE h.topic IS NOT NULL
                      AND h.topic <> 'general'
                      AND h.created_at >= NOW() - %(interval)s::INTERVAL
                      AND s.category IS NOT NULL
                    """,
                    params,
                )
                rows = cursor.fetchall()
                by_category: Dict[str, List[Dict]] = {}
                for row in rows:
                    if row["rn"] > 5:
                        continue
                    cat = row["category"]
                    if cat not in by_category:
                        by_category[cat] = []
                    by_category[cat].append(
                        {
                            "title": row["title"],
                            "url": row["url"],
                            "topic": row["topic"],
                            "topic_confidence": row["topic_confidence"],
                            "source_name": row["source_name"],
                        }
                    )
                result["top_headlines_by_category"] = by_category

                # Topic counts
                cursor.execute(
                    """
                    SELECT topic, COUNT(*) AS count
                    FROM headlines
                    WHERE topic IS NOT NULL
                      AND created_at >= NOW() - %(interval)s::INTERVAL
                    GROUP BY topic
                    ORDER BY count DESC
                    """,
                    params,
                )
                result["topic_counts"] = [dict(r) for r in cursor.fetchall()]

                # Category volume
                cursor.execute(
                    """
                    SELECT s.category, COUNT(h.id) AS count
                    FROM headlines h
                    JOIN sources s ON h.source_id = s.id
                    WHERE h.created_at >= NOW() - %(interval)s::INTERVAL
                      AND s.category IS NOT NULL
                    GROUP BY s.category
                    ORDER BY count DESC
                    """,
                    params,
                )
                result["category_volume"] = [dict(r) for r in cursor.fetchall()]

                # Top 10 event clusters by member count
                cursor.execute(
                    """
                    SELECT c.label,
                           c.event_type,
                           COUNT(m.headline_id) AS headline_count
                    FROM event_clusters c
                    JOIN event_cluster_members m ON m.cluster_id = c.id
                    WHERE c.created_at >= NOW() - %(interval)s::INTERVAL
                    GROUP BY c.id, c.label, c.event_type
                    ORDER BY headline_count DESC
                    LIMIT 10
                    """,
                    params,
                )
                result["top_clusters"] = [dict(r) for r in cursor.fetchall()]

                # Feed health
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) FILTER (
                            WHERE active = TRUE AND (fetch_error IS NULL OR fetch_error = '')
                        ) AS healthy,
                        COUNT(*) FILTER (
                            WHERE active = TRUE AND fetch_error IS NOT NULL AND fetch_error <> ''
                        ) AS erroring,
                        COUNT(*) FILTER (WHERE active = FALSE) AS inactive
                    FROM sources
                    """
                )
                row = cursor.fetchone()
                if row:
                    result["feed_health"] = {
                        "healthy": row["healthy"],
                        "erroring": row["erroring"],
                        "inactive": row["inactive"],
                    }

                # Sentiment breakdown
                cursor.execute(
                    """
                    SELECT sentiment, COUNT(*) AS count
                    FROM headlines
                    WHERE sentiment IS NOT NULL
                      AND created_at >= NOW() - %(interval)s::INTERVAL
                    GROUP BY sentiment
                    """,
                    params,
                )
                result["sentiment_breakdown"] = {
                    r["sentiment"]: r["count"] for r in cursor.fetchall()
                }

                # Sentiment by category
                cursor.execute(
                    """
                    SELECT s.category, h.sentiment, COUNT(*) AS count
                    FROM headlines h
                    JOIN sources s ON h.source_id = s.id
                    WHERE h.sentiment IS NOT NULL
                      AND h.created_at >= NOW() - %(interval)s::INTERVAL
                    GROUP BY s.category, h.sentiment
                    ORDER BY s.category
                    """,
                    params,
                )
                by_cat: Dict[str, Dict[str, int]] = {}
                for row in cursor.fetchall():
                    cat = row["category"]
                    by_cat.setdefault(cat, {"bullish": 0, "bearish": 0, "neutral": 0})
                    by_cat[cat][row["sentiment"]] = row["count"]
                result["sentiment_by_category"] = by_cat

        except Exception as e:
            print(f"Error fetching insights summary: {e}")

        result["period"] = period
        return result

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
        return {w for w in text.lower().split() if len(w) > 3 and w not in InsightsRepository.STOP_WORDS}

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

            # Pre-compute significant words
            for oh in other_headlines:
                oh["_words"] = InsightsRepository._significant_words(oh["title"])

            cross_refs = []
            divergences = []

            for pm in pm_headlines:
                pm_words = InsightsRepository._significant_words(pm["title"])
                if not pm_words:
                    continue

                matches = []
                for oh in other_headlines:
                    shared = pm_words & oh["_words"]
                    if len(shared) >= 2:
                        matches.append({
                            "title": oh["title"], "url": oh["url"],
                            "sentiment": oh["sentiment"], "source_name": oh["source_name"],
                            "category": oh["category"], "shared_words": len(shared),
                        })

                matches.sort(key=lambda m: m["shared_words"], reverse=True)
                top_matches = matches[:3]

                if top_matches:
                    pm_ref = {"title": pm["title"], "url": pm["url"],
                              "sentiment": pm["sentiment"], "source_name": pm["source_name"]}
                    cross_refs.append({"pm_headline": pm_ref, "related": top_matches})

                    pm_sent = pm.get("sentiment")
                    if pm_sent and pm_sent != "neutral":
                        related_sentiments = [m["sentiment"] for m in top_matches if m.get("sentiment") and m["sentiment"] != "neutral"]
                        if related_sentiments:
                            from collections import Counter
                            majority = Counter(related_sentiments).most_common(1)[0][0]
                            if majority != pm_sent:
                                divergences.append({
                                    "pm_headline": pm_ref,
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

    @staticmethod
    def get_category_detail(category: str, period: str = "24h") -> Dict[str, Any]:
        """
        Return detailed insights for a single source category.

        Returned structure:
            {
                "category":             str,
                "period":               str,
                "headlines":            [top 25, ordered by topic_confidence DESC],
                "topic_distribution":   [{"topic": str, "count": int}, ...],
                "sources":              [{"source_id", "name", "headline_count",
                                          "active", "fetch_error"}, ...],
            }
        """
        interval = InsightsRepository._PERIOD_MAP.get(period, "24 hours")
        params = {"interval": interval, "category": category}
        result: Dict[str, Any] = {
            "category": category,
            "headlines": [],
            "topic_distribution": [],
            "sources": [],
        }
        try:
            with get_db_cursor() as cursor:
                # Top 25 headlines for this category
                cursor.execute(
                    """
                    SELECT h.id,
                           h.title,
                           h.url,
                           h.topic,
                           h.topic_confidence,
                           h.published_at,
                           s.name AS source_name
                    FROM headlines h
                    JOIN sources s ON h.source_id = s.id
                    WHERE s.category = %(category)s
                      AND h.created_at >= NOW() - %(interval)s::INTERVAL
                    ORDER BY h.topic_confidence DESC NULLS LAST
                    LIMIT 25
                    """,
                    params,
                )
                result["headlines"] = [dict(r) for r in cursor.fetchall()]

                # Topic distribution within this category
                cursor.execute(
                    """
                    SELECT h.topic, COUNT(*) AS count
                    FROM headlines h
                    JOIN sources s ON h.source_id = s.id
                    WHERE s.category = %(category)s
                      AND h.topic IS NOT NULL
                      AND h.created_at >= NOW() - %(interval)s::INTERVAL
                    GROUP BY h.topic
                    ORDER BY count DESC
                    """,
                    params,
                )
                result["topic_distribution"] = [dict(r) for r in cursor.fetchall()]

                # Sources in this category with headline count and health info
                cursor.execute(
                    """
                    SELECT s.id AS source_id,
                           s.name,
                           s.active,
                           s.fetch_error,
                           COUNT(h.id) AS headline_count
                    FROM sources s
                    LEFT JOIN headlines h
                        ON h.source_id = s.id
                        AND h.created_at >= NOW() - %(interval)s::INTERVAL
                    WHERE s.category = %(category)s
                    GROUP BY s.id, s.name, s.active, s.fetch_error
                    ORDER BY headline_count DESC
                    """,
                    params,
                )
                result["sources"] = [dict(r) for r in cursor.fetchall()]

        except Exception as e:
            print(f"Error fetching category detail for '{category}': {e}")

        result["period"] = period
        return result


# ---------------------------------------------------------------------------


class PipelineRunRepository:
    """Repository for tracking pipeline execution history."""

    @staticmethod
    def create_run() -> Optional[int]:
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    "INSERT INTO pipeline_runs (started_at, status) VALUES (NOW(), 'running') RETURNING id"
                )
                row = cursor.fetchone()
                return row["id"] if row else None
        except Exception as e:
            print(f"Error creating pipeline run: {e}")
            return None

    @staticmethod
    def complete_run(run_id: int, stats: Dict[str, Any], error: Optional[str] = None):
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """UPDATE pipeline_runs
                       SET completed_at = NOW(),
                           status = %(status)s,
                           headlines_gathered = %(gathered)s,
                           headlines_inserted = %(inserted)s,
                           feeds_success = %(feeds_ok)s,
                           feeds_failed = %(feeds_err)s,
                           duration_ms = %(duration)s,
                           error = %(error)s
                       WHERE id = %(run_id)s""",
                    {
                        "run_id": run_id,
                        "status": "error" if error else "completed",
                        "gathered": stats.get("gathered", 0),
                        "inserted": stats.get("inserted", 0),
                        "feeds_success": stats.get("feeds_success", 0),
                        "feeds_failed": stats.get("feeds_failed", 0),
                        "duration": stats.get("duration_ms", 0),
                        "error": error,
                    },
                )
        except Exception as e:
            print(f"Error completing pipeline run: {e}")

    @staticmethod
    def get_recent(limit: int = 10) -> List[Dict]:
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT %s",
                    (limit,),
                )
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching pipeline runs: {e}")
            return []


# ---------------------------------------------------------------------------


class SettingsRepository:
    """Key-value store for application configuration backed by the settings table."""

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
