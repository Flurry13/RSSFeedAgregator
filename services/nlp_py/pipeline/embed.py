#!/usr/bin/env python3
"""
Text Embedding Module
=====================

Provides comprehensive text embedding functionality using sentence-transformers
for the RSS feed processing pipeline. Includes batch processing, caching,
and multiple embedding models support.
"""

import logging
import numpy as np
from typing import List, Union, Optional, Dict, Any
from pathlib import Path
import pickle
import time
from datetime import datetime
import warnings

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.preprocessing import normalize
except ImportError as e:
    logging.error(f"Required dependencies not found: {e}")
    logging.error("Install with: pip install sentence-transformers scikit-learn")
    raise

logger = logging.getLogger(__name__)

class TextEmbedder:
    """
    High-performance text embedding system using sentence-transformers.
    
    Features:
    - Multiple embedding models support
    - Batch processing with configurable batch sizes
    - L2 normalization for cosine similarity
    - Embedding caching and persistence
    - Memory-efficient processing
    """
    
    def __init__(self, 
                 model_name: str = "all-MiniLM-L6-v2",
                 cache_dir: Optional[str] = None,
                 device: Optional[str] = None,
                 batch_size: int = 128):
        """
        Initialize the text embedder.
        
        Args:
            model_name: Name of the sentence-transformers model
            cache_dir: Directory for caching embeddings
            device: Device to use ('cpu', 'cuda', or None for auto)
            batch_size: Default batch size for processing
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.device = device
        
        # Initialize model
        try:
            logger.info(f"Loading embedding model: {model_name}")
            self.model = SentenceTransformer(model_name, device=device)
            logger.info(f"Model loaded successfully on device: {self.model.device}")
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise
        
        # Create cache directory if specified
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Cache directory: {self.cache_dir}")
        
        # Statistics
        self.stats = {
            "total_texts_processed": 0,
            "total_embeddings_generated": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_processing_time": 0.0
        }
    
    def embed_texts(self, 
                    texts: List[str], 
                    normalize_embeddings: bool = True,
                    batch_size: Optional[int] = None,
                    use_cache: bool = True) -> np.ndarray:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            normalize_embeddings: Whether to L2 normalize embeddings
            batch_size: Batch size for processing (overrides default)
            use_cache: Whether to use embedding cache
            
        Returns:
            numpy array of embeddings with shape (n_texts, embedding_dim)
        """
        if not texts:
            return np.array([])
        
        start_time = time.time()
        batch_size = batch_size or self.batch_size
        
        logger.info(f"Processing {len(texts)} texts with batch size {batch_size}")
        
        # Check cache first if enabled
        if use_cache and self.cache_dir:
            cached_embeddings = self._get_cached_embeddings(texts)
            if cached_embeddings is not None:
                self.stats["cache_hits"] += 1
                logger.info("Using cached embeddings")
                return cached_embeddings
        
        # Generate new embeddings
        try:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=len(texts) > 100,
                convert_to_numpy=True
            )
            
            # Normalize if requested
            if normalize_embeddings:
                embeddings = normalize(embeddings, norm='l2')
                logger.info("Embeddings L2 normalized")
            
            # Cache embeddings if enabled
            if use_cache and self.cache_dir:
                self._cache_embeddings(texts, embeddings)
            
            # Update statistics
            self.stats["total_texts_processed"] += len(texts)
            self.stats["total_embeddings_generated"] += len(texts)
            self.stats["cache_misses"] += 1
            
            processing_time = time.time() - start_time
            self.stats["total_processing_time"] += processing_time
            
            logger.info(f"Generated {len(embeddings)} embeddings in {processing_time:.2f}s")
            logger.info(f"Embedding shape: {embeddings.shape}")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def embed_single_text(self, 
                          text: str, 
                          normalize_embedding: bool = True) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Single text string to embed
            normalize_embedding: Whether to L2 normalize the embedding
            
        Returns:
            numpy array of shape (embedding_dim,)
        """
        embeddings = self.embed_texts([text], normalize_embeddings=normalize_embedding)
        return embeddings[0] if len(embeddings) > 0 else np.array([])
    
    def compute_similarity(self, 
                          embeddings1: np.ndarray, 
                          embeddings2: np.ndarray,
                          metric: str = "cosine") -> np.ndarray:
        """
        Compute similarity between two sets of embeddings.
        
        Args:
            embeddings1: First set of embeddings
            embeddings2: Second set of embeddings
            metric: Similarity metric ('cosine', 'euclidean', 'dot')
            
        Returns:
            Similarity matrix
        """
        if metric == "cosine":
            # For L2 normalized vectors, cosine similarity = dot product
            return np.dot(embeddings1, embeddings2.T)
        elif metric == "euclidean":
            # Compute pairwise Euclidean distances
            from sklearn.metrics.pairwise import euclidean_distances
            return -euclidean_distances(embeddings1, embeddings2)  # Negative for similarity
        elif metric == "dot":
            return np.dot(embeddings1, embeddings2.T)
        else:
            raise ValueError(f"Unsupported metric: {metric}")
    
    def find_most_similar(self, 
                          query_embedding: np.ndarray,
                          candidate_embeddings: np.ndarray,
                          top_k: int = 5,
                          threshold: float = 0.0) -> List[Dict[str, Any]]:
        """
        Find most similar embeddings to a query embedding.
        
        Args:
            query_embedding: Query embedding vector
            candidate_embeddings: Candidate embeddings to search through
            top_k: Number of top results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of dictionaries with index and similarity score
        """
        if len(candidate_embeddings) == 0:
            return []
        
        # Ensure query embedding is 2D
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        # Compute similarities
        similarities = self.compute_similarity(query_embedding, candidate_embeddings)[0]
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            similarity = similarities[idx]
            if similarity >= threshold:
                results.append({
                    "index": int(idx),
                    "similarity": float(similarity),
                    "rank": len(results) + 1
                })
        
        return results
    
    def _get_cache_key(self, texts: List[str]) -> str:
        """Generate cache key for a list of texts."""
        import hashlib
        text_hash = hashlib.md5(''.join(texts).encode()).hexdigest()
        return f"{self.model_name}_{text_hash}.pkl"
    
    def _get_cached_embeddings(self, texts: List[str]) -> Optional[np.ndarray]:
        """Retrieve cached embeddings if available."""
        if not self.cache_dir:
            return None
        
        cache_file = self.cache_dir / self._get_cache_key(texts)
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    if (cached_data.get('model_name') == self.model_name and 
                        cached_data.get('texts') == texts):
                        logger.debug(f"Cache hit: {cache_file}")
                        return cached_data['embeddings']
            except Exception as e:
                logger.warning(f"Failed to load cache file {cache_file}: {e}")
        
        return None
    
    def _cache_embeddings(self, texts: List[str], embeddings: np.ndarray):
        """Cache embeddings for future use."""
        if not self.cache_dir:
            return
        
        cache_file = self.cache_dir / self._get_cache_key(texts)
        try:
            cache_data = {
                'model_name': self.model_name,
                'texts': texts,
                'embeddings': embeddings,
                'cached_at': datetime.now().isoformat()
            }
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            logger.debug(f"Cached embeddings: {cache_file}")
        except Exception as e:
            logger.warning(f"Failed to cache embeddings: {e}")
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors."""
        return self.model.get_sentence_embedding_dimension()
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        return {
            "model_name": self.model_name,
            "embedding_dimension": self.get_embedding_dimension(),
            "device": str(self.model.device),
            "max_seq_length": self.model.max_seq_length,
            "stats": self.stats.copy()
        }
    
    def clear_cache(self):
        """Clear all cached embeddings."""
        if self.cache_dir:
            for cache_file in self.cache_dir.glob("*.pkl"):
                try:
                    cache_file.unlink()
                    logger.info(f"Removed cache file: {cache_file}")
                except Exception as e:
                    logger.warning(f"Failed to remove cache file {cache_file}: {e}")
    
    def save_embeddings(self, 
                        embeddings: np.ndarray, 
                        filepath: str,
                        format: str = "numpy"):
        """
        Save embeddings to file.
        
        Args:
            embeddings: Embeddings to save
            filepath: Path to save file
            format: Format to save in ('numpy', 'pickle', 'json')
        """
        filepath = Path(filepath)
        
        try:
            if format == "numpy":
                np.save(filepath, embeddings)
            elif format == "pickle":
                with open(filepath, 'wb') as f:
                    pickle.dump(embeddings, f)
            elif format == "json":
                import json
                with open(filepath, 'w') as f:
                    json.dump(embeddings.tolist(), f)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            logger.info(f"Embeddings saved to {filepath} in {format} format")
            
        except Exception as e:
            logger.error(f"Failed to save embeddings: {e}")
            raise
    
    def load_embeddings(self, 
                        filepath: str,
                        format: str = "numpy") -> np.ndarray:
        """
        Load embeddings from file.
        
        Args:
            filepath: Path to load file from
            format: Format of the file ('numpy', 'pickle', 'json')
            
        Returns:
            Loaded embeddings as numpy array
        """
        filepath = Path(filepath)
        
        try:
            if format == "numpy":
                embeddings = np.load(filepath)
            elif format == "pickle":
                with open(filepath, 'rb') as f:
                    embeddings = pickle.load(f)
            elif format == "json":
                import json
                with open(filepath, 'r') as f:
                    embeddings = np.array(json.load(f))
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            logger.info(f"Embeddings loaded from {filepath}")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to load embeddings: {e}")
            raise


def create_embedder(model_name: str = "all-MiniLM-L6-v2", **kwargs) -> TextEmbedder:
    """
    Factory function to create a TextEmbedder instance.
    
    Args:
        model_name: Name of the sentence-transformers model
        **kwargs: Additional arguments for TextEmbedder
        
    Returns:
        Configured TextEmbedder instance
    """
    return TextEmbedder(model_name=model_name, **kwargs)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Create embedder
    embedder = create_embedder()
    
    # Example texts
    texts = [
        "The quick brown fox jumps over the lazy dog",
        "A quick brown dog jumps over the lazy fox",
        "The weather is sunny today",
        "It's raining heavily outside"
    ]
    
    # Generate embeddings
    embeddings = embedder.embed_texts(texts)
    print(f"Generated embeddings shape: {embeddings.shape}")
    
    # Find similar texts
    query = "The quick brown fox jumps over the lazy dog"
    query_embedding = embedder.embed_single_text(query)
    
    similar = embedder.find_most_similar(query_embedding, embeddings, top_k=3)
    print(f"\nMost similar to '{query}':")
    for result in similar:
        print(f"  {result['rank']}. {texts[result['index']]} (similarity: {result['similarity']:.3f})")
    
    # Print model info
    print(f"\nModel info: {embedder.get_model_info()}") 