```
Step: S067 — Improvement record from tickets
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 30-10-2026
```

# S067 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** One `minor` finding and two nits. The API
matches brief § 6 field for field. D-1 does not change behaviour. The lock sequences agree with
the three LOCK ORDER notes.

## Test runs

- **Unit suites** (`YANTRA_TEST_RUN=s067cr1 tooling/run-tests.bat`): backend 3460 passed,
  frontend 285 passed, tooling 185 passed. All suites PASSED.
- **Browser:** I re-ran nothing. No finding of mine needs a browser run. The coder ran the whole
  suite at Normal once (263 passed, 13 skipped), as § 8.4 asks. No screen changed, no shared
  frontend file (`api.js`, `e2e/support/`, …) changed, and no spec reads the two new fields. No
  targeted spec was missed.

## Findings

### CR1-01 (minor) — the ticket detail lists improvements the reader cannot open

`backend/tickets.py:437-452` (`_improvement_fields`). The ticket detail's `improvements` shows
every link of the ticket to any holder of `improvement:read` at the ticket's **site**. Opening an
improvement uses a different check: `improvements._read_improvement` (`backend/improvements.py:139`)
looks at the improvement's own **unit** or its machine's current unit. Each check follows the
brief (§ 5.3 and § 5.7). Together they let a reader see a link that answers 404.

- **Failure scenario:** IM-2026-11-001 is started from a ticket of an MCC1 machine. An engineer
  then adds a ticket of an MCC2 machine at the same site (allowed, § 5.3 *Add*). An operator whose
  units are only MCC2 opens that MCC2 ticket. The `improvements` field shows IM-2026-11-001.
  S068 § 5 turns it into a link ("Analysed in IM-2026-11-001 · Analysing", S068 brief line 137).
  The operator taps it and gets "Not found". This is the plant's normal case of one fault seen on
  several machines (TPM yokoten).
- **Suggested fix (needs the orchestrator's decision, because it changes § 5.3's text):** pick
  one of these.
  - (a) Recommended: in `improvement_links`, or only on the ticket detail's path, join
    `equipment m ON m.id = i.equipment_id` and apply
    `unit_access_condition(cur, "improvement:read", "i.unit_id", "m.unit_id")`, so a reader is
    shown only the improvements that open. The start and add checks (`link_error`) must still
    read **all** links: one open improvement per ticket holds whoever can see it. So that query
    stays unfiltered, and the detail gets the filtered one.
  - (b) Keep the API as it is. S068 then shows a serial the reader cannot open as plain text,
    which needs a per-item flag from the API anyway.
  Either way, add a test: an operator of the second unit sees no link, or sees one that opens.

## Nits

- **CR1-02** (nit) `docs/steps/S067-improvement-record/3-impl-report.md:14-15`: the summary says
  that "two small departures" are listed (D-2, D-3). § 4 lists twelve, and D-1, D-4 and D-5 also
  depart from the brief's text. Say "twelve decisions; D-1, D-2, D-3, D-4 and D-5 depart from the
  brief's wording; none changes the API".
- **CR1-03** (nit) `backend/equipment.py:106-107`: "removing a ticket and an edit take (6b)
  alone". An edit that picks a new lead also takes a shared lock on that person's row (FK), as
  improvements.py's own note (line 35) says. Add "(an edit's new lead: a shared lock on the
  person)".

## Departures judged (impl report § 4)

- **D-1, shared predicate `equipment.unit_access_condition`:** accepted, and it does not change
  behaviour. The function body is the old `tickets._visible_condition` body, line for line. It
  makes the same `accessible_unit_ids(cur, key)` call with `READ_KEY = "ticket:read"`
  (`tickets.py:127`). It returns `"1 = 1", []` for every unit and None for no unit. It builds the
  same `(t.unit_id IN (…) OR m.unit_id IN (…))` string, and its parameters are the sorted ids
  twice, in the same order. `tickets._visible_condition` passes `"t.unit_id"` and `"m.unit_id"`,
  the columns the old text named. No other caller of `accessible_unit_ids` changed. The full
  backend suite is green, including every ticket visibility test. The helper sits in the
  `accessible_unit_ids` section of equipment.py, and the import direction stays as it was
  (tickets.py and improvements.py import equipment.py). It is the reuse CLAUDE-COMMON's DRY rule
  asks for.
- **D-2** (`removal_error` takes `{id, code}`): accepted. The rule needs the machine's id. The
  message and the result are as § 5.3 states.
- **D-3** (no `field` on the remove refusal): accepted. A `DELETE` has no body field. § 5.3 names
  no field for this refusal.
- **D-4** (`code_ref` and `improvement_links` public in tickets.py): accepted. One function feeds
  both the ticket detail and the start and add checks, so the two cannot drift. tickets.py still
  imports only `improvements_core`.
- **D-5** (a missing ticket on add answers after the improvement's 404/403/409): accepted, and
  better than the brief's order. The shared ticket lock is still taken right after (6b). A user
  who cannot see the improvement learns nothing about ticket ids.
- **D-6 to D-12:** accepted. D-11's hand-written `open_link = NULL` is the only way to build two
  links on one ticket before R05.4. D-12's `monkeypatch` of the key's holders is the only way to
  test the read-key gate today.

## Checked and found consistent

- **API against brief § 6:** every route, key, body, query and status. The list item keys are
  exact (`test_open_newest_first_with_the_loss` asserts the set). The detail carries every field,
  with `unit.site_id`, each ticket's `machine`, `removable`, `lead.active` and `lead.may_lead`,
  `is_open` and `permissions`. The orderings are `i.id DESC` for the list and the ticket detail,
  and `occurred_at DESC, id DESC` for the tickets. The routes use `<int:…>` ids, so `/leads`
  never reaches the detail route and `/abc` answers 404. The leads 400 text is exact. The
  defaults are `state` open and `per_page` 50, up to 200.
- **Lock sequences against the notes** (tickets.py, equipment.py, improvements.py):
  - *Start* takes (6) the `IM:` counter (an X lock), then (7) the ticket shared. Then come the
    plain reads, then the two inserts. `next_counter`'s `SELECT` is the first consistent read,
    made after the counter lock, so the second of two starts sees the first's link. The pool is
    autocommit, so `require_perm`'s membership read before `transaction()` opens no snapshot
    (`db_helpers.transaction`).
  - *Add* takes (6b) X, then (7) shared, then the plain reads. *Remove* and *Edit* take (6b) X,
    then the plain reads.
  - No path takes a ticket and then an improvement row. Ticket writes read `improvement_tickets`
    plain only.
  - The shared-lock exception is written into tickets.py's note. The person-row deadlock is
    accepted, as the brief states.
- **The UNIQUE (ticket_id, open_link) race:** I traced two adds, and a start against an add.
  Both writers hold only the ticket's shared lock. The second link insert waits on the first's
  index lock, then fails with 1062. `UNIQUE_KEY_ERRORS["uq_improvement_tickets_open"]` answers
  409 on `ticket_id` with "This ticket is already in an open improvement. Reload the page."
  Starts in two different months do not meet on the counter, and the key catches them too.
  `test_a_race_meets_the_unique_key` plays the second writer.
- **Permissions:** `improvement:read` goes to the operator and IT admin, so every role but the
  storekeeper holds it. `improvement:edit` goes to the engineer, so the manager holds it too.
  Both keys are in `SITE_SCOPED`, with comments. Every route has `@require_perm`. The order is
  404 by the predicate, then 403 by `require_perm_at` at the record's site; on a start, the
  order is `read_ticket` 404, then the 403 at the ticket's site. `test_role_matrix` and
  `test_improvement_keys` are updated. No actor comes from the client (`actor()`). SQL uses
  placeholders only; f-strings join only constants and placeholder lists.
- **The lead:** the lead check reuses `person_at_site` and `people_at_site` with
  `may_lead(role)` = the key, as D6 says. An unchanged `lead_id` is not checked again.
- **Edit:** only fields that differ are written. An empty change list writes nothing
  (`update_row` returns early).
- **The loss and downtime:** all events come from one query and go through
  `ticket_times(...)["downtime_minutes"]`, the ticket page's own function, with no N+1. A
  not-a-fault ticket counts as 0.
- **Migration v36:** the text matches § 4.1 word for word. It has `IF NOT EXISTS` and no
  precondition (two new tables). `test_migration_v36.py` covers a fresh database (columns, ENUM,
  keys, FKs, CHECK), a v35 database keeping every row, the NULL rule of the unique key (1062 on a
  second open link, several NULLs allowed), the CHECK (4025), and a re-run. `conftest._TABLES` is
  updated. No hard delete of people, units or equipment exists, so the new foreign keys block no
  path.
- **The database down:** the list answers 503 (`db_down` test). Every route goes through
  `get_db()`.
- **Pure core / thin shell:** every rule (states, start, link, removal, lead, loss, validation)
  is in `improvements_core.py`, with no DB, clock or Flask. The shell only locks, reads and
  stores.
- **Tests against § 8.2:** each bullet has a test, including the 404/403 order for Start, Add,
  Remove, Edit and Leads (BR1-03), the scrapped machine (BR1-06), the refused start leaving no gap
  in the numbers, `may_lead` turning false through the API (BR2-07), and the ticket row left
  untouched.
- **Docs pass:** `docs/schema.md` has both tables, the Mermaid entities and their five links,
  `serial_counters`' `IM-` serials, and "migration v36". `docs/schema.html` has both tables on the
  Overview and Tickets tabs and v36 on its meta line. `docs/Plan.MD` § 3 has the key rows and the
  paragraph, and § 4.2 has the start line. `Maintenance-Philosophy.md` § 12 has the *Improvement*
  row. `.claude/CLAUDE.md` is left to the orchestrator, as instructed; the proposed text is in
  the report. No secret, Keycloak or device-check change is due.
- **Scope:** the brief asks for nothing that is missing. Nothing was built beyond D-1 and D-4,
  and both are reported.
- **Manual checks:** the report has a `## Manual checks` section. It holds none, which is right:
  the brief has no *Automated* or *On a real device* check (§ 8.4, § 8.5).

## Manual browser checks for the user

None in this step: it has no screen. S068 holds the screens and the Tamil-text check.

## Feedback

- idea: the orchestrator's prompt asked me to prove D-1 neutral. A one-line hint in the impl
  report ("moved body, diff it against `_visible_condition` at the S066 snapshot") would have saved
  locating the old text in the diff (about 2 min).
- hindrance: the step diff mixes in S068's and S069's brief files and the R05 roadmap edits
  (`docs/steps/S068-…`, `S069-…`, `docs/roadmap/`), 1,600 lines that are not S067's change. I had
  to use `diff S067 -- <paths>` to leave them out (`step_snapshot.py diff S067 --stat`).
- none further.
