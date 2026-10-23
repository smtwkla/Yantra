Step: S029 — Ticket light on the equipment list
Doc: brief
Author: Planner (Opus)
Date: 23-10-2026 (revised 23-10-2026: brief-review r1)
Track: light
Baseline: d686fcd + uncommitted S028
Status: In code review

# S029 — Ticket light on the equipment list

**The request (KLA, 23-10-2026).** On the equipment list, show which equipment is down
because of a breakdown ticket: a small column with a traffic-light bulb. Also filter the
list to the equipment that has tickets.

**Track: light**, kept by the user (23-10-2026) over BR1-01. No migration, no new key, no
new endpoint (one more column and one more filter on `GET /api/equipment`), about 9 files.
The step adds a per-row access check (`ticket:read` at the node's site) through the existing
`accessible_unit_ids` helper; the code review checks it.

## 1. What will be built

- A **ticket bulb** on `/equipment`, in a narrow column **just after the tick box, before
  *Code***, so it stays in view on a phone (the table scrolls sideways there). One bulb
  per row:

  | Bulb | Meaning | Rule (tickets on this row's node, see § 3a *Levels*) |
  |---|---|---|
  | Red | Down: a breakdown is open and the machine is not back in service | a ticket with intensity `critical` in state `raised`, `acknowledged`, `scheduled` or `in_progress` (`tickets_core.DOWN_STATES`) |
  | Amber | Open ticket, not down | any other open ticket: a defect (`degraded` / `initial`), or a breakdown already `back_in_service` and waiting to be closed |
  | Green | No open ticket | none of the above |
  | Grey dash | Not shown to this user | the user does not hold `ticket:read` at the node's site |
  | Nothing | — | a scrapped row (shown only with *Show scrapped*) |

  Red wins over amber, amber over green. Each bulb, and the grey dash, has a tooltip and
  an accessible name, so the colour is never the only signal:
  "Down — breakdown open", "Open ticket", "No open ticket", "Tickets not shown".
  The column header is an icon with the title "Tickets".
- A **Tickets** filter next to the other filters: *All equipment*, *Down now* (red),
  *Any open ticket* (red or amber). It lives in the URL query like the others
  (`tickets=down|open`), so a filtered list can be bookmarked.
- *Print asset list* ignores the Tickets filter: the print shows the units' equipment, not
  today's tickets.

**Out of scope:** counting tickets, listing them on the row, a "closed tickets" view, a
bulb on the equipment page or the asset list, the Tickets screen's own filters, sorting by
bulb, live refresh (the list loads on open as today). A planned stop (S019's
`machine_stopped` on a defect) shows **amber**, and *Down now* does not list it: the light
shows breakdowns only, as asked (BR1-05).

## 2. Standards and practice

- **TPM — visual management**: a traffic light shows the state of a machine at a glance,
  as an andon does. The red / green reading is the one the shop floor already uses.
- **ISO 14224 failure impact, EN 13306 "failure" and "down state"**: *critical* means the
  item stopped (a failure; the item is in a down state), so it is the red case; *degraded*
  (EN 13306 "partial failure") and *initial* (ISO 14224 "incipient") mean it still runs, so
  they are amber. Yantra's own words stay *Down*, *breakdown*, *defect*
  (Maintenance-Philosophy glossary).

## 3. Where

| File | Change |
|---|---|
| `backend/tickets_core.py` | rename `_DOWN_STATES` (line 334, used by `ticket_times`) to public `DOWN_STATES`, the one definition of "down" |
| `backend/alerts_core.py:41-43` | drop its own `_DOWN_STATES` and `_OPEN_STATES`; import `DOWN_STATES` and `OPEN_STATES` from `tickets_core` |
| `backend/equipment.py` (`list_equipment`) | new `tickets` filter (`enum_arg`, `down` / `open`) and a `ticket_light` field on every row (`down` / `open` / `none` / `null`), computed in `list_equipment` beside `part_count` — **not** in `_summary` (the asset list shares it) and **not** in `_list_filters` |
| `frontend/src/utils/ticketLabels.js` | the bulb labels and the filter choices, beside the other ticket labels |
| `frontend/src/components/TicketLight.vue` | new: the bulb (circle, colour, tooltip, accessible name) or the grey dash |
| `frontend/src/views/EquipmentView.vue` | the column, the filter select, `tickets` added to the URL keys in `listUrl()` |
| `backend/tests/test_equipment_api.py` | new tests (§ 5); `TestListing::test_row_fields` (line 708) gains `ticket_light` |
| `frontend/tests/ticketLabels.test.js` | the new labels |
| `frontend/e2e/equipment.spec.js` | e2e tests (§ 5) |

## 3a. Rules the coder needs

- **Permission.** The bulb and the filter use `ticket:read` at the node's site
  (`SITE_SCOPED`). In `list_equipment`: `ticket_units = accessible_unit_ids(cur, "ticket:read")`
  (`None` = every unit: admin, it_admin). Rows in other units get `ticket_light = null`
  (the bulb's SQL is guarded by the same unit list, so no ticket fact leaves for them).
  `tickets=…` also adds `u.id IN (ticket_units)`; an empty set gives an empty list, so the
  filter never reveals tickets of a unit the user cannot read tickets in.
  The frontend shows the column and the filter when `userPermissions` holds `ticket:read`.
  That list is the union over the user's sites, so a user with `ticket:read` at one site
  sees the column, with grey dashes on the other sites' rows. A user without it anywhere
  sees neither.
- **Inputs.** `tickets` missing = no filter. Any value other than `down` / `open`, an empty
  one too, → 400 (`enum_arg`, as for `status`, `api_common.py:146`). The frontend leaves
  the key out when the choice is *All equipment*.
- **Scrapped rows.** `ticket_light` is `none` there (a scrapped node holds no open ticket,
  S017 § 5.8); the frontend draws nothing for a scrapped row.
- **Levels** (as `tickets._equipment_filter`, `tickets.py:498`): a machine row counts
  `t.equipment_id = e.id`, so tickets on any of its parts too. A component-unit or
  component row counts `t.component_id = e.id`: tickets raised on that node itself only.
  A component-unit's bulb does **not** show a ticket raised on one of its components; the
  machine's bulb does. `t.equipment_id = e.id OR t.component_id = e.id` gives exactly this,
  because a machine is never a `component_id` and a part is never an `equipment_id`.
- **Count query.** The total uses the same conditions, so the pager is right.
- **Database down / worker.** Nothing new: same route, same `get_db()` 503.
- **Locks.** None; plain reads.

## 4. Design decisions

1. **Compute the bulb in the list query**, two `EXISTS` per row, for at most 50 rows
   (`ix_tickets_equipment_state`, `ix_tickets_component_state` cover them). Rejected: a
   second endpoint the page calls after the list — one more round trip, and the filter
   could not use it.
2. **Amber for every other open ticket**, so the filter *Any open ticket* and the bulb
   agree. Rejected: only red and green — a degraded machine with a leak ticket would show
   green, which hides work (TPM: early signs matter).
3. **A breakdown that is `back_in_service` is amber, not red**: the machine runs again;
   only the close is open. This matches S018's downtime, which stops at back in service.
4. **A `scheduled` breakdown stays red.** A deferred breakdown is still the item stopped
   (S019: downtime runs on critical tickets while scheduled).
5. **Grey dash for a user with no ticket right at that site**, not green: green would
   claim "no tickets" where the user cannot know.
6. **One definition of "down" and "open"**: `DOWN_STATES` and `OPEN_STATES` in
   `tickets_core`, used by the downtime figures, the alerts and the list.
7. **The bulb beside the code, not after *Status*** (BR1-06): on a phone the table scrolls
   sideways and a column at the end is out of view. Rejected: after *Status* (first draft).
8. **No bulb on a scrapped row** (BR1-07): green there would read as "fine".

## 5. Tests and acceptance

**Backend** — a new `TestTicketLight` in `test_equipment_api.py`, with `make_ticket` and
`set_ticket_state`:
- no ticket → `none`; critical raised → `down`; critical `scheduled` → `down`; critical
  `back_in_service` → `open`; degraded raised → `open`; closed → `none`;
  critical + degraded on one node → `down`.
- a ticket on a component → the machine's row is `down`; the component's row (level
  *component*) is `down`; its component-unit's row is `none`.
- `tickets=down` and `tickets=open` return the right rows and the right `total`;
  `tickets=bogus` and `tickets=` → 400.
- a user with `equipment:read` but `ticket:read` at only one of two sites
  (`user_at_sites`) → `ticket_light` null on the other site's rows, and `tickets=down`
  returns only rows of the site where it is held.
- the asset list (`/api/equipment/asset-list`) rows have no `ticket_light`.
- Existing test that changes: `TestListing::test_row_fields` (line 708), the exact key
  set of a list row, gains `ticket_light`. `test_role_matrix` and `conftest._TABLES` are
  unchanged (no new key, no new table).

**Automated (browser)** — `equipment.spec.js`, names `S029: …`; run targeted
`equipment.spec.js` + `screens.spec.js`. The three projects share one database and
`screens.spec.js` raises a ticket on `seed.extruder`, so each test creates its own machines
(`createEquipment`), raises by API (`raiseByApi`), and judges rows within `?q=<its names>`:
- a breakdown on a machine → its row shows the bulb named "Down — breakdown open"; a
  defect → "Open ticket"; a clean machine → "No open ticket".
- *Down now* shows only the red row and puts `tickets=down` in the URL; *All equipment*
  clears it.
- phone width (Pixel 7 and iPhone projects): the bulb is in view without scrolling, and
  the filter select fits.

**On a real device:** none.

## 6. Open questions and assumptions

- **Assumed** (§ 4.2): amber for any other open ticket.
- **Assumed**: the filter has two choices (*Down now*, *Any open ticket*), not a plain
  yes/no.
- **Assumed**: the column shows on every level (machines, component-units, components).
- **Assumed** (BR1-05): a planned stop on a defect is amber, not red.

## 7. Amendments

None.

## 8. Review log

| ID | Severity | Answer |
|---|---|---|
| BR1-01 | major | Rejected by the user (23-10-2026): light track kept; the access check reuses `accessible_unit_ids`, and the code review covers it. The design is unchanged. |
| BR1-02 | minor | Accepted: rename `tickets_core._DOWN_STATES` to `DOWN_STATES`; `alerts_core` imports it and `OPEN_STATES` (§ 3, § 4.6). |
| BR1-03 | minor | Accepted: `test_row_fields` named in § 5; `ticket_light` on every row, computed in `list_equipment`, not `_summary` (§ 3). |
| BR1-04 | minor | Accepted: § 3a *Levels* states that a component-unit's bulb counts its own tickets only; test added. |
| BR1-05 | minor | Accepted: planned stops stay amber, stated in § 1 out of scope and § 6. |
| BR1-06 | minor | Accepted: bulb before *Code* (§ 1, § 4.7). |
| BR1-07 | minor | Accepted: no bulb on scrapped rows (§ 1, § 4.8). |
| BR1-08 | minor | Accepted: e2e set-up rules in § 5. |
| BR1-09…BR1-15 | nit | Accepted: `user_at_sites` test; grey-dash name; *All equipment*; EN 13306 cited by term; labels in `ticketLabels.js`; *Print asset list* ignores the filter; union noted. |
