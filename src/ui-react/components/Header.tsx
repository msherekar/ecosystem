import React from 'react'
import { Menu, Wifi, WifiOff, Activity } from 'lucide-react'
import { cn } from '../lib/utils'

interface HeaderProps {
  onMenuToggle: () => void
  mcpStatus: {
    connected: boolean
    servers: Record<string, any>
    loading: boolean
  }
}

export function Header({ onMenuToggle, mcpStatus }: HeaderProps) {
  const serverCount = Object.keys(mcpStatus.servers).length
  const runningServers = Object.values(mcpStatus.servers).filter(
    (server: any) => server.status === 'running'
  ).length

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        {/* Left side - Logo and menu */}
        <div className="flex items-center space-x-4">
          <button
            onClick={onMenuToggle}
            className="p-2 rounded-md hover:bg-gray-100 transition-colors"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="flex items-center space-x-2">
            <span className="text-2xl">🧬</span>
            <h1 className="text-xl font-bold text-gray-900">Gliaent</h1>
            <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded">
              v1.0.0
            </span>
          </div>
        </div>

        {/* Right side - MCP Status */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            {mcpStatus.loading ? (
              <Activity className="h-4 w-4 text-yellow-500 animate-spin" />
            ) : mcpStatus.connected ? (
              <Wifi className="h-4 w-4 text-green-500" />
            ) : (
              <WifiOff className="h-4 w-4 text-red-500" />
            )}
            <div className="text-sm">
              <div className={cn(
                "font-medium",
                mcpStatus.connected ? "text-green-700" : "text-red-700"
              )}>
                {mcpStatus.loading 
                  ? "Connecting..." 
                  : mcpStatus.connected 
                    ? "MCP Connected" 
                    : "MCP Disconnected"
                }
              </div>
              {mcpStatus.connected && (
                <div className="text-gray-500">
                  {runningServers}/{serverCount} servers running
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  )
} 