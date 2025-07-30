from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import numpy as np

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

class TextRequest(BaseModel):
    text: str

class EmbeddingResponse(BaseModel):
    text: str
    embedding: List[float]
    embedding_dim: int

class BatchEmbeddingRequest(BaseModel):
    texts: List[str]

class BatchEmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    embedding_dim: int

@app.get("/")
async def root():
    return {"message": "RSS Feed Analysis API with MiniLM Embeddings"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "model": "sentence-transformers/all-MiniLM-L6-v2"}

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

@app.get("/model-info")
async def get_model_info():
    """Get information about the loaded model"""
    return {
        "model_name": "sentence-transformers/all-MiniLM-L6-v2",
        "embedding_dimension": model.get_sentence_embedding_dimension(),
        "max_seq_length": model.max_seq_length
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 