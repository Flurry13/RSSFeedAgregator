"""
Topic Classification Module
Zero-shot text classification using BART-MNLI model via Hugging Face
"""

import os
import time
import asyncio
from typing import List, Dict, Any, Optional
from transformers import pipeline
import torch
from dotenv import load_dotenv

load_dotenv()

# Configuration
HF_API_KEY = os.getenv('HUGGINGFACE_API_KEY')
MODEL_NAME = "facebook/bart-large-mnli"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Default topic labels (optimized 10-topic system)
DEFAULT_TOPICS = [
    'politics', 'economy', 'technology', 'science', 'environment',
    'entertainment', 'world', 'business', 'education', 'art'
]

# Rate limiting configuration
REQUESTS_PER_SECOND = 3
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 1000  # ms
MAX_RETRY_DELAY = 30000  # ms

class TopicClassifier:
    """Topic classification using zero-shot classification"""
    
    def __init__(self, model_name: str = MODEL_NAME, topics: List[str] = None):
        self.model_name = model_name
        self.topics = topics or DEFAULT_TOPICS
        self.classifier = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the classification model"""
        try:
            print(f"🔧 Initializing classifier: {self.model_name}")
            self.classifier = pipeline(
                "zero-shot-classification",
                model=self.model_name,
                device=0 if DEVICE == "cuda" else -1
            )
            print(f"✅ Classifier ready on {DEVICE}")
        except Exception as e:
            print(f"❌ Failed to initialize classifier: {e}")
            self.classifier = None
    
    def classify_single(self, text: str, candidate_labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Classify a single text into topics
        
        Args:
            text: Text to classify
            candidate_labels: List of candidate topic labels (optional)
            
        Returns:
            Dictionary with classification results
        """
        if not self.classifier:
            return self._fallback_classification(text)
        
        labels = candidate_labels or self.topics
        start_time = time.time()
        
        try:
            print(f"🔍 Classifying: \"{text[:60]}{'...' if len(text) > 60 else ''}\"")
            
            result = self.classifier(text, labels, multi_label=True)
            
            processing_time = time.time() - start_time
            
            # Format results
            classification = {
                'text': text,
                'topics': result['labels'],
                'scores': result['scores'],
                'topTopics': [
                    {
                        'topic': label,
                        'confidence': score
                    }
                    for label, score in zip(result['labels'][:3], result['scores'][:3])
                ],
                'processing_time': processing_time,
                'model_version': self.model_name
            }
            
            print(f"✅ Top topics: {', '.join([f\"{t['topic']} ({t['confidence']:.1%})\" for t in classification['topTopics']])}")
            
            return classification
            
        except Exception as e:
            print(f"❌ Classification failed: {e}")
            return self._fallback_classification(text)
    
    async def classify_batch(self, texts: List[str], candidate_labels: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Classify multiple texts concurrently
        
        Args:
            texts: List of texts to classify
            candidate_labels: List of candidate topic labels (optional)
            
        Returns:
            List of classification results
        """
        if not texts:
            return []
        
        print(f"🚀 Starting batch classification of {len(texts)} texts")
        start_time = time.time()
        
        # Process all texts concurrently
        tasks = [
            asyncio.create_task(self._classify_async(text, candidate_labels))
            for text in texts
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Text {i+1} failed: {result}")
                final_results.append(self._fallback_classification(texts[i]))
            else:
                final_results.append(result)
        
        total_time = time.time() - start_time
        success_rate = len([r for r in final_results if r['topics'][0] != 'general']) / len(final_results)
        
        print(f"🎉 Batch completed: {len(final_results)} texts in {total_time:.2f}s")
        print(f"📊 Success rate: {success_rate:.1%}")
        
        return final_results
    
    async def _classify_async(self, text: str, candidate_labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """Async wrapper for single classification"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.classify_single, text, candidate_labels)
    
    def _fallback_classification(self, text: str) -> Dict[str, Any]:
        """Fallback classification when model fails"""
        return {
            'text': text,
            'topics': ['general'],
            'scores': [1.0],
            'topTopics': [{'topic': 'general', 'confidence': 1.0}],
            'processing_time': 0.0,
            'model_version': 'fallback'
        }


# Global classifier instance
_classifier = None

def get_classifier() -> TopicClassifier:
    """Get or create global classifier instance"""
    global _classifier
    if _classifier is None:
        _classifier = TopicClassifier()
    return _classifier

def classify(text: str, candidate_labels: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Classify a single text (convenience function)
    
    Args:
        text: Text to classify
        candidate_labels: Optional list of candidate labels
        
    Returns:
        Classification result dictionary
    """
    classifier = get_classifier()
    return classifier.classify_single(text, candidate_labels)

async def classify_batch(texts: List[str], candidate_labels: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Classify multiple texts (convenience function)
    
    Args:
        texts: List of texts to classify
        candidate_labels: Optional list of candidate labels
        
    Returns:
        List of classification results
    """
    classifier = get_classifier()
    return await classifier.classify_batch(texts, candidate_labels)

# Example usage
if __name__ == "__main__":
    # Test classification
    test_texts = [
        "Breaking: New AI technology revolutionizes healthcare",
        "Climate summit reaches historic agreement on emissions",
        "Stock market hits record highs amid economic recovery"
    ]
    
    # Single classification
    result = classify(test_texts[0])
    print("Single classification result:", result)
    
    # Batch classification
    async def test_batch():
        results = await classify_batch(test_texts)
        for i, result in enumerate(results):
            print(f"Text {i+1}: {result['topTopics'][0]['topic']} ({result['topTopics'][0]['confidence']:.1%})")
    
    asyncio.run(test_batch()) 