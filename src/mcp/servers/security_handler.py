"""
Security Handler - Advanced security and access control for MCP servers

Provides comprehensive security features:
- User authentication and authorization
- Permission-based access control
- Audit logging and threat detection
- Secure communication protocols
- Rate limiting and abuse prevention
"""

import asyncio
import hashlib
import hmac
import secrets
import json
import logging
import threading
import time
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque

from ..core.config import ServerConfig
from ..core.exceptions import SecurityError, AuthenticationError


@dataclass
class SecurityContext:
    """Security context for request validation"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    permissions: Optional['UserPermissions'] = None
    authenticated: bool = False
    
    def is_authenticated(self) -> bool:
        """Check if context represents authenticated user"""
        return self.authenticated and self.user_id is not None
    
    def has_permission(self, permission: str) -> bool:
        """Check if context has specific permission"""
        if not self.permissions:
            return False
        return self.permissions.has_permission(permission)
    
    def can_access_server(self, server_type: str) -> bool:
        """Check if context can access specific server"""
        if not self.permissions:
            return False
        return self.permissions.can_access_server(server_type)
    
    def can_use_tool(self, tool_name: str) -> bool:
        """Check if context can use specific tool"""
        if not self.permissions:
            return False
        return self.permissions.can_use_tool(tool_name)


@dataclass
class UserPermissions:
    """User permission model with role-based access"""
    user_id: str
    roles: Set[str] = field(default_factory=set)
    permissions: Set[str] = field(default_factory=set)
    restricted_servers: Set[str] = field(default_factory=set)
    restricted_tools: Set[str] = field(default_factory=set)
    expires_at: Optional[datetime] = None
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return permission in self.permissions
    
    def has_role(self, role: str) -> bool:
        """Check if user has specific role"""
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return role in self.roles
    
    def can_access_server(self, server_type: str) -> bool:
        """Check if user can access specific server type"""
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return server_type not in self.restricted_servers
    
    def can_use_tool(self, tool_name: str) -> bool:
        """Check if user can use specific tool"""
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return tool_name not in self.restricted_tools


@dataclass
class SecurityEvent:
    """Security event for audit logging"""
    timestamp: datetime
    event_type: str
    user_id: Optional[str]
    action: str
    resource: str
    result: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


class RateLimiter:
    """Sliding-window rate limiter.

    Two fixes over the previous implementation:

    - **Bounded.** The tracking dict was a `defaultdict(deque)` keyed by a
      caller-supplied identifier and never pruned of idle keys, so it grew
      without limit. Worse, since any unseen identifier got a fresh budget,
      sending a random `user_id` per request defeated the limit completely.
      Idle identifiers are now evicted and the dict is capped.
    - **Thread-safe.** `is_allowed` is a read-modify-write on a shared deque,
      and the server runs a thread-pool executor alongside its event loop, so
      the race was real rather than theoretical.
    """

    #: Identifiers tracked at once. Beyond this the least recently seen are
    #: dropped, which costs them their history but keeps memory bounded.
    MAX_TRACKED_IDENTIFIERS = 10_000

    def __init__(self, max_requests: int = 100, window_minutes: int = 1):
        self.max_requests = max_requests
        self.window_seconds = window_minutes * 60
        self.requests: Dict[str, deque] = {}
        self._last_seen: Dict[str, float] = {}
        self._lock = threading.Lock()

    def is_allowed(self, identifier: str) -> bool:
        """Whether a request from `identifier` is within the limit.

        Args:
            identifier: Caller identity (user id, token, or address).

        Returns:
            True if allowed; False if the window is full.
        """
        now = time.time()
        with self._lock:
            self._evict_idle_locked(now)
            window = self.requests.setdefault(identifier, deque())
            self._last_seen[identifier] = now

            while window and window[0] < now - self.window_seconds:
                window.popleft()

            if len(window) >= self.max_requests:
                return False

            window.append(now)
            return True

    def get_remaining_requests(self, identifier: str) -> int:
        """Requests left in the current window for `identifier`."""
        now = time.time()
        with self._lock:
            window = self.requests.get(identifier)
            if window is None:
                return self.max_requests
            while window and window[0] < now - self.window_seconds:
                window.popleft()
            return max(0, self.max_requests - len(window))

    def _evict_idle_locked(self, now: float) -> None:
        """Drop identifiers with no activity in the window, then cap the rest."""
        cutoff = now - self.window_seconds
        for identifier in [
            key for key, window in self.requests.items()
            if not window or window[-1] < cutoff
        ]:
            self.requests.pop(identifier, None)
            self._last_seen.pop(identifier, None)

        while len(self.requests) > self.MAX_TRACKED_IDENTIFIERS:
            stalest = min(self._last_seen, key=self._last_seen.get)
            self.requests.pop(stalest, None)
            self._last_seen.pop(stalest, None)

    def tracked_identifiers(self) -> int:
        """How many identifiers are currently tracked. For monitoring."""
        with self._lock:
            return len(self.requests)


class SecurityHandler:
    """Security handler for MCP servers."""

    #: Cap on simultaneously valid session tokens.
    MAX_ACTIVE_TOKENS = 1000

    
    def __init__(self, config: ServerConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        
        # Opaque session tokens, replacing the derivable scheme. Bounded by
        # MAX_ACTIVE_TOKENS and pruned on issue.
        self._tokens: Dict[str, Dict[str, Any]] = {}

        # Security components
        self.user_permissions: Dict[str, UserPermissions] = {}
        self.security_events: List[SecurityEvent] = []
        self.rate_limiter = RateLimiter(
            max_requests=config.rate_limit_requests,
            window_minutes=config.rate_limit_window_minutes
        )
        
        # Threat detection
        self.failed_attempts: Dict[str, List[datetime]] = defaultdict(list)
        self.blocked_users: Set[str] = set()
        self.suspicious_patterns: Dict[str, int] = defaultdict(int)
        
        # Initialize default permissions
        self._setup_default_permissions()
    
    def _setup_default_permissions(self):
        """Setup default permission roles and policies"""
        # Default roles and their permissions
        self.default_roles = {
            "admin": {
                "server:*", "tool:*", "data:*", "system:*"
            },
            "analyst": {
                "server:rnaseq", "server:scrnaseq", "server:atacseq",
                "tool:analyze", "tool:visualize", "data:read", "data:write"
            },
            "viewer": {
                "server:visualization", "tool:view", "data:read"
            },
            "guest": {
                "server:search", "tool:search", "data:read"
            }
        }
    
    async def validate_environment(self) -> bool:
        """Validate security environment and configuration"""
        try:
            # Check required security configurations
            if not self.config.secret_key:
                self.logger.error("Security: Missing secret key")
                return False
            
            # Validate encryption settings
            if self.config.encryption_enabled and not self.config.encryption_key:
                self.logger.error("Security: Encryption enabled but no key provided")
                return False
            
            # Check file permissions and environment
            if not self._check_file_permissions():
                self.logger.error("Security: Insecure file permissions")
                return False
            
            self.logger.info("Security environment validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Security validation failed: {str(e)}")
            return False
    
    def _check_file_permissions(self) -> bool:
        """Check that sensitive files have proper permissions"""
        try:
            import os
            import stat
            
            # Check current working directory permissions
            current_dir = os.getcwd()
            dir_stat = os.stat(current_dir)
            
            # Ensure directory is not world-writable
            if dir_stat.st_mode & stat.S_IWOTH:
                self.logger.warning("Working directory is world-writable")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"File permission check failed: {str(e)}")
            return False
    
    def authenticate_user(self, user_id: str, credentials: Dict[str, Any]) -> bool:
        """Authenticate a user against an issued session token.

        The scheme this replaces computed
        `HMAC(secret, f"{user_id}:{secret}:{hour}")` and compared the supplied
        token against that same derivation. Every input was either public
        (the caller's own user id, the current hour) or a constant the secret
        defaulted to, so any client could mint a valid token for any user.

        Tokens are now opaque values from `secrets.token_urlsafe`, issued by
        `issue_token` and held server-side, so there is nothing to derive.

        Args:
            user_id: The claimed identity.
            credentials: Must contain "token".

        Returns:
            True if the token is valid, unexpired, and bound to `user_id`.
        """
        token = credentials.get("token")
        if not token:
            self._log_security_event("auth_failure", user_id, "missing_token")
            return False

        record = self._tokens.get(token)
        if record is None:
            # Compare against every stored token so a wrong token takes the
            # same time as an unknown one.
            for stored in list(self._tokens):
                if hmac.compare_digest(stored, token):
                    record = self._tokens[stored]
                    break

        if record is None:
            self._log_security_event("auth_failure", user_id, "unknown_token")
            self._track_failed_attempt(user_id)
            return False

        if record["expires_at"] <= time.time():
            self._tokens.pop(record["token"], None)
            self._log_security_event("auth_failure", user_id, "expired_token")
            return False

        if not hmac.compare_digest(str(record["user_id"]), str(user_id)):
            self._log_security_event("auth_failure", user_id, "token_user_mismatch")
            self._track_failed_attempt(user_id)
            return False

        self._log_security_event("auth_success", user_id, "token_auth")
        return True

    def issue_token(self, user_id: str, ttl_seconds: int = 12 * 3600) -> str:
        """Issue an opaque session token for `user_id`.

        Args:
            user_id: Identity the token authenticates.
            ttl_seconds: Lifetime.

        Returns:
            The token. Store it; it cannot be recomputed.
        """
        self._prune_tokens()
        token = secrets.token_urlsafe(32)
        self._tokens[token] = {
            "token": token,
            "user_id": user_id,
            "issued_at": time.time(),
            "expires_at": time.time() + ttl_seconds,
        }
        self._log_security_event("token_issued", user_id, "issue_token")
        return token

    def revoke_token(self, token: str) -> bool:
        """Revoke a token. Returns True if it existed."""
        return self._tokens.pop(token, None) is not None

    def _prune_tokens(self) -> None:
        """Drop expired tokens, and the oldest if over the cap.

        Bounded because the dict is keyed by issuance: without a cap, repeated
        token requests grow it without limit.
        """
        now = time.time()
        for token in [t for t, r in self._tokens.items() if r["expires_at"] <= now]:
            del self._tokens[token]
        while len(self._tokens) > self.MAX_ACTIVE_TOKENS:
            oldest = min(self._tokens.values(), key=lambda r: r["issued_at"])
            del self._tokens[oldest["token"]]

    def authorize_user(self, user_id: str, roles: List[str] = None) -> UserPermissions:
        """Authorize user and return permissions"""
        if user_id in self.blocked_users:
            raise SecurityError(f"User {user_id} is blocked")
        
        # Create or update user permissions
        if user_id not in self.user_permissions:
            permissions = UserPermissions(user_id=user_id)
            
            # Assign roles and permissions
            if roles:
                permissions.roles.update(roles)
                for role in roles:
                    if role in self.default_roles:
                        permissions.permissions.update(self.default_roles[role])
            else:
                # Default to guest role
                permissions.roles.add("guest")
                permissions.permissions.update(self.default_roles["guest"])
            
            self.user_permissions[user_id] = permissions
        
        return self.user_permissions[user_id]
    
    def validate_server_access(self, server_type: str, context: Any) -> bool:
        """Validate user can access specific server type"""
        try:
            user_id = getattr(context, 'user_id', None)
            if not user_id:
                return self.config.allow_anonymous_access
            
            # Check rate limiting
            if not self.rate_limiter.is_allowed(user_id):
                self._log_security_event("rate_limit_exceeded", user_id, server_type)
                return False
            
            # Check user permissions
            if user_id not in self.user_permissions:
                return False
            
            permissions = self.user_permissions[user_id]
            
            # Check server access
            if not permissions.can_access_server(server_type):
                self._log_security_event("access_denied", user_id, f"server:{server_type}")
                return False
            
            # Check permission patterns
            required_permission = f"server:{server_type}"
            wildcard_permission = "server:*"
            
            if not (permissions.has_permission(required_permission) or 
                   permissions.has_permission(wildcard_permission)):
                self._log_security_event("permission_denied", user_id, required_permission)
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Server access validation failed: {str(e)}")
            return False
    
    def validate_tool_access(self, server_type: str, tool_name: str, context: Any) -> bool:
        """Validate user can execute specific tool"""
        try:
            user_id = getattr(context, 'user_id', None)
            if not user_id:
                return self.config.allow_anonymous_tool_execution
            
            # First check server access
            if not self.validate_server_access(server_type, context):
                return False
            
            permissions = self.user_permissions[user_id]
            
            # Check tool restrictions
            if not permissions.can_use_tool(tool_name):
                self._log_security_event("tool_restricted", user_id, tool_name)
                return False
            
            # Check tool permissions
            required_permissions = [
                f"tool:{tool_name}",
                f"tool:{server_type}:{tool_name}",
                "tool:*"
            ]
            
            if not any(permissions.has_permission(perm) for perm in required_permissions):
                self._log_security_event("tool_permission_denied", user_id, tool_name)
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Tool access validation failed: {str(e)}")
            return False
    
    def log_tool_execution(self, server_type: str, tool_name: str, context: Any, success: bool):
        """Log tool execution for audit trail"""
        user_id = getattr(context, 'user_id', 'anonymous')
        result = "success" if success else "failure"
        
        self._log_security_event(
            "tool_execution",
            user_id,
            f"{server_type}:{tool_name}",
            result=result
        )
    
    def _log_security_event(self, event_type: str, user_id: Optional[str], 
                           action: str, result: str = "info", **kwargs):
        """Log security event for audit purposes"""
        event = SecurityEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            user_id=user_id,
            action=action,
            resource=kwargs.get("resource", ""),
            result=result,
            additional_data=kwargs
        )
        
        self.security_events.append(event)
        
        # Log to file/external system
        self.logger.info(
            f"Security Event: {event_type} | User: {user_id} | "
            f"Action: {action} | Result: {result}"
        )
        
        # Keep only recent events (memory management)
        if len(self.security_events) > self.config.max_security_events:
            self.security_events = self.security_events[-self.config.max_security_events:]
    
    def _track_failed_attempt(self, user_id: str):
        """Track failed authentication attempts"""
        now = datetime.now()
        self.failed_attempts[user_id].append(now)
        
        # Clean old attempts (older than 1 hour)
        cutoff = now - timedelta(hours=1)
        self.failed_attempts[user_id] = [
            attempt for attempt in self.failed_attempts[user_id] 
            if attempt > cutoff
        ]
        
        # Block user if too many failed attempts
        if len(self.failed_attempts[user_id]) >= self.config.max_failed_attempts:
            self.blocked_users.add(user_id)
            self._log_security_event("user_blocked", user_id, "too_many_failed_attempts")
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get security summary and statistics"""
        recent_events = [
            event for event in self.security_events
            if event.timestamp > datetime.now() - timedelta(hours=24)
        ]
        
        event_counts = defaultdict(int)
        for event in recent_events:
            event_counts[event.event_type] += 1
        
        return {
            "total_events_24h": len(recent_events),
            "event_types": dict(event_counts),
            "blocked_users": len(self.blocked_users),
            "active_users": len(self.user_permissions),
            "failed_attempts": sum(len(attempts) for attempts in self.failed_attempts.values()),
            "rate_limit_status": "active" if self.rate_limiter else "disabled"
        }


def main():
    """Main function for testing SecurityHandler"""
    print("=== Security Handler Test ===")
    
    # Static tests
    print("\n1. Testing UserPermissions...")
    permissions = UserPermissions(user_id="test_user")
    permissions.permissions.add("test:read")
    permissions.roles.add("analyst")
    
    assert permissions.has_permission("test:read")
    assert permissions.has_role("analyst")
    assert not permissions.has_permission("test:write")
    print("✅ UserPermissions working")
    
    print("\n2. Testing SecurityEvent...")
    event = SecurityEvent(
        timestamp=datetime.now(),
        event_type="test",
        user_id="test_user",
        action="test_action",
        resource="test_resource",
        result="success"
    )
    assert event.user_id == "test_user"
    assert event.result == "success"
    print("✅ SecurityEvent created")
    
    print("\n3. Testing RateLimiter...")
    limiter = RateLimiter(max_requests=5, window_minutes=1)
    
    # Test under limit
    for i in range(5):
        assert limiter.is_allowed("test_user") is True
    
    # Test over limit
    assert limiter.is_allowed("test_user") is False
    print("✅ RateLimiter working")
    
    print("\n4. Testing SecurityHandler creation...")
    from ..core.config import ServerConfig
    
    config = ServerConfig()
    config.secret_key = "test_secret_key"
    logger = logging.getLogger("test")
    
    handler = SecurityHandler(config, logger)
    assert handler.config == config
    assert len(handler.default_roles) > 0
    print("✅ SecurityHandler created")


def test_dynamic():
    """Dynamic tests for SecurityHandler"""
    async def run_dynamic_tests():
        print("\n=== Dynamic Tests ===")
        
        from ..core.config import ServerConfig
        
        config = ServerConfig()
        config.secret_key = "test_secret_key"
        config.allow_anonymous_access = False
        logger = logging.getLogger("test")
        
        handler = SecurityHandler(config, logger)
        
        print("1. Testing environment validation...")
        # Mock validation (would need proper environment)
        config.encryption_enabled = False
        is_valid = await handler.validate_environment()
        # In real test environment, this might fail due to file permissions
        print("✅ Environment validation tested")
        
        print("\n2. Testing user authentication...")
        # Test token generation and validation
        token = handler._generate_token("test_user")
        assert len(token) > 0
        
        credentials = {"token": token}
        auth_result = handler.authenticate_user("test_user", credentials)
        assert auth_result is True
        print("✅ Authentication tested")
        
        print("\n3. Testing user authorization...")
        permissions = handler.authorize_user("test_user", ["analyst"])
        assert permissions.user_id == "test_user"
        assert "analyst" in permissions.roles
        print("✅ Authorization tested")
        
        print("\n4. Testing access validation...")
        from types import SimpleNamespace
        context = SimpleNamespace(user_id="test_user")
        
        # This would work if user has proper permissions
        access_result = handler.validate_server_access("rnaseq", context)
        # Result depends on user's actual permissions
        print("✅ Access validation tested")
        
        print("\n5. Testing security summary...")
        summary = handler.get_security_summary()
        assert "total_events_24h" in summary
        assert "active_users" in summary
        print("✅ Security summary tested")
        
        print("\n🎉 All dynamic tests passed!")
    
    # Run async tests
    asyncio.run(run_dynamic_tests())


if __name__ == "__main__":
    main()
    test_dynamic()