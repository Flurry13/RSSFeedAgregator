from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import numpy as np
from typing import List, Dict, Any
import time

def load_model():
    """Load the BART model and tokenizer locally"""
    model_name = "facebook/bart-large-mnli"
    
    # Download and cache the model (happens automatically)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    
    return tokenizer, model

def classify_text(text: str, candidate_labels: List[str], model, tokenizer) -> Dict[str, Any]:
    """Classify a single text using the local model"""
    
    # Prepare the inputs
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    
    # Get model predictions
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        
    # Convert to probabilities
    probs = torch.softmax(logits, dim=1)
    
    # Create results in the same format as Hugging Face API
    results = []
    for i, label in enumerate(candidate_labels):
        results.append({
            "label": label,
            "score": float(probs[0][i])
        })
    
    # Sort by score (highest first)
    results.sort(key=lambda x: x["score"], reverse=True)
    
    return results

def classify_batch(texts: List[str], candidate_labels: List[str]) -> List[Dict[str, Any]]:
    """Classify multiple texts efficiently"""
    
    # Load model once (will be cached)
    tokenizer, model = load_model()
    
    results = []
    for text in texts:
        classification = classify_text(text, candidate_labels, model, tokenizer)
        results.append({
            "text": text,
            "topics": [r["label"] for r in classification],
            "scores": [r["score"] for r in classification],
            "topTopics": classification[:3]  # Top 3 results
        })
    
    return results


def main():
    """Test the local classification"""
    
    # Your candidate topics
    candidate_topics = [
        'politics', 'economy', 'technology', 'science', 'health', 'environment',
        'sports', 'entertainment', 'lifestyle', 'world', 'local', 'business',
        'education', 'travel', 'food', 'fashion', 'art'
    ]
    
    # Test headlines
    test_headlines = [
        "Trump Announces New Trade Deal with China",
        "Scientists Discover New Species in Amazon Rainforest",
        "Tech Giant Reports Record Quarterly Profits"
    ]
    
    print("🚀 Starting local classification...")
    start_time = time.time()
    
    results = classify_batch(test_headlines, candidate_topics)
    
    end_time = time.time()
    print(f"✅ Completed in {end_time - start_time:.2f} seconds")
    
    # Display results
    for result in results:
        print(f"\n📰 Text: {result['text']}")
        print(f"🏷️  Top topics: {', '.join([f'{t} ({s:.1%})' for t, s in zip(result['topTopics'][:3], result['scores'][:3])])}")

if __name__ == "__main__":
    main()

