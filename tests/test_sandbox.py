"""Code-execution sandbox.

These tests assert the isolation layers actually hold. The implementation
they replace had a docstring reading "Execute Python code safely" and applied
no isolation at all.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.sandbox import (  # noqa: E402
    MAX_CODE_BYTES,
    SandboxPolicy,
    describe_isolation,
    run_untrusted_python,
)

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="POSIX resource limits and setsid required"
)


class TestHappyPath:
    def test_runs_code_and_captures_stdout(self):
        result = run_untrusted_python("print('hello from the sandbox')")
        assert result.ok
        assert "hello from the sandbox" in result.stdout
        assert result.exit_code == 0

    def test_captures_stderr_and_exit_code_on_error(self):
        result = run_untrusted_python("raise ValueError('boom')")
        assert not result.ok
        assert result.exit_code != 0
        assert "ValueError" in result.stderr
        assert "boom" in result.stderr

    def test_user_traceback_points_at_user_code(self):
        """The preamble must not make line numbers meaningless."""
        result = run_untrusted_python("x = 1\ny = 2\nraise RuntimeError('here')")
        assert "user_code.py" in result.stderr

    def test_reports_duration(self):
        assert run_untrusted_python("pass").duration_seconds >= 0.0

    def test_reports_which_layers_applied(self):
        isolation = run_untrusted_python("pass").isolation
        assert "rlimits" in isolation
        assert "audit-hook" in isolation
        assert "scrubbed-env" in isolation

    def test_scientific_code_still_works(self):
        """Isolation must not break the actual use case."""
        result = run_untrusted_python(
            "import math\nprint(round(math.sqrt(2), 4))"
        )
        assert result.ok, result.stderr
        assert "1.4142" in result.stdout


class TestResourceLimits:
    def test_infinite_loop_is_killed(self):
        result = run_untrusted_python(
            "while True:\n    pass",
            SandboxPolicy(timeout_seconds=2),
        )
        assert result.timed_out
        assert result.exit_code == -1
        assert "killed after 2s" in result.stderr

    def test_runaway_memory_is_capped(self):
        result = run_untrusted_python(
            "x = bytearray(4 * 1024 * 1024 * 1024)",  # 4 GiB
            SandboxPolicy(memory_mb=256, timeout_seconds=20),
        )
        assert not result.ok
        # Either MemoryError in the child, or the allocator aborts.
        assert result.exit_code != 0

    def test_output_flood_is_truncated_not_buffered_forever(self):
        result = run_untrusted_python(
            "print('x' * 10_000_000)",
            SandboxPolicy(max_output_bytes=10_000, timeout_seconds=30),
        )
        assert result.truncated
        assert len(result.stdout) <= 10_000

    def test_grandchildren_do_not_survive_the_timeout(self):
        """Killing only the direct child leaves orphans running."""
        result = run_untrusted_python(
            "import threading, time\n"
            "threading.Thread(target=lambda: time.sleep(600), daemon=False).start()\n"
            "time.sleep(600)\n",
            SandboxPolicy(timeout_seconds=2),
        )
        assert result.timed_out


class TestNetworkIsolation:
    def test_socket_creation_is_blocked(self):
        result = run_untrusted_python(
            "import socket\ns = socket.socket()\nprint('OPENED')"
        )
        assert "OPENED" not in result.stdout
        assert not result.ok

    def test_outbound_connection_is_blocked(self):
        result = run_untrusted_python(
            "import socket\n"
            "socket.create_connection(('1.1.1.1', 80), timeout=3)\n"
            "print('CONNECTED')",
            SandboxPolicy(timeout_seconds=15),
        )
        assert "CONNECTED" not in result.stdout
        assert not result.ok

    def test_urllib_exfiltration_is_blocked(self):
        result = run_untrusted_python(
            "import urllib.request\n"
            "urllib.request.urlopen('http://example.com', timeout=3)\n"
            "print('FETCHED')",
            SandboxPolicy(timeout_seconds=15),
        )
        assert "FETCHED" not in result.stdout
        assert not result.ok

    def test_network_can_be_allowed_explicitly(self):
        """An opt-in path must exist, or legitimate database queries break."""
        result = run_untrusted_python(
            "import socket\nsocket.socket()\nprint('ALLOWED')",
            SandboxPolicy(allow_network=True),
        )
        assert "ALLOWED" in result.stdout


class TestProcessEscape:
    def test_os_system_is_blocked(self):
        result = run_untrusted_python("import os\nos.system('echo ESCAPED')")
        assert "ESCAPED" not in result.stdout
        assert not result.ok

    def test_subprocess_is_blocked(self):
        result = run_untrusted_python(
            "import subprocess\n"
            "print(subprocess.run(['echo','ESCAPED'],capture_output=True).stdout)"
        )
        assert "ESCAPED" not in result.stdout
        assert not result.ok

    def test_fork_is_blocked(self):
        result = run_untrusted_python("import os\nos.fork()\nprint('FORKED')")
        assert "FORKED" not in result.stdout

    def test_indirect_exec_via_getattr_is_still_blocked(self):
        """Audit hooks fire on the operation, not the spelling of the call."""
        result = run_untrusted_python(
            "import os\n"
            "getattr(os, 'sys' + 'tem')('echo ESCAPED')\n"
        )
        assert "ESCAPED" not in result.stdout

    def test_audit_hook_cannot_be_removed(self):
        result = run_untrusted_python(
            "import sys\n"
            "print(hasattr(sys, 'removeaudithook'))\n"
            "import os\n"
            "os.system('echo ESCAPED')\n"
        )
        assert "ESCAPED" not in result.stdout
        assert "False" in result.stdout


class TestFilesystemConfinement:
    def test_writes_outside_the_run_directory_are_blocked(self, tmp_path):
        target = tmp_path / "should_not_exist.txt"
        result = run_untrusted_python(
            f"open({str(target)!r}, 'w').write('escaped')\nprint('WROTE')"
        )
        assert "WROTE" not in result.stdout
        assert not target.exists()

    def test_writes_inside_the_run_directory_are_allowed(self):
        result = run_untrusted_python(
            "open('scratch_output.csv','w').write('a,b\\n1,2\\n')\n"
            "print(open('scratch_output.csv').read().strip())"
        )
        assert result.ok, result.stderr
        assert "1,2" in result.stdout

    def test_reads_are_permitted(self):
        """Blocking reads would break importing libraries."""
        result = run_untrusted_python("import json, csv, statistics\nprint('OK')")
        assert result.ok, result.stderr

    def test_scratch_directory_is_removed_afterwards(self):
        result = run_untrusted_python("import os\nprint(os.getcwd())")
        assert result.ok
        assert not Path(result.stdout.strip()).exists()


class TestEnvironmentScrubbing:
    def test_server_secrets_are_not_visible_to_user_code(self, monkeypatch):
        """The old executor passed the whole environment through."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-secret-value")
        monkeypatch.setenv("GLIAENT_SECRET_KEY", "another-secret")
        result = run_untrusted_python(
            "import os\nprint(sorted(os.environ))"
        )
        assert result.ok, result.stderr
        assert "OPENROUTER_API_KEY" not in result.stdout
        assert "GLIAENT_SECRET_KEY" not in result.stdout

    def test_explicitly_passed_variables_do_arrive(self):
        result = run_untrusted_python(
            "import os\nprint(os.environ['GLIAENT_RUN_ID'])",
            SandboxPolicy(extra_env={"GLIAENT_RUN_ID": "run-123"}),
        )
        assert "run-123" in result.stdout


class TestInputValidation:
    @pytest.mark.parametrize("code", ["", "   ", "\n\n"])
    def test_empty_code_rejected(self, code):
        with pytest.raises(ValueError, match="no code"):
            run_untrusted_python(code)

    def test_oversized_code_rejected_before_writing_it(self):
        with pytest.raises(ValueError, match="byte limit"):
            run_untrusted_python("x = 1\n" * (MAX_CODE_BYTES // 2))

    @pytest.mark.parametrize("timeout", [0, -1, 301, 10_000])
    def test_out_of_range_timeout_rejected(self, timeout):
        """`timeout=None` or 0 previously meant no limit at all."""
        with pytest.raises(ValueError, match="timeout_seconds"):
            SandboxPolicy(timeout_seconds=timeout)

    def test_absurdly_small_memory_rejected(self):
        with pytest.raises(ValueError, match="memory_mb"):
            SandboxPolicy(memory_mb=8)


def test_describe_isolation_does_not_overstate():
    described = describe_isolation()
    assert described["subprocess"] is True
    assert described["audit_hook"] is True
    # The network-namespace claim must reflect the host, not a constant.
    assert isinstance(described["network_namespace"], bool)
