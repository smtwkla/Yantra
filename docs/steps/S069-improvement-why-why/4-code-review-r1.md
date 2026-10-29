```
Step: S069 — Why-why and the root cause
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 30-10-2026
```

# S069 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** One `minor` finding and four nits. All unit
suites are green, the build is clean, and the code follows the brief, with the departures listed
in the report's *Decisions taken*.

## Tests run

- `YANTRA_TEST_RUN=s069cr1 tooling/run-tests.bat`: **backend 3530 passed, frontend 305 passed,
  tooling 185 passed** (ALL SUITES: PASSED).
- `npx vite build` (output to the session scratchpad): clean, with only the known chunk-size
  warning.
- Browser: I made no run. No finding of mine needs one. The coder's runs are the right ones:
  - the new tests alone: 5 passed;
  - targeted at Normal: `improvements`, `screens`, `tickets-work` and `masters` (the brief's § 8.3
    list), 96 passed and 2 skipped (the per-device skips that already exist);
  - the whole suite at Normal once, with its reason (the masters store is used across the app):
    275 passed, 13 skipped.

## Findings

### CR1-01 (minor) — an edit of a why's text can move the why when the page is out of date

- **Where:** `frontend/src/views/improvements/WhyDialog.vue:709`, which sends `position` on every
  edit, and `backend/improvements.py:222-231`, which moves the why to any `position` it is sent.
- **Problem:** the dialog sends the position the page showed when it was opened. The brief asks for
  this (BR1-08), because "the current position writes nothing". That holds only while the page is
  up to date. When another person removed or moved a why after this page loaded, the old position
  is no longer the why's place. A text-only edit then moves the why without anyone asking for it.
- **Failure scenario:**
  1. Priya and Kannan both have the improvement open. It has whys 1 to 4.
  2. Kannan removes why 1. The server renumbers: old why 3 is now why 2.
  3. Priya, on her old page, opens *Edit why 3* and fixes a typo in *Because*. The dialog sends
     `position: 3`.
  4. The server moves her why from 2 to 3. The chain now reads in a different order, and nobody
     chose it. The record shows only an `updated_*` stamp.
  In another case (a chain that became shorter), she gets "Choose a place from 1 to 2" under a
  select that still offers 1 to 3.
- **Suggested fix:** send `position` only when the user changed the select. Compare it with the
  value the dialog opened with. A text-only edit then never reorders. The server stays as it is.
  This changes the approved BR1-08 rule ("position sent on every Edit"), so it goes to the user at
  gate B. The other option is to keep BR1-08 and record the race as accepted: two editors on one
  improvement at the same moment are rare.

## Nits

- **CR1-02** (nit) `backend/improvements.py:129-135`: `_root_cause` builds `{id, code, label}` by
  hand. `tickets.code_ref(row, prefix)` (`backend/tickets.py:197`, already imported here) does
  this from the same `rc_` aliases. Use `{**code_ref(plain, "rc"), "cause_group": …, "active": …}`.
- **CR1-03** (nit) `frontend/e2e/improvements.spec.js:301`: the operator's
  `not.toContainText("Start with why the problem happened.")` cannot fail, because the chain has two
  whys and the empty state never renders. Drop the line, or assert it on an improvement with no
  whys.
- **CR1-04** (nit) `backend/improvements_core.py:351`: "Choose a place in the chain" is the only
  message of the S069 core written as a literal. Name it as a constant beside `WHYS_FULL`, as the
  other messages are, and import it in the core test.
- **CR1-05** (nit) `frontend/src/views/ImprovementDetailView.vue:423-426`: the ticket's and the
  why's inline confirmations can both be open at once, and they share `removing`. Clear
  `confirmingRemoveId` in `askRemoveWhy`, and `confirmingRemoveWhyId` in `askRemove`, so only one
  confirmation shows (the report's § 5 assumes both are never open together).
- **CR1-06** (nit) `frontend/e2e/improvements.spec.js:145-168`: `closeByApi` repeats
  `labourByApi` and the close set-up of `tickets-parts.spec.js:65-77`. Decision 6 gives the reason
  (no change to shared `e2e/support/`). When S072/S073 also need a closed ticket, move one copy to
  `e2e/support/tickets.js`.

## Manual checks still needed

- Not important: row 50 of `docs/steps/device-checks.md`. On an iPhone, the keyboard over
  *Because* in *Add why*; the field and the *Add why* button can still be reached by scrolling.
  This is in the impl report as a plain item, which is correct for a check that is not important.

Every **important** check of the brief (§ 8.3, three of them) is `[auto]` in the report, with a
test that asserts what the user sees and a passing run behind it.

## Checked and found consistent

- **Migration v37** (`backend/local_db.py:1138-1173`): the text is the brief's § 4.1. It has
  `IF NOT EXISTS` on the table, on each column, on `ADD KEY` and on the foreign key, and
  `ADD CONSTRAINT IF NOT EXISTS` on the CHECK. `chk_improvements_root_cause` is
  `(root_cause IS NULL) = (root_cause_id IS NULL)`, and `chk_improvement_whys_position` is
  `position >= 1`. Every existing row has both columns NULL, so it meets the CHECK. No precondition
  is needed, and none was added. `test_migration_v37.py` covers the fresh database, v36 → v37 with
  every old row kept, both CHECKs (each half-set direction refused, error 4025), `position = 0`
  refused, and a re-run with `_schema()` and the rows unchanged. The re-run proves
  `ADD KEY IF NOT EXISTS`. `test_migration_v36.py` is untouched.
- **Schema docs**: `docs/schema.md` has the `improvements` row (three columns, the CHECK, the
  index, "never cleared"), a new `improvement_whys` row, the Mermaid overview (the table,
  `root_cause_id`, both relations) and "migration v37". `docs/schema.html` has the version line
  (v37, 42 tables, 64 links), the overview and the *Tickets* tab (every column of
  `improvement_whys`, the three new columns, both relations, the tab's note).
- **The other docs**: `docs/Plan.MD` § 6, the `docs/Maintenance-Philosophy.md` glossary (*Why-why*,
  *Root cause*), and device-check row 50 match the code. `.claude/CLAUDE.md` was not edited, on the
  orchestrator's instruction. The report proposes the spec-map text. It names
  `improvements` S068/S069, not S067/S068/S069, and gives a reason (S067 has no screens). The
  orchestrator decides.
- **The freeze** (`backend/masters.py:744-758`, `:805`): `_check_code_frozen` keeps the tickets'
  count and message, and returns early as before. It then counts `improvements` `WHERE
  root_cause_id = %s LOCK IN SHARE MODE` under the cause's `FOR UPDATE`. Only
  `update_failure_cause` passes the column, and the column name is a constant. Label, group and
  active still change. The new test in `test_failure_codes_api.py` covers the 409, its message, a
  re-save with the same code, and the deactivation.
- **The lock order** for the (6b) → failure cause (shared) edge. The code change of cause C holds C
  exclusive. It then counts with a shared-lock read on `ix_improvements_root_cause`. That read
  waits only on index entries an open writer changed. Those are entries whose value was C and that
  a writer is moving away from C, and such a writer needs the lock of its new cause, not C. A writer
  moving its root cause to C is still waiting for C before it inserts its new entry. The count's gap
  lock on the next record never waits. So no cycle forms, as the notes in `improvements.py`,
  `equipment.py:21` and `tickets.py:79-84` say. A root-cause write that keeps its cause takes no
  cause lock. No route of this step locks a ticket.
- **Why rows under (6b)**: every write calls `_lock_for_analysis` (the lock first, then the 404
  predicate, the 403 key at the site, the 409 open state). Then it reads the why
  (`id` and `improvement_id`, 404) and the chain. Positions stay 1..n: add at n + 1, `reorder`
  and `renumber` in the pure core, a stamp only on the moved why (BR1-07), and the shifted rows
  get a plain `UPDATE`. A `PUT` that changes nothing writes nothing (`update_row` with an empty
  dict). Tests prove both the stamp rule and the write-nothing rule against the rows.
- **The pure core**: the validators, `position_error`, `reorder` and `renumber` hold no DB code and
  no clock. The core tests cover every message of § 5.2, the bounds (300/301, 1000/1001, 500/501,
  2000/2001), the types, a boolean `position` and `root_cause_id`, null and empty evidence, and the
  reorder cases (front, end, one step, own place) and renumber cases (first, middle, last).
- **The root cause**: `root_cause` and `root_cause_id` are required together, and it is never
  cleared (D4). The active check runs only when the cause changes. A missing cause and an inactive
  one give the same 400. A cause deactivated later is kept on a text edit (tested). The linked
  tickets' rows are unchanged (tested). S067's `PUT` ignores the new fields (tested). The list item
  gains no field (tested).
- **Permissions**: the four routes use `@require_perm(EDIT_KEY)` and then `require_perm_at` at the
  improvement's site. The actor comes from `actor()`, never from the client. Every query uses
  parameters. The tests cover the operator (403), operator here and engineer elsewhere (403), an
  engineer of another site (404), an unknown improvement (404), and a why of another improvement
  (404 on edit and on remove).
- **Decision 7** (the closed 409 tested by setting `improvements_core.IMPROVEMENT_OPEN_STATES` to
  `()`): this is sound. `is_open` reads the module's global when it is called, so the patch
  reaches `_require_open`. One test covers the shared `_lock_for_analysis` that all four routes
  call. The database-down test answers 503.
- **`CAUSE_GROUPS` in `stores/masters.js`**: one list of `{value, label}` objects, and
  `causeGroupLabel` returns an unknown value as it came (tested). `FailureCausesPanel.vue` and
  `MoveDialog.vue` read it, with the same labels and order. No other copy is left in
  `frontend/src`. The targeted `masters` and `tickets-work` specs and the whole Normal suite are
  green after the move.
- **The screens**:
  - The cards are in a `col-lg-6` after *Tickets* on a phone.
  - The edit and remove buttons have full-size tap targets (no `btn-sm`). Their `aria-label`s are
    "Edit why n" and "Remove why n", and the trash button is `btn-outline-danger`.
  - The inline confirmation reads "Remove why n? You cannot undo this.", with its refusal under it.
  - Long text wraps (`text-break`, `overflow-wrap: anywhere`, `text-wrap` on the badge).
  - The dialogs use the shared `FormModal`. Every field shows its `fieldError`. The 20-whys 409 has
    no field and shows at the top.
  - A position refusal on a chain of one has its own line in the dialog.
  - The stored inactive cause is listed last, marked "(inactive)".
  - The screen words are plain and match the brief.
- **Decisions 1–8** in the report: each is a small, stated choice and none changes behaviour. That
  includes `path: null` with `send` in `WhyDialog` (the URL needs the id, as in S068's dialogs) and
  "Choose a place in the chain" for a non-integer position.
- **Track**: full, as the brief says.

## Feedback

- waste: the frontend diff holds `docs/schema.html`'s whole `TABS` line twice, old and new (about
  20 000 tokens for a 4-line change). To find the real change I had to read it by eye
  (`step_snapshot.py diff S069 -- … docs/schema.html`).
- idea: the snapshot diff could take `--exclude <path>` or `--word-diff`. A reviewer could then
  read `schema.html` as a word diff and leave the long line out of the code read.
