"""Test fixtures — app instance and role-specific test clients.

Tests use a separate database (vel_yantra_test) so they never touch dev data.
The test DB is created by the Docker init script (tooling/dev/init-test-db.sql);
start it with tooling/dev/dev-db-up.bat. Migrations are applied automatically.
"""

import os
import shutil
import sys
import tempfile

import pytest
from flask.testing import FlaskClient

# Lets config.py fall back to the example secrets template when the real one is absent
os.environ["YANTRA_TESTING"] = "1"
# Never run the suite with the dev auth bypass, even if the shell has it set
os.environ.pop("DEV_AUTH_BYPASS", None)
# Uploaded files go to a temporary folder, never the dev data/ folder; set before config
# is imported, which reads it.  Removed at the end of the session (_remove_data_dir).
TEST_DATA_DIR = tempfile.mkdtemp(prefix="yantra-test-data-")
os.environ["DATA_DIR"] = TEST_DATA_DIR

# Add backend directory to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Point at the test DB before importing app — mutate in place so the dict
# app.py imported by reference sees it.
import config
config.DB_CONFIG["database"] = "vel_yantra_test"

import access_control
from access_core import Membership
from app import app as flask_app
from auth_utils import make_user
from config_rbac import LOGIN_ROLE, SITE_ROLES, TOKEN_ROLES
from db_helpers import transaction
from local_db import ensure_schema, get_local_db
from tests.access_helpers import site_rows


# ---------------------------------------------------------------------------
# The X-Test-Role harness: require_auth calls TEST_USER_FACTORY(role, X-Test-User) in
# TESTING mode and sets g.user itself, so every later hook sees it (S013 BR1-02)
# ---------------------------------------------------------------------------

def harness_user(role_name, username):
    """The g.user for an X-Test-Role header (S011 § 5.8):
    - a site role: that role at every site (a wildcard membership; DB memberships ignored),
      all units only for the manager; the unit rows come from the DB, as in production;
    - admin, it_admin, maintenance_team: token roles; memberships from the DB, as in production;
    - anything else ("nobody"): no token role and no membership, never a wildcard."""
    name = f"Test {role_name}"
    if role_name in SITE_ROLES:
        return make_user(username, name, [LOGIN_ROLE], [Membership(None, role_name, role_name == "maint_manager")])
    if role_name in ("admin", LOGIN_ROLE, *TOKEN_ROLES):
        return make_user(username, name, [role_name])
    return make_user(username, name, [], [])


def _test_user_factory(role_name, username):
    # X-Test-User gives a unit-access test its own fresh username (default test_<role>)
    return harness_user(role_name, username or f"test_{role_name}")


flask_app.config["TEST_USER_FACTORY"] = _test_user_factory

# Every test request comes from an internal address unless it sends its own X-Real-IP
# (S013 BR1-10): the gate stays out of tests that are not about it.  An explicit header
# overrides this default; it can't be left out, so "missing" is tested as X-Real-IP: "".
TEST_INTERNAL_IP = "10.0.0.5"


class InternalClient(FlaskClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.environ_base["HTTP_X_REAL_IP"] = TEST_INTERNAL_IP


flask_app.test_client_class = InternalClient
# No socket-address fallback in tests, even with FLASK_DEBUG set in the shell (S013 § 5.1)
access_control.REMOTE_ADDR_FALLBACK = False


@pytest.fixture(autouse=True)
def _fresh_access_caches():
    """Each test starts with no sightings, no back-off and no cached ranges (per process)."""
    access_control.reset_access_log_state()
    access_control.clear_networks_cache()
    yield
    access_control.reset_access_log_state()
    access_control.clear_networks_cache()


# Tables emptied once per session so tests start from a known state, child tables first
_TABLES = ("access_log", "task_queue", "person_units", "memberships", "person_trades", "people", "trades", "equipment_documents",
           "equipment_events", "equipment", "equipment_models", "manufacturers", "equipment_types", "user_units",
           "units", "sites", "equipment_classes", "serial_counters")


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


@pytest.fixture(scope="session", autouse=True)
def _remove_data_dir():
    yield
    shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)


@pytest.fixture
def upload_limit_mb():
    """upload_limit_mb(n) sets the upload_max_mb setting (n=None removes it, raw text is
    written as is); the seeded 20 is put back afterwards."""
    def write(value):
        conn = get_local_db(config.DB_CONFIG)
        try:
            with conn.cursor() as cur:
                if value is None:
                    cur.execute("DELETE FROM app_settings WHERE setting_key = 'upload_max_mb'")
                else:
                    cur.execute("INSERT INTO app_settings (setting_key, setting_value) VALUES ('upload_max_mb', %s) "
                                "ON DUPLICATE KEY UPDATE setting_value = %s", (str(value), str(value)))
        finally:
            conn.close()
    yield write
    write(20)


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
        # A copy: a caller's headers dict (often a module constant) is never changed
        kwargs["headers"] = {**kwargs.get("headers", {}), **self._headers}
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

    def trade_name(self):
        return f"Trade {self._next():04d}"

    def manufacturer_name(self):
        return f"Maker {self._next():04d}"

    def designation(self):
        return f"M-{self._next():04d}"

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
def make_manufacturer(admin, uniq):
    def make(**overrides):
        body = {"name": uniq.manufacturer_name(), **overrides}
        res = admin.post(f"{MASTERS}/manufacturers", json=body)
        assert res.status_code == 201, res.get_json()
        return res.get_json()
    return make


@pytest.fixture
def make_model(admin, uniq, make_class, make_manufacturer):
    """make_model() -> a model of a fresh class and manufacturer, with no type;
    make_model(cls=c, type_id=t, manufacturer=m, designation=...) to choose (S012)."""
    def make(cls=None, type_id=None, manufacturer=None, **overrides):
        body = {"manufacturer_id": (manufacturer or make_manufacturer())["id"], "designation": uniq.designation(),
                "class_id": (cls or make_class())["id"], "type_id": type_id, **overrides}
        res = admin.post(f"{MASTERS}/equipment-models", json=body)
        assert res.status_code == 201, res.get_json()
        return res.get_json()
    return make


@pytest.fixture
def make_equipment(admin, make_unit, make_model):
    """make_equipment() → equipment in a fresh unit, of a fresh model and class;
    make_equipment(parent=node) → a component unit under it (level= to choose).
    Equipment is created by model (S012): cls= and type_id= make a model of that class and
    type for it; model= picks a given one."""
    def make(unit=None, parent=None, cls=None, level=None, model=None, type_id=None, **overrides):
        model = model or make_model(cls=cls, type_id=type_id)
        body = {"model_id": model["id"], "name": "Test node"}
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


@pytest.fixture
def make_trade(admin, uniq):
    def make(**overrides):
        body = {"name": uniq.trade_name(), **overrides}
        res = admin.post(f"{MASTERS}/trades", json=body)
        assert res.status_code == 201, res.get_json()
        return res.get_json()
    return make


@pytest.fixture
def make_person(admin):
    """make_person() -> a direct employee with no trades and no login; trades=[t, ...] to give some.
    Created by IT admin, who may also set a login (username=...); a login save carries the
    person's sites (S011 A1 rule 1), none unless sites=[...] is given."""
    def make(trades=None, **overrides):
        body = {"name": "Test person", "employment": "direct", "trade_ids": [t["id"] for t in trades or []],
                **overrides}
        if body.get("username"):
            body.setdefault("sites", [])
        res = admin.post(f"{MASTERS}/people", json=body)
        assert res.status_code == 201, res.get_json()
        return res.get_json()
    return make


@pytest.fixture
def user_with_units(role_client, make_person, uniq):
    """A client for a fresh username holding exactly the given units: a person with that login
    and the role at the units' sites.  With X-Test-Role a site role holds at every site
    (S011 § 5.8), so the units are what counts.  For a token role (it_admin, admin) nothing is
    written: a token role sees every unit anyway."""
    def make(role, units):
        username = uniq.username()
        if role in SITE_ROLES:
            make_person(name=f"User {username}", username=username, sites=site_rows(role, units))
        return role_client(role, username)
    return make


@pytest.fixture
def user_at_sites(role_client, make_person, uniq):
    """user_at_sites([(site, role, units_or_"all"), ...]) -> a maintenance_team client whose
    real memberships are exactly these (the per-site cases: the X-Test-Role wildcard would
    hide "at B -> 403").  The person is returned too: (client, person)."""
    def make(spec):
        username = uniq.username()
        sites = [{"site_id": site["id"], "role": role, "all_units": units == "all",
                  "unit_ids": [] if units == "all" else [u["id"] for u in units]} for site, role, units in spec]
        person = make_person(name=f"User {username}", username=username, sites=sites)
        return role_client(LOGIN_ROLE, username), person
    return make


@pytest.fixture
def db_rows():
    """db_rows(sql, params) -> the rows, read on a connection of its own (outside the API)."""
    def query(sql, params=()):
        conn = get_local_db(config.DB_CONFIG)
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()
        finally:
            conn.close()
    return query


# ---------------------------------------------------------------------------
# One node in a fresh unit (shared by the document tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def unit(make_unit):
    return make_unit()


@pytest.fixture
def node(make_equipment, unit):
    return make_equipment(unit=unit)


@pytest.fixture
def at_unit(user_with_units, unit):
    """at_unit(role) -> a client for a fresh user of that role holding the node's unit."""
    return lambda role: user_with_units(role, [unit])
