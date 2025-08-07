'use client';

import { useState, useEffect } from 'react';

interface Classification {
  text: string;
  topics: string[];
  scores: number[];
  topTopics: Array<{
    topic: string;
    confidence: number;
  }>;
}

interface Headline {
  title: string;
  source: string;
  pubDate: string;
  classification: Classification;
}

interface ApiResponse {
  headlines: Headline[];
  amountBySource: Record<string, number>;
  total: number;
}

export default function Home() {
  const [data, setData] = useState<ApiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('/api/logic');
        if (!response.ok) {
          throw new Error('Failed to fetch data');
        }
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading RSS feeds and classifying headlines...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-600 text-2xl mb-4">⚠️ Error</div>
          <p className="text-gray-600">{error}</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">No data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            RSS Feed Classifier
          </h1>
          <p className="text-xl text-gray-600">
            {data.total} headlines from {Object.keys(data.amountBySource).length} sources
          </p>
        </div>

        {/* Source Summary */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-2xl font-semibold mb-4">Source Summary</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(data.amountBySource).map(([source, count]) => (
              <div key={source} className="bg-gray-50 rounded p-3">
                <div className="font-medium text-sm text-gray-900 truncate">
                  {new URL(source).hostname}
                </div>
                <div className="text-2xl font-bold text-blue-600">{count}</div>
                <div className="text-xs text-gray-500">headlines</div>
              </div>
            ))}
          </div>
        </div>

        {/* Headlines */}
        <div className="space-y-4">
          {data.headlines.map((headline, index) => (
            <div key={index} className="bg-white rounded-lg shadow-md p-6">
              <div className="flex justify-between items-start mb-3">
                <h3 className="text-lg font-semibold text-gray-900 flex-1 mr-4">
                  {headline.title}
                </h3>
                <div className="text-sm text-gray-500">
                  {new Date(headline.pubDate).toLocaleDateString()}
                </div>
              </div>
              
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm text-blue-600">
                  {new URL(headline.source).hostname}
                </div>
                <div className="text-xs text-gray-400">
                  {headline.source}
                </div>
              </div>

              {/* Classification */}
              <div className="bg-gray-50 rounded p-3">
                <div className="text-sm font-medium text-gray-700 mb-2">
                  AI Classification:
                </div>
                <div className="flex flex-wrap gap-2">
                  {headline.classification.topTopics.map((topic, topicIndex) => (
                    <span
                      key={topicIndex}
                      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                    >
                      {topic.topic} ({(topic.confidence * 100).toFixed(1)}%)
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
