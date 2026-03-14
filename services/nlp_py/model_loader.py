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

    from pipeline.classify import TopicClassifier
    _classifier = TopicClassifier()
    logger.info("  Classifier loaded (%.1fs)", time.time() - start)

    t = time.time()
    from pipeline.embed import TextEmbedder
    _embedder = TextEmbedder()
    logger.info("  Embedder loaded (%.1fs)", time.time() - t)

    t = time.time()
    from pipeline.event_extract import EventExtractor
    _extractor = EventExtractor()
    logger.info("  Extractor loaded (%.1fs)", time.time() - t)

    logger.info("All models preloaded in %.1fs", time.time() - start)


def get_classifier():
    global _classifier
    if _classifier is None:
        from pipeline.classify import TopicClassifier
        _classifier = TopicClassifier()
    return _classifier


def get_embedder():
    global _embedder
    if _embedder is None:
        from pipeline.embed import TextEmbedder
        _embedder = TextEmbedder()
    return _embedder


def get_extractor():
    global _extractor
    if _extractor is None:
        from pipeline.event_extract import EventExtractor
        _extractor = EventExtractor()
    return _extractor
