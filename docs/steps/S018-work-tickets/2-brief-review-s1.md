```
Step: S018 — Work the ticket
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 20-10-2026
```

Reviewed against: cfedc46

# S018 — Staleness review s1

**Verdict: no `blocker` or `major` finding is open.** The brief was written
against S017's *brief*; S017's *code* is now committed (cfedc46) and the
working tree holds only doc changes. The design and every user decision hold
against the code as built. Three `minor` findings name places where the
brief's wording, a file list or a test list no longer matches the code; the
rest are nits. The planner can fix these in the brief text and the coder can
start (README § Stale brief check).

What was compared: `git diff 6c771e1 -- backend frontend/src` (37 files), the
new files `tickets.py`, `tickets_core.py`, the three ticket views,
`ticketLabels.js`, `DocumentsCards.vue`, `DocumentUploadModal.vue`,
`FormModal.vue`, `stores/auth.js`, and S017's impl report § 4 *Decisions
taken* (its departures from its brief).

## Findings

### BS1-01 — `minor` — an S017 test breaks when the ticket owner's `kinds` gains `document`

**What changed.** S017 built the kind rule as data: `Owner.kinds`, the ticket
owner `("photo",)`, and `_read_upload(limit_mb, kinds)` refusing anything else
with `400 {field: "kind", error: "Only photos can be added here"}`. S017's
`test_documents_api.py` asserts exactly that:
`test_a_document_kind_is_400_before_the_file_is_read` (a PDF on a ticket →
400 and no file written).

**What in the brief is now wrong.** § 3 *Tests* lists `test_tickets_core.py`,
`test_ticket_work_api.py`, `test_migration_v13.py`, `test_rbac.py`,
`test_failure_codes_api.py`, `conftest.py` and `ticketLabels.test.js` — not
`test_documents_api.py`. User decision 5 makes that test fail. § 3
`documents.py` also says "nothing else changes", but three comments say
photos-only: the `OWNERS["ticket"]` comment ("Photos only (S017 § 9.3)"),
the module docstring ("photos on a ticket … added … by ticket:raise") and
`file_store.py`'s ("for ticket photos"); and the generic refusal text "Only
photos can be added here" is only right while every restricted owner is
photos-only.

**Fix (recommended).** In § 3 *Tests* add `backend/tests/test_documents_api.py`:
the kind test becomes "a `document` on a ticket is accepted (201) by a
`ticket:raise` holder, stored under `tickets/<id>/`, listed, and shown in
Settings › Removed documents after a remove"; keep the 400 path only if some
owner still restricts kinds (none will — the message can go, or stay for a
future owner). In § 3 `documents.py` replace "nothing else changes" with "the
three photos-only comments are updated". Alternative: keep `("photo",)` and
drop user decision 5 — not recommended; the user decided it.

### BS1-02 — `minor` — one `canEdit` on `DocumentsCards` cannot give photos to `ticket:raise` and documents to `ticket:work`

**What changed.** `DocumentsCards.vue` as built has a single `canEdit` prop
that governs *Add photo*, *Add document*, edit-title and remove on both
cards, plus `photosOnly` (hides the Documents card altogether) and `largeAdd`.
The ticket page passes `:can-edit="ticket.can_add_photos" photos-only
large-add`. `DocumentUploadModal` with `photosOnly` hides the Kind radio and
forces `photo`; without it, `open(kind)` presets the radio.

**What in the brief is now wrong.** § 3 *Frontend* says the ticket page shows
"photos and documents (*Add document* for `ticket:work` holders, user
decision 5)" while photos stay with `can_add_photos` (`ticket:raise`, not
closed) — two permissions on one component that has one. No change to
`DocumentsCards.vue` or `DocumentUploadModal.vue` is listed in *Where*, so the
coder would design it alone.

**Fix (recommended, a).** Add to § 3 *Frontend*:
`components/documents/DocumentsCards.vue` gains `canEditDocuments` (default:
`canEdit`), used by the Documents card's *Add document*, edit and remove; the
ticket page drops `photos-only`, keeps `large-add`, passes
`:can-edit="ticket.can_add_photos"` and
`:can-edit-documents="ticket.can_add_photos && permissions.includes('ticket:work')"`.
`DocumentUploadModal` needs no change (the kind is preset by `open(kind)`;
the "Everyone who can see this ticket can see it." line should show for a
ticket whatever the kind — today it is tied to `photosOnly`, so key it on a
`ticket` prop or on `everySite`-style owner text). Alternative (b): show *Add
document* to every `ticket:raise` holder with the one `canEdit` — simpler,
but it contradicts user decision 5's "shown to `ticket:work` holders"; only
with the user's say.

### BS1-03 — `minor` — the code-freeze pattern S018 cites is not the one S017 built

**What changed.** S017's brief § 5.7 (which S018 § 5.6 cites: "As S017 § 5.7
for modes") said the plain pre-read gains `code` and the count is plain. The
code departed (S017 impl report decision 2): `update_failure_mode` compares
`clean["code"]` with the **locked** row `_lock_row` returns, and counts
`tickets` with `LOCK IN SHARE MODE`, because the plain snapshot predates a
raise that held the mode's FK lock and committed — without it "frozen once
used" is not race-free. `_update_plain_master` today calls `_lock_row` and
discards the row it returns.

**What in the brief is now wrong.** § 5.6 and § 3 `masters.py` describe the
`used_by` parameter and "the count goes in before `update_row`", with the
S017 *brief* as the pattern. A coder following the brief literally writes a
plain count against a stale snapshot. The same race exists here: a close that
sets `cause_id` / `action_id` takes a shared FK lock on the cause / action
row, exactly as a raise does on the mode.

**Fix (recommended).** In § 5.6 say: keep the row `_lock_row` returns in
`_update_plain_master`, compare `clean["code"]` with the locked row's, and
count `tickets WHERE <used_by column> = %s LOCK IN SHARE MODE`, as
`update_failure_mode` does; reuse its message "This code is used by tickets
and can no longer change" and 409 on `code`. The S017 brief § 5.7 is the stale
text; cite the code (`update_failure_mode`) instead.

### BS1-04 — `nit` — the people picker already returns each person's role; the route key for `?ticket_id=`

`_people_at_site(cur, site_id)` exists with `{id, name, role, trades:
[{id, name}]}`, site-first, so § 3's "the rows carry each person's role" and
BR1-10's "gains each person's role at the site" are already done — the only
S018 change is the `ticket_id` anchor. Two details to state: `list_people` is
`@require_perm("ticket:raise")` at the route and `_required_node_arg()` 400s
without `equipment_id`; the brief says the ticket anchor checks `ticket:read`
at the ticket's site. The two keys have identical holders, so either route
key is right — say which (simplest: keep `ticket:raise` at the route, then
`read_ticket` (404) and `require_perm_at("ticket:read", site)` inside), and
that one of `equipment_id` / `ticket_id` is required (400 otherwise).

### BS1-05 — `nit` — reuse `_lock_ticket` for the moves

`tickets.py` already has `_lock_ticket(cur, ticket_id, key)`: `SELECT id,
state … FOR UPDATE`, 404 by the access predicate, 403 by `require_perm_at(key,
site_id)` at the site of `tickets.unit_id` — § 5.3's sequence exactly. The
brief names no helper, so a coder might write a parallel one. Say that the
moves, edit, re-grade, labour and assignment routes extend `_lock_ticket`'s
locked SELECT (`intensity`, `failure_mode_id`, `equipment_id`, `occurred_at`)
and decide from that row; `TICKET_CLOSED` ("This ticket is closed") is the
existing 409 for writes on a closed ticket, beside the brief's "This ticket
changed — reload" for a stale state.

### BS1-06 — `nit` — test fixtures and helpers that now exist

- `conftest.py` already has `TICKETS`, `make_mode`, `make_ticket(node,
  client=, **overrides)` and `set_ticket_state(ticket, state)` (docstring
  "S017 never changes a state"); `test_tickets_api.py` has module-level
  `_now_ist`, `_local`, `_api_time`, `_refusal`, `give_site_role`, `operator`
  and `machine`. `test_ticket_work_api.py` should import or move these (to
  `conftest.py`), not copy them; `set_ticket_state`'s docstring is updated
  (S018's tests close through the API).
- `test_rbac.py` has a parametrized `test_ticket_keys` over `ticket:read`,
  `ticket:raise` asserting holders = every role but the storekeeper, and
  `in SITE_SCOPED`; `ticket:restore` fits that parametrize, the other three
  keys need their own holders test. § 8 *RBAC* can say so instead of "on the
  `test_failure_codes_edit_holders` pattern".

### BS1-07 — `nit` — the raise screen's query and the repeat pre-fill

`RaiseTicketView` reads the node from `?equipment=<id>` (not `equipment_id`)
and `resetForm()` runs whenever that query changes. § 3 says
"`repeat_of=<id>` in the query pre-fills and sends `repeat_of_id`"; state
where the pre-fill comes from: `GET /api/tickets/<id>` (machine or component
as the node, `failure_mode.id`, `intensity`), applied after the node loads,
and the link is `/tickets/new?equipment=<component or machine
id>&repeat_of=<id>`. `validate_raise` gains `repeat_of_id` through
`_optional_id` (as `reported_by_id`).

### BS1-08 — `nit` — the symptom picker is anchored on the node's current site

`GET /api/tickets/modes?equipment_id=` (which § 3 names for the close and
edit dialogs) checks `ticket:raise` at the node's **current** site through
`load_node_for_user`, so on a ticket whose machine moved to a unit the
engineer cannot see, the symptom list 404s while the close itself is allowed
(keys at the ticket's site). The same reasoning as BR2-02 for people. Not
from this diff (S017's brief defined it so); accept, or give `modes` the
same `?ticket_id=` anchor (the machine's class through the ticket) — a small
addition to the same route.

## Checked and found consistent

- Migration v12: `tickets` (`state` ENUM holds the full S018 set, `intensity`
  order critical-first, `updated_*` present) and `ticket_events` (`event`
  VARCHAR(30), `from_state`, `to_state`, `occurred_at`, `intensity`,
  `person_id`, `remark`, no `updated_*`) — § 4.3's event names and columns
  hold; `closed_not_a_fault` fits. v13's new columns and tables conflict with
  nothing; `failure_causes`, `maintenance_actions`, `trades`, `people` exist.
- `tickets_core`: `event_time_error(event_time, now, not_before=None)`,
  `FUTURE_SKEW` (5 min), `MAX_BACKDATE_DAYS` (7), `validate_raise`,
  `description_error`, `OTHER_MODE_CODE`, `STATES` — § 3's wrapper
  `validate_event_time` and § 5.1 hold.
- `auth_utils`: private `_person_id(cur)` cached as `g._access_person_id`
  (active person whose login is the token's) — the `current_person_id(cur)`
  of § 3 is a rename-and-expose; `permissions_at_site`, `has_perm_at`,
  `require_perm_at`, and S017's new `check_perm(key)` exist.
- `app.py` `/api/auth/me` with its `DBUnavailable` branch (token permissions
  only) — `person_id: null` there (BR4-08) holds; `tickets_bp` at
  `/api/tickets`, `documents_bp` at `/api` with `/tickets/<id>/documents` —
  the new `/moves/<move>`, `/regrade`, `/assignees`, `/labour` and `PUT
  /api/tickets/<id>` clash with nothing.
- `config_rbac`: `ticket:read`, `ticket:raise` to `maint_operator` and
  `it_admin`, both in `SITE_SCOPED`; `NO_LOGIN_ROLES` (technician, operator);
  `ROLE_INCLUDES` supervisor ⊇ operator — § 5.7's table and
  `test_supervisor_is_off_the_maintenance_ladder` hold with `ticket:restore`
  on the operator only. `test_role_matrix` rows are exact sets with the S017
  keys — § 8's "stacking on S017" is right.
- The detail (`_detail`): `events` carry `intensity`, `person`, `remark`,
  `from_state`, `to_state`, ordered `occurred_at, id`; `can_add_photos` =
  not closed and `ticket:raise` at `row["site_id"]` (the ticket's unit's
  site) — "the ticket's site = site of `tickets.unit_id`" holds everywhere
  (`read_ticket_for_change`, `_lock_ticket`).
- `documents.py`: `Owner(read_key, write_key, purge_key, kinds)`; ticket
  owner `ticket:read` / `ticket:raise` / `equipment:purge_documents`; files
  under `DATA_DIR/tickets/<id>/` (`file_store._OWNER_FOLDERS`); the removed
  list's ticket branch scoped by the ticket's unit and carrying `state` —
  user decision 5's "only `kinds` gains `document`, write key stays
  `ticket:raise`" is one tuple change (plus BS1-01).
- `masters.py`: `update_failure_cause` and `update_maintenance_action` both
  go through `_update_plain_master(table, record_id, validator)` — the
  `used_by` parameter of § 3 fits (subject to BS1-03).
- `equipment.py`: the detail's `children` are two levels (`_children`), each
  row with `status`, `level`, `code`, `name` — `EditTicketDialog`'s component
  list (non-scrapped ones offered) holds; `_check_no_open_tickets` counts
  `state <> 'closed'`, so a not-a-fault close frees the machine for scrap as
  § header says. Both lock-order docstrings (`equipment.py`, `tickets.py`)
  exist for § 3's additions.
- `conftest._TABLES` order: `ticket_events`, `equipment_documents`,
  `tickets` — "`ticket_labour` and `ticket_assignees` before `tickets`" holds.
- Frontend: views are flat (`views/TicketsView.vue`, `RaiseTicketView.vue`,
  `TicketDetailView.vue`) with dialog subfolders per area
  (`views/equipment/*Modal.vue`), so the new `views/tickets/` folder follows
  the pattern; `FormModal` has `saveLabel`, `saveDisabledReason`, `dirty`,
  `footer-left`, and a plain `modal-dialog` div for the one
  `modal-dialog-scrollable` class; `stores/auth.js` `loadProfile` sets
  `userPermissions` from `/api/auth/me` — `userPersonId` sits beside it;
  `ticketLabels.js` has `STATE_LABELS`, `INTENSITY_LABELS`, `EVENT_LABELS`
  ("S018 adds its own"), `toLocalInputValue`, `isBreakdown`;
  `ticketLabels.test.js` exists; `siteRoles.roleLabel` is there for
  `PersonPicker`; the masters store exports `ensureFailureCauses`,
  `ensureMaintenanceActions`, `ensureTrades`.
- The raise screen sends `occurred_at` only when the picker was touched
  (`timeTouched`) and not empty — § 5.1's "S017's raise screen follows the
  same rule" holds.
- The planner's uncommitted `docs/Plan.MD` § 3 already shows the four S018
  keys replacing `breakdown:work` / `breakdown:close`; the README Queued row
  for the event-time correction is in.
