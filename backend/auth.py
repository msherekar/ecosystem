"""Session authentication for the Gliaent API.

Replaces a scheme in which `_generate_token(user_id)` was
`HMAC(secret, f"{user_id}:{secret}:{hour}")` and `authenticate_user` compared
the supplied token against that same derivation. Since the input was the
caller's own user id and the secret defaulted to the literal
`"default_secret_change_me"`, anyone could mint a valid token for any user.

This replacement is a plain opaque bearer token:

- generated from `secrets.token_urlsafe`, so it cannot be derived from
  anything the client knows;
- stored server-side with an expiry, so it can be revoked;
- compared with `secrets.compare_digest`, so comparison is constant-time.

The endpoints that execute code require it. On a single-user desktop install
the token is minted at startup and handed to the Electron main process, which
is why `GLIAENT_DEV=1` is supported: it prints a fixed development token
rather than silently disabling the check.
"""

from __future__ import annotations

import logging
import os
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional

from fastapi import Header, HTTPException, status

logger = logging.getLogger(__name__)

#: Tokens live this long. Short enough that a leaked one expires, long enough
#: for a working session.
TOKEN_TTL_SECONDS = 12 * 60 * 60

#: Cap on stored sessions. Unbounded growth keyed by a caller-supplied id is
#: how the previous rate limiter could be defeated: every new id got a fresh
#: budget and the dict was never pruned.
MAX_SESSIONS = 1000

DEV_TOKEN = "gliaent-dev-token"  # noqa: S105 - only valid when GLIAENT_DEV=1


@dataclass
class Session:
    """One authenticated session."""

    token: str
    label: str
    created_at: float
    expires_at: float

    @property
    def expired(self) -> bool:
        return time.time() >= self.expires_at


class SessionStore:
    """In-memory session registry.

    Thread-safe: FastAPI runs sync endpoints in a thread pool, so this is
    touched concurrently.
    """

    def __init__(self, ttl_seconds: int = TOKEN_TTL_SECONDS) -> None:
        self._sessions: Dict[str, Session] = {}
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def issue(self, label: str = "session") -> Session:
        """Mint a new token.

        Args:
            label: Human-readable tag for logs. Never used in the token.

        Returns:
            The new `Session`.
        """
        now = time.time()
        session = Session(
            token=secrets.token_urlsafe(32),
            label=label,
            created_at=now,
            expires_at=now + self._ttl,
        )
        with self._lock:
            self._prune_locked()
            if len(self._sessions) >= MAX_SESSIONS:
                # Drop the oldest rather than growing without bound.
                oldest = min(self._sessions.values(), key=lambda s: s.created_at)
                self._sessions.pop(oldest.token, None)
            self._sessions[session.token] = session
        logger.info("issued session token for %r", label)
        return session

    def verify(self, token: Optional[str]) -> Optional[Session]:
        """Return the session for `token`, or None.

        Uses `compare_digest` against each candidate so a timing side channel
        does not reveal a valid prefix.
        """
        if not token:
            return None
        with self._lock:
            self._prune_locked()
            for stored, session in self._sessions.items():
                if secrets.compare_digest(stored, token):
                    return session
        return None

    def revoke(self, token: str) -> bool:
        with self._lock:
            return self._sessions.pop(token, None) is not None

    def _prune_locked(self) -> None:
        expired = [t for t, s in self._sessions.items() if s.expired]
        for token in expired:
            del self._sessions[token]

    def __len__(self) -> int:
        with self._lock:
            self._prune_locked()
            return len(self._sessions)


#: Process-wide store. One per server process.
session_store = SessionStore()


def dev_mode() -> bool:
    """Whether development mode is on.

    Explicit opt-in via `GLIAENT_DEV=1`. There is no implicit "no secret
    configured means no auth" path, which is how `allow_anonymous_access`
    defaulting to True previously left every install open.
    """
    return os.environ.get("GLIAENT_DEV", "0").strip().lower() in {"1", "true", "yes"}


async def require_session(
    authorization: Optional[str] = Header(default=None),
    x_gliaent_token: Optional[str] = Header(default=None),
) -> Session:
    """FastAPI dependency enforcing a valid session token.

    Accepts `Authorization: Bearer <token>` or `X-Gliaent-Token: <token>`.

    Returns:
        The authenticated `Session`.

    Raises:
        HTTPException: 401 if the token is missing, unknown or expired.
    """
    token = x_gliaent_token
    if not token and authorization:
        scheme, _, candidate = authorization.partition(" ")
        if scheme.lower() == "bearer":
            token = candidate.strip()

    if dev_mode() and token == DEV_TOKEN:
        return Session(
            token=DEV_TOKEN,
            label="dev",
            created_at=time.time(),
            expires_at=time.time() + TOKEN_TTL_SECONDS,
        )

    session = session_store.verify(token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "A valid session token is required. Send it as "
                "'Authorization: Bearer <token>'. The desktop app receives one "
                "at startup; for local development set GLIAENT_DEV=1 and use "
                f"the token {DEV_TOKEN!r}."
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )
    return session


def startup_token() -> str:
    """Mint the token handed to the desktop shell at startup."""
    if dev_mode():
        logger.warning(
            "GLIAENT_DEV=1: accepting the fixed development token. "
            "Never set this in a deployment."
        )
        return DEV_TOKEN
    return session_store.issue(label="desktop").token
