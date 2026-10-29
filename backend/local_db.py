"""Owned database — migration engine, connection pool and status probe.

Manages the application's MariaDB database with automatic migrations.
Each migration is a (version, description, [sql_statements]) tuple.
Append new migrations with incrementing version numbers — never edit old ones.  v1–v13 were
squashed into v20 (S025); a migration that cannot run on existing data gets a precondition
(_PRECONDITIONS), checked before anything is applied.

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

# DB-level named locks (GET_LOCK).  GET_LOCK names are server-wide, not per database, so each
# lock's name carries the database's (named_lock): two databases on one server (production's
# neighbours, the parallel test workers' databases) never wait on each other's lock.
# Migrations: one process migrates a database at a time.
LOCK_MIGRATIONS = "yantra_migrations"
# The background worker's singleton lock (S013 § 5.5): one worker drains the queue
LOCK_WORKER = "yantra_worker"


# GET_LOCK refuses a longer name with an error
MAX_LOCK_NAME_LENGTH = 64


def named_lock(base, database):
    """The GET_LOCK name of lock ``base`` for ``database`` (MariaDB allows 64 characters)."""
    name = f"{base}:{database}"
    if len(name) > MAX_LOCK_NAME_LENGTH:
        raise ValueError(f"Lock name {name!r} is {len(name)} characters; MariaDB allows {MAX_LOCK_NAME_LENGTH}")
    return name

# Seconds between migration attempts while the database is unavailable
_RETRY_INTERVAL_S = 30

# ---------------------------------------------------------------------------
# Migrations — append new versions after the last one
# ---------------------------------------------------------------------------
#
# v1–v13 (S001–S018) were squashed into v20 on 21-10-2026 (S025, the user's decision U1).
# Production had applied v1–v5 only (release v0.1.3); the dev, test and e2e databases were
# at v13.  v20 builds today's whole schema with CREATE TABLE IF NOT EXISTS plus idempotent
# data statements, so it is safe on each:
#   - an empty database: v20 builds everything;
#   - production (v1–v5): the eight v1–v5 tables already have today's shape except
#     equipment and equipment_events, which the user drops by hand first (they are empty;
#     S025 § 5.1) — _PRECONDITIONS refuses v20 until then; v20 creates the rest;
#   - a v13 database: every CREATE skips and every data statement is a no-op.
# It is numbered 20, not 1, because production has versions 1–5 recorded: a squashed v1
# would be skipped there (a departure from SMTW-WebApp-Base § Migration squashing).
# The old texts live on, frozen, only as the test fixture tests/fixtures/migrations_v13.py.
# New migrations continue at v21.  A migration that cannot run on the data production
# holds gets a _PRECONDITIONS entry, never an edit of an applied migration.
#
# Conventions carried over from the squashed migrations:
#   - audit columns: created_* set on insert, updated_* stay NULL until the first edit (set
#     together by the application, never by ON UPDATE, so a time is never recorded without
#     an actor); app_settings.updated_at is the one ON UPDATE;
#   - every column keeps the place the old migrations' ALTERs gave it (e.g. equipment.notes
#     last, model_id after type_id), so a v20 database and a v13 one are identical;
#   - MariaDB DDL is not transactional and the version is recorded only after the last
#     statement, so every statement is safe to run twice: a half-applied v20 simply re-runs.

_MIGRATIONS = [
    (20, "Full schema (squashed S001–S018)", [
        # --- Core ----------------------------------------------------------------------------
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

        # --- Basic masters (S001) ------------------------------------------------------------
        # is_default is 1 for the default site and NULL for all others (never 0), so the
        # UNIQUE index - which allows many NULLs - lets the database guarantee at most one default.
        """CREATE TABLE IF NOT EXISTS sites (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            code        VARCHAR(20) NOT NULL,
            name        VARCHAR(100) NOT NULL,
            address     VARCHAR(255) NULL,
            active      TINYINT(1) NOT NULL DEFAULT 1,
            is_default  TINYINT(1) NULL,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            CONSTRAINT uq_sites_code UNIQUE (code),
            CONSTRAINT uq_sites_default UNIQUE (is_default)
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
        # Legacy unit access (S001), replaced by person_units (S011 A1).  Kept for the rows
        # production still holds, which the data statements at the end copy into Team; to be
        # dropped by a later step (docs/steps/README.md, Queued).
        """CREATE TABLE IF NOT EXISTS user_units (
            username    VARCHAR(100) NOT NULL,
            unit_id     INT NOT NULL,
            granted_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            granted_by  VARCHAR(100) NOT NULL,
            PRIMARY KEY (username, unit_id),
            CONSTRAINT fk_user_units_unit FOREIGN KEY (unit_id) REFERENCES units (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        # A counter, not a record, so no audit columns; shared by the serials (TK-, …)
        """CREATE TABLE IF NOT EXISTS serial_counters (
            scope       VARCHAR(40) PRIMARY KEY,
            last_value  INT NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        # Equipment types per class, ISO 14224 class/type (S004).  uq_equipment_types_id_class
        # is the index the composite FKs below reference ("the type belongs to the class").
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

        # --- Manufacturers and equipment models (S012) ---------------------------------------
        # A model belongs to one class and at most one type of it, fixed for life; equipment
        # picks its model and its class and type come from it.  The composite FKs make "the
        # model's type is of the model's class" and "the equipment's model is of the
        # equipment's class" database rules.
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

        # --- Trades, Team and roles per site (S010 A1, S011 A1) ------------------------------
        # A person is named as the user chooses: a person, or a contractor firm; never deleted,
        # only deactivated, so tickets can name them.  memberships: a person's role at a site,
        # with all the site's units or the chosen ones (person_units); role is text validated
        # against config_rbac.SITE_ROLES, one list to keep.
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

        # --- Failure codes (S016), ISO 14224 § 9 and Annex B ---------------------------------
        # Failure modes (what is seen; one class, or General when class_id is NULL), failure
        # causes (in Table B.3's five groups; the ENUM's order is the groups' order, so ORDER BY
        # cause_group lists them design … misc) and maintenance actions (Table B.5).  Three
        # tables, so a ticket's cause column can only hold a cause.  Mode labels are unique per
        # picker (a class's modes plus the General ones): checked by the API, an index can't
        # cross the NULL class (S016 § 5.1).
        """CREATE TABLE IF NOT EXISTS failure_modes (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            code        VARCHAR(8) NOT NULL,
            label       VARCHAR(60) NOT NULL,
            description VARCHAR(255) NULL,
            class_id    INT NULL,
            active      TINYINT(1) NOT NULL DEFAULT 1,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            CONSTRAINT uq_failure_modes_code UNIQUE (code),
            KEY ix_failure_modes_class (class_id, active),
            CONSTRAINT fk_failure_modes_class FOREIGN KEY (class_id) REFERENCES equipment_classes (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS failure_causes (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            code        VARCHAR(8) NOT NULL,
            label       VARCHAR(60) NOT NULL,
            description VARCHAR(255) NULL,
            cause_group ENUM('design','fabrication','operation','management','misc') NOT NULL,
            active      TINYINT(1) NOT NULL DEFAULT 1,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            CONSTRAINT uq_failure_causes_code UNIQUE (code),
            CONSTRAINT uq_failure_causes_label UNIQUE (label)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS maintenance_actions (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            code        VARCHAR(8) NOT NULL,
            label       VARCHAR(60) NOT NULL,
            description VARCHAR(255) NULL,
            active      TINYINT(1) NOT NULL DEFAULT 1,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            CONSTRAINT uq_maintenance_actions_code UNIQUE (code),
            CONSTRAINT uq_maintenance_actions_label UNIQUE (label)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

        # --- The equipment register (S002, S004, S012) ---------------------------------------
        # The CHECK makes the tree shape a database rule: equipment has a unit and no parent;
        # component units and components have a parent and no unit.  model_id is NOT NULL: a
        # node's class and type come from its model.  equipment_events is a history log —
        # equipment's own columns stay the truth, nothing replays the events; ENUM values are
        # only ever appended.  These two are the tables production holds in their v5 shape:
        # see _PRECONDITIONS.
        """CREATE TABLE IF NOT EXISTS equipment (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            code        VARCHAR(12) NOT NULL,
            level       ENUM('equipment','component_unit','component') NOT NULL,
            parent_id   INT NULL,
            unit_id     INT NULL,
            class_id    INT NOT NULL,
            type_id     INT NULL,
            model_id    INT NOT NULL,
            name        VARCHAR(100) NOT NULL,
            serial_no   VARCHAR(100) NULL,
            year        SMALLINT NULL,
            criticality ENUM('A','B','C') NULL,
            status      ENUM('in_service','standby','out_of_use','scrapped') NOT NULL DEFAULT 'in_service',
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            notes       TEXT NULL,
            CONSTRAINT uq_equipment_code UNIQUE (code),
            KEY ix_equipment_model (model_id, class_id),
            CONSTRAINT fk_equipment_parent FOREIGN KEY (parent_id) REFERENCES equipment (id),
            CONSTRAINT fk_equipment_unit FOREIGN KEY (unit_id) REFERENCES units (id),
            CONSTRAINT fk_equipment_class FOREIGN KEY (class_id) REFERENCES equipment_classes (id),
            CONSTRAINT fk_equipment_type FOREIGN KEY (type_id, class_id) REFERENCES equipment_types (id, class_id),
            CONSTRAINT fk_equipment_model FOREIGN KEY (model_id, class_id) REFERENCES equipment_models (id, class_id),
            CONSTRAINT chk_equipment_level_place CHECK (
                (level = 'equipment') = (unit_id IS NOT NULL)
                AND (level = 'equipment') = (parent_id IS NULL))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS equipment_events (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            equipment_id  INT NOT NULL,
            event         ENUM('created','moved_unit','moved_parent','status','criticality','class','type','model')
                          NOT NULL,
            old_value     VARCHAR(200) NULL,
            new_value     VARCHAR(200) NULL,
            created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by    VARCHAR(100) NOT NULL,
            KEY ix_equipment_events_equipment (equipment_id, created_at),
            CONSTRAINT fk_equipment_events_equipment FOREIGN KEY (equipment_id) REFERENCES equipment (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

        # --- Tickets (S017, S018) ------------------------------------------------------------
        # One record per problem found on equipment, a breakdown (critical) or a defect
        # (degraded, initial) — EN 13460's work request, ISO 14224's failure record.
        # equipment_id is always the machine; component_id the component-unit or component it
        # was raised on, when lower.  unit_id is the machine's unit at raise, kept when it
        # moves.  The intensity ENUM's order puts critical first in ORDER BY.  The close's
        # cause and action (NULL action on a ticket closed as not a fault), the not-a-fault
        # flag and the repeat link (a new ticket on the same machine after a restoration that
        # did not hold) are S018's.  ticket_events is the timeline the figures (response,
        # repair, downtime) are computed from; they are never stored.
        """CREATE TABLE IF NOT EXISTS tickets (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            serial          VARCHAR(16) NOT NULL,
            equipment_id    INT NOT NULL,
            component_id    INT NULL,
            unit_id         INT NOT NULL,
            intensity       ENUM('critical','degraded','initial') NOT NULL,
            state           ENUM('raised','acknowledged','in_progress','back_in_service','closed')
                            NOT NULL DEFAULT 'raised',
            failure_mode_id INT NULL,
            cause_id        INT NULL,
            action_id       INT NULL,
            not_a_fault     TINYINT(1) NOT NULL DEFAULT 0,
            repeat_of_id    INT NULL,
            description     VARCHAR(1000) NULL,
            reported_by_id  INT NULL,
            occurred_at     DATETIME NOT NULL,
            source          ENUM('manual') NOT NULL DEFAULT 'manual',
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            CONSTRAINT uq_tickets_serial UNIQUE (serial),
            KEY ix_tickets_unit_state (unit_id, state),
            KEY ix_tickets_equipment_state (equipment_id, state),
            KEY ix_tickets_component_state (component_id, state),
            KEY ix_tickets_repeat_of (repeat_of_id),
            CONSTRAINT fk_tickets_equipment FOREIGN KEY (equipment_id) REFERENCES equipment (id),
            CONSTRAINT fk_tickets_component FOREIGN KEY (component_id) REFERENCES equipment (id),
            CONSTRAINT fk_tickets_unit FOREIGN KEY (unit_id) REFERENCES units (id),
            CONSTRAINT fk_tickets_failure_mode FOREIGN KEY (failure_mode_id) REFERENCES failure_modes (id),
            CONSTRAINT fk_tickets_reported_by FOREIGN KEY (reported_by_id) REFERENCES people (id),
            CONSTRAINT fk_tickets_cause FOREIGN KEY (cause_id) REFERENCES failure_causes (id),
            CONSTRAINT fk_tickets_action FOREIGN KEY (action_id) REFERENCES maintenance_actions (id),
            CONSTRAINT fk_tickets_repeat_of FOREIGN KEY (repeat_of_id) REFERENCES tickets (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS ticket_events (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            ticket_id   INT NOT NULL,
            event       VARCHAR(30) NOT NULL,
            from_state  VARCHAR(20) NULL,
            to_state    VARCHAR(20) NULL,
            occurred_at DATETIME NOT NULL,
            intensity   ENUM('critical','degraded','initial') NULL,
            person_id   INT NULL,
            remark      VARCHAR(1000) NULL,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            KEY ix_ticket_events_ticket (ticket_id, occurred_at, id),
            CONSTRAINT fk_ticket_events_ticket FOREIGN KEY (ticket_id) REFERENCES tickets (id),
            CONSTRAINT fk_ticket_events_person FOREIGN KEY (person_id) REFERENCES people (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        # The assignees, and the labour rows (person, trade worked, date, minutes: ISO 14224
        # man-hours per discipline)
        """CREATE TABLE IF NOT EXISTS ticket_assignees (
            ticket_id   INT NOT NULL,
            person_id   INT NOT NULL,
            assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            assigned_by VARCHAR(100) NOT NULL,
            PRIMARY KEY (ticket_id, person_id),
            KEY ix_ticket_assignees_person (person_id),
            CONSTRAINT fk_ticket_assignees_ticket FOREIGN KEY (ticket_id) REFERENCES tickets (id),
            CONSTRAINT fk_ticket_assignees_person FOREIGN KEY (person_id) REFERENCES people (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS ticket_labour (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            ticket_id   INT NOT NULL,
            person_id   INT NOT NULL,
            trade_id    INT NULL,
            work_date   DATE NOT NULL,
            minutes     SMALLINT NOT NULL,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            KEY ix_ticket_labour_ticket (ticket_id),
            KEY ix_ticket_labour_person (person_id, work_date),
            CONSTRAINT fk_ticket_labour_ticket FOREIGN KEY (ticket_id) REFERENCES tickets (id),
            CONSTRAINT fk_ticket_labour_person FOREIGN KEY (person_id) REFERENCES people (id),
            CONSTRAINT fk_ticket_labour_trade FOREIGN KEY (trade_id) REFERENCES trades (id),
            CONSTRAINT chk_ticket_labour_minutes CHECK (minutes BETWEEN 1 AND 1440)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

        # --- Documents and photos (S006, S012, S017) -----------------------------------------
        # The files live under DATA_DIR; a row is never deleted — removed_at hides it (ISO
        # 55001 controlled information).  Only the title is ever edited (updated_*).  Three
        # owners — a node, a model, a ticket — and the CHECK keeps exactly one per document.
        """CREATE TABLE IF NOT EXISTS equipment_documents (
            id             INT AUTO_INCREMENT PRIMARY KEY,
            equipment_id   INT NULL,
            model_id       INT NULL,
            ticket_id      INT NULL,
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
            KEY ix_equipment_documents_model (model_id, removed_at),
            KEY ix_equipment_documents_ticket (ticket_id, removed_at),
            CONSTRAINT fk_equipment_documents_equipment FOREIGN KEY (equipment_id) REFERENCES equipment (id),
            CONSTRAINT fk_equipment_documents_model FOREIGN KEY (model_id) REFERENCES equipment_models (id),
            CONSTRAINT fk_equipment_documents_ticket FOREIGN KEY (ticket_id) REFERENCES tickets (id),
            CONSTRAINT chk_equipment_documents_owner
                CHECK ((equipment_id IS NOT NULL) + (model_id IS NOT NULL) + (ticket_id IS NOT NULL) = 1)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

        # --- Access log and task queue (S013) ------------------------------------------------
        # access_log is append-only by design (ISO 27001 A.8.15): no foreign keys, so it keeps
        # its rows when people or logins change; only the scheduled purge deletes, by age.
        # ux_access_log_sighting keeps one row per sighting key per IST day across every
        # Gunicorn worker (S013 A1).
        """CREATE TABLE IF NOT EXISTS access_log (
            id          BIGINT AUTO_INCREMENT PRIMARY KEY,
            ts          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            username    VARCHAR(100) NULL,
            role        VARCHAR(100) NULL,
            session_id  VARCHAR(100) NULL,
            client_ip   VARCHAR(45) NOT NULL,
            is_internal TINYINT(1) NOT NULL,
            outcome     ENUM('ok','auth_failed','denied_network','denied_perm') NOT NULL,
            method      VARCHAR(10) NOT NULL,
            path        VARCHAR(255) NOT NULL,
            user_agent  VARCHAR(255) NULL,
            detail      VARCHAR(255) NULL,
            sighting_day  DATE NOT NULL,
            sighting_hash CHAR(40) NOT NULL,
            INDEX ix_access_log_ts (ts),
            INDEX ix_access_log_user_ts (username, ts),
            UNIQUE KEY ux_access_log_sighting (sighting_hash, sighting_day)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS task_queue (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            task_type     VARCHAR(50) NOT NULL,
            payload       JSON NULL,
            status        ENUM('pending','running','done','failed') NOT NULL DEFAULT 'pending',
            attempts      INT NOT NULL DEFAULT 0,
            max_attempts  INT NOT NULL DEFAULT 3,
            scheduled_for DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            locked_until  DATETIME NULL,
            last_error    TEXT NULL,
            created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at  DATETIME NULL,
            INDEX ix_task_queue_due (status, scheduled_for),
            INDEX ix_task_queue_type_created (task_type, created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

        # --- Data: every statement keeps what is there (INSERT IGNORE, NOT EXISTS) -----------
        # Setting defaults.  The internal ranges are the RFC 1918 private ranges
        # (network_core.DEFAULT_INTERNAL_NETWORKS, repeated here: a migration is frozen text).
        "INSERT IGNORE INTO app_settings (setting_key, setting_value) VALUES ('upload_max_mb', '20')",
        """INSERT IGNORE INTO app_settings (setting_key, setting_value)
            VALUES ('internal_networks', '10.0.0.0/8,172.16.0.0/12,192.168.0.0/16')""",
        # Legacy unit access into Team (S011 A1 rules 3, 7; was v8): one person per legacy
        # username, told apart by created_by 'migration-v8' (kept verbatim); a username already
        # held by an inactive person attaches to that person.  The copied rows have no
        # membership, so they grant nothing until IT admin adds a role.  user_units is copied,
        # not emptied.
        """INSERT INTO people (name, employment, username, created_by)
            SELECT DISTINCT uu.username, 'direct', uu.username, 'migration-v8' FROM user_units uu
            WHERE NOT EXISTS (SELECT 1 FROM people p WHERE p.username = uu.username)""",
        """INSERT IGNORE INTO person_units (person_id, unit_id, granted_at, granted_by)
            SELECT p.id, uu.unit_id, uu.granted_at, uu.granted_by
            FROM user_units uu JOIN people p ON p.username = uu.username""",
        # The failure-code seed (S016; was v11): ISO's rows, trimmed; created_by 'migration-v11'
        # (kept verbatim) tells them apart.  INSERT IGNORE is keyed on the unique code, so a
        # re-run keeps an engineer's edit of a seed row.
        # General failure modes: ISO's code, a plain label for the operator, the ISO name as help
        """INSERT IGNORE INTO failure_modes (code, label, description, class_id, created_by) VALUES
            ('BRD', 'Stopped, won''t run', 'Breakdown', NULL, 'migration-v11'),
            ('FTS', 'Won''t start', 'Fail to start on demand', NULL, 'migration-v11'),
            ('STP', 'Won''t stop', 'Fail to stop on demand', NULL, 'migration-v11'),
            ('UST', 'Stops by itself', 'Spurious stop', NULL, 'migration-v11'),
            ('ELU', 'Leaking (oil, water, air)',
             'External leakage (ISO ELU utility medium / ELP process medium; one entry here)', NULL, 'migration-v11'),
            ('NOI', 'Abnormal noise', 'Noise', NULL, 'migration-v11'),
            ('VIB', 'Vibration', 'Vibration', NULL, 'migration-v11'),
            ('OHE', 'Overheating', 'Overheating', NULL, 'migration-v11'),
            ('LOO', 'Low output or slow', 'Low output', NULL, 'migration-v11'),
            ('ERO', 'Erratic, behaves oddly', 'Erratic output', NULL, 'migration-v11'),
            ('PDE', 'Reading out of range', 'Parameter deviation', NULL, 'migration-v11'),
            ('STD', 'Broken, cracked or worn part', 'Structural deficiency', NULL, 'migration-v11'),
            ('SER', 'Loose, dirty or minor problem', 'Minor in-service problems', NULL, 'migration-v11'),
            ('OTH', 'Other', 'Other', NULL, 'migration-v11')""",
        # Table B.3, trimmed: the "x.0 general" rows and 5.2 common cause are left out
        """INSERT IGNORE INTO failure_causes (code, cause_group, label, created_by) VALUES
            ('1.1', 'design', 'Improper capacity', 'migration-v11'),
            ('1.2', 'design', 'Improper material', 'migration-v11'),
            ('2.1', 'fabrication', 'Fabrication error', 'migration-v11'),
            ('2.2', 'fabrication', 'Installation error', 'migration-v11'),
            ('3.1', 'operation', 'Off-design service', 'migration-v11'),
            ('3.2', 'operation', 'Operating error', 'migration-v11'),
            ('3.3', 'operation', 'Maintenance error', 'migration-v11'),
            ('3.4', 'operation', 'Expected wear and tear', 'migration-v11'),
            ('4.1', 'management', 'Documentation error', 'migration-v11'),
            ('4.2', 'management', 'Management error', 'migration-v11'),
            ('5.1', 'misc', 'No cause found', 'migration-v11'),
            ('5.3', 'misc', 'Combined causes', 'migration-v11'),
            ('5.4', 'misc', 'Caused by another failure', 'migration-v11'),
            ('5.5', 'misc', 'Other', 'migration-v11'),
            ('5.6', 'misc', 'Unknown', 'migration-v11')""",
        # Table B.5, all twelve
        """INSERT IGNORE INTO maintenance_actions (code, label, description, created_by) VALUES
            ('1', 'Replace', 'Replace with a new or reconditioned item of the same type and make', 'migration-v11'),
            ('2', 'Repair', 'Manual repair work to restore the item', 'migration-v11'),
            ('3', 'Modify', 'Replace, renew or change to a different design or material', 'migration-v11'),
            ('4', 'Adjust', 'Bring a value back within limits (e.g. valve zero/span)', 'migration-v11'),
            ('5', 'Refit', 'Small repair or tidy-up short of a full repair: re-tighten, touch up, clean a seat',
             'migration-v11'),
            ('6', 'Check',
             'Looked for the cause; nothing repaired, or the fix was a restart or reset, or the work is deferred',
             'migration-v11'),
            ('7', 'Service', 'Periodic service: cleaning, lubrication, filter change', 'migration-v11'),
            ('8', 'Test', 'Test the function or performance', 'migration-v11'),
            ('9', 'Inspection', 'Careful look at the item, with or without opening it, by eye, ear and hand',
             'migration-v11'),
            ('10', 'Overhaul', 'Major overhaul', 'migration-v11'),
            ('11', 'Combination', 'Several of the above', 'migration-v11'),
            ('12', 'Other', 'Other action', 'migration-v11')""",
    ]),
    # S019 — deferred work (docs/steps/S019-deferred-work/1-brief.md § 4): the scheduled state,
    # the current plan on the ticket (planned date, waiting reason) and its history on the
    # events, and the "machine stopped for this work?" answer on a started event.
    # No _PRECONDITIONS entry (S019 BS1-02): it adds nullable columns, appends an ENUM value (an
    # in-place change, no rebuild) and a CHECK that every existing row meets (no ticket is
    # scheduled yet, so the plan columns are NULL on all of them); nothing existing is
    # converted or dropped, and the previous image ignores the new columns.  Every statement
    # is safe to run twice; the MODIFY restates NOT NULL DEFAULT 'raised'.
    (21, "Deferred work: scheduled state, plan, waiting reason (S019)", [
        """ALTER TABLE tickets
            MODIFY state ENUM('raised','acknowledged','in_progress','back_in_service','closed','scheduled')
                NOT NULL DEFAULT 'raised',
            ADD COLUMN IF NOT EXISTS planned_date DATE NULL AFTER state,
            ADD COLUMN IF NOT EXISTS waiting_reason ENUM('parts','vendor','expert','slot','approval','other') NULL
                AFTER planned_date""",
        # The database itself keeps the plan on scheduled tickets and on no others
        """ALTER TABLE tickets ADD CONSTRAINT IF NOT EXISTS chk_tickets_plan
            CHECK ((state = 'scheduled') = (planned_date IS NOT NULL AND waiting_reason IS NOT NULL))""",
        # Set on scheduled / rescheduled events, and machine_stopped on a started event written
        # from scheduled on a ticket that was not critical; NULL elsewhere
        """ALTER TABLE ticket_events
            ADD COLUMN IF NOT EXISTS planned_date DATE NULL AFTER remark,
            ADD COLUMN IF NOT EXISTS waiting_reason ENUM('parts','vendor','expert','slot','approval','other') NULL
                AFTER planned_date,
            ADD COLUMN IF NOT EXISTS machine_stopped TINYINT(1) NULL AFTER waiting_reason""",
    ]),
    # S020 — parts used (docs/steps/S020-parts-used/1-brief.md § 4): what was fitted, its number,
    # maker and quantity, on the ticket's machine or a component of it (ISO 14224 Table 8, the
    # spare parts of a maintenance record).  No stock, cost or item master: OneERP's.
    # No _PRECONDITIONS entry (S020 BS1-01): it creates one new table and touches no existing
    # row (Plan.MD's *Proposed* parts_used was never a table), so it is safe on any database.
    # number_kind is set exactly when part_number is (chk_ticket_parts_kind); qty_unit is
    # checked in tickets_core.PART_UNITS, not by an ENUM, so a unit is added without a
    # migration; ix_ticket_parts_number serves the later OneERP link and "where else was this
    # fitted", cheap now on an empty table.
    (22, "Parts used on tickets (S020)", [
        """CREATE TABLE IF NOT EXISTS ticket_parts (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            ticket_id   INT NOT NULL,
            node_id     INT NOT NULL,
            description VARCHAR(200) NOT NULL,
            part_number VARCHAR(60) NULL,
            number_kind ENUM('maker','generic') NULL,
            maker       VARCHAR(100) NULL,
            quantity    DECIMAL(6,2) NOT NULL,
            qty_unit    VARCHAR(8) NOT NULL DEFAULT 'nos',
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            KEY ix_ticket_parts_ticket (ticket_id),
            KEY ix_ticket_parts_node (node_id),
            KEY ix_ticket_parts_number (part_number),
            CONSTRAINT fk_ticket_parts_ticket FOREIGN KEY (ticket_id) REFERENCES tickets (id),
            CONSTRAINT fk_ticket_parts_node FOREIGN KEY (node_id) REFERENCES equipment (id),
            CONSTRAINT chk_ticket_parts_kind CHECK ((part_number IS NULL) = (number_kind IS NULL)),
            CONSTRAINT chk_ticket_parts_quantity CHECK (quantity > 0)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    ]),
    # S027 — work notes (docs/steps/S027-work-notes/1-brief.md § 4): a note is a ticket_events
    # row with event = 'note' and its text in remark (event is a free VARCHAR, so the new value
    # needs no change).  v23 adds only what correcting a note needs: who corrected it last and
    # when on the event row, and the earlier texts in ticket_note_edits (ISO 9001 § 7.5.3: a
    # change of a record is identified).  updated_* is set on notes only.
    # No _PRECONDITIONS entry: both columns are NULLable and the table is new, so no existing
    # row needs a value (and production holds no ticket_events rows yet, v0.1.3).  IF NOT EXISTS
    # on every statement, as v21, so a half-applied v23 simply re-runs.
    (23, "Work notes: note corrections keep the earlier text (S027)", [
        """ALTER TABLE ticket_events
            ADD COLUMN IF NOT EXISTS updated_at DATETIME NULL,
            ADD COLUMN IF NOT EXISTS updated_by VARCHAR(100) NULL""",
        """CREATE TABLE IF NOT EXISTS ticket_note_edits (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            event_id    INT NOT NULL,
            remark      VARCHAR(1000) NOT NULL,
            replaced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            replaced_by VARCHAR(100) NOT NULL,
            KEY ix_ticket_note_edits_event (event_id, id),
            CONSTRAINT fk_ticket_note_edits_event FOREIGN KEY (event_id) REFERENCES ticket_events (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    ]),
    # S021 — alerts by web push (docs/steps/S021-alerts-push/1-brief.md § 4): one row per device
    # (one browser on one phone or computer) that turned notifications on, against the person
    # whose alerts it gets.  endpoint_hash is the unique key (SHA-256 hex of endpoint: the
    # endpoints are too long for an index); a re-subscribe of the same device moves the row to
    # whoever signed in last.  p256dh and auth are the browser's keys for encrypting to it: they
    # only let someone send to that device, so they are stored as plain columns, never sent back.
    # The escalation times' defaults (A 10, B 30, C 60 minutes, decided 21-10-2026) are seeded as
    # v20 seeds upload_max_mb, so get_setting_int finds a row instead of warning at every raise.
    # No _PRECONDITIONS entry: a new table, and INSERT IGNORE adds rows without touching an
    # existing one, so it is safe on any database.  IF NOT EXISTS and INSERT IGNORE, as v21–v23,
    # so a half-applied v24 simply re-runs.
    (24, "Web push subscriptions (S021)", [
        """CREATE TABLE IF NOT EXISTS push_subscriptions (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            person_id     INT NOT NULL,
            endpoint      VARCHAR(1000) NOT NULL,
            endpoint_hash CHAR(64) NOT NULL,
            p256dh        VARCHAR(200) NOT NULL,
            auth          VARCHAR(100) NOT NULL,
            label         VARCHAR(100) NOT NULL,
            created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_sent_at  DATETIME NULL,
            last_error    VARCHAR(255) NULL,
            CONSTRAINT uq_push_subscriptions_endpoint UNIQUE (endpoint_hash),
            KEY ix_push_subscriptions_person (person_id),
            CONSTRAINT fk_push_subscriptions_person FOREIGN KEY (person_id) REFERENCES people (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """INSERT IGNORE INTO app_settings (setting_key, setting_value)
            VALUES ('escalate_minutes_a', '10'), ('escalate_minutes_b', '30'), ('escalate_minutes_c', '60')""",
    ]),
    # S030 — equipment lifecycle (docs/steps/S030-equipment-lifecycle/1-brief.md § 4.1): the
    # register field status is renamed lifecycle (ISO 55000 life cycle), so *status* is free for
    # the machine's maintenance status (down / working).  The column keeps its type, default and
    # place (RENAME COLUMN changes only the name; MariaDB ≥ 10.5.2).  The history event 'status'
    # becomes 'lifecycle' on every existing row; old_value, new_value, time and author stay.
    # The event statements run in this order so that no row holds 'status' when the last MODIFY
    # drops it: a MODIFY that drops a used ENUM value fails in strict mode and blanks the value
    # to '' without it.  Every statement is safe to run twice (a half-applied v25 re-runs: the
    # rename skips, 'status' is re-added, no row is updated, 'status' is dropped again).
    # _PRECONDITIONS: _v25_shape_check.  The previous release cannot run on v25 (it reads
    # e.status): a rollback restores the database dump.
    (25, "Equipment lifecycle: status renamed (S030)", [
        "ALTER TABLE equipment RENAME COLUMN IF EXISTS status TO lifecycle",
        # 1. Allow both names, so existing rows stay valid (safe to re-run; values kept by name)
        """ALTER TABLE equipment_events MODIFY event
            ENUM('created','moved_unit','moved_parent','status','criticality','class','type','model','lifecycle')
            NOT NULL""",
        # 2. Rename the event on every existing row
        "UPDATE equipment_events SET event = 'lifecycle' WHERE event = 'status'",
        # 3. Drop the old name; no row holds it now
        """ALTER TABLE equipment_events MODIFY event
            ENUM('created','moved_unit','moved_parent','lifecycle','criticality','class','type','model')
            NOT NULL""",
    ]),
    # S031 — the Me page (docs/steps/S031-me-page/1-brief.md § 4): two indexes, no data change.
    # *My activity* filters ticket_events on created_by and orders by created_at, id; *Raised by
    # me* filters tickets on created_by OR reported_by_id (which has the FK index).  IF NOT EXISTS
    # makes a re-run of a half-applied v26 a no-op.  No _PRECONDITIONS entry: an index cannot fail
    # on any value the columns hold.  The previous release ignores the indexes, so a rollback
    # needs no restore.
    (26, "Indexes for the Me page (S031)", [
        "CREATE INDEX IF NOT EXISTS ix_ticket_events_created_by ON ticket_events (created_by, created_at, id)",
        "CREATE INDEX IF NOT EXISTS ix_tickets_created_by ON tickets (created_by)",
    ]),
    # S032 — email to managers (docs/steps/S032-closed-ticket-email/1-brief.md § 4): each person's
    # address, copied from the login token's email claim at /api/auth/me; NULL = no address.  254
    # characters, the longest address SMTP carries (RFC 5321).  No index: read by person id.  No
    # _PRECONDITIONS entry: a new NULLable column needs no value from any existing row.  IF NOT
    # EXISTS makes a re-run of a half-applied v27 a no-op.  The previous release ignores the
    # column, so a rollback needs no restore.
    (27, "Email address per person, from Keycloak (S032)", [
        "ALTER TABLE people ADD COLUMN IF NOT EXISTS email VARCHAR(254) NULL",
    ]),
    # S033 — model optional on component units (docs/steps/S033-model-optional-component-units/
    # 1-brief.md § 4): a component unit may have no model; its class and type are then picked
    # directly.  fk_equipment_model (model_id, class_id) stays: InnoDB skips a foreign key whose
    # column is NULL, so a node without a model passes and one with a model still matches its
    # class.  The CHECK keeps "equipment and components have a model" a database rule.  No
    # _PRECONDITIONS entry: the column was NOT NULL, so every existing row has a model and meets
    # the CHECK.  MODIFY re-runs as a no-op and the CHECK has IF NOT EXISTS, so a half-applied v28
    # re-runs.  Rollback: the previous release reads nodes through inner joins to the model, so a
    # component unit saved without a model is lost from its lists until it gets a model again.
    (28, "Model optional on component units (S033)", [
        "ALTER TABLE equipment MODIFY model_id INT NULL",
        """ALTER TABLE equipment ADD CONSTRAINT IF NOT EXISTS chk_equipment_model_level
            CHECK (model_id IS NOT NULL OR level = 'component_unit')""",
    ]),
    # S037 — meter types, the catalogue a model or a machine can later carry (docs/steps/
    # S037-meters-master/1-brief.md § 4).  No _PRECONDITIONS entry: a new table touches no
    # existing row.  IF NOT EXISTS and INSERT IGNORE (name is unique) make a half-applied v29
    # re-run.  The CHECK keeps a Yes / No type's shape (no unit, no decimals, an expected
    # answer) a database rule; the code reports it first, with a field.  Rollback: the previous
    # release ignores the table.
    (29, "Meter types (S037)", [
        """CREATE TABLE IF NOT EXISTS meter_types (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            name        VARCHAR(60) NOT NULL,
            unit        VARCHAR(20) NULL,
            kind        ENUM('counter','gauge','amount','yes_no') NOT NULL,
            expected_answer ENUM('yes','no') NULL,
            decimals    TINYINT NOT NULL DEFAULT 0,
            active      TINYINT(1) NOT NULL DEFAULT 1,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            CONSTRAINT uq_meter_types_name UNIQUE (name),
            CONSTRAINT chk_meter_types_decimals CHECK (decimals BETWEEN 0 AND 3),
            CONSTRAINT chk_meter_types_yes_no CHECK (
                (kind = 'yes_no' AND unit IS NULL AND expected_answer IS NOT NULL AND decimals = 0)
                OR (kind <> 'yes_no' AND unit IS NOT NULL AND expected_answer IS NULL))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """INSERT IGNORE INTO meter_types (name, unit, kind, decimals, created_by) VALUES
            ('Run hours', 'h', 'counter', 1, 'migration-v29'),
            ('Strokes', 'strokes', 'counter', 0, 'migration-v29'),
            ('Production counter', 'pcs', 'counter', 0, 'migration-v29'),
            ('Energy', 'kWh', 'counter', 1, 'migration-v29'),
            ('Odometer', 'km', 'counter', 0, 'migration-v29'),
            ('Oil temperature', '°C', 'gauge', 1, 'migration-v29'),
            ('Fuel level', '%', 'gauge', 0, 'migration-v29'),
            ('Shift production', 'pcs', 'amount', 0, 'migration-v29')""",
    ]),
    # S038 — meters on models and equipment (docs/steps/S038-meters-on-models-equipment/
    # 1-brief.md § 4).  A model lists its meters with default gauge limits; a node's meters are
    # its model's (computed live, never copied) plus its own rows in node_meters.  node_meters
    # holds both a node's own meters (own = 1) and its overrides of a model meter's limits
    # (own = 0); own never changes after insert.  Limits stay NULL on a counter, an amount and a
    # Yes / No meter: a code rule, since the kind is on meter_types.  Rows are never deleted,
    # only set inactive, except an own = 0 override that equals the model again.  The ENUM gains
    # three values at its end, so no row changes.  No _PRECONDITIONS entry: two new tables and a
    # widened ENUM touch no existing value.  IF NOT EXISTS and a MODIFY to the same list make a
    # half-applied v30 re-run.  Rollback: the previous release ignores both tables; an event row
    # with a new value shows as its raw name.
    (30, "Meters on models and equipment (S038)", [
        """CREATE TABLE IF NOT EXISTS model_meters (
            id             INT AUTO_INCREMENT PRIMARY KEY,
            model_id       INT NOT NULL,
            meter_type_id  INT NOT NULL,
            min_value      DECIMAL(14,3) NULL,
            max_value      DECIMAL(14,3) NULL,
            active         TINYINT(1) NOT NULL DEFAULT 1,
            created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by     VARCHAR(100) NOT NULL,
            updated_at     DATETIME NULL,
            updated_by     VARCHAR(100) NULL,
            CONSTRAINT uq_model_meters UNIQUE (model_id, meter_type_id),
            CONSTRAINT fk_model_meters_model FOREIGN KEY (model_id) REFERENCES equipment_models (id),
            CONSTRAINT fk_model_meters_type FOREIGN KEY (meter_type_id) REFERENCES meter_types (id),
            CONSTRAINT chk_model_meters_limits
                CHECK (min_value IS NULL OR max_value IS NULL OR min_value <= max_value)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS node_meters (
            id             INT AUTO_INCREMENT PRIMARY KEY,
            equipment_id   INT NOT NULL,
            meter_type_id  INT NOT NULL,
            own            TINYINT(1) NOT NULL,
            min_value      DECIMAL(14,3) NULL,
            max_value      DECIMAL(14,3) NULL,
            active         TINYINT(1) NOT NULL DEFAULT 1,
            created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by     VARCHAR(100) NOT NULL,
            updated_at     DATETIME NULL,
            updated_by     VARCHAR(100) NULL,
            CONSTRAINT uq_node_meters UNIQUE (equipment_id, meter_type_id),
            CONSTRAINT fk_node_meters_node FOREIGN KEY (equipment_id) REFERENCES equipment (id),
            CONSTRAINT fk_node_meters_type FOREIGN KEY (meter_type_id) REFERENCES meter_types (id),
            CONSTRAINT chk_node_meters_limits
                CHECK (min_value IS NULL OR max_value IS NULL OR min_value <= max_value)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """ALTER TABLE equipment_events MODIFY event
            ENUM('created','moved_unit','moved_parent','lifecycle','criticality','class','type','model',
                 'meter_added','meter_removed','meter_limits')
            NOT NULL""",
    ]),
    # S043 — equipment properties (docs/steps/S043-equipment-properties/1-brief.md § 4): technical
    # data defined once (ISO 14224 Annex A equipment-specific data; IEC 61360: one definition with
    # a data type and a unit, reused across classes), linked to classes, valued on models.
    # One typed column per data type and exactly one filled (chk_model_property_one_value); which
    # one must follow the property's data_type, which properties_core checks (a CHECK cannot read
    # another table).  The option's composite FK makes "the option is this property's" a database
    # rule, as fk_equipment_models_type does for a model's type.  No row = no value.
    # No _PRECONDITIONS entry: new tables and seed rows only, no existing row changes.  IF NOT
    # EXISTS and INSERT IGNORE (keyed on the unique name, created_by 'migration-v31'), so a
    # half-applied v31 simply re-runs and a re-run keeps an engineer's edit of a seed row.
    # Rollback: the previous release ignores the four tables.
    (31, "Equipment properties: master, class links, model values (S043)", [
        """CREATE TABLE IF NOT EXISTS property_definitions (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            name         VARCHAR(80) NOT NULL,
            data_type    ENUM('number','choice','text','yes_no') NOT NULL,
            unit         VARCHAR(20) NULL,
            description  VARCHAR(300) NULL,
            active       TINYINT(1) NOT NULL DEFAULT 1,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            CONSTRAINT uq_property_definitions_name UNIQUE (name),
            CONSTRAINT chk_property_unit CHECK (data_type = 'number' OR unit IS NULL)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS property_options (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            property_id  INT NOT NULL,
            label        VARCHAR(60) NOT NULL,
            active       TINYINT(1) NOT NULL DEFAULT 1,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            CONSTRAINT uq_property_options_label UNIQUE (property_id, label),
            CONSTRAINT uq_property_options_id_property UNIQUE (id, property_id),
            CONSTRAINT fk_property_options_property FOREIGN KEY (property_id) REFERENCES property_definitions (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        # No active flag: removing a property from a class deletes the link; the values stay
        """CREATE TABLE IF NOT EXISTS class_properties (
            class_id     INT NOT NULL,
            property_id  INT NOT NULL,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            PRIMARY KEY (class_id, property_id),
            CONSTRAINT fk_class_properties_class FOREIGN KEY (class_id) REFERENCES equipment_classes (id),
            CONSTRAINT fk_class_properties_property FOREIGN KEY (property_id) REFERENCES property_definitions (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS model_property_values (
            model_id      INT NOT NULL,
            property_id   INT NOT NULL,
            value_number  DECIMAL(16,4) NULL,
            value_text    VARCHAR(100) NULL,
            value_bool    TINYINT(1) NULL,
            option_id     INT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            PRIMARY KEY (model_id, property_id),
            CONSTRAINT fk_model_property_values_model FOREIGN KEY (model_id) REFERENCES equipment_models (id),
            CONSTRAINT fk_model_property_values_property FOREIGN KEY (property_id)
                REFERENCES property_definitions (id),
            CONSTRAINT fk_model_property_values_option FOREIGN KEY (option_id, property_id)
                REFERENCES property_options (id, property_id),
            CONSTRAINT chk_model_property_one_value CHECK (
                (value_number IS NOT NULL) + (value_text IS NOT NULL) + (value_bool IS NOT NULL)
                + (option_id IS NOT NULL) = 1)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        # The seed (§ 4.6): ISO 14224 Annex A names where it has the class, plus common nameplate
        # data.  No pump, motor, compressor or valve type and no execution: how equipment is built
        # is its equipment type (S004), not a property.  Linked to no class: the plant's class
        # codes are not known here.
        """INSERT IGNORE INTO property_definitions (name, data_type, unit, description, created_by) VALUES
            ('Power – design', 'number', 'kW', 'The maker''s rating, from the nameplate or the data sheet.',
             'migration-v31'),
            ('Speed', 'number', 'rpm', 'The maker''s rating, from the nameplate or the data sheet.', 'migration-v31'),
            ('Voltage', 'number', 'V', 'The maker''s rating, from the nameplate or the data sheet.', 'migration-v31'),
            ('Rated current', 'number', 'A', 'The maker''s rating, from the nameplate or the data sheet.',
             'migration-v31'),
            ('Frequency', 'number', 'Hz', 'The maker''s rating, from the nameplate or the data sheet.',
             'migration-v31'),
            ('Suction pressure – design', 'number', 'bar',
             'The maker''s rating, from the nameplate or the data sheet.', 'migration-v31'),
            ('Discharge pressure – design', 'number', 'bar',
             'The maker''s rating, from the nameplate or the data sheet.', 'migration-v31'),
            ('Flow rate – design', 'number', 'L/min', 'The maker''s rating, from the nameplate or the data sheet.',
             'migration-v31'),
            ('Free air delivery', 'number', 'm³/min', 'The maker''s rating, from the nameplate or the data sheet.',
             'migration-v31'),
            ('Number of stages', 'number', NULL, 'From the data sheet.', 'migration-v31'),
            ('Shaft sealing', 'choice', NULL, NULL, 'migration-v31'),
            ('Shaft orientation', 'choice', NULL, NULL, 'migration-v31'),
            ('Coupling', 'choice', NULL, NULL, 'migration-v31'),
            ('Insulation class', 'choice', NULL, NULL, 'migration-v31'),
            ('Degree of protection', 'text', NULL, 'The IP code on the nameplate, for example IP55.',
             'migration-v31'),
            ('Frame size', 'text', NULL, NULL, 'migration-v31'),
            ('Mounting', 'text', NULL, 'The IM or B/V code, for example B3.', 'migration-v31'),
            ('Variable speed drive', 'yes_no', NULL, NULL, 'migration-v31'),
            ('Actuation', 'choice', NULL, NULL, 'migration-v31'),
            ('Nominal size', 'number', 'mm', 'From the data sheet.', 'migration-v31'),
            ('Generator rating', 'number', 'kVA', 'The maker''s rating, from the nameplate or the data sheet.',
             'migration-v31'),
            ('Fuel tank capacity', 'number', 'L', 'From the data sheet.', 'migration-v31')""",
        # The options find their property by name at run time and are keyed on
        # uq_property_options_label (BR1-06); one statement per option keeps the listed order
        *(f"INSERT IGNORE INTO property_options (property_id, label, created_by) SELECT id, '{label}', "
          f"'migration-v31' FROM property_definitions WHERE name = '{name}'"
          for name, labels in (
              ("Shaft sealing", ("Mechanical seal", "Packed gland", "Lip seal", "Seal-less")),
              ("Shaft orientation", ("Horizontal", "Vertical")),
              ("Coupling", ("Rigid", "Flexible", "Magnetic", "Direct")),
              ("Insulation class", ("A", "B", "E", "F", "H")),
              ("Actuation", ("Manual", "Solenoid", "Pneumatic", "Hydraulic", "Electric motor")),
          )
          for label in labels),
    ]),
    # S039 — meter readings (docs/steps/S039-meter-reading-entry/1-brief.md § 4): one row per
    # reading of one meter (node + meter type, S038) at one minute.  A Yes / No reading stores
    # value 1 / 0, so one column serves every kind.  limit_state is stored at saving, so a later
    # limit change never re-judges old readings.  Rows are never deleted: a removal sets
    # removed_at / removed_by (who and when kept, ISO 27001 A.8.15).  No unique key on the time:
    # a removed reading may share its minute with its replacement; two active readings at one
    # minute are refused in code.  No _PRECONDITIONS entry: a new table touches no existing row.
    # IF NOT EXISTS makes a half-applied v32 re-run.  Rollback: the previous release ignores the
    # table.
    (32, "Meter readings (S039)", [
        """CREATE TABLE IF NOT EXISTS meter_readings (
            id             INT AUTO_INCREMENT PRIMARY KEY,
            equipment_id   INT NOT NULL,
            meter_type_id  INT NOT NULL,
            value          DECIMAL(14,3) NOT NULL,
            taken_at       DATETIME NOT NULL,
            is_reset       TINYINT(1) NOT NULL DEFAULT 0,
            limit_state    ENUM('low','high','not_ok') NULL,
            source         ENUM('manual','pm','move','iiot') NOT NULL DEFAULT 'manual',
            note           VARCHAR(200) NULL,
            created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by     VARCHAR(100) NOT NULL,
            removed_at     DATETIME NULL,
            removed_by     VARCHAR(100) NULL,
            CONSTRAINT fk_meter_readings_node FOREIGN KEY (equipment_id) REFERENCES equipment (id),
            CONSTRAINT fk_meter_readings_type FOREIGN KEY (meter_type_id) REFERENCES meter_types (id),
            INDEX ix_meter_readings_meter_time (equipment_id, meter_type_id, taken_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    ]),
    # S044 — property overrides on equipment items (docs/steps/S044-property-overrides/1-brief.md
    # § 4): an item's own value of a property of its class, where its nameplate differs from its
    # model's; it wins over the model's on that item only.  The columns of model_property_values
    # (v31), keyed by the item: exactly one value column filled (chk_equipment_property_one_value),
    # the option's composite FK makes "the option is this property's" a database rule.  No row =
    # no own value.  A model or class change leaves the rows alone (a value of a property the new
    # class lacks is hidden, not deleted).  equipment_events.event gains 'property' at its end, as
    # v30 added the meter events.  No _PRECONDITIONS entry: a new table and a widened ENUM touch no
    # existing row.  IF NOT EXISTS and a MODIFY to the same list make a half-applied v33 re-run.
    # Rollback: the previous release ignores the table, so items show their models' values again;
    # a 'property' event shows as its raw name in the history.  Going back after item values exist
    # loses them from view only; restoring db-server's dump drops them.
    (33, "Property values on equipment items (S044)", [
        """CREATE TABLE IF NOT EXISTS equipment_property_values (
            equipment_id  INT NOT NULL,
            property_id   INT NOT NULL,
            value_number  DECIMAL(16,4) NULL,
            value_text    VARCHAR(100) NULL,
            value_bool    TINYINT(1) NULL,
            option_id     INT NULL,
            updated_at    DATETIME NULL,
            updated_by    VARCHAR(100) NULL,
            PRIMARY KEY (equipment_id, property_id),
            CONSTRAINT fk_equipment_property_values_node FOREIGN KEY (equipment_id) REFERENCES equipment (id),
            CONSTRAINT fk_equipment_property_values_property FOREIGN KEY (property_id)
                REFERENCES property_definitions (id),
            CONSTRAINT fk_equipment_property_values_option FOREIGN KEY (option_id, property_id)
                REFERENCES property_options (id, property_id),
            CONSTRAINT chk_equipment_property_one_value CHECK (
                (value_number IS NOT NULL) + (value_text IS NOT NULL) + (value_bool IS NOT NULL)
                + (option_id IS NOT NULL) = 1)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """ALTER TABLE equipment_events MODIFY event
            ENUM('created','moved_unit','moved_parent','lifecycle','criticality','class','type','model',
                 'meter_added','meter_removed','meter_limits','property')
            NOT NULL""",
    ]),
    # S061 — properties for every class, and a GPS location
    # (docs/steps/S061-global-properties-gps/1-brief.md § 4).  A data type 'geo' (a latitude and a
    # longitude, 6 decimals, about 10 cm), appended to the ENUM so no row changes; two flags:
    # all_classes (on every class without a link) and per_item_only (installation data, valued on
    # each machine, never on a model: ISO 14224's design vs installation data).  Both value tables
    # gain value_lat / value_lng: value_lat is a fifth slot in the one-value CHECK, the pair CHECK
    # keeps both or neither, the range CHECK keeps -90..90 / -180..180 (the columns alone hold up
    # to 99.999999 / 999.999999).  Every existing row has both new columns NULL and one old column
    # set, so it meets the CHECKs.  ADD COLUMN IF NOT EXISTS and DROP CONSTRAINT IF EXISTS before
    # each ADD CONSTRAINT make a half-applied v34 re-run; INSERT IGNORE keys the seed on its name.
    # _PRECONDITIONS: _v34_gps_name_check (a hand-made "GPS location" would keep its own type and
    # no flags, silently).  Rollback: the previous release reads p.* and ignores the flags; "GPS
    # location" shows in its Masters with the raw type geo and on no card.  Known risk: a geo
    # property linked to a class in the old release fails that class's pages until Remove.
    (34, "Properties for every class, per-machine values, Location (S061)", [
        """ALTER TABLE property_definitions
            MODIFY data_type ENUM('number','choice','text','yes_no','geo') NOT NULL,
            ADD COLUMN IF NOT EXISTS all_classes TINYINT(1) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS per_item_only TINYINT(1) NOT NULL DEFAULT 0""",
        *(f"""ALTER TABLE {table}_property_values
            ADD COLUMN IF NOT EXISTS value_lat DECIMAL(8,6) NULL,
            ADD COLUMN IF NOT EXISTS value_lng DECIMAL(9,6) NULL,
            DROP CONSTRAINT IF EXISTS chk_{table}_property_one_value,
            ADD CONSTRAINT chk_{table}_property_one_value CHECK (
                (value_number IS NOT NULL) + (value_text IS NOT NULL) + (value_bool IS NOT NULL)
                + (option_id IS NOT NULL) + (value_lat IS NOT NULL) = 1),
            DROP CONSTRAINT IF EXISTS chk_{table}_property_geo_pair,
            ADD CONSTRAINT chk_{table}_property_geo_pair CHECK ((value_lat IS NULL) = (value_lng IS NULL)),
            DROP CONSTRAINT IF EXISTS chk_{table}_property_geo_range,
            ADD CONSTRAINT chk_{table}_property_geo_range CHECK (value_lat IS NULL OR (
                value_lat BETWEEN -90 AND 90 AND value_lng BETWEEN -180 AND 180))"""
          for table in ("model", "equipment")),
        """INSERT IGNORE INTO property_definitions (name, data_type, description, all_classes, per_item_only,
                                                    created_by)
            VALUES ('GPS location', 'geo',
                    'Where the machine stands. Tap Use my current location next to the machine, or paste from Google Maps.',
                    1, 1, 'migration-v34')""",
    ]),
    # S063 — equipment categories (docs/steps/S063-equipment-category/1-brief.md § 4.1).  A
    # category groups equipment classes (ISO 14224 Annex A); each class is in at most one, so
    # equipment_classes gains a nullable category_id.  Every existing class gets NULL; nothing is
    # seeded (KLA, Q1).  IF NOT EXISTS on the table, the column and the key make a half-applied
    # v35 re-run.  No precondition: a new table and a nullable column meet no production row.
    # Rollback: the previous release reads classes with SELECT * and ignores the column.
    (35, "Equipment categories (S063)", [
        """CREATE TABLE IF NOT EXISTS equipment_categories (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            name        VARCHAR(50) NOT NULL,
            active      TINYINT(1) NOT NULL DEFAULT 1,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            CONSTRAINT uq_equipment_categories_name UNIQUE (name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """ALTER TABLE equipment_classes
            ADD COLUMN IF NOT EXISTS category_id INT NULL AFTER name,
            ADD CONSTRAINT fk_equipment_classes_category
                FOREIGN KEY IF NOT EXISTS (category_id) REFERENCES equipment_categories (id)""",
    ]),
    # S067 — improvements (docs/steps/S067-improvement-record/1-brief.md § 4.1, R05.1): one problem
    # analysed from one or more tickets (TPM focused improvement).  The unit and the machine are the
    # first ticket's; the site is the unit's.  Serials IM-YYYY-MM-NNN through serial_counters rows
    # IM:YYYY-MM.  state holds only 'analysing' (D3); R05.4 appends its values at the end.
    # improvement_tickets.open_link is 1 while the improvement is open and NULL after (R05.4 sets
    # it): the UNIQUE key allows one open link per ticket and any number of NULLs, so a ticket is
    # in at most one open improvement (Q1.4 a, D4).  IF NOT EXISTS on both tables makes a
    # half-applied v36 re-run.  No precondition: two new tables meet no production row.
    # Rollback: the previous release reads neither table; the IM: counter rows stay unused.
    (36, "Improvements and their tickets (S067)", [
        """CREATE TABLE IF NOT EXISTS improvements (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            serial        VARCHAR(16) NOT NULL,
            unit_id       INT NOT NULL,
            equipment_id  INT NOT NULL,
            state         ENUM('analysing') NOT NULL DEFAULT 'analysing',
            title         VARCHAR(120) NOT NULL,
            problem       VARCHAR(2000) NOT NULL,
            lead_id       INT NOT NULL,
            created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by    VARCHAR(100) NOT NULL,
            updated_at    DATETIME NULL,
            updated_by    VARCHAR(100) NULL,
            CONSTRAINT uq_improvements_serial UNIQUE (serial),
            KEY ix_improvements_unit_state (unit_id, state),
            KEY ix_improvements_equipment (equipment_id),
            CONSTRAINT fk_improvements_unit FOREIGN KEY (unit_id) REFERENCES units (id),
            CONSTRAINT fk_improvements_equipment FOREIGN KEY (equipment_id) REFERENCES equipment (id),
            CONSTRAINT fk_improvements_lead FOREIGN KEY (lead_id) REFERENCES people (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS improvement_tickets (
            improvement_id  INT NOT NULL,
            ticket_id       INT NOT NULL,
            open_link       TINYINT(1) NULL DEFAULT 1,
            created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by      VARCHAR(100) NOT NULL,
            PRIMARY KEY (improvement_id, ticket_id),
            CONSTRAINT uq_improvement_tickets_open UNIQUE (ticket_id, open_link),
            CONSTRAINT chk_improvement_tickets_open_link CHECK (open_link IS NULL OR open_link = 1),
            CONSTRAINT fk_improvement_tickets_improvement FOREIGN KEY (improvement_id) REFERENCES improvements (id),
            CONSTRAINT fk_improvement_tickets_ticket FOREIGN KEY (ticket_id) REFERENCES tickets (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    ]),
]

LATEST_VERSION = _MIGRATIONS[-1][0]


# ---------------------------------------------------------------------------
# Preconditions — checked for every pending version before any is applied
# ---------------------------------------------------------------------------

def _old_tables_for_v20(cur):
    """The tables v20 cannot bring to today's shape, as they stand in this database -> names.

    Only equipment and equipment_events changed after v5 (v9 added equipment.model_id and
    appended 'model' to the event ENUM); CREATE TABLE IF NOT EXISTS would skip them in their
    v5 shape.  A table that is absent passes: v20 creates it.  information_schema is read with
    TABLE_SCHEMA = DATABASE(): the dev server hosts several Yantra databases."""
    old = []
    cur.execute("SELECT COUNT(*) AS n FROM information_schema.TABLES"
                " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'equipment'")
    if cur.fetchone()["n"]:
        cur.execute("SELECT COUNT(*) AS n FROM information_schema.COLUMNS"
                    " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'equipment' AND COLUMN_NAME = 'model_id'")
        if not cur.fetchone()["n"]:
            old.append("equipment")
    cur.execute("SELECT COLUMN_TYPE FROM information_schema.COLUMNS"
                " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'equipment_events' AND COLUMN_NAME = 'event'")
    events = cur.fetchone()
    if events is not None and "'model'" not in events["COLUMN_TYPE"]:
        old.append("equipment_events")
    return old


def _v20_shape_check(cur):
    """v20's precondition (S025 § 1.1) -> None, or the refusal Settings › Database shows."""
    old = _old_tables_for_v20(cur)
    if not old:
        return None
    if len(old) == 1:
        return f"Drop the old {old[0]} table first (it must be empty) — S025 § 5.1"
    return f"Drop the old {' and '.join(old)} tables first (they must be empty) — S025 § 5.1"


def _v25_shape_check(cur):
    """v25's precondition (S030 § 4.2) -> None, or the refusal Settings › Database shows.

    equipment must have exactly one of status (the normal case) and lifecycle (a half-applied
    v25).  An absent table passes: on an empty database this runs before v20 has created it,
    and v20 then creates status for v25 to rename.  Both columns would fail the RENAME half-way;
    neither would skip it and leave every equipment read failing.  information_schema is read
    with TABLE_SCHEMA = DATABASE(), as _old_tables_for_v20 does."""
    cur.execute("SELECT COUNT(*) AS n FROM information_schema.TABLES"
                " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'equipment'")
    if not cur.fetchone()["n"]:
        return None
    cur.execute("SELECT COLUMN_NAME FROM information_schema.COLUMNS"
                " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'equipment'"
                " AND COLUMN_NAME IN ('status', 'lifecycle')")
    columns = {row["COLUMN_NAME"] for row in cur.fetchall()}
    if len(columns) == 2:
        return ("equipment has both status and lifecycle columns; drop the one that is not in use first"
                " — S030 § 4.2")
    if not columns:
        return "equipment has neither a status nor a lifecycle column — S030 § 4.2"
    return None


V34_SEED_NAME = "GPS location"
V34_SEED_CREATOR = "migration-v34"


def _v34_gps_name_check(cur):
    """v34's precondition (S061 § 4, D8) -> None, or the refusal Settings › Database shows.

    A property named "GPS location" (any case: the column's collation compares) that v34 did not
    seed would be kept by INSERT IGNORE with its own type and no flags, and nothing would say so.
    The row v34 itself seeded (created_by 'migration-v34') passes, so a half-applied v34 re-runs.
    An absent table passes: on an empty database this runs before v20 has created it.
    information_schema is read with TABLE_SCHEMA = DATABASE(), as _old_tables_for_v20 does."""
    cur.execute("SELECT COUNT(*) AS n FROM information_schema.TABLES"
                " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'property_definitions'")
    if not cur.fetchone()["n"]:
        return None
    cur.execute("SELECT COUNT(*) AS n FROM property_definitions WHERE name = %s AND created_by <> %s",
                (V34_SEED_NAME, V34_SEED_CREATOR))
    if cur.fetchone()["n"]:
        return ("A property named GPS location already exists. Rename it in Masters › Properties; "
                "the update then adds the new one.")
    return None


# version -> a function of the cursor that returns None (go) or why the version cannot run yet
_PRECONDITIONS = {20: _v20_shape_check, 25: _v25_shape_check, 34: _v34_gps_name_check}


class DBUnavailable(Exception):
    """The database cannot be reached or its schema could not be brought up to date."""


class MigrationBlocked(DBUnavailable):
    """A pending migration's precondition failed: nothing was applied.  The message says what
    a person must do first; ensure_schema keeps it for Settings › Database."""


# MySQL error codes that mean the session is gone (the worker reconnects; the API answers 503)
CLIENT_ERROR_CODES = range(2000, 3000)   # libmysqlclient CR_*: gone away, lost, can't connect
SERVER_DROPPED_CONNECTION_CODES = (1053, 1927)   # server shutdown, connection killed


def is_connection_lost(code):
    """True when a pymysql error code means the connection is gone, not that the SQL failed."""
    return code in CLIENT_ERROR_CODES or code in SERVER_DROPPED_CONNECTION_CODES


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
    one migrates, after which they find nothing pending.  The preconditions of every pending
    version are checked first, inside the lock: one failure raises MigrationBlocked and
    nothing is applied, so the previous release still runs on the schema as it was.
    """
    lock = named_lock(LOCK_MIGRATIONS, config["database"])
    conn = get_local_db(config)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT GET_LOCK(%s, 60) AS got", (lock,))
            if cur.fetchone()["got"] != 1:
                raise DBUnavailable("Timed out waiting for the migration lock")
            try:
                applied = _get_applied_versions(cur)
                pending = [m for m in _MIGRATIONS if m[0] not in applied]
                for version, _description, _statements in pending:
                    check = _PRECONDITIONS.get(version)
                    refusal = check(cur) if check else None
                    if refusal:
                        raise MigrationBlocked(refusal)
                for version, description, statements in pending:
                    logger.info("Applying migration v%d: %s", version, description)
                    for sql in statements:
                        cur.execute(sql)
                    cur.execute(
                        "INSERT INTO db_version (version, description) VALUES (%s, %s)",
                        (version, description),
                    )
                    logger.info("Migration v%d applied", version)
            finally:
                cur.execute("SELECT RELEASE_LOCK(%s)", (lock,))
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
