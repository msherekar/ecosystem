"""
Training Data Collector for MCP System
Collects conversation data for future LLM training and fine-tuning
"""

import json
import asyncio
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import streamlit as st
from dataclasses import dataclass, asdict
import logging

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

@dataclass
class TrainingDataset:
    """Collection of conversation turns for training"""
    conversations: List[ConversationTurn]
    metadata: Dict[str, Any]
    created_at: datetime
    version: str = "1.0"

class TrainingDataCollector:
    """Collects and manages training data from MCP interactions"""
    
    def __init__(self, data_dir: str = "data/training"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("training_collector")
        
        # Privacy settings
        self.anonymize_data = True
        self.collect_enabled = True  # Can be disabled for privacy
        
        # Current session data
        self.current_session_data = []
        
    def _anonymize_user_id(self, user_identifier: str) -> str:
        """Create anonymized but consistent user ID"""
        if not self.anonymize_data:
            return user_identifier
        
        # Create consistent hash for user
        return hashlib.sha256(user_identifier.encode()).hexdigest()[:16]
    
    def _get_session_id(self) -> str:
        """Get current session ID"""
        if "training_session_id" not in st.session_state:
            st.session_state.training_session_id = hashlib.md5(
                f"{datetime.now().isoformat()}_{id(st.session_state)}".encode()
            ).hexdigest()[:12]
        return st.session_state.training_session_id
    
    def _extract_context(self) -> Dict[str, Any]:
        """Extract relevant context for training"""
        context = {
            "analysis_state": {},
            "available_tools": [],
            "pipeline_progress": {},
            "data_characteristics": {}
        }
        
        # Analysis state
        if "anndata" in st.session_state:
            adata = st.session_state.anndata
            context["data_characteristics"] = {
                "n_cells": adata.n_obs if adata is not None else 0,
                "n_genes": adata.n_vars if adata is not None else 0,
                "has_raw": hasattr(adata, 'raw') and adata.raw is not None if adata else False
            }
        
        # Pipeline progress
        pipeline_flags = [
            "qc_done", "filtering_done", "normalization_done", 
            "dimred_done", "clustering_done", "dea_done"
        ]
        context["pipeline_progress"] = {
            flag: st.session_state.get(flag, False) for flag in pipeline_flags
        }
        
        # Current step
        context["current_step"] = st.session_state.get("scrna_current_step", "unknown")
        
        return context
    
    def _determine_analysis_type(self) -> str:
        """Determine the type of analysis being performed"""
        if "anndata" in st.session_state:
            return "scrna_seq"
        elif "uploaded_df" in st.session_state:
            return "tabular"
        else:
            return "general"
    
    def _extract_tools_used(self, tool_results: List[str]) -> List[Dict[str, Any]]:
        """Extract tool usage information"""
        tools = []
        for result in tool_results:
            if "Tool " in result:
                parts = result.split(":", 1)
                if len(parts) == 2:
                    tool_name = parts[0].replace("Tool ", "").strip()
                    tools.append({
                        "name": tool_name,
                        "success": "failed" not in result.lower(),
                        "timestamp": datetime.now().isoformat()
                    })
        return tools
    
    async def collect_conversation_turn(
        self,
        user_message: str,
        assistant_response: str,
        tool_results: List[str] = None,
        success: bool = True,
        user_feedback: str = None
    ) -> None:
        """Collect a single conversation turn"""
        
        if not self.collect_enabled:
            return
        
        try:
            # Create conversation turn
            turn = ConversationTurn(
                user_id=self._anonymize_user_id("default_user"),  # Future: real user ID
                session_id=self._get_session_id(),
                timestamp=datetime.now(),
                user_message=user_message,
                assistant_response=assistant_response,
                context=self._extract_context(),
                tools_used=self._extract_tools_used(tool_results or []),
                analysis_type=self._determine_analysis_type(),
                pipeline_step=st.session_state.get("scrna_current_step", "unknown"),
                success=success,
                user_feedback=user_feedback
            )
            
            # Add to current session
            self.current_session_data.append(turn)
            
            # Auto-save periodically
            if len(self.current_session_data) % 10 == 0:
                await self._save_session_data()
                
        except Exception as e:
            self.logger.error(f"Failed to collect conversation turn: {e}")
    
    async def _save_session_data(self) -> None:
        """Save current session data to disk"""
        if not self.current_session_data:
            return
        
        try:
            session_id = self._get_session_id()
            filename = f"session_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = self.data_dir / filename
            
            # Create dataset
            dataset = TrainingDataset(
                conversations=self.current_session_data.copy(),
                metadata={
                    "session_id": session_id,
                    "total_turns": len(self.current_session_data),
                    "analysis_types": list(set(turn.analysis_type for turn in self.current_session_data)),
                    "pipeline_steps": list(set(turn.pipeline_step for turn in self.current_session_data)),
                    "collection_date": datetime.now().isoformat()
                },
                created_at=datetime.now()
            )
            
            # Save to JSON
            with open(filepath, 'w') as f:
                json.dump(asdict(dataset), f, indent=2, default=str)
            
            self.logger.info(f"Saved {len(self.current_session_data)} conversation turns to {filename}")
            
            # Clear current session data
            self.current_session_data = []
            
        except Exception as e:
            self.logger.error(f"Failed to save session data: {e}")
    
    def get_training_statistics(self) -> Dict[str, Any]:
        """Get statistics about collected training data"""
        stats = {
            "total_files": 0,
            "total_conversations": 0,
            "analysis_types": {},
            "pipeline_steps": {},
            "date_range": {"earliest": None, "latest": None}
        }
        
        try:
            json_files = list(self.data_dir.glob("session_*.json"))
            stats["total_files"] = len(json_files)
            
            for file_path in json_files:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                conversations = data.get("conversations", [])
                stats["total_conversations"] += len(conversations)
                
                for conv in conversations:
                    # Analysis types
                    analysis_type = conv.get("analysis_type", "unknown")
                    stats["analysis_types"][analysis_type] = stats["analysis_types"].get(analysis_type, 0) + 1
                    
                    # Pipeline steps
                    pipeline_step = conv.get("pipeline_step", "unknown")
                    stats["pipeline_steps"][pipeline_step] = stats["pipeline_steps"].get(pipeline_step, 0) + 1
                    
                    # Date range
                    timestamp = conv.get("timestamp")
                    if timestamp:
                        if not stats["date_range"]["earliest"] or timestamp < stats["date_range"]["earliest"]:
                            stats["date_range"]["earliest"] = timestamp
                        if not stats["date_range"]["latest"] or timestamp > stats["date_range"]["latest"]:
                            stats["date_range"]["latest"] = timestamp
        
        except Exception as e:
            self.logger.error(f"Failed to get training statistics: {e}")
        
        return stats
    
    async def export_for_training(
        self, 
        output_format: str = "jsonl",
        filter_analysis_type: str = None,
        min_success_rate: float = 0.8
    ) -> str:
        """Export collected data in format suitable for LLM training"""
        
        try:
            # Collect all conversation data
            all_conversations = []
            json_files = list(self.data_dir.glob("session_*.json"))
            
            for file_path in json_files:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    conversations = data.get("conversations", [])
                    
                    # Apply filters
                    for conv in conversations:
                        if filter_analysis_type and conv.get("analysis_type") != filter_analysis_type:
                            continue
                        if not conv.get("success", True):
                            continue
                        
                        all_conversations.append(conv)
            
            # Export based on format
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if output_format == "jsonl":
                output_file = self.data_dir / f"training_data_{timestamp}.jsonl"
                
                with open(output_file, 'w') as f:
                    for conv in all_conversations:
                        # Format for instruction tuning
                        training_example = {
                            "instruction": self._format_instruction(conv),
                            "input": conv["user_message"],
                            "output": conv["assistant_response"],
                            "context": conv["context"],
                            "metadata": {
                                "analysis_type": conv["analysis_type"],
                                "pipeline_step": conv["pipeline_step"],
                                "tools_used": conv["tools_used"]
                            }
                        }
                        f.write(json.dumps(training_example) + "\n")
            
            elif output_format == "chat":
                output_file = self.data_dir / f"chat_training_{timestamp}.json"
                
                chat_data = []
                for conv in all_conversations:
                    chat_example = {
                        "messages": [
                            {
                                "role": "system",
                                "content": self._format_system_prompt(conv)
                            },
                            {
                                "role": "user", 
                                "content": conv["user_message"]
                            },
                            {
                                "role": "assistant",
                                "content": conv["assistant_response"]
                            }
                        ]
                    }
                    chat_data.append(chat_example)
                
                with open(output_file, 'w') as f:
                    json.dump(chat_data, f, indent=2)
            
            self.logger.info(f"Exported {len(all_conversations)} conversations to {output_file}")
            return str(output_file)
            
        except Exception as e:
            self.logger.error(f"Failed to export training data: {e}")
            return ""
    
    def _format_instruction(self, conv: Dict[str, Any]) -> str:
        """Format instruction for instruction tuning"""
        analysis_type = conv.get("analysis_type", "general")
        pipeline_step = conv.get("pipeline_step", "unknown")
        
        return f"You are a bioinformatics assistant helping with {analysis_type} analysis at the {pipeline_step} step. Provide helpful, accurate responses based on the data context."
    
    def _format_system_prompt(self, conv: Dict[str, Any]) -> str:
        """Format system prompt for chat training"""
        context = conv.get("context", {})
        analysis_type = conv.get("analysis_type", "general")
        pipeline_step = conv.get("pipeline_step", "unknown")
        
        prompt = f"""You are an expert bioinformatics assistant specializing in {analysis_type} analysis.

Current Context:
- Analysis Type: {analysis_type}
- Pipeline Step: {pipeline_step}
- Data: {context.get('data_characteristics', {})}
- Progress: {context.get('pipeline_progress', {})}

Provide accurate, helpful responses that guide users through their analysis workflow."""
        
        return prompt

# Global collector instance
training_collector = TrainingDataCollector()

async def get_training_collector() -> TrainingDataCollector:
    """Get the global training data collector"""
    return training_collector 