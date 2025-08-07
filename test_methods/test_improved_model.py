import torch
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
import json
import time

def test_improved_model():
    """Test the improved trained DistilBERT model"""
    
    print("=" * 60)
    print("🧪 TESTING IMPROVED DISTILBERT MODEL")
    print("=" * 60)
    
    # Load the trained model
    model_path = "./distilbert_rss_classifier_improved_final"
    
    print(f"\n📥 Loading model from {model_path}...")
    load_start = time.time()
    
    tokenizer = DistilBertTokenizer.from_pretrained(model_path)
    model = DistilBertForSequenceClassification.from_pretrained(model_path)
    
    # Load topic mappings
    with open(f"{model_path}/topic_mappings.json", 'r') as f:
        mappings = json.load(f)
    
    ID_TO_TOPIC = mappings['id_to_topic']
    
    load_end = time.time()
    print(f"✅ Model loaded in {load_end - load_start:.2f}s")
    
    # Test headlines
    test_headlines = [
        "Trump Announces New Trade Deal with China",
        "Scientists Discover New Species in Amazon Rainforest", 
        "Tech Giant Reports Record Quarterly Profits",
        "Apple Launches New iPhone with AI Features",
        "Olympic Athlete Breaks World Record in Swimming",
        "Hollywood Star Wins Best Actor at Academy Awards",
        "Federal Reserve Raises Interest Rates Again",
        "Climate Summit Reaches Historic Agreement",
        "New Medical Breakthrough Shows Promise for Cancer Treatment",
        "Space Mission Successfully Lands on Mars"
    ]
    
    print(f"\n📝 Testing {len(test_headlines)} headlines...")
    
    model.eval()
    device = next(model.parameters()).device
    print(f"   Using device: {device}")
    
    results = []
    total_start = time.time()
    
    with torch.no_grad():
        for i, headline in enumerate(test_headlines):
            print(f"\n🔄 Testing headline {i+1}/{len(test_headlines)}: {headline[:50]}...")
            
            # Tokenize
            inputs = tokenizer(
                headline,
                truncation=True,
                padding=True,
                return_tensors="pt"
            )
            
            # Move to device
            inputs = {k: v.to(device) for k, v in inputs.items()}
            
            # Get predictions
            classify_start = time.time()
            outputs = model(**inputs)
            predictions = torch.softmax(outputs.logits, dim=-1)
            classify_end = time.time()
            
            # Get top 3 predictions
            top_probs, top_indices = torch.topk(predictions[0], k=3)
            
            top_predictions = []
            for prob, idx in zip(top_probs, top_indices):
                topic = ID_TO_TOPIC[str(idx.item())]
                top_predictions.append({
                    "topic": topic,
                    "confidence": prob.item()
                })
            
            result = {
                "headline": headline,
                "top_predictions": top_predictions,
                "classification_time": classify_end - classify_start
            }
            results.append(result)
            
            # Print top prediction
            top_pred = top_predictions[0]
            print(f"   🏆 Top prediction: {top_pred['topic']} ({top_pred['confidence']:.1%})")
            print(f"   ⚡ Classification time: {result['classification_time']:.3f}s")
    
    total_end = time.time()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    total_time = total_end - total_start
    avg_time = sum(r['classification_time'] for r in results) / len(results)
    avg_confidence = sum(r['top_predictions'][0]['confidence'] for r in results) / len(results)
    
    print(f"   ⏱️  Total test time: {total_time:.2f}s")
    print(f"   🚀 Average classification time: {avg_time:.3f}s")
    print(f"   📈 Throughput: {len(results)/total_time:.1f} headlines/second")
    print(f"   🎯 Average confidence: {avg_confidence:.1%}")
    
    # Topic distribution
    topic_counts = {}
    for result in results:
        top_topic = result['top_predictions'][0]['topic']
        topic_counts[top_topic] = topic_counts.get(top_topic, 0) + 1
    
    print(f"\n   📊 Topic distribution:")
    for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"      {topic}: {count} headlines")
    
    # Detailed results
    print("\n" + "=" * 60)
    print("📋 DETAILED RESULTS")
    print("=" * 60)
    
    for i, result in enumerate(results):
        print(f"\n📰 Headline {i+1}: {result['headline']}")
        top_3 = result['top_predictions'][:3]
        print(f"🏷️  Top 3 predictions:")
        for j, pred in enumerate(top_3):
            print(f"   {j+1}. {pred['topic']} ({pred['confidence']:.1%})")
    
    print("\n🎉 Testing completed successfully!")

if __name__ == "__main__":
    test_improved_model() 