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

        // Check if we're in Electron environment
        if (typeof window !== 'undefined' && (window as any).require) {
          await MCPService.initialize()

          // Subscribe to MCP ready event (sent when backend first connects)
          const unsubscribeMCPReady = MCPService.onMCPReady((data) => {
            console.log('📡 Received MCP ready event:', data)

            if (data && data.available_servers) {
              const servers: Record<string, any> = {}
              data.available_servers.forEach((serverName: string) => {
                servers[serverName] = { status: 'available' }
              })

              setMCPStatus({
                connected: true,
                servers,
                loading: false
              })
              console.log('✅ MCP connection established via ready event')
            }
          })

          // Subscribe to system status updates (periodic updates)
          const unsubscribeStatus = MCPService.onSystemStatusChange((statusData) => {
            console.log('📡 Received system status update:', statusData)

            if (statusData && statusData.available_servers) {
              const servers: Record<string, any> = {}
              statusData.available_servers.forEach((serverName: string) => {
                servers[serverName] = { status: 'available' }
              })

              setMCPStatus({
                connected: true,
                servers,
                loading: false
              })
              console.log('✅ MCP status updated in UI')
            }
          })

          // Also try to get initial status (with retry)
          let retries = 5
          const getStatus = async () => {
            for (let i = 0; i < retries; i++) {
              try {
                const status = await MCPService.getSystemStatus()
                if (status.success && status.data) {
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
                  console.log('✅ MCP connection established (initial poll)')
                  return
                }
              } catch (err) {
                console.log(`⏳ Waiting for MCP backend... (attempt ${i + 1}/${retries})`)
              }
              await new Promise(resolve => setTimeout(resolve, 2000))
            }
            setMCPStatus({ connected: false, servers: {}, loading: false })
          }

          getStatus()

          // Return cleanup function that unsubscribes from both events
          return () => {
            unsubscribeMCPReady()
            unsubscribeStatus()
          }
        } else {
          console.warn('⚠️ Not running in Electron environment')
          setMCPStatus(prev => ({ ...prev, loading: false }))
        }
      } catch (error) {
        console.error('❌ Failed to initialize MCP:', error)
        setMCPStatus(prev => ({ ...prev, loading: false, connected: false }))
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
