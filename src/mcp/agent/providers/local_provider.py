"""
Local LLM Provider
Handles local LLM services with model management, resource monitoring, and security.
Enhanced for scalability and Electron integration.
"""

import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from pydantic import Field
import psutil

from .base_provider import BaseLLMProvider, ProviderType, ProviderStatus, ProviderConfig
from src.mcp.core.local_llm import get_local_llm_manager, LocalLLMManager, LocalLLMConfig
from src.mcp.core.training_collector import get_training_collector


class LocalProviderConfig(ProviderConfig):
    """Configuration for local LLM providers"""
    model_name: str = "llama3.1:8b"
    collect_training_data: bool = True
    gpu_memory_fraction: float = Field(default=0.8, gt=0, le=1)
    resource_monitoring: bool = True
    model_cache_size: int = Field(default=3, gt=0)
    security_sandbox: bool = True


class ResourceMonitor:
    """Monitor system resources for local LLM usage"""
    
    def __init__(self):
        self.stats = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "gpu_usage": 0.0 if self._has_gpu() else None,
            "last_updated": 0.0
        }
        self._monitoring = False
        self._monitor_task = None
    
    def _has_gpu(self) -> bool:
        """Check if GPU is available"""
        try:
            import GPUtil
            return len(GPUtil.getGPUs()) > 0
        except ImportError:
            return False
    
    async def start_monitoring(self):
        """Start resource monitoring"""
        if not self._monitoring:
            self._monitoring = True
            self._monitor_task = asyncio.create_task(self._monitor_loop())
    
    async def stop_monitoring(self):
        """Stop resource monitoring"""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_loop(self):
        """Resource monitoring loop"""
        while self._monitoring:
            try:
                self.stats["cpu_usage"] = psutil.cpu_percent(interval=1)
                self.stats["memory_usage"] = psutil.virtual_memory().percent
                self.stats["last_updated"] = time.time()
                
                if self._has_gpu():
                    import GPUtil
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        self.stats["gpu_usage"] = gpus[0].load * 100
                
                await asyncio.sleep(5)
            except Exception:
                await asyncio.sleep(5)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current resource statistics"""
        return self.stats.copy()


class LocalLLMProvider(BaseLLMProvider):
    """Enhanced local LLM provider with model management and resource monitoring"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(ProviderType.LOCAL, config or {})
        self.local_llm_manager: Optional[LocalLLMManager] = None
        self.training_collector = None
        
        # Model management
        self._model_cache = {}
        self._current_model = None
        self._max_cache_size = self.config.model_cache_size
        
        # Resource monitoring
        self.resource_monitor = ResourceMonitor() if self.config.resource_monitoring else None
    
    def _get_config_class(self):
        return LocalProviderConfig
    
    async def initialize(self) -> bool:
        """Initialize local LLM provider with enhanced capabilities"""
        try:
            self.status = ProviderStatus.INITIALIZING
            
            # Start resource monitoring
            if self.resource_monitor:
                await self.resource_monitor.start_monitoring()
            
            # Initialize training collector
            try:
                self.training_collector = await get_training_collector()
            except Exception as e:
                self.logger.warning("Training collector not available", error=str(e))
            
            # Initialize local LLM manager
            self.local_llm_manager = await get_local_llm_manager()
            if self.local_llm_manager and self.local_llm_manager.is_available:
                self._current_model = self.config.model_name
                self.status = ProviderStatus.AVAILABLE
                self.logger.info("Local LLM provider initialized successfully")
                return True
            else:
                self.status = ProviderStatus.UNAVAILABLE
                self.logger.info("Local LLM not available (this is normal if Ollama is not installed)")
                # Return True to indicate successful initialization, even though service is unavailable
                # This prevents the entire system from failing when Ollama isn't installed
                return True
                
        except Exception as e:
            self.status = ProviderStatus.ERROR
            self.logger.error("Failed to initialize local LLM provider", error=str(e))
            return False
    
    async def chat(self, user_message: str, context: Dict[str, Any] = None) -> Tuple[str, List[str]]:
        """Generate response using local LLM with security and monitoring"""
        if not self.is_available():
            raise RuntimeError("Local LLM provider not available")
        
        # Security: sanitize input
        if self.config.security_sandbox:
            user_message = self._sanitize_input(user_message)
        
        start_time = time.time()
        
        try:
            # Build messages and generate response
            messages = self._build_messages(user_message, context)
            response_data = await self.local_llm_manager.generate_response(messages)
            response_content = response_data["choices"][0]["message"]["content"]
            
            # Collect training data if enabled
            if self.config.collect_training_data and self.training_collector:
                try:
                    await self.training_collector.collect_conversation_turn(
                        user_message=user_message,
                        assistant_response=response_content,
                        tool_results=[],
                        success=True
                    )
                except Exception as e:
                    self.logger.warning("Failed to collect training data", error=str(e))
            
            # Update metrics
            response_time = time.time() - start_time
            self.update_metrics(success=True, response_time=response_time, cost=0.0)
            
            return response_content, []
            
        except Exception as e:
            response_time = time.time() - start_time
            self.update_metrics(success=False, response_time=response_time)
            self.logger.error("Local LLM chat failed", error=str(e))
            raise
    
    def _sanitize_input(self, user_message: str) -> str:
        """Pass the user's message through unchanged.

        This used to run `str.replace` over ["import ", "exec(", "eval(",
        "__import__"], which provided no security and actively broke the
        product:

        - It filtered *prompt text*, not executed code. Nothing here ever
          reaches an interpreter; code execution is isolated in
          `backend.sandbox`, which is where the real boundary is.
        - As a denylist it was trivially evaded (`exec (`, `__imp` + `ort__`,
          `importlib`, unicode escapes), so it deterred nobody.
        - It mangled ordinary questions. "How do I import my counts matrix?"
          became "How do I [FILTERED:import] my counts matrix?", and the
          model answered the corrupted question.

        Kept as a no-op passthrough so existing call sites keep working.
        """
        return user_message
    
    def _build_messages(self, user_message: str, context: Dict[str, Any] = None) -> List[Dict[str, str]]:
        """Build messages for local LLM"""
        messages = [{
            "role": "system",
            "content": "You are an expert bioinformatics assistant. Provide accurate, helpful responses for genomics analysis."
        }]
        
        # Add context if available
        if context and "conversation_history" in context:
            for msg in context["conversation_history"][-4:]:
                messages.append(msg)
        
        messages.append({"role": "user", "content": user_message})
        return messages
    
    async def switch_model(self, model_name: str) -> bool:
        """Switch to a different local model with caching"""
        try:
            if model_name in self._model_cache:
                self.local_llm_manager = self._model_cache[model_name]
                self._current_model = model_name
                return True
            
            # Create new manager
            config = LocalLLMConfig(model_name=model_name)
            manager = LocalLLMManager(config)
            
            if await manager.initialize():
                # Manage cache size
                if len(self._model_cache) >= self._max_cache_size:
                    # Remove least recently used model
                    oldest_model = next(iter(self._model_cache))
                    del self._model_cache[oldest_model]
                
                self._model_cache[model_name] = manager
                self.local_llm_manager = manager
                self._current_model = model_name
                self.logger.info("Switched to model", model=model_name)
                return True
            else:
                self.logger.error("Failed to initialize model", model=model_name)
                return False
                
        except Exception as e:
            self.logger.error("Error switching model", model=model_name, error=str(e))
            return False
    
    def is_available(self) -> bool:
        """Check if local provider is available"""
        return (self.status == ProviderStatus.AVAILABLE and 
                self.local_llm_manager is not None and 
                self.local_llm_manager.is_available)
    
    def estimate_cost(self, user_message: str, response: str = "") -> float:
        """Local models are typically free"""
        return 0.0
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return local provider capabilities"""
        model_info = {}
        if self.local_llm_manager:
            model_info = self.local_llm_manager.get_model_info()
        
        return {
            "provider_type": self.provider_type.value,
            "supports_streaming": False,
            "max_context_length": 8192,
            "supports_function_calling": False,
            "supports_vision": False,
            "cost_per_request": 0.0,
            "latency": "low",
            "quality": "medium",
            "specialized_domains": ["general", "bioinformatics"],
            "current_model": self._current_model,
            "cached_models": list(self._model_cache.keys()),
            "model_info": model_info,
            "resource_monitoring": self.config.resource_monitoring,
            "security_sandbox": self.config.security_sandbox
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        try:
            health_data = {
                "healthy": self.is_available(),
                "current_model": self._current_model,
                "cached_models_count": len(self._model_cache)
            }
            
            # Add resource stats
            if self.resource_monitor:
                health_data["resources"] = self.resource_monitor.get_stats()
            
            # Test model response
            if self.is_available():
                test_start = time.time()
                await self.chat("Test")
                health_data["test_response_time"] = time.time() - test_start
            
            return health_data
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    def list_available_models(self) -> List[str]:
        """List available local models"""
        if self.local_llm_manager:
            return self.local_llm_manager.list_models()
        return []
    
    async def cleanup(self):
        """Clean up local provider resources"""
        if self.resource_monitor:
            await self.resource_monitor.stop_monitoring()
        
        # Clear model cache
        self._model_cache.clear()
        
        await super().cleanup()
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get usage summary for local provider"""
        metrics = self.get_metrics()
        
        summary = {
            "provider": "local",
            "total_cost": 0.0,
            "requests": metrics["total_requests"],
            "success_rate": metrics["success_rate"],
            "avg_response_time": metrics["average_response_time"],
            "cost_savings": "100%",
            "current_model": self._current_model,
            "cached_models": len(self._model_cache)
        }
        
        # Add resource usage if monitoring
        if self.resource_monitor:
            summary["resources"] = self.resource_monitor.get_stats()
        
        return summary
    
    def get_electron_bridge_data(self) -> Dict[str, Any]:
        """Get data for Electron bridge with local-specific info"""
        base_data = super().get_electron_bridge_data()
        base_data.update({
            "connectionStatus": "local",
            "currentModel": self._current_model,
            "cachedModels": list(self._model_cache.keys()),
            "availableModels": self.list_available_models(),
            "costPerRequest": 0.0,
            "resourceMonitoring": self.config.resource_monitoring,
            "securitySandbox": self.config.security_sandbox
        })
        
        # Add resource stats
        if self.resource_monitor:
            base_data["resourceStats"] = self.resource_monitor.get_stats()
        
        return base_data


async def main():
    """Main function for testing enhanced local provider"""
    print("🧪 Testing Enhanced LocalLLMProvider...")
    
    # Test initialization
    config = {
        "model_name": "llama3.1:8b",
        "collect_training_data": False,
        "resource_monitoring": True,
        "security_sandbox": True,
        "model_cache_size": 2
    }
    
    provider = LocalLLMProvider(config)
    init_success = await provider.initialize()
    print(f"✅ Initialization: {init_success} (may fail if Ollama not available)")
    
    # Test configuration
    print(f"✅ Configuration: {provider.config.model_name}")
    print(f"   - Security sandbox: {provider.config.security_sandbox}")
    print(f"   - Resource monitoring: {provider.config.resource_monitoring}")
    
    # Test capabilities
    capabilities = provider.get_capabilities()
    print(f"✅ Capabilities: {capabilities['provider_type']}")
    print(f"   - Current model: {capabilities['current_model']}")
    print(f"   - Cost per request: ${capabilities['cost_per_request']}")
    
    # Test health check
    health = await provider.get_health_status()
    print(f"✅ Health status: {health['status']}")
    
    # Test resource monitoring
    if provider.resource_monitor:
        resource_stats = provider.resource_monitor.get_stats()
        print(f"✅ Resource stats: CPU {resource_stats['cpu_usage']:.1f}%")
    
    # Test security sanitization
    dangerous_input = "import os; exec('rm -rf /')"
    sanitized = provider._sanitize_input(dangerous_input)
    print(f"✅ Security: Input sanitized: {sanitized != dangerous_input}")
    
    # Test model switching (if available)
    if provider.is_available():
        models = provider.list_available_models()
        print(f"✅ Available models: {len(models)} models")
        
        # Test model caching
        current_model = provider._current_model
        print(f"✅ Current model: {current_model}")
    
    # Test usage summary
    summary = provider.get_usage_summary()
    print(f"✅ Usage summary: {summary['provider']}")
    
    # Test Electron bridge data
    bridge_data = provider.get_electron_bridge_data()
    print(f"✅ Electron bridge keys: {list(bridge_data.keys())}")
    
    # Cleanup
    await provider.cleanup()
    
    print("🎉 Enhanced local provider tests completed!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())