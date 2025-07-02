import React from 'react'
import { Link } from 'react-router-dom'
import { formatAnalysisType, formatServerStatus } from '../lib/utils'

interface DashboardProps {
  mcpStatus: {
    connected: boolean
    servers: Record<string, any>
    loading: boolean
  }
}

const analysisTypes = [
  {
    type: 'rnaseq',
    title: 'RNA-seq Analysis',
    description: 'Analyze bulk RNA-seq data for differential expression',
    path: '/rnaseq'
  },
  {
    type: 'scrnaseq', 
    title: 'scRNA-seq Analysis',
    description: 'Single-cell RNA-seq analysis and cell type identification',
    path: '/scrnaseq'
  },
  {
    type: 'atacseq',
    title: 'ATAC-seq Analysis', 
    description: 'Chromatin accessibility and peak calling analysis',
    path: '/atacseq'
  },
  {
    type: 'proteomics',
    title: 'Proteomics Analysis',
    description: 'Mass spectrometry data analysis and protein identification',
    path: '/proteomics'
  }
]

export function Dashboard({ mcpStatus }: DashboardProps) {
  const serverCount = Object.keys(mcpStatus.servers).length
  const runningServers = Object.values(mcpStatus.servers).filter(
    (server: any) => server.status === 'running'
  ).length

  return (
    <div className="space-y-8">
      {/* Welcome Section */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          Welcome to Gliaent
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          Your integrated bioinformatics analysis platform powered by MCP servers
        </p>
      </div>

      {/* System Status Card */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">System Status</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {mcpStatus.connected ? '🟢' : '🔴'}
            </div>
            <div className="text-sm text-gray-600 mt-1">
              MCP Connection
            </div>
            <div className="text-xs text-gray-500">
              {mcpStatus.connected ? 'Connected' : 'Disconnected'}
            </div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {runningServers}
            </div>
            <div className="text-sm text-gray-600 mt-1">
              Active Servers
            </div>
            <div className="text-xs text-gray-500">
              {runningServers} of {serverCount} running
            </div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">
              {analysisTypes.length}
            </div>
            <div className="text-sm text-gray-600 mt-1">
              Analysis Types
            </div>
            <div className="text-xs text-gray-500">
              Available
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-6">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {analysisTypes.map((analysis) => (
            <Link
              key={analysis.type}
              to={analysis.path}
              className="block bg-white rounded-lg border border-gray-200 p-6 hover:shadow-md transition-shadow"
            >
              <div className="text-center">
                <div className="text-3xl mb-3">
                  {formatAnalysisType(analysis.type).split(' ')[0]}
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {analysis.title}
                </h3>
                <p className="text-sm text-gray-600">
                  {analysis.description}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Server Status Grid */}
      {mcpStatus.connected && Object.keys(mcpStatus.servers).length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900">Server Status</h2>
            <Link 
              to="/servers" 
              className="text-blue-600 hover:text-blue-800 text-sm font-medium"
            >
              View All →
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(mcpStatus.servers).slice(0, 6).map(([serverName, server]: [string, any]) => (
              <div
                key={serverName}
                className="bg-white rounded-lg border border-gray-200 p-4"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-gray-900">
                      {formatAnalysisType(serverName)}
                    </h3>
                    <p className="text-sm text-gray-600 capitalize">
                      {serverName} server
                    </p>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    server.status === 'running' ? 'bg-green-100 text-green-800' :
                    server.status === 'stopped' ? 'bg-gray-100 text-gray-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {server.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
} 