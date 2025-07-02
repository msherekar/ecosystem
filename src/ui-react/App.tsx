import { useState, useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Header } from './components/Header'
import { Sidebar } from './components/Sidebar'
import { Footer } from './components/Footer'
import { Dashboard } from './pages/Dashboard'
import { RNASeqAnalysis } from './pages/RNASeqAnalysis'
import { SCRNASeqAnalysis } from './pages/SCRNASeqAnalysis'
import { ATACSeqAnalysis } from './pages/ATACSeqAnalysis'
import { ProteomicsAnalysis } from './pages/ProteomicsAnalysis'
import { ServerStatus } from './pages/ServerStatus'
import { MCPService } from './services/mcpService'
import { Toast, ToastProvider } from './components/ui/toast'

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [mcpStatus, setMCPStatus] = useState({
    connected: false,
    servers: {},
    loading: true
  })

  useEffect(() => {
    // Initialize MCP connection when app starts
    const initializeMCP = async () => {
      try {
        console.log('🔌 Initializing MCP connection...')
        
        // Suppress React DevTools message in development
        if (process.env.NODE_ENV === 'development') {
          console.info('💡 Tip: Install React DevTools extension for better debugging')
        }
        
        // Check if we're in Electron environment
        if (typeof window !== 'undefined' && (window as any).require) {
          await MCPService.initialize()
          
          // Get initial server status
          const status = await MCPService.getSystemStatus()
          if (status.success && status.data) {
            // Convert available_servers array to servers object format
            const servers: Record<string, any> = {}
            if (status.data.available_servers) {
              status.data.available_servers.forEach((serverName: string) => {
                servers[serverName] = { status: 'available' }
              })
            }
            setMCPStatus({
              connected: true,
              servers,
              loading: false
            })
          } else {
            setMCPStatus({
              connected: false,
              servers: {},
              loading: false
            })
          }
          
          console.log('✅ MCP connection established')
        } else {
          console.warn('⚠️ Not running in Electron environment')
          setMCPStatus(prev => ({ ...prev, loading: false }))
        }
      } catch (error) {
        console.error('❌ Failed to initialize MCP:', error)
        setMCPStatus(prev => ({ ...prev, loading: false }))
      }
    }

    initializeMCP()
  }, [])

  return (
    <ToastProvider>
      <div className="h-screen flex flex-col bg-background">
        <Header 
          onMenuToggle={() => setSidebarOpen(!sidebarOpen)}
          mcpStatus={mcpStatus}
        />
        
        <div className="flex flex-1 overflow-hidden">
          <Sidebar isOpen={sidebarOpen} mcpStatus={mcpStatus} />
          
          <main className="flex-1 overflow-y-auto">
            <div className="container mx-auto px-6 py-8">
              <Routes>
                <Route path="/" element={<Dashboard mcpStatus={mcpStatus} />} />
                <Route path="/rnaseq" element={<RNASeqAnalysis />} />
                <Route path="/scrnaseq" element={<SCRNASeqAnalysis />} />
                <Route path="/atacseq" element={<ATACSeqAnalysis />} />
                <Route path="/proteomics" element={<ProteomicsAnalysis />} />
                <Route path="/servers" element={<ServerStatus mcpStatus={mcpStatus} />} />
              </Routes>
            </div>
          </main>
        </div>
        
        <Footer />
      </div>
      <Toast />
    </ToastProvider>
  )
}

export default App
