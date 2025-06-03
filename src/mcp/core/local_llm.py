"""
Local LLM Integration for MCP System
Supports Ollama and other local LLM deployments
"""

import json
import asyncio
import requests
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import logging
from pathlib import Path
import subprocess
import time

@dataclass
class LocalLLMConfig:
    """Configuration for local LLM deployment"""
    model_name: str
    base_url: str = "http://localhost:11434"  # Default Ollama URL
    api_format: str = "ollama"  # ollama, openai, custom
    max_tokens: int = 4000
    temperature: float = 0.3
    timeout: int = 60
    context_window: int = 8192

class LocalLLMManager:
    """Manages local LLM deployments and inference"""
    
    def __init__(self, config: LocalLLMConfig):
        self.config = config
        self.logger = logging.getLogger("local_llm")
        self.is_available = False
        self.model_info = {}
        
    async def initialize(self) -> bool:
        """Initialize and check local LLM availability"""
        try:
            if self.config.api_format == "ollama":
                return await self._check_ollama_availability()
            elif self.config.api_format == "openai":
                return await self._check_openai_compatible()
            else:
                self.logger.warning(f"Unsupported API format: {self.config.api_format}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to initialize local LLM: {e}")
            return False
    
    async def _check_ollama_availability(self) -> bool:
        """Check if Ollama is running and model is available"""
        try:
            # Check if Ollama is running
            response = requests.get(f"{self.config.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                self.logger.warning("Ollama server not responding")
                return False
            
            # Check if our model is available
            models = response.json().get("models", [])
            model_names = [model["name"] for model in models]
            
            if self.config.model_name not in model_names:
                self.logger.warning(f"Model {self.config.model_name} not found in Ollama. Available: {model_names}")
                
                # Try to pull the model
                if await self._pull_ollama_model():
                    self.logger.info(f"Successfully pulled model {self.config.model_name}")
                else:
                    return False
            
            # Get model info
            for model in models:
                if model["name"] == self.config.model_name:
                    self.model_info = model
                    break
            
            self.is_available = True
            self.logger.info(f"Ollama model {self.config.model_name} is available")
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Ollama not available: {e}")
            return False
    
    async def _pull_ollama_model(self) -> bool:
        """Pull a model in Ollama"""
        try:
            self.logger.info(f"Pulling Ollama model: {self.config.model_name}")
            
            response = requests.post(
                f"{self.config.base_url}/api/pull",
                json={"name": self.config.model_name},
                stream=True,
                timeout=300  # 5 minutes for model download
            )
            
            if response.status_code == 200:
                # Stream the download progress
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        if "status" in data:
                            self.logger.info(f"Pull status: {data['status']}")
                        if data.get("status") == "success":
                            return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to pull model: {e}")
            return False
    
    async def _check_openai_compatible(self) -> bool:
        """Check OpenAI-compatible API"""
        try:
            response = requests.get(f"{self.config.base_url}/v1/models", timeout=5)
            if response.status_code == 200:
                models = response.json().get("data", [])
                model_ids = [model["id"] for model in models]
                
                if self.config.model_name in model_ids:
                    self.is_available = True
                    return True
                else:
                    self.logger.warning(f"Model {self.config.model_name} not found. Available: {model_ids}")
            
            return False
            
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"OpenAI-compatible API not available: {e}")
            return False
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response using local LLM"""
        
        if not self.is_available:
            raise RuntimeError("Local LLM not available")
        
        try:
            if self.config.api_format == "ollama":
                return await self._generate_ollama_response(messages, tools, **kwargs)
            elif self.config.api_format == "openai":
                return await self._generate_openai_response(messages, tools, **kwargs)
            else:
                raise ValueError(f"Unsupported API format: {self.config.api_format}")
                
        except Exception as e:
            self.logger.error(f"Failed to generate response: {e}")
            raise
    
    async def _generate_ollama_response(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response using Ollama API"""
        
        # Convert messages to Ollama format
        prompt = self._format_messages_for_ollama(messages, tools)
        
        payload = {
            "model": self.config.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
            }
        }
        
        response = requests.post(
            f"{self.config.base_url}/api/generate",
            json=payload,
            timeout=self.config.timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "choices": [{
                    "message": {
                        "content": result.get("response", ""),
                        "role": "assistant"
                    }
                }],
                "usage": {
                    "prompt_tokens": result.get("prompt_eval_count", 0),
                    "completion_tokens": result.get("eval_count", 0),
                    "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0)
                },
                "model": self.config.model_name
            }
        else:
            raise RuntimeError(f"Ollama API error: {response.status_code} - {response.text}")
    
    async def _generate_openai_response(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response using OpenAI-compatible API"""
        
        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = kwargs.get("tool_choice", "auto")
        
        response = requests.post(
            f"{self.config.base_url}/v1/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=self.config.timeout
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise RuntimeError(f"OpenAI API error: {response.status_code} - {response.text}")
    
    def _format_messages_for_ollama(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Format messages for Ollama prompt"""
        
        prompt_parts = []
        
        # Add system message if present
        system_msg = None
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
                break
        
        if system_msg:
            prompt_parts.append(f"System: {system_msg}\n")
        
        # Add tools information if available
        if tools:
            tools_desc = "Available tools:\n"
            for tool in tools:
                func = tool.get("function", {})
                tools_desc += f"- {func.get('name', 'unknown')}: {func.get('description', 'No description')}\n"
            prompt_parts.append(tools_desc + "\n")
        
        # Add conversation history
        for msg in messages:
            if msg["role"] == "system":
                continue  # Already handled
            elif msg["role"] == "user":
                prompt_parts.append(f"Human: {msg['content']}\n")
            elif msg["role"] == "assistant":
                prompt_parts.append(f"Assistant: {msg['content']}\n")
        
        prompt_parts.append("Assistant: ")
        
        return "".join(prompt_parts)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        return {
            "model_name": self.config.model_name,
            "api_format": self.config.api_format,
            "base_url": self.config.base_url,
            "is_available": self.is_available,
            "model_info": self.model_info,
            "config": {
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "context_window": self.config.context_window
            }
        }

class LocalLLMTrainer:
    """Handles training and fine-tuning of local models"""
    
    def __init__(self, training_data_dir: str = "data/training"):
        self.training_data_dir = Path(training_data_dir)
        self.logger = logging.getLogger("local_llm_trainer")
    
    async def prepare_training_data(
        self,
        source_file: str,
        output_format: str = "alpaca",
        validation_split: float = 0.1
    ) -> Dict[str, str]:
        """Prepare training data for fine-tuning"""
        
        try:
            source_path = Path(source_file)
            if not source_path.exists():
                raise FileNotFoundError(f"Training data file not found: {source_file}")
            
            # Load training data
            with open(source_path, 'r') as f:
                if source_path.suffix == '.jsonl':
                    data = [json.loads(line) for line in f]
                else:
                    data = json.load(f)
            
            # Split data
            split_idx = int(len(data) * (1 - validation_split))
            train_data = data[:split_idx]
            val_data = data[split_idx:]
            
            # Save formatted data
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            train_file = self.training_data_dir / f"train_{output_format}_{timestamp}.json"
            val_file = self.training_data_dir / f"val_{output_format}_{timestamp}.json"
            
            with open(train_file, 'w') as f:
                json.dump(train_data, f, indent=2)
            
            with open(val_file, 'w') as f:
                json.dump(val_data, f, indent=2)
            
            self.logger.info(f"Prepared training data: {len(train_data)} train, {len(val_data)} validation samples")
            
            return {
                "train_file": str(train_file),
                "val_file": str(val_file),
                "train_samples": len(train_data),
                "val_samples": len(val_data)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to prepare training data: {e}")
            raise
    
    async def create_ollama_modelfile(
        self,
        base_model: str,
        training_data: str,
        model_name: str,
        system_prompt: str = None
    ) -> str:
        """Create Ollama Modelfile for fine-tuning"""
        
        modelfile_content = f"""FROM {base_model}

# Set custom system prompt for bioinformatics
SYSTEM \"\"\"You are an expert bioinformatics assistant specializing in genomics data analysis. You help users with:
- Single-cell RNA sequencing (scRNA-seq) analysis
- Bulk RNA sequencing analysis  
- Quality control and preprocessing
- Statistical analysis and visualization
- Biological interpretation of results

Provide accurate, helpful responses that guide users through their analysis workflows.\"\"\"

# Set parameters for better bioinformatics responses
PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_predict 2048

# Custom template for bioinformatics context
TEMPLATE \"\"\"{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
{{ .Response }}<|im_end|>
\"\"\"
"""
        
        if system_prompt:
            modelfile_content = modelfile_content.replace(
                "You are an expert bioinformatics assistant...",
                system_prompt
            )
        
        # Save Modelfile
        modelfile_path = self.training_data_dir / f"Modelfile_{model_name}"
        with open(modelfile_path, 'w') as f:
            f.write(modelfile_content)
        
        self.logger.info(f"Created Modelfile: {modelfile_path}")
        return str(modelfile_path)
    
    async def fine_tune_with_ollama(
        self,
        base_model: str,
        training_data: str,
        model_name: str,
        system_prompt: str = None
    ) -> bool:
        """Fine-tune a model using Ollama"""
        
        try:
            # Create Modelfile
            modelfile_path = await self.create_ollama_modelfile(
                base_model, training_data, model_name, system_prompt
            )
            
            # Create model with Ollama
            cmd = ["ollama", "create", model_name, "-f", modelfile_path]
            
            self.logger.info(f"Creating Ollama model: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes
            )
            
            if result.returncode == 0:
                self.logger.info(f"Successfully created model: {model_name}")
                return True
            else:
                self.logger.error(f"Failed to create model: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Fine-tuning failed: {e}")
            return False

# Recommended models for different use cases
RECOMMENDED_MODELS = {
    "lightweight": {
        "model": "llama3.2:3b",
        "description": "Fast, lightweight model for basic queries",
        "memory_gb": 4
    },
    "balanced": {
        "model": "llama3.1:8b", 
        "description": "Good balance of performance and resource usage",
        "memory_gb": 8
    },
    "high_performance": {
        "model": "llama3.1:70b",
        "description": "Best performance for complex bioinformatics tasks",
        "memory_gb": 64
    },
    "code_specialized": {
        "model": "codellama:13b",
        "description": "Specialized for code generation and analysis scripts",
        "memory_gb": 16
    }
}

async def setup_local_llm(
    model_choice: str = "balanced",
    custom_model: str = None
) -> LocalLLMManager:
    """Setup and initialize local LLM"""
    
    if custom_model:
        model_name = custom_model
    else:
        model_name = RECOMMENDED_MODELS[model_choice]["model"]
    
    config = LocalLLMConfig(
        model_name=model_name,
        base_url="http://localhost:11434",
        api_format="ollama"
    )
    
    manager = LocalLLMManager(config)
    
    if await manager.initialize():
        return manager
    else:
        raise RuntimeError(f"Failed to initialize local LLM: {model_name}")

# Global local LLM manager
local_llm_manager = None

async def get_local_llm_manager() -> Optional[LocalLLMManager]:
    """Get the global local LLM manager if available"""
    global local_llm_manager
    
    if local_llm_manager is None:
        try:
            local_llm_manager = await setup_local_llm()
        except Exception as e:
            logging.getLogger("local_llm").warning(f"Local LLM not available: {e}")
            return None
    
    return local_llm_manager 