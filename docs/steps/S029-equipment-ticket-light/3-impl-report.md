Step: S029 — Ticket light on the equipment list
Doc: impl-report
Author: Coder (Sonnet)
Date: 23-10-2026

# S029 — Implementation report

## 1. What was built

- A ticket bulb on `/equipment`, in a narrow column after the tick box and before *Code*: red (breakdown open, machine not back in service), amber (any other open ticket), green (none), a grey dash where the user holds no `ticket:read` at the row's unit, nothing on a scrapped row. Each bulb has a tooltip and an accessible name.
- A *Tickets* filter (*All equipment*, *Down now*, *Any open ticket*) in the URL as `tickets=down|open`.
- `GET /api/equipment` gains the `tickets` filter and a `ticket_light` field on every row (`down` / `open` / `none` / `null`).
- One definition of "down" and "open" states in `tickets_core`, used by the downtime figures, the alerts and the list.

## 2. How it works

- `equipment.list_equipment` reads `ticket_units = accessible_unit_ids(cur, "ticket:read")` (`None` = every unit).
- `_ticket_light_column` builds the column: `CASE WHEN u.id IN (ticket_units) THEN <down / open / none> END`. For a row outside `ticket_units` the CASE is NULL and the ticket subqueries are never evaluated, so no ticket fact is read for it. An empty set gives a plain `NULL` column. `None` has no gate.
- The two `EXISTS` use `t.equipment_id = e.id OR t.component_id = e.id` (§ 3a *Levels*). Red: `intensity = 'critical'` and `state IN DOWN_STATES`. Amber: `state <> 'closed'`.
- `tickets=…`: adds `u.id IN (ticket_units)` first (an empty set returns the empty page at once), then the same `EXISTS` as the bulb. The `COUNT(*)` for `total` uses the same `where`, so the pager is right.
- `enum_arg("tickets", ("down", "open"))`: a missing key is no filter; any other value, an empty one too, is 400.
- `ticket_light` is added in `list_equipment` beside `part_count`, not in `_summary` or `_list_filters`, so the asset list and its print are unchanged.
- Frontend: `EquipmentView.vue` shows the column and the filter when `userPermissions` holds `ticket:read` (the union over sites; other sites' rows get the dash). `TicketLight.vue` only renders; texts are in `ticketLabels.js`. `tickets` is added to the `listUrl()` keys; *Print asset list* ignores it (`assetList.js` passes only the shared filters, unchanged).

## 3. Files touched (9, not counting the report, brief status and README row)

- `backend/tickets_core.py`: `_DOWN_STATES` renamed `DOWN_STATES`.
- `backend/alerts_core.py`: imports `DOWN_STATES` and `OPEN_STATES`; own copies dropped; unused imports removed.
- `backend/equipment.py`: `tickets` filter, `ticket_light` column and its unit gate.
- `backend/tests/test_equipment_api.py`: `TestTicketLight` (18 cases); `test_row_fields` gains `ticket_light`.
- `frontend/src/utils/ticketLabels.js`: `TICKET_LIGHT_LABELS`, `TICKET_FILTER_CHOICES`.
- `frontend/src/components/TicketLight.vue`: new.
- `frontend/src/views/EquipmentView.vue`: column, filter, URL key.
- `frontend/tests/ticketLabels.test.js`: the new labels.
- `frontend/e2e/equipment.spec.js`: three `S029:` tests.

S028's uncommitted edits in `tickets_core.py`, `alerts_core.py` and `ticketLabels.js` were left as they were; mine sit on top.

## 4. Decisions taken

- Column header icon is `fa-ticket` (Font Awesome is already loaded), title and accessible name "Tickets".
- The bulb is a small CSS circle with Bootstrap colours (`bg-danger`, `bg-warning`, `bg-success`); no new CSS file.
- `_ticket_light_column` and `_TICKET_FILTERS` are module-level in `equipment.py`, so the bulb and the filter share one SQL text for "down" and "open".
- The scrapped rule is in the frontend only (`v-if` on status), as the brief says; the API sends `none` for a scrapped row (it holds no open ticket).
- e2e tests raise as `supervisor`: `operator` gets 404 on the MCC1 machines (not in its units).
- e2e rows are found by `tbody tr` with the machine code, because the list's rows carry `role="link"`; the filter is found as `combobox` named "Tickets" (the header icon has the same name).

No departure from the brief.

## 5. Not done, deferred or assumed

- Nothing deferred. Out-of-scope items of the brief stay out (counts, closed view, sorting, live refresh, planned stops as red).
- The brief says "about 9 files"; the step touches 9 files, one of them new (`TicketLight.vue`).

## 6. Tests run

- Full suite, `YANTRA_TEST_RUN=s029c1 tooling/run-tests.bat`: backend 2316 passed, frontend 119 passed, deps 42 passed, tooling 91 passed. `npx vite build`: built.
- Targeted e2e, `tooling/run-e2e-tests.bat e2e/equipment.spec.js e2e/screens.spec.js` (equipment screen changed; `screens.spec.js` opens `/equipment` for every role, so the storekeeper's list without the column is covered): 48 passed (three projects, 6 lanes). No shared frontend code changed, so not the full suite.
- Access check tests (`TestTicketLight`): engineer at site A and storekeeper at site B (`user_at_sites`): `ticket_light` null at B, `tickets=down` / `open` list A only with the right `total`; storekeeper alone: every row null, `tickets=down` empty page; admin sees every row.

## Manual checks

- [auto] A breakdown shows "Down — breakdown open", a defect "Open ticket", a clean machine "No open ticket" — frontend/e2e/equipment.spec.js::S029: the equipment list shows a red, amber and green bulb with a name each
- [auto] *Down now* shows only the red row and puts `tickets=down` in the URL; *All equipment* clears it — frontend/e2e/equipment.spec.js::S029: Down now lists only the red row and the URL carries it; All equipment clears it
- [auto] At phone width the bulb is in view without scrolling and the filter fits — frontend/e2e/equipment.spec.js::S029: the bulb is in view without scrolling and the Tickets filter fits the screen

On a real device: none (no rows added to `docs/steps/device-checks.md`).

## Fix rounds

### Round 1

- **CR1-01 — Accepted, fixed.** `EquipmentView.vue` `listUrl()` now skips the `tickets` key when `canSeeTickets` (`ticket:read`) is false, so a bookmarked `?tickets=down` shows the plain list to a user without the column and filter. The URL itself is left alone. New e2e test `frontend/e2e/equipment.spec.js::S029: a bookmarked tickets=down shows the plain list to a storekeeper, who has no ticket column` (storekeeper opens `/equipment?tickets=down` and sees the red, amber and green machines, and no Tickets filter).
- CR1-02, CR1-03, CR1-04, CR1-05: not asked for by the user. CR1-02 (colour alone on a
  phone, no tooltip on touch): accepted as built by KLA, 23-10-2026 (not fixed, no
  objection at gate B).
- Red without the fix: not run in this round (the rule came after it, 23-10-2026); the code
  reviewer's r2 reasons that the test fails without the fix.
- Tests: frontend `YANTRA_TEST_RUN=s029c2` 119 passed; targeted e2e `e2e/equipment.spec.js e2e/screens.spec.js` 51 passed. Full backend suite not re-run (no backend change).
