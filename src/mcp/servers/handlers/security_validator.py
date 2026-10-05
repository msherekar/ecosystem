"""Input validation and audit logging for MCP handlers.

What changed and why:

**The denylist is gone.** This class used to reject any parameter matching
patterns like ``(__import__|exec|eval|compile)`` case-insensitively, plus
``(DROP|DELETE|UPDATE|INSERT)\\s+``. It bought no security — these are
*parameter values*, not executed code, and a denylist does not stop
``getattr(__builtins__, "ex" + "ec")`` anyway — while breaking ordinary use:
"run **eval**uation of binding curves" and "**delete** the outlier samples"
were both rejected as attacks. Code isolation lives in ``backend.sandbox``,
which bounds what executed code can do.

**The upload allowlist now includes protein formats.** It previously permitted
only ``.h5ad .csv .tsv .xlsx .h5 .mtx .gz``, so a biochemist could not upload
a PDB, mmCIF or FASTA file at all.

**The audit log records parameters instead of hashing them.** A SHA-256 of
the parameters cannot be used to reconstruct what was run, which is the one
thing a scientific audit trail needs.
"""

from __future__ import annotations

import json
import logging
import re
import threading
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Set

#: Formats Gliaent can ingest, grouped by what they are.
TABULAR_EXTENSIONS = {".csv", ".tsv", ".txt", ".xlsx", ".parquet"}
OMICS_EXTENSIONS = {".h5ad", ".h5", ".mtx", ".loom", ".rds"}
#: Protein formats. Their absence is why the structure viewer had nothing to
#: show and why a biochemist could not load their own data.
SEQUENCE_EXTENSIONS = {".fasta", ".fa", ".faa", ".fas", ".seq", ".a3m", ".sto", ".aln"}
STRUCTURE_EXTENSIONS = {".pdb", ".cif", ".mmcif", ".ent", ".pdbqt", ".sdf", ".mol2", ".xyz"}
MASS_SPEC_EXTENSIONS = {".mzml", ".mzxml", ".mgf", ".raw", ".pepxml", ".mzid"}
#: Instrument exports: plate readers, SPR, ITC, DSF.
ASSAY_EXTENSIONS = {".xls", ".json", ".xml", ".dat", ".asc"}
#: Compression suffixes, checked against the extension *underneath*.
COMPRESSION_EXTENSIONS = {".gz", ".bz2", ".xz", ".zip"}

DEFAULT_ALLOWED_EXTENSIONS: Set[str] = (
    TABULAR_EXTENSIONS
    | OMICS_EXTENSIONS
    | SEQUENCE_EXTENSIONS
    | STRUCTURE_EXTENSIONS
    | MASS_SPEC_EXTENSIONS
    | ASSAY_EXTENSIONS
)

DEFAULT_MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024  # 2 GiB: omics files are large

#: Parameter names must be plain identifiers.
_SAFE_PARAM_NAME = re.compile(r"^[A-Za-z0-9_-]{1,128}$")

#: Characters never valid in a filename we accept.
_UNSAFE_FILENAME_CHARS = set('/\\:*?"<>|\x00')

MAX_PARAM_VALUE_LENGTH = 100_000


class SecurityValidator:
    """Validates handler inputs and records an audit trail."""

    #: Cap on tracked rate-limit keys, so the dict cannot grow without bound.
    MAX_TRACKED_OPERATIONS = 10_000

    def __init__(
        self,
        audit_log_path: str = "logs/security_audit.log",
        allowed_extensions: Set[str] | None = None,
        max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
        max_operations_per_minute: int = 60,
    ) -> None:
        self.audit_log_path = Path(audit_log_path)
        self.allowed_extensions = set(
            allowed_extensions if allowed_extensions is not None
            else DEFAULT_ALLOWED_EXTENSIONS
        )
        self.max_upload_bytes = max_upload_bytes
        self.max_operations_per_minute = max_operations_per_minute

        self._operation_counts: Dict[str, Deque[datetime]] = {}
        self._lock = threading.Lock()

        self.security_logger = self._build_logger()

    def _build_logger(self) -> logging.Logger:
        """Attach a file handler exactly once.

        The previous version added a new `FileHandler` to the shared global
        "security" logger inside every `__init__`, so N instances meant N
        handlers on one logger: duplicated log lines and a leaked file
        descriptor per instance.
        """
        logger = logging.getLogger("gliaent.security")
        logger.setLevel(logging.INFO)

        target = str(self.audit_log_path.resolve())
        for existing in logger.handlers:
            if getattr(existing, "_gliaent_target", None) == target:
                return logger

        try:
            self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
            handler: logging.Handler = logging.FileHandler(self.audit_log_path)
        except OSError as exc:
            # An unwritable log directory must not stop the server; fall back
            # to stderr and say so.
            logger.warning("audit log unavailable at %s (%s)", target, exc)
            handler = logging.StreamHandler()

        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        handler._gliaent_target = target  # type: ignore[attr-defined]
        logger.addHandler(handler)
        return logger

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate handler parameters.

        Checks structure only: that names are identifiers and values are not
        absurdly large. It does NOT inspect values for "dangerous" words.

        Args:
            params: Parameters to check.

        Returns:
            `{"valid": bool, "errors": [str, ...]}`
        """
        errors: List[str] = []

        for key, value in params.items():
            if not _SAFE_PARAM_NAME.match(str(key)):
                errors.append(
                    f"invalid parameter name {key!r}: expected letters, digits, "
                    "underscore or hyphen"
                )
                continue
            for item in value if isinstance(value, (list, tuple)) else [value]:
                if isinstance(item, str) and len(item) > MAX_PARAM_VALUE_LENGTH:
                    errors.append(
                        f"parameter {key!r} is {len(item)} characters, over the "
                        f"{MAX_PARAM_VALUE_LENGTH} limit"
                    )

        return {"valid": not errors, "errors": errors}

    def validate_file_upload(self, filename: str, file_size: int) -> Dict[str, Any]:
        """Validate an upload's name, extension and size.

        Args:
            filename: The client-supplied name. Only the basename is used.
            file_size: Size in bytes.

        Returns:
            `{"valid": bool, "errors": [str, ...], "extension": str}`
        """
        errors: List[str] = []

        if not filename or not filename.strip():
            return {"valid": False, "errors": ["filename is empty"], "extension": ""}

        # Only ever consider the basename: a client sending "../../x.csv"
        # should fail on the path, not be silently accepted by suffix.
        base = Path(filename).name
        if base != filename.strip():
            errors.append("filename must not contain a path")
        if any(c in base for c in _UNSAFE_FILENAME_CHARS):
            errors.append("filename contains characters that are not permitted")
        if base.startswith("."):
            errors.append("filename must not start with a dot")

        extension = self._effective_extension(base)
        if extension not in self.allowed_extensions:
            errors.append(
                f"file type {extension or '(none)'} is not supported. "
                f"Supported: {', '.join(sorted(self.allowed_extensions))}"
            )

        if file_size < 0:
            errors.append("file size cannot be negative")
        elif file_size > self.max_upload_bytes:
            errors.append(
                f"file is {file_size / 1e9:.2f} GB, over the "
                f"{self.max_upload_bytes / 1e9:.2f} GB limit"
            )

        return {"valid": not errors, "errors": errors, "extension": extension}

    def _effective_extension(self, filename: str) -> str:
        """The meaningful extension, looking through compression suffixes.

        `counts.csv.gz` reports `.csv`, not `.gz`, so a compressed file is
        judged on what it actually contains.
        """
        suffixes = [s.lower() for s in Path(filename).suffixes]
        if not suffixes:
            return ""
        if suffixes[-1] in COMPRESSION_EXTENSIONS and len(suffixes) >= 2:
            return suffixes[-2]
        return suffixes[-1]

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def check_rate_limit(self, operation_key: str) -> bool:
        """Whether `operation_key` is within its per-minute budget.

        Thread-safe, and bounded: idle keys are evicted so the tracking dict
        cannot grow without limit.
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=60)

        with self._lock:
            self._evict_idle_locked(cutoff)
            window = self._operation_counts.setdefault(operation_key, deque())
            while window and window[0] < cutoff:
                window.popleft()

            if len(window) >= self.max_operations_per_minute:
                return False

            window.append(now)
            return True

    def _evict_idle_locked(self, cutoff: datetime) -> None:
        for key in [
            k for k, window in self._operation_counts.items()
            if not window or window[-1] < cutoff
        ]:
            del self._operation_counts[key]
        while len(self._operation_counts) > self.MAX_TRACKED_OPERATIONS:
            stalest = min(
                self._operation_counts,
                key=lambda k: self._operation_counts[k][-1],
            )
            del self._operation_counts[stalest]

    # ------------------------------------------------------------------
    # Audit trail
    # ------------------------------------------------------------------

    def audit_operation(
        self, technique: str, operation: str, parameters: Dict[str, Any]
    ) -> None:
        """Record an operation and the parameters it ran with.

        Parameters are recorded, not hashed. The previous version stored a
        truncated SHA-256 of them, which is useless for the purpose an audit
        trail serves in science: reconstructing what was actually run.
        Oversized values are summarised rather than dropped.
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "technique": technique,
            "operation": operation,
            "parameters": {k: _summarise(v) for k, v in parameters.items()},
        }
        self.security_logger.info("AUDIT %s", json.dumps(entry, default=str))

    def get_security_report(self) -> Dict[str, Any]:
        """Current validator state.

        `recent_operations_count` covers the last minute, matching the window
        `check_rate_limit` actually retains. The previous version reported a
        "last hour" count over data pruned at 60 seconds, so the number was
        always wrong.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=60)
        with self._lock:
            recent = sum(
                sum(1 for t in window if t >= cutoff)
                for window in self._operation_counts.values()
            )
            tracked = len(self._operation_counts)

        return {
            "audit_log_exists": self.audit_log_path.exists(),
            "operations_last_minute": recent,
            "tracked_operation_keys": tracked,
            "rate_limit_per_minute": self.max_operations_per_minute,
            "max_upload_bytes": self.max_upload_bytes,
            "allowed_extensions": sorted(self.allowed_extensions),
        }


def _summarise(value: Any, limit: int = 2000) -> Any:
    """Shrink a value for the audit log without losing its identity."""
    if isinstance(value, str) and len(value) > limit:
        return f"{value[:limit]}... ({len(value)} chars total)"
    if isinstance(value, (list, tuple)) and len(value) > 50:
        return list(value[:50]) + [f"... ({len(value)} items total)"]
    if hasattr(value, "shape"):  # DataFrame / ndarray
        return {"type": type(value).__name__, "shape": list(getattr(value, "shape"))}
    return value
