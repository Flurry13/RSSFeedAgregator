"""RSSFeed2 API Server — Flask + Flask-SocketIO."""
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit

sys.path.append(os.path.join(os.path.dirname(__file__), "pipeline"))

from database import init_connection_pool, get_db_cursor
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
    result = HeadlineRepository.get_paginated(
        page=page,
        limit=limit,
        sort=sort,
        order=order,
        topic=topic,
        language=language,
        source_id=source_id,
        q=q,
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
    result = SourceRepository.get_paginated(
        page=page,
        limit=limit,
        active=active,
        language=language,
        group_name=group_name,
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
                classification = classifier.classify_single(text)
                topic = (
                    classification.get("labels", ["other"])[0]
                    if classification.get("labels")
                    else "other"
                )
                confidence = (
                    classification.get("scores", [0.0])[0]
                    if classification.get("scores")
                    else 0.0
                )
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


@app.route("/api/run", methods=["POST"])
def run_full_pipeline():
    if pipeline_status["status"] == "running":
        return jsonify({"error": "Pipeline already running"}), 409

    def _run():
        from gather import gather
        from translate import Translator
        from parallel_pipeline import (
            run_parallel_ml,
            classify_batch_wrapper,
            extract_batch_wrapper,
            embed_batch_wrapper,
        )

        start = time.time()
        emit_log("info", "Starting full pipeline")

        try:
            # Stage 1: Gather
            emit_status("gather", "running", message="Gathering RSS feeds...")
            headlines = gather()
            emit_log("info", f"Gathered {len(headlines)} headlines")
            result = HeadlineRepository.bulk_insert(headlines)
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

            # Stage 3: Parallel ML (classify + extract + embed)
            emit_status(
                "ml_parallel",
                "running",
                progress=0,
                total=3,
                message="Running classify, extract, embed in parallel...",
            )
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
                hid = h.get("id") or h.get("source_id")
                if not hid:
                    continue
                if h.get("topic"):
                    HeadlineRepository.update_topic(
                        hid, h["topic"], h.get("topic_confidence", 0.0)
                    )
                if h.get("entities"):
                    HeadlineRepository.update_entities(
                        hid, h["entities"], h.get("event_type", "other")
                    )
                if h.get("embedding_id"):
                    HeadlineRepository.update_embedding_id(hid, h["embedding_id"])
            emit_log("info", "ML results persisted to DB")

            # Stage 5: Group events into clusters
            emit_status("group", "running", message="Clustering events...")
            try:
                from group_by_event import EventGrouper

                grouper = EventGrouper()
                texts = [h.get("translated_title") or h["title"] for h in headlines]
                h_ids = [str(h.get("id", i)) for i, h in enumerate(headlines)]
                grouping_result = grouper.create_event_groups(
                    texts, headline_ids=h_ids
                )

                groups = grouping_result.get("groups", [])
                for g in groups:
                    member_ids = [
                        int(mid)
                        for mid in g.get("member_ids", [])
                        if str(mid).isdigit()
                    ]
                    scores = g.get("similarity_scores", [0.5] * len(member_ids))
                    if member_ids:
                        EventClusterRepository.create_cluster(
                            label=g.get("summary", {}).get("keywords", ["Event"])[0]
                            if isinstance(g.get("summary"), dict)
                            else "Event cluster",
                            event_type=g.get("event_type", "other"),
                            key_entities=g.get("summary", {}).get(
                                "top_entities", {}
                            ),
                            summary=str(g.get("summary", "")),
                            start_time=g.get("time_span", {}).get("start"),
                            end_time=g.get("time_span", {}).get("end"),
                            headline_ids=member_ids,
                            similarity_scores=scores[: len(member_ids)],
                        )
                emit_log("info", f"Created {len(groups)} event clusters")
            except Exception as e:
                emit_log("warn", f"Event clustering failed (non-fatal): {e}")

            elapsed = int((time.time() - start) * 1000)
            pipeline_status["last_run"] = datetime.utcnow().isoformat()
            pipeline_status["last_duration_ms"] = elapsed

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
