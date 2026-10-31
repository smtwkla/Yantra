"""Owned database — migration engine, connection pool and status probe.

Manages the application's MariaDB database with automatic migrations.
Each migration is a (version, description, [sql_statements]) tuple.
Append new migrations with incrementing version numbers — never edit old ones.  v1–v13 were
squashed into v20 (S025), and v20–v41 into v41 (S088); a migration that cannot run on existing
data gets a precondition (_PRECONDITIONS), checked before anything is applied.

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
# Three squashes:
#   - v1–v13 (S001–S018) into v20, 21-10-2026 (S025, the user's decision U1): production was at
#     v5 (release v0.1.3) and got v20 over its masters;
#   - v20–v41 (S001–S075) into v41, 31-10-2026 (S088, docs/steps/S088-migrations-squash-v41/
#     1-brief.md): production was at v41 (release v0.1.14);
#   - v42–v47 (S079–S085, never released) with S087's change into v50, 31-10-2026 (S087 § 4.1): it
#     follows v41 and converges a dev or test database that holds any of v42–v47 (its comment).
# v41 builds the v41 schema with CREATE TABLE IF NOT EXISTS plus the seed rows (INSERT IGNORE):
#   - an empty database (e2e, the schema docs, a new install): v41 builds everything, then the
#     later versions run;
#   - production, and the dev and test databases (v41 recorded): v41 is skipped; they got the
#     same shape through v20–v41, which the equivalence test proves;
#   - a database with versions recorded but not v41 (an old kept test database, a production dump
#     from before v0.1.14): refused by _v41_squash_check, nothing applied.
# It is numbered 41, production's own version, not above it: a departure from SMTW-WebApp-Base
# § Migration squashing, safe because every database that skips it has the v41 shape and the
# precondition lets only an empty one run it (S088 D1).
# The old texts live on, frozen, only as the test fixture tests/fixtures/migrations_v41.py
# (v20–v41; v20 is itself the squash of v1–v13, whose texts git keeps), and v42–v47's as
# tests/fixtures/migrations_v47.py.  New migrations continue
# after the last entry.  A migration that cannot run on the data production holds gets a
# _PRECONDITIONS entry, never an edit of an applied migration.
#
# Conventions carried over from the squashed migrations:
#   - audit columns: created_* set on insert, updated_* stay NULL until the first edit (set
#     together by the application, never by ON UPDATE, so a time is never recorded without
#     an actor); app_settings.updated_at is the one ON UPDATE;
#   - every column keeps the place the old migrations' ALTERs gave it (e.g. equipment.notes
#     last, model_id after type_id, people.email last), so a database built by v41 and one
#     built by v20–v41 are identical;
#   - MariaDB DDL is not transactional and the version is recorded only after the last
#     statement, so every statement is safe to run twice: a half-applied v41 simply re-runs.

_MIGRATIONS = [
    (41, "Full schema (squashed S001–S075)", [
        # --- Core ----------------------------------------------------------------------------
        """CREATE TABLE IF NOT EXISTS db_version (
            version     INT PRIMARY KEY,
            description VARCHAR(255) NULL,
            applied_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS app_settings (
            setting_key   VARCHAR(100) PRIMARY KEY,
            setting_value TEXT NULL,
            updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )""",

        # --- Basic masters (S001, S004, S063) -------------------------------------------------
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
            created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by       VARCHAR(100) NOT NULL,
            updated_at       DATETIME NULL,
            updated_by       VARCHAR(100) NULL,
            CONSTRAINT uq_units_site_code UNIQUE (site_id, code),
            CONSTRAINT uq_units_warehouse UNIQUE (oneerp_warehouse),
            CONSTRAINT fk_units_site FOREIGN KEY (site_id) REFERENCES sites (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        # A category groups equipment classes (ISO 14224 Annex A, S063); a class is in at most one
        # (equipment_classes.category_id, NULL = none).
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
        """CREATE TABLE IF NOT EXISTS equipment_classes (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            code        VARCHAR(4) NOT NULL,
            name        VARCHAR(100) NOT NULL,
            category_id INT NULL,
            active      TINYINT(1) NOT NULL DEFAULT 1,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            CONSTRAINT uq_equipment_classes_code UNIQUE (code),
            CONSTRAINT fk_equipment_classes_category FOREIGN KEY (category_id)
                REFERENCES equipment_categories (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        # Legacy unit access (S001), replaced by person_units (S011 A1).  Empty on a new database:
        # v20 copied production's rows into Team.  To be dropped by a later step.
        """CREATE TABLE IF NOT EXISTS user_units (
            username    VARCHAR(100) NOT NULL,
            unit_id     INT NOT NULL,
            granted_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            granted_by  VARCHAR(100) NOT NULL,
            PRIMARY KEY (username, unit_id),
            CONSTRAINT fk_user_units_unit FOREIGN KEY (unit_id) REFERENCES units (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        # A counter, not a record, so no audit columns; shared by the serials (TK-, IM-, …)
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
            id              INT AUTO_INCREMENT PRIMARY KEY,
            manufacturer_id INT NOT NULL,
            designation     VARCHAR(80) NOT NULL,
            class_id        INT NOT NULL,
            type_id         INT NULL,
            active          TINYINT(1) NOT NULL DEFAULT 1,
            created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by      VARCHAR(100) NOT NULL,
            updated_at      DATETIME NULL,
            updated_by      VARCHAR(100) NULL,
            CONSTRAINT uq_equipment_models_maker_designation UNIQUE (manufacturer_id, designation),
            CONSTRAINT uq_equipment_models_id_class UNIQUE (id, class_id),
            CONSTRAINT fk_equipment_models_class FOREIGN KEY (class_id) REFERENCES equipment_classes (id),
            CONSTRAINT fk_equipment_models_manufacturer FOREIGN KEY (manufacturer_id)
                REFERENCES manufacturers (id),
            CONSTRAINT fk_equipment_models_type FOREIGN KEY (type_id, class_id)
                REFERENCES equipment_types (id, class_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

        # --- Trades, Team and roles per site (S010 A1, S011 A1, S032) -------------------------
        # A person is named as the user chooses: a person, or a contractor firm; never deleted,
        # only deactivated, so tickets can name them.  memberships: a person's role at a site,
        # with all the site's units or the chosen ones (person_units); role is text validated
        # against config_rbac.SITE_ROLES, one list to keep.  people.email is the login token's
        # address, copied at /api/auth/me (S032); NULL = none; 254 characters, the longest SMTP
        # carries (RFC 5321).
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
            email       VARCHAR(254) NULL,
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

        # --- The equipment register (S002, S004, S012, S030, S033) ----------------------------
        # chk_equipment_level_place makes the tree shape a database rule: equipment has a unit
        # and no parent; component units and components have a parent and no unit.
        # chk_equipment_model_level: equipment and components have a model; a component unit may
        # have none, its class and type then picked directly (S033; InnoDB skips
        # fk_equipment_model while model_id is NULL).  lifecycle is the register status (ISO
        # 55000 life cycle, S030).  equipment_events is a history log — equipment's own columns
        # stay the truth, nothing replays the events; ENUM values are only ever appended.
        """CREATE TABLE IF NOT EXISTS equipment (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            code        VARCHAR(12) NOT NULL,
            level       ENUM('equipment','component_unit','component') NOT NULL,
            parent_id   INT NULL,
            unit_id     INT NULL,
            class_id    INT NOT NULL,
            type_id     INT NULL,
            model_id    INT NULL,
            name        VARCHAR(100) NOT NULL,
            serial_no   VARCHAR(100) NULL,
            year        SMALLINT NULL,
            criticality ENUM('A','B','C') NULL,
            lifecycle   ENUM('in_service','standby','out_of_use','scrapped') NOT NULL DEFAULT 'in_service',
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            notes       TEXT NULL,
            CONSTRAINT uq_equipment_code UNIQUE (code),
            INDEX ix_equipment_model (model_id, class_id),
            CONSTRAINT fk_equipment_class FOREIGN KEY (class_id) REFERENCES equipment_classes (id),
            CONSTRAINT fk_equipment_model FOREIGN KEY (model_id, class_id)
                REFERENCES equipment_models (id, class_id),
            CONSTRAINT fk_equipment_parent FOREIGN KEY (parent_id) REFERENCES equipment (id),
            CONSTRAINT fk_equipment_type FOREIGN KEY (type_id, class_id)
                REFERENCES equipment_types (id, class_id),
            CONSTRAINT fk_equipment_unit FOREIGN KEY (unit_id) REFERENCES units (id),
            CONSTRAINT chk_equipment_level_place CHECK (
                (level = 'equipment') = (unit_id IS NOT NULL)
                AND (level = 'equipment') = (parent_id IS NULL)),
            CONSTRAINT chk_equipment_model_level CHECK (model_id IS NOT NULL OR level = 'component_unit')
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS equipment_events (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            equipment_id INT NOT NULL,
            event        ENUM('created','moved_unit','moved_parent','lifecycle','criticality','class','type',
                              'model','meter_added','meter_removed','meter_limits','property') NOT NULL,
            old_value    VARCHAR(200) NULL,
            new_value    VARCHAR(200) NULL,
            created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by   VARCHAR(100) NOT NULL,
            INDEX ix_equipment_events_equipment (equipment_id, created_at),
            CONSTRAINT fk_equipment_events_equipment FOREIGN KEY (equipment_id) REFERENCES equipment (id)
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
            INDEX ix_failure_modes_class (class_id, active),
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

        # --- Tickets (S017, S018, S019, S020, S027) ------------------------------------------
        # One record per problem found on equipment, a breakdown (critical) or a defect
        # (degraded, initial) — EN 13460's work request, ISO 14224's failure record.
        # equipment_id is always the machine; component_id the component-unit or component it
        # was raised on, when lower.  unit_id is the machine's unit at raise, kept when it
        # moves.  The intensity ENUM's order puts critical first in ORDER BY.  The close's
        # cause and action (NULL action on a ticket closed as not a fault), the not-a-fault
        # flag and the repeat link (a new ticket on the same machine after a restoration that
        # did not hold) are S018's.  The plan (planned_date, waiting_reason) is set on scheduled
        # tickets and on no others (chk_tickets_plan, S019).  ticket_events is the timeline the
        # figures (response, repair, downtime) are computed from; they are never stored.
        """CREATE TABLE IF NOT EXISTS tickets (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            serial          VARCHAR(16) NOT NULL,
            equipment_id    INT NOT NULL,
            component_id    INT NULL,
            unit_id         INT NOT NULL,
            intensity       ENUM('critical','degraded','initial') NOT NULL,
            state           ENUM('raised','acknowledged','in_progress','back_in_service','closed','scheduled')
                            NOT NULL DEFAULT 'raised',
            planned_date    DATE NULL,
            waiting_reason  ENUM('parts','vendor','expert','slot','approval','other') NULL,
            failure_mode_id INT NULL,
            cause_id        INT NULL,
            action_id       INT NULL,
            not_a_fault     TINYINT(1) NOT NULL DEFAULT 0,
            repeat_of_id    INT NULL,
            description     VARCHAR(1000) NULL,
            reported_by_id  INT NULL,
            occurred_at     DATETIME NOT NULL,
            source          ENUM('manual') NOT NULL DEFAULT 'manual',
            created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by      VARCHAR(100) NOT NULL,
            updated_at      DATETIME NULL,
            updated_by      VARCHAR(100) NULL,
            CONSTRAINT uq_tickets_serial UNIQUE (serial),
            INDEX ix_tickets_unit_state (unit_id, state),
            INDEX ix_tickets_equipment_state (equipment_id, state),
            INDEX ix_tickets_component_state (component_id, state),
            INDEX ix_tickets_repeat_of (repeat_of_id),
            INDEX ix_tickets_created_by (created_by),
            CONSTRAINT fk_tickets_action FOREIGN KEY (action_id) REFERENCES maintenance_actions (id),
            CONSTRAINT fk_tickets_cause FOREIGN KEY (cause_id) REFERENCES failure_causes (id),
            CONSTRAINT fk_tickets_component FOREIGN KEY (component_id) REFERENCES equipment (id),
            CONSTRAINT fk_tickets_equipment FOREIGN KEY (equipment_id) REFERENCES equipment (id),
            CONSTRAINT fk_tickets_failure_mode FOREIGN KEY (failure_mode_id) REFERENCES failure_modes (id),
            CONSTRAINT fk_tickets_repeat_of FOREIGN KEY (repeat_of_id) REFERENCES tickets (id),
            CONSTRAINT fk_tickets_reported_by FOREIGN KEY (reported_by_id) REFERENCES people (id),
            CONSTRAINT fk_tickets_unit FOREIGN KEY (unit_id) REFERENCES units (id),
            CONSTRAINT chk_tickets_plan CHECK (
                (state = 'scheduled') = (planned_date IS NOT NULL AND waiting_reason IS NOT NULL))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        # The assignees, and the labour rows (person, trade worked, date, minutes: ISO 14224
        # man-hours per discipline)
        """CREATE TABLE IF NOT EXISTS ticket_assignees (
            ticket_id   INT NOT NULL,
            person_id   INT NOT NULL,
            assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            assigned_by VARCHAR(100) NOT NULL,
            PRIMARY KEY (ticket_id, person_id),
            INDEX ix_ticket_assignees_person (person_id),
            CONSTRAINT fk_ticket_assignees_person FOREIGN KEY (person_id) REFERENCES people (id),
            CONSTRAINT fk_ticket_assignees_ticket FOREIGN KEY (ticket_id) REFERENCES tickets (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        # planned_date and waiting_reason are set on scheduled / rescheduled events, and
        # machine_stopped on a started event written from scheduled on a ticket that was not
        # critical; NULL elsewhere (S019).  A work note is a row with event 'note'; updated_* is
        # set on notes only, and ticket_note_edits keeps a corrected note's earlier texts (S027,
        # ISO 9001 § 7.5.3).
        """CREATE TABLE IF NOT EXISTS ticket_events (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            ticket_id       INT NOT NULL,
            event           VARCHAR(30) NOT NULL,
            from_state      VARCHAR(20) NULL,
            to_state        VARCHAR(20) NULL,
            occurred_at     DATETIME NOT NULL,
            intensity       ENUM('critical','degraded','initial') NULL,
            person_id       INT NULL,
            remark          VARCHAR(1000) NULL,
            planned_date    DATE NULL,
            waiting_reason  ENUM('parts','vendor','expert','slot','approval','other') NULL,
            machine_stopped TINYINT(1) NULL,
            created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by      VARCHAR(100) NOT NULL,
            updated_at      DATETIME NULL,
            updated_by      VARCHAR(100) NULL,
            INDEX ix_ticket_events_ticket (ticket_id, occurred_at, id),
            INDEX ix_ticket_events_created_by (created_by, created_at, id),
            CONSTRAINT fk_ticket_events_person FOREIGN KEY (person_id) REFERENCES people (id),
            CONSTRAINT fk_ticket_events_ticket FOREIGN KEY (ticket_id) REFERENCES tickets (id)
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
            INDEX ix_ticket_labour_ticket (ticket_id),
            INDEX ix_ticket_labour_person (person_id, work_date),
            CONSTRAINT fk_ticket_labour_person FOREIGN KEY (person_id) REFERENCES people (id),
            CONSTRAINT fk_ticket_labour_ticket FOREIGN KEY (ticket_id) REFERENCES tickets (id),
            CONSTRAINT fk_ticket_labour_trade FOREIGN KEY (trade_id) REFERENCES trades (id),
            CONSTRAINT chk_ticket_labour_minutes CHECK (minutes BETWEEN 1 AND 1440)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS ticket_note_edits (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            event_id    INT NOT NULL,
            remark      VARCHAR(1000) NOT NULL,
            replaced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            replaced_by VARCHAR(100) NOT NULL,
            INDEX ix_ticket_note_edits_event (event_id, id),
            CONSTRAINT fk_ticket_note_edits_event FOREIGN KEY (event_id) REFERENCES ticket_events (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        # Parts used (S020): what was fitted, its number, maker and quantity, on the ticket's
        # machine or a component of it (ISO 14224 Table 8).  No stock, cost or item master:
        # OneERP's.  number_kind is set exactly when part_number is; qty_unit is checked in
        # tickets_core.PART_UNITS, not by an ENUM, so a unit is added without a migration.
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
            INDEX ix_ticket_parts_ticket (ticket_id),
            INDEX ix_ticket_parts_node (node_id),
            INDEX ix_ticket_parts_number (part_number),
            CONSTRAINT fk_ticket_parts_node FOREIGN KEY (node_id) REFERENCES equipment (id),
            CONSTRAINT fk_ticket_parts_ticket FOREIGN KEY (ticket_id) REFERENCES tickets (id),
            CONSTRAINT chk_ticket_parts_kind CHECK ((part_number IS NULL) = (number_kind IS NULL)),
            CONSTRAINT chk_ticket_parts_quantity CHECK (quantity > 0)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

        # --- Access log, task queue and push subscriptions (S013, S021) -----------------------
        # access_log is append-only by design (ISO 27001 A.8.15): no foreign keys, so it keeps
        # its rows when people or logins change; only the scheduled purge deletes, by age.
        # ux_access_log_sighting keeps one row per sighting key per IST day across every
        # Gunicorn worker (S013 A1).
        """CREATE TABLE IF NOT EXISTS access_log (
            id            BIGINT AUTO_INCREMENT PRIMARY KEY,
            ts            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            username      VARCHAR(100) NULL,
            role          VARCHAR(100) NULL,
            session_id    VARCHAR(100) NULL,
            client_ip     VARCHAR(45) NOT NULL,
            is_internal   TINYINT(1) NOT NULL,
            outcome       ENUM('ok','auth_failed','denied_network','denied_perm') NOT NULL,
            method        VARCHAR(10) NOT NULL,
            path          VARCHAR(255) NOT NULL,
            user_agent    VARCHAR(255) NULL,
            detail        VARCHAR(255) NULL,
            sighting_day  DATE NOT NULL,
            sighting_hash CHAR(40) NOT NULL,
            CONSTRAINT ux_access_log_sighting UNIQUE (sighting_hash, sighting_day),
            INDEX ix_access_log_ts (ts),
            INDEX ix_access_log_user_ts (username, ts)
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
        # One row per device that turned notifications on, against the person whose alerts it
        # gets (S021).  endpoint_hash (SHA-256 hex of endpoint, too long for an index) is the
        # unique key; a re-subscribe of the same device moves the row to whoever signed in last.
        # p256dh and auth only let someone send to that device: plain columns, never sent back.
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
            INDEX ix_push_subscriptions_person (person_id),
            CONSTRAINT fk_push_subscriptions_person FOREIGN KEY (person_id) REFERENCES people (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

        # --- Meters (S037, S038, S039) -------------------------------------------------------
        # chk_meter_types_yes_no keeps a Yes / No type's shape (no unit, no decimals, an expected
        # answer) a database rule; the code reports it first, with a field.
        """CREATE TABLE IF NOT EXISTS meter_types (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            name            VARCHAR(60) NOT NULL,
            unit            VARCHAR(20) NULL,
            kind            ENUM('counter','gauge','amount','yes_no') NOT NULL,
            expected_answer ENUM('yes','no') NULL,
            decimals        TINYINT NOT NULL DEFAULT 0,
            active          TINYINT(1) NOT NULL DEFAULT 1,
            created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by      VARCHAR(100) NOT NULL,
            updated_at      DATETIME NULL,
            updated_by      VARCHAR(100) NULL,
            CONSTRAINT uq_meter_types_name UNIQUE (name),
            CONSTRAINT chk_meter_types_decimals CHECK (decimals BETWEEN 0 AND 3),
            CONSTRAINT chk_meter_types_yes_no CHECK (
                (kind = 'yes_no' AND unit IS NULL AND expected_answer IS NOT NULL AND decimals = 0)
                OR (kind <> 'yes_no' AND unit IS NOT NULL AND expected_answer IS NULL))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        # A model lists its meters with default gauge limits; a node's meters are its model's
        # (computed live, never copied) plus its own rows in node_meters.  node_meters holds both
        # a node's own meters (own = 1) and its overrides of a model meter's limits (own = 0);
        # own never changes after insert.  Limits stay NULL on a counter, an amount and a Yes / No
        # meter: a code rule, since the kind is on meter_types.  Rows are never deleted, only set
        # inactive, except an own = 0 override that equals the model again.
        """CREATE TABLE IF NOT EXISTS model_meters (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            model_id      INT NOT NULL,
            meter_type_id INT NOT NULL,
            min_value     DECIMAL(14,3) NULL,
            max_value     DECIMAL(14,3) NULL,
            active        TINYINT(1) NOT NULL DEFAULT 1,
            created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by    VARCHAR(100) NOT NULL,
            updated_at    DATETIME NULL,
            updated_by    VARCHAR(100) NULL,
            CONSTRAINT uq_model_meters UNIQUE (model_id, meter_type_id),
            CONSTRAINT fk_model_meters_model FOREIGN KEY (model_id) REFERENCES equipment_models (id),
            CONSTRAINT fk_model_meters_type FOREIGN KEY (meter_type_id) REFERENCES meter_types (id),
            CONSTRAINT chk_model_meters_limits CHECK (min_value IS NULL OR max_value IS NULL OR min_value <= max_value)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS node_meters (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            equipment_id  INT NOT NULL,
            meter_type_id INT NOT NULL,
            own           TINYINT(1) NOT NULL,
            min_value     DECIMAL(14,3) NULL,
            max_value     DECIMAL(14,3) NULL,
            active        TINYINT(1) NOT NULL DEFAULT 1,
            created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by    VARCHAR(100) NOT NULL,
            updated_at    DATETIME NULL,
            updated_by    VARCHAR(100) NULL,
            CONSTRAINT uq_node_meters UNIQUE (equipment_id, meter_type_id),
            CONSTRAINT fk_node_meters_node FOREIGN KEY (equipment_id) REFERENCES equipment (id),
            CONSTRAINT fk_node_meters_type FOREIGN KEY (meter_type_id) REFERENCES meter_types (id),
            CONSTRAINT chk_node_meters_limits CHECK (min_value IS NULL OR max_value IS NULL OR min_value <= max_value)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        # One row per reading of one meter (node + meter type) at one minute; a Yes / No reading
        # stores 1 / 0.  limit_state is stored at saving, so a later limit change never re-judges
        # old readings.  Rows are never deleted: a removal sets removed_at / removed_by (ISO 27001
        # A.8.15).  No unique key on the time: a removed reading may share its minute with its
        # replacement; two active readings at one minute are refused in code.
        """CREATE TABLE IF NOT EXISTS meter_readings (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            equipment_id  INT NOT NULL,
            meter_type_id INT NOT NULL,
            value         DECIMAL(14,3) NOT NULL,
            taken_at      DATETIME NOT NULL,
            is_reset      TINYINT(1) NOT NULL DEFAULT 0,
            limit_state   ENUM('low','high','not_ok') NULL,
            source        ENUM('manual','pm','move','iiot') NOT NULL DEFAULT 'manual',
            note          VARCHAR(200) NULL,
            created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by    VARCHAR(100) NOT NULL,
            removed_at    DATETIME NULL,
            removed_by    VARCHAR(100) NULL,
            INDEX ix_meter_readings_meter_time (equipment_id, meter_type_id, taken_at),
            CONSTRAINT fk_meter_readings_node FOREIGN KEY (equipment_id) REFERENCES equipment (id),
            CONSTRAINT fk_meter_readings_type FOREIGN KEY (meter_type_id) REFERENCES meter_types (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

        # --- Properties (S043, S044, S061) ---------------------------------------------------
        # Technical data defined once (ISO 14224 Annex A; IEC 61360: one definition with a data
        # type and a unit, reused across classes), linked to classes, valued on models and, where
        # a nameplate differs, on an item.  all_classes: on every class without a link;
        # per_item_only: installation data, valued on each machine, never on a model (S061).
        """CREATE TABLE IF NOT EXISTS property_definitions (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            name          VARCHAR(80) NOT NULL,
            data_type     ENUM('number','choice','text','yes_no','geo') NOT NULL,
            unit          VARCHAR(20) NULL,
            description   VARCHAR(300) NULL,
            active        TINYINT(1) NOT NULL DEFAULT 1,
            created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by    VARCHAR(100) NOT NULL,
            updated_at    DATETIME NULL,
            updated_by    VARCHAR(100) NULL,
            all_classes   TINYINT(1) NOT NULL DEFAULT 0,
            per_item_only TINYINT(1) NOT NULL DEFAULT 0,
            CONSTRAINT uq_property_definitions_name UNIQUE (name),
            CONSTRAINT chk_property_unit CHECK (data_type = 'number' OR unit IS NULL)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        # No active flag: removing a property from a class deletes the link; the values stay
        """CREATE TABLE IF NOT EXISTS class_properties (
            class_id    INT NOT NULL,
            property_id INT NOT NULL,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            PRIMARY KEY (class_id, property_id),
            CONSTRAINT fk_class_properties_class FOREIGN KEY (class_id) REFERENCES equipment_classes (id),
            CONSTRAINT fk_class_properties_property FOREIGN KEY (property_id)
                REFERENCES property_definitions (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS property_options (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            property_id INT NOT NULL,
            label       VARCHAR(60) NOT NULL,
            active      TINYINT(1) NOT NULL DEFAULT 1,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            CONSTRAINT uq_property_options_label UNIQUE (property_id, label),
            CONSTRAINT uq_property_options_id_property UNIQUE (id, property_id),
            CONSTRAINT fk_property_options_property FOREIGN KEY (property_id)
                REFERENCES property_definitions (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        # One typed column per data type and exactly one filled (the one-value CHECK; a geo value
        # is value_lat with value_lng, both or neither, in range); which one must follow the
        # property's data_type, which properties_core checks (a CHECK cannot read another table).
        # The option's composite FK makes "the option is this property's" a database rule.  No
        # row = no value.  equipment_property_values: an item's own value, which wins over its
        # model's (S044); a model or class change leaves the rows alone.
        """CREATE TABLE IF NOT EXISTS model_property_values (
            model_id     INT NOT NULL,
            property_id  INT NOT NULL,
            value_number DECIMAL(16,4) NULL,
            value_text   VARCHAR(100) NULL,
            value_bool   TINYINT(1) NULL,
            option_id    INT NULL,
            updated_at   DATETIME NULL,
            updated_by   VARCHAR(100) NULL,
            value_lat    DECIMAL(8,6) NULL,
            value_lng    DECIMAL(9,6) NULL,
            PRIMARY KEY (model_id, property_id),
            CONSTRAINT fk_model_property_values_model FOREIGN KEY (model_id)
                REFERENCES equipment_models (id),
            CONSTRAINT fk_model_property_values_option FOREIGN KEY (option_id, property_id)
                REFERENCES property_options (id, property_id),
            CONSTRAINT fk_model_property_values_property FOREIGN KEY (property_id)
                REFERENCES property_definitions (id),
            CONSTRAINT chk_model_property_one_value CHECK (
                (value_number IS NOT NULL) + (value_text IS NOT NULL) + (value_bool IS NOT NULL)
                + (option_id IS NOT NULL) + (value_lat IS NOT NULL) = 1),
            CONSTRAINT chk_model_property_geo_pair CHECK ((value_lat IS NULL) = (value_lng IS NULL)),
            CONSTRAINT chk_model_property_geo_range CHECK (value_lat IS NULL OR (
                value_lat BETWEEN -90 AND 90 AND value_lng BETWEEN -180 AND 180))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS equipment_property_values (
            equipment_id INT NOT NULL,
            property_id  INT NOT NULL,
            value_number DECIMAL(16,4) NULL,
            value_text   VARCHAR(100) NULL,
            value_bool   TINYINT(1) NULL,
            option_id    INT NULL,
            updated_at   DATETIME NULL,
            updated_by   VARCHAR(100) NULL,
            value_lat    DECIMAL(8,6) NULL,
            value_lng    DECIMAL(9,6) NULL,
            PRIMARY KEY (equipment_id, property_id),
            CONSTRAINT fk_equipment_property_values_node FOREIGN KEY (equipment_id)
                REFERENCES equipment (id),
            CONSTRAINT fk_equipment_property_values_option FOREIGN KEY (option_id, property_id)
                REFERENCES property_options (id, property_id),
            CONSTRAINT fk_equipment_property_values_property FOREIGN KEY (property_id)
                REFERENCES property_definitions (id),
            CONSTRAINT chk_equipment_property_one_value CHECK (
                (value_number IS NOT NULL) + (value_text IS NOT NULL) + (value_bool IS NOT NULL)
                + (option_id IS NOT NULL) + (value_lat IS NOT NULL) = 1),
            CONSTRAINT chk_equipment_property_geo_pair CHECK ((value_lat IS NULL) = (value_lng IS NULL)),
            CONSTRAINT chk_equipment_property_geo_range CHECK (value_lat IS NULL OR (
                value_lat BETWEEN -90 AND 90 AND value_lng BETWEEN -180 AND 180))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

        # --- Improvements (S067, S069, S070, S072, S074) -------------------------------------
        # One problem analysed from one or more tickets (TPM focused improvement).  The unit and
        # the machine are the first ticket's; the site is the unit's.  Serials IM-YYYY-MM-NNN
        # through serial_counters rows IM:YYYY-MM.  ready_to_verify is computed, never stored.
        # The root cause is a text and one cause of the failure-cause list, both or neither.  The
        # watch (watch_days, watch_from), the close (closed_at, closed_by, close_remark) and the
        # follow-up a *not effective* close starts (follow_up_of_id, at most one).
        # ready_alert_for (S074): the watch end the daily scan alerted; NULL = never.
        """CREATE TABLE IF NOT EXISTS improvements (
            id                  INT AUTO_INCREMENT PRIMARY KEY,
            serial              VARCHAR(16) NOT NULL,
            unit_id             INT NOT NULL,
            equipment_id        INT NOT NULL,
            state               ENUM('analysing','actions_open','watching','closed_effective','closed_not_effective',
                                     'dropped') NOT NULL DEFAULT 'analysing',
            title               VARCHAR(120) NOT NULL,
            problem             VARCHAR(2000) NOT NULL,
            root_cause          VARCHAR(500) NULL,
            root_cause_id       INT NULL,
            contributing_causes VARCHAR(2000) NULL,
            watch_days          SMALLINT NOT NULL DEFAULT 90,
            watch_from          DATETIME NULL,
            ready_alert_for     DATETIME NULL,
            closed_at           DATETIME NULL,
            closed_by           VARCHAR(100) NULL,
            close_remark        VARCHAR(1000) NULL,
            follow_up_of_id     INT NULL,
            lead_id             INT NOT NULL,
            created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by          VARCHAR(100) NOT NULL,
            updated_at          DATETIME NULL,
            updated_by          VARCHAR(100) NULL,
            CONSTRAINT uq_improvements_serial UNIQUE (serial),
            CONSTRAINT uq_improvements_follow_up UNIQUE (follow_up_of_id),
            INDEX ix_improvements_unit_state (unit_id, state),
            INDEX ix_improvements_equipment (equipment_id),
            INDEX ix_improvements_root_cause (root_cause_id),
            CONSTRAINT fk_improvements_equipment FOREIGN KEY (equipment_id) REFERENCES equipment (id),
            CONSTRAINT fk_improvements_follow_up FOREIGN KEY (follow_up_of_id) REFERENCES improvements (id),
            CONSTRAINT fk_improvements_lead FOREIGN KEY (lead_id) REFERENCES people (id),
            CONSTRAINT fk_improvements_root_cause FOREIGN KEY (root_cause_id) REFERENCES failure_causes (id),
            CONSTRAINT fk_improvements_unit FOREIGN KEY (unit_id) REFERENCES units (id),
            CONSTRAINT chk_improvements_root_cause CHECK ((root_cause IS NULL) = (root_cause_id IS NULL)),
            CONSTRAINT chk_improvements_watch_days CHECK (watch_days BETWEEN 30 AND 365),
            CONSTRAINT chk_improvements_watch_from CHECK (
                (state IN ('analysing','actions_open') AND watch_from IS NULL)
                OR (state IN ('watching','closed_effective','closed_not_effective') AND watch_from IS NOT NULL)
                OR state = 'dropped'),
            CONSTRAINT chk_improvements_closed CHECK (
                (state IN ('closed_effective','closed_not_effective','dropped'))
                = (closed_at IS NOT NULL AND closed_by IS NOT NULL)),
            CONSTRAINT chk_improvements_close_remark CHECK (
                state NOT IN ('closed_not_effective','dropped') OR close_remark IS NOT NULL)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        # One ordered chain of Why? / Because lines per improvement (TPM why-why).  position is
        # 1..n with no gaps, kept by improvements.py under the improvement's lock (6b); no unique
        # key, so a reorder needs no temporary values.  A removed why is deleted.
        """CREATE TABLE IF NOT EXISTS improvement_whys (
            id             INT AUTO_INCREMENT PRIMARY KEY,
            improvement_id INT NOT NULL,
            position       SMALLINT NOT NULL,
            question       VARCHAR(300) NOT NULL,
            answer         VARCHAR(1000) NOT NULL,
            evidence       VARCHAR(500) NULL,
            created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by     VARCHAR(100) NOT NULL,
            updated_at     DATETIME NULL,
            updated_by     VARCHAR(100) NULL,
            INDEX ix_improvement_whys_position (improvement_id, position),
            CONSTRAINT fk_improvement_whys_improvement FOREIGN KEY (improvement_id)
                REFERENCES improvements (id),
            CONSTRAINT chk_improvement_whys_position CHECK (position >= 1)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        # Countermeasures: each with a kind, an owner and a due date (ISO 9001 § 10.2.1 c).  Never
        # deleted: a cancel keeps the row with its reason (ISO 9001 § 7.5.3).  A done row carries
        # its text, time and recorder, a row that is not done never all three; the same for
        # cancelled.  overdue_alert_for (S074): the due date the daily scan alerted; NULL = never.
        """CREATE TABLE IF NOT EXISTS improvement_actions (
            id                INT AUTO_INCREMENT PRIMARY KEY,
            improvement_id    INT NOT NULL,
            kind              ENUM('correction','corrective','preventive','design_out','lesson','spread')
                              NOT NULL,
            text              VARCHAR(500) NOT NULL,
            owner_id          INT NOT NULL,
            due_date          DATE NOT NULL,
            overdue_alert_for DATE NULL,
            state             ENUM('open','done','cancelled') NOT NULL DEFAULT 'open',
            done_text         VARCHAR(1000) NULL,
            done_at           DATETIME NULL,
            done_by           VARCHAR(100) NULL,
            cancel_reason     VARCHAR(500) NULL,
            cancelled_at      DATETIME NULL,
            cancelled_by      VARCHAR(100) NULL,
            created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by        VARCHAR(100) NOT NULL,
            updated_at        DATETIME NULL,
            updated_by        VARCHAR(100) NULL,
            INDEX ix_improvement_actions_improvement (improvement_id, id),
            INDEX ix_improvement_actions_owner_state (owner_id, state, due_date),
            CONSTRAINT fk_improvement_actions_improvement FOREIGN KEY (improvement_id)
                REFERENCES improvements (id),
            CONSTRAINT fk_improvement_actions_owner FOREIGN KEY (owner_id) REFERENCES people (id),
            CONSTRAINT chk_improvement_actions_done CHECK (
                (state = 'done') = (done_text IS NOT NULL AND done_at IS NOT NULL AND done_by IS NOT NULL)),
            CONSTRAINT chk_improvement_actions_cancelled CHECK (
                (state = 'cancelled')
                = (cancel_reason IS NOT NULL AND cancelled_at IS NOT NULL AND cancelled_by IS NOT NULL))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        # open_link is 1 while the improvement is open and NULL after: the UNIQUE key allows one
        # open link per ticket and any number of NULLs, so a ticket is in at most one open
        # improvement.
        """CREATE TABLE IF NOT EXISTS improvement_tickets (
            improvement_id INT NOT NULL,
            ticket_id      INT NOT NULL,
            open_link      TINYINT(1) NULL DEFAULT 1,
            created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by     VARCHAR(100) NOT NULL,
            PRIMARY KEY (improvement_id, ticket_id),
            CONSTRAINT uq_improvement_tickets_open UNIQUE (ticket_id, open_link),
            CONSTRAINT fk_improvement_tickets_improvement FOREIGN KEY (improvement_id)
                REFERENCES improvements (id),
            CONSTRAINT fk_improvement_tickets_ticket FOREIGN KEY (ticket_id) REFERENCES tickets (id),
            CONSTRAINT chk_improvement_tickets_open_link CHECK (open_link IS NULL OR open_link = 1)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        # The timeline, as ticket_events: one line per change, who and when; remark the new text,
        # earlier the replaced one (ISO 9001 § 7.5.3).  ticket_id and action_id name the ticket or
        # countermeasure a line is about.  No why_id: a removed why's row is deleted, so a why
        # line carries its text.
        """CREATE TABLE IF NOT EXISTS improvement_events (
            id             INT AUTO_INCREMENT PRIMARY KEY,
            improvement_id INT NOT NULL,
            event          VARCHAR(30) NOT NULL,
            occurred_at    DATETIME NOT NULL,
            from_state     VARCHAR(30) NULL,
            to_state       VARCHAR(30) NULL,
            ticket_id      INT NULL,
            action_id      INT NULL,
            remark         TEXT NULL,
            earlier        TEXT NULL,
            created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by     VARCHAR(100) NOT NULL,
            INDEX ix_improvement_events_improvement (improvement_id, occurred_at, id),
            CONSTRAINT fk_improvement_events_action FOREIGN KEY (action_id)
                REFERENCES improvement_actions (id),
            CONSTRAINT fk_improvement_events_improvement FOREIGN KEY (improvement_id)
                REFERENCES improvements (id),
            CONSTRAINT fk_improvement_events_ticket FOREIGN KEY (ticket_id) REFERENCES tickets (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

        # --- Procedures and documents (S006, S012, S017, S070, S075) -------------------------
        # One-point lessons, the first kind of the Procedures master (S075).  A lesson names the
        # machine it was written on; class_id, when set, shows it on every machine of that class
        # too (TPM yokoten).  action_id: the countermeasure of kind Lesson it was written for, one
        # lesson per countermeasure (NULLs repeat).  Never deleted: a retired lesson keeps its row.
        """CREATE TABLE IF NOT EXISTS procedures (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            serial       VARCHAR(16) NOT NULL,
            kind         ENUM('one_point_lesson') NOT NULL DEFAULT 'one_point_lesson',
            equipment_id INT NOT NULL,
            class_id     INT NULL,
            title        VARCHAR(80) NOT NULL,
            body         VARCHAR(1000) NOT NULL,
            action_id    INT NULL,
            active       TINYINT(1) NOT NULL DEFAULT 1,
            created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by   VARCHAR(100) NOT NULL,
            updated_at   DATETIME NULL,
            updated_by   VARCHAR(100) NULL,
            CONSTRAINT uq_procedures_serial UNIQUE (serial),
            CONSTRAINT uq_procedures_action UNIQUE (action_id),
            INDEX ix_procedures_equipment (equipment_id, active),
            INDEX ix_procedures_class (class_id, active),
            CONSTRAINT fk_procedures_action FOREIGN KEY (action_id) REFERENCES improvement_actions (id),
            CONSTRAINT fk_procedures_class FOREIGN KEY (class_id) REFERENCES equipment_classes (id),
            CONSTRAINT fk_procedures_equipment FOREIGN KEY (equipment_id) REFERENCES equipment (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        # The files live under DATA_DIR; a row is never deleted — removed_at hides it (ISO
        # 55001 controlled information).  Only the title is ever edited (updated_*).  Five
        # owners — a node, a model, a ticket, a countermeasure, a lesson — and the CHECK keeps
        # exactly one per document.
        """CREATE TABLE IF NOT EXISTS equipment_documents (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            equipment_id  INT NULL,
            model_id      INT NULL,
            ticket_id     INT NULL,
            action_id     INT NULL,
            procedure_id  INT NULL,
            kind          ENUM('document','photo') NOT NULL,
            title         VARCHAR(200) NOT NULL,
            original_name VARCHAR(255) NOT NULL,
            stored_name   VARCHAR(80) NOT NULL,
            content_type  VARCHAR(50) NOT NULL,
            size_bytes    INT NOT NULL,
            has_thumb     TINYINT(1) NOT NULL DEFAULT 0,
            created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by    VARCHAR(100) NOT NULL,
            updated_at    DATETIME NULL,
            updated_by    VARCHAR(100) NULL,
            removed_at    DATETIME NULL,
            removed_by    VARCHAR(100) NULL,
            CONSTRAINT uq_equipment_documents_stored UNIQUE (stored_name),
            INDEX ix_equipment_documents_node (equipment_id, removed_at),
            INDEX ix_equipment_documents_model (model_id, removed_at),
            INDEX ix_equipment_documents_ticket (ticket_id, removed_at),
            INDEX ix_equipment_documents_action (action_id, removed_at),
            INDEX ix_equipment_documents_procedure (procedure_id, removed_at),
            CONSTRAINT fk_equipment_documents_action FOREIGN KEY (action_id)
                REFERENCES improvement_actions (id),
            CONSTRAINT fk_equipment_documents_equipment FOREIGN KEY (equipment_id) REFERENCES equipment (id),
            CONSTRAINT fk_equipment_documents_model FOREIGN KEY (model_id) REFERENCES equipment_models (id),
            CONSTRAINT fk_equipment_documents_procedure FOREIGN KEY (procedure_id)
                REFERENCES procedures (id),
            CONSTRAINT fk_equipment_documents_ticket FOREIGN KEY (ticket_id) REFERENCES tickets (id),
            CONSTRAINT chk_equipment_documents_owner CHECK (
                (equipment_id IS NOT NULL) + (model_id IS NOT NULL) + (ticket_id IS NOT NULL)
                + (action_id IS NOT NULL) + (procedure_id IS NOT NULL) = 1)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

        # --- Data: INSERT IGNORE, so a re-run keeps an edited row and adds a missing one -------
        # The rows are written in the order the old migrations wrote them, so their ids match.
        # The created_by tags name the version that first seeded them (migration-v11, -v29, -v31,
        # -v34) and are kept verbatim: the code and the tests tell the seed rows apart by them.
        # Setting defaults.  The internal ranges are the RFC 1918 private ranges
        # (network_core.DEFAULT_INTERNAL_NETWORKS, repeated here: a migration is frozen text).
        "INSERT IGNORE INTO app_settings (setting_key, setting_value) VALUES ('upload_max_mb', '20')",
        """INSERT IGNORE INTO app_settings (setting_key, setting_value)
            VALUES ('internal_networks', '10.0.0.0/8,172.16.0.0/12,192.168.0.0/16')""",
        # The escalation times' defaults (S021: A 10, B 30, C 60 minutes), so get_setting_int finds
        # a row instead of warning at every raise
        """INSERT IGNORE INTO app_settings (setting_key, setting_value)
            VALUES ('escalate_minutes_a', '10'), ('escalate_minutes_b', '30'), ('escalate_minutes_c', '60')""",
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
        # The meter-type seed (S037), keyed on the unique name
        """INSERT IGNORE INTO meter_types (name, unit, kind, decimals, created_by) VALUES
            ('Run hours', 'h', 'counter', 1, 'migration-v29'),
            ('Strokes', 'strokes', 'counter', 0, 'migration-v29'),
            ('Production counter', 'pcs', 'counter', 0, 'migration-v29'),
            ('Energy', 'kWh', 'counter', 1, 'migration-v29'),
            ('Odometer', 'km', 'counter', 0, 'migration-v29'),
            ('Oil temperature', '°C', 'gauge', 1, 'migration-v29'),
            ('Fuel level', '%', 'gauge', 0, 'migration-v29'),
            ('Shift production', 'pcs', 'amount', 0, 'migration-v29')""",
        # The property seed (S043 § 4.6): ISO 14224 Annex A names where it has the class, plus common nameplate
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
        # The GPS location (S061): on every class, valued on each machine
        """INSERT IGNORE INTO property_definitions (name, data_type, description, all_classes, per_item_only,
                                                    created_by)
            VALUES ('GPS location', 'geo',
                    'Where the machine stands. Tap Use my current location next to the machine, or paste from Google Maps.',
                    1, 1, 'migration-v34')""",
    ]),
    # S087 — v42–v47 (S079–S085, R02, never released) squashed into one entry with S087's change: a contract has no
    # site (docs/steps/S087-contracts-across-sites/1-brief.md § 4.1).  Numbered 50, above every version a database
    # has recorded (dev and test hold up to v47; SMTW-WebApp-Base § Migration squashing); the old v42–v47 rows of a dev
    # database stay as history, and their texts live frozen in tests/fixtures/migrations_v47.py.  Three shapes:
    #   - fresh after v41 (a new install, e2e, the tests) and production at v41: steps 1–8 create everything, the
    #     convergence statements are no-ops;
    #   - dev and test at any of v42–v47: every IF NOT EXISTS piece is a no-op, and the convergence statements bring
    #     contracts to the final shape (the v46 columns, v47's key, the site's foreign key, key and column dropped).
    # No precondition: production holds none of these tables; on dev, dropping site_id with its values is S087's
    # decision (the site is no longer a fact of a contract).  Every statement is safe to run twice, so a half-applied
    # v50 re-runs.  What each part does:
    #   - vendors (S079): one row per outside firm, shared by all sites; the name unique in the table's
    #     case-insensitive collation.  people.vendor_id links a contractor's Team record to its firm; chk_people_vendor
    #     keeps it to contractors (NULL on every existing row, and a NULL foreign key is not checked);
    #   - contracts (S080, S084, S085, S087): one row per contract, company-wide; its sites are its machines' sites,
    #     derived on read.  Status is computed from the dates; never deleted (set inactive, ISO 9001 § 7.5).  The
    #     reminder markers hold the To date each reminder was queued for (S084).  One renewal per contract
    #     (uq_contracts_renewal_of; many NULLs pass).  ix_contracts_active_to serves the list and the daily scan;
    #   - contract_equipment (S081): one row per contract and node, any level and any site; price per machine before
    #     GST, read and written only with contract:read_senior; the history's two kinds at the end of the ENUM;
    #   - equipment_documents.contract_id (S083): the sixth owner, the owner CHECK dropped and added with six owners
    #     (every existing row has one of the five).  No ON DELETE: a contract is never deleted.
    # The site's foreign key is dropped before its column (a column under a foreign key cannot be dropped), and
    # ix_contracts_site by name (dropping only the column would leave (active, to_date) under that name).
    # Rollback: release v0.1.14 (v41) never reads vendors, contracts, contract_equipment, people.vendor_id or
    # equipment_documents.contract_id; on it a PUT {employment: "direct"} of a linked person breaks chk_people_vendor
    # (a 500), so unlink such people before a rollback.
    (50, "Vendors and contracts, company-wide (S079–S085, S087)", [
        """CREATE TABLE IF NOT EXISTS vendors (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            name        VARCHAR(100) NOT NULL,
            phone       VARCHAR(20) NULL,
            note        VARCHAR(255) NULL,
            active      TINYINT(1) NOT NULL DEFAULT 1,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL,
            updated_at  DATETIME NULL,
            updated_by  VARCHAR(100) NULL,
            CONSTRAINT uq_vendors_name UNIQUE (name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """ALTER TABLE people
            ADD COLUMN IF NOT EXISTS vendor_id INT NULL AFTER employment,
            ADD KEY IF NOT EXISTS ix_people_vendor (vendor_id),
            ADD CONSTRAINT fk_people_vendor
                FOREIGN KEY IF NOT EXISTS (vendor_id) REFERENCES vendors (id)""",
        """ALTER TABLE people ADD CONSTRAINT IF NOT EXISTS chk_people_vendor
            CHECK (vendor_id IS NULL OR employment = 'contractor')""",
        """CREATE TABLE IF NOT EXISTS contracts (
            id                        INT AUTO_INCREMENT PRIMARY KEY,
            vendor_id                 INT NOT NULL,
            contract_type             ENUM('warranty', 'amc', 'cmc', 'on_call') NOT NULL,
            title                     VARCHAR(100) NOT NULL,
            contract_number           VARCHAR(60) NULL,
            from_date                 DATE NOT NULL,
            to_date                   DATE NOT NULL,
            first_reminder_for        DATE NULL,
            second_reminder_for       DATE NULL,
            covers_labour             TINYINT(1) NOT NULL DEFAULT 0,
            covers_parts              TINYINT(1) NOT NULL DEFAULT 0,
            covers_consumables        TINYINT(1) NOT NULL DEFAULT 0,
            covers_breakdown_calls    TINYINT(1) NOT NULL DEFAULT 0,
            breakdown_calls_per_year  SMALLINT NULL,
            covered_text              VARCHAR(1000) NULL,
            not_covered_text          VARCHAR(1000) NULL,
            pm_visits_per_year        TINYINT NULL,
            response_hours            SMALLINT NULL,
            only_vendor_repairs       TINYINT(1) NOT NULL DEFAULT 0,
            callout_number            VARCHAR(20) NULL,
            cost_note                 VARCHAR(255) NULL,
            notes                     VARCHAR(1000) NULL,
            renewal_of_id             INT NULL,
            active                    TINYINT(1) NOT NULL DEFAULT 1,
            created_at                DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by                VARCHAR(100) NOT NULL,
            updated_at                DATETIME NULL,
            updated_by                VARCHAR(100) NULL,
            KEY ix_contracts_active_to (active, to_date),
            KEY ix_contracts_vendor (vendor_id),
            UNIQUE KEY uq_contracts_renewal_of (renewal_of_id),
            CONSTRAINT fk_contracts_vendor FOREIGN KEY (vendor_id) REFERENCES vendors (id),
            CONSTRAINT fk_contracts_renewal_of FOREIGN KEY (renewal_of_id) REFERENCES contracts (id),
            CONSTRAINT chk_contracts_period CHECK (to_date >= from_date),
            CONSTRAINT chk_contracts_pm_visits CHECK (pm_visits_per_year IS NULL OR pm_visits_per_year BETWEEN 0 AND 52),
            CONSTRAINT chk_contracts_response CHECK (response_hours IS NULL OR response_hours BETWEEN 1 AND 720),
            CONSTRAINT chk_contracts_breakdown_calls CHECK (breakdown_calls_per_year IS NULL
                OR (covers_breakdown_calls = 1 AND breakdown_calls_per_year BETWEEN 1 AND 365))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        # Convergence of a dev or test contracts table built by v43–v47 (no-ops on the table above)
        """ALTER TABLE contracts
            ADD COLUMN IF NOT EXISTS first_reminder_for DATE NULL AFTER to_date,
            ADD COLUMN IF NOT EXISTS second_reminder_for DATE NULL AFTER first_reminder_for""",
        "ALTER TABLE contracts ADD UNIQUE KEY IF NOT EXISTS uq_contracts_renewal_of (renewal_of_id)",
        "ALTER TABLE contracts DROP INDEX IF EXISTS ix_contracts_renewal_of",
        "ALTER TABLE contracts DROP FOREIGN KEY IF EXISTS fk_contracts_site",
        "ALTER TABLE contracts ADD KEY IF NOT EXISTS ix_contracts_active_to (active, to_date)",
        "ALTER TABLE contracts DROP INDEX IF EXISTS ix_contracts_site",
        "ALTER TABLE contracts DROP COLUMN IF EXISTS site_id",
        """CREATE TABLE IF NOT EXISTS contract_equipment (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            contract_id   INT NOT NULL,
            equipment_id  INT NOT NULL,
            price         DECIMAL(10,2) NULL,
            created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by    VARCHAR(100) NOT NULL,
            updated_at    DATETIME NULL,
            updated_by    VARCHAR(100) NULL,
            CONSTRAINT uq_contract_equipment UNIQUE (contract_id, equipment_id),
            KEY ix_contract_equipment_equipment (equipment_id),
            CONSTRAINT fk_contract_equipment_contract FOREIGN KEY (contract_id) REFERENCES contracts (id),
            CONSTRAINT fk_contract_equipment_equipment FOREIGN KEY (equipment_id) REFERENCES equipment (id),
            CONSTRAINT chk_contract_equipment_price CHECK (price IS NULL OR price >= 0)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """ALTER TABLE equipment_events MODIFY event
            ENUM('created','moved_unit','moved_parent','lifecycle','criticality','class','type','model',
                 'meter_added','meter_removed','meter_limits','property','contract_added','contract_removed')
            NOT NULL""",
        """ALTER TABLE equipment_documents
            ADD COLUMN IF NOT EXISTS contract_id INT NULL AFTER procedure_id,
            ADD KEY IF NOT EXISTS ix_equipment_documents_contract (contract_id, removed_at),
            ADD CONSTRAINT fk_equipment_documents_contract
                FOREIGN KEY IF NOT EXISTS (contract_id) REFERENCES contracts (id)""",
        "ALTER TABLE equipment_documents DROP CONSTRAINT IF EXISTS chk_equipment_documents_owner",
        """ALTER TABLE equipment_documents ADD CONSTRAINT IF NOT EXISTS chk_equipment_documents_owner
            CHECK ((equipment_id IS NOT NULL) + (model_id IS NOT NULL) + (ticket_id IS NOT NULL)
                   + (action_id IS NOT NULL) + (procedure_id IS NOT NULL) + (contract_id IS NOT NULL) = 1)""",
    ]),
]

LATEST_VERSION = _MIGRATIONS[-1][0]


# ---------------------------------------------------------------------------
# Preconditions — checked for every pending version before any is applied
# ---------------------------------------------------------------------------

def _v41_squash_check(cur):
    """The squashed v41's precondition (S088 § 5.2) -> None, or the refusal Settings › Database shows.

    v41 is pending, so any version recorded is another one: a database between v20 and v40, or
    a v13 one.  The squashed v41 would skip its existing tables (CREATE TABLE IF NOT EXISTS) and
    the later versions would run on a shape they do not expect, so it is refused.  An absent or
    empty db_version passes: an empty database, or a half-applied v41 (its first statement
    created db_version, nothing is recorded yet), which then re-runs.  Read through the engine's
    own reader, so the check and the engine agree on what is recorded."""
    applied = _get_applied_versions(cur)
    if not applied:
        return None
    return (f"This database is at schema v{max(applied)}, older than v41, and this release cannot update it. "
            "A dev or test database: drop it and start the app again. "
            "A restored production database: deploy release v0.1.14 first, which brings it to v41. — S088 § 5.2")


# version -> a function of the cursor that returns None (go) or why the version cannot run yet
_PRECONDITIONS = {41: _v41_squash_check}


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
