"""Pydantic models for the Gliaent backend.

Validation lives here rather than in handlers, so a malformed request is
rejected at the boundary with a 422 naming the field instead of becoming a
confusing failure deeper in.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from .sandbox import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_CODE_BYTES,
    MAX_TIMEOUT_SECONDS,
    MIN_TIMEOUT_SECONDS,
)

#: A module or function name must be a bare Python identifier. This is the
#: containment check for `/execute-module`, whose `module_name` was previously
#: interpolated straight into a filesystem path — "../../../../tmp" escaped
#: src/modules entirely and the file was then exec'd.
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class CodeRequest(BaseModel):
    """A request to execute Python source."""

    code: str = Field(
        ...,
        min_length=1,
        max_length=MAX_CODE_BYTES,
        description="Python source to execute in the sandbox.",
    )
    timeout: int = Field(
        DEFAULT_TIMEOUT_SECONDS,
        ge=MIN_TIMEOUT_SECONDS,
        le=MAX_TIMEOUT_SECONDS,
        description=(
            "Wall-clock limit in seconds. Required to be finite: this field "
            "was previously Optional[int], so `null` meant no timeout at all."
        ),
    )
    allow_network: bool = Field(
        False,
        description="Opt in to network access for this run. Off by default.",
    )
    memory_mb: int = Field(2048, ge=64, le=32768)

    @field_validator("code")
    @classmethod
    def code_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("code must not be blank")
        return value


class CodeResponse(BaseModel):
    """The outcome of a sandboxed execution."""

    output: str
    error: Optional[str] = None
    exit_code: int
    timed_out: bool = False
    duration_seconds: float = 0.0
    truncated: bool = False
    isolation: List[str] = Field(
        default_factory=list,
        description="Isolation layers actually applied to this run.",
    )


class ModuleListResponse(BaseModel):
    modules: List[Dict[str, Any]]


class ModuleInfoRequest(BaseModel):
    """A request for metadata about one bundled module."""

    module_name: str = Field(..., min_length=1, max_length=128)

    @field_validator("module_name")
    @classmethod
    def must_be_a_bare_identifier(cls, value: str) -> str:
        if not _IDENTIFIER_RE.match(value):
            raise ValueError(
                "module_name must be a bare Python identifier "
                "(letters, digits, underscore; not starting with a digit). "
                "Path separators and '..' are rejected."
            )
        return value


class ModuleExecuteRequest(BaseModel):
    """A request to call a function in a bundled module.

    Replaces the untyped `request: dict` the endpoint previously accepted,
    which is how unvalidated path components reached `exec_module`.
    """

    module_name: str = Field(..., min_length=1, max_length=128)
    function_name: str = Field("main", min_length=1, max_length=128)
    params: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("module_name", "function_name")
    @classmethod
    def must_be_a_bare_identifier(cls, value: str) -> str:
        if not _IDENTIFIER_RE.match(value):
            raise ValueError(
                "module_name and function_name must be bare Python identifiers; "
                "path separators and '..' are rejected."
            )
        return value
