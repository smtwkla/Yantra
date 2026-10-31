```
Step: S086 — Breakdown calls on the contract
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 31-10-2026
```

# S086 — code review, round 1

**Verdict: no `blocker` or `major` finding is open.** One `minor` finding and three nits. The calls route, its
access rules, the coverage and vendor rules, the period edges, the moved helper, the picker and the two screens
follow the brief. All unit suites are green, the build passes, and the schema-docs check exits 0.

## Tests run

- `YANTRA_TEST_RUN=s086cr1 tooling/run-tests.bat`: backend 4532 passed (292 s), frontend 408 passed, tooling 231
  passed; ALL SUITES PASSED.
- `YANTRA_TEST_RUN=s086cr1 tooling/schema-docs.bat check`: PASSED at migration v47 (4 passed), exit 0. S086 adds
  no migration.
- `npx vite build` in `frontend/`: built in 4.93 s; only the old chunk-size warning.
- Browser: none re-run. No finding of mine needs a run. The coder's runs are the right ones:
  - the new tests alone (`-g S086`, phone-chromium);
  - one targeted run with the specs of § 8.3 and § 8.4 plus `screens.spec.js`: 145 passed, 2 skipped;
  - the whole suite at Normal once: 367 passed, 15 skipped, 2 failed. The 2 failures are
    `e2e/changelog.spec.js:14` on desktop-chromium (the empty 0.1.14 section in `CHANGELOG.md`, S048). That fault
    is outside S086, and no S086 file touches the changelog.

## Findings

### CR1-01 (minor) — the ticket line hides "Do not repair" with no sign when its load fails

`frontend/src/views/tickets/TicketContractLine.vue:42`

- **Problem:** the `catch` takes every error the same way: a 403, a 404, a 503 and a dropped network call. Each one
  draws nothing and logs nothing. Brief § 5.6 asks for this ("an error, a 403 or 404: nothing drawn"), and impl
  report § 4 decision 8 states it. But this line carries S082's D9 warning, so its result is an instruction, not a
  hint. (`PartsPanel.vue` uses the same quiet catch, but only for part suggestions.) CLAUDE-COMMON *Error
  handling* says never swallow an exception silently.
- **Failure scenario:** a technician opens a breakdown ticket on a compressor under an AMC with *Only the vendor
  may repair* ticked. The phone's Wi-Fi drops for a moment, or the backend restarts during a deploy, just as
  `/api/contracts/for-equipment/<id>` is called. The ticket page has already loaded and looks complete. No
  contract line and no "Do not repair" show, and nothing says that a check failed. The technician taps *Start*
  and opens the machine, which the contract forbids.
- **Suggested fix:** keep the quiet catch for `err.status` 403 and 404 (the expected cases of § 5.6). For any
  other error, draw one small line in the same place, for example "The contract could not be checked. Reload
  the page before you start work." This departs from § 5.6's wording, so the orchestrator decides. Options:
  1. an amendment to § 5.6, then the fix;
  2. the answer "accepted as § 5.6 says", with a short note in the code comment that a 503 hides the D9
     warning.

## Nits

- **CR1-02** (nit) `frontend/src/views/contracts/BreakdownCallsCard.vue:96`: an open defect (machine never down)
  shows "· not back in service yet", which reads as if the machine is down. Show it only when
  `r.call.is_breakdown` (the answer already sends it), or ask KLA to keep the brief's "while open".
- **CR1-03** (nit) `frontend/src/views/tickets/PersonPicker.vue:56`: the filter now matches the vendor, but the
  placeholder still says "Type a name to filter" (impl report § 4 decision 10). "Type a name or vendor to
  filter" tells the engineer that "atlas" works. The specs that find the box by this placeholder then need the
  new text.
- **CR1-04** (nit) `backend/tests/test_contract_calls_api.py:407`: § 5.1 rule 5 says an inactive contract lists
  its calls the same way, and no test asserts it. Cover a machine and add one call in
  `test_no_warning_on_an_ended_or_inactive_contract`, then assert that the inactive contract still lists it.

## Checked and found consistent

- **The access rules (§ 5.5).**
  - `contract_calls` has `require_perm(READ_BASIC)` and `require_perm(TICKET_READ)`, so the storekeeper gets 403
    (tested).
  - Next comes S080's rule: a missing contract, or no `contract:read_basic` at its site, gives 404 (both tested).
  - Each row passes `unit_access_condition(cur, "ticket:read", "t.unit_id", "m.unit_id")`. This is the same
    call as `tickets._visible_condition`, so every serial link opens. `None` gives no ticket query.
  - `_vendor_people` reads only the visible ticket ids. The total sums the visible rows. No count of hidden
    tickets is sent.
  - `complete` holds only when `accessible_unit_ids(cur, "ticket:read")` is `None` or covers every active unit of
    the site. `used` is `None` otherwise (tested with a one-unit technician and the manager).
- **Contract fields by key.** The answer's keys are exactly § 6's. The only contract fields are `vendor_name` and
  `site_code`. The test sets a call-out number and a cost note and checks the key sets. The ticket line reads
  S082's `for-equipment` route, which builds its items through `_contract_out`. The line's text uses only the
  headline, `response_hours` and `covers_breakdown_calls`.
- **Coverage and moved parts (§ 5.1).** `_covered_nodes` gives each line's root as `COALESCE(gp.id, p.id, e.id)`,
  and the part lines with their current children. `_ON_A_LINE` matches `(t.equipment_id, t.component_id,
  c.parent_id)`. Seven route tests cover this: a line on a machine, on a component-unit (the machine and a sibling
  excluded), a covered part moved after its ticket, a part that left a covered machine, and the accepted
  residual of a component that left.
- **The vendor rule.** Two `EXISTS` over assignees and labour, on `people.vendor_id` now. Tested: an assignee, a
  labour row alone, in-house, another vendor, a relink, an inactive person, an unassignment. One row per ticket;
  each person once, by name.
- **The period in IST.** The bounds are `[from 00:00, to + 1 day 00:00)` on `occurred_at`, which is stored as IST.
  `test_the_period_edges` checks all four edges on a contract that ended yesterday.
- **The figures (§ 5.2).** `call_figures` makes one call to `ticket_times` and one to `latest_restoration`. The
  wait is `waiting_by_reason["vendor"]`. `now` is IST, as `tickets._now`. Core tests cover a defect, *Not a
  fault*, parts versus vendor, an open breakdown, the 366/367-day edge and the one-day contract.
- **`events_by_ticket` moved** to `tickets.py` with the same text. Both callers in `improvements.py` use it, and
  `marks` is still used there. The improvement tests are green.
- **`people_at_site`** adds `vendor_name` through a `LEFT JOIN vendors`. Both callers in `improvements.py` still
  map items to `{id, name}`. The changed test and the new test (including an inactive vendor) are in
  `test_tickets_api.py`.
- **Locks.** The route takes no lock and writes nothing. The LOCK ORDER notes are unchanged; one sentence in
  `contracts.py` adds the reads.
- **Imports.** `contracts.py` imports `READ_KEY` and `events_by_ticket` from `tickets.py`. Nothing that
  `tickets.py` imports (`alerts`, `equipment`, `improvements_core`, `tickets_core`) imports `contracts.py`. Only
  `app.py` and `documents.py` import it. `contracts_core` adds only `tickets_core`, which is pure.
- **Layers.** The rules and the sums are in `contracts_core` (pure). The route reads and assembles. The Vue files
  only format, through the tested helpers in `contractLabels.js`.
- **The screens.**
  - The card is last on `ContractView.vue`, after the *Documents* card, and draws only for holders of
    `ticket:read`. Its *Loading*, error, empty, partial and partial-empty states follow § 5.3. Long names wrap
    (`overflow-wrap: anywhere`). The `@device` fit test covers the phone.
  - The ticket line sits between the plan line and the action bar (DOM order tested). It shows only on an open
    ticket and only with `contract:read_basic` in `ticket.permissions`. It uses S082's `DO_NOT_REPAIR`,
    `showsDoNotRepair` and `isEnded`. S082's route already leaves out upcoming and inactive contracts.
  - The picker shows the vendor after the role, in the list and on the picked line. `groupPeople` matches
    `vendor_name`, and a `null` value matches nothing (unit-tested).
- **Scope B texts.** The two warnings, the empty, partial and error lines, and "By: …" are each one plain line
  that says what to do. No `btn-sm` and no dialog are added. The Assign dialog test calls `expectDialogFits`.
- **Browser tests.** Each S086 test asserts what the user sees: texts, counts, the danger class, the link it
  opens, DOM order. Only the fit test is tagged `@device`, which is right. The impl report's `## Manual checks`
  marks all five **important** checks of § 8.4 `[auto]`, each with its test. § 8.5 has no real-device check, so
  no row in `device-checks.md` is right.
- **Docs pass.** `docs/Plan.MD` § 2 item 9 and § 4.2, and the § SMTW-Review point *Breakdown calls (S086)*,
  match § 3 and § 8.6. No migration, so `docs/schema/` stays unchanged (check exit 0). There is no new secret,
  role or key.
- **Decisions taken (impl report § 4).** Decisions 1–7 and 9 are small and in scope. 7 (the reload on
  `machine_count`) is a visible behaviour, and it is reported. Decision 8 is CR1-01, and decision 10 is CR1-03.
  I found no departure that the report does not list.

## Manual browser check for the user

None from this review. The brief has no real-device check. S082's device row (the "Do not repair" warning in the
shop's light) also covers the ticket line.

## Feedback

- waste: `run-tests.bat` and `schema-docs.bat check` each take about 3 to 5 minutes, and they share the dev DB
  container. The schema-docs check could start in the background at the same time as the suites, but the
  settings give no hint that this is safe (about 3 min waiting).
