"""
Local LLM Provider
Handles local LLM services (Ollama, local models, etc.)
"""

import time
import streamlit as st
from typing import Dict, List, Any, Optional, Tuple
from .base_provider import BaseLLMProvider, ProviderType, ProviderStatus
from src.mcp.core.local_llm import get_local_llm_manager, LocalLLMManager
from src.mcp.core.training_collector import get_training_collector


class LocalLLMProvider(BaseLLMProvider):
    """Provider for local LLM services (Ollama, etc.)"""
    
    def __init__(self):
        super().__init__(ProviderType.LOCAL)
        self.local_llm_manager: Optional[LocalLLMManager] = None
        self.training_collector = None
        
        # Local provider specific configuration
        self.config.update({
            "model_name": "llama3.1:8b",
            "max_tokens": 4096,
            "temperature": 0.7,
            "collect_training_data": True
        })
    
    async def initialize(self) -> bool:
        """Initialize local LLM provider"""
        try:
            self.status = ProviderStatus.INITIALIZING
            
            # Initialize training collector
            try:
                self.training_collector = await get_training_collector()
            except Exception as e:
                self.logger.warning(f"Training collector not available: {e}")
            
            # Initialize local LLM manager
            try:
                self.local_llm_manager = await get_local_llm_manager()
                if self.local_llm_manager and self.local_llm_manager.is_available:
                    self.status = ProviderStatus.AVAILABLE
                    self.logger.info("Local LLM provider initialized successfully")
                    return True
                else:
                    self.status = ProviderStatus.UNAVAILABLE
                    self.logger.warning("Local LLM not available")
                    return False
            except Exception as e:
                self.status = ProviderStatus.ERROR
                self.logger.error(f"Failed to initialize local LLM: {e}")
                return False
                
        except Exception as e:
            self.status = ProviderStatus.ERROR
            self.logger.error(f"Failed to initialize local LLM provider: {e}")
            return False
    
    async def chat(self, user_message: str, context: Dict[str, Any] = None) -> Tuple[str, List[str]]:
        """Generate response using local LLM"""
        if not self.is_available():
            raise RuntimeError("Local LLM provider not available")
        
        start_time = time.time()
        
        try:
            # Build messages similar to external agent
            messages = self._build_messages(user_message, context)
            
            # Generate response
            response_data = await self.local_llm_manager.generate_response(messages)
            response_content = response_data["choices"][0]["message"]["content"]
            
            # Calculate metrics
            response_time = time.time() - start_time
            cost = self.estimate_cost(user_message, response_content)
            
            # Collect training data if enabled
            if self.config.get("collect_training_data", True) and self.training_collector:
                try:
                    await self.training_collector.collect_conversation_turn(
                        user_message=user_message,
                        assistant_response=response_content,
                        tool_results=[],
                        success=True
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to collect training data: {e}")
            
            # Update metrics
            self.update_metrics(success=True, response_time=response_time, cost=cost)
            
            return response_content, []
            
        except Exception as e:
            response_time = time.time() - start_time
            self.update_metrics(success=False, response_time=response_time)
            
            self.logger.error(f"Local LLM chat failed: {e}")
            raise
    
    def _build_messages(self, user_message: str, context: Dict[str, Any] = None) -> List[Dict[str, str]]:
        """Build messages for local LLM similar to external agent"""
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
        
        # Add conversation history from Streamlit if available
        if "messages" in st.session_state:
            recent_messages = st.session_state.messages[-4:] if len(st.session_state.messages) > 4 else st.session_state.messages
            for msg in recent_messages[:-1]:  # Exclude current message
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # Add current message
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    def is_available(self) -> bool:
        """Check if local provider is available"""
        return (self.status == ProviderStatus.AVAILABLE and 
                self.local_llm_manager is not None and 
                self.local_llm_manager.is_available)
    
    def estimate_cost(self, user_message: str, response: str = "") -> float:
        """Estimate cost for local LLM usage (usually free or very low)"""
        # Local models typically have no direct cost, but we can estimate 
        # computational cost or electricity cost
        
        # For now, return 0 as local models are typically free to use
        # Could be extended to estimate electricity/compute costs
        return 0.0
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return local provider capabilities"""
        model_info = {}
        if self.local_llm_manager:
            model_info = self.local_llm_manager.get_model_info()
        
        return {
            "provider_type": self.provider_type.value,
            "supports_streaming": False,
            "max_context_length": 8192,  # Typical for local models
            "supports_function_calling": False,
            "supports_vision": False,
            "cost_per_request": 0.0,
            "latency": "low",
            "quality": "medium",
            "specialized_domains": ["general", "bioinformatics"],
            "model_info": model_info
        }
    
    async def train_model(
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
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get usage summary for local provider"""
        metrics = self.get_metrics()
        
        return {
            "provider": "local",
            "total_cost": 0.0,  # Local models are typically free
            "requests": metrics["total_requests"],
            "success_rate": metrics["success_rate"],
            "avg_response_time": metrics["average_response_time"],
            "cost_savings": "100%"  # Compared to external APIs
        }


if __name__ == "__main__":
    """Test the local provider individually"""
    import asyncio
    
    async def test_local_provider():
        print("🧪 Testing LocalLLMProvider...")
        
        # Test initialization
        provider = LocalLLMProvider()
        init_success = await provider.initialize()
        print(f"✅ Initialization: {init_success} (may fail if Ollama not available)")
        
        # Test availability
        available = provider.is_available()
        print(f"✅ Availability: {available}")
        
        # Test capabilities
        capabilities = provider.get_capabilities()
        print(f"✅ Capabilities: {capabilities['provider_type']}")
        print(f"   - Max context: {capabilities['max_context_length']}")
        print(f"   - Cost per request: ${capabilities['cost_per_request']}")
        
        # Test cost estimation (should be 0 for local)
        cost = provider.estimate_cost("Hello world", "Hi there!")
        print(f"✅ Cost estimation: ${cost} (expected: $0.0)")
        
        # Test configuration
        provider.configure(
            model_name="llama3.1:8b",
            temperature=0.7,
            collect_training_data=False
        )
        print(f"✅ Configuration: {list(provider.config.keys())}")
        
        # Test chat if available
        if available:
            try:
                response, flags = await provider.chat("Say hello briefly")
                print(f"✅ Chat response: {response[:50]}...")
            except Exception as e:
                print(f"⚠️  Chat failed: {e}")
        else:
            print("ℹ️  Skipping chat test (provider not available)")
        
        # Test usage summary
        summary = provider.get_usage_summary()
        print(f"✅ Usage summary: {summary}")
        
        # Test metrics
        metrics = provider.get_metrics()
        print(f"✅ Metrics: requests={metrics['total_requests']}, success_rate={metrics['success_rate']}")
        
        print("🎉 Local provider tests completed!")
    
    # Run tests
    asyncio.run(test_local_provider())