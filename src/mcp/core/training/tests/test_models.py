"""
Tests for training data models.
"""

import unittest
import json
from datetime import datetime
from typing import Dict, Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import ConversationTurn, TrainingDataset

class TestConversationTurn(unittest.TestCase):
    """Test ConversationTurn model"""
    
    def setUp(self):
        """Set up test data"""
        self.sample_turn = ConversationTurn(
            user_id="test_user",
            session_id="test_session",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            user_message="Test message",
            assistant_response="Test response",
            context={"test": "context"},
            tools_used=[{"name": "test_tool", "success": True}],
            analysis_type="test_analysis",
            pipeline_step="test_step",
            success=True,
            user_feedback="Good response"
        )
    
    def test_conversation_turn_creation(self):
        """Test basic conversation turn creation"""
        self.assertEqual(self.sample_turn.user_id, "test_user")
        self.assertEqual(self.sample_turn.session_id, "test_session")
        self.assertEqual(self.sample_turn.user_message, "Test message")
        self.assertEqual(self.sample_turn.assistant_response, "Test response")
        self.assertTrue(self.sample_turn.success)
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        turn_dict = self.sample_turn.to_dict()
        
        self.assertIsInstance(turn_dict, dict)
        self.assertEqual(turn_dict["user_id"], "test_user")
        self.assertEqual(turn_dict["session_id"], "test_session")
        self.assertEqual(turn_dict["user_message"], "Test message")
        self.assertEqual(turn_dict["context"], {"test": "context"})
        self.assertEqual(len(turn_dict["tools_used"]), 1)
    
    def test_from_dict(self):
        """Test creation from dictionary"""
        turn_dict = self.sample_turn.to_dict()
        reconstructed = ConversationTurn.from_dict(turn_dict)
        
        self.assertEqual(reconstructed.user_id, self.sample_turn.user_id)
        self.assertEqual(reconstructed.session_id, self.sample_turn.session_id)
        self.assertEqual(reconstructed.user_message, self.sample_turn.user_message)
        self.assertEqual(reconstructed.assistant_response, self.sample_turn.assistant_response)
        self.assertEqual(reconstructed.context, self.sample_turn.context)
        self.assertEqual(reconstructed.tools_used, self.sample_turn.tools_used)
        self.assertEqual(reconstructed.analysis_type, self.sample_turn.analysis_type)
        self.assertEqual(reconstructed.pipeline_step, self.sample_turn.pipeline_step)
        self.assertEqual(reconstructed.success, self.sample_turn.success)
        self.assertEqual(reconstructed.user_feedback, self.sample_turn.user_feedback)
    
    def test_from_dict_with_string_timestamp(self):
        """Test creation from dictionary with string timestamp"""
        turn_dict = self.sample_turn.to_dict()
        turn_dict["timestamp"] = turn_dict["timestamp"].isoformat()
        
        reconstructed = ConversationTurn.from_dict(turn_dict)
        self.assertEqual(reconstructed.timestamp, self.sample_turn.timestamp)
    
    def test_to_json(self):
        """Test JSON serialization"""
        json_str = self.sample_turn.to_json()
        
        self.assertIsInstance(json_str, str)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["user_id"], "test_user")
        self.assertEqual(parsed["session_id"], "test_session")
        
    def test_optional_fields(self):
        """Test conversation turn with optional fields"""
        minimal_turn = ConversationTurn(
            user_id="user",
            session_id="session",
            timestamp=datetime.now(),
            user_message="message",
            assistant_response="response",
            context={},
            tools_used=[],
            analysis_type="test",
            pipeline_step="step",
            success=True
        )
        
        self.assertIsNone(minimal_turn.user_feedback)
        self.assertEqual(minimal_turn.tools_used, [])
        self.assertEqual(minimal_turn.context, {})

class TestTrainingDataset(unittest.TestCase):
    """Test TrainingDataset model"""
    
    def setUp(self):
        """Set up test data"""
        self.sample_conversations = [
            ConversationTurn(
                user_id="user1",
                session_id="session1",
                timestamp=datetime(2024, 1, 1, 12, 0, 0),
                user_message="Message 1",
                assistant_response="Response 1",
                context={"step": 1},
                tools_used=[],
                analysis_type="scrna_seq",
                pipeline_step="qc",
                success=True
            ),
            ConversationTurn(
                user_id="user2",
                session_id="session2",
                timestamp=datetime(2024, 1, 2, 12, 0, 0),
                user_message="Message 2",
                assistant_response="Response 2",
                context={"step": 2},
                tools_used=[{"name": "tool1", "success": True}],
                analysis_type="rna_seq",
                pipeline_step="normalization",
                success=False
            )
        ]
        
        self.sample_dataset = TrainingDataset(
            conversations=self.sample_conversations,
            metadata={"source": "test", "total_turns": 2},
            created_at=datetime(2024, 1, 1, 10, 0, 0),
            version="1.0"
        )
    
    def test_dataset_creation(self):
        """Test basic dataset creation"""
        self.assertEqual(len(self.sample_dataset.conversations), 2)
        self.assertEqual(self.sample_dataset.metadata["source"], "test")
        self.assertEqual(self.sample_dataset.version, "1.0")
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        dataset_dict = self.sample_dataset.to_dict()
        
        self.assertIsInstance(dataset_dict, dict)
        self.assertEqual(len(dataset_dict["conversations"]), 2)
        self.assertEqual(dataset_dict["metadata"]["source"], "test")
        self.assertEqual(dataset_dict["version"], "1.0")
    
    def test_from_dict(self):
        """Test creation from dictionary"""
        dataset_dict = self.sample_dataset.to_dict()
        reconstructed = TrainingDataset.from_dict(dataset_dict)
        
        self.assertEqual(len(reconstructed.conversations), 2)
        self.assertEqual(reconstructed.metadata["source"], "test")
        self.assertEqual(reconstructed.version, "1.0")
        self.assertEqual(reconstructed.created_at, self.sample_dataset.created_at)
    
    def test_from_dict_with_string_timestamp(self):
        """Test creation from dictionary with string timestamp"""
        dataset_dict = self.sample_dataset.to_dict()
        dataset_dict["created_at"] = dataset_dict["created_at"].isoformat()
        
        reconstructed = TrainingDataset.from_dict(dataset_dict)
        self.assertEqual(reconstructed.created_at, self.sample_dataset.created_at)
    
    def test_to_json(self):
        """Test JSON serialization"""
        json_str = self.sample_dataset.to_json()
        
        self.assertIsInstance(json_str, str)
        parsed = json.loads(json_str)
        self.assertEqual(len(parsed["conversations"]), 2)
        self.assertEqual(parsed["metadata"]["source"], "test")
    
    def test_add_conversation(self):
        """Test adding conversation to dataset"""
        initial_count = len(self.sample_dataset.conversations)
        
        new_conversation = ConversationTurn(
            user_id="user3",
            session_id="session3",
            timestamp=datetime.now(),
            user_message="New message",
            assistant_response="New response",
            context={},
            tools_used=[],
            analysis_type="test",
            pipeline_step="test",
            success=True
        )
        
        self.sample_dataset.add_conversation(new_conversation)
        
        self.assertEqual(len(self.sample_dataset.conversations), initial_count + 1)
        self.assertEqual(self.sample_dataset.metadata["total_turns"], initial_count + 1)
    
    def test_filter_by_analysis_type(self):
        """Test filtering by analysis type"""
        filtered = self.sample_dataset.filter_by_analysis_type("scrna_seq")
        
        self.assertEqual(len(filtered.conversations), 1)
        self.assertEqual(filtered.conversations[0].analysis_type, "scrna_seq")
        self.assertEqual(filtered.metadata["filtered_by"], "analysis_type=scrna_seq")
        self.assertEqual(filtered.metadata["original_count"], 2)
        self.assertEqual(filtered.metadata["filtered_count"], 1)
    
    def test_filter_by_analysis_type_no_matches(self):
        """Test filtering by analysis type with no matches"""
        filtered = self.sample_dataset.filter_by_analysis_type("non_existent")
        
        self.assertEqual(len(filtered.conversations), 0)
        self.assertEqual(filtered.metadata["filtered_count"], 0)
    
    def test_filter_by_success(self):
        """Test filtering by success status"""
        filtered_success = self.sample_dataset.filter_by_success(True)
        
        self.assertEqual(len(filtered_success.conversations), 1)
        self.assertTrue(filtered_success.conversations[0].success)
        self.assertEqual(filtered_success.metadata["filtered_by"], "success=True")
        
        filtered_failure = self.sample_dataset.filter_by_success(False)
        
        self.assertEqual(len(filtered_failure.conversations), 1)
        self.assertFalse(filtered_failure.conversations[0].success)
        self.assertEqual(filtered_failure.metadata["filtered_by"], "success=False")
    
    def test_default_version(self):
        """Test default version setting"""
        dataset = TrainingDataset(
            conversations=[],
            metadata={},
            created_at=datetime.now()
        )
        
        self.assertEqual(dataset.version, "1.0")

if __name__ == "__main__":
    unittest.main(verbosity=2) 