```
Step: S067 — Improvement record from tickets
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 30-10-2026
Track: full
Baseline: 32eb122 + uncommitted S066
Status: Gate B 30-10-2026 (snapshot 4182561; verify review r2 clean) — approved 30-10-2026 by KLA (delegated)
From: R05.1 (first half: the record and its API; the screens are S068)
```

# S067 — Improvement record from tickets

## 1. What will be built

An **improvement** is a record where the team analyses one problem that tickets showed, so it does
not happen again (TPM focused improvement, § 2). R05.1 builds the record, its link to tickets and
its screens. **This step builds the backend half**: the tables, the rules, the API and the keys.
**S068** (`docs/steps/S068-improvement-screens/1-brief.md`) builds the screens on the API of § 6,
exactly as written here (§ 9, *The split*).

1. **Start an improvement from a ticket.** `POST /api/improvements` takes a ticket that is *back in
   service* or *closed* (Q1.1 a), a title, the problem and a lead. Only an engineer or manager of the
   ticket's site may start one. The ticket row is not written: closed is final (Plan § 4.2).
2. **The improvement's detail.** `GET /api/improvements/<id>`: the serial `IM-YYYY-MM-NNN`, the state
   *Analysing*, the title, the problem, the machine and unit, the lead, who started it and when, the
   linked tickets with each one's symptom, cause and downtime, and the loss (tickets, breakdowns,
   the downtime sum). Downtime is computed as the ticket page computes it, never stored.
3. **Edit** the title, the problem and the lead (`PUT`).
4. **Add a ticket** of the same site, in any state (Q1.1 a).
5. **Remove a ticket** (a scope addition beyond R05.1, § 9 Q2, D9): a wrongly added ticket is taken
   off again. The improvement always keeps at least one ticket of its own machine (BR1-02).
6. **The list.** `GET /api/improvements`: open or closed, by unit, newest first.
7. **The lead choices.** `GET /api/improvements/leads`: the engineers and managers of the site.
8. **The ticket detail** (`GET /api/tickets/<id>`) gains `improvements` (the links, derived) and
   `can_start_improvement`.
9. **Two keys** (Q1.3 a): `improvement:read` (operator and up, and IT admin) and `improvement:edit`
   (engineer, so manager). Both are site-scoped. IT admin reads only.

**One open improvement per ticket** (Q1.4 a). The database enforces it (§ 4.1, D4).

**States in this step.** Only *Analysing* exists (D3). Every improvement is open, so a *closed* list
is always empty in this step. R05.4 adds the other states and closing.

**After S067 and S068:** the team starts IM-2026-10-001 from TK-2026-10-002 (the dusty contactor)
and writes the problem down. R05.2 adds the why-why on the same page.

### Out of scope

- **Every screen** (S068): the tab, the list, the improvement page, the dialogs, the ticket page's
  line and button, the browser tests.
- Why-why, root cause (R05.2); countermeasures and *Me › Open work* (R05.3).
- States beyond *Analysing*, *Drop*, the timeline, notes, the watch and the verified close (R05.4).
  So this step keeps no history of edits, link changes or removals (§ 2, ISO 9001 § 7.5.3).
- Alerts (R05.5), one-point lessons (R05.6), the register (R05.10).
- *Suggested* improvements (R05.8, deferred).
- An improvement with no ticket (Q1.1 b), a named team on the record.
- Counts per state on the list (one query per state; S068 shows no counts).

## 2. Standards and practice

- **TPM — focused improvement** (*Kobetsu Kaizen*, one of the eight TPM pillars). In plain words: a
  small team takes one chronic loss, finds its root cause and removes it for good; it does not stop
  at the repair. The improvement record is the place for that work. This step builds its first
  part: the problem and the losses (tickets) behind it. Maintenance-Philosophy § 3 brings this
  pillar forward for the presses.
- **ISO 9001:2015 § 10.2.1 (a) and (b)** (nonconformity and corrective action). In plain words:
  when something goes wrong, first correct it, then find out why, so it does not come back. The
  ticket is the correction (a). The improvement starts the "find out why" (b). Clause letters as
  Plan § 1 cites them; the next edition's numbers are *to verify* (R05 § Standards).
- **ISO 9001 § 10.2.2** (records). In plain words: keep a record of what went wrong and what was
  done. The improvement keeps the problem, its tickets, who started it, who leads it and when.
- **ISO 9001 § 7.5.3** (control of records). In plain words: records are kept, protected from
  change, and show who did what and when. The closed ticket is never written (it is only linked).
  **Departure (recorded):** in this step an edit of the problem, an added ticket and a removed
  ticket keep only `created_*` / `updated_*`, not a history. R05.4's timeline adds the history and
  backfills what the rows show. The step is short-lived (R05.2–R05.4 follow), and the problem text
  is a draft until the analysis is done.
- **ISO 14224 — failure data** (failure mode and cause per event). The improvement does not copy the
  tickets' symptom or cause: it reads them from the tickets, so each ticket stays the one record of
  its failure (no second copy to drift).
- **EN 13306 — time to restoration** (downtime). The loss sums each linked ticket's downtime,
  computed as the ticket page computes it (`tickets_core.ticket_times`, S018 § 5.4), never stored.
- **ISO 27001 A.5.15 (access control) and A.8.2 (privileged access)**: read for the floor, write for
  engineers, IT admin reads only (Q1.3 a, as R03 Q2.2 for PM).

## 3. Where

### Backend

- `backend/local_db.py`: migration **v36** (§ 4.1). No `_PRECONDITIONS` entry (§ 4.1).
- `backend/tickets_core.py`: the serial helper takes a prefix (§ 5.1): new
  `format_serial(prefix, year, month, number)`; `serial_scope(year, month, prefix="TK")`;
  `format_ticket_serial` keeps its signature and calls `format_serial("TK", …)`. TK serials do not
  change. Today `format_ticket_serial` (`backend/tickets_core.py:82`) and `serial_scope`
  (`backend/tickets_core.py:87`) hard-code `TK`.
- `backend/improvements_core.py` (new, pure): the states, the start, link and remove rules, the
  field validation, the loss, who may lead (§ 5).
- `backend/improvements.py` (new): the blueprint `improvements_bp`, the routes of § 6, the access
  predicate, the LOCK ORDER note (§ 5.4). It imports from `tickets.py` (`read_ticket`, the event
  read) and never the other way round.
- `backend/app.py`: register `improvements_bp` with `url_prefix="/api/improvements"`, beside
  `tickets_bp` (`backend/app.py:187`).
- `backend/config_rbac.py`: the two keys in `PERMISSIONS` (`backend/config_rbac.py:89`) and in
  `SITE_SCOPED` (`backend/config_rbac.py:166`), with a comment (§ 5.5).
- `backend/tickets.py`: `_detail` (`backend/tickets.py:404`) adds `improvements` and
  `can_start_improvement` (§ 5.3); the module docstring's LOCK ORDER note (from
  `backend/tickets.py:22`) names improvements.py as a new locker of ticket rows, shared only
  (§ 5.4). `tickets.py` imports `improvements_core` (pure) only, never `improvements.py`.
  `_person_at_site` (`backend/tickets.py:362`) and `_people_at_site` (`backend/tickets.py:692`)
  become public, `person_at_site` and `people_at_site`, as `read_ticket` is, with their callers in
  `tickets.py` renamed (lines 374, 717, 737, 1197): improvements.py reuses them for the lead
  (§ 5.6; BR2-02).
- `backend/equipment.py`: the global LOCK ORDER note (`backend/equipment.py:9`) gains *(6b) the
  improvement row* and an `improvements.py` bullet (docstring only).

### Tests

- `backend/tests/test_migration_v36.py` (new), on the pattern of `test_migration_v35.py`.
  `test_migration_v35.py` is unchanged: it slices `range(20, 36)` (`VERSIONS = list(range(20, 36))`,
  line 16), so v36 does not touch it.
- `backend/tests/test_improvements_core.py` (new).
- `backend/tests/test_improvements_api.py` (new): every route, and the ticket detail's two new
  fields (§ 8.2).
- `backend/tests/test_tickets_core.py`: `TestSerial` (`backend/tests/test_tickets_core.py:39`) gains
  the prefix cases; its TK cases stay unchanged.
- `backend/tests/test_rbac.py`: `test_role_matrix` (lines 178–209) gains the two keys for operator,
  technician, supervisor, engineer, manager (`improvement:read`, and `improvement:edit` from the
  engineer) and IT admin (`improvement:read`); a `test_improvement_keys` beside `test_ticket_keys`.
- `backend/tests/conftest.py`: `improvement_tickets` and `improvements` join `_TABLES`
  (`backend/tests/conftest.py:162`), before `tickets` and `people` for readability (the fixture
  deletes with `FOREIGN_KEY_CHECKS = 0`, so order does not matter).
- `backend/tests/test_tickets_api.py`: unchanged. It asserts no exact key set on the detail
  (checked: no `set(body) ==` in `test_ticket*.py`), so the two new detail fields break nothing. It
  runs again in the full suite.

### Docs (housekeeping, by the coder)

- `docs/schema.md` and `docs/schema.html`: the two tables, the Mermaid overview (improvements →
  units, equipment, people; improvement_tickets → improvements, tickets), the "migration v36" line.
- `docs/Plan.MD`: § 3, the key table gains the rows `improvement:read` and `improvement:edit`, and a
  paragraph on them; § 4.2, one line: a ticket back in service or closed can start an improvement
  (S067). The screens (§ 6) are S068's.
- `docs/Maintenance-Philosophy.md` § 12 Glossary: the row *Improvement*.
- `.claude/CLAUDE.md`: § Step workflow, *Self-check, repo items* (2) names the LOCK ORDER note of
  `improvements.py` beside `tickets.py` and `masters.py`. (The § SMTW-Review spec map is S068's.)

**File count:** 14 code and test files (8 code, 6 tests), 5 docs.

## 4. Data model

### 4.1 Migration v36

```sql
-- An improvement (S067, R05.1): one problem analysed from one or more tickets (TPM focused
-- improvement).  The unit and the machine are the first ticket's; the site is the unit's.
CREATE TABLE IF NOT EXISTS improvements (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    serial        VARCHAR(16) NOT NULL,
    unit_id       INT NOT NULL,
    equipment_id  INT NOT NULL,
    state         ENUM('analysing') NOT NULL DEFAULT 'analysing',
    title         VARCHAR(120) NOT NULL,
    problem       VARCHAR(2000) NOT NULL,
    lead_id       INT NOT NULL,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by    VARCHAR(100) NOT NULL,
    updated_at    DATETIME NULL,
    updated_by    VARCHAR(100) NULL,
    CONSTRAINT uq_improvements_serial UNIQUE (serial),
    KEY ix_improvements_unit_state (unit_id, state),
    KEY ix_improvements_equipment (equipment_id),
    CONSTRAINT fk_improvements_unit FOREIGN KEY (unit_id) REFERENCES units (id),
    CONSTRAINT fk_improvements_equipment FOREIGN KEY (equipment_id) REFERENCES equipment (id),
    CONSTRAINT fk_improvements_lead FOREIGN KEY (lead_id) REFERENCES people (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- The tickets an improvement analyses.  open_link is 1 while the improvement is open and NULL
-- after (R05.4 sets it when it closes or drops one): the UNIQUE key allows one open link per
-- ticket and any number of NULLs, so a ticket is in at most one open improvement (Q1.4 a).
CREATE TABLE IF NOT EXISTS improvement_tickets (
    improvement_id  INT NOT NULL,
    ticket_id       INT NOT NULL,
    open_link       TINYINT(1) NULL DEFAULT 1,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by      VARCHAR(100) NOT NULL,
    PRIMARY KEY (improvement_id, ticket_id),
    CONSTRAINT uq_improvement_tickets_open UNIQUE (ticket_id, open_link),
    CONSTRAINT chk_improvement_tickets_open_link CHECK (open_link IS NULL OR open_link = 1),
    CONSTRAINT fk_improvement_tickets_improvement FOREIGN KEY (improvement_id) REFERENCES improvements (id),
    CONSTRAINT fk_improvement_tickets_ticket FOREIGN KEY (ticket_id) REFERENCES tickets (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

- **The serial:** `IM-YYYY-MM-NNN` from the IST start date, through `serial_counters` row
  `IM:YYYY-MM` (`backend/local_db.py:145`, "shared by the serials (TK-, …)"). `VARCHAR(16)` as
  `tickets.serial`; past 999 the number grows (the ticket rule, `backend/tickets_core.py:82`).
- **`state`:** an ENUM with the one value of this step (D3). R05.4 appends its values at the end,
  as v19 appended `scheduled` to `tickets.state` (an append changes no row).
- **`unit_id`, `equipment_id`:** the first ticket's `tickets.unit_id` and `tickets.equipment_id`
  (the machine, never a component). They never change in this step: the remove rule (§ 5.3) keeps
  a ticket of this machine on the record. The site is `units.site_id`. A ticket's unit never
  changes (`backend/tickets.py:456`, "The unit never changes"), so the improvement's site is fixed
  too.
- **`lead_id`:** required; the rule is § 5.6.
- **Text:** `title` 1–120 characters, `problem` 1–2000 (§ 5.2). utf8mb4, so Tamil text fits; MariaDB
  counts characters, not bytes, in `VARCHAR(n)`.
- **`open_link`:** see D4. In this step every link row has 1, because every improvement is open.
  The **NULL rule** (a UNIQUE key allows several rows with NULL) is MariaDB's documented behaviour
  for InnoDB unique indexes; `test_migration_v36.py` proves it (§ 8.1), so it is not a guess.
- **Removing a link** deletes its row (D9). No row of `improvements` is ever deleted.
- **Re-run safety:** `IF NOT EXISTS` on both tables; a half-applied v36 (the first table made, the
  second not) runs again.
- **No precondition:** two new tables meet no production row. **Rollback:** the previous release
  does not read the new tables. The `IM:` counter rows stay in `serial_counters`, unused.

### 4.2 What is computed, never stored

- Each linked ticket's downtime: `ticket_times(events, now)["downtime_minutes"]`
  (`backend/tickets_core.py:753`), an open ticket's to now, as on the ticket page.
- The loss: the number of linked tickets, the number with intensity *critical* (breakdowns), the
  sum of their downtime.
- Each linked ticket's `removable` (§ 5.3) and the improvement's `is_open`.
- The improvements on the ticket detail: from `improvement_tickets`.

## 5. Rules

### 5.1 The serial helper

- `format_serial(prefix, year, month, number)` → `f"{prefix}-{year:04d}-{month:02d}-{str(number).zfill(3)}"`;
  `serial_scope(year, month, prefix="TK")` → `f"{prefix}:{year:04d}-{month:02d}"`.
- `format_ticket_serial(year, month, number)` = `format_serial("TK", year, month, number)`.
  `tickets.py:820` calls `serial_scope(now.year, now.month)` unchanged, so TK serials are as before.
- `improvements_core.SERIAL_PREFIX = "IM"`. R03.3 reuses both functions with `"PM"`.

### 5.2 The fields

| Field | Create | `PUT` | Rule and message (field) |
|---|---|---|---|
| `ticket_id` | required | not taken | integer ≥ 1, not a boolean: "Choose a ticket" (`ticket_id`) |
| `title` | required | optional | text, trimmed, 1–120: "Enter a title" / "Title: up to 120 characters" / "Title must be text" (`title`) |
| `problem` | required | optional | text, trimmed, 1–2000: "Describe the problem" / "Problem: up to 2000 characters" / "Problem must be text" (`problem`) |
| `lead_id` | required | optional, not `null` | integer ≥ 1, then § 5.6: "Choose a lead" (`lead_id`) |

- An absent field on a `PUT` stays as it is. A field equal to the stored value is not written. A
  `PUT` that changes nothing answers 200 with the detail and writes nothing (no `updated_at`).
- Unknown body fields are ignored, as `clean_body`'s validators do elsewhere.
- `validate_improvement(body, creating)` in `improvements_core.py` returns `(clean, errors)` for
  `clean_body` (`backend/api_common.py:121`).

### 5.3 Start, add, remove: the ticket rules

`improvements_core` holds them as pure functions; the shell feeds them the locked rows.

- **Start** (Q1.1 a): the ticket's state is `back_in_service` or `closed` (`START_FROM_STATES`).
  Otherwise 409 "Start an improvement when the ticket is back in service or closed" (`ticket_id`).
- **Not a fault:** a ticket closed as not a fault (`tickets.not_a_fault = 1`) can neither start an
  improvement nor be added: 409 "This ticket was closed as not a fault. There is nothing to
  analyse." (`ticket_id`). D7.
- **A scrapped machine** (BR1-06): a closed ticket's machine may be scrapped later
  (`_check_no_open_tickets`, `backend/equipment.py:477`, counts open tickets only). Its tickets
  may still start or join an improvement: the analysis is about the plant and the class (TPM
  yokoten, R05.6), not the one machine. Nothing reads `equipment.lifecycle`, and no lock is added.
- **Add** (Q1.1 a): any state. The ticket must be at the improvement's site (its unit's site):
  otherwise 400 "Choose a ticket from this site" (`ticket_id`).
- **The ticket must be visible** to the user through the tickets' access predicate
  (`_visible_condition`, `backend/tickets.py:180`). On start, outside it is 404 (the ticket is the
  anchor, as every ticket route). On add, outside it, or an unknown id, is 400 "Choose a ticket
  from the list" (`ticket_id`): nothing tells the user that the ticket exists.
- **One open improvement per ticket** (Q1.4 a). A ticket with an open link: 409 "TK-2026-10-002
  is already in IM-2026-10-001" (`ticket_id`). On add, a ticket already in *this* improvement:
  409 "This ticket is already in this improvement" (`ticket_id`). The unique key
  `uq_improvement_tickets_open` catches a race (§ 5.4); `UNIQUE_KEY_ERRORS` maps it to 409 "This
  ticket is already in an open improvement. Reload the page." (`ticket_id`).
- **Add or remove needs an open improvement:** 409 "This improvement is closed" when its state is
  not in `improvements_core.IMPROVEMENT_OPEN_STATES`. In this step every improvement is open; the
  check is written now so R05.4 needs no change here.
- **Remove** (BR1-02 a): the link must exist: otherwise 404 "Not found". The improvement keeps at
  least one ticket of its own machine: removing the last linked ticket whose `equipment_id` is the
  improvement's is refused, 409 "An improvement keeps a ticket of HP003." (the machine's code;
  `removal_error(ticket, links, machine_code)` in `improvements_core`). The rule also keeps the
  record from ever having no ticket. The ticket row is not written.
- **`removable`** on each ticket of the detail: `is_open and removal_error(ticket, links,
  machine_code) is None` (BR2-03), the same function the `DELETE` route calls, so the two cannot
  drift apart. S068 shows the remove button only where it is true.
- **The ticket detail** (`_detail`):
  - `improvements`: `[{id, serial, state}]`, the ticket's links, **newest first by
    `improvements.id DESC`** (the serial order, BR1-13). Empty unless the user holds
    `improvement:read` at the ticket's site, so nothing shows to a storekeeper or to someone
    without the key.
  - `can_start_improvement`: true when the user holds `improvement:edit` at the ticket's site, the
    start rule holds, the ticket is not a not-a-fault, and it has no open link.

### 5.4 Locks

The database runs REPEATABLE READ. A locking read (`FOR UPDATE`, `LOCK IN SHARE MODE`) sees the
newest committed row. A plain read sees the snapshot taken at the transaction's first plain read.
Every decision below is made from a locking read, or from a plain read whose snapshot starts after
the lock that guards it is held.

**The global order** (`backend/equipment.py:9`): (1) node … (6) the serial counter → **(6b) the
improvement row (new)** → (7) the ticket row. The improvement row sits after the counter and
before tickets.

**Start** (`POST /api/improvements`), in one `transaction`:

1. (6) `next_counter(cur, serial_scope(now.year, now.month, "IM"))`: the `IM:YYYY-MM` row, X. Only
   starts touch it, so two starts serialise here. Its `SELECT last_value` is the transaction's
   first plain read, so the snapshot starts after this lock is granted: a start committed before
   is seen by every plain read below.
2. (7) The ticket row `LOCK IN SHARE MODE`: `state`, `not_a_fault`, `unit_id`, `equipment_id`. The
   start rule and the not-a-fault rule are decided from this row. A send-back holds the ticket
   `FOR UPDATE`; the two serialise, and a start after a send-back sees `in_progress` and is refused.
3. Plain reads: the tickets' access predicate (`read_ticket`, `backend/tickets.py:241`: 404), the key
   `improvement:edit` at the ticket's site (`require_perm_at`: 403), the open-link check (409 with
   the serial), the lead (§ 5.6).
4. Insert `improvements` (its foreign keys take shared locks on the unit, the machine and the lead's
   `people` row).
5. Insert `improvement_tickets` (shared locks on the new improvement, its own, and the ticket, already
   held).
6. Read the detail inside the transaction (the raise's pattern, `backend/tickets.py:847`).

A refused start rolls back, the counter bump included, so no number is lost (`next_counter`'s
docstring, `backend/db_helpers.py:78`).

**Add ticket** (`POST /api/improvements/<id>/tickets`):

1. (6b) The improvement row `FOR UPDATE` (`state`, `unit_id`). 404 when missing.
2. (7) The ticket row `LOCK IN SHARE MODE` (`state`, `not_a_fault`, `unit_id`). 400 when missing.
3. Plain reads, the transaction's first: the improvement through its access predicate (404), the key
   at its site (403), the open state (409), the ticket through the tickets' predicate (400), its
   site (400), not a fault (409), its links (409 twice, § 5.3).
4. Insert the link.

**Remove ticket** (`DELETE /api/improvements/<id>/tickets/<ticket_id>`): (1) (6b) the improvement
`FOR UPDATE` (`state`, `equipment_id`); (2) plain reads: predicate 404, key 403, open state 409,
the link 404, the links with their tickets' `equipment_id` (409 by the removal rule); (3) delete
the link row. The links read is safe: every link write takes (6b) first, so no other link of this
improvement changes while (6b) is held. A ticket's `equipment_id` changes only through the ticket
edit, which changes the component, never the machine (`machine_and_component`).

**Edit** (`PUT /api/improvements/<id>`): (1) (6b) `FOR UPDATE`; (2) plain reads: predicate 404,
key 403, and the lead (§ 5.6) **only when `lead_id` differs from the stored value** (BR1-07);
(3) `update_row` (a new `lead_id` takes a shared lock on that person).

**Reads** (list, detail, leads, the ticket detail): plain, no lock.

**Why one open link is race-free.** Two writers that link the same ticket both hold its shared
lock (step 2), so neither waits for the other there. Both may pass the plain check. Their link
inserts then meet on `uq_improvement_tickets_open`: the second insert waits for the first
transaction, then fails with a duplicate key, which answers the 409 of § 5.3. Two starts
serialise earlier, on the counter, so the second sees the first's link in its plain check and
answers the message with the serial.

**No new deadlock cycle, checked against the notes:**
- *Ticket writes* (`backend/tickets.py:22`): every ticket write locks (7) `FOR UPDATE` and then
  only shared locks on the unit, machine and component (index changes), never an improvement. A
  start or an add holds only a **shared** ticket lock while it waits for anything, so a ticket
  write waits for it, or it waits for the ticket write; never both. tickets.py's rule "nothing that
  holds a ticket lock then takes an equipment, unit or counter lock" gains one stated exception:
  improvements.py holds a *shared* ticket lock and then takes the improvement insert's *shared*
  foreign-key locks on the unit, the machine and the person. No path holds those rows `FOR
  UPDATE` and then waits for a ticket `FOR UPDATE`:
  - a unit edit holds the unit `FOR UPDATE` and then counts its tickets `LOCK IN SHARE MODE`
    (`backend/masters.py:287`, `:320`): shared with shared, so it does not wait for a start;
  - a scrap holds the machine `FOR UPDATE` and counts open tickets with a plain read
    (`backend/equipment.py:477`): no ticket lock;
  - a raise of a repeat holds the machine (1) and takes the earlier ticket shared: shared with
    shared.
- *The person row:* a start's insert takes the unit's and the lead's shared locks after the ticket.
  A person's site-row edit (masters.py: person `FOR UPDATE`, then memberships, person_units, units)
  can deadlock with a start that names that person as lead. This is the same shape as tickets'
  accepted deadlock "a person's site-row edit against a raise naming that person"
  (`backend/tickets.py:61`). **Accepted:** InnoDB rolls one side back (1213), a rare JSON 500, and a
  retry gives the right answer.
- *The counter (6):* only starts take `IM:` rows; a ticket raise takes its own `TK:` row.
- *(6b) → (7):* add takes the improvement, then the ticket. Nothing takes a ticket and then an
  improvement row: ticket writes never touch improvements, and a start inserts its own new row.

The coder writes this as improvements.py's LOCK ORDER note, and adds the (6b) line and an
`improvements.py` bullet to equipment.py's note, and the exception to tickets.py's note.

### 5.5 Permissions

| Key | Holders | Site-scoped | Comment in `config_rbac.py` |
|---|---|---|---|
| `improvement:read` | `maint_operator`, `it_admin` (so supervisor, technician, engineer, manager inherit) | yes | S067, Q1.3 a: TPM wants the floor to see the analysis; IT admin reads only |
| `improvement:edit` | `maint_engineer` (so manager) | yes | S067, Q1.3 a: engineers lead the analysis; not IT admin (as R03 Q2.2 for PM) |

- The storekeeper holds neither. Admin bypasses (as everywhere).
- **Where each is checked**, always 404 (the predicate) before 403 (the key at the site):
  - list, detail: `@require_perm("improvement:read")`, then the access predicate (§ 5.7);
  - start: `@require_perm("improvement:edit")`, then `read_ticket` (404), then `require_perm_at` at
    the ticket's site (403);
  - add, remove, edit: `@require_perm("improvement:edit")`, then the improvements' predicate (404),
    then `require_perm_at` at the improvement's site (403);
  - leads: `@require_perm("improvement:edit")`, then the anchor (§ 6: `read_ticket` or the
    improvements' predicate, 404), then `require_perm_at` at the anchor's site (403), as
    `_picker_anchor` does (`backend/tickets.py:660`; BR1-14).
- **What the screens need:** the detail sends `permissions` (`permissions_at_site` of its site,
  `backend/auth_utils.py:466`) and `is_open`; the ticket detail sends `can_start_improvement`. S068
  shows every control from these, so no button ends in a 403.
- **No personal data** beyond names: the lead and the starter show by name; no login, role or
  email.

### 5.6 The lead

- The lead is an **active person with a membership at the improvement's site whose role there
  grants `improvement:edit`** (today engineer or manager). The rule reads the key, not a role list,
  so it follows `config_rbac` (`improvements_core.may_lead(role)` =
  `"improvement:edit" in compute_permissions([role])`, `backend/access_core.py:44`). D6.
- **Reuse, no new membership query** (BR2-02): the lead check and the detail's `lead.may_lead`
  call `tickets.person_at_site(cur, person_id, site_id)` (`{id, name, role}`, or None for no
  membership at the site or an inactive person) and then `may_lead(row["role"])`. The leads list
  is `tickets.people_at_site(cur, site_id)` (active people with a membership at the site, by name)
  filtered by `may_lead(row["role"])`, answered as `{id, name}`. So the people picker of tickets
  and the lead rule agree on what "at the site" means (`memberships` has one row per person and
  site, `backend/local_db.py:243`).
- Otherwise 400 "Choose an engineer or manager of this site" (`lead_id`).
- A lead who later leaves the site or is deactivated stays on the record (history). A `PUT` that
  sends the same `lead_id` does not check it again (§ 5.4 Edit). The detail's `lead.active` and
  `lead.may_lead` tell S068's dialog to mark such a lead "(not a lead now)".

### 5.7 Access to improvements

- **The predicate** (mirrors the tickets', `backend/tickets.py:180`): an improvement is visible
  when its unit, or its machine's current unit, is among the units where the user holds
  `improvement:read` (`accessible_unit_ids(cur, "improvement:read")`). Outside it: 404, as tickets.
- **Linked tickets in the detail** go to every reader of the improvement, with symptom, cause and
  downtime, also a ticket of another unit of the site. The ticket page applies its own predicate
  (404). D8.
- **Unit access:** an operator at MCC2 sees the improvements of MCC2 machines; a manager with all
  units sees the site's; IT admin (`equipment:read_all_units`) sees every unit's.

### 5.8 The database down

Every new route goes through `get_db()`: 503 while the database is down or missing (§ Yantra
Specifics, *DB may not exist*). No background task, no alert.

## 6. API

S068 builds on this table as it stands.

| Route | Key | Body / query | Answer |
|---|---|---|---|
| `GET /api/improvements` | `improvement:read` | `state=open\|closed` (default open), `unit_id`, `page`, `per_page` | `{items, total, page, per_page}`; item: `{id, serial, state, title, machine{id, code, name}, unit{id, code, site_id, site_code}, lead{id, name}, loss{tickets, breakdowns, downtime_minutes}, created_at}`; newest first by `improvements.id DESC` |
| `GET /api/improvements/<id>` | `improvement:read` | — | the detail (below); 404 outside the predicate |
| `POST /api/improvements` | `improvement:edit` | `{ticket_id, title, problem, lead_id}` | 201, the detail; 400, 403, 404, 409 per § 5 |
| `PUT /api/improvements/<id>` | `improvement:edit` | `{title?, problem?, lead_id?}` | 200, the detail |
| `POST /api/improvements/<id>/tickets` | `improvement:edit` | `{ticket_id}` | 201, the detail |
| `DELETE /api/improvements/<id>/tickets/<ticket_id>` | `improvement:edit` | — | 200, the detail |
| `GET /api/improvements/leads` | `improvement:edit` | `ticket_id` (through `read_ticket`, 404) or `improvement_id` (through the improvements' predicate, 404); neither: 400 "ticket_id or improvement_id is required" | `{items: [{id, name}]}` by name; 403 without the key at the anchor's site |
| `GET /api/tickets/<id>` | `ticket:read` (unchanged) | — | adds `improvements: [{id, serial, state}]` (by `improvements.id DESC`) and `can_start_improvement` |

**The detail:** `{id, serial, state, is_open, title, problem, machine{id, code, name}, unit{id,
code, site_id, site_code}, lead{id, name, active, may_lead}, created_at, created_by,
created_by_name, updated_at, updated_by, tickets: [{id, serial, state, intensity, is_breakdown,
occurred_at, not_a_fault, machine{id, code, name}, failure_mode{id, code, label}|null, cause{id,
code, label}|null, downtime_minutes, removable}], loss{tickets, breakdowns, downtime_minutes},
permissions}`.

- `unit.site_id` (BR2-06) lets S068 pass the site to `GET /api/tickets?site_id=`; `s.id AS
  site_id` is already selected for tickets (`backend/tickets.py:152`).
- Each ticket's `machine` (BR2-01) shows which machine it is on, so S068 can tell a ticket of
  another machine from one of the improvement's machine and explain `removable`.
  `_TICKET_COLUMNS` already joins the machine (`backend/tickets.py:139`).
- `tickets` are ordered `occurred_at DESC, id DESC` (BR2-04).
- The routes declare their ids as `<int:improvement_id>` and `<int:ticket_id>` (BR2-05), so
  `/api/improvements/leads` never meets `/<id>` and a non-numeric id is a 404, as `tickets_bp`
  does.
- `created_by_name` is the person whose login is `created_by`, or the login itself when there is
  none. `lead.may_lead` is § 5.6's rule today at the improvement's site.
- The events of all linked tickets are read in one query (`WHERE ticket_id IN (…)`), then grouped
  for `ticket_times`. The list does the same for the page's linked tickets (no N+1).
- `unit_id` and `page` are read by `int_arg(…, minimum=1)`; `state` by `enum_arg` (400 on another
  value). `per_page` 1–200 (`MAX_PER_PAGE`), default 50, as the Tickets list.

## 7. Design decisions

- **D1. Routes under `/api/improvements`, a blueprint of their own.** The improvement is its own
  record; its routes do not grow `tickets.py` (1418 lines). The screens' paths are S068's (D1
  there).
- **D2. The serial helper stays in `tickets_core.py`, with a prefix.** It is two short functions,
  and the TK callers and tests stay as they are. Rejected: a new `serials_core.py` (one more file
  for two functions; R03.3 may move them if PM wants).
- **D3. Only the state *Analysing* in this step.** The ENUM holds one value; R05.4 appends its
  states, as `tickets.state` grew in S019. "Open" is `improvements_core.IMPROVEMENT_OPEN_STATES`
  (today `("analysing",)`), so every check that asks "open?" is written once and R05.4 only widens
  the tuple. Rejected: all seven R05.4 states now (states with no way in or out, and names R05.4's
  brief may still change); a *Dropped* state now (it needs a reason and a record of who dropped it,
  which is R05.4's timeline).
- **D4. One open link per ticket by a unique key on `(ticket_id, open_link)`.** The database
  enforces Q1.4 even in a race, with no ticket `FOR UPDATE` from improvements.py (which would block
  ticket work and add a lock edge, § 5.4). R05.4 sets `open_link` to NULL when an improvement
  closes, so a *not effective* follow-up can take the same tickets. Rejected: `UNIQUE (ticket_id)`
  alone (R05.4 would have to change the key on a table with rows); a check-then-insert under a
  ticket `FOR UPDATE` (a new exclusive locker of tickets).
- **D5. The unit and machine are the first ticket's, stored on the improvement, and kept true.**
  The list filters by them and the predicate reads them, as tickets store `unit_id`. The remove
  rule (§ 5.3) keeps a ticket of that machine on the record, so *Where* always names a machine the
  record analyses. The machine's lifecycle does not matter: a scrapped machine's tickets may start
  or join (BR1-06). Rejected: deriving them from the links (the list's unit would change when a
  ticket is removed); allowing the machine's last ticket to go (*Where* would name a machine with
  no ticket).
- **D6. The lead rule reads the key, not a role list.** `may_lead(role)` asks whether the role grants
  `improvement:edit`, so a later change of the key's holders changes the lead list too. Rejected: a
  new `config_rbac.IMPROVEMENT_LEAD_ROLES` (a second list to keep in step with the key).
- **D7. A not-a-fault ticket cannot be analysed.** Not a fault means the equipment had no fault;
  there is no failure to find a cause for. Rejected: allow it (a false alarm again and again may
  point at a sensor, but that is a new ticket on the sensor).
- **D8. Linked tickets go in full to every reader of the improvement.** The improvement is a
  shared record of the site; its value is in seeing the losses together. The ticket page still
  opens only where the reader may read it. Rejected: hide rows of tickets the reader cannot open
  (the loss sum would not match the rows).
- **D9. *Remove ticket*, a scope addition beyond R05.1** (§ 9 Q2, accepted). Without it, a ticket
  added by mistake is stuck in the improvement (Q1.4) until R05.4's *Drop*. The server decides
  `removable`, so the screen never offers a refused removal. Rejected: no removal in this step.

## 8. Tests and acceptance

### 8.1 Migration (`backend/tests/test_migration_v36.py`)

- A fresh database: both tables, their keys, the CHECK, `state` ENUM `('analysing')`.
- A v35 database with tickets: every old row kept; the new tables empty.
- The unique key: two link rows with the same `ticket_id` and `open_link = 1` are refused (1062);
  two with `open_link` NULL are allowed; `open_link = 2` is refused by the CHECK.
- A re-run of v36 changes nothing (`_schema()` equal, as `test_migration_v35.py`).

### 8.2 Backend (`test_improvements_core.py`, `test_improvements_api.py`, `test_tickets_core.py`, `test_rbac.py`)

**Core** (`test_improvements_core.py`): `validate_improvement` (each message of § 5.2: missing,
empty after trim, 120 / 121 and 2000 / 2001 characters, a number, a boolean `lead_id`, `null`
`lead_id` on a `PUT`); `start_error` for each ticket state and not a fault; `removal_error` (the
machine's only ticket, the machine's second ticket, a ticket of another machine, the message with
the code); `may_lead` for every site role; the loss of a list of tickets (no tickets, defects only,
a mix).

**Serial** (`test_tickets_core.py`, `TestSerial`): `format_serial("IM", 2026, 10, 1)` =
`"IM-2026-10-001"`, past 999; `serial_scope(2026, 10, "IM")` = `"IM:2026-10"`; the TK cases unchanged.

**API** (`test_improvements_api.py`), with `ticket_helpers.py`'s ticket set-up and the session DB;
each test makes its own tickets, so the kept worker database gives the starting state. "Another
site" means a person with **no membership at the record's site** (404 by the predicate); "a key
missing here" means a person who is **operator at this site and engineer at another** (the
predicate passes, the key does not: 403). BR1-03.
- **Start:** from a back-in-service ticket and from a closed one (201, serial `IM-YYYY-MM-NNN`,
  the next start gets the next number); from a closed ticket whose machine was scrapped after
  (201, BR1-06); from `raised`, `in_progress`, `scheduled` (409); a not-a-fault ticket (409); a
  ticket already in an open improvement (409 naming both serials); a refused start leaves no gap in
  the numbers; an unknown ticket (404); an engineer of another site (404); an operator here who
  is engineer elsewhere (403); an operator, a technician, a supervisor and IT admin (403); the lead
  a technician, an engineer of another site, an inactive engineer, missing (400 on `lead_id`); the
  title and problem bounds (400). The ticket row's `updated_at` is unchanged after a start.
- **Detail:** the tickets with symptom, cause, downtime and `removable`; the loss; an open
  breakdown counts to now; a defect counts 0; an operator of the unit reads it; an operator of
  another unit gets 404; the storekeeper 403; `permissions` carry the keys at the site; `is_open`
  true; `lead.may_lead` false after the lead's membership is removed through the API
  (`DELETE /api/masters/people/<person_id>/sites/<site_id>`, `backend/masters.py:1482`) or with a
  second `user_at_sites` spec (`backend/tests/conftest.py:530`), so the test writes no SQL
  (BR2-07); each ticket carries its `machine`, and a ticket of another machine shows that
  machine's code.
- **Add ticket:** a raised ticket of the same site (201); a ticket of another site that the user
  can see (400); an invisible ticket (400, the same text as unknown); already here (409); in
  another open improvement (409); not a fault (409); an engineer of another site (404); an
  operator here who is engineer elsewhere (403).
- **Remove:** a ticket of another machine (200, the ticket row untouched); the machine's second
  ticket (200); the machine's last ticket (409 "An improvement keeps a ticket of <code>."), also
  when tickets of other machines remain; a ticket not linked (404); then the removed ticket can
  start a new improvement.
- **Edit:** each field; a `PUT` with no change writes nothing (`updated_at` stays NULL); `lead_id`
  `null` (400); a lead no longer at the site kept when unchanged (200), refused when sent as a new
  lead (400).
- **List:** open by default, newest first; `state=closed` empty; `state=x` (400); `unit_id`
  filter; an operator sees only the improvements of their units; `loss`; `unit.site_id`; paging.
- **Routes:** `/api/improvements/abc` answers 404; `/api/improvements/leads` is the leads route,
  not a detail.
- **Leads:** only active engineers and managers of the anchor's site, by name; neither anchor
  (400); an unknown or invisible anchor (404); an engineer of another site (404); an operator here
  who is engineer elsewhere (403).
- **Ticket detail:** `improvements` empty, then the link after a start; two improvements (after a
  remove and a new start) by `id DESC`; `can_start_improvement` true for an engineer on a
  back-in-service ticket, false on a raised one, on a not-a-fault one, on one in an open
  improvement, for an operator, for IT admin; `improvements` empty for a user without
  `improvement:read` at the site.
- **The database down** (`db_down`, `backend/tests/conftest.py:212`): the list answers 503.

**RBAC** (`test_rbac.py`): `test_role_matrix` with the new keys (§ 3); `test_improvement_keys`:
the holders of § 5.5 and both keys in `SITE_SCOPED`.

### 8.3 Existing tests that run again

- `backend/tests/test_tickets_api.py`, `test_ticket_work_api.py`: the ticket detail gains two
  fields; no test asserts the exact key set, so they stay green.
- `backend/tests/test_migration_v20.py` … `v35`: unchanged (each slices its own range).
- **IT admin's role-matrix row** (`test_rbac.py`) gains only `improvement:read`; a test that
  compares `/api/auth/me`'s permissions with `compute_permissions(["it_admin"])`
  (`backend/tests/test_auth.py:388`) follows by itself.

### 8.4 Automated (e2e)

None in this step: no screen changes. The ticket detail only gains fields, which no spec reads.
The coder runs the whole browser suite at Normal once at the end, as the step workflow asks, to
show the added fields break nothing. The browser tests of improvements are S068's.

### 8.5 On a real device

None. S068 holds the Tamil-text check.

### 8.6 Acceptance

- All unit suites green; the whole browser suite at Normal green once at the end.
- TK serials unchanged; the first improvement of a month is `IM-YYYY-MM-001`.
- `docs/schema.md` and `docs/schema.html` show v36.

## 9. Open questions and assumptions

- **The split** (BR1-01, accepted 30-10-2026). The approved roadmap's own rule ("If a brief passes
  25 files, it splits there") cut R05.1 at the API: this step is the backend (14 code and test
  files), S068 the screens (`docs/steps/S068-improvement-screens/1-brief.md`). S067 is coded first;
  S068 builds on § 6 as written. Nothing is visible to users until S068.
- **Q2. *Remove ticket* in this step?** Answered 30-10-2026: **(a) yes**, with BR1-02's rule (the
  machine's last ticket stays). A scope addition beyond R05.1, for KLA at gate B.
- **Assumption:** the improvement's unit and machine are the first ticket's (D5). Tickets added
  later may be on other machines of the site; the list shows the improvement under the first
  ticket's unit.
- **Assumption:** the problem is required at start; S068's dialog prefills it from the ticket.
- **Assumption:** R05.4 owns `open_link` (sets NULL on close and drop) and the history of what this
  step overwrites (§ 2, *Departure*).

## 10. Amendments

### A1 — The ticket detail lists only the improvements the reader can open (30-10-2026, from CR1-01)

- **Why:** § 5.3 listed every link on the ticket detail to anyone with `improvement:read` at the
  ticket's site, while opening an improvement checks its own unit or its machine's unit (§ 5.7).
  A ticket of an MCC2 machine added to an improvement started on MCC1 would show its link to an
  MCC2-only operator, who then gets "Not found".
- **Rule:** the ticket detail's `improvements` list is filtered by the improvements' own access
  predicate (`unit_access_condition` on the improvement's unit and its machine's unit, key
  `improvement:read`). An improvement the reader cannot open is left out of the list. The
  unfiltered `improvement_links` stays for the one-open-link checks of start and add.
- **API:** the shape of § 6 is unchanged; only which items appear. S068 needs no change.
- **Tests:** a reader with only the ticket's unit does not see the link; a reader of both units
  does.
- **Approval:** decided by the orchestrator under KLA's delegation for R05 ("start coding unless
  a defining question"), 30-10-2026. The rule narrows what a reader sees, and changes no other
  behaviour. Shown to KLA at gate B.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 30-10-2026

The step is split at the API (BR1-01): the screens moved to S068. Sections changed: header (Status,
From), § 1, § 1 Out of scope, § 3 (frontend, e2e and screen docs removed), § 4.1 notes, § 4.2,
§ 5.3, § 5.4 (Remove, Edit), § 5.5, § 5.6, § 5.8 (*Screens* removed; *The database down* renumbered),
§ 6 (list `loss`, detail `is_open`, `removable`, `not_a_fault`, `lead.may_lead`, the orderings,
the leads anchors), § 7 (D1, D5, D9; D10 and D11 moved to S068), § 8.2, § 8.3, § 8.4, § 8.5,
§ 8.6, § 9.

| Finding | Answer |
|---|---|
| BR1-01 minor | Accepted (b): split at the API, by the approved roadmap's rule. S067 keeps the backend; S068 holds the screens. § 1, § 3, § 8.4, § 9. |
| BR1-02 minor | Accepted (a): the machine's last ticket cannot be removed, 409 "An improvement keeps a ticket of HP003."; `removable` per ticket in the detail. § 5.3, § 5.4 Remove, § 6, D5, D9, § 8.2. |
| BR1-03 minor | Accepted (a): the order stays (404 before 403). Tests: another site → 404; operator here and engineer elsewhere → 403, for Start, Add and Leads. § 5.5, § 8.2. |
| BR1-04 minor | Accepted (a): the *Add ticket* dialog is a form (radio rows, `"Cancel"` / `"Add ticket"`). In S068 § 5. |
| BR1-05 minor | Accepted (a): a 403 on the list shows a plain line, no Retry. In S068 § 5. |
| BR1-06 minor | Accepted (a): a scrapped machine's tickets may start or join. § 5.3, D5, § 8.2. |
| BR1-07…BR1-14 nits | Accepted. In S067: BR1-07 § 5.4 Edit and § 5.6; BR1-13 § 5.3, § 6; BR1-14 § 5.5, § 6. In S068: BR1-08 (prefill), BR1-09 (no not-a-fault rows), BR1-10 (the screens set-up), BR1-11 (button sizes), BR1-12 (one loss text). |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 30-10-2026

Sections changed: header (Status), § 3 (`tickets.py` helpers made public), § 5.3 (`removable`),
§ 5.6 (reuse), § 6 (`unit.site_id`, each ticket's `machine`, orderings, int routes), § 8.2.

| Finding | Answer |
|---|---|
| BR2-01 minor | Accepted (a): each entry of `tickets[]` carries `machine{id, code, name}` (§ 6, § 8.2). S068 § 5.4 shows the code when it differs from the improvement's machine. |
| BR2-02 minor | Accepted (a): `_person_at_site` and `_people_at_site` become public (`person_at_site`, `people_at_site`) and are reused for the lead check, `lead.may_lead` and the leads list (§ 3, § 5.6). |
| BR2-03…BR2-07 nits | Accepted: BR2-03 § 5.3 `removable` formula; BR2-04 § 6 `occurred_at DESC, id DESC`; BR2-05 § 6 int routes, § 8.2; BR2-06 § 6 `unit.site_id` in the detail and the list item (also S068 BR1-04); BR2-07 § 8.2 the membership removed through the API or `user_at_sites`. |
