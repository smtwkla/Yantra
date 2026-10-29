```
Step: S069 — Why-why and the root cause
Doc: impl-report
Author: Coder (Opus)
Date: 30-10-2026
```

# S069 — Implementation report

**Result:** the why-why chain, the root cause and the contributing causes are built as the brief
says: migration v37, four routes, the freeze of a cause a root cause uses, two cards and two
dialogs on the improvement page. All unit suites are green (backend 3530, frontend 305, tooling
185), `npx vite build` is clean, the targeted browser run is green (96 passed, 2 skipped by device)
and the whole browser suite at Normal is green (275 passed, 13 skipped). No design question is open.

## Stale brief check

The brief was written while S067 was being coded and before S068 existed. I compared every name,
line and route it cites in S067/S068 code (and the other cited lines) with the tree. Every name,
route, constant and helper exists as the brief says. The differences are line numbers and one
detail of S068's dialogs; none changes the design.

| Brief says | The tree | Followed |
|---|---|---|
| S067's bullet in equipment.py's LOCK ORDER at `backend/equipment.py:9` | The (6b) line is at `:21` | The code; the edge is added to the (6b) line |
| `_check_active_code` at `backend/tickets.py:775` | `:794` | No effect (cited only as a precedent) |
| `TestCauseAndActionCodeFrozenOnceUsed` at `test_failure_codes_api.py:268` | `:269` | No effect |
| `describe("failure codes (S016)")` at `frontend/tests/masters.test.js:65` | `:66` | No effect |
| `WhyDialog` on `useFormModal({ path: "/api/improvements/<id>/whys" })`, `openCreate(seed)` with `seed = {previousAnswer}` | `useFormModal` fixes `path` at set-up; S068's own dialogs (`AddTicketDialog`, the root cause's model `MoveDialog`) use `path: null` and `send` | `path: null` and `send` with the URL built at save time; the previous answer is a ref set before `openCreate()` (Decisions 2) |
| S068's `"Edit"` and `"Add ticket"` locators may match the new buttons as substrings (§ 8.3) | Every one already has `exact: true` | No change to S068's tests |
| `test_improvements_api.py:514` pins the list item's key set | It does (line 514) | The list item gains no field; a new test checks it too |

Every other citation matches: v36 at `local_db.py:1104`, `_text` `:60` and `_is_id` `:56`,
`is_open` `:108`, `IMPROVEMENT_CLOSED` `:45`, `_check_code_frozen` `:743`, `_update_plain_master`
`:763`, `update_failure_cause` `:795`, the failure-codes comment `:651`, `_lock_row` `:144`, the
tickets' freeze paragraph `:79-83`, `require_perm_at` `:451`, `update_row` `:68`, `db_down` `:213`,
`_TABLES` `:162`, `useFormModal.js:22`, `MoveDialog.vue:55` and `:92`, `FailureCausesPanel.vue:17-24`,
`LabourPanel.vue:144-151`, `masters.spec.js:103`, `tickets-parts.spec.js:281`.

## 1. What was built

- **The why-why chain.** An improvement holds up to 20 *Why? / Because* lines, each with optional
  evidence, its writer and its last changer. *Add why* appends; *Edit why n* changes the text and
  the place in the chain; *Remove why n* deletes after a confirmation on the row, and the lines
  after it move up.
- **The root cause.** A text plus one cause from the failure-cause list, set and changed, never
  cleared. *Set root cause* fills the text with the last why's answer. The same dialog holds
  *Other causes (optional)* (the contributing causes).
- **Both causes side by side.** Under the *Root cause* card: "Cause on the tickets: 3.4 Expected
  wear and tear" and the line on the difference. The tickets are never written.
- **The freeze.** Masters refuses a code change on a cause an improvement's root cause uses: 409
  "This code is used by an improvement's root cause and can no longer change".
- **One cause-group list.** `CAUSE_GROUPS` and `causeGroupLabel` live in the masters store; the
  Masters panel, the close dialog and the root-cause dialog read it (D7).

## 2. How it works

**Database (v37).** A new table `improvement_whys` (`position` 1..n, CHECK ≥ 1, foreign key to
`improvements`, index `(improvement_id, position)`). `improvements` gains `root_cause`,
`root_cause_id` (foreign key to `failure_causes`, index `ix_improvements_root_cause`) and
`contributing_causes`; the CHECK `chk_improvements_root_cause` keeps text and cause both set or
both NULL. Every statement is `IF NOT EXISTS`, and the re-run test proves `ADD KEY IF NOT EXISTS`.
No precondition (new table, nullable columns, all existing rows NULL).

**Pure core** (`improvements_core.py`). `validate_why(body, creating)` and
`validate_root_cause(body, _creating)` return `(clean, errors)` for `clean_body`, with the brief's
messages. `position_error(n, position)` returns "Choose a place from 1 to n" or None.
`reorder(whys, why_id, new_position)` and `renumber(whys)` take the chain as `(id, position)`
pairs and return only the pairs whose position changes.

**Routes** (`improvements.py`). Each write runs in one transaction:

1. `_lock_for_analysis`: the improvement row `FOR UPDATE` (6b), then the predicate (404), the key
   at the site (403), the open state (409).
2. Add: the chain's length (409 at 20), insert at n + 1.
3. Edit: the why by id and improvement (404); changed text fields only; when `position` is sent,
   `position_error` (400), then `reorder`. The moved why's new position goes in its own
   `update_row` (stamped `updated_*`); the shifted lines get a plain `UPDATE … SET position`.
4. Remove: delete the row, then the `renumber` updates.
5. Root cause: changed fields only; a changed cause must exist and be active (plain read, 400
   "Choose an active cause from the list"). An unchanged, later deactivated cause is kept.
6. Every write answers with the whole detail.

The detail gains `whys` (by position, with `created_by_name` / `updated_by_name`), `root_cause`
(`{text, cause{id, code, label, cause_group, active}}` or null) and `contributing_causes`. The
shared select joins `failure_causes rc`; the list builds its items field by field, so it is
unchanged. The LOCK ORDER notes of `improvements.py`, `equipment.py` and `tickets.py` name the new
edge (6b) → a failure cause (shared) and why it makes no cycle.

**Freeze** (`masters.py`). `_check_code_frozen(…, root_cause_column=None)` counts the tickets as
before, then, for a cause, the improvements `WHERE root_cause_id = %s LOCK IN SHARE MODE`.
`_update_plain_master` passes the column through; only `update_failure_cause` gives it.

**Screens.** `ImprovementDetailView.vue` gets a right column (`col-lg-6`; after *Tickets* on a
phone) with the *Why-why* card (help line, rows, edit and remove buttons with `aria-label`
"Edit why n" / "Remove why n", the inline confirmation, the empty state) and the *Root cause*
card (badge "4.2 Management error", "Group: Management", the text, "Other causes: …",
"(inactive)" for a deactivated cause), then the note on the two causes. `WhyDialog.vue` shows the
previous line's answer above the fields and, on an edit with more than one why, *Place in the
chain*. `RootCauseDialog.vue` lists the active causes in `optgroup`s by `CAUSE_GROUPS`, with a
stored inactive cause last; a load error of the cause list shows at the top. Controls follow the
detail's `permissions` and `is_open`, so no button ends in a 403.

## 3. Files touched

Backend (6 code, 5 tests):

- `backend/local_db.py`: migration v37.
- `backend/improvements_core.py`: why and root-cause bounds and messages, `validate_why`,
  `validate_root_cause`, `position_error`, `reorder`, `renumber`, `_optional_text`.
- `backend/improvements.py`: the four routes, the detail's three fields, the select join, the lock
  columns, the LOCK ORDER note.
- `backend/masters.py`: the freeze's second user; the comment and docstrings.
- `backend/tickets.py`: the freeze paragraph names the improvements count (docstring only).
- `backend/equipment.py`: the (6b) line names the new edge (docstring only).
- `backend/tests/test_migration_v37.py` (new): fresh database, v36 → v37 keeps rows, the CHECKs,
  re-run.
- `backend/tests/test_improvements_core.py`: the S069 core cases.
- `backend/tests/test_improvement_whys_api.py` (new): add, edit, remove, root cause, detail, list,
  closed (409), database down (503).
- `backend/tests/test_failure_codes_api.py`: a cause used only by a root cause keeps its code.
- `backend/tests/conftest.py`: `improvement_whys` first in `_TABLES`.

Frontend (7 code, 3 tests):

- `frontend/src/views/ImprovementDetailView.vue`: the two cards, the note, the remove-why state.
- `frontend/src/views/improvements/WhyDialog.vue` (new).
- `frontend/src/views/improvements/RootCauseDialog.vue` (new).
- `frontend/src/utils/improvementLabels.js`: the bounds, `causeText`, `ticketCauses`,
  `defaultRootCause`.
- `frontend/src/stores/masters.js`: `CAUSE_GROUPS`, `causeGroupLabel`.
- `frontend/src/views/tickets/MoveDialog.vue`: reads the store's `CAUSE_GROUPS` (objects).
- `frontend/src/views/masters/FailureCausesPanel.vue`: reads `CAUSE_GROUPS` and `causeGroupLabel`.
- `frontend/tests/improvementLabels.test.js`: the three helpers.
- `frontend/tests/masters.test.js`: `causeGroupLabel` for the five groups and an unknown one.
- `frontend/e2e/improvements.spec.js`: five S069 tests, `closeByApi` and `whysByApi` helpers.

Docs: see *Docs updated*. Step files: this report; the brief's `Status`.

## 4. Decisions taken

1. **`reorder` takes `(id, position)` pairs, not ids.** The brief writes `reorder(ids, …)` and
   § 5.3 says the shell feeds `[(id, position)]`. One input form for both functions keeps the
   shell simple; `reorder` places the why and calls `renumber`. Behaviour as the brief's examples.
2. **`WhyDialog` uses `path: null` and `send`**, and keeps the previous answer in a ref set before
   `openCreate()` / `openEdit()`, not in the seed. `useFormModal` fixes `path` at set-up, and the
   URL needs the improvement's id; S068's dialogs do the same. `blank()` takes no seed (its result
   is the same empty form). The brief's call contract (BR1-04) holds: `blank()` with no argument
   gives empty strings.
3. **A non-integer `position` gets "Choose a place in the chain"** (`position`). The brief gives
   the range message only, which needs n; the type check runs in `validate_why`, which does not
   know n. The page never sends one (a select of numbers).
4. **The why rows' writer line** reads "Priya (engineer), 30-10-2026 02:43" and adds " · changed
   by <name>" when the changer differs from the writer, as the brief's "changed by …".
5. **`_lock_for_analysis`, `_chain`, `_shift`, `_read_why`** are new small helpers in
   `improvements.py`, shared by the four routes (no copy of the lock-and-check sequence).
6. **`closeByApi` lives in `improvements.spec.js`,** not in `e2e/support/improvements.js`. Only
   this spec needs it, and a change to `e2e/support/` is a shared-code change (a second whole-suite
   run and the WebKit screens run). It repeats the close set-up of `tickets-parts.spec.js:65-77`,
   281 (labour, mode, cause, action) as a function of its own.
7. **The 409 for a closed improvement** is tested by setting `IMPROVEMENT_OPEN_STATES` to `()`
   (every improvement is open until R05.4).
8. **The badge** is `text-bg-primary text-wrap` so a long cause label wraps on a phone.

No departure from the brief's behaviour, routes, messages or screen words.

## 5. Not done, deferred or assumed

- Out of scope as the brief says: the *Watching* rule, history and timeline (R05.4),
  countermeasures (R05.3).
- **Assumption:** the inline remove confirmation of a why and of a ticket share the page's
  `removing` flag; both cannot be open together in practice (one tap each).
- The `updated_at` of `update_row` is the database's `NOW()`, as everywhere in Yantra.

## Manual checks

- [auto] **important** The engineer adds three whys (the second dialog shows the first answer),
  sees 1, 2, 3 and the evidence line, and moves why 3 to place 1 — `frontend/e2e/improvements.spec.js`::"S069: the engineer writes three whys, the second dialog shows the first answer, and moves why 3 to the front"
- [auto] **important** The engineer removes why 2 through the inline confirmation; two whys left,
  1 and 2 — `frontend/e2e/improvements.spec.js`::"S069: the engineer removes why 2 after the confirmation on the row; the rest are numbered 1 and 2"
- [auto] **important** *Set root cause*: the text holds the last answer; 4.2 picked; the card shows
  the cause, "Group: Management" and the text; the note shows "Cause on the tickets: 3.4 Expected
  wear and tear" and the line; the button reads *Edit root cause* — `frontend/e2e/improvements.spec.js`::"S069: the engineer sets the root cause from the last why; the tickets' own cause shows beside it"
- [auto] The help line shows, also with no whys — `frontend/e2e/improvements.spec.js`::"S069: the help line shows on the why-why card, also with no whys"
- [auto] The operator reads the whys and the root cause, with no button to change them — `frontend/e2e/improvements.spec.js`::"S069: the operator reads the whys and the root cause, with no button to change them"
- On a real device (not important): the why dialog on an iPhone, the keyboard over *Because*;
  row 50 of `docs/steps/device-checks.md`.

## Tests run

- Migration, core and API while coding: `test_migration_v36/v37` (9 passed),
  `test_improvements_core` (89), `test_improvement_whys_api` + `test_improvements_api` (103),
  `test_failure_codes_api` + `test_masters_api` + `test_tickets_api` (239).
- Frontend unit: `improvementLabels.test.js`, `masters.test.js` (26 passed).
- All suites (`YANTRA_TEST_RUN=s069c1 tooling/run-tests.bat`): the first run was red (a collection
  error in `test_improvements_core.py`, left by my own import tidy-up); after the fix:
  **backend 3530 passed, frontend 305 passed, tooling 185 passed**.
- `npx vite build`: clean (the known chunk-size warning only).
- Browser, the new tests alone (`E2E_LANES=1`, `phone-chromium`, `-g S069`): 5 passed at the first
  run.
- Browser, targeted (`improvements`, `screens`, `tickets-work`, `masters` at Normal; the brief's
  § 8.3 list: the page, the close dialog and the Masters panel changed): **96 passed, 2 skipped**
  (the existing per-device skips of `tickets-work.spec.js:730` and `:748`).
- Browser, the whole suite at Normal once at the end (the masters store is used across the app):
  **275 passed, 13 skipped** in 163 s on 6 lanes (the existing per-device and conditional skips; no failure, no flaky test).

## Docs updated

- `docs/schema.md`: the `improvements` row (three columns, key, CHECK), a new `improvement_whys`
  row, the Mermaid overview (the table, `root_cause_id`, two relations), the "migration v37" line.
- `docs/schema.html`: the version line (v37, 42 tables, 64 links), the overview and the *Tickets*
  tab (the table with every column, the three columns, two relations, the tab's note).
- `docs/Plan.MD` § 6 *Screens*: the improvement page's *Why-why* and *Root cause* cards.
- `docs/Maintenance-Philosophy.md` § 12 Glossary: rows *Why-why* and *Root cause*, beside
  *Failure cause*.
- `docs/steps/device-checks.md`: row 50 (§ 8.4).
- `.claude/CLAUDE.md`: not edited (the orchestrator's instruction); the text is below.

## Proposed CLAUDE.md changes

In § SMTW-Review, the **Browser tests** bullet's spec-to-step map has no `improvements` entry yet.
Insert after `` `floor` S064, ``:

```
`improvements` S068/S069,
```

so the list reads `… `floor` S064, `improvements` S068/S069, `settings` S064).` (S067 has no
screens; its API is covered by the backend tests.)

## Fix rounds

### Round 1

Amendment A1 (brief � 10) is in. All six findings answered.

- **CR1-01 (minor) � Fixed.** The body is built by a new `whyBody(form, isEdit, openedPosition)` in
  `frontend/src/utils/improvementLabels.js`. `WhyDialog.vue` remembers the place the edit opened with
  (`openedPosition`, set in `openChange`) and sends `position` only when the select differs from it.
  The server is unchanged. The comment on the chain-of-one refusal line is reworded. Tests: four
  cases in `frontend/tests/improvementLabels.test.js` (`whyBody`): no `position` on an add, none on an
  edit with the place unchanged, `position` when changed, evidence kept. Red then green: written
  first, the four tests failed (`whyBody` did not exist, so no body could pass them); I did not
  restore the old always-send code to see the assertion fail, because the test targets the new
  function; after the fix, 23 passed. The old behaviour is the case "none on an edit with the place
  unchanged", which that function now guards.
- **CR1-02 (nit) � Fixed.** `_root_cause` in `backend/improvements.py` uses
  `{**code_ref(plain, "rc"), "cause_group": �, "active": �}`. Backend improvement tests: 192 passed
  (`YANTRA_TEST_RUN=s069f1`; `test_improvements_core.py`, `test_improvements_api.py`,
  `test_improvement_whys_api.py`).
- **CR1-03 (nit) � Fixed.** The operator test no longer asserts the empty state is absent (it could
  not fail); the empty state is asserted on an improvement with no whys in the test at line 316.
- **CR1-04 (nit) � Fixed.** `POSITION_NOT_NUMBER` in `improvements_core.py`, beside the other
  messages; `test_position_must_be_an_integer` now asserts the field and this constant.
- **CR1-05 (nit) � Fixed.** `askRemove` clears the why's confirmation and error; `askRemoveWhy`
  clears the ticket's. Only one confirmation shows, so the shared `removing` flag is safe. No new
  test: no browser test opens both, and the change is two assignments.
- **CR1-06 (nit) � Deferred.** `closeByApi` stays in `e2e/improvements.spec.js`. S073 also needs a
  closed ticket and moves it to `e2e/support/` then, with its own WebKit run (a change to
  `e2e/support/` runs `screens.spec.js` on `phone-webkit`).

Runs: frontend `improvementLabels.test.js` 23 passed; backend files above 192 passed; `npx vite
build` clean (chunk-size warning only); `tooling/run-e2e-tests.bat e2e/improvements.spec.js
e2e/screens.spec.js`: 29 passed, 1 skipped (the existing per-device skip).

Docs updated: none, because A1 changes no route, message or screen text; the brief's � 10 already
records it.

#### Feedback

- none

## Feedback

- waste: a Python script I wrote to merge an import block cut at the `)` inside a comment and left
  four lines behind; I did not re-run the module's tests after it, so the full run went red and
  had to run again (`test_improvements_core.py`, 1 extra full run, about 2 min).
- hindrance: a Python script written in text mode on Windows turned two LF files into CRLF
  (`masters.py`, `test_improvements_core.py`); `newline=""` on open avoids it. The README § Shell
  rule could name it (2 extra commands).
- rule: I first wrote a script inline as a heredoc, against README § Shell rule 1, and it failed on
  quoting; the rule held (1 lost call).
- idea: the brief's file list names `e2e/support/improvements.js` implicitly through S068 § 8.1's
  set-up; a brief that needs a new set-up helper could say whether it goes in the spec or in
  `e2e/support/` (shared code, with its extra WebKit run), so the coder does not have to weigh it.
