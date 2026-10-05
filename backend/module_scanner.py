"""Discover the bundled analysis modules.

Paths are resolved from this file, not the process CWD. Both functions here
previously used a relative `Path("src/modules")`, so the `/modules` endpoint
returned an empty list whenever uvicorn was started from anywhere but the
repository root — indistinguishable from "no modules installed".

Returned paths are relative to the repository root. The previous version
returned absolute filesystem paths, which leaks the server's directory layout
to any client.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any, Dict, List

from fastapi import HTTPException

from .module_executor import MODULES_ROOT

logger = logging.getLogger(__name__)

REPO_ROOT = MODULES_ROOT.parent.parent
EXAMPLES_ROOT = (REPO_ROOT / "examples").resolve()

_SKIP_NAMES = {"__pycache__", ".DS_Store"}


def _is_module_dir(path: Path) -> bool:
    return (
        path.is_dir()
        and not path.name.startswith((".", "__"))
        and path.name not in _SKIP_NAMES
    )


def _relative(path: Path) -> str:
    """Render a path relative to the repo root, never absolute."""
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:  # pragma: no cover - outside the repo
        return path.name


def scan_modules() -> List[Dict[str, Any]]:
    """List the available analysis modules.

    Returns:
        One dict per module with `name`, `path` (repo-relative),
        `display_name`, `available` and `type`.
    """
    if not MODULES_ROOT.is_dir():
        logger.warning("modules root does not exist: %s", MODULES_ROOT)
        return []

    modules = []
    for module_dir in sorted(MODULES_ROOT.iterdir()):
        if not _is_module_dir(module_dir):
            continue
        modules.append(
            {
                "name": module_dir.name,
                "path": _relative(module_dir),
                "display_name": module_dir.name.replace("_", " ").title(),
                "available": any(module_dir.glob("*.py")),
                "type": get_module_type(module_dir),
            }
        )
    return modules


def get_module_type(module_dir: Path) -> str:
    """Classify a module by the files it contains."""
    if (module_dir / "workflow.py").exists():
        return "workflow"
    if (module_dir / "streamlit_app.py").exists():
        return "streamlit_app"
    return "module"


def get_module_details(module_name: str) -> Dict[str, Any]:
    """Describe one module.

    Args:
        module_name: A bare module name. Validated by `ModuleInfoRequest`;
            re-checked here for containment.

    Returns:
        Name, repo-relative path, Python files, examples and description.

    Raises:
        HTTPException: 400 if the path escapes the modules root, 404 if the
            module does not exist.
    """
    candidate = (MODULES_ROOT / module_name).resolve()
    if not candidate.is_relative_to(MODULES_ROOT):
        raise HTTPException(
            status_code=400,
            detail=f"module path escapes the modules directory: {module_name!r}",
        )
    if not candidate.is_dir():
        raise HTTPException(status_code=404, detail=f"no module {module_name!r}")

    return {
        "name": module_name,
        "path": _relative(candidate),
        "files": [
            {"name": f.name, "path": _relative(f), "type": "python"}
            for f in sorted(candidate.glob("*.py"))
        ],
        "examples": get_examples(module_name),
        "description": extract_description(candidate),
    }


def get_examples(module_name: str) -> List[Dict[str, str]]:
    """List example scripts for a module, if any."""
    candidate = (EXAMPLES_ROOT / module_name).resolve()
    if not candidate.is_relative_to(EXAMPLES_ROOT) or not candidate.is_dir():
        return []
    return [
        {"name": f.name, "path": _relative(f)}
        for f in sorted(candidate.glob("*.py"))
    ]


def extract_description(module_path: Path) -> str:
    """Read a module's description from its workflow docstring.

    Parses with `ast` rather than scanning for `\"\"\"`, which previously
    matched the first triple-quote anywhere in the file — including inside a
    string literal or a commented-out block.
    """
    workflow_file = module_path / "workflow.py"
    if not workflow_file.exists():
        return "No description available"
    try:
        tree = ast.parse(workflow_file.read_text())
    except (OSError, SyntaxError) as exc:
        # Narrow: a malformed or unreadable module is worth a log line. The
        # previous `except Exception: pass` hid every cause.
        logger.warning("could not read docstring from %s: %s", workflow_file, exc)
        return "No description available"
    return (ast.get_docstring(tree) or "No description available").strip()
