```
Step: S020 — Parts used
Doc: impl-report
Author: Coder (Opus)
Date: 22-10-2026
```

# S020 — Implementation report

**Result: the brief is built as approved, with staleness check s1 answered, and every suite is green.**
- Backend: 1998 passed.
- Frontend: 13 files, 110 unit tests passed; `vite build` passed with no new warnings.
- Dependency-audit tests: 42 passed. Tooling tests: 20 passed.
- Browser suite: 180 passed in 6.7 min (60 tests × 3 projects: Pixel 7 Chromium, iPhone 14 WebKit, desktop Chromium); 0 failed, 0 skipped. The six S020 tests pass in all three projects.

The code sits on top of S025's and S019's uncommitted code; the user commits the three together. Nothing departs from a rule of the brief. Two small points of wording or order are listed under § 4 (decisions 3 and 8). No question is open for the user.

## Questions for the user

None.

## 1. What was built

1. **A *Parts used* card on the ticket page**, beside *Labour*. Each line shows the quantity and unit, the description, the part number with its kind, the maker, and "Fitted to <code> <name>", in the order entered. A `ticket:work` holder always sees the card ("No parts recorded" when empty). Anyone else sees it only when the ticket has lines.
2. **Add, change and remove a line** while the ticket is open, in any open state (scheduled included), for `ticket:work` holders at the ticket's site. Remove asks first with the inline *Remove? Yes / No* bar. A closed ticket's lines are read-only.
3. **The dialog** (*Add part* / *Change part*), top to bottom:
   - *Description*, and directly under it on *Add* the **Fitted here before** list;
   - *Part number* (optional) with its help line;
   - while the number has text, "Where does the number come from?" as two large buttons, *A standard number (6205-2RS, a filter spec)* (the default) and *From the maker's drawing or quote*;
   - *Maker*, marked "(optional)" except for a maker's number;
   - *Quantity* (default 1, a text field with the decimal keyboard) and its unit (*nos*, *set*, *m*, *L*, *kg*; default *nos*);
   - *Fitted to*: the machine first, then its parts; default the ticket's component, or the machine.
4. **Fitted here before**: the distinct lines already recorded on the same machine and its parts, on any ticket, newest first, at most 20, fetched once when *Add* opens. Five show, the rest behind *More (N)*. Typing in *Description* narrows the list. A tap fills description, number, kind and maker.
5. **Not a fault is refused while parts are recorded.** On the page, *Not a fault* is disabled with "Remove the parts first". A stale page gets 409 "Parts are recorded, so it was a fault — remove them first", shown at the top of the dialog, and the page reloads.
6. **The close hint**: with the action *Replace*, *Modify* or *Overhaul* and no parts recorded, the close dialog shows "No parts recorded. If any were fitted, cancel and add them on the ticket first." It does not refuse.
7. **Migration v22**: the table `ticket_parts`.

## 2. How it works

**The core (`tickets_core.py`, pure).**
- `validate_part(body)` returns `(clean, errors)` in field order: description, part number, maker, kind, quantity, unit, node.
- Text is trimmed; an empty string becomes NULL; the length message is `_optional_text`'s "Too long (max N)".
- A kind sent without a number is dropped. A number without a valid kind is "Choose where the number comes from". A maker's number without a maker is "Name the maker of this part number".
- `part_quantity(value)` accepts a string or a non-bool `int`/`float`, converts through `Decimal(str(value))`, refuses NaN and infinity, checks the maximum before `quantize` (a huge value cannot be quantized), and refuses more than two decimals instead of rounding. It returns the quantized value, so `1.5` is stored as `1.50`.
- `PART_UNITS`, `PART_KINDS`, `PARTS_HINT_ACTION_CODES = ("1", "3", "10")` and every message are constants here.

**The shell (`tickets.py`).**
- `POST /api/tickets/<id>/parts`, `PUT …/parts/<row>`, `DELETE …/parts/<row>` follow the labour routes: `@require_perm("ticket:work")`, then `_lock_open_ticket` (the ticket (7) `FOR UPDATE`; 404, 403 at the ticket's site, 409 closed), then the body (400), then the node.
- `_part_body` checks the node on an add, and on a change only when `node_id` differs from the stored one.
- The node check is `_locked_node_of_machine(cur, node_id, machine_id, machine_counts)`. It reads the node row alone `LOCK IN SHARE MODE`, reads its parent plain, and returns the row when the node is not scrapped and is the machine (only when `machine_counts`) or below it. Otherwise it returns `None`.
- `_check_component` (the ticket edit, S025) now calls the same helper with `machine_counts=False` and raises its own `component_id` refusal. Behaviour unchanged.
- `_part_row` gives 404 for a line of another ticket. A remove locks only the ticket and deletes the row, with no timeline line.
- `GET /api/tickets/<id>/part-suggestions`: the ticket by the access predicate (404), `ticket:work` at its site (403), then one grouped query over lines whose node is the machine, a child or a grandchild. The query groups by number, kind, maker and description, orders by `MAX(created_at) DESC, MAX(id) DESC`, and has `LIMIT 20`. It answers `{"items": [...], "total": N}`.
- The detail gains `parts` (by `id`; quantity as a string, e.g. `"1.50"`; the node's id, code and name).
- The `close` entry of `moves` gains `parts_hint_actions`: the ids of actions 1, 3 and 10, active or not.
- `_not_a_fault` counts the ticket's lines under the ticket lock and refuses with 409 before it checks the cause.

**Locks.** No new lock-order edge. The node's shared lock is the one `fk_ticket_parts_node` takes at the insert anyway. A scrap holds the node `FOR UPDATE`, so the two serialise. The lock-order notes say so:
- `tickets.py`: the parts change joins the writes that lock (7) only; "Three reads take a shared lock" with the parts read as the third bullet; the parts write named under the repeat-raise deadlock (decision 3).
- `equipment.py`: "Three of its shared locks", with the parts line's node, and that scrap does not look at parts lines.

**The page.**
- `PartsPanel.vue` follows `LabourPanel.vue`: `FormModal` through `useFormModal`, and the same inline remove bar.
- The dialog sends the quantity as the trimmed text typed, the kind only with a number, and `node_id` as a number. It runs no checks of its own: the API decides, and each refusal shows beside its field.
- `utils/machineParts.js` holds `partRows` (two levels, scrapped left out, the lower level indented), `loadMachineParts(machineId)` and `keepChoice(rows, node)`. `EditTicketDialog.vue` uses them with no change in behaviour.
- `TicketDetailView.vue`: the four cards are `col-md-6 col-xl-3`; `showParts`; *Not a fault* disabled with its reason.
- `MoveDialog.vue`: `showPartsHint` when the move is `close`, the ticket has no parts, and the chosen action is in `parts_hint_actions`.

## 3. Files touched

Files marked **(S025 / S019 too)** also hold those steps' uncommitted changes. Only S020's lines are described.

**Backend**
- `backend/local_db.py` **(S025, S019 too)**: migration v22, `ticket_parts`, with the comment on why it needs no `_PRECONDITIONS` entry.
- `backend/tickets_core.py` **(S025, S019 too)**: the parts constants and messages, `part_quantity`, `validate_part`; `decimal` import.
- `backend/tickets.py` **(S025, S019 too)**: the docstring and lock-order note; `_parts`, `_parts_hint_actions`; `parts` in the detail; `parts_hint_actions` on the close entry; the refusal in `_not_a_fault`; `_locked_node_of_machine` with `_check_component` on it; `PART_SUGGESTIONS_MAX`, `_part_body`, `_part_row` and the four routes.
- `backend/equipment.py` **(S025 too)**: the lock-order sentence only.

**Backend tests**
- `backend/tests/test_tickets_core.py` **(S025, S019 too)**: `TestValidatePart` (55 cases).
- `backend/tests/test_ticket_parts_api.py` (new): 26 tests.
- `backend/tests/test_migration_v22.py` (new): a v21 database gets v22 (columns, two CHECKs, two foreign keys, three indexes, re-run unchanged); the CHECKs hold in the database.
- `backend/tests/conftest.py` **(S025 too)**: `ticket_parts` in `_TABLES`, before `ticket_labour` and `tickets`.

**Frontend**
- `frontend/src/views/tickets/PartsPanel.vue` (new).
- `frontend/src/utils/machineParts.js` (new).
- `frontend/src/utils/ticketLabels.js` **(S019 too)**: `PART_UNITS`, `PART_KIND_CHOICES`, `DEFAULT_PART_KIND`, `PART_KIND_SHORT`, `quantityText`, `partText`, `matchingParts`.
- `frontend/src/views/tickets/EditTicketDialog.vue`: uses `machineParts.js`; no change in behaviour.
- `frontend/src/views/TicketDetailView.vue` **(S019 too)**: the card, the grid, *Not a fault* disabled with its reason, the docstring.
- `frontend/src/views/tickets/MoveDialog.vue` **(S019 too)**: the close hint, the docstring.
- `frontend/tests/machineParts.test.js` (new); `frontend/tests/ticketLabels.test.js` **(S019 too)**: an S020 block.

**Browser tests**
- `frontend/e2e/tickets-parts.spec.js` (new): six tests.
- `frontend/e2e/support/tickets.js` **(S025, S019 too)**: `actionId`; `causeId` and `actionId` share one private look-up, `codeId` (decision 10).

**Docs**
- `docs/steps/device-checks.md` **(S025, S019 too)**: row 11.
- `docs/steps/S020-parts-used/1-brief.md`: Status only.
- `docs/steps/README.md` **(S025, S019 too)**: the S020 index row only.
- `docs/steps/S020-parts-used/3-impl-report.md` (new): this report.

## 4. Decisions taken

1. **The helper's name and shape**: `_locked_node_of_machine(cur, node_id, machine_id, machine_counts)` returns the row or `None`; each caller raises its own refusal (BR2-05). A scrapped node is `None` before the level test, so a scrapped machine is refused too.
2. **The not-a-fault check comes before the cause check.** A ticket with parts answers 409 even when the cause is missing: the stale-page refusal first, as 409 comes before 400 on every ticket write.
3. **Where the parts write is named in the deadlock list.** The brief says "the fourth accepted deadlock". S019 reordered that list, and the shape the brief describes (the raise holds the node, then the earlier ticket's shared lock; the other write holds the ticket, then the node's shared lock) is now the **third** bullet, the repeat raise against a send-back. I named the parts write there. *Wording only; the rule is the brief's.*
4. **The order of the suggestions**: `MAX(created_at) DESC`, then `MAX(id) DESC`, because `created_at` has one-second resolution and lines added in the same second must still come out newest first. The grouping uses the table's case-insensitive collation, so "Seal kit" and "seal kit" with the same number and maker are one suggestion.
5. **The suggestions' maximum (20) is a constant in the shell** (`tickets.PART_SUGGESTIONS_MAX`), beside the query. It is a display size, not a business rule.
6. **The dialog runs no checks of its own.** Every refusal comes from the API, as the brief's e2e conventions say for the maker and quantity messages. The HTML `required` attribute is not used on *Maker*, so the browser does not block the request; the required state shows as the label losing "(optional)".
7. **A failed suggestions fetch shows nothing.** The list is a help; the dialog works without it. The `catch` has a comment saying so. *This is a choice the user may want to see:* the alternative is a one-line message in the dialog.
8. **The kind buttons' order**: *A standard number* first, then *From the maker's drawing or quote*. The brief names the maker's first, but the standard number is the default (Plant-Facts § 6), and the default is listed first. *Order only.*
9. **Screen text the brief does not give** (scope B): the card title "Parts used", "Add part", "Change part", the question "Where does the number come from?", "Fitted here before", "More (N)", "Fitted to <code> <name>", the kind in the list as "(standard number)" or "(maker's number)", and the placeholders "e.g. Deep-groove ball bearing" and "e.g. SKF". A quantity shows without trailing zeros ("1.5 m", "2 nos").
10. **`codeId` in the e2e support.** `actionId` would have been a copy of S025's `causeId`. Both now call one private `codeId(list, code)`. `causeId`'s behaviour is unchanged.
11. **The e2e spec closes its own tickets** in an `afterEach`, as IT admin through the API: parts removed, then *Not a fault*, or a plain close from back in service. The first full run failed S017's test "raise from the Tickets list …" on desktop Chromium: the raise screen lists at most 50 open tickets of a machine (the API's default page), the three projects share one database, and the S020 tests had left 12 more open tickets on the extruder by the time desktop Chromium ran. That S017 test was already near the limit (S018, S019 and S025 tests also leave open tickets on the extruder); see § 5.
12. **The e2e spec waits for *Fitted here before* to settle** after typing a description, then checks each typed value. On iPhone WebKit, a part number typed while the list was collapsing was lost once (the list moves the fields below it). A person does not type during that instant, but the test must not race it.
13. **A second migration test** (`test_the_checks_hold_in_the_database`) checks that `chk_ticket_parts_kind` and `chk_ticket_parts_quantity` refuse bad rows. The brief asks only for their presence.

## 5. Not done, deferred, assumed

- **The docs of § 3 "at approval, by the planner"** (Plan.MD § 4.2, Q21 and § 5; Maintenance-Philosophy *Parts and part numbers*) are the planner's. I did not change them.
- **The SMTW-Review section in `.claude/CLAUDE.md`** maps spec files to steps. It does not name `tickets-parts` → S020. The brief proposes no point there, so I left it. *Recommendation:* add `tickets-parts` S020 to that list.
- **The S017 open-tickets test is fragile.** It expects its ticket in a list capped at 50 on a machine that every ticket test uses. S020's tests no longer add to it, but the S018, S019 and S025 tests still leave open tickets on the extruder. *Recommendation:* a queued tidy-up, either the tests close their tickets or the S017 test uses its own machine.
- **The dev database** `vel_yantra_master` gets v22 the next time the dev backend starts. The test, upgrade and e2e databases got it in these runs.
- **Assumption:** a part line whose node is later moved to another machine stays on the ticket as it is. The scrap path and the move path do not look at parts lines (§ 5.2 accepts this for scrap; a move is the same kind of history).

## 6. Tests

**Results** (real runs, 22-10-2026):

| Suite | Result |
|---|---|
| `tooling/run-tests.bat` (exit 0) | backend 1998 passed; frontend 13 files, 110 tests passed; deps 42 passed; tooling 20 passed |
| `npx vite build` | built, no new warnings |
| `tooling/run-e2e-tests.bat` | exit 0: 180 passed in 6.7 min (60 tests × 3 projects); 0 failed, 0 skipped. An earlier full run had 1 failure (S017's open-tickets test, decision 11), fixed before this run |

A mutation check: with `LOCK IN SHARE MODE` removed from the node read, `test_a_scrap_committed_during_the_add_is_seen` fails; restored, it passes.

## Fix rounds

### Round 1

- **CR1-01 — Fixed.** `frontend/e2e/tickets-parts.spec.js`: the operator check now runs on an open ticket that has a line (added through the API): the line shows, with no *Add part*, *Change* or *Remove*. The ticket is closed in `afterEach` like the rest. The closed-ticket checks for the engineer stay.
- **Files:** `frontend/e2e/tickets-parts.spec.js`, this report.
- Tests after the round: `tooling/run-tests.bat` exit 0 (backend 2003 passed, frontend 13 files / 110 tests, deps 42, tooling 22); `tooling/run-e2e-tests.bat e2e/tickets-parts.spec.js e2e/tickets-work.spec.js`: 66 passed (22 tests x 3 projects), 0 failed.
- Not touched: CR1-02 (S003 flake, outside S020, queued by the reviewer) and CR1-03 to CR1-05 (nits; not asked).

## Manual checks

**Automated** (passing run of 22-10-2026, all three projects):
- [auto] **Important.** A technician adds a part line on an in-progress ticket the short way (description, a number with the default kind *standard number*, the default 1 nos, fitted to a component); the card shows it with the component's code; *Change* sets the quantity to 2; *Remove* asks first and removes it — `frontend/e2e/tickets-parts.spec.js`::`S020: technician adds a part line the short way, fitted to a component; changes the quantity; removes it`
- [auto] **Important.** A maker's part number without a maker shows the message beside *Maker*; a quantity of 0 beside *Quantity* — `frontend/e2e/tickets-parts.spec.js`::`S020: a maker's part number without a maker, and a quantity of 0, are refused beside their fields`
- [auto] **Important.** A second ticket on the same machine shows the first line under *Fitted here before*; a tap fills number, kind, maker and description — `frontend/e2e/tickets-parts.spec.js`::`S020: a second ticket on the same machine offers the first one's line under Fitted here before; a tap fills it`
- [auto] *Not a fault* is disabled with "Remove the parts first" on a ticket with a part line; after removing the line it is offered and succeeds — `frontend/e2e/tickets-parts.spec.js`::`S020: Not a fault waits while parts are recorded; after removing them it is offered and succeeds`
- [auto] The close dialog shows the hint for *Replace* and *Overhaul* with no parts (not for *Repair*), and not once a part is recorded — `frontend/e2e/tickets-parts.spec.js`::`S020: the close dialog hints at parts for Replace or Overhaul with none recorded, and not once one is`
- [auto] A closed ticket shows its parts with no *Add part*, *Change* or *Remove*; an operator sees the lines with no *Add part*, and no card on a ticket without parts — `frontend/e2e/tickets-parts.spec.js`::`S020: a closed ticket's parts are read-only; an operator sees the lines but no Add, and no panel when there are none`
- [auto] The parts dialog fits a phone with the *Fitted here before* list showing (`expectDialogFits` on Pixel 7 and iPhone 14) — `frontend/e2e/tickets-parts.spec.js`::`S020: a second ticket on the same machine offers the first one's line under Fitted here before; a tap fills it` (and every *Add part* / *Change part* dialog of the tests above)

**On a real device** (row 11 of `docs/steps/device-checks.md`):
- On an iPhone: the *Quantity* field opens the decimal keyboard, and *Save* stays reachable with the keyboard up. Account: a technician (production) or none (dev server); network: Company Wi-Fi or mobile data, either; where: the dev server on KLA's laptop or production on the TEST machine. Done by KLA or IT Admin. (Not marked important in the brief.)
