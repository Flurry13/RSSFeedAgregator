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
        """Stamp last_fetched_at (and optionally last_error) for a source."""
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE sources
                    SET last_fetched_at = NOW(),
                        fetch_error = %(error)s,
                        updated_at = NOW()
                    WHERE id = %(source_id)s
                    """,
                    {"source_id": source_id, "error": error},
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
                            "published_at": h.get("published_at") or h.get("published"),
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
            "daily_volume": [],
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
                    GROUP BY s.name
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

                # Daily volume
                cursor.execute(
                    """
                    SELECT DATE(created_at) AS date, COUNT(*) AS count
                    FROM headlines
                    WHERE created_at >= NOW() - %(interval)s::INTERVAL
                    GROUP BY day
                    ORDER BY day ASC
                    """,
                    params,
                )
                result["daily_volume"] = [dict(r) for r in cursor.fetchall()]

        except Exception as e:
            print(f"Error fetching analytics: {e}")

        result["period"] = period
        return result
