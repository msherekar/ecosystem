import React from 'react'
import { Upload, Settings } from 'lucide-react'
import { useAnalysis } from '../hooks/useAnalysis'
import { AnalysisCard } from '../components/bioinformatics/analysis-card'
import { ParameterForm, ParameterDefinition } from '../components/bioinformatics/parameter-form'
import { FileUpload } from '../components/ui/file-upload'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'

export function SCRNASeqAnalysis() {
  const {
    uploadedFiles,
    analysisParams,
    analysisStatus,
    analysisProgress,
    currentStep,
    results,
    plots,
    isAnalyzing,
    canRunAnalysis,
    uploadFiles,
    setParameters,
    runAnalysis,
    generatePlots,
    goToStep
  } = useAnalysis('scrnaseq')

  const scrnaseqParameters: ParameterDefinition[] = [
    {
      key: 'min_genes',
      label: 'Minimum Genes per Cell',
      type: 'number',
      defaultValue: 200,
      min: 50,
      max: 5000,
      step: 50,
      required: true,
      description: 'Filter cells with fewer than this many detected genes'
    },
    {
      key: 'min_cells',
      label: 'Minimum Cells per Gene',
      type: 'number',
      defaultValue: 3,
      min: 1,
      max: 100,
      step: 1,
      required: true,
      description: 'Filter genes detected in fewer than this many cells'
    },
    {
      key: 'max_mito_pct',
      label: 'Max Mitochondrial %',
      type: 'number',
      defaultValue: 20.0,
      min: 1.0,
      max: 50.0,
      step: 1.0,
      required: true,
      description: 'Maximum percentage of mitochondrial gene expression per cell'
    },
    {
      key: 'normalization_method',
      label: 'Normalization Method',
      type: 'select',
      defaultValue: 'scanpy',
      options: [
        { label: 'Scanpy (LogNormalize)', value: 'scanpy' },
        { label: 'Seurat (SCTransform)', value: 'sctransform' },
        { label: 'Scran', value: 'scran' }
      ],
      required: true,
      description: 'Method for normalizing single-cell expression data'
    },
    {
      key: 'n_top_genes',
      label: 'Number of Variable Genes',
      type: 'number',
      defaultValue: 2000,
      min: 500,
      max: 5000,
      step: 100,
      required: true,
      description: 'Number of highly variable genes to identify'
    },
    {
      key: 'clustering_resolution',
      label: 'Clustering Resolution',
      type: 'number',
      defaultValue: 0.5,
      min: 0.1,
      max: 2.0,
      step: 0.1,
      required: true,
      description: 'Resolution parameter for Leiden clustering (higher = more clusters)'
    },
    {
      key: 'n_neighbors',
      label: 'Number of Neighbors',
      type: 'number',
      defaultValue: 15,
      min: 5,
      max: 50,
      step: 5,
      required: true,
      description: 'Number of neighbors for graph construction'
    },
    {
      key: 'n_pcs',
      label: 'Number of PCs',
      type: 'number',
      defaultValue: 50,
      min: 10,
      max: 100,
      step: 10,
      required: true,
      description: 'Number of principal components to compute'
    }
  ]

  const handleFilesSelected = (files: File[]) => {
    uploadFiles(files)
  }

  const handleParametersSubmit = (params: Record<string, any>) => {
    setParameters(params)
  }

  const handleRunAnalysis = async () => {
    await runAnalysis()
  }

  const handleGeneratePlots = async () => {
    await generatePlots(['umap', 'violin', 'heatmap', 'pca'])
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">🔬 scRNA-seq Analysis</h1>
          <p className="text-gray-600">Single-cell RNA-seq analysis and cell type identification</p>
        </div>
        <div className="flex space-x-3">
          <Button
            variant="outline"
            onClick={() => goToStep('upload')}
            disabled={isAnalyzing}
          >
            <Upload className="h-4 w-4 mr-2" />
            Upload Data
          </Button>
          <Button
            variant="outline"
            onClick={() => goToStep('parameters')}
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
            description="Upload h5ad, mtx, or CSV format single-cell data"
            status={uploadedFiles.length > 0 ? 'completed' : 'pending'}
            onConfigure={() => goToStep('upload')}
          >
            {currentStep === 'upload' && (
              <FileUpload
                onFileSelect={handleFilesSelected}
                acceptedTypes={['.h5ad', '.mtx', '.csv', '.tsv', '.txt', '.h5']}
                maxSize={1000}
                multiple={true}
              />
            )}
          </AnalysisCard>
        </div>

        {/* Parameters */}
        <div className="lg:col-span-1">
          <AnalysisCard
            title="Analysis Parameters"
            description="Configure QC, normalization, and clustering parameters"
            status={Object.keys(analysisParams).length > 0 ? 'completed' : 'pending'}
            onConfigure={() => goToStep('parameters')}
            disabled={uploadedFiles.length === 0}
          >
            {currentStep === 'parameters' && (
              <ParameterForm
                title="scRNA-seq Parameters"
                parameters={scrnaseqParameters}
                initialValues={analysisParams}
                onSubmit={handleParametersSubmit}
              />
            )}
          </AnalysisCard>
        </div>

        {/* Analysis Execution */}
        <div className="lg:col-span-1">
          <AnalysisCard
            title="Run Analysis"
            description="Execute QC, normalization, clustering, and cell type annotation"
            status={analysisStatus}
            progress={analysisProgress}
            onStart={handleRunAnalysis}
            onViewResults={() => goToStep('results')}
            disabled={!canRunAnalysis}
          />
        </div>
      </div>

      {/* Results Section */}
      {currentStep === 'results' && results && (
        <Card>
          <CardHeader>
            <CardTitle>Analysis Results</CardTitle>
            <CardDescription>Single-cell RNA-seq analysis completed successfully</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">
                  {results?.total_cells || results?.summary?.total_cells || results?.n_cells || 'N/A'}
                </div>
                <div className="text-sm text-blue-800">Total Cells</div>
              </div>
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <div className="text-2xl font-bold text-purple-600">
                  {results?.total_genes || results?.summary?.total_genes || results?.n_genes || 'N/A'}
                </div>
                <div className="text-sm text-purple-800">Total Genes</div>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600">
                  {results?.n_clusters || results?.summary?.n_clusters || 'N/A'}
                </div>
                <div className="text-sm text-green-800">Cell Clusters</div>
              </div>
              <div className="text-center p-4 bg-orange-50 rounded-lg">
                <div className="text-2xl font-bold text-orange-600">
                  {results?.n_variable_genes || results?.summary?.n_variable_genes || 'N/A'}
                </div>
                <div className="text-sm text-orange-800">Variable Genes</div>
              </div>
            </div>

            {/* Cell Type Information */}
            {results?.cell_types && (
              <div className="mt-6">
                <h4 className="text-lg font-medium text-gray-900 mb-4">Identified Cell Types</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {Object.entries(results.cell_types).map(([cluster, cellType]: [string, any]) => (
                    <div key={cluster} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-gray-900">Cluster {cluster}</span>
                        <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-medium">
                          {cellType?.count || 0} cells
                        </span>
                      </div>
                      <div className="text-sm text-gray-600">
                        {cellType?.type || cellType || 'Unknown'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* QC Metrics */}
            {results?.qc_metrics && (
              <div className="mt-6">
                <h4 className="text-lg font-medium text-gray-900 mb-4">Quality Control Metrics</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Object.entries(results.qc_metrics).map(([key, value]: [string, any]) => (
                    <div key={key} className="text-center p-3 bg-gray-50 rounded-lg">
                      <div className="text-lg font-semibold text-gray-900">
                        {typeof value === 'number' ? value.toFixed(2) : value}
                      </div>
                      <div className="text-xs text-gray-600 capitalize">
                        {key.replace(/_/g, ' ')}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Debug Info */}
            <div className="mt-4 p-4 bg-gray-50 rounded-lg">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Debug Info:</h4>
              <pre className="text-xs text-gray-600 overflow-auto max-h-32">
                {JSON.stringify(results, null, 2)}
              </pre>
            </div>

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
