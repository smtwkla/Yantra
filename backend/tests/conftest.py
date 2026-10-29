"""Test fixtures — app instance and role-specific test clients.

Tests use their own database so they never touch dev data: one per test run and per
pytest-xdist worker (tests/db_names.py), created here if missing; tooling/run-backend-tests.bat
grants the DB user the right to create it.  Start the dev DB with tooling/dev/dev-db-up.bat.
Migrations are applied automatically.
"""

import atexit
import os
import shutil
import sys
import tempfile

import pymysql
import pytest
from flask.testing import FlaskClient

# Lets config.py fall back to the example secrets template when the real one is absent
os.environ["YANTRA_TESTING"] = "1"
# Never run the suite with the dev auth bypass, even if the shell has it set
os.environ.pop("DEV_AUTH_BYPASS", None)
# Uploaded files go to a temporary folder, never the dev data/ folder; set before config
# is imported, which reads it.  Removed at the end of the session (_remove_data_dir), and at exit
# for the pytest-xdist controller, which imports this file but runs no fixtures.
TEST_DATA_DIR = tempfile.mkdtemp(prefix="yantra-test-data-")
atexit.register(shutil.rmtree, TEST_DATA_DIR, ignore_errors=True)
os.environ["DATA_DIR"] = TEST_DATA_DIR

# Add backend directory to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.db_names import TEST_DB

# Point at the test DB before importing app — mutate in place so the dict
# app.py imported by reference sees it.
import config
config.DB_CONFIG["database"] = TEST_DB


def _create_test_db():
    """This run's and worker's database, if missing; kept between runs so only new
    migrations run (the first run builds the schema).  Before app is imported: its import
    calls ensure_schema, which would otherwise remember "unknown database" for 30 s.
    The xdist controller imports this file too, so it makes (and migrates) a database
    ``..._main`` that no test uses.  Left so: skipping it would need the controller to not
    import ``app``, i.e. a second code path through this file, for one idle database per run."""
    cfg = config.DB_CONFIG
    conn = pymysql.connect(host=cfg["host"], port=cfg["port"], user=cfg["user"], password=cfg["password"],
                           autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{TEST_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    finally:
        conn.close()


try:
    _create_test_db()
    _CREATE_ERROR = None
except pymysql.MySQLError as exc:   # reported by _clean_tables, so every test shows it
    _CREATE_ERROR = exc

import access_control
import db_helpers
from app import app as flask_app
from config_rbac import LOGIN_ROLE, SITE_ROLES
from db_helpers import transaction
from local_db import ensure_schema, get_local_db
from tests.access_helpers import site_rows
from tests.harness import harness_user
from vapid_keys import make_key_pair


# ---------------------------------------------------------------------------
# Web push (S021 BR1-06): one VAPID pair for the session, set in config after import (push.py
# and push_sender read it at call time), so push is on whatever the local secrets_app.py
# holds; push_off empties it for the "not set up" cases.
# ---------------------------------------------------------------------------

_VAPID_NAMES = ("VAPID_PUBLIC_KEY", "VAPID_PRIVATE_KEY", "VAPID_SUBJECT")


@pytest.fixture(scope="session", autouse=True)
def vapid_pair():
    public, private = make_key_pair()
    with pytest.MonkeyPatch.context() as patch:
        for name, value in zip(_VAPID_NAMES, (public, private, "mailto:test@example.invalid")):
            patch.setattr(config, name, value)
        yield public, private


@pytest.fixture
def push_off(monkeypatch):
    for name in _VAPID_NAMES:
        monkeypatch.setattr(config, name, "")


# Email (S032): on for the session with reserved test values, whatever the local secrets hold,
# so no test can reach a real mail server; the tests pass a fake sender.  email_off empties it
# for the "not set up" cases.
_SMTP_TEST_VALUES = {"SMTP_HOST": "smtp.example.test", "SMTP_PORT": 2525, "SMTP_USER": "yantra-test",
                     "SMTP_PASSWORD": "test-password", "SMTP_FROM": "yantra@example.test"}


@pytest.fixture(scope="session", autouse=True)
def smtp_test_values():
    with pytest.MonkeyPatch.context() as patch:
        for name, value in _SMTP_TEST_VALUES.items():
            patch.setattr(config, name, value)
        patch.setattr(config, "DEV_STUB_EMAIL", "")
        yield _SMTP_TEST_VALUES


@pytest.fixture
def email_off(monkeypatch):
    monkeypatch.setattr(config, "SMTP_HOST", "")


# ---------------------------------------------------------------------------
# The X-Test-Role harness: require_auth calls TEST_USER_FACTORY(role, X-Test-User, X-Test-Email) in
# TESTING mode and sets g.user itself, so every later hook sees it (S013 BR1-02).
# harness_user lives in tests/harness.py, shared with the browser tests' backend (S024).
# ---------------------------------------------------------------------------

def _test_user_factory(role_name, username, email=""):
    # X-Test-User gives a unit-access test its own fresh username (default test_<role>);
    # X-Test-Email the token's email claim (S032)
    return harness_user(role_name, username or f"test_{role_name}", email=email)


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
_TABLES = ("improvement_actions", "improvement_whys", "improvement_tickets", "improvements",
           "meter_readings", "node_meters", "model_meters", "access_log", "task_queue", "push_subscriptions", "person_units", "memberships", "person_trades", "ticket_parts", "ticket_labour", "ticket_assignees", "people", "trades", "ticket_note_edits", "ticket_events",
           "equipment_documents", "tickets",
           "equipment_events", "equipment_property_values", "equipment", "model_property_values", "equipment_models",
           "manufacturers",
           "equipment_types", "user_units", "units", "sites", "class_properties", "equipment_classes", "equipment_categories",
           "serial_counters")

# The failure-code lists (S016) keep their seed rows (migration v11): only what tests added goes
# Table -> the created_by values of its seed rows (meter types: migration v29, S037; the property
# master and its options: migration v31, S043; "GPS location": migration v34, S061)
SEED_CREATOR = "migration-v11"  # the failure-code seeds' creator only, for test_migration_v11.py
_SEEDED_TABLES = {"failure_modes": (SEED_CREATOR,), "failure_causes": (SEED_CREATOR,),
                  "maintenance_actions": (SEED_CREATOR,), "meter_types": ("migration-v29",),
                  "property_definitions": ("migration-v31", "migration-v34"), "property_options": ("migration-v31",)}


@pytest.fixture(scope="session", autouse=True)
def _clean_tables():
    if _CREATE_ERROR:
        pytest.fail(f"Could not create the test database {TEST_DB} (is the dev DB up, and the grant made by "
                    f"tooling/run-backend-tests.bat?): {_CREATE_ERROR}", pytrace=False)
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
                    for table, creators in _SEEDED_TABLES.items():
                        cur.execute(f"DELETE FROM {table} WHERE created_by NOT IN ({', '.join(['%s'] * len(creators))})",
                                    creators)
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
def db_down(monkeypatch):
    """Every get_db() in the request raises DBUnavailable, as while the database is down; the
    access-log hook's own ensure_schema reference answers "down" too (S013 BR2-03).  Shared by
    the auth, network-gate and properties tests (S043 BR1-16)."""
    monkeypatch.setattr(db_helpers, "ensure_schema", lambda _config: "Can't connect (test)")
    monkeypatch.setattr(access_control, "ensure_schema", lambda _config: "Can't connect (test)")


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

    def category_name(self):
        return f"Category {self._next():04d}"

    def trade_name(self):
        return f"Trade {self._next():04d}"

    def manufacturer_name(self):
        return f"Maker {self._next():04d}"

    def designation(self):
        return f"M-{self._next():04d}"

    def username(self):
        return f"user{self._next():04d}"

    def failure_code(self):
        """Fits the failure-code rule (S016 § 5.1) and never matches a seed code."""
        return f"T{self._next():04d}"

    def failure_label(self):
        return f"Test label {self._next():04d}"

    def meter_type_name(self):
        return f"Test meter {self._next():04d}"

    def property_name(self, prefix):
        """A property name, unique without regard to case (S043): "<prefix> <n>"."""
        return f"{prefix} {self._next():04d}"


@pytest.fixture(scope="session")
def uniq():
    return Uniq()


# ---------------------------------------------------------------------------
# Records made through the real API (shared by the masters and equipment tests)
# ---------------------------------------------------------------------------

# An unhandled error's answer (S025 § 1.3), as server_error() reads a response
SERVER_ERROR = (500, {"error": "Something went wrong — try again"})


def server_error(res):
    return res.status_code, res.get_json()

MASTERS = "/api/masters"
EQUIPMENT = "/api/equipment"


@pytest.fixture
def admin(role_client):
    """IT admin: writes masters and equipment, and sees every unit."""
    return role_client("it_admin")


@pytest.fixture
def keycloak_admin(role_client):
    """The Keycloak admin role (mspv-apps-admin), not IT admin: holds every key by the bypass."""
    return role_client("admin")


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
def make_category(admin, uniq):
    """make_category() -> a fresh active equipment category (S063)."""
    def make(**overrides):
        body = {"name": uniq.category_name(), **overrides}
        res = admin.post(f"{MASTERS}/equipment-categories", json=body)
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
def make_meter_type(admin, uniq):
    """make_meter_type() -> a fresh gauge (unit °C, 1 decimal); make_meter_type(kind=..., ...) to
    choose.  Tests make their own types; the v29 seed rows are never changed (S037)."""
    def make(**overrides):
        body = {"name": uniq.meter_type_name(), "unit": "°C", "kind": "gauge", "decimals": 1, **overrides}
        if body["kind"] == "yes_no":
            body = {"expected_answer": "yes", **body, "unit": None, "decimals": 0}
        res = admin.post(f"{MASTERS}/meter-types", json=body)
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
# Equipment properties (S044, S061, S062; shared by the item-values, property-master and
# property-filter tests; test_properties_api.py keeps its own make_property and link, which
# override these by name in that module)
# ---------------------------------------------------------------------------

@pytest.fixture
def make_property(admin, uniq):
    """make_property("A power") -> a number property in kW named "<prefix> <n>"; data_type= etc."""
    def make(prefix, **overrides):
        body = {"name": uniq.property_name(prefix), "data_type": "number", "unit": "kW", **overrides}
        if body["data_type"] != "number":
            body.pop("unit")
        res = admin.post(f"{MASTERS}/properties", json=body)
        assert res.status_code == 201, res.get_json()
        return res.get_json()
    return make


@pytest.fixture
def link(admin):
    """link(class_id, *props) -> the props added to the class."""
    def add(class_id, *props):
        res = admin.post(f"{MASTERS}/equipment-classes/{class_id}/properties",
                         json={"property_ids": [p["id"] for p in props]})
        assert res.status_code == 200, res.get_json()
    return add


@pytest.fixture
def every_class(admin, make_property):
    """every_class(...) -> make_property(..., all_classes=True), with the module's make_property.
    The flag is turned off afterwards: the test database is shared by the tests of a worker, and
    the property would otherwise show on every later test's machines (S061 D-10, S062 BS1-02)."""
    made = []

    def make(*args, **overrides):
        prop = make_property(*args, all_classes=True, **overrides)
        made.append(prop)
        return prop
    yield make
    for prop in made:
        res = admin.put(f"{MASTERS}/properties/{prop['id']}", json={"all_classes": False})
        assert res.status_code == 200, res.get_json()


# ---------------------------------------------------------------------------
# Failure modes and tickets (S016, S017; shared by the failure-code, ticket, document and
# equipment tests)
# ---------------------------------------------------------------------------

TICKETS = "/api/tickets"


@pytest.fixture
def make_mode(engineer, uniq):
    """make_mode() -> a General mode; make_mode(cls=c, label=...) to choose."""
    def make(cls=None, **overrides):
        body = {"code": uniq.failure_code(), "label": uniq.failure_label(), **overrides}
        if cls is not None:
            body["class_id"] = cls["id"]
        res = engineer.post(f"{MASTERS}/failure-modes", json=body)
        assert res.status_code == 201, res.get_json()
        return res.get_json()
    return make


@pytest.fixture
def make_ticket(admin):
    """make_ticket(node) -> a critical ticket raised on the node by IT admin, with a
    description; client= to raise as someone else, any body field to override."""
    def make(node, client=None, **overrides):
        body = {"equipment_id": node["id"], "intensity": "critical", "description": "Stopped", **overrides}
        res = (client or admin).post(TICKETS, json=body)
        assert res.status_code == 201, res.get_json()
        return res.get_json()
    return make


@pytest.fixture
def set_ticket_state(db_rows):
    """set_ticket_state(ticket, "closed"): the state written straight to the row, for tests
    about what a state allows rather than how a ticket gets there (S018's moves write events)."""
    def write(ticket, state):
        db_rows("UPDATE tickets SET state = %s WHERE id = %s", (state, ticket["id"]))
    return write


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


# ---------------------------------------------------------------------------
# Ticket tests (S017, S018): a machine in that unit, an operator there, a site role by IT admin
# ---------------------------------------------------------------------------

@pytest.fixture
def machine(make_equipment, unit):
    return make_equipment(unit=unit)


@pytest.fixture
def operator(at_unit):
    return at_unit("maint_operator")


@pytest.fixture
def give_site_role(admin):
    """give_site_role(person, site, role="maint_operator") -> a site row, all units, set by IT admin."""
    def give(person, site, role="maint_operator"):
        res = admin.put(f"{MASTERS}/people/{person['id']}/sites/{site['id']}",
                        json={"role": role, "all_units": True, "unit_ids": []})
        assert res.status_code == 200, res.get_json()
    return give
