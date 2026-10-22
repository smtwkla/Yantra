```
Step: S020 — Parts used
Doc: brief
Author: Planner (Opus)
Date: 21-10-2026 (revised 21-10-2026 after brief-reviews r1 and r2)
Track: full
Status: Done (committed b6b8dfb; checks: 7 auto; row 11, plain, left for IT Admin)
Baseline: 3df667c + uncommitted S025 and S019
```

# S020 — Parts used

Today a technician who replaces a bearing records the action *Replace* and
types the bearing's number into the remarks, if at all. This step gives the
ticket a **parts line**: what was fitted, its number, its maker, how many, and
on which component. No stock, no cost, no ordering: those stay in OneERP.
Over time the lines build the parts list the makers never gave (Plan.MD § 4.2
*Parts used*, Q21; Maintenance-Philosophy *Parts and part numbers*), and they
seed each model's bill of materials when spares come.

The other half of the original request, work done without a ticket, is done:
S018 A1 (*Already fixed* on the raise screen, 20-10-2026).

**Track: full** — a new table (a migration), locks across the equipment and
ticket rows, a new panel and dialog.
**Depends on:** S018 (the ticket page, labour as the pattern), S025 (the
squashed schema v20) and S019 (v21). This step's migration is **v22**. It is
coded on top of S025's and S019's code, which is not committed yet; the user
commits S025, S019 and S020 together (BS1-05).

## 1. What will be built

1. **A *Parts used* panel on the ticket page**, beside *Labour*, listing each
   line: quantity and unit, description, part number with its kind, maker,
   and the component it was fitted to, in the order entered. The panel shows
   to `ticket:work` holders (empty: "No parts recorded"), and to others only
   when the ticket has lines — the labour panel's rule (BR1-04).
2. **Add, edit and remove a line** while the ticket is not closed, for
   `ticket:work` holders at the ticket's site (the labour key; the labour
   panel's pattern: a dialog through `FormModal`; remove asks first with the
   inline *Remove? Yes / No* bar of `LabourPanel.vue`, not a modal). A closed
   ticket's lines are read-only, like its labour; a not-a-fault ticket never
   has lines (§ 1.5). Lines can be added, changed and removed in any open
   state, scheduled (S019) included (BS1-03).
3. **The line's fields:**
   - **Description** (required, up to 200 characters): "Deep-groove ball
     bearing", "Seal kit, main cylinder".
   - **Part number** (optional, up to 60), with one line of help under it:
     "What is on the part, the drawing or the quote. Leave empty if there is
     none."
   - **Kind of number** (stored when a number is given; shown **only while
     *Part number* has text**, BR2-02 — a description-only line such as
     "Servo 68, 5 L" shows neither the buttons nor a required *Maker*): two
     large choice buttons, worded for the floor — **"From the maker's drawing or quote"**
     (`maker`) and **"A standard number (6205-2RS, a filter spec)"**
     (`generic`). Default *standard number*, since most press spares are
     bought generic (Plant-Facts § 6), or the kind of the suggestion picked;
     one tap flips it (BR1-06). This is what lets a later step map maker
     numbers to OneERP items and group generic ones across machines.
   - **Maker** (free text, up to 100; required for a maker's part number —
     marked required only while the buttons show *maker* — optional for a
     generic one or with no number; the brand bought, e.g. SKF).
   - **Quantity** (required, more than 0, up to 9999.99, at most two
     decimals; **default 1**) and its **unit** from a fixed list: *nos*
     (default), *set*, *m*, *L*, *kg* — a hose is bought by the metre and oil
     by the litre.
   - **Fitted to** (required): the ticket's machine or a component below it,
     two levels as the ticket's own component; defaults to the ticket's
     component (or the machine when the ticket has none). The machine is the
     first row, labelled with its code and name. Not a scrapped node — checked
     when the line is added or its *Fitted to* changes (§ 5.2, BR1-03).
4. **"Fitted here before"** (BR1-05). The *Add* dialog has *Description* as
   its first field and, **directly under it** (BR2-09, so the list stays in
   view while the phone keyboard is up), a short list of the lines already
   recorded on **the same machine and
   its components**, on any ticket, newest first, distinct by number, kind,
   maker and description (up to 20, fetched once when the dialog opens). Each
   row shows *description · number · maker*; the five newest show, the rest
   behind *More*, and typing in *Description* narrows the list. A tap fills
   number, kind, maker and description; quantity and *fitted to* stay to be
   entered. *Edit* does not show the list (the line already has its number).
   So the second time a press's seal kit is changed, nobody hunts for the
   number again — and *Description* stays a plain field, with no dropdown to
   keep clear of the phone keyboard.
5. **Not a fault with parts is refused**: a ticket with part lines cannot be
   closed as not a fault, from every from-state of `MOVES["not-a-fault"]`
   (raised, acknowledged, scheduled since S019, in progress since S025 § 1.10;
   BS1-03). On the page, *Not a fault* is disabled
   with "Remove the parts first" while `parts` is not empty — S018's
   pre-empting of the labour refusal (BR4-02); no extra button, the panel is
   on the page. A stale page gets **409, no field**: "Parts are recorded, so
   it was a fault — remove them first" (BR2-06), shown at
   the top of the dialog, which reloads the page behind it as for the other
   409s (BR1-07). Fitting a part is a maintenance action on a failure (ISO
   14224); a not-a-fault ticket stays out of the failure counts, so the two
   cannot both be true.
6. **The close dialog shows a hint**, not a refusal, when the action is
   *Replace* (ISO action 1), *Modify* (3) or *Overhaul* (10) and no part is
   recorded (§ 9 Q6, U1): "No parts recorded. If any were fitted, cancel and
   add them on the ticket first." It does not refuse (§ 9 Q1, U1). The
   engineer who knows nothing was numbered simply saves.
   Acting on the hint costs the dialog's inputs (the `FormModal` guard asks,
   then discards them) — accepted (BR2-04): it is a hint, and engineers learn
   to record parts before closing. *Rejected:* opening the parts dialog over
   the close dialog (two stacked modals on a phone, no base pattern); a
   page-level reminder beside *Close* whenever there are no parts (it would
   nag on every *Adjust* or *Clean* close).

### Out of scope

- Parts on **PM jobs**: PM is not built (phase 4). The line's columns are the
  ones a job's line needs too, so the PM step adds `job_parts` with the same
  columns, or a `job_id` beside `ticket_id`; it decides then (§ 7 decision 6).
- A **parts history per equipment or per model** (a "parts fitted" card on the
  equipment page, the model's emerging parts list): belongs with history and
  reports (Plan.MD § 4.6). The suggestions of § 1.4 read the same data in the
  meantime.
- **Stock, issue, cost, ordering**, the storekeeper's work: OneERP's (Plant-
  Facts § 6; ISO 8000, below).
- A **link to OneERP item codes**: a later step, once OneERP's item master is
  read.
- A parts **master** in Yantra: rejected (§ 7 decision 1).
- Parts at **raise** (*Already fixed*): the raise screen stays as it is; the
  lines are added on the ticket page after the save.

## 2. Standards and practice

- **ISO 14224:2016 (maintenance data).** A maintenance record carries, beside
  the failure's mode, cause and action, the **maintenance resources used
  (Table 8): the man-hours per discipline (S018's labour) and the spare
  parts**. A record that says
  *Replace* but not what was replaced cannot show which component keeps
  failing or which part number is a poor buy. ISO 14224 records a failure
  against the **equipment unit** (taxonomy level 6, Yantra's machine) and names
  the **subunit and maintainable item** (levels 7–8) where it occurred;
  Yantra's component is that maintainable item. The line sits on it, so a part
  lands against the thing it fits (BR2-07).
- **EN 13460 (maintenance documentation)**: the work order's completion
  report lists the materials used. With labour and parts, Yantra's ticket is
  that report.
- **ISO 8000 (master data quality)** supports the master-data-management
  practice of a **single authoritative item master** (that practice is not
  itself a clause of ISO 8000). OneERP holds it; Yantra records **what was
  fitted**, not a second catalogue (BR1-12). The kind of number (maker or generic) is kept so a later link can
  map each maker number to one OneERP item — the departure, recorded: Yantra
  holds part numbers as text, without a master, until that link exists (§ 7
  decision 1).
- **TPM, planned-maintenance pillar**: spare-parts control starts with knowing
  which parts a machine actually consumes; the history these lines build is
  the input to a critical-spares list (Maintenance-Philosophy: "build the parts
  list from maintenance history").
- **ISO 9001 § 7.5 (documented information)**: who recorded each line and when
  (the audit columns), and a closed ticket's lines are not changed afterwards.
- **ISO 55001 § 7.5 (information requirements)**: the asset information the
  organisation decides it needs — here, what was fitted to what — and the
  quality it keeps that information at.

## 3. Where

### Backend

- `backend/local_db.py`: migration **v22**, `ticket_parts` (§ 4). It has
  **no `_PRECONDITIONS` entry**: it creates one new table and touches no
  existing row. The comment above v22 says so, as v21's does, so the
  SMTW-Review migrations check passes on reading (BS1-01).
- `backend/tickets_core.py` (pure): `PART_UNITS = ("nos", "set", "m", "L",
  "kg")`, `PART_KINDS = ("maker", "generic")`, `validate_part(body) ->
  (clean, errors)` (the field rules of § 1.3, trimmed text, the quantity
  rule and the messages of § 5.1), the not-a-fault
  refusal message, and `PARTS_HINT_ACTION_CODES = ("1", "3", "10")` — the action
  codes of the hint of § 1.6, in one place, so the dialog does not hard-code
  them. No hint function: the hint is decided in the dialog before the close
  is sent (BR1-02).
- `backend/tickets.py`:
  - `_parts(cur, ticket_id)` in the detail (`"parts": [...]`, with the node's
    code and name, ordered by `id`);
  - `_moves`: the entry whose `name` is `close` carries
    `parts_hint_actions`, the ids of `maintenance_actions WHERE code IN
    PARTS_HINT_ACTION_CODES`, one query, **active or not** (a retired code's
    hint does not vanish while old tickets still carry it);
  - `POST /api/tickets/<id>/parts`, `PUT …/parts/<row>`, `DELETE
    …/parts/<row>` on the labour routes' pattern, `@require_perm(WORK_KEY)`;
  - `GET /api/tickets/<id>/part-suggestions` (`ticket:work` at the ticket's
    site): § 1.4;
  - `_not_a_fault` refuses when the ticket has lines (§ 1.5), decided under
    the ticket lock;
  - the node check of § 5.2 shares `_check_component`'s query (after S025:
    the component row `LOCK IN SHARE MODE`): one helper that reads the node
    locked and returns the row, or `None` when it is not the machine or below
    it (a parameter says whether the machine itself counts); each caller
    raises its own refusal — the ticket edit `COMPONENT_OF_MACHINE` /
    `MACHINE_LEVEL` on `component_id`, the parts line "Choose the machine or
    one of its parts" on `node_id` (BR1-01, BR2-05). One helper, not a second
    copy;
  - the lock-order note in the module docstring, in the note's own words
    (BS1-02): the parts write joins the writes in "Working a ticket … locks
    (7) explicitly"; the parts add, and the edit whose `node_id` changes, are
    a **third bullet** in the list of reads that take a shared lock (the node
    row, the lock `fk_ticket_parts_node` takes at the insert anyway; a scrap
    holds it `FOR UPDATE`, so the two serialise); and the parts write is named
    under the fourth accepted deadlock (§ 5.2).
- `backend/equipment.py`: a third item in its sentence on the shared locks
  that fall on rows this module locks: the parts line's node (no code change;
  the scrap path is unchanged and does not look at part lines, § 5.2).

### Frontend

- `frontend/src/views/tickets/PartsPanel.vue` (new): the list and the
  add/edit/remove dialog, on `LabourPanel.vue`'s pattern (the inline *Remove?
  Yes / No* bar); *Description* first, the *Fitted here before* list directly
  under it (§ 1.4); the kind as two choice buttons (the `MoveDialog.vue`
  send-back pattern), rendered only while *Part number* has text, *Maker*
  marked required with *maker* chosen (BR2-02); *Fitted to* a select of the
  machine and its components; quantity as `<input type="text"
  inputmode="decimal">`, sent **as the string typed**, trimmed (BR2-01;
  `type="number"` would let the browser localise the separator).
- `frontend/src/utils/machineParts.js` (new): `loadMachineParts(machineId)` →
  `[{id, label}]` (`GET /api/equipment/<machine>`, two levels, scrapped left
  out) and the "keep the current choice when it is not listed" rule —
  extracted from `EditTicketDialog.vue` (BR1-09).
- `frontend/src/views/tickets/EditTicketDialog.vue`: uses the util; no
  behaviour change.
- `frontend/src/views/TicketDetailView.vue`: the panel beside labour; the
  second row's four cards (Times, Assigned, Labour, Parts used) become
  `col-md-6 col-xl-3`: two by two on a tablet, four across on a wide screen
  (BS1-06); `showParts = can("ticket:work") || parts.length > 0`; *Not a fault*
  disabled with "Remove the parts first" while `parts` is not empty.
- `frontend/src/views/tickets/MoveDialog.vue`: the close hint (§ 1.6) from
  `parts_hint_actions`; the not-a-fault 409 shown at the top like the other
  move refusals.

### Tests

- `backend/tests/test_tickets_core.py`: `validate_part` (each rule and message
  of § 5.1, by name: `number_kind` without a number dropped; a maker with no
  number allowed; the quantity cases `1.1` sent as a JSON number accepted as
  1.10, `True` refused, `"1e2"` accepted as 100, `"NaN"` and infinity refused,
  `1,5` refused — BR2-01, BR2-10).
- `backend/tests/conftest.py`: `_TABLES` gains `ticket_parts` before
  `tickets` (BR1-08).
- `backend/tests/test_ticket_parts_api.py` (new): add, edit, remove; closed
  ticket 409; wrong key 403 at the site; outside the units 404; a PUT or
  DELETE on a row of another ticket 404 (labour's `_labour_row` rule, BR2-10);
  *fitted to*
  outside the machine 400, scrapped 400; suggestions (same machine only,
  distinct, newest first, 20 at most, another site's machine not offered);
  not-a-fault refused with lines (409, from scheduled and in progress too;
  scheduled set up with `moves/schedule` as an engineer, BS1-03), allowed
  after removing them; the detail carries `parts` in entry order; the close entry
  carries the ids of Replace and Modify, also when one is deactivated; a PUT
  that leaves *Fitted to* unchanged on a node scrapped since succeeds, one
  that changes it to a scrapped node is refused.
- `backend/tests/test_migration_v22.py` (new), on `test_migration_v21.py`'s
  upgrade-database pattern (BS1-01), because the shared test database already
  has v22 when the tests start: import the helpers from
  `test_migration_v20.py`; in `vel_yantra_upgrade`, `_recreate()`, `_migrate`
  with `_MIGRATIONS` pinned to `(20, 21)`, then `(20, 21, 22)`; check the
  columns, `chk_ticket_parts_kind`, `chk_ticket_parts_quantity`, the two
  foreign keys and the three indexes; delete `db_version` 22, run again, and
  compare `_schema()`.
- `frontend/e2e/support/tickets.js`: `actionId(code)` beside `causeId(code)`,
  for the closed-ticket setup (BS1-04).
- `frontend/e2e/tickets-parts.spec.js` (new), § 8.

### Docs (at approval, by the planner)

- `docs/Plan.MD` § 4.2 *Parts used*: Decided, with the fields and the rules;
  Q21 settled; § 5 data model: the *Proposed* `parts_used` row is **replaced**
  by `ticket_parts`, PM jobs decided later (§ 7 decision 6) (BR2-07).
- `docs/Maintenance-Philosophy.md` *Parts and part numbers*: Decided.

## 4. Data model (the next migration)

The migration is **v22** (S019 took v21; BS1-01), tested by
`test_migration_v22.py`. No `_PRECONDITIONS` entry: `parts_used` was never a
table, only the *Proposed* row in Plan.MD § 5, so no database holds it; v22
creates `ticket_parts` with `CREATE TABLE IF NOT EXISTS` and touches no
existing row.

**`ticket_parts`**:

| Column | Type | Notes |
|---|---|---|
| `id` | INT PK | |
| `ticket_id` | INT NOT NULL | FK `fk_ticket_parts_ticket` → `tickets` |
| `node_id` | INT NOT NULL | FK `fk_ticket_parts_node` → `equipment`; the machine or a component below it |
| `description` | VARCHAR(200) NOT NULL | |
| `part_number` | VARCHAR(60) NULL | as typed, trimmed |
| `number_kind` | ENUM('maker','generic') NULL | NOT NULL exactly when `part_number` is; CHECK `chk_ticket_parts_kind` |
| `maker` | VARCHAR(100) NULL | |
| `quantity` | DECIMAL(6,2) NOT NULL | CHECK `chk_ticket_parts_quantity` (> 0) |
| `qty_unit` | VARCHAR(8) NOT NULL DEFAULT 'nos' | one of `PART_UNITS` (checked in the core; no ENUM, so a unit is added without a migration) |
| `created_at`, `created_by`, `updated_at`, `updated_by` | | as `ticket_labour` |

Indexes: `ix_ticket_parts_ticket (ticket_id)`; `ix_ticket_parts_node
(node_id)` for the suggestions and the later history; `ix_ticket_parts_number
(part_number)` for the later OneERP link and "where else was this fitted" —
cheap now on an empty table, a migration later, which is why it is here.

The maker-required-for-a-maker-number rule is the core's, not a CHECK, so its
message reaches the field.

## 5. Rules

### 5.1 Fields

As § 1.3. The text fields are trimmed; an empty string is NULL. **The
quantity** (BR2-01): the dialog sends it as the string typed; the core accepts
a string or a non-bool `int`/`float` (a bool is refused, as `_is_id` does),
converts through `Decimal(str(value))` — never `Decimal(float)`, whose binary
expansion would make `1.1` fail the two-decimal rule — refuses `NaN` and
infinity, and judges "at most two decimals" on the value
(`value == value.quantize(Decimal("0.01"))`), so `"1e2"` is 100 and `1.5` m of
hose stays 1.50. The core's cases and messages (BR1-10), on the body's field
names:

| Case | Result |
|---|---|
| `description` missing, empty or whitespace only | `description`: "Describe the part" |
| a text longer than its column | that field: "Too long (max N)" — `_optional_text`'s words, reused (BS1-07) |
| `number_kind` sent without a `part_number` | dropped (stored NULL), no error |
| `part_number` given, `number_kind` missing or unknown | `number_kind`: "Choose where the number comes from" |
| `number_kind` `maker`, no `maker` | `maker`: "Name the maker of this part number" |
| `maker` with no number at all ("Servo 68" by Indian Oil) | allowed |
| `quantity` missing, a bool, not a number, `NaN` or infinite, a comma decimal (`1,5`), 0 or negative | `quantity`: "Enter a quantity, e.g. 2 or 1.5" |
| `quantity` with more than two decimals (`1.505`) | `quantity`: "At most two decimals" — refused, not rounded |
| `quantity` above 9999.99 | `quantity`: "At most 9999.99" |
| `qty_unit` missing | `nos` |
| `qty_unit` not in `PART_UNITS` | `qty_unit`: "Choose a unit" |
| `node_id` missing, not the machine or below it, or scrapped (when checked, § 5.2) | `node_id`: "Choose the machine or one of its parts" |

### 5.2 Transactions and locks

Add and edit: one transaction, in S025 § 1.6's order (BR1-01):
1. Lock the ticket row (7) `FOR UPDATE` (`_lock_open_ticket`): 404, 403 at the
   ticket's site, closed 409 — decided from the locked row, so the refusal
   order stays 404 → 403 → 409 → 400 as on every ticket write.
2. Validate the body in the core (the 400s of § 5.1).
3. Check the node, on an **add**, or on an **edit whose `node_id` changes**:
   read the node row `LOCK IN SHARE MODE` (the helper shared with
   `_check_component`, § 3) and decide from that row: the machine itself or
   below it (the ticket's `equipment_id` from the locked ticket), not
   scrapped → else 400 on `node_id`. This is the shared lock the insert's
   foreign key takes anyway, taken explicitly so the decision is made from the
   locked row; so, as S025 argues for the edit, **no new lock-order edge**. A
   scrap of the node at the same moment holds it `FOR UPDATE` and serialises
   with this check either way. An edit that leaves `node_id` as it is does not
   re-check it (BR1-03): the line is history, and a node scrapped since is
   true of it; the dialog keeps that node as a choice when it is no longer
   listed (`machineParts.js`).
4. Insert or update the line; return the detail.

Remove locks only the ticket (7), like labour; a hard delete with no timeline
line (labour's rule, S018 § 4.2: the ticket is open, the row carries its audit
columns).

Not a fault (§ 1.5): the count of lines is read after the ticket lock; a
concurrent add holds or waits for the same ticket lock, so the two cannot both
succeed.

A repeat raised on the node at the same moment as a part is recorded on the
earlier ticket can deadlock: the raise holds the node (1) `FOR UPDATE` and then
takes the earlier ticket's shared lock, while the parts write holds the ticket
(7) and then takes the node's shared lock. This is the shape of the note's
fourth accepted deadlock, which S025's edit shares (S025 CR1-02): one side
gets the JSON 500 "Something went wrong — try again", a retry works, and
integrity holds. The coder names the parts write there (BS1-02).

**Scrap does not look at part lines** (BR1-03): its guard counts open tickets
on the node and its parts (`equipment_id` / `component_id`), so a component
carrying a line of an open ticket raised on the machine can be scrapped. That
is accepted — the line stays true as history, and § 5.2 step 3 does not
re-check an unchanged node. The equipment `ON DELETE` is the default
(restrict); equipment is never deleted.

### 5.3 Suggestions

`SELECT part_number, number_kind, maker, description, MAX(created_at)` over the
lines whose node is the ticket's machine or below it (the machine's subtree,
two levels, as `_check_component` knows it), grouped by the first four, newest
first, `LIMIT 20`; read plain. `total` is the number of rows returned (at
most 20); the list shape is kept.

**Who sees what** (BR2-03). The lines are read **by machine**, not through the
ticket access predicate (`t.unit_id … OR m.unit_id …`). So a user who may work
a ticket on the machine sees what was fitted to that machine on any ticket,
including tickets raised after the machine moved to a unit at another site,
which they cannot open. **Accepted:** a part number, description and maker on a
machine they maintain are not confidential, and a suggestion carries no ticket
number and no site. *Rejected:* filtering the suggestions by the ticket
predicate — one more join, for a case that arises only after a machine moves
between sites.

### 5.4 Permissions

No new key. Write: `ticket:work` at the ticket's site (technician and up, IT
admin) — whoever books labour records the parts. Read: the detail's
`ticket:read`. The storekeeper keeps no ticket access (S017 decision 7).

## 6. API

| Method and path | Key | Body / answer |
|---|---|---|
| `POST /api/tickets/<id>/parts` | `ticket:work` | `{description, part_number?, number_kind?, maker?, quantity, qty_unit?, node_id}` → 201, the detail |
| `PUT /api/tickets/<id>/parts/<row>` | `ticket:work` | the same → the detail |
| `DELETE /api/tickets/<id>/parts/<row>` | `ticket:work` | → the detail |
| `GET /api/tickets/<id>/part-suggestions` | `ticket:work` | `{"items": [{part_number, number_kind, maker, description}], "total": N}` |

The detail gains `parts: [{id, description, part_number, number_kind, maker,
quantity, qty_unit, node: {id, code, name}, created_at, created_by}]` (quantity
as a string, `"1.50"`, so no float rounding on the way; in entry order, by
`id`) and, on the `moves` entry whose `name` is `close`,
`parts_hint_actions: [<action ids>]` — the ids of *Replace*, *Modify* and *Overhaul*, so
the dialog shows the hint when the chosen action is one of them and `parts` is
empty. Errors: the usual `{"error", "field"}` (field names as the body's).

## 7. Design decisions

1. **Part numbers as text on the line, no parts master.** The parts list is
   meant to emerge from the work (Maintenance-Philosophy), and OneERP is the
   item master (ISO 8000); a Yantra master would be a second catalogue to
   keep in step, and a technician at the machine could not add to it.
   *Rejected:* a `parts` master with lines pointing at it (upkeep, duplicates
   OneERP); free remarks only (today's state, not countable).
2. **The kind of number is stored.** A maker's number maps to one OneERP item;
   a generic designation may map to several brands. Without the kind, the
   later link cannot tell which is which. *Rejected:* inferring it from the
   maker field (a generic bearing has a brand too).
3. **Maker as free text, not the `manufacturers` master** (S012). That master
   is edited by IT admin (`masters:edit`) and holds equipment makers; part
   makers (SKF, Rexroth, Parker) are many more, and a technician must not wait
   for IT. *Rejected:* an FK to `manufacturers` (blocks the technician),
   a second makers master (upkeep). The suggestions keep spelling consistent
   in practice.
4. **The line names its own node**, defaulting to the ticket's component. One
   repair often fits parts to several components of the machine (a motor's
   bearing and its coupling's insert), and the history is per component.
   *Rejected:* parts always on the ticket's component (wrong node for the
   second part); on the machine only (loses the component view ISO 14224
   wants). The suggestions follow the machine too, not the ticket's access
   (§ 5.3, BR2-03).
5. **Quantity with a unit from a short fixed list**, two decimals. Hoses and
   oil are not counted in pieces. *Rejected:* an integer count (forces "1" for
   2.5 m of hose); free-text units (`mtr`, `m`, `meter` would not add up).
6. **PM jobs decided later.** The columns suit a job's line too; whether that
   is a `job_id` beside `ticket_id` (one table, a CHECK that exactly one is
   set) or a `job_parts` table is decided with PM's data model. *Rejected:*
   adding a nullable `job_id` now (a column for a table that does not exist).
7. **Not a fault refused when parts are fitted; the *Replace* hint is only a
   hint.** The first is a contradiction in the record; the second is often
   true but not always (a part replaced from the workshop's own stock that
   nobody numbers). The user kept it a hint (§ 9 Q1, U1).
8. **Lock the ticket, then read the node in share mode** — S025 § 1.6's
   order for the ticket edit, with the same helper. The node's shared lock is
   the one the insert's foreign key takes anyway, taken explicitly so the
   "not scrapped" decision is made from the locked row: it closes the scrap
   race of audit [4] (a plain read racing a scrap) with no new lock-order
   edge, and keeps one lock pattern in `tickets.py`. *Rejected:* share-locking
   the node before the ticket (deadlock-free too, but a second pattern beside
   S025's, and a node refusal before the ticket's own 404/403); a plain read
   (the race audit [4] found). *Also decided:* an unchanged node is not
   re-checked on edit (§ 5.2).
9. **No timeline line for parts**, as for labour. The lines carry who and when;
   the timeline stays the failure's story. *Rejected:* a line per add (noise on
   a ticket with five parts).

## 8. Tests and acceptance

### Automated (e2e, `tickets-parts.spec.js`, three projects)

Conventions (S024's suite; BS1-04):
- **Setup by API** on the seed's extruder (`seed.extruder`, SMTW.MCC2, the
  operator's unit): `raiseByApi("operator", …)`, then
  `moveByApi("technician", id, "start")` for the in-progress ticket. The
  closed ticket: `restore`, a labour row (close refuses without one), the
  part through the API, then `close` with `cause_id` and `action_id` from
  `causeId` and the new `actionId`.
- **Refusals the test provokes are declared**: the maker and quantity
  messages are 400s from the API (the API decides, § 5.1), so the test calls
  `consoleWatch.allowFailedRequest("/parts", 400)` and checks each message
  with `expectFieldMessage`.
- **Shared database**: the three projects run on one database, and earlier
  lines stay. The *Fitted here before* test gives its line a description
  unique to the run (with the ticket's serial in it), finds that row by text,
  and never asserts the list's length or that a list is empty.

- **Important:** a technician adds a part line on an in-progress ticket the
  short way — description, a number with the default kind (*standard
  number*), the default quantity 1 nos, fitted to a component; the panel
  shows it with the component's code; edit changes the quantity to 2; remove
  asks first and removes it.
- **Important:** a maker's part number without a maker shows the message
  beside *Maker*; a quantity of 0 beside *Quantity*.
- **Important:** a second ticket on the same machine shows the first line
  under *Fitted here before*; a tap fills number, kind, maker and description.
- *Not a fault* is disabled with "Remove the parts first" on a ticket with a
  part line; after removing the line it is offered and succeeds.
- The close dialog shows the hint for *Replace* or *Overhaul* with no parts,
  and not once a part is recorded.
- A closed ticket shows its parts with no *Add* or *Edit*; an operator sees
  the lines, with no *Add*, on a ticket that has them, and no panel on one
  that has none.
- The parts dialog fits a phone (`expectDialogFits`), with the *Fitted here
  before* list showing.

### On a real device

- The iPhone keyboard over the parts dialog: the quantity field opens the
  decimal keyboard and the *Save* button stays reachable (KLA or IT Admin, a
  technician account; network: plant Wi-Fi or mobile data, either; dev server
  on KLA's laptop or the TEST machine on production).

### Acceptance

The suites are green; the e2e spec passes on all three projects; a ticket can
carry parts on its components, the second ticket on a machine offers them
again, and a not-a-fault ticket cannot carry parts.

## 9. Open questions and assumptions

All settled by the user at gate A (U1, 21-10-2026), each as proposed:

1. ~~*Replace* without parts refuses the close?~~ No: a hint only (§ 7
   decision 7).
2. ~~Units~~: *nos, set, m, L, kg*. Adding one later is a code change, no
   migration.
3. ~~Who records parts~~: `ticket:work` only (technician and up). The
   operator who restores a machine (`ticket:restore`) does not.
4. ~~Suggestions~~: from the same machine only. Across machines of the same
   model is for the history step.
5. ~~Limit on lines~~: none.
6. ~~The hint's actions~~: *Replace* (1), *Modify* (3) and *Overhaul* (10),
   `("1", "3", "10")`. *Repair* (2) stays out, since most repairs fit nothing
   numbered.

## 10. Amendments

(none)

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 21-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR1-01 decision 8 misreads S025; two lock patterns | major | **Accepted** (a): ticket (7) first, then the node `LOCK IN SHARE MODE` through the helper shared with `_check_component` (a parameter admits the machine itself); refusal order 404 → 403 → 409 → 400; the "inversion" reasoning dropped; lock-order notes say the same as S025 (§ 3, § 5.2, § 7.8) |
| BR1-02 `close_parts_hint` has no caller | minor | **Accepted**: only `PARTS_HINT_ACTION_CODES` in the core; `_moves` resolves the ids on the close entry, active or not (a retired code keeps its hint); tested in the API (§ 3) |
| BR1-03 a line's node scrapped while open; edit refuses an untouched field | minor | **Accepted** (a): the node is checked on add and when `node_id` changes; the dialog keeps the line's own node; § 5.2 now says scrap does not look at part lines |
| BR1-04 panel visibility vs labour | minor | **Accepted**: `showParts = can("ticket:work") or parts.length > 0`, as `showLabour` (§ 1.1, § 3, § 8) |
| BR1-05 suggestions unspecified | minor | **Accepted**: *Fitted here before* at the dialog's top, fetched once on open, a row = description · number · maker, five shown then *More*, narrowed by *Description*, not on *Edit*; in the dialog-fit check (§ 1.4, § 3, § 8) |
| BR1-06 kind and quantity defaults | minor | **Accepted**: two choice buttons in floor words, default *standard number* (or the suggestion's kind); quantity 1 nos; a help line under the number; the important e2e takes the default path (§ 1.3, § 8) |
| BR1-07 not-a-fault refusal status; pre-empt on the page | minor | **Accepted**: 409, no field, shorter message, the dialog reloads the page; *Not a fault* disabled with "Remove the parts first"; covers all three from-states incl. S025's in progress (§ 1.5, § 3, § 8) |
| BR1-08 `conftest._TABLES` | minor | **Accepted** (§ 3 Tests) |
| BR1-09 *Fitted to* list duplicates `EditTicketDialog` | minor | **Accepted**: `utils/machineParts.js` extracted and used by both; the machine itself is the first row (§ 3) |
| BR1-10 validation cases and messages | minor | **Accepted**: the table in § 5.1 |
| BR1-11 device check network | minor | **Accepted**: "plant Wi-Fi or mobile data, either" (§ 8) |
| BR1-12 ISO 8000 / ISO 14224 citations | nit | **Accepted**: ISO 8000 as master-data-quality support for a single item master; ISO 14224 Table 8; ISO 55001 § 7.5 added (§ 2) |
| BR1-13 Overhaul in the hint | nit | **Deferred to the user**: § 9 Q6, proposed Replace, Modify and Overhaul |
| BR1-14 notation and small gaps | nit | **Accepted**: "the entry whose `name` is `close`"; lines by `id`; a not-a-fault ticket never has lines; the v21 note in § 4; the index's reason (§ 1.2, § 4, § 6) |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 21-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR2-01 quantity as a JSON number through `Decimal` | minor | **Accepted**: the dialog sends the typed string (`type="text" inputmode="decimal"`); the core converts via `Decimal(str(v))`, refuses bools, `NaN`, infinity, judges two decimals with `quantize`; core tests for `1.1`, `True`, `"1e2"`, `"NaN"` (§ 3, § 5.1) |
| BR2-02 kind buttons and *Maker* with no number | minor | **Accepted**: the buttons and the required mark on *Maker* show only while *Part number* has text (§ 1.3, § 3) |
| BR2-03 § 5.3's access sentence | minor | **Accepted** (as recommended): reworded; suggestions are read by machine, so after a cross-site move a user may see part lines from tickets they cannot open; accepted, since a part number on a machine they maintain carries no ticket or site; filtering by the ticket predicate rejected; `total` defined (§ 5.3, § 7.4) |
| BR2-04 the close hint's cost | minor | **Accepted** (a): the hint reads "No parts recorded. If any were fitted, cancel and add them on the ticket first."; the loss of the dialog's inputs on cancel is stated and accepted; (b) and (c) rejected (§ 1.6) |
| BR2-05 the shared helper's field and message | nit | **Accepted**: the helper returns the row or `None`; each caller raises its own refusal on its own field (§ 3) |
| BR2-06 the stale-page message | nit | **Accepted**: "Parts are recorded, so it was a fault — remove them first" (§ 1.5) |
| BR2-07 docs and standards wording | nit | **Accepted**: Plan.MD's `parts_used` row is replaced; ISO 14224 taxonomy (equipment unit level 6, maintainable item levels 7–8); the inline *Remove? Yes / No* bar named (§ 1.2, § 2, § 3) |
| BR2-08 empty parts card on closed tickets | nit | **Rejected** (no change): consistent with the labour panel (`showLabour`); a change would be made for both panels or neither |
| BR2-09 the list narrowed by a field below it | nit | **Accepted**: *Description* first, the list directly under it (§ 1.4, § 3) |
| BR2-10 two small test gaps | nit | **Accepted**: another ticket's row 404; the two core cases named (§ 3 Tests) |

### U1 — user answers, 21-10-2026 (gate A)

"parts brief ok. suggestions ok." and "decisions as per suggested" → approved 21-10-2026; every § 9 proposal accepted (Q1 hint only; Q2 the five units; Q3 `ticket:work` only; Q4 same machine; Q5 no limit; Q6 Overhaul joins the hint, § 1.6, § 3, § 6). Baseline from r2's *Reviewed against:*.

### Staleness check s1 — `2-brief-review-s1.md` (Fable), answered 22-10-2026

Against 3df667c + uncommitted S025 and S019. Verdict: no blocker or major.

| Finding | Severity | Answer |
|---|---|---|
| BS1-01 the migration is v22; precondition; upgrade test | minor | **Accepted** (a): v22, no `_PRECONDITIONS` entry and why (a new table only), the comment above v22; `test_migration_v22.py` on v21's upgrade-database pattern (Depends on, § 3, § 4) |
| BS1-02 the rewritten lock-order notes; the repeat-raise deadlock | minor | **Accepted** (a): a third bullet in the shared-read list, in the note's own words; `equipment.py`'s sentence; one paragraph in § 5.2 naming the accepted deadlock shape (§ 3, § 5.2) |
| BS1-03 *Not a fault* also from scheduled | minor | **Accepted**: the refusal covers every from-state, scheduled included; parts allowed in any open state; tested from scheduled and in progress (§ 1.2, § 1.5, § 3 Tests) |
| BS1-04 e2e conventions | minor | **Accepted**: setup by API on `seed.extruder`; an `actionId` helper; `allowFailedRequest("/parts", 400)` with `expectFieldMessage`; a unique description and presence-only asserts (§ 3, § 8) |
| BS1-05 "coded after S025 is committed" | nit | **Accepted**: coded on top of uncommitted S025 and S019, committed together; `Baseline:` set |
| BS1-06 where the parts card goes | nit | **Accepted**: the four cards as `col-md-6 col-xl-3` (§ 3 Frontend) |
| BS1-07 the length message | nit | **Accepted**: reuse `_optional_text` and its words, "Too long (max N)" (§ 5.1) |

