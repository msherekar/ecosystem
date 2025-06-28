"""
Centralized Error Handling System

Provides comprehensive error handling, logging, and recovery mechanisms
for the MCP server and handler system.
"""

import logging
import traceback
import json
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""
    SYSTEM = "system"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    RESOURCE = "resource"
    NETWORK = "network"
    DATA = "data"
    ANALYSIS = "analysis"
    USER = "user"


@dataclass
class ErrorDetails:
    """Structured error information"""
    error_id: str
    error_type: str
    message: str
    severity: ErrorSeverity
    category: ErrorCategory
    timestamp: str
    context: Dict[str, Any]
    stack_trace: Optional[str] = None
    user_message: Optional[str] = None
    recovery_suggestion: Optional[str] = None


class ErrorHandler:
    """Centralized error handling and logging system"""
    
    def __init__(self, log_file: str = "logs/errors.log"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Setup error logger
        self.logger = logging.getLogger("error_handler")
        self.logger.setLevel(logging.ERROR)
        
        # File handler for error logs
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(file_handler)
        
        # Error tracking
        self.error_count = 0
        self.recent_errors: List[ErrorDetails] = []
        self.max_recent_errors = 100
        
        # Error type mappings
        self.error_mappings = self._setup_error_mappings()
        
        # Recovery handlers
        self.recovery_handlers: Dict[str, Callable] = {}
    
    def _setup_error_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Setup error type mappings with metadata"""
        return {
            # System errors
            "server_initialization": {
                "severity": ErrorSeverity.CRITICAL,
                "category": ErrorCategory.SYSTEM,
                "user_message": "Server failed to start. Please check configuration and try again.",
                "recovery": "Check logs, verify configuration, restart server"
            },
            "handler_initialization": {
                "severity": ErrorSeverity.HIGH,
                "category": ErrorCategory.SYSTEM,
                "user_message": "Failed to initialize analysis handler. Some features may be unavailable.",
                "recovery": "Check handler configuration and dependencies"
            },
            "memory_error": {
                "severity": ErrorSeverity.HIGH,
                "category": ErrorCategory.RESOURCE,
                "user_message": "Insufficient memory to complete operation.",
                "recovery": "Reduce data size or upgrade system memory"
            },
            
            # Validation errors
            "parameter_validation": {
                "severity": ErrorSeverity.MEDIUM,
                "category": ErrorCategory.VALIDATION,
                "user_message": "Invalid parameters provided.",
                "recovery": "Check parameter values and try again"
            },
            "file_validation": {
                "severity": ErrorSeverity.MEDIUM,
                "category": ErrorCategory.VALIDATION,
                "user_message": "Invalid file format or content.",
                "recovery": "Check file format and content requirements"
            },
            
            # Data errors
            "no_data": {
                "severity": ErrorSeverity.MEDIUM,
                "category": ErrorCategory.DATA,
                "user_message": "No data available for analysis.",
                "recovery": "Upload data before running analysis"
            },
            "data_corruption": {
                "severity": ErrorSeverity.HIGH,
                "category": ErrorCategory.DATA,
                "user_message": "Data appears to be corrupted.",
                "recovery": "Re-upload data or check data integrity"
            },
            
            # Analysis errors
            "analysis_failed": {
                "severity": ErrorSeverity.MEDIUM,
                "category": ErrorCategory.ANALYSIS,
                "user_message": "Analysis failed to complete.",
                "recovery": "Check data quality and analysis parameters"
            },
            "tool_execution": {
                "severity": ErrorSeverity.MEDIUM,
                "category": ErrorCategory.ANALYSIS,
                "user_message": "Tool execution failed.",
                "recovery": "Check tool parameters and data requirements"
            },
            
            # Network errors
            "connection_failed": {
                "severity": ErrorSeverity.MEDIUM,
                "category": ErrorCategory.NETWORK,
                "user_message": "Connection failed.",
                "recovery": "Check network connection and try again"
            },
            "timeout": {
                "severity": ErrorSeverity.MEDIUM,
                "category": ErrorCategory.NETWORK,
                "user_message": "Operation timed out.",
                "recovery": "Try again or reduce operation complexity"
            },
            
            # Security errors
            "rate_limit": {
                "severity": ErrorSeverity.LOW,
                "category": ErrorCategory.AUTHENTICATION,
                "user_message": "Rate limit exceeded. Please wait before trying again.",
                "recovery": "Wait and retry operation"
            },
            "security_violation": {
                "severity": ErrorSeverity.HIGH,
                "category": ErrorCategory.AUTHENTICATION,
                "user_message": "Security violation detected.",
                "recovery": "Contact administrator"
            }
        }
    
    def handle_error(self, error_type: str, error_message: str, 
                    context: Dict[str, Any] = None, 
                    exception: Exception = None) -> Dict[str, Any]:
        """Handle and log error with structured response"""
        try:
            # Generate unique error ID
            self.error_count += 1
            error_id = f"ERR_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.error_count:04d}"
            
            # Get error mapping
            error_mapping = self.error_mappings.get(error_type, {
                "severity": ErrorSeverity.MEDIUM,
                "category": ErrorCategory.SYSTEM,
                "user_message": "An unexpected error occurred.",
                "recovery": "Please try again or contact support"
            })
            
            # Create error details
            error_details = ErrorDetails(
                error_id=error_id,
                error_type=error_type,
                message=error_message,
                severity=error_mapping["severity"],
                category=error_mapping["category"],
                timestamp=datetime.now().isoformat(),
                context=context or {},
                stack_trace=traceback.format_exc() if exception else None,
                user_message=error_mapping.get("user_message"),
                recovery_suggestion=error_mapping.get("recovery")
            )
            
            # Log error
            self._log_error(error_details)
            
            # Store recent error
            self._store_recent_error(error_details)
            
            # Attempt recovery if handler exists
            self._attempt_recovery(error_type, error_details)
            
            # Return structured response
            return {
                "success": False,
                "error": {
                    "id": error_id,
                    "type": error_type,
                    "message": error_details.user_message or error_message,
                    "severity": error_details.severity.value,
                    "category": error_details.category.value,
                    "timestamp": error_details.timestamp,
                    "recovery_suggestion": error_details.recovery_suggestion
                }
            }
            
        except Exception as e:
            # Fallback error handling
            fallback_error = {
                "success": False,
                "error": {
                    "id": "ERR_FALLBACK",
                    "type": "error_handler_failure",
                    "message": "Error handler failed",
                    "severity": "critical"
                }
            }
            self.logger.error(f"Error handler failed: {e}")
            return fallback_error
    
    def log_error(self, error_type: str, message: str, context: Dict[str, Any] = None):
        """Log error without returning response (for non-blocking error logging)"""
        try:
            self.handle_error(error_type, message, context)
        except Exception as e:
            self.logger.error(f"Failed to log error: {e}")
    
    def _log_error(self, error_details: ErrorDetails):
        """Log error details to file and console"""
        # Create log message
        log_data = {
            "error_id": error_details.error_id,
            "type": error_details.error_type,
            "message": error_details.message,
            "severity": error_details.severity.value,
            "category": error_details.category.value,
            "context": error_details.context
        }
        
        # Log to file
        self.logger.error(json.dumps(log_data, indent=2))
        
        # Log stack trace if available
        if error_details.stack_trace:
            self.logger.error(f"Stack trace for {error_details.error_id}:\n{error_details.stack_trace}")
    
    def _store_recent_error(self, error_details: ErrorDetails):
        """Store error in recent errors list"""
        self.recent_errors.append(error_details)
        
        # Trim to max size
        if len(self.recent_errors) > self.max_recent_errors:
            self.recent_errors = self.recent_errors[-self.max_recent_errors:]
    
    def _attempt_recovery(self, error_type: str, error_details: ErrorDetails):
        """Attempt automatic recovery if handler exists"""
        if error_type in self.recovery_handlers:
            try:
                recovery_handler = self.recovery_handlers[error_type]
                recovery_handler(error_details)
                self.logger.info(f"Recovery attempted for error {error_details.error_id}")
            except Exception as e:
                self.logger.error(f"Recovery failed for {error_details.error_id}: {e}")
    
    def register_recovery_handler(self, error_type: str, handler: Callable):
        """Register recovery handler for specific error type"""
        self.recovery_handlers[error_type] = handler
        self.logger.info(f"Registered recovery handler for {error_type}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics and analysis"""
        if not self.recent_errors:
            return {"total_errors": 0, "recent_errors": []}
        
        # Count by severity
        severity_counts = {}
        for error in self.recent_errors:
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Count by category
        category_counts = {}
        for error in self.recent_errors:
            category = error.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Count by type
        type_counts = {}
        for error in self.recent_errors:
            error_type = error.error_type
            type_counts[error_type] = type_counts.get(error_type, 0) + 1
        
        return {
            "total_errors": len(self.recent_errors),
            "severity_distribution": severity_counts,
            "category_distribution": category_counts,
            "type_distribution": type_counts,
            "recent_errors": [asdict(error) for error in self.recent_errors[-10:]]  # Last 10 errors
        }
    
    def clear_error_log(self) -> bool:
        """Clear recent errors (not log file)"""
        try:
            self.recent_errors.clear()
            self.logger.info("Error log cleared")
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear error log: {e}")
            return False


def main():
    """Test error handler functionality"""
    import tempfile
    
    # Create temporary log file
    with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as f:
        log_path = f.name
    
    try:
        # Test error handler
        error_handler = ErrorHandler(log_path)
        
        # Test basic error handling
        result = error_handler.handle_error(
            "parameter_validation",
            "Invalid resolution parameter",
            {"parameter": "resolution", "value": -1}
        )
        
        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] == "parameter_validation"
        assert "recovery_suggestion" in result["error"]
        
        # Test error logging
        error_handler.log_error(
            "data_corruption",
            "Data file appears corrupted",
            {"file": "test.h5ad"}
        )
        
        # Test error statistics
        stats = error_handler.get_error_statistics()
        assert stats["total_errors"] == 2
        assert "severity_distribution" in stats
        
        # Test recovery handler registration
        def test_recovery(error_details):
            print(f"Recovery attempted for {error_details.error_id}")
        
        error_handler.register_recovery_handler("test_error", test_recovery)
        assert "test_error" in error_handler.recovery_handlers
        
        print("✅ Error handler tests passed")
        
    finally:
        # Cleanup
        import os
        os.unlink(log_path)


if __name__ == "__main__":
    main()