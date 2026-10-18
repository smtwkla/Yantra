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
    # Equipment types per class (ISO 14224 class/type) and notes (S004).  MariaDB DDL is
    # not transactional and the version is recorded only after the last statement, so
    # every statement here is safe to run twice: a half-applied v5 is simply re-run.
    # The composite FK makes "the type belongs to the equipment's class" a database rule;
    # uq_equipment_types_id_class is the index it references.  A NULL type_id skips it.
    (5, "Equipment types per class, equipment notes", [
        """CREATE TABLE IF NOT EXISTS equipment_types (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            class_id    INT NOT NULL,
            name        VARCHAR(100) NOT NULL,
            active      TINYINT(1) NOT NULL DEFAULT 1,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            CONSTRAINT uq_equipment_types_class_name UNIQUE (class_id, name),
            CONSTRAINT uq_equipment_types_id_class UNIQUE (id, class_id),
            CONSTRAINT fk_equipment_types_class FOREIGN KEY (class_id) REFERENCES equipment_classes (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS type_id INT NULL AFTER class_id",
        "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS notes TEXT NULL",
        """ALTER TABLE equipment ADD CONSTRAINT fk_equipment_type FOREIGN KEY IF NOT EXISTS
            (type_id, class_id) REFERENCES equipment_types (id, class_id)""",
        # The six old values keep their order and 'type' is appended: metadata only
        """ALTER TABLE equipment_events MODIFY event
            ENUM('created','moved_unit','moved_parent','status','criticality','class','type') NOT NULL""",
    ]),
    # Documents and photos on equipment (S006).  The files live under DATA_DIR; a row is
    # never deleted — removed_at hides it (ISO 55001 controlled information).  Only the
    # title is ever edited (updated_*).  Each statement is safe to run twice, as in v5.
    (6, "Equipment documents and photos, upload size limit", [
        """CREATE TABLE IF NOT EXISTS equipment_documents (
            id             INT AUTO_INCREMENT PRIMARY KEY,
            equipment_id   INT NOT NULL,
            kind           ENUM('document','photo') NOT NULL,
            title          VARCHAR(200) NOT NULL,
            original_name  VARCHAR(255) NOT NULL,
            stored_name    VARCHAR(80) NOT NULL,
            content_type   VARCHAR(50) NOT NULL,
            size_bytes     INT NOT NULL,
            has_thumb      TINYINT(1) NOT NULL DEFAULT 0,
            created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by     VARCHAR(100) NOT NULL,
            updated_at     DATETIME NULL,
            updated_by     VARCHAR(100) NULL,
            removed_at     DATETIME NULL,
            removed_by     VARCHAR(100) NULL,
            CONSTRAINT uq_equipment_documents_stored UNIQUE (stored_name),
            KEY ix_equipment_documents_node (equipment_id, removed_at),
            CONSTRAINT fk_equipment_documents_equipment FOREIGN KEY (equipment_id) REFERENCES equipment (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        "INSERT IGNORE INTO app_settings (setting_key, setting_value) VALUES ('upload_max_mb', '20')",
    ]),
    # Trades and the Team register of people (S010, amendment A1).  A person is named as the
    # user chooses: a person, or a contractor firm; never deleted, only deactivated, so
    # tickets can name them.  Every statement is safe to run twice, as in v5.
    # Edited in place for A1 (technicians -> people) before any commit or deploy; the dev
    # databases were reset (S010 3-impl-report, Amendment A1).
    (7, "Trades, people", [
        """CREATE TABLE IF NOT EXISTS trades (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            name        VARCHAR(50) NOT NULL,
            active      TINYINT(1) NOT NULL DEFAULT 1,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            CONSTRAINT uq_trades_name UNIQUE (name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS people (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            name        VARCHAR(100) NOT NULL,
            employment  ENUM('direct','contractor') NOT NULL,
            username    VARCHAR(100) NULL,
            active      TINYINT(1) NOT NULL DEFAULT 1,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            CONSTRAINT uq_people_username UNIQUE (username)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS person_trades (
            person_id   INT NOT NULL,
            trade_id    INT NOT NULL,
            granted_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            granted_by  VARCHAR(100) NOT NULL,
            PRIMARY KEY (person_id, trade_id),
            CONSTRAINT fk_person_trades_person FOREIGN KEY (person_id) REFERENCES people (id),
            CONSTRAINT fk_person_trades_trade FOREIGN KEY (trade_id) REFERENCES trades (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    ]),
    # Roles per site, held in Yantra (S011, amendment A1): a person's role at a site, with all
    # the site's units or the chosen ones (person_units).  role is text validated against
    # config_rbac.SITE_ROLES, one list to keep.  SQL only and additive, every statement safe
    # to re-run: user_units is copied, not dropped, so the previous release still runs on
    # this schema (rollback, S011 § 5.7); a later step drops it.  The copied rows have no
    # membership yet, so they grant nothing until IT admin adds a role.  People created for
    # legacy usernames are found by created_by = 'migration-v8'; a username already held by
    # an inactive person attaches to that person.
    (8, "Memberships (role per site), person units", [
        """CREATE TABLE IF NOT EXISTS memberships (
            person_id   INT NOT NULL,
            site_id     INT NOT NULL,
            role        VARCHAR(30) NOT NULL,
            all_units   TINYINT(1) NOT NULL DEFAULT 0,
            granted_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            granted_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            PRIMARY KEY (person_id, site_id),
            CONSTRAINT fk_memberships_person FOREIGN KEY (person_id) REFERENCES people (id),
            CONSTRAINT fk_memberships_site FOREIGN KEY (site_id) REFERENCES sites (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS person_units (
            person_id   INT NOT NULL,
            unit_id     INT NOT NULL,
            granted_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            granted_by  VARCHAR(100) NOT NULL,
            PRIMARY KEY (person_id, unit_id),
            CONSTRAINT fk_person_units_person FOREIGN KEY (person_id) REFERENCES people (id),
            CONSTRAINT fk_person_units_unit FOREIGN KEY (unit_id) REFERENCES units (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """INSERT INTO people (name, employment, username, created_by)
            SELECT DISTINCT uu.username, 'direct', uu.username, 'migration-v8' FROM user_units uu
            WHERE NOT EXISTS (SELECT 1 FROM people p WHERE p.username = uu.username)""",
        """INSERT IGNORE INTO person_units (person_id, unit_id, granted_at, granted_by)
            SELECT p.id, uu.unit_id, uu.granted_at, uu.granted_by
            FROM user_units uu JOIN people p ON p.username = uu.username""",
    ]),
    # Manufacturers and equipment models (S012).  A model belongs to one class and at most one
    # type of it, fixed for life; equipment picks its model and its class and type come from
    # it.  The composite FKs make "the model's type is of the model's class" and "the
    # equipment's model is of the equipment's class" database rules (as v5); each index comes
    # before its FK, so the FK uses it.  A model document has model_id instead of
    # equipment_id, and the CHECK keeps exactly one owner per document (S009's design).
    # Every statement is safe to run twice, as in v5.
    # equipment.model_id is NOT NULL: production had no equipment when v9 was written (S012
    # § 4.2).  On a table that has equipment rows the ADD COLUMN fills them with 0 and the
    # FOREIGN KEY then fails (1452): v9 stays half-applied and fails on every retry until
    # those rows are gone.  Dev and test databases are reset (tooling/dev/dev-db-reset.bat).
    (9, "Manufacturers, equipment models, model documents", [
        """CREATE TABLE IF NOT EXISTS manufacturers (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            name        VARCHAR(100) NOT NULL,
            active      TINYINT(1) NOT NULL DEFAULT 1,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            CONSTRAINT uq_manufacturers_name UNIQUE (name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS equipment_models (
            id               INT AUTO_INCREMENT PRIMARY KEY,
            manufacturer_id  INT NOT NULL,
            designation      VARCHAR(80) NOT NULL,
            class_id         INT NOT NULL,
            type_id          INT NULL,
            active           TINYINT(1) NOT NULL DEFAULT 1,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            CONSTRAINT uq_equipment_models_maker_designation UNIQUE (manufacturer_id, designation),
            CONSTRAINT uq_equipment_models_id_class UNIQUE (id, class_id),
            CONSTRAINT fk_equipment_models_manufacturer FOREIGN KEY (manufacturer_id) REFERENCES manufacturers (id),
            CONSTRAINT fk_equipment_models_class FOREIGN KEY (class_id) REFERENCES equipment_classes (id),
            CONSTRAINT fk_equipment_models_type FOREIGN KEY (type_id, class_id)
                REFERENCES equipment_types (id, class_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        "ALTER TABLE equipment ADD COLUMN IF NOT EXISTS model_id INT NOT NULL AFTER type_id",
        "ALTER TABLE equipment ADD INDEX IF NOT EXISTS ix_equipment_model (model_id, class_id)",
        """ALTER TABLE equipment ADD CONSTRAINT fk_equipment_model FOREIGN KEY IF NOT EXISTS
            (model_id, class_id) REFERENCES equipment_models (id, class_id)""",
        "ALTER TABLE equipment DROP COLUMN IF EXISTS make",
        "ALTER TABLE equipment DROP COLUMN IF EXISTS model",
        "ALTER TABLE equipment_documents MODIFY equipment_id INT NULL",
        "ALTER TABLE equipment_documents ADD COLUMN IF NOT EXISTS model_id INT NULL AFTER equipment_id",
        "ALTER TABLE equipment_documents ADD INDEX IF NOT EXISTS ix_equipment_documents_model (model_id, removed_at)",
        """ALTER TABLE equipment_documents ADD CONSTRAINT fk_equipment_documents_model FOREIGN KEY IF NOT EXISTS
            (model_id) REFERENCES equipment_models (id)""",
        """ALTER TABLE equipment_documents ADD CONSTRAINT IF NOT EXISTS chk_equipment_documents_owner
            CHECK ((equipment_id IS NOT NULL) + (model_id IS NOT NULL) = 1)""",
        # The seven old values keep their order and 'model' is appended: metadata only
        """ALTER TABLE equipment_events MODIFY event
            ENUM('created','moved_unit','moved_parent','status','criticality','class','type','model') NOT NULL""",
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
