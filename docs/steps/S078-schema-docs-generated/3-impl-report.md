```
Step: S078 — Schema docs from the migrations
Doc: impl-report
Author: coder (Opus 5.5)
Date: 30-10-2026
```

# S078 — Implementation report

**Result: built as briefed; every test and the schema docs check are green.** `tooling\schema-docs.bat write|check`
makes `docs/schema/schema.json` and `schema-data.js` from a fresh database built from `_MIGRATIONS`,
and checks them and `notes.json`. The page `docs/schema.html` now draws from the data and has a
Tables view that works offline. `docs/schema.md` is prose only. Every live reference is updated. No
app code, migration, RBAC key or dependency changed.

**This work started in a stopped run.** A first coder was stopped part-way (KLA paused it for a
release). Its work is commit `d490e69 WIP;`: `backend/tests/db_names.py`, the core, the shell, the
wrapper, the core's tests and first versions of the three `docs/schema/` files. This run reviewed it
against the brief and **kept all of it unchanged**:

- The core, shell and wrapper follow § 4, § 5.1–5.5 point by point: the guard before any
  connection, the lock, DROP and CREATE as `_recreate_database`, `init_db` on a copy of
  `DB_CONFIG`, the drop in a `finally`, the notes read before the build, the messages word for word.
- The tooling tests (24 tests of the core, § 8.1 items 1–11) pass.
- The generated files were from a complete run: a fresh `write` in this run changed no byte of them
  (`git status docs/schema` empty after it).
- `notes.json` passed the § 5.8 comparison (below).

This run added the page, the shell test, the vitest, the release hook, the new `schema.md`, the
reference updates and the comparisons.

## 1. What was built

- **The generator and the check** (from the stopped run, verified): `tooling\schema-docs.bat write`
  builds `vel_yantra_test_<run>_schemadocs` from the migrations, reads `information_schema`, writes
  `schema.json` and `schema-data.js`, then runs the four checks. `check` runs the four checks and
  writes nothing. Exit 0 / 1 / 2.
- **The page** `docs/schema.html`: no data in it. It loads `schema/schema-data.js` and
  `schema/schema-view.js`, draws the five tabs as Mermaid diagrams (Mermaid by dynamic `import()`),
  and has **Show diagram** / **Show tables** buttons. The Tables view lists, per area, each table
  with its *holds* text and four small tables (Columns, Indexes, Foreign keys, Checks); on the
  Overview, all tables with their area, then the planned tables.
- **`docs/schema/schema-view.js`**: the page's pure functions (`tabs`, `areaTables`,
  `diagramSource`, `metaLine`, `holdsParts`) as a classic script.
- **The release hook**: `tooling\release-tests.bat` runs `schema-docs.bat check` in its worktree
  after the unit suites.
- **`docs/schema.md`** rewritten as prose (§ 5.9).
- **Tests**: `backend/tests/test_schema_docs_shell.py` (4 tests), `frontend/tests/schemaView.test.js`
  (9 tests).

## 2. How it works

**The command.** The wrapper sets the run name and the log, then runs the shell through
`run_test_suite.py`, so the whole output is in the log and the last line is the standard summary.
The shell:

1. refuses a non-local host or a name not ending in `_schemadocs` (exit 2, before any connection);
2. reads and parses `notes.json` (an invalid file ends the run at once: checks 3 and 4 fail);
3. connects with no database selected, takes `GET_LOCK("yantra_schema_docs:<db>", 60)`, drops and
   creates the database, runs `local_db.init_db`, reads the five row sets, reads `MAX(version)`,
   drops the database in a `finally` and releases the lock;
4. hands the rows to the pure core, which normalises them (§ 5.2), builds the texts, runs the
   checks and returns the exit code and the lines.

**The page.** `schema-data.js` sets `window.YANTRA_SCHEMA` and `window.YANTRA_SCHEMA_NOTES`;
`schema-view.js` sets `window.YantraSchemaView`. The inline script builds the tabs, the bar and the
Tables view with `createElement` and `textContent` only. The only `innerHTML` is Mermaid's SVG
(`securityLevel: "strict"`), as before. Mermaid is imported the first time a diagram is drawn; a
failed import shows the offline message, and the Tables view never needs it. The selected tab
(`yantra-schema-tab`, by name) and view (`yantra-schema-view`) are kept in `localStorage`, in
try/catch. When the data is missing, the page shows the § 5.6.4 message and no tabs.

**The diagram rules** (§ 5.4) in `schema-view.js`:

- Overview: every table with its keyed columns; every foreign key as a link.
- Area tab: own tables with every column, neighbours (tables of another area linked to or from an
  own table) with their primary-key columns, every link with an own end and both ends drawn.
- Link: `||` required / `o|` optional on the parent side; `o|` on the child side when the key's
  columns alone form a unique key, else `o{`; the label is the key's columns joined by `, `.
- Order: own tables by name, then neighbours by name; links by parent, child, label.

## 3. Files touched

From the stopped run (`d490e69`), kept unchanged:

| File | What |
|---|---|
| `backend/tests/db_names.py` | `SCHEMA_DOCS_DB = vel_yantra_test_<run>_schemadocs` |
| `tooling/schema/schema_docs_core.py` | new: the pure core (normalising, texts, four checks, guard, messages, outcome) |
| `tooling/schema/schema_docs.py` | new: the shell (guard, lock, build, read, drop, write, print) |
| `tooling/schema-docs.bat` | new: the wrapper |
| `tooling/tests/test_schema_docs_core.py` | new: the core's tests (§ 8.1) |
| `docs/schema/notes.json` | new: hand-edited notes, first filled from the old docs |
| `docs/schema/schema.json`, `docs/schema/schema-data.js` | new: generated (a fresh `write` in this run left them byte for byte the same) |

This run:

| File | What |
|---|---|
| `docs/schema/schema-view.js` | new: the page's pure functions |
| `docs/schema.html` | rewritten: no `TABS`; loads the data and the functions; Tables view; Mermaid by dynamic import |
| `docs/schema.md` | rewritten as prose (§ 5.9) |
| `backend/tests/test_schema_docs_shell.py` | new: the shell tests (§ 8.2) |
| `frontend/tests/schemaView.test.js` | new: the page functions' tests (§ 8.3) |
| `tooling/release-tests.bat` | runs the check after the unit suites; its result fails the release |
| `.claude/CLAUDE.md` | § 5.10 texts: *Stack*, *Dev commands*, § Pre-flight (two entries), *Plan and domain docs*, § Docs to keep current, § SMTW-Review |
| `docs/Plan.MD` | § 5 points to the new files |
| `docs/roadmap/R02-amc-contracts.md`, `R03-pm.md`, `R05-rca.md` | evidence cells cite `docs/schema/notes.json` |
| `docs/steps/INDEX.md` | S078 row status; the queued *Module and schema docs* row's note |
| `docs/steps/S078-schema-docs-generated/1-brief.md` | status |
| `docs/steps/S078-schema-docs-generated/3-impl-report.md` | this report |

## 4. Decisions taken

1. **Links in an area tab need both ends drawn.** The brief says a table with no notes entry is
   "drawn only in the Overview". A link from an own table to such a table would make Mermaid draw
   it anyway, as a bare box. So an area tab draws a link only when both ends are own or neighbour
   tables, and a table with no valid area is never a neighbour. The vitest showed the gap: its area
   test failed on the first version (`units ||--o{ orphans`), and passes after the fix. No effect
   on today's data (every table has an area).
2. **One to one also when the key's columns equal the primary key.** The brief says "the key's
   columns alone form a unique key"; a primary key is one. No table has such a key today, so the
   output is the same either way.
3. **The Overview's Tables view has a heading "All tables"** above the table of every built table,
   to match the "Planned tables (not built yet)" heading below it. The brief names only the second.
4. **The Default column shows nothing for no default** (JSON `null`), not "None" or "NULL": the
   JSON does not tell "no default" from "DEFAULT NULL" apart (§ 5.2), and an empty cell claims
   neither.
5. **`docs/schema.md` names bullet: one sentence added.** 28 indexes are named `fk_…`: MariaDB
   made them for the foreign key of the same name. Without the sentence the bullet reads as if
   those break the rule. Checked by a scratch script over `schema.json`: the only names that break
   the rule are `ux_access_log_sighting` and `payload`, as the brief says; 75 of 75 keys are
   `RESTRICT`.
6. **Roadmaps: the full path `docs/schema/notes.json` in every cell**, where § 5.10 writes
   `notes.json` for short. R02's *PM plans and jobs* row cited `docs/schema.md` in its state cell
   too; that cite is also changed (same claim, same file). R05: "`docs/schema/notes.json`
   `planned`; § Planned: `procedures`, … (`procedures` built since S075)".
7. **The page's title stays "Yantra Schema"**, and the page keeps its colours and layout.
8. **`MigrationBlocked` is not named apart in the shell.** It is a subclass of
   `local_db.DBUnavailable`, which the shell catches, so § 5.5's three exception types are all
   caught.
9. **No `npx vite build`**: nothing under `frontend/src` changed; the only frontend file is a test.

No departure from the brief's rules, texts or files.

## 5. Not done, deferred or assumed

- **A1, the build time: measured.** A `write` or `check` run takes **16–17 s** end to end (the
  wrapper, `uv` start, the v20–v41 migrations on a fresh database, the read, the drop): four runs
  on 30-10-2026, 17 s, 16 s, 15 s, 16 s. The brief guessed "about 5 s". The release tests and gate
  B each gain about 16 s.
- **A3** (MariaDB 11.8 prints the same texts): not verifiable here; the dev DB runs 11.4.13.
- **No browser test of the page** (D10). In its place this run made a one-off headless look with
  the repo's own Playwright (`scratch/s078/smoke_page.cjs`, not committed), from `file://` on a
  412 px wide window:
  - online: the meta line "Migration v41 · 46 tables, 75 links · …", the five tabs, each diagram
    drawn (46, 28, 15, 21 and 5 entities), the Tables view (Overview 2 sections and 57 rows,
    Equipment 20 sections, System 5), zoom buttons hidden in the Tables view, no sideways scroll,
    no console error;
  - offline (network off): each tab shows "The diagram could not be drawn. Check the internet
    connection, then reload the page. The tables work without internet: select Show tables.", and
    the Tables view is the same as online.
  This does not replace KLA's check of § 8.5 (Chrome and Edge on his laptop, from the file
  explorer).
- **Follow-ups F1–F3** (synced files in smtw-common): not edited, as briefed.
- **`docs/steps/device-checks.md`**: no row, as briefed (a developer document, not the app).

## Acceptance (§ 8.4)

1. **`write` then `check`**: both exit 0, `Schema docs at migration v41: 4 passed`. Files:
   `schema.json` 1 120 lines, 86 966 bytes; `schema-data.js` 1 192 lines, 109 120 bytes;
   `notes.json` 71 lines, 21 984 bytes. All LF (`git ls-files --eol`: `w/lf`). The database
   `vel_yantra_test_s078c1_schemadocs` is gone after each run (`SHOW DATABASES LIKE
   '%schemadocs%'` empty).
2. **One notes line removed** (`trades`): `check` exits 1:
   `docs/schema/notes.json has no line for table trades. Add "trades": {"area": "<one of: Equipment, Team and access, Tickets, System>", "holds": "<what it holds>"} under "tables", then run tooling\schema-docs.bat write.`
   It also names `schema-data.js` stale at line 1174 (the notes copy), as D2 intends. Count line
   `2 passed, 2 failed`. The file was restored.
3. **One line of `schema.json` edited** (`people.email` `varchar(254)` → `varchar(200)`): `check`
   exits 1: `docs/schema/schema.json is stale: line 691 differs (on disk: … "varchar(200)" …;
   generated: … "varchar(254)" …). Run tooling\schema-docs.bat write and commit the result.` Then
   `write` exits 0 and restores it (`git status` clean for the file).
4. **The § 5.8 comparison** (`scratch/s078/compare_notes.py`, against `git show 1643f65:docs/schema.md`
   and `:docs/schema.html`) passed:

   ```
   ok   § Built tables: 46 rows, each holds compared word for word
   ok   § Planned tables: intro and 11 rows compared word for word
   ok   TABS: overview note and 4 area names and notes, in order
   ok   TABS areas: 45 tables with a single own tab match
   ok   counts: 46 tables in notes.json, 46 built

   PASSED: 0 problem(s)
   ```

   `db_version`'s text is compared with "(internal; not in the diagram)" changed to "(internal)", as
   § 5.8 says; it is in no old tab and is in System (D6). The old `schema.md`'s other prose: the
   intro bullets and § Conventions are in the new `schema.md`; the history lines are dropped
   (decision 5); "Indexes are not listed here" and the overview's legend are replaced by the JSON's
   indexes and the page's meta line.
5. **The Mermaid comparison** (`scratch/s078/compare_tabs.cjs`, the five tabs of `schema-view.js`
   against the old `TABS` of `1643f65`; the brief names `12a682e`, which has the same `TABS`, as
   only S078's files changed since). Output, then each difference explained:

   ```
   === Overview: old 303 lines, new 302 lines; entities 45 -> 46; links 75 -> 75
     + entity db_version: int version PK
     - improvement_events:    varchar event
     - improvement_tickets:    tinyint open_link UK "null"
     - improvement_whys:    smallint position
     ~ improvements: same column lines, other order
     ~ entity order differs (...): equipment_property_values, equipment_types, failure_causes, ...
     + link  equipment_models o|--o{ equipment : "model_id, class_id"
     + link  equipment_types o|--o{ equipment : "type_id, class_id"
     + link  equipment_types o|--o{ equipment_models : "type_id, class_id"
     + link  property_options o|--o{ equipment_property_values : "option_id, property_id"
     + link  property_options o|--o{ model_property_values : "option_id, property_id"
     - link  equipment_models o|--o{ equipment : "model_id"
     - link  equipment_types o|--o{ equipment : "type_id"
     - link  property_options o|--o{ model_property_values : "option_id"
     - link  property_options o|--o{ equipment_property_values : "option_id"
     - link  equipment_types o|--o{ equipment_models : "type_id"
     ~ link order differs (new: by parent, child, label)
   === Equipment: old 316 lines, new 320 lines; entities 27 -> 28; links 43 -> 45
     + entity improvements: int id PK
     ~ entity order differs (...): equipment_property_values, equipment_types, manufacturers, ...
     + link  equipment ||--o{ improvements : "equipment_id"
     + link  units ||--o{ improvements : "unit_id"
     (+ the same five relabelled links as the Overview, - their five old labels)
     ~ link order differs (new: by parent, child, label)
   === Team and access: old 95 lines, new 102 lines; entities 13 -> 15; links 13 -> 15
     + entity improvement_actions: int id PK
     + entity improvements: int id PK
     + link  people ||--o{ improvement_actions : "owner_id"
     + link  people ||--o{ improvements : "lead_id"
     ~ link order differs (new: by parent, child, label)
   === Tickets: old 252 lines, new 251 lines; entities 21 -> 21; links 35 -> 35
     - improvement_tickets:    tinyint open_link UK "null"
     + improvement_tickets:    tinyint open_link "null"
     ~ entity order differs (...): people, procedures
     ~ link order differs (new: by parent, child, label)
   === System: old 40 lines, new 44 lines; entities 4 -> 5; links 0 -> 0
     + entity db_version: int version PK | varchar description "null" | datetime applied_at "null"
   ```

   | Difference | Kind | Why |
   |---|---|---|
   | `db_version` in the Overview and System | expected (§ 5.4, D6) | every built table has an area now |
   | `open_link` loses `UK` (Tickets); leaves the Overview | expected (§ 5.4, D5) | its unique key `uq_improvement_tickets_open` has two columns; with no key it is not a keyed column |
   | Overview drops `varchar event`, `smallint position` | expected (§ 5.4) | hand-edit error: non-key columns in the keyed-only Overview |
   | `property_options` links labelled `option_id, property_id` | expected (§ 5.4) | the key has two columns |
   | `equipment_models → equipment` labelled `model_id, class_id`; `equipment_types → equipment` and `equipment_types → equipment_models` labelled `type_id, class_id` | **not in the brief's list; a hand-edit error** | the same rule as the line above: these three keys have two columns (a model or type must be of the item's class, S004/S012). The old text labelled them by the first column only |
   | Entity order | expected (§ 5.4) | by name: own, then neighbours |
   | Link order | expected (§ 5.4 *Order*) | the old text ordered by child table; the rule orders by parent, child, label |
   | Overview `improvements`: `lead_id` moves after `follow_up_of_id` | **not in the brief's list; a hand-edit error** | the old Overview had `lead_id` third; its Tickets tab and the migrations have it last (column position). The new text follows the column position everywhere |
   | Equipment tab: `improvements` as a neighbour, with `equipment ||--o{ improvements` and `units ||--o{ improvements` | **not in the brief's list; a hand-edit error** | S067 (v36) added the two keys; the hand edit drew them in the Tickets tab only, not in the Equipment tab of the parent tables |
   | Team tab: `improvements`, `improvement_actions` as neighbours, with `people ||--o{ improvements : "lead_id"` and `people ||--o{ improvement_actions : "owner_id"` | **not in the brief's list; a hand-edit error** | S067 and S070 added the keys to `people`; the hand edit missed the Team tab |

   No difference is a bug of `schema-view.js`: each new line follows from the § 5.4 rules and the
   catalogue.
6. **Tests**: see § Tests run below.
7. **The release hook, not run** (as briefed). The changed lines of `tooling\release-tests.bat`:

   ```bat
   call "%WT%\tooling\run-tests.bat"
   set UNIT_RESULT=%ERRORLEVEL%
   :: run-tests.bat's setlocal dropped its TEST_SUMMARY_FILE: set it again for the schema docs line
   set "TEST_SUMMARY_FILE=%YANTRA_TEST_LOG_DIR%\test-summary-release.txt"
   call "%WT%\tooling\schema-docs.bat" check
   set SCHEMA_RESULT=%ERRORLEVEL%
   call "%WT%\tooling\run-e2e-tests.bat" --level=full
   ...
   if not "%SCHEMA_RESULT%"=="0" (
     echo Release tests: the schema docs are stale or were not checked ^(see scratch\release-tests\schema-docs-release.log^).
     set RELEASE_RESULT=1
   )
   ```

   Plus the header comment (step 3 and the exit code). The check as the worktree would run it
   (`YANTRA_TEST_RUN=s078c1`, `tooling\schema-docs.bat check`): see § Tests run.

## Tests run

All with `YANTRA_TEST_RUN=s078c1`, 30-10-2026.

- While coding: `tooling\run-tooling-tests.bat` 224 passed (the 24 schema docs tests among them);
  `tooling\run-backend-tests.bat tests/test_schema_docs_shell.py -n 0` 4 passed;
  `tooling\run-frontend-tests.bat tests/schemaView.test.js` 9 passed (one red run first, decision 1).
- **The full run, once** (`tooling\run-tests.bat`): **ALL SUITES: PASSED** — backend 4055 passed
  (241 s: the first run of the run name `s078c1`, so each worker built its database fresh),
  frontend 377 passed, tooling 224 passed.
- **The final check** (§ 8.4 item 7, as the worktree runs it): `tooling\schema-docs.bat check` →
  exit 0, `Schema docs at migration v41: 4 passed`, `== schema-docs: PASSED in 21 s: 4 passed`.
  With no mode it prints `Usage: tooling\schema-docs.bat write|check` and exits 2.

No browser run: no app screen or API changed (§ 8.4). The always-check tests are untouched: no
table, key or migration changed.

## Docs updated

- `docs/schema.md`: rewritten as prose (§ 5.9).
- `docs/schema/notes.json`, `schema.json`, `schema-data.js`: new; `write` then `check` exit 0.
- `docs/schema.html`: rewritten (the page is part of the step and a doc).
- `.claude/CLAUDE.md`: the § 5.10 texts (*Stack*, *Dev commands*, § Pre-flight *Failure logs* and
  *Re-run failing tests*, § Step workflow *Plan and domain docs*, the schema row of § Docs to keep
  current, § SMTW-Review *Schema docs (S078)*).
- `docs/Plan.MD` § 5: the § 5.10 text.
- `docs/roadmap/R02-amc-contracts.md`, `R03-pm.md`, `R05-rca.md`: the evidence cells.
- `docs/steps/INDEX.md`: the queued *Module and schema docs* row says the schema half is done by
  S078; the S078 row's status.
- `docs/steps/device-checks.md`: none, because the one manual check is of a developer document
  (§ 8.5), not of the app.
- `backend/example_secrets_app.py`, `docs/Keycloak.md`, the domain docs: none, because the step adds
  no secret, role or maintenance rule.

## Manual checks

- [ ] **important** — On KLA's laptop, in Chrome and in Edge, open `docs/schema.html` from the file
  explorer (a `file://` address, no server). See: the meta line "Migration v41 · 46 tables, 75 links";
  the tabs Overview, Equipment, Team and access, Tickets, System; each diagram draws; `Show tables`
  lists the tables with columns, and the Overview's planned tables. Then turn Wi-Fi off and reload:
  the tables still show, the diagram shows its internet message. Network: any (offline for the last
  part). (KLA, at gate B; not a row of `docs/steps/device-checks.md`.)

## Verify review r2: CR2-01, fixed by the orchestrator

- **CR2-01 (nit) — Fixed.** `tooling/schema/schema_docs.py`: the final `DROP DATABASE` and `RELEASE_LOCK` now have
  their own `try`. A failed drop is kept and named as before; a failed lock release is only logged (the lock
  ends with the session when the connection closes), so it no longer reads as "could not be dropped".
  Test: `backend/tests/test_schema_docs_shell.py::test_a_failed_lock_release_is_not_a_failed_drop`; on the
  old code a failed release took the drop path. Run `s078gb`: shell tests 8 passed; `tooling\schema-docs.bat
  check` 4 passed.

## Feedback

- hindrance: a Node script in `scratch/` cannot `require("@playwright/test")`, since Node resolves
  modules from the script's folder, not from `frontend/`; it needed `NODE_PATH=frontend/node_modules`
  (1 run lost, `scratch/s078/smoke_page.cjs`).
- hindrance: Playwright's `context.route("https://**", …)` did not stop the dynamic `import()` from a
  `file://` page; the offline case needed `context.setOffline(true)` (1 run lost, the same script).
- idea: a resumed step would start faster with a short hand-over note from the stopped coder (what is
  done, what is verified, the next action); here the WIP had to be re-read and re-run whole to know
  that it was complete (about 10 min, `d490e69`).
- rule: the coder's rule "the full suite once" costs 4 minutes on a new run name, because each
  backend worker migrates a fresh database (241 s against about 40 s; `scratch/backend-tests-s078c1.log`);
  a coder given a run name used once before would not pay it.

## Fix round 1

All four nits of `4-code-review-r1.md` fixed. Run name `s078f1`. No browser run (no app screen changed).

- **CR1-01 Fixed.** `docs/schema.html`: the svg-pan-zoom `<script src>` tag is gone. A new `loadPanZoom()` adds the script element on the first drawing, and `loadMermaid()` waits for it together with Mermaid (`Promise.all`). I chose "inside `loadMermaid()`" over `async`: with `async` a cached Mermaid could finish before the script and `svgPanZoom` would be undefined at the draw; here the draw always has both. A load error resets the promise like a Mermaid error, so the same message shows and a later click retries. The offline Tables view no longer waits for the CDN. Check: `scratch/s078/smoke_page.cjs` (headless, `file://`) online: 5 diagrams drawn (svg 1 each), no errors; offline: tables show, the diagram shows the brief's message. No new test (the smoke script is not committed).
- **CR1-02 Fixed.** `schema_docs.py` `build_and_read`: the final `DROP` and `RELEASE_LOCK` run in their own try inside the `finally`; a failure is kept and raised only after the body succeeded, so it never hides an earlier error (the migration-failed message stays). The outer `except` maps only errors 2003, 2006, 2013 (`CONNECTION_ERRORS`) to the "cannot be reached" message; any other server error gives the new `core.database_error_message` ("The schema docs were not built. The database refused a command: <detail>. Check the dev database and the user's rights, then run the command again."). A failed final drop gives the new `core.cleanup_failed_message` ("… The database <name> could not be dropped: <detail>. Drop <name> by hand, then run the command again."). All exit 2. Tests (`backend/tests/test_schema_docs_shell.py`, a fake cursor): `test_a_ddl_error_other_than_1044_gives_its_own_message`, `test_a_failed_final_drop_is_named_and_does_not_say_unreachable`, `test_a_failed_drop_does_not_hide_the_migration_failure`. Red: with the old `schema_docs.py` (from `refs/steps/S078`) the first two fail on `assert 'cannot be reached' not in …` (the output of the third was cut off in my run, so I did not see its red). Green: 7 passed with the fix.
- **CR1-03 Fixed.** `schema_docs_core.py` `parse_notes` now calls `_wrong_type`: `tables` must be an object; `areas` and `planned` must be lists of objects; `tables` in a planned entry must be a list. A missing key or `null` counts as none. The message is `docs/schema/notes.json is not valid JSON: <what>. Fix the file, then run the command again.`, so checks 3 and 4 fail and nothing is written. Tests (`tooling/tests/test_schema_docs_core.py`): `test_notes_wrong_type_under_a_key_is_a_notes_problem` (6 cases), `test_notes_with_right_types_still_parse`. Red: with the old core 6 failed (the six cases); green: 231 passed. (My first draft used `or {}` and let `"tables": []` through; the test caught it.)
- **CR1-04 Fixed.** `tooling/release-tests.bat`: the comment now reads "Every failed part prints its line, so the end of the output shows every fault."

Results: `run-tooling-tests.bat` 231 passed; `run-backend-tests.bat tests/test_schema_docs_shell.py` 7 passed; `run-frontend-tests.bat tests/schemaView.test.js` 9 passed; `tooling\schema-docs.bat check` exit 0, "Schema docs at migration v41: 4 passed" (23 s). Generated files unchanged.

Docs updated: none changed by this round (no doc describes these messages or the script tag).

### Feedback (round 1)

- none
