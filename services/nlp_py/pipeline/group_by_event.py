"""
Event Grouping Module
====================

Cluster related events into coherent groups using embeddings and clustering.
This module processes extracted events and groups them for analysis.
"""

import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

import numpy as np
from sklearn.preprocessing import normalize
from sklearn.metrics.pairwise import cosine_similarity
import hdbscan
from sentence_transformers import SentenceTransformer

# Import event extraction functionality
try:
    from .event_extract import EventExtractor
except ImportError:
    # Fallback for direct execution
    from event_extract import EventExtractor

# Configure logging
logger = logging.getLogger(__name__)


class EventGrouper:
    """Group events into clusters using embeddings and clustering algorithms."""
    
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        """Initialize the event grouper."""
        self.embedding_model_name = embedding_model
        self.embedding_model = SentenceTransformer(embedding_model)
        self.event_extractor = EventExtractor()
        
        # Clustering parameters
        self.min_cluster_size = 3
        self.min_samples = None
        self.similarity_threshold = 0.7
        self.time_window_hours = 24
        self.location_threshold = 0.8
        
        logger.info(f"Initialized EventGrouper with model: {embedding_model}")
    
    def compute_event_similarity(self, event1: Dict[str, Any], event2: Dict[str, Any]) -> float:
        """Compute similarity between two events combining multiple measures."""
        if not event1.get("embedding") or not event2.get("embedding"):
            return self._compute_text_similarity(event1, event2)
        
        # Semantic similarity using embeddings
        semantic_sim = cosine_similarity(
            [event1["embedding"]], [event2["embedding"]]
        )[0][0]
        
        # Entity overlap
        entity_sim = self._compute_entity_overlap(event1, event2)
        
        # Event type similarity
        type_sim = 1.0 if event1.get("event_type") == event2.get("event_type") else 0.0
        
        # Combine similarities with weights
        combined_similarity = (
            0.6 * semantic_sim +
            0.2 * entity_sim +
            0.2 * type_sim
        )
        
        return combined_similarity
    
    def _compute_text_similarity(self, event1: Dict[str, Any], event2: Dict[str, Any]) -> float:
        """Compute text-based similarity as fallback."""
        text1 = event1.get("text", "")
        text2 = event2.get("text", "")
        
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _compute_entity_overlap(self, event1: Dict[str, Any], event2: Dict[str, Any]) -> float:
        """Compute entity overlap between two events."""
        entities1 = event1.get("entities", [])
        entities2 = event2.get("entities", [])
        
        if not entities1 or not entities2:
            return 0.0
        
        ent_texts1 = {(ent["text"].lower(), ent["label"]) for ent in entities1}
        ent_texts2 = {(ent["text"].lower(), ent["label"]) for ent in entities2}
        
        if not ent_texts1 or not ent_texts2:
            return 0.0
        
        intersection = len(ent_texts1.intersection(ent_texts2))
        union = len(ent_texts1.union(ent_texts2))
        
        return intersection / union if union > 0 else 0.0
    
    def deduplicate_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate events based on hashes and high similarity."""
        if not events:
            return events
        
        # Group by event hash
        hash_groups = defaultdict(list)
        for event in events:
            event_hash = event.get("event_hash", "")
            hash_groups[event_hash].append(event)
        
        deduplicated = []
        for event_group in hash_groups.values():
            if len(event_group) == 1:
                deduplicated.append(event_group[0])
            else:
                # Keep the event with highest confidence
                best_event = max(event_group, key=lambda e: (
                    e.get("type_confidence", 0) + 
                    e.get("relationship_confidence", 0)
                ))
                deduplicated.append(best_event)
        
        logger.info(f"Deduplicated {len(events)} events to {len(deduplicated)}")
        return deduplicated
    
    def _compute_embeddings(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compute embeddings for events."""
        texts = []
        for event in events:
            text_parts = [
                event.get("text", ""),
                event.get("subject", ""),
                event.get("predicate", ""),
                event.get("object", "")
            ]
            combined_text = " ".join([part for part in text_parts if part])
            texts.append(combined_text)
        
        logger.info(f"Computing embeddings for {len(texts)} events...")
        embeddings = self.embedding_model.encode(texts, batch_size=32, show_progress_bar=False)
        embeddings = normalize(embeddings, norm='l2')
        
        # Add embeddings to events
        events_with_embeddings = []
        for i, event in enumerate(events):
            event_copy = event.copy()
            event_copy["embedding"] = embeddings[i]
            events_with_embeddings.append(event_copy)
        
        return events_with_embeddings
    
    def cluster_events(self, events: List[Dict[str, Any]]) -> List[int]:
        """Cluster events using HDBSCAN algorithm."""
        if len(events) < 2:
            return [0] * len(events)
        
        embeddings = np.array([event["embedding"] for event in events])
        
        logger.info(f"Clustering {len(events)} events with HDBSCAN...")
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
            metric='euclidean'
        )
        
        cluster_labels = clusterer.fit_predict(embeddings)
        
        n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
        n_noise = list(cluster_labels).count(-1)
        
        logger.info(f"Found {n_clusters} clusters, {n_noise} noise points")
        return cluster_labels.tolist()
    
    def select_representative_event(self, event_cluster: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select the most representative event from a cluster."""
        if len(event_cluster) == 1:
            return event_cluster[0]
        
        embeddings = np.array([event["embedding"] for event in event_cluster])
        centroid = np.mean(embeddings, axis=0)
        centroid = centroid / np.linalg.norm(centroid)
        
        similarities = cosine_similarity([centroid], embeddings)[0]
        best_idx = np.argmax(similarities)
        
        return event_cluster[best_idx]
    
    def calculate_cohesion_score(self, event_cluster: List[Dict[str, Any]]) -> float:
        """Calculate cohesion score for an event cluster."""
        if len(event_cluster) < 2:
            return 1.0
        
        similarities = []
        for i in range(len(event_cluster)):
            for j in range(i + 1, len(event_cluster)):
                sim = self.compute_event_similarity(event_cluster[i], event_cluster[j])
                similarities.append(sim)
        
        return np.mean(similarities) if similarities else 0.0
    
    def generate_group_summary(self, event_cluster: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a summary for an event group."""
        if not event_cluster:
            return {}
        
        # Extract common entities
        all_entities = []
        for event in event_cluster:
            all_entities.extend(event.get("entities", []))
        
        entity_counts = defaultdict(int)
        for entity in all_entities:
            key = (entity["text"], entity["label"])
            entity_counts[key] += 1
        
        common_entities = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Extract event types
        event_types = [event.get("event_type", "other") for event in event_cluster]
        most_common_type = max(set(event_types), key=event_types.count)
        
        return {
            "size": len(event_cluster),
            "dominant_event_type": most_common_type,
            "common_entities": [{"text": text, "label": label, "count": count} 
                              for (text, label), count in common_entities],
            "time_span": self._get_time_span(event_cluster),
            "cohesion_score": self.calculate_cohesion_score(event_cluster)
        }
    
    def _get_time_span(self, event_cluster: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get time span information for a cluster."""
        timestamps = []
        for event in event_cluster:
            if "extracted_at" in event:
                try:
                    ts = datetime.fromisoformat(event["extracted_at"].replace('Z', '+00:00'))
                    timestamps.append(ts)
                except ValueError:
                    continue
        
        if not timestamps:
            return {"start": None, "end": None, "duration_hours": 0}
        
        start_time = min(timestamps)
        end_time = max(timestamps)
        duration = (end_time - start_time).total_seconds() / 3600
        
        return {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "duration_hours": round(duration, 2)
        }
    
    def group_events_by_time(self, events: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group events within temporal windows."""
        if not events:
            return []
        
        timestamped_events = []
        for event in events:
            if "extracted_at" in event:
                try:
                    ts = datetime.fromisoformat(event["extracted_at"].replace('Z', '+00:00'))
                    timestamped_events.append((ts, event))
                except ValueError:
                    continue
        
        timestamped_events.sort(key=lambda x: x[0])
        
        time_groups = []
        current_group = []
        current_window_start = None
        
        for timestamp, event in timestamped_events:
            if current_window_start is None:
                current_window_start = timestamp
                current_group = [event]
            else:
                hours_diff = (timestamp - current_window_start).total_seconds() / 3600
                if hours_diff <= self.time_window_hours:
                    current_group.append(event)
                else:
                    if current_group:
                        time_groups.append(current_group)
                    current_group = [event]
                    current_window_start = timestamp
        
        if current_group:
            time_groups.append(current_group)
        
        logger.info(f"Grouped events into {len(time_groups)} time windows")
        return time_groups
    
    def group_events_by_location(self, events: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group events by geographic proximity."""
        location_groups = defaultdict(list)
        
        for event in events:
            locations = []
            for entity in event.get("entities", []):
                if entity["label"] in ["GPE", "LOC"]:
                    locations.append(entity["text"].lower())
            
            location_key = locations[0] if locations else "unknown"
            location_groups[location_key].append(event)
        
        logger.info(f"Grouped events into {len(location_groups)} geographic regions")
        return list(location_groups.values())
    
    def create_event_groups(self, texts: List[str], headline_ids: Optional[List[str]] = None, 
                           config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Main function to create event groups from text headlines."""
        start_time = time.time()
        
        if config:
            self.min_cluster_size = config.get("min_cluster_size", self.min_cluster_size)
            self.similarity_threshold = config.get("similarity_threshold", self.similarity_threshold)
            self.time_window_hours = config.get("time_window_hours", self.time_window_hours)
        
        logger.info(f"Starting event grouping for {len(texts)} headlines")
        
        # Extract events from texts
        logger.info("Extracting events from texts...")
        all_events = []
        event_lists = self.event_extractor.extract_events_batch(texts, headline_ids)
        
        for event_list in event_lists:
            all_events.extend(event_list)
        
        logger.info(f"Extracted {len(all_events)} events")
        
        if not all_events:
            return {
                "metadata": {
                    "total_headlines": len(texts),
                    "total_events": 0,
                    "total_groups": 0,
                    "processing_time": time.time() - start_time
                },
                "groups": []
            }
        
        # Deduplicate events
        logger.info("Deduplicating events...")
        unique_events = self.deduplicate_events(all_events)
        
        # Compute embeddings
        logger.info("Computing embeddings...")
        events_with_embeddings = self._compute_embeddings(unique_events)
        
        # Cluster events
        logger.info("Clustering events...")
        cluster_labels = self.cluster_events(events_with_embeddings)
        
        # Create groups and select representatives
        logger.info("Creating event groups...")
        clusters = defaultdict(list)
        for i, label in enumerate(cluster_labels):
            clusters[label].append(events_with_embeddings[i])
        
        groups = []
        for cluster_id, event_cluster in clusters.items():
            if cluster_id == -1:
                # Handle noise points as individual groups
                for event in event_cluster:
                    group_summary = {
                        "group_id": f"noise_{event['event_id']}",
                        "representative": event,
                        "events": [event],
                        "summary": self.generate_group_summary([event])
                    }
                    groups.append(group_summary)
            else:
                # Regular cluster
                representative = self.select_representative_event(event_cluster)
                group_summary = {
                    "group_id": f"cluster_{cluster_id}",
                    "representative": representative,
                    "events": event_cluster,
                    "summary": self.generate_group_summary(event_cluster)
                }
                groups.append(group_summary)
        
        # Sort groups by size
        groups.sort(key=lambda g: g["summary"]["size"], reverse=True)
        
        processing_time = time.time() - start_time
        logger.info(f"Event grouping completed in {processing_time:.2f}s")
        
        return {
            "metadata": {
                "total_headlines": len(texts),
                "total_events": len(all_events),
                "unique_events": len(unique_events),
                "total_groups": len(groups),
                "processing_time": processing_time,
                "clustering_params": {
                    "min_cluster_size": self.min_cluster_size,
                    "similarity_threshold": self.similarity_threshold,
                    "embedding_model": self.embedding_model_name
                }
            },
            "groups": groups
        }


# Default grouper instance
_default_grouper = None


def get_default_grouper() -> EventGrouper:
    """Get or create the default event grouper instance."""
    global _default_grouper
    if _default_grouper is None:
        _default_grouper = EventGrouper()
    return _default_grouper


# Convenience functions
def compute_event_similarity(event1: Dict[str, Any], event2: Dict[str, Any]) -> float:
    return get_default_grouper().compute_event_similarity(event1, event2)


def deduplicate_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return get_default_grouper().deduplicate_events(events)


def cluster_events(events: List[Dict[str, Any]]) -> List[int]:
    return get_default_grouper().cluster_events(events)


def select_representative_event(event_cluster: List[Dict[str, Any]]) -> Dict[str, Any]:
    return get_default_grouper().select_representative_event(event_cluster)


def calculate_cohesion_score(event_cluster: List[Dict[str, Any]]) -> float:
    return get_default_grouper().calculate_cohesion_score(event_cluster)


def generate_group_summary(event_cluster: List[Dict[str, Any]]) -> Dict[str, Any]:
    return get_default_grouper().generate_group_summary(event_cluster)


def group_events_by_time(events: List[Dict[str, Any]], time_window_hours: int = 24) -> List[List[Dict[str, Any]]]:
    grouper = get_default_grouper()
    original_window = grouper.time_window_hours
    grouper.time_window_hours = time_window_hours
    result = grouper.group_events_by_time(events)
    grouper.time_window_hours = original_window
    return result


def group_events_by_location(events: List[Dict[str, Any]], location_threshold: float = 0.8) -> List[List[Dict[str, Any]]]:
    grouper = get_default_grouper()
    original_threshold = grouper.location_threshold
    grouper.location_threshold = location_threshold
    result = grouper.group_events_by_location(events)
    grouper.location_threshold = original_threshold
    return result


def create_event_groups(texts: List[str], headline_ids: Optional[List[str]] = None, 
                       config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return get_default_grouper().create_event_groups(texts, headline_ids, config)


# Event extraction utilities
def extract_all_events(grouping_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract all individual events from grouping results.
    
    Args:
        grouping_result: Result from create_event_groups()
        
    Returns:
        List of all events (both clustered and singleton)
    """
    all_events = []
    for group in grouping_result.get('groups', []):
        all_events.extend(group.get('events', []))
    
    return all_events


def extract_events_by_type(grouping_result: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract events organized by clustering type.
    
    Args:
        grouping_result: Result from create_event_groups()
        
    Returns:
        Dictionary with 'clustered' and 'singleton' event lists
    """
    clustered_events = []
    singleton_events = []
    
    for group in grouping_result.get('groups', []):
        events = group.get('events', [])
        if len(events) > 1:
            clustered_events.extend(events)
        elif len(events) == 1:
            singleton_events.extend(events)
    
    return {
        'clustered': clustered_events,
        'singleton': singleton_events
    }


def get_event_by_id(grouping_result: Dict[str, Any], event_id: str) -> Optional[Dict[str, Any]]:
    """
    Find a specific event by its event_id.
    
    Args:
        grouping_result: Result from create_event_groups()
        event_id: The event_id to search for
        
    Returns:
        Event dictionary if found, None otherwise
    """
    for group in grouping_result.get('groups', []):
        for event in group.get('events', []):
            if event.get('event_id') == event_id:
                return event
    
    return None


def get_event_by_headline_id(grouping_result: Dict[str, Any], headline_id: str) -> Optional[Dict[str, Any]]:
    """
    Find an event by its original headline_id.
    
    Args:
        grouping_result: Result from create_event_groups()
        headline_id: The headline_id to search for
        
    Returns:
        Event dictionary if found, None otherwise
    """
    for group in grouping_result.get('groups', []):
        for event in group.get('events', []):
            if event.get('headline_id') == headline_id:
                return event
    
    return None


def create_event_lookup_table(grouping_result: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Create a lookup table for fast event access by event_id.
    
    Args:
        grouping_result: Result from create_event_groups()
        
    Returns:
        Dictionary mapping event_id to event data
    """
    lookup_table = {}
    
    for group in grouping_result.get('groups', []):
        for event in group.get('events', []):
            event_id = event.get('event_id')
            if event_id:
                lookup_table[event_id] = event
    
    return lookup_table


def get_events_with_group_info(grouping_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get all events with additional group information attached.
    
    Args:
        grouping_result: Result from create_event_groups()
        
    Returns:
        List of events with group_id and group_size added
    """
    events_with_group_info = []
    
    for group in grouping_result.get('groups', []):
        group_id = group.get('group_id')
        group_size = group.get('summary', {}).get('size', len(group.get('events', [])))
        
        for event in group.get('events', []):
            event_with_info = event.copy()
            event_with_info['group_id'] = group_id
            event_with_info['group_size'] = group_size
            event_with_info['is_clustered'] = group_size > 1
            events_with_group_info.append(event_with_info)
    
    return events_with_group_info


def print_event_summary(grouping_result: Dict[str, Any]) -> None:
    """
    Print a summary of all events and their grouping status.
    
    Args:
        grouping_result: Result from create_event_groups()
    """
    metadata = grouping_result.get('metadata', {})
    
    print("Event Grouping Summary")
    print("=" * 50)
    print(f"Total Headlines: {metadata.get('total_headlines', 0)}")
    print(f"Total Events: {metadata.get('total_events', 0)}")
    print(f"Total Groups: {metadata.get('total_groups', 0)}")
    
    events_by_type = extract_events_by_type(grouping_result)
    print(f"Clustered Events: {len(events_by_type['clustered'])}")
    print(f"Singleton Events: {len(events_by_type['singleton'])}")
    
    print(f"\nAll Events:")
    print("-" * 50)
    
    events_with_info = get_events_with_group_info(grouping_result)
    
    for i, event in enumerate(events_with_info, 1):
        print(f"{i:3}. Event ID: {event['event_id']}")
        print(f"     Headline: {event.get('text', 'N/A')}")
        print(f"     Group: {event['group_id']} (size: {event['group_size']})")
        print(f"     Type: {event.get('event_type', 'unknown')}")
        print(f"     Clustered: {'Yes' if event['is_clustered'] else 'No'}")
        print()
