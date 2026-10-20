```
Step: S017 — Raise and see tickets
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 20-10-2026
```

Reviewed against: 90284ec + uncommitted S016, S015

**Verdict: no `blocker` or `major` finding is open.** Both round-1 majors are
answered in the text, not only in the log: the documents owner now carries its
keys and kinds as data (§ 5.5), and the user's decision 5 lets a person without
a login hold an Operator row (§ 5.9), so *reported by* can name the sorting-line
operator. The revisions introduced a handful of smaller gaps, mostly where the
new text leans on code that behaves slightly differently from what it says.

Findings: 0 blocker, 0 major, 5 minor, 3 nit.

---

## Round 1 — every `Accepted` answer checked against the brief text

| Finding | In the text? |
|---|---|
| BR1-01 owner keys as data | Yes: § 3 documents.py / file_store / DocumentsCards, § 5.5 key table, § 7 #4 |
| BR1-02 operators without a login | Yes: user decision 5, § 1, § 3 masters_core / PeoplePanel / tests, § 5.9, § 7 #11, § 9.2 — see BR2-06 for two details |
| BR1-03 FK deadlocks | Yes: § 5.4 names both, the 1213 → 500 consequence, the harmless deactivation race; § 7 #12 |
| BR1-04 one predicate, SQL order | Yes: § 5.3; `list_order_key` gone; order tested in the API (§ 8) |
| BR1-05 removed list, purge, title | Yes: § 5.5 (third branch, item shape, purge without the closed check, title by `ticket:raise`), § 3 tests |
| BR1-06 sequencing, wire format | Yes: § 3 `validate_raise` / `description_error`, § 5.1 |
| BR1-07 standards | Yes: § 2 — failure (event) / fault (state) / partial failure; EN 13460 *work request*; detection method under ISO 14224, *reported by* under TPM; ISO 27001 A.8.3 and A.5.15 |
| BR1-08 two tests | Yes: § 8 (monkeypatched insert; raw `UPDATE`) |
| BR1-09 `next_counter` | Yes: § 3 db_helpers, § 4.3 |
| BR1-10 router | Yes: § 3 Router |
| BR1-11 photo picker | Yes: § 3 RaiseTicketView |
| BR1-12 scrap with open tickets | Yes: user decision 6, § 5.8, § 7 #10, § 8 |
| BR1-13 text gaps | Yes: age from the event time; `app.py`; blueprint paths; `/modes` reason; Plan § 5 `attachments` row; manual check made plain |

---

## Minor

### BR2-01 · minor — Migration v12 must re-add the owner CHECK under its old name, or `test_migration_v9`'s re-run puts the two-owner rule back

**Problem.** § 4.2: the v9 CHECK "is dropped and re-added as exactly one of the
three". `test_migration_v9.py` deletes `db_version` 9 and runs `init_db` twice
on the test database. v9's statement is `ADD CONSTRAINT IF NOT EXISTS
chk_equipment_documents_owner CHECK ((equipment_id IS NOT NULL) + (model_id IS
NOT NULL) = 1)`. If v12 re-adds the three-owner CHECK under **another** name,
that re-run adds the two-owner CHECK back beside it, and from then on every
ticket photo insert in the session (both old columns NULL) fails with 4025 —
an order-dependent failure in `test_documents_api.py` that would look like a
bug in the upload code.

**Why it matters.** The brief's "every statement safe to run twice" is about
v12; this is v9 re-running on top of v12, which the suite does on purpose.

**Options.**
1. **Keep the name** (recommended): `DROP CONSTRAINT IF EXISTS
   chk_equipment_documents_owner` then `ADD CONSTRAINT IF NOT EXISTS
   chk_equipment_documents_owner CHECK (… + (ticket_id IS NOT NULL) = 1)`, so
   v9's `IF NOT EXISTS` is a no-op afterwards. One line in § 4.2, and
   `test_migration_v12.py` asserts the name.
2. Change `test_migration_v9.py` to drop the new CHECK first — fragile.

### BR2-02 · minor — The ticket owner's write path omits its 404 step; say the order for `read_for_change` and `lock_for_change`

**Problem.** § 5.5 gives the ticket owner's *read* ("by the access predicate,
404 otherwise") and its *lock for change* ("lock the ticket row (7);
`write_key` at the ticket's site (403); closed 409"), but not that the lock
also applies the access predicate first, and says nothing about the ticket's
`read_for_change` — the plain pre-check `upload_document` runs before the file
is read (`OWNERS[owner].read_for_change`). For nodes both steps go 404 (unit
access) → 403 (key at the site) → 409 (scrapped), from the locked row where it
counts. Without the 404, a user holding `ticket:raise` at the ticket's site but
no unit access to it (a chosen-units operator) could upload to a ticket he
cannot open.

**Options.** State both functions for the ticket owner, in the node's order:
`read_for_change` = plain read by the predicate (404) → `write_key` at the
site of `tickets.unit_id` (403) → closed (409); `lock_for_change` = the same
decided from the row locked `FOR UPDATE`. Add "upload by a user with the key
at the site but not the unit → 404" to § 8 *Documents*.

### BR2-03 · minor — "`ticket:read` only → upload 403" cannot be set up with the matrix of § 5.6

**Problem.** § 8 *Documents*: "`ticket:read` only → list and view but upload
403". Every role that holds `ticket:read` also holds `ticket:raise` (§ 5.6:
both go to `maint_operator`, everyone else inherits), and admin bypasses, so no
`X-Test-Role` user has one key without the other — the BR1-08 class of test
again.

**Options.**
1. **Use the moved machine** (recommended, and it tests the thing that matters):
   raise at unit U1 (site A), move the machine to U2 (site B) as admin, then a
   user with operator at B only **reads** the ticket (the predicate's second
   door) but gets 403 on upload, title and remove (`ticket:raise` checked at
   the ticket's site, A). § 8 already builds that machine for the list test.
2. Monkeypatch `config_rbac.PERMISSIONS` for one test, as
   `test_removed_documents_api.py` patches the module.

### BR2-04 · minor — The equipment page's *Open tickets* section for users who hold no `ticket:read` at the node's site

**Problem.** § 1 / § 3 add an *Open tickets* section to the equipment page,
loaded from `GET /api/tickets?equipment_id=…&state=open`. IT admin (and the
storekeeper) can open every equipment page but holds neither key (§ 5.6), so
the call answers 403 at the decorator, and the section would show an error on
every page IT admin opens for masters housekeeping. The brief hides the *Raise
ticket* button by permission but says nothing about the section.

**Options.** The node detail already sends `permissions` (the user's keys at
the node's site, `permissions_at_site`): render the section only when
`ticket:read` is in it, and the button only when `ticket:raise` is — one line
in § 3 `EquipmentDetailView.vue`. (The same `permissions` list makes the
button follow the site, as `canEdit` does today.)

### BR2-05 · minor — The raise screen must send `occurred_at` only when the user changed it; S018 already assumes it does

**Problem.** § 3: "event time (`<input type="datetime-local">`, default now)".
If the field is pre-filled with the phone's clock and always sent, a phone six
minutes fast gets `400 occurred_at` on every raise, with a message about
"When did it happen?" for a user who typed nothing. S018's brief (§ 5.1,
decision 9, BR1-05) settled that its dialogs send no time unless the user
changed it, so the server's clock is the default — and states "S017's raise
screen follows the same rule". S017's text does not say so.

**Options.** Add to § 3 `RaiseTicketView.vue` and § 5.1: the field shows the
phone's now, but `occurred_at` is sent only when the user changed it; absent →
`now` on the server (`validate_raise` already defaults it). One frontend test
is not needed; the API test "raise without `occurred_at` gets the server's
time" covers it.

---

## Nit

### BR2-06 · nit — Two details of user decision 5: where the no-login roles live, and what the Team dialog offers to whom

- `config_rbac.TECHNICIAN_ROLE`'s comment says it is "the one a person without
  a login may hold", and `masters_core.no_login_role_error` compares against
  that one constant. With two roles allowed, keep `config_rbac.py` the single
  source (CLAUDE.md): a `NO_LOGIN_ROLES = (TECHNICIAN_ROLE, "maint_operator")`
  tuple there, used by `no_login_role_error`; `TECHNICIAN_ROLE` keeps its
  engineer-grant meaning. Add `config_rbac.py` to that part of § 3.
- `PeoplePanel.vue`'s `roleChoices` offers all roles only when IT admin is
  giving a login, else Technician alone — for engineers and for IT admin alike.
  § 3 / § 5.9 should say: IT admin without a login → Technician or Operator;
  an engineer → Technician only, as today (the server answers 403 "Only IT
  admin can set this role" otherwise).
- § 8 *Masters*: "an engineer still cannot set an Operator row (403 / refused
  as today)". Today it is **400** for an engineer, because the no-login check
  runs before the 403 in `put_person_site`; after the change the same request
  is 403. `TestNoLoginTechnicianOnly.test_other_roles_are_400` runs operator
  for both the engineer and admin clients, so it splits: admin + operator →
  200, engineer + operator → 403, the other roles → 400 with the new message.

### BR2-07 · nit — Restore on a closed ticket, and the removed-list item's `state`

Restore goes through `lock_for_change` (documents.py), so with § 5.5's closed
rule a closed ticket's removed photo cannot be restored (409), as a scrapped
node's cannot today — right by analogy with S008, but say it. The removed
list's ticket shape (`{owner: "ticket", name: <serial>, unit, full_path:
null}`) should then carry `state`, so `RemovedDocuments.vue` can disable
*Restore* with a title, as it does for `status === 'scrapped'`. Also hide the
upload modal's Kind radio when `photosOnly` (today it always offers Document,
which a ticket would refuse with 400 after the pick).

### BR2-08 · nit — Small gaps in the text

- § 6 `equipment_id` "(machine or component)": for a **component-unit** say
  whether its page lists tickets on it alone (`component_id = node`) or on it
  and its components; and the raise screen's "machine's open tickets" warning
  on a component node needs the machine's id (`ancestors[0]` of the node
  detail), not the node's — say which call it makes.
- `machine_and_component(node, ancestors)`: `equipment._ancestors` is private;
  either expose it or derive from the node's `gp_id` / `parent_id` / `level`.
- `raised` event's `person_id`: NULL, or `reported_by_id`? Pick one (the
  ticket column holds the reporter either way).
- tickets.py never imports documents.py (documents.py imports the ticket
  owner's predicate from tickets.py); one line in § 3 keeps the circle out.
- § 3 / § 5.5 "before the file is read": `request.form` spools the whole body,
  so the kind check is before the file is *checked and written*, not before it
  is read from the wire.
- A component re-parented to another machine while its ticket is open keeps
  the stored machine (as the unit does, § 5.3); S018's edit rule ("a node
  under the ticket's machine") then refers to the stored one. One line.
- Hand-over note for S018: `GET /api/tickets/people?equipment_id=` resolves the
  **node's current** site, while S018 checks assignees and labour at the
  **ticket's** site (`tickets.unit_id`); after a cross-site move the two differ.
  S018 may need a `ticket_id=` anchor on the same endpoint; mention it so the
  endpoint's helper (`_people_at_site(cur, site_id)`) is written site-first.
- README Queued has no row for "supervisors and engineers create operators
  without a login at their own site" (Plan.MD § 3 says it is decided); the Docs
  list at approval should add it, since the brief calls it "still queued".

---

## Checked and found consistent

- **User decisions 5 and 6** are reflected in § 1, § 3, § 5.8, § 5.9, § 7
  #10–11, § 8 and the Docs list (Plan.MD § 3 and § 4.1, the S011 gate-A note).
  S011 A1's gate-A text ("without a login, only a technician"; the Team dialog
  offers only Technician) is exactly what changes, and `Plan.MD` § 3 already
  reads "Technician or an Operator", so the plan and the code will agree again.
- **S018 hand-overs**: `GET /api/tickets/people` with trades `[{id, name}]`
  and the role at the site (§ 6); the detail's events carry `intensity`, NULL
  when unchanged (§ 4.1, § 6); `event_time_error(event_time, now,
  not_before=None)` with S018's `validate_event_time` calling it (§ 3, § 8);
  `current_person_id(cur)` left to S018 (§ 6); full state ENUM (§ 4.1); the
  closed-ticket rule for photos written and tested now (§ 5.5, § 8); "the
  ticket's site" = the site of `tickets.unit_id` everywhere (§ 5.3).
- **Code claims verified.** `update_failure_mode` runs `_lock_row` on the mode
  before `update_row`, so the count-then-409 of § 5.7 sits under the lock and
  an in-flight ticket insert's FK shared lock queues behind it (its `stored`
  read must gain `code` to see whether the code changes). `no_login_role_error`
  is called at exactly the two places § 3 names (`_replace_site_rows` on a
  login save with no username, `put_person_site`); `technician_only` and
  `_SiteViewer.editable` are untouched by the change. `load_node_for_user(…,
  for_update=True, key=…)` decides 404 (equipment:read units) then 403
  (`require_perm_at` at the node's site) and returns the locked status, as
  § 5.4 step 1 relies on; the machine's status is not in `_NODE_COLUMNS`, so
  the "re-read plain" of § 5.2 is a separate one-row read, as the brief implies.
  `_check_parts_scrapped` locks children then grandchildren `FOR UPDATE`, which
  is the lock § 5.8 counts under. `every_unit_by_token` returns False for
  IT admin on a key its role lacks, so `accessible_unit_ids(cur, "ticket:read")`
  is an empty set for IT admin (§ 5.6). `_check_site_args` asserts
  `SITE_SCOPED`, so a forgotten key fails loudly. `documents_bp` is registered
  at `/api` and spells each owner's path; `equipment_bp` at `/api/equipment`;
  a `tickets_bp` at `/api/tickets` with `/api/tickets/<id>/documents` in
  documents.py has no clash (§ 3). `_OWNER_FOLDERS` has two owners today, so
  `"ticket": "tickets"` is needed as § 3 says. `_DOCS` routes carry
  `@require_perm("equipment:…")` literals in all seven write/read routes and
  pass the literal into `lock_for_change` / `lock_for_purge`, which is what
  § 5.5's data-driven keys replace; `list_removed_documents` keeps its
  `equipment:purge_documents` decorator (global list), which is right.
  `serial_counters.scope` VARCHAR(40), `serial` VARCHAR(16) fits
  `TK-2026-10-1000`; `format_equipment_code` pads to 3 digits and grows, the
  rule `format_ticket_serial` copies. `row_to_dict` answers `+05:30`, and the
  wire format of § 5.1 refuses offsets on input, which keeps one zone (base
  § Timezone policy). `DocumentUploadModal` already has no `capture`, uses
  `ACCEPT.photo` = `image/jpeg,image/png,image/webp` and pre-fills the title
  from the file name without its extension, as § 3 says to reuse.
- **Tests that change**: `test_role_matrix` rows for operator, technician,
  supervisor, engineer and manager gain the two keys (not IT admin, not the
  storekeeper); `test_no_login_only_technician` and
  `TestNoLoginTechnicianOnly` flip as § 3 says (detail in BR2-06);
  `test_migration_v9.py`'s two-owner / no-owner insert still fails with 4025
  under the three-owner CHECK (and keeps failing only if BR2-01 is followed);
  `test_operator_reads_but_cannot_upload_edit_or_remove` and the model-document
  tests keep passing because the node and model owners keep today's keys as
  data.
- **Standards** (for the owner, in plain terms): EN 13306 draws the line the
  brief now draws — a *failure* is the moment the item loses its ability (an
  event); the *fault* is the state it is then in; running with reduced function
  is a *partial failure* (a degraded state), which is why *degraded* is not a
  fault. ISO 14224 asks for the item, the failure date, the failure mode, the
  failure impact (critical / degraded / incipient — our three intensities) and
  the detection method (*how* it was found, not *who*; deferred to `source`).
  EN 13460 calls the first record a *work request* and the maintained one a
  *work order*; one table holding both is the plan's choice. TPM's tag is the
  operator's ownership, which is where *reported by* belongs. ISO 27001 A.8.3
  (information access restriction) covers photos served only through checked
  routes; A.5.15 (access control) the names-only picker at the user's own
  sites. ISO 55001's controlled disposal justifies refusing a scrap with open
  tickets. All cited correctly.
- **Base patterns**: serial from a counter row in the transaction
  (`PREFIX-YYYY-MM-NNN`); paginated `{items, total, page, per_page}`; uploads
  only through the checked path; IST naive `DATETIME`; nav items data-driven
  and permission-filtered; migration statements safe to run twice.
- **Track**: full, rightly. **Manual checks**: the three important ones (phone
  QR → raise with photo; unit access on the list and by URL; IT admin's
  Operator row then *reported by* as a supervisor) are the ones only a person
  can do; the plain ones are plain.
- **Over-engineering**: none; `tickets_core` stays small, the owner
  generalisation is data, not a second upload path.
