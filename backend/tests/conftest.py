"""Test fixtures — app instance and role-specific test clients.

Tests use a separate database (vel_yantra_test) so they never touch dev data.
The test DB is created by the Docker init script (tooling/dev/init-test-db.sql);
start it with tooling/dev/dev-db-up.bat. Migrations are applied automatically.
"""

import os
import sys

import pytest

# Lets config.py fall back to the example secrets template when the real one is absent
os.environ["YANTRA_TESTING"] = "1"
# Never run the suite with the dev auth bypass, even if the shell has it set
os.environ.pop("DEV_AUTH_BYPASS", None)

# Add backend directory to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Point at the test DB before importing app — mutate in place so the dict
# app.py imported by reference sees it.
import config
config.DB_CONFIG["database"] = "vel_yantra_test"

from app import app as flask_app
from auth_utils import compute_permissions


# ---------------------------------------------------------------------------
# Inject g.user when the X-Test-Role header is present. Registered once at
# import time so it works even after the first request has been served.
# ---------------------------------------------------------------------------

@flask_app.before_request
def _inject_test_user():
    from flask import g, request
    role_name = request.headers.get("X-Test-Role")
    if not role_name:
        return
    g.user = {
        "username": f"test_{role_name}",
        "name": f"Test {role_name}",
        "role": role_name,
        "roles": [role_name],
        "permissions": compute_permissions([role_name]),
    }


@pytest.fixture
def app():
    flask_app.config["TESTING"] = True
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class RoleClient:
    """Wraps a Flask test client to inject the X-Test-Role header."""

    def __init__(self, inner, role):
        self._inner = inner
        self._headers = {"X-Test-Role": role}

    def _call(self, method, *args, **kwargs):
        kwargs.setdefault("headers", {}).update(self._headers)
        return getattr(self._inner, method)(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self._call("get", *args, **kwargs)

    def post(self, *args, **kwargs):
        return self._call("post", *args, **kwargs)

    def put(self, *args, **kwargs):
        return self._call("put", *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._call("delete", *args, **kwargs)


@pytest.fixture
def role_client(app):
    """Factory: role_client("it_admin") → a client acting as that role."""
    return lambda role: RoleClient(app.test_client(), role)
