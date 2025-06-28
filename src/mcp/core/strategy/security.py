"""
Security Management Module

Provides security validation, input sanitization, and
access control for the strategy system.
"""

import re
import html
import json
import hashlib
import secrets
from typing import Dict, Any, List, Union, Optional
from functools import wraps
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class SecurityManager:
    """Manages security validation and sanitization"""
    
    def __init__(self):
        self.max_string_length = 10000
        self.allowed_file_extensions = {'.h5ad', '.csv', '.tsv', '.xlsx', '.txt', '.json'}
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.blocked_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'eval\s*\(',
            r'exec\s*\(',
            r'import\s+',
            r'__import__',
        ]
        self.sql_injection_patterns = [
            r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)',
            r'(--|#|/\*|\*/)',
            r"('|(\\x27)|(\\x2D)|(\\x23))",
            r'(\b(OR|AND)\b.*(\b(=|>|<|\s+LIKE\s+|\s+IS\s+NULL\s+|\s+IS\s+NOT\s+NULL\s+)\b))',
        ]
    
    def sanitize_string(self, value: str) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            return str(value)
        
        # Truncate if too long
        if len(value) > self.max_string_length:
            value = value[:self.max_string_length]
            logger.warning(f"Truncated string input to {self.max_string_length} characters")
        
        # HTML escape
        value = html.escape(value)
        
        # Remove dangerous patterns
        for pattern in self.blocked_patterns:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        
        # Check for SQL injection patterns
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"Potential SQL injection detected and sanitized")
                value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        
        return value.strip()
    
    def sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize context dictionary"""
        if not isinstance(context, dict):
            logger.warning("Context is not a dictionary, returning empty dict")
            return {}
        
        sanitized = {}
        for key, value in context.items():
            # Sanitize key
            clean_key = self.sanitize_string(str(key))
            
            # Sanitize value based on type
            if isinstance(value, str):
                clean_value = self.sanitize_string(value)
            elif isinstance(value, (int, float, bool)):
                clean_value = value
            elif isinstance(value, dict):
                clean_value = self.sanitize_context(value)
            elif isinstance(value, list):
                clean_value = [self.sanitize_string(str(item)) if isinstance(item, str) else item for item in value]
            else:
                clean_value = self.sanitize_string(str(value))
            
            sanitized[clean_key] = clean_value
        
        return sanitized
    
    def validate_file_path(self, file_path: Union[str, Path]) -> bool:
        """Validate file path for security"""
        try:
            path = Path(file_path)
            
            # Check file extension
            if path.suffix.lower() not in self.allowed_file_extensions:
                logger.warning(f"File extension {path.suffix} not allowed")
                return False
            
            # Check for path traversal
            if '..' in str(path) or str(path).startswith('/'):
                logger.warning("Path traversal attempt detected")
                return False
            
            # Check file size if exists
            if path.exists() and path.stat().st_size > self.max_file_size:
                logger.warning(f"File size exceeds limit: {path.stat().st_size}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating file path: {e}")
            return False
    
    def generate_session_id(self) -> str:
        """Generate secure session ID"""
        return secrets.token_urlsafe(32)
    
    def hash_data(self, data: str) -> str:
        """Create secure hash of data"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def validate_analysis_type(self, analysis_type: str) -> bool:
        """Validate analysis type input"""
        if not isinstance(analysis_type, str):
            return False
        
        # Allow only alphanumeric and underscore
        if not re.match(r'^[a-zA-Z0-9_]+$', analysis_type):
            return False
        
        # Check length
        if len(analysis_type) > 50:
            return False
        
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get security manager status"""
        return {
            "max_string_length": self.max_string_length,
            "max_file_size": self.max_file_size,
            "allowed_extensions": list(self.allowed_file_extensions),
            "blocked_patterns_count": len(self.blocked_patterns),
            "sql_patterns_count": len(self.sql_injection_patterns)
        }


def validate_input(func):
    """Decorator for input validation"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Basic validation for string arguments
        for arg in args:
            if isinstance(arg, str) and len(arg) > 10000:
                raise ValueError("Input string too long")
        
        for key, value in kwargs.items():
            if isinstance(value, str) and len(value) > 10000:
                raise ValueError(f"Input string for {key} too long")
        
        return func(self, *args, **kwargs)
    return wrapper


class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, max_calls: int = 100, window_seconds: int = 60):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.calls: Dict[str, List[float]] = {}
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if call is allowed for identifier"""
        import time
        current_time = time.time()
        
        if identifier not in self.calls:
            self.calls[identifier] = []
        
        # Remove old calls outside window
        self.calls[identifier] = [
            call_time for call_time in self.calls[identifier]
            if current_time - call_time < self.window_seconds
        ]
        
        # Check if under limit
        if len(self.calls[identifier]) < self.max_calls:
            self.calls[identifier].append(current_time)
            return True
        
        return False


def main():
    """Test security manager functionality"""
    print("Testing Security Manager...")
    
    # Test string sanitization
    security_manager = SecurityManager()
    
    # Test malicious inputs
    malicious_inputs = [
        "<script>alert('xss')</script>",
        "'; DROP TABLE users; --",
        "javascript:alert('test')",
        "eval('malicious code')",
        "import os; os.system('rm -rf /')"
    ]
    
    for malicious in malicious_inputs:
        sanitized = security_manager.sanitize_string(malicious)
        assert "<script>" not in sanitized, f"Failed to sanitize: {malicious}"
        assert "javascript:" not in sanitized, f"Failed to sanitize: {malicious}"
        print(f"✅ Sanitized: {malicious[:30]}... → {sanitized[:30]}...")
    
    # Test context sanitization
    unsafe_context = {
        "normal_key": "normal_value",
        "<script>": "malicious_value",
        "sql_injection": "'; DROP TABLE users; --",
        "nested": {"evil": "<script>alert('nested')</script>"}
    }
    
    clean_context = security_manager.sanitize_context(unsafe_context)
    assert "script" not in str(clean_context), "Context sanitization failed"
    print("✅ Context sanitization passed")
    
    # Test file validation
    assert security_manager.validate_file_path("data.csv"), "Valid CSV should pass"
    assert security_manager.validate_file_path("data.h5ad"), "Valid h5ad should pass"
    assert not security_manager.validate_file_path("../../../etc/passwd"), "Path traversal should fail"
    assert not security_manager.validate_file_path("malicious.exe"), "Invalid extension should fail"
    print("✅ File validation passed")
    
    # Test analysis type validation
    assert security_manager.validate_analysis_type("scrnaseq"), "Valid analysis type should pass"
    assert security_manager.validate_analysis_type("rna_seq"), "Valid with underscore should pass"
    assert not security_manager.validate_analysis_type("script<>"), "Invalid characters should fail"
    assert not security_manager.validate_analysis_type("a" * 100), "Too long should fail"
    print("✅ Analysis type validation passed")
    
    # Test rate limiter
    rate_limiter = RateLimiter(max_calls=3, window_seconds=1)
    assert rate_limiter.is_allowed("user1"), "First call should be allowed"
    assert rate_limiter.is_allowed("user1"), "Second call should be allowed"
    assert rate_limiter.is_allowed("user1"), "Third call should be allowed"
    assert not rate_limiter.is_allowed("user1"), "Fourth call should be blocked"
    print("✅ Rate limiting passed")
    
    # Test session ID generation
    session_id = security_manager.generate_session_id()
    assert len(session_id) > 30, "Session ID should be long enough"
    assert session_id != security_manager.generate_session_id(), "Session IDs should be unique"
    print("✅ Session ID generation passed")
    
    print("🎉 All security tests passed!")


if __name__ == "__main__":
    def test_static_security():
        """Static security tests"""
        print("Running static security tests...")
        
        security = SecurityManager()
        
        # Test configuration
        assert security.max_string_length > 0, "Max string length should be positive"
        assert len(security.allowed_file_extensions) > 0, "Should have allowed extensions"
        assert len(security.blocked_patterns) > 0, "Should have blocked patterns"
        
        print("✅ Static security tests passed!")
    
    def test_dynamic_security():
        """Dynamic security tests"""
        print("Running dynamic security tests...")
        
        # Run main tests
        main()
        
        print("✅ Dynamic security tests passed!")
    
    # Run tests
    test_static_security()
    test_dynamic_security()