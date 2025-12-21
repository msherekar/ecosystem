"""
Async storage operations for training data with improved performance.
Handles concurrent file operations and caching for scalability.
"""

import asyncio
import aiofiles
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import aiocache

from .models import ConversationTurn, TrainingDataset
from .config import TrainingConfig

class AsyncTrainingDataStorage:
    """Async storage manager with caching and concurrent operations"""
    
    def __init__(self, data_dir: str = "data/training", config: TrainingConfig = None):
        self.data_dir = Path(data_dir)
        self.config = config or TrainingConfig()
        self.logger = logging.getLogger("async_storage")
        
        # Ensure directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize cache
        self.cache = aiocache.SimpleMemoryCache()
        self._file_locks: Dict[str, asyncio.Lock] = {}
        self._stats_cache: Optional[Dict[str, Any]] = None
        self._cache_ttl = 300  # 5 minutes
    
    async def save_dataset_async(self, dataset: TrainingDataset, filename: str = None) -> str:
        """Save dataset asynchronously with file locking"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"dataset_{timestamp}.json"
        
        filepath = self.data_dir / filename
        
        # Get file lock
        lock = self._get_file_lock(str(filepath))
        
        async with lock:
            try:
                # Check if file would exceed size limit
                if await self._would_exceed_size_limit_async(dataset):
                    return await self._save_split_dataset_async(dataset, filename)
                
                # Save to JSON asynchronously
                async with aiofiles.open(filepath, 'w') as f:
                    await f.write(json.dumps(dataset.to_dict(), indent=2, default=str))
                
                # Update cache
                await self.cache.set(f"dataset_{filename}", dataset.to_dict(), ttl=self._cache_ttl)
                
                self.logger.info(f"Saved dataset with {len(dataset.conversations)} conversations to {filename}")
                return str(filepath)
                
            except Exception as e:
                self.logger.error(f"Failed to save dataset: {e}")
                raise
    
    def _get_file_lock(self, filepath: str) -> asyncio.Lock:
        """Get or create file lock for concurrent access"""
        if filepath not in self._file_locks:
            self._file_locks[filepath] = asyncio.Lock()
        return self._file_locks[filepath]
    
    async def _would_exceed_size_limit_async(self, dataset: TrainingDataset) -> bool:
        """Check if dataset would exceed file size limit"""
        # Estimate size: ~1KB per conversation
        estimated_size_mb = len(dataset.conversations) * 1 / 1024
        return estimated_size_mb > self.config.max_file_size_mb
    
    async def _save_split_dataset_async(self, dataset: TrainingDataset, base_filename: str) -> str:
        """Save dataset split into multiple files asynchronously"""
        conversations_per_file = self._calculate_conversations_per_file(dataset)
        save_tasks = []
        
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
            
            # Create save task
            save_tasks.append(self.save_dataset_async(split_dataset, split_filename))
        
        # Execute all saves concurrently
        saved_files = await asyncio.gather(*save_tasks)
        
        self.logger.info(f"Split dataset into {len(saved_files)} files")
        return saved_files[0]  # Return first file
    
    def _calculate_conversations_per_file(self, dataset: TrainingDataset) -> int:
        """Calculate optimal conversations per file"""
        total_conversations = len(dataset.conversations)
        max_size_kb = self.config.max_file_size_mb * 1024
        
        # Estimate: 1KB per conversation
        conversations_per_file = max_size_kb
        
        return max(10, min(conversations_per_file, total_conversations))
    
    async def load_dataset_async(self, filepath: str, use_cache: bool = True) -> TrainingDataset:
        """Load dataset asynchronously with caching"""
        filename = Path(filepath).name
        cache_key = f"dataset_{filename}"
        
        # Check cache first
        if use_cache:
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                return TrainingDataset.from_dict(cached_data)
        
        try:
            async with aiofiles.open(filepath, 'r') as f:
                content = await f.read()
                data = json.loads(content)
            
            dataset = TrainingDataset.from_dict(data)
            
            # Cache the result
            await self.cache.set(cache_key, data, ttl=self._cache_ttl)
            
            self.logger.info(f"Loaded dataset with {len(dataset.conversations)} conversations from {filepath}")
            return dataset
            
        except Exception as e:
            self.logger.error(f"Failed to load dataset from {filepath}: {e}")
            raise
    
    async def list_datasets_async(self) -> List[Dict[str, Any]]:
        """List all available datasets asynchronously"""
        datasets = []
        
        # Use asyncio.gather for concurrent file stat operations
        json_files = list(self.data_dir.glob("*.json"))
        
        if not json_files:
            return datasets
        
        async def get_file_info(json_file: Path) -> Dict[str, Any]:
            try:
                stat = json_file.stat()
                return {
                    'filename': json_file.name,
                    'filepath': str(json_file),
                    'size_mb': stat.st_size / (1024 * 1024),
                    'modified': datetime.fromtimestamp(stat.st_mtime),
                    'created': datetime.fromtimestamp(stat.st_ctime)
                }
            except Exception as e:
                self.logger.error(f"Failed to get info for {json_file}: {e}")
                return None
        
        # Process files concurrently
        file_info_tasks = [get_file_info(json_file) for json_file in json_files]
        file_infos = await asyncio.gather(*file_info_tasks, return_exceptions=True)
        
        # Filter out None results and exceptions
        datasets = [info for info in file_infos if info and not isinstance(info, Exception)]
        
        # Sort by modification time (newest first)
        datasets.sort(key=lambda x: x['modified'], reverse=True)
        return datasets
    
    async def get_dataset_info_async(self, filepath: str, use_cache: bool = True) -> Dict[str, Any]:
        """Get dataset information asynchronously"""
        filename = Path(filepath).name
        cache_key = f"info_{filename}"
        
        # Check cache
        if use_cache:
            cached_info = await self.cache.get(cache_key)
            if cached_info:
                return cached_info
        
        try:
            async with aiofiles.open(filepath, 'r') as f:
                content = await f.read()
                data = json.loads(content)
            
            conversations = data.get('conversations', [])
            metadata = data.get('metadata', {})
            
            info = {
                'filename': filename,
                'total_conversations': len(conversations),
                'date_range': self._get_date_range(conversations),
                'analysis_types': self._get_analysis_types(conversations),
                'pipeline_steps': self._get_pipeline_steps(conversations),
                'success_rate': self._calculate_success_rate(conversations),
                'metadata': metadata,
                'created_at': data.get('created_at'),
                'version': data.get('version', 'unknown')
            }
            
            # Cache the result
            await self.cache.set(cache_key, info, ttl=self._cache_ttl)
            
            return info
            
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
    
    async def cleanup_old_files_async(self, max_age_days: int = None) -> int:
        """Clean up old files asynchronously"""
        if not self.config.cleanup_enabled:
            return 0
        
        max_age = max_age_days or self.config.max_age_days
        cutoff_date = datetime.now() - timedelta(days=max_age)
        
        json_files = list(self.data_dir.glob("*.json"))
        removal_tasks = []
        
        async def remove_file_if_old(json_file: Path) -> bool:
            try:
                file_date = datetime.fromtimestamp(json_file.stat().st_mtime)
                if file_date < cutoff_date:
                    json_file.unlink()
                    # Remove from cache
                    await self.cache.delete(f"dataset_{json_file.name}")
                    await self.cache.delete(f"info_{json_file.name}")
                    self.logger.info(f"Removed old file: {json_file.name}")
                    return True
                return False
            except Exception as e:
                self.logger.error(f"Failed to remove {json_file}: {e}")
                return False
        
        # Process removals concurrently
        removal_tasks = [remove_file_if_old(json_file) for json_file in json_files]
        removal_results = await asyncio.gather(*removal_tasks, return_exceptions=True)
        
        removed_count = sum(1 for result in removal_results if result is True)
        return removed_count
    
    async def get_storage_statistics_async(self) -> Dict[str, Any]:
        """Get storage statistics asynchronously"""
        cache_key = "storage_stats"
        
        # Check cache
        cached_stats = await self.cache.get(cache_key)
        if cached_stats:
            return cached_stats
        
        try:
            json_files = list(self.data_dir.glob("*.json"))
            
            if not json_files:
                return {
                    'total_files': 0,
                    'total_size_mb': 0,
                    'data_directory': str(self.data_dir),
                    'oldest_file': None,
                    'newest_file': None,
                    'average_file_size_mb': 0
                }
            
            # Process file stats concurrently
            async def get_file_stat(file_path: Path) -> tuple:
                stat = file_path.stat()
                return stat.st_size, stat.st_mtime
            
            stat_tasks = [get_file_stat(f) for f in json_files]
            stat_results = await asyncio.gather(*stat_tasks)
            
            sizes, mtimes = zip(*stat_results)
            total_size = sum(sizes)
            
            stats = {
                'total_files': len(json_files),
                'total_size_mb': total_size / (1024 * 1024),
                'data_directory': str(self.data_dir),
                'oldest_file': min(mtimes),
                'newest_file': max(mtimes),
                'average_file_size_mb': (total_size / len(json_files) / (1024 * 1024))
            }
            
            # Cache for 5 minutes
            await self.cache.set(cache_key, stats, ttl=300)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get storage statistics: {e}")
            return {}
    
    async def merge_datasets_async(self, filepaths: List[str], output_filename: str = None) -> str:
        """Merge multiple datasets asynchronously"""
        try:
            # Load all datasets concurrently
            load_tasks = [self.load_dataset_async(filepath) for filepath in filepaths]
            datasets = await asyncio.gather(*load_tasks)
            
            # Merge conversations
            all_conversations = []
            merged_metadata = {
                'source_files': [Path(fp).name for fp in filepaths],
                'merge_date': datetime.now().isoformat()
            }
            
            for dataset in datasets:
                all_conversations.extend(dataset.conversations)
            
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
            
            return await self.save_dataset_async(merged_dataset, output_filename)
            
        except Exception as e:
            self.logger.error(f"Failed to merge datasets: {e}")
            raise
    
    async def clear_cache(self) -> None:
        """Clear all cached data"""
        await self.cache.clear()
        self.logger.info("Storage cache cleared")

if __name__ == "__main__":
    def main():
        """Test async storage operations"""
        import asyncio
        from .models import ConversationTurn
        
        async def test_async_storage():
            print("Testing Async Training Data Storage")
            print("=" * 40)
            
            # Create storage
            storage = AsyncTrainingDataStorage("data/training/test")
            
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
            
            # Test async save
            saved_path = await storage.save_dataset_async(sample_dataset)
            print(f"✓ Async save: {saved_path}")
            
            # Test async load
            loaded_dataset = await storage.load_dataset_async(saved_path)
            print(f"✓ Async load: {len(loaded_dataset.conversations)} conversations")
            
            # Test async list
            datasets = await storage.list_datasets_async()
            print(f"✓ Async list: {len(datasets)} datasets")
            
            # Test async statistics
            stats = await storage.get_storage_statistics_async()
            print(f"✓ Async statistics: {stats['total_files']} files")
            
            # Test cache performance
            import time
            start = time.time()
            await storage.get_dataset_info_async(saved_path, use_cache=False)
            no_cache_time = time.time() - start
            
            start = time.time()
            await storage.get_dataset_info_async(saved_path, use_cache=True)
            cache_time = time.time() - start
            
            print(f"✓ Cache performance: {cache_time:.4f}s vs {no_cache_time:.4f}s")
            
            # Cleanup
            import os
            if os.path.exists(saved_path):
                os.remove(saved_path)
            
            print("✓ All async storage tests completed!")
        
        asyncio.run(test_async_storage())
    
    main()