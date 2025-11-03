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
        <div className="relative">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          <div className="absolute inset-0 blur-xl bg-blue-500/30"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card">
        <div className="text-center">
          <div className="text-red-400 text-lg font-medium mb-2">Error</div>
          <div className="text-gray-300 mb-4">{error}</div>
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
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 via-cyan-300 to-blue-500 bg-clip-text text-transparent">
            Dashboard
          </h1>
          <p className="text-gray-300 mt-2">Real-time monitoring of your RSS feed aggregation system</p>
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
        <div className="card group">
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 rounded-xl border border-blue-400/30 backdrop-blur-sm">
              <Globe className="h-6 w-6 text-blue-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-white">{stats.totalHeadlines}</div>
              <div className="text-sm text-gray-400">Total Headlines</div>
            </div>
          </div>
        </div>

        <div className="card group">
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-gradient-to-br from-green-500/20 to-emerald-500/20 rounded-xl border border-green-400/30 backdrop-blur-sm">
              <Languages className="h-6 w-6 text-green-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-white">{stats.translatedHeadlines}</div>
              <div className="text-sm text-gray-400">Translated</div>
            </div>
          </div>
        </div>

        <div className="card group">
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-xl border border-purple-400/30 backdrop-blur-sm">
              <Globe className="h-6 w-6 text-purple-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-white">{stats.languages}</div>
              <div className="text-sm text-gray-400">Languages</div>
            </div>
          </div>
        </div>

        <div className="card group">
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-gradient-to-br from-orange-500/20 to-red-500/20 rounded-xl border border-orange-400/30 backdrop-blur-sm">
              <TrendingUp className="h-6 w-6 text-orange-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-white">{stats.sources}</div>
              <div className="text-sm text-gray-400">Sources</div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Headlines */}
      <div className="card">
        <h2 className="text-xl font-semibold text-white mb-6 bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
          Recent Headlines
        </h2>
        <div className="space-y-3">
          {recentHeadlines.length > 0 ? (
            recentHeadlines.map((headline, index) => (
              <div 
                key={index} 
                className="flex items-start space-x-4 p-4 rounded-xl backdrop-blur-sm bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 transition-all duration-300 group"
              >
                <div className="flex-1">
                  <h3 className="font-medium text-white mb-2 group-hover:text-blue-400 transition-colors">
                    <a
                      href={headline.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:text-cyan-400 transition-colors"
                    >
                      {headline.title}
                    </a>
                  </h3>
                  <div className="flex items-center space-x-4 text-sm text-gray-400">
                    <span className="flex items-center space-x-1">
                      <Globe className="h-3 w-3" />
                      <span>{headline.source}</span>
                    </span>
                    <span className="flex items-center space-x-1">
                      <Languages className="h-3 w-3" />
                      <span>{headline.language.toUpperCase()}</span>
                    </span>
                    {headline.translated && (
                      <span className="glass-badge bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-400 border-green-400/30">
                        Translated
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="text-center py-12 text-gray-400">
              <div className="relative inline-block">
                <Globe className="h-16 w-16 mx-auto mb-4 text-blue-500/30" />
                <div className="absolute inset-0 blur-xl bg-blue-500/20"></div>
              </div>
              <div className="text-lg font-medium mb-2 text-gray-300">No headlines yet</div>
              <div className="text-sm">Click "Gather" to start collecting RSS feeds</div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Dashboard 