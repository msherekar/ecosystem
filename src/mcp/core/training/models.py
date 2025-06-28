"""
Data models for training data collection.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Any, Optional
import json

@dataclass
class ConversationTurn:
    """Single conversation turn for training data"""
    user_id: str  # Anonymized user ID
    session_id: str
    timestamp: datetime
    user_message: str
    assistant_response: str
    context: Dict[str, Any]  # Analysis state, available tools, etc.
    tools_used: List[Dict[str, Any]]
    analysis_type: str  # scrna_seq, rna_seq, etc.
    pipeline_step: str  # qc, filtering, normalization, etc.
    success: bool  # Whether the interaction was successful
    user_feedback: Optional[str] = None  # Future: user satisfaction rating
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationTurn':
        """Create from dictionary"""
        # Handle datetime parsing
        if isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), default=str, indent=2)

@dataclass
class TrainingDataset:
    """Collection of conversation turns for training"""
    conversations: List[ConversationTurn]
    metadata: Dict[str, Any]
    created_at: datetime
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization"""
        return {
            'conversations': [conv.to_dict() for conv in self.conversations],
            'metadata': self.metadata,
            'created_at': self.created_at,
            'version': self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrainingDataset':
        """Create from dictionary"""
        conversations = [ConversationTurn.from_dict(conv) for conv in data['conversations']]
        
        # Handle datetime parsing
        if isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
            
        return cls(
            conversations=conversations,
            metadata=data['metadata'],
            created_at=data['created_at'],
            version=data.get('version', '1.0')
        )
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), default=str, indent=2)
    
    def add_conversation(self, conversation: ConversationTurn) -> None:
        """Add a conversation turn to the dataset"""
        self.conversations.append(conversation)
        self.metadata['total_turns'] = len(self.conversations)
    
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
            version=self.version
        )
    
    def filter_by_success(self, success_only: bool = True) -> 'TrainingDataset':
        """Filter conversations by success status"""
        filtered_conversations = [
            conv for conv in self.conversations 
            if conv.success == success_only
        ]
        
        return TrainingDataset(
            conversations=filtered_conversations,
            metadata={
                **self.metadata,
                'filtered_by': f'success={success_only}',
                'original_count': len(self.conversations),
                'filtered_count': len(filtered_conversations)
            },
            created_at=datetime.now(),
            version=self.version
        )

if __name__ == "__main__":
    # Suppress the RuntimeWarning about module import behavior
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning, 
                          message=".*found in sys.modules.*")
    
    # Example usage
    from datetime import datetime
    
    # Create a sample conversation turn
    turn = ConversationTurn(
        user_id="user123",
        session_id="session456",
        timestamp=datetime.now(),
        user_message="How do I normalize my data?",
        assistant_response="You can use scanpy's pp.normalize_total function...",
        context={"analysis_type": "scrna_seq", "step": "normalization"},
        tools_used=[{"name": "scanpy", "success": True}],
        analysis_type="scrna_seq",
        pipeline_step="normalization",
        success=True
    )
    
    # Create a dataset
    dataset = TrainingDataset(
        conversations=[turn],
        metadata={"source": "example"},
        created_at=datetime.now()
    )
    
    print("Sample conversation turn:")
    print(turn.to_json())
    print("\nSample dataset:")
    print(f"Total conversations: {len(dataset.conversations)}") 