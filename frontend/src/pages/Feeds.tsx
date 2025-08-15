import React, { useState, useMemo } from 'react'
import { useHeadlines } from '../context/HeadlinesContext'
import { Search, Globe, Languages, ExternalLink, Calendar } from 'lucide-react'

const Feeds: React.FC = () => {
  const { headlines, loading, error } = useHeadlines()
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedLanguage, setSelectedLanguage] = useState('all')
  const [selectedSource, setSelectedSource] = useState('all')

  const languages = useMemo(() => 
    Array.from(new Set(headlines.map(h => h.language))).sort(), 
    [headlines]
  )
  
  const sources = useMemo(() => 
    Array.from(new Set(headlines.map(h => h.source))).sort(), 
    [headlines]
  )

  const filteredHeadlines = useMemo(() => {
    return headlines.filter(headline => {
      const matchesSearch = headline.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           headline.source.toLowerCase().includes(searchTerm.toLowerCase())
      const matchesLanguage = selectedLanguage === 'all' || headline.language === selectedLanguage
      const matchesSource = selectedSource === 'all' || headline.source === selectedSource
      
      return matchesSearch && matchesLanguage && matchesSource
    })
  }, [headlines, searchTerm, selectedLanguage, selectedSource])

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

  const formatDate = (s?: string) => {
    if (!s) return ''
    try {
      const d = new Date(s)
      if (!isNaN(d.getTime())) return d.toLocaleString()
      return s
    } catch {
      return s
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Feeds</h1>
        <p className="text-gray-600 mt-2">Browse and search through all collected headlines</p>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Search */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Search</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search headlines..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="input-field pl-10"
              />
            </div>
          </div>

          {/* Language Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Language</label>
            <select
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value)}
              className="input-field"
            >
              <option value="all">All Languages</option>
              {languages.map(lang => (
                <option key={lang} value={lang}>{lang.toUpperCase()}</option>
              ))}
            </select>
          </div>

          {/* Source Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Source</label>
            <select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              className="input-field"
            >
              <option value="all">All Sources</option>
              {sources.map(source => (
                <option key={source} value={source}>{source}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Results Count */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="text-sm text-gray-600">
            Showing {filteredHeadlines.length} of {headlines.length} headlines
          </div>
        </div>
      </div>

      {/* Headlines List */}
      <div className="space-y-4">
        {filteredHeadlines.map((headline, index) => (
          <div key={index} className="card">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h3 className="text-lg font-medium text-gray-900 mb-1">
                  {headline.title}
                </h3>

                {headline.original_title && (
                  <div className="bg-gray-50 p-3 rounded-lg mb-3">
                    <div className="text-sm text-gray-600 mb-1">Original:</div>
                    <div className="text-gray-800">{headline.original_title}</div>
                  </div>
                )}
                
                <div className="flex items-center flex-wrap gap-4 text-sm text-gray-600 mb-3">
                  <span className="flex items-center space-x-1">
                    <Globe className="h-4 w-4" />
                    <span>{headline.source}</span>
                  </span>
                  <span className="flex items-center space-x-1">
                    <Languages className="h-4 w-4" />
                    <span>{headline.language.toUpperCase()}</span>
                  </span>
                  {headline.published && (
                    <span className="flex items-center space-x-1">
                      <Calendar className="h-4 w-4" />
                      <span>{formatDate((headline as any).published)}</span>
                    </span>
                  )}
                </div>
              </div>

              <div className="ml-4">
                <a
                  href={headline.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-secondary flex items-center space-x-2"
                >
                  <ExternalLink className="h-4 w-4" />
                  <span>Read</span>
                </a>
              </div>
            </div>
          </div>
        ))}

        {filteredHeadlines.length === 0 && (
          <div className="card text-center py-12">
            <div className="text-gray-500">
              <Globe className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <div className="text-lg font-medium mb-2">No headlines found</div>
              <div className="text-sm">Try adjusting your search or filters</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Feeds 