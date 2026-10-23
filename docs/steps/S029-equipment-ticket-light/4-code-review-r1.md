```
Step: S029 — Ticket light on the equipment list
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 23-10-2026
```

# S029 — Code review r1

**Verdict: no blocker or major finding is open.** 2 minor, 3 nit. Every suite is green, and the targeted e2e run passes on the three projects.

Scope: the 9 files of the impl report, S029's hunks only. The uncommitted S028 changes in the same files (`tickets_core.py` backdating, `alerts_core.raise_alert(age)`, `ticketLabels.daysAgoHint`, `tickets.py`, the raise and event screens) are not reviewed here.

## Test results (run by the reviewer, 23-10-2026)

| Run | Result |
|---|---|
| `YANTRA_TEST_RUN=s029cr1 tooling/run-tests.bat` | backend **2316 passed**; frontend **119 passed**; deps **42 passed**; tooling **91 passed**. All suites PASSED. |
| `npx vite build` (`frontend/`) | built in 3.9 s, no errors |
| `tooling/run-e2e-tests.bat e2e/equipment.spec.js e2e/screens.spec.js` | **48 passed** (Pixel 7 Chromium, iPhone 14 WebKit, desktop Chromium; 6 lanes), 82 s. Exit 0. |

Why these specs: S029 changes the equipment screen (`equipment.spec.js`, S003/S006/S012 and the new `S029:` tests), and `screens.spec.js` opens `/equipment` for every role, which covers the list without the column (storekeeper). No shared frontend code changed (`FormModal.vue`, `useFormModal.js`, `api.js`, router, auth store, `e2e/support/`), so not the full suite.

## The access check (the user's condition for the light track)

Checked closely. **No path reveals a ticket fact for a unit where the user lacks `ticket:read`.** Facts:

- `ticket_unit_ids = accessible_unit_ids(cur, "ticket:read")` (`equipment.py:522`). `ticket:read` is in `SITE_SCOPED` (`config_rbac.py:165`), and `user_unit_ids` asserts that. `None` comes only from the admin bypass or a token role that holds the key with `equipment:read_all_units` (it_admin).
- The column (`_ticket_light_column`, `equipment.py:156`): an empty set gives a literal `NULL` with no subquery; a non-empty set wraps the whole CASE in `CASE WHEN u.id IN (…) THEN … END`, so a row outside the set is `NULL`, whatever its tickets.
- The filter (`equipment.py:523-532`): with `tickets=…`, an empty set returns the empty page before any query; otherwise `u.id IN (ticket units)` is ANDed into `conditions` **before** the `EXISTS`. `total` is counted with the same `where`, so the pager cannot leak a count either.
- `u` is the row's root unit (`NODE_JOINS`: `COALESCE(gp.unit_id, p.unit_id, e.unit_id)`), so a component row is gated at its machine's unit. The Tickets screen shows a ticket when `t.unit_id` **or** `m.unit_id` (the machine's current unit) is readable (`tickets._visible_condition`, `tickets.py:180`). The bulb is gated on `m.unit_id` alone, so it shows a strict subset of what the Tickets screen already shows. A machine moved out of a readable unit shows the dash, which reveals nothing.
- Params order is right: the column's params come first because the column sits in the SELECT list before `FROM … WHERE`; the `COUNT(*)` gets only `params`.
- Tests: `TestTicketLight::test_ticket_read_at_one_of_two_sites` (engineer at A, storekeeper at B: B's row `null`; `down` and `open` list A only, `total` 1) and `test_no_ticket_read_anywhere` (every row `null`, filter gives the empty page).

## Findings

### CR1-01 — minor — a bookmarked `tickets=` filter is applied invisibly for a user without `ticket:read`

- **Where:** `frontend/src/views/EquipmentView.vue:157` (`listUrl` sends `tickets` from the URL) and `:277` (the select is `v-if="canSeeTickets"`).
- **Problem:** the select is hidden from a user with no `ticket:read`, but `listUrl()` still sends a `tickets` value taken from the URL. The API then answers the empty page (`equipment.py:526`). The screen shows "No equipment matches these filters." with no visible filter to clear. The same view already guards against this for the type filter: "so a bookmarked type filter is never applied invisibly" (`EquipmentView.vue:82`).
- **Failure scenario:** a supervisor shares the link `/equipment?tickets=down` in a WhatsApp group. A storekeeper opens it and sees an empty equipment list. Every visible filter reads "All …", so the storekeeper concludes the unit has no equipment.
- **Fix:** send `tickets` only when `canSeeTickets` is true (one condition in `listUrl`), so the storekeeper gets the plain list. An e2e or unit check for it is cheap: open `/equipment?tickets=down` as the storekeeper and expect a row.

### CR1-02 — minor — on a phone the colour is the only signal a sighted user gets

- **Where:** `frontend/src/components/TicketLight.vue:12-19`.
- **Problem:** the brief says each bulb has a tooltip and an accessible name "so the colour is never the only signal" (§ 1). The tooltip is a `title` attribute. A touch screen never shows a `title`, and the accessible name reaches only a screen reader. On the Pixel and iPhone the floor uses, red, amber and green dots of one shape are the only cue. About 1 man in 12 has red-green colour blindness and cannot tell the red bulb from the green one. The e2e test passes because it reads the accessible name, not what is drawn.
- **Failure scenario:** a colour-blind technician scans the list on a phone for stopped machines. Red and green dots look the same to him, so he misses the stopped mixer. (*Down now* still works, so the impact is limited to reading the bulbs.)
- **Fix (recommendation; the user decides):** draw a different mark per state, for example Font Awesome `fa-circle-xmark` (down), `fa-circle-exclamation` (open) and `fa-circle-check` (none) in the same colours, so the shape carries the meaning too. Alternatively accept colour-only on touch and add a row to `docs/steps/device-checks.md` so the decision is recorded.

## Nits

- **CR1-03** (nit) `frontend/e2e/equipment.spec.js:108`: the new S029 block was inserted between the doc comment "A machine at SMTW.MCC1 made through the API as admin" and `createEquipment`, so that comment now sits above `lightMachines`; move the block above the comment.
- **CR1-04** (nit) `frontend/src/views/EquipmentView.vue:325-327`: the header icon and the filter select both have the accessible name "Tickets", which made the e2e test pick the select by role (`combobox`); name the icon "Ticket light" so each control has its own name.
- **CR1-05** (nit) `frontend/src/views/EquipmentView.vue:325,350`: the bulb column reuses the `tick-cell` class of the tick box column for its width; a class of its own (or a comment) keeps a later change to the tick box column from moving the bulb.

## Checked and found consistent

- **Brief § 1 rules.** Red = `critical` in `DOWN_STATES` (raised, acknowledged, scheduled, in_progress); amber = any other non-closed ticket, including a `back_in_service` breakdown and a defect; red wins (`CASE` order); scrapped rows draw nothing (`v-if` on status) while the API sends `none`; the grey dash for `null`. Labels and filter choices match § 1 word for word.
- **Levels (§ 3a).** `t.equipment_id = e.id OR t.component_id = e.id` gives the machine its parts' tickets and a component-unit only its own; `test_levels` covers machine, component and component-unit.
- **Inputs.** `tickets` missing = no filter; `bogus` and empty → 400 with `field: tickets` (`enum_arg`); the frontend leaves the key out for *All equipment* (`update` drops empty values).
- **One definition of "down" and "open".** `tickets_core.DOWN_STATES` (renamed), used by `ticket_times`, `alerts_core._SEND_STATES` and the list; `alerts_core` imports `OPEN_STATES` and drops its copies. No other `_DOWN_STATES` remains.
- **Layers.** The bulb rule is SQL in `equipment.py` beside `part_count`, not in `_summary` (the asset list) or `_list_filters`; the frontend only maps the value to a colour and a text. `TicketLight.vue` holds no rule.
- **Print asset list ignores the filter.** `assetList.FILTER_KEYS` has no `tickets`; the backend asset list never reads it; `test_asset_list_has_no_light`.
- **Security.** Route still `@require_perm("equipment:read")`; no actor from the client; every value is a bound parameter (the f-strings only join fixed SQL and `%s` placeholders).
- **Database down, locks.** Same route and `get_db()`; plain reads, no lock needed.
- **Performance.** Two correlated `EXISTS` per row for at most 50 rows, on `ix_tickets_equipment_state` and `ix_tickets_component_state`; right-sized.
- **Tests.** `TestTicketLight` covers the § 5 list: each state and intensity, two tickets on one node, levels, scrapped, both filters with `total`, 400s, the two access cases, the asset list. `test_row_fields` gains `ticket_light`. The three `S029:` e2e tests assert what the user sees (the named bulb per row, the rows under *Down now*, the URL, the bulb and select inside the viewport); no dialog is opened, so `expectDialogFits` does not apply.
- **Manual checks.** The impl report's `## Manual checks` carries the three automated checks as `[auto]` with their tests; the brief has no real-device check, and none was added to `device-checks.md`.
- **Scope.** Everything in § 1 is built; nothing out of scope (counts, sorting, live refresh) was added. The impl report's "Decisions taken" lists the icon, the CSS circle and the e2e locator choices; no unreported departure.
- **Writing.** Screen texts follow scope B ("Down — breakdown open", "Open ticket", "No open ticket", "Tickets not shown", "All equipment", "Down now", "Any open ticket"). The impl report follows scope A.
- **Track.** Light, kept by the user over BR1-01; the access check the user asked for is verified above.

## Manual browser check for the user

- Open `/equipment` on a phone and judge whether the bulbs read clearly at a glance (see CR1-02).
- Open `/equipment?tickets=down` as a user without `ticket:read` (e.g. a storekeeper) once CR1-01 is fixed, and confirm the plain list shows.
