"""/api/health (S025 § 1.1): public, always 200, and schema_ready — whether this worker's
ensure_schema() finds the schema up to date.  The deploy waits for schema_ready: true."""

import app as app_module


def test_schema_ready_on_the_test_database(client):
    res = client.get("/api/health")
    assert (res.status_code, res.get_json()) == (200, {"status": "ok", "schema_ready": True})


def test_not_ready_is_still_200_with_no_reason(client, monkeypatch):
    # The session's schema is already up to date, so init_db would not run: the route's own
    # reference is replaced, as test_auth's db_down does (BR2-06)
    monkeypatch.setattr(app_module, "ensure_schema", lambda _config: "Drop the old equipment table first")
    res = client.get("/api/health")
    assert (res.status_code, res.get_json()) == (200, {"status": "ok", "schema_ready": False})
