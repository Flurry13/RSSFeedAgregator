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
  note?: string;
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
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-4 border-blue-600 mx-auto"></div>
          <p className="mt-6 text-lg text-gray-700">Analyzing news with AI...</p>
          <p className="mt-2 text-sm text-gray-500">Processing RSS feeds and classifying headlines</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-pink-100 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-red-600 text-6xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Error</h1>
          <p className="text-gray-600 mb-4">{error}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">
            🤖 News AI
          </h1>
          <p className="text-xl text-gray-600 mb-2">
            Advanced RSS Feed Analysis Platform
          </p>
          <div className="flex justify-center items-center gap-4 text-sm text-gray-500">
            <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full">
              ✅ {data.total} headlines processed
            </span>
            <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full">
              📡 {Object.keys(data.amountBySource).length} sources
            </span>
            <span className="bg-purple-100 text-purple-800 px-3 py-1 rounded-full">
              🎯 AI-powered classification
            </span>
          </div>
          {data.note && (
            <div className="mt-4 p-3 bg-yellow-100 border border-yellow-300 rounded-lg text-sm text-yellow-800">
              💡 {data.note}
            </div>
          )}
        </div>

        {/* Source Summary */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-8 border border-gray-200">
          <h2 className="text-2xl font-semibold mb-6 text-gray-800">📊 Source Overview</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(data.amountBySource).map(([source, count]) => (
              <div key={source} className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4 border border-blue-200">
                <div className="font-medium text-sm text-gray-900 truncate mb-1">
                  🌐 {new URL(source).hostname}
                </div>
                <div className="text-3xl font-bold text-blue-600 mb-1">{count}</div>
                <div className="text-xs text-gray-500">headlines analyzed</div>
              </div>
            ))}
          </div>
        </div>

        {/* Headlines */}
        <div className="space-y-6">
          <h2 className="text-2xl font-semibold text-gray-800 mb-4">📰 Classified Headlines</h2>
          {data.headlines.map((headline, index) => (
            <div key={index} className="bg-white rounded-xl shadow-lg p-6 border border-gray-200 hover:shadow-xl transition-shadow">
              <div className="flex justify-between items-start mb-4">
                <h3 className="text-xl font-semibold text-gray-900 flex-1 mr-4 leading-relaxed">
                  {headline.title}
                </h3>
                <div className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                  {new Date(headline.pubDate).toLocaleDateString()}
                </div>
              </div>
              
              <div className="flex items-center justify-between mb-4">
                <div className="text-sm text-blue-600 font-medium">
                  🔗 {new URL(headline.source).hostname}
                </div>
              </div>

              {/* AI Classification */}
              <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-4 border border-purple-200">
                <div className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                  🎯 AI Classification Results:
                </div>
                <div className="flex flex-wrap gap-2">
                  {headline.classification.topTopics.map((topic, topicIndex) => {
                    const confidenceLevel = topic.confidence > 0.9 ? 'high' : topic.confidence > 0.7 ? 'medium' : 'low';
                    const colorClass = confidenceLevel === 'high' ? 'bg-green-100 text-green-800 border-green-300' :
                                     confidenceLevel === 'medium' ? 'bg-yellow-100 text-yellow-800 border-yellow-300' :
                                     'bg-gray-100 text-gray-800 border-gray-300';
                    
                    return (
                      <span
                        key={topicIndex}
                        className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${colorClass}`}
                      >
                        {topic.topic} ({(topic.confidence * 100).toFixed(1)}%)
                      </span>
                    );
                  })}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="mt-12 text-center text-gray-500 text-sm">
          <p>Powered by News AI • Next.js • Machine Learning • Real-time Analysis</p>
        </div>
      </div>
    </div>
  );
}
