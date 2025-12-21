"""
Export functionality for training data with async support.
Handles multiple export formats and compression options.
"""

import json
import logging
import gzip
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from .models import ConversationTurn, TrainingDataset
from .storage import TrainingDataStorage
from .async_storage import AsyncTrainingDataStorage
from .config import TrainingConfig
from .events import get_event_bus, EventType
from .export_formats import ExportFormatManager

class TrainingDataExporter:
    """Exports training data in various formats for LLM training"""
    
    def __init__(self, storage: Union[TrainingDataStorage, AsyncTrainingDataStorage], 
                 config: TrainingConfig = None):
        self.storage = storage
        self.config = config or TrainingConfig()
        self.logger = logging.getLogger("training_exporter")
        self.event_bus = get_event_bus()
        self.format_manager = ExportFormatManager()
        
        # Export statistics
        self._last_export_stats: Optional[Dict[str, Any]] = None
    
    async def export_for_training(
        self, 
        output_format: str = None,
        filter_analysis_type: str = None,
        min_success_rate: float = None,
        output_filename: str = None,
        compress: bool = False
    ) -> str:
        """Export collected data in format suitable for LLM training"""
        
        format_to_use = output_format or self.config.default_export_format
        min_success = min_success_rate or self.config.min_success_rate
        
        try:
            # Emit start event
            await self.event_bus.emit(
                EventType.PROGRESS_UPDATED,
                {"operation": "export", "progress": 0, "status": "starting"}
            )
            
            # Collect conversations
            all_conversations = await self._collect_all_conversations()
            
            await self.event_bus.emit(
                EventType.PROGRESS_UPDATED,
                {"operation": "export", "progress": 25, "status": "data_collected"}
            )
            
            # Apply filters
            filtered_conversations = self._apply_filters(
                all_conversations, 
                filter_analysis_type, 
                min_success
            )
            
            if not filtered_conversations:
                self.logger.warning("No conversations match the filter criteria")
                await self.event_bus.emit(
                    EventType.ERROR_OCCURRED,
                    {"error": "No conversations match filter criteria", "operation": "export"}
                )
                return ""
            
            await self.event_bus.emit(
                EventType.PROGRESS_UPDATED,
                {"operation": "export", "progress": 50, "status": "filtering_complete"}
            )
            
            # Generate output filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if not output_filename:
                output_filename = f"training_data_{format_to_use}_{timestamp}"
            
            # Export based on format
            output_file = await self.format_manager.export_conversations(
                conversations=filtered_conversations,
                format_type=format_to_use,
                output_filename=output_filename,
                data_dir=self.storage.data_dir,
                compress=compress
            )
            
            await self.event_bus.emit(
                EventType.PROGRESS_UPDATED,
                {"operation": "export", "progress": 90, "status": "export_complete"}
            )
            
            # Generate and cache statistics
            self._last_export_stats = self._generate_export_statistics(
                filtered_conversations, format_to_use, output_file
            )
            
            # Emit completion event
            await self.event_bus.emit(
                EventType.DATA_EXPORTED,
                {
                    "filename": output_file,
                    "format": format_to_use,
                    "conversations_count": len(filtered_conversations),
                    "compressed": compress
                }
            )
            
            await self.event_bus.emit(
                EventType.PROGRESS_UPDATED,
                {"operation": "export", "progress": 100, "status": "complete"}
            )
            
            self.logger.info(f"Exported {len(filtered_conversations)} conversations to {format_to_use}")
            return output_file
                
        except Exception as e:
            self.logger.error(f"Failed to export training data: {e}")
            await self.event_bus.emit(
                EventType.ERROR_OCCURRED,
                {"error": str(e), "operation": "export"}
            )
            raise
    
    async def _collect_all_conversations(self) -> List[ConversationTurn]:
        """Collect all conversations from storage"""
        all_conversations = []
        
        # Use async storage if available
        if isinstance(self.storage, AsyncTrainingDataStorage):
            datasets_info = await self.storage.list_datasets_async()
            
            # Load datasets concurrently
            load_tasks = []
            for dataset_info in datasets_info:
                task = self.storage.load_dataset_async(dataset_info['filepath'])
                load_tasks.append(task)
            
            if load_tasks:
                datasets = await asyncio.gather(*load_tasks, return_exceptions=True)
                
                for dataset in datasets:
                    if isinstance(dataset, TrainingDataset):
                        all_conversations.extend(dataset.conversations)
                    elif isinstance(dataset, Exception):
                        self.logger.error(f"Failed to load dataset: {dataset}")
        else:
            # Fallback to sync storage
            for dataset_info in self.storage.list_datasets():
                try:
                    dataset = self.storage.load_dataset(dataset_info['filepath'])
                    all_conversations.extend(dataset.conversations)
                except Exception as e:
                    self.logger.error(f"Failed to load dataset {dataset_info['filename']}: {e}")
        
        return all_conversations
    
    def _apply_filters(
        self, 
        conversations: List[ConversationTurn], 
        analysis_type: str = None,
        min_success_rate: float = None
    ) -> List[ConversationTurn]:
        """Apply filters to conversations"""
        
        filtered = conversations
        
        # Filter by analysis type
        if analysis_type:
            filtered = [conv for conv in filtered if conv.analysis_type == analysis_type]
            self.logger.info(f"Filtered by analysis type '{analysis_type}': {len(filtered)} conversations")
        
        # Filter by success rate
        if min_success_rate is not None:
            successful_conversations = [conv for conv in filtered if conv.success]
            current_success_rate = len(successful_conversations) / len(filtered) if filtered else 0
            
            if current_success_rate >= min_success_rate:
                filtered = successful_conversations
                self.logger.info(f"Filtered by success rate >= {min_success_rate}: {len(filtered)} conversations")
            else:
                self.logger.warning(f"Success rate {current_success_rate:.2f} below minimum {min_success_rate}")
        
        return filtered
    
    def _generate_export_statistics(
        self, 
        conversations: List[ConversationTurn], 
        format_type: str,
        output_file: str
    ) -> Dict[str, Any]:
        """Generate comprehensive export statistics"""
        
        if not conversations:
            return {"error": "No conversations in export"}
        
        stats = {
            "export_metadata": {
                "format": format_type,
                "output_file": output_file,
                "export_timestamp": datetime.now().isoformat(),
                "total_conversations": len(conversations)
            },
            "content_analysis": self._analyze_conversation_content(conversations),
            "distribution_analysis": self._analyze_distributions(conversations),
            "quality_metrics": self._calculate_quality_metrics(conversations)
        }
        
        return stats
    
    def _analyze_conversation_content(self, conversations: List[ConversationTurn]) -> Dict[str, Any]:
        """Analyze conversation content characteristics"""
        total_user_chars = sum(len(conv.user_message) for conv in conversations)
        total_assistant_chars = sum(len(conv.assistant_response) for conv in conversations)
        
        return {
            "average_user_message_length": total_user_chars / len(conversations),
            "average_assistant_response_length": total_assistant_chars / len(conversations),
            "total_characters": total_user_chars + total_assistant_chars,
            "conversations_with_tools": sum(1 for conv in conversations if conv.tools_used),
            "conversations_with_feedback": sum(1 for conv in conversations if conv.user_feedback)
        }
    
    def _analyze_distributions(self, conversations: List[ConversationTurn]) -> Dict[str, Any]:
        """Analyze data distributions"""
        analysis_types = {}
        pipeline_steps = {}
        tools_usage = {}
        
        for conv in conversations:
            # Analysis types
            analysis_type = conv.analysis_type
            analysis_types[analysis_type] = analysis_types.get(analysis_type, 0) + 1
            
            # Pipeline steps
            pipeline_step = conv.pipeline_step
            pipeline_steps[pipeline_step] = pipeline_steps.get(pipeline_step, 0) + 1
            
            # Tools usage
            for tool in conv.tools_used:
                tool_name = tool.get('name', 'unknown')
                tools_usage[tool_name] = tools_usage.get(tool_name, 0) + 1
        
        return {
            "analysis_types": analysis_types,
            "pipeline_steps": pipeline_steps,
            "tools_usage": tools_usage
        }
    
    def _calculate_quality_metrics(self, conversations: List[ConversationTurn]) -> Dict[str, Any]:
        """Calculate data quality metrics"""
        successful = sum(1 for conv in conversations if conv.success)
        success_rate = successful / len(conversations)
        
        # Date range
        timestamps = [conv.timestamp for conv in conversations]
        date_range = {
            "earliest": min(timestamps).isoformat(),
            "latest": max(timestamps).isoformat(),
            "span_days": (max(timestamps) - min(timestamps)).days
        }
        
        # Session diversity
        unique_sessions = len(set(conv.session_id for conv in conversations))
        unique_users = len(set(conv.user_id for conv in conversations))
        
        return {
            "success_rate": success_rate,
            "date_range": date_range,
            "unique_sessions": unique_sessions,
            "unique_users": unique_users,
            "avg_conversations_per_session": len(conversations) / unique_sessions if unique_sessions > 0 else 0
        }
    
    def export_statistics(self) -> Dict[str, Any]:
        """Get statistics from last export operation"""
        if self._last_export_stats is None:
            return {"error": "No export has been performed yet"}
        
        return self._last_export_stats
    
    async def export_batch(
        self,
        export_configs: List[Dict[str, Any]],
        output_dir: str = None
    ) -> List[str]:
        """Export multiple configurations in batch"""
        
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
        
        export_tasks = []
        
        for i, config in enumerate(export_configs):
            # Add batch info to filename if not specified
            if output_dir and 'output_filename' not in config:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                format_type = config.get('output_format', 'jsonl')
                config['output_filename'] = str(output_path / f"batch_export_{i+1}_{format_type}_{timestamp}")
            
            task = self.export_for_training(**config)
            export_tasks.append(task)
        
        # Execute all exports concurrently
        results = await asyncio.gather(*export_tasks, return_exceptions=True)
        
        # Filter successful exports
        successful_exports = [
            result for result in results 
            if isinstance(result, str) and result
        ]
        
        # Log any failures
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Batch export {i+1} failed: {result}")
        
        return successful_exports
    
    async def validate_export_integrity(self, export_file: str) -> Dict[str, Any]:
        """Validate the integrity of an exported file"""
        try:
            file_path = Path(export_file)
            
            if not file_path.exists():
                return {"valid": False, "error": "File does not exist"}
            
            # Basic file validation
            file_size = file_path.stat().st_size
            if file_size == 0:
                return {"valid": False, "error": "File is empty"}
            
            # Format-specific validation
            validation_result = await self.format_manager.validate_export_file(export_file)
            
            return {
                "valid": validation_result.get("valid", False),
                "file_size_bytes": file_size,
                "file_size_mb": file_size / (1024 * 1024),
                **validation_result
            }
        
        except Exception as e:
            return {"valid": False, "error": str(e)}


def main():
    """Test the refactored exporter"""
    import asyncio
    from .models import ConversationTurn
    
    async def test_exporter():
        print("Testing Refactored Training Data Exporter")
        print("=" * 50)
        
        # Create test storage
        from .async_storage import AsyncTrainingDataStorage
        storage = AsyncTrainingDataStorage("data/training/test")
        exporter = TrainingDataExporter(storage)
        
        # Create sample conversations
        sample_conversations = [
            ConversationTurn(
                user_id="test_user",
                session_id="test_session",
                timestamp=datetime.now(),
                user_message="How do I normalize my data?",
                assistant_response="You can use scanpy's pp.normalize_total function...",
                context={"analysis_type": "scrna_seq"},
                tools_used=[{"name": "scanpy", "success": True}],
                analysis_type="scrna_seq",
                pipeline_step="normalization",
                success=True
            )
        ]
        
        # Save sample data
        sample_dataset = TrainingDataset(
            conversations=sample_conversations,
            metadata={"test": True},
            created_at=datetime.now()
        )
        await storage.save_dataset_async(sample_dataset, "test_export.json")
        
        # Test export
        output_file = await exporter.export_for_training(
            output_format="jsonl",
            output_filename="test_output"
        )
        
        print(f"✓ Export completed: {output_file}")
        
        # Test statistics
        stats = exporter.export_statistics()
        print(f"✓ Export statistics generated: {len(stats)} sections")
        
        # Test validation
        validation = await exporter.validate_export_integrity(output_file)
        print(f"✓ Export validation: {validation.get('valid', False)}")
        
        # Cleanup
        import os
        for file in [output_file, "data/training/test/test_export.json"]:
            if os.path.exists(file):
                os.remove(file)
        
        print("✓ All exporter tests completed!")
    
    asyncio.run(test_exporter())
    
if __name__ == "__main__":
    main()