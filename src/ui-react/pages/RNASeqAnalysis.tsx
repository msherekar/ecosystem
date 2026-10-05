import { useEffect, useRef, useState } from 'react'
import { Upload, Play, Settings } from 'lucide-react'
import { MCPService } from '../services/mcpService'
import { AnalysisCard, AnalysisStatus } from '../components/bioinformatics/analysis-card'
import { ParameterForm, ParameterDefinition } from '../components/bioinformatics/parameter-form'
import { FileUpload } from '../components/ui/file-upload'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'

export function RNASeqAnalysis() {
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [results, setResults] = useState<any>(null)
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const [currentStep, setCurrentStep] = useState<'upload' | 'parameters' | 'analysis' | 'results'>('upload')
  const [analysisParams, setAnalysisParams] = useState<Record<string, any>>({})
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus>('pending')
  const [analysisProgress, setAnalysisProgress] = useState(0)
  const [plots, setPlots] = useState<any[]>([])

  /**
   * Run the analysis.
   *
   * Two bugs this had to fix:
   *
   * 1. `setAnalysisStatus('completed')` ran unconditionally and
   *    `response.success` was never checked anywhere on this page. Because
   *    backendManager RETURNS `{success: false, error}` rather than throwing,
   *    the catch block was unreachable for backend failures: a failed run
   *    showed a green "completed" with the error object rendered as results.
   * 2. `clearInterval` was only called on the happy path, after the awaits.
   *    A FileReader error skipped it and the progress timer ran forever,
   *    calling setState on a possibly-unmounted component.
   */
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [plotError, setPlotError] = useState<string | null>(null)
  /** Progress timer id, so unmount can clear it mid-analysis. */
  const progressTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  // Clears the progress timer if the component unmounts while running.
  useEffect(() => {
    return () => {
      if (progressTimer.current !== null) {
        clearInterval(progressTimer.current)
      }
    }
  }, [])

  const handleAnalysis = async () => {
    setIsAnalyzing(true)
    setAnalysisStatus('running')
    setAnalysisProgress(0)
    setErrorMessage(null)

    // Held in a ref so the unmount effect can clear it too.
    progressTimer.current = setInterval(() => {
      setAnalysisProgress(prev => (prev >= 95 ? 95 : prev + 5))
    }, 1000)

    try {
      const fileContents = await Promise.all(
        uploadedFiles.map(
          file =>
            new Promise((resolve, reject) => {
              const reader = new FileReader()
              reader.onload = e =>
                resolve({
                  name: file.name,
                  type: file.type,
                  size: file.size,
                  content: e.target?.result,
                })
              reader.onerror = () =>
                reject(new Error(`Could not read ${file.name}`))
              reader.readAsText(file)
            })
        )
      )

      const response = await MCPService.analyzeRNASeq({
        files: fileContents,
        parameters: analysisParams,
      })

      // The check that was missing.
      if (!response.success) {
        setAnalysisStatus('error')
        setErrorMessage(
          response.error ?? 'The analysis failed without reporting a reason.'
        )
        return
      }

      setAnalysisProgress(100)
      setAnalysisStatus('completed')
      setResults(response.data ?? null)
      setCurrentStep('results')
    } catch (error) {
      setAnalysisStatus('error')
      setErrorMessage(
        error instanceof Error ? error.message : String(error)
      )
    } finally {
      // In `finally`, so it runs on every path including a FileReader error.
      if (progressTimer.current !== null) {
        clearInterval(progressTimer.current)
        progressTimer.current = null
      }
      setIsAnalyzing(false)
    }
  }

  /** Generate plots from the analysis results. */
  const handleGeneratePlots = async () => {
    setPlotError(null)
    try {
      const plotResponse = await MCPService.createVisualization({
        data: results,
        plotTypes: ['volcano', 'heatmap', 'pca'],
        analysisType: 'rnaseq',
      })

      if (!plotResponse.success) {
        // Previously a silent no-op with only a console.error.
        setPlotError(
          plotResponse.error ?? 'Plot generation failed without a reason.'
        )
        return
      }
      const payload = plotResponse.data as { plots?: unknown[] } | undefined
      setPlots(payload?.plots ?? [])
    } catch (error) {
      setPlotError(error instanceof Error ? error.message : String(error))
    }
  }

  const rnaseqParameters: ParameterDefinition[] = [
    {
      key: 'pvalue_threshold',
      label: 'P-value Threshold',
      type: 'number',
      defaultValue: 0.05,
      min: 0.001,
      max: 1,
      step: 0.001,
      required: true,
      description: 'Statistical significance threshold for differential expression'
    },
    {
      key: 'log2fc_threshold',
      label: 'Log2 Fold Change Threshold',
      type: 'number',
      defaultValue: 1.0,
      min: 0.1,
      max: 10,
      step: 0.1,
      required: true,
      description: 'Minimum fold change threshold for significant genes'
    },
    {
      key: 'normalization_method',
      label: 'Normalization Method',
      type: 'select',
      defaultValue: 'deseq2',
      options: [
        { label: 'DESeq2', value: 'deseq2' },
        { label: 'EdgeR', value: 'edger' },
        { label: 'TMM', value: 'tmm' },
        { label: 'RLE', value: 'rle' }
      ],
      required: true,
      description: 'Method for normalizing read counts'
    },
    {
      key: 'filter_low_counts',
      label: 'Filter Low Count Genes',
      type: 'boolean',
      defaultValue: true,
      description: 'Remove genes with very low expression levels'
    },
    {
      key: 'min_count',
      label: 'Minimum Count Threshold',
      type: 'number',
      defaultValue: 10,
      min: 1,
      max: 100,
      description: 'Minimum read count required per gene'
    }
  ]

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">📊 RNA-seq Analysis</h1>
          <p className="text-gray-600">Analyze bulk RNA-seq data for differential expression</p>
        </div>
        <div className="flex space-x-3">
          <Button 
            variant="outline" 
            onClick={() => setCurrentStep('upload')}
            disabled={isAnalyzing}
          >
            <Upload className="h-4 w-4 mr-2" />
            Upload Data
          </Button>
          <Button 
            variant="outline" 
            onClick={() => setCurrentStep('parameters')}
            disabled={uploadedFiles.length === 0 || isAnalyzing}
          >
            <Settings className="h-4 w-4 mr-2" />
            Configure
          </Button>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center justify-between bg-white rounded-lg border border-gray-200 p-4">
        {[
          { key: 'upload', label: 'Upload Data', completed: uploadedFiles.length > 0 },
          { key: 'parameters', label: 'Set Parameters', completed: Object.keys(analysisParams).length > 0 },
          { key: 'analysis', label: 'Run Analysis', completed: analysisStatus === 'completed' },
          { key: 'results', label: 'View Results', completed: results !== null }
        ].map((step, index) => (
          <div key={step.key} className="flex items-center">
            <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium ${
              step.completed 
                ? 'bg-green-100 text-green-800' 
                : currentStep === step.key 
                  ? 'bg-blue-100 text-blue-800' 
                  : 'bg-gray-100 text-gray-600'
            }`}>
              {index + 1}
            </div>
            <span className={`ml-2 text-sm ${
              step.completed ? 'text-green-800' : currentStep === step.key ? 'text-blue-800' : 'text-gray-600'
            }`}>
              {step.label}
            </span>
            {index < 3 && <div className="w-8 h-px bg-gray-300 ml-4" />}
          </div>
        ))}
      </div>

      {/* Step Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Data Upload */}
        <div className="lg:col-span-1">
          <AnalysisCard
            title="Data Upload"
            description="Upload your count matrix and metadata files"
            status={uploadedFiles.length > 0 ? 'completed' : 'pending'}
            onConfigure={() => setCurrentStep('upload')}
          >
            {currentStep === 'upload' && (
              <FileUpload
                onFileSelect={setUploadedFiles}
                acceptedTypes={['.csv', '.tsv', '.txt', '.xlsx']}
                maxSize={500}
                multiple={true}
              />
            )}
          </AnalysisCard>
        </div>

        {/* Parameters */}
        <div className="lg:col-span-1">
          <AnalysisCard
            title="Analysis Parameters"
            description="Configure differential expression analysis settings"
            status={Object.keys(analysisParams).length > 0 ? 'completed' : 'pending'}
            onConfigure={() => setCurrentStep('parameters')}
            disabled={uploadedFiles.length === 0}
          >
            {currentStep === 'parameters' && (
              <ParameterForm
                title="RNA-seq Parameters"
                parameters={rnaseqParameters}
                initialValues={analysisParams}
                onSubmit={(values) => {
                  setAnalysisParams(values)
                  setCurrentStep('analysis')
                }}
              />
            )}
          </AnalysisCard>
        </div>

        {/* Analysis Execution */}
        <div className="lg:col-span-1">
          <AnalysisCard
            title="Run Analysis"
            description="Execute differential expression analysis"
            status={analysisStatus}
            progress={analysisProgress}
            onStart={handleAnalysis}
            onViewResults={() => setCurrentStep('results')}
            disabled={uploadedFiles.length === 0 || Object.keys(analysisParams).length === 0}
          />

          {/* The failure actually shown to the user. Previously a failed run
              displayed a green "completed" and the error object as results. */}
          {analysisStatus === 'error' && errorMessage && (
            <div
              role="alert"
              className="mt-4 rounded-lg border border-red-300 bg-red-50 p-4"
            >
              <h4 className="text-sm font-semibold text-red-800">
                Analysis failed
              </h4>
              <p className="mt-1 text-sm text-red-700 whitespace-pre-wrap">
                {errorMessage}
              </p>
              <button
                type="button"
                onClick={handleAnalysis}
                className="mt-3 text-sm font-medium text-red-800 underline"
              >
                Try again
              </button>
            </div>
          )}

          {plotError && (
            <div
              role="alert"
              className="mt-4 rounded-lg border border-amber-300 bg-amber-50 p-4"
            >
              <h4 className="text-sm font-semibold text-amber-900">
                Plots could not be generated
              </h4>
              <p className="mt-1 text-sm text-amber-800">{plotError}</p>
            </div>
          )}
        </div>
      </div>

      {/* Results Section */}
      {currentStep === 'results' && results && (
        <Card>
          <CardHeader>
            <CardTitle>Analysis Results</CardTitle>
            <CardDescription>Differential expression analysis</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">
                  {results?.total_genes || results?.summary?.total_genes || 'N/A'}
                </div>
                <div className="text-sm text-blue-800">Total Genes</div>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600">
                  {results?.upregulated || results?.summary?.upregulated || 'N/A'}
                </div>
                <div className="text-sm text-green-800">Upregulated</div>
              </div>
              <div className="text-center p-4 bg-red-50 rounded-lg">
                <div className="text-2xl font-bold text-red-600">
                  {results?.downregulated || results?.summary?.downregulated || 'N/A'}
                </div>
                <div className="text-sm text-red-800">Downregulated</div>
              </div>
            </div>
            
            {/* The cutoffs that produced these numbers, shown alongside
                them. A count of significant genes is uninterpretable without
                the alpha and fold-change thresholds behind it. */}
            {results?.params && (
              <div className="mt-4 rounded-lg bg-gray-50 p-4">
                <h4 className="mb-1 text-sm font-medium text-gray-700">
                  Significance criterion
                </h4>
                <p className="text-sm text-gray-600">
                  {results.significance_criterion ??
                    `adjusted p < ${results.params.alpha}, |log2FC| > ${results.params.log2fc_threshold}`}
                </p>
                {results.params.seed !== null && (
                  <p className="mt-1 text-xs text-gray-500">
                    Random seed {results.params.seed} — this run is reproducible.
                  </p>
                )}
              </div>
            )}
            <div className="mt-6 flex space-x-4">
              <Button variant="analysis">Download Results</Button>
              <Button variant="outline" onClick={handleGeneratePlots}>
                Generate Plots
              </Button>
              <Button variant="outline">Export Report</Button>
            </div>
            
            {/* Display generated plots */}
            {plots.length > 0 && (
              <div className="mt-6">
                <h4 className="text-lg font-medium text-gray-900 mb-4">Generated Plots</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {plots.map((plot, index) => (
                    <div key={index} className="border rounded-lg p-4">
                      <h5 className="font-medium mb-2">{plot.title || `Plot ${index + 1}`}</h5>
                      {plot.image ? (
                        <img src={plot.image} alt={plot.title} className="w-full rounded" />
                      ) : plot.html ? (
                        <div dangerouslySetInnerHTML={{ __html: plot.html }} />
                      ) : (
                        <div className="text-gray-500">Plot data: {JSON.stringify(plot)}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
} 