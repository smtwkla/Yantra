"""The browser tests' backend refuses any database but a local *_e2e one, before it drops
anything (S024 § 5.1): tooling/e2e/e2e_backend.check_target."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tooling", "e2e"))

from e2e_backend import check_target  # noqa: E402  (after the path above)


def _db(host="127.0.0.1", database="vel_yantra_e2e"):
    return {"host": host, "port": 3307, "user": "u", "password": "p", "database": database}


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost"])
def test_a_local_e2e_database_is_accepted(host):
    assert check_target(_db(host=host)) is None


@pytest.mark.parametrize("database", ["vel_yantra_test", "vel_yantra_master", "vel_yantra_e2e_old", "", None])
def test_any_other_database_is_refused(database):
    assert "must end in _e2e" in check_target(_db(database=database))


@pytest.mark.parametrize("host", ["10.24.0.30", "db.smtw.in", "", None])
def test_a_database_on_another_host_is_refused(host):
    assert "must be local" in check_target(_db(host=host))
