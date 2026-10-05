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
    loading: true,
    error: null as string | null
  })

  useEffect(() => {
    let cancelled = false

    /**
     * Connect to the backend and read its initial status.
     *
     * Three fixes here:
     *
     * 1. `process.env.NODE_ENV` was read in the renderer. That only resolved
     *    because nodeIntegration leaked Node's `process` in, and would have
     *    thrown "process is not defined" the moment contextIsolation was
     *    turned on — killing app startup. Build-time flags now come through
     *    the preload bridge.
     * 2. The Electron check tested `(window as any).require`, which no longer
     *    exists with contextIsolation. It tests for the bridge instead.
     * 3. The error state carried no message, so a backend that failed to
     *    start was indistinguishable from one still booting.
     */
    const initializeMCP = async () => {
      if (typeof window === 'undefined' || !window.gliaent) {
        setMCPStatus({
          connected: false,
          servers: {},
          loading: false,
          error:
            'Not running inside the Gliaent desktop app, so the analysis '
            + 'backend is unavailable.',
        })
        return
      }

      try {
        await MCPService.initialize()

        const status = await MCPService.getSystemStatus()
        if (cancelled) return

        if (!status.success) {
          setMCPStatus({
            connected: false,
            servers: {},
            loading: false,
            error: status.error ?? 'The analysis backend did not respond.',
          })
          return
        }

        // `status.data` is now populated: four main-process handlers used to
        // return `status`/`servers` instead, so this branch never ran and the
        // UI reported "disconnected" against a healthy backend.
        const payload = (status.data ?? {}) as {
          available_servers?: string[]
          active_servers?: string[]
        }
        const active = new Set(payload.active_servers ?? [])
        const servers: Record<string, { status: string }> = {}
        for (const name of payload.available_servers ?? []) {
          servers[name] = { status: active.has(name) ? 'running' : 'available' }
        }

        setMCPStatus({ connected: true, servers, loading: false, error: null })
      } catch (error) {
        if (cancelled) return
        setMCPStatus({
          connected: false,
          servers: {},
          loading: false,
          error: error instanceof Error ? error.message : String(error),
        })
      }
    }

    initializeMCP()

    // Live backend status, so a backend that dies or recovers after startup
    // is reflected without the user hitting Refresh on another page. There
    // was no re-poll and no subscription at all before.
    const unsubscribe = window.gliaent?.on
      ? MCPService.onBackendStatusChange(({ status, message }) => {
          if (cancelled) return
          if (status === 'connected') {
            setMCPStatus(prev => ({ ...prev, connected: true, error: null }))
          } else {
            setMCPStatus(prev => ({
              ...prev,
              connected: false,
              error: message ?? 'The analysis backend disconnected.',
            }))
          }
        })
      : () => {}

    return () => {
      cancelled = true
      unsubscribe()
    }
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
