```
Step: S078 — Schema docs from the migrations
Doc: code-review r1
Author: code-reviewer (Opus 5.5)
Date: 30-10-2026
```

# S078 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The step is built as briefed. All three unit
suites are green, and `tooling\schema-docs.bat check` exits 0. Four nits remain.

**What I reviewed.** Part of the code was committed as `d490e69 WIP;` before the release v0.1.14, so
`step_snapshot.py diff S078` shows only the second half. I reviewed the whole step from the brief's
baseline: `git diff 1643f65 refs/steps/S078 -- . ':!docs/steps/S078-schema-docs-generated'`
(22 files; `VERSION` and `CHANGELOG.md` come from the release commits and are ignored). The working
tree equals the snapshot `401c039` (`git diff refs/steps/S078` shows only the untracked files).
I read every code file in full: `tooling/schema/schema_docs_core.py`, `tooling/schema/schema_docs.py`,
`tooling/schema-docs.bat`, `tooling/release-tests.bat`, `backend/tests/db_names.py`,
`docs/schema/schema-view.js`, `docs/schema.html`, `backend/tests/test_schema_docs_shell.py`, the
names and set-up of `tooling/tests/test_schema_docs_core.py` and `frontend/tests/schemaView.test.js`,
the new `docs/schema.md`, and the doc diffs. I checked the generated files by shape only.

## Tests run

All with `YANTRA_TEST_RUN=s078cr1`, 30-10-2026.

- `tooling\run-tests.bat`: **ALL SUITES: PASSED**. Backend 4055 passed (256 s, a new run name),
  frontend 377 passed, tooling 224 passed.
- `tooling\schema-docs.bat check`: exit 0, `Schema docs at migration v41: 4 passed`,
  `== schema-docs: PASSED in 78 s`. It ran at the same time as the backend suite, so the time is
  high. The coder measured 15–21 s alone.
- Browser tests: none due. No app screen or API changed; the only frontend file is a unit test. No
  `npx vite build` is due, because nothing under `frontend/src` changed.
- A scratchpad script (`check_tabs.py`, read-only) compared the old `TABS` and `schema.md` of
  `1643f65` with the new files (results below).

## Nits

- **CR1-01** (nit) `docs/schema.html:83`: the svg-pan-zoom `<script src>` is parser-blocking. On a
  network that drops packets to the CDN instead of refusing them, the page stays blank until the
  connection times out, so the offline Tables view waits too. Add `async` (it is used only after
  Mermaid loads), or load it inside `loadMermaid()`. The brief said "as today", so this is optional.
- **CR1-02** (nit) `tooling/schema/schema_docs.py:83` and `:111`: a DDL error other than 1044 (for
  example a failed `DROP DATABASE`) falls through to the outer `except` and prints "The dev database
  cannot be reached". Also, a failed `DROP` in the inner `finally` replaces an earlier
  migration-failed message with that text. Map only connection errors (2003, 2006, 2013) to
  `unreachable_message`, and give other errors the server's text.
- **CR1-03** (nit) `tooling/schema/schema_docs_core.py:184-187`: `notes.json` with a wrong type under
  a key (for example `"tables": []`) raises `AttributeError` in `_notes_lines` before the checks run,
  so the user sees a traceback, not a notes message. Check in `parse_notes` that `tables` is an
  object and `areas` and `planned` are lists, with the "not valid JSON" message form.
- **CR1-04** (nit) `tooling/release-tests.bat:67`: the comment "Both lines print when both parts
  failed" is out of date now that there are three parts. Write "Every failed part prints its line".

## Manual checks

The impl report's `## Manual checks` carries the brief's one important check (§ 8.5) as an unticked
box. It is still due:

- [ ] **important** — KLA, on his laptop, in Chrome and Edge: open `docs/schema.html` from the file
  explorer. Check the meta line "Migration v41 · 46 tables, 75 links", the five tabs, each diagram,
  `Show tables` with the planned tables. Then turn Wi-Fi off and reload: the tables still show, and
  the diagram shows its internet message.

## Checked and found consistent

- **The guard and `vel_yantra_master`.** `main` reads `config.DB_CONFIG` inside the call and replaces
  `database` with `SCHEMA_DOCS_DB`. `core.check_target` refuses a host outside
  `("localhost", "127.0.0.1")` and a name without `_schemadocs`, before any connection.
  `SCHEMA_DOCS_DB` always ends in `_schemadocs` (`db_names.py:45`). `init_db` gets the same copy,
  and `get_local_db` connects to `config["database"]`. Nothing in the shell names
  `vel_yantra_master`. The test `test_guard_refuses_a_remote_host_before_any_connection` patches
  `pymysql.connect` to fail if called.
- **The lock and the drop (§ 5.1).** `GET_LOCK(named_lock("yantra_schema_docs", db), 60)` comes
  before the drop. The drop and `RELEASE_LOCK` are in a `finally`, also after a failed migration.
  `init_db`'s own lock has another name, so the two never wait on each other. A lock that cannot be
  got gives exit 2 with the brief's message. `MAX(version)` is compared with `LATEST_VERSION`.
- **Pure core and outcome (§ 5.5).** The core has no I/O, clock or framework import. `outcome`
  decides the exit code and the lines: 0 all passed, 1 a check failed, 2 not completed with
  `Schema docs: not completed`. An invalid `notes.json` fails checks 3 and 4, counts 1 and 2 as
  failed, and ends before the build; `write` then writes nothing. The shell catches only
  `pymysql.MySQLError`, `DBUnavailable` (decision 8: `MigrationBlocked` is its subclass, correct)
  and its own `NotCompleted`; other errors show a traceback. The wrapper rejects a wrong or missing
  mode with exit 2. The child's stdout is UTF-8 (`run_test_suite.py` sets `PYTHONIOENCODING`), so
  a message with a non-ASCII character prints safely.
- **Stable output (§ 4.1, § 5.2).** Tables, foreign keys, indexes and checks are sorted by name;
  columns by `ORDINAL_POSITION`; key order is fixed. `_write_text` writes LF with `newline=""`.
  `git ls-files --eol` shows `i/lf w/lf` for the three files. The check turns CRLF into LF before
  it compares. A fresh `check` after the coder's run found no difference.
- **Generated files' shape.** `schema.json` starts with `_note`, `migration: 41`, `tables`. `people`
  matches the brief's § 4.1 example line for line. `task_queue` has the column-level check
  `payload` with `level: "column"`. `improvement_tickets.open_link` has key `""`, and
  `improvements.follow_up_of_id` has `FK,UK`. `schema-data.js` starts with the comment line, then
  `window.YANTRA_SCHEMA = …;` and `window.YANTRA_SCHEMA_NOTES = …;`, one entry per line.
- **The notes migration (§ 5.8).** My script compared the `holds` texts of `improvements` (2004
  characters), `meter_readings`, `improvement_tickets`, `equipment`, `tickets` and `task_queue` with
  their cells in `git show 1643f65:docs/schema.md`. All six are equal. No holds text has an unpaired
  `*` outside backticks, so `holdsParts` cannot italicise a wrong part. § Conventions is copied word
  for word into the new `schema.md`.
- **The diagram rules (§ 5.4) and the four extra differences (§ 8.4 item 5).** `schema-view.js`
  follows the rules: own tables by name, then neighbours by name; links by parent, child, label;
  `||`/`o|` by `required`; `o|` on the child side for a one-to-one key. I checked the coder's four
  extra differences against the old `TABS` and `schema.json`. All four are hand-edit faults of the
  old page:
  - `fk_equipment_model` and `fk_equipment_type` (on `equipment`) and `fk_equipment_models_type`
    have two columns (`model_id, class_id`, `type_id, class_id`). The old page labelled them with
    the first column only, the same fault the brief lists for `property_options`.
  - The old Overview's `improvements` box had `lead_id` before `root_cause_id`. The column
    positions and the old Tickets tab put it after `follow_up_of_id`.
  - `units ||--o{ improvements` and `equipment ||--o{ improvements` were drawn only in the old
    Overview and Tickets tab, not in the Equipment tab. The old rule draws every link with one end
    in the area.
  - `people ||--o{ improvements : "lead_id"` and `people ||--o{ improvement_actions : "owner_id"`
    were missing from the old Team tab, for the same reason.
- **The page (§ 5.6).** It has classic scripts with relative paths and loads Mermaid 11.4.1 with a
  dynamic `import()` inside `try`, with the same `initialize` settings as before. A failed import
  shows the § 5.6.4 message and resets the promise, so a later click tries again. The DOM is built
  only with `createElement` and `textContent`; the one `innerHTML` is Mermaid's SVG. Missing data
  shows the brief's message with no tabs. Tab and view are kept in `localStorage` by name, in
  try/catch. Each small table sits in an `overflow-x: auto` box. A stale draw is dropped by the
  `ticket` check. The header, footer and messages use the brief's exact texts. The coder's headless
  run (`scratch/s078/smoke_page.cjs`) covers the drawing and the offline case. I did not re-run it,
  because no finding of mine needs it.
- **The release hook (§ 5.7).** The check runs after `run-tests.bat`, also when the unit suites
  were red, and before the browser tests. `TEST_SUMMARY_FILE` is set again to
  `test-summary-release.txt`, because `run-tests.bat`'s `setlocal` dropped it. `run-e2e-tests.bat`
  does not read that variable, so it changes nothing there. A non-zero result sets
  `RELEASE_RESULT=1` with the brief's line, and the header comment and the exit-code line are
  updated. The run name `release` gives `schema-docs-release.log` and
  `vel_yantra_test_release_schemadocs`. The worktree has no `secrets_app.py`, so
  `YANTRA_TESTING=1` uses `example_secrets_app.py` (`127.0.0.1`), which passes the guard.
- **The § 5.10 texts.** The texts in `.claude/CLAUDE.md` (*Stack*, *Dev commands*, § Pre-flight
  *Failure logs* and *Re-run failing tests*, *Plan and domain docs*, the schema row of § Docs to
  keep current, § SMTW-Review) and `docs/Plan.MD` § 5 are applied word for word. The roadmap cells
  use the full path, as decision 6 says. `git grep` finds no live reference to the old table list
  outside step records. No synced file changed: `git diff --stat 1643f65 refs/steps/S078` over
  `.claude/skills`, `.claude/agents`, `docs/steps/README.md`, `tooling/steps`, `tooling/common` and
  `.claude/SMTW-WebApp-Base.md` is empty.
- **The coder's decisions.** None needs the user:
  - Decision 1 (an area tab draws a link only when both ends are drawn) carries out the brief's
    "drawn only in the Overview", and has no effect on today's data.
  - Decision 2 (a key equal to the primary key is one-to-one) has no case today.
  - Decisions 3, 4 and 7 are small page choices: the "All tables" heading, an empty Default cell,
    and the title.
  - Decision 5 adds one true sentence to `schema.md`.
  - Decision 6 only fixes cites.
  - Decisions 8 and 9 are correct readings of the brief.
- **Build time.** 15–21 s alone, against the brief's guess of about 5 s (A1). Most of it is the
  migration build of v20–v41 and `uv` start-up. That adds about 20 s to gate B, each review round
  and the release. That is acceptable, and the report states it.
- **Docs pass.** `## Docs updated` matches the diff and § Docs to keep current. The step has no
  migration, secret, role or device-check row.
- **Tests against § 8.** The core tests cover § 8.1 items 1–11. The shell tests cover § 8.2 tests 1,
  1b and 2 (with the `SCHEMA_DOCS_DB` case), plus the usage line. The vitest covers § 8.3 items 1–7,
  including a table with no notes entry.
- **Track and scope.** The step is on the full track. No app code, migration, RBAC key or dependency
  changed. The impl report lists every addition beyond the brief under Decisions taken.

## Feedback

- hindrance: `step_snapshot.py diff S078` showed only half the step, because KLA committed the
  first half (`d490e69 WIP;`) during a release. The orchestrator gave the
  `git diff 1643f65 refs/steps/S078` form by hand, and the release commits' `VERSION` and
  `CHANGELOG.md` came in as noise (22 files listed, 2 ignored).
- idea: `step_snapshot.py diff` could take `--from <commit>` (the brief's baseline) and leave out
  release-only commits, so a step that spans a mid-step commit diffs in one command.
- rule: the brief (§ 5.7 item 2) says the reviewer's schema docs check costs "seconds". It took 78 s here while
  the backend suite ran, and the coder measured 15–21 s alone. The rule could say to run it after
  `run-tests.bat`, not beside it (`scratch/schema-docs-s078cr1.log`).
