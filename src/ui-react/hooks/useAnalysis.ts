/**
 * Custom hook for analysis workflow management
 *
 * Provides a simplified API for running analyses with real-time updates
 */

import { useCallback, useEffect } from 'react'
import { useAnalysisStore, AnalysisType } from '../store/analysisStore'
import { MCPService } from '../services/mcpService'

export function useAnalysis(analysisType: AnalysisType) {
  const store = useAnalysisStore()

  // Get state for this analysis type
  const uploadedFiles = store.uploadedFiles[analysisType]
  const analysisParams = store.analysisParams[analysisType]
  const analysisStatus = store.analysisStatus[analysisType]
  const analysisProgress = store.analysisProgress[analysisType]
  const currentStep = store.currentStep[analysisType]
  const results = store.results[analysisType]
  const plots = store.plots[analysisType]
  const error = store.errors[analysisType]
  const realTimeUpdates = store.realTimeUpdates[analysisType]

  // Set up real-time progress updates from MCP server
  useEffect(() => {
    const unsubscribe = MCPService.onServerStatusChange((status) => {
      // Extract progress for this analysis type if available
      const serverType = analysisType.replace('seq', '_seq') // Convert to server naming
      const serverStatus = status[serverType]

      if (serverStatus && serverStatus.status === 'running') {
        // Check if there's progress information
        const progress = (serverStatus as any).progress
        if (typeof progress === 'number') {
          store.setAnalysisProgress(analysisType, progress)
        }

        // Add real-time update
        store.addRealTimeUpdate(analysisType, {
          type: 'server_status',
          data: serverStatus
        })
      }
    })

    return unsubscribe
  }, [analysisType, store])

  // Run analysis with real-time progress
  const runAnalysis = useCallback(async () => {
    if (uploadedFiles.length === 0 || Object.keys(analysisParams).length === 0) {
      store.setError(analysisType, 'Missing required files or parameters')
      return null
    }

    store.setAnalysisStatus(analysisType, 'running')
    store.setAnalysisProgress(analysisType, 0)
    store.clearError(analysisType)

    try {
      // Read file contents
      const fileContents = await Promise.all(
        uploadedFiles.map(async (fileInfo) => {
          return new Promise((resolve, reject) => {
            const reader = new FileReader()
            reader.onload = (e) => resolve({
              name: fileInfo.name,
              type: fileInfo.type,
              size: fileInfo.size,
              content: e.target?.result
            })
            reader.onerror = reject
            reader.readAsText(fileInfo.file)
          })
        })
      )

      // Call appropriate MCP service method
      let response
      switch (analysisType) {
        case 'rnaseq':
          response = await MCPService.analyzeRNASeq({
            files: fileContents,
            parameters: analysisParams
          })
          break
        case 'scrnaseq':
          response = await MCPService.analyzeSCRNASeq({
            files: fileContents,
            parameters: analysisParams
          })
          break
        case 'atacseq':
          response = await MCPService.analyzeATACSeq({
            files: fileContents,
            parameters: analysisParams
          })
          break
        default:
          throw new Error(`Unsupported analysis type: ${analysisType}`)
      }

      if (response.success) {
        store.setAnalysisProgress(analysisType, 100)
        store.setAnalysisStatus(analysisType, 'completed')
        store.setResults(analysisType, response.data || response)
        store.setCurrentStep(analysisType, 'results')
        return response.data || response
      } else {
        throw new Error(response.error || 'Analysis failed')
      }
    } catch (err: any) {
      console.error('Analysis failed:', err)
      store.setAnalysisStatus(analysisType, 'error')
      store.setError(analysisType, err.message || 'Analysis failed')
      return null
    }
  }, [analysisType, uploadedFiles, analysisParams, store])

  // Generate plots
  const generatePlots = useCallback(async (plotTypes: string[]) => {
    if (!results) {
      store.setError(analysisType, 'No results available for plotting')
      return null
    }

    try {
      const plotResponse = await MCPService.createVisualization({
        data: results,
        plotTypes,
        analysisType
      })

      if (plotResponse.success && plotResponse.data?.plots) {
        store.setPlots(analysisType, plotResponse.data.plots)
        return plotResponse.data.plots
      } else {
        throw new Error(plotResponse.error || 'Plot generation failed')
      }
    } catch (err: any) {
      console.error('Plot generation failed:', err)
      store.setError(analysisType, err.message || 'Plot generation failed')
      return null
    }
  }, [analysisType, results, store])

  // Upload files
  const uploadFiles = useCallback((files: File[]) => {
    const analysisFiles = files.map(file => ({
      file,
      name: file.name,
      type: file.type,
      size: file.size
    }))
    store.setUploadedFiles(analysisType, analysisFiles)
    store.setCurrentStep(analysisType, 'parameters')
  }, [analysisType, store])

  // Set parameters
  const setParameters = useCallback((params: Record<string, any>) => {
    store.setAnalysisParams(analysisType, params)
    store.setCurrentStep(analysisType, 'analysis')
  }, [analysisType, store])

  // Navigate steps
  const goToStep = useCallback((step: typeof currentStep) => {
    store.setCurrentStep(analysisType, step)
  }, [analysisType, store])

  // Reset analysis
  const resetAnalysis = useCallback(() => {
    store.resetAnalysis(analysisType)
  }, [analysisType, store])

  return {
    // State
    uploadedFiles,
    analysisParams,
    analysisStatus,
    analysisProgress,
    currentStep,
    results,
    plots,
    error,
    realTimeUpdates,

    // Computed state
    isAnalyzing: analysisStatus === 'running',
    isComplete: analysisStatus === 'completed',
    hasError: analysisStatus === 'error',
    canRunAnalysis: uploadedFiles.length > 0 && Object.keys(analysisParams).length > 0,

    // Actions
    uploadFiles,
    setParameters,
    runAnalysis,
    generatePlots,
    goToStep,
    resetAnalysis
  }
}
