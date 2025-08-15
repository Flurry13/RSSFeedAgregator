import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { io, Socket } from 'socket.io-client'

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

export interface StatusUpdate {
  status: 'idle' | 'gathering' | 'gathered' | 'translating' | 'translated' | 'error'
  task: string
  progress: number
  total: number
  message: string
  timestamp: number
}

export interface LogMessage {
  level: 'info' | 'warning' | 'error' | 'success'
  message: string
  timestamp: number
}

interface HeadlinesContextType {
  headlines: Headline[]
  loading: boolean
  error: string | null
  status: StatusUpdate | null
  logMessages: LogMessage[]
  refreshHeadlines: () => Promise<void>
  translateHeadlines: () => Promise<void>
  startGathering: () => Promise<void>
  isConnected: boolean
}

const HeadlinesContext = createContext<HeadlinesContextType | undefined>(undefined)

export const useHeadlines = () => {
  const context = useContext(HeadlinesContext)
  if (context === undefined) {
    throw new Error('useHeadlines must be used within a HeadlinesProvider')
  }
  return context
}

interface HeadlinesProviderProps {
  children: ReactNode
}

export const HeadlinesProvider: React.FC<HeadlinesProviderProps> = ({ children }) => {
  const [headlines, setHeadlines] = useState<Headline[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<StatusUpdate | null>(null)
  const [logMessages, setLogMessages] = useState<LogMessage[]>([])
  const [socket, setSocket] = useState<Socket | null>(null)
  const [isConnected, setIsConnected] = useState(false)

  // Initialize WebSocket connection
  useEffect(() => {
    const newSocket = io('http://localhost:5050')
    
    newSocket.on('connect', () => {
      console.log('Connected to backend')
      setIsConnected(true)
      setError(null)
    })

    newSocket.on('disconnect', () => {
      console.log('Disconnected from backend')
      setIsConnected(false)
    })

    newSocket.on('status_update', (data: StatusUpdate) => {
      setStatus(data)
      console.log('Status update:', data)
    })

    newSocket.on('headlines_update', (data: { headlines: Headline[], message: string }) => {
      setHeadlines(data.headlines)
      console.log('Headlines update:', data.message)
    })

    newSocket.on('log_message', (data: LogMessage) => {
      setLogMessages(prev => [...prev, data].slice(-100)) // Keep last 100 messages
      console.log('Log message:', data)
    })

    newSocket.on('connected', (data: { message: string }) => {
      console.log('Backend message:', data.message)
    })

    setSocket(newSocket)

    return () => {
      newSocket.close()
    }
  }, [])

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

  const value: HeadlinesContextType = {
    headlines,
    loading,
    error,
    status,
    logMessages,
    refreshHeadlines,
    translateHeadlines,
    startGathering,
    isConnected,
  }

  return (
    <HeadlinesContext.Provider value={value}>
      {children}
    </HeadlinesContext.Provider>
  )
} 