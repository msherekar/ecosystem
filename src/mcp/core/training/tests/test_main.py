"""
Tests for main training system entry point.
"""

import unittest
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import from parent directory
from ..config import TrainingConfig
from ..utils import MockSessionProvider
from ..storage import TrainingDataStorage
from ..collectors import ConversationCollector
from ..exporters import TrainingDataExporter

# Note: This test file assumes there would be a main.py with TrainingSystemManager
# For now, we'll create minimal test cases that work with existing components

class TestTrainingComponents(unittest.TestCase):
    """Test individual training system components"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = TrainingConfig(
            data_dir=self.temp_dir,
            collect_enabled=True,
            anonymize_data=False,
            log_level="DEBUG"
        )
        self.session_provider = MockSessionProvider({
            "qc_done": True,
            "scrna_current_step": "normalization"
        })
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_config_creation(self):
        """Test configuration creation"""
        config = TrainingConfig(data_dir=self.temp_dir)
        self.assertEqual(config.data_dir, self.temp_dir)
        self.assertTrue(config.collect_enabled)
    
    def test_storage_creation(self):
        """Test storage system creation"""
        storage = TrainingDataStorage(self.temp_dir, self.config)
        self.assertIsNotNone(storage)
        self.assertEqual(storage.data_dir.name, os.path.basename(self.temp_dir))
    
    def test_collector_creation(self):
        """Test collector creation"""
        storage = TrainingDataStorage(self.temp_dir, self.config)
        collector = ConversationCollector(storage, self.config, self.session_provider)
        self.assertIsNotNone(collector)
    
    def test_exporter_creation(self):
        """Test exporter creation"""
        storage = TrainingDataStorage(self.temp_dir, self.config)
        exporter = TrainingDataExporter(storage, self.config)
        self.assertIsNotNone(exporter)
    
    async def test_conversation_collection(self):
        """Test basic conversation collection"""
        storage = TrainingDataStorage(self.temp_dir, self.config)
        collector = ConversationCollector(storage, self.config, self.session_provider)
        
        turn = await collector.collect_conversation_turn(
            user_message="Test message",
            assistant_response="Test response",
            tool_results=["Tool test: Success"],
            success=True
        )
        
        self.assertIsNotNone(turn)
        self.assertEqual(turn.user_message, "Test message")
        self.assertEqual(turn.assistant_response, "Test response")

def run_async_test(coro):
    """Helper to run async tests"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# Override test methods to handle async
for cls_name, cls in list(globals().items()):
    if isinstance(cls, type) and issubclass(cls, unittest.TestCase):
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if (attr_name.startswith('test_') and 
                asyncio.iscoroutinefunction(attr)):
                # Wrap async test methods
                def make_sync_test(async_test):
                    def sync_test(self):
                        return run_async_test(async_test(self))
                    return sync_test
                
                setattr(cls, attr_name, make_sync_test(attr))

if __name__ == "__main__":
    unittest.main(verbosity=2) 