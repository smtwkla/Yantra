```
Step: S025 — Release safety and ticket integrity (audit fixes)
Doc: brief-review s1 (staleness)
Author: Brief reviewer (Fable)
Date: 21-10-2026
```

Reviewed against: 3df667c

# Staleness review s1 — S025 against the code after S024's commit

**Verdict: no `blocker` or `major` finding. The brief's statements about the code still hold; one `minor` (a new CLAUDE.md rule the brief must follow) and four nits. The coder can start once the planner fixes the brief text.**

## What was compared

The brief's `Baseline:` is `28d3be3 + uncommitted S024`. Since then: S024
committed as 3df667c, plus four docs-only commits (3c6ac06, ea1f985, 8a594c3,
64ca5ee). Uncommitted now: `docs/steps/README.md`, S024's brief and impl
report (status lines only).

Of the files in the brief's § 3 *Where*, these changed between 28d3be3 and
3df667c (`git diff 28d3be3 3df667c -- <file>`):

| File | What changed | Brief still holds? |
|---|---|---|
| `.claude/CLAUDE.md` | S024 A1: a *Browser tests (S024)* bullet and a new `## SMTW-Review` section | The two edits the brief plans (deploy bullet, migrations note) still apply. The new section adds a rule the brief does not follow yet: **BS1-01** |
| `tooling/e2e/e2e_backend.py` | New in S024 (it was uncommitted at the baseline) | Yes: `_recreate_database` drops and creates the database on a plain connection, the pattern the brief's upgrade test copies (§ 3 Tests) |
| `tooling/run-e2e-tests.bat` | New in S024 | Yes: step 2 creates `vel_yantra_e2e` as root on a running container, the pattern the brief gives `run-backend-tests.bat` for `vel_yantra_upgrade` (BR1-03) |
| `tooling/dev/init-test-db.sql` | S024: creates and grants `vel_yantra_e2e` | Yes: the brief adds `vel_yantra_upgrade` the same way |

Unchanged since the baseline (no diff): `backend/local_db.py`, `app.py`,
`api_common.py`, `masters.py`, `equipment.py`, `tickets.py`,
`tickets_core.py`, `worker.py`, every file under `backend/tests/`,
`tooling/deploy.py`, `tooling/build/build.bat`, `tooling/run-tests.bat`,
`tooling/run-backend-tests.bat`, the run configs, and
`frontend/src/views/tickets/RegradeDialog.vue`.

Frontend files S024 A2 changed that S025's e2e checks drive:
`MoveDialog.vue`, `EditTicketDialog.vue`, `EventFields.vue`, `LabourPanel.vue`,
`UnitsPanel.vue` (field messages now `v-if` + `invalid-feedback d-block`),
`FormModal.vue` (dispose after `hidden.bs.modal`), `main.js` (`import
"bootstrap"`). None of these changes touches a statement in the brief:
`RegradeDialog.vue` already uses the A2 pattern (line 94), and the brief's
one screen change (a refusal on `intensity` in "stopped" mode, `reload` on a
400 or 409 without a field) is unaffected.

## Findings

### BS1-01 (minor) — CLAUDE.md's new `## SMTW-Review` rule: the brief must say what it adds there

**Fact.** S024 A1 added to `.claude/CLAUDE.md` a section `## SMTW-Review`
whose last point says: "a step that adds something a later audit should check
(a new invariant, a check that only a full run shows) adds a point here; the
planner proposes the point in the step's brief." The brief's § 3 Tooling plans
two edits to CLAUDE.md (the deploy bullet, the migrations note) and nothing in
the new section.

**Why it matters.** S025 adds exactly the kind of thing the rule means: the
migration list now starts at v20 with a precondition dict, and v1–v13 live
only as a frozen test fixture; the deploy waits on `schema_ready`;
`build.bat` refuses a dirty tree, an untagged HEAD and an existing tag. A later
`/smtw-review` should check that a migration after v21 which touches existing
rows carries a precondition, and that the fixture was never edited. Without a
line in the brief, the coder decides alone whether and what to add.

**Options.**
- (a) **Recommended.** Add to § 3 Tooling (`.claude/CLAUDE.md`) one point for
  the `## SMTW-Review` section, e.g.: "**Migrations**: `_MIGRATIONS` starts at
  v20 (squashed 21-10-2026); v1–v13 live only in
  `backend/tests/fixtures/migrations_v13.py` and are never edited; a migration
  that touches rows that exist in production carries a `_PRECONDITIONS` entry
  and a test from the production schema. Check both on every migration after
  v21." The deploy gate and `build.bat`'s refusals can go in the same point or
  stay in the deploy bullet.
- (b) State in the brief that S025 adds no point, and why.

### BS1-02 (nit) — S024 is committed: three places still say it is being coded

**Fact.** The intro says "S024 (browser tests) is being coded in parallel;
S025 is coded after S024 is committed (§ 9 Q4)"; the `Status:` line says
"(coded after S024 is committed)"; § 9 Q4 reads as open. S024 is committed as
3df667c.

**Fix.** "S024 committed (3df667c)" in the intro; Q4 struck through as settled;
`Baseline:` set to `3df667c` after this check (README § Stale brief check).

### BS1-03 (nit) — the e2e checks: name the suite's conventions the coder must follow

The brief's three e2e checks (§ 8) hold, but the committed suite has
conventions the brief does not name. A line each saves the coder a wrong turn:

- **A refused request fails the test unless named.** `support/console.js`
  fails a test on any browser "Failed to load resource" line not declared with
  `consoleWatch.allowFailedRequest(urlPart, status)` (see
  `masters.spec.js:50`). The *Machine stopped* refusal is a **400** on
  `intensity` (`tickets_core.validate_regrade`: `new == current` →
  `ALREADY_BREAKDOWN`), so the test declares `("/regrade", 400)`; the unit
  deactivation refusal declares `("/api/masters/units/", 409)`.
- **The API provocation.** `support/tickets.js` `moveByApi` builds
  `/api/tickets/<id>/moves/<move>`, so despite its docstring ("A move or
  re-grade") it cannot reach `POST /api/tickets/<id>/regrade`. The test uses
  `apiAs(key)` from `support/people.js` directly, or adds a `regradeByApi`
  beside `moveByApi` (recommended: one helper, and fix the docstring).
- **The message check** is `expectFieldMessage(scope, text)` in
  `support/dialogs.js`; since A2 it asserts "visible" on every project.
- **A ticket with a repeat**: raise the earlier ticket with `raiseByApi`,
  restore it with `moveByApi("technician", id, "restore", …)`, then raise the
  repeat with `raiseByApi("operator", { …, repeat_of_id })`; the
  "Not fixed — raise again" test in `tickets-work.spec.js` is the model.

### BS1-04 (nit) — which deactivation guard runs first, and how the e2e test reaches the ticket one

**Fact.** `masters.update_unit` already refuses deactivation of a unit that
holds equipment not scrapped ("The unit holds equipment that is not scrapped;
move or scrap it first", 409 on `active`). A unit with an open ticket also
holds that ticket's machine, unless the machine was moved out (allowed, U3).
The brief's § 5.3 adds the ticket guard but does not say whether it runs
before or after the equipment guard. This was true at the baseline too; it is
raised here only because it decides how the e2e check "the unit deactivation
refusal shows" is written.

**Options.**
- (a) **Recommended.** The ticket guard runs first: tickets must be closed
  before anything else, and the count "(N open)" is the message the user
  needs most. The e2e test then raises a ticket on `E2E MCC1 mill`, opens
  Masters › Units as `it_admin`, edits `SMTW.MCC1`, taps *Deactivate* → *Yes*,
  and sees "Close its tickets first (1 open)". The three projects share one
  database and run in turn, so the test closes its ticket at the end (or
  raises on a machine it creates), as the suite's tests keep their data to
  themselves.
- (b) The equipment guard stays first; the test moves the machine to another
  unit first (U3) before deactivating. More steps, and it moves seed
  equipment other tests look up by unit.

### BS1-05 (nit) — one comment outside `backend/` names an old migration number

**Fact.** `frontend/e2e/masters.spec.js:10`: `const GENERAL_MODES = 14; // the
General modes migration v11 fills in (S016 § 4.4)`. After the squash there is
no v11. The brief's § 3 Tests lists the fate of the backend's migration tests
only.

**Fix.** Add the line to § 3 Tests: the comment says "v20 (S016's seed)"; the
constant stays 14. No other file under `frontend/e2e/`, `tooling/e2e/` or
`tooling/dev/seed_dev.py` names an old version.

## Checked and found consistent

- `backend/local_db.py` `init_db` / `ensure_schema` / `_last_error` are as the
  brief describes (lines 674–734): the precondition hook goes after
  `_get_applied_versions` inside the lock; `ensure_schema` never raises and
  keeps `_last_error`.
- `backend/app.py` runs `ensure_schema(DB_CONFIG)` at import (line 31) and
  `/api/health` returns `{"status": "ok"}` (line 98): the brief's change adds
  `schema_ready` on the same route. Playwright's `webServer` waits on that URL
  for any 2xx (`playwright.config.js:39`), unchanged by the brief since the
  route stays 200; on the e2e stack the import-time call has already built
  the schema before the server answers.
- `tooling/e2e/e2e_backend.py` rebuilds `vel_yantra_e2e` from an empty
  database at every run, so "every screen still opens on a database built by
  v20" is `screens.spec.js` as it is: no new test needed, only a green run.
- `tooling/run-e2e-tests.bat` creates the e2e database as root with the
  compose file's dev password; `run-backend-tests.bat` can create
  `vel_yantra_upgrade` the same way (BR1-03).
- `RegradeDialog.vue` is unchanged since the baseline and already uses the A2
  field-message pattern; its `reload` emit on a 409 without a field exists
  (line 37–39), and `topError` hides `intensity` (line 41), which is the gap
  the brief closes.
- S024 A2's `FormModal.vue` change (dispose after `hidden.bs.modal`) does not
  affect the brief: the ticket page keeps the dialog mounted on `reload`.
- The brief's `created_by` tags `'migration-v8'` / `'migration-v11'` are not
  used by `seed_e2e.py` or `seed_dev.py`.
- CLAUDE.md's *Browser tests* bullet says the e2e run is never in
  `run-tests.bat`; the brief adds `run-tooling-tests.bat` there, not the e2e
  run — consistent.
- Whitespace-only changes (CRLF warnings in `git diff`) ignored per README
  § IDE reformatting.
