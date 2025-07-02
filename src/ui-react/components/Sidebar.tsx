import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { 
  BarChart3, 
  Microscope, 
  Dna, 
  TestTube, 
  Server, 
  Settings,
  ChevronRight
} from 'lucide-react'
import { cn, formatServerStatus } from '../lib/utils'

interface SidebarProps {
  isOpen: boolean
  mcpStatus: {
    connected: boolean
    servers: Record<string, any>
    loading: boolean
  }
}

const navigationItems = [
  {
    title: 'Analysis Types',
    items: [
      { name: 'RNA-seq Analysis', icon: BarChart3, path: '/rnaseq', emoji: '📊' },
      { name: 'scRNA-seq Analysis', icon: Microscope, path: '/scrnaseq', emoji: '🔬' },
      { name: 'ATAC-seq Analysis', icon: Dna, path: '/atacseq', emoji: '🧬' },
      { name: 'Proteomics Analysis', icon: TestTube, path: '/proteomics', emoji: '🧪' },
    ]
  },
  {
    title: 'System',
    items: [
      { name: 'Server Status', icon: Server, path: '/servers', emoji: '⚙️' },
      { name: 'Settings', icon: Settings, path: '/settings', emoji: '🔧' },
    ]
  }
]

export function Sidebar({ isOpen, mcpStatus }: SidebarProps) {
  const location = useLocation()

  if (!isOpen) {
    return (
      <aside className="w-16 bg-gray-50 border-r border-gray-200 flex flex-col items-center py-4 space-y-4">
        {navigationItems.flatMap(section => 
          section.items.map(item => (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "p-3 rounded-lg transition-colors",
                location.pathname === item.path
                  ? "bg-blue-100 text-blue-700"
                  : "text-gray-600 hover:bg-gray-100"
              )}
            >
              <span className="text-lg">{item.emoji}</span>
            </Link>
          ))
        )}
      </aside>
    )
  }

  return (
    <aside className="w-64 bg-gray-50 border-r border-gray-200 flex flex-col">
      <nav className="flex-1 px-4 py-6 space-y-6">
        {navigationItems.map((section) => (
          <div key={section.title}>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              {section.title}
            </h3>
            <div className="space-y-1">
              {section.items.map((item) => {
                const Icon = item.icon
                const isActive = location.pathname === item.path
                
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={cn(
                      "group flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors",
                      isActive
                        ? "bg-blue-100 text-blue-700"
                        : "text-gray-700 hover:bg-gray-100"
                    )}
                  >
                    <span className="mr-3 text-base">{item.emoji}</span>
                    <span className="flex-1">{item.name}</span>
                    {isActive && (
                      <ChevronRight className="h-4 w-4 text-blue-500" />
                    )}
                  </Link>
                )
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Server Status Summary */}
      <div className="p-4 border-t border-gray-200">
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
          MCP Servers
        </h4>
        <div className="space-y-1">
          {Object.entries(mcpStatus.servers).slice(0, 3).map(([serverName, server]: [string, any]) => (
            <div key={serverName} className="flex items-center justify-between text-xs">
              <span className="text-gray-600 truncate">{serverName}</span>
              <span className={cn(
                "px-2 py-1 rounded-full text-xs",
                server.status === 'running' ? "bg-green-100 text-green-800" :
                server.status === 'stopped' ? "bg-gray-100 text-gray-800" :
                "bg-red-100 text-red-800"
              )}>
                {formatServerStatus(server.status)}
              </span>
            </div>
          ))}
          {Object.keys(mcpStatus.servers).length > 3 && (
            <Link 
              to="/servers" 
              className="text-xs text-blue-600 hover:text-blue-800 block mt-2"
            >
              View all servers →
            </Link>
          )}
        </div>
      </div>
    </aside>
  )
} 