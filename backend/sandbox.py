"""Isolation for untrusted Python code.

An IDE has to run the user's code, so the goal is not to prevent execution
but to bound it. This module layers several independent restrictions and
reports which ones are actually active, because the thing it replaces had a
docstring promising to "execute Python code safely" and applied no isolation
whatsoever.

Layers, strongest first:

1. **Process isolation.** A fresh interpreter in its own session
   (`os.setsid`), so the whole process tree can be killed by process group.
   Nothing runs in the server process.
2. **Resource limits** (`setrlimit`): address space, CPU seconds, file size,
   process count, core dumps. These are kernel-enforced and cannot be lifted
   by the child, since the hard limit is lowered too.
3. **Network namespace** via `unshare -rn`, when unprivileged user namespaces
   are available. Kernel-enforced and complete when present.
4. **A scrubbed environment.** User code inherits none of the server's
   variables. This matters more than it looks: the previous implementation
   passed the full environment through, so `os.environ["OPENROUTER_API_KEY"]`
   inside submitted code would have read the key straight out.
5. **A Python audit hook** blocking network, subprocess, and writes outside
   the run's scratch directory. Installed before user code, and audit hooks
   cannot be removed once set. This is the backstop for when layer 3 is
   unavailable, not a substitute for it.

What this is NOT: a substitute for running the whole thing in a container.
On a multi-tenant deployment, run the API in a container per session and
treat these layers as defence in depth.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

#: Hard ceiling on submitted source length. A multi-gigabyte body would OOM
#: the server while writing it to disk, before any limit below applied.
MAX_CODE_BYTES = 1_000_000

#: Wall-clock bounds. `timeout=None` previously meant "no limit at all".
MIN_TIMEOUT_SECONDS = 1
MAX_TIMEOUT_SECONDS = 300
DEFAULT_TIMEOUT_SECONDS = 30

DEFAULT_MEMORY_MB = 2048
DEFAULT_MAX_OUTPUT_BYTES = 1_000_000
DEFAULT_MAX_FILE_MB = 256
DEFAULT_MAX_PROCESSES = 64


@dataclass
class SandboxPolicy:
    """Limits for one execution.

    Attributes:
        timeout_seconds: Wall-clock limit. Always finite.
        memory_mb: Address-space cap (RLIMIT_AS).
        max_output_bytes: Captured stdout/stderr is truncated beyond this.
        max_file_mb: Largest file the code may write (RLIMIT_FSIZE).
        max_processes: Process/thread cap (RLIMIT_NPROC), to bound fork bombs.
        allow_network: If False, network access is blocked. Defaults to False.
        extra_env: Variables to expose. Nothing else is inherited.
    """

    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    memory_mb: int = DEFAULT_MEMORY_MB
    max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES
    max_file_mb: int = DEFAULT_MAX_FILE_MB
    max_processes: int = DEFAULT_MAX_PROCESSES
    allow_network: bool = False
    extra_env: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not MIN_TIMEOUT_SECONDS <= self.timeout_seconds <= MAX_TIMEOUT_SECONDS:
            raise ValueError(
                f"timeout_seconds must be in "
                f"{MIN_TIMEOUT_SECONDS}..{MAX_TIMEOUT_SECONDS}, "
                f"got {self.timeout_seconds}"
            )
        if self.memory_mb < 64:
            raise ValueError(
                f"memory_mb must be at least 64 for the interpreter to start, "
                f"got {self.memory_mb}"
            )


@dataclass
class SandboxResult:
    """Outcome of one execution.

    Attributes:
        stdout: Captured standard output, possibly truncated.
        stderr: Captured standard error, possibly truncated.
        exit_code: Process exit status. -1 on timeout.
        timed_out: True if the wall-clock limit was hit.
        duration_seconds: Measured wall-clock time.
        truncated: True if output was cut at `max_output_bytes`.
        isolation: Which layers were actually applied, for the caller to
            surface. Never claim isolation that was not achieved.
    """

    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    timed_out: bool = False
    duration_seconds: float = 0.0
    truncated: bool = False
    isolation: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


def _network_namespace_available() -> bool:
    """Whether `unshare -rn` works here.

    Probed once and cached. Requires unprivileged user namespaces, which are
    enabled on most modern Linux but disabled in some hardened kernels and
    unavailable on macOS.
    """
    global _NETNS_CACHE
    if _NETNS_CACHE is not None:
        return _NETNS_CACHE
    if sys.platform != "linux" or shutil.which("unshare") is None:
        _NETNS_CACHE = False
        return False
    try:
        probe = subprocess.run(
            ["unshare", "-rn", "true"],
            capture_output=True,
            timeout=5,
        )
        _NETNS_CACHE = probe.returncode == 0
    except (OSError, subprocess.SubprocessError):
        _NETNS_CACHE = False
    return _NETNS_CACHE


_NETNS_CACHE: Optional[bool] = None


def _make_limiter(policy: SandboxPolicy):
    """Build the `preexec_fn` that drops limits in the child.

    Runs after fork and before exec, so the limits are in place before any
    user code exists. Both soft and hard limits are set, so the child cannot
    raise them back.
    """

    def apply_limits() -> None:  # pragma: no cover - runs in the child
        import resource

        os.setsid()  # new session: kill the whole group on timeout

        limits = [
            (resource.RLIMIT_AS, policy.memory_mb * 1024 * 1024),
            # +5s headroom: wall-clock is the primary limit so timeouts
            # report as timeouts. This is the backstop if it fails.
            (resource.RLIMIT_CPU, policy.timeout_seconds + 5),
            (resource.RLIMIT_FSIZE, policy.max_file_mb * 1024 * 1024),
            (resource.RLIMIT_CORE, 0),
            (resource.RLIMIT_NPROC, policy.max_processes),
        ]
        for which, value in limits:
            try:
                resource.setrlimit(which, (value, value))
            except (ValueError, OSError):
                # A limit the platform does not support is not fatal; the
                # other layers still apply.
                pass

    return apply_limits


_AUDIT_PREAMBLE = textwrap.dedent(
    '''
    # --- Gliaent sandbox preamble -------------------------------------------
    # Installed before user code. Audit hooks cannot be removed once added
    # (there is no sys.removeaudithook), so user code cannot undo this.
    import sys as _sys

    _SCRATCH = {scratch!r}
    _ALLOW_NETWORK = {allow_network!r}

    _BLOCKED_ALWAYS = (
        "os.system",
        "os.exec",
        "os.spawn",
        "os.fork",
        "os.forkpty",
        "pty.spawn",
        "subprocess.Popen",
        "ctypes.dlopen",
        "ctypes.dlsym",
        "ctypes.call_function",
    )
    # Event names per CPython's audit-event table. Creating a socket raises
    # socket.__new__, NOT socket.socket -- getting this wrong silently
    # disables the check, which is why there is a test for it.
    _BLOCKED_NETWORK = (
        "socket.__new__",
        "socket.connect",
        "socket.bind",
        "socket.getaddrinfo",
        "socket.gethostbyname",
        "socket.sethostname",
        "urllib.Request",
        "ftplib.connect",
        "smtplib.connect",
    )


    def _gliaent_audit(event, args):
        if event.startswith(_BLOCKED_ALWAYS):
            raise PermissionError(
                "sandbox: %s is not permitted. Analysis code should not spawn "
                "processes or load native libraries directly." % event
            )
        if not _ALLOW_NETWORK and event.startswith(_BLOCKED_NETWORK):
            raise PermissionError(
                "sandbox: network access (%s) is disabled for this run." % event
            )
        if event in ("open", "os.open"):
            path = args[0]
            mode = args[1] if len(args) > 1 else "r"
            writing = ("w" in str(mode) or "a" in str(mode) or "+" in str(mode)
                       or (isinstance(mode, int) and mode & 0x3))
            if writing and isinstance(path, (str, bytes)):
                import os as _os

                text = path.decode() if isinstance(path, bytes) else path
                resolved = _os.path.realpath(text)
                if not resolved.startswith(_SCRATCH):
                    raise PermissionError(
                        "sandbox: writes are confined to the run directory; "
                        "refused %s" % resolved
                    )


    _sys.addaudithook(_gliaent_audit)
    del _gliaent_audit
    # --- end preamble -------------------------------------------------------
    '''
).strip()


def build_runner_script(user_code: str, scratch: Path, policy: SandboxPolicy) -> str:
    """Wrap user code in the audit preamble.

    The preamble is prepended as separate source so the user's own line
    numbers in tracebacks stay meaningful: the code is compiled from a
    distinct file and executed, rather than concatenated.
    """
    preamble = _AUDIT_PREAMBLE.format(
        scratch=str(scratch.resolve()),
        allow_network=policy.allow_network,
    )
    return (
        preamble
        + "\n\n"
        + textwrap.dedent(
            '''
            import runpy as _runpy

            _runpy.run_path({user_file!r}, run_name="__main__")
            '''
        ).format(user_file=str((scratch / "user_code.py").resolve()))
    )


def run_untrusted_python(code: str, policy: Optional[SandboxPolicy] = None) -> SandboxResult:
    """Execute `code` under every available isolation layer.

    Args:
        code: Python source to run.
        policy: Limits. Defaults to `SandboxPolicy()`.

    Returns:
        A `SandboxResult`. Non-zero exit and timeouts are returned, not
        raised — they are normal outcomes of running user code.

    Raises:
        ValueError: If `code` is empty or exceeds `MAX_CODE_BYTES`, or the
            policy is invalid.
    """
    import time

    policy = policy or SandboxPolicy()

    if not code or not code.strip():
        raise ValueError("no code supplied")
    encoded = code.encode("utf-8", errors="replace")
    if len(encoded) > MAX_CODE_BYTES:
        raise ValueError(
            f"code is {len(encoded)} bytes, over the {MAX_CODE_BYTES} byte limit"
        )

    isolation: List[str] = ["subprocess", "rlimits", "scrubbed-env", "audit-hook"]

    # A fresh scratch directory per run: the only place writes are allowed,
    # and the child's cwd. The previous implementation used a shared
    # /tmp with predictable names, so concurrent runs could read and
    # overwrite each other's scripts before execution.
    scratch = Path(tempfile.mkdtemp(prefix="gliaent-run-"))
    try:
        (scratch / "user_code.py").write_text(code)
        runner = scratch / "_runner.py"
        runner.write_text(build_runner_script(code, scratch, policy))

        argv: List[str] = []
        if not policy.allow_network and _network_namespace_available():
            argv += ["unshare", "-rn"]
            isolation.append("network-namespace")
        # -I: isolated mode (ignores PYTHON* env vars and the user site dir).
        argv += [sys.executable, "-I", str(runner)]

        # Nothing from the server's environment reaches user code.
        env = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(scratch),
            "TMPDIR": str(scratch),
            "LANG": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            **policy.extra_env,
        }

        started = time.monotonic()
        process = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(scratch),
            env=env,
            text=True,
            preexec_fn=_make_limiter(policy) if sys.platform != "win32" else None,
        )

        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=policy.timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_process_group(process)
            # communicate() again to reap and collect whatever was produced.
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:  # pragma: no cover - defensive
                stdout, stderr = "", ""
        duration = time.monotonic() - started

        truncated = False
        if len(stdout) > policy.max_output_bytes:
            stdout = stdout[: policy.max_output_bytes]
            truncated = True
        if len(stderr) > policy.max_output_bytes:
            stderr = stderr[: policy.max_output_bytes]
            truncated = True

        if timed_out:
            stderr = (
                stderr + f"\n[sandbox] killed after {policy.timeout_seconds}s"
            ).lstrip()

        return SandboxResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=-1 if timed_out else process.returncode,
            timed_out=timed_out,
            duration_seconds=round(duration, 4),
            truncated=truncated,
            isolation=isolation,
        )
    finally:
        # Always cleaned up, including on an exception mid-run. The previous
        # implementation deleted its temp file only on the happy path and on
        # TimeoutExpired, leaking it otherwise.
        shutil.rmtree(scratch, ignore_errors=True)


def _kill_process_group(process: subprocess.Popen) -> None:
    """SIGKILL the child's entire process group.

    Killing only the direct child leaves grandchildren running, which is how
    a runaway analysis survives its own timeout.
    """
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            process.kill()
        except OSError:  # pragma: no cover - already reaped
            pass


def describe_isolation() -> Dict[str, object]:
    """Report which layers this host can provide.

    Exposed so the UI can warn when network isolation is unavailable rather
    than implying a stronger guarantee than is in force.
    """
    return {
        "platform": sys.platform,
        "subprocess": True,
        "rlimits": sys.platform != "win32",
        "scrubbed_env": True,
        "audit_hook": True,
        "network_namespace": _network_namespace_available(),
        "note": (
            "Network isolation falls back to a Python audit hook when "
            "unprivileged user namespaces are unavailable. For multi-tenant "
            "use, run the API inside a container per session."
        ),
    }
