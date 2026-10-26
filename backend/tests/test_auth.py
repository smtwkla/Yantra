"""Keycloak token validation, the auth middleware and /api/auth/me.

Tokens are signed with a throwaway RSA key and the JWKS lookup is stubbed,
so these run without a Keycloak server.  From S011 a token's maintenance roles are
ignored: maintenance_team lets a user log in, and the roles come from memberships.
"""

import base64
import hashlib
import hmac
import json
import logging
import time

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import auth_utils
import config
from local_db import get_local_db

CLIENT_ID = config.KEYCLOAK_CLIENT_ID

_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


# The real factory, taken before the autouse stub replaces it (S059 BR1-11)
_REAL_GET_JWK_CLIENT = auth_utils._get_jwk_client

# The issuer the app checks: app.py passes config.KEYCLOAK_REALM_URL to require_auth (S059 BR1-01)
ISSUER = config.KEYCLOAK_REALM_URL

# Passed for a claim, _token leaves that claim out of the payload
OMIT = object()


class _StubJWKClient:
    def __init__(self, key):
        self._key = key
        self.calls = 0

    def get_signing_key_from_jwt(self, _token):
        self.calls += 1
        return type("SigningKey", (), {"key": self._key.public_key()})()


class _DownJWKClient:
    """Keycloak's key list cannot be fetched, for any token (S059 § 1.2)."""

    def get_signing_key_from_jwt(self, _token):
        raise jwt.exceptions.PyJWKClientConnectionError("Fail to fetch data from the url, err: timed out")


class _RaisingJWKClient:
    """The key-list fetch fails with an error PyJWT does not wrap (S059 CR1-01)."""

    def __init__(self, exc):
        self._exc = exc

    def get_signing_key_from_jwt(self, _token):
        raise self._exc


@pytest.fixture(autouse=True)
def stub_jwks(monkeypatch):
    monkeypatch.setattr(auth_utils, "_get_jwk_client", lambda _url: _StubJWKClient(_KEY))


@pytest.fixture
def jwks_down(monkeypatch):
    monkeypatch.setattr(auth_utils, "_get_jwk_client", lambda _url: _DownJWKClient())


def _token(realm_roles=(), client_roles=(), azp=CLIENT_ID, exp_in=300, key=_KEY, username="jdoe", sid=None,
           email=None, iss=ISSUER, iat_in=0, typ="Bearer", headers=None):
    """A signed token.  exp_in, iat_in (seconds from now), iss and typ default to a valid
    access token; OMIT for any of them leaves that claim out."""
    now = int(time.time())
    claims = {"exp": exp_in, "iat": iat_in, "iss": iss, "typ": typ}
    payload = {
        "sid": sid,
        "preferred_username": username,
        "name": "John Doe",
        "azp": azp,
        "realm_access": {"roles": list(realm_roles)},
        "resource_access": {CLIENT_ID: {"roles": list(client_roles)}},
    }
    for claim, value in claims.items():
        if value is not OMIT:
            payload[claim] = now + value if claim in ("exp", "iat") else value
    if email is not None:
        payload["email"] = email
    return jwt.encode(payload, key, algorithm="RS256", headers=headers)


def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _hs256_token_keyed_by_public_pem():
    """The algorithm-confusion attack, made by hand (PyJWT refuses to sign HMAC with an
    asymmetric key): HS256 with the realm's public key, as PEM, for the secret."""
    secret = _KEY.public_key().public_bytes(serialization.Encoding.PEM,
                                            serialization.PublicFormat.SubjectPublicKeyInfo)
    now = int(time.time())
    payload = {"preferred_username": "jdoe", "azp": CLIENT_ID, "exp": now + 300, "iat": now, "iss": ISSUER,
               "typ": "Bearer", "realm_access": {"roles": ["maintenance_team"]}}
    signing_input = f"{_b64(json.dumps({'alg': 'HS256', 'typ': 'JWT'}).encode())}.{_b64(json.dumps(payload).encode())}"
    signature = hmac.new(secret, signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64(signature)}"


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _validate(app, token):
    headers = _bearer(token) if token else {}
    with app.test_request_context("/api/auth/me", headers=headers):
        return auth_utils.validate_keycloak_token(ISSUER, CLIENT_ID)


def _detail(app, token):
    """(the validator's result, g.access_detail)."""
    from flask import g
    with app.test_request_context("/api/auth/me", headers=_bearer(token)):
        return auth_utils.validate_keycloak_token(ISSUER, CLIENT_ID), g.get("access_detail")


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


class TestTokenChecks:
    """S059 § 1.3, § 5: issuer, required claims, leeway, the token's kind, the algorithm."""

    def test_another_issuer_is_refused(self, app):
        token = _token(realm_roles=["maintenance_team"], iss="https://sso.example.test/realms/Other")
        assert _detail(app, token) == (None, "invalid_token")

    @pytest.mark.parametrize("claim", ["exp_in", "iat_in", "iss"])
    def test_a_required_claim_left_out_is_refused(self, app, claim):
        assert _detail(app, _token(realm_roles=["maintenance_team"], **{claim: OMIT})) == (None, "invalid_token")

    @pytest.mark.parametrize("typ", ["ID", "Refresh", OMIT])
    def test_a_token_that_is_not_an_access_token_is_refused(self, app, typ):
        assert _detail(app, _token(realm_roles=["maintenance_team"], typ=typ)) == (None, "wrong_type")

    def test_the_typ_is_logged_cut_short_never_the_token(self, app, caplog):
        token = _token(realm_roles=["maintenance_team"], typ="X" * 50)
        with caplog.at_level(logging.WARNING):
            _detail(app, token)
        [line] = [r.getMessage() for r in caplog.records if "is not Bearer" in r.getMessage()]
        assert "'" + "X" * 19 in line and "X" * 20 not in line and token not in line

    def test_hs256_signed_with_the_public_key_is_refused(self, app):
        assert _detail(app, _hs256_token_keyed_by_public_pem()) == (None, "invalid_token")

    @pytest.mark.parametrize("times, accepted", [
        ({"iat_in": 20}, True),     # issued 20 s ahead of this clock: within the leeway
        ({"iat_in": 60}, False),
        ({"exp_in": -20}, True),    # expired 20 s ago: within the leeway
        ({"exp_in": -40}, False),
    ])
    def test_the_clock_leeway(self, app, times, accepted):
        user, _code = _detail(app, _token(realm_roles=["maintenance_team"], **times))
        assert (user is not None) == accepted

    def test_a_bad_token_is_decoded_once(self, app, monkeypatch):
        """No evict-and-retry: a bad token costs one key lookup (§ 1.1)."""
        stub = _StubJWKClient(_KEY)
        monkeypatch.setattr(auth_utils, "_get_jwk_client", lambda _url: stub)
        assert _detail(app, _token(realm_roles=["maintenance_team"], key=_OTHER_KEY)) == (None, "invalid_token")
        assert stub.calls == 1

    def test_the_key_list_fetch_times_out_after_5_s(self):
        url = "https://sso.example.test/realms/S059"
        uri = f"{url}/protocol/openid-connect/certs"
        auth_utils._jwk_clients.pop(uri, None)
        try:
            client = _REAL_GET_JWK_CLIENT(url)   # builds the client; fetches nothing yet
            assert isinstance(client, jwt.PyJWKClient)
            assert client.timeout == auth_utils.JWKS_TIMEOUT_S == 5
        finally:
            auth_utils._jwk_clients.pop(uri, None)


class TestLoginServerDown:
    """S059 § 1.2: a key-list fetch failure answers 503 with its own message and detail."""

    def test_the_validator_raises(self, app, jwks_down):
        with app.test_request_context("/api/auth/me", headers=_bearer(_token(realm_roles=["maintenance_team"]))):
            with pytest.raises(auth_utils.LoginServerUnavailable):
                auth_utils.validate_keycloak_token(ISSUER, CLIENT_ID)

    @pytest.mark.parametrize("headers", [None, {"kid": "unknown-key"}])
    def test_the_handler_answers_503_and_marks_the_outcome(self, app, jwks_down, headers):
        """A token with an unknown key id (junk) gets the same 503 during an outage (BR1-03)."""
        from flask import g
        token = _token(client_roles=["maintenance_team"], headers=headers)
        with app.test_request_context("/api/auth/me", headers=_bearer(token)):
            body, status = auth_utils.require_auth(ISSUER, CLIENT_ID)()
            assert status == 503
            assert body.get_json() == {"error": auth_utils.LOGIN_SERVER_DOWN_TEXT}
            assert (g.access_outcome, g.access_detail) == ("auth_failed", "login_server_down")

    @pytest.mark.parametrize("exc", [
        ConnectionResetError(10054, "connection reset mid-body"),
        json.JSONDecodeError("Expecting value", "<html>maintenance</html>", 0),   # an HTML page with 200
    ], ids=["connection_reset", "html_page"])
    def test_an_unreadable_key_list_answers_503(self, app, monkeypatch, exc):
        """PyJWT wraps only URLError, TimeoutError and HTTPException; the others are an outage too (CR1-01)."""
        from flask import g
        monkeypatch.setattr(auth_utils, "_get_jwk_client", lambda _url: _RaisingJWKClient(exc))
        with app.test_request_context("/api/auth/me", headers=_bearer(_token(client_roles=["maintenance_team"]))):
            body, status = auth_utils.require_auth(ISSUER, CLIENT_ID)()
            assert status == 503
            assert body.get_json() == {"error": auth_utils.LOGIN_SERVER_DOWN_TEXT}
            assert (g.access_outcome, g.access_detail) == ("auth_failed", "login_server_down")

    def test_a_token_with_a_junk_header_stays_401(self, app, monkeypatch):
        """The real client reads the header before any fetch: a header that is not JSON is a
        token error (DecodeError), never the outage's 503 (CR1-01)."""
        url = "https://sso.example.test/realms/S059junk"
        uri = f"{url}/protocol/openid-connect/certs"
        auth_utils._jwk_clients.pop(uri, None)
        monkeypatch.setattr(auth_utils, "_get_jwk_client", _REAL_GET_JWK_CLIENT)
        junk = f"{_b64(b'not json')}.{_b64(b'{}')}.{_b64(b'sig')}"
        try:
            with app.test_request_context("/api/auth/me", headers=_bearer(junk)):
                assert auth_utils.validate_keycloak_token(url, CLIENT_ID) is None
                from flask import g
                assert g.access_detail == "invalid_token"
        finally:
            auth_utils._jwk_clients.pop(uri, None)

    def test_through_the_app_and_the_access_log(self, client, jwks_down, db_rows, uniq):
        n = int(uniq.username()[4:])
        address = f"198.18.{n // 250 % 250}.{n % 250 + 1}"   # a range of its own, apart from test_access_log_api's
        res = client.get("/api/auth/me", headers={**_bearer(_token(client_roles=["maintenance_team"])),
                                                  "X-Real-IP": address})
        assert res.status_code == 503
        assert res.get_json() == {"error": auth_utils.LOGIN_SERVER_DOWN_TEXT}
        rows = db_rows("SELECT outcome, detail, username FROM access_log WHERE client_ip = %s", (address,))
        assert [(r["outcome"], r["detail"], r["username"]) for r in rows] == [
            ("auth_failed", "login_server_down", None)]


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
            assert auth_utils.validate_keycloak_token(ISSUER, CLIENT_ID) is None
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
