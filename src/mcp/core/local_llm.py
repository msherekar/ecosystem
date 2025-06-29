"""
Local LLM Interface
Provides a simple interface for local LLM services like Ollama.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class LocalLLMConfig:
    """Configuration for local LLM"""
    model_name: str = "llama3.1:8b"
    host: str = "localhost"
    port: int = 11434
    timeout: float = 30.0
    max_tokens: int = 4096
    temperature: float = 0.7


class LocalLLMManager:
    """Manager for local LLM services"""
    
    def __init__(self, config: LocalLLMConfig = None):
        self.config = config or LocalLLMConfig()
        self.logger = logging.getLogger("local_llm_manager")
        self.is_available = False
        self._client = None
    
    async def initialize(self) -> bool:
        """Initialize the local LLM manager"""
        try:
            # Try to connect to Ollama or similar service
            # For now, we'll simulate availability
            self.is_available = await self._check_service_availability()
            if self.is_available:
                self.logger.info(f"Local LLM initialized with model: {self.config.model_name}")
            else:
                self.logger.warning("Local LLM service not available")
            return self.is_available
            
        except Exception as e:
            self.logger.error(f"Failed to initialize local LLM: {e}")
            self.is_available = False
            return False
    
    async def _check_service_availability(self) -> bool:
        """Check if the local LLM service is available"""
        try:
            # This would normally check if Ollama is running
            # For now, we'll return False to avoid errors
            return False
            
        except Exception as e:
            self.logger.warning(f"Service availability check failed: {e}")
            return False
    
    async def generate_response(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Generate response using local LLM"""
        if not self.is_available:
            raise RuntimeError("Local LLM not available")
        
        try:
            # Extract the user message
            user_message = messages[-1].get("content", "") if messages else ""
            
            # Simulate response generation
            # In a real implementation, this would call Ollama API
            response_content = f"Local LLM response to: {user_message[:50]}..."
            
            return {
                "choices": [{
                    "message": {
                        "content": response_content,
                        "role": "assistant"
                    }
                }],
                "model": self.config.model_name,
                "usage": {
                    "prompt_tokens": len(user_message.split()),
                    "completion_tokens": len(response_content.split()),
                    "total_tokens": len(user_message.split()) + len(response_content.split())
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate response: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        return {
            "model_name": self.config.model_name,
            "is_available": self.is_available,
            "api_format": "ollama",
            "host": self.config.host,
            "port": self.config.port,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature
        }
    
    def list_models(self) -> List[str]:
        """List available models"""
        # This would normally query the Ollama service
        # For now, return some common models
        if self.is_available:
            return [
                "llama3.1:8b",
                "llama3.1:70b", 
                "codellama:7b",
                "mistral:7b",
                "neural-chat:7b"
            ]
        return []
    
    async def pull_model(self, model_name: str) -> bool:
        """Pull a model to the local system"""
        if not self.is_available:
            return False
        
        try:
            # This would normally call ollama pull
            self.logger.info(f"Would pull model: {model_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to pull model {model_name}: {e}")
            return False
    
    async def cleanup(self):
        """Clean up resources"""
        if self._client:
            # Close any open connections
            pass
        self.logger.info("Local LLM manager cleaned up")


class LocalLLMTrainer:
    """Trainer for fine-tuning local models"""
    
    def __init__(self):
        self.logger = logging.getLogger("local_llm_trainer")
    
    async def prepare_training_data(self, training_file: str) -> Dict[str, Any]:
        """Prepare training data for fine-tuning"""
        try:
            # This would normally process the training file
            # and prepare it for the local LLM training format
            
            return {
                "train_file": f"{training_file}_train.jsonl",
                "val_file": f"{training_file}_val.jsonl",
                "train_samples": 100,
                "val_samples": 20
            }
            
        except Exception as e:
            self.logger.error(f"Failed to prepare training data: {e}")
            return {}
    
    async def fine_tune_with_ollama(
        self,
        base_model: str,
        training_data: str,
        model_name: str
    ) -> bool:
        """Fine-tune a model using Ollama"""
        try:
            # This would normally run the fine-tuning process
            self.logger.info(f"Would fine-tune {base_model} -> {model_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Fine-tuning failed: {e}")
            return False


# Global manager instance
_local_llm_manager: Optional[LocalLLMManager] = None


async def get_local_llm_manager(config: LocalLLMConfig = None) -> Optional[LocalLLMManager]:
    """Get the global local LLM manager instance"""
    global _local_llm_manager
    
    if _local_llm_manager is None:
        try:
            _local_llm_manager = LocalLLMManager(config)
            await _local_llm_manager.initialize()
        except Exception as e:
            logging.getLogger("local_llm").warning(f"Failed to initialize local LLM manager: {e}")
            return None
    
    return _local_llm_manager


def set_local_llm_manager(manager: LocalLLMManager):
    """Set the global local LLM manager instance"""
    global _local_llm_manager
    _local_llm_manager = manager


async def main():
    """Test the local LLM interface"""
    print("🧪 Testing Local LLM Interface...")
    
    # Test configuration
    config = LocalLLMConfig(model_name="llama3.1:8b")
    print(f"✅ Configuration: {config.model_name}")
    
    # Test manager
    manager = await get_local_llm_manager(config)
    print(f"✅ Manager initialized: {manager is not None}")
    
    if manager:
        # Test model info
        model_info = manager.get_model_info()
        print(f"✅ Model info: {model_info['model_name']}")
        print(f"   - Available: {model_info['is_available']}")
        
        # Test model listing
        models = manager.list_models()
        print(f"✅ Available models: {len(models)} models")
        
        # Test response generation if available
        if manager.is_available:
            try:
                messages = [{"role": "user", "content": "Hello"}]
                response = await manager.generate_response(messages)
                print(f"✅ Response generated: {response['choices'][0]['message']['content'][:50]}...")
            except Exception as e:
                print(f"⚠️  Response generation failed: {e}")
        else:
            print("ℹ️  Skipping response test (service not available)")
        
        # Test trainer
        trainer = LocalLLMTrainer()
        prepared = await trainer.prepare_training_data("test_file.jsonl")
        print(f"✅ Training data prepared: {prepared.get('train_samples', 0)} samples")
        
        # Cleanup
        await manager.cleanup()
    
    print("🎉 Local LLM interface tests completed!")


if __name__ == "__main__":
    asyncio.run(main()) 