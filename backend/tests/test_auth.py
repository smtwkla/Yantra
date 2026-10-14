"""Keycloak token validation and the auth middleware.

Tokens are signed with a throwaway RSA key and the JWKS lookup is stubbed,
so these run without a Keycloak server.
"""

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

import auth_utils
import config

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


def _token(realm_roles=(), client_roles=(), azp=CLIENT_ID, exp_in=300, key=_KEY):
    payload = {
        "preferred_username": "jdoe",
        "name": "John Doe",
        "azp": azp,
        "exp": int(time.time()) + exp_in,
        "realm_access": {"roles": list(realm_roles)},
        "resource_access": {CLIENT_ID: {"roles": list(client_roles)}},
    }
    return jwt.encode(payload, key, algorithm="RS256")


def _validate(app, token):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    with app.test_request_context("/api/auth/me", headers=headers):
        return auth_utils.validate_keycloak_token("https://sso.example/realms/R", CLIENT_ID)


class TestValidateToken:

    def test_storekeeper_client_role_accepted(self, app):
        user = _validate(app, _token(client_roles=["maint_storekeeper"]))
        assert user["roles"] == ["maint_storekeeper"]
        assert user["permissions"] == ["masters:read"]

    def test_realm_role_maps_to_user(self, app):
        user = _validate(app, _token(realm_roles=["maint_operator", "offline_access"]))
        assert user["username"] == "jdoe"
        assert user["name"] == "John Doe"
        assert user["roles"] == ["maint_operator"]
        assert user["permissions"] == ["masters:read"]

    def test_client_roles_count_too(self, app):
        user = _validate(app, _token(client_roles=["it_admin"]))
        assert user["role"] == "it_admin"

    def test_multiple_roles_primary_is_most_privileged(self, app):
        user = _validate(app, _token(realm_roles=["maint_operator", "maint_manager"]))
        assert user["roles"] == ["maint_manager", "maint_operator"]
        assert user["role"] == "maint_manager"

    @pytest.mark.parametrize("admin_role", ["admin", "mspv-apps-admin"])
    def test_admin_realm_roles_map_to_admin(self, app, admin_role):
        user = _validate(app, _token(realm_roles=[admin_role, "maint_operator"]))
        assert user["roles"] == ["admin"]
        assert "settings:edit" in user["permissions"]

    def test_no_recognised_role_is_rejected(self, app):
        assert _validate(app, _token(realm_roles=["offline_access"])) is None

    def test_wrong_client_is_rejected(self, app):
        assert _validate(app, _token(realm_roles=["maint_operator"], azp="other-app")) is None

    def test_expired_token_is_rejected(self, app):
        assert _validate(app, _token(realm_roles=["maint_operator"], exp_in=-60)) is None

    def test_bad_signature_is_rejected(self, app):
        assert _validate(app, _token(realm_roles=["maint_operator"], key=_OTHER_KEY)) is None

    def test_missing_header_is_rejected(self, app):
        assert _validate(app, None) is None


class TestMiddleware:

    @pytest.mark.parametrize("path", ["/api/health", "/api/version", "/api/auth/config"])
    def test_public_paths_need_no_token(self, client, path):
        assert client.get(path).status_code == 200

    def test_protected_path_without_token_is_401(self, client):
        assert client.get("/api/auth/me").status_code == 401

    def test_valid_bearer_token_reaches_route(self, client):
        token = _token(realm_roles=["maint_engineer"])
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        body = res.get_json()
        assert body["name"] == "John Doe"
        assert body["role"] == "maint_engineer"
        assert "equipment:edit" in body["permissions"]

    def test_auth_config_exposes_realm_and_client(self, client):
        body = client.get("/api/auth/config").get_json()
        assert body == {
            "url": config.KEYCLOAK_URL,
            "realm": config.KEYCLOAK_REALM,
            "clientId": CLIENT_ID,
            "devBypass": False,
        }


class TestInternalUrl:

    def test_rewrites_to_lan_ip_on_8080(self):
        assert auth_utils._make_internal_url(
            "https://sso.mspv.app/realms/Office.smtw.in", "10.24.0.119"
        ) == "http://10.24.0.119:8080/realms/Office.smtw.in"

    def test_empty_ip_keeps_public_url(self):
        url = "https://sso.mspv.app/realms/Office.smtw.in"
        assert auth_utils._make_internal_url(url, "") == url
