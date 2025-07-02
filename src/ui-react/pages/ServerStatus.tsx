import React, { useState, useEffect } from 'react'
import { RefreshCw, Play, Square, AlertCircle } from 'lucide-react'
import { MCPService } from '../services/mcpService'
import { formatAnalysisType, formatServerStatus } from '../lib/utils'

interface ServerStatusProps {
  mcpStatus: {
    connected: boolean
    servers: Record<string, any>
    loading: boolean
  }
}

export function ServerStatus({ mcpStatus }: ServerStatusProps) {
  const [refreshing, setRefreshing] = useState(false)
  const [serverDetails, setServerDetails] = useState<Record<string, any>>({})

  const refreshStatus = async () => {
    setRefreshing(true)
    try {
      const response = await MCPService.getSystemStatus()
      if (response.success) {
        setServerDetails(response.data)
      }
    } catch (error) {
      console.error('Failed to refresh status:', error)
    } finally {
      setRefreshing(false)
    }
  }

  const handleServerAction = async (serverName: string, action: 'start' | 'stop') => {
    try {
      if (action === 'start') {
        await MCPService.startServer(serverName)
      } else {
        await MCPService.stopServer(serverName)
      }
      // Refresh status after action
      await refreshStatus()
    } catch (error) {
      console.error(`Failed to ${action} server:`, error)
    }
  }

  useEffect(() => {
    refreshStatus()
  }, [])

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">⚙️ Server Status</h1>
          <p className="text-gray-600">Monitor and manage MCP server instances</p>
        </div>
        <button
          onClick={refreshStatus}
          disabled={refreshing}
          className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Connection Status */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">MCP Connection</h2>
        <div className="flex items-center space-x-4">
          <div className={`h-4 w-4 rounded-full ${
            mcpStatus.connected ? 'bg-green-500' : 'bg-red-500'
          }`}></div>
          <div>
            <div className="font-medium">
              {mcpStatus.connected ? 'Connected' : 'Disconnected'}
            </div>
            <div className="text-sm text-gray-600">
              {mcpStatus.connected 
                ? `${Object.keys(mcpStatus.servers).length} servers available`
                : 'Unable to connect to MCP backend'
              }
            </div>
          </div>
        </div>
      </div>

      {/* Server Grid */}
      {mcpStatus.connected && Object.keys(mcpStatus.servers).length > 0 ? (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-6">Servers</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Object.entries(mcpStatus.servers).map(([serverName, server]: [string, any]) => (
              <div
                key={serverName}
                className="bg-white rounded-lg border border-gray-200 p-6"
              >
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="font-semibold text-gray-900">
                      {formatAnalysisType(serverName)}
                    </h3>
                    <p className="text-sm text-gray-600 capitalize">
                      {serverName} server
                    </p>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    server.status === 'running' 
                      ? 'bg-green-100 text-green-800' 
                      : server.status === 'stopped'
                      ? 'bg-gray-100 text-gray-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {server.status}
                  </span>
                </div>

                {/* Server Details */}
                <div className="space-y-2 mb-4">
                  {server.last_activity && (
                    <div className="text-xs text-gray-600">
                      Last activity: {new Date(server.last_activity).toLocaleString()}
                    </div>
                  )}
                  {server.capabilities && server.capabilities.length > 0 && (
                    <div className="text-xs text-gray-600">
                      Capabilities: {server.capabilities.join(', ')}
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex space-x-2">
                  {server.status === 'stopped' ? (
                    <button
                      onClick={() => handleServerAction(serverName, 'start')}
                      className="flex items-center px-3 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700"
                    >
                      <Play className="h-3 w-3 mr-1" />
                      Start
                    </button>
                  ) : server.status === 'running' ? (
                    <button
                      onClick={() => handleServerAction(serverName, 'stop')}
                      className="flex items-center px-3 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700"
                    >
                      <Square className="h-3 w-3 mr-1" />
                      Stop
                    </button>
                  ) : (
                    <div className="flex items-center px-3 py-1 bg-yellow-100 text-yellow-800 text-xs rounded">
                      <AlertCircle className="h-3 w-3 mr-1" />
                      Error
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Servers Available</h3>
          <p className="text-gray-600">
            {mcpStatus.connected 
              ? 'No MCP servers are currently registered'
              : 'Connect to MCP backend to view servers'
            }
          </p>
        </div>
      )}
    </div>
  )
} 