"""
Data File Analyzer for Biological Context

This module analyzes uploaded data files to extract context clues
about experimental design and data types.
"""

import logging
from typing import Dict, List, Any


class DataFileAnalyzer:
    """Analyzes uploaded data files for context clues."""
    
    def __init__(self):
        self.logger = logging.getLogger("data_file_analyzer")
    
    async def analyze(self, files: List[Any]) -> Dict[str, Any]:
        """Analyze file metadata and content for context."""
        
        file_contexts = []
        
        for file in files:
            file_context = {
                'filename': getattr(file, 'name', 'unknown'),
                'size': getattr(file, 'size', 0),
                'type': self._detect_file_type(file),
                'data_characteristics': {},
                'inferred_experiment': None
            }
            
            # Analyze file content
            if hasattr(file, 'read'):
                try:
                    content_sample = file.read(1024).decode('utf-8', errors='ignore')
                    file_context['data_characteristics'] = self._analyze_content(content_sample)
                    file_context['inferred_experiment'] = self._infer_experiment_type(
                        file_context['filename'], content_sample
                    )
                except Exception as e:
                    self.logger.warning(f"Could not analyze file content: {e}")
            
            file_contexts.append(file_context)
        
        # Aggregate file analysis
        return {
            'file_count': len(files),
            'file_types': list(set(fc['type'] for fc in file_contexts)),
            'total_size': sum(fc['size'] for fc in file_contexts),
            'experiment_types': list(set(fc['inferred_experiment'] for fc in file_contexts if fc['inferred_experiment'])),
            'data_complexity': self._assess_data_complexity(file_contexts)
        }
    
    def _detect_file_type(self, file) -> str:
        """Detect biological data file type."""
        filename = getattr(file, 'name', '').lower()
        
        # Check file extensions first (more specific)
        extension_patterns = {
            'fastq': ['.fastq', '.fq'],
            'bam': ['.bam'],
            'vcf': ['.vcf'],
            'gff': ['.gff', '.gtf'],
            'h5ad': ['.h5ad'],
            'csv': ['.csv'],
            'tsv': ['.tsv', '.txt'],
            'excel': ['.xlsx', '.xls']
        }
        
        for file_type, patterns in extension_patterns.items():
            if any(filename.endswith(pattern) for pattern in patterns):
                return file_type
        
        # Then check content-based patterns (more general)
        content_patterns = {
            'counts_matrix': ['counts', 'matrix', 'expression'],
            'metadata': ['metadata', 'sample_info', 'phenotype']
        }
        
        for file_type, patterns in content_patterns.items():
            if any(pattern in filename for pattern in patterns):
                return file_type
        
        return 'unknown'
    
    def _analyze_content(self, content_sample: str) -> Dict[str, Any]:
        """Analyze file content to extract data characteristics."""
        characteristics = {
            'has_header': False,
            'delimiter': None,
            'estimated_columns': 0,
            'estimated_rows': 0,
            'numeric_columns': 0
        }
        
        lines = content_sample.split('\n')[:10]  # First 10 lines
        
        if not lines:
            return characteristics
        
        # Detect delimiter
        delimiters = ['\t', ',', ';', ' ']
        delimiter_counts = {}
        
        for delimiter in delimiters:
            delimiter_counts[delimiter] = sum(line.count(delimiter) for line in lines)
        
        if delimiter_counts:
            characteristics['delimiter'] = max(delimiter_counts, key=delimiter_counts.get)
        
        # Estimate columns
        if characteristics['delimiter']:
            characteristics['estimated_columns'] = max(
                line.count(characteristics['delimiter']) + 1 for line in lines if line.strip()
            )
        
        # Check for header
        if lines and characteristics['delimiter']:
            first_line_parts = lines[0].split(characteristics['delimiter'])
            if any(not part.replace('.', '').replace('-', '').isdigit() for part in first_line_parts):
                characteristics['has_header'] = True
        
        return characteristics
    
    def _infer_experiment_type(self, filename: str, content_sample: str) -> str:
        """Infer experiment type from filename and content."""
        filename_lower = filename.lower()
        content_lower = content_sample.lower()
        
        # Check more specific patterns first
        
        # scRNA-seq indicators (check before RNA-seq)
        if any(keyword in filename_lower or keyword in content_lower 
               for keyword in ['scrna', 'single_cell', 'sc_rna', 'single cell']):
            return 'scrna_seq'
        
        # ATAC-seq indicators
        if any(keyword in filename_lower or keyword in content_lower 
               for keyword in ['atac', 'chromatin', 'accessibility']):
            return 'atac_seq'
        
        # ChIP-seq indicators
        if any(keyword in filename_lower or keyword in content_lower 
               for keyword in ['chip', 'histone', 'tf_binding']):
            return 'chip_seq'
        
        # Proteomics indicators
        if any(keyword in filename_lower or keyword in content_lower 
               for keyword in ['protein', 'proteome', 'mass_spec']):
            return 'proteomics'
        
        # RNA-seq indicators (check after more specific types)
        if any(keyword in filename_lower or keyword in content_lower 
               for keyword in ['rnaseq', 'rna-seq', 'expression', 'counts']):
            return 'rnaseq'
        
        return 'unknown'
    
    def _assess_data_complexity(self, file_contexts: List[Dict]) -> str:
        """Assess overall data complexity based on file characteristics."""
        total_size = sum(fc['size'] for fc in file_contexts)
        file_types = set(fc['type'] for fc in file_contexts)
        
        # Simple heuristic for complexity
        if total_size > 1e9:  # > 1GB
            return 'high'
        elif len(file_types) > 3:
            return 'high'
        elif total_size > 1e8:  # > 100MB
            return 'medium'
        else:
            return 'low'


def main():
    """Test function for the file analyzer module."""
    print("Testing DataFileAnalyzer...")
    
    # Create mock file objects for testing
    class MockFile:
        def __init__(self, name, size, content):
            self.name = name
            self.size = size
            self.content = content
        
        def read(self, n):
            return self.content.encode('utf-8')
    
    # Test files
    test_files = [
        MockFile("counts.tsv", 1000000, "gene_id\tsample1\tsample2\nGENE1\t100\t200\nGENE2\t150\t300"),
        MockFile("metadata.csv", 5000, "sample_id,condition,batch\nsample1,control,1\nsample2,treated,1"),
        MockFile("scrna_data.h5ad", 50000000, "# Single cell RNA-seq data")
    ]
    
    analyzer = DataFileAnalyzer()
    
    # Test analysis (would need to be async in real usage)
    print("Created analyzer instance")
    print(f"Testing with {len(test_files)} mock files")
    
    # Test individual methods
    for file in test_files:
        file_type = analyzer._detect_file_type(file)
        experiment_type = analyzer._infer_experiment_type(file.name, file.content)
        print(f"File: {file.name} -> Type: {file_type}, Experiment: {experiment_type}")


if __name__ == "__main__":
    main() 