import React from 'react'
import { CheckCircle, Clock, AlertCircle, Play, Settings } from 'lucide-react'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { Progress } from '../ui/progress'
import { cn } from '../../lib/utils'

export type AnalysisStatus = 'pending' | 'running' | 'completed' | 'error'

interface AnalysisCardProps {
  title: string
  description: string
  status: AnalysisStatus
  progress?: number
  onStart?: () => void
  onConfigure?: () => void
  onViewResults?: () => void
  disabled?: boolean
  className?: string
  children?: React.ReactNode
}

const statusConfig = {
  pending: {
    icon: Clock,
    color: 'text-gray-500',
    bgColor: 'bg-gray-100',
    label: 'Pending'
  },
  running: {
    icon: Play,
    color: 'text-blue-500',
    bgColor: 'bg-blue-100',
    label: 'Running'
  },
  completed: {
    icon: CheckCircle,
    color: 'text-green-500',
    bgColor: 'bg-green-100',
    label: 'Completed'
  },
  error: {
    icon: AlertCircle,
    color: 'text-red-500',
    bgColor: 'bg-red-100',
    label: 'Error'
  }
}

export function AnalysisCard({
  title,
  description,
  status,
  progress,
  onStart,
  onConfigure,
  onViewResults,
  disabled = false,
  className,
  children
}: AnalysisCardProps) {
  const config = statusConfig[status]
  const StatusIcon = config.icon

  return (
    <Card className={cn("transition-shadow hover:shadow-md", className)}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-lg">{title}</CardTitle>
            <CardDescription className="mt-1">{description}</CardDescription>
          </div>
          <div className={cn(
            "flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium",
            config.bgColor,
            config.color
          )}>
            <StatusIcon className="w-3 h-3" />
            <span>{config.label}</span>
          </div>
        </div>
        
        {/* Progress Bar for Running Analysis */}
        {status === 'running' && progress !== undefined && (
          <div className="mt-4">
            <div className="flex justify-between text-sm text-gray-600 mb-2">
              <span>Progress</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <Progress value={progress} className="h-2" />
          </div>
        )}
      </CardHeader>

      {children && (
        <CardContent>
          {children}
        </CardContent>
      )}

      <CardFooter className="flex justify-between space-x-2">
        <div className="flex space-x-2">
          {onConfigure && (
            <Button
              variant="outline"
              size="sm"
              onClick={onConfigure}
              disabled={disabled || status === 'running'}
            >
              <Settings className="w-4 h-4 mr-2" />
              Configure
            </Button>
          )}
        </div>
        
        <div className="flex space-x-2">
          {status === 'pending' && onStart && (
            <Button
              variant="analysis"
              size="sm"
              onClick={onStart}
              disabled={disabled}
            >
              <Play className="w-4 h-4 mr-2" />
              Start Analysis
            </Button>
          )}
          
          {status === 'completed' && onViewResults && (
            <Button
              variant="success"
              size="sm"
              onClick={onViewResults}
              disabled={disabled}
            >
              View Results
            </Button>
          )}
          
          {status === 'error' && onStart && (
            <Button
              variant="warning"
              size="sm"
              onClick={onStart}
              disabled={disabled}
            >
              Retry
            </Button>
          )}
        </div>
      </CardFooter>
    </Card>
  )
} 