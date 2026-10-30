```
Step: S078 — Schema docs from the migrations
Doc: brief
Author: orchestrator (Opus 5.5)
Date: 30-10-2026
Track: full
Baseline: 1643f65 (review r1 against 12a682e; only S078's own files changed since; stale check 30-10-2026: nothing changed)
Status: Implementing (approved 30-10-2026 by KLA: one step; Q1 a; Q2 keep)
```

# S078 — Schema docs from the migrations

**Size**: 20 files in § 3 (under 25), but the draft is about 740 lines (over 600), mostly exact rules and
message texts. Proposed cut, if KLA wants one: **S078a** the generator, the check, `schema.json`,
`notes.json`, the new `schema.md`, the references and the release hook; the old page stays, frozen at v41
with a line "Out of date: see docs/schema/schema.json"; **S078b** the new page (`schema-view.js`,
`schema-data.js`, the Tables view). Recommendation: **one step**. The page is about 150 lines of code,
and with the cut the page is wrong between the two steps, which is the problem this step removes.

## 1. What will be built

The schema docs come from the migrations, by a command, and a check tells when they are stale. Agents no
longer edit diagrams by hand. Why (KLA, 30-10-2026): every migration step edited `docs/schema.html` by
hand (the diagrams are one JSON line; each step wrote a one-off script; a 4-line change made a
20 000-token review diff), and "if a further step's coder agent reads an outdated doc, then it is an
issue". So the docs must be current at every commit, not only at a release.

1. **A generator** (`tooling\schema-docs.bat write`). It builds a fresh database from `_MIGRATIONS`, reads
   the catalogue (`information_schema`), and writes two files:
   - `docs/schema/schema.json`: every table, column (type, empty allowed, default, key, extra), primary
     key, foreign key (with required or optional), index and check, and the migration number. One column
     per line, in a fixed order, so a schema change gives a small diff.
   - `docs/schema/schema-data.js`: the same data, and the notes (item 2), as a script
     (`window.YANTRA_SCHEMA = …`), because a page opened from disk (`file://`) may load a script but may
     not fetch a file.
2. **One hand-edited file**, `docs/schema/notes.json`: for each table its area (the diagram tab) and what
   it holds; the areas' names and notes; the planned tables. It is the only data file a person or an
   agent edits.
3. **A check** (`tooling\schema-docs.bat check`). It builds the same data and fails when the committed
   `schema.json` or `schema-data.js` differ from it, when a built table has no line in `notes.json` (or a
   line names no built table), or when a planned table is already built. It runs at three points: the
   coder's docs pass, the orchestrator at gate B, and the pre-flight (through `tooling\release-tests.bat`).
   It is not in `tooling\run-tests.bat`.
4. **The page** `docs/schema.html` holds no data. Its script reads `schema/schema-data.js` and draws, in
   the browser, what it shows today (the tabs, the Overview, one ER diagram per area with neighbour
   tables by key only, the link notation `||` required / `o|` optional, each link labelled by its
   column), plus a new **Tables** view: per area, each table with what it holds, its columns, indexes,
   foreign keys and checks; on the Overview, every table with its area, and the planned tables. The
   Tables view works without internet; the diagram needs the drawing library from the CDN, as today.
5. **`docs/schema.md`** keeps its prose (what the schema docs are, the conventions, the names) and points
   to the JSON. Its table lists and its Mermaid overview go: the built-table texts and the planned tables
   move to `notes.json`, the overview is drawn by the page.
6. **No edit history in the docs.** The hand-written history lines in `schema.md` (its intro) and
   `schema.html` (its meta line) go. The data carries one value, the migration number. Git holds the
   history.
7. **Every reference is updated**: `.claude/CLAUDE.md` (§ Yantra Specifics, § Pre-flight, § Step
   workflow *Plan and domain docs*, § Docs to keep current, § SMTW-Review), `docs/Plan.MD` § 5, and the
   three roadmaps that cite `docs/schema.md`. The synced files are not edited (§ 9, follow-ups for
   smtw-common).

Example of the agent's work per migration, after this step: write the migration in `local_db.py`; for a
new table add one line to `notes.json`; run `tooling\schema-docs.bat write`; read `git diff docs/schema/`
(a few lines). The check is red if a step was skipped.

### Out of scope

- **Table and column comments in MariaDB** (`COMMENT '…'`). KLA, 30-10-2026: keep the descriptions in
  `notes.json` for now, decide later.
- **An exported DDL file** (`docs/schema.sql`, named by SMTW-WebApp-Base § layout). Not built; the JSON
  carries the same facts in a diffable form (D9).
- **The check in `tooling\run-tests.bat`** or in a backend test that compares the docs (decision 7: three
  points only, so a normal test run is not slowed or broken by a doc).
- **A browser test of the page** (D10).
- **Shortening the table texts** to one sentence (Q1): the first migration copies today's texts whole.
- **Moving the dev database to MariaDB 11.8** (queued: *Dev and test MariaDB match production*).
- **Edits to synced files**: `.claude/skills/`, `.claude/agents/`, `docs/steps/README.md`,
  `.claude/SMTW-WebApp-Base.md`, `tooling/common/` (§ 9 follow-ups).
- **A separate documenter agent** (decision 8, KLA agreed): the coder runs the command in its docs pass.

## 2. Standards and practice

- **ISO 9001 § 7.5.3, control of documented information.** In plain words: a document the work relies on
  must be available and fit for use where and when it is needed, and its changes must be controlled
  (version control). Here the schema docs are what the next coder relies on. They are made from the
  source (the migrations), checked against it at every gate, and identified by the migration number they
  describe; git is the version control, so the docs carry no edit history. ISO 9001:2015 7.5.3.1 a)
  "available and suitable for use, where and when it is needed"; 7.5.3.2 c) "control of changes (e.g.
  version control)" (confirmed, BR1-08).
- **ISO 9001 § 7.5.2, creating and updating: identification.** A document says what it is and which
  version. The page and the JSON name the migration number (`"migration": 41`) and say they are
  generated (the `_note` line, § 4.1). 7.5.2 a) is "identification and description (e.g. a title, date,
  author, or reference number)"; here the migration number is the identification (confirmed, BR1-08).
- **Single source of truth (docs as code).** A fact lives in one place; everything else is derived from
  it by a tool and checked. The migrations are the source of the structure; `notes.json` is the source of
  the human parts (areas, descriptions, planned tables).
- **SMTW-WebApp-Base § layout**: names `docs/schema.sql`, "Full DDL — exported, never hand-edited". This
  step follows the rule (exported, never hand-edited) with JSON instead of DDL: a deliberate departure,
  D9.
- **CLAUDE-COMMON**: *Pure core, thin shell* (the core takes plain rows, returns text and problems);
  *Wrapper scripts* (one `.bat`, a log and one summary line); *Explicit over implicit* (fixed key order,
  no hidden normalisation beyond § 5.2).
- **No maintenance standard is touched** (TPM, ISO 14224, EN 13306, ISO 55000, SMRP): the step changes
  documentation and tooling only, no app behaviour. ISO 27001: the generated files carry structure only,
  no rows and no secrets (§ 5.2 reads only `information_schema`).

## 3. Where

### Tooling

- `tooling/schema/schema_docs_core.py` — **new**, pure: catalogue rows in; the schema dict, the JSON text,
  the script text, the list of problems and the outcome (exit code, lines) out. No DB, no file access, no
  clock. Stdlib only (`json`, `re`).
- `tooling/schema/schema_docs.py` — **new**, thin shell: builds and drops the database (§ 5.1), reads the
  catalogue (§ 5.2), reads `notes.json` and the files on disk, writes (mode `write`), prints, exits.
  Imports `config`, `local_db` and `tests.db_names` from `backend/` (it runs in the backend's uv project).
- `tooling/schema-docs.bat` — **new**, wrapper: `tooling\schema-docs.bat write|check` (§ 5.5).
- `tooling/release-tests.bat` — runs `schema-docs.bat check` in the worktree after the unit suites
  (§ 5.7).

### The page

- `docs/schema.html` — the `TABS` line goes; loads `schema/schema-data.js` and `schema/schema-view.js`;
  thin DOM code; Mermaid loaded by a dynamic `import()` (§ 5.6).
- `docs/schema/schema-view.js` — **new**, a classic script (not a module) with the page's pure
  functions: the Mermaid text of a tab, an area's own and neighbour tables, the meta line, the parts of
  a table text (§ 5.6.3).
- `docs/schema/notes.json` — **new**, hand-edited; first filled from today's docs (§ 5.8).
- `docs/schema/schema.json`, `docs/schema/schema-data.js` — **new**, generated by `write`.

### Tests

- `tooling/tests/test_schema_docs_core.py` — **new**, the core's unit tests (§ 8.1), in the tooling suite.
- `backend/tests/test_schema_docs_shell.py` — **new**, two tests of the shell against the dev DB
  container (§ 8.2).
- `backend/tests/db_names.py` — adds `SCHEMA_DOCS_DB` (§ 5.1), beside `TEST_DB` and `UPGRADE_DB`.
- `frontend/tests/schemaView.test.js` — **new**, unit tests of `schema-view.js` (§ 8.3).

### Docs (housekeeping, by the coder)

- `docs/schema.md` — rewritten as prose (§ 5.9).
- `.claude/CLAUDE.md` — § Yantra Specifics *Stack* and *Dev commands*; § Pre-flight *Failure logs* and
  *Re-run failing tests*; § Step workflow *Plan and domain docs*; § Docs to keep current, the schema row;
  § SMTW-Review, a new point (§ 5.10 gives each text).
- `docs/Plan.MD` § 5 *Data model* — points to the new files.
- `docs/roadmap/R02-amc-contracts.md`, `docs/roadmap/R03-pm.md`, `docs/roadmap/R05-rca.md` — the
  evidence cells that cite `docs/schema.md` (§ 5.10).
- `docs/steps/INDEX.md` — the queued row *Module and schema docs*: its note says the schema half is done
  by S078 (the orchestrator may make this edit instead; the coder in a worktree writes it under
  `## Shared docs`).

No migration, no app code, no RBAC key, no secret, no new dependency (the shell uses `pymysql`, already
in the backend's lock; the core and its tests use the stdlib and the tooling suite's `pytest`).

## 4. The files

### 4.1 `docs/schema/schema.json` (generated)

Top-level keys in this order: `_note`, `migration`, `tables`. Tables sorted by name. In each table the
keys in this order: `columns` (by `ORDINAL_POSITION`, the order the migrations gave), `primary_key`,
`foreign_keys` (by name), `indexes` (by name, without `PRIMARY`), `checks` (by name). Each column, foreign
key, index and check is one JSON object on one line. Example (one table, abridged to the shape; values as
the dev DB returns them for `people` at v41):

```json
{
  "_note": "Generated by tooling\\schema-docs.bat write from backend/local_db.py _MIGRATIONS. Do not edit; edit docs/schema/notes.json and run the command.",
  "migration": 41,
  "tables": {
    "people": {
      "columns": [
        {"name": "id", "type": "int", "null": false, "default": null, "key": "PK", "extra": "auto_increment"},
        {"name": "name", "type": "varchar(100)", "null": false, "default": null, "key": "", "extra": ""},
        {"name": "employment", "type": "enum('direct','contractor')", "null": false, "default": null, "key": "", "extra": ""},
        {"name": "username", "type": "varchar(100)", "null": true, "default": null, "key": "UK", "extra": ""},
        {"name": "active", "type": "tinyint", "null": false, "default": "1", "key": "", "extra": ""},
        {"name": "created_at", "type": "datetime", "null": false, "default": "current_timestamp()", "key": "", "extra": ""}
      ],
      "primary_key": ["id"],
      "foreign_keys": [],
      "indexes": [
        {"name": "uq_people_username", "unique": true, "columns": ["username"]}
      ],
      "checks": []
    }
  }
}
```

A foreign key line: `{"name": "fk_model_property_values_option", "columns": ["option_id", "property_id"],
"references": "property_options", "ref_columns": ["id", "property_id"], "required": false, "on_delete":
"RESTRICT", "on_update": "RESTRICT"}`. A check line: `{"name": "chk_improvements_watch_days", "level": "table", "clause":
"`watch_days` between 30 and 365"}` (`level` is `table` or `column`, BR1-03). An empty list is written `[]` on its key's line. Indent two spaces.
UTF-8, no BOM, `ensure_ascii=False`, LF line ends, one final newline.

### 4.2 `docs/schema/schema-data.js` (generated)

```js
// Generated by tooling\schema-docs.bat write from docs/schema/schema.json and docs/schema/notes.json. Do not edit.
window.YANTRA_SCHEMA = {
  …the lines of schema.json, unchanged…
};
window.YANTRA_SCHEMA_NOTES = {
  …notes.json in the same layout: one table, one area, one planned group per line…
};
```

The notes go into this file (decision 4 left the choice): the generator copies them, so the page loads
one script and `notes.json` stays plain JSON for editing (D2).

### 4.3 `docs/schema/notes.json` (hand-edited)

```json
{
  "overview_note": "Every table with its keyed columns, and every link. Use the area tabs for all columns.",
  "areas": [
    {"name": "Equipment", "note": "Sites and units, the register tree, …"},
    {"name": "Team and access", "note": "People, trades, site roles and units, devices for push. …"},
    {"name": "Tickets", "note": "…"},
    {"name": "System", "note": "…"}
  ],
  "tables": {
    "access_log": {"area": "System", "holds": "One row per sighting of a login session from an address, or a refusal (S013); kept 365 days"},
    "…": {}
  },
  "planned_note": "Not built yet; the design is in `Plan.MD` § 4. Names may change when their step is briefed.",
  "planned": [
    {"tables": ["pm_templates", "pm_template_items"], "holds": "Reusable PM work: …"}
  ]
}
```

- `areas` is in tab order; the page puts *Overview* first, then the areas, in this order.
- `tables` has one key per built table. `area` must be the `name` of one entry of `areas`. `holds` is
  plain text; the page shows `` `x` `` as code and `*x*` as italics, nothing else (§ 5.6.3).
- `planned` groups the names of one planned row, as § Planned tables of `schema.md` does today.
- The generator reads it with `json.loads`; it never rewrites it. Key order and layout are the editor's;
  the copy in `schema-data.js` is written in the fixed layout of § 4.2.

## 5. Rules

### 5.1 The database

1. **Name**: `vel_yantra_test_<run>_schemadocs`, from `backend/tests/db_names.py`: a new constant
   `SCHEMA_DOCS_DB`, built with the module's `_part` from `YANTRA_TEST_RUN` (default `dev`), and the fixed
   part `schemadocs`. Reason: the name falls inside the existing grant on `vel_yantra_test_%`
   (`tooling/dev/init-test-db.sql`, `tooling/run-backend-tests.bat`), so no new grant is needed, and
   `schemadocs` can never equal a worker part (`gw0`…, `main`). Two runs with different run names never
   share the database; the release uses `release`, a coder its own name (settings: *Unit tests*). The
   names of the drop list in CLAUDE.md § Dev commands already cover it.
2. **One run at a time per name**: the shell takes `GET_LOCK(named_lock("yantra_schema_docs",
   SCHEMA_DOCS_DB), 60)` before it drops the database and releases it after the read. A lock not got in
   60 s ends the run with exit 2 ("Another schema docs run with the same run name is still running. Wait
   for it, or set YANTRA_TEST_RUN to another name."). `local_db.init_db` takes its own lock
   (`LOCK_MIGRATIONS` on the same database name); the names differ, so the two never wait on each other.
3. **Guard before any drop** (BR1-01): the shell refuses, with exit 2, a host outside
   `("localhost", "127.0.0.1")` (the e2e backend's `LOCAL_HOSTS`, copied, not imported: that module imports
   the app) and a database name that does not end in `_schemadocs`, before the lock and the drop. Message
   in the form of `tooling/e2e/e2e_backend.py` `check_target`'s: `The schema docs were not built: refusing
   database host <host>; the schema docs database must be local (localhost, 127.0.0.1).`
4. **Fresh every run**: `DROP DATABASE IF EXISTS`, then `CREATE DATABASE … CHARACTER SET utf8mb4 COLLATE
   utf8mb4_unicode_ci`, on a connection with no database selected, as `tooling/e2e/e2e_backend.py`
   `_recreate_database` does; then `local_db.init_db` with a copy of `config.DB_CONFIG` whose `database` is
   `SCHEMA_DOCS_DB`. Reason for no reuse: during coding the coder
   changes its new migration several times; a kept database would keep the first version.
5. **Dropped at the end** (in a `finally`), also after a failed read; a run cut off leaves it, and the
   next run drops it first.
6. **Imports**: a script run by path has its own folder as `sys.path[0]`, so `schema_docs.py` inserts
   `backend/` (from its own path: `Path(__file__).resolve().parents[2] / "backend"`) before `import config,
   local_db` and `from tests.db_names import SCHEMA_DOCS_DB` (BR1-04). It reads `config.DB_CONFIG` inside
   `main`, not at import, so a test's monkeypatch takes effect (BR1-11).
7. **Credentials**: `config.DB_CONFIG`, with `YANTRA_TESTING=1` set before `config` is imported, so a
   worktree without `secrets_app.py` uses `example_secrets_app.py` (the dev container on 127.0.0.1:3307),
   as the backend tests do (`conftest.py`). The shell never connects to `vel_yantra_master`.
8. **The migration number** is `MAX(version)` of the built `db_version`. If it differs from
   `local_db.LATEST_VERSION` the run ends with exit 2 (a migration was skipped; should not happen).

### 5.2 Reading and normalising the catalogue

The shell reads five result sets for `SCHEMA_DOCS_DB` (filter `TABLE_SCHEMA` on the first four;
`CONSTRAINT_SCHEMA` on `CHECK_CONSTRAINTS`, which has no `TABLE_SCHEMA` column, BR1-03) and passes the rows,
as plain dicts, to the core:

| Source | Columns read |
|---|---|
| `information_schema.TABLES` (`TABLE_TYPE = 'BASE TABLE'`) | `TABLE_NAME` |
| `information_schema.COLUMNS` | `TABLE_NAME`, `COLUMN_NAME`, `ORDINAL_POSITION`, `COLUMN_TYPE`, `IS_NULLABLE`, `COLUMN_DEFAULT`, `EXTRA` |
| `information_schema.STATISTICS` | `TABLE_NAME`, `INDEX_NAME`, `NON_UNIQUE`, `SEQ_IN_INDEX`, `COLUMN_NAME`, `SUB_PART` |
| `KEY_COLUMN_USAGE` joined with `REFERENTIAL_CONSTRAINTS` (on schema, constraint name and table) | constraint name, table, column, `ORDINAL_POSITION`, `REFERENCED_TABLE_NAME`, `REFERENCED_COLUMN_NAME`, `DELETE_RULE`, `UPDATE_RULE` |
| `information_schema.CHECK_CONSTRAINTS` | `TABLE_NAME`, `CONSTRAINT_NAME`, `LEVEL`, `CHECK_CLAUSE` |

The core normalises, so the output does not depend on what one server version prints (dev runs 11.4.13,
read 30-10-2026 by `SELECT VERSION()`; production 11.8.8, `docs/steps/INDEX.md` queue):

- **Type**: `COLUMN_TYPE` in lower case, with the display width removed from the integer types
  (`tinyint`, `smallint`, `mediumint`, `int`, `bigint`): `int(11)` → `int`, `tinyint(1)` → `tinyint`,
  `int(10) unsigned` → `int unsigned`. Every other type is kept as the server gives it (`varchar(100)`,
  `decimal(14,3)`, `enum('low','high','not_ok')`). Reason: MariaDB 11.4 prints the widths (seen on the dev
  DB: `int(11)`, `smallint(6)`, `tinyint(1)`); MySQL 8 has dropped them, and they mean nothing for
  storage.
- **Empty allowed** (`null`): `IS_NULLABLE = 'YES'`.
- **Default**: JSON `null` when `COLUMN_DEFAULT` is SQL NULL (no default) or the text `NULL` (default
  NULL); MariaDB 11.4 gives both (seen: `people.id` SQL NULL, `people.username` the text `NULL`). Any other
  value is kept as the server's text: quoted literals `'manual'`, numbers `1`, `current_timestamp()`.
- **Extra**: `EXTRA` in lower case (`auto_increment`, `on update current_timestamp()`, or `""`).
- **Key** of a column: the tags `PK` (in the primary key), `FK` (in any foreign key), `UK` (a unique index
  other than `PRIMARY` has this column alone), in that order, joined by `,`; `""` when none. So
  `improvements.follow_up_of_id` is `FK,UK` and `improvement_tickets.open_link` is `""` (its unique key
  `uq_improvement_tickets_open` has two columns).
- **Index columns**: by `SEQ_IN_INDEX`; a prefix index writes `name(n)` from `SUB_PART`. An index that
  backs a foreign key is listed like any other.
- **Foreign key** `required`: true when every one of its columns has `null` false.
- **Check level**: `LEVEL` in lower case (`table` or `column`). A column-level check is named after its
  column, as MariaDB names it: today one, `task_queue` `payload`, clause `` json_valid(`payload`) ``
  (BR1-03).
- **Check clause**: as the server gives it. *To verify*: whether 11.8 prints the same text as 11.4. If
  it does not, the first run on 11.8 shows a diff once, and `write` settles it (§ 9 A3).

Collation, character set, engine, row counts and `AUTO_INCREMENT` values are not read: they change with
the server version or the data, and `schema.md` § Conventions states the fixed ones (InnoDB, `utf8mb4`).

### 5.3 The checks

Four checks, each counted once, in this order:

The shell reads and parses `notes.json` **before** it builds the database, so an invalid notes file ends
the run in a second (exit 1, checks 3 and 4 failed, checks 1 and 2 not run and counted failed), not after a
migration build (BR1-06). "The file on disk" below means the file in the tree being checked, committed or
not (BR1-07).

1. **`schema.json` is current**: the file on disk equals the generated text.
2. **`schema-data.js` is current**: the same for the script.
3. **The notes match the tables**: every built table has a `tables` entry; every entry names a built
   table; every entry's `area` is the name of an `areas` entry (a missing `area` gives the "names area"
   message with `(none)`); every entry has a non-empty `holds` (a missing or empty one is a problem:
   `docs/schema/notes.json: table <name> has no "holds" text. Write what it holds.`); every `areas` name is
   unique (BR1-06).
4. **No planned table is built**: no name in `planned[].tables` is a built table.

Comparison rules: both texts with `\r\n` turned into `\n` before comparing (the repo has
`* text=auto` in `.gitattributes`, and `core.autocrlf` is `true` on KLA's machine, so a checkout may hold
CRLF; read 30-10-2026: `git ls-files --eol` shows `w/lf` for today's schema files). A missing file is a
failed check ("… is missing"). For a stale file the message names the first line that differs, with its
number, the text on disk and the generated text (each cut to 120 characters), and the action.

Messages (developer-facing, CLAUDE-COMMON writing style A; each says what to do):

- `docs/schema/schema.json is stale: line 214 differs (on disk: …; generated: …). Run tooling\schema-docs.bat write and commit the result.`
- `docs/schema/notes.json has no line for table improvement_causes. Add "improvement_causes": {"area": "<one of: Equipment, Team and access, Tickets, System>", "holds": "<what it holds>"} under "tables", then run tooling\schema-docs.bat write.`
- `docs/schema/notes.json has a line for table user_units, which is not built. Remove the line, or move it to "planned".`
- `docs/schema/notes.json: table tickets names area "Ticket", which is not in "areas".`
- `docs/schema/notes.json lists pm_plans under "planned", but it is built. Move it to "tables" with its area.`
- `docs/schema/notes.json is not valid JSON: <the json error with line and column>. Fix the file, then run the command again.`
  (A file that cannot be read fails checks 3 and 4, and `write` writes nothing, since `schema-data.js`
  needs the notes.)

### 5.4 The diagrams (rules of `schema-view.js`, unchanged from today's page)

- **Overview**: every table (46, `db_version` included, D6); for each, only the columns with a key
  (`PK`, `FK` or `UK`); every foreign key as a link.
- **An area tab**: the area's own tables with every column; its **neighbours** (tables of other areas
  linked to or from an own table) with their primary-key columns only; every link with at least one end
  in the area. A link between two neighbours is not drawn (as today: the Team tab draws no
  `units ||--o{ tickets`).
- **Order**: own tables by name, then neighbours by name; links by parent table, child table, label.
- **Column line**: four spaces, the base type (the type up to the first `(` or space: `varchar`, `enum`,
  `int`), the name, the key when not empty, and `"null"` when empty is allowed. E.g.
  `    int unit_id FK "null"`.
- **Link line**: two spaces, `<parent> <left>--<right> <child> : "<columns>"`. `<left>` is `||` when the
  key is required, `o|` when not. `<right>` is `o|` when the key's columns alone form a unique key (one
  to one: `improvements o|--o| improvements : "follow_up_of_id"`), else `o{`. The label is the key's
  columns joined by `, `.
- **Meta line**: `Migration v41 · 46 tables, 75 links · PK primary key, FK foreign key, UK unique; "null" = may be empty. A line runs from the parent table to the table that points at it (crow's foot = many).`
  (the numbers from the data; 75 = the foreign keys in the dev DB at v41, all `RESTRICT`, read
  30-10-2026).

**Differences the first run shows against today's hand-made diagrams** (each is a hand-edit error or a
rule today's text broke; the coder lists every one it finds in the impl report, § 8.4):
`db_version` appears (Overview, System); `improvement_tickets.open_link` loses `UK`; the Overview drops
the non-key lines `varchar event` (`improvement_events`) and `smallint position` (`improvement_whys`);
the two links to `property_options` are labelled `option_id, property_id`; entities are in name order
(today `meter_types` stands before `meter_readings`, and `equipment_property_values` after
`model_property_values`).

### 5.5 The command

`tooling\schema-docs.bat <mode>`, mode `write` or `check`; another or no mode prints the usage line
`Usage: tooling\schema-docs.bat write|check` and exits 2.

- The wrapper sets `YANTRA_TEST_RUN=dev` when unset and `YANTRA_TEST_LOG_DIR` to `scratch\` when unset
  (as `run-backend-tests.bat`), the log `%YANTRA_TEST_LOG_DIR%\schema-docs.log`, or
  `schema-docs-<run>.log` when the run is not `dev`, then runs, from `backend\`:
  `uv run --no-project python "%~dp0common\run_test_suite.py" schema-docs "%LOG%" -- uv run python
  "%~dp0schema\schema_docs.py" <mode>`. So the whole output is in the log and the last line is the
  standard summary (CLAUDE-COMMON § Wrapper scripts), appended to `TEST_SUMMARY_FILE` when set.
- **`write`**: build, read, write `schema.json` and `schema-data.js` (always LF, § 4.1), then run the four
  checks on what is now on disk, so the output is the same as `check`'s.
- **`check`**: build, read, run the four checks; writes nothing.
- **Output**: one line per problem, then the count line, e.g. `Schema docs at migration v41: 3 passed,
  1 failed` (the form `run_test_suite.counts_of` reads, so the summary line shows the counts). On exit 2
  the last line is `Schema docs: not completed`, and the summary line says "no test counts found"; that is
  expected (BR1-05).
- **Exit codes** (as the dependency audit's, § Yantra Specifics *Software inventory*): **0** every check
  passed; **1** a check failed; **2** not completed: the database could not be reached, the user may not
  create the database, a migration failed, the lock timed out, `LATEST_VERSION` differs, or the mode is
  wrong. The core decides the code and the lines (`outcome`), so the tooling tests cover it.
- **The database down** (exit 2): `The schema docs were not built. The dev database cannot be reached: <describe_error text>. Start it with tooling\dev\dev-db-up.bat, then run the command again.`
  A refused `CREATE DATABASE` (error 1044): `The schema docs were not built. The database user may not create <name>. Run tooling\run-backend-tests.bat once (it grants the test databases), then run the command again.`
  A failed migration: `The schema docs were not built. The migrations could not be applied: <describe_error text>. Fix the migration in backend/local_db.py, then run the command again.`
  The message names no version: `init_db` raises the plain `pymysql` error, and its log line
  "Applying migration v%d" (printed to the console by the shell's `logging.basicConfig(level=INFO)`)
  already shows the last version tried, just above the message.
  The shell catches `pymysql.MySQLError`, `local_db.DBUnavailable` and `local_db.MigrationBlocked`
  only; any other exception is a bug and shows its traceback (CLAUDE-COMMON: never swallow).

### 5.6 The page `docs/schema.html`

#### 5.6.1 Loading

1. `<script src="schema/schema-data.js"></script>` and `<script src="schema/schema-view.js"></script>`,
   classic scripts with a relative path: they load from `file://` as from a server (*fact*, the device
   check of § 8.5 confirms it for Chrome and Edge on KLA's laptop).
2. svg-pan-zoom 3.6.1 from jsDelivr, as today.
3. The page's own code is a classic inline script. Mermaid 11.4.1 is loaded by
   `await import("https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.esm.min.mjs")` the first time a
   diagram is drawn, inside a `try`. Reason: today the static `import` stops the whole page when the CDN
   cannot be reached; the Tables view must work offline. The same URL and version as today (the
   artifact rule's pinned versions; both are older than two weeks).
4. `mermaid.initialize` keeps today's settings (`securityLevel: "strict"`, `maxTextSize: 200000`, the
   theme from the colour scheme, `er.useMaxWidth: false`).

#### 5.6.2 What it shows

- **Header**: the title "Yantra database schema" and the meta line (§ 5.4).
- **Tabs**: *Overview*, then each area of `notes.areas`, in order. The selected tab is remembered in
  `localStorage` (`yantra-schema-tab`, by tab name now, not by number; try/catch as today).
- **The bar**: the tab's note (`overview_note` or the area's `note`); two buttons `Show diagram` and
  `Show tables` (`aria-pressed` on the selected one; remembered as `yantra-schema-view`); the zoom buttons
  `Zoom in`, `Zoom out`, `Fit to screen`, shown only in the diagram view.
- **Diagram view**: as today (pan and zoom, fit on resize).
- **Tables view, an area**: for each own table, by name: the name as a heading, the `holds` text, then
  four small tables: **Columns** (Column, Type, Empty allowed: `Yes` / `No`, Default, Key, Extra),
  **Indexes** (Name, Unique: `Yes` / `No`, Columns), **Foreign keys** (Name, Columns, Points to
  `table (columns)`, Required: `Yes` / `No`), **Checks** (Name, Rule). An empty list shows `None`.
  Neighbour tables are not repeated; each foreign key's target names its table.
- **Tables view, the Overview**: one table of every built table (Table, Area, Holds), then the heading
  "Planned tables (not built yet)", the `planned_note`, and one row per planned group (Tables, Holds).
- **Phone width**: each small table sits in a box with `overflow-x: auto`, so the page never scrolls
  sideways (16 px gutter, as today).
- **Footer**: `Drag to move, scroll or pinch to zoom. The diagram needs internet for its drawing library; the tables do not. Data: docs/schema/schema.json, made by tooling\schema-docs.bat.`

#### 5.6.3 `schema-view.js`

A classic script that sets `window.YantraSchemaView` (in the test, the sandbox's `window`), with pure
functions only (no DOM, no `fetch`, no storage):

- `tabs(notes)` → the tab names, *Overview* first.
- `areaTables(schema, notes, area)` → `{own, neighbours}` (names, sorted).
- `diagramSource(schema, notes, tab)` → the Mermaid text (§ 5.4).
- `metaLine(schema)` → the meta line.
- `holdsParts(text)` → `[{kind: "text" | "code" | "em", text}]`: `` `x` `` → code, `*x*` → em, all else
  text; an unpaired mark stays text.

The DOM code in `schema.html` builds every element with `createElement` and `textContent`; it never sets
`innerHTML` from data (the notes are repo text, but a stray `<` must show as a `<`). The Mermaid SVG is
set as today (Mermaid's own output, `securityLevel: "strict"`).

#### 5.6.4 When the data is missing

- `window.YANTRA_SCHEMA` or `window.YANTRA_SCHEMA_NOTES` undefined (file missing, or a syntax error in
  it): no tabs; the stage shows `The schema data was not found. The file docs/schema/schema-data.js is missing or broken. Run tooling\schema-docs.bat write, then reload this page.`
- A built table with no notes entry (a check would be red): it is listed in the Overview's Tables view
  with the area `No area`, and drawn only in the Overview. Its holds cell is empty.
- The CDN cannot be reached: the diagram stage shows `The diagram could not be drawn. Check the internet connection, then reload the page. The tables work without internet: select Show tables.`

### 5.7 The three check points

1. **The coder's docs pass**, at the end of the coding and of every fix round, in any step whose change
   touches `_MIGRATIONS` or `docs/schema/notes.json`: run `tooling\schema-docs.bat write`, read
   `git diff docs/schema/`, then `check` must exit 0. Written into the schema row of § Docs to keep
   current (§ 5.10), which the coder reads in every docs pass (`.claude/agents/coder.md`, the docs pass).
2. **Gate B**, by the orchestrator: `tooling\schema-docs.bat check`; a non-zero exit is a blocker. Also
   in that row. It runs in the tree that holds the step's changes (the coder's worktree when it used one,
   else the working folder), with `YANTRA_TEST_RUN` set to the step's run name (e.g. `s078c1`), so it never
   shares a database with a run in progress (BR1-02). Reason for that place (decision 7 b left it open): the step skill is synced and may not be
   edited; the orchestrator already reads § Docs to keep current when planning and checks `## Docs
   updated` against the diff before gate B (`.claude/skills/step/SKILL.md`, the docs pass, "Schema docs
   are the hard rule"); a new § Step workflow entry would be an entry `docs/steps/README.md` § The repo's
   settings and index does not list, which the synced tools do not read. The code reviewer reads the
   same row (`.claude/agents/code-reviewer.md`, the docs pass), so it runs the check in its rounds too
   (seconds).
3. **Pre-flight**, through `tooling\release-tests.bat`: after `call "%WT%\tooling\run-tests.bat"`, before
   the browser tests: `set "TEST_SUMMARY_FILE=%YANTRA_TEST_LOG_DIR%\test-summary-release.txt"`, `call
   "%WT%\tooling\schema-docs.bat" check`, `set SCHEMA_RESULT=%ERRORLEVEL%`. A non-zero result sets
   `RELEASE_RESULT=1` with the line `Release tests: the schema docs are stale or were not checked (see
   scratch\release-tests\schema-docs-release.log).` It runs also when the unit suites were red (one
   attempt shows every fault, as the browser tests). It needs what the backend tests need: the dev DB
   container up (the release's backend suite already needs it); it adds the time of one fresh migration
   build (*to verify*: about 5 s, by the coder's run). The worktree is HEAD, so it checks the committed
   docs against the committed migrations. The run name is `release`, so the database is
   `vel_yantra_test_release_schemadocs`. `run-tests.bat` prints its summary block before the schema line
   is appended to `test-summary-release.txt`, so the line is in the file but not in that block;
   `schema-docs.bat`'s own last line shows it (BR1-10).

`tooling\run-tests.bat` is not changed.

### 5.8 The first notes.json (lose nothing)

The coder fills `notes.json` from the files at the baseline, by a one-off script in the scratchpad (not
committed), and states in the impl report that the comparison passed:

- **`areas`**: the four area tabs of today's `TABS` (`Equipment`, `Team and access`, `Tickets`,
  `System`), in this order, each `note` copied word for word; `overview_note` from the Overview tab.
- **`tables`**: each table's area from the tab where it is drawn with all its columns today (read
  30-10-2026 from `TABS`):
  - Equipment (20): `class_properties`, `equipment`, `equipment_categories`, `equipment_classes`,
    `equipment_documents`, `equipment_events`, `equipment_models`, `equipment_property_values`,
    `equipment_types`, `manufacturers`, `meter_readings`, `meter_types`, `model_meters`,
    `model_property_values`, `node_meters`, `procedures`, `property_definitions`, `property_options`,
    `sites`, `units`.
  - Team and access (7): `memberships`, `people`, `person_trades`, `person_units`, `push_subscriptions`,
    `trades`, `user_units`.
  - Tickets (14): `failure_causes`, `failure_modes`, `improvement_actions`, `improvement_events`,
    `improvement_tickets`, `improvement_whys`, `improvements`, `maintenance_actions`,
    `ticket_assignees`, `ticket_events`, `ticket_labour`, `ticket_note_edits`, `ticket_parts`, `tickets`.
  - System (5): `access_log`, `app_settings`, `serial_counters`, `task_queue`, and `db_version` (today in
    no tab, D6).
  - Each `holds` is the table's *Holds* cell of `schema.md` § Built tables, word for word (Q1), with one
    change: `db_version`'s "(internal; not in the diagram)" becomes "(internal)", since it is now drawn.
- **`planned_note`** and **`planned`**: § Planned tables' intro sentence and its 11 rows, word for word,
  each row's backticked names split into `tables`.
- **The comparison** (the script): every § Built tables row has its `holds` equal to its cell; every
  § Planned row is in `planned`; every table of `TABS` has the same area; 46 tables in `tables`, 46 built.
  `schema.md`'s other prose (the intro bullets, § Conventions, the "Indexes are not listed here" note,
  the overview's legend) is either kept in the new `schema.md` (§ 5.9) or replaced by the page's meta line
  and the JSON's indexes.

### 5.9 The new `docs/schema.md`

About 40 lines, no table list:

1. What the schema docs are: the migrations (`backend/local_db.py`, `_MIGRATIONS`) are the source;
   `docs/schema/schema.json` is made from them by `tooling\schema-docs.bat write` and holds every
   table, column, key, index and check; `docs/schema/notes.json` holds each table's area and what it
   holds, the areas and the planned tables; `docs/schema.html` draws both (open it from disk).
2. For agents: read `schema.json` for the structure and `notes.json` for the meaning; never edit
   `schema.json` or `schema-data.js`; per migration, the three moves of § 1's example.
3. § Conventions, kept word for word (IST timestamps, login usernames in `*_by`, no deletes where history
   matters, InnoDB and `utf8mb4`), plus one bullet on the names, as the dev DB shows them (read
   30-10-2026): `uq_<table>_<what>` a unique key, `ix_<table>_<what>` an index, `fk_<table>_<what>` a
   foreign key, `chk_<table>_<what>` a check; two names break it: the older `ux_access_log_sighting`, and
   the column-level check `payload` on `task_queue`, which MariaDB names after its column (BR1-03). All
   foreign keys are `RESTRICT` today (75 of 75).

No "migration vN" line and no history (decision 5): the number is in the JSON and on the page.

### 5.10 The reference updates (exact texts)

- **CLAUDE.md § Yantra Specifics, *Stack***: "Database schema: `docs/schema/schema.json` (every table,
  column, key, index and check; generated from the migrations by `tooling/schema-docs.bat write`, never
  edited), `docs/schema/notes.json` (each table's area and what it holds, the planned tables; edited by
  hand), drawn by `docs/schema.html`; conventions in `docs/schema.md`. A migration step runs the command
  (§ Docs to keep current)."
- **§ Dev commands**, a new bullet: "Schema docs: `tooling/schema-docs.bat write|check` (needs the dev
  DB; builds `vel_yantra_test_<run>_schemadocs` from `_MIGRATIONS` and drops it; exit 0 current, 1 stale
  or a notes problem, 2 not completed; log `scratch/schema-docs.log`)."
- **§ Pre-flight, *Failure logs***: add "the schema docs check `scratch/release-tests/schema-docs-release.log`".
  ***Re-run failing tests***: add "schema docs `tooling/schema-docs.bat check` (with
  `YANTRA_TEST_RUN=preflight`)".
- **§ Step workflow, *Plan and domain docs***: "schema docs `docs/schema/schema.json` (generated) and
  `docs/schema/notes.json`, conventions `docs/schema.md`".
- **§ Docs to keep current**, the schema row: Doc `docs/schema/notes.json`, `docs/schema/schema.json`,
  `docs/schema/schema-data.js`; due when the step "adds or changes a migration, or edits
  `docs/schema/notes.json` (BR1-09), or renames an area: a new
  table gets a line in `notes.json` (a planned one moves there from `planned`); then run
  `tooling\schema-docs.bat write` and read `git diff docs/schema/`; `check` must exit 0 at the end of the
  coding and of every fix round. Never edit `schema.json` or `schema-data.js` by hand. **Gate B**: the
  orchestrator runs `tooling\schema-docs.bat check` in the tree that holds the step's changes, with the
  step's `YANTRA_TEST_RUN`; a non-zero exit is a blocker (as a missing migration was). The code reviewer
  runs it in each round."
- **§ SMTW-Review**, a new point: "**Schema docs (S078)**: run `tooling/schema-docs.bat check`; exit 0
  means `docs/schema/` matches the migrations. A red check names the stale file or the table without
  notes."
- **`docs/Plan.MD` § 5**: "The tables, keys and indexes are in `docs/schema/schema.json`, generated from
  the migrations; what each table holds and the planned tables in `docs/schema/notes.json`; the diagram
  in `docs/schema.html` (open it in a browser); the conventions in `docs/schema.md` (S078, 30-10-2026)."
- **Roadmaps**: each evidence cell that cites `docs/schema.md` cites the new file instead, the text
  quoted unchanged: R02 (*Vendor as a Team record*: `docs/schema/notes.json` `people`; *Equipment
  history*: `notes.json` `equipment_events`; *PM plans and jobs*: `notes.json` `planned`), R03 (*Equipment
  tree*, *Serial numbers*: `notes.json`; *Planned tables*: `notes.json` `planned`), R05 (*Procedures*:
  `notes.json` `planned`; its words "§ Planned: `procedures`" stay a record of the roadmap's day, add
  "(`procedures` built since S075)"). Earlier step files and reviews are records and are not changed.

## 6. API

None.

## 7. Design decisions

- **D1 — A fresh database per run, named from the test run.** `vel_yantra_test_<run>_schemadocs`, dropped
  before and after. Rejected: the dev DB `vel_yantra_master` (KLA's data, and it can lag: the proposal of
  30-10-2026 found it at v35; it is at v41 today, read 30-10-2026, but nothing keeps it so); the backend
  suite's own `vel_yantra_test_<run>_<worker>` (kept between runs, so a migration edited during coding is
  not rebuilt; and it holds test rows).
- **D2 — The notes go into `schema-data.js`, copied by the generator.** The page loads one generated
  script. Rejected: a hand-edited `notes.js` (`window.… = {…}`), which needs no copy step but makes the
  hand-edited file a script, where a stray character breaks the page instead of failing a JSON parse with
  a line number. Consequence: a notes edit needs a `write`; check 2 catches a forgotten one.
- **D3 — Check clauses are included.** Decision 1 named tables, columns, keys and indexes. The checks are
  added because today's *Holds* texts cite them by name (`chk_improvements_watch_from`, …) and an agent
  needs their rules. Risk: their text may differ between 11.4 and 11.8 (§ 5.2, *to verify*). Rejected:
  leave them out (one fewer source of version drift; agents read the migration text). KLA may drop them
  at gate A (Q2).
- **D4 — Integer display widths removed; other types kept.** § 5.2. Rejected: `DATA_TYPE` only (loses
  `varchar(100)`, the enum values and the decimal scale, which agents use); `COLUMN_TYPE` unchanged
  (a server that drops widths would change every int line).
- **D5 — `UK` marks a single-column unique key only.** A composite unique key is shown in the Tables
  view's Indexes, not on a column. Today's hand text marked `open_link` `UK` though its key has two
  columns, while it marks no column of the other composite unique keys (e.g. `uq_model_meters`,
  `uq_units_site_code`); the rule makes all of them alike.
- **D6 — `db_version` is drawn, in System.** Every built table has a notes line, with no exception list.
  Rejected: keep it out of the diagram (today's choice), which needs a hidden-table rule in the check and
  the page for one table without links.
- **D7 — Mermaid by dynamic import; the Tables view needs no network.** § 5.6.1. Rejected: keep the
  static import (an offline page shows nothing at all).
- **D8 — The page's pure functions in `schema-view.js`, tested by vitest in a `node:vm` sandbox.** A
  classic script (a module script from `file://` is refused by Chrome: *fact to verify* in the device
  check) that sets `window.YantraSchemaView`; the test reads the file and runs it with
  `vm.runInNewContext(code, {window: {}})`. Rejected: the functions inline in `schema.html` (untestable);
  Mermaid text built in Python and stored in `schema-data.js` (decision 4 has the page draw; it would
  double the data and its diff).
- **D9 — JSON, not DDL.** SMTW-WebApp-Base names an exported `schema.sql`. JSON is chosen because the page
  and agents read it as data, and one column per line keeps diffs small; a DDL dump would need parsing
  for the page. Departure stated; the base may later name this pattern (§ 9 F2).
- **D10 — No browser test of the page; one manual check.** Playwright can open `file://`, but the
  browser suite is the app's (lanes, backends, seeded databases), and the diagram needs the CDN, which
  the tests must not reach. The pure functions are unit-tested (D8); the loading from disk and the
  drawing are one manual check by KLA at gate B (§ 8.5). Rejected: a spec in `frontend/e2e/` that routes
  the CDN; it tests the app's harness more than the page.
- **D11 — Through `run_test_suite.py`, counted as four checks.** One log, one summary line, the
  `TEST_SUMMARY_FILE` line in the release (CLAUDE-COMMON § Wrapper scripts). Rejected: a plain `uv run`
  (no log, no summary in the release's list).
- **D12 — Exit codes 0 / 1 / 2 as the dependency audit's.** A stale doc (1) and a check that could not
  run (2) need different actions; both fail the release.

## 8. Tests and acceptance

### 8.1 Core (`tooling/tests/test_schema_docs_core.py`, tooling suite)

The test file puts `tooling/schema` on `sys.path` and imports `schema_docs_core`. Rows are small dicts
built in the test.

1. Type normalisation: `int(11)` → `int`; `tinyint(1)` → `tinyint`; `bigint(20) unsigned` →
   `bigint unsigned`; `varchar(100)`, `decimal(14,3)`, `enum('a','b')` unchanged; upper case lowered.
2. Default: SQL NULL → `null`; text `NULL` → `null`; `'manual'`, `1`, `current_timestamp()` kept.
3. Key tags: a PK that is also an FK → `PK,FK`; a single-column unique FK → `FK,UK`; a column in a
   two-column unique key only → `""`.
4. Foreign key `required`: all columns NOT NULL → true; one of two nullable → false; columns in
   `ORDINAL_POSITION` order.
5. Ordering: tables, foreign keys, indexes, checks by name; columns by position; the same rows in a
   shuffled order give the same text.
6. JSON layout: one column per line, the key order of § 4.1, `[]` for empty lists, LF, final newline,
   non-ASCII kept (`−` in a check clause); `json.loads` of the text gives the dict back.
7. `schema-data.js`: starts with the comment line; `window.YANTRA_SCHEMA = ` + the JSON text + `;`, then
   the notes in the fixed layout.
8. Check 1 and 2: equal → passes; CRLF copy of an equal text → passes; one changed line → fails, the
   message names the line number and both texts; missing (`None`) → fails with "is missing".
9. Check 3: a built table without notes; a notes table not built; an unknown area; two areas with one
   name — each fails with its message (§ 5.3).
10. Check 4: a planned name that is built fails; none built passes.
11. `outcome`: four passes → exit 0 and `… 4 passed`; one fail → exit 1 and `3 passed, 1 failed`; not
    completed (the DB message) → exit 2 and the message; the notes not valid JSON → checks 3 and 4 fail,
    and in `write` nothing is to be written.

### 8.2 Shell (`backend/tests/test_schema_docs_shell.py`, backend suite)

Imports `schema_docs` from `tooling/schema` (path added in the test). They need the dev DB container, as
every backend test.

1. The database down: `config.DB_CONFIG` copied with an unused port (monkeypatch) → `main(["check"])`
   returns 2 and prints the "cannot be reached" message; no file is written. The refused connection is
   the first one (no database selected), before any lock (BR1-11).
1b. The guard: a host `db.example.test` (monkeypatch) → exit 2 with the refusing message, and no
   connection is tried (BR1-01).
2. The catalogue reader on the suite's own `TEST_DB` (already migrated by `conftest.py`): the tables
   include `db_version` and `people`; the reader returns the five row sets the core takes; no write. It
   does not build `SCHEMA_DOCS_DB` (keeps the suite fast and free of the lock).

`SCHEMA_DOCS_DB` in `db_names.py` is checked by one more case in test 2: it starts with
`vel_yantra_test_` and ends with `_schemadocs`.

### 8.3 Page functions (`frontend/tests/schemaView.test.js`, vitest)

Loads `../../docs/schema/schema-view.js` (path from the test file) with `fs.readFileSync` and runs it in a
`node:vm` sandbox, then:

1. `tabs`: *Overview* first, then the areas in notes order.
2. `areaTables`: own tables sorted; a table of another area linked to an own table is a neighbour; a
   table linked only to a neighbour is not.
3. `diagramSource` for an area: an own table with every column, a neighbour with its PK columns only,
   `"null"` on an empty-allowed column, the base type (`varchar`, not `varchar(100)`); a link between two
   neighbours absent.
4. Link notation: required → `||--o{`; optional → `o|--o{`; single-column unique FK → `o|--o|`; a
   two-column FK labelled `"option_id, property_id"`.
5. Overview: only keyed columns; every foreign key one link; a table with no notes entry is still drawn.
6. `metaLine`: the migration and the counts.
7. `holdsParts`: `` `a` `` code, `*b*` em, an unpaired `` ` `` stays text, `<b>` stays text.

### 8.4 Acceptance (the coder, in the impl report)

1. `tooling\schema-docs.bat write` then `check` → exit 0, `4 passed`; the files' sizes and line counts.
2. Remove one table's line from `notes.json` → `check` exits 1 naming it; restore.
3. Edit one line of `schema.json` → `check` exits 1 naming the line; `write` restores it.
4. The first `notes.json` comparison of § 5.8 passed (the script's output).
5. The Mermaid text that `schema-view.js` gives for each of today's five tabs, compared with today's
   `TABS` (`git show 12a682e:docs/schema.html`), by a one-off `node` script in the scratchpad: every
   difference listed and explained (the expected ones in § 5.4; any other is a bug or a hand-edit error,
   said which).
6. `tooling\run-tooling-tests.bat`, `tooling\run-backend-tests.bat tests/test_schema_docs_shell.py`,
   `tooling\run-frontend-tests.bat tests/schemaView.test.js`, then `tooling\run-tests.bat` once, green.
7. `tooling\release-tests.bat` is **not** run by the coder (the Full browser level runs only in the
   release, at pre-flight, or when KLA asks); the coder shows the changed lines and runs the check
   command as the worktree would (`set YANTRA_TEST_RUN=s078c1` then `tooling\schema-docs.bat check`).

Existing tests: none reads `docs/schema.md`, `docs/schema.html` or `TABS` (grep 30-10-2026 over
`backend`, `frontend`, `tooling`). No browser spec is changed or run (no app screen or API changes). The
always-check tests (`test_role_matrix`, `conftest.py` `_TABLES`, the `db_down` fixture, the
`test_migration_*` tests) are untouched: no table, key or migration changes.

### 8.5 Manual check (KLA, at gate B)

- [ ] **important** — On KLA's laptop, in Chrome and in Edge, open `docs/schema.html` from the file
  explorer (a `file://` address, no server). See: the meta line "Migration v41 · 46 tables, 75 links";
  the tabs Overview, Equipment, Team and access, Tickets, System; each diagram draws; `Show tables` lists
  the tables with columns, and the Overview's planned tables. Then turn Wi-Fi off and reload: the tables
  still show, the diagram shows its internet message. Network: any (offline for the last part).

This is a check of a developer document, not of the app on a device, so it is not a row of
`docs/steps/device-checks.md` (the IT Admin list).

## 9. Open questions and assumptions

**Questions for KLA (gate A)** — answered 30-10-2026 by KLA: one step (no cut); Q1 (a) copy the texts whole; Q2 keep the check clauses.

- **Q1 — The table texts.** Decision 3 says "one sentence on what it holds". Today's *Holds* texts are
  often many sentences (`improvements` about 250 words), with the rules and the step that made each
  column. Options:
  - **(a) copy them whole now (recommended)**: nothing is lost; shortening is a later, reviewed edit of
    `notes.json`, and the CHECKs and indexes the texts repeat are now in `schema.json`;
  - (b) cut each to one sentence in this step: the long texts go to git history only, and the coder
    would judge what to keep;
  - (c) one sentence plus a second key `details` with the rest: two fields to keep.
- **Q2 — Check clauses in `schema.json`** (D3): keep (recommended) or leave out.

**Assumptions**

- A1 — A fresh build of v20–v41 takes seconds (the backend suite builds one per worker per new run);
  *to verify* by the coder's timing.
- A2 — `schemadocs` is never a pytest-xdist worker name (they are `gw<n>`, or `main`).
- A3 — MariaDB 11.8 prints the same `COLUMN_TYPE`, `COLUMN_DEFAULT` and `CHECK_CLAUSE` text as 11.4 after
  § 5.2's normalisation: *to verify* when the dev DB moves to 11.8 (queued). If not, one `write` settles
  it.
- A4 — The page opened from disk may load classic scripts by relative path and a module by dynamic
  `import()` from https (today's page already imports Mermaid from https on `file://`); a module
  *script file* from `file://` would be refused (D8). Confirmed by § 8.5.

**Follow-ups for smtw-common (synced files, not edited here)**

- F1 — `.claude/skills/smtw-review/SKILL.md` names `docs/Schema.md` and `docs/schema.sql` as the schema
  docs; it could read "the repo's schema docs (its CLAUDE.md names them)".
- F2 — `.claude/SMTW-WebApp-Base.md` § layout could name the generated-schema pattern (a JSON from the
  migrations, a notes file, a check at gate B and in the release) beside or instead of `schema.sql`.
- F3 — `.claude/agents/code-reviewer.md` (the docs pass) speaks of "the repo's schema doc"; with a
  check command the reviewer could be told to run the repo's command when its CLAUDE.md names one.

## 10. Amendments

None.

## Review log

| Finding | Answer | Change |
|---|---|---|
| BR1-01 (minor) the drop has no guard on host and name | Accepted, option (a) | § 5.1 item 3: the local-host and `_schemadocs` guard, exit 2; item 4 mirrors `_recreate_database`; § 8.2 test 1b |
| BR1-02 (minor) the gate B check's tree and run name | Accepted, option (a) | § 5.7 item 2 and the § 5.10 schema row: the tree with the step's changes, the step's `YANTRA_TEST_RUN` |
| BR1-03 (minor) the check filter column and the column-level check | Accepted, option (a) | § 5.2 filter `CONSTRAINT_SCHEMA`, `LEVEL` read and written (§ 4.1 check line); § 5.9 names `payload` as the second exception |
| BR1-04…BR1-11 (nits) | All accepted | BR1-04, BR1-11: § 5.1 item 6 and § 8.2 test 1; BR1-05: § 5.5 *Output*; BR1-06, BR1-07: § 5.3; BR1-08: § 2, the *to verify* marks removed; BR1-09: § 5.10 schema row; BR1-10: § 5.7 item 3 |

Sections changed in round 1: § 2, § 4.1, § 5.1, § 5.2, § 5.3, § 5.5, § 5.7, § 5.9, § 5.10, § 8.2, Review log.
