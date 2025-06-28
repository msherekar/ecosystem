"""
Security Validator

Provides security validation and audit logging for MCP handlers.
Protects against injection attacks, validates inputs, and maintains audit trails.
"""

import re
import logging
import hashlib
from typing import Any, Dict, List, Set
from datetime import datetime
from pathlib import Path
import json


class SecurityValidator:
    """Security validation and audit logging"""
    
    def __init__(self, audit_log_path: str = "logs/security_audit.log"):
        self.audit_log_path = Path(audit_log_path)
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize security logger
        self.security_logger = logging.getLogger("security")
        handler = logging.FileHandler(self.audit_log_path)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.security_logger.addHandler(handler)
        self.security_logger.setLevel(logging.INFO)
        
        # Dangerous patterns to check for
        self.dangerous_patterns = [
            r'(__import__|exec|eval|compile)',  # Code execution
            r'(subprocess|os\.system|popen)',   # System commands
            r'(file://|ftp://)',                # File access
            r'(<script|javascript:|vbscript:)', # Script injection
            r'(DROP|DELETE|UPDATE|INSERT)\s+', # SQL-like commands
            r'(\.\./|\.\.\\)',                  # Path traversal
        ]
        
        # Allowed file extensions for uploads
        self.allowed_extensions = {
            '.h5ad', '.csv', '.tsv', '.xlsx', '.h5', '.mtx', '.gz'
        }
        
        # Rate limiting tracking
        self._operation_counts: Dict[str, List[datetime]] = {}
        self.max_operations_per_minute = 60
    
    def validate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameters for security issues"""
        validation_result = {"valid": True, "errors": []}
        
        for key, value in params.items():
            # Check parameter names
            if not self._is_safe_parameter_name(key):
                validation_result["valid"] = False
                validation_result["errors"].append(f"Invalid parameter name: {key}")
                continue
            
            # Check parameter values
            if isinstance(value, str):
                if not self._is_safe_string_value(value):
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"Potentially dangerous value in parameter: {key}")
            
            elif isinstance(value, (list, tuple)):
                for item in value:
                    if isinstance(item, str) and not self._is_safe_string_value(item):
                        validation_result["valid"] = False
                        validation_result["errors"].append(f"Potentially dangerous value in list parameter: {key}")
        
        return validation_result
    
    def validate_file_upload(self, filename: str, file_size: int) -> Dict[str, Any]:
        """Validate file uploads"""
        validation_result = {"valid": True, "errors": []}
        
        # Check filename
        if not self._is_safe_filename(filename):
            validation_result["valid"] = False
            validation_result["errors"].append("Invalid filename")
        
        # Check extension
        file_path = Path(filename)
        if file_path.suffix.lower() not in self.allowed_extensions:
            validation_result["valid"] = False
            validation_result["errors"].append(f"File extension not allowed: {file_path.suffix}")
        
        # Check file size (100MB limit)
        max_file_size = 100 * 1024 * 1024  # 100MB
        if file_size > max_file_size:
            validation_result["valid"] = False
            validation_result["errors"].append(f"File too large: {file_size} bytes (max: {max_file_size})")
        
        return validation_result
    
    def check_rate_limit(self, operation_key: str) -> bool:
        """Check if operation is within rate limits"""
        now = datetime.now()
        
        # Clean old entries (older than 1 minute)
        if operation_key in self._operation_counts:
            self._operation_counts[operation_key] = [
                timestamp for timestamp in self._operation_counts[operation_key]
                if (now - timestamp).total_seconds() < 60
            ]
        else:
            self._operation_counts[operation_key] = []
        
        # Check current count
        current_count = len(self._operation_counts[operation_key])
        if current_count >= self.max_operations_per_minute:
            return False
        
        # Add current operation
        self._operation_counts[operation_key].append(now)
        return True
    
    def audit_operation(self, technique: str, operation: str, parameters: Dict[str, Any]):
        """Log operation for security audit"""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "technique": technique,
            "operation": operation,
            "parameter_hash": self._hash_parameters(parameters),
            "parameter_keys": list(parameters.keys())
        }
        
        self.security_logger.info(f"AUDIT: {json.dumps(audit_entry)}")
    
    def _is_safe_parameter_name(self, name: str) -> bool:
        """Check if parameter name is safe"""
        # Allow only alphanumeric, underscore, and hyphen
        return re.match(r'^[a-zA-Z0-9_-]+$', name) is not None
    
    def _is_safe_string_value(self, value: str) -> bool:
        """Check if string value is safe"""
        # Check against dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return False
        
        # Check for excessive length
        if len(value) > 1000:
            return False
        
        return True
    
    def _is_safe_filename(self, filename: str) -> bool:
        """Check if filename is safe"""
        # Basic filename validation
        dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        return not any(char in filename for char in dangerous_chars)
    
    def _hash_parameters(self, parameters: Dict[str, Any]) -> str:
        """Create hash of parameters for audit trail"""
        param_str = json.dumps(parameters, sort_keys=True, default=str)
        return hashlib.sha256(param_str.encode()).hexdigest()[:16]
    
    def get_security_report(self) -> Dict[str, Any]:
        """Generate security report"""
        try:
            # Count recent operations
            now = datetime.now()
            recent_operations = 0
            
            for timestamps in self._operation_counts.values():
                recent_operations += len([
                    t for t in timestamps 
                    if (now - t).total_seconds() < 3600  # Last hour
                ])
            
            return {
                "audit_log_exists": self.audit_log_path.exists(),
                "recent_operations_count": recent_operations,
                "rate_limit_status": "active",
                "allowed_extensions": list(self.allowed_extensions)
            }
        except Exception as e:
            return {"error": str(e)}


def main():
    """Test security validator functionality"""
    validator = SecurityValidator()
    
    # Test parameter validation
    safe_params = {"resolution": 0.5, "n_neighbors": 15}
    result = validator.validate_parameters(safe_params)
    assert result["valid"] is True
    
    # Test dangerous parameters
    dangerous_params = {"evil": "__import__('os').system('rm -rf /')"}
    result = validator.validate_parameters(dangerous_params)
    assert result["valid"] is False
    
    # Test file validation
    result = validator.validate_file_upload("data.h5ad", 1024)
    assert result["valid"] is True
    
    result = validator.validate_file_upload("../evil.py", 1024)
    assert result["valid"] is False
    
    # Test rate limiting
    for i in range(5):
        assert validator.check_rate_limit("test_op") is True
    
    print("✅ Security validator tests passed")


if __name__ == "__main__":
    main()