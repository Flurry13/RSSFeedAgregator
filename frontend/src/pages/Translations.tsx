import React, { useState } from 'react'
import { useHeadlines } from '../context/HeadlinesContext'
import { Languages, Globe, RefreshCw, CheckCircle, AlertCircle, TrendingUp } from 'lucide-react'

const Translations: React.FC = () => {
  const { headlines, loading, error, translateHeadlines } = useHeadlines()
  const [isTranslating, setIsTranslating] = useState(false)

  const translationStats = {
    total: headlines.length,
    translated: headlines.filter(h => h.translated).length,
    pending: headlines.filter(h => !h.translated && h.language !== 'en').length,
    english: headlines.filter(h => h.language === 'en').length,
  }

  const handleTranslate = async () => {
    setIsTranslating(true)
    try {
      await translateHeadlines()
    } finally {
      setIsTranslating(false)
    }
  }

  const pendingHeadlines = headlines.filter(h => !h.translated && h.language !== 'en')
  const translatedHeadlines = headlines.filter(h => h.translated)

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
          <div className="text-gray-300">{error}</div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 via-cyan-300 to-blue-500 bg-clip-text text-transparent">
            Translations
          </h1>
          <p className="text-gray-300 mt-2">Manage and monitor headline translations</p>
        </div>
        <button
          onClick={handleTranslate}
          disabled={isTranslating || translationStats.pending === 0}
          className="btn-primary flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RefreshCw className={`h-4 w-4 ${isTranslating ? 'animate-spin' : ''}`} />
          <span>{isTranslating ? 'Translating...' : 'Translate All'}</span>
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card group">
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 rounded-xl border border-blue-400/30 backdrop-blur-sm">
              <Globe className="h-6 w-6 text-blue-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-white">{translationStats.total}</div>
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
              <div className="text-2xl font-bold text-white">{translationStats.translated}</div>
              <div className="text-sm text-gray-400">Translated</div>
            </div>
          </div>
        </div>

        <div className="card group">
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-gradient-to-br from-yellow-500/20 to-orange-500/20 rounded-xl border border-yellow-400/30 backdrop-blur-sm">
              <AlertCircle className="h-6 w-6 text-yellow-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-white">{translationStats.pending}</div>
              <div className="text-sm text-gray-400">Pending</div>
            </div>
          </div>
        </div>

        <div className="card group">
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-xl border border-purple-400/30 backdrop-blur-sm">
              <CheckCircle className="h-6 w-6 text-purple-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-white">{translationStats.english}</div>
              <div className="text-sm text-gray-400">Already English</div>
            </div>
          </div>
        </div>
      </div>

      {/* Pending Translations */}
      {pendingHeadlines.length > 0 && (
        <div className="card">
          <h2 className="text-xl font-semibold text-white mb-6 bg-gradient-to-r from-yellow-400 to-orange-400 bg-clip-text text-transparent">
            Pending Translations ({pendingHeadlines.length})
          </h2>
          <div className="space-y-3">
            {pendingHeadlines.slice(0, 10).map((headline, index) => (
              <div key={index} className="flex items-center justify-between p-4 rounded-xl backdrop-blur-sm bg-yellow-500/10 border border-yellow-400/30 hover:bg-yellow-500/20 hover:border-yellow-400/50 transition-all duration-300">
                <div className="flex-1">
                  <div className="font-medium text-white mb-1">{headline.title}</div>
                  <div className="text-sm text-gray-400">
                    {headline.source} • {headline.language.toUpperCase()}
                  </div>
                </div>
                <div className="glass-badge bg-gradient-to-r from-yellow-500/20 to-orange-500/20 text-yellow-400 border-yellow-400/30">
                  Pending
                </div>
              </div>
            ))}
            {pendingHeadlines.length > 10 && (
              <div className="text-center text-sm text-gray-500 pt-2">
                ... and {pendingHeadlines.length - 10} more
              </div>
            )}
          </div>
        </div>
      )}

      {/* Recent Translations */}
      {translatedHeadlines.length > 0 && (
        <div className="card">
          <h2 className="text-xl font-semibold text-white mb-6 bg-gradient-to-r from-green-400 to-emerald-400 bg-clip-text text-transparent">
            Recent Translations ({translatedHeadlines.length})
          </h2>
          <div className="space-y-4">
            {translatedHeadlines.slice(0, 5).map((headline, index) => (
              <div key={index} className="p-4 rounded-xl backdrop-blur-sm bg-green-500/10 border border-green-400/30 hover:bg-green-500/20 hover:border-green-400/50 transition-all duration-300">
                <div className="flex items-start justify-between mb-3">
                  <h3 className="font-medium text-white flex-1 mr-3">{headline.title}</h3>
                  <span className="glass-badge bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-400 border-green-400/30">
                    Translated
                  </span>
                </div>
                
                {headline.original_title && (
                  <div className="bg-white/5 p-3 rounded-lg border border-white/10 mb-3 backdrop-blur-sm">
                    <div className="text-sm text-gray-400 mb-1">Original ({headline.language}):</div>
                    <div className="text-gray-200">{headline.original_title}</div>
                  </div>
                )}
                
                <div className="text-sm text-gray-400">
                  {headline.source} • {headline.language.toUpperCase()} → English
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No translations message */}
      {translatedHeadlines.length === 0 && pendingHeadlines.length === 0 && (
        <div className="card text-center py-12">
          <div className="text-gray-400">
            <div className="relative inline-block">
              <Languages className="h-16 w-16 mx-auto mb-4 text-blue-500/30" />
              <div className="absolute inset-0 blur-xl bg-blue-500/20"></div>
            </div>
            <div className="text-lg font-medium mb-2 text-gray-300">No translations yet</div>
            <div className="text-sm">Start by collecting headlines from your RSS feeds</div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Translations 