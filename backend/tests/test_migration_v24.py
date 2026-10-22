"""v24, web push subscriptions (S021 § 4, § 10 BS1-02), in the upgrade database vel_yantra_upgrade
that the v20-v23 migration tests also use (pytest runs the files one after another, so they do
not collide).  A fresh database gets v24; a v23 database with a ticket and a person gets the
push_subscriptions table and keeps every existing row; a re-run changes nothing.  Needs the dev
MariaDB container.
"""

import local_db
from tests.test_migration_v20 import _migrate, _recreate, _run, _schema
from tests.test_migration_v22 import _fill_one_ticket

V23 = [m for m in local_db._MIGRATIONS if m[0] in (20, 21, 22, 23)]
V24 = [m for m in local_db._MIGRATIONS if m[0] in (20, 21, 22, 23, 24)]


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]


def _columns(table):
    return {r["COLUMN_NAME"]: (r["COLUMN_TYPE"], r["IS_NULLABLE"], r["COLUMN_DEFAULT"]) for r in _run(
        "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT FROM information_schema.COLUMNS"
        " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", (table,))}


def test_a_fresh_database_gets_v24():
    _recreate()
    _migrate(V24)
    assert _versions() == [20, 21, 22, 23, 24]
    assert "push_subscriptions" in {r["TABLE_NAME"] for r in _run(
        "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()")}


def test_a_v23_database_gets_v24():
    _recreate()
    _migrate(V23)
    _fill_one_ticket()
    _run("INSERT INTO people (name, employment, username, created_by) VALUES ('Priya', 'direct', 'priya', 'kla')")
    before = {table: _run(f"SELECT * FROM {table} ORDER BY id") for table in ("tickets", "people")}

    _migrate(V24)
    assert _versions() == [20, 21, 22, 23, 24]
    assert {table: _run(f"SELECT * FROM {table} ORDER BY id") for table in ("tickets", "people")} == before

    assert _columns("push_subscriptions") == {
        "id": ("int(11)", "NO", None),
        "person_id": ("int(11)", "NO", None),
        "endpoint": ("varchar(1000)", "NO", None),
        "endpoint_hash": ("char(64)", "NO", None),
        "p256dh": ("varchar(200)", "NO", None),
        "auth": ("varchar(100)", "NO", None),
        "label": ("varchar(100)", "NO", None),
        "created_at": ("datetime", "NO", "current_timestamp()"),
        "last_sent_at": ("datetime", "YES", "NULL"),
        "last_error": ("varchar(255)", "YES", "NULL"),
    }
    indexes = {(r["INDEX_NAME"], r["COLUMN_NAME"], r["NON_UNIQUE"]) for r in _run(
        "SELECT INDEX_NAME, COLUMN_NAME, NON_UNIQUE FROM information_schema.STATISTICS"
        " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'push_subscriptions'")}
    assert indexes == {("PRIMARY", "id", 0), ("uq_push_subscriptions_endpoint", "endpoint_hash", 0),
                       ("ix_push_subscriptions_person", "person_id", 1)}
    foreign_keys = {(r["CONSTRAINT_NAME"], r["COLUMN_NAME"], r["REFERENCED_TABLE_NAME"]) for r in _run(
        "SELECT CONSTRAINT_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME FROM information_schema.KEY_COLUMN_USAGE"
        " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'push_subscriptions'"
        " AND REFERENCED_TABLE_NAME IS NOT NULL")}
    assert foreign_keys == {("fk_push_subscriptions_person", "person_id", "people")}

    # The escalation defaults are seeded (S021 § 4.2)
    assert {r["setting_key"]: r["setting_value"] for r in _run(
        "SELECT setting_key, setting_value FROM app_settings WHERE setting_key LIKE 'escalate_minutes_%%'")} == {
        "escalate_minutes_a": "10", "escalate_minutes_b": "30", "escalate_minutes_c": "60"}

    # Re-run: v24 twice is a no-op, and a value IT admin changed is kept
    _run("UPDATE app_settings SET setting_value = '45' WHERE setting_key = 'escalate_minutes_c'")
    schema = _schema()
    _run("DELETE FROM db_version WHERE version = 24")
    _migrate(V24)
    assert _versions() == [20, 21, 22, 23, 24]
    assert _schema() == schema
    assert list(_run("SELECT setting_value FROM app_settings WHERE setting_key = 'escalate_minutes_c'")) == [
        {"setting_value": "45"}]
