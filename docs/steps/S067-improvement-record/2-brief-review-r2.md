```
Step: S067 — Improvement record from tickets
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 30-10-2026
```

Reviewed against: 32eb122 + uncommitted S066

**Verdict:** no `blocker` or `major` is open. Two `minor` findings and five nits, all on § 6 as
S068's contract and on reuse; none needs KLA's decision and none is defining. The only point
still for KLA is the one the brief already marks: *Remove ticket* is a scope addition beyond
R05.1, for gate B (§ 9 Q2); it is not defining. Facts file read: `scratch/brief-facts-S067.md`.

**Re-read this round** (the diff `scratch/S067-brief-r1.md` → the brief): the header; § 1 and
*Out of scope*; § 3; § 4.1 notes and § 4.2; § 5.3; § 5.4 Remove and Edit; § 5.5; § 5.6; § 5.8;
§ 6; § 7 D1, D5, D9; § 8.2–8.6; § 9; the Review log. Not re-read: § 2, § 4.1 SQL, § 5.1, § 5.2,
§ 5.4 Start and Add, § 5.7, D2–D4, D6–D8, § 8.1.

**Round-1 answers in the text.** Every `Accepted` finding is in the brief, not only in the log:
BR1-01 (§ 1, § 3, § 8.4, § 9), BR1-02 (§ 5.3 Remove and `removable`, § 5.4 Remove, § 6, D5, D9,
§ 8.2), BR1-03 (§ 5.5 "always 404 before 403", the 404/403 pairs in § 8.2 for Start, Add and
Leads), BR1-06 (§ 5.3, D5, § 8.2), BR1-07 (§ 5.4 Edit, § 5.6), BR1-13 (§ 5.3, § 6), BR1-14
(§ 5.5, § 6). BR1-04, 05, 08–12 are in S068's brief where the log says (§ 5.3, § 5.5, § 5.2,
§ 5.3, § 8.1, § 5.4, § 5.6 there).

## Findings

### BR2-01 — minor — § 6 the detail: a linked ticket does not say which machine it is on

- **Problem.** D5 and § 5.3 let an improvement hold tickets of other machines of the site, and
  the removal rule (BR1-02) treats the improvement's machine's tickets differently (`removable`
  false on its last one). The detail's `tickets[]` carries no `machine`. S068's *Tickets (n)*
  row shows serial, badge, time, symptom, cause and downtime; the user cannot tell a ticket of
  another machine from one of this machine, nor why one row has no remove button while the
  others have one. The 409 "An improvement keeps a ticket of HP003." names a machine the rows
  never show.
- **Why it matters.** § 6 is S068's contract; without the field S068 cannot show it, and the
  change would come back as an amendment after S067 is coded. The columns are already selected:
  `_TICKET_COLUMNS` joins `equipment m` (`backend/tickets.py:139`) and `_ticket_out` emits
  `machine{id, code, name, class_code}` (`backend/tickets.py:210`).
- **Options.** (a) **Recommended:** add `machine{id, code, name}` to each entry of `tickets[]`
  in § 6, and one line in S068 § 5.4: the row shows the machine code when it differs from the
  improvement's machine (the orchestrator carries it into S068's brief). (b) Leave the field
  out and accept that S068's rows cannot explain `removable`. Not defining; the orchestrator can
  settle it in the Review log.

### BR2-02 — minor — § 5.6 / § 6 leads: the membership reads exist in `tickets.py`; the brief does not name the reuse

- **Problem.** § 5.6's rule ("an active person with a membership at the improvement's site whose
  role there grants `improvement:edit`") is `_person_at_site(cur, person_id, site_id)`
  (`backend/tickets.py:362`, returns `{id, name, role}` or None for no membership or inactive)
  plus `may_lead(role)`. The detail's `lead.may_lead` is the same call. The leads list is
  `_people_at_site`'s query (`backend/tickets.py:692`: `people JOIN memberships … WHERE site_id
  = %s AND p.active = 1 ORDER BY p.name, p.id`) filtered by `may_lead`. § 3 names only
  `read_ticket` and the event read as improvements.py's imports from tickets.py, so the coder
  would write a third copy of the membership query, or import a private name unasked.
- **Why it matters.** A parallel query for the same rule (CLAUDE-COMMON *DRY*); and the people
  picker and the lead check should agree on what "at the site" means (`memberships` has one row
  per person and site, `PRIMARY KEY (person_id, site_id)`, `backend/local_db.py:243`).
- **Options.** (a) **Recommended:** state the reuse in § 3 and § 5.6: the lead check and
  `lead.may_lead` call `_person_at_site`; the leads list runs the same membership query with
  `may_lead(row["role"])` as its filter and returns `{id, name}`; `_person_at_site` is made
  public (`person_at_site`) in `tickets.py`, as `read_ticket` is. (b) A query of improvements.py's
  own, stated as such. Not defining.

## Nits

- **BR2-03** (nit) § 5.3 `removable`: write it as `is_open and removal_error(ticket, links,
  machine_code) is None`, so the rule is one function in `improvements_core` and the detail and
  the DELETE cannot drift apart.
- **BR2-04** (nit) § 6 "`tickets` are newest first by `occurred_at`, then `id`": write
  `occurred_at DESC, id DESC`, so the tie-break direction is not the coder's guess.
- **BR2-05** (nit) § 6 routes: declare `<int:improvement_id>` and `<int:ticket_id>`, so
  `/api/improvements/leads` never meets `/<id>` and a non-numeric id is a 404, as `tickets_bp`
  does.
- **BR2-06** (nit) § 6 `unit{id, code, site_code}`: S068 § 5.3 needs the site **id** for
  `GET /api/tickets?site_id=` and maps `site_code` through `ensureSites` (S068 § 9 assumption).
  `s.id AS site_id` is already selected (`backend/tickets.py:152`); adding `site_id` to `unit`
  removes that assumption. The ticket detail has the same shape today, so either way is
  consistent; your call.
- **BR2-07** (nit) § 8.2 Detail, "`lead.may_lead` false after the lead's membership is
  removed": name the way: the people sites route that deletes the membership
  (`backend/masters.py:1407`) or a second `user_at_sites` spec (`backend/tests/conftest.py:530`),
  so the test writes no SQL.

## § 6 as S068's contract

Checked each screen of S068's brief against § 6; everything else it reads is there:

- the ticket page: `can_start_improvement`, `improvements[{id, serial, state}]` (BR1-13 order);
  the prefill from the ticket detail's `machine.code`, `failure_mode.label`, `description`
  (existing fields, `_ticket_out`);
- *Start* / *Edit*: `POST` body, the detail as the answer (`id` for the router), `PUT` with
  optional fields, `lead{id, name, active, may_lead}` for "(not a lead now)",
  `GET /api/improvements/leads?ticket_id=|improvement_id=` with `{items: [{id, name}]}`;
- the page: `serial`, `state`, `is_open`, `title`, `problem`, `machine`, `unit`, `created_at`,
  `created_by_name`, `lead.name`, `tickets[]` with `occurred_at`, `intensity`, `failure_mode`,
  `cause`, `downtime_minutes`, `removable`, `loss{…}`, `permissions`; gaps: BR2-01, BR2-06;
- *Add ticket*: `POST …/tickets {ticket_id}` with the field `ticket_id` on every refusal; the
  rows from the existing Tickets list, which has `state=all` (`tickets_core.STATE_FILTERS:47`),
  `equipment_id` on a machine → `t.equipment_id` (`tickets.py:506`), `site_id`, `q`, and
  `not_a_fault` on each item (`_ticket_out` serves list and detail);
- *Remove*: `DELETE …/tickets/<ticket_id>`, 200 with the detail;
- the list: `state`, `unit_id`, `page`, `per_page`; items with `serial`, `state`, `title`,
  `lead.name`, `loss{tickets, breakdowns, downtime_minutes}`, `id DESC`.

## Checked and found consistent

- **§ 5.4 Remove's new claim** "a ticket's `equipment_id` changes only through the ticket edit,
  which changes the component, never the machine": the edit checks `component_id` against
  `ticket["equipment_id"]` (`backend/tickets.py:1163–1165`, `_check_component`) and the move
  takes only a node of the same machine (`:1347`, `_locked_node_of_machine`); the raise stores
  `equipment_id = machine_id` (`:823`). The links read under (6b) is safe as written.
- **§ 5.3 scrapped machine (BR1-06):** `_check_no_open_tickets` counts `state <> closed`
  (`backend/equipment.py:484`), so a closed ticket's machine can be scrapped; a start's insert
  then takes only a shared FK lock on the scrapped row, no new edge.
- **§ 5.5 (BR1-03, BR1-14):** `_picker_anchor` (`backend/tickets.py:660`) reads `read_ticket`
  (404) before `require_perm_at` (403); the brief's leads route mirrors it. The decorator's
  403 for a role with no `improvement:edit` anywhere (operator, technician, supervisor, IT
  admin) comes first, as every ticket route does; § 8.2's expectations match.
- **§ 5.6 (BR1-07):** `compute_permissions` takes a list or a string and expands
  `ROLE_INCLUDES` (`backend/access_core.py:44`), so `may_lead("maint_manager")` is true through
  the engineer's grant; an unchanged `lead_id` on `PUT` is not re-checked (§ 5.4 Edit).
- **§ 3 role matrix:** the parametrize block spans `backend/tests/test_rbac.py:178–209`
  (`def` at 208); the six roles the brief names are the rows there; the storekeeper gains
  nothing.
- **§ 3 import direction:** improvements.py → tickets.py (`read_ticket`, `_event_rows`), and
  tickets.py → `improvements_core` only (for `can_start_improvement`); no cycle.
- **§ 8.4 / § 8.6:** a backend-only step that changes `GET /api/tickets/<id>` still runs the
  whole browser suite once (README § Manual checks: "whenever … an API the screens use
  changed"); no automated or device check is wrongly listed.
- **§ 9 and the track:** full stays right (a migration, keys, locks). Q2 is marked for KLA at
  gate B as a scope addition; the split follows the roadmap's rule.
- **Writing style:** the changed text is in scope A; the two new messages ("An improvement keeps
  a ticket of HP003.", "This improvement is closed") are one line, plain, no codes.

## Feedback

- idea: for a round-2 review the orchestrator's prompt listed the changed sections; the
  `git diff --no-index -w` of `scratch/S067-brief-r1.md` confirmed it in one read. Keep that
  copy as a standing step (`scratch/S0NN-brief-r<N-1>.md`) for every round; it is the fastest
  way to scope round N.
- waste: `git diff --no-index` printed two "LF will be replaced by CRLF" warnings and a 53 KB
  diff to a file I then read again (`tool-results/bqly4t8i1.txt`); `--stat` first, then the
  hunks of the sections named, would have halved it. My own doing; noting it for the
  agents' instructions.
