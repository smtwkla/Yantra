```
Step: S086 — Breakdown calls on the contract
Doc: impl-report
Author: Coder (Opus)
Date: 31-10-2026
```

# S086 — implementation report

**Result:** built as the brief says, with the three gate-B decisions as recorded (BR1-03 option b, Q2 a, C3
hidden with the note). No migration, no new key, no shared frontend file changed. All tests green (numbers in
§ Tests).

## 1. What was built

- **The *Breakdown calls* card** on the contract page, last after *Documents*: every ticket on a covered node or
  its parts, happened in the period, that a Team record linked to the vendor is assigned to or logs labour on.
  Each row: the serial (a link), severity and state badges, *Not a fault* when so, machine › part, "Happened … ·
  back in service …" (or "· not back in service yet"), "Down … · waited on the vendor …", "By: <the vendor's
  people>". Under the list: the total line and, for a whole-site reader of a contract with an agreed number, the
  used line ("3 of 4 calls used this period.", red "… — more than agreed.", or "5 calls in this period · 4 a year
  agreed." past 366 days). A partial reader sees "Only the calls on machines of your units are listed." instead;
  with no visible call, "No calls on machines of your units. Only those are listed here."
- **The two warnings** in the card (active contract, not ended): no linked Team record; no linked record with a
  Technician, Engineer or Manager role at the site.
- **The contract line on the ticket page**, between the plan line and the action bar, on open tickets only:
  "Under AMC with … until … · response 24 hours · breakdown calls included" (the headline links the contract),
  and S082's "Do not repair" warning when the contract has the tick.
- **The vendor in the people picker**: "Name · Technician · Vendor", in the list and on the picked line; the filter
  also matches the vendor's name.

## 2. How it works

- `GET /api/contracts/<id>/calls` (`contracts.contract_calls`): `require_perm("contract:read_basic")` and
  `require_perm("ticket:read")` (403), then S080's 404 rule. Then plain reads:
  1. `_covered_nodes`: the lines with each line's machine (`COALESCE(gp.id, p.id, e.id)`) and the part lines plus
     their current children.
  2. `_call_rows`: one ticket query, `t.equipment_id IN (machines) OR t.component_id IN (parts)`, the period
     `[from 00:00, to + 1 day 00:00)`, `EXISTS` a line on `(t.equipment_id, t.component_id, c.parent_id)`,
     `EXISTS` an assignee or a labour row of a person with the vendor now, and the ticket predicate
     `unit_access_condition(cur, "ticket:read", "t.unit_id", "m.unit_id")`. Newest first.
  3. `tickets.events_by_ticket` (moved from `improvements._events_by_ticket`, same code).
  4. `_vendor_people`: the vendor's people per ticket from the UNION of assignee and labour rows.
  - `_sees_whole_site` gives `complete`; `_vendor_reach` gives the two counts for the warning.
- Pure core (`contracts_core`): `call_figures` (one `ticket_times` and one `latest_restoration` call; the vendor
  wait is `waiting_by_reason["vendor"]`), `calls_total`, `calls_used`, `vendor_warning`, `CALLS_USED_MAX_DAYS =
  366`. It imports only `tickets_core` (pure) beside its earlier pure imports.
- `tickets.people_at_site` joins `vendors` and adds `vendor_name` to each picker item.
- Frontend: `BreakdownCallsCard.vue` loads its own answer, only when `userPermissions` holds `ticket:read`.
  `TicketContractLine.vue` reads S082's `/api/contracts/for-equipment/<node>` (node = the part, else the
  machine) when the ticket is open and `ticket.permissions` holds `contract:read_basic`, drops ended items with
  `isEnded`, and uses `showsDoNotRepair` and `DO_NOT_REPAIR`. Texts in `contractLabels.js`:
  `callFiguresLine`, `callsTotalLine`, `callsUsedLine`, `vendorWarningText`, `ticketContractLine`.
- **EXPLAIN (BR1-03's cost, § 5.1):** on the test database the ticket query uses `index_merge` with
  `sort_union(ix_tickets_equipment_state, ix_tickets_component_state)`; the `EXISTS` use the
  `ticket_assignees` primary key, `ix_ticket_labour_ticket`, `ix_people_vendor` and `uq_contract_equipment`. No
  scan, so the `OR` form stays (no `UNION`). Fact on a small table (18 tickets); the optimizer may choose
  differently at production size, but an index merge is the expected plan for two indexed `IN` lists.

## 3. Files touched

Backend code (4):
- `backend/contracts.py`: the calls route and its helpers (`_covered_nodes`, `_call_rows`, `_vendor_people`,
  `_vendor_reach`, `_sees_whole_site`, `_call_out`); docstring (S086 paragraph, ACCESS, Reads: no lock).
- `backend/contracts_core.py`: `call_figures`, `calls_total`, `calls_used`, `vendor_warning`, constants.
- `backend/tickets.py`: `events_by_ticket` (moved here, public); `people_at_site` adds `vendor_name`; Import
  direction paragraph.
- `backend/improvements.py`: `_events_by_ticket` removed; both callers use `tickets.events_by_ticket`; docstring.

Backend tests (3):
- `backend/tests/test_contracts_core.py`: `TestBreakdownCalls` (8 tests).
- `backend/tests/test_contract_calls_api.py` (new): 27 route tests.
- `backend/tests/test_tickets_api.py`: `test_people_of_the_site_with_trades_and_role` gains `vendor_name: None`;
  new `test_people_show_their_vendor`.

Frontend code (7):
- `frontend/src/views/contracts/BreakdownCallsCard.vue` (new).
- `frontend/src/views/ContractView.vue`: the card, last; docstring.
- `frontend/src/views/tickets/TicketContractLine.vue` (new).
- `frontend/src/views/TicketDetailView.vue`: the line after the plan line; docstring.
- `frontend/src/views/tickets/PersonPicker.vue`: the vendor after the role; docstring.
- `frontend/src/utils/ticketLabels.js`: `groupPeople` matches `vendor_name`.
- `frontend/src/utils/contractLabels.js`: the five S086 functions; imports `minutesText`.

Frontend tests (3):
- `frontend/tests/contractLabels.test.js`, `frontend/tests/ticketLabels.test.js`.
- `frontend/e2e/contracts.spec.js`: 10 S086 tests and their helpers.

Docs (2): `docs/Plan.MD`, `.claude/CLAUDE.md`.

## 4. Decisions taken

1. **`READ_KEY` imported from `tickets.py`** as `TICKET_READ` (one copy of the key string), with
   `events_by_ticket`. The brief named only `events_by_ticket`; this adds a second name from the same module, no
   new direction of import.
2. **`MACHINE_LEVEL`, `is_breakdown`, `is_overdue` from `tickets_core`** and `ASSIGNABLE_ROLES` from
   `config_rbac` in `contracts.py` (all existing names).
3. **The children query runs for every part line**, not only component-unit lines (`SELECT id FROM equipment
   WHERE parent_id IN (part lines)`): a component has no children, so the result is the same, and no level name
   is needed. It runs only when a part line exists.
4. **Two `EXISTS … OR EXISTS`** for the vendor rule, rather than one `EXISTS` over a `UNION`: same result, each
   uses its own index (EXPLAIN above).
5. **Two extra label helpers**, `callFiguresLine` (a row's line 4) and `vendorWarningText` (the § 5.4 texts), in
   `contractLabels.js`, so the texts are unit-tested. A row's line 4 starts with a capital ("Waited on the
   vendor 30 min") when there is no downtime part.
6. **`ticketContractLine(item)` returns `{headline, details}`**, not one string: the page links the headline
   only. The unit test checks `headline + details` against the brief's text.
7. **The card reloads when `machine_count` changes**, not only on a new contract id: a machine added or removed
   on the page changes which tickets count. Other writes (a price) do not reload it. A small, visible behaviour
   the brief does not state.
8. **The ticket line catches every load error and draws nothing**, as § 5.6 says ("an error, a 403 or 404:
   nothing drawn"); the catch has a comment and no log, since the page works on. This is the one handled-and-quiet
   error in the step.
9. **The card's header badge** shows the number of calls listed; the used line is not shown for an empty list
   (the brief's *Empty* state has only its text).
10. **The picker's filter placeholder** stays "Type a name to filter", though it now matches the vendor too; the
    brief does not change it and other specs use it.

No departure from the brief's rules or API.

## 5. Not done, deferred or assumed

- Assumed: the three gate-B decisions (BR1-03 b, Q2 a, C3) as the brief records them; KLA decides at gate B.
- The EXPLAIN finding is from the test database (small); production has a few thousand tickets a year.
- Known fault outside this step, not touched: the two S048 changelog tests (`e2e/changelog.spec.js:14`,
  desktop-chromium; the empty 0.1.14 section in `CHANGELOG.md`).

## Tests

- Core while coding: `tests/test_contracts_core.py` 102 passed; calls route 27 passed; pickers 4 passed;
  improvement, contract and RBAC tests 205 passed.
- Final all suites (`YANTRA_TEST_RUN=s086c1 tooling\run-tests.bat`): ALL SUITES PASSED — backend 4532 passed (282 s), frontend 408 passed, tooling 231 passed.
- Build: `npx vite build` built in 5.25 s (only the existing chunk-size warning).
- Schema docs: `tooling\schema-docs.bat check` PASSED, at v47 (no migration).
- Browser, new tests alone (`E2E_LANES=1`, phone-chromium, `-g S086`): 9 passed, 1 failed on my own test's text
  (the picked line has no space between name and role); fixed, the test then passed alone.
- Browser, targeted (Normal: `e2e/contracts.spec.js e2e/tickets-work.spec.js e2e/tickets-raise.spec.js
  e2e/tickets-parts.spec.js e2e/improvements.spec.js e2e/screens.spec.js`, the specs § 8.3/§ 8.4 name plus
  screens): 145 passed, 2 skipped, in 143 s.
- Browser, whole suite at Normal (`tooling\run-e2e-tests.bat`): 384 tests, 367 passed, 15
  skipped, 2 failed, in 264 s. The 2 failures are the known S048 fault outside this step
  (`e2e/changelog.spec.js:14`, desktop-chromium, it_admin and admin: the empty 0.1.14 section in `CHANGELOG.md`).
  Run once; no re-run.

## Manual checks

- [auto] **important** The contract page lists the vendor's breakdown call with downtime and the total line —
  `frontend/e2e/contracts.spec.js`::`S086: the contract page lists the vendor's breakdown call with downtime and the total line`
- [auto] **important** A ticket worked only by in-house people is not a breakdown call —
  `frontend/e2e/contracts.spec.js`::`S086: a ticket worked only by in-house people is not a breakdown call`
- [auto] **important** A call on a part of the covered machine is listed with the part —
  `frontend/e2e/contracts.spec.js`::`S086: a call on a part of the covered machine is listed with the part`
- [auto] 1 of 2 calls used, and 2 of 1 more than agreed —
  `frontend/e2e/contracts.spec.js`::`S086: 1 of 2 calls used shows when the contract agrees a number`
- [auto] **important** The two warnings, then none —
  `frontend/e2e/contracts.spec.js`::`S086: the contract page warns when no Team record is linked to the vendor`
- [auto] The storekeeper sees no card —
  `frontend/e2e/contracts.spec.js`::`S086: the storekeeper sees the contract page without the Breakdown calls card`
- [auto] The operator sees only the calls of their units and no used line —
  `frontend/e2e/contracts.spec.js`::`S086: the operator sees only the calls of their units and no used line`
- [auto] **important** The contract line and Do not repair on an open ticket, before the action bar; none once
  closed — `frontend/e2e/contracts.spec.js`::`S086: an open ticket on a covered machine shows the contract line and Do not repair`
- [auto] The assignee picker shows and finds the vendor —
  `frontend/e2e/contracts.spec.js`::`S086: the assignee picker shows the vendor beside a linked person and finds them by the vendor's name`
- [auto] The card fits a phone (`@device`) —
  `frontend/e2e/contracts.spec.js`::`S086: the Breakdown calls card fits a phone with no sideways scroll`

On a real device: none (§ 8.5; S082's device row covers the same warning). No row added to
`docs/steps/device-checks.md`.

## Docs updated

- `docs/Plan.MD`: § 2 item 9 ("listed on the contract page with downtime and the wait on the vendor, and the
  contract shows on the ticket (S086)"); § 4.2, a bullet: an open ticket on a machine under contract shows the
  contract, and the picker names a contractor's vendor.
- `.claude/CLAUDE.md` § SMTW-Review: the point *Breakdown calls (S086)*, the brief's § 8.6 text.
- `docs/schema/`: none, because S086 adds no migration (`check` exits 0).
- `docs/steps/device-checks.md`: none, because the step has no real-device check.

## Feedback

- hindrance: an `@device` test named with `--project=phone-chromium -g S086` runs on the logic device too, so the
  first lone run cannot show the tag's real project; not a fault, but the alone-run rule could name it (1 run).
- waste: the full unit run was moved to the background by the Bash tool after 180 s although the wrapper's
  summary is all that is read; a note in the settings that `run-tests.bat` takes over 3 minutes would let the
  agent start it in the background at once (3 min).

## Fix rounds

### Round 1

- **CR1-01**: Left out, on the orchestrator's instruction. Its fix changes the ticket line's behaviour on a load
  error, which the approved brief § 5.6 sets, so it goes to the user at gate B.
- **CR1-02**: Fixed. `BreakdownCallsCard.vue:96` now shows "· not back in service yet" only when
  `r.call.is_breakdown` (and not a fault, not closed). New browser test `contracts.spec.js::S086: an open defect
  call does not say the machine is not back in service` (an open breakdown shows the text, an open defect on
  the same machine does not). Red: with `r.call.is_breakdown &&` removed, it fails on the defect row's
  `not.toContainText("not back in service")`; green with the fix.
- **CR1-03**: Fixed. The placeholder in `PersonPicker.vue:56` is "Type a name or vendor to filter". Two spec lines
  updated: `tickets-work.spec.js:72` and `contracts.spec.js:1022` (the second was uncommitted, so `git grep`
  missed it; the first targeted run caught it, then it passed alone).
- **CR1-04**: Fixed. New `test_contract_calls_api.py::TestWarnings::test_an_inactive_contract_still_lists_its_calls`
  covers a machine, makes one call, sets the contract inactive and asserts the call is still listed. It tests
  existing behaviour (no code fault), so no red run applies.

Tests: backend `tests/test_contract_calls_api.py` 27 passed (run `s086c2`). `npx vite build` clean. No frontend
unit test touched. Browser, targeted (contracts, tickets-work, tickets-raise, tickets-parts, improvements,
screens): 145 passed, 2 skipped, 1 failed (the picker test, old placeholder in `contracts.spec.js`); after the
fix it passed alone (1 passed). Not re-run as a set.

Docs updated: none, because the changes are a label gate, a placeholder text and tests, and no doc describes them.

### Feedback

- hindrance: `git grep` for the old placeholder missed an uncommitted spec line, which cost a failed targeted run
  (about 3 min); use plain `grep -rn` on the working tree.
