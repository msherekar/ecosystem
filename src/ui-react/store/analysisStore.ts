/**
 * Zustand Store for Analysis State Management
 *
 * Centralized state management for all analysis workflows
 */

import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'

export type AnalysisType = 'rnaseq' | 'scrnaseq' | 'atacseq' | 'proteomics'
export type AnalysisStatus = 'pending' | 'running' | 'completed' | 'error'
export type AnalysisStep = 'upload' | 'parameters' | 'analysis' | 'results'

export interface AnalysisFile {
  file: File
  name: string
  type: string
  size: number
  content?: any
}

export interface AnalysisState {
  // Current analysis type
  currentAnalysisType: AnalysisType | null

  // Files management
  uploadedFiles: Record<AnalysisType, AnalysisFile[]>

  // Parameters management
  analysisParams: Record<AnalysisType, Record<string, any>>

  // Analysis status
  analysisStatus: Record<AnalysisType, AnalysisStatus>
  analysisProgress: Record<AnalysisType, number>
  currentStep: Record<AnalysisType, AnalysisStep>

  // Results storage
  results: Record<AnalysisType, any>
  plots: Record<AnalysisType, any[]>

  // Error handling
  errors: Record<AnalysisType, string | null>

  // Real-time updates from backend
  realTimeUpdates: Record<AnalysisType, any[]>

  // Actions
  setCurrentAnalysisType: (type: AnalysisType) => void
  setUploadedFiles: (type: AnalysisType, files: AnalysisFile[]) => void
  addUploadedFile: (type: AnalysisType, file: AnalysisFile) => void
  removeUploadedFile: (type: AnalysisType, fileName: string) => void
  clearUploadedFiles: (type: AnalysisType) => void

  setAnalysisParams: (type: AnalysisType, params: Record<string, any>) => void
  updateAnalysisParam: (type: AnalysisType, key: string, value: any) => void

  setAnalysisStatus: (type: AnalysisType, status: AnalysisStatus) => void
  setAnalysisProgress: (type: AnalysisType, progress: number) => void
  setCurrentStep: (type: AnalysisType, step: AnalysisStep) => void

  setResults: (type: AnalysisType, results: any) => void
  setPlots: (type: AnalysisType, plots: any[]) => void
  addPlot: (type: AnalysisType, plot: any) => void

  setError: (type: AnalysisType, error: string | null) => void
  clearError: (type: AnalysisType) => void

  addRealTimeUpdate: (type: AnalysisType, update: any) => void
  clearRealTimeUpdates: (type: AnalysisType) => void

  // Reset functions
  resetAnalysis: (type: AnalysisType) => void
  resetAllAnalyses: () => void
}

const initialState = {
  currentAnalysisType: null,
  uploadedFiles: {
    rnaseq: [],
    scrnaseq: [],
    atacseq: [],
    proteomics: []
  },
  analysisParams: {
    rnaseq: {},
    scrnaseq: {},
    atacseq: {},
    proteomics: {}
  },
  analysisStatus: {
    rnaseq: 'pending' as AnalysisStatus,
    scrnaseq: 'pending' as AnalysisStatus,
    atacseq: 'pending' as AnalysisStatus,
    proteomics: 'pending' as AnalysisStatus
  },
  analysisProgress: {
    rnaseq: 0,
    scrnaseq: 0,
    atacseq: 0,
    proteomics: 0
  },
  currentStep: {
    rnaseq: 'upload' as AnalysisStep,
    scrnaseq: 'upload' as AnalysisStep,
    atacseq: 'upload' as AnalysisStep,
    proteomics: 'upload' as AnalysisStep
  },
  results: {
    rnaseq: null,
    scrnaseq: null,
    atacseq: null,
    proteomics: null
  },
  plots: {
    rnaseq: [],
    scrnaseq: [],
    atacseq: [],
    proteomics: []
  },
  errors: {
    rnaseq: null,
    scrnaseq: null,
    atacseq: null,
    proteomics: null
  },
  realTimeUpdates: {
    rnaseq: [],
    scrnaseq: [],
    atacseq: [],
    proteomics: []
  }
}

export const useAnalysisStore = create<AnalysisState>()(
  devtools(
    persist(
      (set) => ({
        ...initialState,

        setCurrentAnalysisType: (type) => set({ currentAnalysisType: type }),

        setUploadedFiles: (type, files) =>
          set((state) => ({
            uploadedFiles: {
              ...state.uploadedFiles,
              [type]: files
            }
          })),

        addUploadedFile: (type, file) =>
          set((state) => ({
            uploadedFiles: {
              ...state.uploadedFiles,
              [type]: [...state.uploadedFiles[type], file]
            }
          })),

        removeUploadedFile: (type, fileName) =>
          set((state) => ({
            uploadedFiles: {
              ...state.uploadedFiles,
              [type]: state.uploadedFiles[type].filter(f => f.name !== fileName)
            }
          })),

        clearUploadedFiles: (type) =>
          set((state) => ({
            uploadedFiles: {
              ...state.uploadedFiles,
              [type]: []
            }
          })),

        setAnalysisParams: (type, params) =>
          set((state) => ({
            analysisParams: {
              ...state.analysisParams,
              [type]: params
            }
          })),

        updateAnalysisParam: (type, key, value) =>
          set((state) => ({
            analysisParams: {
              ...state.analysisParams,
              [type]: {
                ...state.analysisParams[type],
                [key]: value
              }
            }
          })),

        setAnalysisStatus: (type, status) =>
          set((state) => ({
            analysisStatus: {
              ...state.analysisStatus,
              [type]: status
            }
          })),

        setAnalysisProgress: (type, progress) =>
          set((state) => ({
            analysisProgress: {
              ...state.analysisProgress,
              [type]: progress
            }
          })),

        setCurrentStep: (type, step) =>
          set((state) => ({
            currentStep: {
              ...state.currentStep,
              [type]: step
            }
          })),

        setResults: (type, results) =>
          set((state) => ({
            results: {
              ...state.results,
              [type]: results
            }
          })),

        setPlots: (type, plots) =>
          set((state) => ({
            plots: {
              ...state.plots,
              [type]: plots
            }
          })),

        addPlot: (type, plot) =>
          set((state) => ({
            plots: {
              ...state.plots,
              [type]: [...state.plots[type], plot]
            }
          })),

        setError: (type, error) =>
          set((state) => ({
            errors: {
              ...state.errors,
              [type]: error
            }
          })),

        clearError: (type) =>
          set((state) => ({
            errors: {
              ...state.errors,
              [type]: null
            }
          })),

        addRealTimeUpdate: (type, update) =>
          set((state) => ({
            realTimeUpdates: {
              ...state.realTimeUpdates,
              [type]: [...state.realTimeUpdates[type], { ...update, timestamp: Date.now() }]
            }
          })),

        clearRealTimeUpdates: (type) =>
          set((state) => ({
            realTimeUpdates: {
              ...state.realTimeUpdates,
              [type]: []
            }
          })),

        resetAnalysis: (type) =>
          set((state) => ({
            uploadedFiles: {
              ...state.uploadedFiles,
              [type]: []
            },
            analysisParams: {
              ...state.analysisParams,
              [type]: {}
            },
            analysisStatus: {
              ...state.analysisStatus,
              [type]: 'pending'
            },
            analysisProgress: {
              ...state.analysisProgress,
              [type]: 0
            },
            currentStep: {
              ...state.currentStep,
              [type]: 'upload'
            },
            results: {
              ...state.results,
              [type]: null
            },
            plots: {
              ...state.plots,
              [type]: []
            },
            errors: {
              ...state.errors,
              [type]: null
            },
            realTimeUpdates: {
              ...state.realTimeUpdates,
              [type]: []
            }
          })),

        resetAllAnalyses: () => set(initialState)
      }),
      {
        name: 'gliaent-analysis-storage',
        partialize: (state) => ({
          // Only persist results and params, not progress or status
          analysisParams: state.analysisParams,
          results: state.results
        })
      }
    )
  )
)
