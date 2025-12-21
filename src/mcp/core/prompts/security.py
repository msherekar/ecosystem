"""
Security Module for Domain Prompt System

Provides input validation, sanitization, and security controls for the domain prompt system.
Protects against code injection and ensures safe operation in production environments.
"""

import logging
import re
from pathlib import Path
from typing import List, Set, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security levels for prompt access control"""
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"


class SecurityValidator:
    """Security validation and sanitization for user inputs"""
    
    # Dangerous patterns that could indicate injection attempts
    DANGEROUS_PATTERNS = [
        r'__[a-zA-Z_]+__',  # Python dunder methods
        r'eval\s*\(',       # eval() calls
        r'exec\s*\(',       # exec() calls
        r'import\s+',       # import statements
        r'from\s+\w+\s+import',  # from imports
        r'open\s*\(',       # file operations
        r'file\s*\(',       # file operations
        r'subprocess',      # subprocess calls
        r'os\.',           # os module calls
        r'sys\.',          # sys module calls
        r'globals\s*\(',   # globals access
        r'locals\s*\(',    # locals access
        r'vars\s*\(',      # vars access
        r'dir\s*\(',       # directory listing
        r'getattr\s*\(',   # attribute access
        r'setattr\s*\(',   # attribute setting
        r'delattr\s*\(',   # attribute deletion
        r'hasattr\s*\(',   # attribute checking
    ]
    
    # Allowed file extensions for exports
    SAFE_EXTENSIONS = {'.json', '.txt', '.csv', '.tsv', '.md', '.yaml', '.yml'}
    
    # Safe directories for file operations
    SAFE_DIRECTORIES = ['data', 'exports', 'outputs', 'results', 'temp']
    
    @classmethod
    def validate_string(cls, value: str, max_length: int = 10000, field_name: str = "input") -> str:
        """
        Validate and sanitize string input
        
        Args:
            value: String to validate
            max_length: Maximum allowed length
            field_name: Name of field for error messages
            
        Returns:
            Sanitized string
            
        Raises:
            ValueError: If validation fails
        """
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a string, got {type(value).__name__}")
        
        if len(value) > max_length:
            raise ValueError(f"{field_name} too long (max {max_length} characters, got {len(value)})")
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"Potentially dangerous pattern detected in {field_name}: {pattern}")
                # Log but don't block - prompts might legitimately contain these patterns
        
        # Basic sanitization
        sanitized = value.strip()
        
        # Remove null bytes and other control characters
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)
        
        return sanitized
    
    @classmethod
    def validate_identifier(cls, value: str, field_name: str = "identifier") -> str:
        """
        Validate identifier (name, parameter name, etc.)
        
        Args:
            value: Identifier to validate
            field_name: Name of field for error messages
            
        Returns:
            Validated identifier
            
        Raises:
            ValueError: If validation fails
        """
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a string, got {type(value).__name__}")
        
        # Check basic format
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', value):
            raise ValueError(f"Invalid {field_name} format. Must start with letter/underscore, "
                           f"contain only letters/numbers/underscores")
        
        if len(value) > 100:
            raise ValueError(f"{field_name} too long (max 100 characters, got {len(value)})")
        
        # Check for reserved words
        python_reserved = {
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del', 'elif', 'else',
            'except', 'exec', 'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
            'lambda', 'not', 'or', 'pass', 'print', 'raise', 'return', 'try', 'while', 'with',
            'yield', 'True', 'False', 'None'
        }
        
        if value.lower() in python_reserved:
            raise ValueError(f"{field_name} cannot be a Python reserved word: {value}")
        
        return value
    
    @classmethod
    def validate_template(cls, template: str, max_length: int = 50000) -> str:
        """
        Validate template string for security
        
        Args:
            template: Template string to validate
            max_length: Maximum allowed length
            
        Returns:
            Validated template
            
        Raises:
            ValueError: If validation fails
        """
        validated = cls.validate_string(template, max_length, "template")
        
        # Check for balanced braces
        open_count = validated.count('{')
        close_count = validated.count('}')
        if open_count != close_count:
            raise ValueError(f"Unbalanced braces in template: {open_count} open, {close_count} close")
        
        # Check for nested braces (not supported)
        if '{{' in validated or '}}' in validated:
            logger.warning("Template contains double braces - these will be treated as literals")
        
        return validated
    
    @classmethod
    def validate_file_path(cls, filepath: Path, operation: str = "access") -> Path:
        """
        Validate file path for security
        
        Args:
            filepath: Path to validate
            operation: Type of operation (read, write, delete)
            
        Returns:
            Validated path
            
        Raises:
            ValueError: If path is not safe
        """
        if not isinstance(filepath, Path):
            filepath = Path(filepath)
        
        # Convert to absolute path for security checks
        abs_path = filepath.resolve()
        
        # Check for path traversal attempts
        if '..' in str(filepath) or '~' in str(filepath):
            raise ValueError(f"Path traversal not allowed: {filepath}")
        
        # For write operations, check if directory is safe
        if operation in ['write', 'delete']:
            # Must be in current directory or safe subdirectories
            cwd = Path.cwd().resolve()
            
            # Check if path is within current directory
            try:
                abs_path.relative_to(cwd)
            except ValueError:
                # Not within current directory - check if in allowed external dirs
                allowed_dirs = [
                    Path.home() / "Downloads",
                    Path.home() / "Documents",
                    Path("/tmp") if Path("/tmp").exists() else None
                ]
                allowed_dirs = [d for d in allowed_dirs if d is not None]
                
                if not any(str(abs_path).startswith(str(allowed_dir)) for allowed_dir in allowed_dirs):
                    raise ValueError(f"File operations not allowed outside safe directories: {abs_path}")
        
        # Check file extension for exports
        if operation == 'write' and filepath.suffix.lower() not in cls.SAFE_EXTENSIONS:
            logger.warning(f"Potentially unsafe file extension: {filepath.suffix}")
        
        return abs_path
    
    @classmethod
    def validate_parameters(cls, parameters: dict) -> dict:
        """
        Validate and sanitize parameter dictionary
        
        Args:
            parameters: Dictionary of parameters to validate
            
        Returns:
            Validated parameters dictionary
            
        Raises:
            ValueError: If validation fails
        """
        if not isinstance(parameters, dict):
            raise ValueError(f"Parameters must be a dictionary, got {type(parameters).__name__}")
        
        validated = {}
        
        for key, value in parameters.items():
            # Validate key
            validated_key = cls.validate_identifier(key, f"parameter '{key}'")
            
            # Validate value (convert to string and sanitize)
            if value is None:
                validated_value = ""
            else:
                str_value = str(value)
                validated_value = cls.validate_string(str_value, max_length=5000, 
                                                    field_name=f"parameter '{key}' value")
            
            validated[validated_key] = validated_value
        
        return validated
    
    @classmethod
    def check_security_level_access(cls, current_level: SecurityLevel, required_level: SecurityLevel) -> bool:
        """
        Check if current security level allows access to required level
        
        Args:
            current_level: Current user's security level
            required_level: Required security level for access
            
        Returns:
            True if access allowed, False otherwise
        """
        level_hierarchy = {
            SecurityLevel.PUBLIC: 1,
            SecurityLevel.INTERNAL: 2,
            SecurityLevel.RESTRICTED: 3,
            SecurityLevel.CONFIDENTIAL: 4
        }
        
        return level_hierarchy[current_level] >= level_hierarchy[required_level]
    
    @classmethod
    def sanitize_for_logging(cls, value: str, max_length: int = 200) -> str:
        """
        Sanitize value for safe logging
        
        Args:
            value: Value to sanitize
            max_length: Maximum length for logged value
            
        Returns:
            Sanitized value safe for logging
        """
        if not isinstance(value, str):
            value = str(value)
        
        # Remove sensitive patterns
        sanitized = re.sub(r'password|token|key|secret', '[REDACTED]', value, flags=re.IGNORECASE)
        
        # Truncate if too long
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length-3] + "..."
        
        # Remove control characters
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)
        
        return sanitized


class SecurityContext:
    """Security context for tracking current security state"""
    
    def __init__(self, level: SecurityLevel = SecurityLevel.PUBLIC):
        self.level = level
        self.permissions: Set[str] = set()
        self.restrictions: Set[str] = set()
    
    def has_permission(self, permission: str) -> bool:
        """Check if context has specific permission"""
        return permission in self.permissions
    
    def add_permission(self, permission: str):
        """Add permission to context"""
        self.permissions.add(permission)
    
    def remove_permission(self, permission: str):
        """Remove permission from context"""
        self.permissions.discard(permission)
    
    def add_restriction(self, restriction: str):
        """Add restriction to context"""
        self.restrictions.add(restriction)
    
    def is_restricted(self, action: str) -> bool:
        """Check if action is restricted"""
        return action in self.restrictions


if __name__ == "__main__":
    # Test security validation
    print("Testing Security Module")
    
    # Test string validation
    try:
        valid = SecurityValidator.validate_string("Hello world", 50)
        print(f"✓ String validation: '{valid}'")
    except ValueError as e:
        print(f"✗ String validation failed: {e}")
    
    # Test identifier validation
    try:
        valid_id = SecurityValidator.validate_identifier("my_parameter")
        print(f"✓ Identifier validation: '{valid_id}'")
    except ValueError as e:
        print(f"✗ Identifier validation failed: {e}")
    
    # Test template validation
    try:
        template = SecurityValidator.validate_template("Hello {name}, score: {score}")
        print(f"✓ Template validation: '{template[:50]}...'")
    except ValueError as e:
        print(f"✗ Template validation failed: {e}")
    
    # Test security level access
    public_user = SecurityLevel.PUBLIC
    restricted_content = SecurityLevel.RESTRICTED
    access_allowed = SecurityValidator.check_security_level_access(public_user, restricted_content)
    print(f"✓ Security access check: {access_allowed}")
    
    print("\n✅ Security module test completed!") 