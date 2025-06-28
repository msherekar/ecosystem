"""
Core Exception Classes

Defines custom exception classes used throughout the MCP system.
Provides structured error handling with proper categorization.
"""

from typing import Optional, Dict, Any
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"  
    HIGH = "high"
    CRITICAL = "critical"


class MCPBaseException(Exception):
    """Base exception class for all MCP-related errors"""
    
    def __init__(self, message: str, error_code: str = None, 
                 details: Dict[str, Any] = None, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.severity = severity
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for serialization"""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "severity": self.severity.value,
            "details": self.details
        }


class SecurityError(MCPBaseException):
    """Security-related errors"""
    
    def __init__(self, message: str, error_code: str = "SECURITY_ERROR", 
                 details: Dict[str, Any] = None):
        super().__init__(message, error_code, details, ErrorSeverity.HIGH)


class AuthenticationError(SecurityError):
    """Authentication failures"""
    
    def __init__(self, message: str = "Authentication failed", 
                 error_code: str = "AUTH_FAILED", details: Dict[str, Any] = None):
        super().__init__(message, error_code, details)


class AuthorizationError(SecurityError):
    """Authorization failures"""
    
    def __init__(self, message: str = "Access denied", 
                 error_code: str = "ACCESS_DENIED", details: Dict[str, Any] = None):
        super().__init__(message, error_code, details)


class ValidationError(MCPBaseException):
    """Data validation errors"""
    
    def __init__(self, message: str, field: str = None, 
                 error_code: str = "VALIDATION_ERROR", details: Dict[str, Any] = None):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(message, error_code, details, ErrorSeverity.MEDIUM)


class ConfigurationError(MCPBaseException):
    """Configuration-related errors"""
    
    def __init__(self, message: str, config_key: str = None,
                 error_code: str = "CONFIG_ERROR", details: Dict[str, Any] = None):
        details = details or {}
        if config_key:
            details["config_key"] = config_key
        super().__init__(message, error_code, details, ErrorSeverity.HIGH)


class DataError(MCPBaseException):
    """Data processing errors"""
    
    def __init__(self, message: str, data_type: str = None,
                 error_code: str = "DATA_ERROR", details: Dict[str, Any] = None):
        details = details or {}
        if data_type:
            details["data_type"] = data_type
        super().__init__(message, error_code, details, ErrorSeverity.MEDIUM)


class AnalysisError(MCPBaseException):
    """Analysis pipeline errors"""
    
    def __init__(self, message: str, technique: str = None, step: str = None,
                 error_code: str = "ANALYSIS_ERROR", details: Dict[str, Any] = None):
        details = details or {}
        if technique:
            details["technique"] = technique
        if step:
            details["step"] = step
        super().__init__(message, error_code, details, ErrorSeverity.MEDIUM)


class ServerError(MCPBaseException):
    """Server-related errors"""
    
    def __init__(self, message: str, server_type: str = None,
                 error_code: str = "SERVER_ERROR", details: Dict[str, Any] = None):
        details = details or {}
        if server_type:
            details["server_type"] = server_type
        super().__init__(message, error_code, details, ErrorSeverity.HIGH)


class MCPServerError(ServerError):
    """MCP server-specific errors"""
    
    def __init__(self, message: str, server_name: str = None,
                 error_code: str = "MCP_SERVER_ERROR", details: Dict[str, Any] = None):
        details = details or {}
        if server_name:
            details["server_name"] = server_name
        super().__init__(message, server_type="MCP", error_code=error_code, details=details)


class ResourceError(MCPBaseException):
    """Resource access errors"""
    
    def __init__(self, message: str, resource_type: str = None,
                 error_code: str = "RESOURCE_ERROR", details: Dict[str, Any] = None):
        details = details or {}
        if resource_type:
            details["resource_type"] = resource_type
        super().__init__(message, error_code, details, ErrorSeverity.MEDIUM)


class NetworkError(MCPBaseException):
    """Network communication errors"""
    
    def __init__(self, message: str, endpoint: str = None,
                 error_code: str = "NETWORK_ERROR", details: Dict[str, Any] = None):
        details = details or {}
        if endpoint:
            details["endpoint"] = endpoint
        super().__init__(message, error_code, details, ErrorSeverity.MEDIUM)


class TimeoutError(MCPBaseException):
    """Operation timeout errors"""
    
    def __init__(self, message: str = "Operation timed out", timeout_duration: float = None,
                 error_code: str = "TIMEOUT", details: Dict[str, Any] = None):
        details = details or {}
        if timeout_duration:
            details["timeout_duration"] = timeout_duration
        super().__init__(message, error_code, details, ErrorSeverity.MEDIUM)


class RateLimitError(SecurityError):
    """Rate limiting errors"""
    
    def __init__(self, message: str = "Rate limit exceeded", limit: int = None,
                 error_code: str = "RATE_LIMIT", details: Dict[str, Any] = None):
        details = details or {}
        if limit:
            details["limit"] = limit
        super().__init__(message, error_code, details)


# Convenience functions for common error scenarios
def security_error(message: str, **kwargs) -> SecurityError:
    """Create a security error"""
    return SecurityError(message, **kwargs)

def auth_error(message: str = "Authentication required", **kwargs) -> AuthenticationError:
    """Create an authentication error"""
    return AuthenticationError(message, **kwargs)

def validation_error(message: str, field: str = None, **kwargs) -> ValidationError:
    """Create a validation error"""
    return ValidationError(message, field=field, **kwargs)

def config_error(message: str, config_key: str = None, **kwargs) -> ConfigurationError:
    """Create a configuration error"""
    return ConfigurationError(message, config_key=config_key, **kwargs)

def analysis_error(message: str, technique: str = None, step: str = None, **kwargs) -> AnalysisError:
    """Create an analysis error"""
    return AnalysisError(message, technique=technique, step=step, **kwargs)


# Export all exception classes
__all__ = [
    'MCPBaseException',
    'SecurityError', 
    'AuthenticationError',
    'AuthorizationError',
    'ValidationError',
    'ConfigurationError', 
    'DataError',
    'AnalysisError',
    'ServerError',
    'MCPServerError',
    'ResourceError',
    'NetworkError',
    'TimeoutError',
    'RateLimitError',
    'ErrorSeverity',
    'security_error',
    'auth_error', 
    'validation_error',
    'config_error',
    'analysis_error'
] 