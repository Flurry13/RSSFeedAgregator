"""
Event Extraction Module
=======================

Extract structured events from news headlines and content.
This module identifies entities, relationships, and event types for clustering.
"""

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
import warnings

import spacy
from spacy.tokens import Token

# Configure logging
logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", message=".*Skipping token.*")


class EventExtractor:
    """Extract structured events from news text."""
    
    def __init__(self, model_name: str = "en_core_web_sm"):
        """Initialize the event extractor with spaCy model."""
        self.model_name = model_name
        self.nlp = None
        self._load_model()
        
        # Event type keywords for classification
        self.event_type_keywords = {
            "political": ["election", "vote", "government", "policy", "parliament", "congress", "minister", "president"],
            "economic": ["stock", "market", "economy", "trade", "GDP", "inflation", "recession", "bank", "financial"],
            "social": ["protest", "demonstration", "rally", "social", "community", "rights", "civil", "movement"],
            "environmental": ["climate", "environment", "pollution", "carbon", "emissions", "renewable", "green"],
            "technological": ["technology", "tech", "AI", "artificial intelligence", "software", "hardware", "innovation"],
            "other": []
        }
    
    def _load_model(self):
        """Load spaCy model with error handling."""
        try:
            self.nlp = spacy.load(self.model_name)
            logger.info(f"Loaded spaCy model: {self.model_name}")
        except OSError:
            logger.error(f"spaCy model '{self.model_name}' not found. Install with: python -m spacy download {self.model_name}")
            raise
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities from text using spaCy NER."""
        if not self.nlp:
            raise RuntimeError("spaCy model not loaded")
        
        doc = self.nlp(text)
        entities = []
        
        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
                "confidence": 1.0
            })
        
        return entities
    
    def extract_relationships(self, text: str) -> List[Dict[str, Any]]:
        """Extract subject-predicate-object relationships using dependency parsing."""
        if not self.nlp:
            raise RuntimeError("spaCy model not loaded")
        
        doc = self.nlp(text)
        relationships = []
        
        # Find main verbs and their subjects/objects
        for token in doc:
            if token.pos_ == "VERB" and token.dep_ in ["ROOT", "ccomp", "xcomp"]:
                relationship = self._extract_verb_relationship(token)
                if relationship:
                    relationships.append(relationship)
        
        return relationships
    
    def _extract_verb_relationship(self, verb_token: Token) -> Optional[Dict[str, Any]]:
        """Extract relationship for a specific verb token."""
        subject = None
        obj = None
        
        # Find subject
        for child in verb_token.children:
            if child.dep_ in ["nsubj", "nsubjpass"]:
                subject = self._get_full_phrase(child)
                break
        
        # Find object
        for child in verb_token.children:
            if child.dep_ in ["dobj", "pobj", "attr"]:
                obj = self._get_full_phrase(child)
                break
            elif child.dep_ == "prep":
                for grandchild in child.children:
                    if grandchild.dep_ == "pobj":
                        obj = self._get_full_phrase(grandchild)
                        break
        
        if subject and obj:
            return {
                "subject": subject,
                "predicate": verb_token.lemma_,
                "object": obj,
                "confidence": 0.8
            }
        
        return None
    
    def _get_full_phrase(self, token: Token) -> str:
        """Get the full phrase for a token including its modifiers."""
        phrase_tokens = list(token.subtree)
        phrase_tokens.sort(key=lambda x: x.i)
        phrase = " ".join([t.text for t in phrase_tokens])
        return phrase.strip()
    
    def classify_event_type(self, text: str, entities: List[Dict[str, Any]]) -> Tuple[str, float]:
        """Classify event type based on text content and entities."""
        text_lower = text.lower()
        
        scores = {}
        
        # Score each event type based on keyword matches
        for event_type, keywords in self.event_type_keywords.items():
            if event_type == "other":
                continue
                
            score = sum(1 for keyword in keywords if keyword in text_lower)
            scores[event_type] = score
        
        # Get best match
        if not scores or max(scores.values()) == 0:
            return "other", 0.1
        
        best_type = max(scores, key=scores.get)
        confidence = min(scores[best_type] / 3.0, 1.0)
        
        return best_type, confidence
    
    def generate_event_hash(self, subject: str, predicate: str, obj: str) -> str:
        """Generate unique hash for event deduplication."""
        # Normalize components
        subject_norm = re.sub(r'\s+', ' ', subject.lower().strip())
        predicate_norm = re.sub(r'\s+', ' ', predicate.lower().strip())
        obj_norm = re.sub(r'\s+', ' ', obj.lower().strip())
        
        # Create hash input
        hash_input = f"{subject_norm}|{predicate_norm}|{obj_norm}"
        
        # Generate SHA-256 hash
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()[:16]
    
    def extract_events(self, text: str, headline_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Extract complete events from text with all components."""
        if not text or not text.strip():
            return []
        
        try:
            # Extract components
            entities = self.extract_entities(text)
            relationships = self.extract_relationships(text)
            event_type, type_confidence = self.classify_event_type(text, entities)
            
            events = []
            
            if relationships:
                # Create events from relationships
                for rel in relationships:
                    event_hash = self.generate_event_hash(
                        rel["subject"], rel["predicate"], rel["object"]
                    )
                    
                    event = {
                        "event_id": f"evt_{event_hash}",
                        "headline_id": headline_id,
                        "text": text,
                        "subject": rel["subject"],
                        "predicate": rel["predicate"],
                        "object": rel["object"],
                        "event_type": event_type,
                        "type_confidence": type_confidence,
                        "relationship_confidence": rel["confidence"],
                        "entities": entities,
                        "event_hash": event_hash,
                        "extracted_at": datetime.now(timezone.utc).isoformat()
                    }
                    events.append(event)
            else:
                # Create a basic event from the text itself
                event_hash = self.generate_event_hash(text, "mentions", "event")
                
                event = {
                    "event_id": f"evt_{event_hash}",
                    "headline_id": headline_id,
                    "text": text,
                    "subject": text,
                    "predicate": "mentions",
                    "object": "event",
                    "event_type": event_type,
                    "type_confidence": type_confidence,
                    "relationship_confidence": 0.3,
                    "entities": entities,
                    "event_hash": event_hash,
                    "extracted_at": datetime.now(timezone.utc).isoformat()
                }
                events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Error extracting events from text: {e}")
            return []
    
    def extract_events_batch(self, texts: List[str], headline_ids: Optional[List[str]] = None) -> List[List[Dict[str, Any]]]:
        """Extract events from multiple texts efficiently."""
        if headline_ids and len(headline_ids) != len(texts):
            raise ValueError("Number of headline_ids must match number of texts")
        
        results = []
        for i, text in enumerate(texts):
            headline_id = headline_ids[i] if headline_ids else None
            events = self.extract_events(text, headline_id)
            results.append(events)
        
        return results


# Default extractor instance
_default_extractor = None


def get_default_extractor() -> EventExtractor:
    """Get or create the default event extractor instance."""
    global _default_extractor
    if _default_extractor is None:
        _default_extractor = EventExtractor()
    return _default_extractor


# Convenience functions
def extract_entities(text: str) -> List[Dict[str, Any]]:
    return get_default_extractor().extract_entities(text)


def extract_relationships(text: str) -> List[Dict[str, Any]]:
    return get_default_extractor().extract_relationships(text)


def classify_event_type(text: str, entities: List[Dict[str, Any]]) -> Tuple[str, float]:
    return get_default_extractor().classify_event_type(text, entities)


def generate_event_hash(subject: str, predicate: str, obj: str) -> str:
    return get_default_extractor().generate_event_hash(subject, predicate, obj)


def extract_events(text: str, headline_id: Optional[str] = None) -> List[Dict[str, Any]]:
    return get_default_extractor().extract_events(text, headline_id)


def extract_events_batch(texts: List[str], headline_ids: Optional[List[str]] = None) -> List[List[Dict[str, Any]]]:
    return get_default_extractor().extract_events_batch(texts, headline_ids)
