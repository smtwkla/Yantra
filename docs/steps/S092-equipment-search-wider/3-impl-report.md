```
Step: S092 — Find a machine by model, maker or class, and confirm it
Doc: impl report
Author: Coder (Sonnet)
Date: 01-11-2026
Status: Complete — all tests green (second run, after KLA started Docker)
```

# S092 — Impl report

## 1. What was built

- The equipment search (`q` on `GET /api/equipment`) splits the text into words. A node is found when every word
  matches at least one of: code, name, notes, type name, class name, class code, manufacturer name, model
  designation. At most 8 words are used. Unit and site names are not searched.
- All search boxes got one hint form. The picker shows a hint line while there is no result.
- Each match in the picker has a third line: model label, class code, lifecycle badge, criticality badge.
- Raise ticket and contract › Add machine show an *Open equipment page* link (new tab) after the pick.

## 2. How it works

`list_equipment` loops over `q.split()[:MAX_SEARCH_WORDS]` and adds one `AND`-ed condition per word, each an `OR`
over the eight fields, with `like_pattern(word)` (the `%` and `_` escaping stays per word). Empty or blank text adds
no condition. The picker's third line uses fields the list row already sends (`model_label`, `class_code`,
`lifecycle`, `effective_criticality`); no new request. The links are `router-link` with `target="_blank"
rel="noopener"`, the existing pattern of `RaiseTicketView.vue`.

## 3. Files touched

- `backend/equipment.py` — `MAX_SEARCH_WORDS`, the per-word search condition.
- `backend/tests/test_equipment_api.py` — four new tests (class name and code; any order; across fields; eight words).
- `frontend/src/components/EquipmentPicker.vue` — placeholder, hint line (`v-if="!results"`), third line, "More found" text.
- `frontend/src/views/EquipmentView.vue` — placeholder `Code, name, model, class or notes`.
- `frontend/src/views/equipment/EquipmentMoveModal.vue` — placeholder and "More found" text.
- `frontend/src/views/RaiseTicketView.vue` — *Open equipment page* link beside *Change*.
- `frontend/src/views/contracts/ContractMachineDialog.vue` — the link in `picked-machine`.
- `frontend/e2e/tickets-raise.spec.js`, `frontend/e2e/contracts.spec.js` — one new `S092:` test each.
- `docs/Plan.MD` (line 315), `docs/steps/device-checks.md` (row 63).

No change to `api.js`, the router, `FormModal` or `e2e/support/`.

## 4. Decisions taken

- The eight `LIKE` parameters per word are repeated with a literal `* 8` and a comment, not a constant: one use.
- `ContractMachineDialog.vue`: the `picked-machine` row got `flex-wrap` (it had `d-flex align-items-start gap-2`),
  so the second button wraps on a narrow dialog instead of squeezing the text. The brief did not name this class.
- The picker's third line: the class code is plain `text-secondary` text; the model label has no style. Gap `mt-1`
  above the line.
- In the Raise ticket browser test the class code is checked as the node code without its trailing serial digits.

## 5. Not done, deferred or assumed

- Test results (run name `s092c1`):
  - Backend, changed modules (`test_equipment_api.py`, `test_removed_documents_api.py`): 250 passed.
  - All suites (`tooling/run-tests.bat`): backend 4471 passed, frontend 412 passed, tooling 231 passed.
  - `npx vite build`: passed.
  - Browser, the two new `S092:` tests alone (phone-chromium, one lane): both passed. The first run of the contracts test failed: after the pick the focus left the dialog, so `expectDialogFits` timed out in `openDialog`. Fixed in the test by focusing *Change* before the fit check.
  - Browser, targeted (`tickets-raise`, `contracts`, `readings`, `equipment`, `screens`, Normal): 189 passed, 2 skipped.
  - Browser, whole suite once (Normal): 375 passed, 15 skipped, 0 failed.
- Red-then-green of the new tests was not shown (new step, not a fix round).
- The shared-file rule does not apply (no shared frontend file touched).

## Docs updated

- `docs/Plan.MD` line 315: what the search finds.
- `docs/steps/device-checks.md`: row 63 (PWA new-tab check, IT Admin, important).
- Schema docs: none, because no migration.
- `.claude/CLAUDE.md`: none, because no invariant, command, port or secret changed.

## Manual checks

- [ ] **important** In the installed app on an Android phone and an iPhone, tap *Open equipment page* on Raise ticket; the half-filled form is still there on return (device-checks row 63).
- [auto] Words in any order find the machine; the match shows class and model; the card links to its page — `tickets-raise.spec.js::S092: words in any order find the machine by its model; the match shows class and model; the card links to its page`
- [auto] Add machine links to the machine's page in a new tab; the dialog fits — `contracts.spec.js::S092: after the pick, Add machine links to the machine's page in a new tab`

## Feedback

- hindrance: `expectDialogFits` fails after a pick that removes the focused button; nothing in `support/dialogs.js` says to refocus first (1 failed run, 2 min).

## Fix rounds

### Round 1

- **CR1-01 (minor) — Fixed.** `test_search_finds_the_class_name_and_code` now changes the node's model to a model of a
  second class (`_put(..., model_id=…)`; the code is kept, S012), asserts the second class code is not in the node's
  code, and searches by that class code. Fails without the fix: with `c.code` removed from the search (placeholder and
  parameter count kept in step), `assert [] == [3]` on the class-code search; passes with it restored. Run name
  `s092f1`: `tests/test_equipment_api.py` 214 passed.
- **CR1-02 (nit) — Fixed.** `tickets-raise.spec.js` now checks the class code with
  `match.getByText(<class code>, { exact: true })`, not layout classes. The S092 test alone (phone-chromium, one lane):
  1 passed. No red run: a check of text the user sees, not a fix for a fault.
- Not touched: the `test_readings_api.py` timing test (outside this step).
- Docs updated: none new, because the round changes tests only (the list above stands).

#### Feedback

- none
