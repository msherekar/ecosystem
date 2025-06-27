"""
Export functionality for training data.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from .models import ConversationTurn, TrainingDataset
from .storage import TrainingDataStorage
from .config import TrainingConfig

class TrainingDataExporter:
    """Exports training data in various formats for LLM training"""
    
    def __init__(self, storage: TrainingDataStorage, config: TrainingConfig = None):
        self.storage = storage
        self.config = config or TrainingConfig()
        self.logger = logging.getLogger("training_exporter")
    
    def export_for_training(
        self, 
        output_format: str = None,
        filter_analysis_type: str = None,
        min_success_rate: float = None,
        output_filename: str = None
    ) -> str:
        """Export collected data in format suitable for LLM training"""
        
        # Use config defaults if not specified
        format_to_use = output_format or self.config.default_export_format
        min_success = min_success_rate or self.config.min_success_rate
        
        try:
            # Collect all conversation data
            all_conversations = self._collect_all_conversations()
            
            # Apply filters
            filtered_conversations = self._apply_filters(
                all_conversations, 
                filter_analysis_type, 
                min_success
            )
            
            if not filtered_conversations:
                self.logger.warning("No conversations match the filter criteria")
                return ""
            
            # Export based on format
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if format_to_use == "jsonl":
                return self._export_jsonl(filtered_conversations, output_filename, timestamp)
            elif format_to_use == "chat":
                return self._export_chat(filtered_conversations, output_filename, timestamp)
            elif format_to_use == "raw":
                return self._export_raw(filtered_conversations, output_filename, timestamp)
            else:
                raise ValueError(f"Unsupported export format: {format_to_use}")
                
        except Exception as e:
            self.logger.error(f"Failed to export training data: {e}")
            raise
    
    def _collect_all_conversations(self) -> List[ConversationTurn]:
        """Collect all conversations from storage"""
        all_conversations = []
        
        for dataset_info in self.storage.list_datasets():
            try:
                dataset = self.storage.load_dataset(dataset_info['filepath'])
                all_conversations.extend(dataset.conversations)
            except Exception as e:
                self.logger.error(f"Failed to load dataset {dataset_info['filename']}: {e}")
        
        return all_conversations
    
    def _apply_filters(
        self, 
        conversations: List[ConversationTurn], 
        analysis_type: str = None,
        min_success_rate: float = None
    ) -> List[ConversationTurn]:
        """Apply filters to conversations"""
        
        filtered = conversations
        
        # Filter by analysis type
        if analysis_type:
            filtered = [conv for conv in filtered if conv.analysis_type == analysis_type]
            self.logger.info(f"Filtered by analysis type '{analysis_type}': {len(filtered)} conversations")
        
        # Filter by success rate
        if min_success_rate is not None:
            successful_conversations = [conv for conv in filtered if conv.success]
            current_success_rate = len(successful_conversations) / len(filtered) if filtered else 0
            
            if current_success_rate >= min_success_rate:
                filtered = successful_conversations
                self.logger.info(f"Filtered by success rate >= {min_success_rate}: {len(filtered)} conversations")
            else:
                self.logger.warning(f"Success rate {current_success_rate:.2f} below minimum {min_success_rate}")
        
        return filtered
    
    def _export_jsonl(self, conversations: List[ConversationTurn], filename: str, timestamp: str) -> str:
        """Export in JSONL format for instruction tuning"""
        
        if not filename:
            filename = f"training_data_{timestamp}.jsonl"
        
        output_file = self.storage.data_dir / filename
        
        with open(output_file, 'w') as f:
            for conv in conversations:
                # Format for instruction tuning
                training_example = {
                    "instruction": self._format_instruction(conv),
                    "input": conv.user_message,
                    "output": conv.assistant_response,
                    "context": conv.context,
                    "metadata": {
                        "analysis_type": conv.analysis_type,
                        "pipeline_step": conv.pipeline_step,
                        "tools_used": conv.tools_used,
                        "session_id": conv.session_id,
                        "timestamp": conv.timestamp.isoformat()
                    }
                }
                f.write(json.dumps(training_example) + "\n")
        
        self.logger.info(f"Exported {len(conversations)} conversations to JSONL format: {filename}")
        return str(output_file)
    
    def _export_chat(self, conversations: List[ConversationTurn], filename: str, timestamp: str) -> str:
        """Export in chat format for chat-based training"""
        
        if not filename:
            filename = f"chat_training_{timestamp}.json"
        
        output_file = self.storage.data_dir / filename
        
        chat_data = []
        for conv in conversations:
            chat_example = {
                "messages": [
                    {
                        "role": "system",
                        "content": self._format_system_prompt(conv)
                    },
                    {
                        "role": "user", 
                        "content": conv.user_message
                    },
                    {
                        "role": "assistant",
                        "content": conv.assistant_response
                    }
                ],
                "metadata": {
                    "analysis_type": conv.analysis_type,
                    "pipeline_step": conv.pipeline_step,
                    "tools_used": conv.tools_used,
                    "success": conv.success,
                    "timestamp": conv.timestamp.isoformat()
                }
            }
            chat_data.append(chat_example)
        
        with open(output_file, 'w') as f:
            json.dump(chat_data, f, indent=2)
        
        self.logger.info(f"Exported {len(conversations)} conversations to chat format: {filename}")
        return str(output_file)
    
    def _export_raw(self, conversations: List[ConversationTurn], filename: str, timestamp: str) -> str:
        """Export in raw format (original conversation structure)"""
        
        if not filename:
            filename = f"raw_training_{timestamp}.json"
        
        output_file = self.storage.data_dir / filename
        
        # Create a dataset with the filtered conversations
        dataset = TrainingDataset(
            conversations=conversations,
            metadata={
                "export_type": "raw",
                "export_date": datetime.now().isoformat(),
                "total_conversations": len(conversations),
                "filtered": True
            },
            created_at=datetime.now()
        )
        
        with open(output_file, 'w') as f:
            json.dump(dataset.to_dict(), f, indent=2, default=str)
        
        self.logger.info(f"Exported {len(conversations)} conversations to raw format: {filename}")
        return str(output_file)
    
    def _format_instruction(self, conv: ConversationTurn) -> str:
        """Format instruction for instruction tuning"""
        analysis_type = conv.analysis_type
        pipeline_step = conv.pipeline_step
        
        base_instruction = f"You are a bioinformatics assistant helping with {analysis_type} analysis"
        
        if pipeline_step != "unknown":
            base_instruction += f" at the {pipeline_step} step"
        
        base_instruction += ". Provide helpful, accurate responses based on the data context."
        
        # Add context-specific instructions
        context_instructions = self._get_context_instructions(conv.context)
        if context_instructions:
            base_instruction += f"\n\nContext: {context_instructions}"
        
        return base_instruction
    
    def _format_system_prompt(self, conv: ConversationTurn) -> str:
        """Format system prompt for chat training"""
        context = conv.context
        analysis_type = conv.analysis_type
        pipeline_step = conv.pipeline_step
        
        prompt = f"""You are an expert bioinformatics assistant specializing in {analysis_type} analysis.

Current Context:
- Analysis Type: {analysis_type}
- Pipeline Step: {pipeline_step}"""
        
        # Add data characteristics if available
        data_chars = context.get('data_characteristics', {})
        if data_chars:
            prompt += f"\n- Data: {data_chars}"
        
        # Add pipeline progress if available
        progress = context.get('pipeline_progress', {})
        if progress:
            completed_steps = [step for step, done in progress.items() if done]
            if completed_steps:
                prompt += f"\n- Completed Steps: {', '.join(completed_steps)}"
        
        prompt += "\n\nProvide accurate, helpful responses that guide users through their analysis workflow."
        
        return prompt
    
    def _get_context_instructions(self, context: Dict[str, Any]) -> str:
        """Generate context-specific instructions"""
        instructions = []
        
        # Data characteristics
        data_chars = context.get('data_characteristics', {})
        if data_chars:
            if data_chars.get('n_cells'):
                instructions.append(f"Working with {data_chars['n_cells']} cells")
            if data_chars.get('n_genes'):
                instructions.append(f"{data_chars['n_genes']} genes")
        
        # Pipeline progress
        progress = context.get('pipeline_progress', {})
        completed_steps = [step for step, done in progress.items() if done]
        if completed_steps:
            instructions.append(f"Completed: {', '.join(completed_steps)}")
        
        return "; ".join(instructions)
    
    def export_statistics(self, conversations: List[ConversationTurn] = None) -> Dict[str, Any]:
        """Generate export statistics"""
        
        if conversations is None:
            conversations = self._collect_all_conversations()
        
        if not conversations:
            return {"error": "No conversations available"}
        
        stats = {
            "total_conversations": len(conversations),
            "analysis_types": {},
            "pipeline_steps": {},
            "success_rate": 0,
            "date_range": {"earliest": None, "latest": None},
            "average_message_length": {
                "user": 0,
                "assistant": 0
            },
            "tools_usage": {}
        }
        
        # Analysis types and pipeline steps
        for conv in conversations:
            # Analysis types
            analysis_type = conv.analysis_type
            stats["analysis_types"][analysis_type] = stats["analysis_types"].get(analysis_type, 0) + 1
            
            # Pipeline steps
            pipeline_step = conv.pipeline_step
            stats["pipeline_steps"][pipeline_step] = stats["pipeline_steps"].get(pipeline_step, 0) + 1
            
            # Tools usage
            for tool in conv.tools_used:
                tool_name = tool.get('name', 'unknown')
                stats["tools_usage"][tool_name] = stats["tools_usage"].get(tool_name, 0) + 1
        
        # Success rate
        successful = sum(1 for conv in conversations if conv.success)
        stats["success_rate"] = successful / len(conversations)
        
        # Date range
        timestamps = [conv.timestamp for conv in conversations]
        stats["date_range"]["earliest"] = min(timestamps).isoformat()
        stats["date_range"]["latest"] = max(timestamps).isoformat()
        
        # Average message lengths
        stats["average_message_length"]["user"] = sum(len(conv.user_message) for conv in conversations) / len(conversations)
        stats["average_message_length"]["assistant"] = sum(len(conv.assistant_response) for conv in conversations) / len(conversations)
        
        return stats

if __name__ == "__main__":
    # Example usage
    from .storage import TrainingDataStorage
    from .models import ConversationTurn
    
    print("Training Data Exporter Examples:")
    
    # Create exporter with test storage
    storage = TrainingDataStorage("data/training/test")
    exporter = TrainingDataExporter(storage)
    
    # Create sample data
    sample_conversations = [
        ConversationTurn(
            user_id="test_user",
            session_id="test_session",
            timestamp=datetime.now(),
            user_message="How do I normalize my data?",
            assistant_response="You can use scanpy's pp.normalize_total function...",
            context={"analysis_type": "scrna_seq", "pipeline_progress": {"qc_done": True}},
            tools_used=[{"name": "scanpy", "success": True}],
            analysis_type="scrna_seq",
            pipeline_step="normalization",
            success=True
        )
    ]
    
    # Save sample data
    sample_dataset = TrainingDataset(
        conversations=sample_conversations,
        metadata={"test": True},
        created_at=datetime.now()
    )
    storage.save_dataset(sample_dataset, "test_export.json")
    
    # Export in different formats
    jsonl_file = exporter.export_for_training(output_format="jsonl")
    chat_file = exporter.export_for_training(output_format="chat")
    raw_file = exporter.export_for_training(output_format="raw")
    
    print(f"JSONL export: {jsonl_file}")
    print(f"Chat export: {chat_file}")
    print(f"Raw export: {raw_file}")
    
    # Get statistics
    stats = exporter.export_statistics()
    print(f"Export statistics: {stats}")
    
    # Cleanup
    import os
    for file in [jsonl_file, chat_file, raw_file, "data/training/test/test_export.json"]:
        if os.path.exists(file):
            os.remove(file) 