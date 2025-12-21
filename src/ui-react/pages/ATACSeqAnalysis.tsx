import React from 'react'
import { Upload, Settings } from 'lucide-react'
import { useAnalysis } from '../hooks/useAnalysis'
import { AnalysisCard } from '../components/bioinformatics/analysis-card'
import { ParameterForm, ParameterDefinition } from '../components/bioinformatics/parameter-form'
import { FileUpload } from '../components/ui/file-upload'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'

export function ATACSeqAnalysis() {
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
  } = useAnalysis('atacseq')

  const atacseqParameters: ParameterDefinition[] = [
    {
      key: 'genome',
      label: 'Reference Genome',
      type: 'select',
      defaultValue: 'hg38',
      options: [
        { label: 'Human (hg38)', value: 'hg38' },
        { label: 'Human (hg19)', value: 'hg19' },
        { label: 'Mouse (mm10)', value: 'mm10' },
        { label: 'Mouse (mm39)', value: 'mm39' }
      ],
      required: true,
      description: 'Reference genome for alignment and peak calling'
    },
    {
      key: 'peak_caller',
      label: 'Peak Calling Algorithm',
      type: 'select',
      defaultValue: 'macs2',
      options: [
        { label: 'MACS2', value: 'macs2' },
        { label: 'HOMER', value: 'homer' },
        { label: 'Genrich', value: 'genrich' }
      ],
      required: true,
      description: 'Algorithm for identifying chromatin accessibility peaks'
    },
    {
      key: 'q_value_threshold',
      label: 'Q-value Threshold',
      type: 'number',
      defaultValue: 0.05,
      min: 0.001,
      max: 0.1,
      step: 0.001,
      required: true,
      description: 'FDR threshold for peak calling significance'
    },
    {
      key: 'shift_size',
      label: 'Shift Size',
      type: 'number',
      defaultValue: 100,
      min: 0,
      max: 200,
      step: 10,
      required: true,
      description: 'Read shift size for ATAC-seq data'
    },
    {
      key: 'motif_analysis',
      label: 'Perform Motif Analysis',
      type: 'boolean',
      defaultValue: true,
      description: 'Identify enriched transcription factor motifs in peaks'
    }
  ]

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">🧬 ATAC-seq Analysis</h1>
          <p className="text-gray-600">Chromatin accessibility and peak calling analysis</p>
        </div>
        <div className="flex space-x-3">
          <Button variant="outline" onClick={() => goToStep('upload')} disabled={isAnalyzing}>
            <Upload className="h-4 w-4 mr-2" />Upload Data
          </Button>
          <Button variant="outline" onClick={() => goToStep('parameters')} disabled={uploadedFiles.length === 0 || isAnalyzing}>
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
          <AnalysisCard title="Data Upload" description="Upload BAM, BED, or FASTQ files"
            status={uploadedFiles.length > 0 ? 'completed' : 'pending'} onConfigure={() => goToStep('upload')}>
            {currentStep === 'upload' && (
              <FileUpload onFileSelect={uploadFiles} acceptedTypes={['.bam', '.bed', '.bedgraph', '.fastq', '.fq', '.gz']} maxSize={5000} multiple={true} />
            )}
          </AnalysisCard>
        </div>
        <div className="lg:col-span-1">
          <AnalysisCard title="Analysis Parameters" description="Configure peak calling and analysis settings"
            status={Object.keys(analysisParams).length > 0 ? 'completed' : 'pending'} onConfigure={() => goToStep('parameters')} disabled={uploadedFiles.length === 0}>
            {currentStep === 'parameters' && (
              <ParameterForm title="ATAC-seq Parameters" parameters={atacseqParameters} initialValues={analysisParams} onSubmit={setParameters} />
            )}
          </AnalysisCard>
        </div>
        <div className="lg:col-span-1">
          <AnalysisCard title="Run Analysis" description="Execute peak calling, annotation, and motif analysis"
            status={analysisStatus} progress={analysisProgress} onStart={runAnalysis} onViewResults={() => goToStep('results')} disabled={!canRunAnalysis} />
        </div>
      </div>

      {/* Results Section */}
      {currentStep === 'results' && results && (
        <Card>
          <CardHeader>
            <CardTitle>Analysis Results</CardTitle>
            <CardDescription>ATAC-seq analysis completed successfully</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">{results?.total_peaks || results?.summary?.total_peaks || 'N/A'}</div>
                <div className="text-sm text-blue-800">Total Peaks</div>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600">{results?.promoter_peaks || results?.summary?.promoter_peaks || 'N/A'}</div>
                <div className="text-sm text-green-800">Promoter Peaks</div>
              </div>
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <div className="text-2xl font-bold text-purple-600">{results?.enhancer_peaks || results?.summary?.enhancer_peaks || 'N/A'}</div>
                <div className="text-sm text-purple-800">Enhancer Peaks</div>
              </div>
              <div className="text-center p-4 bg-orange-50 rounded-lg">
                <div className="text-2xl font-bold text-orange-600">{results?.tss_enrichment || results?.summary?.tss_enrichment || 'N/A'}</div>
                <div className="text-sm text-orange-800">TSS Enrichment</div>
              </div>
            </div>
            <div className="mt-4 p-4 bg-gray-50 rounded-lg">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Debug Info:</h4>
              <pre className="text-xs text-gray-600 overflow-auto max-h-32">{JSON.stringify(results, null, 2)}</pre>
            </div>
            <div className="mt-6 flex space-x-4">
              <Button variant="analysis">Download Results</Button>
              <Button variant="outline" onClick={() => generatePlots(['fragment_distribution', 'tss_enrichment', 'peak_annotation'])}>
                Generate Plots
              </Button>
              <Button variant="outline">Export Report</Button>
            </div>
            {plots.length > 0 && (
              <div className="mt-6">
                <h4 className="text-lg font-medium text-gray-900 mb-4">Generated Plots</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {plots.map((plot, index) => (
                    <div key={index} className="border rounded-lg p-4">
                      <h5 className="font-medium mb-2">{plot.title || `Plot ${index + 1}`}</h5>
                      {plot.image ? <img src={plot.image} alt={plot.title} className="w-full rounded" /> :
                       plot.html ? <div dangerouslySetInnerHTML={{ __html: plot.html }} /> :
                       <div className="text-gray-500">Plot data: {JSON.stringify(plot)}</div>}
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