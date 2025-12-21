"""
Training Data Collection System for MCP

This module provides a comprehensive system for collecting, storing, and exporting
training data from MCP interactions for future LLM training and fine-tuning.
"""

from .models import ConversationTurn, TrainingDataset
from .collectors import ConversationCollector
from .storage import TrainingDataStorage
from .exporters import TrainingDataExporter
from .config import TrainingConfig
from .utils import UserAnonymizer, ContextExtractor

__version__ = "1.0.0"
__all__ = [
    "ConversationTurn",
    "TrainingDataset", 
    "ConversationCollector",
    "TrainingDataStorage",
    "TrainingDataExporter",
    "TrainingConfig",
    "UserAnonymizer",
    "ContextExtractor"
]

def create_training_system(config: TrainingConfig = None) -> ConversationCollector:
    """
    Factory function to create a complete training system with all components.
    
    Args:
        config: Training configuration. If None, uses default config.
        
    Returns:
        ConversationCollector: Configured collector ready for use
    """
    if config is None:
        config = TrainingConfig()
    
    storage = TrainingDataStorage(config.data_dir)
    exporter = TrainingDataExporter(storage)
    collector = ConversationCollector(storage, config)
    
    return collector

if __name__ == "__main__":
    print("Training Data Collection System")
    print(f"Version: {__version__}")
    print("Use create_training_system() to get started.") 