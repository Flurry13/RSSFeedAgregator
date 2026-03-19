"""RSSFeed2 API Server — Flask + Flask-SocketIO."""
import csv
import io
import logging
import os
import sys
import threading
import time
from datetime import datetime
from typing import Optional

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit

sys.path.append(os.path.join(os.path.dirname(__file__), "pipeline"))

from database import init_connection_pool, get_db_cursor
from repositories import (
    AnalyticsRepository,
    EventClusterRepository,
    HeadlineRepository,
    InsightsRepository,
    PipelineRunRepository,
    SettingsRepository,
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
    pipeline_status.update(
        stage=stage, status=status, progress=progress, total=total, message=message
    )
    socketio.emit("status_update", pipeline_status)


def emit_log(level, message):
    entry = {
        "level": level,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    }
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
    sentiment = request.args.get("sentiment")
    result = HeadlineRepository.get_paginated(
        page=page,
        limit=limit,
        sort=sort,
        order=order,
        topic=topic,
        language=language,
        source_id=source_id,
        q=q,
        sentiment=sentiment,
    )
    return jsonify(result)


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


# --- Events ---


@app.route("/api/events")
def get_events():
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 50, type=int), 200)
    event_type = request.args.get("event_type")
    since = request.args.get("since")
    result = EventClusterRepository.get_paginated(
        page=page, limit=limit, event_type=event_type, since=since
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


# --- Insights ---


@app.route("/api/insights/summary")
def get_insights_summary():
    period = request.args.get("period", "24h")
    if period not in ("24h", "7d", "30d"):
        period = "24h"
    return jsonify(InsightsRepository.get_summary(period))


@app.route("/api/insights/category/<category>")
def get_insights_category(category):
    period = request.args.get("period", "24h")
    if period not in ("24h", "7d", "30d"):
        period = "24h"
    return jsonify(InsightsRepository.get_category_detail(category, period))


@app.route("/api/insights/predictions")
def get_prediction_signals():
    period = request.args.get("period", "24h")
    if period not in ("24h", "7d", "30d"):
        period = "24h"
    return jsonify(InsightsRepository.get_prediction_signals(period))


# --- Settings ---


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


# --- Sources CRUD ---


@app.route("/api/sources", methods=["GET"])
def list_sources():
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 50, type=int), 200)
    active = (
        request.args.get("active", type=lambda v: v.lower() == "true")
        if "active" in request.args
        else None
    )
    language = request.args.get("language")
    group_name = request.args.get("group_name")
    category = request.args.get("category")
    subcategory = request.args.get("subcategory")
    result = SourceRepository.get_paginated(
        page=page,
        limit=limit,
        active=active,
        language=language,
        group_name=group_name,
        category=category,
        subcategory=subcategory,
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


@app.route("/api/pipeline/history")
def get_pipeline_history():
    limit = min(request.args.get("limit", 10, type=int), 50)
    return jsonify(PipelineRunRepository.get_recent(limit))


@app.route("/api/gather", methods=["POST"])
def start_gather():
    if pipeline_status["status"] == "running":
        return jsonify({"error": "Pipeline already running"}), 409

    def _run():
        from gather import gather

        start = time.time()
        emit_status("gather", "running", message="Gathering RSS feeds...")
        emit_log("info", "Starting RSS gathering")
        try:
            headlines = gather()
            emit_log("info", f"Gathered {len(headlines)} headlines")
            result = HeadlineRepository.bulk_insert(headlines)
            emit_log("info", f"Inserted {result['inserted']}, skipped {result['skipped']}")
            emit_status(
                "gather",
                "idle",
                progress=len(headlines),
                total=len(headlines),
                message=f"Gathered {len(headlines)} headlines",
            )
            socketio.emit(
                "headlines_update",
                {"count": len(headlines), "new_headlines": result["inserted"]},
            )
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
        from translate import Translator

        start = time.time()
        emit_status("translate", "running", message="Translating headlines...")
        emit_log("info", "Starting translation")
        try:
            translator = Translator()
            result = HeadlineRepository.get_paginated(limit=200)
            headlines = [
                h
                for h in result["data"]
                if h.get("language") != "en" and not h.get("translated_title")
            ]
            emit_log("info", f"Found {len(headlines)} headlines to translate")

            for i, h in enumerate(headlines):
                translated = translator.translate_text(h["title"], h.get("language", "en"))
                if translated:
                    HeadlineRepository.update_translation(h["id"], translated)
                emit_status(
                    "translate",
                    "running",
                    progress=i + 1,
                    total=len(headlines),
                    message=f"Translating {i + 1}/{len(headlines)}",
                )

            emit_status(
                "translate",
                "idle",
                progress=len(headlines),
                total=len(headlines),
                message=f"Translated {len(headlines)} headlines",
            )
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
            result = HeadlineRepository.get_paginated(limit=200)
            headlines = [h for h in result["data"] if not h.get("topic")]
            emit_log("info", f"Found {len(headlines)} headlines to classify")

            for i, h in enumerate(headlines):
                text = h.get("translated_title") or h["title"]
                source_category = h.get("category")
                classification = classifier.classify_single(text, source_category=source_category)
                top = classification.get("topTopics", [{}])[0]
                topic = top.get("topic", "general")
                confidence = top.get("confidence", 0.0)
                HeadlineRepository.update_topic(h["id"], topic, confidence)
                emit_status(
                    "classify",
                    "running",
                    progress=i + 1,
                    total=len(headlines),
                    message=f"Classifying {i + 1}/{len(headlines)}",
                )

            emit_status(
                "classify",
                "idle",
                progress=len(headlines),
                total=len(headlines),
                message=f"Classified {len(headlines)} headlines",
            )
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


def _run_pipeline_body():
    from gather import gather
    from translate import Translator
    from parallel_pipeline import (
        run_parallel_ml,
        classify_batch_wrapper,
        extract_batch_wrapper,
    )

    start = time.time()
    run_id = PipelineRunRepository.create_run()
    emit_log("info", "Starting full pipeline")

    _run_stats: dict = {
        "gathered": 0,
        "inserted": 0,
        "feeds_success": 0,
        "feeds_failed": 0,
        "duration_ms": 0,
    }

    try:
        # Stage 1: Gather
        emit_status("gather", "running", message="Gathering RSS feeds...")
        headlines = gather()
        _run_stats["gathered"] = len(headlines)
        emit_log("info", f"Gathered {len(headlines)} headlines")
        result = HeadlineRepository.bulk_insert(headlines)
        _run_stats["inserted"] = result["inserted"]
        emit_log(
            "info", f"Inserted {result['inserted']}, skipped {result['skipped']}"
        )

        # Stage 2: Translate
        emit_status(
            "translate",
            "running",
            progress=0,
            total=len(headlines),
            message="Translating...",
        )
        translator = Translator()
        headlines = translator.translate_headlines(headlines)
        emit_log("info", "Translation complete")

        # Stage 3: Parallel ML (classify + extract)
        emit_status(
            "ml_parallel",
            "running",
            progress=0,
            total=2,
            message="Running classify + extract in parallel...",
        )
        headlines = run_parallel_ml(
            headlines,
            classify_fn=classify_batch_wrapper,
            extract_fn=extract_batch_wrapper,
            progress_callback=lambda **kw: emit_status(**kw),
        )
        emit_log("info", "Parallel ML stage complete")

        # Stage 4: Store ML results to DB + collect real headline IDs
        emit_status("store", "running", message="Persisting ML results...")
        db_headlines = []
        for h in headlines:
            url = h.get("url") or h.get("link")
            source_id = h.get("source_id")
            if not url or not source_id:
                continue
            # Look up the real DB id by unique (url, source_id)
            with get_db_cursor() as cur:
                cur.execute(
                    "SELECT id FROM headlines WHERE url = %s AND source_id = %s",
                    (url, source_id),
                )
                row = cur.fetchone()
            if not row:
                continue
            hid = row["id"]
            h["id"] = hid
            if h.get("topic"):
                HeadlineRepository.update_topic(
                    hid, h["topic"], h.get("topic_confidence", 0.0)
                )
            if h.get("entities"):
                HeadlineRepository.update_entities(
                    hid, h["entities"], h.get("event_type", "other")
                )
            if h.get("sentiment"):
                HeadlineRepository.update_sentiment(
                    hid, h["sentiment"], h.get("sentiment_score", 0.5)
                )
            db_headlines.append(h)
        emit_log("info", f"ML results persisted for {len(db_headlines)} headlines")

        # Stage 5: Group events into clusters
        emit_status("group", "running", message="Clustering events...")
        try:
            from group_by_event import EventGrouper

            grouper = EventGrouper()
            texts = [h.get("translated_title") or h["title"] for h in db_headlines]
            h_ids = [str(h["id"]) for h in db_headlines]
            grouping_result = grouper.create_event_groups(
                texts, headline_ids=h_ids
            )

            groups = grouping_result.get("groups", [])
            created = 0
            for g in groups:
                if g["group_id"].startswith("noise_"):
                    continue
                events = g.get("events", [])
                member_ids = [
                    int(ev["headline_id"])
                    for ev in events
                    if str(ev.get("headline_id", "")).isdigit()
                ]
                if not member_ids:
                    continue
                summary = g.get("summary", {})
                common_ents = summary.get("common_entities", [])
                if common_ents:
                    label = common_ents[0]["text"]
                else:
                    # Fallback: use most common significant word from headlines
                    from collections import Counter
                    words = []
                    for mid in member_ids:
                        h = next((x for x in db_headlines if str(x["id"]) == str(mid)), None)
                        if h:
                            for w in (h.get("title") or "").split():
                                if len(w) > 3 and w[0].isupper():
                                    words.append(w.rstrip("'s").rstrip(",").rstrip("."))
                    if words:
                        label = Counter(words).most_common(1)[0][0]
                    else:
                        label = "Uncategorized"
                cohesion = summary.get("cohesion_score", 0.5)
                time_span = summary.get("time_span", {})
                EventClusterRepository.create_cluster(
                    label=label,
                    event_type=summary.get("dominant_event_type", "other"),
                    key_entities=common_ents,
                    summary=str(summary),
                    start_time=time_span.get("start"),
                    end_time=time_span.get("end"),
                    headline_ids=member_ids,
                    similarity_scores=[cohesion] * len(member_ids),
                )
                created += 1
            emit_log("info", f"Created {created} event clusters")
        except Exception as e:
            emit_log("warn", f"Event clustering failed (non-fatal): {e}")

        elapsed = int((time.time() - start) * 1000)
        _run_stats["duration_ms"] = elapsed
        pipeline_status["last_run"] = datetime.utcnow().isoformat()
        pipeline_status["last_duration_ms"] = elapsed

        if run_id is not None:
            PipelineRunRepository.complete_run(run_id, _run_stats)

        emit_status(None, "idle", message="Pipeline complete")
        socketio.emit(
            "pipeline_complete",
            {
                "duration_ms": elapsed,
                "headlines_gathered": len(headlines),
                "translated": sum(
                    1 for h in headlines if h.get("translated_title")
                ),
                "classified": sum(1 for h in headlines if h.get("topic")),
            },
        )
        socketio.emit(
            "headlines_update",
            {"count": len(headlines), "new_headlines": result["inserted"]},
        )

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
                        cur.execute("DELETE FROM event_clusters WHERE id NOT IN (SELECT DISTINCT cluster_id FROM event_cluster_members)")
        except Exception as e:
            emit_log("warn", f"Retention cleanup failed: {e}")

    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        _run_stats["duration_ms"] = elapsed
        if run_id is not None:
            PipelineRunRepository.complete_run(run_id, _run_stats, error=str(e))
        emit_status(None, "error", message=str(e))
        emit_log("error", f"Pipeline failed: {e}")


_scheduler_timer: Optional[threading.Timer] = None
_scheduler_lock = threading.Lock()

def _restart_scheduler():
    global _scheduler_timer
    with _scheduler_lock:
        if _scheduler_timer:
            _scheduler_timer.cancel()
            _scheduler_timer = None
        try:
            enabled = SettingsRepository.get("pipeline_schedule_enabled")
            interval = SettingsRepository.get("pipeline_schedule_interval")
            if enabled == "true" and interval:
                minutes = int(interval)
                _scheduler_timer = threading.Timer(minutes * 60, _scheduled_run)
                _scheduler_timer.daemon = True
                _scheduler_timer.start()
        except Exception:
            pass

def _scheduled_run():
    if pipeline_status["status"] != "running":
        threading.Thread(target=_run_pipeline_body, daemon=True).start()
    _restart_scheduler()


@app.route("/api/run", methods=["POST"])
def run_full_pipeline():
    if pipeline_status["status"] == "running":
        return jsonify({"error": "Pipeline already running"}), 409
    threading.Thread(target=_run_pipeline_body, daemon=True).start()
    return jsonify({"message": "Full pipeline started"})


# --- Search ---


@app.route("/api/search")
def search():
    q = request.args.get("q", "")
    limit = min(request.args.get("limit", 20, type=int), 100)
    if not q:
        return jsonify({"error": "q parameter required"}), 400

    try:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT h.*, s.name AS source_name, s.country,
                       ts_rank(
                           to_tsvector('simple', coalesce(h.translated_title, '') || ' ' || h.title),
                           plainto_tsquery('simple', %(q)s)
                       ) AS score
                FROM headlines h
                LEFT JOIN sources s ON h.source_id = s.id
                WHERE to_tsvector('simple', coalesce(h.translated_title, '') || ' ' || h.title)
                      @@ plainto_tsquery('simple', %(q)s)
                ORDER BY score DESC
                LIMIT %(limit)s
                """,
                {"q": q, "limit": limit},
            )
            rows = [dict(r) for r in cur.fetchall()]
        data = [{"headline": row, "score": row.pop("score", 0)} for row in rows]
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

try:
    _restart_scheduler()
except Exception:
    pass

if __name__ == "__main__":
    logger.info("Initializing database connection pool...")
    init_connection_pool()

    port = int(os.getenv("NLP_PORT", 8081))
    logger.info("Starting server on port %d", port)
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
