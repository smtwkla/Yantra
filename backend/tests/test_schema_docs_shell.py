"""The schema docs' shell, tooling/schema/schema_docs.py (S078 § 8.2): the database down, the
guard before any drop, and the catalogue reader.  None of these builds SCHEMA_DOCS_DB: the full
build runs in tooling\\schema-docs.bat, so this suite stays fast and takes no schema docs lock."""
import socket
import sys
from pathlib import Path

import config
import local_db
from tests.db_names import SCHEMA_DOCS_DB, TEST_DB

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tooling" / "schema"))

import schema_docs  # noqa: E402


def _unused_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _never(name):
    def fail(*_args, **_kwargs):
        raise AssertionError(f"{name} must not be called")
    return fail


def test_database_down_ends_with_exit_2_and_writes_nothing(monkeypatch, capsys):
    monkeypatch.setitem(config.DB_CONFIG, "host", "127.0.0.1")
    monkeypatch.setitem(config.DB_CONFIG, "port", _unused_port())
    monkeypatch.setattr(schema_docs, "_write_text", _never("_write_text"))
    monkeypatch.setattr(schema_docs.local_db, "init_db", _never("init_db"))   # the first connection fails, before the lock

    assert schema_docs.main(["write"]) == 2

    out = capsys.readouterr().out.splitlines()
    assert out[-2].startswith("The schema docs were not built. The dev database cannot be reached: ")
    assert out[-2].endswith(r"Start it with tooling\dev\dev-db-up.bat, then run the command again.")
    assert out[-1] == "Schema docs: not completed"


def test_guard_refuses_a_remote_host_before_any_connection(monkeypatch, capsys):
    monkeypatch.setitem(config.DB_CONFIG, "host", "db.example.test")
    monkeypatch.setattr(schema_docs.pymysql, "connect", _never("pymysql.connect"))

    assert schema_docs.main(["check"]) == 2

    out = capsys.readouterr().out.splitlines()
    assert out == ["The schema docs were not built: refusing database host db.example.test; "
                   "the schema docs database must be local (localhost, 127.0.0.1).",
                   "Schema docs: not completed"]


class _FakeCursor:
    """Answers the lock calls; fails a statement that starts with a given text, with a MySQL error."""

    def __init__(self, fail_on=None, fail_code=1064):
        self.fail_on, self.fail_code, self.last = fail_on, fail_code, ""

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def execute(self, sql, _args=None):
        self.last = sql
        if self.fail_on and sql.startswith(self.fail_on):
            raise schema_docs.pymysql.err.OperationalError(self.fail_code, "boom")

    def fetchone(self):
        return {"got": 1} if "GET_LOCK" in self.last else {"version": local_db.LATEST_VERSION}


class _FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def close(self):
        pass


def _run_with_fake(monkeypatch, capsys, cursor, init_db=lambda _cfg: None):
    monkeypatch.setattr(schema_docs.pymysql, "connect", lambda **_kw: _FakeConn(cursor))
    monkeypatch.setattr(schema_docs.local_db, "init_db", init_db)
    monkeypatch.setattr(schema_docs, "read_catalogue", lambda _cur, _name: {})
    monkeypatch.setattr(schema_docs, "_write_text", _never("_write_text"))
    code = schema_docs.main(["write"])
    return code, capsys.readouterr().out.splitlines()


def test_a_ddl_error_other_than_1044_gives_its_own_message(monkeypatch, capsys):
    code, out = _run_with_fake(monkeypatch, capsys, _FakeCursor(fail_on="CREATE DATABASE"))
    assert code == 2
    assert "cannot be reached" not in out[-2]
    assert out[-2].startswith("The schema docs were not built. The database refused a command: ")
    assert out[-1] == "Schema docs: not completed"


def test_a_failed_final_drop_is_named_and_does_not_say_unreachable(monkeypatch, capsys):
    code, out = _run_with_fake(monkeypatch, capsys, _DropFailsAfterBuild())
    assert code == 2
    assert "cannot be reached" not in out[-2]
    assert " could not be dropped: " in out[-2] and out[-2].endswith("by hand, then run the command again.")


def test_a_failed_drop_does_not_hide_the_migration_failure(monkeypatch, capsys):
    def bad_init(_cfg):
        raise schema_docs.pymysql.err.OperationalError(1146, "table gone")

    code, out = _run_with_fake(monkeypatch, capsys, _DropFailsAfterBuild(), init_db=bad_init)
    assert code == 2
    assert out[-2].startswith("The schema docs were not built. The migrations could not be applied: ")


class _DropFailsAfterBuild(_FakeCursor):
    """The first DROP (before the build) works; the second (the clean-up) fails."""

    def __init__(self):
        super().__init__()
        self.drops = 0

    def execute(self, sql, _args=None):
        self.last = sql
        if sql.startswith("DROP DATABASE"):
            self.drops += 1
            if self.drops == 2:
                raise schema_docs.pymysql.err.OperationalError(1051, "boom")


def test_a_failed_lock_release_is_not_a_failed_drop(monkeypatch, capsys, caplog):
    # S078 CR2-01: the drop worked; a RELEASE_LOCK error is only logged, the run goes on to the checks
    monkeypatch.setattr(schema_docs.pymysql, "connect",
                        lambda **_kw: _FakeConn(_FakeCursor(fail_on="SELECT RELEASE_LOCK")))
    monkeypatch.setattr(schema_docs.local_db, "init_db", lambda _cfg: None)
    empty = {key: [] for key in ("tables", "columns", "statistics", "foreign_keys", "checks")}
    monkeypatch.setattr(schema_docs, "read_catalogue", lambda _cur, _name: empty)
    monkeypatch.setattr(schema_docs, "_write_text", _never("_write_text"))
    code = schema_docs.main(["check"])
    out = capsys.readouterr().out
    assert code == 1  # the empty fake catalogue fails the checks; the run was completed
    assert "could not be dropped" not in out and "not completed" not in out
    assert "The schema docs lock was not released" in caplog.text


def test_wrong_mode_prints_the_usage(capsys):
    assert schema_docs.main(["draw"]) == 2
    assert capsys.readouterr().out.strip() == r"Usage: tooling\schema-docs.bat write|check"


def test_catalogue_reader_on_the_suite_database():
    conn = local_db.get_local_db(config.DB_CONFIG)
    try:
        with conn.cursor() as cur:
            catalogue = schema_docs.read_catalogue(cur, TEST_DB)
    finally:
        conn.close()

    assert set(catalogue) == {"tables", "columns", "statistics", "foreign_keys", "checks"}
    tables = {row["TABLE_NAME"] for row in catalogue["tables"]}
    assert {"db_version", "people"} <= tables
    assert all(isinstance(row, dict) for rows in catalogue.values() for row in rows)
    people_id = next(r for r in catalogue["columns"] if r["TABLE_NAME"] == "people" and r["COLUMN_NAME"] == "id")
    assert set(people_id) == {"TABLE_NAME", "COLUMN_NAME", "ORDINAL_POSITION", "COLUMN_TYPE", "IS_NULLABLE",
                              "COLUMN_DEFAULT", "EXTRA"}
    assert catalogue["foreign_keys"] and catalogue["checks"]
    assert set(catalogue["checks"][0]) == {"TABLE_NAME", "CONSTRAINT_NAME", "LEVEL", "CHECK_CLAUSE"}

    # The core takes the rows as they come
    schema = schema_docs.core.build_schema(catalogue, local_db.LATEST_VERSION)
    assert schema["tables"]["people"]["primary_key"] == ["id"]

    assert SCHEMA_DOCS_DB.startswith("vel_yantra_test_") and SCHEMA_DOCS_DB.endswith("_schemadocs")
