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
        <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 via-cyan-300 to-blue-500 bg-clip-text text-transparent">
          Feeds
        </h1>
        <p className="text-gray-300 mt-2">Browse and search through all collected headlines</p>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Search */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Search</label>
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
            <label className="block text-sm font-medium text-gray-300 mb-2">Language</label>
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
            <label className="block text-sm font-medium text-gray-300 mb-2">Source</label>
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
        <div className="mt-4 pt-4 border-t border-white/10">
          <div className="text-sm text-gray-400">
            Showing <span className="text-blue-400 font-medium">{filteredHeadlines.length}</span> of <span className="text-blue-400 font-medium">{headlines.length}</span> headlines
          </div>
        </div>
      </div>

      {/* Headlines List */}
      <div className="space-y-4">
        {filteredHeadlines.map((headline, index) => (
          <div key={index} className="card hover:bg-white/10 transition-all duration-300 group">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <h3 className="text-lg font-medium text-white mb-2 group-hover:text-blue-400 transition-colors">
                  {headline.title}
                </h3>

                {headline.original_title && (
                  <div className="bg-white/5 p-3 rounded-lg border border-white/10 mb-3 backdrop-blur-sm">
                    <div className="text-sm text-gray-400 mb-1">Original:</div>
                    <div className="text-gray-200">{headline.original_title}</div>
                  </div>
                )}
                
                <div className="flex items-center flex-wrap gap-4 text-sm text-gray-400">
                  <span className="flex items-center space-x-1">
                    <Globe className="h-4 w-4 text-blue-400" />
                    <span>{headline.source}</span>
                  </span>
                  <span className="flex items-center space-x-1">
                    <Languages className="h-4 w-4 text-green-400" />
                    <span>{headline.language.toUpperCase()}</span>
                  </span>
                  {headline.published && (
                    <span className="flex items-center space-x-1">
                      <Calendar className="h-4 w-4 text-purple-400" />
                      <span>{formatDate((headline as any).published)}</span>
                    </span>
                  )}
                  {headline.translated && (
                    <span className="glass-badge bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-400 border-green-400/30">
                      Translated
                    </span>
                  )}
                </div>
              </div>

              <div className="flex-shrink-0">
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
            <div className="text-gray-400">
              <div className="relative inline-block">
                <Globe className="h-16 w-16 mx-auto mb-4 text-blue-500/30" />
                <div className="absolute inset-0 blur-xl bg-blue-500/20"></div>
              </div>
              <div className="text-lg font-medium mb-2 text-gray-300">No headlines found</div>
              <div className="text-sm">Try adjusting your search or filters</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Feeds 