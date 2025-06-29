"""
Simple Training Collector Interface
Provides a basic interface for collecting training data from LLM interactions.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime


class SimpleTrainingCollector:
    """Simple training data collector for LLM interactions"""
    
    def __init__(self):
        self.logger = logging.getLogger("training_collector")
        self.conversations = []
        self.enabled = True
    
    async def collect_conversation_turn(
        self,
        user_message: str,
        assistant_response: str,
        tool_results: List[str] = None,
        success: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Collect a conversation turn for training"""
        if not self.enabled:
            return None
        
        try:
            turn_data = {
                "user_message": user_message,
                "assistant_response": assistant_response,
                "tool_results": tool_results or [],
                "success": success,
                "timestamp": datetime.now().isoformat(),
                **kwargs
            }
            
            self.conversations.append(turn_data)
            self.logger.debug("Collected conversation turn")
            return turn_data
            
        except Exception as e:
            self.logger.error(f"Failed to collect conversation turn: {e}")
            return None
    
    def get_training_statistics(self) -> Dict[str, Any]:
        """Get training statistics"""
        if not self.conversations:
            return {"total_conversations": 0}
        
        successful = sum(1 for conv in self.conversations if conv.get("success", False))
        
        return {
            "total_conversations": len(self.conversations),
            "successful_conversations": successful,
            "success_rate": successful / len(self.conversations) if self.conversations else 0,
            "last_conversation": self.conversations[-1]["timestamp"] if self.conversations else None
        }
    
    async def export_for_training(
        self,
        output_format: str = "jsonl",
        filter_analysis_type: str = None,
        **kwargs
    ) -> Optional[str]:
        """Export training data (basic implementation)"""
        if not self.conversations:
            return None
        
        # Simple export - just return a placeholder filename
        # In a full implementation, this would write to a file
        return f"training_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{output_format}"
    
    def set_enabled(self, enabled: bool):
        """Enable or disable training collection"""
        self.enabled = enabled
        self.logger.info(f"Training collection {'enabled' if enabled else 'disabled'}")


# Global collector instance
_training_collector: Optional[SimpleTrainingCollector] = None


async def get_training_collector() -> Optional[SimpleTrainingCollector]:
    """Get the global training collector instance"""
    global _training_collector
    
    if _training_collector is None:
        try:
            _training_collector = SimpleTrainingCollector()
        except Exception as e:
            logging.getLogger("training_collector").warning(f"Failed to initialize training collector: {e}")
            return None
    
    return _training_collector


def set_training_collector(collector: SimpleTrainingCollector):
    """Set the global training collector instance"""
    global _training_collector
    _training_collector = collector


async def main():
    """Test the training collector"""
    print("🧪 Testing SimpleTrainingCollector...")
    
    # Get collector
    collector = await get_training_collector()
    print(f"✅ Collector initialized: {collector is not None}")
    
    if collector:
        # Test conversation collection
        turn = await collector.collect_conversation_turn(
            user_message="How do I analyze scRNA-seq data?",
            assistant_response="You can use scanpy for scRNA-seq analysis...",
            tool_results=["scanpy.pp.filter_cells", "scanpy.pp.normalize_total"],
            success=True
        )
        print(f"✅ Conversation collected: {turn is not None}")
        
        # Test statistics
        stats = collector.get_training_statistics()
        print(f"✅ Statistics: {stats['total_conversations']} conversations")
        
        # Test export
        export_file = await collector.export_for_training()
        print(f"✅ Export file: {export_file}")
    
    print("🎉 Training collector tests completed!")


if __name__ == "__main__":
    asyncio.run(main()) 