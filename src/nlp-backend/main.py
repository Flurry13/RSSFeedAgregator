from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn
from datetime import datetime
import json
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import logging
import re
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="RSS Event Grouping API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the sentence transformer model for semantic similarity
model = SentenceTransformer('all-MiniLM-L6-v2')

# Fresh Simple Clustering System (Target: 70-90% Accuracy)
class FreshSimpleClustering:
    """
    Fresh simple clustering approach focused on pure semantic similarity
    """
    
    def __init__(self):
        # Aggressive parameters for high accuracy
        self.min_samples = 2
        self.metric = 'cosine'
    
    def fresh_clustering(self, embeddings: np.ndarray, similarity_threshold: float, 
                        min_cluster_size: int) -> List[int]:
        """
        Fresh simple clustering with aggressive thresholds
        """
        # Calculate cosine similarity
        similarity_matrix = cosine_similarity(embeddings)
        
        # Use much more aggressive similarity threshold
        # Convert similarity threshold to distance (more lenient)
        if similarity_threshold > 0.5:
            # For high similarity thresholds, use more lenient distance
            eps = 1 - (similarity_threshold * 0.7)  # Make it more lenient
        else:
            # For low similarity thresholds, use very lenient distance
            eps = 1 - (similarity_threshold * 0.5)  # Even more lenient
        
        # Ensure eps is not too small
        eps = max(eps, 0.1)  # Minimum distance threshold
        
        # Convert similarity to distance
        distance_matrix = 1 - similarity_matrix
        
        # Use DBSCAN with aggressive parameters
        clustering = DBSCAN(
            eps=eps,
            min_samples=self.min_samples,
            metric='precomputed'
        )
        
        # Perform clustering
        cluster_labels = clustering.fit_predict(distance_matrix)
        
        # Post-process to ensure minimum cluster size
        for i, label in enumerate(cluster_labels):
            if label != -1:
                cluster_size = sum(1 for l in cluster_labels if l == label)
                if cluster_size < min_cluster_size:
                    cluster_labels[i] = -1
        
        return cluster_labels

# Initialize fresh simple clustering
fresh_clustering = FreshSimpleClustering()

class Headline(BaseModel):
    title: str
    source: str
    pubDate: str
    topics: Optional[List[str]] = []
    scores: Optional[List[float]] = []

class EventGroup(BaseModel):
    event_id: str
    event_name: str
    headlines: List[Headline]
    similarity_score: float
    event_keywords: List[str]
    event_type: str
    top_entities: List[str]
    locations: List[str]
    created_at: str

class GroupingRequest(BaseModel):
    headlines: List[Headline]
    similarity_threshold: float = 0.4  # Much more lenient threshold
    min_cluster_size: int = 2

class GroupingResponse(BaseModel):
    event_groups: List[EventGroup]
    ungrouped_headlines: List[Headline]
    total_groups: int
    total_grouped: int
    total_ungrouped: int

def extract_event_keywords(headlines: List[str]) -> List[str]:
    """
    Extract common keywords that represent the event
    """
    from collections import Counter
    
    # Combine all headlines
    all_text = " ".join(headlines).lower()
    
    # Remove common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
        'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
    }
    
    # Extract words and filter
    words = re.findall(r'\b\w+\b', all_text)
    words = [word for word in words if word not in stop_words and len(word) > 2]
    
    # Get most common words
    word_counts = Counter(words)
    return [word for word, count in word_counts.most_common(5)]

def generate_event_name(headlines: List[str], keywords: List[str]) -> str:
    """
    Generate a descriptive name for the event group
    """
    if not headlines:
        return "Unknown Event"
    
    # Use the first headline as base and enhance with keywords
    first_headline = headlines[0]
    
    # If we have keywords, use them to create a more descriptive name
    if keywords:
        keyword_str = ", ".join(keywords[:3])
        return f"Event: {keyword_str}"
    
    # Otherwise, use a truncated version of the first headline
    return f"Event: {first_headline[:50]}..."

@app.post("/group-headlines", response_model=GroupingResponse)
async def group_headlines_by_events(request: GroupingRequest):
    """
    Group headlines by events using fresh simple clustering (Target: 70-90% accuracy)
    """
    try:
        if not request.headlines:
            return GroupingResponse(
                event_groups=[],
                ungrouped_headlines=[],
                total_groups=0,
                total_grouped=0,
                total_ungrouped=0
            )
        
        # Extract headline texts
        headline_texts = [headline.title for headline in request.headlines]
        
        logger.info(f"Generating embeddings for {len(headline_texts)} headlines")
        
        # Generate embeddings for all headlines
        embeddings = model.encode(headline_texts)
        
        # Perform fresh simple clustering (no entity interference)
        cluster_labels = fresh_clustering.fresh_clustering(
            embeddings, request.similarity_threshold, request.min_cluster_size
        )
        
        # Group headlines by cluster
        event_groups = []
        used_indices = set()
        
        unique_clusters = set(cluster_labels)
        unique_clusters.discard(-1)  # Remove noise points
        
        for cluster_id in unique_clusters:
            cluster_indices = [i for i, label in enumerate(cluster_labels) if label == cluster_id]
            
            if len(cluster_indices) >= request.min_cluster_size:
                cluster_headlines = [request.headlines[i] for i in cluster_indices]
                cluster_texts = [headline_texts[i] for i in cluster_indices]
                
                # Calculate average similarity within the cluster
                cluster_embeddings = embeddings[cluster_indices]
                similarities = cosine_similarity(cluster_embeddings)
                avg_similarity = np.mean(similarities[np.triu_indices_from(similarities, k=1)])
                
                # Extract event keywords
                event_keywords = extract_event_keywords(cluster_texts)
                
                # Generate event name
                event_name = generate_event_name(cluster_texts, event_keywords)
                
                # Simple event type classification
                event_type = classify_event_type_simple(cluster_texts)
                
                # Simple entity extraction (no complex processing)
                top_entities = extract_entities_simple(cluster_texts)
                
                # Extract locations (simplified)
                locations = extract_locations_simple(cluster_texts)
                
                event_group = EventGroup(
                    event_id=f"event_{cluster_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    event_name=event_name,
                    headlines=cluster_headlines,
                    similarity_score=float(avg_similarity),
                    event_keywords=event_keywords,
                    event_type=event_type,
                    top_entities=top_entities[:5],  # Limit to top 5 entities
                    locations=locations,
                    created_at=datetime.now().isoformat()
                )
                
                event_groups.append(event_group)
                used_indices.update(cluster_indices)
        
        # Get ungrouped headlines
        ungrouped_headlines = [
            headline for i, headline in enumerate(request.headlines)
            if i not in used_indices
        ]
        
        return GroupingResponse(
            event_groups=event_groups,
            ungrouped_headlines=ungrouped_headlines,
            total_groups=len(event_groups),
            total_grouped=len(used_indices),
            total_ungrouped=len(ungrouped_headlines)
        )
        
    except Exception as e:
        logger.error(f"Error in group_headlines_by_events: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def extract_entities_simple(headlines: List[str]) -> List[str]:
    """
    Simple entity extraction without complex processing
    """
    entities = []
    combined_text = " ".join(headlines).lower()
    
    # Extract basic entities using regex patterns
    person_pattern = r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b'
    persons = re.findall(person_pattern, combined_text)
    entities.extend(persons)
    
    # Extract company names
    company_patterns = [
        r'\b(Apple|Google|Microsoft|Tesla|Amazon|Facebook|Twitter)\b',
        r'\b(Biden|Trump|Obama|Clinton)\b',
        r'\b(Manchester United|Liverpool|Arsenal|Chelsea)\b',
        r'\b(Dow Jones|NASDAQ|S&P 500)\b',
        r'\b(Oscars|Grammys|Academy Awards)\b',
        r'\b(United Nations|NATO|UN)\b'
    ]
    
    for pattern in company_patterns:
        matches = re.findall(pattern, combined_text)
        entities.extend(matches)
    
    return list(set(entities))  # Remove duplicates

def classify_event_type_simple(headlines: List[str]) -> str:
    """
    Simple event type classification based on keywords
    """
    combined_text = " ".join(headlines).lower()
    
    # Define event type patterns
    event_patterns = {
        'politics': ['election', 'vote', 'campaign', 'politician', 'government', 'president', 'minister'],
        'conflict': ['attack', 'bombing', 'shooting', 'war', 'conflict', 'violence', 'terror'],
        'economy': ['market', 'economy', 'trade', 'business', 'financial', 'stock', 'currency'],
        'disaster': ['disaster', 'accident', 'earthquake', 'flood', 'fire', 'storm', 'hurricane'],
        'technology': ['launch', 'release', 'technology', 'app', 'software', 'digital'],
        'sports': ['game', 'match', 'tournament', 'championship', 'player', 'team', 'league'],
        'entertainment': ['movie', 'film', 'celebrity', 'award', 'concert', 'show']
    }
    
    # Count matches for each event type
    scores = {}
    for event_type, keywords in event_patterns.items():
        score = sum(1 for keyword in keywords if keyword in combined_text)
        scores[event_type] = score
    
    # Return the event type with the highest score, or 'general' if no matches
    if any(scores.values()):
        return max(scores, key=scores.get)
    else:
        return 'general'

def extract_locations_simple(headlines: List[str]) -> List[str]:
    """
    Simple location extraction
    """
    locations = []
    combined_text = " ".join(headlines).lower()
    
    # Common location patterns
    location_keywords = [
        'california', 'new york', 'washington', 'london', 'paris', 'tokyo', 'beijing',
        'middle east', 'europe', 'asia', 'africa', 'america', 'united states', 'uk'
    ]
    
    for location in location_keywords:
        if location in combined_text:
            locations.append(location.title())
    
    return locations[:3]  # Return top 3 locations

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/model-info")
async def model_info():
    """Get information about the loaded model"""
    return {
        "model_name": "all-MiniLM-L6-v2",
        "embedding_dimension": 384,
        "max_sequence_length": 256,
        "model_type": "sentence-transformers"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
