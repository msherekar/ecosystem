"""
Export format handlers for different training data formats.
Supports JSONL, chat, raw, and HuggingFace dataset formats.
"""

import json
import gzip
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import aiofiles

from .models import ConversationTurn

class ExportFormatManager:
    """Manages different export formats for training data"""
    
    def __init__(self):
        self.logger = logging.getLogger("export_formats")
        self.format_handlers = {
            "jsonl": self._export_jsonl,
            "chat": self._export_chat,
            "raw": self._export_raw,
            "huggingface": self._export_huggingface
        }
    
    async def export_conversations(
        self,
        conversations: List[ConversationTurn],
        format_type: str,
        output_filename: str,
        data_dir: Path,
        compress: bool = False
    ) -> str:
        """Export conversations in specified format"""
        
        if format_type not in self.format_handlers:
            raise ValueError(f"Unsupported export format: {format_type}")
        
        handler = self.format_handlers[format_type]
        
        # Add appropriate extension
        file_extension = self._get_file_extension(format_type)
        if not output_filename.endswith(file_extension):
            output_filename += file_extension
        
        if compress:
            output_filename += ".gz"
        
        output_file = data_dir / output_filename
        
        # Export using the appropriate handler
        await handler(conversations, output_file, compress)
        
        self.logger.info(f"Exported {len(conversations)} conversations to {format_type} format")
        return str(output_file)
    
    def _get_file_extension(self, format_type: str) -> str:
        """Get file extension for format type"""
        extensions = {
            "jsonl": ".jsonl",
            "chat": ".json",
            "raw": ".json",
            "huggingface": ".json"
        }
        return extensions.get(format_type, ".txt")
    
    async def _export_jsonl(self, conversations: List[ConversationTurn], 
                           output_file: Path, compress: bool = False) -> None:
        """Export in JSONL format for instruction tuning"""
        
        open_func = gzip.open if compress else aiofiles.open
        mode = 'wt' if compress else 'w'
        
        async with open_func(output_file, mode) as f:
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
                        "timestamp": conv.timestamp.isoformat(),
                        "success": conv.success
                    }
                }
                
                line = json.dumps(training_example, ensure_ascii=False) + "\n"
                if compress:
                    f.write(line)
                else:
                    await f.write(line)
    
    async def _export_chat(self, conversations: List[ConversationTurn], 
                          output_file: Path, compress: bool = False) -> None:
        """Export in chat format for chat-based training"""
        
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
                    "timestamp": conv.timestamp.isoformat(),
                    "session_id": conv.session_id
                }
            }
            chat_data.append(chat_example)
        
        # Write to file
        content = json.dumps(chat_data, indent=2, ensure_ascii=False)
        
        if compress:
            with gzip.open(output_file, 'wt') as f:
                f.write(content)
        else:
            async with aiofiles.open(output_file, 'w') as f:
                await f.write(content)
    
    async def _export_raw(self, conversations: List[ConversationTurn], 
                         output_file: Path, compress: bool = False) -> None:
        """Export in raw format (original conversation structure)"""
        
        from .models import TrainingDataset
        from datetime import datetime
        
        # Create a dataset with the conversations
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
        
        content = json.dumps(dataset.to_dict(), indent=2, default=str, ensure_ascii=False)
        
        if compress:
            with gzip.open(output_file, 'wt') as f:
                f.write(content)
        else:
            async with aiofiles.open(output_file, 'w') as f:
                await f.write(content)
    
    async def _export_huggingface(self, conversations: List[ConversationTurn], 
                                 output_file: Path, compress: bool = False) -> None:
        """Export in HuggingFace datasets format"""
        
        # HuggingFace format with features schema
        hf_dataset = {
            "info": {
                "description": "Training conversations for bioinformatics assistant",
                "version": "1.0.0",
                "features": {
                    "conversation_id": {"dtype": "string"},
                    "user_message": {"dtype": "string"},
                    "assistant_response": {"dtype": "string"},
                    "analysis_type": {"dtype": "string"},
                    "pipeline_step": {"dtype": "string"},
                    "success": {"dtype": "bool"},
                    "tools_used": {"dtype": "string"},  # JSON string
                    "context": {"dtype": "string"},     # JSON string
                    "timestamp": {"dtype": "string"}
                }
            },
            "split": "train",
            "data": []
        }
        
        for i, conv in enumerate(conversations):
            hf_example = {
                "conversation_id": f"{conv.session_id}_{i}",
                "user_message": conv.user_message,
                "assistant_response": conv.assistant_response,
                "analysis_type": conv.analysis_type,
                "pipeline_step": conv.pipeline_step,
                "success": conv.success,
                "tools_used": json.dumps(conv.tools_used),
                "context": json.dumps(conv.context),
                "timestamp": conv.timestamp.isoformat()
            }
            hf_dataset["data"].append(hf_example)
        
        content = json.dumps(hf_dataset, indent=2, ensure_ascii=False)
        
        if compress:
            with gzip.open(output_file, 'wt') as f:
                f.write(content)
        else:
            async with aiofiles.open(output_file, 'w') as f:
                await f.write(content)
    
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
    
    async def validate_export_file(self, file_path: str) -> Dict[str, Any]:
        """Validate exported file format and content"""
        try:
            path = Path(file_path)
            
            # Determine format from extension
            if path.name.endswith('.jsonl') or path.name.endswith('.jsonl.gz'):
                return await self._validate_jsonl_file(path)
            elif path.name.endswith('.json') or path.name.endswith('.json.gz'):
                return await self._validate_json_file(path)
            else:
                return {"valid": False, "error": "Unknown file format"}
        
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    async def _validate_jsonl_file(self, file_path: Path) -> Dict[str, Any]:
        """Validate JSONL format file"""
        try:
            line_count = 0
            valid_lines = 0
            
            if file_path.name.endswith('.gz'):
                import gzip
                open_func = gzip.open
                mode = 'rt'
            else:
                open_func = open
                mode = 'r'
            
            with open_func(file_path, mode) as f:
                for line in f:
                    line_count += 1
                    try:
                        data = json.loads(line.strip())
                        # Check required fields
                        if all(key in data for key in ['instruction', 'input', 'output']):
                            valid_lines += 1
                    except json.JSONDecodeError:
                        pass
            
            return {
                "valid": valid_lines > 0,
                "total_lines": line_count,
                "valid_lines": valid_lines,
                "format": "jsonl"
            }
        
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    async def _validate_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Validate JSON format file"""
        try:
            if file_path.name.endswith('.gz'):
                import gzip
                with gzip.open(file_path, 'rt') as f:
                    data = json.load(f)
            else:
                with open(file_path, 'r') as f:
                    data = json.load(f)
            
            # Determine JSON format type
            if isinstance(data, list) and data and 'messages' in data[0]:
                # Chat format
                valid_entries = sum(1 for item in data if 'messages' in item)
                return {
                    "valid": valid_entries > 0,
                    "total_entries": len(data),
                    "valid_entries": valid_entries,
                    "format": "chat"
                }
            elif isinstance(data, dict) and 'conversations' in data:
                # Raw format
                conversations = data.get('conversations', [])
                return {
                    "valid": len(conversations) > 0,
                    "total_conversations": len(conversations),
                    "format": "raw"
                }
            elif isinstance(data, dict) and 'data' in data:
                # HuggingFace format
                hf_data = data.get('data', [])
                return {
                    "valid": len(hf_data) > 0,
                    "total_entries": len(hf_data),
                    "format": "huggingface"
                }
            else:
                return {"valid": False, "error": "Unknown JSON structure"}
        
        except Exception as e:
            return {"valid": False, "error": str(e)}


def main():
        """Test export formats"""
        import asyncio
        from datetime import datetime
        from .models import ConversationTurn
        
        async def test_export_formats():
            print("Testing Export Format Manager")
            print("=" * 40)
            
            # Create sample conversation
            sample_conv = ConversationTurn(
                user_id="test_user",
                session_id="test_session",
                timestamp=datetime.now(),
                user_message="How do I normalize my data?",
                assistant_response="You can use scanpy's normalize function...",
                context={"analysis_type": "scrna_seq"},
                tools_used=[{"name": "scanpy", "success": True}],
                analysis_type="scrna_seq",
                pipeline_step="normalization",
                success=True
            )
            
            format_manager = ExportFormatManager()
            test_dir = Path("data/test_exports")
            test_dir.mkdir(parents=True, exist_ok=True)
            
            # Test all formats
            formats = ["jsonl", "chat", "raw", "huggingface"]
            
            for format_type in formats:
                try:
                    output_file = await format_manager.export_conversations(
                        conversations=[sample_conv],
                        format_type=format_type,
                        output_filename=f"test_{format_type}",
                        data_dir=test_dir,
                        compress=False
                    )
                    
                    # Validate the export
                    validation = await format_manager.validate_export_file(output_file)
                    
                    print(f"✓ {format_type}: {validation.get('valid', False)}")
                    
                    # Cleanup
                    Path(output_file).unlink(missing_ok=True)
                
                except Exception as e:
                    print(f"✗ {format_type}: {e}")
            
            # Cleanup test directory
            test_dir.rmdir()
            print("✓ All export format tests completed!")
        
        asyncio.run(test_export_formats())
    
if __name__ == "__main__":
    main()