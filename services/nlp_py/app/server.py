from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="News AI - NLP Service",
    description="Machine Learning pipeline for news analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ClassificationRequest(BaseModel):
    text: str
    candidate_labels: Optional[List[str]] = None
    multi_label: bool = True
    confidence_threshold: float = 0.1

class TopicResult(BaseModel):
    label: str
    confidence: float
    rank: int

class ClassificationResponse(BaseModel):
    topics: List[TopicResult]
    processing_time: float
    model_version: str

class TranslationRequest(BaseModel):
    text: str
    source_language: str = "auto"
    target_language: str = "en"

class TranslationResponse(BaseModel):
    translated_text: str
    detected_language: str
    confidence: float
    processing_time: float

class EmbeddingRequest(BaseModel):
    text: str
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"

class EmbeddingResponse(BaseModel):
    embedding: List[float]
    dimension: int
    processing_time: float

class HealthResponse(BaseModel):
    status: str
    message: str
    version: str
    services: dict

# Default topic labels
DEFAULT_TOPICS = [
    'politics', 'economy', 'technology', 'science', 'environment',
    'entertainment', 'world', 'business', 'education', 'art'
]

@app.get("/", summary="Root endpoint")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "News AI - NLP Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "classify": "/classify",
            "translate": "/translate", 
            "embed": "/embed",
            "docs": "/docs"
        }
    }

@app.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check():
    """Health check endpoint for service monitoring"""
    return HealthResponse(
        status="healthy",
        message="NLP service is running",
        version="1.0.0",
        services={
            "classification": "available",
            "translation": "available", 
            "embedding": "available",
            "database": "checking...",
            "vector_db": "checking..."
        }
    )

@app.post("/classify", response_model=ClassificationResponse, summary="Classify text")
async def classify_text(request: ClassificationRequest):
    """
    Classify text into predefined topic categories using zero-shot classification
    """
    try:
        import time
        start_time = time.time()
        
        # Use default topics if none provided
        labels = request.candidate_labels or DEFAULT_TOPICS
        
        # Mock classification for now - replace with actual model
        mock_results = [
            TopicResult(label="technology", confidence=0.85, rank=1),
            TopicResult(label="business", confidence=0.72, rank=2),
            TopicResult(label="science", confidence=0.45, rank=3)
        ]
        
        processing_time = time.time() - start_time
        
        return ClassificationResponse(
            topics=mock_results,
            processing_time=processing_time,
            model_version="facebook/bart-large-mnli"
        )
        
    except Exception as e:
        logger.error(f"Classification error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")

@app.post("/translate", response_model=TranslationResponse, summary="Translate text")
async def translate_text(request: TranslationRequest):
    """
    Translate text between languages
    """
    try:
        import time
        start_time = time.time()
        
        # Mock translation for now - replace with actual model
        translated_text = request.text  # No translation in mock
        detected_language = request.source_language
        
        processing_time = time.time() - start_time
        
        return TranslationResponse(
            translated_text=translated_text,
            detected_language=detected_language,
            confidence=0.95,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")

@app.post("/embed", response_model=EmbeddingResponse, summary="Generate embeddings")
async def generate_embedding(request: EmbeddingRequest):
    """
    Generate vector embeddings for text using sentence transformers
    """
    try:
        import time
        import random
        start_time = time.time()
        
        # Mock embedding for now - replace with actual model
        dimension = 384  # MiniLM dimension
        mock_embedding = [random.random() for _ in range(dimension)]
        
        processing_time = time.time() - start_time
        
        return EmbeddingResponse(
            embedding=mock_embedding,
            dimension=dimension,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Embedding error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")

@app.get("/models", summary="List available models")
async def list_models():
    """List all available ML models and their status"""
    return {
        "classification": {
            "model": "facebook/bart-large-mnli",
            "status": "loaded",
            "topics": DEFAULT_TOPICS
        },
        "translation": {
            "model": "Helsinki-NLP/opus-mt-mul-en", 
            "status": "available"
        },
        "embedding": {
            "model": "sentence-transformers/all-MiniLM-L6-v2",
            "status": "loaded",
            "dimension": 384
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("NLP_PORT", 8081))
    host = os.getenv("NLP_HOST", "0.0.0.0")
    
    logger.info(f"Starting NLP service on {host}:{port}")
    uvicorn.run(app, host=host, port=port) 