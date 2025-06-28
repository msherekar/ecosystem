"""
Enhanced data models for training data collection with security and validation.
Includes encryption support, data validation, and serialization improvements.
"""

import json
import hashlib
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from enum import Enum

class ConversationStatus(Enum):
    """Status of conversation processing"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"

class DataSensitivity(Enum):
    """Data sensitivity levels for privacy handling"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

@dataclass
class ConversationTurn:
    """Enhanced conversation turn with security and validation features"""
    user_id: str
    session_id: str
    timestamp: datetime
    user_message: str
    assistant_response: str
    context: Dict[str, Any]
    tools_used: List[Dict[str, Any]]
    analysis_type: str
    pipeline_step: str
    success: bool
    user_feedback: Optional[str] = None
    
    # Enhanced fields
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: ConversationStatus = ConversationStatus.COMPLETED
    sensitivity_level: DataSensitivity = DataSensitivity.INTERNAL
    quality_score: Optional[float] = None
    processing_time_ms: Optional[int] = None
    error_details: Optional[Dict[str, Any]] = None
    encrypted_fields: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate and process data after initialization"""
        self._validate_data()
        self._calculate_quality_metrics()
    
    def _validate_data(self) -> None:
        """Validate conversation data"""
        if not self.user_message or not self.user_message.strip():
            raise ValueError("User message cannot be empty")
        
        if not self.assistant_response or not self.assistant_response.strip():
            raise ValueError("Assistant response cannot be empty")
        
        if not self.user_id or not self.session_id:
            raise ValueError("User ID and Session ID are required")
        
        if self.quality_score is not None and not 0 <= self.quality_score <= 1:
            raise ValueError("Quality score must be between 0 and 1")
    
    def _calculate_quality_metrics(self) -> None:
        """Calculate quality score based on conversation characteristics"""
        if self.quality_score is not None:
            return  # Already set
        
        score = 0.0
        
        # Base score for successful conversations
        if self.success:
            score += 0.5
        
        # Message length quality (not too short, not too long)
        user_len = len(self.user_message)
        assistant_len = len(self.assistant_response)
        
        if 10 <= user_len <= 1000:
            score += 0.1
        if 20 <= assistant_len <= 2000:
            score += 0.1
        
        # Tool usage indicates engagement
        if self.tools_used:
            score += 0.1
        
        # User feedback indicates quality
        if self.user_feedback:
            score += 0.1
        
        # Context richness
        if self.context and len(self.context) > 2:
            score += 0.1
        
        self.quality_score = min(1.0, score)
    
    def to_dict(self, include_sensitive: bool = True) -> Dict[str, Any]:
        """Convert to dictionary with optional sensitive data exclusion"""
        data = asdict(self)
        
        # Convert enums to values
        data['status'] = self.status.value
        data['sensitivity_level'] = self.sensitivity_level.value
        
        # Handle datetime serialization
        data['timestamp'] = self.timestamp.isoformat()
        
        # Remove sensitive data if requested
        if not include_sensitive and self.sensitivity_level in [DataSensitivity.CONFIDENTIAL, DataSensitivity.RESTRICTED]:
            sensitive_fields = ['user_message', 'assistant_response', 'context', 'user_feedback']
            for field in sensitive_fields:
                if field in data:
                    data[field] = "[REDACTED]"
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationTurn':
        """Create from dictionary with proper type conversion"""
        # Handle datetime parsing
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        
        # Handle enum conversion
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = ConversationStatus(data['status'])
        
        if 'sensitivity_level' in data and isinstance(data['sensitivity_level'], str):
            data['sensitivity_level'] = DataSensitivity(data['sensitivity_level'])
        
        return cls(**data)
    
    def to_json(self, include_sensitive: bool = True) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(include_sensitive), default=str, indent=2)
    
    def get_content_hash(self) -> str:
        """Get content hash for deduplication"""
        content = f"{self.user_message}|{self.assistant_response}|{self.session_id}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def mark_as_encrypted(self, fields: List[str]) -> None:
        """Mark fields as encrypted"""
        self.encrypted_fields = fields
    
    def is_high_quality(self, threshold: float = 0.7) -> bool:
        """Check if conversation meets quality threshold"""
        return self.quality_score is not None and self.quality_score >= threshold
    
    def get_duration_estimate(self) -> Optional[int]:
        """Estimate conversation duration in seconds"""
        if not self.processing_time_ms:
            return None
        
        # Rough estimate: 150 words per minute reading speed
        total_words = len(self.user_message.split()) + len(self.assistant_response.split())
        reading_time = (total_words / 150) * 60  # seconds
        
        return int(reading_time + (self.processing_time_ms / 1000))

@dataclass
class TrainingDataset:
    """Enhanced training dataset with metadata and validation"""
    conversations: List[ConversationTurn]
    metadata: Dict[str, Any]
    created_at: datetime
    version: str = "2.0"
    
    # Enhanced fields
    dataset_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    data_schema_version: str = "1.0"
    quality_metrics: Optional[Dict[str, Any]] = None
    export_settings: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate metrics after initialization"""
        self._calculate_quality_metrics()
        self._update_metadata()
    
    def _calculate_quality_metrics(self) -> None:
        """Calculate dataset quality metrics"""
        if not self.conversations:
            self.quality_metrics = {"error": "No conversations in dataset"}
            return
        
        total_conversations = len(self.conversations)
        successful_conversations = sum(1 for conv in self.conversations if conv.success)
        high_quality_conversations = sum(1 for conv in self.conversations if conv.is_high_quality())
        
        # Calculate average quality score
        quality_scores = [conv.quality_score for conv in self.conversations if conv.quality_score is not None]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # Diversity metrics
        unique_analysis_types = len(set(conv.analysis_type for conv in self.conversations))
        unique_pipeline_steps = len(set(conv.pipeline_step for conv in self.conversations))
        unique_sessions = len(set(conv.session_id for conv in self.conversations))
        
        self.quality_metrics = {
            "total_conversations": total_conversations,
            "success_rate": successful_conversations / total_conversations,
            "high_quality_rate": high_quality_conversations / total_conversations,
            "average_quality_score": avg_quality,
            "diversity": {
                "analysis_types": unique_analysis_types,
                "pipeline_steps": unique_pipeline_steps,
                "sessions": unique_sessions
            },
            "content_stats": self._get_content_statistics()
        }
    
    def _get_content_statistics(self) -> Dict[str, Any]:
        """Get content-related statistics"""
        if not self.conversations:
            return {}
        
        user_message_lengths = [len(conv.user_message) for conv in self.conversations]
        assistant_response_lengths = [len(conv.assistant_response) for conv in self.conversations]
        
        return {
            "avg_user_message_length": sum(user_message_lengths) / len(user_message_lengths),
            "avg_assistant_response_length": sum(assistant_response_lengths) / len(assistant_response_lengths),
            "conversations_with_tools": sum(1 for conv in self.conversations if conv.tools_used),
            "conversations_with_feedback": sum(1 for conv in self.conversations if conv.user_feedback),
            "total_characters": sum(user_message_lengths) + sum(assistant_response_lengths)
        }
    
    def _update_metadata(self) -> None:
        """Update metadata with current dataset information"""
        self.metadata.update({
            "dataset_id": self.dataset_id,
            "total_conversations": len(self.conversations),
            "created_timestamp": self.created_at.isoformat(),
            "data_schema_version": self.data_schema_version,
            "last_updated": datetime.now().isoformat()
        })
    
    def to_dict(self, include_sensitive: bool = True) -> Dict[str, Any]:
        """Convert to dictionary with optional sensitive data filtering"""
        return {
            'dataset_id': self.dataset_id,
            'conversations': [conv.to_dict(include_sensitive) for conv in self.conversations],
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'version': self.version,
            'description': self.description,
            'tags': self.tags,
            'data_schema_version': self.data_schema_version,
            'quality_metrics': self.quality_metrics,
            'export_settings': self.export_settings
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrainingDataset':
        """Create from dictionary with backward compatibility"""
        conversations = [ConversationTurn.from_dict(conv) for conv in data['conversations']]
        
        # Handle datetime parsing
        created_at = data['created_at']
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        # Handle optional fields with defaults
        return cls(
            conversations=conversations,
            metadata=data['metadata'],
            created_at=created_at,
            version=data.get('version', '1.0'),
            dataset_id=data.get('dataset_id', str(uuid.uuid4())),
            description=data.get('description'),
            tags=data.get('tags', []),
            data_schema_version=data.get('data_schema_version', '1.0'),
            quality_metrics=data.get('quality_metrics'),
            export_settings=data.get('export_settings', {})
        )
    
    def to_json(self, include_sensitive: bool = True) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(include_sensitive), default=str, indent=2)
    
    def add_conversation(self, conversation: ConversationTurn) -> None:
        """Add a conversation and update metrics"""
        self.conversations.append(conversation)
        self._calculate_quality_metrics()
        self._update_metadata()
    
    def filter_by_quality(self, min_quality: float = 0.7) -> 'TrainingDataset':
        """Filter conversations by quality score"""
        high_quality_conversations = [
            conv for conv in self.conversations 
            if conv.is_high_quality(min_quality)
        ]
        
        return TrainingDataset(
            conversations=high_quality_conversations,
            metadata={
                **self.metadata,
                'filtered_by': f'quality>={min_quality}',
                'original_count': len(self.conversations),
                'filtered_count': len(high_quality_conversations)
            },
            created_at=datetime.now(),
            version=self.version,
            description=f"Quality-filtered dataset (min_quality={min_quality})"
        )
    
    def filter_by_analysis_type(self, analysis_type: str) -> 'TrainingDataset':
        """Filter conversations by analysis type"""
        filtered_conversations = [
            conv for conv in self.conversations 
            if conv.analysis_type == analysis_type
        ]
        
        return TrainingDataset(
            conversations=filtered_conversations,
            metadata={
                **self.metadata,
                'filtered_by': f'analysis_type={analysis_type}',
                'original_count': len(self.conversations),
                'filtered_count': len(filtered_conversations)
            },
            created_at=datetime.now(),
            version=self.version,
            description=f"Filtered by analysis type: {analysis_type}"
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive dataset statistics"""
        return {
            "dataset_info": {
                "id": self.dataset_id,
                "version": self.version,
                "created_at": self.created_at.isoformat(),
                "description": self.description,
                "tags": self.tags
            },
            "quality_metrics": self.quality_metrics,
            "metadata": self.metadata
        }


def main():
        """Test enhanced models"""
        print("Testing Enhanced Training Data Models")
        print("=" * 45)
        
        # Test conversation turn
        turn = ConversationTurn(
            user_id="test_user",
            session_id="test_session",
            timestamp=datetime.now(),
            user_message="How do I normalize my single-cell RNA-seq data?",
            assistant_response="You can use scanpy's pp.normalize_total function to normalize your data...",
            context={"analysis_type": "scrna_seq", "step": "normalization"},
            tools_used=[{"name": "scanpy", "success": True}],
            analysis_type="scrna_seq",
            pipeline_step="normalization",
            success=True,
            user_feedback="Very helpful!",
            sensitivity_level=DataSensitivity.INTERNAL
        )
        
        print(f"✓ Conversation created with quality score: {turn.quality_score:.2f}")
        print(f"✓ Content hash: {turn.get_content_hash()}")
        print(f"✓ High quality: {turn.is_high_quality()}")
        
        # Test dataset
        dataset = TrainingDataset(
            conversations=[turn],
            metadata={"source": "test", "purpose": "validation"},
            created_at=datetime.now(),
            description="Test dataset for model validation",
            tags=["test", "scrna_seq", "normalization"]
        )
        
        print(f"✓ Dataset created with {len(dataset.conversations)} conversations")
        print(f"✓ Success rate: {dataset.quality_metrics['success_rate']:.2%}")
        print(f"✓ High quality rate: {dataset.quality_metrics['high_quality_rate']:.2%}")
        
        # Test filtering
        quality_filtered = dataset.filter_by_quality(0.5)
        print(f"✓ Quality filtering: {len(quality_filtered.conversations)} conversations remain")
        
        # Test serialization
        json_data = dataset.to_json(include_sensitive=False)
        reconstructed = TrainingDataset.from_dict(json.loads(json_data))
        print(f"✓ Serialization test: {len(reconstructed.conversations)} conversations reconstructed")
        
        print("✓ All enhanced model tests completed!")
    
if __name__ == "__main__":
    main()