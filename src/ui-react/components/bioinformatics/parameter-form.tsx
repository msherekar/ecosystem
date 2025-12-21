import React, { useState } from 'react'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { cn } from '../../lib/utils'

export interface ParameterDefinition {
  key: string
  label: string
  type: 'text' | 'number' | 'select' | 'boolean' | 'file'
  defaultValue?: any
  options?: Array<{ label: string; value: any }>
  min?: number
  max?: number
  step?: number
  required?: boolean
  description?: string
  placeholder?: string
}

interface ParameterFormProps {
  title: string
  parameters: ParameterDefinition[]
  initialValues?: Record<string, any>
  onSubmit: (values: Record<string, any>) => void
  onCancel?: () => void
  disabled?: boolean
  className?: string
}

export function ParameterForm({
  title,
  parameters,
  initialValues = {},
  onSubmit,
  onCancel,
  disabled = false,
  className
}: ParameterFormProps) {
  const [values, setValues] = useState<Record<string, any>>(() => {
    const defaultValues: Record<string, any> = {}
    parameters.forEach(param => {
      defaultValues[param.key] = initialValues[param.key] ?? param.defaultValue ?? ''
    })
    return defaultValues
  })

  const [errors, setErrors] = useState<Record<string, string>>({})

  const handleValueChange = (key: string, value: any) => {
    setValues(prev => ({ ...prev, [key]: value }))
    
    // Clear error when user starts typing
    if (errors[key]) {
      setErrors(prev => ({ ...prev, [key]: '' }))
    }
  }

  const validateForm = () => {
    const newErrors: Record<string, string> = {}
    
    parameters.forEach(param => {
      if (param.required && !values[param.key]) {
        newErrors[param.key] = `${param.label} is required`
      }
      
      if (param.type === 'number' && values[param.key] !== '') {
        const numValue = Number(values[param.key])
        if (isNaN(numValue)) {
          newErrors[param.key] = `${param.label} must be a number`
        } else {
          if (param.min !== undefined && numValue < param.min) {
            newErrors[param.key] = `${param.label} must be at least ${param.min}`
          }
          if (param.max !== undefined && numValue > param.max) {
            newErrors[param.key] = `${param.label} must be at most ${param.max}`
          }
        }
      }
    })
    
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (validateForm()) {
      onSubmit(values)
    }
  }

  const renderInput = (param: ParameterDefinition) => {
    const value = values[param.key]
    const error = errors[param.key]

    switch (param.type) {
      case 'text':
        return (
          <Input
            type="text"
            value={value}
            onChange={(e) => handleValueChange(param.key, e.target.value)}
            placeholder={param.placeholder}
            disabled={disabled}
            className={cn(error && "border-red-500")}
          />
        )

      case 'number':
        return (
          <Input
            type="number"
            value={value}
            onChange={(e) => handleValueChange(param.key, e.target.value)}
            placeholder={param.placeholder}
            min={param.min}
            max={param.max}
            step={param.step}
            disabled={disabled}
            className={cn(error && "border-red-500")}
          />
        )

      case 'select':
        return (
          <select
            value={value}
            onChange={(e) => handleValueChange(param.key, e.target.value)}
            disabled={disabled}
            className={cn(
              "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
              error && "border-red-500"
            )}
          >
            <option value="">Select...</option>
            {param.options?.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        )

      case 'boolean':
        return (
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={!!value}
              onChange={(e) => handleValueChange(param.key, e.target.checked)}
              disabled={disabled}
              className="rounded border-gray-300"
            />
            <span className="text-sm">Enable</span>
          </div>
        )

      default:
        return (
          <Input
            type="text"
            value={value}
            onChange={(e) => handleValueChange(param.key, e.target.value)}
            placeholder={param.placeholder}
            disabled={disabled}
            className={cn(error && "border-red-500")}
          />
        )
    }
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {parameters.map(param => (
            <div key={param.key} className="space-y-2">
              <label className="text-sm font-medium text-gray-900">
                {param.label}
                {param.required && <span className="text-red-500 ml-1">*</span>}
              </label>
              
              {renderInput(param)}
              
              {param.description && (
                <p className="text-xs text-gray-500">{param.description}</p>
              )}
              
              {errors[param.key] && (
                <p className="text-xs text-red-600">{errors[param.key]}</p>
              )}
            </div>
          ))}
          
          <div className="flex justify-end space-x-2 pt-4 border-t">
            {onCancel && (
              <Button
                type="button"
                variant="outline"
                onClick={onCancel}
                disabled={disabled}
              >
                Cancel
              </Button>
            )}
            <Button
              type="submit"
              variant="analysis"
              disabled={disabled}
            >
              Apply Parameters
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
} 