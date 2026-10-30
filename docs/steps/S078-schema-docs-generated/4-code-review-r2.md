```
Step: S078 — Schema docs from the migrations
Doc: code-review r2
Author: code-reviewer (Opus 5.5)
Date: 30-10-2026
```

# S078 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** The fix round fixes all four nits of round 1.
The fix round's own diff brings in one new nit (CR2-01).

**What I re-read.** The fix round's diff (`step_snapshot.py diff S078 --from-round 1`, 6 files), and
in full: `tooling/schema/schema_docs.py` `_recreate_database` and `build_and_read`;
`tooling/schema/schema_docs_core.py` `parse_notes`, `_wrong_type`, `_notes_lines`, `notes_problems`,
`planned_problems` and the two new messages; `docs/schema.html` from `dark()` to the end of
`drawDiagram()`; the new tests in `backend/tests/test_schema_docs_shell.py` and
`tooling/tests/test_schema_docs_core.py`; `## Fix round 1` in `3-impl-report.md`.

## Tests run

All with `YANTRA_TEST_RUN=s078cr2`, 30-10-2026.

- `tooling\run-tooling-tests.bat`: **PASSED**, 231 passed.
- `tooling\run-backend-tests.bat tests/test_schema_docs_shell.py`: **PASSED**, 7 passed.
- `tooling\schema-docs.bat check`: **PASSED**, `Schema docs at migration v41: 4 passed` (23 s).
- The fix round changed code in the tooling folder, one backend test file and `docs/schema.html`
  only, so the run of all suites is not due. No browser run is due: no app screen or API changed.
  I did not run `scratch/s078/smoke_page.cjs`, because no finding of mine needs it.

## Round 1 findings

| ID | Status |
|---|---|
| CR1-01 | Fixed |
| CR1-02 | Fixed |
| CR1-03 | Fixed |
| CR1-04 | Fixed |

- **CR1-01.** The static `<script src>` for svg-pan-zoom is gone. `loadPanZoom()` adds the script
  element on the first drawing. `loadMermaid()` waits for both libraries with `Promise.all`, so
  `svgPanZoom(svg, …)` in `drawDiagram()` always runs after both loaded. The Tables view no longer
  waits for the CDN. A failed load of either library rejects the promise, and the existing `catch`
  resets `mermaidPromise`, so the diagram message shows and a later click tries again. A failed
  script element is removed, so a retry adds a fresh one. When pan-zoom loaded but Mermaid failed,
  the retry skips pan-zoom (`window.svgPanZoom` is set). The coder's choice of this form over
  `async` is sound and is in the report.
- **CR1-02.** The `DROP` and `RELEASE_LOCK` in the `finally` now run in their own `try`. A failure
  there is kept in `cleanup_error`. When the body raised, the body's error propagates and the kept
  error is dropped, so an earlier message (for example "The migrations could not be applied") is no
  longer hidden. The cleanup error is raised only after a body that succeeded, as `NotCompleted`,
  which the outer `except pymysql.MySQLError` does not catch. The outer `except` maps only 2003
  (cannot connect), 2006 (server gone away) and 2013 (connection lost) to the "cannot be reached"
  message. These are the codes PyMySQL raises for a lost or refused connection. The connect call
  has its own `except` that still gives "cannot be reached" for every connect error, which is
  right. The two new messages follow the pattern of the other messages: what happened, the
  server's text with its code (`describe_error`), and what to do. They are developer-facing CLI
  text and read clearly.
- **CR1-03.** `parse_notes` calls `_wrong_type` after the JSON parse. `tables` must be an object;
  `areas` and `planned` must be lists of objects; `tables` in a planned entry must be a list. A
  missing key or `null` passes (`notes.get(key)` is `None`). The message uses the "is not valid
  JSON" form, so checks 3 and 4 fail and nothing is written. The six parametrised cases and the
  right-types case cover it.
- **CR1-04.** The comment now reads "Every failed part prints its line, so the end of the output
  shows every fault."

## Nits

- **CR2-01** (nit) `tooling/schema/schema_docs.py:114-118`: the `DROP` and the `RELEASE_LOCK` share
  one `try`, so a failed `RELEASE_LOCK` after a successful drop prints "The database … could not be
  dropped", which is then false. Give the release its own `try`, or ignore its error (closing the
  connection releases the lock anyway).

## Manual checks

The impl report's `## Manual checks` still carries the brief's one important check (§ 8.5) as an
unticked box. It is still due:

- [ ] **important** — KLA, on his laptop, in Chrome and Edge: open `docs/schema.html` from the file
  explorer. Check the meta line "Migration v41 · 46 tables, 75 links", the five tabs, each diagram,
  and `Show tables` with the planned tables. Check that the diagram still zooms and pans with the
  mouse wheel and a drag (svg-pan-zoom now loads on the first drawing). Then turn Wi-Fi off and
  reload: the tables still show, and the diagram shows its internet message.

## Checked and found consistent

- **Red, then green.** The report gives the red result for the two CR1-02 tests and the six CR1-03
  cases. For `test_a_failed_drop_does_not_hide_the_migration_failure` the report states why the red
  result was not seen (the output was cut). The reason is given, so this is no finding. Reading the
  old code confirms the test is red there: the old `finally`'s failed `DROP` raised error 1051,
  which replaced the migration-failed `NotCompleted` and reached the outer `except` as "cannot be
  reached".
- **The fake cursor tests.** `_DropFailsAfterBuild` lets the first `DROP` (in `_recreate_database`)
  pass and fails the second (the cleanup), so the test reaches the cleanup path. `_write_text` is
  patched to fail if called, so the tests also show that nothing is written.
- **A falsy wrong type.** `_wrong_type` lets a falsy `tables` in a planned entry (for example `""`)
  pass. Every reader uses the same `or []` / `or {}`, so such a value is read as empty and cannot
  raise. The comment "an empty value of the wrong type is still wrong" holds for the top-level keys.
- **The 1044 path.** `_recreate_database` still turns error 1044 into `create_refused_message`
  before the outer `except` sees it.
- **Generated files.** `schema-docs.bat check` passes, so `schema.json`, `schema-data.js` and
  `schema.md` are unchanged by the fix round.
- **Docs pass.** The report's "Docs updated: none" is right: no doc describes these messages or the
  script tag.

## Feedback

- none
