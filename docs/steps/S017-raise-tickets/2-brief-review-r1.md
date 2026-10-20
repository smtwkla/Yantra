```
Step: S017 — Raise and see tickets
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 20-10-2026
```

Reviewed against: 90284ec + uncommitted S016

**Verdict: two `major` findings are open** (BR1-01, BR1-02). The design is
sound and fits Plan.MD § 4.2 and the S016 / S018 briefs; the two majors are
places where the brief relies on code that does not do what it says: the
documents owner pattern hard-codes the equipment keys, so operators could not
upload ticket photos as described, and "operators without a login" do not
exist under S011 A1's rule, so *reported by* cannot name the sorting-line
operator the use case is about. Both need the user, not the coder, to decide.

Findings: 2 major, 6 minor, 5 nit.

---

## Major

### BR1-01 · major — Ticket photos: the documents routes hard-code `equipment:edit`, which raisers do not hold

**Problem.** § 3 and § 5.5 say the ticket owner's routes are "the existing
ones, stacked once more", with upload and remove needing `ticket:raise` and
list / file needing `ticket:read`. The existing routes cannot do that:

- every write route in `documents.py` is decorated `@require_perm("equipment:edit")`
  (`upload_document`, `update_document_title`, `remove_document`) and passes
  the literal `"equipment:edit"` into `OWNERS[owner].lock_for_change(cur, owner_id, "equipment:edit")`;
  list and serve are `@require_perm("equipment:read")`; restore and purge are
  `@require_perm("equipment:purge_documents")` with the same literal;
- `maint_operator` (and the supervisor) hold none of the write keys, so an
  operator adding a photo to a ticket he just raised — the first manual check —
  would get 403 from the decorator before the owner is even looked at;
- `_read_upload` accepts kind `document` and `photo` alike; § 5.5 says photos
  only on a ticket, and nothing in the owner says so;
- `file_store._OWNER_FOLDERS` has `equipment` and `model` only; a third owner
  needs `"ticket": "tickets"`, and `file_store.py` is not in § 3 *Where*.

**Why it matters.** As written the coder either ships a feature operators
cannot use, or redesigns the documents permission model alone — exactly the
decision the brief should take.

**Options.**
1. **Generalise `Owner`** (recommended): add `read_key`, `write_key`,
   `purge_key` and `kinds` to the dataclass (`equipment`: `equipment:read` /
   `equipment:edit` / `equipment:purge_documents` / both kinds; `model`: the
   same; `ticket`: `ticket:read` / `ticket:raise` / `equipment:purge_documents`
   / `("photo",)`). Replace the route-level `@require_perm(<literal>)` with a
   check inside the route on `OWNERS[owner].<key>` (a one-line helper
   `_require_owner_key(owner, which)` that raises the same 403 as
   `require_perm`), and pass the owner's key to `read_for_change` /
   `lock_for_change` / `lock_for_purge`. Refuse a kind outside `kinds` with
   `400 {field: "kind"}` before the file is read. The frontend's
   `DocumentsCards` needs a `photosOnly` prop (no Documents card, no *Add
   document*). Tests: the existing node and model tests keep passing (same
   keys, now data), plus the ticket cases of § 8.
2. **Separate photo routes in `tickets.py`** — a second upload path, which
   § 7 decision 4 rightly rejects.

**Recommendation.** Option 1; write the key table into § 5.5 and add
`file_store.py` and `DocumentsCards.vue` to § 3.

### BR1-02 · major — "Reported by" relies on operators without a login, which S011 A1 does not allow

**Problem.** § 5.1 and assumption 2 say a reporter is "an active person with a
membership at the ticket's site (operators without a login have one, S011
A1)". The code says otherwise: `masters_core.no_login_role_error` refuses any
role but Technician for a person without a login ("Without a login, a person
can only be a technician"), and the S011 brief records it as the user's
decision at A1 gate A ("A person without a login can only be a Technician at a
site … operators, supervisors, engineers and managers are people who log in").
Plan.MD § 3's later sentence — "A person without a login can be a Technician
**or an Operator** … Operators without a login are created by supervisors and
engineers at their own site (decided 16-10-2026; the permission key is settled
in the brief that builds it)" — names a step that has not been briefed or
built.

So today the sorting-line operator who found the fault (Plant-Facts § 5:
packing-machine operators have no phone and report to the supervisor) can be
named only if IT admin enters him as a *Technician*, which is wrong for
pick-lists and for the labour rows S018 builds on the same table.

**Why it matters.** *Reported by* is the TPM operator-ownership field the
brief argues for (§ 2); the user approves a rule that cannot deliver the use
case. S018 § 5.8 ("an assignee or a labour person is an active person with a
membership at the ticket's site") inherits the same gap.

**Options.**
1. **Extend S011's rule in this step, minimally**: a person without a login
   may hold Technician **or Operator** rows (`no_login_role_error`, the Team
   dialog's role select, and the S011 tests that assert "operator → 400"
   flip). Who may set an Operator row stays as today: IT admin
   (`masters:edit`) any role, engineers Technician only (`technician_only`
   unchanged). "Supervisors create operators at their own site" (a new key)
   stays queued. About four files.
2. **Widen the reporter rule instead**: any active person in Team, or any
   person at the site *or with no site rows at all*. Cheaper, but the picker
   then lists people from every site (or people nobody placed), and the
   membership is still the thing that says "works at the sorting line".
3. **Defer**: keep § 5.1 as written; the picker shows what exists (logged-in
   people and no-login technicians); the no-login operator comes with the
   step that builds them. State it as a known gap in § 9.

**Recommendation.** Option 1, presented to the user as a change to an S011
decision; S018 then gets its labour people for free. If the user prefers 3,
assumption 2 must be rewritten to say the use case is not yet served.

---

## Minor

### BR1-03 · minor — "No lock cycle" overlooks the shared locks the ticket insert takes through its foreign keys

**Problem.** § 5.4 says ticket rows are locked last and "nothing that holds a
ticket lock then takes an equipment, unit or counter lock, so no cycle". The
brief itself notes (step 2) that the FK insert takes a shared lock on the
`failure_modes` row; the same insert also takes shared locks on the
**machine's** `equipment` row (when the ticket is raised on a part, the
machine is only plain-read), the `units` row and the `people` row. Two cycles
exist:
- **scrap the machine vs raise on its part**: scrap locks M (1) then its parts
  `FOR UPDATE` (`_check_parts_scrapped`) and waits on C; the raise holds C (1)
  and its insert waits for a shared lock on M;
- **a person's site-row edit vs a raise naming that person**: `put_person_site`
  locks the person then the units (`_check_grantable … FOR UPDATE`); the
  insert takes its FK locks in constraint order (unit, then person, if defined
  so), the reverse.

InnoDB detects both and rolls one transaction back (error 1213), which today
surfaces as a 500, not a 409.

**Why it matters.** Rare, but the claim in the brief is what the code reviewer
will check the docstring against; a known, named race is fine, an undocumented
one is not (equipment.py already records "the one accepted deadlock" for the
scrap check).

**Options.** (a) Accept and document both in the lock-order note (equipment.py
and tickets.py), as equipment.py does — recommended; (b) lock top-down
(machine first, then the node) and re-read the node's parent after locking, so
the raise follows the scrap check's direction — more code for a race between
scrapping a machine and reporting a fault on it. Either way, note that mode
*deactivation* between the plain read and the insert is not race-free and need
not be (an inactive code "stays on old tickets", S016 § 1.5).

### BR1-04 · minor — One unit rule for list and detail; the order must be SQL, not a Python key

**Problem.** § 5.3 gives the detail two doors (the ticket's unit **or** the
machine's current unit) but the list only one (`tickets.unit_id IN …`). The
equipment page lists tickets through `GET /api/tickets?equipment_id=…`, so a
user who holds the machine's current unit but not the unit it was raised in
sees nothing on the equipment page yet can open the ticket by URL — the
opposite of § 5.3's "the equipment page still lists the machine's tickets
wherever it now stands".

Separately, § 3 puts `list_order_key(row)` in the pure core and § 8 tests it
there. The list is server-paginated (`page`, `per_page`), so the order must be
in the SQL; a Python key would order each page on its own.

**Options.** List and detail share one predicate: `t.unit_id IN (…) OR
mu.id IN (…)` with `JOIN equipment m ON m.id = t.equipment_id JOIN units mu ON
mu.id = m.unit_id` (the machine is level 6, so one join). Order: `ORDER BY
t.intensity, t.occurred_at, t.id` — the ENUM is declared critical, degraded,
initial, so it sorts critical first with no `FIELD()` (the trick S016 uses for
`cause_group`); say what order `state=closed` / `all` use (newest first is the
useful one). Drop `list_order_key` from the core, or keep it only as the
documented SQL expression; the "list order" test becomes an API test.

### BR1-05 · minor — The rest of the third owner: removed documents, restore / purge, title edit

**Problem.** § 4.2 says ticket photos get "S008's restore and purge from
Settings", but `documents.py`'s removed list is a `UNION ALL` of exactly two
branches (`_REMOVED_NODE_BRANCH`, `_REMOVED_MODEL_BRANCH`), `_removed_item`
shapes a row as a node (unit, full path) or a model (label), and
`RemovedDocuments.vue` renders those two shapes. Restore and purge routes are
stacked per owner and call `lock_for_change` / `lock_for_purge` with the purge
key. None of this is in § 3 or § 5.5, nor: which key edits a ticket photo's
title (`PUT …/documents/<id>`), whether a closed ticket refuses a title edit
too, and which units scope the ticket branch of the removed list.

**Options.** Add to § 5.5: a third branch joining `tickets` → `units`, scoped
to `accessible_unit_ids(cur, "equipment:purge_documents")` by the ticket's unit
(as the node branch is); item shape `{owner: "ticket", name: <serial>, unit,
full_path: null}` and one more `v-if` in the card; `lock_for_purge` for a
ticket = lock the row, `equipment:purge_documents` at the ticket's site, no
closed check (as the node's purge skips scrapped — erasing is disposition, not
a change to the record, S008 § 5.3); title edit by `ticket:raise`, refused on
a closed ticket like remove. Add `test_removed_documents_api.py` to § 3 *Tests*.

### BR1-06 · minor — `validate_raise` needs the mode before it can apply the description rule; the event-time wire format is unsaid

**Problem.** § 3 says `validate_raise(body, now)` "receives whether the mode is
`OTH` from the shell", but every other route validates the body
(`clean_body`) before the transaction, and the mode is read inside it
(§ 5.4 step 2). The coder has to invent the sequence. Also unspecified: the
format of `occurred_at` on the wire (an `<input type="datetime-local">` sends
`YYYY-MM-DDTHH:MM`, no seconds, no offset; `row_to_dict` answers with
`+05:30`), how a value with an offset is treated, and what `now` is (IST
naive, from `datetime.now(IST)` as `equipment.IST`).

**Options.** Split the pure core in two: `validate_raise(body, now)` → shape,
intensity, lengths, ids, the event-time window; then
`description_error(description, mode_code)` → the message or None, called in
the transaction once the mode row is read (and for no mode). State the
accepted `occurred_at` forms (`YYYY-MM-DDTHH:MM[:SS]`, optional ` ` instead of
`T`, an optional `+05:30` ignored or refused — pick one) and that the stored
value is IST naive (base § Timezone policy).

### BR1-07 · minor — Standards: a few terms are not what the standards say

**Problem and fix** (for the owner, who is learning these):
- **EN 13306**: a *failure* is an **event** — the loss of the ability to
  perform as required; a *fault* is the **state** of the item after a failure
  (it cannot perform). § 2 says "a fault that has not yet stopped the item is a
  degraded state": in EN 13306 the running-with-reduced-function case is a
  **partial failure** / **degraded state**, not a fault; the item still has a
  fault only once it cannot perform. So: critical = failure (and the item is in
  a fault state), degraded = partial failure, initial = ISO 14224's *incipient*
  impact. The mapping is right; the sentence is wrong.
- **EN 13460** (maintenance documentation) calls the document a **work
  request** (then a **work order**); "maintenance request" is this project's
  word for it, fine to keep, but say which is the standard's.
- **ISO 14224** does not record *who* detected a failure; it records the
  **detection method** (how: operator observation, periodic maintenance,
  condition monitoring …) — which § 1 correctly defers. *Reported by* is TPM's
  operator ownership, not an ISO field; § 2 says "and who detected it" under
  ISO 14224 — move that clause to the TPM bullet.
- **ISO 27001** is not cited: photos served only through permission-checked
  routes is A.8.3 (information access restriction, as S006 cites); the
  `reporters` picker shows names only and only at a site where the user may
  raise, which is A.5.15 / least privilege — one line each.

### BR1-08 · minor — Two API tests cannot be set up as described

**Problem.**
- "A raise refused after the counter bump (bad mode) leaves no gap": by § 5.4
  the mode is checked in step 2 and the counter bumped in step 3, so a bad
  mode never reaches the bump and the test proves nothing about the rollback.
- "Node under a scrapped machine 409": the API cannot produce one — scrapping
  a machine needs every part scrapped first (`_check_parts_scrapped`), so the
  check is defence in depth only.

**Options.** For the gap test, fail *after* the bump (monkeypatch
`db_helpers.insert_row` to raise inside the transaction, or send a
`reported_by_id` that passes the check but whose FK insert fails — hard) and
assert the next serial continues; or drop the test and rely on `transaction()`
as the equipment code does. For the scrapped-machine case, set the machine
scrapped with a raw `UPDATE` through `db_rows`' connection, or drop the test
and keep the check as a one-line note.

---

## Nit

### BR1-09 · nit — Share the counter bump with equipment codes

`_next_code` in equipment.py is private and scoped `EQ:<prefix>`; the brief
says "the same INSERT … ON DUPLICATE KEY UPDATE / read-back as `_next_code`",
i.e. a copy. Extract `next_counter(cur, scope) -> int` (db_helpers, or a
small `serials.py`) and have both call it (DRY); `format_ticket_serial` stays
in `tickets_core`.

### BR1-10 · nit — The router guards nav items only

`canOpenRoute` checks a route only when it is a nav item, so "route permission
`ticket:raise` for `/tickets/new`" is not something the router does today;
`/tickets/:id` likewise. Either say the API's 403 / 404 is the gate and the
buttons are hidden by permission, or extend `navigation.js` with a small
per-route permission map (and a test in `navigation.test.js`). Also hide
*Raise ticket* on a scrapped node (the API refuses with 409 anyway).

### BR1-11 · nit — Photo picker: `capture`, `accept`, and the title

`capture` forces the camera and hides the gallery on most phones; S006 left it
out on purpose ("so a phone offers the camera and the gallery"). An operator
may have taken the photo before opening Yantra: recommend no `capture`.
`accept="image/*"` lets HEIC through to a 400; reuse `ACCEPT.photo`
(`image/jpeg,image/png,image/webp`) and S006's iPhone hint. The upload API
requires a `title`: say what the raise screen sends (the file name without its
extension, as `DocumentUploadModal` pre-fills, or "Photo n").

### BR1-12 · nit — Scrapping a machine that has open tickets

Not covered: equipment.py's scrap rule does not look at tickets. Say that S017
allows it (the open ticket stays, S018 closes it) or refuses it (409 "Close its
tickets first"), and record it in § 9 so S018 / S019 inherit a decision rather
than a gap.

### BR1-13 · nit — Small gaps in the text

- `age` in the list row: from `occurred_at` (say so; for a breakdown it is the
  stop so far).
- § 3 "`backend/app.py` (or wherever blueprints are registered)": it is
  `app.py`; drop the hedge. The documents blueprint is registered at `/api`
  and spells out each owner's path, so `/api/tickets/<id>/documents` lives
  there while `tickets_bp` takes `/api/tickets` — no clash, worth one line.
- `GET /api/tickets/modes` duplicates S016's
  `GET /api/masters/failure-modes?class_id=N`; it is justified because a
  component's detail does not carry its machine's `class_id` (`_ancestors`
  gives id, code, level, name) — say that, or add `class_id` to the ancestors
  and drop the endpoint.
- Plan.MD § 5 still lists an `attachments` table for ticket photos; the Docs
  list in § 3 should remove it (decision 4).
- Manual check 1 on a phone and 3 (unit access) are rightly important; check
  2 (the open-ticket warning) is a screen behaviour a desktop shows as well —
  plain is enough, but keeping it important does no harm.

---

## Checked and found consistent

- **Plan.MD**: § 4.2 one table with states, intensity → breakdown / defect,
  event time entered, reported by, symptom optional at raise (user decision),
  `TK-` prefix (user decision over the plan's `BD-`), `ticket:*` replacing
  `breakdown:*` as the plan allows ("settled in the phase 3 brief"); § 3 key
  rows for `breakdown:raise` match § 5.6; § 4.1 "codes frozen once in use"
  matches § 5.7.
- **S016**: § 5.4's three hand-overs are all taken up — the mode's class
  checked in the API against the **machine's** class (not a composite FK),
  code frozen once a ticket uses it (label, description, active stay
  editable), S016 assumption 5 confirmed. `update_failure_mode` does lock the
  mode row (`_lock_row`) before the update, so the count-then-409 of § 5.7
  sits under that lock; the FK shared lock on insert serialises with it as
  the brief says. `GET /failure-modes?class_id=N` returns class N plus General
  by label, as § 6 relies on.
- **S018 hand-over**: `ticket_events.intensity` (set on `raised`, NULL when
  unchanged) and `person_id`, `from_state` / `to_state`, `occurred_at` per
  event; the full state ENUM so v13 alters no ENUM; the closed rule for photos
  written and tested now; `FUTURE_SKEW` / `MAX_BACKDATE_DAYS` in
  `tickets_core`; `raised.occurred_at` = the ticket's event time, which S018
  assumption 3 measures response time from; `validate_raise` is extensible
  with `repeat_of_id` (S018 § 5.5). S018 § 5.8's labour-people rule is the same
  as § 5.1's reporter rule, so BR1-02's answer serves both.
- **Code claims verified**: `load_node_for_user(cur, id, for_update=True,
  key=…)` decides 404 (equipment:read units) then 403 (`require_perm_at` at the
  node's site) as § 5.3 / § 5.4 say; `accessible_unit_ids(cur, key)` fails
  closed for IT admin on a new key (`every_unit_by_token`), so "not IT admin"
  needs no extra code; `has_perm_at` asserts the key is in `SITE_SCOPED`, so
  forgetting it fails loudly in tests; `_check_parts_scrapped` makes "a node
  under a scrapped machine" unreachable through the API (BR1-08);
  `serial_counters.scope` is VARCHAR(40) and `serial` VARCHAR(16) fits
  `TK-2026-10-1000`; the v9 CHECK is a named constraint
  (`chk_equipment_documents_owner`) so drop-and-re-add works, and
  `test_migration_v9.py` tests behaviour (two owners / none), not the text, so
  it keeps passing; `equipment_documents.ix_…_model (model_id, removed_at)` is
  the index pattern § 4.2 copies; `test_role_matrix` asserts exact sets, so
  the two keys go into every row that gains them.
- **Base patterns**: serial from a counter row locked in the transaction
  (base § Serial Number Generation, `PREFIX-YYYY-MM-NNN`); paginated list
  shape; uploads through S006's checked path only; IST naive `DATETIME`; nav
  items data-driven and permission-filtered (sidebar and bottom nav share
  `navItems`).
- **Track**: full, rightly (migration, keys, locks, uploads).
- **Over-engineering**: none seen; `tickets_core` stays small and pure.
