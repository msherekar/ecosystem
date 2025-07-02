import React from 'react'

export function Footer() {
  return (
    <footer className="bg-gray-50 border-t border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between text-sm text-gray-600">
        <div>
          © 2024 Gliaent - Bioinformatics Analysis Platform
        </div>
        <div className="flex items-center space-x-4">
          <span>React UI Mode</span>
          <span className="text-gray-400">|</span>
          <span>MCP Backend</span>
        </div>
      </div>
    </footer>
  )
} 