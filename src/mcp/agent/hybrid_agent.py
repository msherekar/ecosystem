"""
Hybrid Agent for MCP System
Seamlessly switches between external LLMs and local models
Optimizes for cost, performance, and availability
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import streamlit as st

from src.agent.core import Agent
from src.mcp.core.local_llm import get_local_llm_manager, LocalLLMManager
from src.mcp.core.training_collector import get_training_collector

class LLMProvider(Enum):
    """Available LLM providers"""
    EXTERNAL = "external"  # OpenRouter, OpenAI, etc.
    LOCAL = "local"       # Ollama, local models
    HYBRID = "hybrid"     # Automatic selection

class HybridAgent:
    """Agent that can use both external and local LLMs intelligently"""
    
    def __init__(self, api_key: str = None):
        self.external_agent = Agent(api_key) if api_key else None
        self.local_llm_manager: Optional[LocalLLMManager] = None
        self.training_collector = None
        
        # Configuration
        self.preferred_provider = LLMProvider.HYBRID
        self.cost_optimization = True
        self.local_first = False  # Prefer local models when available
        
        # Statistics
        self.usage_stats = {
            "external_calls": 0,
            "local_calls": 0,
            "total_cost_saved": 0.0,
            "fallback_count": 0
        }
        
        self.logger = logging.getLogger("hybrid_agent")
    
    async def initialize(self) -> bool:
        """Initialize both external and local LLM capabilities"""
        try:
            # Initialize training collector
            self.training_collector = await get_training_collector()
            
            # Try to initialize local LLM
            try:
                self.local_llm_manager = await get_local_llm_manager()
                if self.local_llm_manager:
                    self.logger.info("Local LLM initialized successfully")
                else:
                    self.logger.warning("Local LLM not available")
            except Exception as e:
                self.logger.warning(f"Failed to initialize local LLM: {e}")
            
            # Check external agent
            if self.external_agent:
                self.logger.info("External LLM agent available")
            else:
                self.logger.warning("External LLM agent not available (no API key)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize hybrid agent: {e}")
            return False
    
    def set_provider_preference(self, provider: LLMProvider, local_first: bool = False):
        """Set LLM provider preference"""
        self.preferred_provider = provider
        self.local_first = local_first
        self.logger.info(f"Provider preference set to: {provider.value}, local_first: {local_first}")
    
    def _should_use_local_llm(self, user_message: str, context: Dict[str, Any] = None) -> bool:
        """Determine whether to use local LLM based on various factors"""
        
        # If local LLM not available, use external
        if not self.local_llm_manager or not self.local_llm_manager.is_available:
            return False
        
        # If external agent not available, use local
        if not self.external_agent:
            return True
        
        # Provider preference
        if self.preferred_provider == LLMProvider.LOCAL:
            return True
        elif self.preferred_provider == LLMProvider.EXTERNAL:
            return False
        
        # Hybrid decision logic
        if self.preferred_provider == LLMProvider.HYBRID:
            
            # Simple queries can be handled locally
            simple_keywords = [
                "what is", "explain", "define", "how to", "show me",
                "summarize", "describe", "list", "compare"
            ]
            
            if any(keyword in user_message.lower() for keyword in simple_keywords):
                if self.local_first:
                    return True
            
            # Complex analysis might need external LLM
            complex_keywords = [
                "interpret results", "biological significance", "pathway analysis",
                "statistical significance", "recommend next steps", "troubleshoot"
            ]
            
            if any(keyword in user_message.lower() for keyword in complex_keywords):
                if not self.local_first:
                    return False
            
            # Cost optimization: use local for frequent queries
            if self.cost_optimization and self.usage_stats["external_calls"] > 10:
                return True
            
            # Default based on local_first preference
            return self.local_first
        
        return False
    
    async def chat(self, user_message: str) -> Tuple[str, List[str]]:
        """Main chat method with intelligent provider selection"""
        
        try:
            # Determine which LLM to use
            use_local = self._should_use_local_llm(user_message)
            
            if use_local and self.local_llm_manager:
                return await self._chat_with_local_llm(user_message)
            elif self.external_agent:
                return await self._chat_with_external_llm(user_message)
            else:
                # Fallback
                if self.local_llm_manager:
                    self.usage_stats["fallback_count"] += 1
                    return await self._chat_with_local_llm(user_message)
                else:
                    return "No LLM providers available. Please check your configuration.", []
        
        except Exception as e:
            self.logger.error(f"Chat failed: {e}")
            
            # Try fallback provider
            try:
                if use_local and self.external_agent:
                    self.logger.info("Falling back to external LLM")
                    self.usage_stats["fallback_count"] += 1
                    return await self._chat_with_external_llm(user_message)
                elif not use_local and self.local_llm_manager:
                    self.logger.info("Falling back to local LLM")
                    self.usage_stats["fallback_count"] += 1
                    return await self._chat_with_local_llm(user_message)
            except Exception as fallback_error:
                self.logger.error(f"Fallback also failed: {fallback_error}")
            
            return f"I encountered an error: {str(e)}", []
    
    async def _chat_with_external_llm(self, user_message: str) -> Tuple[str, List[str]]:
        """Chat using external LLM (OpenRouter, etc.)"""
        
        self.usage_stats["external_calls"] += 1
        self.logger.info("Using external LLM")
        
        # Use existing agent implementation
        response, flags = await self.external_agent.chat(user_message)
        
        # Estimate cost saved if we had used local
        if self.local_llm_manager and self.local_llm_manager.is_available:
            estimated_cost = self._estimate_external_cost(user_message, response)
            self.usage_stats["total_cost_saved"] -= estimated_cost  # Negative because we spent money
        
        return response, flags
    
    async def _chat_with_local_llm(self, user_message: str) -> Tuple[str, List[str]]:
        """Chat using local LLM (Ollama, etc.)"""
        
        self.usage_stats["local_calls"] += 1
        self.logger.info("Using local LLM")
        
        try:
            # Get MCP context (similar to external agent)
            mcp_registry = await self.external_agent._ensure_mcp_initialized() if self.external_agent else None
            
            # Build messages
            messages = []
            
            # System prompt
            system_prompt = """You are an expert bioinformatics assistant specializing in genomics data analysis. You help users with:
- Single-cell RNA sequencing (scRNA-seq) analysis
- Bulk RNA sequencing analysis  
- Quality control and preprocessing
- Statistical analysis and visualization
- Biological interpretation of results

Provide accurate, helpful responses that guide users through their analysis workflows."""
            
            messages.append({"role": "system", "content": system_prompt})
            
            # Add conversation history from Streamlit
            if "messages" in st.session_state:
                recent_messages = st.session_state.messages[-4:] if len(st.session_state.messages) > 4 else st.session_state.messages
                for msg in recent_messages[:-1]:  # Exclude current message
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # Add current message
            messages.append({"role": "user", "content": user_message})
            
            # Generate response
            response_data = await self.local_llm_manager.generate_response(messages)
            
            response_content = response_data["choices"][0]["message"]["content"]
            
            # Collect training data
            if self.training_collector:
                try:
                    await self.training_collector.collect_conversation_turn(
                        user_message=user_message,
                        assistant_response=response_content,
                        tool_results=[],
                        success=True
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to collect training data: {e}")
            
            # Estimate cost saved
            estimated_cost = self._estimate_external_cost(user_message, response_content)
            self.usage_stats["total_cost_saved"] += estimated_cost
            
            return response_content, []
            
        except Exception as e:
            self.logger.error(f"Local LLM chat failed: {e}")
            raise
    
    def _estimate_external_cost(self, user_message: str, response: str) -> float:
        """Estimate cost if external LLM was used"""
        # Rough estimation based on token count
        # GPT-4: ~$0.03/1K input tokens, ~$0.06/1K output tokens
        
        input_tokens = len(user_message.split()) * 1.3  # Rough token estimation
        output_tokens = len(response.split()) * 1.3
        
        input_cost = (input_tokens / 1000) * 0.03
        output_cost = (output_tokens / 1000) * 0.06
        
        return input_cost + output_cost
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get usage statistics and cost savings"""
        
        total_calls = self.usage_stats["external_calls"] + self.usage_stats["local_calls"]
        local_percentage = (self.usage_stats["local_calls"] / total_calls * 100) if total_calls > 0 else 0
        
        return {
            "total_calls": total_calls,
            "external_calls": self.usage_stats["external_calls"],
            "local_calls": self.usage_stats["local_calls"],
            "local_percentage": round(local_percentage, 1),
            "estimated_cost_saved": round(self.usage_stats["total_cost_saved"], 4),
            "fallback_count": self.usage_stats["fallback_count"],
            "providers_available": {
                "external": self.external_agent is not None,
                "local": self.local_llm_manager is not None and self.local_llm_manager.is_available
            }
        }
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of available providers"""
        
        status = {
            "external": {
                "available": self.external_agent is not None,
                "description": "OpenRouter/OpenAI API" if self.external_agent else "No API key provided"
            },
            "local": {
                "available": False,
                "description": "Not available"
            }
        }
        
        if self.local_llm_manager:
            model_info = self.local_llm_manager.get_model_info()
            status["local"] = {
                "available": model_info["is_available"],
                "model_name": model_info["model_name"],
                "api_format": model_info["api_format"],
                "description": f"Local model: {model_info['model_name']}" if model_info["is_available"] else "Local LLM not available"
            }
        
        return status
    
    async def train_local_model(
        self,
        base_model: str = "llama3.1:8b",
        model_name: str = "bioinformatics-assistant",
        min_conversations: int = 50
    ) -> Dict[str, Any]:
        """Train a local model using collected conversation data"""
        
        try:
            if not self.training_collector:
                return {"success": False, "error": "Training collector not available"}
            
            # Check if we have enough training data
            stats = self.training_collector.get_training_statistics()
            
            if stats["total_conversations"] < min_conversations:
                return {
                    "success": False,
                    "error": f"Need at least {min_conversations} conversations, have {stats['total_conversations']}"
                }
            
            # Export training data
            training_file = await self.training_collector.export_for_training(
                output_format="jsonl",
                filter_analysis_type="scrna_seq"  # Focus on scRNA-seq for now
            )
            
            if not training_file:
                return {"success": False, "error": "Failed to export training data"}
            
            # Initialize trainer
            from src.mcp.core.local_llm import LocalLLMTrainer
            trainer = LocalLLMTrainer()
            
            # Prepare training data
            prepared_data = await trainer.prepare_training_data(training_file)
            
            # Fine-tune model
            success = await trainer.fine_tune_with_ollama(
                base_model=base_model,
                training_data=prepared_data["train_file"],
                model_name=model_name
            )
            
            if success:
                # Update local LLM to use new model
                from src.mcp.core.local_llm import LocalLLMConfig, LocalLLMManager
                
                new_config = LocalLLMConfig(model_name=model_name)
                new_manager = LocalLLMManager(new_config)
                
                if await new_manager.initialize():
                    self.local_llm_manager = new_manager
                    self.logger.info(f"Successfully trained and loaded model: {model_name}")
                
                return {
                    "success": True,
                    "model_name": model_name,
                    "training_samples": prepared_data["train_samples"],
                    "validation_samples": prepared_data["val_samples"],
                    "base_model": base_model
                }
            else:
                return {"success": False, "error": "Model training failed"}
                
        except Exception as e:
            self.logger.error(f"Training failed: {e}")
            return {"success": False, "error": str(e)}

# Global hybrid agent instance
hybrid_agent = None

async def get_hybrid_agent(api_key: str = None) -> HybridAgent:
    """Get the global hybrid agent instance"""
    global hybrid_agent
    
    if hybrid_agent is None:
        hybrid_agent = HybridAgent(api_key)
        await hybrid_agent.initialize()
    
    return hybrid_agent 