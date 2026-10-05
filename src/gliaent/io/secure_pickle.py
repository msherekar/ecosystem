"""Integrity-checked pickle for data that crosses a trust boundary.

The on-disk and Redis caches pickled arbitrary Python objects and read them
back with no verification — the filename was an MD5 of the cache key, which
is a checksum of the *key*, not a MAC of the *contents*. Any local process
that could write one `.cache` file under `~/.mcp_servers`, or influence a
shared Redis, got code execution the next time the cache was read.

Replacing pickle with JSON was not viable: the cache legitimately holds
DataFrames and AnnData objects that JSON cannot represent, and converting
them would change what the cache is for. Instead, every payload leaving the
process is wrapped in an HMAC-SHA256 envelope and verified before
`pickle.loads` is ever reached. Unpickling still runs arbitrary code by
design, so the guarantee is specifically: *nothing is unpickled that this
installation did not write*.

Within a single process there is no trust boundary, so plain pickle is fine
for things like the in-memory compression round-trip.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import pickle
import struct
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

#: Envelope layout: MAGIC | version | 32-byte HMAC-SHA256 | payload
_MAGIC = b"GLIAENT1"
_VERSION = 1
_DIGEST_SIZE = hashlib.sha256().digest_size
_HEADER = struct.Struct(f"<8sB{_DIGEST_SIZE}s")

#: Pickle protocol 5 supports out-of-band buffers for large arrays.
_PICKLE_PROTOCOL = 5


class IntegrityError(Exception):
    """A payload failed verification and was not deserialised.

    Raised rather than returning None so a tampered cache entry cannot be
    mistaken for a cache miss.
    """


def _signing_key() -> bytes:
    """The HMAC key for cache envelopes.

    Derived from the configured secret. When none is set, a per-installation
    key is generated and stored with owner-only permissions — so even an
    unconfigured install verifies its own writes, rather than falling back to
    no verification at all.
    """
    secret = os.environ.get("GLIAENT_SECRET_KEY") or os.environ.get("MCP_SECRET_KEY")
    if secret:
        return hashlib.sha256(secret.encode()).digest()

    key_path = Path(
        os.environ.get("GLIAENT_DATA_DIR", Path.home() / ".gliaent")
    ) / "cache_signing.key"
    try:
        if key_path.exists():
            return key_path.read_bytes()
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key = os.urandom(32)
        # Write then chmod before any other process is likely to see it.
        key_path.write_bytes(key)
        key_path.chmod(0o600)
        logger.info("generated a cache signing key at %s", key_path)
        return key
    except OSError as exc:
        # A read-only home is not fatal: fall back to a process-lifetime key.
        # Persisted entries then fail verification after a restart, which is
        # the safe direction to fail in.
        logger.warning(
            "could not persist a cache signing key (%s); using an ephemeral "
            "key, so on-disk cache entries will not survive a restart",
            exc,
        )
        global _EPHEMERAL_KEY
        if _EPHEMERAL_KEY is None:
            _EPHEMERAL_KEY = os.urandom(32)
        return _EPHEMERAL_KEY


_EPHEMERAL_KEY: Optional[bytes] = None


def dumps_signed(value: Any, key: Optional[bytes] = None) -> bytes:
    """Serialise `value` into a signed envelope.

    Args:
        value: Any picklable object.
        key: Signing key. Defaults to this installation's key.

    Returns:
        The envelope bytes.

    Raises:
        pickle.PicklingError: If `value` cannot be pickled.
    """
    payload = pickle.dumps(value, protocol=_PICKLE_PROTOCOL)
    digest = hmac.new(key or _signing_key(), payload, hashlib.sha256).digest()
    return _HEADER.pack(_MAGIC, _VERSION, digest) + payload


def loads_signed(blob: bytes, key: Optional[bytes] = None) -> Any:
    """Verify and deserialise a signed envelope.

    Verification happens before `pickle.loads` is called, so a forged payload
    never reaches the unpickler.

    Args:
        blob: Envelope produced by `dumps_signed`.
        key: Signing key. Defaults to this installation's key.

    Returns:
        The deserialised object.

    Raises:
        IntegrityError: If the envelope is truncated, has the wrong magic or
            version, or fails the MAC check.
    """
    if len(blob) < _HEADER.size:
        raise IntegrityError(
            f"payload is {len(blob)} bytes, shorter than the "
            f"{_HEADER.size}-byte envelope header"
        )

    magic, version, digest = _HEADER.unpack(blob[: _HEADER.size])
    payload = blob[_HEADER.size :]

    if magic != _MAGIC:
        raise IntegrityError(
            "not a Gliaent cache envelope (wrong magic). An unsigned pickle "
            "from an older version will not be loaded; delete the cache."
        )
    if version != _VERSION:
        raise IntegrityError(f"unsupported envelope version {version}")

    expected = hmac.new(key or _signing_key(), payload, hashlib.sha256).digest()
    if not hmac.compare_digest(digest, expected):
        raise IntegrityError(
            "cache entry failed its integrity check and was NOT deserialised. "
            "It was written by a different installation or has been tampered "
            "with."
        )

    return pickle.loads(payload)


def dump_signed(value: Any, path: str | Path, key: Optional[bytes] = None) -> None:
    """Write `value` to `path` as a signed envelope.

    Written to a temporary file and renamed, so a crash mid-write cannot leave
    a truncated entry that later fails verification.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_bytes(dumps_signed(value, key=key))
    temp.replace(target)


def load_signed(path: str | Path, key: Optional[bytes] = None) -> Any:
    """Read and verify a signed envelope from `path`.

    Raises:
        IntegrityError: If verification fails.
        FileNotFoundError: If `path` does not exist.
    """
    return loads_signed(Path(path).read_bytes(), key=key)
