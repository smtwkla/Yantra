# Yantra — database schema

The schema docs are made from the migrations, by a command, and a check says when they are
stale (S078). This file holds only what the data cannot: what the files are, how to use them,
and the conventions.

## The files

- **The source of truth is the migrations** (`backend/local_db.py`, `_MIGRATIONS`).
- [`schema/schema.json`](schema/schema.json) holds every table, column, primary key, foreign
  key, index and check, and the migration number it describes. `tooling\schema-docs.bat write`
  makes it from a database built fresh from the migrations. It is never edited by hand.
- [`schema/notes.json`](schema/notes.json) holds what the data cannot: each table's area (its
  diagram tab) and what it holds, the areas and their notes, and the planned tables. It is the
  only data file a person or an agent edits.
- [`schema/schema-data.js`](schema/schema-data.js) holds both, as a script, for the page. It is
  generated with `schema.json` and never edited.
- [`schema.html`](schema.html) draws both: open it from disk in a browser. It has an overview
  and one tab per area, each as a diagram (it needs internet for its drawing library) or as
  tables (they work without internet).
- `tooling\schema-docs.bat check` fails when `schema.json` or `schema-data.js` differ from the
  migrations and the notes, when a built table has no line in `notes.json` (or a line names no
  built table), or when a planned table is already built. It runs in the coder's docs pass, at
  gate B and in the pre-flight. Exit 0 current, 1 stale or a notes problem, 2 not completed.

## For agents

- Read `schema.json` for the structure and `notes.json` for the meaning. Never edit
  `schema.json` or `schema-data.js`.
- Per migration:
  1. Write the migration in `backend/local_db.py`.
  2. For a new table, add one line to `notes.json` under `tables` (a planned one moves there
     from `planned`).
  3. Run `tooling\schema-docs.bat write` and read `git diff docs/schema/` (a few lines). Then
     `tooling\schema-docs.bat check` must exit 0.

## Conventions

- All timestamps are stored as IST (`DATETIME`, connection time zone
  Asia/Kolkata) per the base time-zone policy. Dates are shown as DD-MM-YYYY.
- `created_by`, `updated_by`, `granted_by`, `assigned_by` and the like hold
  the **login username** of who did it, not a foreign key. A person's login
  is `people.username`.
- Rows are not deleted where history matters: `active` hides masters,
  `removed_at` hides documents, and a ticket keeps every event.
- Every table is InnoDB, `utf8mb4`.
- Names: `uq_<table>_<what>` a unique key, `ix_<table>_<what>` an index,
  `fk_<table>_<what>` a foreign key, `chk_<table>_<what>` a check. An index named
  `fk_…` is the one MariaDB made for the foreign key of that name. Two names break
  the rule: the older `ux_access_log_sighting`, and the column-level check
  `payload` on `task_queue`, which MariaDB names after its column. All foreign
  keys are `RESTRICT` today (88 of 88, at v51).
