```
Step: S087 — Contracts across sites
Doc: code-review r3
Author: Code reviewer (Opus)
Date: 31-10-2026
```

# S087 — code review, round 3 (amendment A1)

**Verdict: no `blocker` or `major` finding is open.** Amendment A1 is built as § 10 A1 asks. Three nits are new.
CR1-03 (nit) stays open from round 2; A1 did not touch `backend/contracts.py`.

Files re-read: the round-3 diff (`step_snapshot.py diff S087 --from-round 3`), `frontend/src/stores/equipment.js`
(`filterableUnits`, `unitSites`, `readingSites`), `frontend/src/components/EquipmentPicker.vue` (template),
`backend/contracts.py` lines 520–530 (the add-line unit check), `backend/equipment.py` `accessible_unit_ids`,
the `readingSites.test.js` fixtures, and the readings sheet's site select (for the pattern).

## Tests run

Run name `s087cr3`:

- `tooling/run-frontend-tests.bat tests/readingSites.test.js`: **7 passed** (4 `readingSites`, 3 `unitSites`).
- No full unit run. A1 changed only frontend files, and the coder's run `s087a1` was green (backend 4467, frontend
  412, tooling 231 passed; `npx vite build` built).
- No browser run. The coder's targeted run names the right specs (`e2e/contracts.spec.js`, `e2e/screens.spec.js`,
  Normal): 69 passed, 1 skipped, 0 failed. No finding of mine needs a re-run.
- Schema docs: no migration changed in this round.

## Status of earlier findings

| ID | Severity | Status |
|---|---|---|
| CR1-01 | blocker | Fixed (round 2). |
| CR1-02 | nit | Fixed (round 2). |
| CR1-03 | nit | **Open** (round 2); not in A1's scope. |

## A1 against the brief

- **Options:** `unitSites` takes the active sites of the units `filterableUnits` gives from `my-units.unit_ids`.
  These are the units of `accessible_unit_ids(cur)` (key `equipment:read`), the same check the add-line route makes
  (`backend/contracts.py:526`). So the select offers no site where the API would refuse every machine. Correct.
- **One site preselected:** `openAdd` awaits the three caches, then sets `siteId` when `siteChoices` has one entry.
  The engineer's e2e test checks the value and that BRICKS is not offered. Correct.
- **Search disabled until a site is chosen:** `:disabled="siteId === null"` and the hint "Choose a site first."
  (`data-testid="site-hint"`). The A1 e2e test asserts both, then that the search is enabled. Correct.
- **Site change clears the search and the pick:** `@change="changeMachine"` clears `picked` and bumps `pickerKey`.
  The select stays visible after a pick, so a change also clears a picked machine. The e2e test checks the cleared
  search (see CR3-01 for the pick).
- **Site not sent; no API change:** `lineBody` and `save` are unchanged; `siteId` goes only to the picker as
  `site_id` on `GET /api/equipment`, a filter that already exists (`backend/equipment.py:603`). No backend file
  changed. Correct.
- **Load failure:** a failed cache load shows the `ApiError` message under the select; the search stays disabled.
- **Coder's decisions:** the `disabled` prop beside `siteId` is the smallest way to keep the input in place with its
  label; a hidden input would move the layout. Site code alone matches the readings sheet. Both are listed in the
  A1 section's "Decisions taken". Accepted.
- **Scope B:** "Site", "Choose a site", "Choose a site first.", "You have no unit at any site." are short and plain.
- **Tags:** the new test is a logic test and is untagged; correct by the layout-tag rule.
- **Manual checks and docs:** the A1 section lists two `[auto]` checks with their tests and no device check. "Docs
  updated: none" is right: no doc in § Docs to keep current names this dialog.

## Nits

- **CR3-01** (nit) `frontend/e2e/contracts.spec.js:390`: the A1 test checks that a site change clears the search, but
  not that it clears a picked machine (an A1 rule). Pick a machine at BRICKS, change to SMTW, and assert that
  `picked-machine` has count 0 and the search is empty.
- **CR3-02** (nit) `frontend/src/stores/equipment.js:43-50`: the docstring says "every active unit for all-units
  access", but `filterableUnits` returns inactive units too for an all-units user. So an active site whose units
  are all inactive is offered to IT admin or admin. Filter `u.active` in `unitSites`, or fix the docstring.
- **CR3-03** (nit) `frontend/src/views/contracts/ContractMachineDialog.vue:93`: the Site select is `form-select`
  while the search under it is `form-control-lg`. On a phone the first tap target of the dialog is the smaller
  one. Use `form-select form-select-lg`.

## Manual browser check

None new for A1. The A1 checks are `[auto]`.

## Checked and found consistent

- `unitSites` and its three unit tests (loaded and not-loaded lists, all-units, no units, an inactive site).
- `siteChoices` guards `myUnits` being null before the load (the fault the coder's first e2e run found).
- `EquipmentPicker` callers elsewhere pass no `siteId` or `disabled`; the defaults (`null`, `false`) keep their
  behaviour.
- The Edit price path (`creating` false) shows no Site select.
- The existing Add machine e2e tests choose the site first, as A1 asks.

## Feedback

- idea: the orchestrator's prompt listed A1's rules one by one; it made the brief-to-code check quick and could be
  the default for an amendment round (this run, about 2 min to map the rules).
- none else.
