```
Step: S067 — Improvement record from tickets
Doc: impl-report
Author: Coder (Opus)
Date: 30-10-2026
```

# S067 — Implementation report

The backend of the improvement record is built as § 6 states it: migration v36, the serial
`IM-YYYY-MM-NNN`, the keys `improvement:read` / `improvement:edit`, seven routes under
`/api/improvements`, and two new fields on the ticket detail. All unit suites are green
(backend 3460, frontend 285, tooling 185). The whole browser suite at Normal is green (263 passed, 13 skipped).
There are no questions for the user. *Decisions taken* lists twelve decisions; D-1, D-2, D-3,
D-4 and D-5 depart from the brief's wording; none changes the API.

## 1. What was built

- **Migration v36** (`backend/local_db.py`): tables `improvements` and `improvement_tickets`,
  word for word from § 4.1. No `_PRECONDITIONS` entry.
- **The serial helper** (`backend/tickets_core.py`): `format_serial(prefix, year, month, number)`,
  `serial_scope(year, month, prefix="TK")`; `format_ticket_serial` calls `format_serial("TK", …)`.
  TK serials are unchanged.
- **The pure core** (`backend/improvements_core.py`): the keys, the states (only `analysing`),
  `IMPROVEMENT_OPEN_STATES`, `START_FROM_STATES`, every message of § 5, `validate_improvement`,
  `validate_link`, `is_open`, `start_error`, `link_error`, `removal_error`, `may_lead`, `loss`.
- **The shell** (`backend/improvements.py`, blueprint `improvements_bp` at `/api/improvements`):
  - `GET /` the list (open or closed, `unit_id`, paging, newest first, each with its loss);
  - `GET /<int:id>` the detail;
  - `GET /leads?ticket_id=|improvement_id=` the lead choices;
  - `POST /` start from a ticket;
  - `PUT /<int:id>` edit title, problem, lead;
  - `POST /<int:id>/tickets` add a ticket;
  - `DELETE /<int:id>/tickets/<int:ticket_id>` remove a ticket.
- **The keys** (`backend/config_rbac.py`): `improvement:read` (operator, IT admin; so every role
  but the storekeeper) and `improvement:edit` (engineer, so manager). Both in `SITE_SCOPED`.
- **The ticket detail** (`backend/tickets.py` `_detail`): `improvements` (`[{id, serial, state}]`,
  newest first by id) and `can_start_improvement`.

Nothing is visible to users until S068 builds the screens.

## 2. How it works

**Start** (`POST /api/improvements`). The body is validated first (§ 5.2). Then, in one
transaction:
1. the `IM:YYYY-MM` counter is bumped (lock (6));
2. the ticket row is read `LOCK IN SHARE MODE` (lock (7), shared); no row → 404;
3. the ticket is read through the tickets' predicate (404), and `improvement:edit` is checked at
   the ticket's site (403);
4. the start rule and the not-a-fault rule are decided from the locked row; the open-link rule
   from `tickets.improvement_links` (409, with both serials);
5. the lead is checked with `tickets.person_at_site` and `may_lead` (400);
6. the improvement row and its first link row are inserted; the detail is read inside the
   transaction and returned with 201.

A refused start rolls back, so the counter has no gap (tested).

**Add ticket.** Lock (6b), the improvement `FOR UPDATE`; then the ticket `LOCK IN SHARE MODE`;
then the plain reads in the brief's order: the improvement's predicate (404), the key at its site
(403), open (409), the ticket through the tickets' predicate (unknown or hidden: 400 "Choose a
ticket from the list"), the same site (400), not a fault (409), already here or in another open
improvement (409). The unique key `uq_improvement_tickets_open` catches a race; it maps to 409
"This ticket is already in an open improvement. Reload the page." (tested by blinding the plain
check).

**Remove ticket.** Lock (6b), then the predicate, the key, open, the link (404), and
`removal_error` over the links and their tickets' machine (409 "An improvement keeps a ticket of
HP003."). The link row is deleted; the ticket row is never written.

**Edit.** Lock (6b), predicate, key. Only fields that differ from the stored values are written;
an edit that changes nothing writes nothing (`updated_at` stays NULL). The lead is checked only
when it changes.

**The detail.** One query for the linked tickets (with machine, symptom and cause), one for all
their events; `ticket_times` gives each ticket's downtime, exactly as the ticket page computes it.
`removable` is `is_open and removal_error(...) is None`, the same function the `DELETE` route
calls. `lead.may_lead` is the lead rule today; `permissions` is `permissions_at_site` of the
improvement's site. The list uses the same two queries for the whole page (no N+1).

**The predicate.** An improvement is visible when its unit or its machine's current unit is among
the units where the user holds `improvement:read`. It shares one helper with the tickets'
predicate (D-1 below).

**The ticket detail.** When the user holds either improvement key at the ticket's site, one plain
read of `improvement_tickets` gives the links. `improvements` is shown only with
`improvement:read`; `can_start_improvement` needs `improvement:edit`, the start rule, not a
not-a-fault, and no open link.

## 3. Files touched

Code (8):
- `backend/local_db.py` — migration v36.
- `backend/tickets_core.py` — `format_serial`, `TICKET_SERIAL_PREFIX`, `serial_scope` with a prefix.
- `backend/improvements_core.py` (new) — the rules of § 5.
- `backend/improvements.py` (new) — the routes of § 6, the predicate, the LOCK ORDER note.
- `backend/app.py` — registers `improvements_bp` at `/api/improvements`.
- `backend/config_rbac.py` — the two keys with their comment; both in `SITE_SCOPED`.
- `backend/tickets.py` — `_person_at_site` / `_people_at_site` / `_code_ref` made public
  (`person_at_site`, `people_at_site`, `code_ref`); new `improvement_links`; `_detail` gains the
  two fields (`_improvement_fields`); `_visible_condition` calls the shared helper; the module
  docstring's LOCK ORDER note gains the shared-lock exception and the import direction.
- `backend/equipment.py` — new `unit_access_condition` (the shared predicate); the global LOCK
  ORDER list gains (6b) and (7), and an `improvements.py` bullet.

Tests (6):
- `backend/tests/test_migration_v36.py` (new) — 5 tests.
- `backend/tests/test_improvements_core.py` (new) — validation, states, start, links, removal,
  `may_lead` per site role, loss.
- `backend/tests/test_improvements_api.py` (new) — 73 tests: every route, the ticket detail's
  two fields, the 404/403 order for start, add, remove, edit and leads, the database down.
- `backend/tests/test_tickets_core.py` — `TestSerial` gains the prefix cases.
- `backend/tests/test_rbac.py` — `test_role_matrix` with the two keys; `test_improvement_keys`.
- `backend/tests/conftest.py` — `improvement_tickets`, `improvements` join `_TABLES`.

Docs (4): see § Docs updated. Step files: this report; the brief's `Status`.

## 4. Decisions taken

- **D-1. A shared predicate helper** (`equipment.unit_access_condition`). The improvements'
  predicate is the tickets' with other columns and another key. To avoid a near-copy, the
  tickets' body moved into `unit_access_condition(cur, key, unit_column, machine_unit_column)`
  beside `accessible_unit_ids`; `tickets._visible_condition` is now one call. The brief said
  `equipment.py` changes in its docstring only; this adds one function there. Behaviour of the
  tickets' predicate is unchanged (the full suite is green).
- **D-2. `removal_error(ticket, links, machine)`**, where `machine` is `{id, code}`. The brief
  writes `removal_error(ticket, links, machine_code)`; the rule needs the machine's id to tell
  which tickets are on it, so the function takes both. Same rule, same message.
- **D-3. The remove refusal has no `field`** (409 "An improvement keeps a ticket of HP003."): the
  `DELETE` has no body field to flag. Every other refusal names `ticket_id` or `lead_id` as § 5
  says; "This improvement is closed" also has no field.
- **D-4. More helpers made public in `tickets.py`** beyond the two the brief names:
  `code_ref` (the `{id, code, label}` of a symptom or cause) and a new `improvement_links(cur,
  ticket_id)` (the ticket's links, newest first). The ticket detail and the start / add checks
  read the links through this one function, so the two cannot drift.
- **D-5. Add ticket: the 400 for an unknown ticket comes after the improvement's 404/403/409.**
  The shared ticket lock is taken right after (6b), as § 5.4 says, but a missing ticket is
  reported at its place in the plain-read order. So a user who cannot see the improvement gets
  404, whatever ticket id he sends.
- **D-6. A hidden ticket on add**: `read_ticket`'s 404 is caught and answered as 400 "Choose a
  ticket from the list" (§ 5.3), rather than making the tickets' private `_find_ticket` public.
- **D-7. Validation details** (§ 5.2 leaves them open): a `PUT` with `title` or `problem` sent as
  `null` or empty is 400 "Enter a title" / "Describe the problem"; `ticket_id` in a `PUT` body is
  ignored; the add body `{ticket_id}` is validated by `validate_link` ("Choose a ticket").
- **D-8. The leads 400's field** is `ticket_id` ("ticket_id or improvement_id is required").
- **D-9. No mapping for `uq_improvements_serial`**: the counter makes a collision impossible; a
  collision would answer the generic 409. The brief maps only the open-link key.
- **D-10. `improvements.py` has its own `_now()`** (two lines, as `tickets.py`'s private one).
- **D-11. One test writes SQL**: `TestTicketDetail::test_two_improvements_newest_first` sets
  `open_link = NULL` on a link by hand, the row R05.4 will write on close. In S067 a ticket can
  be in only one improvement (a removed link is deleted), so two links on one ticket can only be
  built this way. It also proves that a closed link does not block a new start.
- **D-12. One test changes a key's holders**: `test_a_reader_without_the_read_key_sees_no_links`
  removes `improvement:read` from the operator with `monkeypatch`, because no role today holds
  `ticket:read` without `improvement:read`.

No departure changes the API of § 6.

## 5. Not done, deferred or assumed

- Every screen, browser test and the § SMTW-Review spec map: S068.
- No history of edits, link changes or removals (§ 2 departure, R05.4).
- The concurrency claims of § 5.4 are argued in the LOCK ORDER notes; the race on the unique key
  is tested by blinding the plain check, not with two real threads.
- `.claude/CLAUDE.md` is not edited (orchestrator's instruction); the text is under
  § Proposed CLAUDE.md changes.

## Tests

- **Targeted while coding:** `test_improvements_core.py`, `test_tickets_core.py`, `test_rbac.py`
  (381 passed); `test_migration_v36.py` + `test_migration_v35.py` (9 passed);
  `test_improvements_api.py` with the ticket, RBAC and auth tests (442 passed).
- **Full unit run, once at the end** (`YANTRA_TEST_RUN=s067c1 tooling/run-tests.bat`):
  backend 3460 passed, frontend 285 passed, tooling 185 passed. All suites PASSED.
- **Browser, whole suite at Normal, once at the end** (`tooling/run-e2e-tests.bat`, no flag):
  263 passed, 13 skipped (the existing skips), 0 failed; all six lanes exit 0, "All lanes done
  in 154 s". It ran on `phone-chromium` (every test) and `desktop-chromium` (the `@device`
  tests). It guards the ticket detail's two new fields; no spec reads them. The working tree
  also held S066's uncommitted ticket-page change, so its tests ran too and passed.
- No frontend change, so no `npx vite build`.

## Manual checks

None in this step (§ 8.4: no screen changes; § 8.5: no real-device check). S068 holds the
browser tests and the Tamil-text check.

## Docs updated

- `docs/schema.md` — header line now "migration v36"; table rows `improvements` and
  `improvement_tickets`; `serial_counters` names the `IM-` serials; the Mermaid overview gains
  both tables and their five links.
- `docs/schema.html` — edited by hand from the migration text (no generator): the Overview tab
  (keyed columns and five links), the Tickets tab (both tables with every column, five links, its
  note), and the meta line ("Migration v36 … v36 by hand 30-10-2026 · 41 tables, 62 links").
- `docs/Plan.MD` — § 3: key-table rows `improvement:read`, `improvement:edit` and a paragraph on
  them; § 4.2: one bullet, a ticket back in service or closed can start an improvement (S067).
- `docs/Maintenance-Philosophy.md` — § 12 Glossary: the row *Improvement*.
- `.claude/CLAUDE.md` — not edited (see below).
- `docs/steps/device-checks.md` — none, because the step has no real-device check.

## Proposed CLAUDE.md changes

In `.claude/CLAUDE.md` § Step workflow, entry **Self-check, repo items**, item (2), replace

> (2) The lock notes: the LOCK ORDER notes in `tickets.py` and `masters.py`;

with

> (2) The lock notes: the LOCK ORDER notes in `tickets.py`, `masters.py` and `improvements.py` (S067: (6b) the improvement row, between the counter and the ticket; improvements.py takes ticket rows only `LOCK IN SHARE MODE`);

## Fix rounds

### Round 1

Answers to `4-code-review-r1.md`. Amendment A1 (brief § 10) settles CR1-01.

- **CR1-01 (minor) — Fixed**, per A1. `tickets.py`: the ticket detail's `improvements` now
  comes from `_readable_improvement_links`, which joins the improvement's machine and applies
  `unit_access_condition(cur, "improvement:read", "i.unit_id", "m.unit_id")`, the same
  predicate as `improvements._read_improvement`. `improvement_links` stays unfiltered and still
  feeds `link_error` for `can_start_improvement` and for start and add in `improvements.py`.
  Both queries share one `SELECT … JOIN` text (`_IMPROVEMENT_LINKS`). The unfiltered read now
  runs only for a holder of `improvement:edit`, the only case where `can_start_improvement`
  uses it; the result is the same as before. New test
  `tests/test_improvements_api.py::TestTicketDetail::test_only_the_improvements_the_reader_can_open`:
  an improvement on unit A's machine, joined by a ticket of unit B's machine; an operator of B
  alone gets 404 on the improvement and an empty `improvements` on B's ticket; an operator of A
  and B gets the link. Fails without the fix: `assert [{'id': 1, 'serial': 'IM-2026-10-001',
  'state': 'analysing'}] == []` (the test was written first and run red on the old code);
  passes with it.
- **CR1-02 (nit) — Fixed.** The report's summary now says twelve decisions, of which D-1, D-2,
  D-3, D-4 and D-5 depart from the brief's wording, and none changes the API.
- **CR1-03 (nit) — Fixed.** `equipment.py` LOCK ORDER note: "removing a ticket and an edit take
  (6b) alone (an edit's new lead: a shared lock on the person, its foreign key)". Comment only;
  no test.

**Runs:**

- Targeted: the new test alone, before the fix (1 failed, the assertion above) and after it
  (1 passed); `tests/test_improvements_api.py` (73 passed).
- All unit suites once (`YANTRA_TEST_RUN=s067f1 tooling/run-tests.bat`): backend 3461 passed,
  frontend 285 passed, tooling 185 passed. All suites PASSED.
- No browser run: no screen and no shared frontend file changed (the orchestrator's
  instruction).

**Docs updated (round 1):**

- `docs/Plan.MD` § 3, the `improvement:read` paragraph: one sentence, a ticket page lists only
  the improvements its reader can open (S067 A1).
- `docs/schema.md`, `docs/schema.html`: none, because no migration changed.
- `.claude/CLAUDE.md`: no further change proposed; the round-0 proposal stands.

#### Feedback (round 1)

- none

## Feedback

- rule: the brief named the public helpers to reuse, but the shell also needed `code_ref` and a
  shared predicate; the "never paste a near-copy" rule then forced changes to `equipment.py` and
  `tickets.py` the brief called docstring-only (D-1, D-4). A brief's *Where* could list "helpers
  the shell will reuse" as a check, not only the ones already found (brief § 3).
- hindrance: `set_ticket_state(ticket, "scheduled")` fails on `chk_tickets_plan` (1 run lost,
  test_improvements_api.py); the fixture's docstring could say that scheduled needs the move.
- hindrance: `docs/schema.html` keeps all diagrams in one JSON line, so a hand edit needs a
  script (scratchpad `schema_v36.py`, about 5 min); a small `tooling` helper to add a table to a
  tab would save this on every migration step.
