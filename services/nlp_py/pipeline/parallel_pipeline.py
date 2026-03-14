"""
Parallel ML Pipeline
====================

Runs classify, extract, and embed stages concurrently using ThreadPoolExecutor.
Each stage writes to distinct fields so merge is conflict-free.
"""

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Batch wrappers
# ---------------------------------------------------------------------------

def classify_batch_wrapper(headlines: List[Dict]) -> List[Dict]:
    """Classify each headline's title and return {topic, confidence} per item."""
    from model_loader import get_classifier
    classifier = get_classifier()

    results = []
    for h in headlines:
        text = h.get("title") or h.get("text") or ""
        try:
            result = classifier.classify_single(text)
            top = result["topTopics"][0] if result.get("topTopics") else {}
            results.append({
                "topic": top.get("topic", "general"),
                "confidence": top.get("confidence", 0.0),
            })
        except Exception as e:
            logger.warning("classify_batch_wrapper error for %r: %s", text[:60], e)
            results.append({"topic": "general", "confidence": 0.0})

    return results


def extract_batch_wrapper(headlines: List[Dict]) -> List[Dict]:
    """Extract entities and event_type per headline."""
    from model_loader import get_extractor
    extractor = get_extractor()

    results = []
    for h in headlines:
        text = h.get("title") or h.get("text") or ""
        try:
            entities = extractor.extract_entities(text)
            event_type, _confidence = extractor.classify_event_type(text, entities)
            results.append({
                "entities": entities,
                "event_type": event_type,
            })
        except Exception as e:
            logger.warning("extract_batch_wrapper error for %r: %s", text[:60], e)
            results.append({"entities": [], "event_type": "other"})

    return results


def embed_batch_wrapper(headlines: List[Dict]) -> List[Dict]:
    """Embed all headline texts in a single batch call and return embedding + embedding_id."""
    from model_loader import get_embedder
    embedder = get_embedder()

    texts = [h.get("title") or h.get("text") or "" for h in headlines]

    try:
        embeddings = embedder.embed_texts(texts)
        results = []
        for emb in embeddings:
            results.append({
                "embedding": emb.tolist(),
                "embedding_id": str(uuid.uuid4()),
            })
        return results
    except Exception as e:
        logger.error("embed_batch_wrapper failed: %s", e)
        return [{"embedding": [], "embedding_id": str(uuid.uuid4())} for _ in headlines]


# ---------------------------------------------------------------------------
# Parallel runner
# ---------------------------------------------------------------------------

def run_parallel_ml(
    headlines: List[Dict],
    classify_fn: Callable[[List[Dict]], List[Dict]] = classify_batch_wrapper,
    extract_fn: Callable[[List[Dict]], List[Dict]] = extract_batch_wrapper,
    embed_fn: Callable[[List[Dict]], List[Dict]] = embed_batch_wrapper,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> List[Dict]:
    """
    Run classify, extract, and embed on *headlines* concurrently.

    Each function receives the full list of headline dicts and returns a
    parallel list of result dicts.  Because each stage writes to distinct
    fields (topic/confidence, entities/event_type, embedding/embedding_id)
    the merge step is conflict-free.

    Args:
        headlines: List of headline dicts (must contain 'title' or 'text').
        classify_fn: Callable matching classify_batch_wrapper signature.
        extract_fn: Callable matching extract_batch_wrapper signature.
        embed_fn: Callable matching embed_batch_wrapper signature.
        progress_callback: Optional callable(stage_name) called as each stage
                           completes — useful for SSE / WebSocket progress.

    Returns:
        List of headline dicts enriched with ML fields.
    """
    if not headlines:
        return []

    stage_results: Dict[str, Any] = {}

    def _run(name: str, fn: Callable, data: List[Dict]):
        logger.info("parallel_pipeline: starting %s on %d items", name, len(data))
        result = fn(data)
        logger.info("parallel_pipeline: %s done", name)
        if progress_callback:
            try:
                progress_callback(name)
            except Exception:
                pass
        return name, result

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_run, "classify", classify_fn, headlines): "classify",
            pool.submit(_run, "extract", extract_fn, headlines): "extract",
            pool.submit(_run, "embed", embed_fn, headlines): "embed",
        }

        for future in as_completed(futures):
            try:
                name, result = future.result()
                stage_results[name] = result
            except Exception as e:
                stage_name = futures[future]
                logger.error("parallel_pipeline: %s stage raised: %s", stage_name, e)
                # Fill with empty placeholders so merge always has data
                if stage_name == "classify":
                    stage_results["classify"] = [
                        {"topic": "general", "confidence": 0.0} for _ in headlines
                    ]
                elif stage_name == "extract":
                    stage_results["extract"] = [
                        {"entities": [], "event_type": "other"} for _ in headlines
                    ]
                elif stage_name == "embed":
                    stage_results["embed"] = [
                        {"embedding": [], "embedding_id": str(uuid.uuid4())}
                        for _ in headlines
                    ]

    # Merge: start from copies of the original headlines
    enriched = []
    for i, headline in enumerate(headlines):
        merged = dict(headline)
        merged.update(stage_results.get("classify", [{}] * len(headlines))[i])
        merged.update(stage_results.get("extract", [{}] * len(headlines))[i])
        merged.update(stage_results.get("embed", [{}] * len(headlines))[i])
        enriched.append(merged)

    return enriched
