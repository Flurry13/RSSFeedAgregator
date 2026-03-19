"""Lazy model loaders. No preloading — models are created on first use."""
import logging

logger = logging.getLogger(__name__)

_classifier = None
_extractor = None


def get_classifier():
    """Get or create the keyword-based classifier (instant, no model to load)."""
    global _classifier
    if _classifier is None:
        from pipeline.classify import TopicClassifier
        _classifier = TopicClassifier()
        logger.info("Keyword classifier ready")
    return _classifier


def get_extractor():
    """Get or create the spaCy event extractor (loads on first use)."""
    global _extractor
    if _extractor is None:
        from pipeline.event_extract import EventExtractor
        _extractor = EventExtractor()
        logger.info("Event extractor ready")
    return _extractor
