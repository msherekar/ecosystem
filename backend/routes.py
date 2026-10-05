"""Gliaent backend API routes.

Every endpoint that executes code or reads the filesystem requires a session
token. Previously none of them did, and `setup_routes` had no call site at
all, so this surface was never exercised or reviewed.
"""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI

from .auth import Session, require_session
from .code_executor import execute_code
from .models import (
    CodeRequest,
    CodeResponse,
    ModuleExecuteRequest,
    ModuleInfoRequest,
    ModuleListResponse,
)
from .module_executor import execute_module_function
from .module_scanner import get_module_details, scan_modules
from .sandbox import describe_isolation

logger = logging.getLogger(__name__)


def setup_routes(app: FastAPI) -> FastAPI:
    """Register the backend routes on `app`.

    Args:
        app: The FastAPI application.

    Returns:
        The same app, for chaining.
    """

    @app.get("/sandbox/isolation")
    async def sandbox_isolation() -> dict:
        """Report which isolation layers this host provides.

        Unauthenticated on purpose: the UI needs it to warn the user before
        they run anything, and it reveals no secrets.
        """
        return describe_isolation()

    @app.post("/execute", response_model=CodeResponse)
    async def execute_python_code(
        request: CodeRequest,
        session: Session = Depends(require_session),
    ) -> CodeResponse:
        """Execute Python in the sandbox.

        Requires a session token. See `backend.sandbox` for the isolation
        layers applied.
        """
        logger.info("execute requested by session %r", session.label)
        return await execute_code(request)

    @app.get("/modules", response_model=ModuleListResponse)
    async def list_available_modules(
        session: Session = Depends(require_session),
    ) -> ModuleListResponse:
        """List the bundled analysis modules."""
        return ModuleListResponse(modules=scan_modules())

    @app.post("/module-info")
    async def get_module_info(
        request: ModuleInfoRequest,
        session: Session = Depends(require_session),
    ) -> dict:
        """Describe one bundled module."""
        return get_module_details(request.module_name)

    @app.post("/execute-module")
    async def run_module_function(
        request: ModuleExecuteRequest,
        session: Session = Depends(require_session),
    ) -> dict:
        """Call a function in a bundled module.

        `request` is a validated model rather than a bare dict, which is what
        allowed unvalidated path components to reach `exec_module`.
        """
        logger.info(
            "module execution requested by %r: %s.%s",
            session.label,
            request.module_name,
            request.function_name,
        )
        return await execute_module_function(request)

    return app
