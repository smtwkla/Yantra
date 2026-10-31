"""Migrations v42–v47 as they stood at f5bbb38 (S079–S085), before S087 squashed them into v50.

FROZEN — never edit.  A test fixture only.  v42–v47 were never released: production went from
v41 (release v0.1.14) straight to v50.  The dev and test databases hold some or all of them, so
test_migration_v50.py builds those shapes with these texts and proves that v50 converges them to
the schema a fresh database gets (S087 § 4.1, § 8.1).

It holds no precondition functions: none of v42–v47 had one.

The rule: build on the squashed v41 first (tests.migration_helpers.SQUASHED), then these, in
one list or one call after it; never these on an empty database (v42 alters people, which v41
creates).
"""

MIGRATIONS_V42_V47 = [
    # S079 — the vendor master (docs/steps/S079-vendor-master/1-brief.md § 4.1, R02.9): one row per
    # outside firm the plant buys maintenance from, shared by all sites like manufacturers.  The name
    # is unique in the table's case-insensitive collation; the API collapses inner spaces first
    # (ISO 8000: one spelling per firm).  people.vendor_id links a contractor's Team record to its
    # firm; chk_people_vendor keeps it to contractors.  No seed rows and no links: the engineer adds
    # the vendors and links people by hand (no guess from a name).  No precondition: a new table, a
    # nullable column (NULL on every production row, and a NULL foreign key is not checked) and a
    # CHECK every existing row meets; nothing is converted or dropped.  IF NOT EXISTS on the table,
    # the column, the key, the foreign key and the CHECK make a half-applied v42 re-run.  Rollback:
    # a release before v42 reads people with SELECT * and returns vendor_id unused; it never reads
    # vendors.  On it, a PUT {employment: "direct"} of a linked person breaks the CHECK (a 500), so
    # unlink such people before a rollback.
    (42, "Vendor master and a contractor's vendor (S079)", [
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
    ]),
    # Vendor contracts (S080, R02.1): one row per contract, at one site (Q1.5 a), with a vendor
    # from the vendors master (S079, v42).  Status is computed from the dates, never stored.  Never
    # deleted: one entered by mistake is set inactive (ISO 9001 § 7.5).  The price is per machine and
    # lands with R02.2 (D8); this table holds only the cost note.  renewal_of_id is filled by R02.4.
    # One statement, so v43 is never half-applied; a new table, so no precondition.  Rollback: a
    # release before v43 never reads contracts.
    (43, "Vendor contracts (S080)", [
        """CREATE TABLE IF NOT EXISTS contracts (
            id                        INT AUTO_INCREMENT PRIMARY KEY,
            site_id                   INT NOT NULL,
            vendor_id                 INT NOT NULL,
            contract_type             ENUM('warranty', 'amc', 'cmc', 'on_call') NOT NULL,
            title                     VARCHAR(100) NOT NULL,
            contract_number           VARCHAR(60) NULL,
            from_date                 DATE NOT NULL,
            to_date                   DATE NOT NULL,
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
            KEY ix_contracts_site (site_id, active, to_date),
            KEY ix_contracts_vendor (vendor_id),
            KEY ix_contracts_renewal_of (renewal_of_id),
            CONSTRAINT fk_contracts_site FOREIGN KEY (site_id) REFERENCES sites (id),
            CONSTRAINT fk_contracts_vendor FOREIGN KEY (vendor_id) REFERENCES vendors (id),
            CONSTRAINT fk_contracts_renewal_of FOREIGN KEY (renewal_of_id) REFERENCES contracts (id),
            CONSTRAINT chk_contracts_period CHECK (to_date >= from_date),
            CONSTRAINT chk_contracts_pm_visits CHECK (pm_visits_per_year IS NULL OR pm_visits_per_year BETWEEN 0 AND 52),
            CONSTRAINT chk_contracts_response CHECK (response_hours IS NULL OR response_hours BETWEEN 1 AND 720),
            CONSTRAINT chk_contracts_breakdown_calls CHECK (breakdown_calls_per_year IS NULL
                OR (covers_breakdown_calls = 1 AND breakdown_calls_per_year BETWEEN 1 AND 365))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    ]),
    # The machines a contract covers (S081, R02.2): one row per contract and node, any level (Q2.1 a), a
    # node of the contract's site when added.  A node may be on several contracts (Q2.2 a).  price: the
    # vendor's price for this machine for the contract period, in rupees before GST (D8), NULL = not
    # entered; read and written only with contract:read_senior.  The contract's total is the sum, never
    # stored.  A line removed by mistake is deleted; the machine's history keeps the add and the remove
    # (equipment_events, the two new kinds at the end of the ENUM, as v30 and v33 added theirs).  A new
    # table and an ENUM widened at its end convert no existing row, so no precondition; a re-run is a no-op.
    # Rollback: a release before v44 never reads contract_equipment; a contract_added line shows as its
    # raw name in the history.
    (44, "Machines on a contract (S081)", [
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
    ]),
    # S083 — a contract's documents and photos (docs/steps/S083-contract-documents/1-brief.md § 4.1, R02.3): the
    # sixth owner of the documents store.  The owner CHECK is dropped and added again with its name, as v38 and v41
    # did; every existing row has one of the five owners and contract_id NULL, so it meets the new CHECK.  No
    # precondition: a nullable column, a key, a foreign key no row uses yet and a CHECK every row meets; nothing is
    # converted or dropped.  IF NOT EXISTS on the column, the key, the foreign key and the CHECK make a half-applied
    # v45 (the CHECK dropped, not added) re-run.  The foreign key has no ON DELETE: a contract is never deleted.
    # Rollback: a release before v45 never reads contract_id (its queries name their columns and its removed-list
    # branches join their own owner), and its uploads meet v45's CHECK.
    (45, "Contract documents (S083)", [
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
    # S084 — contract reminders (docs/steps/S084-contract-reminders/1-brief.md § 4.1, R02.5): the To date each
    # reminder was queued for, so the daily contract_reminder_scan sends each once per To date (as v40's markers).
    # NULL = never sent; a changed To date differs from both, so the reminders are sent again.  No index: tens of
    # contracts, read once a day.  No precondition: two nullable columns, no existing value changes, and
    # production holds no contract yet (v43 ships in the same release).  ADD COLUMN IF NOT EXISTS makes a re-run
    # safe.  Rollback: a release before v46 never reads the columns and has no scan.
    (46, "Contract reminders sent once (S084)", [
        """ALTER TABLE contracts
            ADD COLUMN IF NOT EXISTS first_reminder_for DATE NULL AFTER to_date,
            ADD COLUMN IF NOT EXISTS second_reminder_for DATE NULL AFTER first_reminder_for""",
    ]),
    # S085 — contract renewal (docs/steps/S085-contract-renewal/1-brief.md § 4.1, R02.4): one renewal per contract.
    # A renewal set inactive keeps its place; it is set active again to renew with it.  The unique key serves
    # fk_contracts_renewal_of and S084's renewed check, so the plain key goes; the unique key comes first, so the
    # foreign key always has an index on its column.  Many NULLs pass (a contract that renews nothing).  No
    # precondition: nothing wrote renewal_of_id before S085, and production holds no contract before v46.  Two
    # statements, each safe to run twice: a half-applied v47 re-runs.  Rollback: a release before v47 reads
    # renewal_of_id only in S084's renewed check, which works with either key.
    (47, "One renewal per contract (S085)", [
        "ALTER TABLE contracts ADD UNIQUE KEY IF NOT EXISTS uq_contracts_renewal_of (renewal_of_id)",
        "ALTER TABLE contracts DROP INDEX IF EXISTS ix_contracts_renewal_of",
    ]),
]
