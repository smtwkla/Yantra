"""Migrations v1–v13 as they stood at ae3841f (S018), before S025 squashed them into v20.

FROZEN — never edit.  A test fixture only: test_migration_v20.py builds a database with
these to prove that v20 builds the same schema (equivalence), and that a database at v5 —
production's v0.1.3 — reaches it (the production path).  v1–v5 here are byte-identical to
v0.1.3's, so MIGRATIONS_V13[:5] is production's schema.
"""

MIGRATIONS_V13 = [
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
    # S013.  access_log is append-only by design (ISO 27001 A.8.15): no foreign keys, so it
    # keeps its rows when people or logins change; only the scheduled purge deletes, by age.
    # ux_access_log_sighting keeps one row per sighting key per IST day across every
    # Gunicorn worker (A1: edited in place, v10 was applied only to disposable dev/test DBs).
    # The default internal ranges are the RFC 1918 private ranges
    # (network_core.DEFAULT_INTERNAL_NETWORKS, repeated here: a migration is frozen text);
    # INSERT IGNORE keeps a value already there.
    (10, "Access log, task queue, internal networks", [
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
        """INSERT IGNORE INTO app_settings (setting_key, setting_value)
            VALUES ('internal_networks', '10.0.0.0/8,172.16.0.0/12,192.168.0.0/16')""",
    ]),
    # Failure codes (S016), ISO 14224 § 9 and Annex B: failure modes (what is seen; one class,
    # or General when class_id is NULL), failure causes (in Table B.3's five groups; the ENUM's
    # order is the groups' order, so ORDER BY cause_group lists them design … misc) and
    # maintenance actions (Table B.5).  Three tables, so a ticket's cause column can only hold
    # a cause.  Mode labels are unique per picker (a class's modes plus the General ones):
    # checked by the API, an index can't cross the NULL class (S016 § 5.1).
    # The seed rows are ISO's, trimmed; created_by 'migration-v11' tells them apart.  INSERT
    # IGNORE is keyed on the unique code, so a re-run keeps an engineer's edit of a seed row.
    # Every statement is safe to run twice, as in v5.
    (11, "Failure modes, causes, maintenance actions", [
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
    # Tickets (S017): one record per problem found on equipment, a breakdown (critical) or a
    # defect (degraded, initial) — EN 13460's work request, ISO 14224's failure record.
    # equipment_id is always the machine; component_id the component-unit or component it
    # was raised on, when lower.  unit_id is the machine's unit at raise, kept when it moves.
    # The intensity ENUM's order puts critical first in ORDER BY; state holds S018's whole set
    # so S018 adds no ENUM change.  ticket_events is the timeline S018's figures come from.
    # Ticket photos are a third owner of equipment_documents: the v9 owner CHECK is dropped and
    # re-added under the same name, so a re-run of v9 (its ADD … IF NOT EXISTS) stays a no-op
    # instead of bringing the two-owner rule back beside this one (S017 BR2-01).
    # Every statement is safe to run twice, as in v5.
    (12, "Tickets, ticket events, ticket photos", [
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
            CONSTRAINT fk_tickets_equipment FOREIGN KEY (equipment_id) REFERENCES equipment (id),
            CONSTRAINT fk_tickets_component FOREIGN KEY (component_id) REFERENCES equipment (id),
            CONSTRAINT fk_tickets_unit FOREIGN KEY (unit_id) REFERENCES units (id),
            CONSTRAINT fk_tickets_failure_mode FOREIGN KEY (failure_mode_id) REFERENCES failure_modes (id),
            CONSTRAINT fk_tickets_reported_by FOREIGN KEY (reported_by_id) REFERENCES people (id)
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
        "ALTER TABLE equipment_documents ADD COLUMN IF NOT EXISTS ticket_id INT NULL AFTER model_id",
        "ALTER TABLE equipment_documents ADD INDEX IF NOT EXISTS ix_equipment_documents_ticket (ticket_id, removed_at)",
        """ALTER TABLE equipment_documents ADD CONSTRAINT fk_equipment_documents_ticket FOREIGN KEY IF NOT EXISTS
            (ticket_id) REFERENCES tickets (id)""",
        "ALTER TABLE equipment_documents DROP CONSTRAINT IF EXISTS chk_equipment_documents_owner",
        """ALTER TABLE equipment_documents ADD CONSTRAINT IF NOT EXISTS chk_equipment_documents_owner
            CHECK ((equipment_id IS NOT NULL) + (model_id IS NOT NULL) + (ticket_id IS NOT NULL) = 1)""",
    ]),
    # Ticket work (S018): the close's cause and action (S016 lists; NULL action on a ticket closed
    # as not a fault), the not-a-fault flag, the repeat link (a new ticket on the same machine
    # after a restoration that did not hold), the assignees and the labour rows (person, trade
    # worked, date, minutes: ISO 14224 man-hours per discipline).  The figures (response,
    # repair, downtime) are computed from ticket_events, never stored.
    # Every statement is safe to run twice, as in v5.
    (13, "Ticket work: cause, action, not a fault, repeat, assignees, labour", [
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS cause_id INT NULL AFTER failure_mode_id",
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS action_id INT NULL AFTER cause_id",
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS not_a_fault TINYINT(1) NOT NULL DEFAULT 0 AFTER action_id",
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS repeat_of_id INT NULL AFTER not_a_fault",
        "ALTER TABLE tickets ADD INDEX IF NOT EXISTS ix_tickets_repeat_of (repeat_of_id)",
        """ALTER TABLE tickets ADD CONSTRAINT fk_tickets_cause FOREIGN KEY IF NOT EXISTS
            (cause_id) REFERENCES failure_causes (id)""",
        """ALTER TABLE tickets ADD CONSTRAINT fk_tickets_action FOREIGN KEY IF NOT EXISTS
            (action_id) REFERENCES maintenance_actions (id)""",
        """ALTER TABLE tickets ADD CONSTRAINT fk_tickets_repeat_of FOREIGN KEY IF NOT EXISTS
            (repeat_of_id) REFERENCES tickets (id)""",
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
    ]),
]
