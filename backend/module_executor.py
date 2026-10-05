"""Invoke a function in one of Gliaent's bundled analysis modules.

Only modules shipped inside `src/modules` are reachable, resolved against a
fixed root and verified to be inside it. The previous implementation
interpolated the caller's `module_name` into a path with no containment check
and then called `spec.loader.exec_module`, so `{"module_name":
"../../../../tmp"}` executed an arbitrary file.
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import logging
from pathlib import Path
from typing import Any, Dict, List

from fastapi import HTTPException

from .models import ModuleExecuteRequest

logger = logging.getLogger(__name__)

#: Resolved from this file rather than the process CWD. The scanner and
#: executor previously used a relative Path("src/modules"), so both silently
#: returned nothing whenever uvicorn was started from another directory.
MODULES_ROOT = (Path(__file__).resolve().parent.parent / "src" / "modules").resolve()

#: Importable prefix corresponding to MODULES_ROOT.
MODULES_PACKAGE = "modules"


def _resolve_module_dir(module_name: str) -> Path:
    """Resolve a module directory, refusing anything outside MODULES_ROOT.

    `module_name` is already constrained to a bare identifier by
    `ModuleExecuteRequest`; this is the second, independent check, because a
    containment bug should require two mistakes rather than one.

    Raises:
        HTTPException: 404 if the module does not exist, 400 if the resolved
            path escapes the modules root.
    """
    candidate = (MODULES_ROOT / module_name).resolve()
    if not candidate.is_relative_to(MODULES_ROOT):
        raise HTTPException(
            status_code=400,
            detail=f"module path escapes the modules directory: {module_name!r}",
        )
    if not candidate.is_dir():
        available = sorted(
            p.name for p in MODULES_ROOT.iterdir()
            if p.is_dir() and not p.name.startswith(("_", "."))
        )
        raise HTTPException(
            status_code=404,
            detail=f"no module {module_name!r} (available: {', '.join(available)})",
        )
    return candidate


async def execute_module_function(request: ModuleExecuteRequest) -> Dict[str, Any]:
    """Call `function_name` in `module_name` with `params`.

    The module is imported through `importlib.import_module` using its proper
    package path, so it is loaded once and shares identity with every other
    import of it. The previous `spec_from_file_location` +
    `exec_module` approach loaded a second, independent copy on every call,
    duplicating any module-level registry or singleton it defined.

    Args:
        request: Validated module, function and keyword arguments.

    Returns:
        `{"success": True, "result": ...}` on success.

    Raises:
        HTTPException: 404 for an unknown module or function, 400 for
            arguments that do not match the signature, 500 for an error
            raised inside the called function.
    """
    _resolve_module_dir(request.module_name)

    dotted = f"{MODULES_PACKAGE}.{request.module_name}"
    try:
        module = importlib.import_module(dotted)
    except ImportError as exc:
        # Surfaced rather than swallowed: an ImportError here usually means a
        # missing optional dependency, which the user can act on.
        raise HTTPException(
            status_code=500,
            detail=f"could not import {dotted}: {exc}",
        ) from exc

    target = getattr(module, request.function_name, None)
    if target is None:
        exported = sorted(
            name for name, value in vars(module).items()
            if callable(value) and not name.startswith("_")
        )
        raise HTTPException(
            status_code=404,
            detail=(
                f"{dotted} has no function {request.function_name!r} "
                f"(callable: {', '.join(exported) or 'none'})"
            ),
        )
    if not callable(target):
        raise HTTPException(
            status_code=400,
            detail=f"{dotted}.{request.function_name} is not callable",
        )

    # Reject unexpected keywords here, with the signature in the message,
    # instead of letting Python raise a bare TypeError from inside the call.
    try:
        inspect.signature(target).bind(**request.params)
    except TypeError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                f"arguments do not match {request.function_name}"
                f"{inspect.signature(target)}: {exc}"
            ),
        ) from exc

    try:
        if inspect.iscoroutinefunction(target):
            result = await target(**request.params)
        else:
            result = await asyncio.to_thread(lambda: target(**request.params))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("module function %s.%s failed", dotted, request.function_name)
        raise HTTPException(
            status_code=500,
            detail=f"{request.function_name} raised {type(exc).__name__}: {exc}",
        ) from exc

    return {"success": True, "result": _jsonable(result)}


def _jsonable(value: Any) -> Any:
    """Make a return value safe to serialise.

    Analysis functions commonly return DataFrames, which FastAPI cannot
    encode. Converting here, with a row cap, beats a 500 from the serialiser.
    """
    try:
        import pandas as pd

        if isinstance(value, pd.DataFrame):
            capped = value.head(1000)
            return {
                "type": "dataframe",
                "rows": int(len(value)),
                "truncated": bool(len(value) > len(capped)),
                "columns": [str(c) for c in value.columns],
                "data": capped.to_dict(orient="records"),
            }
        if isinstance(value, pd.Series):
            return {"type": "series", "data": value.head(1000).to_dict()}
    except ImportError:
        pass
    return value


def list_module_names() -> List[str]:
    """Names of the bundled analysis modules."""
    if not MODULES_ROOT.is_dir():
        return []
    return sorted(
        p.name
        for p in MODULES_ROOT.iterdir()
        if p.is_dir() and not p.name.startswith(("_", "."))
    )
