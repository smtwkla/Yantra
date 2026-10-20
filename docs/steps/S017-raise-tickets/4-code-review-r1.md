```
Step: S017 — Raise and see tickets
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 20-10-2026
```

# S017 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** 0 blocker, 0 major, 2 minor, 4 nit.

## Test run

- `tooling/run-tests.bat`: exit 0.
  - backend (pytest): **1623 passed** (160 s);
  - frontend (vitest): **80 passed** (12 files);
  - dependency-audit tests: **42 passed**.
- `npx vite build` in `frontend/`: built in 3.6 s, no errors and no warnings.

This matches the counts in the impl report.

## Scope reviewed

The working tree against HEAD 6c771e1 (`git diff -w --ignore-cr-at-eol` plus the untracked
files), read in full where the hunks were not enough:

- backend: `tickets.py`, `tickets_core.py` (new); `documents.py`, `auth_utils.py`,
  `config_rbac.py`, `db_helpers.py`, `equipment.py`, `file_store.py`, `local_db.py` (v12),
  `masters.py`, `masters_core.py`, `app.py`;
- backend tests: `test_tickets_api.py`, `test_tickets_core.py`, `test_migration_v12.py` (new);
  `conftest.py`, `test_documents_api.py`, `test_removed_documents_api.py`,
  `test_equipment_api.py`, `test_failure_codes_api.py`, `test_masters_core.py`,
  `test_site_roles_api.py`, `test_rbac.py`;
- frontend: `RaiseTicketView.vue`, `TicketsView.vue`, `TicketDetailView.vue`,
  `IntensityBadge.vue`, `utils/ticketLabels.js`, `utils/documentTypes.js` (new);
  `EquipmentDetailView.vue`, `DocumentsCards.vue`, `DocumentUploadModal.vue`,
  `RemovedDocuments.vue`, `PeoplePanel.vue`, `utils/siteRoles.js`, `router/index.js`,
  `stores/navigation.js`, and the three test files.

I also read the helpers these call: `load_node_for_user`, `_read_node`, `_ancestors`,
`_check_parts_scrapped`, `update_equipment`, `accessible_unit_ids` / `user_unit_ids` /
`every_unit_by_token`, `require_perm_at`, `transaction`, `row_to_dict`, `formatDateTime`.
As instructed, the S015, S016, S017 and S018 docs folders and the README were not reviewed
as code, and `FormModal` scrolling (S023) is not raised.

## Findings

### CR1-01 — minor — `frontend/src/views/RaiseTicketView.vue:168` (with `backend/tickets_core.py:144-153`)

**Problem.** Once the user has touched the *When did it happen?* field, `occurred_at` is sent
even when the field is empty. A cleared `datetime-local` gives `""`. The server parses it and
answers "Enter the time as YYYY-MM-DD HH:MM".

**Scenario.** On a phone the user opens the date picker and taps *Clear* (iOS Safari and
Chrome on Android both offer it), or on a desktop deletes part of the value. They then tap
*Save ticket*. The field turns red with a format string they cannot type, because the field
is a picker. The checklist asks for one plain line saying what to do.

**Fix.** Choose one:
- in `save()`, send `occurred_at` only when it was touched **and** is not empty (an empty
  field then means "now", like an untouched one);
- or check it before sending, with the message "Pick when it happened".

### CR1-02 — minor — `frontend/src/components/documents/DocumentsCards.vue:312`

**Problem.** The ticket page is a floor screen: an operator opens it from the list or after a
raise to add a photo later. Its *Add photo* button, and the photo viewer's actions, are
`btn-sm`, because they come from the shared office component. The raise screen does it right
(`btn-lg w-100`). The ticket page shrinks the same action.

**Scenario.** A technician with gloves, or a phone in one hand, misses the small *Add photo*
button in the card header and taps the photo tile next to it, which opens the viewer.

**Fix.** With `photosOnly` (or a new `floor` prop), render *Add photo* at normal size, or as
a full-width button under the photos. Leave the equipment and model pages as they are. If
the user prefers to keep the shared look, record it as a decision instead.

### CR1-03 — nit — `frontend/src/views/TicketsView.vue:136-141`

**Problem.** The equipment filter shows only "One equipment only", without saying which
equipment. Its clear control is a bare `btn-close` (about 16 px), well under a gloved tap
target.

**Scenario.** A user who comes from *All its tickets*, or opens a shared link, can't tell
which machine or part the list is limited to, and on a component node it is "tickets raised
on this part only". Clearing it on a phone takes a precise tap.

**Fix.** Show the code, e.g. "Only RPP-001": take it from the first row's machine or
component, or read the node once. Make the whole chip the clear button, at normal button
size.

### CR1-04 — nit — `frontend/src/views/TicketDetailView.vue:40-41`

**Problem.** A non-404 error is shown as the API's raw message. The router guards only the
nav item `/tickets`. A storekeeper who opens a ticket URL (a forwarded link) sees
"Forbidden: requires 'ticket:read'". That is a permission key, which the UX checklist rules
out ("no codes, no field names"; "no permission: the control hidden, not a 403"). The brief
accepts the API's 403 as the gate (BR1-10), so this is wording only.

**Fix.** Map `err.status === 403` to the not-found panel, or to the line "You can't see
tickets." The same applies to `TicketsView`'s `loadError`, although the router guard
already keeps a storekeeper away from that page.

### CR1-05 — nit — `docs/steps/S017-raise-tickets/3-impl-report.md` § 4, decisions 3 and 4

**Problem.** The report says "Departures from the brief's wording are marked
**(departure)**", but only decision 2 is marked. Two more change what the brief states:
- decision 3: the scrap 409 carries `field: "status"`, where the brief's shape has no field;
- decision 4: a second description message for *Other*, where § 5.1 gives one message for
  both cases.

Both are listed in the report and both are sensible, so they are not unreported departures.
Only the marking is missing.

**Fix.** Mark decisions 3 and 4 **(departure)** in the report.

### CR1-06 — nit — `backend/tickets.py:211`

**Problem.** `_equipment_filter` compares `node["level"]` with the literal `"equipment"`.
`tickets_core.MACHINE_LEVEL` exists for exactly this, and `machine_and_component` uses it.

**Fix.** Import `MACHINE_LEVEL` and use it here.

## Points the orchestrator asked about

- **Freezing a failure mode's code: a locking count instead of the plain pre-read (decision
  2, departure).** This is correct, and needed for the "race-free" claim of brief § 5.7:
  - `update_failure_mode`'s first plain read (`_fetch_failure_mode`) fixes the REPEATABLE
    READ snapshot before `_lock_row`;
  - a raise that holds the mode's FK shared lock makes the masters `FOR UPDATE` wait until
    the raise commits;
  - a plain `COUNT` from the old snapshot would then miss that ticket. `LOCK IN SHARE MODE`
    is a current read and sees it;
  - comparing against the locked row's `code`, not the pre-read, also stops two concurrent
    code edits from passing on a stale value.

  There is no deadlock. Masters holds the mode X lock and reads the tickets range. A waiting
  raise holds node (1) and counter (6) locks only, and InnoDB checks foreign keys before it
  inserts the index entries, so the raise holds no `tickets` record lock yet. Gap locks on
  `fk_tickets_failure_mode` can make a raise with a neighbouring mode wait for that short
  transaction, which is harmless. `LOCK IN SHARE MODE` is MariaDB's current syntax, not a
  deprecated API. Tested: a used mode's code gives 409 while its label, description and
  active flag still change, and an unused mode's code still changes.
- **The "One equipment only" chip and the "All its tickets" link (decision 10).** The brief
  lists *equipment* among the list's filters (§ 1) and the API's `equipment_id` (§ 6) but
  gives no UI for it. The link and the chip are the smallest way to reach that filter: no
  new endpoint, no new picker. They are in the report. I judge them within scope; CR1-03
  covers how the chip reads.
- **The new helpers.**
  - `auth_utils.check_perm` is the brief's "`_require_owner_key` raising the same 403" (§ 3)
    under a reusable name. It shares `_log_denied` and `_forbidden_message` with
    `require_perm`, so the 403 body, the log line and the access-log fields are identical.
    The local `ApiError` import follows `require_perm_at`'s existing pattern (no import
    cycle). Its only caller is `documents._owner_key`.
  - `utils/documentTypes.js`: the brief asked for `ACCEPT` as a shared export, and a
    `<script setup>` block cannot export. Moving the iPhone hint and `withoutExtension` with
    it removes the second copy the raise screen would otherwise need (DRY).
  - `siteRoleChoices`: a pure function with tests, which `PeoplePanel` calls. It gives
    exactly § 5.9's rule: IT admin gets every role with a login and Technician or Operator
    without one; anyone else gets Technician only.

  None of the three adds behaviour the brief did not ask for.
- **The lock order and the accepted deadlocks.** The order is node (1) → counter (6) →
  ticket (7). It is stated in `tickets.py` and in `equipment.py`'s docstring with both
  accepted FK deadlocks (scrapping a machine vs raising on its part; a person's site-row
  edit vs a raise naming that person), and `documents.py`'s lock paragraph names the third
  owner (BS1-03).

  Ticket rows are locked only by `_lock_ticket`, which then does plain reads alone
  (`read_ticket`, `require_perm_at`). I found no further cycle:
  - an edit, re-parent or move of the machine takes no lock on its parts;
  - a masters unit or person deactivation takes no equipment lock;
  - the ticket counter row (`TK:…`) is not an equipment counter row (`EQ:…`).

  The scrap check's plain count is safe in both directions:
  - on the node itself, the raise and the scrap serialise on (1), and the snapshot is taken
    after the lock is granted;
  - on a part, a raise that commits while the scrap holds the parent leaves the part not
    scrapped, so `_check_parts_scrapped`'s locking read already refuses.

  The docstring of `_check_no_open_tickets` explains only the first case. The behaviour is
  correct, so this is not a finding.
- **Migration v12 re-adding the owner CHECK.** `DROP CONSTRAINT IF EXISTS` and then
  `ADD CONSTRAINT IF NOT EXISTS chk_equipment_documents_owner` with the three-owner sum,
  under the same name (BR2-01). Every statement is safe to run twice: `IF NOT EXISTS` on the
  tables, column, index and FK. Existing rows have `ticket_id` NULL, so the new CHECK holds
  for them. `test_migration_v12.py` checks the name, each single owner accepted, none or two
  refused, a re-run, and a ticket-photo insert after a re-run of v9. v12 is a new version; no
  applied migration was edited.
- **The generalised documents `Owner` keys.** `Owner` carries `read_key`, `write_key`,
  `purge_key` and `kinds`. The route-level `@require_perm("equipment:…")` literals are
  replaced by `_owner_key(owner, which)` at the top of every route:
  - list, file and thumb use `read_key`;
  - upload, title and remove use `write_key`;
  - restore and purge use `purge_key`.

  The same key is passed to the owner's read and lock function. Equipment and model keep
  exactly their old keys (`test_node_and_model_keys_are_unchanged`), and the S006, S008 and
  S012 suites pass unchanged. A kind outside `kinds` is refused (400, field `kind`) right
  after the form fields are read and before the file is touched. The removed list's ticket
  branch is scoped by `t.unit_id` to the `equipment:purge_documents` units, inside the same
  "has units" block as the node branch.
- **The access predicate.** `_visible_condition` gives `t.unit_id IN (…) OR m.unit_id IN
  (…)` over the `ticket:read` units: `None` means every ticket, an empty set means no
  query. It is used in the list, in `read_ticket` (the detail, and the documents read for
  list, file and thumb), in `read_ticket_for_change` and in `_lock_ticket`, so a ticket's
  photos follow exactly the detail's visibility.

  The write order is 404 (predicate) → 403 (key at the site of `tickets.unit_id`) → 409
  (closed), as BR2-02 asks, with purge skipping the closed check. Tests cover:
  - the moved machine (old unit, new unit, neither);
  - read but not write after a move to another site;
  - access before the key.
- **IT admin holding the ticket keys (decision 7).** `it_admin` is in both new tuples. The
  comments on the keys and on `ROLE_INCLUDES` name the departure (BS1-02). Through
  `every_unit_by_token` IT admin sees every ticket (`test_admin_and_it_admin_see_every_unit`),
  can raise, and can add photos. Restore and purge of ticket photos then pass the 404 step,
  because IT admin holds `ticket:read` everywhere. The storekeeper holds neither key: 403 on
  the API, no nav item (`navigation.test.js`), no section or button on the equipment page.

## Use on the floor (UX) — the three new screens and the equipment page

- **Raise screen.** One job per screen:
  - pick the equipment (skipped when a QR label opens the page);
  - fill the ticket;
  - add photos, then *Done*.

  The controls are sized for gloved hands: three full-width `btn-lg` intensity buttons in
  plain words ("Stopped", "Running, reduced", "Early signs"), `-lg` selects, a full-width
  *Save ticket* and *Add photos*. Everything that can be defaulted is: the time is "now" and
  sent only when changed (BR2-05); symptom and *found by* are optional.

  The open-tickets warning sits just above *Save*, links each ticket in a new tab so the
  form is kept, and says "If this is a different problem, save it as a new ticket".

  Messages are short and plain: "Choose how bad it is", "Describe the problem, or pick a
  symptom", "Choose a symptom from the list", "Choose a person from this site",
  "Scrapped equipment takes no tickets", "That time is in the future", "When did it happen?
  Up to 7 days back". The exception is the empty-time case (CR1-01).

  The no-permission and scrapped states render a line, not a form or a 403. *Save* is
  disabled while saving, so a double tap gives one ticket. A raise cannot be withdrawn in
  S017; S018's *not a fault* covers a mistaken one, and a confirm step on the main floor
  action would only add a tap. No finding.
- **Tickets list.** The rows are a list-group, not a table, and wrap at phone width (badge,
  serial and age on one line, then machine, problem, unit and state). The open order puts
  breakdowns first, then the oldest. The empty, no-units and filtered-empty states each have
  their own line. The four selects and the search wrap above the list on a phone: some
  scrolling, acceptable. See CR1-03.
- **Ticket page.** The details (`dl`) and the timeline stack below `lg`. Long text wraps
  (`overflow-wrap: anywhere`). *Not found* gets a plain line with a link back to the list.
  Photo removal keeps S006's two-step confirm. See CR1-02 and CR1-04.
- **Equipment page.** *Raise ticket* is a normal-size red button, kept apart from the small
  office edit buttons and hidden on scrapped nodes. The *Open tickets* card has loading,
  error and empty states, and appears only with `ticket:read` at the node's site (BR2-04).
- **Settings › Removed documents.** Ticket rows read "Ticket TK-…", with the unit and
  *closed*. *Restore* is disabled, with the reason as a title, on a closed ticket, as on
  scrapped equipment.

## Checked and found consistent

- **Brief § 5.1 raise validation.**
  - `validate_raise` runs before the transaction.
  - Intensity is required and one of three.
  - The description is trimmed (empty → NULL), with a 1000-character limit.
  - Ids are positive ints, booleans refused.
  - `occurred_at`: local `YYYY-MM-DDTHH:MM[:SS]`, `T` or a space; offset and `Z` refused;
    +5 min / −7 day window; default is the server's IST now.
  - `description_error` runs in the transaction after the mode is read.
  - The mode must be active and General or of the **machine's** class (also on a part).
  - The reporter must be active with a membership at the node's site.
- **§ 5.2.** `machine_and_component` reads `level`, `parent_id` and `gp_id`. A scrapped node
  is decided from the locked row; on a part, the machine's status is re-read plain (defence
  in depth). Tested for all three levels and for a machine scrapped by a raw `UPDATE`.
- **§ 5.3.**
  - `unit_id` is the machine's unit at raise.
  - The order is in SQL (`intensity, occurred_at, id` for open; newest first otherwise).
  - `ticket:raise` is checked at the node's site after `load_node_for_user`.
  - The `equipment_id` filter matches the machine on `t.equipment_id` and a part on
    `t.component_id`; an unknown id gives an empty list.
- **§ 5.4.** The serial comes from the IST raise date through `db_helpers.next_counter`, in
  the raise transaction. `_next_code` uses the same helper (DRY, no behaviour change). The
  no-gap test fails the insert after the counter bump. The answer is read inside the
  transaction.
- **§ 5.6.** Both keys are in `SITE_SCOPED`, and the role-matrix tests are updated.
- **§ 5.8.** Scrapping is refused with an open ticket on the node or a part below (the part
  forced scrapped by a raw `UPDATE`), and allowed once the ticket is closed. A ticket on a
  sibling does not block.
- **§ 5.9.**
  - `NO_LOGIN_ROLES` is in `config_rbac` and `TECHNICIAN_ROLE`'s comment is fixed.
  - `no_login_role_error` gives the new message.
  - An engineer asking for an Operator row gets 403 (it was 400).
  - `PeoplePanel` offers Operator without a login to IT admin only.
- **§ 6.**
  - The routes, keys and response shapes match.
  - `/modes` gives the machine's class modes first, then the General ones, active only, by
    label.
  - `/people` gives the people at the node's current site, by name, with their role and
    active trades. `_people_at_site` takes the site first, ready for S018.
  - The documents routes under `/api/tickets/<id>/documents…` do not clash with
    `tickets_bp`.
- **Security.**
  - Every new route is permission-gated: `require_perm` on the tickets routes,
    `_owner_key` on every documents route.
  - The site key is re-checked at the record's site.
  - The actor always comes from `actor()`, never from the body.
  - All SQL is parameterised; the f-strings hold only placeholders, constant columns and
    the constant `ORDER BY`.
  - Files are served only through the permission-checked routes, under `DATA_DIR/tickets/`.
- **Errors and DB.**
  - Exceptions are not swallowed; the frontend's one `catch {}` (the photo-limit read) is
    commented, and the server still checks.
  - `get_db()` raises `DBUnavailable` (503) as everywhere.
  - Pooled connections are handled by `get_db`.
- **Pure core.** `tickets_core` takes `now` from its caller, with no DB and no Flask. Its
  tests cover every item of § 8 *Pure*.
- **Tests and the brief's § 8 list.** Every item of § 8 is covered, failure modes included:
  - 404, 403, 409 and 400 refusals;
  - closed-ticket refusals (restore included);
  - the removed list scoped by unit;
  - storekeeper 403;
  - no-units empty list.

  There are no race tests, as for earlier steps; the races are argued in the code.
- **Report.** "Decisions taken" lists every behaviour I found that the brief did not fix
  (see CR1-05 for the marking). Its `## Manual checks` section carries all three important
  checks of the brief as unticked boxes, and the five plain ones as a list.
- **Comments** say why: the lock notes, the snapshot reasoning, the BR references. No
  deprecated APIs.

## Manual browser checks still needed

From the report's `## Manual checks` (important, unticked):
- [ ] On a phone: scan a QR label → equipment page → **Raise ticket** → critical, a symptom,
  a photo (camera or gallery offered) → the ticket page shows it, with the thumbnail and the
  *raised* line.
- [ ] As an operator of one unit: the list shows only that unit's tickets; another unit's
  ticket URL gives "not found".
- [ ] As IT admin, give a person without a login an Operator row; as a supervisor there,
  raise naming that person as *found by*.

Also worth a look on a real phone (only a phone can show these):
- `datetime-local` on iOS Safari and Android Chrome: changing the time sets `timeTouched`
  (the picker fires `input`), and the picker's *Clear* behaves as CR1-01 describes until it
  is fixed.
- The raise screen's photo step with several photos picked at once over mobile data:
  progress and failure lines readable, *Done* enabled once all have finished.
- The ticket page's *Add photo* button with a gloved hand (CR1-02).
- The list's filter bar at 360 px width: how far the first ticket is pushed down.
