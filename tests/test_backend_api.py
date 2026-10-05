"""Backend API: auth, validation, containment, CORS.

End-to-end through FastAPI's TestClient, so the dependency wiring is
exercised rather than the handlers in isolation.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from backend.app import allowed_origins, create_app  # noqa: E402
from backend.auth import session_store  # noqa: E402


@pytest.fixture
def client():
    return TestClient(create_app(origins=["http://localhost:3000"]))


@pytest.fixture
def token():
    return session_store.issue(label="test").token


@pytest.fixture
def auth(token):
    return {"Authorization": f"Bearer {token}"}


class TestAuthentication:
    """Every code-execution endpoint was previously unauthenticated."""

    @pytest.mark.parametrize(
        "method,path,body",
        [
            ("post", "/execute", {"code": "print(1)"}),
            ("get", "/modules", None),
            ("post", "/module-info", {"module_name": "rna_seq"}),
            ("post", "/execute-module", {"module_name": "rna_seq"}),
        ],
    )
    def test_requires_a_token(self, client, method, path, body):
        response = getattr(client, method)(path, json=body) if body else (
            getattr(client, method)(path)
        )
        assert response.status_code == 401

    def test_rejects_an_unknown_token(self, client):
        response = client.post(
            "/execute",
            json={"code": "print(1)"},
            headers={"Authorization": "Bearer not-a-real-token"},
        )
        assert response.status_code == 401

    def test_rejects_a_forged_token_derived_from_a_user_id(self, client):
        """The old scheme let any client derive a token from its own user id."""
        import hashlib
        import hmac

        forged = hmac.new(
            b"default_secret_change_me",
            b"alice:default_secret_change_me:0",
            hashlib.sha256,
        ).hexdigest()
        response = client.post(
            "/execute",
            json={"code": "print(1)"},
            headers={"Authorization": f"Bearer {forged}"},
        )
        assert response.status_code == 401

    def test_accepts_a_valid_token(self, client, auth):
        assert client.post("/execute", json={"code": "print(1)"}, headers=auth).status_code == 200

    def test_accepts_the_alternate_header(self, client, token):
        response = client.post(
            "/execute", json={"code": "print(1)"}, headers={"X-Gliaent-Token": token}
        )
        assert response.status_code == 200

    def test_revoked_token_stops_working(self, client, token):
        auth = {"Authorization": f"Bearer {token}"}
        assert client.get("/modules", headers=auth).status_code == 200
        session_store.revoke(token)
        assert client.get("/modules", headers=auth).status_code == 401

    def test_isolation_report_needs_no_token(self, client):
        response = client.get("/sandbox/isolation")
        assert response.status_code == 200
        assert "network_namespace" in response.json()


class TestExecuteValidation:
    def test_blank_code_rejected(self, client, auth):
        assert client.post("/execute", json={"code": "   "}, headers=auth).status_code == 422

    def test_null_timeout_rejected(self, client, auth):
        """`timeout: null` previously meant no timeout at all."""
        response = client.post(
            "/execute", json={"code": "print(1)", "timeout": None}, headers=auth
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("timeout", [0, -5, 9999])
    def test_out_of_range_timeout_rejected(self, client, auth, timeout):
        response = client.post(
            "/execute", json={"code": "print(1)", "timeout": timeout}, headers=auth
        )
        assert response.status_code == 422

    def test_oversized_body_rejected(self, client, auth):
        response = client.post(
            "/execute", json={"code": "x=1\n" * 500_000}, headers=auth
        )
        assert response.status_code == 422


class TestExecuteBehaviour:
    def test_runs_code(self, client, auth):
        body = client.post(
            "/execute", json={"code": "print(6*7)"}, headers=auth
        ).json()
        assert "42" in body["output"]
        assert body["exit_code"] == 0

    def test_reports_isolation_layers(self, client, auth):
        body = client.post("/execute", json={"code": "pass"}, headers=auth).json()
        assert "audit-hook" in body["isolation"]

    def test_network_is_blocked_by_default(self, client, auth):
        body = client.post(
            "/execute",
            json={
                "code": "import socket\nsocket.create_connection(('1.1.1.1',80),timeout=2)\nprint('OUT')",
                "timeout": 15,
            },
            headers=auth,
        ).json()
        assert "OUT" not in body["output"]
        assert body["exit_code"] != 0

    def test_runaway_code_times_out_rather_than_hanging(self, client, auth):
        body = client.post(
            "/execute", json={"code": "while True: pass", "timeout": 2}, headers=auth
        ).json()
        assert body["timed_out"] is True

    def test_user_error_is_a_200_with_detail_not_a_500(self, client, auth):
        response = client.post(
            "/execute", json={"code": "1/0"}, headers=auth
        )
        assert response.status_code == 200
        assert "ZeroDivisionError" in response.json()["error"]

    def test_server_secrets_do_not_reach_submitted_code(self, client, auth, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-leaked")
        body = client.post(
            "/execute",
            json={"code": "import os\nprint(os.environ.get('OPENROUTER_API_KEY'))"},
            headers=auth,
        ).json()
        assert "sk-or-v1-leaked" not in body["output"]


class TestModulePathContainment:
    @pytest.mark.parametrize(
        "name",
        [
            "../../../../tmp",
            "../../etc",
            "rna_seq/../../..",
            "/etc/passwd",
            "..",
            "rna_seq\x00",
        ],
    )
    def test_traversal_is_rejected_at_validation(self, client, auth, name):
        """`{"module_name": "../../../../tmp"}` previously reached exec_module."""
        response = client.post(
            "/execute-module", json={"module_name": name}, headers=auth
        )
        assert response.status_code == 422, response.text

    @pytest.mark.parametrize("name", ["../../../../tmp", "/etc", ".."])
    def test_module_info_traversal_rejected(self, client, auth, name):
        response = client.post(
            "/module-info", json={"module_name": name}, headers=auth
        )
        assert response.status_code == 422

    def test_unknown_module_is_a_404_not_a_200(self, client, auth):
        """The old handler swallowed its own HTTPException into a 200."""
        response = client.post(
            "/execute-module", json={"module_name": "no_such_module"}, headers=auth
        )
        assert response.status_code == 404

    def test_lists_real_modules(self, client, auth):
        modules = client.get("/modules", headers=auth).json()["modules"]
        names = {m["name"] for m in modules}
        assert "rna_seq" in names
        assert "scrna_seq" in names

    def test_listed_paths_are_relative_not_absolute(self, client, auth):
        """Absolute paths leak the server's directory layout."""
        modules = client.get("/modules", headers=auth).json()["modules"]
        assert all(not m["path"].startswith("/") for m in modules)

    def test_modules_found_regardless_of_cwd(self, client, auth, monkeypatch, tmp_path):
        """Paths were CWD-relative, so this returned [] from any other dir."""
        monkeypatch.chdir(tmp_path)
        modules = client.get("/modules", headers=auth).json()["modules"]
        assert len(modules) > 0


class TestCors:
    def test_wildcard_origin_is_refused(self, monkeypatch):
        monkeypatch.setenv("GLIAENT_ALLOWED_ORIGINS", "*")
        with pytest.raises(ValueError, match="must not contain"):
            allowed_origins()

    def test_default_allowlist_is_local_only(self, monkeypatch):
        monkeypatch.delenv("GLIAENT_ALLOWED_ORIGINS", raising=False)
        assert all(
            o.startswith(("http://localhost", "http://127.0.0.1"))
            for o in allowed_origins()
        )

    def test_unlisted_origin_gets_no_allow_header(self, client, auth):
        response = client.post(
            "/execute",
            json={"code": "print(1)"},
            headers={**auth, "Origin": "http://evil.example.com"},
        )
        assert response.headers.get("access-control-allow-origin") != (
            "http://evil.example.com"
        )

    def test_listed_origin_is_allowed(self, client, auth):
        response = client.post(
            "/execute",
            json={"code": "print(1)"},
            headers={**auth, "Origin": "http://localhost:3000"},
        )
        assert response.headers.get("access-control-allow-origin") == (
            "http://localhost:3000"
        )
