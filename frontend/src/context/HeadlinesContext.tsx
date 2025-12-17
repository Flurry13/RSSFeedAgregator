/**
 * HeadlinesContext - Unified context combining data and status
 * OPTIMIZED: Now uses split contexts internally to reduce re-renders
 */

import React, { ReactNode } from 'react'
import { StatusProvider, useStatus } from './StatusContext'
import { HeadlinesDataProvider, useHeadlinesData } from './HeadlinesDataContext'

// Re-export types for backward compatibility
export type { Headline } from './HeadlinesDataContext'
export type { StatusUpdate, LogMessage } from './StatusContext'

// Combined hook for components that need both
export const useHeadlines = () => {
  const dataContext = useHeadlinesData()
  const statusContext = useStatus()
  
  return {
    // Data context
    headlines: dataContext.headlines,
    loading: dataContext.loading,
    error: dataContext.error,
    refreshHeadlines: dataContext.refreshHeadlines,
    translateHeadlines: dataContext.translateHeadlines,
    startGathering: dataContext.startGathering,
    
    // Status context
    status: statusContext.status,
    logMessages: statusContext.logMessages,
    isConnected: statusContext.isConnected,
  }
}

interface HeadlinesProviderProps {
  children: ReactNode
}

// Combined provider that wraps both contexts
export const HeadlinesProvider: React.FC<HeadlinesProviderProps> = ({ children }) => {
  return (
    <StatusProvider>
      <HeadlinesDataProviderWrapper>
        {children}
      </HeadlinesDataProviderWrapper>
    </StatusProvider>
  )
}

// Wrapper to inject socket from StatusContext into HeadlinesDataProvider
const HeadlinesDataProviderWrapper: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { socket } = useStatus()
  
  return (
    <HeadlinesDataProvider socket={socket}>
      {children}
    </HeadlinesDataProvider>
  )
} 