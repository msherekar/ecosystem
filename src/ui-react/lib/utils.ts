import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Bioinformatics utility functions
export function formatServerStatus(status: string): string {
  switch (status) {
    case 'running':
      return '🟢 Running'
    case 'stopped':
      return '🔴 Stopped'
    case 'error':
      return '🟡 Error'
    default:
      return '⚪ Unknown'
  }
}

export function formatAnalysisType(type: string): string {
  const typeMap: Record<string, string> = {
    'rnaseq': '📊 RNA-seq',
    'scrnaseq': '🔬 scRNA-seq',
    'atacseq': '🧬 ATAC-seq',
    'proteomics': '🧪 Proteomics',
    'visualization': '📈 Visualization',
    'data': '💾 Data Management'
  }
  
  return typeMap[type] || type
}
