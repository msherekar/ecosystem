#!/usr/bin/env python3
"""Launch the Gliaent API server.

Binds loopback by default. The previous version bound 0.0.0.0 with
`reload=True`, exposing an unauthenticated API — including the code-execution
endpoints — to the whole local network.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SRC = REPO_ROOT / "src"


def main() -> None:
    """Run the server."""
    # PYTHONPATH must be set before uvicorn's reloader forks its child, and
    # with `=` not `setdefault`: an inherited PYTHONPATH previously won,
    # leaving the reload child unable to import the app.
    existing = os.environ.get("PYTHONPATH", "")
    parts = [str(SRC), str(REPO_ROOT)] + ([existing] if existing else [])
    os.environ["PYTHONPATH"] = os.pathsep.join(parts)
    for path in (str(SRC), str(REPO_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)

    import uvicorn

    dev = os.environ.get("GLIAENT_DEV", "0").strip().lower() in {"1", "true", "yes"}
    host = os.environ.get("GLIAENT_HOST", "127.0.0.1")

    if host not in {"127.0.0.1", "localhost", "::1"}:
        print(
            f"WARNING: binding {host} exposes this API beyond this machine.\n"
            "         Every caller can execute code through /execute. Only do "
            "this behind an authenticating proxy.",
            file=sys.stderr,
        )

    uvicorn.run(
        "backend.app:app",
        host=host,
        port=int(os.environ.get("GLIAENT_PORT", "8000")),
        reload=dev,
        log_level=os.environ.get("GLIAENT_LOG_LEVEL", "info"),
        access_log=True,
    )


if __name__ == "__main__":
    main()
