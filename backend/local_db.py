"""Owned database — migration engine, connection pool and status probe.

Manages the application's MariaDB database with automatic migrations.
Each migration is a (version, description, [sql_statements]) tuple.
Append new migrations with incrementing version numbers — never edit old ones.

The app must keep running while the database is unreachable or not yet
created (a fresh deployment): nothing here connects at import, and
ensure_schema() retries the migrations on later requests, so the app picks the
database up without a restart once it exists.
"""

import logging
import threading
import time

import pymysql
import pymysql.cursors
from dbutils.pooled_db import PooledDB

logger = logging.getLogger(__name__)

# DB-level named lock (GET_LOCK) — one process runs migrations at a time.
LOCK_MIGRATIONS = "yantra_migrations"

# Seconds between migration attempts while the database is unavailable
_RETRY_INTERVAL_S = 30

# ---------------------------------------------------------------------------
# Migrations — append new versions after the last one
# ---------------------------------------------------------------------------

_MIGRATIONS = [
    (1, "Core tables", [
        """CREATE TABLE IF NOT EXISTS db_version (
            version     INT PRIMARY KEY,
            description VARCHAR(255),
            applied_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS app_settings (
            setting_key   VARCHAR(100) PRIMARY KEY,
            setting_value TEXT,
            updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )""",
    ]),
    # Audit convention for every table: created_* set on insert, updated_* stay
    # NULL until the first edit (set together by the application, never by
    # ON UPDATE, so a time is never recorded without an actor).
    (2, "Basic masters: sites, units, equipment classes, unit access", [
        """CREATE TABLE IF NOT EXISTS sites (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            code        VARCHAR(20) NOT NULL,
            name        VARCHAR(100) NOT NULL,
            address     VARCHAR(255) NULL,
            active      TINYINT(1) NOT NULL DEFAULT 1,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            CONSTRAINT uq_sites_code UNIQUE (code)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS units (
            id               INT AUTO_INCREMENT PRIMARY KEY,
            site_id          INT NOT NULL,
            code             VARCHAR(20) NOT NULL,
            name             VARCHAR(100) NOT NULL,
            oneerp_warehouse VARCHAR(140) NULL,
            active           TINYINT(1) NOT NULL DEFAULT 1,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            CONSTRAINT uq_units_site_code UNIQUE (site_id, code),
            CONSTRAINT uq_units_warehouse UNIQUE (oneerp_warehouse),
            CONSTRAINT fk_units_site FOREIGN KEY (site_id) REFERENCES sites (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS equipment_classes (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            code        VARCHAR(4) NOT NULL,
            name        VARCHAR(100) NOT NULL,
            active      TINYINT(1) NOT NULL DEFAULT 1,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            CONSTRAINT uq_equipment_classes_code UNIQUE (code)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS user_units (
            username    VARCHAR(100) NOT NULL,
            unit_id     INT NOT NULL,
            granted_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            granted_by  VARCHAR(100) NOT NULL,
            PRIMARY KEY (username, unit_id),
            CONSTRAINT fk_user_units_unit FOREIGN KEY (unit_id) REFERENCES units (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    ]),
    # is_default is 1 for the default site and NULL for all others (never 0), so the
    # UNIQUE index - which allows many NULLs - lets the database guarantee at most one default.
    (3, "Default site", [
        "ALTER TABLE sites ADD COLUMN is_default TINYINT(1) NULL AFTER active",
        "ALTER TABLE sites ADD CONSTRAINT uq_sites_default UNIQUE (is_default)",
    ]),
    # The equipment register (S002).  serial_counters is a counter, not a record, so no
    # audit columns; it is shared by later serials (BD-, PM-).  equipment_events is a
    # history log — equipment's own columns stay the truth, nothing replays the events.
    (4, "Equipment register: equipment tree, events, serial counters", [
        """CREATE TABLE IF NOT EXISTS serial_counters (
            scope       VARCHAR(40) PRIMARY KEY,
            last_value  INT NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        # The CHECK makes the tree shape a database rule: equipment has a unit and no
        # parent; component units and components have a parent and no unit.
        """CREATE TABLE IF NOT EXISTS equipment (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            code        VARCHAR(12) NOT NULL,
            level       ENUM('equipment','component_unit','component') NOT NULL,
            parent_id   INT NULL,
            unit_id     INT NULL,
            class_id    INT NOT NULL,
            name        VARCHAR(100) NOT NULL,
            make        VARCHAR(100) NULL,
            model       VARCHAR(100) NULL,
            serial_no   VARCHAR(100) NULL,
            year        SMALLINT NULL,
            criticality ENUM('A','B','C') NULL,
            status      ENUM('in_service','standby','out_of_use','scrapped') NOT NULL DEFAULT 'in_service',
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            CONSTRAINT uq_equipment_code UNIQUE (code),
            CONSTRAINT fk_equipment_parent FOREIGN KEY (parent_id) REFERENCES equipment (id),
            CONSTRAINT fk_equipment_unit FOREIGN KEY (unit_id) REFERENCES units (id),
            CONSTRAINT fk_equipment_class FOREIGN KEY (class_id) REFERENCES equipment_classes (id),
            CONSTRAINT chk_equipment_level_place CHECK (
                (level = 'equipment') = (unit_id IS NOT NULL)
                AND (level = 'equipment') = (parent_id IS NULL))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS equipment_events (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            equipment_id  INT NOT NULL,
            event         ENUM('created','moved_unit','moved_parent','status','criticality','class') NOT NULL,
            old_value     VARCHAR(200) NULL,
            new_value     VARCHAR(200) NULL,
            created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by    VARCHAR(100) NOT NULL,
            KEY ix_equipment_events_equipment (equipment_id, created_at),
            CONSTRAINT fk_equipment_events_equipment FOREIGN KEY (equipment_id) REFERENCES equipment (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    ]),
]

LATEST_VERSION = _MIGRATIONS[-1][0]


class DBUnavailable(Exception):
    """The database cannot be reached or its schema could not be brought up to date."""


# ---------------------------------------------------------------------------
# Connections
# ---------------------------------------------------------------------------

def _connect_kwargs(config, connect_timeout):
    return {
        "host": config["host"],
        "port": config.get("port", 3306),
        "user": config["user"],
        "password": config["password"],
        "database": config["database"],
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": True,
        # All datetimes in the DB are IST — the session setting is the one switch
        "init_command": "SET time_zone = '+05:30'",
        "connect_timeout": connect_timeout,
    }


def get_local_db(config, connect_timeout=5):
    """Open a dedicated connection (not from the pool). Caller closes it."""
    return pymysql.connect(**_connect_kwargs(config, connect_timeout))


_pool = None


def init_pool(config, maxconn=10):
    """Create the connection pool. Opens no connections until first use."""
    global _pool
    _pool = PooledDB(
        creator=pymysql,
        mincached=0,
        maxconnections=maxconn,
        blocking=True,
        # Ping on every checkout — reconnects a connection that died overnight
        ping=1,
        **_connect_kwargs(config, connect_timeout=5),
    )
    logger.info("Connection pool created (max=%d)", maxconn)


def get_pooled_db():
    """Borrow a connection from the pool. Return it with return_pooled_db()."""
    return _pool.connection()


def return_pooled_db(conn):
    """Return a pooled connection — close() hands it back to the pool."""
    if conn is not None:
        conn.close()


# ---------------------------------------------------------------------------
# Migration engine
# ---------------------------------------------------------------------------

def _get_applied_versions(cur):
    cur.execute("SHOW TABLES LIKE 'db_version'")
    if cur.fetchone() is None:
        return set()
    cur.execute("SELECT version FROM db_version")
    return {row["version"] for row in cur.fetchall()}


def init_db(config):
    """Apply any pending migrations. Raises pymysql errors on failure.

    Gunicorn workers boot concurrently; GET_LOCK makes the others wait while
    one migrates, after which they find nothing pending.
    """
    conn = get_local_db(config)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT GET_LOCK(%s, 60) AS got", (LOCK_MIGRATIONS,))
            if cur.fetchone()["got"] != 1:
                raise DBUnavailable("Timed out waiting for the migration lock")
            try:
                applied = _get_applied_versions(cur)
                for version, description, statements in _MIGRATIONS:
                    if version in applied:
                        continue
                    logger.info("Applying migration v%d: %s", version, description)
                    for sql in statements:
                        cur.execute(sql)
                    cur.execute(
                        "INSERT INTO db_version (version, description) VALUES (%s, %s)",
                        (version, description),
                    )
                    logger.info("Migration v%d applied", version)
            finally:
                cur.execute("SELECT RELEASE_LOCK(%s)", (LOCK_MIGRATIONS,))
    finally:
        conn.close()


_schema_lock = threading.Lock()
_schema_ready = False
_last_attempt = 0.0
_last_error = None


def ensure_schema(config):
    """Make sure migrations have run; retry at most every _RETRY_INTERVAL_S.

    Returns None when the schema is up to date, else the last error message.
    Never raises — callers decide what an unavailable database means for them.
    """
    global _schema_ready, _last_attempt, _last_error
    if _schema_ready:
        return None
    with _schema_lock:
        if _schema_ready:
            return None
        if time.monotonic() - _last_attempt < _RETRY_INTERVAL_S and _last_attempt:
            return _last_error
        _last_attempt = time.monotonic()
        try:
            init_db(config)
        except (pymysql.MySQLError, DBUnavailable) as exc:
            _last_error = describe_error(exc)
            logger.error("Database not ready: %s", _last_error)
            return _last_error
        _schema_ready = True
        _last_error = None
        return None


def describe_error(exc):
    """Short human-readable message for a DB error (pymysql args are (code, msg))."""
    if isinstance(exc, pymysql.MySQLError) and len(exc.args) >= 2:
        return f"{exc.args[1]} (error {exc.args[0]})"
    return str(exc)


# ---------------------------------------------------------------------------
# Status probe — for Settings › Database
# ---------------------------------------------------------------------------

def db_status(config):
    """Report reachability, server version and schema version of the database.

    Uses a dedicated short-timeout connection so a dead DB cannot tie up the pool.
    """
    result = {
        "host": config["host"],
        "port": config.get("port", 3306),
        "database": config["database"],
        "reachable": False,
        "server_version": None,
        "schema_version": None,
        "schema_description": None,
        "schema_applied_at": None,
        "schema_latest": LATEST_VERSION,
        "error": None,
    }

    schema_error = ensure_schema(config)

    try:
        conn = get_local_db(config, connect_timeout=3)
    except pymysql.MySQLError as exc:
        result["error"] = describe_error(exc)
        return result

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION() AS v")
            result["server_version"] = cur.fetchone()["v"]
            result["reachable"] = True
            if _get_applied_versions(cur):
                cur.execute(
                    "SELECT version, description, applied_at "
                    "FROM db_version ORDER BY version DESC LIMIT 1"
                )
                row = cur.fetchone()
                result["schema_version"] = row["version"]
                result["schema_description"] = row["description"]
                result["schema_applied_at"] = row["applied_at"]
    except pymysql.MySQLError as exc:
        result["error"] = describe_error(exc)
    finally:
        conn.close()

    if result["error"] is None and schema_error:
        result["error"] = schema_error
    return result
