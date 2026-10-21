```
Step: S020 — Parts used
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 21-10-2026
```

Reviewed against: 28d3be3 + uncommitted S024

**Verdict: one `major` finding open (BR1-01, the locking decision contradicts
S025's). The rest is minor or nits. The step is rightly on the full track.**

The brief is a good fit for the floor and the Plan: part numbers as text on
the ticket's component, no second catalogue, the kind of number kept for the
OneERP link later, suggestions from the same machine. The findings below are
mostly rules the coder would otherwise settle alone, plus one decision whose
reasoning misreads S025.

## Findings

### BR1-01 · major · Decision 8 misreads S025 and leaves two lock patterns side by side

**Problem.** § 5.2 and § 7 decision 8 share-lock the node *before* the ticket
row "the way S025 fixes it for the ticket edit", and reject "checking the node
after the ticket lock (an equipment lock taken while a ticket lock is held —
the inversion S025 audit [4] found)". That is not what S025 does or what the
audit found. Audit [4] (`docs/review/2026-10-21-smtw-review.md:85-92`) is a
plain read racing a scrap, not a lock inversion; its fix, approved in S025
§ 1.6 and § 3, is: `_lock_open_ticket` (7) **first**, then `_check_component`
reads the component row `LOCK IN SHARE MODE` — "the lock its foreign key takes
anyway, so no new lock-order edge". So once S025 is coded, `edit_ticket` will
take the node's shared lock *after* the ticket lock, and `add_part` in the same
module would take it *before*, each claiming to be the safe order.

Both orders are in fact deadlock-free here (the scrap path never takes a ticket
lock, and a shared lock on the node is compatible with another shared lock),
but the brief's stated reason is wrong, and the coder is left to reconcile two
patterns in one file.

Two smaller consequences of node-before-ticket, as § 5.2 writes it:
- step 1 reads a node id from the body before the ticket's own 404/403 have
  been decided. The brief does not say what a missing node does at step 1; if
  it refuses there, the refusal order becomes 400 → 404 → 403, unlike every
  other ticket write (404 → 403 → 409 → 400);
- the lock-order notes in both modules would need a new sentence for a write
  that takes (1) in share mode then (7), distinct from S025's "(7), then the
  FK's shared lock on the component".

**Options.**
- (a) **Follow S025** (recommended): lock the ticket (7) with
  `_lock_open_ticket` first, then read the node `LOCK IN SHARE MODE` and decide
  "below the ticket's machine, not scrapped" from that row — the same shape as
  the edit's `_check_component` after S025, and in fact the same helper can
  serve both once it accepts "the machine itself" as a valid node (the edit
  refuses `MACHINE_LEVEL`, the parts line allows it: a parameter, or a
  second small helper that shares the query). The insert's FK lock is the lock
  already held, so S025's "no new edge" argument carries over verbatim. The
  refusal order stays 404 → 403 → 409 → 400. Rewrite decision 8 accordingly
  ("the shared lock the FK takes anyway, taken explicitly so the decision is
  made from the locked row; S025 § 1.6"), and drop the "inversion" sentence.
- (b) Keep node-before-ticket, but say why parts differ from the edit, fix the
  description of audit [4], say what a missing node does at step 1, and add the
  new sentence to both lock-order notes.

### BR1-02 · minor · `close_parts_hint(action_code, part_count)` can never run where a hint is useful

**Problem.** § 3 puts a pure `close_parts_hint(action_code, part_count)` in
`tickets_core`, yet the hint is shown *in the dialog, before the close is
sent*, from `moves.close.parts_hint_actions` and `parts.length` (§ 6). The
server only learns the chosen action at the close POST, when a hint is too
late and the brief says it must not refuse. So the function has no caller: a
planned dead helper.

**Fix.** Keep in the core only what the brief wants in one place: the code
list, `PARTS_HINT_ACTION_CODES = ("1", "3")` (verified: the S016 seed stores
Replace as `'1'` and Modify as `'3'`, `local_db.py:472-474`). `_moves` resolves
the ids with one query on `maintenance_actions WHERE code IN (…)` for the close
entry; the dialog does the comparison. Drop `close_parts_hint` and its test;
test the resolution in the API test instead ("the close entry carries the ids
of Replace and Modify"). Add a test that a deactivated Replace still resolves
(the hint should not vanish because a code was retired — or decide that it
should, and say so).

### BR1-03 · minor · A line's node can be scrapped while the ticket is open, and the edit then refuses an untouched field

**Problem.** § 5.2 says "Scrapping a node a line points at, once its tickets
are closed, stays allowed". The scrap guard (`equipment._check_no_open_tickets`,
`equipment.py:383-394`) counts open tickets **on the node and its parts**
(`equipment_id` / `component_id`), not part lines, so a component that carries
a part line of a ticket raised on the *machine* (component NULL) can be
scrapped while that ticket is still open. The brief then re-checks "not
scrapped" on every PUT (step 3), so correcting the quantity of that line is
refused 400 on *Fitted to* — a field the user did not touch. The edit dialog
would also drop the line's own node from its select (the component list leaves
scrapped nodes out, `EditTicketDialog.vue:36-41`).

**Options.**
- (a) **Check the node only when `node_id` changes** on a PUT (S018's edit
  checks only the fields present; the same idea), and keep the line's own node
  as a choice in the select when it is no longer listed (the
  `EditTicketDialog.vue:55-59` pattern). Recommended: the line is history and a
  scrapped node on it is true.
- (b) Make the scrap guard count part lines of open tickets too ("Close its
  tickets first" would then also cover a line). More locking in a path S025 is
  already changing; not worth it for a line that is correct as history.

Either way, fix the sentence in § 5.2: scrap does not look at part lines at all.

### BR1-04 · minor · When the panel shows: the brief contradicts the labour pattern it cites

**Problem.** § 1.1 says every ticket shows the panel ("No parts recorded"
when empty), and § 8 tests "an operator sees the panel without *Add*". The
labour panel it is modelled on is shown "to ticket:work holders, or when not
empty" (`TicketDetailView.vue:79`, `showLabour`), so an operator never sees an
empty "No labour yet" card. An empty parts card on every ticket an operator
opens is noise on a phone where the page is already long.

**Fix.** Follow the labour rule: `showParts = can("ticket:work") ||
parts.length > 0`; the test becomes "an operator sees the lines, with no
*Add*, on a ticket that has them; no panel on one that has none". Say it in
§ 1.1 and § 3 (`TicketDetailView.vue`).

### BR1-05 · minor · The suggestions: when they load, how they filter, and where they sit on a phone

**Problem.** § 1.4 and § 3 describe "a datalist-like dropdown under the
description field, touch-sized rows", up to 20. Not stated: when
`part-suggestions` is fetched (on dialog open, presumably — one call, cached
for the dialog's life), whether the list filters as the user types, what one
row shows (number · maker · description?), and how 20 touch-sized rows behave
inside a modal on a 390 px phone (the dropdown opens under a field that is
itself near the top; the modal scrolls, but the keyboard covers half the
screen while the user types).

The second-time job on the floor is "the same seal kit as last time", before
anyone types. The simpler screen is a short **"Fitted here before"** list at
the top of the *Add* dialog — tappable rows, the five newest shown, the rest
behind "More" or narrowed by what is typed in *Description* — and a tap fills
number, kind, maker and description as § 1.4 says. Then the description field
is a plain field, no custom dropdown component to build and to keep off the
keyboard.

**Fix.** Pick one (the list at the top, recommended) and state: fetched once
on open (`GET …/part-suggestions`), what a row shows, how many show, and that
*Edit* does not show it (the line already has its number). Add it to the
`expectDialogFits` check with suggestions present.

### BR1-06 · minor · The *kind of number* and *quantity* ask for taps that can be defaulted

**Problem.** *Kind of number* is required whenever a number is typed, with no
default and in words a technician does not use ("maker's part number",
"generic designation"). *Quantity* has no default although one piece is the
common case. On a phone that is two extra decisions per line.

**Options.**
- Kind: two large choice buttons (the send-back pattern, `MoveDialog.vue:
  157-175`) worded with examples — "From the maker's drawing or quote" / "A
  standard number (6205-2RS, a filter spec)" — and a **default** so the
  common case needs no tap. Decision 2 rejects *inferring the stored kind*
  from the maker; a UI default the user can flip is not that. Recommended
  default: *standard number* (most press spares are generic, Plant-Facts § 6),
  or the kind of the suggestion picked.
- Quantity defaults to `1`, unit `nos`.
- Help text under the number field, one line: "What is on the part, the
  drawing or the quote. Leave empty if there is none."

State the choices in § 1.3 and § 3; the e2e "important" check then exercises
the default path, not only the full one.

### BR1-07 · minor · The not-a-fault refusal: its status, how the dialog treats it, and pre-empting it on the page

**Problem.** § 1.5 gives the message but not the status or the field. If it is
a 409 with no field (as `LABOUR_BEFORE_CLOSE` is), `MoveDialog`'s watch
(`MoveDialog.vue:69-71`) also reloads the page behind the dialog — acceptable,
but it should be said rather than discovered. And S018 (BR4-02) chose to
**pre-empt** the labour refusal on the page: *Close* disabled with "Add the
labour first" and the fix beside it. A ticket with parts shows the same shape
of problem: *Not a fault* will always be refused, so offering the button and
refusing after a filled dialog (cause, remark, time) wastes the engineer's
taps.

**Fix.** State: 409, field none, the message shown at the top of the dialog;
and on the page, when `parts.length > 0`, *Not a fault* disabled with
"Remove the parts first" (no extra button: the panel is on the page). Shorten
the message to one line: "Parts are recorded, so it was a fault — remove them
or close it with cause and action". Tests: the page's disabled button, and the
API's 409 (a stale page). Note S025 § 1.10 allows not-a-fault from *in
progress* too; the refusal covers all three from-states, which § 1.5 should
say.

### BR1-08 · minor · `backend/tests/conftest.py` `_TABLES` is hand-kept and is not in Where

**Problem.** The backend tests truncate a hand-kept list of tables in FK
order (`conftest.py:83`); S018 added `ticket_labour` there (S018 § 3). The
brief's Where does not list it, so the first run after the migration fails on
a foreign-key truncation, or leaves parts rows behind between tests.

**Fix.** Add `backend/tests/conftest.py` (`_TABLES` gains `ticket_parts`
before `tickets`) to § 3 Tests.

### BR1-09 · minor · The *Fitted to* list would be a copy of `EditTicketDialog`'s

**Problem.** § 3 says *Fitted to* is "a select of the machine and its
components" but not where the list comes from. The only existing source is
`EditTicketDialog.vue:36-61`: `GET /api/equipment/<machine>`, `flatten` two
levels, scrapped left out, the ticket's own node kept. A second copy in
`PartsPanel.vue` is the duplicate CLAUDE-COMMON's DRY rule forbids.

**Fix.** Extract it (e.g. `utils/machineParts.js`: `loadMachineParts(machineId)`
→ `[{id, label}]`, plus the "keep the current choice" rule) and use it in both
dialogs; list the util and the touched `EditTicketDialog.vue` in Where. The
parts select adds the machine itself as the first row ("— The machine itself
—" is already the edit's wording for "none"; here it is a real choice, so
label it with the machine's code and name).

### BR1-10 · minor · Rules the core must settle that § 1.3 / § 5.1 leave open

**Problem.** Cases `validate_part` will meet and the brief does not decide:
- a `number_kind` sent without a `part_number` — dropped to NULL, or refused
  on `number_kind`?
- a `maker` with no number at all ("Oil, Servo 68" by Indian Oil) — allowed
  (the description-only line with a brand)? The text implies yes; say so;
- `quantity` with more than two decimals (`1.505`) — refused, not rounded
  (the brief says "at most two places"; say refused, with the message);
- `quantity` as a non-numeric string, negative, or a comma decimal (`1,5` —
  a phone keyboard in another locale) — one message for all: "Enter a
  quantity, e.g. 2 or 1.5";
- `qty_unit` missing → `nos` (the column default); unknown → refused;
- `description` whitespace-only → "Describe the part".

**Fix.** A short list of the messages in § 5.1, as S018 § 5 does for labour,
so the e2e checks and the core tests match the same strings.

### BR1-11 · minor · The device check lacks its network

**Problem.** § 8 *On a real device* gives who and where ("KLA or IT Admin, a
technician account; dev server … or the TEST machine on production") but not
the network, which `docs/steps/README.md` § Manual checks asks for in each
row.

**Fix.** Add it (plant Wi-Fi or mobile data; either is fine for this check,
so say "either").

### BR1-12 · nit · Standards: the ISO 8000 and ISO 14224 citations

- **ISO 8000** is the data-quality family for master data (ISO 8000-110:
  exchange of characteristic data; -115: quality identifiers). "One item
  master per company" is master-data-management practice that ISO 8000
  supports, not a clause of it. Cite it as "ISO 8000 (master data quality): a
  single authoritative item master, so Yantra records what was fitted and
  does not keep a second catalogue".
- **ISO 14224:2016** lists spare parts among the *maintenance resources* of
  the maintenance record (Table 8, beside man-hours per discipline); naming
  the table helps the reader find it, as S018 does for labour.
- **ISO 55001 § 7.5** (information requirements) fits in one line: the asset
  information an organisation decides it needs — here, what was fitted to
  what — and the data quality it keeps. Optional.

### BR1-13 · nit · The hint's action list

Replace (1) and Modify (3) are the right two to name, but *Overhaul* (10)
almost always fits parts and *Repair* (2) often does (a seal during a repair).
Since it is only a hint, consider `("1", "3", "10")`; or keep the two and say
why Overhaul is left out. The user's call.

### BR1-14 · nit · Notation and small gaps

- § 6 "in `moves.close`": `moves` is a list of `{name, …}` entries
  (`tickets.py:271-286`); say "on the entry whose `name` is `close`".
- The order of lines in the panel and in `_parts` is not stated; propose by
  `id` (the order entered), as the labour list's secondary key.
- § 1.2 says a closed ticket's lines are read-only; add that a **not-a-fault**
  ticket never has lines (follows from § 1.5), so the panel needs no special
  case for it.
- Migration number: S019's brief already claims v21 (`S019 § 4`); "whichever is
  coded first takes v21" is fine, but the planner should fix the number in
  both briefs at the moment the first is coded, so `test_migration_<next>.py`
  gets its name.
- "`ix_ticket_parts_number`" is for a later step; harmless, but say it is
  cheap now and would need a migration later, which is the reason it is here.

## Checked and found consistent

- The labour routes, `_lock_open_ticket` (404 → 403 at the ticket's site →
  409), the hard delete with no timeline line and the inline "Remove?"
  confirm are as the brief describes them (`tickets.py:336-355, 938-972`;
  `LabourPanel.vue:144-157`).
- `ticket:work` is technician and up plus IT admin through `ROLE_INCLUDES`;
  supervisor and operator do not hold it; storekeeper has no ticket keys
  (`config_rbac.py:82-115`). No new key is needed.
- The detail already carries `labour`, `moves` and `permissions`; `parts`
  and a field on the close entry extend it without breaking the existing
  tests (they match keys, not the full shape).
- `Decimal` through `jsonify` becomes a string (`db_helpers.py:105`), so
  `"1.50"` needs no custom encoder.
- `_check_component` is the two-level "below the machine, not scrapped"
  check, and `machine_and_component` the subtree rule the suggestions need
  (`tickets.py:831-839`, `tickets_core.py:201-210`).
- The S016 seed stores the action codes as `'1'` Replace and `'3'` Modify.
- `FormModal` is `modal-dialog-scrollable` and `expectDialogFits` exists in
  the e2e support (`frontend/e2e/support/dialogs.js:19`); the e2e seed has a
  machine with a component (`E2E extruder` / `E2E extruder gearbox`), enough
  for the "fitted to a component" and "second ticket on the same machine"
  checks.
- Out of scope matches Plan.MD § 4.2 and Plant-Facts § 6: stock, issue, cost
  and the item master stay in OneERP; PM jobs are phase 4.
- Light criteria: a migration and locking — full track, correctly.
