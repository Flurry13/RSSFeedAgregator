import React, { useState } from 'react'
import { useHeadlines } from '../context/HeadlinesContext'
import { Languages, Globe, RefreshCw, CheckCircle, AlertCircle } from 'lucide-react'

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
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card">
        <div className="text-center text-red-500">
          <div className="text-lg font-medium mb-2">Error</div>
          <div className="text-gray-600">{error}</div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Translations</h1>
          <p className="text-gray-600 mt-2">Manage and monitor headline translations</p>
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
        <div className="card">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Globe className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{translationStats.total}</div>
              <div className="text-sm text-gray-600">Total Headlines</div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <CheckCircle className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{translationStats.translated}</div>
              <div className="text-sm text-gray-600">Translated</div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-yellow-100 rounded-lg">
              <AlertCircle className="h-6 w-6 text-yellow-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{translationStats.pending}</div>
              <div className="text-sm text-gray-600">Pending</div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-gray-100 rounded-lg">
              <Languages className="h-6 w-6 text-gray-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{translationStats.english}</div>
              <div className="text-sm text-gray-600">Already English</div>
            </div>
          </div>
        </div>
      </div>

      {/* Pending Translations */}
      {pendingHeadlines.length > 0 && (
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Pending Translations ({pendingHeadlines.length})
          </h2>
          <div className="space-y-3">
            {pendingHeadlines.slice(0, 10).map((headline, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
                <div className="flex-1">
                  <div className="font-medium text-gray-900">{headline.title}</div>
                  <div className="text-sm text-gray-600">
                    {headline.source} • {headline.language.toUpperCase()}
                  </div>
                </div>
                <div className="text-sm text-yellow-600 font-medium">Pending</div>
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
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Recent Translations ({translatedHeadlines.length})
          </h2>
          <div className="space-y-4">
            {translatedHeadlines.slice(0, 5).map((headline, index) => (
              <div key={index} className="p-4 bg-green-50 rounded-lg">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-medium text-gray-900">{headline.title}</h3>
                  <span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs">
                    Translated
                  </span>
                </div>
                
                {headline.original_title && (
                  <div className="bg-white p-3 rounded border border-green-200 mb-2">
                    <div className="text-sm text-gray-600 mb-1">Original ({headline.language}):</div>
                    <div className="text-gray-800">{headline.original_title}</div>
                  </div>
                )}
                
                <div className="text-sm text-gray-600">
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
          <div className="text-gray-500">
            <Languages className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <div className="text-lg font-medium mb-2">No translations yet</div>
            <div className="text-sm">Start by collecting headlines from your RSS feeds</div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Translations 