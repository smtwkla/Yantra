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
from db_helpers import transaction
from local_db import ensure_schema, get_local_db


# ---------------------------------------------------------------------------
# Inject g.user when the X-Test-Role header is present. Registered once at
# import time so it works even after the first request has been served.
# ---------------------------------------------------------------------------

@flask_app.before_request
def _inject_test_user():
    from flask import current_app, g, request
    role_name = request.headers.get("X-Test-Role")
    if not role_name or not current_app.config.get("TESTING"):
        return
    # X-Test-User gives a unit-access test its own fresh username (default test_<role>)
    g.user = {
        "username": request.headers.get("X-Test-User") or f"test_{role_name}",
        "name": f"Test {role_name}",
        "role": role_name,
        "roles": [role_name],
        "permissions": compute_permissions([role_name]),
    }


# Tables emptied once per session so tests start from a known state, child tables first
_TABLES = ("equipment_events", "equipment", "equipment_types", "user_units", "units", "sites",
           "equipment_classes", "serial_counters")


@pytest.fixture(scope="session", autouse=True)
def _clean_tables():
    error = ensure_schema(config.DB_CONFIG)
    if error:
        pytest.fail(f"Test database not ready (is the dev DB up?): {error}", pytrace=False)
    conn = get_local_db(config.DB_CONFIG)
    try:
        with conn.cursor() as cur:
            # equipment references itself (parent_id), so row-by-row DELETE order would fail
            # with 1451; this connection alone runs with the checks off.
            cur.execute("SET FOREIGN_KEY_CHECKS = 0")
            try:
                with transaction(conn):
                    for table in _TABLES:
                        cur.execute(f"DELETE FROM {table}")
            finally:
                cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    finally:
        conn.close()


@pytest.fixture
def app():
    flask_app.config["TESTING"] = True
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class RoleClient:
    """Wraps a Flask test client to inject the X-Test-Role (and optional X-Test-User) header."""

    def __init__(self, inner, role, username=None):
        self._inner = inner
        self._headers = {"X-Test-Role": role}
        if username:
            self._headers["X-Test-User"] = username

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
    """Factory: role_client("it_admin") → a client acting as that role, as user test_<role>;
    role_client("maint_engineer", "eng_x") acts as that username instead."""
    return lambda role, username=None: RoleClient(app.test_client(), role, username)


class Uniq:
    """Unique codes and names, so tests never collide with each other or with leftovers."""

    def __init__(self):
        self._n = 0

    def _next(self):
        self._n += 1
        return self._n

    def site_code(self):
        return f"T{self._next():04d}"

    def unit_code(self):
        return f"U{self._next():04d}"

    def class_code(self):
        n, letters = self._next(), ""
        for _ in range(4):
            n, rest = divmod(n, 26)
            letters += chr(ord("A") + rest)
        return letters

    def warehouse(self):
        return f"Test Warehouse {self._next()} - SMTW"

    def type_name(self):
        return f"Type {self._next():04d}"

    def username(self):
        return f"user{self._next():04d}"


@pytest.fixture(scope="session")
def uniq():
    return Uniq()


# ---------------------------------------------------------------------------
# Records made through the real API (shared by the masters and equipment tests)
# ---------------------------------------------------------------------------

MASTERS = "/api/masters"
EQUIPMENT = "/api/equipment"


@pytest.fixture
def admin(role_client):
    """IT admin: writes masters and equipment, and sees every unit."""
    return role_client("it_admin")


@pytest.fixture
def engineer(role_client):
    return role_client("maint_engineer")


@pytest.fixture
def make_site(admin, uniq):
    def make(**overrides):
        body = {"code": uniq.site_code(), "name": "Test site", **overrides}
        res = admin.post(f"{MASTERS}/sites", json=body)
        assert res.status_code == 201, res.get_json()
        return res.get_json()
    return make


@pytest.fixture
def make_unit(admin, uniq, make_site):
    def make(site=None, **overrides):
        site = site or make_site()
        body = {"site_id": site["id"], "code": uniq.unit_code(), "name": "Test unit", **overrides}
        res = admin.post(f"{MASTERS}/units", json=body)
        assert res.status_code == 201, res.get_json()
        return res.get_json()
    return make


@pytest.fixture
def make_class(admin, uniq):
    def make(**overrides):
        body = {"code": uniq.class_code(), "name": "Test class", **overrides}
        res = admin.post(f"{MASTERS}/equipment-classes", json=body)
        assert res.status_code == 201, res.get_json()
        return res.get_json()
    return make


@pytest.fixture
def make_equipment(admin, make_unit, make_class):
    """make_equipment() → equipment in a fresh unit and class;
    make_equipment(parent=node) → a component unit under it (level= to choose)."""
    def make(unit=None, parent=None, cls=None, level=None, **overrides):
        body = {"class_id": (cls or make_class())["id"], "name": "Test node"}
        if parent is None:
            body.update(level=level or "equipment", unit_id=(unit or make_unit())["id"])
        else:
            body.update(level=level or "component_unit", parent_id=parent["id"])
        res = admin.post(EQUIPMENT, json={**body, **overrides})
        assert res.status_code == 201, res.get_json()
        return res.get_json()
    return make


@pytest.fixture
def make_type(admin, uniq, make_class):
    """make_type() -> a type of a fresh class; make_type(cls=c, name=...) to choose."""
    def make(cls=None, **overrides):
        body = {"class_id": (cls or make_class())["id"], "name": uniq.type_name(), **overrides}
        res = admin.post(f"{MASTERS}/equipment-types", json=body)
        assert res.status_code == 201, res.get_json()
        return res.get_json()
    return make
