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
    if (!isConnected) return <WifiOff className="h-5 w-5 text-red-500" />
    
    switch (status?.status) {
      case 'gathering':
        return <Globe className="h-5 w-5 text-blue-500 animate-pulse" />
      case 'translating':
        return <Languages className="h-5 w-5 text-green-500 animate-pulse" />
      case 'gathered':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'translated':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-500" />
      default:
        return <Wifi className="h-5 w-5 text-gray-500" />
    }
  }

  const getStatusColor = () => {
    if (!isConnected) return 'bg-red-100 border-red-300'
    
    switch (status?.status) {
      case 'gathering':
        return 'bg-blue-100 border-blue-300'
      case 'translating':
        return 'bg-green-100 border-green-300'
      case 'gathered':
        return 'bg-green-100 border-green-300'
      case 'translated':
        return 'bg-green-100 border-green-300'
      case 'error':
        return 'bg-red-100 border-red-300'
      default:
        return 'bg-gray-100 border-gray-300'
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
              <div className="font-medium text-gray-900">
                {isConnected ? 'Connected to Backend' : 'Disconnected from Backend'}
              </div>
              <div className="text-sm text-gray-600">
                {status?.task || 'Ready'}
              </div>
            </div>
          </div>
          
          <div className="flex space-x-2">
            <button
              onClick={startGathering}
              disabled={!isConnected || status?.status === 'gathering'}
              className="btn-primary flex items-center space-x-2 disabled:opacity-50"
            >
              <Play className="h-4 w-4" />
              <span>Gather</span>
            </button>
            
            <button
              onClick={translateHeadlines}
              disabled={!isConnected || status?.status === 'translating'}
              className="btn-secondary flex items-center space-x-2 disabled:opacity-50"
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
          <div className="mb-2 flex items-center justify-between">
            <div className="font-medium text-gray-900">{status.task}</div>
            <div className="text-sm text-gray-600">
              {status.progress} / {status.total} ({getProgressPercentage()}%)
            </div>
          </div>
          
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-primary-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${getProgressPercentage()}%` }}
            ></div>
          </div>
          
          <div className="mt-2 text-sm text-gray-600">
            {status.message}
          </div>
        </div>
      )}

      {/* Log Messages */}
      {logMessages.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Live Log</h3>
            <div className="text-sm text-gray-500">
              {logMessages.length} messages
            </div>
          </div>
          
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {logMessages.map((log, index) => (
              <div key={index} className="flex items-start space-x-2 p-2 rounded bg-gray-50">
                <div className="flex-shrink-0 mt-1">
                  {log.level === 'success' && <CheckCircle className="h-4 w-4 text-green-500" />}
                  {log.level === 'warning' && <AlertCircle className="h-4 w-4 text-yellow-500" />}
                  {log.level === 'error' && <AlertCircle className="h-4 w-4 text-red-500" />}
                  {log.level === 'info' && <Loader className="h-4 w-4 text-blue-500" />}
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-gray-900">{log.message}</div>
                  <div className="text-xs text-gray-500">
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