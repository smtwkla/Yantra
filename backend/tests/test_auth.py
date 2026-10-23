"""Keycloak token validation, the auth middleware and /api/auth/me.

Tokens are signed with a throwaway RSA key and the JWKS lookup is stubbed,
so these run without a Keycloak server.  From S011 a token's maintenance roles are
ignored: maintenance_team lets a user log in, and the roles come from memberships.
"""

import logging
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

import access_control
import auth_utils
import config
import db_helpers
from local_db import get_local_db

CLIENT_ID = config.KEYCLOAK_CLIENT_ID

_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _StubJWKClient:
    def __init__(self, key):
        self._key = key

    def get_signing_key_from_jwt(self, _token):
        return type("SigningKey", (), {"key": self._key.public_key()})()


@pytest.fixture(autouse=True)
def stub_jwks(monkeypatch):
    monkeypatch.setattr(auth_utils, "_get_jwk_client", lambda _url: _StubJWKClient(_KEY))


def _token(realm_roles=(), client_roles=(), azp=CLIENT_ID, exp_in=300, key=_KEY, username="jdoe", sid=None,
           email=None):
    payload = {
        "sid": sid,
        "preferred_username": username,
        "name": "John Doe",
        "azp": azp,
        "exp": int(time.time()) + exp_in,
        "realm_access": {"roles": list(realm_roles)},
        "resource_access": {CLIENT_ID: {"roles": list(client_roles)}},
    }
    if email is not None:
        payload["email"] = email
    return jwt.encode(payload, key, algorithm="RS256")


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _validate(app, token):
    headers = _bearer(token) if token else {}
    with app.test_request_context("/api/auth/me", headers=headers):
        return auth_utils.validate_keycloak_token("https://sso.example/realms/R", CLIENT_ID)


@pytest.fixture
def db_down(monkeypatch):
    """Every get_db() in the request raises DBUnavailable, as while the database is down; the
    access-log hook's own ensure_schema reference answers "down" too (S013 BR2-03)."""
    monkeypatch.setattr(db_helpers, "ensure_schema", lambda _config: "Can't connect (test)")
    monkeypatch.setattr(access_control, "ensure_schema", lambda _config: "Can't connect (test)")


class TestValidateToken:

    def test_login_role_accepted_and_grants_nothing(self, app):
        user = _validate(app, _token(client_roles=["maintenance_team"]))
        assert user["roles"] == ["maintenance_team"]
        assert user["permissions"] == []

    def test_realm_role_maps_to_user(self, app):
        user = _validate(app, _token(realm_roles=["maintenance_team", "offline_access"]))
        assert user["username"] == "jdoe"
        assert user["name"] == "John Doe"
        assert user["roles"] == ["maintenance_team"]

    def test_client_roles_count_too(self, app):
        user = _validate(app, _token(client_roles=["it_admin"]))
        assert user["role"] == "it_admin"

    def test_it_admin_and_login_role_together(self, app):
        user = _validate(app, _token(client_roles=["maintenance_team", "it_admin"]))
        assert user["roles"] == ["it_admin", "maintenance_team"]
        assert user["role"] == "it_admin"

    def test_old_maintenance_roles_alone_are_rejected(self, app):
        assert _validate(app, _token(realm_roles=["maint_operator", "maint_manager"])) is None

    def test_old_maintenance_roles_are_kept_as_stale(self, app):
        user = _validate(app, _token(client_roles=["maintenance_team", "maint_engineer"]))
        assert user["roles"] == ["maintenance_team"] and user["permissions"] == []
        assert user["stale_roles"] == ["maint_engineer"]

    @pytest.mark.parametrize("admin_role", ["admin", "mspv-apps-admin"])
    def test_admin_realm_roles_map_to_admin(self, app, admin_role):
        user = _validate(app, _token(realm_roles=[admin_role, "maint_operator"]))
        assert user["roles"] == ["admin"]
        assert "settings:edit" in user["permissions"]

    def test_no_recognised_role_is_rejected(self, app):
        assert _validate(app, _token(realm_roles=["offline_access"])) is None

    def test_wrong_client_is_rejected(self, app):
        assert _validate(app, _token(realm_roles=["maintenance_team"], azp="other-app")) is None

    def test_expired_token_is_rejected(self, app):
        assert _validate(app, _token(realm_roles=["maintenance_team"], exp_in=-60)) is None

    def test_bad_signature_is_rejected(self, app):
        assert _validate(app, _token(realm_roles=["maintenance_team"], key=_OTHER_KEY)) is None

    def test_missing_header_is_rejected(self, app):
        assert _validate(app, None) is None

    def test_the_email_claim_goes_into_the_user_as_given(self, app):
        """S032 § 5.4: checked and cleaned only when /auth/me stores it."""
        assert _validate(app, _token(client_roles=["maintenance_team"], email=" Priya@Example.TEST"))["email"] == (
            " Priya@Example.TEST")
        assert _validate(app, _token(client_roles=["maintenance_team"]))["email"] == ""


class TestMiddleware:

    @pytest.mark.parametrize("path", ["/api/health", "/api/version", "/api/auth/config"])
    def test_public_paths_need_no_token(self, client, path):
        assert client.get(path).status_code == 200

    def test_protected_path_without_token_is_401(self, client):
        assert client.get("/api/auth/me").status_code == 401

    def test_old_role_token_is_401(self, client):
        assert client.get("/api/auth/me", headers=_bearer(_token(realm_roles=["maint_engineer"]))).status_code == 401

    def test_valid_bearer_token_reaches_route(self, client, make_unit, make_person, uniq):
        unit = make_unit()
        login = uniq.username()
        make_person(username=login, sites=[{"site_id": unit["site_id"], "role": "maint_engineer",
                                            "all_units": True, "unit_ids": []}])
        res = client.get("/api/auth/me", headers=_bearer(_token(client_roles=["maintenance_team"], username=login)))
        assert res.status_code == 200
        body = res.get_json()
        assert body["name"] == "John Doe"
        assert body["role"] == "maint_engineer"
        assert body["roles"] == ["maintenance_team"]
        assert "equipment:edit" in body["permissions"]
        assert body["db_unavailable"] is False
        assert body["sites"] == [{"site_id": unit["site_id"], "site_code": unit["site_code"],
                                  "role": "maint_engineer", "all_units": True}]

    def test_auth_config_exposes_realm_and_client(self, client):
        body = client.get("/api/auth/config").get_json()
        assert body == {
            "url": config.KEYCLOAK_URL,
            "realm": config.KEYCLOAK_REALM,
            "clientId": CLIENT_ID,
            "devBypass": False,
        }


class TestLoginOnly:
    """S011 § 5.1, § 8: maintenance_team without a membership logs in and sees nothing."""

    def test_me_is_200_with_nothing(self, client, uniq):
        headers = _bearer(_token(client_roles=["maintenance_team"], username=uniq.username()))
        body = client.get("/api/auth/me", headers=headers).get_json()
        assert body["permissions"] == [] and body["sites"] == [] and body["role"] is None
        assert client.get("/api/equipment", headers=headers).status_code == 403

    def test_an_inactive_person_has_no_access(self, client, admin, make_unit, make_person, uniq):
        unit = make_unit()
        login = uniq.username()
        person = make_person(username=login, sites=[{"site_id": unit["site_id"], "role": "maint_operator",
                                                     "all_units": True, "unit_ids": []}])
        headers = _bearer(_token(client_roles=["maintenance_team"], username=login))
        assert client.get("/api/equipment", headers=headers).status_code == 200
        assert admin.put(f"/api/masters/people/{person['id']}", json={"active": 0}).status_code == 200
        # Deactivating ends access on the next request (A1 rule 3)
        assert client.get("/api/equipment", headers=headers).status_code == 403
        assert client.get("/api/auth/me", headers=headers).get_json()["permissions"] == []


class TestStaleRolesWarning:
    """§ 5.1, BR2-04: one WARNING from /auth/me, none from other routes."""

    def _stale(self, caplog):
        return [r for r in caplog.records if "still carries old Keycloak roles" in r.getMessage()]

    def test_logged_from_me_only(self, client, caplog, uniq):
        headers = _bearer(_token(client_roles=["maintenance_team", "maint_engineer"], username=uniq.username()))
        with caplog.at_level(logging.WARNING):
            client.get("/api/masters/sites", headers=headers)
            assert self._stale(caplog) == []
            client.get("/api/auth/me", headers=headers)
        assert len(self._stale(caplog)) == 1
        assert "maint_engineer" in self._stale(caplog)[0].getMessage()


class TestDatabaseDown:
    """§ 5.2: the token answers what it can; /auth/me says the database is down."""

    def test_it_admin_gets_token_permissions(self, client, db_down):
        body = client.get("/api/auth/me", headers=_bearer(_token(client_roles=["it_admin"]))).get_json()
        assert body["db_unavailable"] is True and body["sites"] is None
        assert body["permissions"] == auth_utils.compute_permissions(["it_admin"])
        assert body["role"] == "it_admin"
        # S018 BR4-08: no Team record can be read either
        assert body["person_id"] is None

    def test_login_only_user_gets_nothing(self, client, db_down):
        res = client.get("/api/auth/me", headers=_bearer(_token(client_roles=["maintenance_team"])))
        assert res.status_code == 200
        assert res.get_json()["permissions"] == [] and res.get_json()["db_unavailable"] is True

    def test_a_check_that_needs_memberships_is_503(self, client, db_down):
        res = client.get("/api/masters/sites", headers=_bearer(_token(client_roles=["maintenance_team"])))
        assert res.status_code == 503


class TestInternalUrl:

    def test_rewrites_to_lan_ip_on_8080(self):
        assert auth_utils._make_internal_url(
            "https://sso.mspv.app/realms/Office.smtw.in", "10.24.0.119"
        ) == "http://10.24.0.119:8080/realms/Office.smtw.in"

    def test_empty_ip_keeps_public_url(self):
        url = "https://sso.mspv.app/realms/Office.smtw.in"
        assert auth_utils._make_internal_url(url, "") == url


class TestAccessLogMarks:
    """S013 § 5.4, BR2-04: a failing validation leaves one fixed code; sid is the session."""

    @pytest.mark.parametrize("make_headers, code", [
        (lambda: {}, "no_token"),
        (lambda: _bearer(_token(realm_roles=["maintenance_team"], key=_OTHER_KEY)), "invalid_token"),
        (lambda: _bearer(_token(realm_roles=["maintenance_team"], azp="other-app")), "wrong_client"),
        (lambda: _bearer(_token(realm_roles=["offline_access"])), "no_role"),
    ])
    def test_failure_codes(self, app, make_headers, code):
        from flask import g
        with app.test_request_context("/api/auth/me", headers=make_headers()):
            assert auth_utils.validate_keycloak_token("https://sso.example/realms/R", CLIENT_ID) is None
            assert g.access_detail == code

    def test_sid_is_the_session(self, app):
        user = _validate(app, _token(client_roles=["it_admin"], sid="abc-123"))
        assert user["session_id"] == "abc-123"

    def test_a_real_token_it_admin_is_gated(self, client):
        headers = _bearer(_token(client_roles=["it_admin"]))
        assert client.get("/api/masters/sites", headers={**headers, "X-Real-IP": "203.0.113.7"}).status_code == 403
        assert client.get("/api/masters/sites", headers=headers).status_code == 200

    def test_the_session_id_is_logged(self, client, db_rows, uniq):
        login, sid = uniq.username(), f"sid-{uniq.username()}"
        client.get("/api/masters/sites", headers=_bearer(_token(client_roles=["it_admin"], username=login, sid=sid)))
        rows = db_rows("SELECT session_id, outcome FROM access_log WHERE username = %s", (login,))
        assert [(r["session_id"], r["outcome"]) for r in rows] == [(sid, "ok")]


class TestLoginEmail:
    """S032 § 5.4, § 8: /auth/me copies the token's email onto the person."""

    def _person(self, make_unit, make_person, uniq):
        unit = make_unit()
        login = uniq.username()
        person = make_person(username=login, sites=[{"site_id": unit["site_id"], "role": "maint_manager",
                                                     "all_units": True, "unit_ids": []}])
        return login, person

    def _me(self, client, login, email):
        res = client.get("/api/auth/me", headers=_bearer(_token(client_roles=["maintenance_team"], username=login,
                                                                email=email)))
        assert res.status_code == 200, res.get_json()
        return res.get_json()

    def _stored(self, db_rows, person):
        return db_rows("SELECT email, updated_at, updated_by FROM people WHERE id = %s", (person["id"],))[0]

    def test_stored_lower_cased_replaced_and_cleared(self, client, db_rows, make_unit, make_person, uniq):
        login, person = self._person(make_unit, make_person, uniq)
        before = self._stored(db_rows, person)
        self._me(client, login, "  Priya@Example.TEST ")
        assert self._stored(db_rows, person)["email"] == "priya@example.test"
        self._me(client, login, "priya.k@example.test")
        assert self._stored(db_rows, person)["email"] == "priya.k@example.test"
        self._me(client, login, "a@b.test, c@d.test")       # fails the address check: cleared
        assert self._stored(db_rows, person)["email"] is None
        self._me(client, login, "priya@example.test")
        self._me(client, login, None)                       # no claim at all: cleared
        stored = self._stored(db_rows, person)
        assert stored["email"] is None
        # A cached value from Keycloak, not an edit of the Team record
        assert (stored["updated_at"], stored["updated_by"]) == (before["updated_at"], before["updated_by"])

    def test_no_person_writes_nothing(self, client, db_rows, uniq):
        login = uniq.username()
        body = self._me(client, login, "nobody@example.test")
        assert body["person_id"] is None
        assert db_rows("SELECT id FROM people WHERE email = 'nobody@example.test'") == ()

    def test_database_down_answers_as_today(self, client, db_down):
        res = client.get("/api/auth/me", headers=_bearer(_token(client_roles=["it_admin"], email="it@example.test")))
        assert res.status_code == 200
        assert res.get_json()["db_unavailable"] is True and res.get_json()["person_id"] is None

    def test_store_login_email_counts_a_real_write_only(self, app, make_unit, make_person, uniq):
        """BR2-05: people.updated_at has no ON UPDATE, so the row count is what shows a write."""
        _login, person = self._person(make_unit, make_person, uniq)
        conn = get_local_db(config.DB_CONFIG)
        try:
            with conn.cursor() as cur:
                assert auth_utils.store_login_email(cur, person["id"], "Same@Example.test") == 1
                assert auth_utils.store_login_email(cur, person["id"], "same@example.test") == 0
                assert auth_utils.store_login_email(cur, person["id"], "") == 1
                assert auth_utils.store_login_email(cur, person["id"], None) == 0
        finally:
            conn.close()
