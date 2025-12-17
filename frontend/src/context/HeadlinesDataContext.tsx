import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { Socket } from 'socket.io-client'

export interface Headline {
  title: string
  link: string
  language: string
  source: string
  group: string
  country: string
  original_title?: string
  translated?: boolean
  published?: string
}

interface HeadlinesDataContextType {
  headlines: Headline[]
  setHeadlines: (headlines: Headline[]) => void
  loading: boolean
  setLoading: (loading: boolean) => void
  error: string | null
  setError: (error: string | null) => void
  refreshHeadlines: () => Promise<void>
  translateHeadlines: () => Promise<void>
  startGathering: () => Promise<void>
  socket: Socket | null
}

const HeadlinesDataContext = createContext<HeadlinesDataContextType | undefined>(undefined)

export const useHeadlinesData = () => {
  const context = useContext(HeadlinesDataContext)
  if (context === undefined) {
    throw new Error('useHeadlinesData must be used within a HeadlinesDataProvider')
  }
  return context
}

interface HeadlinesDataProviderProps {
  children: ReactNode
  socket: Socket | null
}

export const HeadlinesDataProvider: React.FC<HeadlinesDataProviderProps> = ({ children, socket }) => {
  const [headlines, setHeadlines] = useState<Headline[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Listen for headlines updates via WebSocket
  useEffect(() => {
    if (!socket) return
    
    const handleHeadlinesUpdate = (data: { headlines: Headline[], message: string }) => {
      setHeadlines(data.headlines)
      console.log('Headlines update:', data.message)
    }
    
    socket.on('headlines_update', handleHeadlinesUpdate)
    
    return () => {
      socket.off('headlines_update', handleHeadlinesUpdate)
    }
  }, [socket])

  const refreshHeadlines = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('http://localhost:5050/api/headlines')
      if (response.ok) {
        const data = await response.json()
        setHeadlines(data.headlines)
      } else {
        throw new Error('Failed to fetch headlines')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const startGathering = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('http://localhost:5050/api/gather?translate=1', { method: 'POST' })
      if (response.ok) {
        const data = await response.json()
        console.log('Gathering started:', data.message)
      } else {
        throw new Error('Failed to start gathering')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start gathering')
    } finally {
      setLoading(false)
    }
  }

  const translateHeadlines = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('http://localhost:5050/api/translate', { method: 'POST' })
      if (response.ok) {
        const data = await response.json()
        console.log('Translation started:', data.message)
      } else {
        throw new Error('Failed to start translation')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start translation')
    } finally {
      setLoading(false)
    }
  }

  const value: HeadlinesDataContextType = {
    headlines,
    setHeadlines,
    loading,
    setLoading,
    error,
    setError,
    refreshHeadlines,
    translateHeadlines,
    startGathering,
    socket,
  }

  return (
    <HeadlinesDataContext.Provider value={value}>
      {children}
    </HeadlinesDataContext.Provider>
  )
}

