import React, { useCallback, useState } from 'react'
import { Upload, File, X, CheckCircle, AlertCircle } from 'lucide-react'
import { cn } from '../../lib/utils'

interface FileUploadProps {
  onFileSelect: (files: File[]) => void
  acceptedTypes?: string[]
  maxSize?: number // in MB
  multiple?: boolean
  disabled?: boolean
  className?: string
}

export function FileUpload({
  onFileSelect,
  acceptedTypes = ['.csv', '.tsv', '.txt', '.xlsx', '.h5ad', '.h5', '.fastq', '.fq'],
  maxSize = 100,
  multiple = false,
  disabled = false,
  className
}: FileUploadProps) {
  const [dragActive, setDragActive] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const [errors, setErrors] = useState<string[]>([])

  const handleFiles = useCallback((fileList: FileList | null) => {
    if (!fileList) return

    const files = Array.from(fileList)
    const newErrors: string[] = []
    const validFiles: File[] = []

    files.forEach(file => {
      // Check file size
      if (file.size > maxSize * 1024 * 1024) {
        newErrors.push(`${file.name}: File size exceeds ${maxSize}MB`)
        return
      }

      // Check file type
      const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()
      if (acceptedTypes.length > 0 && !acceptedTypes.includes(fileExtension)) {
        newErrors.push(`${file.name}: File type not supported`)
        return
      }

      validFiles.push(file)
    })

    setErrors(newErrors)
    
    if (validFiles.length > 0) {
      const newUploadedFiles = multiple ? [...uploadedFiles, ...validFiles] : validFiles
      setUploadedFiles(newUploadedFiles)
      onFileSelect(newUploadedFiles)
    }
  }, [acceptedTypes, maxSize, multiple, onFileSelect, uploadedFiles])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (disabled) return
    handleFiles(e.dataTransfer.files)
  }, [disabled, handleFiles])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!disabled) setDragActive(true)
  }, [disabled])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
  }, [])

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files)
  }, [handleFiles])

  const removeFile = useCallback((index: number) => {
    const newFiles = uploadedFiles.filter((_, i) => i !== index)
    setUploadedFiles(newFiles)
    onFileSelect(newFiles)
  }, [uploadedFiles, onFileSelect])

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <div className={cn("w-full", className)}>
      {/* Upload Area */}
      <div
        className={cn(
          "relative border-2 border-dashed rounded-lg p-8 text-center transition-colors",
          dragActive && !disabled 
            ? "border-blue-500 bg-blue-50" 
            : "border-gray-300 hover:border-gray-400",
          disabled && "opacity-50 cursor-not-allowed"
        )}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <input
          type="file"
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
          onChange={handleFileInput}
          multiple={multiple}
          accept={acceptedTypes.join(',')}
          disabled={disabled}
        />
        
        <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          Drop files here or click to browse
        </h3>
        <p className="text-sm text-gray-600 mb-2">
          Supported formats: {acceptedTypes.join(', ')}
        </p>
        <p className="text-xs text-gray-500">
          Maximum file size: {maxSize}MB
        </p>
      </div>

      {/* Error Messages */}
      {errors.length > 0 && (
        <div className="mt-4 space-y-2">
          {errors.map((error, index) => (
            <div key={index} className="flex items-center space-x-2 text-red-600 text-sm">
              <AlertCircle className="h-4 w-4" />
              <span>{error}</span>
            </div>
          ))}
        </div>
      )}

      {/* Uploaded Files */}
      {uploadedFiles.length > 0 && (
        <div className="mt-4 space-y-2">
          <h4 className="text-sm font-medium text-gray-900">Uploaded Files:</h4>
          {uploadedFiles.map((file, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
            >
              <div className="flex items-center space-x-3">
                <File className="h-5 w-5 text-gray-400" />
                <div>
                  <p className="text-sm font-medium text-gray-900">{file.name}</p>
                  <p className="text-xs text-gray-500">
                    {formatFileSize(file.size)} • {file.type || 'Unknown type'}
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <CheckCircle className="h-5 w-5 text-green-500" />
                <button
                  onClick={() => removeFile(index)}
                  className="text-gray-400 hover:text-red-500 transition-colors"
                  disabled={disabled}
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
} 