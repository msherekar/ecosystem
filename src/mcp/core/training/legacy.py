"""
Legacy Training Data Collector - Backward Compatibility Wrapper

This module provides backward compatibility for the refactored training system.
For new code, use the modular components in this package directly.

DEPRECATED: This module is for backward compatibility only.
Use the modular training system components directly for new code.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import from the new modular system
from . import (
    ConversationTurn, TrainingDataset, ConversationCollector,
    TrainingDataStorage, TrainingDataExporter, TrainingConfig,
    UserAnonymizer, ContextExtractor, create_training_system
)
from .utils import StreamlitSessionProvider

# Re-export models for backward compatibility
__all__ = [
    'ConversationTurn', 'TrainingDataset', 'TrainingDataCollector',
    'training_collector', 'get_training_collector'
]

class TrainingDataCollector:
    """
    Backward compatibility wrapper for the old TrainingDataCollector interface.
    
    This class maintains the same API as the original but delegates to the new
    modular system underneath.
    
    DEPRECATED: Use the modular training components directly for new code.
    """
    
    def __init__(self, data_dir: str = "data/training"):
        self.logger = logging.getLogger("training_collector")
        
        # Create the new system
        config = TrainingConfig(data_dir=data_dir)
        
        # Set up Streamlit session provider if available
        try:
            import streamlit as st
            session_provider = StreamlitSessionProvider(st.session_state)
        except ImportError:
            session_provider = None
        
        # Create the new collector
        storage = TrainingDataStorage(data_dir, config)
        self._collector = ConversationCollector(storage, config, session_provider)
        self._exporter = TrainingDataExporter(storage, config)
        
        # Backward compatibility properties
        self.data_dir = self._collector.storage.data_dir
        self.anonymize_data = config.anonymize_data
        self.collect_enabled = config.collect_enabled
        self.current_session_data = []  # For compatibility (read-only)
    
    @property
    def current_session_data(self) -> List[ConversationTurn]:
        """Get current session data (read-only for compatibility)"""
        return self._collector.get_current_session_turns()
    
    @current_session_data.setter
    def current_session_data(self, value):
        """Setter for backward compatibility (no-op)"""
        pass
    
    def _anonymize_user_id(self, user_identifier: str) -> str:
        """Backward compatibility method"""
        return self._collector.anonymizer.anonymize_user_id(user_identifier)
    
    def _get_session_id(self) -> str:
        """Backward compatibility method"""
        return self._collector._get_or_create_session_id()
    
    def _extract_context(self) -> Dict[str, Any]:
        """Backward compatibility method"""
        return self._collector.context_extractor.extract_analysis_context()
    
    def _determine_analysis_type(self) -> str:
        """Backward compatibility method"""
        return self._collector.context_extractor.determine_analysis_type()
    
    def _extract_tools_used(self, tool_results: List[str]) -> List[Dict[str, Any]]:
        """Backward compatibility method"""
        return self._collector.tool_extractor.extract_tools_used(tool_results)
    
    async def collect_conversation_turn(
        self,
        user_message: str,
        assistant_response: str,
        tool_results: List[str] = None,
        success: bool = True,
        user_feedback: str = None
    ) -> None:
        """Collect a single conversation turn (backward compatibility)"""
        await self._collector.collect_conversation_turn(
            user_message=user_message,
            assistant_response=assistant_response,
            tool_results=tool_results,
            success=success,
            user_feedback=user_feedback
        )
    
    async def _save_session_data(self) -> None:
        """Save session data (backward compatibility)"""
        await self._collector._save_session_data()
    
    def get_training_statistics(self) -> Dict[str, Any]:
        """Get training statistics (backward compatibility)"""
        stats = self._collector.get_training_statistics()
        
        # Transform to old format for compatibility
        if "totals" in stats:
            totals = stats["totals"]
            return {
                "total_files": stats.get("storage", {}).get("total_files", 0),
                "total_conversations": totals.get("conversations", 0),
                "analysis_types": totals.get("analysis_types", {}),
                "pipeline_steps": totals.get("pipeline_steps", {}),
                "date_range": totals.get("date_range", {"earliest": None, "latest": None})
            }
        
        return stats
    
    async def export_for_training(
        self, 
        output_format: str = "jsonl",
        filter_analysis_type: str = None,
        min_success_rate: float = 0.8
    ) -> str:
        """Export for training (backward compatibility)"""
        return self._exporter.export_for_training(
            output_format=output_format,
            filter_analysis_type=filter_analysis_type,
            min_success_rate=min_success_rate
        )
    
    def _format_instruction(self, conv: Dict[str, Any]) -> str:
        """Format instruction (backward compatibility)"""
        # Convert dict to ConversationTurn if needed
        if isinstance(conv, dict):
            conv_turn = ConversationTurn.from_dict(conv)
        else:
            conv_turn = conv
        return self._exporter._format_instruction(conv_turn)
    
    def _format_system_prompt(self, conv: Dict[str, Any]) -> str:
        """Format system prompt (backward compatibility)"""
        # Convert dict to ConversationTurn if needed
        if isinstance(conv, dict):
            conv_turn = ConversationTurn.from_dict(conv)
        else:
            conv_turn = conv
        return self._exporter._format_system_prompt(conv_turn)

# Global collector instance for backward compatibility
training_collector = TrainingDataCollector()

async def get_training_collector() -> TrainingDataCollector:
    """Get the global training data collector (backward compatibility)"""
    return training_collector

if __name__ == "__main__":
    print("Legacy Training Data Collector")
    print("DEPRECATED: Use the modular training components for new code")
    print("Available in training module:")
    print("- ConversationCollector")
    print("- TrainingDataStorage") 
    print("- TrainingDataExporter")
    print("- create_training_system()") 