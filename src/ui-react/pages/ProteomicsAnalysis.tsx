import React, { useState } from 'react'
import { Upload, Settings } from 'lucide-react'
import { ParameterForm, ParameterDefinition } from '../components/bioinformatics/parameter-form'
import { FileUpload } from '../components/ui/file-upload'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { AnalysisCard } from '../components/bioinformatics/analysis-card'

type AnalysisStep = 'upload' | 'parameters' | 'analysis' | 'results'
type AnalysisStatus = 'pending' | 'running' | 'completed' | 'error'

export function ProteomicsAnalysis() {
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const [analysisParams, setAnalysisParams] = useState<Record<string, any>>({})
  const [currentStep, setCurrentStep] = useState<AnalysisStep>('upload')
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus>('pending')
  const [analysisProgress, setAnalysisProgress] = useState(0)
  const [results, setResults] = useState<any>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  const proteomicsParameters: ParameterDefinition[] = [
    {
      key: 'search_engine',
      label: 'Search Engine',
      type: 'select',
      defaultValue: 'mascot',
      options: [
        { label: 'Mascot', value: 'mascot' },
        { label: 'Sequest', value: 'sequest' },
        { label: 'MaxQuant', value: 'maxquant' },
        { label: 'MSFragger', value: 'msfragger' }
      ],
      required: true,
      description: 'Peptide identification search engine'
    },
    {
      key: 'fdr_threshold',
      label: 'FDR Threshold',
      type: 'number',
      defaultValue: 0.01,
      min: 0.001,
      max: 0.1,
      step: 0.001,
      required: true,
      description: 'False discovery rate threshold for peptide identification'
    },
    {
      key: 'min_peptides',
      label: 'Minimum Peptides per Protein',
      type: 'number',
      defaultValue: 2,
      min: 1,
      max: 10,
      step: 1,
      required: true,
      description: 'Minimum unique peptides required for protein identification'
    },
    {
      key: 'mass_tolerance',
      label: 'Precursor Mass Tolerance (ppm)',
      type: 'number',
      defaultValue: 10,
      min: 1,
      max: 50,
      step: 1,
      required: true,
      description: 'Mass tolerance for precursor ion matching'
    },
    {
      key: 'fragment_tolerance',
      label: 'Fragment Mass Tolerance (Da)',
      type: 'number',
      defaultValue: 0.02,
      min: 0.01,
      max: 1.0,
      step: 0.01,
      required: true,
      description: 'Mass tolerance for fragment ion matching'
    },
    {
      key: 'quantification_method',
      label: 'Quantification Method',
      type: 'select',
      defaultValue: 'lfq',
      options: [
        { label: 'Label-Free (LFQ)', value: 'lfq' },
        { label: 'TMT', value: 'tmt' },
        { label: 'SILAC', value: 'silac' },
        { label: 'iTRAQ', value: 'itraq' }
      ],
      required: true,
      description: 'Protein quantification strategy'
    },
    {
      key: 'normalization',
      label: 'Normalization Method',
      type: 'select',
      defaultValue: 'median',
      options: [
        { label: 'Median', value: 'median' },
        { label: 'Mean', value: 'mean' },
        { label: 'Quantile', value: 'quantile' },
        { label: 'VSN', value: 'vsn' }
      ],
      required: true,
      description: 'Method for normalizing protein abundances'
    }
  ]

  const handleAnalysis = async () => {
    setIsAnalyzing(true)
    setAnalysisStatus('running')
    setAnalysisProgress(0)

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setAnalysisProgress(prev => Math.min(prev + Math.random() * 15, 100))
      }, 1000)

      // Simulated analysis
      await new Promise(resolve => setTimeout(resolve, 5000))

      clearInterval(progressInterval)
      setAnalysisProgress(100)
      setAnalysisStatus('completed')

      // Mock results
      setResults({
        total_proteins: 1247,
        identified_proteins: 1189,
        quantified_proteins: 1054,
        total_peptides: 8532,
        unique_peptides: 6421,
        fdr_protein: 0.009,
        fdr_peptide: 0.008,
        coverage_median: 34.5
      })
      setCurrentStep('results')
    } catch (error) {
      console.error('Analysis failed:', error)
      setAnalysisStatus('error')
    } finally {
      setIsAnalyzing(false)
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">🧪 Proteomics Analysis</h1>
          <p className="text-gray-600">Mass spectrometry data analysis and protein identification</p>
        </div>
        <div className="flex space-x-3">
          <Button variant="outline" onClick={() => setCurrentStep('upload')} disabled={isAnalyzing}>
            <Upload className="h-4 w-4 mr-2" />Upload Data
          </Button>
          <Button variant="outline" onClick={() => setCurrentStep('parameters')} disabled={uploadedFiles.length === 0 || isAnalyzing}>
            <Settings className="h-4 w-4 mr-2" />Configure
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
              step.completed ? 'bg-green-100 text-green-800' : currentStep === step.key ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-600'
            }`}>{index + 1}</div>
            <span className={`ml-2 text-sm ${step.completed ? 'text-green-800' : currentStep === step.key ? 'text-blue-800' : 'text-gray-600'}`}>
              {step.label}
            </span>
            {index < 3 && <div className="w-8 h-px bg-gray-300 ml-4" />}
          </div>
        ))}
      </div>

      {/* Step Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-1">
          <AnalysisCard title="Data Upload" description="Upload mzML, RAW, or MGF files"
            status={uploadedFiles.length > 0 ? 'completed' : 'pending'} onConfigure={() => setCurrentStep('upload')}>
            {currentStep === 'upload' && (
              <FileUpload onFileSelect={setUploadedFiles} acceptedTypes={['.mzml', '.mzxml', '.raw', '.mgf', '.wiff']} maxSize={10000} multiple={true} />
            )}
          </AnalysisCard>
        </div>
        <div className="lg:col-span-1">
          <AnalysisCard title="Analysis Parameters" description="Configure search and quantification settings"
            status={Object.keys(analysisParams).length > 0 ? 'completed' : 'pending'} onConfigure={() => setCurrentStep('parameters')} disabled={uploadedFiles.length === 0}>
            {currentStep === 'parameters' && (
              <ParameterForm title="Proteomics Parameters" parameters={proteomicsParameters} initialValues={analysisParams}
                onSubmit={(params) => { setAnalysisParams(params); setCurrentStep('analysis') }} />
            )}
          </AnalysisCard>
        </div>
        <div className="lg:col-span-1">
          <AnalysisCard title="Run Analysis" description="Execute peptide search and protein quantification"
            status={analysisStatus} progress={analysisProgress} onStart={handleAnalysis} onViewResults={() => setCurrentStep('results')}
            disabled={uploadedFiles.length === 0 || Object.keys(analysisParams).length === 0} />
        </div>
      </div>

      {/* Results Section */}
      {currentStep === 'results' && results && (
        <Card>
          <CardHeader>
            <CardTitle>Analysis Results</CardTitle>
            <CardDescription>Proteomics analysis completed successfully</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">{results.identified_proteins}</div>
                <div className="text-sm text-blue-800">Proteins Identified</div>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600">{results.quantified_proteins}</div>
                <div className="text-sm text-green-800">Proteins Quantified</div>
              </div>
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <div className="text-2xl font-bold text-purple-600">{results.unique_peptides}</div>
                <div className="text-sm text-purple-800">Unique Peptides</div>
              </div>
              <div className="text-center p-4 bg-orange-50 rounded-lg">
                <div className="text-2xl font-bold text-orange-600">{(results.fdr_protein * 100).toFixed(2)}%</div>
                <div className="text-sm text-orange-800">Protein FDR</div>
              </div>
            </div>
            <div className="mt-4 p-4 bg-gray-50 rounded-lg">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Debug Info:</h4>
              <pre className="text-xs text-gray-600 overflow-auto max-h-32">{JSON.stringify(results, null, 2)}</pre>
            </div>
            <div className="mt-6 flex space-x-4">
              <Button variant="analysis">Download Results</Button>
              <Button variant="outline">Generate Plots</Button>
              <Button variant="outline">Export Report</Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
} 