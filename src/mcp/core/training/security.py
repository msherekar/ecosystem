"""
Enhanced security module for training data collection.
Provides encryption, secure storage, and data privacy controls.
"""

import hashlib
import secrets
import base64
import json
import re
import logging
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

@dataclass
class SecurityConfig:
    """Security configuration settings"""
    encryption_enabled: bool = True
    data_retention_days: int = 365
    anonymization_strength: str = "strong"  # weak, medium, strong
    audit_logging: bool = True
    rate_limiting: bool = True
    max_requests_per_minute: int = 100

class DataEncryption:
    """Handles encryption/decryption of sensitive training data"""
    
    def __init__(self, password: str = None, salt: bytes = None):
        self.logger = logging.getLogger("data_encryption")
        self.salt = salt or self._generate_salt()
        self._fernet = self._initialize_encryption(password)
    
    def _generate_salt(self) -> bytes:
        """Generate cryptographically secure salt"""
        return secrets.token_bytes(32)
    
    def _initialize_encryption(self, password: str = None) -> Fernet:
        """Initialize encryption with password or generate new key"""
        try:
            if password:
                # Derive key from password using PBKDF2
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=self.salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            else:
                # Generate random key
                key = Fernet.generate_key()
            
            return Fernet(key)
        except Exception as e:
            self.logger.error(f"Encryption initialization failed: {e}")
            raise
    
    def encrypt_data(self, data: Dict[str, Any]) -> str:
        """Encrypt sensitive data fields"""
        try:
            json_data = json.dumps(data, default=str).encode()
            encrypted = self._fernet.encrypt(json_data)
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            self.logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt_data(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt sensitive data fields"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self._fernet.decrypt(encrypted_bytes)
            return json.loads(decrypted.decode())
        except Exception as e:
            self.logger.error(f"Decryption failed: {e}")
            raise
    
    def get_salt_b64(self) -> str:
        """Get base64 encoded salt for storage"""
        return base64.urlsafe_b64encode(self.salt).decode()

class PrivacyManager:
    """Manages privacy controls and data sanitization"""
    
    def __init__(self, anonymization_strength: str = "strong"):
        self.logger = logging.getLogger("privacy_manager")
        self.anonymization_strength = anonymization_strength
        
        # Sensitive data patterns
        self.sensitive_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b',
            'phone': r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
            'ip_address': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            'api_key': r'\b[A-Za-z0-9]{32,}\b',
            'file_path': r'[A-Za-z]:\\[^<>:"|?*\r\n]*|\/[^<>:"|?*\r\n]*'
        }
        
        self.replacement_map = {}
    
    def sanitize_text(self, text: str) -> str:
        """Remove or mask sensitive information from text"""
        sanitized = text
        
        for pattern_name, pattern in self.sensitive_patterns.items():
            matches = re.finditer(pattern, sanitized, re.IGNORECASE)
            
            for match in matches:
                original = match.group()
                replacement = self._get_replacement(original, pattern_name)
                sanitized = sanitized.replace(original, replacement)
        
        return sanitized
    
    def _get_replacement(self, original: str, pattern_type: str) -> str:
        """Get replacement text for sensitive data"""
        if original in self.replacement_map:
            return self.replacement_map[original]
        
        if self.anonymization_strength == "weak":
            # Just mask part of the data
            if len(original) > 4:
                replacement = original[:2] + "*" * (len(original) - 4) + original[-2:]
            else:
                replacement = "*" * len(original)
        
        elif self.anonymization_strength == "medium":
            # Replace with generic placeholder
            replacement = f"[{pattern_type.upper()}_REDACTED]"
        
        else:  # strong
            # Replace with consistent hash
            hash_input = f"{original}_{pattern_type}"
            hash_value = hashlib.sha256(hash_input.encode()).hexdigest()[:8]
            replacement = f"[{pattern_type.upper()}_{hash_value}]"
        
        self.replacement_map[original] = replacement
        return replacement
    
    def sanitize_conversation_data(self, conversation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize conversation data for privacy"""
        sanitized = conversation_data.copy()
        
        # Sanitize text fields
        text_fields = ['user_message', 'assistant_response', 'user_feedback']
        for field in text_fields:
            if field in sanitized and sanitized[field]:
                sanitized[field] = self.sanitize_text(sanitized[field])
        
        # Sanitize context data
        if 'context' in sanitized and isinstance(sanitized['context'], dict):
            sanitized['context'] = self._sanitize_dict(sanitized['context'])
        
        # Sanitize tool results
        if 'tools_used' in sanitized and isinstance(sanitized['tools_used'], list):
            for tool in sanitized['tools_used']:
                if isinstance(tool, dict) and 'output' in tool:
                    tool['output'] = self.sanitize_text(str(tool['output']))
        
        return sanitized
    
    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize dictionary data"""
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = self.sanitize_text(value)
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self.sanitize_text(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized

class AuditLogger:
    """Audit logging for security and compliance"""
    
    def __init__(self, log_file: str = "training_audit.log"):
        self.log_file = log_file
        self.logger = logging.getLogger("audit_logger")
        
        # Setup audit log handler
        audit_handler = logging.FileHandler(log_file)
        audit_handler.setFormatter(
            logging.Formatter('%(asctime)s - AUDIT - %(message)s')
        )
        self.logger.addHandler(audit_handler)
        self.logger.setLevel(logging.INFO)
    
    def log_data_access(self, user_id: str, action: str, resource: str, 
                       success: bool, details: Dict[str, Any] = None) -> None:
        """Log data access events"""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "success": success,
            "details": details or {}
        }
        
        self.logger.info(json.dumps(audit_entry))
    
    def log_security_event(self, event_type: str, severity: str, 
                          description: str, metadata: Dict[str, Any] = None) -> None:
        """Log security-related events"""
        security_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "severity": severity,
            "description": description,
            "metadata": metadata or {}
        }
        
        self.logger.warning(json.dumps(security_entry))

class RateLimiter:
    """Rate limiting for API endpoints"""
    
    def __init__(self, max_requests: int = 100, window_minutes: int = 1):
        self.max_requests = max_requests
        self.window_minutes = window_minutes
        self.requests: Dict[str, List[datetime]] = {}
        self.logger = logging.getLogger("rate_limiter")
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed under rate limit"""
        now = datetime.now()
        window_start = now - timedelta(minutes=self.window_minutes)
        
        # Clean old requests
        if client_id in self.requests:
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if req_time > window_start
            ]
        else:
            self.requests[client_id] = []
        
        # Check rate limit
        if len(self.requests[client_id]) >= self.max_requests:
            self.logger.warning(f"Rate limit exceeded for client: {client_id}")
            return False
        
        # Add current request
        self.requests[client_id].append(now)
        return True
    
    def get_remaining_requests(self, client_id: str) -> int:
        """Get remaining requests for client"""
        current_count = len(self.requests.get(client_id, []))
        return max(0, self.max_requests - current_count)

class SecureTrainingManager:
    """Main security manager for training system"""
    
    def __init__(self, config: SecurityConfig = None):
        self.config = config or SecurityConfig()
        self.logger = logging.getLogger("secure_training")
        
        # Initialize security components
        self.encryption = DataEncryption() if self.config.encryption_enabled else None
        self.privacy_manager = PrivacyManager(self.config.anonymization_strength)
        self.audit_logger = AuditLogger() if self.config.audit_logging else None
        self.rate_limiter = RateLimiter(
            self.config.max_requests_per_minute
        ) if self.config.rate_limiting else None
    
    def secure_conversation_data(self, data: Dict[str, Any], 
                               user_id: str = "unknown") -> Dict[str, Any]:
        """Apply all security measures to conversation data"""
        try:
            # Log access
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    user_id, "secure_data", "conversation", True
                )
            
            # Sanitize for privacy
            sanitized_data = self.privacy_manager.sanitize_conversation_data(data)
            
            # Encrypt if enabled
            if self.encryption:
                # Only encrypt sensitive fields, keep metadata readable
                sensitive_fields = ['user_message', 'assistant_response', 'context']
                for field in sensitive_fields:
                    if field in sanitized_data:
                        field_data = {field: sanitized_data[field]}
                        sanitized_data[f"{field}_encrypted"] = self.encryption.encrypt_data(field_data)
                        del sanitized_data[field]
            
            return sanitized_data
            
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_security_event(
                    "encryption_error", "high", str(e), {"user_id": user_id}
                )
            raise
    
    def validate_api_request(self, client_id: str, endpoint: str) -> bool:
        """Validate API request for security"""
        # Check rate limiting
        if self.rate_limiter and not self.rate_limiter.is_allowed(client_id):
            if self.audit_logger:
                self.audit_logger.log_security_event(
                    "rate_limit_exceeded", "medium",
                    f"Client {client_id} exceeded rate limit for {endpoint}"
                )
            return False
        
        return True
    
    def cleanup_expired_data(self) -> int:
        """Clean up data older than retention period"""
        # This would integrate with storage layer
        # For now, return mock count
        return 0


def main():
    """Test security components"""
    print("Testing Training Security System")
    print("=" * 40)
    
    # Test encryption
    encryption = DataEncryption("test_password")
    test_data = {"sensitive": "secret_info", "user_id": "user123"}
    
    encrypted = encryption.encrypt_data(test_data)
    decrypted = encryption.decrypt_data(encrypted)
    
    print(f"✓ Encryption test: {test_data == decrypted}")
    
    # Test privacy manager
    privacy = PrivacyManager("strong")
    test_text = "Contact me at john@example.com or call 555-123-4567"
    sanitized = privacy.sanitize_text(test_text)
    
    print(f"✓ Privacy sanitization: {sanitized}")
    
    # Test rate limiter
    rate_limiter = RateLimiter(max_requests=5, window_minutes=1)
    
    # Test multiple requests
    client_id = "test_client"
    allowed_count = 0
    for i in range(7):
        if rate_limiter.is_allowed(client_id):
            allowed_count += 1
    
    print(f"✓ Rate limiting: {allowed_count}/7 requests allowed")
    
    # Test secure manager
    config = SecurityConfig(
        encryption_enabled=True,
        anonymization_strength="strong",
        audit_logging=False  # Disable for test
    )
    
    secure_manager = SecureTrainingManager(config)
    
    test_conversation = {
        "user_message": "My email is test@example.com",
        "assistant_response": "I'll help you with that",
        "context": {"user_ip": "192.168.1.1"}
    }
    
    secured = secure_manager.secure_conversation_data(test_conversation)
    print(f"✓ Secure conversation data: {len(secured)} fields processed")
    
    print("✓ All security tests completed!")
    
if __name__ == "__main__":
    main()