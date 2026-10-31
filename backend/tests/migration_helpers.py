"""The migration tests' shared helpers, moved unchanged from the v20 squash's test file (S088 D7).

Each test file runs migrations in its own database (UPGRADE_DB, one per test run and worker:
tests/db_names.py), dropped and created by _recreate.  _migrate runs the engine with a given
migration list by replacing local_db._MIGRATIONS; the engine itself is unchanged.  Needs the
dev MariaDB container.
"""

import pymysql
import pytest

import config
import local_db
from local_db import get_local_db, init_db
from tests.db_names import UPGRADE_DB

UPGRADE_CONFIG = {**config.DB_CONFIG, "database": UPGRADE_DB}

# The squashed migration (v41), which the per-version tests start from (S088).
SQUASHED = [m for m in local_db._MIGRATIONS if m[0] == 41]


def _recreate():
    """An empty upgrade database, as tooling/e2e/e2e_backend.py makes the e2e one."""
    conn = pymysql.connect(host=UPGRADE_CONFIG["host"], port=UPGRADE_CONFIG["port"], user=UPGRADE_CONFIG["user"],
                           password=UPGRADE_CONFIG["password"], autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS `{UPGRADE_DB}`")
            cur.execute(f"CREATE DATABASE `{UPGRADE_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    finally:
        conn.close()


def _run(sql, params=()):
    conn = get_local_db(UPGRADE_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def _migrate(migrations):
    """init_db on the upgrade database with ``migrations`` as the migration list."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(local_db, "_MIGRATIONS", migrations)
        init_db(UPGRADE_CONFIG)


def _rows(sql):
    return sorted(tuple(r.values()) for r in _run(sql))


def _schema():
    """Everything a migration defines, from information_schema, for this database only."""
    return {
        "tables": _rows("SELECT TABLE_NAME, ENGINE, TABLE_COLLATION FROM information_schema.TABLES"
                        " WHERE TABLE_SCHEMA = DATABASE()"),
        "columns": _rows("SELECT TABLE_NAME, ORDINAL_POSITION, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT,"
                         " EXTRA, CHARACTER_SET_NAME, COLLATION_NAME FROM information_schema.COLUMNS"
                         " WHERE TABLE_SCHEMA = DATABASE()"),
        # Including the indexes MariaDB creates for foreign keys
        "indexes": _rows("SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME"
                         " FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE()"),
        "foreign_keys": _rows("SELECT CONSTRAINT_NAME, TABLE_NAME, REFERENCED_TABLE_NAME, DELETE_RULE, UPDATE_RULE"
                              " FROM information_schema.REFERENTIAL_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = DATABASE()"),
        "foreign_key_columns": _rows(
            "SELECT CONSTRAINT_NAME, TABLE_NAME, ORDINAL_POSITION, COLUMN_NAME, REFERENCED_TABLE_NAME,"
            " REFERENCED_COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE"
            " WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL"),
        "checks": _rows("SELECT TABLE_NAME, CONSTRAINT_NAME, CHECK_CLAUSE FROM information_schema.CHECK_CONSTRAINTS"
                        " WHERE CONSTRAINT_SCHEMA = DATABASE()"),
    }


def _versions():
    return [r["version"] for r in _run("SELECT version FROM db_version ORDER BY version")]
