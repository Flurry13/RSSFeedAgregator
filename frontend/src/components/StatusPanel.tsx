import React from 'react'
import { useHeadlines } from '../context/HeadlinesContext'
import { 
  Wifi, 
  WifiOff, 
  Play, 
  CheckCircle, 
  AlertCircle, 
  Loader,
  Globe,
  Languages
} from 'lucide-react'

const StatusPanel: React.FC = () => {
  const { status, logMessages, isConnected, startGathering, translateHeadlines } = useHeadlines()

  const getStatusIcon = () => {
    if (!isConnected) return <WifiOff className="h-5 w-5 text-red-400" />
    
    switch (status?.status) {
      case 'gathering':
        return <Globe className="h-5 w-5 text-blue-400 animate-pulse drop-shadow-[0_0_8px_rgba(59,130,246,0.6)]" />
      case 'translating':
        return <Languages className="h-5 w-5 text-green-400 animate-pulse drop-shadow-[0_0_8px_rgba(34,197,94,0.6)]" />
      case 'gathered':
        return <CheckCircle className="h-5 w-5 text-green-400" />
      case 'translated':
        return <CheckCircle className="h-5 w-5 text-green-400" />
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-400" />
      default:
        return <Wifi className="h-5 w-5 text-gray-400" />
    }
  }

  const getStatusColor = () => {
    if (!isConnected) return 'bg-red-500/10 border-red-500/30'
    
    switch (status?.status) {
      case 'gathering':
        return 'bg-blue-500/10 border-blue-400/30'
      case 'translating':
        return 'bg-green-500/10 border-green-400/30'
      case 'gathered':
        return 'bg-green-500/10 border-green-400/30'
      case 'translated':
        return 'bg-green-500/10 border-green-400/30'
      case 'error':
        return 'bg-red-500/10 border-red-500/30'
      default:
        return 'bg-white/5 border-white/10'
    }
  }

  const getProgressPercentage = () => {
    if (!status || status.total === 0) return 0
    return Math.round((status.progress / status.total) * 100)
  }

  return (
    <div className="space-y-4">
      {/* Connection Status */}
      <div className={`card border-2 ${getStatusColor()}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {getStatusIcon()}
            <div>
              <div className="font-medium text-white">
                {isConnected ? 'Connected to Backend' : 'Disconnected from Backend'}
              </div>
              <div className="text-sm text-gray-400">
                {status?.task || 'Ready'}
              </div>
            </div>
          </div>
          
          <div className="flex space-x-2">
            <button
              onClick={startGathering}
              disabled={!isConnected || status?.status === 'gathering'}
              className="btn-primary flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Play className="h-4 w-4" />
              <span>Gather</span>
            </button>
            
            <button
              onClick={translateHeadlines}
              disabled={!isConnected || status?.status === 'translating'}
              className="btn-secondary flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Languages className="h-4 w-4" />
              <span>Translate</span>
            </button>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      {status && (status.status === 'gathering' || status.status === 'translating') && (
        <div className="card">
          <div className="mb-3 flex items-center justify-between">
            <div className="font-medium text-white">{status.task}</div>
            <div className="text-sm text-gray-400">
              {status.progress} / {status.total} ({getProgressPercentage()}%)
            </div>
          </div>
          
          <div className="w-full bg-white/10 rounded-full h-3 border border-white/20 overflow-hidden backdrop-blur-sm">
            <div 
              className="bg-gradient-to-r from-blue-500 to-cyan-500 h-full rounded-full transition-all duration-300 shadow-[0_0_15px_rgba(59,130,246,0.5)]"
              style={{ width: `${getProgressPercentage()}%` }}
            ></div>
          </div>
          
          <div className="mt-3 text-sm text-gray-300">
            {status.message}
          </div>
        </div>
      )}

      {/* Log Messages */}
      {logMessages.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
              Live Log
            </h3>
            <div className="text-sm text-gray-400">
              {logMessages.length} messages
            </div>
          </div>
          
          <div className="space-y-2 max-h-64 overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
            {logMessages.map((log, index) => (
              <div key={index} className="flex items-start space-x-2 p-3 rounded-lg bg-white/5 border border-white/10 backdrop-blur-sm hover:bg-white/10 transition-all">
                <div className="flex-shrink-0 mt-1">
                  {log.level === 'success' && <CheckCircle className="h-4 w-4 text-green-400" />}
                  {log.level === 'warning' && <AlertCircle className="h-4 w-4 text-yellow-400" />}
                  {log.level === 'error' && <AlertCircle className="h-4 w-4 text-red-400" />}
                  {log.level === 'info' && <Loader className="h-4 w-4 text-blue-400" />}
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-white font-mono">{log.message}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    {new Date(log.timestamp * 1000).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default StatusPanel 