import { NextResponse } from 'next/server';

// Mock data for testing until Go API service is implemented
const mockHeadlines = [
  {
    title: "Breaking: Major Economic Policy Announced",
    source: "https://example-news.com/feed",
    pubDate: new Date().toISOString(),
    classification: {
      text: "Breaking: Major Economic Policy Announced",
      topics: ["politics", "economy", "business"],
      scores: [0.92, 0.87, 0.65],
      topTopics: [
        { topic: "politics", confidence: 0.92 },
        { topic: "economy", confidence: 0.87 },
        { topic: "business", confidence: 0.65 }
      ]
    }
  },
  {
    title: "Scientists Discover Revolutionary Climate Solution",
    source: "https://science-daily.com/feed",
    pubDate: new Date(Date.now() - 3600000).toISOString(),
    classification: {
      text: "Scientists Discover Revolutionary Climate Solution",
      topics: ["science", "environment", "technology"],
      scores: [0.95, 0.89, 0.71],
      topTopics: [
        { topic: "science", confidence: 0.95 },
        { topic: "environment", confidence: 0.89 },
        { topic: "technology", confidence: 0.71 }
      ]
    }
  },
  {
    title: "Tech Giant Announces AI Breakthrough",
    source: "https://tech-news.com/feed", 
    pubDate: new Date(Date.now() - 7200000).toISOString(),
    classification: {
      text: "Tech Giant Announces AI Breakthrough",
      topics: ["technology", "business", "science"],
      scores: [0.98, 0.82, 0.76],
      topTopics: [
        { topic: "technology", confidence: 0.98 },
        { topic: "business", confidence: 0.82 },
        { topic: "science", confidence: 0.76 }
      ]
    }
  }
];

const mockAmountBySource = {
  "https://example-news.com/feed": 1,
  "https://science-daily.com/feed": 1,
  "https://tech-news.com/feed": 1
};

export async function GET() {
  try {
    console.log('🚀 API route called - returning mock data');
    
    // Simulate processing time
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const startTime = Date.now();
    const endTime = Date.now() + 100; // Mock processing time
    
    console.log(`🎉 Successfully processed ${mockHeadlines.length} mock headlines`);

    return NextResponse.json({
      headlines: mockHeadlines,
      amountBySource: mockAmountBySource,
      total: mockHeadlines.length,
      originalTotal: mockHeadlines.length,
      processingTime: endTime - startTime,
      note: "This is mock data. Connect to Go API service for real RSS processing."
    });

  } catch (error) {
    console.error('❌ Error in API route:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
} 