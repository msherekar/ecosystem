"""Gliaent backend application factory.

`setup_routes` previously had no call site: there was no app, so the
code-execution surface was never built, served or reviewed. This module
builds it with the security posture the audit called for.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import startup_token
from .routes import setup_routes

logger = logging.getLogger(__name__)

#: Only these origins may call the API. The previous configuration used
#: `allow_origins=["*"]` together with `allow_credentials=True`; Starlette
#: then echoes the request's Origin, so any website the user visited could
#: make credentialed calls to the local API.
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def allowed_origins() -> List[str]:
    """Resolve the CORS allowlist.

    `GLIAENT_ALLOWED_ORIGINS` is a comma-separated override. A literal `*` is
    rejected: with credentials enabled it is not a valid configuration, and
    silently accepting it is how this became a vulnerability.

    Raises:
        ValueError: If the override contains `*`.
    """
    raw = os.environ.get("GLIAENT_ALLOWED_ORIGINS", "").strip()
    if not raw:
        return list(DEFAULT_ALLOWED_ORIGINS)
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if "*" in origins:
        raise ValueError(
            "GLIAENT_ALLOWED_ORIGINS must not contain '*': a wildcard origin "
            "with credentials enabled lets any site call this API. List the "
            "exact origins instead."
        )
    return origins


def create_app(origins: Optional[List[str]] = None) -> FastAPI:
    """Build the backend application.

    Args:
        origins: CORS allowlist override, mainly for tests.

    Returns:
        A configured `FastAPI` app.
    """
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        """Mint the session token the desktop shell authenticates with.

        Logged rather than printed so it lands in the stream the Electron
        main process already reads.
        """
        logger.info("GLIAENT_SESSION_TOKEN=%s", startup_token())
        yield

    app = FastAPI(
        lifespan=lifespan,
        title="Gliaent Backend",
        description=(
            "Sandboxed code execution and module invocation for the Gliaent "
            "analysis environment."
        ),
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins is not None else allowed_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-Gliaent-Token"],
    )

    setup_routes(app)

    return app


app = create_app()
