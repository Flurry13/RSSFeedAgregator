"""
Event Grouping Module
====================

Cluster related events into coherent groups using entity overlap and
word similarity.  No embeddings or ML models required.
"""

import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Any

try:
    from .event_extract import EventExtractor
except ImportError:
    from event_extract import EventExtractor

logger = logging.getLogger(__name__)


class EventGrouper:
    """Group events into clusters using entity overlap + word similarity."""

    def __init__(self):
        self.event_extractor = EventExtractor()
        self.min_cluster_size = 3
        self.similarity_threshold = 0.35
        self.time_window_hours = 24
        logger.info("Initialized EventGrouper (keyword mode)")

    # ------------------------------------------------------------------
    # Similarity
    # ------------------------------------------------------------------

    def compute_event_similarity(self, event1: Dict, event2: Dict) -> float:
        """Combine entity overlap (0.5) + word Jaccard (0.3) + type match (0.2)."""
        entity_sim = self._entity_overlap(event1, event2)
        word_sim = self._word_jaccard(event1, event2)
        type_sim = 1.0 if event1.get("event_type") == event2.get("event_type") else 0.0
        return 0.5 * entity_sim + 0.3 * word_sim + 0.2 * type_sim

    @staticmethod
    def _entity_overlap(e1: Dict, e2: Dict) -> float:
        ents1 = {(ent["text"].lower(), ent["label"]) for ent in e1.get("entities", [])}
        ents2 = {(ent["text"].lower(), ent["label"]) for ent in e2.get("entities", [])}
        if not ents1 or not ents2:
            return 0.0
        return len(ents1 & ents2) / len(ents1 | ents2)

    @staticmethod
    def _word_jaccard(e1: Dict, e2: Dict) -> float:
        w1 = set(e1.get("text", "").lower().split())
        w2 = set(e2.get("text", "").lower().split())
        if not w1 or not w2:
            return 0.0
        return len(w1 & w2) / len(w1 | w2)

    # ------------------------------------------------------------------
    # Clustering  (greedy single-link)
    # ------------------------------------------------------------------

    def cluster_events(self, events: List[Dict]) -> List[int]:
        """Assign cluster labels using greedy single-link above threshold."""
        n = len(events)
        if n < 2:
            return list(range(n))

        labels = [-1] * n
        cluster_id = 0

        for i in range(n):
            if labels[i] != -1:
                continue
            # start a new cluster from event i
            group = [i]
            labels[i] = cluster_id
            for j in range(i + 1, n):
                if labels[j] != -1:
                    continue
                for member in group:
                    if self.compute_event_similarity(events[member], events[j]) >= self.similarity_threshold:
                        labels[j] = cluster_id
                        group.append(j)
                        break
            # only keep cluster if meets min size
            if len(group) < self.min_cluster_size:
                for idx in group:
                    labels[idx] = -1
            else:
                cluster_id += 1

        n_clusters = cluster_id
        n_noise = labels.count(-1)
        logger.info("Found %d clusters, %d noise points", n_clusters, n_noise)
        return labels

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    def deduplicate_events(self, events: List[Dict]) -> List[Dict]:
        if not events:
            return events
        hash_groups: Dict[str, List[Dict]] = defaultdict(list)
        for event in events:
            hash_groups[event.get("event_hash", "")].append(event)
        deduped = []
        for group in hash_groups.values():
            best = max(group, key=lambda e: e.get("type_confidence", 0) + e.get("relationship_confidence", 0))
            deduped.append(best)
        logger.info("Deduplicated %d events to %d", len(events), len(deduped))
        return deduped

    # ------------------------------------------------------------------
    # Representative selection  (most entities)
    # ------------------------------------------------------------------

    @staticmethod
    def select_representative_event(cluster: List[Dict]) -> Dict:
        if len(cluster) == 1:
            return cluster[0]
        return max(cluster, key=lambda e: len(e.get("entities", [])))

    def calculate_cohesion_score(self, cluster: List[Dict]) -> float:
        if len(cluster) < 2:
            return 1.0
        sims = []
        for i in range(len(cluster)):
            for j in range(i + 1, len(cluster)):
                sims.append(self.compute_event_similarity(cluster[i], cluster[j]))
        return sum(sims) / len(sims) if sims else 0.0

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def generate_group_summary(self, cluster: List[Dict]) -> Dict:
        if not cluster:
            return {}
        LABEL_ENTITY_TYPES = {'PERSON', 'ORG', 'GPE', 'NORP', 'FAC', 'EVENT', 'PRODUCT', 'LAW'}
        STOP_LABELS = {'the', 'a', 'an', 'this', 'that', 'it', 'they', 'we', 'he', 'she',
                       'first', 'second', 'third', 'last', 'new', 'old', 'more', 'most',
                       'one', 'two', 'three', 'four', 'five', 'million', 'billion', 'trillion'}

        all_entities: List[Dict] = []
        for event in cluster:
            all_entities.extend(event.get("entities", []))

        filtered = [e for e in all_entities
                    if e.get("label") in LABEL_ENTITY_TYPES
                    and e["text"].lower().strip() not in STOP_LABELS
                    and len(e["text"].strip()) > 1
                    and not e["text"].strip().replace('.', '').replace(',', '').isdigit()]

        entity_counts: Dict[tuple, int] = defaultdict(int)
        for ent in filtered:
            entity_counts[(ent["text"], ent["label"])] += 1
        common = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        event_types = [e.get("event_type", "other") for e in cluster]
        dominant = max(set(event_types), key=event_types.count)
        return {
            "size": len(cluster),
            "dominant_event_type": dominant,
            "common_entities": [{"text": t, "label": l, "count": c} for (t, l), c in common],
            "time_span": self._get_time_span(cluster),
            "cohesion_score": self.calculate_cohesion_score(cluster),
        }

    @staticmethod
    def _get_time_span(cluster: List[Dict]) -> Dict:
        timestamps = []
        for event in cluster:
            if "extracted_at" in event:
                try:
                    ts = datetime.fromisoformat(event["extracted_at"].replace("Z", "+00:00"))
                    timestamps.append(ts)
                except ValueError:
                    continue
        if not timestamps:
            return {"start": None, "end": None, "duration_hours": 0}
        start, end = min(timestamps), max(timestamps)
        return {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "duration_hours": round((end - start).total_seconds() / 3600, 2),
        }

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def create_event_groups(
        self,
        texts: List[str],
        headline_ids: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        start_time = time.time()

        if config:
            self.min_cluster_size = config.get("min_cluster_size", self.min_cluster_size)
            self.similarity_threshold = config.get("similarity_threshold", self.similarity_threshold)

        logger.info("Starting event grouping for %d headlines", len(texts))

        all_events: List[Dict] = []
        event_lists = self.event_extractor.extract_events_batch(texts, headline_ids)
        for el in event_lists:
            all_events.extend(el)

        logger.info("Extracted %d events", len(all_events))
        if not all_events:
            return {
                "metadata": {
                    "total_headlines": len(texts),
                    "total_events": 0,
                    "total_groups": 0,
                    "processing_time": time.time() - start_time,
                },
                "groups": [],
            }

        unique_events = self.deduplicate_events(all_events)
        cluster_labels = self.cluster_events(unique_events)

        clusters: Dict[int, List[Dict]] = defaultdict(list)
        for i, label in enumerate(cluster_labels):
            clusters[label].append(unique_events[i])

        groups = []
        for cid, event_cluster in clusters.items():
            if cid == -1:
                for ev in event_cluster:
                    groups.append({
                        "group_id": f"noise_{ev['event_id']}",
                        "representative": ev,
                        "events": [ev],
                        "summary": self.generate_group_summary([ev]),
                    })
            else:
                groups.append({
                    "group_id": f"cluster_{cid}",
                    "representative": self.select_representative_event(event_cluster),
                    "events": event_cluster,
                    "summary": self.generate_group_summary(event_cluster),
                })

        groups.sort(key=lambda g: g["summary"]["size"], reverse=True)
        elapsed = time.time() - start_time
        logger.info("Event grouping completed in %.2fs", elapsed)

        return {
            "metadata": {
                "total_headlines": len(texts),
                "total_events": len(all_events),
                "unique_events": len(unique_events),
                "total_groups": len(groups),
                "processing_time": elapsed,
            },
            "groups": groups,
        }


# Convenience singleton
_default_grouper = None


def get_default_grouper() -> EventGrouper:
    global _default_grouper
    if _default_grouper is None:
        _default_grouper = EventGrouper()
    return _default_grouper


def create_event_groups(
    texts: List[str],
    headline_ids: Optional[List[str]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return get_default_grouper().create_event_groups(texts, headline_ids, config)
