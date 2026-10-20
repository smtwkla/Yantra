```
Step: S017 — Raise and see tickets
Doc: impl-report
Author: Coder (Opus)
Date: 20-10-2026
```

# S017 — Implementation report

Built from `1-brief.md` as approved 20-10-2026 (baseline 6c771e1, stale check s1), with
user decisions 1–7. No amendments.

**Tests run** (dev DB up):
- `tooling/run-tests.bat`: backend **1623 passed**, frontend **80 passed** (12 files),
  deps tests **42 passed**; exit 0.
- `npx vite build` in `frontend/`: built with no errors or warnings.

## 1. What was built

- **Raise a ticket** (`/tickets/new`, phone first), from the equipment page's **Raise ticket**
  button (so from a QR label) or from the Tickets list, where the equipment is searched first.
  Intensity (three large buttons: Stopped / Running, reduced / Early signs), symptom (optional;
  the machine's class modes, then the General ones), description (needed with no symptom or
  with *Other*), when it happened (default now; sent only if changed), found by (people with a
  role at the site, operators without a login included). The machine's open tickets are listed
  above Save (a warning, not a block). After Save, photos are added on the same screen
  (camera or gallery), then **Done** opens the ticket.
- **Raised on any node**: the ticket stores the machine and, when raised lower, the
  component; serial `TK-YYYY-MM-NNN` from the IST raise date, one monthly counter, no gaps.
- **Tickets list** (`/tickets`, new nav item after Equipment, `ticket:read`): open tickets
  at the user's units by default; filters state, breakdown/defect, site, unit, text (serial or
  description), and one equipment (from the equipment page's *All its tickets* link). Open:
  critical first, then oldest event; closed / all: newest first. Each row: intensity badge,
  serial, age, machine (and component), symptom or start of description, unit, state.
- **Ticket page** (`/tickets/:id`): serial, intensity, state, machine and part (links),
  unit, symptom, when it happened (with age), found by, raised by, description, timeline
  (the *raised* event), photos (thumbnails, full size, add / retitle / remove while allowed).
- **Equipment page**: *Open tickets* card (with `ticket:read` at the node's site) and
  *Raise ticket* button (with `ticket:raise` there, not on scrapped equipment).
- **Ticket photos** are a third owner in `equipment_documents`: S006's checks, S008's
  restore / purge in Settings › Removed documents.
- **Failure-mode code frozen** once a ticket uses the mode (409 on the code; label,
  description, active still editable).
- **Scrap refused** while the node or a part below it has an open ticket: 409 "Close its
  tickets first".
- **Operators without a login**: IT admin may give a person without a login an Operator row
  (engineers still Technician only; an engineer asking for Operator now gets 403).
- **Permissions**: `ticket:read`, `ticket:raise` for the operator (so every maintenance role
  and the supervisor), and IT admin (decision 7); not the storekeeper. Both site-scoped.

## 2. How it works

**Pure core — `backend/tickets_core.py`.** Constants (intensities, states, open states, the
list's intensity groups, `FUTURE_SKEW` 5 min, `MAX_BACKDATE_DAYS` 7), the serial and its
counter scope, `parse_event_time` (local `YYYY-MM-DDTHH:MM[:SS]`, `T` or space; offsets and
`Z` refused), `event_time_error(…, not_before)` (the window; S018 reuses `not_before`),
`validate_raise(body, now)` (every field cleaned before the transaction; `occurred_at`
defaults to `now`), `description_error(description, mode_code)` (called in the transaction
once the mode is read) and `machine_and_component(node)` from the node's `level`,
`parent_id`, `gp_id`.

**Migration v12 — `local_db.py`.** `tickets` and `ticket_events` as § 4.1 (FKs, the three
indexes, ENUM orders), `equipment_documents.ticket_id` with FK and index, and the owner CHECK
dropped and re-added **under the same name** with the three-owner sum, so a v9 re-run stays
a no-op (BR2-01). Every statement is safe to re-run.

**Raise — `backend/tickets.py`, `POST /api/tickets`.** `validate_raise` runs first. In one
transaction: `load_node_for_user(…, for_update=True, key="ticket:raise")` locks the node (1)
and decides 404 (not at the user's units) and 403 (key not held at its site); scrapped is
decided from the locked row (409); for a part, the machine is read plain and its status
checked too. The mode (active, General or of the machine's class) and the description rule
come next, then the reporter (active, with a membership at the site). `next_counter` bumps
`TK:YYYY-MM` (6) in the same transaction, then the ticket and its `raised` event are
inserted, and the answer (the detail) is read inside the transaction.

**Access — one predicate** for list, detail and photos: `t.unit_id IN (units) OR m.unit_id IN
(units)` with the units where the user holds `ticket:read`; admin / IT admin see every
ticket; no units → empty list with no query; outside → 404. "The ticket's site" for write
checks is the site of `tickets.unit_id`.

**List — `GET /api/tickets`.** Filters `state` (open default / closed / all), `intensity`
(`breakdown`, `defect` or one of the three), `site_id`, `unit_id` (the ticket's unit),
`equipment_id` (a machine → `t.equipment_id`; a part → `t.component_id`; unknown → empty),
`q` (serial or description), paged. Order in SQL: open → `t.intensity, t.occurred_at, t.id`;
else `t.occurred_at DESC, t.id DESC`.

**Pickers.** `GET /api/tickets/modes?equipment_id=` and `GET /api/tickets/people?equipment_id=`
both check the node as the raise does (`ticket:raise` at its site, unit access). Modes: the
machine's class (also for a part), then General, active only, by label. People:
`_people_at_site(cur, site_id)`, site first for S018's `ticket_id=` anchor: active people with
a membership at the site, by name, with `role` and active `trades [{id, name}]`.

**Photos — `backend/documents.py`.** `Owner` now carries `read_key`, `write_key`,
`purge_key`, `kinds`. The route-level `@require_perm("equipment:…")` literals are gone: each
route calls `_owner_key(owner, which)`, which checks the owner's key held at any site
(`auth_utils.check_perm`, the same 403 and access-log entry as `require_perm`) and passes it
to the owner's read / lock function, which checks it at the record's site. Equipment and model
keep exactly their old keys. The ticket owner's functions live in `tickets.py`
(`read_ticket`, `read_ticket_for_change`, `lock_ticket_for_change`, `lock_ticket_for_purge`):
404 (predicate) → 403 (key at the ticket's site) → 409 "This ticket is closed" (not for
purge), the lock version locking the ticket row (7) and deciding from it. A kind outside the
owner's `kinds` is refused (400, `kind`) right after the form fields are read, before the
file. The removed list gains a ticket branch scoped by the ticket's own unit, with item
`{owner: "ticket", name: <serial>, unit, full_path: null, state}`. Files go to
`DATA_DIR/tickets/<id>/`.

**Scrap — `equipment.py`.** `_check_parts_scrapped` now returns the locked part ids;
`_check_no_open_tickets` counts tickets not closed on the node or those parts (as machine or
component) and refuses with 409.

**Mode code freeze — `masters.py`.** After the mode row is locked, a code change counts the
mode's tickets with a shared-lock read; one or more → 409 on `code`.

**No-login roles.** `config_rbac.NO_LOGIN_ROLES = (TECHNICIAN_ROLE, "maint_operator")`;
`masters_core.no_login_role_error` checks against it (new message "…a technician or an
operator"). The engineer's Technician-only rule (`technician_only`) is unchanged, so an
engineer's Operator row is now 403 instead of 400.

**Frontend.** New views `TicketsView`, `RaiseTicketView`, `TicketDetailView`; routes
`/tickets`, `/tickets/new`, `/tickets/:id`; nav item *Tickets*. `IntensityBadge`,
`utils/ticketLabels.js` (labels, `isBreakdown`, `ageText`, `problemText`,
`toLocalInputValue`), `utils/documentTypes.js` (the shared `ACCEPT`, the iPhone hint and
`withoutExtension`, moved out of `DocumentUploadModal`). `DocumentsCards` and
`DocumentUploadModal` gain `photosOnly` (no Documents card, no Kind choice). The equipment page
reads `permissions` (keys at the node's site) for the section and the button.
`RemovedDocuments` shows ticket rows and disables Restore on a closed ticket. `PeoplePanel`
offers Technician or Operator to IT admin for a person without a login, Technician only to an
engineer (`siteRoleChoices` in `utils/siteRoles.js`).

## 3. Files touched

Backend:
- `backend/tickets_core.py` (new) — the pure rules above.
- `backend/tickets.py` (new) — blueprint `/api/tickets`: list, detail, raise, modes, people;
  the access predicate; the ticket-owner read / lock functions for documents.py; the lock-order
  and accepted-deadlock notes.
- `backend/local_db.py` — migration v12.
- `backend/config_rbac.py` — `ticket:read`, `ticket:raise` (+ `SITE_SCOPED`), `NO_LOGIN_ROLES`,
  comments on `TECHNICIAN_ROLE`, `ROLE_INCLUDES` and the keys (decision 7).
- `backend/db_helpers.py` — `next_counter(cur, scope)`.
- `backend/equipment.py` — `_next_code` uses `next_counter`; scrap refuses open tickets;
  docstring lock notes (ticket row, the two accepted deadlocks, documents' third owner).
- `backend/documents.py` — `Owner` keys and kinds as data, third owner `ticket`, routes for
  `/api/tickets/<id>/documents…`, kind check, removed-list ticket branch, docstring.
- `backend/auth_utils.py` — `check_perm(key)` (the raising form of `require_perm`), shared
  `_log_denied` / `_forbidden_message`.
- `backend/file_store.py` — `tickets` folder.
- `backend/masters_core.py` — `no_login_role_error` on `NO_LOGIN_ROLES`, new message.
- `backend/masters.py` — mode code frozen once used; S016 section comment and docstring.
- `backend/app.py` — registers `tickets_bp`.

Backend tests:
- `backend/tests/test_tickets_core.py` (new), `test_tickets_api.py` (new),
  `test_migration_v12.py` (new).
- `backend/tests/conftest.py` — ticket tables in the clean-up; shared fixtures `make_mode`
  (moved from test_failure_codes_api.py), `make_ticket`, `set_ticket_state`, `TICKETS`.
- `test_documents_api.py` — ticket photos; node and model keys unchanged.
- `test_removed_documents_api.py` — ticket rows: listed, scoped, restored, purged, closed.
- `test_equipment_api.py` — scrap with open tickets.
- `test_failure_codes_api.py` — code freeze; `make_mode` now from conftest.
- `test_masters_core.py`, `test_site_roles_api.py` — the no-login rule (Operator accepted;
  engineer + Operator → 403; others 400 with the new message).
- `test_rbac.py` — role matrix rows, the ticket keys' holders and `SITE_SCOPED`, `NO_LOGIN_ROLES`.

Frontend:
- `frontend/src/views/TicketsView.vue`, `RaiseTicketView.vue`, `TicketDetailView.vue` (new).
- `frontend/src/components/IntensityBadge.vue` (new).
- `frontend/src/utils/ticketLabels.js` (new), `utils/documentTypes.js` (new).
- `frontend/src/router/index.js` — three routes. `stores/navigation.js` — *Tickets*.
- `frontend/src/views/EquipmentDetailView.vue` — Open tickets card, Raise ticket button.
- `frontend/src/components/documents/DocumentsCards.vue`, `DocumentUploadModal.vue` — `photosOnly`;
  the modal takes `ACCEPT`, the hint and `withoutExtension` from `utils/documentTypes.js`.
- `frontend/src/views/settings/RemovedDocuments.vue` — ticket rows; Restore disabled when closed.
- `frontend/src/views/masters/PeoplePanel.vue`, `utils/siteRoles.js` — role choices without a login.
- `frontend/tests/ticketLabels.test.js` (new); `navigation.test.js` (Tickets, storekeeper);
  `siteRoles.test.js` (role choices).

Docs: `docs/steps/S017-raise-tickets/1-brief.md` and `docs/steps/README.md` (status only); this
report.

## 4. Decisions taken

Small choices the brief did not settle; none changes the design. Departures from the brief's
wording are marked **(departure)**.

1. **`auth_utils.check_perm(key)`** is the "`_require_owner_key` raising the same 403" of
   § 3: documents.py's `_owner_key(owner, which)` calls it. It sits in auth_utils so the 403
   body, the log line and the access-log fields are the ones `require_perm` writes (shared
   `_log_denied`).
2. **Mode code freeze decided from the locked row** **(departure)**: § 3 said the plain
   pre-read gains `code`; I compare against the row `_lock_row` returns instead (two code edits
   at once can't both pass on a stale pre-read), and the ticket count is a `LOCK IN SHARE MODE`
   read, because the plain snapshot is taken by the pre-read, before a raise holding the
   mode's FK lock commits. Without it the "race-free" of § 5.7 would not hold.
3. **Scrap 409 carries `field: "status"`** **(departure)**, like its sibling "Scrap or move its parts first",
   so the status dialog shows it at the same place. The brief's shape had no field.
4. **Two description messages** **(departure)**: no symptom → the brief's "Description is needed when no
   symptom is picked"; symptom *Other* → "Describe the problem when the symptom is Other"
   (the first would read wrongly when a symptom was picked).
5. **Other user-visible messages**: mode refused "Choose a symptom from the list"; reporter
   refused "Choose a person from this site"; kind refused "Only photos can be added here";
   intensity missing "Choose how bad it is"; event time "That time is in the future" /
   "When did it happen? Up to 7 days back" / "Enter the time as YYYY-MM-DD HH:MM".
6. **The raise answers 201 with the detail shape** (events and `can_add_photos` too), so the
   photo step needs no second request for the ticket.
7. **People picker**: active trades only; `role` is the person's role at that site.
8. **Modes picker** items carry `class_id` and `description` besides id, code, label.
9. **List filters**: `unit_id` and `site_id` filter on the ticket's own unit and site (where
   it happened); an unknown `equipment_id` gives an empty list, not 404.
10. **Equipment filter in the UI**: the equipment page's Open tickets card links *All its
    tickets* (`/tickets?equipment_id=<id>&state=all`); the list shows an "Only <code>"
    button to clear it (fix round 1). The list has no equipment picker of its own.
11. **Tickets list rows are a list-group, not a table**, so they read on a phone; normal-size
    controls (no `btn-sm`) on the floor screens.
12. **Raise screen equipment picker**: `GET /api/equipment?level=all&q=…&per_page=20` (code or
    name, any level, scrapped left out by the list's default), tap to choose.
13. **Raise screen pre-checks** intensity and the description rule before sending (short
    messages); the server still decides.
14. **Photos after Save**: several at once (`multiple`), uploaded one at a time; the size
    limit read from the ticket's documents list and checked first, as S006's dialog does.
15. **`utils/documentTypes.js`** holds `ACCEPT`, the iPhone hint and `withoutExtension`,
    shared by the upload dialog and the raise screen (§ 3 asked for `ACCEPT` as a shared
    export; a `<script setup>` cannot export).
16. **Upload dialog with `photosOnly`** says "Everyone who can see this ticket can see it."
    instead of the equipment line.
17. **Removed documents**: the ticket row is plain text ("Ticket TK-…", unit, *closed*), like
    a model row (the item has no ticket id outside its `path`); the column header changed from
    *Equipment* to *Belongs to*, since it now holds models and tickets too.
18. **`siteRoleChoices(isItAdmin, hasLogin)`** in `utils/siteRoles.js` (with tests) decides
    the Team dialog's role list; `PeoplePanel` calls it.
19. **Equipment page**: *Raise ticket* is a red, normal-size button above the edit buttons;
    the Open tickets card sits above Details, loaded after the node only when `ticket:read` is
    in its `permissions`.
20. **Scrap check count is a plain read**: its snapshot is taken by `load_node_for_user`'s plain
    read, after the node lock is granted, so a raise committed before that is seen (comment in
    `_check_no_open_tickets`).
21. **Test fixtures**: `make_mode` moved to conftest (DRY with the ticket tests);
    `make_ticket` and `set_ticket_state` (S017 never closes a ticket, so tests write `closed`
    to the row) added there.

## 5. Not done, deferred, assumed

- Everything § 1 *Out of scope* lists (states after *raised*, labour, codes at close,
  assignment, re-grade, editing a ticket, alerts, scheduled work) — S018–S021.
- The two FK deadlocks of § 5.4 surface as a rare 500 (no 1213 → 409 mapping), as accepted.
- The shared unit-access helper (README › Queued, "S017 adds a fifth use") was not done:
  tickets.py has its own `_visible_condition`, which is an OR over two unit columns and so
  would not fit the four list routes' helper as is.
- No frontend component tests for the three new views (the project tests pure utils only);
  their behaviour is in the manual checks.
- `FormModal` left as it is (S023 fixes its scrolling).
- Assumed: phones send `datetime-local` without seconds; the server accepts both.
- Docs (Plan.MD, Maintenance-Philosophy, the S011 note, the README Queued row) were done by
  the planner at approval, as the brief says; not touched here.

## Manual checks

Important:
- [ ] On a phone: scan a QR label → equipment page → **Raise ticket** → pick critical, a
  symptom, take a photo (camera or gallery offered) → the ticket page shows it, with the
  thumbnail and the *raised* line in the timeline.
- [ ] As an operator of one unit, the Tickets list shows only that unit's tickets; a ticket
  URL of another unit gives "not found".
- [ ] As IT admin, give a person without a login an Operator row at a site; as a supervisor
  there, raise a ticket naming that person as *reported by*.

Plain:
- Raise a second ticket on the same machine: the open ticket is listed before Save.
- Raise with no symptom and no description → the description is asked for.
- Back-date by two days → the timeline shows that time, the serial this month.
- Try to scrap a machine with an open ticket → "Close its tickets first".
- Remove a ticket photo; Settings › Removed documents lists it under the ticket's serial.

## Fix rounds

### Fix round 1 (4-code-review-r1.md)

Frontend and one backend line; no behaviour of the API changed.

- **CR1-01 Fixed.** `RaiseTicketView.save()` sends `occurred_at` only when the field was
  touched and is not empty; a cleared picker means "now".
- **CR1-02 Fixed.** `DocumentsCards` has a new prop `largeAdd`: the one *Add photo* button
  becomes `btn-lg`, and its card header stacks (`d-grid`) so it is full width. The ticket page
  passes it; equipment and model pages do not (unchanged). One button, no copy.
- **CR1-03 Fixed.** The chip is now one normal-size button "Only <code> x" that clears the
  filter. The code comes from the first row's machine or part whose id equals the filter (no
  extra request); on an empty list it reads "Only this equipment".
- **CR1-04 Fixed.** `TicketDetailView` shows "You can't see this ticket." on a 403. Left
  alone: `TicketsView`'s `loadError` (the router guard keeps a user without `ticket:read` off
  that page) and app-wide error wording (S023).
- **CR1-05 Fixed.** Decisions 3 and 4 are marked **(departure)** in § 4.
- **CR1-06 Fixed.** `_equipment_filter` uses `tickets_core.MACHINE_LEVEL`.

Tests: no new automated test (the changes are in views and a constant; the project tests pure
utils only). The Manual checks list is unchanged; also worth a look: Add photo on the ticket
page, the chip, and clearing the time picker on a phone.
