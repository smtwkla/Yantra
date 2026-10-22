"""The JSON error handlers (S025 § 1.3): an unknown /api path, a wrong method and any unhandled
exception answer {error} with their status, never Flask's HTML page; a lost database
connection is a 503 like DBUnavailable; other OperationalErrors (a deadlock) are the 500."""

import logging

import pymysql
import pytest

from tests.conftest import SERVER_ERROR, server_error


@pytest.fixture
def failing_version(app, monkeypatch):
    """/api/version (public, no database) raises ``exc`` when called."""
    def install(exc):
        def boom():
            raise exc
        monkeypatch.setitem(app.view_functions, "version", boom)
    return install


def test_unknown_api_path_is_json_404(admin):
    res = admin.get("/api/no-such-thing")
    assert (res.status_code, res.get_json()) == (404, {"error": "Not found"})


def test_wrong_method_is_json_405(admin):
    res = admin.delete("/api/version")
    assert (res.status_code, res.get_json()) == (405, {"error": "Not allowed"})


def test_an_unhandled_exception_is_json_500_and_logged(client, failing_version, caplog):
    failing_version(RuntimeError("forced"))
    with caplog.at_level(logging.ERROR, logger="api_common"):
        res = client.get("/api/version")
    assert server_error(res) == SERVER_ERROR
    assert any(r.exc_info and "forced" in str(r.exc_info[1]) for r in caplog.records)


def test_a_lost_connection_is_503(client, failing_version):
    failing_version(pymysql.err.OperationalError(2013, "Lost connection to server during query"))
    res = client.get("/api/version")
    assert (res.status_code, res.get_json()) == (503, {"error": "Database unavailable — try again shortly"})


def test_a_deadlock_is_the_500(client, failing_version):
    failing_version(pymysql.err.OperationalError(1213, "Deadlock found when trying to get lock"))
    assert server_error(client.get("/api/version")) == SERVER_ERROR


def test_an_api_error_keeps_its_own_handler(admin):
    # The most specific handler wins: an ApiError is still {error, field?} with its status
    res = admin.get("/api/equipment?page=0")
    assert res.status_code == 400 and res.get_json()["field"] == "page"
