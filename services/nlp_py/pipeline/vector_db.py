#!/usr/bin/env python3
"""
Vector Database Module
======================

Provides vector storage and retrieval functionality for the RSS feed processing pipeline.
Supports multiple backends including in-memory, file-based, and external vector databases.
Includes similarity search, clustering, and efficient storage operations.
"""

import logging
import numpy as np
import json
import pickle
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
import time
from datetime import datetime
import uuid
from dataclasses import dataclass, asdict
import warnings

try:
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.cluster import DBSCAN
except ImportError as e:
    logging.error(f"Required dependencies not found: {e}")
    logging.error("Install with: pip install scikit-learn")
    raise

logger = logging.getLogger(__name__)

@dataclass
class VectorRecord:
    """Represents a vector record in the database."""
    id: str
    text: str
    embedding: np.ndarray
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        record_dict = asdict(self)
        record_dict['embedding'] = self.embedding.tolist()
        return record_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VectorRecord':
        """Create from dictionary."""
        data['embedding'] = np.array(data['embedding'])
        return cls(**data)

class VectorDatabase:
    """
    High-performance vector database for storing and retrieving text embeddings.
    
    Features:
    - Efficient similarity search
    - Automatic clustering
    - Metadata storage and filtering
    - Multiple storage backends
    - Batch operations
    """
    
    def __init__(self, 
                 storage_path: Optional[str] = None,
                 max_vectors: Optional[int] = None,
                 similarity_threshold: float = 0.7,
                 enable_clustering: bool = True):
        """
        Initialize the vector database.
        
        Args:
            storage_path: Path for persistent storage
            max_vectors: Maximum number of vectors to store
            similarity_threshold: Threshold for similarity search
            enable_clustering: Whether to enable automatic clustering
        """
        self.storage_path = Path(storage_path) if storage_path else None
        self.max_vectors = max_vectors
        self.similarity_threshold = similarity_threshold
        self.enable_clustering = enable_clustering
        
        # Storage
        self.vectors: Dict[str, VectorRecord] = {}
        self.embeddings_matrix: Optional[np.ndarray] = None
        self.vector_ids: List[str] = []
        
        # Clustering
        self.clusters: Dict[str, List[str]] = {}
        self.cluster_centroids: Dict[str, np.ndarray] = {}
        
        # Statistics
        self.stats = {
            "total_vectors": 0,
            "total_searches": 0,
            "total_clusters": 0,
            "storage_size_bytes": 0,
            "last_updated": None
        }
        
        # Load existing data if storage path provided
        if self.storage_path:
            self._load_database()
        
        logger.info(f"Vector database initialized with {len(self.vectors)} vectors")
    
    def add_vector(self, 
                   text: str, 
                   embedding: np.ndarray, 
                   metadata: Optional[Dict[str, Any]] = None,
                   vector_id: Optional[str] = None) -> str:
        """
        Add a vector to the database.
        
        Args:
            text: Original text
            embedding: Vector embedding
            metadata: Additional metadata
            vector_id: Custom vector ID (auto-generated if None)
            
        Returns:
            Vector ID
        """
        # Check capacity
        if self.max_vectors and len(self.vectors) >= self.max_vectors:
            raise ValueError(f"Database at capacity ({self.max_vectors} vectors)")
        
        # Generate ID if not provided
        if vector_id is None:
            vector_id = str(uuid.uuid4())
        
        # Create record
        now = datetime.now().isoformat()
        record = VectorRecord(
            id=vector_id,
            text=text,
            embedding=embedding,
            metadata=metadata or {},
            created_at=now,
            updated_at=now
        )
        
        # Store
        self.vectors[vector_id] = record
        self.vector_ids.append(vector_id)
        
        # Update embeddings matrix
        self._update_embeddings_matrix()
        
        # Update clustering if enabled
        if self.enable_clustering:
            self._update_clustering()
        
        # Update statistics
        self.stats["total_vectors"] = len(self.vectors)
        self.stats["last_updated"] = now
        
        logger.info(f"Added vector {vector_id} to database")
        
        # Persist if storage path provided
        if self.storage_path:
            self._save_database()
        
        return vector_id
    
    def add_vectors_batch(self, 
                          texts: List[str], 
                          embeddings: np.ndarray,
                          metadata_list: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """
        Add multiple vectors in batch.
        
        Args:
            texts: List of texts
            embeddings: Array of embeddings
            metadata_list: List of metadata dictionaries
            
        Returns:
            List of vector IDs
        """
        if len(texts) != len(embeddings):
            raise ValueError("Texts and embeddings must have same length")
        
        if metadata_list and len(metadata_list) != len(texts):
            raise ValueError("Metadata list must have same length as texts")
        
        vector_ids = []
        
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            metadata = metadata_list[i] if metadata_list else None
            vector_id = self.add_vector(text, embedding, metadata)
            vector_ids.append(vector_id)
        
        logger.info(f"Added {len(vector_ids)} vectors in batch")
        return vector_ids
    
    def get_vector(self, vector_id: str) -> Optional[VectorRecord]:
        """Retrieve a vector by ID."""
        return self.vectors.get(vector_id)
    
    def search_similar(self, 
                       query_embedding: np.ndarray,
                       top_k: int = 10,
                       threshold: Optional[float] = None,
                       filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.
        
        Args:
            query_embedding: Query embedding
            top_k: Number of top results
            threshold: Similarity threshold (uses default if None)
            filter_metadata: Metadata filter criteria
            
        Returns:
            List of search results with similarity scores
        """
        if not self.vectors:
            return []
        
        threshold = threshold or self.similarity_threshold
        
        # Ensure query embedding is 2D
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        # Compute similarities
        similarities = cosine_similarity(query_embedding, self.embeddings_matrix)[0]
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            vector_id = self.vector_ids[idx]
            record = self.vectors[vector_id]
            similarity = similarities[idx]
            
            # Apply threshold
            if similarity < threshold:
                continue
            
            # Apply metadata filter
            if filter_metadata and not self._matches_filter(record.metadata, filter_metadata):
                continue
            
            results.append({
                "vector_id": vector_id,
                "text": record.text,
                "similarity": float(similarity),
                "metadata": record.metadata,
                "rank": len(results) + 1
            })
        
        # Update statistics
        self.stats["total_searches"] += 1
        
        logger.info(f"Search returned {len(results)} results")
        return results
    
    def find_duplicates(self, 
                        similarity_threshold: float = 0.95,
                        min_group_size: int = 2) -> List[List[str]]:
        """
        Find duplicate or near-duplicate vectors.
        
        Args:
            similarity_threshold: Threshold for considering vectors similar
            min_group_size: Minimum size for duplicate groups
            
        Returns:
            List of duplicate groups (each group is a list of vector IDs)
        """
        if not self.vectors:
            return []
        
        # Compute similarity matrix
        similarity_matrix = cosine_similarity(self.embeddings_matrix)
        
        # Find duplicates using clustering
        clustering = DBSCAN(
            eps=1 - similarity_threshold,
            min_samples=min_group_size,
            metric='precomputed'
        )
        
        # Convert similarity to distance
        distance_matrix = 1 - similarity_matrix
        cluster_labels = clustering.fit_predict(distance_matrix)
        
        # Group by cluster
        duplicate_groups = {}
        for i, label in enumerate(cluster_labels):
            if label >= 0:  # Skip noise points
                if label not in duplicate_groups:
                    duplicate_groups[label] = []
                duplicate_groups[label].append(self.vector_ids[i])
        
        # Filter by minimum group size
        result = [group for group in duplicate_groups.values() if len(group) >= min_group_size]
        
        logger.info(f"Found {len(result)} duplicate groups")
        return result
    
    def get_clusters(self) -> Dict[str, List[str]]:
        """Get current clustering information."""
        return self.clusters.copy()
    
    def get_cluster_centroid(self, cluster_id: str) -> Optional[np.ndarray]:
        """Get centroid of a specific cluster."""
        return self.cluster_centroids.get(cluster_id)
    
    def remove_vector(self, vector_id: str) -> bool:
        """
        Remove a vector from the database.
        
        Args:
            vector_id: ID of vector to remove
            
        Returns:
            True if vector was removed, False if not found
        """
        if vector_id not in self.vectors:
            return False
        
        # Remove from storage
        del self.vectors[vector_id]
        self.vector_ids.remove(vector_id)
        
        # Update embeddings matrix
        self._update_embeddings_matrix()
        
        # Update clustering
        if self.enable_clustering:
            self._update_clustering()
        
        # Update statistics
        self.stats["total_vectors"] = len(self.vectors)
        self.stats["last_updated"] = datetime.now().isoformat()
        
        logger.info(f"Removed vector {vector_id}")
        
        # Persist changes
        if self.storage_path:
            self._save_database()
        
        return True
    
    def clear_database(self):
        """Clear all vectors from the database."""
        self.vectors.clear()
        self.vector_ids.clear()
        self.embeddings_matrix = None
        self.clusters.clear()
        self.cluster_centroids.clear()
        
        # Update statistics
        self.stats["total_vectors"] = 0
        self.stats["total_clusters"] = 0
        self.stats["last_updated"] = datetime.now().isoformat()
        
        logger.info("Database cleared")
        
        # Persist changes
        if self.storage_path:
            self._save_database()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        stats = self.stats.copy()
        stats["storage_size_bytes"] = self._calculate_storage_size()
        return stats
    
    def export_vectors(self, 
                       filepath: str, 
                       format: str = "json",
                       include_embeddings: bool = True) -> bool:
        """
        Export vectors to file.
        
        Args:
            filepath: Path to export file
            format: Export format ('json', 'pickle', 'csv')
            include_embeddings: Whether to include embedding vectors
            
        Returns:
            True if export successful
        """
        filepath = Path(filepath)
        
        try:
            if format == "json":
                export_data = {
                    "vectors": {},
                    "metadata": {
                        "exported_at": datetime.now().isoformat(),
                        "total_vectors": len(self.vectors),
                        "database_stats": self.stats
                    }
                }
                
                for vector_id, record in self.vectors.items():
                    export_data["vectors"][vector_id] = record.to_dict()
                    if not include_embeddings:
                        export_data["vectors"][vector_id]["embedding"] = None
                
                with open(filepath, 'w') as f:
                    json.dump(export_data, f, indent=2)
                
            elif format == "pickle":
                export_data = {
                    "vectors": self.vectors,
                    "stats": self.stats,
                    "exported_at": datetime.now().isoformat()
                }
                
                with open(filepath, 'wb') as f:
                    pickle.dump(export_data, f)
                
            elif format == "csv":
                import pandas as pd
                
                # Create DataFrame
                data = []
                for vector_id, record in self.vectors.items():
                    row = {
                        "id": vector_id,
                        "text": record.text,
                        "created_at": record.created_at,
                        "updated_at": record.updated_at
                    }
                    row.update(record.metadata)
                    data.append(row)
                
                df = pd.DataFrame(data)
                df.to_csv(filepath, index=False)
                
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            logger.info(f"Exported {len(self.vectors)} vectors to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
    
    def _update_embeddings_matrix(self):
        """Update the embeddings matrix for efficient similarity computation."""
        if not self.vectors:
            self.embeddings_matrix = None
            return
        
        # Extract embeddings in order
        embeddings_list = []
        for vector_id in self.vector_ids:
            record = self.vectors[vector_id]
            embeddings_list.append(record.embedding)
        
        self.embeddings_matrix = np.vstack(embeddings_list)
        logger.debug(f"Updated embeddings matrix: {self.embeddings_matrix.shape}")
    
    def _update_clustering(self):
        """Update clustering of vectors."""
        if not self.vectors or len(self.vectors) < 2:
            self.clusters.clear()
            self.cluster_centroids.clear()
            self.stats["total_clusters"] = 0
            return
        
        try:
            # Perform clustering
            clustering = DBSCAN(
                eps=1 - self.similarity_threshold,
                min_samples=2,
                metric='cosine'
            )
            
            cluster_labels = clustering.fit_predict(self.embeddings_matrix)
            
            # Group vectors by cluster
            self.clusters.clear()
            self.cluster_centroids.clear()
            
            for i, label in enumerate(cluster_labels):
                if label >= 0:  # Skip noise points
                    cluster_id = f"cluster_{label}"
                    if cluster_id not in self.clusters:
                        self.clusters[cluster_id] = []
                    self.clusters[cluster_id].append(self.vector_ids[i])
            
            # Compute centroids
            for cluster_id, vector_ids in self.clusters.items():
                cluster_embeddings = [self.vectors[vid].embedding for vid in vector_ids]
                centroid = np.mean(cluster_embeddings, axis=0)
                self.cluster_centroids[cluster_id] = centroid
            
            self.stats["total_clusters"] = len(self.clusters)
            logger.debug(f"Updated clustering: {len(self.clusters)} clusters")
            
        except Exception as e:
            logger.warning(f"Clustering update failed: {e}")
    
    def _matches_filter(self, metadata: Dict[str, Any], filter_criteria: Dict[str, Any]) -> bool:
        """Check if metadata matches filter criteria."""
        for key, value in filter_criteria.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True
    
    def _calculate_storage_size(self) -> int:
        """Calculate approximate storage size in bytes."""
        total_size = 0
        
        # Estimate size of vectors
        for record in self.vectors.values():
            total_size += len(record.text.encode('utf-8'))
            total_size += record.embedding.nbytes
            total_size += len(json.dumps(record.metadata))
        
        return total_size
    
    def _save_database(self):
        """Save database to persistent storage."""
        if not self.storage_path:
            return
        
        try:
            # Create storage directory
            self.storage_path.mkdir(parents=True, exist_ok=True)
            
            # Save vectors
            vectors_file = self.storage_path / "vectors.pkl"
            with open(vectors_file, 'wb') as f:
                pickle.dump(self.vectors, f)
            
            # Save metadata
            metadata_file = self.storage_path / "metadata.json"
            metadata = {
                "vector_ids": self.vector_ids,
                "stats": self.stats,
                "clusters": self.clusters,
                "cluster_centroids": {k: v.tolist() for k, v in self.cluster_centroids.items()},
                "saved_at": datetime.now().isoformat()
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.debug(f"Database saved to {self.storage_path}")
            
        except Exception as e:
            logger.error(f"Failed to save database: {e}")
    
    def _load_database(self):
        """Load database from persistent storage."""
        if not self.storage_path:
            return
        
        try:
            # Load vectors
            vectors_file = self.storage_path / "vectors.pkl"
            if vectors_file.exists():
                with open(vectors_file, 'rb') as f:
                    self.vectors = pickle.load(f)
            
            # Load metadata
            metadata_file = self.storage_path / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                self.vector_ids = metadata.get("vector_ids", [])
                self.stats = metadata.get("stats", self.stats)
                self.clusters = metadata.get("clusters", {})
                
                # Restore cluster centroids
                centroids_data = metadata.get("cluster_centroids", {})
                self.cluster_centroids = {
                    k: np.array(v) for k, v in centroids_data.items()
                }
            
            # Update embeddings matrix
            self._update_embeddings_matrix()
            
            logger.info(f"Database loaded from {self.storage_path}")
            
        except Exception as e:
            logger.error(f"Failed to load database: {e}")


def create_vector_db(storage_path: Optional[str] = None, **kwargs) -> VectorDatabase:
    """
    Factory function to create a VectorDatabase instance.
    
    Args:
        storage_path: Path for persistent storage
        **kwargs: Additional arguments for VectorDatabase
        
    Returns:
        Configured VectorDatabase instance
    """
    return VectorDatabase(storage_path=storage_path, **kwargs)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Create database
    db = create_vector_db(storage_path="./vector_db_example")
    
    # Example embeddings (random for demo)
    texts = [
        "The quick brown fox jumps over the lazy dog",
        "A quick brown dog jumps over the lazy fox",
        "The weather is sunny today",
        "It's raining heavily outside",
        "Machine learning is fascinating",
        "Artificial intelligence advances rapidly"
    ]
    
    # Generate random embeddings (384-dimensional like all-MiniLM-L6-v2)
    embeddings = np.random.rand(len(texts), 384)
    
    # Add vectors
    vector_ids = db.add_vectors_batch(texts, embeddings)
    print(f"Added {len(vector_ids)} vectors to database")
    
    # Search for similar vectors
    query_embedding = np.random.rand(384)
    results = db.search_similar(query_embedding, top_k=3)
    
    print(f"\nSearch results:")
    for result in results:
        print(f"  {result['rank']}. {result['text']} (similarity: {result['similarity']:.3f})")
    
    # Get statistics
    stats = db.get_statistics()
    print(f"\nDatabase statistics: {stats}")
    
    # Export vectors
    db.export_vectors("vectors_export.json", format="json")
    print(f"\nVectors exported to vectors_export.json") 