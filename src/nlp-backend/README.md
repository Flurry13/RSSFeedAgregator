# RSS Event Grouping Backend

This Python backend provides efficient event-based grouping of RSS headlines using advanced NLP techniques and semantic similarity.

## Features

- **Semantic Similarity**: Uses sentence transformers to compute semantic similarity between headlines
- **Advanced Event Detection**: Leverages NLP techniques including named entity recognition and key phrase extraction
- **Intelligent Clustering**: Groups headlines by events using similarity-based clustering algorithms
- **Event Classification**: Automatically classifies events into categories (politics, conflict, diplomacy, etc.)
- **Entity Extraction**: Identifies key entities (people, organizations, locations) in events
- **Temporal Analysis**: Considers temporal indicators for better event grouping
- **RESTful API**: FastAPI-based API with comprehensive endpoints

## Architecture

### Core Components

1. **EventDetector** (`event_detector.py`): Advanced NLP-based event detection
2. **FastAPI Server** (`main.py`): REST API endpoints for event grouping
3. **Sentence Transformers**: Semantic similarity computation
4. **scikit-learn**: Clustering algorithms and similarity metrics

### Key Algorithms

- **Semantic Similarity**: Cosine similarity using sentence embeddings
- **Event Clustering**: Custom clustering algorithm with similarity thresholds
- **Entity Recognition**: Named entity extraction using spaCy
- **Event Classification**: Keyword-based event type classification
- **Cluster Merging**: Intelligent merging of similar clusters

## Installation

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Install spaCy model** (for advanced NLP features):
   ```bash
   python -m spacy download en_core_web_sm
   ```

3. **Verify installation**:
   ```bash
   python -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('spaCy installed successfully')"
   ```

## Usage

### Starting the Server

```bash
cd src/nlp-backend
python main.py
```

The server will start on `http://localhost:8000`

### API Endpoints

#### 1. Group Headlines by Events
**POST** `/group-headlines`

Groups headlines into events based on semantic similarity.

**Request Body**:
```json
{
  "headlines": [
    {
      "title": "Breaking: Major earthquake hits California",
      "source": "CNN",
      "pubDate": "2024-01-15T10:30:00Z",
      "topics": ["disaster", "local"],
      "scores": [0.9, 0.8]
    }
  ],
  "similarity_threshold": 0.7,
  "min_cluster_size": 2
}
```

**Response**:
```json
{
  "event_groups": [
    {
      "event_id": "event_0_20240115_143022",
      "event_name": "Disaster Event: earthquake in California",
      "headlines": [...],
      "similarity_score": 0.85,
      "event_keywords": ["earthquake", "california", "damage"],
      "event_type": "disaster",
      "top_entities": ["california", "earthquake"],
      "locations": ["California"],
      "created_at": "2024-01-15T14:30:22Z"
    }
  ],
  "ungrouped_headlines": [...],
  "total_groups": 1,
  "total_grouped": 3,
  "total_ungrouped": 0
}
```

#### 2. Health Check
**GET** `/health`

Returns server health status.

#### 3. Model Information
**GET** `/model-info`

Returns information about the loaded sentence transformer model.

### Testing

Run the test script to see the system in action:

```bash
python test_event_grouping.py
```

This will:
1. Test the health endpoint
2. Send sample headlines to the API
3. Display grouped events with detailed information
4. Save results to `event_grouping_results.json`

## Configuration

### Similarity Threshold
- **Default**: 0.7
- **Range**: 0.0 - 1.0
- **Effect**: Higher values create more strict grouping (fewer, more similar groups)

### Minimum Cluster Size
- **Default**: 2
- **Effect**: Minimum number of headlines required to form an event group

### Event Types
The system automatically classifies events into these categories:
- `politics`: Elections, government actions, political events
- `conflict`: Attacks, violence, wars
- `diplomacy`: Meetings, agreements, treaties
- `economy`: Financial news, markets, business
- `disaster`: Natural disasters, accidents
- `technology`: Product launches, tech news
- `sports`: Games, matches, tournaments
- `entertainment`: Movies, celebrities, awards
- `general`: Uncategorized events

## Performance Considerations

### Scalability
- **Embedding Generation**: O(n) where n is number of headlines
- **Similarity Computation**: O(n²) for full similarity matrix
- **Clustering**: O(n²) for similarity-based clustering
- **Memory Usage**: Scales with headline count and embedding dimensions

### Optimization Tips
1. **Batch Processing**: Process headlines in batches for large datasets
2. **Caching**: Cache embeddings for repeated processing
3. **Threshold Tuning**: Adjust similarity threshold based on your needs
4. **Model Selection**: Use smaller models for faster processing

### Recommended Limits
- **Headlines per request**: 100-500 (depending on server resources)
- **Similarity threshold**: 0.6-0.8 (balance between precision and recall)
- **Minimum cluster size**: 2-5 (depending on data characteristics)

## Advanced Features

### Named Entity Recognition
- Extracts people, organizations, locations, and events
- Used for event naming and context extraction
- Requires spaCy model installation

### Key Phrase Extraction
- Identifies event-specific terminology
- Uses regex patterns for common event phrases
- Helps in event classification and summarization

### Temporal Analysis
- Considers temporal indicators in headlines
- Groups events by time proximity
- Useful for breaking news and ongoing events

### Cluster Merging
- Merges very similar clusters automatically
- Prevents over-fragmentation of events
- Uses centroid similarity for merging decisions

## Error Handling

The API includes comprehensive error handling:
- **Invalid input validation**
- **Model loading errors**
- **Processing timeouts**
- **Memory management**
- **Graceful degradation** when spaCy is not available

## Integration with Frontend

The backend is designed to work seamlessly with your existing TypeScript frontend:

1. **CORS enabled** for cross-origin requests
2. **JSON API** with consistent response format
3. **Error handling** with HTTP status codes
4. **Health checks** for monitoring

## Troubleshooting

### Common Issues

1. **spaCy model not found**:
   ```bash
   python -m spacy download en_core_web_sm
   ```

2. **Memory issues with large datasets**:
   - Reduce batch size
   - Use smaller sentence transformer model
   - Increase server memory

3. **Slow processing**:
   - Use GPU if available (CUDA)
   - Reduce similarity threshold
   - Process smaller batches

4. **Poor grouping quality**:
   - Adjust similarity threshold
   - Increase minimum cluster size
   - Check headline quality and diversity

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

- **Real-time processing**: WebSocket support for live headline processing
- **Event timeline**: Temporal ordering of events
- **Multi-language support**: Non-English headline processing
- **Event prediction**: Predict emerging events from early indicators
- **Advanced clustering**: Hierarchical and density-based clustering
- **Event summarization**: Generate event summaries using LLMs 