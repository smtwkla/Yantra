"""Migrations v51–v56 as they stood before S104 (S096–S102, held, never released) squashed them into v57.

FROZEN — never edit.  A test fixture only.  v51–v56 were never released: production went from v50 straight to
v57.  The dev and test databases hold some or all of them, so test_migration_v57.py builds those shapes with these
texts and proves that v57 drops the six PM tables and makes the final shape a fresh database gets (S104 § 4.1,
§ 8.1).

It holds no precondition functions: none of v51–v56 had one.

The rule: build on v41 and v50 first (local_db._MIGRATIONS up to v50), then these, in one list or one call after
it; never these on an empty database (v51 references equipment, people and meter_types, which v41 creates).
"""

MIGRATIONS_V51_V56 = [
    # PM plans (S096, R03.2): the planned work on one node of the equipment tree, written by an engineer.
    # trigger_kind takes pm_schedule_core.KINDS (S095), calendar_unit its CALENDAR_UNITS (test_migration_v51
    # pins both); the calendar columns are set exactly for calendar and both, the meter columns exactly for
    # meter and both, none for before_use (R03.13).  The meter is a counter of the node or of a node above it
    # (meter_equipment_id names which).  last_done_on / last_done_meter: the engineer's seed, when the work
    # was last done before Yantra.  Never deleted: a plan entered by mistake or no longer wanted is set
    # inactive (ISO 9001 § 7.5.3); a removed item is set inactive too, so R03.4's results and R03.17's
    # reference photos can name an item for ever.  New tables only: no precondition.
    (51, "PM plans and their items (S096)", [
        """CREATE TABLE IF NOT EXISTS pm_plans (
            id                  INT AUTO_INCREMENT PRIMARY KEY,
            equipment_id        INT NOT NULL,
            title               VARCHAR(100) NOT NULL,
            performer           ENUM('maintenance','operator') NOT NULL DEFAULT 'maintenance',
            assignee_id         INT NULL,
            needs_verification  TINYINT(1) NOT NULL DEFAULT 1,
            trigger_kind        ENUM('calendar','meter','both','before_use') NOT NULL,
            calendar_every      SMALLINT NULL,
            calendar_unit       ENUM('day','week','month','year') NULL,
            meter_equipment_id  INT NULL,
            meter_type_id       INT NULL,
            meter_every         DECIMAL(14,3) NULL,
            last_done_on        DATE NULL,
            last_done_meter     DECIMAL(14,3) NULL,
            active              TINYINT(1) NOT NULL DEFAULT 1,
            created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by          VARCHAR(100) NOT NULL,
            updated_at          DATETIME NULL,
            updated_by          VARCHAR(100) NULL,
            CONSTRAINT uq_pm_plans_title UNIQUE (equipment_id, title),
            CONSTRAINT fk_pm_plans_equipment FOREIGN KEY (equipment_id) REFERENCES equipment (id),
            CONSTRAINT fk_pm_plans_assignee FOREIGN KEY (assignee_id) REFERENCES people (id),
            CONSTRAINT fk_pm_plans_meter_equipment FOREIGN KEY (meter_equipment_id) REFERENCES equipment (id),
            CONSTRAINT fk_pm_plans_meter_type FOREIGN KEY (meter_type_id) REFERENCES meter_types (id),
            CONSTRAINT chk_pm_plans_calendar CHECK (
                (calendar_every IS NOT NULL) = (trigger_kind IN ('calendar','both'))
                AND (calendar_unit IS NOT NULL) = (calendar_every IS NOT NULL)
                AND (calendar_every IS NULL OR calendar_every BETWEEN 1 AND 3650)),
            CONSTRAINT chk_pm_plans_meter CHECK (
                (meter_type_id IS NOT NULL) = (trigger_kind IN ('meter','both'))
                AND (meter_equipment_id IS NOT NULL) = (meter_type_id IS NOT NULL)
                AND (meter_every IS NOT NULL) = (meter_type_id IS NOT NULL)
                AND (meter_every IS NULL OR meter_every > 0)),
            CONSTRAINT chk_pm_plans_seed CHECK (
                (last_done_meter IS NULL OR (meter_type_id IS NOT NULL AND last_done_meter >= 0))
                AND (last_done_on IS NULL OR trigger_kind <> 'before_use')),
            CONSTRAINT chk_pm_plans_assignee CHECK (assignee_id IS NULL OR performer = 'maintenance')
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS pm_plan_items (
            id                  INT AUTO_INCREMENT PRIMARY KEY,
            plan_id             INT NOT NULL,
            position            SMALLINT NOT NULL,
            item_type           ENUM('task','check','reading') NOT NULL,
            text                VARCHAR(200) NOT NULL,
            help_text           VARCHAR(500) NULL,
            photo               ENUM('none','optional','required') NOT NULL DEFAULT 'optional',
            unit                VARCHAR(20) NULL,
            min_value           DECIMAL(14,3) NULL,
            max_value           DECIMAL(14,3) NULL,
            meter_equipment_id  INT NULL,
            meter_type_id       INT NULL,
            active              TINYINT(1) NOT NULL DEFAULT 1,
            created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by          VARCHAR(100) NOT NULL,
            updated_at          DATETIME NULL,
            updated_by          VARCHAR(100) NULL,
            INDEX ix_pm_plan_items_plan (plan_id, active, position),
            CONSTRAINT fk_pm_plan_items_plan FOREIGN KEY (plan_id) REFERENCES pm_plans (id),
            CONSTRAINT fk_pm_plan_items_meter_equipment FOREIGN KEY (meter_equipment_id) REFERENCES equipment (id),
            CONSTRAINT fk_pm_plan_items_meter_type FOREIGN KEY (meter_type_id) REFERENCES meter_types (id),
            CONSTRAINT chk_pm_plan_items_position CHECK (position >= 1),
            CONSTRAINT chk_pm_plan_items_reading CHECK (item_type = 'reading'
                OR (unit IS NULL AND min_value IS NULL AND max_value IS NULL AND meter_type_id IS NULL)),
            CONSTRAINT chk_pm_plan_items_meter CHECK (
                (meter_equipment_id IS NOT NULL) = (meter_type_id IS NOT NULL)
                AND (meter_type_id IS NULL OR unit IS NULL)),
            CONSTRAINT chk_pm_plan_items_limits CHECK (
                min_value IS NULL OR max_value IS NULL OR min_value <= max_value)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    ]),
    # PM jobs (S097, R03.3): one occurrence of a plan, made when the plan enters its Upcoming window
    # (pm_schedule_core), against the plan's node (ISO 14224: one record per item per event).  The state
    # covers the whole life (Plan § 4.3): due -> in_progress -> done -> verified, skipped (R03.9), cancelled
    # (its plan deactivated or its machine scrapped while not started).  due_on .. meter_window are copies of
    # pm_schedule_core.Due, refreshed by the daily run and the plan save while the job is due; meter_offset
    # carries the meter's usage across a counter reset.  done_at, done_meter, timeliness are written at Mark
    # done (R03.4) and are the record.  open_plan_id: the plan while the job is open, else NULL; its unique key
    # keeps one open job per plan (MariaDB has no partial index).  Never deleted.  pm_job_events is the job's
    # timeline (as ticket_events): created, due_changed (the new due point; the line before holds the old one),
    # assignee_changed (person_id the new assignee, NULL = no one), cancelled (remark: why); created_by is the
    # user, or pm_generate for the daily run.  New tables only: no precondition.
    (52, "PM jobs and their timeline (S097)", [
        """CREATE TABLE IF NOT EXISTS pm_jobs (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            serial          VARCHAR(16) NOT NULL,
            plan_id         INT NOT NULL,
            equipment_id    INT NOT NULL,
            state           ENUM('due','in_progress','done','verified','skipped','cancelled') NOT NULL DEFAULT 'due',
            created_why     ENUM('calendar','meter') NOT NULL,
            due_on          DATE NULL,
            due_meter       DECIMAL(14,3) NULL,
            grace_days      SMALLINT NULL,
            upcoming_days   SMALLINT NULL,
            meter_window    DECIMAL(14,3) NULL,
            meter_offset    DECIMAL(14,3) NOT NULL DEFAULT 0,
            assignee_id     INT NULL,
            done_at         DATETIME NULL,
            done_meter      DECIMAL(14,3) NULL,
            timeliness      ENUM('on_time','late') NULL,
            open_plan_id    INT AS (CASE WHEN state IN ('due','in_progress') THEN plan_id END) PERSISTENT,
            created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by      VARCHAR(100) NOT NULL,
            updated_at      DATETIME NULL,
            updated_by      VARCHAR(100) NULL,
            CONSTRAINT uq_pm_jobs_serial UNIQUE (serial),
            CONSTRAINT uq_pm_jobs_open_plan UNIQUE (open_plan_id),
            INDEX ix_pm_jobs_plan (plan_id, state, done_at),
            INDEX ix_pm_jobs_state (state, due_on),
            INDEX ix_pm_jobs_assignee (assignee_id, state),
            CONSTRAINT fk_pm_jobs_plan FOREIGN KEY (plan_id) REFERENCES pm_plans (id),
            CONSTRAINT fk_pm_jobs_equipment FOREIGN KEY (equipment_id) REFERENCES equipment (id),
            CONSTRAINT fk_pm_jobs_assignee FOREIGN KEY (assignee_id) REFERENCES people (id),
            CONSTRAINT chk_pm_jobs_windows CHECK (
                (due_on IS NULL) = (grace_days IS NULL) AND (grace_days IS NULL) = (upcoming_days IS NULL)
                AND (due_on IS NOT NULL OR meter_window IS NOT NULL)
                AND (due_meter IS NULL OR meter_window IS NOT NULL)
                AND meter_offset >= 0),
            CONSTRAINT chk_pm_jobs_done CHECK (
                (state NOT IN ('done','verified') OR done_at IS NOT NULL)
                AND (done_at IS NULL OR state IN ('done','verified','skipped'))
                AND (done_meter IS NULL OR done_at IS NOT NULL)
                AND (timeliness IS NULL OR state IN ('done','verified')))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS pm_job_events (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            job_id          INT NOT NULL,
            event           VARCHAR(30) NOT NULL,
            from_state      VARCHAR(20) NULL,
            to_state        VARCHAR(20) NULL,
            occurred_at     DATETIME NOT NULL,
            person_id       INT NULL,
            due_on          DATE NULL,
            due_meter       DECIMAL(14,3) NULL,
            remark          VARCHAR(1000) NULL,
            created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by      VARCHAR(100) NOT NULL,
            INDEX ix_pm_job_events_job (job_id, occurred_at, id),
            CONSTRAINT fk_pm_job_events_job FOREIGN KEY (job_id) REFERENCES pm_jobs (id),
            CONSTRAINT fk_pm_job_events_person FOREIGN KEY (person_id) REFERENCES people (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    ]),

    # --- PM job results (S098, R03.4) -------------------------------------------------------
    # Who performed a job (any person with a membership at the site, also one without a login:
    # recorded on behalf, Plan § 4.3) and when it started; both set at Start, so a job in progress
    # or done has both.  done_at is v52's, written at Mark done.  pm_job_results: a copy of the
    # plan's active items at Start (Plan § 4.3a: a plan edit never rewrites a job's record) and the
    # result of each: a check ok / not_ok / na, a task done / not_done, a reading a value (judged by
    # the copied limits: limit_state) or na.  A reading that names a meter logs its value as a meter
    # reading (source pm); reading_id names it.  Rows are never deleted; a result changes only while
    # its job is in progress.  Existing pm_jobs rows are due or cancelled with the new columns NULL,
    # which the CHECK allows: no precondition.
    (53, "PM job results; who performed a job and when it started (S098)", [
        """ALTER TABLE pm_jobs
            ADD COLUMN IF NOT EXISTS performed_by_id INT NULL AFTER assignee_id,
            ADD COLUMN IF NOT EXISTS started_at DATETIME NULL AFTER performed_by_id,
            ADD KEY IF NOT EXISTS ix_pm_jobs_performer (performed_by_id, state),
            ADD CONSTRAINT fk_pm_jobs_performer
                FOREIGN KEY IF NOT EXISTS (performed_by_id) REFERENCES people (id)""",
        """ALTER TABLE pm_jobs ADD CONSTRAINT IF NOT EXISTS chk_pm_jobs_started CHECK (
            (state NOT IN ('in_progress','done','verified') OR (started_at IS NOT NULL AND performed_by_id IS NOT NULL))
            AND (started_at IS NOT NULL OR performed_by_id IS NULL)
            AND (done_at IS NULL OR started_at IS NULL OR done_at >= started_at))""",
        """CREATE TABLE IF NOT EXISTS pm_job_results (
            id                  INT AUTO_INCREMENT PRIMARY KEY,
            job_id              INT NOT NULL,
            plan_item_id        INT NOT NULL,
            position            SMALLINT NOT NULL,
            item_type           ENUM('task','check','reading') NOT NULL,
            text                VARCHAR(200) NOT NULL,
            help_text           VARCHAR(500) NULL,
            photo               ENUM('none','optional','required') NOT NULL,
            unit                VARCHAR(20) NULL,
            min_value           DECIMAL(14,3) NULL,
            max_value           DECIMAL(14,3) NULL,
            meter_equipment_id  INT NULL,
            meter_type_id       INT NULL,
            outcome             ENUM('ok','not_ok','na','done','not_done') NULL,
            value               DECIMAL(14,3) NULL,
            limit_state         ENUM('low','high') NULL,
            remark              VARCHAR(500) NULL,
            reading_id          INT NULL,
            filled_at           DATETIME NULL,
            filled_by           VARCHAR(100) NULL,
            created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by          VARCHAR(100) NOT NULL,
            CONSTRAINT uq_pm_job_results_item UNIQUE (job_id, plan_item_id),
            CONSTRAINT uq_pm_job_results_position UNIQUE (job_id, position),
            CONSTRAINT fk_pm_job_results_job FOREIGN KEY (job_id) REFERENCES pm_jobs (id),
            CONSTRAINT fk_pm_job_results_item FOREIGN KEY (plan_item_id) REFERENCES pm_plan_items (id),
            CONSTRAINT fk_pm_job_results_meter_equipment FOREIGN KEY (meter_equipment_id) REFERENCES equipment (id),
            CONSTRAINT fk_pm_job_results_meter_type FOREIGN KEY (meter_type_id) REFERENCES meter_types (id),
            CONSTRAINT fk_pm_job_results_reading FOREIGN KEY (reading_id) REFERENCES meter_readings (id),
            CONSTRAINT chk_pm_job_results_outcome CHECK (
                (item_type = 'check' AND (outcome IS NULL OR outcome IN ('ok','not_ok','na')) AND value IS NULL)
                OR (item_type = 'task' AND (outcome IS NULL OR outcome IN ('done','not_done')) AND value IS NULL)
                OR (item_type = 'reading' AND (outcome IS NULL OR outcome = 'na')
                    AND (outcome IS NULL OR value IS NULL))),
            CONSTRAINT chk_pm_job_results_reading CHECK (
                (limit_state IS NULL OR value IS NOT NULL)
                AND (reading_id IS NULL OR (value IS NOT NULL AND meter_type_id IS NOT NULL))
                AND ((meter_equipment_id IS NOT NULL) = (meter_type_id IS NOT NULL))),
            CONSTRAINT chk_pm_job_results_filled CHECK (
                (filled_at IS NULL) = (outcome IS NULL AND value IS NULL)
                AND (filled_at IS NULL) = (filled_by IS NULL))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    ]),
    # PM jobs (S099, R03.5): whether a finished job waits for an engineer's verification, copied from
    # its plan's needs_verification at Mark done, so a later change of the plan's setting never moves a
    # finished job in or out of the To verify list (R03 Q5.1 a).  1: the job waits at done until it is
    # verified or sent back; 0: done is final.  NULL while the job is not done, and on a job done before
    # S099 (final, as S098 left it).  A send-back clears it with done_at; Mark done copies it again.
    # Existing rows get NULL, which the CHECK allows (nobody wrote verified before S099): no precondition.
    # <=> (not =): a CHECK passes when its result is NULL, so "= 1" would let a verified job with NULL through.
    (54, "PM jobs: whether a done job waits for verification (S099)", [
        """ALTER TABLE pm_jobs
            ADD COLUMN IF NOT EXISTS needs_verification TINYINT(1) NULL AFTER timeliness""",
        """ALTER TABLE pm_jobs ADD CONSTRAINT IF NOT EXISTS chk_pm_jobs_verification CHECK (
            (needs_verification IS NULL OR state IN ('done','verified'))
            AND (state <> 'verified' OR needs_verification <=> 1))""",
    ]),
    # PM jobs (S101, R03.9): the engineer's reschedule of an open job.  rescheduled_on replaces the
    # computed due date and rescheduled_meter the computed due meter value (pm_schedule_core.next_due's
    # override; the windows stay the computed interval's).  NULL: not moved.  While set, due_on (or
    # due_meter) equals it: the daily run and a plan save pass it to next_due, so the copy keeps it.  A
    # change of the plan's schedule clears it.  Kept on a done or skipped job as the record that it was
    # moved; the moves themselves are the job's 'rescheduled' events.  A skipped job (R03.9) has
    # done_at (the skip time) and done_meter, which v52's chk_pm_jobs_done already allows.  Existing
    # rows get NULL, which the CHECK allows: no precondition.  <=>, as v54: a CHECK passes on NULL.
    (55, "PM jobs: the engineer's reschedule of a job (S101)", [
        """ALTER TABLE pm_jobs
            ADD COLUMN IF NOT EXISTS rescheduled_on DATE NULL AFTER meter_offset,
            ADD COLUMN IF NOT EXISTS rescheduled_meter DECIMAL(14,3) NULL AFTER rescheduled_on""",
        """ALTER TABLE pm_jobs ADD CONSTRAINT IF NOT EXISTS chk_pm_jobs_rescheduled CHECK (
            (rescheduled_on IS NULL OR rescheduled_on <=> due_on)
            AND (rescheduled_meter IS NULL OR rescheduled_meter <=> due_meter))""",
    ]),
    # PM alerts (S102, R03.7): the due point (date and meter value, as due_on and due_meter) each alert
    # was queued for, so the daily scan sends each once per due point.  Both NULL = never sent.  A changed
    # due point (a plan edit, a reschedule) sends them again.  No CHECK, no index: tens of jobs, read once a
    # day through ix_pm_jobs_state.  Nullable new columns on a table production does not hold yet (v52 is
    # unreleased): no precondition.
    (56, "PM jobs: the due point each PM alert was sent for (S102)", [
        """ALTER TABLE pm_jobs
            ADD COLUMN IF NOT EXISTS due_alert_on DATE NULL AFTER needs_verification,
            ADD COLUMN IF NOT EXISTS due_alert_meter DECIMAL(14,3) NULL AFTER due_alert_on,
            ADD COLUMN IF NOT EXISTS overdue_alert_on DATE NULL AFTER due_alert_meter,
            ADD COLUMN IF NOT EXISTS overdue_alert_meter DECIMAL(14,3) NULL AFTER overdue_alert_on""",
    ]),
]
