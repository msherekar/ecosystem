"""
Storage management for training data.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Iterator
import glob

from .models import ConversationTurn, TrainingDataset
from .config import TrainingConfig

class TrainingDataStorage:
    """Handles persistent storage of training data"""
    
    def __init__(self, data_dir: str = "data/training", config: TrainingConfig = None):
        self.data_dir = Path(data_dir)
        self.config = config or TrainingConfig()
        self.logger = logging.getLogger("training_storage")
        
        # Ensure directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Setup logging configuration"""
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        self.logger.setLevel(log_level)
        
        if self.config.log_file:
            handler = logging.FileHandler(self.config.log_file)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def save_dataset(self, dataset: TrainingDataset, filename: str = None) -> str:
        """Save a training dataset to disk"""
        try:
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"dataset_{timestamp}.json"
            
            filepath = self.data_dir / filename
            
            # Check file size limits
            if self._would_exceed_size_limit(dataset):
                self.logger.warning(f"Dataset would exceed size limit, splitting...")
                return self._save_split_dataset(dataset, filename)
            
            # Save to JSON
            with open(filepath, 'w') as f:
                json.dump(dataset.to_dict(), f, indent=2, default=str)
            
            self.logger.info(f"Saved dataset with {len(dataset.conversations)} conversations to {filename}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Failed to save dataset: {e}")
            raise
    
    def _would_exceed_size_limit(self, dataset: TrainingDataset) -> bool:
        """Check if dataset would exceed file size limit"""
        # Rough estimate: 1KB per conversation on average
        estimated_size_mb = len(dataset.conversations) * 1 / 1024
        return estimated_size_mb > self.config.max_file_size_mb
    
    def _save_split_dataset(self, dataset: TrainingDataset, base_filename: str) -> str:
        """Save dataset split into multiple files"""
        conversations_per_file = self._calculate_conversations_per_file(dataset)
        saved_files = []
        
        for i, start_idx in enumerate(range(0, len(dataset.conversations), conversations_per_file)):
            end_idx = min(start_idx + conversations_per_file, len(dataset.conversations))
            
            # Create split dataset
            split_conversations = dataset.conversations[start_idx:end_idx]
            split_metadata = {
                **dataset.metadata,
                'split_info': {
                    'part': i + 1,
                    'total_parts': (len(dataset.conversations) + conversations_per_file - 1) // conversations_per_file,
                    'conversations_in_part': len(split_conversations)
                }
            }
            
            split_dataset = TrainingDataset(
                conversations=split_conversations,
                metadata=split_metadata,
                created_at=dataset.created_at,
                version=dataset.version
            )
            
            # Generate filename for this part
            name_parts = base_filename.split('.')
            split_filename = f"{name_parts[0]}_part{i+1:03d}.{name_parts[1]}"
            
            split_filepath = self.save_dataset(split_dataset, split_filename)
            saved_files.append(split_filepath)
        
        self.logger.info(f"Split dataset into {len(saved_files)} files")
        return saved_files[0]  # Return first file
    
    def _calculate_conversations_per_file(self, dataset: TrainingDataset) -> int:
        """Calculate optimal conversations per file"""
        total_conversations = len(dataset.conversations)
        max_size_kb = self.config.max_file_size_mb * 1024
        
        # Rough estimate: 1KB per conversation
        conversations_per_file = max_size_kb
        
        # Ensure at least 10 conversations per file
        return max(10, min(conversations_per_file, total_conversations))
    
    def load_dataset(self, filepath: str) -> TrainingDataset:
        """Load a training dataset from disk"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            dataset = TrainingDataset.from_dict(data)
            self.logger.info(f"Loaded dataset with {len(dataset.conversations)} conversations from {filepath}")
            return dataset
            
        except Exception as e:
            self.logger.error(f"Failed to load dataset from {filepath}: {e}")
            raise
    
    def list_datasets(self) -> List[Dict[str, Any]]:
        """List all available datasets"""
        datasets = []
        
        for json_file in self.data_dir.glob("*.json"):
            try:
                stat = json_file.stat()
                datasets.append({
                    'filename': json_file.name,
                    'filepath': str(json_file),
                    'size_mb': stat.st_size / (1024 * 1024),
                    'modified': datetime.fromtimestamp(stat.st_mtime),
                    'created': datetime.fromtimestamp(stat.st_ctime)
                })
            except Exception as e:
                self.logger.error(f"Failed to get info for {json_file}: {e}")
        
        # Sort by modification time (newest first)
        datasets.sort(key=lambda x: x['modified'], reverse=True)
        return datasets
    
    def get_dataset_info(self, filepath: str) -> Dict[str, Any]:
        """Get information about a dataset without loading it"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            conversations = data.get('conversations', [])
            metadata = data.get('metadata', {})
            
            return {
                'filename': Path(filepath).name,
                'total_conversations': len(conversations),
                'date_range': self._get_date_range(conversations),
                'analysis_types': self._get_analysis_types(conversations),
                'pipeline_steps': self._get_pipeline_steps(conversations),
                'success_rate': self._calculate_success_rate(conversations),
                'metadata': metadata,
                'created_at': data.get('created_at'),
                'version': data.get('version', 'unknown')
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get dataset info for {filepath}: {e}")
            return {}
    
    def _get_date_range(self, conversations: List[Dict[str, Any]]) -> Dict[str, Optional[str]]:
        """Get date range of conversations"""
        if not conversations:
            return {'earliest': None, 'latest': None}
        
        timestamps = [conv.get('timestamp') for conv in conversations if conv.get('timestamp')]
        if not timestamps:
            return {'earliest': None, 'latest': None}
        
        return {
            'earliest': min(timestamps),
            'latest': max(timestamps)
        }
    
    def _get_analysis_types(self, conversations: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get analysis type distribution"""
        types = {}
        for conv in conversations:
            analysis_type = conv.get('analysis_type', 'unknown')
            types[analysis_type] = types.get(analysis_type, 0) + 1
        return types
    
    def _get_pipeline_steps(self, conversations: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get pipeline step distribution"""
        steps = {}
        for conv in conversations:
            pipeline_step = conv.get('pipeline_step', 'unknown')
            steps[pipeline_step] = steps.get(pipeline_step, 0) + 1
        return steps
    
    def _calculate_success_rate(self, conversations: List[Dict[str, Any]]) -> float:
        """Calculate success rate of conversations"""
        if not conversations:
            return 0.0
        
        successful = sum(1 for conv in conversations if conv.get('success', False))
        return successful / len(conversations)
    
    def cleanup_old_files(self, max_age_days: int = None) -> int:
        """Clean up old training data files"""
        if not self.config.cleanup_enabled:
            return 0
        
        max_age = max_age_days or self.config.max_age_days
        cutoff_date = datetime.now() - timedelta(days=max_age)
        
        removed_count = 0
        
        for json_file in self.data_dir.glob("*.json"):
            try:
                file_date = datetime.fromtimestamp(json_file.stat().st_mtime)
                if file_date < cutoff_date:
                    json_file.unlink()
                    removed_count += 1
                    self.logger.info(f"Removed old file: {json_file.name}")
            except Exception as e:
                self.logger.error(f"Failed to remove {json_file}: {e}")
        
        return removed_count
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            json_files = list(self.data_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in json_files)
            
            return {
                'total_files': len(json_files),
                'total_size_mb': total_size / (1024 * 1024),
                'data_directory': str(self.data_dir),
                'oldest_file': min((f.stat().st_mtime for f in json_files), default=None),
                'newest_file': max((f.stat().st_mtime for f in json_files), default=None),
                'average_file_size_mb': (total_size / len(json_files) / (1024 * 1024)) if json_files else 0
            }
        except Exception as e:
            self.logger.error(f"Failed to get storage statistics: {e}")
            return {}
    
    def merge_datasets(self, filepaths: List[str], output_filename: str = None) -> str:
        """Merge multiple datasets into one"""
        try:
            all_conversations = []
            merged_metadata = {'source_files': [], 'merge_date': datetime.now().isoformat()}
            
            for filepath in filepaths:
                dataset = self.load_dataset(filepath)
                all_conversations.extend(dataset.conversations)
                merged_metadata['source_files'].append(Path(filepath).name)
            
            # Create merged dataset
            merged_dataset = TrainingDataset(
                conversations=all_conversations,
                metadata=merged_metadata,
                created_at=datetime.now()
            )
            
            # Save merged dataset
            if not output_filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_filename = f"merged_dataset_{timestamp}.json"
            
            return self.save_dataset(merged_dataset, output_filename)
            
        except Exception as e:
            self.logger.error(f"Failed to merge datasets: {e}")
            raise

if __name__ == "__main__":
    # Suppress the RuntimeWarning about module import behavior
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning, 
                          message=".*found in sys.modules.*")
    
    # Example usage
    from .models import ConversationTurn
    
    print("Training Data Storage Examples:")
    
    # Create storage
    storage = TrainingDataStorage("data/training/test")
    
    # Create sample data
    sample_conversation = ConversationTurn(
        user_id="test_user",
        session_id="test_session",
        timestamp=datetime.now(),
        user_message="Test message",
        assistant_response="Test response",
        context={"test": "context"},
        tools_used=[],
        analysis_type="test",
        pipeline_step="test_step",
        success=True
    )
    
    sample_dataset = TrainingDataset(
        conversations=[sample_conversation],
        metadata={"test": True},
        created_at=datetime.now()
    )
    
    # Save and load
    saved_path = storage.save_dataset(sample_dataset)
    print(f"Saved to: {saved_path}")
    
    loaded_dataset = storage.load_dataset(saved_path)
    print(f"Loaded {len(loaded_dataset.conversations)} conversations")
    
    # Get statistics
    stats = storage.get_storage_statistics()
    print(f"Storage stats: {stats}")
    
    # List datasets
    datasets = storage.list_datasets()
    print(f"Available datasets: {len(datasets)}")
    
    # Cleanup
    os.remove(saved_path) 