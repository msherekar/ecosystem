"""
Configuration-driven agent system for scalable bioinformatics analysis.
This allows adding new techniques without modifying core agent code.
"""

from typing import Dict, List, Any
import yaml
import json
from pathlib import Path

class AgentConfig:
    """Configuration manager for agent behavior"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or "config/agent_config.yaml"
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    return yaml.safe_load(f)
        except Exception as e:
            print(f"Warning: Could not load agent config: {e}")
        
        # Return default configuration
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Default agent configuration"""
        return {
            "agent": {
                "model": "openai/gpt-4",
                "temperature": 0.1,
                "max_tokens": 2000,
                "system_prompt_template": """
                You are an intelligent bioinformatics assistant for {analysis_type} analysis.
                
                Current Context:
                {context}
                
                Available Tools:
                {tools}
                
                Guidelines:
                {guidelines}
                """
            },
            "analysis_types": {
                "scrnaseq": {
                    "name": "Single-cell RNA sequencing",
                    "description": "Analysis of gene expression in individual cells",
                    "guidelines": [
                        "Follow the standard scRNA-seq pipeline order",
                        "Always suggest the next logical step",
                        "Interpret biological significance of results",
                        "Focus on cell type identification and differential expression"
                    ],
                    "common_commands": {
                        "advance": ["advance_scrnaseq_step"],
                        "analyze": ["analyze_plots", "get_plot_details"],
                        "insights": ["get_scrnaseq_insights"]
                    }
                },
                "rnaseq": {
                    "name": "Bulk RNA sequencing", 
                    "description": "Analysis of gene expression in bulk tissue samples",
                    "guidelines": [
                        "Focus on differential expression analysis",
                        "Emphasize pathway enrichment results",
                        "Consider experimental design and batch effects"
                    ],
                    "common_commands": {
                        "run": ["run_rnaseq"],
                        "analyze": ["analyze_plots"],
                        "insights": ["get_rnaseq_insights"]
                    }
                }
            },
            "response_templates": {
                "step_completion": "✅ {step_name} completed successfully. {insights}. Next, I recommend {next_action}.",
                "error": "❌ Error in {step_name}: {error_message}. Please {suggested_fix}.",
                "suggestion": "Based on your {analysis_type} data, I suggest {action} because {reason}."
            }
        }
    
    def get_analysis_config(self, analysis_type: str) -> Dict[str, Any]:
        """Get configuration for specific analysis type"""
        return self.config.get("analysis_types", {}).get(analysis_type, {})
    
    def get_system_prompt(self, analysis_type: str, context: str, tools: List[str]) -> str:
        """Generate dynamic system prompt"""
        analysis_config = self.get_analysis_config(analysis_type)
        
        template = self.config["agent"]["system_prompt_template"]
        guidelines = "\n".join(f"- {g}" for g in analysis_config.get("guidelines", []))
        tools_list = "\n".join(f"- {t}" for t in tools)
        
        return template.format(
            analysis_type=analysis_config.get("name", analysis_type),
            context=context,
            tools=tools_list,
            guidelines=guidelines
        )
    
    def get_command_mapping(self, analysis_type: str) -> Dict[str, List[str]]:
        """Get command to tool mapping for analysis type"""
        analysis_config = self.get_analysis_config(analysis_type)
        return analysis_config.get("common_commands", {})
    
    def save_config(self):
        """Save current configuration to file"""
        config_dir = Path(self.config_path).parent
        config_dir.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)

# Global configuration instance
agent_config = AgentConfig() 