"""
Core conversation collection functionality.
Handles individual conversation turns and session management.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from .models import ConversationTurn, TrainingDataset
from .storage import TrainingDataStorage
from .config import TrainingConfig
from .utils import UserAnonymizer, ContextExtractor, ToolUsageExtractor
from .events import get_event_bus, EventType
from .security import SecureTrainingManager
from .validation import ConversationValidator

class ConversationCollector:
    """Core collector for individual conversation turns"""
    
    def __init__(
        self, 
        storage: TrainingDataStorage, 
        config: TrainingConfig,
        session_provider = None
    ):
        self.storage = storage
        self.config = config
        self.session_provider = session_provider
        self.logger = logging.getLogger("conversation_collector")
        
        # Initialize components
        self.anonymizer = UserAnonymizer()
        self.context_extractor = ContextExtractor(session_provider)
        self.tool_extractor = ToolUsageExtractor()
        self.validator = ConversationValidator()
        self.security_manager = SecureTrainingManager()
        self.event_bus = get_event_bus()
        
        # Current session state
        self.current_session_data = []
        self.current_session_id = None
        
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Setup logging configuration"""
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        self.logger.setLevel(log_level)
    
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
        """Collect and validate a single conversation turn"""
        
        if not self.config.collect_enabled:
            self.logger.debug("Collection disabled, skipping")
            return None
        
        try:
            # Build conversation data
            conversation_data = {
                "user_message": user_message,
                "assistant_response": assistant_response,
                "timestamp": datetime.now(),
                "success": success,
                "user_feedback": user_feedback
            }
            
            # Validate data
            validation_result = self.validator.validate_conversation_turn(conversation_data)
            if not validation_result.is_valid:
                self.logger.error(f"Validation failed: {validation_result.issues}")
                return None
            
            # Use sanitized data
            validated_data = validation_result.sanitized_data
            
            # Apply security measures
            secured_data = self.security_manager.secure_conversation_data(
                validated_data, user_id
            )
            
            # Generate IDs and extract context
            anonymized_user_id = self.anonymizer.anonymize_user_id(user_id) if self.config.anonymize_data else user_id
            session_id = session_id or self._get_or_create_session_id()
            
            context = self.context_extractor.extract_analysis_context()
            if additional_context:
                context.update(additional_context)
            
            tools_used = self.tool_extractor.extract_tools_used(tool_results or [])
            analysis_type = self.context_extractor.determine_analysis_type()
            pipeline_step = context.get('current_step', 'unknown')
            
            # Create conversation turn
            turn = ConversationTurn(
                user_id=anonymized_user_id,
                session_id=session_id,
                timestamp=validated_data["timestamp"],
                user_message=validated_data["user_message"],
                assistant_response=validated_data["assistant_response"],
                context=context,
                tools_used=tools_used,
                analysis_type=analysis_type,
                pipeline_step=pipeline_step,
                success=validated_data["success"],
                user_feedback=validated_data.get("user_feedback")
            )
            
            # Add to current session
            self.current_session_data.append(turn)
            
            # Emit event
            await self.event_bus.emit(
                EventType.CONVERSATION_COLLECTED,
                {
                    "session_id": session_id,
                    "analysis_type": analysis_type,
                    "pipeline_step": pipeline_step,
                    "success": success
                }
            )
            
            # Auto-save if needed
            if len(self.current_session_data) >= self.config.auto_save_interval:
                await self._save_session_data()
            
            self.logger.debug(f"Collected conversation turn: {analysis_type}/{pipeline_step}")
            return turn
            
        except Exception as e:
            self.logger.error(f"Failed to collect conversation turn: {e}")
            await self.event_bus.emit(
                EventType.ERROR_OCCURRED,
                {"error": str(e), "component": "collector"}
            )
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
                metadata=self._build_session_metadata(session_id),
                created_at=datetime.now()
            )
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"session_{session_id}_{timestamp}.json"
            
            # Save to storage
            await self.storage.save_dataset_async(dataset, filename)
            
            # Emit event
            await self.event_bus.emit(
                EventType.DATASET_SAVED,
                {
                    "filename": filename,
                    "conversations_count": len(self.current_session_data),
                    "session_id": session_id
                }
            )
            
            self.logger.info(f"Saved {len(self.current_session_data)} conversation turns")
            
            # Clear current session data
            self.current_session_data = []
            
        except Exception as e:
            self.logger.error(f"Failed to save session data: {e}")
            await self.event_bus.emit(
                EventType.ERROR_OCCURRED,
                {"error": str(e), "component": "collector", "operation": "save"}
            )
    
    def _build_session_metadata(self, session_id: str) -> Dict[str, Any]:
        """Build metadata for session dataset"""
        return {
            "session_id": session_id,
            "total_turns": len(self.current_session_data),
            "analysis_types": list(set(turn.analysis_type for turn in self.current_session_data)),
            "pipeline_steps": list(set(turn.pipeline_step for turn in self.current_session_data)),
            "collection_date": datetime.now().isoformat(),
            "success_rate": sum(1 for turn in self.current_session_data if turn.success) / len(self.current_session_data),
            "tools_used": list(set(
                tool.get('name', 'unknown') 
                for turn in self.current_session_data 
                for tool in turn.tools_used
            ))
        }
    
    async def finalize_session(self) -> None:
        """Finalize current session and save any remaining data"""
        if self.current_session_data:
            await self._save_session_data()
        
        # Emit session ended event
        await self.event_bus.emit(
            EventType.SESSION_ENDED,
            {
                "session_id": self.current_session_id,
                "final_turn_count": len(self.current_session_data)
            }
        )
        
        # Reset session
        self.current_session_id = None
        self.logger.info("Session finalized")
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get statistics for current session"""
        if not self.current_session_data:
            return {"total_turns": 0}
        
        return {
            "total_turns": len(self.current_session_data),
            "session_id": self.current_session_id,
            "analysis_types": self._count_analysis_types(),
            "pipeline_steps": self._count_pipeline_steps(),
            "success_rate": self._calculate_success_rate(),
            "tools_used": self._get_unique_tools(),
            "started_at": min(turn.timestamp for turn in self.current_session_data).isoformat(),
            "latest_turn": max(turn.timestamp for turn in self.current_session_data).isoformat()
        }
    
    def _count_analysis_types(self) -> Dict[str, int]:
        """Count analysis types in current session"""
        counts = {}
        for turn in self.current_session_data:
            analysis_type = turn.analysis_type
            counts[analysis_type] = counts.get(analysis_type, 0) + 1
        return counts
    
    def _count_pipeline_steps(self) -> Dict[str, int]:
        """Count pipeline steps in current session"""
        counts = {}
        for turn in self.current_session_data:
            pipeline_step = turn.pipeline_step
            counts[pipeline_step] = counts.get(pipeline_step, 0) + 1
        return counts
    
    def _calculate_success_rate(self) -> float:
        """Calculate success rate for current session"""
        if not self.current_session_data:
            return 0.0
        successful = sum(1 for turn in self.current_session_data if turn.success)
        return successful / len(self.current_session_data)
    
    def _get_unique_tools(self) -> List[str]:
        """Get list of unique tools used in session"""
        tools = set()
        for turn in self.current_session_data:
            for tool in turn.tools_used:
                tools.add(tool.get('name', 'unknown'))
        return list(tools)
    
    def is_collecting(self) -> bool:
        """Check if collection is currently enabled"""
        return self.config.collect_enabled
    
    def get_current_session_turns(self) -> List[ConversationTurn]:
        """Get current session conversation turns"""
        return self.current_session_data.copy()


def main():
    """Test the collector"""
    import asyncio
    from .utils import MockSessionProvider
    
    async def test_collector():
        print("Testing Conversation Collector")
        print("=" * 40)
        
        # Create mock session
        mock_session = MockSessionProvider({
            "qc_done": True,
            "scrna_current_step": "normalization"
        })
        
        # Create collector
        config = TrainingConfig(data_dir="data/test", collect_enabled=True)
        storage = TrainingDataStorage("data/test", config)
        collector = ConversationCollector(storage, config, mock_session)
        
        # Test conversation collection
        turn = await collector.collect_conversation_turn(
            user_message="How do I normalize my data?",
            assistant_response="You can use scanpy's normalize function...",
            tool_results=["Tool scanpy: Success"],
            success=True
        )
        
        print(f"✓ Collected turn: {turn is not None}")
        
        # Test session stats
        stats = collector.get_session_statistics()
        print(f"✓ Session stats: {stats['total_turns']} turns")
        
        # Test finalization
        await collector.finalize_session()
        print("✓ Session finalized")
    
    asyncio.run(test_collector())
    
if __name__ == "__main__":
    main()