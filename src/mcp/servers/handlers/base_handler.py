"""
Base Handler Class

Provides common functionality for all MCP technique handlers.
Enhanced for security, scalability, and Electron integration.
"""

import logging
import streamlit as st
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
from datetime import datetime
import uuid
import asyncio
from dataclasses import dataclass

from .security_validator import SecurityValidator
from .electron_bridge import ElectronBridge


@dataclass
class OperationResult:
    """Standardized operation result"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error_type: Optional[str] = None
    operation_id: Optional[str] = None
    timestamp: Optional[datetime] = None


class BaseHandler(ABC):
    """Base class for all MCP technique handlers"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.security_validator = SecurityValidator()
        self.electron_bridge = ElectronBridge()
        self._operation_history: List[OperationResult] = []
    
    @abstractmethod
    def get_technique_name(self) -> str:
        """Get the name of the technique this handler supports"""
        pass
    
    @abstractmethod
    def _check_data_availability(self) -> Dict[str, Any]:
        """Check if required data is available for this technique"""
        pass
    
    def _validate_parameters(self, **kwargs) -> Dict[str, Any]:
        """Validate common parameters with security checks"""
        validation_result = {"valid": True, "errors": []}
        
        # Security validation first
        security_check = self.security_validator.validate_parameters(kwargs)
        if not security_check["valid"]:
            validation_result["valid"] = False
            validation_result["errors"].extend(security_check["errors"])
            return validation_result
        
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
        operation_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        response = {
            "success": True,
            "message": message,
            "technique": self.get_technique_name(),
            "operation_id": operation_id,
            "timestamp": timestamp.isoformat()
        }
        response.update(additional_data)
        
        # Store in operation history
        result = OperationResult(
            success=True,
            message=message,
            data=additional_data,
            operation_id=operation_id,
            timestamp=timestamp
        )
        self._operation_history.append(result)
        
        # Notify Electron if available
        self.electron_bridge.notify_operation_complete(result)
        
        return response
    
    def _create_error_response(self, message: str, error_type: str = "unknown", 
                              suggestion: str = None) -> Dict[str, Any]:
        """Create standardized error response"""
        operation_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        response = {
            "success": False,
            "message": message,
            "error_type": error_type,
            "technique": self.get_technique_name(),
            "operation_id": operation_id,
            "timestamp": timestamp.isoformat()
        }
        if suggestion:
            response["suggestion"] = suggestion
        
        # Store in operation history
        result = OperationResult(
            success=False,
            message=message,
            error_type=error_type,
            operation_id=operation_id,
            timestamp=timestamp
        )
        self._operation_history.append(result)
        
        # Log error
        self.logger.error(f"{self.get_technique_name()} - {error_type}: {message}")
        
        # Notify Electron if available
        self.electron_bridge.notify_operation_error(result)
        
        return response
    
    def _log_operation(self, operation: str, **params):
        """Log operation with parameters and security audit"""
        param_str = ", ".join([f"{k}={v}" for k, v in params.items()])
        log_message = f"{self.get_technique_name()} - {operation}: {param_str}"
        
        self.logger.info(log_message)
        
        # Security audit log
        self.security_validator.audit_operation(
            technique=self.get_technique_name(),
            operation=operation,
            parameters=params
        )
    
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
        
        # Notify Electron of progress update
        self.electron_bridge.notify_progress_update(
            technique=self.get_technique_name(),
            step=step,
            completed=completed
        )
    
    def get_operation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent operation history"""
        recent_operations = self._operation_history[-limit:]
        return [
            {
                "success": op.success,
                "message": op.message,
                "operation_id": op.operation_id,
                "timestamp": op.timestamp.isoformat() if op.timestamp else None,
                "error_type": op.error_type
            }
            for op in recent_operations
        ]
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for this handler"""
        try:
            data_check = self._check_data_availability()
            return {
                "healthy": True,
                "technique": self.get_technique_name(),
                "data_available": data_check.get("available", False),
                "last_operation": self._operation_history[-1].timestamp.isoformat() if self._operation_history else None
            }
        except Exception as e:
            return {
                "healthy": False,
                "technique": self.get_technique_name(),
                "error": str(e)
            }


def main():
    """Test base handler functionality"""
    import logging
    
    # Create test handler implementation
    class TestHandler(BaseHandler):
        def get_technique_name(self) -> str:
            return "test"
        
        def _check_data_availability(self) -> Dict[str, Any]:
            return {"available": True, "test": True}
    
    # Test basic functionality
    logger = logging.getLogger("test")
    handler = TestHandler(logger)
    
    # Test parameter validation
    validation = handler._validate_parameters(resolution=0.5, n_neighbors=15)
    assert validation["valid"] is True
    
    # Test invalid parameters
    validation = handler._validate_parameters(resolution=5.0)
    assert validation["valid"] is False
    
    # Test response creation
    response = handler._create_success_response("Test success")
    assert response["success"] is True
    assert "operation_id" in response
    
    print("✅ Base handler tests passed")


if __name__ == "__main__":
    main()