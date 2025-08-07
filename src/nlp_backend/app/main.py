from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import numpy as np
import sys
import os

# Add the parent directory to the path to import the vector_db module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from vector_db.qdrant_client import NewsVectorDB

# Load environment variables
load_dotenv()

app = FastAPI(title="RSS Feed Analysis API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the MiniLM model
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# Initialize vector database
vector_db = NewsVectorDB(mock_mode=True)  # Use mock mode for testing

class TextRequest(BaseModel):
    text: str

class HeadlineRequest(BaseModel):
    headline: str
    source: str
    region: str
    language: str
    topic: str
    sentiment: Optional[str] = None
    bias_score: Optional[float] = None

class EmbeddingResponse(BaseModel):
    text: str
    embedding: List[float]
    embedding_dim: int

class BatchEmbeddingRequest(BaseModel):
    texts: List[str]

class BatchEmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    embedding_dim: int

class VectorSearchRequest(BaseModel):
    query: str
    limit: int = 10
    score_threshold: float = 0.7
    filters: Optional[Dict] = None

class UnderrepresentationRequest(BaseModel):
    topic: str

@app.get("/")
async def root():
    return {"message": "RSS Feed Analysis API with MiniLM Embeddings and Vector Database"}

@app.get("/health")
async def health_check():
    try:
        collection_info = vector_db.get_collection_info()
        return {
            "status": "healthy", 
            "model": "sentence-transformers/all-MiniLM-L6-v2",
            "vector_db": "connected",
            "collection_info": collection_info
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.post("/embed", response_model=EmbeddingResponse)
async def get_embedding(request: TextRequest):
    """Get embedding for a single text using MiniLM"""
    try:
        embedding = model.encode(request.text)
        return EmbeddingResponse(
            text=request.text,
            embedding=embedding.tolist(),
            embedding_dim=len(embedding)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding error: {str(e)}")

@app.post("/embed-batch", response_model=BatchEmbeddingResponse)
async def get_batch_embeddings(request: BatchEmbeddingRequest):
    """Get embeddings for multiple texts using MiniLM"""
    try:
        embeddings = model.encode(request.texts)
        return BatchEmbeddingResponse(
            embeddings=embeddings.tolist(),
            embedding_dim=embeddings.shape[1]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch embedding error: {str(e)}")

@app.post("/store-headline")
async def store_headline(request: HeadlineRequest):
    """Store a headline with its embedding in the vector database"""
    try:
        # Generate embedding
        embedding = model.encode(request.headline)
        
        # Store in vector database
        point_id = vector_db.store_headline(
            headline=request.headline,
            embedding=embedding.tolist(),
            source=request.source,
            region=request.region,
            language=request.language,
            topic=request.topic,
            sentiment=request.sentiment,
            bias_score=request.bias_score
        )
        
        return {
            "message": "Headline stored successfully",
            "point_id": point_id,
            "embedding_dim": len(embedding)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error storing headline: {str(e)}")

@app.post("/search-similar")
async def search_similar_headlines(request: VectorSearchRequest):
    """Search for similar headlines using vector similarity"""
    try:
        # Generate embedding for the query
        query_embedding = model.encode(request.query)
        
        # Search in vector database
        results = vector_db.search_similar(
            query_embedding=query_embedding.tolist(),
            limit=request.limit,
            score_threshold=request.score_threshold,
            filters=request.filters
        )
        
        return {
            "query": request.query,
            "results": results,
            "total_found": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@app.get("/topic-statistics/{topic}")
async def get_topic_statistics(topic: str, region: Optional[str] = None):
    """Get statistics for a specific topic"""
    try:
        stats = vector_db.get_topic_statistics(topic, region)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting topic statistics: {str(e)}")

@app.post("/underrepresentation-metrics")
async def get_underrepresentation_metrics(request: UnderrepresentationRequest):
    """Calculate underrepresentation metrics for a topic"""
    try:
        metrics = vector_db.get_underrepresentation_metrics(request.topic)
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating metrics: {str(e)}")

@app.get("/model-info")
async def get_model_info():
    """Get information about the loaded model"""
    return {
        "model_name": "sentence-transformers/all-MiniLM-L6-v2",
        "embedding_dimension": model.get_sentence_embedding_dimension(),
        "max_seq_length": model.max_seq_length
    }

@app.get("/vector-db-info")
async def get_vector_db_info():
    """Get information about the vector database"""
    try:
        info = vector_db.get_collection_info()
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting vector DB info: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 