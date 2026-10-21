```
Step: S017 — Raise and see tickets
Doc: brief
Author: Planner (Opus)
Date: 20-10-2026 (revised 20-10-2026 after brief-reviews r1 and r2)
Track: full
Baseline: 6c771e1 (stale brief check s1, 20-10-2026)
Status: Committed cfedc46; manual checks pending (approved 20-10-2026 by KLA)
```

# S017 — Raise and see tickets

Phase 3 starts here: **one ticket for every problem found on equipment**
(Plan.MD § 4.2, decided 18-10-2026). This step lets the shop floor **raise** a
ticket — a breakdown or a defect, by intensity — and lets everyone with access
**see** the open tickets of their units and each ticket's page with its
timeline and photos. Working the ticket (acknowledge, in progress, back in
service, close, labour, codes) is **S018**; deferred work is S019; alerts are
S021.

User decisions taken before this brief (20-10-2026):
1. **Serial prefix `TK-`**: `TK-2026-10-001`, one series for breakdowns and
   defects (a defect can be re-graded to a breakdown; Plan.MD § 4.2).
2. **The symptom (failure mode) is optional at raise.** The technician or
   engineer fills it later (S018 requires it at close).
3. **"Not fixed" after back in service is a new ticket**, linked to the old one
   (built in S018, where the states exist).
4. **Assignment to technicians is in S018.**

User decisions after brief-review r1 (20-10-2026):
5. **A person without a login may be an Operator** at a site, not only a
   Technician (BR1-02; changes the S011 A1 gate-A decision "without a login,
   only a technician"). Only IT admin sets an Operator row; engineers still set
   Technician rows only. So the phone-less sorting-line operator can be named as
   *reported by*. "Supervisors create operators at their own site" stays queued.
6. **Scrapping equipment that has open tickets is refused** (BR1-12): 409
   "Close its tickets first".

User decision at gate A (20-10-2026, open question 1):
7. **IT admin gets full access to tickets** (`ticket:read`, `ticket:raise`,
   and S018's keys); **the storekeeper gets none for now**.

**Track: full** — a migration, new permission keys, a locked serial counter,
uploads on a new owner, a change to an S011 rule, more than 10 files.
**Depends on:** S016 (`failure_modes`), being coded now; S017 is coded after
S016 is committed.

## 1. What will be built

- **Raise a ticket** (phone first):
  - from the equipment page (**Raise ticket** button), which a QR label opens
    (`/e/<code>`, S014), or from the Tickets list (**Raise ticket**, then pick
    the equipment);
  - the user gives:
    - **intensity** — *critical* (stopped), *degraded* (running, reduced),
      *initial* (early signs). Critical is a **breakdown**, the other two are a
      **defect** (Plan.MD § 4.2);
    - **symptom** — optional: the failure modes of the machine's class plus
      the General ones (S016 § 5.2);
    - **description** — free text; required when no symptom is picked, or the
      symptom is *Other* (`OTH`);
    - **when it happened** — the event time, default now (Plan.MD § 4.2: event
      time is entered, not implied);
    - **reported by** — optional, a person from Team at the site: the operator
      who found the fault, when someone else raises it (the supervisor). Kept
      apart from who raised the ticket (the login). Operators without a login
      can be named (user decision 5);
    - **photos** — optional, one or more, added right after the ticket is saved,
      on the same screen.
  - The ticket can be raised on any node of the tree: on a machine, or on a
    component-unit or component (a QR on a press's door sensor). The ticket
    stores the **machine** (the level-6 equipment) and, when raised lower, the
    **component** (§ 5.2).
  - **Before saving**, the screen lists the machine's open tickets, so the user
    can see the fault is already reported. It warns, it does not block: one
    machine can have two faults.
  - The ticket gets its serial `TK-YYYY-MM-NNN` and state **raised**.
- **Tickets list** (new nav item *Tickets*):
  - open tickets at the user's units by default (states raised to back in
    service); filters: site, unit, intensity (breakdown / defect), state
    (open / closed / all), equipment, text in serial or description;
  - open tickets sorted by intensity (critical first), then oldest event time
    first: what is down and waiting longest leads. Closed and all: newest
    first (§ 5.3);
  - each row: serial, intensity badge, machine code and name (component code
    when set), unit, symptom or the start of the description, state, **age**
    (from the event time: for a breakdown, how long it has been stopped so
    far).
- **Ticket page** — serial, intensity, state, machine (link to the equipment
  page) and component, symptom, description, reported by, raised by, when it
  happened, the photos (thumbnails, open full size), and the **timeline** (one
  line per event: what, event time, who, remark). In S017 the timeline holds
  the *raised* event; S018 adds the rest.
- **Equipment page** — an **Open tickets** section (the machine's open tickets,
  and on a component the tickets on that component), and the **Raise ticket**
  button for users who may raise at its site, hidden on scrapped equipment.
- **Failure-mode codes frozen once in use** (S016 § 5.4, Plan.MD § 4.1): once a
  ticket uses a mode, its code can no longer be changed.
- **Scrapping refused while tickets are open** (user decision 6): scrapping a
  node with an open ticket on it — as machine or as component — gives 409
  "Close its tickets first" (§ 5.8).
- **Team: Operator rows without a login** (user decision 5): in Masters ›
  Team, IT admin may give a person without a login an Operator row at a site,
  as already possible for Technician (§ 5.9).
- **Ticket photos** use the existing documents store as a third owner, and
  show in Settings › Removed documents for restore or purge like the others
  (§ 5.5).

### Out of scope

- Every state after *raised*, labour, cause and action codes, assignment,
  re-grading the intensity, editing a raised ticket, "not fixed" — **S018**.
- Scheduled state, planned date, waiting reasons — **S019**.
- Raise-and-close for work done without a ticket, parts used — **S020**.
- Notifications and escalation — **S021**. A new breakdown notifies nobody
  until then; the list is where maintenance sees it.
- Tickets from CIL / PM items or readings (phase 4), and the shared ticket API
  for other systems (later). The `source` column leaves room for them.
- Detection method (Plan.MD § 4.2, *Proposed*): every S017 ticket is raised by
  hand, so it would always be *operator observation*; it is derived from
  `source` when other sources exist.
- Diagnostic procedures (Plan.MD § 4.3a).
- Supervisors and engineers creating operators without a login at their own
  site (Plan.MD § 3, a new permission key) — still queued; S017 lets IT admin
  do it.
- Correcting a ticket's event time after the raise — S018 decides.

## 2. Standards and practice

- **EN 13460 (maintenance documentation)** names the **work request**: what is
  wrong, where, how urgent, who asks. Once maintenance takes it up, the same
  record becomes the **work order** (S018). *Maintenance request* is this
  project's word for the work request (Plan.MD § 4.2); *ticket* is the record
  in Yantra. One table, not two: the record of the event stays in one place.
- **ISO 14224 (reliability and maintenance data)** lists what a failure record
  holds: the item (our machine and component, levels 6–8 of its taxonomy), the
  **failure date** (our event time), the **failure mode** (our symptom), the
  **failure impact** (our intensity: critical / degraded / incipient, with the
  plain word *initial*), and the **detection method** — *how* the failure was
  found (operator observation, periodic maintenance, condition monitoring),
  not who; derived later from `source` (§ 1 Out of scope). Failure mode is
  ISO's core field; it is optional at raise by the user's decision and
  required at close (S018), so every closed ticket still carries it.
- **EN 13306 (maintenance terminology)**: a **failure** is an **event** — the
  loss of the ability to perform as required; a **fault** is the **state** of
  the item after a failure, when it cannot perform. Running with reduced
  function is a **partial failure** (a degraded state). So: *critical* = a
  failure, the item is in a fault state (a breakdown); *degraded* = a partial
  failure; *initial* = ISO 14224's *incipient* impact, early signs. Only
  critical time is **downtime** (computed in S018).
- **TPM — autonomous maintenance**: the operator who finds an abnormality
  (*fuguai*) hangs a **tag** on it. The ticket is that tag. *Reported by* is
  TPM's operator ownership (not an ISO 14224 field): it keeps the operator's
  name on the tag even when the supervisor types it, which is why phone-less
  operators must be nameable (user decision 5). Showing open tickets before
  raising is the tag board: look first, then tag.
- **SMRP metrics** (response time, MTTR, MTBF) are measured from these
  records; this step stores the first timestamps they need (event time, raise
  time).
- **ISO 27001**: ticket photos are served only through permission-checked
  routes (A.8.3, information access restriction, as S006). The people picker
  shows names only, and only at a site where the user may raise (A.5.15
  access control, least privilege).
- **ISO 55001 § 8 / asset disposal**: scrapping is a controlled step; an open
  ticket on scrapped equipment could never be closed (a scrapped record is
  read-only), so the scrap waits until its tickets are closed.

## 3. Where

### Backend
- **`backend/local_db.py`** — migration **v12** "Tickets": tables `tickets`
  and `ticket_events` (§ 4.1), and a third owner on `equipment_documents`
  (§ 4.2). Every statement safe to run twice (as v9).
- **`backend/config_rbac.py`** — keys **`ticket:read`** and **`ticket:raise`**
  (§ 5.6), both added to `SITE_SCOPED`; **`NO_LOGIN_ROLES =
  (TECHNICIAN_ROLE, "maint_operator")`**, the roles a person without a login may
  hold (§ 5.9), so `config_rbac.py` stays the single source of roles;
  `TECHNICIAN_ROLE` keeps only its "the one role an engineer may give" meaning
  and its comment says so (BR2-06). The new keys' comment names user
  decision 7 (IT admin holds them, a departure from "not maintenance work"),
  and the `ROLE_INCLUDES` comment on `it_admin` is adjusted to match (BS1-02).
- **`backend/tickets_core.py`** (new, pure; no DB, no clock):
  - `INTENSITIES`, `BREAKDOWN_INTENSITY = "critical"`, `STATES`,
    `OPEN_STATES`, `FUTURE_SKEW`, `MAX_BACKDATE_DAYS`;
  - `format_ticket_serial(year, month, number)` → `TK-2026-10-001`, three
    digits growing to four past 999 (the equipment-code rule);
  - `serial_scope(year, month)` → `TK:2026-10`;
  - `parse_event_time(text)` → a naive datetime or an error (§ 5.1);
  - `event_time_error(event_time, now, not_before=None)` → the window check
    of § 5.1 (S018 reuses it with `not_before` = the last event's time);
  - `validate_raise(body, now)` → the cleaned fields or field errors:
    intensity, description length, ids, the event time (§ 5.1). Called before
    the transaction, as every route's `clean_body`;
  - `description_error(description, mode_code)` → the message or None: the
    description-required rule, called **in the transaction** once the mode row
    is read (`mode_code` None when no mode) (BR1-06);
  - `machine_and_component(node)` → `(machine_id, component_id)` from the
    node's own `level`, `parent_id` and `gp_id` (the tree is at most two steps
    deep), so tickets.py needs no private equipment.py helper (§ 5.2, BR2-08).
- **`backend/db_helpers.py`** — **`next_counter(cur, scope) -> int`**,
  extracted from `equipment._next_code` (the `INSERT … ON DUPLICATE KEY UPDATE`
  and read-back, in the caller's transaction). `_next_code` and the raise both
  call it (DRY, BR1-09).
- **`backend/tickets.py`** (new blueprint `/api/tickets`, thin shell): the
  routes of § 6; the access predicate of § 5.3, used by the list, the detail
  and documents.py's ticket owner; the raise transaction of § 5.4. **Import
  direction**: documents.py imports the ticket owner's read / lock functions
  from tickets.py; tickets.py never imports documents.py, so there is no import
  circle (BR2-08). The people picker sits on a helper `_people_at_site(cur,
  site_id)`, written site-first so S018 can anchor it on a ticket (§ 6).
- **`backend/documents.py`** — the `Owner` dataclass generalised and a third
  owner `"ticket"` (§ 5.5):
  - `Owner` gains `read_key`, `write_key`, `purge_key` and `kinds`; the
    route-level `@require_perm("equipment:…")` literals are replaced by
    `@require_perm`-equivalent checks on `OWNERS[owner].<key>` inside each
    route (a helper `_require_owner_key(owner, which)` raising the same 403),
    and the owner's key is passed to `read_for_change`, `lock_for_change` and
    `lock_for_purge`. Equipment and model keep exactly today's keys, now as
    data;
  - a kind outside `kinds` → `400 {field: "kind"}` before the file is checked
    and written (`request.form` has already spooled the body; BR2-08);
  - the removed-documents list gains a third `UNION ALL` branch for tickets
    and `_removed_item` a ticket shape (§ 5.5).
  The module docstring's "one owner lock, node or model" paragraph names the
  third owner, the ticket row (lock 7) (BS1-03).
  The documents blueprint is registered at `/api` and spells out each owner's
  path, so `/api/tickets/<id>/documents` lives in documents.py while
  `tickets_bp` takes `/api/tickets`; Flask matches the longer rule, no clash.
- **`backend/file_store.py`** — `_OWNER_FOLDERS` gains `"ticket": "tickets"`.
- **`backend/equipment.py`**:
  - `_next_code` calls `next_counter` (no behaviour change);
  - the scrap path refuses a node with open tickets (§ 5.8);
  - the module docstring's lock-order note gains the ticket row, its place,
    and the two accepted deadlocks of § 5.4; its documents paragraph ("one
    owner lock, node or model") names the ticket row too (BS1-03).
- **`backend/masters_core.py`** — `no_login_role_error` checks against
  `config_rbac.NO_LOGIN_ROLES` (Technician **or Operator** without a login);
  its docstring and `NO_LOGIN_ROLE_MESSAGE` ("Without a login, a person can
  only be a technician or an operator") follow (§ 5.9). `technician_only`
  unchanged.
- **`backend/masters.py`** —
  - updating a failure mode refuses a code change when a ticket uses the mode:
    `409 {error, field: "code"}` (§ 5.7); `update_failure_mode`'s pre-read
    (`SELECT class_id …`) gains `code` so "the code changes" can be told, and
    the S016 section comment and route docstring ("nothing references them
    yet") are updated (BS1-01);
  - no code change for § 5.9 beyond what `no_login_role_error` decides (both
    call sites, the person-level check and the site-row check, already use
    it).
- **`backend/app.py`** — register `tickets_bp`.

### Frontend
- **Router:** `/tickets` → `views/TicketsView.vue`; `/tickets/new` →
  `views/RaiseTicketView.vue` (query `equipment=<id>` when opened from an
  equipment page); `/tickets/:id(\d+)` → `views/TicketDetailView.vue`. The
  router guards nav items only (`canOpenRoute`); for `/tickets/new` and
  `/tickets/:id` the **API's 403 / 404 is the gate**, and the buttons that
  lead there are hidden by permission (BR1-10).
- **Sidebar:** *Tickets* after *Equipment*, `perm: "ticket:read"`.
- **`views/TicketsView.vue`** (new) — the list, filters in the query string
  (as the equipment list), `PagerBar`, **Raise ticket** button
  (`ticket:raise`).
- **`views/RaiseTicketView.vue`** (new, phone first):
  - equipment picker when no `equipment` in the query (search by code or name
    among the user's units, the existing equipment list endpoint);
  - intensity as three large buttons; symptom select (modes for the machine,
    § 6); description; event time (`<input type="datetime-local">`, showing
    the phone's now); reported by (select from `GET /api/tickets/people`,
    optional);
  - **`occurred_at` is sent only when the user changed the field**; untouched,
    it is left out and the server's clock is the default (§ 5.1). A phone a few
    minutes fast then never gets a 400 for a time nobody typed (BR2-05; the
    same rule as S018's move dialogs);
  - the machine's open tickets above the Save button (§ 1): `GET
    /api/tickets?equipment_id=<machine>&state=open`, with the **machine's** id
    — on a component node, `ancestors[0].id` of the node detail (BR2-08);
  - after Save: the photo picker — `accept` = S006's photo types
    (`image/jpeg,image/png,image/webp`, the `ACCEPT.photo` list of
    `DocumentUploadModal`, moved to a shared export) and S006's iPhone hint;
    **no `capture`**, so a phone offers the camera and the gallery (S006's
    choice; the operator may have taken the photo already). Each photo is
    uploaded to the ticket's documents with the **file name without its
    extension** as title (as `DocumentUploadModal` pre-fills). Then **Done**
    opens the ticket page.
- **`views/TicketDetailView.vue`** (new) — the page of § 1; photos through
  `components/documents/DocumentsCards.vue` with the ticket's documents path.
- **`components/documents/DocumentsCards.vue`** — a `photosOnly` prop: no
  Documents card, no *Add document* (BR1-01).
- **`components/documents/DocumentUploadModal.vue`** — `ACCEPT` exported for
  reuse; with `photosOnly` the Kind radio is hidden and the kind is `photo`
  (a ticket would refuse a document with 400 after the pick; BR2-07).
- **Settings › Removed documents** (`RemovedDocuments.vue`) — one more
  `v-if` for the ticket shape (serial and unit); *Restore* disabled with a
  title when the ticket is closed, as for a scrapped node (BR1-05, BR2-07).
- **`views/EquipmentDetailView.vue`** — *Open tickets* section and *Raise
  ticket* button, each rendered from the node detail's `permissions` (the
  user's keys at the node's site, `permissions_at_site`): the section only
  when `ticket:read` is in it, the button only when `ticket:raise` is and the
  node is not scrapped. The storekeeper, who holds neither key, sees
  neither — no 403 on their equipment pages (BR2-04).
- **`views/masters/PeoplePanel.vue`** — the site-row role select for a person
  without a login: **IT admin** is offered Technician or Operator; an
  **engineer** is offered Technician only, as today (§ 5.9, BR2-06).
- **`components/IntensityBadge.vue`** (new) — critical red "Breakdown",
  degraded amber "Defect", initial grey "Defect · initial".
- **`utils/ticketLabels.js`** (new, pure) — intensity and state labels, age
  text ("3 h", "2 d"), `isBreakdown(intensity)`.

### Tests
- `backend/tests/test_tickets_core.py` (new) — § 8.
- `backend/tests/test_tickets_api.py` (new) — § 8.
- `backend/tests/test_migration_v12.py` (new) — tables, the documents owner
  CHECK and its name, re-run; v9 re-run on top of v12 leaves the three-owner
  CHECK alone (BR2-01).
- `backend/tests/test_rbac.py` — the two keys in the role matrix.
- `backend/tests/test_failure_codes_api.py` — the mode code freeze.
- `backend/tests/test_documents_api.py` (the S006 module) — ticket owner:
  upload, list, serve, title, remove, kind refused, access; node and model
  tests unchanged (same keys, now data).
- `backend/tests/test_removed_documents_api.py` (S008) — the ticket branch:
  listed, restored, purged, scoped by the ticket's unit.
- `backend/tests/test_equipment_api.py` (or the S002 module) — scrap refused
  with an open ticket on the node or below; allowed once closed (a row set to
  closed in the test).
- `backend/tests/test_masters_core.py`, `backend/tests/test_site_roles_api.py`
  — the no-login rule: Operator now accepted, supervisor / engineer / manager
  still refused; the assertions that expected "operator → 400" flip;
  `TestNoLoginTechnicianOnly.test_other_roles_are_400` splits as § 8 says
  (BR2-06).
- `backend/tests/conftest.py` — clean-up of tickets, their events and
  documents; `Uniq` helpers if needed.
- `frontend/tests/ticketLabels.test.js` (new).

### Docs (at approval, by the planner)
- `docs/Plan.MD` § 3 (keys `ticket:*` replace `breakdown:*`; a person without
  a login may be Technician or Operator, set by IT admin), § 4.2 (prefix `TK-`,
  symptom optional at raise, "not fixed" = new ticket), § 4.1 (scrap refused
  with open tickets), § 5 (`tickets`, `ticket_events` replace `breakdowns`,
  `breakdown_events`; the `attachments` row removed — ticket photos are in
  `equipment_documents`), § 9 Q4.
- `docs/Maintenance-Philosophy.md` glossary: work request, work order,
  ticket, intensity, partial failure.
- `docs/steps/S011-site-roles/1-brief.md` — a note under its gate A that S017
  changed "without a login, only a technician" (user, 20-10-2026).
- `docs/steps/README.md` › Queued — the row "Supervisors and engineers create
  operators without a login at their own site" was added at round 2 (BR2-08),
  so the "still queued" of § 1 Out of scope has a home.

## 4. Data model (migration v12)

### 4.1 New tables

**`tickets`**

| Column | Type | Notes |
|---|---|---|
| `id` | INT PK | |
| `serial` | VARCHAR(16) NOT NULL | UNIQUE `uq_tickets_serial` |
| `equipment_id` | INT NOT NULL | FK `fk_tickets_equipment`; always the **machine** (level `equipment`) |
| `component_id` | INT NULL | FK `fk_tickets_component` → `equipment`; a component-unit or component under the machine, or NULL |
| `unit_id` | INT NOT NULL | FK `fk_tickets_unit`; the machine's unit **when raised** (§ 5.3) |
| `intensity` | ENUM('critical','degraded','initial') NOT NULL | declared in this order, so `ORDER BY intensity` puts critical first |
| `state` | ENUM('raised','acknowledged','in_progress','back_in_service','closed') NOT NULL DEFAULT 'raised' | the full S018 set now, so S018 adds no ENUM change; S019 adds `scheduled` |
| `failure_mode_id` | INT NULL | FK `fk_tickets_failure_mode` |
| `description` | VARCHAR(1000) NULL | |
| `reported_by_id` | INT NULL | FK `fk_tickets_reported_by` → `people` |
| `occurred_at` | DATETIME NOT NULL | the event time entered (IST naive) |
| `source` | ENUM('manual') NOT NULL DEFAULT 'manual' | widened when other sources come |
| `created_at`, `created_by`, `updated_at`, `updated_by` | | as every table; `created_by` is who raised |

Indexes: `ix_tickets_unit_state (unit_id, state)` for the list,
`ix_tickets_equipment_state (equipment_id, state)` for the equipment page,
`ix_tickets_component_state (component_id, state)` for the component page and
the scrap check.

**`ticket_events`** — the timeline; S018's response, repair and downtime
figures come from here.

| Column | Type | Notes |
|---|---|---|
| `id` | INT PK | |
| `ticket_id` | INT NOT NULL | FK `fk_ticket_events_ticket` |
| `event` | VARCHAR(30) NOT NULL | `raised` in S017; S018 adds its events. Text, not ENUM, as `equipment_events.event` |
| `from_state` | VARCHAR(20) NULL | |
| `to_state` | VARCHAR(20) NULL | |
| `occurred_at` | DATETIME NOT NULL | the event time entered |
| `intensity` | ENUM('critical','degraded','initial') NULL | the intensity set by this event: the raise's on `raised`; S018's re-grades. NULL when unchanged. S018's downtime is computed from it |
| `person_id` | INT NULL | FK `fk_ticket_events_person` → `people`: the person the event names (S018: the technician who did the work). NULL on `raised`: the reporter is on the ticket (`reported_by_id`), not repeated here (BR2-08) |
| `remark` | VARCHAR(1000) NULL | |
| `created_at`, `created_by` | | when and by whom it was recorded |

Index `ix_ticket_events_ticket (ticket_id, occurred_at, id)`.

### 4.2 `equipment_documents` gains a ticket owner

- `ADD COLUMN IF NOT EXISTS ticket_id INT NULL AFTER model_id`, its FK
  `fk_equipment_documents_ticket` and index `ix_equipment_documents_ticket
  (ticket_id, removed_at)`.
- The v9 CHECK `chk_equipment_documents_owner` (exactly one of
  `equipment_id`, `model_id`) is dropped and re-added **under the same name**
  as exactly one of the three: `DROP CONSTRAINT IF EXISTS
  chk_equipment_documents_owner`, then `ADD CONSTRAINT IF NOT EXISTS
  chk_equipment_documents_owner CHECK ((equipment_id IS NOT NULL) + (model_id
  IS NOT NULL) + (ticket_id IS NOT NULL) = 1)`. Keeping the name matters:
  `test_migration_v9.py` re-runs v9 on the test database, and v9's `ADD
  CONSTRAINT IF NOT EXISTS chk_equipment_documents_owner` is then a no-op; under
  another name it would put the two-owner rule back beside the new one, and
  every ticket photo insert after it would fail with 4025 (BR2-01).
- Ticket photos then get S006's checks (file type from the first bytes, size
  limit, thumbnail), S008's restore and purge from Settings, and serving only
  through permission-checked routes, with no second upload path (§ 7
  decision 4).

### 4.3 Serial counter

`serial_counters` row `TK:YYYY-MM`, from the IST **raise** date (not the event
time): the serial says when the ticket was written; one counter per month, as
`PM-` will be. Bumped through `next_counter` (§ 3).

## 5. Rules

### 5.1 Raising

`validate_raise(body, now)`, before the transaction:
- `intensity` required, one of the three.
- `description` up to 1000 characters, trimmed (empty → NULL).
- `equipment_id` required; `failure_mode_id`, `reported_by_id` optional ids.
- `occurred_at` optional, default `now` (the server's clock). The raise
  screen sends it **only when the user changed the field** (BR2-05), so the
  default is the server's time, not the phone's. **Wire format** (BR1-06): an IST
  local time `YYYY-MM-DDTHH:MM` or `YYYY-MM-DDTHH:MM:SS`, `T` or a space
  between date and time — what `<input type="datetime-local">` sends. A value
  with an offset or `Z` is refused, `400 {field: "occurred_at"}`, so a phone's
  time zone can never shift it. Stored IST naive (base § Timezone policy).
  `now` is `datetime.now(IST)` made naive, as `equipment.IST` is used today.
- **The window** (`event_time_error`): refused when more than `FUTURE_SKEW`
  (5 minutes; phone clocks drift) in the future, or more than
  `MAX_BACKDATE_DAYS` (7) in the past — "When did it happen? Up to 7 days back"
  (a late entry at the end of a shift is fine; history from notebooks is out of
  scope, Plan.MD § 2).

In the transaction, once the rows are read:
- `failure_mode_id`, when given, must be active and General or of the
  **machine's** class (S016 § 5.4: checked in the API, on the machine even
  when the ticket is on a component; the operator does not know the
  component's class) — `400 {field: "failure_mode_id"}`.
- `description_error(description, mode_code)`: the description is
  **required** when no mode is given or the mode is `OTH` — "Description is
  needed when no symptom is picked" — `400 {field: "description"}`.
- `reported_by_id`, when given: an **active person with a membership at the
  ticket's site** (the site of the machine's unit). With user decision 5 that
  includes operators without a login. `400 {field: "reported_by_id"}`.

### 5.2 Machine and component

The request names one node, `equipment_id`. The server walks up (at most two
steps, the tree's depth):
- a node of level `equipment` → machine = it, component = NULL;
- a component-unit or component → machine = its level-6 ancestor, component =
  the node.

`machine_and_component(node)` reads this from the node's own `level`,
`parent_id` and `gp_id` (the node fragment's columns), not from equipment.py's
private `_ancestors`.

A component later **re-parented** to another machine keeps the ticket's stored
`equipment_id`, as the unit is kept (§ 5.3): the ticket records where the
failure was. S018's edit rule ("a node under the ticket's machine") refers to
that stored machine (BR2-08).

A **scrapped** node is refused (409, "Scrapped equipment takes no tickets").
A node under a scrapped machine cannot occur through the API (a machine is
scrapped only after all its parts, `_check_parts_scrapped`); the machine's
status is still re-read and checked as defence in depth. Standby and
out-of-use equipment can take tickets: a standby pump found leaking is a
defect.

### 5.3 Unit and access

- `tickets.unit_id` is the machine's unit **at raise**, kept when the machine
  later moves: the failure happened there, and the tickets of a unit stay with
  that unit's team (ISO 14224 records the location of the failure event).
- **One access predicate** for the list, the detail and the ticket's documents
  (BR1-04): a ticket is visible when its `unit_id` **or** its machine's
  current unit is among `accessible_unit_ids(cur, "ticket:read")`:
  `t.unit_id IN (…) OR m.unit_id IN (…)`, with `JOIN equipment m ON m.id =
  t.equipment_id` (the machine is level 6, one join). `None` (admin) means
  every ticket; an empty set gives an empty list with no query. So the
  equipment page lists a moved machine's tickets wherever it now stands, and
  the old unit's team still sees them. A ticket outside the predicate is 404,
  as equipment is.
- **Order**, in SQL (the list is paginated, so the order cannot be applied in
  Python per page): `state=open` → `ORDER BY t.intensity, t.occurred_at,
  t.id` (the ENUM's declared order puts critical first); `closed` and `all` →
  `ORDER BY t.occurred_at DESC, t.id DESC`.
- `ticket:raise` is checked **at the machine's site** (`require_perm_at`), after
  the node's unit-access check (`load_node_for_user`). "The ticket's site" in
  every later check is the site of `tickets.unit_id`.

### 5.4 The raise transaction and lock order

`validate_raise` runs first (no transaction). Then one transaction:
1. lock the **node** (1), via `load_node_for_user(cur, id, for_update=True,
   key="ticket:raise")` — 404 / 403 decided there, scrapped decided from the
   locked row; when the node is below the machine, the machine row is read
   plain (ancestors are never locked, equipment.py's rule) and its status
   checked;
2. read the mode (plain read of `failure_modes`) and check it and
   `description_error`; read and check the person;
3. bump the **serial counter** (6) with `next_counter`, in the caller's
   transaction, so a failed raise leaves no gap;
4. insert the ticket, then its `raised` event (`occurred_at` and `intensity`
   = the ticket's).

**Lock order** (equipment.py docstring and tickets.py): **(1) node → (6)
serial counter → (7) ticket row**. Ticket rows are locked only by tickets.py
and documents.py, always last; nothing that holds a ticket lock then takes an
equipment, unit or counter lock.

**Shared locks from the foreign keys** (BR1-03). The ticket insert takes
shared locks on the rows its FKs point at: the machine's `equipment` row, the
`units` row, the `people` row and the `failure_modes` row. Two deadlocks
follow, both **accepted and documented** in the lock-order notes of
equipment.py and tickets.py, as equipment.py already records "the one
accepted deadlock" for the scrap check:
- **scrap the machine vs raise on its part**: scrap locks the machine (1), then
  its parts `FOR UPDATE`; a raise on a part holds the part (1) and its insert
  waits for a shared lock on the machine. With § 5.8 a scrap of a machine
  whose part is being ticketed would be refused anyway; the race only decides
  which of the two fails;
- **a person's site-row edit vs a raise naming that person**: the site-row
  write locks the person, then the units; the insert's FK checks take unit,
  then person.

InnoDB detects both and rolls one back (error 1213). The backend has no
1213 → 409 mapping today (only the worker treats it as a task failure), so it
surfaces as a 500; accepted as rare (two people acting on the same machine or
person within the same second), and no new infrastructure is built for it.
The plain read of the mode in step 2 is not race-free against a
**deactivation** of that mode, and need not be: an inactive mode stays on the
tickets that already use it (S016 § 1.5). A **code change** of the mode is
race-free: masters locks the mode row `FOR UPDATE` and the insert's FK shared
lock queues behind it (§ 5.7).

### 5.5 Photos: the third documents owner

`Owner` (documents.py) carries its keys and kinds as data (BR1-01):

| Owner | `read_key` (list, file, thumb) | `write_key` (upload, title, remove) | `purge_key` (restore, purge) | `kinds` |
|---|---|---|---|---|
| `equipment` | `equipment:read` | `equipment:edit` | `equipment:purge_documents` | document, photo |
| `model` | `equipment:read` | `equipment:edit` | `equipment:purge_documents` | document, photo |
| `ticket` | `ticket:read` | `ticket:raise` | `equipment:purge_documents` | photo |

- Each route checks `OWNERS[owner].<key>` held at any site (the route-level
  check `require_perm` did), then the owner's read / lock function checks it at
  the record's site, as today for nodes. Equipment and model behave exactly as
  now.
- **Ticket read**: the ticket by the access predicate of § 5.3 (404
  otherwise).
- **Ticket read for change** (the plain pre-check `upload_document` runs
  before the file is checked and written) and **ticket lock for change** (in
  the write transaction) decide in the node's order (BR2-02):
  1. the access predicate of § 5.3 → **404** (a user with `ticket:raise` at
     the site but no access to the ticket's units cannot write to a ticket he
     cannot open);
  2. `write_key` at the ticket's site (the site of `tickets.unit_id`) →
     **403**;
  3. a **closed** ticket → **409** "This ticket is closed": upload, title edit,
     remove and **restore** are refused (restore goes through
     `lock_for_change`, as a scrapped node's does today; BR2-07). The
     equivalent of the scrapped rule.

  `read_for_change` decides from a plain read; `lock_for_change` locks the
  ticket row (7) `FOR UPDATE` and decides from the locked row. S017 never
  closes a ticket, so the closed rule is written now and tested with a row set
  to closed.
- **Ticket lock for purge**: lock the ticket row; `purge_key` at the ticket's
  site; **no** closed check (erasing is disposition of information, not a
  change to the record, S008 § 5.3 — as the node purge skips the scrapped
  check).
- **Kind**: a kind outside the owner's `kinds` → `400 {field: "kind"}`, before
  the file is checked and written. A ticket takes photos only; a vendor's PDF
  is open question 3.
- **Removed documents** (Settings, S008): a third `UNION ALL` branch joins
  `tickets` → `units` → `sites`, scoped by the ticket's unit to
  `accessible_unit_ids(cur, "equipment:purge_documents")` as the node branch
  is; item shape `{owner: "ticket", name: <serial>, unit: <SITE.UNIT>,
  full_path: null, state: <ticket state>}`. `RemovedDocuments.vue` shows it
  with one more `v-if` and disables *Restore* with a title when `state` is
  `closed`, as it does for `status === 'scrapped'` (BR2-07).
- Removal hides the photo (S006); restore or purge from Settings (S008).
- Files under `file_store`'s `tickets/` folder.

### 5.6 Permissions

| Key | operator | supervisor | technician | engineer | manager | it_admin |
|---|---|---|---|---|---|---|
| `ticket:read` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `ticket:raise` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

Granted to `maint_operator`: the ladder (technician → engineer → manager) and
the supervisor inherit it. Both in `SITE_SCOPED`. **IT admin holds both
(user decision 7)**: `it_admin` is a token role, so it holds them at every
site and unit (`every_unit_by_token`, as `equipment:edit`), with no
membership needed; it raises from the office network only (S013 gate). This
departs from Plan.MD § 3 ("maintenance work is not IT admin's") and is
recorded there at approval. Every IT admin action is an event with its user,
so the trail stays complete (ISO 27001 A.8.15 logging). The storekeeper holds
neither (no v1 work). These replace Plan.MD's first-cut `breakdown:raise`.

### 5.7 Failure-mode code frozen once in use

`PUT /api/masters/failure-modes/<id>` (S016) locks the mode row, then — if the
code changes — counts tickets with that `failure_mode_id`; one or more →
`409 {error: "This code is used by tickets and can no longer change", field:
"code"}`. Label, description and active stay editable (a relabel corrects the
words, the code keeps the meaning; S016 § 5.4). The class is already fixed
after create (S016). The lock on the mode row and the FK's shared lock on
ticket insert make the check race-free.

### 5.8 Scrapping with open tickets (user decision 6)

equipment.py's scrap path, after its existing locks (the node (1), then the
subtree top-down in `_check_parts_scrapped`), counts tickets **not closed**
whose `equipment_id` or `component_id` is the node or one of its locked
descendants; one or more → `409 {error: "Close its tickets first"}`. Race
with a raise: the raise locks its node (1) before it inserts, and the scrap
holds that node's lock (the node itself, or a descendant locked top-down)
while it counts. Whichever locks the node first wins: a raise that got there
first has committed its ticket before the scrap's lock is granted, so the
scrap sees it and refuses; a scrap that got there first commits, and the
raise then sees a scrapped node and refuses (§ 5.2). The deadlock of § 5.4
(raise on a part vs scrap of its machine) is the one case where InnoDB picks
the loser instead.

### 5.9 Operators without a login (user decision 5)

- `masters_core.no_login_role_error` accepts the roles in
  `config_rbac.NO_LOGIN_ROLES` (`maint_technician` **and** `maint_operator`)
  for a person without a login; any other role is refused with "Without a
  login, a person can only be a technician or an operator" (BR2-06).
- Who may write the row is unchanged: IT admin (`masters:edit`) any role;
  engineers (`people:assign_technicians`) Technician only (`technician_only`
  unchanged). So an Operator row without a login is set by IT admin. An
  engineer asking for an Operator row now gets **403** "Only IT admin can set
  this role" (today 400, because the no-login check ran first and refused
  Operator; now Operator passes it and the engineer check answers).
- An Operator row without a login grants nothing (no login, no access); it
  places the person at the site's units for pick-lists (*reported by* here;
  S018's labour and assignees use the same people list).
- The Team dialog (`PeoplePanel.vue`) offers Operator in the role select for a
  person without a login **to IT admin only**; an engineer is offered
  Technician alone, as today.
- This changes the S011 A1 gate-A decision; Plan.MD § 3 already describes it
  ("A person without a login can be a Technician **or an Operator**"), so the
  plan and the code agree again. Supervisors and engineers creating such
  operators at their own site (a new key) stays queued (README › Queued row
  added at round 2, BR2-08).

## 6. API

| Method | URL | Key | Does |
|---|---|---|---|
| GET | `/api/tickets` | `ticket:read` | List; query `site_id`, `unit_id`, `equipment_id` (a machine → its tickets, `t.equipment_id = id`; a component-unit or component → the tickets **raised on that node itself**, `t.component_id = id`, not those on its components — the page shows what was raised there; BR2-08), `intensity` (`breakdown` / `defect` / one of the three), `state` (`open` default / `closed` / `all`), `q`, `page`, `per_page`. Returns `{items, total, page, per_page}` |
| POST | `/api/tickets` | `ticket:raise` | Raise; body `{equipment_id, intensity, failure_mode_id?, description?, occurred_at?, reported_by_id?}` → 201 with the ticket |
| GET | `/api/tickets/<id>` | `ticket:read` | The ticket, its timeline, `can_add_photos` |
| GET | `/api/tickets/modes?equipment_id=<node>` | `ticket:raise` | Symptoms for the node's machine: its class's active modes, then General ones, by label |
| GET | `/api/tickets/people?equipment_id=<node>` | `ticket:raise` | Active people with a membership at the node's **current** site, by name, with their trades `[{id, name}]` and their **role at that site** — the one people picker. S017 anchors it on `equipment_id` only; **S018 adds a `ticket_id=` anchor** to the same endpoint (the ticket's site, the site of `tickets.unit_id`, which differs after a cross-site move) and owns that change; the helper `_people_at_site(cur, site_id)` is site-first for it (BR2-08) |
| GET/POST/PUT/DELETE | `/api/tickets/<id>/documents…` | as § 5.5 | documents.py, third owner |

`/api/tickets/modes` is kept although S016 has `GET
/api/masters/failure-modes?class_id=N`: the raise screen knows a **node**,
and a component's detail does not carry its machine's `class_id`
(`_ancestors` gives id, code, level, name); the endpoint resolves the machine
on the server (from the node's `level` / `parent_id` / `gp_id`, § 5.2) and
applies the same unit-access check as the raise.

A ticket in the API: `id, serial, state, intensity, is_breakdown, occurred_at,
created_at, created_by, machine {id, code, name, class_code}, component {id,
code, name} | null, unit {id, code, site_code}, failure_mode {id, code, label}
| null, description, reported_by {id, name} | null`. The detail adds `events:
[{event, from_state, to_state, occurred_at, intensity, person, remark,
created_at, created_by}]`, oldest first (`intensity` as stored, null when
unchanged; S018 shows re-grades from it).

The equipment page uses `GET /api/tickets?equipment_id=<id>&state=open`.

`current_person_id(cur)` (the Team person whose login is the user's) is not
needed by S017; S018 owns it.

## 7. Design decisions

| # | Decision | Reason | Rejected alternative |
|---|---|---|---|
| 1 | **One `tickets` table** for breakdowns and defects; breakdown = critical intensity | Plan.MD § 4.2; a defect re-graded keeps its record | Separate breakdown and defect tables (a re-grade would move rows) |
| 2 | **`ticket:*` keys, `tickets` tables** instead of the plan's `breakdown:*` / `breakdowns` | The plan left the names to this brief; a defect is not a breakdown | Keep `breakdown` names (misleading for two thirds of the intensities) |
| 3 | **Machine and component in two columns**; raise from any node | Reports by machine stay one column; chronic problems per component (Plan.MD § 4.6); the operator scans whatever label is nearest | One `node_id` (every machine report would walk the tree) |
| 4 | **Ticket photos in `equipment_documents`** as a third owner, with each owner's keys and kinds as data | One upload path with S006's checks, S008's restore/purge, no second file store (DRY); the owner pattern exists (S012); keys as data let raisers upload without `equipment:edit` | A new `attachments` table (Plan.MD § 5 sketch): a second copy of upload, thumbnails, serving and purge; or separate photo routes in tickets.py (a second upload path) |
| 5 | **Unit kept at raise; visible through the old or the current unit** | The failure belongs to where it happened; history stays with the unit's team; the equipment page still shows a moved machine's tickets | Follow the machine's current unit only (a moved press would take its old tickets away from the old team) |
| 6 | **Serial from the raise date, monthly counter** | The plan's `YYYY-MM-NNN`; the serial says when it was written | From the event time (a back-dated ticket would take a number from a closed month) |
| 7 | **Full state ENUM now** | S018 adds no schema change to `state` | Add states as S018 needs them (one more ALTER on a growing table) |
| 8 | **Warn on open tickets, don't block** | Two faults on one machine are real; the list shows the first | Block a second open ticket per machine (forces unrelated faults into one record) |
| 9 | **Back-dating capped at 7 days; local time only on the wire** | A shift-end entry is covered; old notebook history is out of scope and would distort this month's figures; refusing offsets keeps one time zone | No cap (typos like a wrong year go into MTBF); accepting offsets (a phone set to another zone shifts the time) |
| 10 | **Scrap refused while tickets are open** (user) | A scrapped record is read-only, so an open ticket on it could never be closed | Allow, and let S018 close tickets on scrapped equipment |
| 11 | **Operator rows without a login, set by IT admin** (user) | The phone-less operator who found the fault can be named (TPM ownership); one people list for reporter, assignees, labour | Any active person in Team (mixes sites); defer (the use case not served) |
| 12 | **Two FK-lock deadlocks accepted and documented** | Rare (same machine or person in the same second); the database resolves them; the scrap check already accepts one | Lock top-down from the machine on every raise (more code, a second read of the parent after locking) |

## 8. Tests and acceptance

### Pure (`test_tickets_core.py`)
- serial: `TK-2026-10-001`, `-999`, `-1000`; scope text;
- `parse_event_time`: with `T`, with a space, with seconds, without; an offset
  or `Z` refused; garbage refused;
- `event_time_error`: default, +4 min accepted, +6 min refused, 7 days back
  accepted, 8 refused; `not_before` refuses an earlier time (for S018);
- `validate_raise`: each intensity; missing intensity; description too long;
  missing `equipment_id`;
- `description_error`: required with no mode and with `OTH`, optional with
  another mode;
- `machine_and_component` for the three levels (component-unit under a
  machine, component under a component-unit, component straight under a
  machine).

### API (`test_tickets_api.py`)
- raise on a machine, on a component-unit, on a component → machine and
  component stored; serial issued; `raised` event written with the event
  time and the intensity; `created_by` the user;
- two raises in one month → consecutive serials; a raise that fails **after**
  the counter bump (the ticket insert monkeypatched to raise inside the
  transaction) leaves no gap: the next raise takes the next number;
- refusals: scrapped node 409; a machine set scrapped by a raw `UPDATE`
  (through the test's connection) with an in-service part → raise on the part
  409; node outside the user's units 404; `ticket:raise` not held at the site
  403; mode of another class 400; inactive mode 400; reporter from another
  site 400; description missing with no mode 400; `occurred_at` with an
  offset 400;
- a General mode on any machine is accepted; an operator without a login is
  accepted as reporter;
- a raise without `occurred_at` gets the server's time (BR2-05);
- `equipment_id` filter: on a machine lists its tickets; on a component-unit
  lists only the tickets raised on that node (BR2-08);
- list: only the user's units; default open; filters; **order** (critical
  before degraded before initial, then oldest; closed newest first); a user
  with no units gets an empty list; admin sees all;
- a machine moved to another unit: its ticket is listed and opens for a user
  of the old unit and for a user of the new unit only; 404 for a user of
  neither;
- `modes` and `people` pickers (people with their trades, only the site's).

### Documents (`test_documents_api.py`, `test_removed_documents_api.py`)
- ticket photos: upload, list, file and thumb, title edit, remove by a raiser
  (an operator); a `document` kind on a ticket 400; closed ticket refuses
  upload, title, remove and restore (409); node and model tests unchanged;
- **read but not write** (BR2-03; every role holding `ticket:read` also holds
  `ticket:raise`, so no role has one alone): raise on a machine at unit U1
  (site A), move the machine as admin to U2 (site B); a user with an operator
  row at B only **reads** the ticket (the predicate's second door: the
  machine's current unit) but gets **403** on upload, title edit and remove
  (`ticket:raise` checked at the ticket's site, A);
- **access before key** (BR2-02): a user holding `ticket:raise` at the
  ticket's site but with chosen units that exclude the ticket's unit gets
  **404** on upload;
- removed list: a removed ticket photo listed for the manager of the ticket's
  unit, restored, purged; not listed for a unit outside the manager's access.

### Equipment (`test_equipment_api.py`)
- scrap refused with an open ticket on the node, and on a component below
  it; accepted when the ticket is closed (row set to closed in the test).

### Migration (`test_migration_v12.py`)
- tables and indexes exist; the documents CHECK is named
  `chk_equipment_documents_owner`, accepts each single owner and refuses none
  or two; re-run is harmless; re-running v9 afterwards leaves a ticket-photo
  insert working (BR2-01).

### RBAC (`test_rbac.py`)
- the role matrix rows gain `ticket:read` and `ticket:raise` as § 5.6
  (it_admin included, storekeeper not); both in `SITE_SCOPED`.

### Masters (`test_failure_codes_api.py`, `test_masters_core.py`, `test_site_roles_api.py`)
- a mode used by a ticket: code change 409; label change accepted; an unused
  mode's code still changes;
- no-login rule: Operator accepted, Supervisor refused with the new message;
  `TestNoLoginTechnicianOnly.test_other_roles_are_400` splits (BR2-06):
  admin + operator → 200; engineer + operator → **403** (today 400); the other
  roles → 400 with the new message.

### Frontend (`ticketLabels.test.js`)
- labels, `isBreakdown`, age text at minutes / hours / days.

### Manual checks
Important:
- [ ] On a phone: scan a QR label → equipment page → **Raise ticket** → pick
  critical, a symptom, take a photo (camera or gallery offered) → the ticket
  page shows it, with the thumbnail and the *raised* line in the timeline.
- [ ] As an operator of one unit, the Tickets list shows only that unit's
  tickets; a ticket URL of another unit gives "not found".
- [ ] As IT admin, give a person without a login an Operator row at a site;
  as a supervisor there, raise a ticket naming that person as *reported by*.

Plain:
- Raise a second ticket on the same machine: the open ticket is listed before
  Save.
- Raise with no symptom and no description → the description is asked for.
- Back-date by two days → the timeline shows that time, the serial this month.
- Try to scrap a machine with an open ticket → "Close its tickets first".
- Remove a ticket photo; Settings › Removed documents lists it under the
  ticket's serial.

### Acceptance
`tooling/run-tests.bat` green; `npx vite build` with no new errors.

## 9. Open questions and assumptions

1. ~~IT admin and storekeeper read tickets?~~ **Decided (user decision 7,
   20-10-2026):** IT admin gets full access to tickets; the storekeeper none
   for now (§ 5.6).
2. **Assumption:** reported-by is chosen from active people with a membership
   at the ticket's site; with user decision 5 that includes operators without
   a login, set by IT admin. A person who reports from another site cannot be
   named.
3. **Assumption:** only photos attach to a ticket in S017; a vendor's PDF
   report (Plan.MD § 4.2 parts use case) is S018's open question 2 (adding
   `document` to the ticket owner's `kinds` is then one line).
4. **Assumption:** the raise screen works in the phone browser; the PWA shell
   comes with S021.
5. **Assumption:** S016 is committed before S017 is coded (the failure-mode
   table and masters routes are S016's).

## 10. Amendments

(none)

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 20-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR1-01 documents routes hard-code the equipment keys | major | **Accepted** (option 1, planner): `Owner` gains `read_key` / `write_key` / `purge_key` / `kinds`; the key checked in the route from the owner and passed to the read / lock functions; kind outside `kinds` → 400; `file_store` gains `tickets`; `DocumentsCards` `photosOnly`. Key table in § 5.5; files in § 3 |
| BR1-02 reported-by relies on operators without a login | major | **Accepted** (option 1, **user decision 5**, 20-10-2026): a person without a login may hold Technician or Operator rows; only IT admin sets Operator; engineers unchanged; changes the S011 A1 gate-A decision. § 1, § 3 (masters_core, PeoplePanel, tests), § 5.9, § 8, assumption 2 |
| BR1-03 FK shared locks make two deadlocks | minor | **Accepted** (a): both documented as accepted in the lock-order notes; no 1213 → 409 mapping exists, so a rare 500 is accepted; mode deactivation race noted as harmless (§ 5.4, § 7 #12) |
| BR1-04 one unit rule for list and detail; order in SQL | minor | **Accepted**: one predicate (ticket's unit or machine's current unit) for list, detail and documents; `ORDER BY intensity, occurred_at, id` for open, newest first otherwise; `list_order_key` dropped; order tested in the API (§ 5.3, § 8) |
| BR1-05 removed documents, restore / purge, title edit for tickets | minor | **Accepted**: third removed-list branch scoped by the ticket's unit, ticket item shape, purge without the closed check, title edit by `ticket:raise` refused when closed; `test_removed_documents_api.py` added (§ 3, § 5.5, § 8) |
| BR1-06 `validate_raise` sequencing; event-time wire format | minor | **Accepted**: `validate_raise` before the transaction, `description_error(description, mode_code)` inside it; `occurred_at` as local `YYYY-MM-DDTHH:MM[:SS]` (T or space), offsets refused, stored IST naive, `now` = `datetime.now(IST)` naive (§ 3, § 5.1) |
| BR1-07 standards wording | minor | **Accepted**: EN 13306 failure (event) / fault (state) / partial failure; EN 13460 *work request*; ISO 14224 detection method, *reported by* moved to TPM; ISO 27001 A.8.3 and A.5.15 added (§ 2) |
| BR1-08 two API tests cannot be set up | minor | **Accepted**: gap test fails the insert after the bump (monkeypatch); the scrapped-machine case set up by a raw `UPDATE` (§ 8) |
| BR1-09 share the counter bump | nit | **Accepted**: `db_helpers.next_counter(cur, scope)`; `_next_code` and the raise call it (§ 3) |
| BR1-10 router guards nav items only | nit | **Accepted**: the API's 403 / 404 is the gate; buttons hidden by permission; *Raise ticket* hidden on scrapped nodes (§ 1, § 3) |
| BR1-11 photo picker `capture`, `accept`, title | nit | **Accepted**: no `capture`; S006's photo types via an exported `ACCEPT`; title = file name without extension (§ 3) |
| BR1-12 scrapping a machine with open tickets | nit | **Accepted** (**user decision 6**: refuse): 409 "Close its tickets first", checked after the scrap locks; race-free with a raise by the node lock (§ 1, § 3, § 5.8, § 8) |
| BR1-13 small text gaps | nit | **Accepted**: age from the event time; `app.py` named; documents vs tickets blueprint paths stated; `/modes` kept with its reason; Plan.MD § 5 `attachments` row removed in the Docs list; open-ticket warning check made plain (§ 1, § 3, § 6, § 8) |

Changes asked by the S018 review (`docs/steps/S018-work-tickets/2-brief-review-r1.md`), made here:
- the people picker is `GET /api/tickets/people` with trades, the one list S018 reuses for assignees and labour (S018 BR1-10);
- the detail's events carry `intensity` (S018 BR1-12);
- `current_person_id(cur)` is left to S018, which is the first step to need it (S018 BR1-11);
- the event-time window is `event_time_error(…, not_before)`, which S018's `validate_event_time` reuses (S018 BR1-14).

### Round 2 — `2-brief-review-r2.md` (Fable), answered 20-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR2-01 v12 must re-add the owner CHECK under its old name | minor | **Accepted** (option 1): `DROP CONSTRAINT IF EXISTS` then `ADD CONSTRAINT IF NOT EXISTS chk_equipment_documents_owner` with the three-owner sum, so v9's re-run is a no-op; `test_migration_v12.py` asserts the name and a ticket-photo insert after a v9 re-run (§ 4.2, § 3, § 8) |
| BR2-02 ticket owner's write path omits the 404 step | minor | **Accepted**: `read_for_change` and `lock_for_change` both decide 404 (predicate) → 403 (`write_key` at the site of `tickets.unit_id`) → 409 (closed), the lock from the locked row; test "key at the site but not the unit → 404" (§ 5.5, § 8) |
| BR2-03 "`ticket:read` only → upload 403" cannot be set up | minor | **Accepted** (option 1): the moved-machine setup — a user at the machine's new site reads the ticket but gets 403 on upload, title and remove at the ticket's site (§ 8) |
| BR2-04 *Open tickets* section for users without `ticket:read` | minor | **Accepted**: section and button rendered from the node detail's `permissions` (keys at the node's site); IT admin and the storekeeper see neither (§ 3) |
| BR2-05 send `occurred_at` only when changed | minor | **Accepted**: the raise screen sends it only when the user changed the field; the server's clock is the default; API test "raise without `occurred_at` gets the server's time" (§ 3, § 5.1, § 8) |
| BR2-06 where the no-login roles live; what the Team dialog offers | nit | **Accepted**: `config_rbac.NO_LOGIN_ROLES`, used by `no_login_role_error`; `TECHNICIAN_ROLE`'s comment fixed; PeoplePanel offers Operator to IT admin only; engineer + operator becomes 403, the test splits (§ 3, § 5.9, § 8) |
| BR2-07 restore on a closed ticket; removed item's `state`; Kind radio | nit | **Accepted**: restore refused on a closed ticket via `lock_for_change` (said); the removed ticket item carries `state` and *Restore* is disabled with a title; the upload modal hides the Kind radio with `photosOnly` (§ 3, § 5.5) |
| BR2-08 small text gaps | nit | **Accepted**: `equipment_id` filter semantics (machine → its tickets; component-unit or component → tickets raised on that node only); the warning calls with the machine's id (`ancestors[0]`); `raised.person_id` NULL; `machine_and_component(node)` from `level` / `parent_id` / `gp_id`, no private `_ancestors`; import direction stated; "before the file is checked and written"; a re-parented component keeps the stored machine; the people picker takes `equipment_id` now and **S018 adds `ticket_id=`** (S018 owns it), helper site-first; README › Queued row "Supervisors and engineers create operators without a login at their own site" added (§ 3, § 4.1, § 5.2, § 5.9, § 6) |

### Stale brief check s1 — `2-brief-review-s1.md` (Fable), answered 20-10-2026

Baseline `90284ec + uncommitted S016, S015` → `6c771e1` (S015 and S016 committed with their fix rounds). The brief still holds.

| Finding | Severity | Answer |
|---|---|---|
| BS1-01 `update_failure_mode` pre-read lacks `code`; S016 comments go stale | nit | **Accepted**: one line in § 3 `masters.py` |
| BS1-02 IT admin departure not recorded in `config_rbac.py` comments | nit | **Accepted**: the new keys' comment names decision 7; the `ROLE_INCLUDES` comment adjusted (§ 3 `config_rbac.py`) |
| BS1-03 documents lock paragraphs in `equipment.py` and `documents.py` need the ticket owner | nit | **Accepted**: both docstrings named in § 3 |
