"""
Utility functions for training data collection.
"""

import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Protocol
from abc import ABC, abstractmethod

class SessionProvider(Protocol):
    """Protocol for session state providers (e.g., Streamlit)"""
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from session state"""
        ...
    
    def set(self, key: str, value: Any) -> None:
        """Set value in session state"""
        ...

class UserAnonymizer:
    """Handles user anonymization for privacy"""
    
    def __init__(self, salt: str = None):
        self.salt = salt or "training_data_salt_2024"
        self.logger = logging.getLogger("user_anonymizer")
    
    def anonymize_user_id(self, user_identifier: str) -> str:
        """Create anonymized but consistent user ID"""
        if not user_identifier:
            return "anonymous"
        
        # Create consistent hash for user
        salted_id = f"{user_identifier}_{self.salt}"
        return hashlib.sha256(salted_id.encode()).hexdigest()[:16]
    
    def generate_session_id(self, session_data: str = None) -> str:
        """Generate a unique session ID"""
        if not session_data:
            session_data = f"{datetime.now().isoformat()}_{id(object())}"
        
        return hashlib.md5(session_data.encode()).hexdigest()[:12]

class ContextExtractor:
    """Extracts relevant context from session state"""
    
    def __init__(self, session_provider: SessionProvider = None):
        self.session_provider = session_provider
        self.logger = logging.getLogger("context_extractor")
    
    def extract_analysis_context(self) -> Dict[str, Any]:
        """Extract analysis-specific context"""
        if not self.session_provider:
            return {}
        
        context = {
            "analysis_state": {},
            "available_tools": [],
            "pipeline_progress": {},
            "data_characteristics": {}
        }
        
        try:
            # Data characteristics
            anndata = self.session_provider.get("anndata")
            if anndata is not None:
                context["data_characteristics"] = {
                    "n_cells": getattr(anndata, 'n_obs', 0),
                    "n_genes": getattr(anndata, 'n_vars', 0),
                    "has_raw": hasattr(anndata, 'raw') and anndata.raw is not None
                }
            
            # Pipeline progress
            pipeline_flags = [
                "qc_done", "filtering_done", "normalization_done", 
                "dimred_done", "clustering_done", "dea_done"
            ]
            context["pipeline_progress"] = {
                flag: self.session_provider.get(flag, False) 
                for flag in pipeline_flags
            }
            
            # Current step
            context["current_step"] = self.session_provider.get("scrna_current_step", "unknown")
            
            # Analysis parameters
            context["analysis_params"] = self._extract_analysis_parameters()
            
        except Exception as e:
            self.logger.error(f"Failed to extract context: {e}")
        
        return context
    
    def _extract_analysis_parameters(self) -> Dict[str, Any]:
        """Extract analysis parameters from session"""
        if not self.session_provider:
            return {}
        
        params = {}
        
        # Common parameters
        param_keys = [
            "n_top_genes", "min_genes", "min_cells", "max_genes", "max_cells",
            "target_sum", "n_comps", "n_neighbors", "resolution"
        ]
        
        for key in param_keys:
            value = self.session_provider.get(key)
            if value is not None:
                params[key] = value
        
        return params
    
    def determine_analysis_type(self) -> str:
        """Determine the type of analysis being performed"""
        if not self.session_provider:
            return "general"
        
        if self.session_provider.get("anndata") is not None:
            return "scrna_seq"
        elif self.session_provider.get("uploaded_df") is not None:
            return "tabular"
        elif self.session_provider.get("rna_seq_data") is not None:
            return "rna_seq"
        else:
            return "general"

class ToolUsageExtractor:
    """Extracts tool usage information from results"""
    
    def __init__(self):
        self.logger = logging.getLogger("tool_extractor")
    
    def extract_tools_used(self, tool_results: List[str]) -> List[Dict[str, Any]]:
        """Extract tool usage information from results"""
        tools = []
        
        for result in tool_results:
            try:
                tool_info = self._parse_tool_result(result)
                if tool_info:
                    tools.append(tool_info)
            except Exception as e:
                self.logger.error(f"Failed to parse tool result: {e}")
        
        return tools
    
    def _parse_tool_result(self, result: str) -> Optional[Dict[str, Any]]:
        """Parse individual tool result"""
        if not result or "Tool " not in result:
            return None
        
        parts = result.split(":", 1)
        if len(parts) != 2:
            return None
        
        tool_name = parts[0].replace("Tool ", "").strip()
        tool_output = parts[1].strip()
        
        return {
            "name": tool_name,
            "success": "failed" not in result.lower() and "error" not in result.lower(),
            "timestamp": datetime.now().isoformat(),
            "output_length": len(tool_output),
            "has_error": "error" in result.lower() or "failed" in result.lower()
        }

class StreamlitSessionProvider:
    """Streamlit-specific session provider"""
    
    def __init__(self, session_state):
        self.session_state = session_state
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from Streamlit session state"""
        return getattr(self.session_state, key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set value in Streamlit session state"""
        setattr(self.session_state, key, value)

class MockSessionProvider:
    """Mock session provider for testing"""
    
    def __init__(self, data: Dict[str, Any] = None):
        self.data = data or {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from mock session"""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set value in mock session"""
        self.data[key] = value

def create_context_extractor(session_provider: SessionProvider = None) -> ContextExtractor:
    """Factory function to create context extractor"""
    return ContextExtractor(session_provider)

def create_user_anonymizer(salt: str = None) -> UserAnonymizer:
    """Factory function to create user anonymizer"""
    return UserAnonymizer(salt)

if __name__ == "__main__":
    # Example usage
    print("Training Utilities Examples:")
    
    # User anonymization
    anonymizer = UserAnonymizer()
    user_id = anonymizer.anonymize_user_id("user@example.com")
    session_id = anonymizer.generate_session_id()
    print(f"Anonymized user ID: {user_id}")
    print(f"Session ID: {session_id}")
    
    # Context extraction with mock data
    mock_session = MockSessionProvider({
        "qc_done": True,
        "filtering_done": False,
        "scrna_current_step": "normalization",
        "n_top_genes": 2000
    })
    
    extractor = ContextExtractor(mock_session)
    context = extractor.extract_analysis_context()
    analysis_type = extractor.determine_analysis_type()
    
    print(f"Analysis type: {analysis_type}")
    print(f"Context: {context}")
    
    # Tool usage extraction
    tool_extractor = ToolUsageExtractor()
    tool_results = [
        "Tool scanpy: Successfully normalized data",
        "Tool matplotlib: Failed to create plot"
    ]
    tools_used = tool_extractor.extract_tools_used(tool_results)
    print(f"Tools used: {tools_used}") 