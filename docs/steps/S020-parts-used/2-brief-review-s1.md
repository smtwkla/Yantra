```
Step: S020 — Parts used
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 22-10-2026
```

Reviewed against: 3df667c + uncommitted S025 and S019

# S020 — Staleness review, round s1

**Verdict: no `blocker` or `major` finding is open.** The design and every
decision the user approved still hold. Four `minor` findings and three `nit`s
need wording in the brief before the coder starts.

**What I compared.** The brief's *Where* files and the modules they call,
between `28d3be3` and the working tree now: S024 as committed (`3df667c`), and
S025's and S019's uncommitted code (`git diff 28d3be3`, plus the untracked
files `backend/tests/fixtures/`, `test_migration_v20.py`,
`test_migration_v21.py`, `test_errors.py`, `test_health.py`,
`frontend/src/views/tickets/ScheduleFields.vue`). I read S025's and S019's
impl reports and code reviews r1, and S019's staleness review s1.

**What changed that touches S020:**
- `local_db.py`: one squashed migration v20 with `_PRECONDITIONS`
  (`{20: _v20_shape_check}`) and `MigrationBlocked`; S019's v21 took the
  number the brief left open, with a comment saying why it needs no
  precondition; `LATEST_VERSION = _MIGRATIONS[-1][0]`.
- `tickets_core.py`: `SCHEDULED`; `MOVES["not-a-fault"]` from `(RAISED,
  ACKNOWLEDGED, SCHEDULED, IN_PROGRESS)`; `allowed_moves(state, held_keys,
  has_repeat=False)`; `Move.key_at` / `Move.keys`; `_optional_date`,
  `_optional_bool`; `ticket_times` with six keys.
- `tickets.py`: the lock-order note rewritten (S025 CR1-02, extended by S019);
  `_check_component` reads the component `LOCK IN SHARE MODE` and its parent
  plain; `_lock_ticket(cur, id, key)` also takes a function of the locked
  state; `_moves` entries carry `asks_machine_stopped`; `_LOCK_TICKET` selects
  the plan columns; `_ticket_out(row, today)`; the labour routes unchanged.
- `equipment.py`: the lock-order note lists S025's two shared reads; the scrap
  refusal gives the count (`close_tickets_first`).
- `TicketDetailView.vue`: `state-badge`, the plan line, the plan buttons, the
  times card with the waiting split and *Planned stop*, the timeline's plan
  and stopped lines. `MoveDialog.vue`: `ScheduleFields`, the stopped question,
  `SHOWN_FIELDS` grown; the reload rule unchanged (`!value.field && status ===
  409`). `LabourPanel.vue`: `minutesText(…, { days: false })` and
  `invalid-feedback d-block`. `EditTicketDialog.vue`: `d-block` only.
- Tests and e2e: `test_migration_v20.py` pins `V20` to version 20,
  `test_migration_v21.py` pins `(20, 21)` and imports the v20 helpers;
  `support/tickets.js` gains `postAs` (private), `regradeByApi`, `causeId`,
  `istDay`, `shownDay`; `seed_e2e.py` connects to the e2e database itself
  (`e2e_connection`, `check_target`) for the overdue ticket.
- `.claude/CLAUDE.md`: a *Migrations (S025)* bullet, and the SMTW-Review point
  "a migration that touches rows that exist in production carries a
  `_PRECONDITIONS` entry and a test from the production schema. Check both on
  every migration after v20."

## Findings

### BS1-01 — `minor` — The migration is v22; the brief must say it needs no precondition and name the upgrade-database test

**What changed.** S019 took v21 (`local_db.py`, `test_migration_v21.py`). S025
set the convention: a migration that cannot run on existing data gets a
`_PRECONDITIONS` entry, and the SMTW-Review audit checks every migration after
v20 for "a precondition and a test from the production schema". S019's v21
answers it with a comment above the migration ("No `_PRECONDITIONS` entry
(S019 BS1-02): …"). An upgrade is tested in `vel_yantra_upgrade` by building
the older schema with `_MIGRATIONS` pinned, then running the new list
(`test_migration_v20.py`: `_recreate`, `_migrate`, `_run`, `_schema`;
`test_migration_v21.py` imports them and pins `V21 = [m … if m[0] in (20,
21)]`).

**What is now wrong or missing.**
1. The Depends-on paragraph ("the next version after v20, whichever S019 or
   S020 is coded first takes v21"), § 3 ("the next migration",
   `test_migration_<next>.py`) and the first paragraph of § 4 ("S019 also
   claims v21 …") are settled: **v22** and `test_migration_v22.py`. S025's
   impl report already says "S020's v22".
2. The brief does not say whether v22 needs a `_PRECONDITIONS` entry. Fact:
   it does not. v22 creates one new table, `ticket_parts`, with `CREATE TABLE
   IF NOT EXISTS`, and touches no existing row. `parts_used` was never a
   table: it is the *Proposed* row in Plan.MD § 5 that the planner replaces
   (§ 3 Docs); no database, production included, holds it (checked:
   `backend/`, `tooling/`, the frozen fixture). The brief should say so, and
   direct the coder to write it in the comment above v22 as v21 does, so the
   audit's check passes on reading.
3. § 3 Tests: "`test_migration_<next>.py` (new): the table, its CHECKs and
   foreign keys; a re-run is a no-op." On the shared test database v22 is
   already applied when the tests start (`conftest` runs `ensure_schema`).
   The test must follow `test_migration_v21.py`: `_recreate()`, `_migrate`
   with `_MIGRATIONS` pinned to `(20, 21)`, then `(20, 21, 22)`; check the
   columns, `chk_ticket_parts_kind`, `chk_ticket_parts_quantity`, the two
   foreign keys and the three indexes; delete `db_version` 22, run again, and
   compare `_schema()`. Import the helpers from `test_migration_v20.py`, as
   v21's test does. The v20 and v21 tests pin their lists, so v22 breaks
   neither.

**Fix.** The wording above in the Depends-on paragraph, § 3 and § 4. No
design change.

- (a) State v22, "no precondition, because a new table only", and the
  upgrade-database test — **recommended**.
- (b) Add a `_PRECONDITIONS` entry for v22 anyway: it would check nothing.

### BS1-02 — `minor` — The lock-order notes were rewritten; the parts write is a third shared read, and it shares the repeat-raise deadlock

**What changed.** S025 CR1-02 and S019 rewrote the note in `tickets.py`. It
no longer has "the same sentence as S025's edit". It now says: working a
ticket "locks (7) explicitly, and nothing else explicitly"; a state change
re-checks the unit, machine and component foreign keys (shared locks); then a
list "Two reads take a shared lock, each the one a foreign key of the same
write takes anyway" (the edit's component; the repeat raise's earlier ticket);
then "Four deadlocks follow, accepted", the fourth being a repeat raise (the
machine (1), then the earlier ticket's shared lock) against a send-back of
that ticket (the ticket, then the machine's shared FK lock). `equipment.py`'s
note has the matching "Two of its shared locks fall on rows this module
locks" sentence.

**What is now wrong or missing.**
1. § 3 (`tickets.py`, `equipment.py`): "the same sentence as S025's edit" and
   "names the parts line among the writes that take the node's shared lock
   after (7)" point at text that no longer exists in that form. The parts
   add and the edit whose `node_id` changes are a **third bullet** in the
   "reads take a shared lock" list of `tickets.py` (the node row, the lock
   `fk_ticket_parts_node` takes at the insert anyway; a scrap holds it `FOR
   UPDATE`, so the two serialise), and a third item in `equipment.py`'s
   sentence. The parts line also joins the list of writes in "Working a
   ticket … locks (7) explicitly".
2. The parts write has the fourth deadlock's shape, and the brief's § 5.2 and
   § 7.8 do not say so. Sequence: a technician records a part on a ticket
   that is back in service (parts are allowed until closed) — the ticket (7)
   `FOR UPDATE`, then the node's shared lock; at the same moment an operator
   raises a repeat on that node — the node (1) `FOR UPDATE`, the insert, then
   `_recheck_repeat`'s shared lock on the earlier ticket. Each waits on the
   other: 1213, one side gets the JSON 500 "Something went wrong — try
   again", and a retry works. S025's edit already has this shape (an edit of
   the earlier ticket's component against a repeat raised on that component),
   and the note does not list it either. This is the accepted class of
   CR1-02, not a new design question: integrity holds, and the brief's "no
   new lock-order edge" argument (the explicit read takes only the lock the
   foreign key takes anyway) still stands.

**Fix.** Reword § 3's two note bullets to "a third bullet in the shared-read
list, in the note's own words", and add one sentence to § 5.2: "A repeat
raised on the node at the same moment as a part is recorded on the earlier
ticket can deadlock (the shape of the note's fourth accepted deadlock, which
S025's edit shares); the coder names the parts write there." Design unchanged.

- (a) The wording above — **recommended**.
- (b) Lock the node before the ticket: rejected already (§ 7.8), and it would
  not remove the deadlock with the raise, which holds the node first.

### BS1-03 — `minor` — *Not a fault* now also starts from scheduled

**What changed.** S019 added `SCHEDULED` to `MOVES["not-a-fault"]`'s
from-states, beside S025's `IN_PROGRESS`. Parts can be recorded on a
scheduled ticket: the brief's rule is "while the ticket is not closed"
(`_lock_open_ticket` refuses only closed), and that is right — a technician
who fits one part and schedules the rest has a line to record.

**What is now wrong.** § 1.5 lists the from-states as "raised, acknowledged,
and in progress since S025 § 1.10", and § 3 Tests says "not-a-fault refused
with lines (409, from in progress too)". Scheduled is missing from both.
A coder who tests the three named states leaves the fourth untested.

**Fix.** § 1.5: "from every from-state of `MOVES['not-a-fault']` (raised,
acknowledged, scheduled since S019, in progress since S025)". § 3 Tests: "from
scheduled and in progress too" (setup: `moves/schedule` as an engineer, then
`moves/not-a-fault` with a part line). One sentence in § 1.2: lines can be
added, changed and removed in any open state, scheduled included. No design
change.

### BS1-04 — `minor` — The e2e checks must name S024's conventions: the allowed 400s, the setup by API, the shared database

**What changed.** S025 BS1-03 and S019 BS1-03 set the conventions the suite
now has: `consoleWatch.allowFailedRequest(urlPart, status)` for every refused
request a test provokes (the console watch fails the test otherwise);
`expectFieldMessage(scope, text)`; setup through `raiseByApi` and `moveByApi`
(the flows use the screens); the three projects share one database, so a
test reads what it asserts about shared rows rather than assuming a count
(S025 decision 9).

**What is now wrong or missing in § 8.**
1. "A maker's part number without a maker shows the message beside *Maker*; a
   quantity of 0 beside *Quantity*" are 400s from `POST
   /api/tickets/<id>/parts` (the messages are the core's, § 5.1). The test
   must declare `consoleWatch.allowFailedRequest("/parts", 400)`, or the brief
   must say the panel pre-checks them client-side as `LabourPanel.save()`
   does for minutes. Recommended: the API decides, as § 5.1 says, and the
   test allows the 400.
2. Setup is by API, on the seed's extruder (`seed.extruder`, SMTW.MCC2: the
   operator sees that unit only, so the operator check works there):
   `raiseByApi("operator", …)`, `moveByApi("technician", id, "start")` for the
   in-progress ticket; for the closed ticket, `restore`, a labour row (close
   refuses without one, `validate_close`), the part through the API, then
   `close` with `cause_id` and `action_id`. `support/tickets.js` has
   `causeId(code)` but no action look-up: add `actionId(code)` beside it, or
   close on the screen as the S018 test does. Say which.
3. The *Fitted here before* check runs three times on the same machine, and
   the lines of every earlier test and project stay in the database. The
   test must give its line a description unique to the run (the ticket's
   serial in it, for example), find that row by text, and never assert the
   list's length or that a first ticket's list is empty.

**Fix.** Add the three points to § 8 (and the `actionId` helper to § 3 if
chosen). No design change.

### BS1-05 — `nit` — "Coded after S025 is committed" no longer describes the order

The Depends-on paragraph and the Status line say S020 is coded after S025 is
committed. S025 and S019 are in the working tree, uncommitted; the user
commits S025, S019 and S020 together, and S020 is coded on top of both.

**Fix.** Say so in both places, and set `Baseline: 3df667c + uncommitted
S025 and S019` after this round.

### BS1-06 — `nit` — Where the parts card goes on the page after S019

Not staleness in the strict sense: the row was the same at the baseline. But
S019 made the Times card up to seven lines taller (the waiting split, the two
delay totals, *Planned stop*), and the row's cards are `h-100`, so each
stretches to the tallest. The second row holds three `col-md-4` cards (Times,
Assigned, Labour). "Beside *Labour*" (§ 3) leaves the coder to choose: a
fourth `col-md-4` wraps alone onto the next row on a laptop, or the four
become `col-md-6 col-xl-3`, or the parts card sits in the next row. On a
phone every card stacks, so the floor is unaffected.

**Fix.** One phrase in § 3: the four cards as `col-md-6 col-xl-3` (two by
two on a tablet, four across on a wide screen) — recommended — or whichever
the planner prefers.

### BS1-07 — `nit` — The length message of the core's text helper differs from the brief's table

`tickets_core._optional_text` (unchanged since the baseline) refuses a long
text with "Too long (max N)". § 5.1's table says "At most N characters". If
`validate_part` reuses the helper, as it should, the message is the helper's.
One wording for one thing (scope B): change the table to the helper's words,
or say why parts get their own.

## Checked and found consistent

- **The labour routes and lock helpers.** `_lock_open_ticket(cur, id, key)`
  still takes a plain key and gives 404 → 403 at the site → closed 409 from
  the locked row; `_labour_row`'s "another ticket's row is 404" and the hard
  delete are as the brief cites. S019's callable `key` is for moves only.
- **The shared node helper (§ 3, § 5.2, § 7.8).** `_check_component` now does
  what the brief expects to split: the row `LOCK IN SHARE MODE`, the parent
  plain for `gp_id`, then the refusals (machine level, scrapped, not under
  the machine) on `component_id`. `machine_and_component` returns `(id,
  None)` for a machine, so the same comparison admits the machine itself
  when the parameter says so. S025's code review confirmed the lock order
  (ticket, then the component shared; a scrap never waits on a ticket row).
- **Not a fault with parts (§ 1.5).** `_not_a_fault` runs under the ticket's
  `FOR UPDATE`; a count of lines there is race-free against an add, as § 5.2
  says. A 409 with no field reaches `MoveDialog`'s `topError`, and its watch
  emits `reload` for `!field && status === 409`, so the page behind reloads
  as BR1-07 wants. S025's "times blank, labour stays" for not a fault is
  untouched: with parts the move is refused.
- **The close hint (§ 1.6).** `_moves` builds one entry per name, so
  `parts_hint_actions` on the `close` entry fits beside `recording_as` and
  `asks_machine_stopped`; `test_moves_listed_per_user` compares names only,
  and the tests that read an entry pick it by name, so nothing breaks.
  `MoveDialog` has `props.ticket` and the action select `#move-action` for
  the hint; the `FormModal` guard on cancel is as the brief describes.
- **The page (§ 3).** `showLabour = can("ticket:work") || labour.length > 0`
  still exists for `showParts` to copy; the disabled *Close* with "Add the
  labour first" under it is the pattern for the disabled *Not a fault*;
  `canWork` is `isOpen && can("ticket:work")`. S019's plan buttons and the
  badge do not touch the action bar's significant moves.
- **`machineParts.js` (§ 3).** `EditTicketDialog.open` still holds the
  loader to extract: `GET /api/equipment/<machine>`, `children` two levels,
  scrapped left out, the ticket's own component kept when not listed. S025
  and S019 changed only its `invalid-feedback d-block` lines.
- **The core (§ 3, § 5.1).** `_optional_text`, `_optional_id` and `_is_id`
  are there for `validate_part` to reuse; the maintenance-action codes are
  strings (`'1'`, `'3'`, `'10'` in v20's seed), as `PARTS_HINT_ACTION_CODES`
  assumes. `ticket_labour`'s audit columns in v20 are the four the brief
  copies.
- **Permissions (§ 5.4).** `config_rbac.py` is unchanged: `ticket:work`
  (technician and up, IT admin), `ticket:read` (operator and up), both
  site-scoped; the engineer holds `ticket:work` and `ticket:close`, so the
  not-a-fault e2e check can add and remove the line as one person.
- **Scrap (§ 5.2).** `_check_no_open_tickets` still counts tickets by
  `equipment_id` / `component_id` only (S025 added the count to the message),
  so "scrap does not look at part lines" holds.
- **`conftest._TABLES`** has no `ticket_parts` yet; the brief's addition
  before `tickets` is right. `test_modules.py` reads `LATEST_VERSION` from the
  module, so v22 does not break it.
- **JSON errors (S025).** The parts refusals are `ApiError`s with
  `{"error", "field"}`; S025's handlers cover only what was unhandled.
- **The e2e helpers the brief names.** `expectDialogFits`,
  `expectFieldMessage`, `card(page, "Parts used")` (the header regex), the
  seed people and `seed.extruder` exist with the described shapes. The seed
  needs no change for S020.
- **Standards, UX, decisions 1–9, § 9.** Not re-reviewed; nothing in the diff
  touches them.

## Summary for the orchestrator

- File: `docs/steps/S020-parts-used/2-brief-review-s1.md`.
- Findings: 0 blocker, 0 major, 4 minor (BS1-01 … BS1-04), 3 nit (BS1-05 …
  BS1-07).
- No blocker or major is open: the planner fixes the wording and the coder
  starts, with `Baseline: 3df667c + uncommitted S025 and S019`.
