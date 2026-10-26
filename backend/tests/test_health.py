"""/api/health (S025 § 1.1): public, always 200, and schema_ready — whether this worker's
ensure_schema() finds the schema up to date.  The deploy waits for schema_ready: true."""

import app as app_module


def test_schema_ready_on_the_test_database(client):
    res = client.get("/api/health")
    assert (res.status_code, res.get_json()) == (200, {"status": "ok", "schema_ready": True})


def test_not_ready_is_still_200_with_no_reason(client, monkeypatch):
    # The session's schema is already up to date, so init_db would not run: the route's own
    # reference is replaced, as conftest's db_down does (BR2-06)
    monkeypatch.setattr(app_module, "ensure_schema", lambda _config: "Drop the old equipment table first")
    res = client.get("/api/health")
    assert (res.status_code, res.get_json()) == (200, {"status": "ok", "schema_ready": False})


def test_no_cors_headers_are_sent(client):
    # S060: production served the dev origin in Access-Control-Allow-Origin because Flask-CORS
    # sends its literal origins when a request has no Origin header.  The app is same-origin
    # (Nginx in production, Vite's proxy in dev), so no response carries a CORS header.
    for headers in ({}, {"Origin": "http://localhost:5176"}):
        res = client.get("/api/health", headers=headers)
        assert "Access-Control-Allow-Origin" not in res.headers, headers
