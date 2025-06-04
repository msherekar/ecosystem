"""
Base Handler Class

Provides common functionality for all MCP technique handlers.
This improves modularity and reduces code duplication.
"""

import logging
import streamlit as st
from typing import Any, Dict, List
from abc import ABC, abstractmethod


class BaseHandler(ABC):
    """Base class for all MCP technique handlers"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    @abstractmethod
    def get_technique_name(self) -> str:
        """Get the name of the technique this handler supports"""
        pass
    
    @abstractmethod
    def _check_data_availability(self) -> Dict[str, Any]:
        """Check if required data is available for this technique"""
        pass
    
    def _validate_parameters(self, **kwargs) -> Dict[str, Any]:
        """Validate common parameters"""
        validation_result = {"valid": True, "errors": []}
        
        # Common parameter validations
        if "resolution" in kwargs:
            resolution = kwargs["resolution"]
            if not isinstance(resolution, (int, float)) or not 0.1 <= resolution <= 2.0:
                validation_result["valid"] = False
                validation_result["errors"].append("Resolution must be between 0.1 and 2.0")
        
        if "n_neighbors" in kwargs:
            n_neighbors = kwargs["n_neighbors"]
            if not isinstance(n_neighbors, int) or not 5 <= n_neighbors <= 100:
                validation_result["valid"] = False
                validation_result["errors"].append("n_neighbors must be between 5 and 100")
        
        if "n_pcs" in kwargs:
            n_pcs = kwargs["n_pcs"]
            if not isinstance(n_pcs, int) or not 10 <= n_pcs <= 100:
                validation_result["valid"] = False
                validation_result["errors"].append("n_pcs must be between 10 and 100")
        
        return validation_result
    
    def _create_success_response(self, message: str, **additional_data) -> Dict[str, Any]:
        """Create standardized success response"""
        response = {
            "success": True,
            "message": message,
            "technique": self.get_technique_name()
        }
        response.update(additional_data)
        return response
    
    def _create_error_response(self, message: str, error_type: str = "unknown", 
                              suggestion: str = None) -> Dict[str, Any]:
        """Create standardized error response"""
        response = {
            "success": False,
            "message": message,
            "error_type": error_type,
            "technique": self.get_technique_name()
        }
        if suggestion:
            response["suggestion"] = suggestion
        return response
    
    def _log_operation(self, operation: str, **params):
        """Log operation with parameters"""
        param_str = ", ".join([f"{k}={v}" for k, v in params.items()])
        self.logger.info(f"{self.get_technique_name()} - {operation}: {param_str}")
    
    def _get_session_state_key(self, key: str) -> str:
        """Get technique-specific session state key"""
        return f"{self.get_technique_name().lower()}_{key}"
    
    def _update_progress(self, step: str, completed: bool = True):
        """Update analysis progress in session state"""
        progress_key = self._get_session_state_key("progress")
        if progress_key not in st.session_state:
            st.session_state[progress_key] = {}
        
        st.session_state[progress_key][step] = completed
        
        # Update current step
        current_step_key = self._get_session_state_key("current_step")
        st.session_state[current_step_key] = step 