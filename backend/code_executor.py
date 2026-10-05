"""Code execution endpoint logic.

Thin adapter over `backend.sandbox`. The isolation and the limits live there;
this module only translates between the HTTP models and the sandbox.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import HTTPException

from .models import CodeRequest, CodeResponse
from .sandbox import SandboxPolicy, run_untrusted_python

logger = logging.getLogger(__name__)


async def execute_code(request: CodeRequest) -> CodeResponse:
    """Run submitted Python under the sandbox.

    Args:
        request: Validated source and limits.

    Returns:
        A `CodeResponse`. A non-zero exit, a raised exception in the user's
        code, or a timeout are all normal outcomes and come back as 200 with
        the detail in `error` — they are not server errors.

    Raises:
        HTTPException: 400 if the sandbox rejects the input outright, 500 if
            the sandbox itself fails to start.
    """
    policy = SandboxPolicy(
        timeout_seconds=request.timeout,
        memory_mb=request.memory_mb,
        allow_network=request.allow_network,
    )

    try:
        # The sandbox is blocking (subprocess + communicate); run it off the
        # event loop so one long execution does not stall the whole server.
        result = await asyncio.to_thread(run_untrusted_python, request.code, policy)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        logger.exception("sandbox failed to start")
        raise HTTPException(
            status_code=500, detail=f"Sandbox failed to start: {exc}"
        ) from exc

    logger.info(
        "execution finished: exit=%s timed_out=%s duration=%.3fs isolation=%s",
        result.exit_code,
        result.timed_out,
        result.duration_seconds,
        ",".join(result.isolation),
    )

    return CodeResponse(
        output=result.stdout,
        error=result.stderr or None,
        exit_code=result.exit_code,
        timed_out=result.timed_out,
        duration_seconds=result.duration_seconds,
        truncated=result.truncated,
        isolation=result.isolation,
    )
