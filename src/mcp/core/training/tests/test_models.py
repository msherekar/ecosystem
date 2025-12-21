"""
Enhanced tests for training data models with security and validation testing.
"""

import unittest
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import ConversationTurn, TrainingDataset, ConversationStatus, DataSensitivity

class TestEnhancedConversationTurn(unittest.TestCase):
    """Test enhanced ConversationTurn model"""
    
    def setUp(self):
        """Set up test data"""
        self.sample_turn = ConversationTurn(
            user_id="test_user",
            session_id="test_session",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            user_message="How do I normalize my single-cell RNA-seq data?",
            assistant_response="You can use scanpy's pp.normalize_total function to normalize your data...",
            context={"analysis_type": "scrna_seq", "step": "normalization"},
            tools_used=[{"name": "scanpy", "success": True, "execution_time": 1200}],
            analysis_type="scrna_seq",
            pipeline_step="normalization",
            success=True,
            user_feedback="Very helpful explanation!",
            sensitivity_level=DataSensitivity.INTERNAL,
            processing_time_ms=1500
        )
    
    def test_enhanced_dataset_creation(self):
        """Test enhanced dataset creation with automatic metrics"""
        self.assertEqual(len(self.sample_dataset.conversations), 3)
        self.assertIsNotNone(self.sample_dataset.dataset_id)
        self.assertIsNotNone(self.sample_dataset.quality_metrics)
        self.assertEqual(self.sample_dataset.description, "Test dataset for enhanced features")
        self.assertEqual(self.sample_dataset.tags, ["test", "scrna_seq", "validation"])
        self.assertEqual(self.sample_dataset.version, "2.0")
    
    def test_quality_metrics_calculation(self):
        """Test automatic quality metrics calculation"""
        metrics = self.sample_dataset.quality_metrics
        
        self.assertEqual(metrics["total_conversations"], 3)
        self.assertEqual(metrics["success_rate"], 2/3)  # 2 successful out of 3
        self.assertIn("high_quality_rate", metrics)
        self.assertIn("average_quality_score", metrics)
        self.assertIn("diversity", metrics)
        self.assertIn("content_stats", metrics)
        
        # Check diversity metrics
        diversity = metrics["diversity"]
        self.assertEqual(diversity["analysis_types"], 1)  # All scrna_seq
        self.assertEqual(diversity["pipeline_steps"], 3)  # qc, normalization, clustering
        self.assertEqual(diversity["sessions"], 3)  # 3 different sessions
        
        # Check content stats
        content_stats = metrics["content_stats"]
        self.assertIn("avg_user_message_length", content_stats)
        self.assertIn("avg_assistant_response_length", content_stats)
        self.assertIn("conversations_with_tools", content_stats)
        self.assertEqual(content_stats["conversations_with_tools"], 2)  # First two have tools
    
    def test_quality_filtering(self):
        """Test filtering by quality score"""
        high_quality_dataset = self.sample_dataset.filter_by_quality(0.7)
        
        # Should have 2 conversations (quality scores 0.8 and 0.9)
        self.assertEqual(len(high_quality_dataset.conversations), 2)
        
        # Check metadata
        self.assertEqual(high_quality_dataset.metadata["filtered_by"], "quality>=0.7")
        self.assertEqual(high_quality_dataset.metadata["original_count"], 3)
        self.assertEqual(high_quality_dataset.metadata["filtered_count"], 2)
        
        # All remaining conversations should be high quality
        for conv in high_quality_dataset.conversations:
            self.assertTrue(conv.is_high_quality(0.7))
    
    def test_analysis_type_filtering(self):
        """Test filtering by analysis type"""
        # Add a different analysis type conversation
        rna_seq_conv = ConversationTurn(
            user_id="user4",
            session_id="session4",
            timestamp=datetime.now(),
            user_message="RNA-seq analysis help",
            assistant_response="RNA-seq analysis involves...",
            context={},
            tools_used=[],
            analysis_type="rna_seq",
            pipeline_step="analysis",
            success=True
        )
        
        self.sample_dataset.add_conversation(rna_seq_conv)
        
        # Filter by scrna_seq
        scrna_dataset = self.sample_dataset.filter_by_analysis_type("scrna_seq")
        self.assertEqual(len(scrna_dataset.conversations), 3)  # Original 3
        
        # Filter by rna_seq
        rna_dataset = self.sample_dataset.filter_by_analysis_type("rna_seq")
        self.assertEqual(len(rna_dataset.conversations), 1)  # Just the new one
        
        # Check metadata
        self.assertEqual(scrna_dataset.metadata["filtered_by"], "analysis_type=scrna_seq")
    
    def test_dataset_statistics(self):
        """Test comprehensive dataset statistics"""
        stats = self.sample_dataset.get_statistics()
        
        self.assertIn("dataset_info", stats)
        self.assertIn("quality_metrics", stats)
        self.assertIn("metadata", stats)
        
        dataset_info = stats["dataset_info"]
        self.assertEqual(dataset_info["id"], self.sample_dataset.dataset_id)
        self.assertEqual(dataset_info["version"], "2.0")
        self.assertEqual(dataset_info["description"], "Test dataset for enhanced features")
        self.assertEqual(dataset_info["tags"], ["test", "scrna_seq", "validation"])
    
    def test_conversation_addition(self):
        """Test adding conversations and metric updates"""
        initial_count = len(self.sample_dataset.conversations)
        initial_metrics = self.sample_dataset.quality_metrics.copy()
        
        new_conv = ConversationTurn(
            user_id="new_user",
            session_id="new_session",
            timestamp=datetime.now(),
            user_message="New question",
            assistant_response="New response",
            context={},
            tools_used=[],
            analysis_type="scrna_seq",
            pipeline_step="new_step",
            success=True,
            quality_score=0.95
        )
        
        self.sample_dataset.add_conversation(new_conv)
        
        # Check count increased
        self.assertEqual(len(self.sample_dataset.conversations), initial_count + 1)
        
        # Check metrics updated
        updated_metrics = self.sample_dataset.quality_metrics
        self.assertEqual(updated_metrics["total_conversations"], initial_count + 1)
        
        # Success rate should increase (added successful conversation)
        self.assertGreaterEqual(updated_metrics["success_rate"], initial_metrics["success_rate"])
    
    def test_enhanced_serialization(self):
        """Test enhanced serialization with all new fields"""
        dataset_dict = self.sample_dataset.to_dict()
        
        # Check all enhanced fields are present
        self.assertIn("dataset_id", dataset_dict)
        self.assertIn("description", dataset_dict)
        self.assertIn("tags", dataset_dict)
        self.assertIn("data_schema_version", dataset_dict)
        self.assertIn("quality_metrics", dataset_dict)
        self.assertIn("export_settings", dataset_dict)
        
        # Test deserialization
        reconstructed = TrainingDataset.from_dict(dataset_dict)
        
        self.assertEqual(reconstructed.dataset_id, self.sample_dataset.dataset_id)
        self.assertEqual(reconstructed.description, self.sample_dataset.description)
        self.assertEqual(reconstructed.tags, self.sample_dataset.tags)
        self.assertEqual(reconstructed.data_schema_version, self.sample_dataset.data_schema_version)
        self.assertEqual(len(reconstructed.conversations), len(self.sample_dataset.conversations))
    
    def test_sensitive_data_filtering(self):
        """Test dataset-wide sensitive data filtering"""
        # Add confidential conversation
        confidential_conv = ConversationTurn(
            user_id="confidential_user",
            session_id="confidential_session",
            timestamp=datetime.now(),
            user_message="Confidential medical data",
            assistant_response="Analysis of confidential information",
            context={"patient_data": "sensitive"},
            tools_used=[],
            analysis_type="medical",
            pipeline_step="analysis",
            success=True,
            sensitivity_level=DataSensitivity.CONFIDENTIAL
        )
        
        self.sample_dataset.add_conversation(confidential_conv)
        
        # Test with sensitive data
        data_with_sensitive = self.sample_dataset.to_dict(include_sensitive=True)
        confidential_conv_data = data_with_sensitive["conversations"][-1]
        self.assertEqual(confidential_conv_data["user_message"], "Confidential medical data")
        
        # Test without sensitive data
        data_without_sensitive = self.sample_dataset.to_dict(include_sensitive=False)
        confidential_conv_data = data_without_sensitive["conversations"][-1]
        self.assertEqual(confidential_conv_data["user_message"], "[REDACTED]")
    
    def test_backward_compatibility(self):
        """Test backward compatibility with old dataset format"""
        # Create old format data
        old_format_data = {
            "conversations": [
                {
                    "user_id": "old_user",
                    "session_id": "old_session",
                    "timestamp": "2024-01-01T12:00:00",
                    "user_message": "Old message",
                    "assistant_response": "Old response",
                    "context": {},
                    "tools_used": [],
                    "analysis_type": "general",
                    "pipeline_step": "unknown",
                    "success": True
                }
            ],
            "metadata": {"old": True},
            "created_at": "2024-01-01T10:00:00",
            "version": "1.0"
        }
        
        # Should be able to load old format
        dataset = TrainingDataset.from_dict(old_format_data)
        
        self.assertEqual(len(dataset.conversations), 1)
        self.assertEqual(dataset.version, "1.0")
        self.assertIsNotNone(dataset.dataset_id)  # Should be auto-generated
        self.assertIsNotNone(dataset.quality_metrics)  # Should be calculated

class TestDataModelIntegration(unittest.TestCase):
    """Test integration between enhanced models"""
    
    def test_conversation_to_dataset_workflow(self):
        """Test complete workflow from conversation to dataset"""
        # Create conversations with different characteristics
        conversations = []
        
        for i in range(5):
            conv = ConversationTurn(
                user_id=f"user{i}",
                session_id=f"session{i//2}",  # 2-3 conversations per session
                timestamp=datetime.now() - timedelta(hours=i),
                user_message=f"Question {i} about data analysis",
                assistant_response=f"Answer {i} with detailed explanation",
                context={"question_number": i},
                tools_used=[{"name": "tool1", "success": True}] if i % 2 == 0 else [],
                analysis_type="scrna_seq" if i < 3 else "rna_seq",
                pipeline_step=["qc", "normalization", "clustering", "dea", "visualization"][i],
                success=i != 2,  # One failed conversation
                user_feedback="Helpful" if i % 2 == 0 else None,
                quality_score=0.8 if i != 2 else 0.4
            )
            conversations.append(conv)
        
        # Create dataset
        dataset = TrainingDataset(
            conversations=conversations,
            metadata={"test": "integration"},
            created_at=datetime.now(),
            description="Integration test dataset"
        )
        
        # Test dataset metrics
        self.assertEqual(dataset.quality_metrics["total_conversations"], 5)
        self.assertEqual(dataset.quality_metrics["success_rate"], 0.8)  # 4/5 successful
        
        # Test filtering workflows
        high_quality = dataset.filter_by_quality(0.7)
        scrna_only = dataset.filter_by_analysis_type("scrna_seq")
        
        self.assertEqual(len(high_quality.conversations), 4)  # Exclude the 0.4 quality one
        self.assertEqual(len(scrna_only.conversations), 3)  # First 3 are scrna_seq
        
        # Test serialization roundtrip
        serialized = dataset.to_json()
        reconstructed = TrainingDataset.from_dict(json.loads(serialized))
        
        self.assertEqual(len(reconstructed.conversations), 5)
        self.assertEqual(reconstructed.dataset_id, dataset.dataset_id)
    
    def test_performance_with_large_dataset(self):
        """Test performance with larger dataset"""
        import time
        
        # Create larger dataset (100 conversations)
        conversations = []
        start_time = time.time()
        
        for i in range(100):
            conv = ConversationTurn(
                user_id=f"user{i % 10}",
                session_id=f"session{i % 20}",
                timestamp=datetime.now() - timedelta(minutes=i),
                user_message=f"Question {i}",
                assistant_response=f"Response {i}",
                context={"index": i},
                tools_used=[],
                analysis_type=["scrna_seq", "rna_seq", "proteomics"][i % 3],
                pipeline_step=["qc", "analysis", "visualization"][i % 3],
                success=i % 10 != 0  # 10% failure rate
            )
            conversations.append(conv)
        
        creation_time = time.time() - start_time
        
        # Create dataset
        start_time = time.time()
        dataset = TrainingDataset(
            conversations=conversations,
            metadata={"size": "large"},
            created_at=datetime.now()
        )
        dataset_time = time.time() - start_time
        
        # Test operations
        start_time = time.time()
        high_quality = dataset.filter_by_quality()
        filtering_time = time.time() - start_time
        
        start_time = time.time()
        serialized = dataset.to_json()
        serialization_time = time.time() - start_time
        
        # Performance assertions (generous limits for test environments)
        self.assertLess(creation_time, 5.0)  # Should create 100 conversations in < 5s
        self.assertLess(dataset_time, 2.0)   # Should process dataset in < 2s
        self.assertLess(filtering_time, 1.0) # Should filter in < 1s
        self.assertLess(serialization_time, 3.0) # Should serialize in < 3s
        
        # Verify correctness
        self.assertEqual(len(dataset.conversations), 100)
        self.assertEqual(dataset.quality_metrics["total_conversations"], 100)
        self.assertGreater(len(serialized), 1000)  # Should produce substantial JSON


    
    def test_quality_score_calculation(self):
        """Test automatic quality score calculation"""
        # High quality conversation
        high_quality = ConversationTurn(
            user_id="user1",
            session_id="session1",
            timestamp=datetime.now(),
            user_message="Detailed question about data analysis with specific parameters",
            assistant_response="Comprehensive response with step-by-step instructions and code examples",
            context={"rich": "context", "with": "multiple", "fields": "present"},
            tools_used=[{"name": "scanpy", "success": True}],
            analysis_type="scrna_seq",
            pipeline_step="analysis",
            success=True,
            user_feedback="Perfect answer!"
        )
        
        self.assertGreaterEqual(high_quality.quality_score, 0.7)
        self.assertTrue(high_quality.is_high_quality())
        
        # Low quality conversation
        low_quality = ConversationTurn(
            user_id="user2",
            session_id="session2",
            timestamp=datetime.now(),
            user_message="help",
            assistant_response="ok",
            context={},
            tools_used=[],
            analysis_type="general",
            pipeline_step="unknown",
            success=False
        )
        
        self.assertLess(low_quality.quality_score, 0.5)
        self.assertFalse(low_quality.is_high_quality())
    
    def test_content_hash_generation(self):
        """Test content hash for deduplication"""
        hash1 = self.sample_turn.get_content_hash()
        
        # Same content should produce same hash
        duplicate_turn = ConversationTurn(
            user_id=self.sample_turn.user_id,
            session_id=self.sample_turn.session_id,
            timestamp=datetime.now(),  # Different timestamp
            user_message=self.sample_turn.user_message,
            assistant_response=self.sample_turn.assistant_response,
            context={},
            tools_used=[],
            analysis_type="test",
            pipeline_step="test",
            success=True
        )
        
        hash2 = duplicate_turn.get_content_hash()
        self.assertEqual(hash1, hash2)
        
        # Different content should produce different hash
        different_turn = ConversationTurn(
            user_id=self.sample_turn.user_id,
            session_id=self.sample_turn.session_id,
            timestamp=self.sample_turn.timestamp,
            user_message="Different message",
            assistant_response=self.sample_turn.assistant_response,
            context={},
            tools_used=[],
            analysis_type="test",
            pipeline_step="test",
            success=True
        )
        
        hash3 = different_turn.get_content_hash()
        self.assertNotEqual(hash1, hash3)
    
    def test_sensitive_data_handling(self):
        """Test sensitive data handling in serialization"""
        confidential_turn = ConversationTurn(
            user_id="sensitive_user",
            session_id="sensitive_session",
            timestamp=datetime.now(),
            user_message="My personal medical data analysis",
            assistant_response="Analysis of your confidential data",
            context={"patient_id": "12345"},
            tools_used=[],
            analysis_type="medical",
            pipeline_step="analysis",
            success=True,
            sensitivity_level=DataSensitivity.CONFIDENTIAL
        )
        
        # Test with sensitive data included
        data_with_sensitive = confidential_turn.to_dict(include_sensitive=True)
        self.assertEqual(data_with_sensitive["user_message"], "My personal medical data analysis")
        
        # Test with sensitive data excluded
        data_without_sensitive = confidential_turn.to_dict(include_sensitive=False)
        self.assertEqual(data_without_sensitive["user_message"], "[REDACTED]")
        self.assertEqual(data_without_sensitive["assistant_response"], "[REDACTED]")
        self.assertEqual(data_without_sensitive["context"], "[REDACTED]")
    
    def test_encryption_field_tracking(self):
        """Test encryption field tracking"""
        self.sample_turn.mark_as_encrypted(["user_message", "assistant_response"])
        self.assertEqual(self.sample_turn.encrypted_fields, ["user_message", "assistant_response"])
    
    def test_duration_estimation(self):
        """Test conversation duration estimation"""
        self.sample_turn.processing_time_ms = 2000
        duration = self.sample_turn.get_duration_estimate()
        self.assertIsInstance(duration, int)
        self.assertGreater(duration, 0)
    
    def test_validation_errors(self):
        """Test data validation errors"""
        # Test empty user message
        with self.assertRaises(ValueError):
            ConversationTurn(
                user_id="user",
                session_id="session",
                timestamp=datetime.now(),
                user_message="",  # Empty message
                assistant_response="Response",
                context={},
                tools_used=[],
                analysis_type="test",
                pipeline_step="test",
                success=True
            )
        
        # Test invalid quality score
        with self.assertRaises(ValueError):
            ConversationTurn(
                user_id="user",
                session_id="session",
                timestamp=datetime.now(),
                user_message="Message",
                assistant_response="Response",
                context={},
                tools_used=[],
                analysis_type="test",
                pipeline_step="test",
                success=True,
                quality_score=1.5  # Invalid score > 1
            )
    
    def test_serialization_deserialization(self):
        """Test enhanced serialization/deserialization"""
        # Test to_dict and from_dict
        turn_dict = self.sample_turn.to_dict()
        reconstructed = ConversationTurn.from_dict(turn_dict)
        
        self.assertEqual(reconstructed.user_id, self.sample_turn.user_id)
        self.assertEqual(reconstructed.conversation_id, self.sample_turn.conversation_id)
        self.assertEqual(reconstructed.status, self.sample_turn.status)
        self.assertEqual(reconstructed.sensitivity_level, self.sample_turn.sensitivity_level)
        self.assertEqual(reconstructed.quality_score, self.sample_turn.quality_score)
        
        # Test JSON serialization
        json_str = self.sample_turn.to_json()
        self.assertIsInstance(json_str, str)
        parsed = json.loads(json_str)
        self.assertIn("conversation_id", parsed)
        self.assertIn("quality_score", parsed)


if __name__ == "__main__":
    def main():
        """Run all enhanced model tests"""
        unittest.main(verbosity=2)
    
    def test_enhanced_conversation_turn_creation(self):
        """Test enhanced conversation turn creation with validation"""
        self.assertEqual(self.sample_turn.user_id, "test_user")
        self.assertEqual(self.sample_turn.session_id, "test_session")
        self.assertEqual(self.sample_turn.status, ConversationStatus.COMPLETED)
        self.assertEqual(self.sample_turn.sensitivity_level, DataSensitivity.INTERNAL)
        self.assertIsNotNone(self.sample_turn.conversation_id)
        self.assertIsNotNone(self.sample_turn.quality_score)
        self.assertTrue(0 <= self.sample_turn.quality_score <= 1)