"""
Parallel ML Pipeline
====================

Runs classify and extract stages concurrently using ThreadPoolExecutor.
Each stage writes to distinct fields so merge is conflict-free.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Batch wrappers
# ---------------------------------------------------------------------------

def classify_batch_wrapper(headlines: List[Dict]) -> List[Dict]:
    """Classify each headline's title via keyword matching."""
    from model_loader import get_classifier
    classifier = get_classifier()

    results = []
    for h in headlines:
        text = h.get("title") or h.get("text") or ""
        source_category = h.get("category")
        try:
            result = classifier.classify_single(text, source_category=source_category)
            top = result["topTopics"][0] if result.get("topTopics") else {}
            results.append({
                "topic": top.get("topic", "general"),
                "topic_confidence": top.get("confidence", 0.0),
            })
        except Exception as e:
            logger.warning("classify_batch_wrapper error for %r: %s", text[:60], e)
            results.append({"topic": "general", "topic_confidence": 0.0})

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


# ---------------------------------------------------------------------------
# Parallel runner
# ---------------------------------------------------------------------------

def run_parallel_ml(
    headlines: List[Dict],
    classify_fn: Callable[[List[Dict]], List[Dict]] = classify_batch_wrapper,
    extract_fn: Callable[[List[Dict]], List[Dict]] = extract_batch_wrapper,
    progress_callback: Optional[Callable[..., None]] = None,
    **_kwargs,
) -> List[Dict]:
    """
    Run classify and extract on *headlines* concurrently.

    Each function receives the full list of headline dicts and returns a
    parallel list of result dicts.  Because each stage writes to distinct
    fields (topic/confidence, entities/event_type) the merge is conflict-free.
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

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {
            pool.submit(_run, "classify", classify_fn, headlines): "classify",
            pool.submit(_run, "extract", extract_fn, headlines): "extract",
        }

        for future in as_completed(futures):
            try:
                name, result = future.result()
                stage_results[name] = result
            except Exception as e:
                stage_name = futures[future]
                logger.error("parallel_pipeline: %s stage raised: %s", stage_name, e)
                if stage_name == "classify":
                    stage_results["classify"] = [
                        {"topic": "general", "topic_confidence": 0.0} for _ in headlines
                    ]
                elif stage_name == "extract":
                    stage_results["extract"] = [
                        {"entities": [], "event_type": "other"} for _ in headlines
                    ]

    # Merge
    enriched = []
    for i, headline in enumerate(headlines):
        merged = dict(headline)
        merged.update(stage_results.get("classify", [{}] * len(headlines))[i])
        merged.update(stage_results.get("extract", [{}] * len(headlines))[i])
        enriched.append(merged)

    return enriched
