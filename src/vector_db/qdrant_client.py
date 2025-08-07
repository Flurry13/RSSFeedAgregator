from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from typing import List, Dict, Optional, Tuple
import numpy as np
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class NewsVectorDB:
    def __init__(self, host: str = "localhost", port: int = 6333, mock_mode: bool = False):
        """Initialize Qdrant client for news vector storage"""
        self.mock_mode = mock_mode
        self.collection_name = "news_headlines"
        self.vector_size = 384  # MiniLM embedding dimension
        
        if not mock_mode:
            try:
                self.client = QdrantClient(host=host, port=port)
                self._ensure_collection_exists()
            except Exception as e:
                logger.warning(f"Could not connect to Qdrant: {e}")
                logger.info("Falling back to mock mode")
                self.mock_mode = True
        
        if self.mock_mode:
            self.mock_data = []
            logger.info("Running in mock mode - data will be stored in memory")
    
    def _ensure_collection_exists(self):
        """Create the collection if it doesn't exist"""
        if self.mock_mode:
            return
            
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {self.collection_name}")
            else:
                logger.info(f"Collection {self.collection_name} already exists")
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise
    
    def store_headline(
        self,
        headline: str,
        embedding: List[float],
        source: str,
        region: str,
        language: str,
        topic: str,
        sentiment: Optional[str] = None,
        bias_score: Optional[float] = None,
        timestamp: Optional[datetime] = None
    ) -> str:
        """Store a headline with its embedding and metadata"""
        try:
            point_id = str(uuid.uuid4())
            
            if self.mock_mode:
                # Store in memory for mock mode
                self.mock_data.append({
                    "id": point_id,
                    "vector": embedding,
                    "payload": {
                        "headline": headline,
                        "source": source,
                        "region": region,
                        "language": language,
                        "topic": topic,
                        "sentiment": sentiment,
                        "bias_score": bias_score,
                        "timestamp": timestamp.isoformat() if timestamp else datetime.now().isoformat(),
                        "created_at": datetime.now().isoformat()
                    }
                })
                logger.info(f"Stored headline in mock mode: {headline[:50]}...")
                return point_id
            
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "headline": headline,
                    "source": source,
                    "region": region,
                    "language": language,
                    "topic": topic,
                    "sentiment": sentiment,
                    "bias_score": bias_score,
                    "timestamp": timestamp.isoformat() if timestamp else datetime.now().isoformat(),
                    "created_at": datetime.now().isoformat()
                }
            )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"Stored headline: {headline[:50]}...")
            return point_id
            
        except Exception as e:
            logger.error(f"Error storing headline: {e}")
            raise
    
    def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 10,
        score_threshold: float = 0.7,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """Search for similar headlines"""
        try:
            if self.mock_mode:
                # Simple cosine similarity in mock mode
                results = []
                for item in self.mock_data:
                    # Apply filters if provided
                    if filters:
                        skip = False
                        for key, value in filters.items():
                            if item["payload"].get(key) != value:
                                skip = True
                                break
                        if skip:
                            continue
                    
                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(query_embedding, item["vector"])
                    
                    if similarity >= score_threshold:
                        results.append({
                            "id": item["id"],
                            "score": similarity,
                            "headline": item["payload"]["headline"],
                            "source": item["payload"]["source"],
                            "region": item["payload"]["region"],
                            "topic": item["payload"]["topic"],
                            "timestamp": item["payload"]["timestamp"]
                        })
                
                # Sort by similarity and limit
                results.sort(key=lambda x: x["score"], reverse=True)
                return results[:limit]
            
            search_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
                search_filter = Filter(must=conditions)
            
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=search_filter
            )
            
            return [
                {
                    "id": result.id,
                    "score": result.score,
                    "headline": result.payload["headline"],
                    "source": result.payload["source"],
                    "region": result.payload["region"],
                    "topic": result.payload["topic"],
                    "timestamp": result.payload["timestamp"]
                }
                for result in results
            ]
            
        except Exception as e:
            logger.error(f"Error searching similar headlines: {e}")
            raise
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def get_topic_statistics(self, topic: str, region: Optional[str] = None) -> Dict:
        """Get statistics for a specific topic"""
        try:
            if self.mock_mode:
                # Filter mock data
                filtered_data = []
                for item in self.mock_data:
                    if item["payload"]["topic"] == topic:
                        if region is None or item["payload"]["region"] == region:
                            filtered_data.append(item)
                
                # Calculate statistics
                sources = [item["payload"]["source"] for item in filtered_data]
                regions = [item["payload"]["region"] for item in filtered_data]
                sentiments = [item["payload"].get("sentiment") for item in filtered_data if item["payload"].get("sentiment")]
                
                return {
                    "topic": topic,
                    "region": region,
                    "total_count": len(filtered_data),
                    "unique_sources": len(set(sources)),
                    "source_distribution": self._count_occurrences(sources),
                    "region_distribution": self._count_occurrences(regions),
                    "sentiment_distribution": self._count_occurrences(sentiments) if sentiments else {}
                }
            
            filter_conditions = [FieldCondition(key="topic", match=MatchValue(value=topic))]
            if region:
                filter_conditions.append(FieldCondition(key="region", match=MatchValue(value=region)))
            
            search_filter = Filter(must=filter_conditions)
            
            # Get all points for this topic
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=search_filter,
                limit=1000  # Adjust based on your needs
            )[0]
            
            # Calculate statistics
            sources = [point.payload["source"] for point in results]
            regions = [point.payload["region"] for point in results]
            sentiments = [point.payload.get("sentiment") for point in results if point.payload.get("sentiment")]
            
            return {
                "topic": topic,
                "region": region,
                "total_count": len(results),
                "unique_sources": len(set(sources)),
                "source_distribution": self._count_occurrences(sources),
                "region_distribution": self._count_occurrences(regions),
                "sentiment_distribution": self._count_occurrences(sentiments) if sentiments else {}
            }
            
        except Exception as e:
            logger.error(f"Error getting topic statistics: {e}")
            raise
    
    def get_underrepresentation_metrics(self, topic: str) -> Dict:
        """Calculate underrepresentation metrics for a topic"""
        try:
            # Get global stats
            global_stats = self.get_topic_statistics(topic)
            
            # Get Western stats (assuming "western" region)
            western_stats = self.get_topic_statistics(topic, region="western")
            
            # Calculate metrics
            global_count = global_stats["total_count"]
            western_count = western_stats["total_count"]
            
            if global_count == 0:
                return {"error": "No data available for this topic"}
            
            # URI calculation
            uri = (western_count - global_count) / (global_count + 1e-6)
            
            # Lift calculation
            lift = global_count / (western_count + 1e-6)
            
            # Z-score calculation (simplified)
            expected_western = global_count * 0.3  # Assuming 30% of news is Western
            z_score = (western_count - expected_western) / np.sqrt(expected_western * 0.7 + 1e-6)
            
            return {
                "topic": topic,
                "global_count": global_count,
                "western_count": western_count,
                "uri": uri,
                "lift": lift,
                "z_score": z_score,
                "underrepresented": uri < -0.1  # Threshold for underrepresentation
            }
            
        except Exception as e:
            logger.error(f"Error calculating underrepresentation metrics: {e}")
            raise
    
    def _count_occurrences(self, items: List) -> Dict:
        """Helper function to count occurrences in a list"""
        counts = {}
        for item in items:
            counts[item] = counts.get(item, 0) + 1
        return counts
    
    def get_collection_info(self) -> Dict:
        """Get information about the collection"""
        try:
            if self.mock_mode:
                return {
                    "name": f"{self.collection_name}_mock",
                    "vector_size": self.vector_size,
                    "distance": "COSINE",
                    "points_count": len(self.mock_data),
                    "mode": "mock"
                }
            
            info = self.client.get_collection(self.collection_name)
            return {
                "name": info.name,
                "vector_size": info.config.params.vectors.size,
                "distance": info.config.params.vectors.distance,
                "points_count": info.points_count,
                "mode": "qdrant"
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            raise 