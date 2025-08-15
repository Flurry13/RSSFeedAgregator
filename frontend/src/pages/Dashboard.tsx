import React from 'react'
import { useHeadlines } from '../context/HeadlinesContext'
import { RefreshCw, Globe, Languages, TrendingUp } from 'lucide-react'
import StatusPanel from '../components/StatusPanel'

const Dashboard: React.FC = () => {
  const { headlines, loading, error, refreshHeadlines } = useHeadlines()

  const stats = {
    totalHeadlines: headlines.length,
    translatedHeadlines: headlines.filter(h => h.translated).length,
    languages: new Set(headlines.map(h => h.language)).size,
    sources: new Set(headlines.map(h => h.source)).size,
  }

  const recentHeadlines = headlines.slice(0, 5)

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card">
        <div className="text-center">
          <div className="text-red-500 text-lg font-medium mb-2">Error</div>
          <div className="text-gray-600 mb-4">{error}</div>
          <button onClick={refreshHeadlines} className="btn-primary">
            Try Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-2">Real-time monitoring of your RSS feed aggregation system</p>
        </div>
        <button
          onClick={refreshHeadlines}
          className="btn-primary flex items-center space-x-2"
        >
          <RefreshCw className="h-4 w-4" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Real-time Status Panel */}
      <StatusPanel />

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Globe className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{stats.totalHeadlines}</div>
              <div className="text-sm text-gray-600">Total Headlines</div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <Languages className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{stats.translatedHeadlines}</div>
              <div className="text-sm text-gray-600">Translated</div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-purple-100 rounded-lg">
              <Globe className="h-6 w-6 text-purple-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{stats.languages}</div>
              <div className="text-sm text-gray-600">Languages</div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-orange-100 rounded-lg">
              <TrendingUp className="h-6 w-6 text-orange-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{stats.sources}</div>
              <div className="text-sm text-gray-600">Sources</div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Headlines */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Recent Headlines</h2>
        <div className="space-y-4">
          {recentHeadlines.length > 0 ? (
            recentHeadlines.map((headline, index) => (
              <div key={index} className="flex items-start space-x-4 p-4 bg-gray-50 rounded-lg">
                <div className="flex-1">
                  <h3 className="font-medium text-gray-900 mb-1">
                    <a
                      href={headline.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:text-primary-600 transition-colors"
                    >
                      {headline.title}
                    </a>
                  </h3>
                  <div className="flex items-center space-x-4 text-sm text-gray-600">
                    <span className="flex items-center space-x-1">
                      <Globe className="h-3 w-3" />
                      <span>{headline.source}</span>
                    </span>
                    <span className="flex items-center space-x-1">
                      <Languages className="h-3 w-3" />
                      <span>{headline.language.toUpperCase()}</span>
                    </span>
                    {headline.translated && (
                      <span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs">
                        Translated
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="text-center py-8 text-gray-500">
              <Globe className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <div className="text-lg font-medium mb-2">No headlines yet</div>
              <div className="text-sm">Click "Gather" to start collecting RSS feeds</div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Dashboard 