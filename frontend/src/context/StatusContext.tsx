import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { io, Socket } from 'socket.io-client'

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

interface StatusContextType {
  status: StatusUpdate | null
  logMessages: LogMessage[]
  isConnected: boolean
  socket: Socket | null
}

const StatusContext = createContext<StatusContextType | undefined>(undefined)

export const useStatus = () => {
  const context = useContext(StatusContext)
  if (context === undefined) {
    throw new Error('useStatus must be used within a StatusProvider')
  }
  return context
}

interface StatusProviderProps {
  children: ReactNode
}

export const StatusProvider: React.FC<StatusProviderProps> = ({ children }) => {
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
    })

    newSocket.on('disconnect', () => {
      console.log('Disconnected from backend')
      setIsConnected(false)
    })

    newSocket.on('status_update', (data: StatusUpdate) => {
      setStatus(data)
      console.log('Status update:', data)
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

  const value: StatusContextType = {
    status,
    logMessages,
    isConnected,
    socket,
  }

  return (
    <StatusContext.Provider value={value}>
      {children}
    </StatusContext.Provider>
  )
}

