"""
Conversation collection orchestration.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from .models import ConversationTurn, TrainingDataset
from .storage import TrainingDataStorage
from .config import TrainingConfig
from .utils import UserAnonymizer, ContextExtractor, ToolUsageExtractor, SessionProvider

class ConversationCollector:
    """Main collector that orchestrates training data collection"""
    
    def __init__(
        self, 
        storage: TrainingDataStorage, 
        config: TrainingConfig,
        session_provider: SessionProvider = None
    ):
        self.storage = storage
        self.config = config
        self.logger = logging.getLogger("conversation_collector")
        
        # Initialize components
        self.anonymizer = UserAnonymizer()
        self.context_extractor = ContextExtractor(session_provider)
        self.tool_extractor = ToolUsageExtractor()
        
        # Current session data
        self.current_session_data = []
        self.current_session_id = None
        
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
    
    async def collect_conversation_turn(
        self,
        user_message: str,
        assistant_response: str,
        user_id: str = "default_user",
        session_id: str = None,
        tool_results: List[str] = None,
        success: bool = True,
        user_feedback: str = None,
        additional_context: Dict[str, Any] = None
    ) -> Optional[ConversationTurn]:
        """Collect a single conversation turn"""
        
        if not self.config.collect_enabled:
            self.logger.debug("Collection disabled, skipping")
            return None
        
        try:
            # Generate IDs
            anonymized_user_id = self.anonymizer.anonymize_user_id(user_id) if self.config.anonymize_data else user_id
            session_id = session_id or self._get_or_create_session_id()
            
            # Extract context and tools
            context = self.context_extractor.extract_analysis_context()
            if additional_context:
                context.update(additional_context)
            
            tools_used = self.tool_extractor.extract_tools_used(tool_results or [])
            
            # Determine analysis info
            analysis_type = self.context_extractor.determine_analysis_type()
            pipeline_step = context.get('current_step', 'unknown')
            
            # Create conversation turn
            turn = ConversationTurn(
                user_id=anonymized_user_id,
                session_id=session_id,
                timestamp=datetime.now(),
                user_message=user_message,
                assistant_response=assistant_response,
                context=context,
                tools_used=tools_used,
                analysis_type=analysis_type,
                pipeline_step=pipeline_step,
                success=success,
                user_feedback=user_feedback
            )
            
            # Add to current session
            self.current_session_data.append(turn)
            
            # Auto-save periodically
            if len(self.current_session_data) >= self.config.auto_save_interval:
                await self._save_session_data()
            
            self.logger.debug(f"Collected conversation turn: {analysis_type}/{pipeline_step}")
            return turn
            
        except Exception as e:
            self.logger.error(f"Failed to collect conversation turn: {e}")
            return None
    
    def _get_or_create_session_id(self) -> str:
        """Get or create current session ID"""
        if not self.current_session_id:
            self.current_session_id = self.anonymizer.generate_session_id()
        return self.current_session_id
    
    async def _save_session_data(self) -> None:
        """Save current session data to storage"""
        if not self.current_session_data:
            return
        
        try:
            session_id = self._get_or_create_session_id()
            
            # Create dataset
            dataset = TrainingDataset(
                conversations=self.current_session_data.copy(),
                metadata={
                    "session_id": session_id,
                    "total_turns": len(self.current_session_data),
                    "analysis_types": list(set(turn.analysis_type for turn in self.current_session_data)),
                    "pipeline_steps": list(set(turn.pipeline_step for turn in self.current_session_data)),
                    "collection_date": datetime.now().isoformat(),
                    "success_rate": sum(1 for turn in self.current_session_data if turn.success) / len(self.current_session_data)
                },
                created_at=datetime.now()
            )
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"session_{session_id}_{timestamp}.json"
            
            # Save to storage
            self.storage.save_dataset(dataset, filename)
            
            self.logger.info(f"Saved {len(self.current_session_data)} conversation turns to {filename}")
            
            # Clear current session data
            self.current_session_data = []
            
        except Exception as e:
            self.logger.error(f"Failed to save session data: {e}")
    
    async def finalize_session(self) -> None:
        """Finalize current session and save any remaining data"""
        if self.current_session_data:
            await self._save_session_data()
        
        # Reset session
        self.current_session_id = None
        self.logger.info("Session finalized")
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get statistics for current session"""
        if not self.current_session_data:
            return {"total_turns": 0}
        
        stats = {
            "total_turns": len(self.current_session_data),
            "session_id": self.current_session_id,
            "analysis_types": {},
            "pipeline_steps": {},
            "success_rate": 0,
            "tools_used": set(),
            "started_at": None,
            "latest_turn": None
        }
        
        for turn in self.current_session_data:
            # Analysis types
            analysis_type = turn.analysis_type
            stats["analysis_types"][analysis_type] = stats["analysis_types"].get(analysis_type, 0) + 1
            
            # Pipeline steps
            pipeline_step = turn.pipeline_step
            stats["pipeline_steps"][pipeline_step] = stats["pipeline_steps"].get(pipeline_step, 0) + 1
            
            # Tools
            for tool in turn.tools_used:
                stats["tools_used"].add(tool.get('name', 'unknown'))
        
        # Success rate
        successful = sum(1 for turn in self.current_session_data if turn.success)
        stats["success_rate"] = successful / len(self.current_session_data)
        
        # Timestamps
        timestamps = [turn.timestamp for turn in self.current_session_data]
        stats["started_at"] = min(timestamps).isoformat()
        stats["latest_turn"] = max(timestamps).isoformat()
        
        # Convert set to list for JSON serialization
        stats["tools_used"] = list(stats["tools_used"])
        
        return stats
    
    def get_training_statistics(self) -> Dict[str, Any]:
        """Get comprehensive training statistics from storage"""
        try:
            # Get storage stats
            storage_stats = self.storage.get_storage_statistics()
            
            # Get dataset info for all files
            detailed_stats = {
                "storage": storage_stats,
                "datasets": [],
                "totals": {
                    "conversations": 0,
                    "analysis_types": {},
                    "pipeline_steps": {},
                    "overall_success_rate": 0,
                    "date_range": {"earliest": None, "latest": None}
                }
            }
            
            total_conversations = 0
            total_successful = 0
            all_timestamps = []
            
            for dataset_info in self.storage.list_datasets():
                try:
                    info = self.storage.get_dataset_info(dataset_info['filepath'])
                    detailed_stats["datasets"].append(info)
                    
                    # Aggregate totals
                    conv_count = info.get('total_conversations', 0)
                    total_conversations += conv_count
                    
                    success_rate = info.get('success_rate', 0)
                    total_successful += int(conv_count * success_rate)
                    
                    # Analysis types
                    for analysis_type, count in info.get('analysis_types', {}).items():
                        detailed_stats["totals"]["analysis_types"][analysis_type] = \
                            detailed_stats["totals"]["analysis_types"].get(analysis_type, 0) + count
                    
                    # Pipeline steps
                    for step, count in info.get('pipeline_steps', {}).items():
                        detailed_stats["totals"]["pipeline_steps"][step] = \
                            detailed_stats["totals"]["pipeline_steps"].get(step, 0) + count
                    
                    # Date range
                    date_range = info.get('date_range', {})
                    if date_range.get('earliest'):
                        all_timestamps.append(date_range['earliest'])
                    if date_range.get('latest'):
                        all_timestamps.append(date_range['latest'])
                        
                except Exception as e:
                    self.logger.error(f"Failed to get info for {dataset_info['filename']}: {e}")
            
            # Calculate overall stats
            detailed_stats["totals"]["conversations"] = total_conversations
            detailed_stats["totals"]["overall_success_rate"] = total_successful / total_conversations if total_conversations > 0 else 0
            
            if all_timestamps:
                detailed_stats["totals"]["date_range"]["earliest"] = min(all_timestamps)
                detailed_stats["totals"]["date_range"]["latest"] = max(all_timestamps)
            
            return detailed_stats
            
        except Exception as e:
            self.logger.error(f"Failed to get training statistics: {e}")
            return {"error": str(e)}
    
    async def cleanup_old_data(self, max_age_days: int = None) -> int:
        """Clean up old training data"""
        try:
            removed_count = self.storage.cleanup_old_files(max_age_days)
            self.logger.info(f"Cleaned up {removed_count} old files")
            return removed_count
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")
            return 0
    
    def update_config(self, **kwargs) -> None:
        """Update collector configuration"""
        self.config = self.config.update(**kwargs)
        self.logger.info(f"Updated configuration: {kwargs}")
    
    def is_collecting(self) -> bool:
        """Check if collection is currently enabled"""
        return self.config.collect_enabled
    
    def get_current_session_turns(self) -> List[ConversationTurn]:
        """Get current session conversation turns"""
        return self.current_session_data.copy()

# Factory function for easy instantiation
def create_collector(
    data_dir: str = "data/training",
    config: TrainingConfig = None,
    session_provider: SessionProvider = None
) -> ConversationCollector:
    """Create a conversation collector with default components"""
    
    if config is None:
        config = TrainingConfig(data_dir=data_dir)
    
    storage = TrainingDataStorage(data_dir, config)
    return ConversationCollector(storage, config, session_provider)

# Global collector instance for backward compatibility
_global_collector: Optional[ConversationCollector] = None

def get_global_collector() -> ConversationCollector:
    """Get or create global collector instance"""
    global _global_collector
    if _global_collector is None:
        _global_collector = create_collector()
    return _global_collector

# Async wrapper for backward compatibility
async def collect_conversation_turn(
    user_message: str,
    assistant_response: str,
    tool_results: List[str] = None,
    success: bool = True,
    user_feedback: str = None
) -> Optional[ConversationTurn]:
    """Convenience function using global collector"""
    collector = get_global_collector()
    return await collector.collect_conversation_turn(
        user_message=user_message,
        assistant_response=assistant_response,
        tool_results=tool_results,
        success=success,
        user_feedback=user_feedback
    )

if __name__ == "__main__":
    # Example usage
    import asyncio
    from .utils import MockSessionProvider
    
    async def main():
        print("Conversation Collector Examples:")
        
        # Create collector with mock session
        mock_session = MockSessionProvider({
            "qc_done": True,
            "scrna_current_step": "normalization",
            "n_top_genes": 2000
        })
        
        collector = create_collector(
            data_dir="data/training/test",
            session_provider=mock_session
        )
        
        # Collect some conversation turns
        turn1 = await collector.collect_conversation_turn(
            user_message="How do I normalize my data?",
            assistant_response="You can use scanpy's pp.normalize_total function...",
            tool_results=["Tool scanpy: Successfully normalized data"],
            success=True
        )
        
        turn2 = await collector.collect_conversation_turn(
            user_message="What's next after normalization?",
            assistant_response="After normalization, you typically want to identify highly variable genes...",
            success=True
        )
        
        print(f"Collected turns: {turn1 is not None}, {turn2 is not None}")
        
        # Get session statistics
        session_stats = collector.get_session_statistics()
        print(f"Session stats: {session_stats}")
        
        # Finalize session
        await collector.finalize_session()
        
        # Get training statistics
        training_stats = collector.get_training_statistics()
        print(f"Training stats: {training_stats}")
        
        print("Example completed successfully!")
    
    asyncio.run(main()) 