"""The schema docs' shell (S078): build a fresh database from backend/local_db.py _MIGRATIONS,
read its catalogue, and write or check docs/schema/schema.json and docs/schema/schema-data.js.

    uv run python tooling/schema/schema_docs.py write|check     (from backend/, in its uv project)

Run it through tooling\\schema-docs.bat, which keeps a log and prints the summary line.  All
decisions (the texts, the checks, the messages, the exit code) are in schema_docs_core.py;
this file fetches, locks, drops, writes and prints.

The database is vel_yantra_test_<run>_schemadocs (backend/tests/db_names.py SCHEMA_DOCS_DB),
<run> from YANTRA_TEST_RUN: dropped and created before the migrations run, dropped again after
the read, under a named lock, so two runs with one run name never share it.
Exit codes: 0 every check passed, 1 a check failed, 2 not completed.
"""

import logging
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# A script run by path has only its own folder on sys.path: the backend's modules need theirs
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
# Lets config.py fall back to example_secrets_app.py (the dev container) in a worktree without
# secrets_app.py, as the backend tests do (conftest.py); set before config is imported
os.environ["YANTRA_TESTING"] = "1"

import pymysql  # noqa: E402
import pymysql.cursors  # noqa: E402

import config  # noqa: E402
import local_db  # noqa: E402
import schema_docs_core as core  # noqa: E402
from tests.db_names import SCHEMA_DOCS_DB  # noqa: E402

LOCK_BASE = "yantra_schema_docs"
LOCK_WAIT_S = 60
CONNECT_TIMEOUT_S = 5
ACCESS_DENIED_TO_DATABASE = 1044   # MariaDB ER_DBACCESS_DENIED_ERROR

CATALOGUE_QUERIES = {
    "tables": """SELECT TABLE_NAME FROM information_schema.TABLES
                 WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'""",
    "columns": """SELECT TABLE_NAME, COLUMN_NAME, ORDINAL_POSITION, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, EXTRA
                  FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = %s""",
    "statistics": """SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME, SUB_PART
                     FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = %s""",
    "foreign_keys": """SELECT k.CONSTRAINT_NAME, k.TABLE_NAME, k.COLUMN_NAME, k.ORDINAL_POSITION,
                              k.REFERENCED_TABLE_NAME, k.REFERENCED_COLUMN_NAME, r.DELETE_RULE, r.UPDATE_RULE
                       FROM information_schema.KEY_COLUMN_USAGE k
                       JOIN information_schema.REFERENTIAL_CONSTRAINTS r
                         ON r.CONSTRAINT_SCHEMA = k.CONSTRAINT_SCHEMA AND r.CONSTRAINT_NAME = k.CONSTRAINT_NAME
                        AND r.TABLE_NAME = k.TABLE_NAME
                       WHERE k.TABLE_SCHEMA = %s""",
    # CHECK_CONSTRAINTS has no TABLE_SCHEMA column
    "checks": """SELECT TABLE_NAME, CONSTRAINT_NAME, LEVEL, CHECK_CLAUSE
                 FROM information_schema.CHECK_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = %s""",
}


class NotCompleted(Exception):
    """The run could not check: the message is the user's (schema_docs_core's texts)."""


def read_catalogue(cur, database):
    """The five row sets the core takes, as plain dicts (a DictCursor's rows)."""
    catalogue = {}
    for key, sql in CATALOGUE_QUERIES.items():
        cur.execute(sql, (database,))
        catalogue[key] = [dict(row) for row in cur.fetchall()]
    return catalogue


def _recreate_database(cur, name):
    """DROP and CREATE, as tooling/e2e/e2e_backend.py _recreate_database does."""
    try:
        cur.execute(f"DROP DATABASE IF EXISTS `{name}`")
        cur.execute(f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    except pymysql.MySQLError as exc:
        if exc.args and exc.args[0] == ACCESS_DENIED_TO_DATABASE:
            raise NotCompleted(core.create_refused_message(name)) from exc
        raise


def build_and_read(db_config):
    """(migration, catalogue) of a database built fresh from _MIGRATIONS; dropped again after."""
    name = db_config["database"]
    try:
        conn = pymysql.connect(host=db_config["host"], port=db_config["port"], user=db_config["user"],
                               password=db_config["password"], autocommit=True, charset="utf8mb4",
                               cursorclass=pymysql.cursors.DictCursor, connect_timeout=CONNECT_TIMEOUT_S)
    except pymysql.MySQLError as exc:
        raise NotCompleted(core.unreachable_message(local_db.describe_error(exc))) from exc
    lock = local_db.named_lock(LOCK_BASE, name)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT GET_LOCK(%s, %s) AS got", (lock, LOCK_WAIT_S))
            if cur.fetchone()["got"] != 1:
                raise NotCompleted(core.LOCK_TIMEOUT_MESSAGE)
            try:
                _recreate_database(cur, name)
                try:
                    local_db.init_db(db_config)
                except (pymysql.MySQLError, local_db.DBUnavailable) as exc:
                    raise NotCompleted(core.migration_failed_message(local_db.describe_error(exc))) from exc
                catalogue = read_catalogue(cur, name)
                cur.execute(f"SELECT MAX(version) AS version FROM `{name}`.db_version")
                migration = cur.fetchone()["version"]
            finally:
                cur.execute(f"DROP DATABASE IF EXISTS `{name}`")
                cur.execute("SELECT RELEASE_LOCK(%s)", (lock,))
    except pymysql.MySQLError as exc:
        raise NotCompleted(core.unreachable_message(local_db.describe_error(exc))) from exc
    finally:
        conn.close()
    if migration != local_db.LATEST_VERSION:
        raise NotCompleted(core.version_mismatch_message(migration, local_db.LATEST_VERSION))
    return migration, catalogue


def _read_text(path):
    """The file's text, or None when it is missing."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def _write_text(path, text):
    """UTF-8, no BOM, the text's own LF line ends (newline="" writes them unchanged)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def _finish(result):
    code, lines = result
    for line in lines:
        print(line, flush=True)
    return code


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0] not in ("write", "check"):
        print(core.usage_message())
        return core.EXIT_NOT_COMPLETED
    mode = args[0]
    # Read here, not at import, so a test's monkeypatch of config.DB_CONFIG takes effect
    db_config = {**config.DB_CONFIG, "database": SCHEMA_DOCS_DB}
    refusal = core.check_target(db_config["host"], db_config["database"])
    if refusal:
        return _finish(core.outcome(None, not_completed=refusal))

    # The notes first: an invalid file ends the run before a migration build
    notes, notes_problem = core.parse_notes(_read_text(REPO / core.NOTES_JSON))
    if notes_problem:
        return _finish(core.outcome(local_db.LATEST_VERSION, core.checks_without_notes(notes_problem)))

    try:
        migration, catalogue = build_and_read(db_config)
    except NotCompleted as exc:
        return _finish(core.outcome(None, not_completed=str(exc)))

    schema = core.build_schema(catalogue, migration)
    generated = core.files_to_write(schema, notes)
    if mode == "write":
        for path, text in generated.items():
            _write_text(REPO / path, text)
    on_disk = {path: _read_text(REPO / path) for path in generated}
    return _finish(core.outcome(migration, core.run_checks(schema, notes, on_disk, generated)))


if __name__ == "__main__":
    # init_db's "Applying migration vN" lines show the last version tried above a failure
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(main())
