```
Step: S020 — Parts used
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 22-10-2026
```

# S020 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** Two `minor` findings and five `nit`s are open. The step is built as the brief asks, and the unit and API suites are green. One full browser run had one failure, in an S003 test that S020 does not touch. A re-run of that spec passed (CR1-02).

Reviewed: the working tree on 3df667c, S020's part only. S025 and S019 are uncommitted in the same files. I separated them with their impl reports and their `4-code-review-r1.md`.

## Test results (real runs, 22-10-2026)

| Suite | Result |
|---|---|
| `tooling/run-tests.bat` | exit 0. Backend: 1998 passed. Frontend: 13 files, 110 tests passed. Deps: 42 passed. Tooling: 20 passed. |
| `npx vite build` (`frontend/`) | Built in 3.4 s with no new warnings. |
| `tooling/run-e2e-tests.bat` (full) | exit 1: **179 passed, 1 failed** in 7.0 min. All 18 S020 runs passed (6 tests × 3 projects). The failure is `equipment.spec.js:42` "S003: engineer adds equipment from the list; its page opens" on `phone-webkit` (CR1-02). |
| `tooling/run-e2e-tests.bat e2e/equipment.spec.js` (re-run) | 12 passed, 0 failed (44 s). |

## Findings

### CR1-01 — minor — The operator's "no *Add part*" check is made on a closed ticket

- **Where:** `frontend/e2e/tickets-parts.spec.js:293-295`.
- **Problem:** The test checks that the operator sees the lines with no *Add part*. It does this on the ticket it has just closed. On a closed ticket nobody sees *Add part* (`canWork` needs `isOpen`). So the assertion cannot fail because of a permission fault. The *bare* ticket later in the test is open, but it has no lines, so it has no card.
- **Failure scenario:** `PartsPanel` gets `:can-edit="isOpen"` instead of `canWork`, or `showParts` hands the edit buttons to readers. An operator on an open ticket with lines then sees *Add part*, *Change* and *Remove* (the API answers 403). This test still passes.
- **Fix:** Check the operator on an **open** ticket that has a line. For example, add a line to the *bare* ticket through the API, then assert as the operator that the line shows, with no *Add part* and no *Change* or *Remove*. Or make that check before the ticket is closed.

### CR1-02 — minor — The full browser run failed once, in S003's *Add equipment* test on iPhone WebKit

- **Where:** `frontend/e2e/equipment.spec.js:51`; the screen is the *Add equipment* dialog. S020 did not change that spec or that screen.
- **Problem:** The page snapshot at the failure shows *Name* empty after `fill(name)`. The API answered 400 "Name is required", and the dialog stayed open. The re-run of the spec passed in all three projects. So the cause is a race on WebKit: the typed name is lost. Either a late list load re-seeds the form, or the field is filled before the dialog has settled. S020 met the same kind of loss in its own spec and guarded against it with `fillIn` (impl report decision 12).
- **Failure scenario:** A run before a commit or at `/smtw-review` comes out red with no fault in the code under review. On a real phone, a name typed just after choosing the model might also be lost, if the cause is a form reset.
- **Why not a blocker for S020:** S020 does not touch the equipment screens or the equipment create API. Its own 18 runs are green, and the coder's full run was green (180 passed).
- **Fix (outside S020; queue it):**
  1. Find out whether the dialog resets *Name* when the model list or the class filter loads. If it does, fix the screen.
  2. Otherwise, check the value after the fill, as `fillIn` does in `tickets-parts.spec.js`.

### CR1-03 — nit — The list of units is kept twice

- **Where:** `frontend/src/utils/ticketLabels.js:377` (`PART_UNITS`) and `backend/tickets_core.py:820`.
- **Problem:** The brief keeps `qty_unit` out of an ENUM so that a unit can be added without a migration (§ 4). As built, a new unit needs the same edit in both languages. The close hint avoids this kind of copy, because the API sends `parts_hint_actions`. S019's waiting reasons follow the same two-copy pattern, so this is not new.
- **Failure scenario:** Someone adds `"pair"` to `PART_UNITS` in the core only. The dialog never offers it. Or the edit is made in the frontend only, and the API refuses the unit with "Choose a unit".
- **Fix:** Send the units from the API (for example `part_units` in the detail), or leave a comment on each copy that names the other. The cheaper option is the comment.

### CR1-04 — nit — "Part" means two things on the ticket page

- **Where:** `backend/tickets_core.py:841` "Choose the machine or one of its parts"; `PartsPanel.vue:86` "The machine's parts could not be loaded"; `EditTicketDialog.vue:77` label *Part* (S018). On the other side are *Parts used*, *Add part*, *Change part* and "Remove the parts first".
- **Problem:** CLAUDE-COMMON scope B asks for one word for one thing. In the *Add part* dialog, "part" means the spare part in the title and the component in the *Fitted to* refusal. The wording comes from the approved brief (§ 5.1) and from S018, so the coder followed it.
- **Failure scenario:** A technician who sees "Choose the machine or one of its parts" under *Fitted to* in a dialog called *Add part* may think the message is about the spare part.
- **Fix:** The planner and the user decide the wording. One option is to keep "part" for spare parts and say "Choose the machine or one of its components" (or the plant's own word for a sub-assembly) in the refusal, the load error and S018's *Part* label. A queued tidy-up item is enough.

### CR1-05 — nit — A failed suggestions fetch is swallowed with no trace

- **Where:** `frontend/src/views/tickets/PartsPanel.vue:98-100` (impl report decision 7).
- **Problem:** CLAUDE-COMMON says never to swallow an exception silently. The comment gives the reason: the list is only a help, and the dialog works without it. But nothing tells the user or the developer that the list failed. An empty list looks the same as "nothing fitted here before".
- **Failure scenario:** The suggestions route starts to fail, for example after a schema change. Technicians keep typing part numbers by hand, and nobody notices that the help is gone.
- **Fix:** Show one quiet line under *Description*, for example "Earlier parts could not be loaded." The coder named this alternative. The user decides.

### CR1-06 — nit — The SMTW-Review map does not name the new spec

- **Where:** `.claude/CLAUDE.md` § SMTW-Review, *Browser tests*: the map from spec files to steps.
- **Problem:** `tickets-parts` → S020 is missing. The impl report (§ 5) recommends adding it, and the brief proposed no point there.
- **Fix:** The planner adds "`tickets-parts` S020" to the map.

### CR1-07 — nit — Decision 2 says more than the code does

- **Where:** `3-impl-report.md` § 4, decision 2. The code is in `backend/tickets.py`: `_apply_move` at line 963, and `_not_a_fault` at line 914.
- **Problem:** The report says the parts refusal is a 409 "as 409 comes before 400 on every ticket write". In `_apply_move`, the event-time check runs before the move's step. So a stale *Not a fault* with a bad `occurred_at` gets the 400 on `occurred_at` first. The order inside `_not_a_fault` (parts, then the cause) is right, and so is the rule.
- **Fix:** Reword decision 2: "within the move's own checks, the parts refusal comes before the cause check". No code change.

## Points the orchestrator asked about

- **v22** (`backend/local_db.py:608-640`) creates one table with `CREATE TABLE IF NOT EXISTS` and touches no row. The comment above it gives the reason there is no `_PRECONDITIONS` entry. Its columns, CHECKs, foreign keys and indexes match brief § 4, and the audit columns match `ticket_labour`. `test_migration_v22.py` upgrades a v21 database and checks every part. It then deletes `db_version` 22, runs v22 again, and compares `_schema()`. A second test shows that both CHECKs refuse bad rows (error 4025). It is safe to re-run.
- **RBAC.**
  - The four routes carry `@require_perm(WORK_KEY)`, the union check.
  - The three writes then call `_lock_open_ticket(cur, id, WORK_KEY)`: 404 through the access predicate, 403 at the ticket's site, 409 when closed.
  - The suggestions call `read_ticket` (404) and then `require_perm_at(WORK_KEY, site)` (403).
  - The actor comes from `actor()`, never from the body. All SQL is parameterised; the one f-string builds `%s` placeholders only.
  - The tests cover 403 for an operator, 403 at another site after a machine move, 404 outside the units, and 404 for a line of another ticket.
- **Validation** (`tickets_core.validate_part`, `part_quantity`) follows § 5.1 case by case.
  - Bools are refused. Values go through `Decimal(str(v))`. NaN, infinity, sNaN, zero and negative values are refused.
  - The maximum is checked before `quantize`, and "at most two decimals" is judged on the value.
  - A kind sent without a number is dropped. A maker's number needs a maker. A too-long maker does not also raise the "maker needed" error.
  - The core tests name every case of the brief.
- **Lock order.** The add and the edit lock the ticket (7) `FOR UPDATE`, then validate, then read the node alone `LOCK IN SHARE MODE` (its parent plain). This is S025's order, and it adds no new lock-order edge. A remove locks only the ticket. `test_a_scrap_committed_during_the_add_is_seen` puts a committed scrap between the ticket lock and the node read, and the add is refused. The coder's mutation check shows that the test fails without the share lock.
- **Not a fault with parts** is counted in `_not_a_fault` under the ticket lock, so it covers every from-state of `MOVES["not-a-fault"]`. The API test runs raised, acknowledged, scheduled (set up with `moves/schedule` as an engineer) and in progress. Each one is refused with 409 and no field, then allowed once the line is removed. On the page, *Not a fault* is disabled with "Remove the parts first".
- **"Fitted here before" scope.** The route needs `ticket:work` at the ticket's site and access to the ticket. It reads by machine (the machine, its children and its grandchildren), as § 5.3 accepts (BR2-03). It answers only number, kind, maker and description: no ticket and no site. A machine at another site is not offered (tested).
- **Close hint.** `_parts_hint_actions` returns the ids of codes 1, 3 and 10, active or not. It is set on the `close` entry only. `MoveDialog` shows the hint when the chosen action is one of them and `parts` is empty. The API tests cover Replace, Modify and Overhaul, including a deactivated Modify. The e2e test covers Replace and Overhaul, checks that Repair shows no hint, and checks that the hint goes once a part is recorded.
- **Helper refactor.** `_check_component` now calls `_locked_node_of_machine(..., machine_counts=False)`. Before, it refused when the node was missing, at machine level, scrapped, or under another machine. Now the helper returns `None` in the same four cases, and the caller raises the same `COMPONENT_OF_MACHINE` on `component_id`. Only the order of the checks changed, and every case gives the same refusal. The edit's behaviour is unchanged. `test_the_ticket_edit_still_refuses_the_machine_itself` and S025's edit tests pass. On the frontend, `EditTicketDialog.vue` now uses `partRows` and `keepChoice`, with the same rows and the same order (the kept node comes first).
- **e2e data isolation.** Each test raises its own tickets, and the `afterEach` closes them as admin through the API. It removes the parts and closes as not a fault, or uses a plain close from back in service. The *Fitted here before* test finds its line by a description that holds the serial, and no test asserts a list's length. In the full run, S017's open-tickets test passed in all three projects. The coder is right that S018, S019 and S025 tests still leave open tickets on the extruder. That is outside S020; it should be queued.

## My view on the two small departures

1. **Deadlock note bullet** (decision 3): **agreed.** S019 reordered the list. The shape the brief describes (the raise holds the node (1) and then takes the earlier ticket's shared lock; the other write holds the ticket (7) and then takes the node's shared lock) is now the third bullet, the repeat raise against a send-back. I checked the case of a raise on a component while the line sits on the machine. Both sides take only shared locks on the machine, so that case cannot deadlock. The note names the one case that can. The departure is wording only.
2. **Kind-button order** (decision 8): **agreed.** The brief lists the two labels; it does not fix their order. Putting the default first (*A standard number*) is the usual form pattern, and it matches Plant-Facts § 6: most press spares are bought generic. The departure is reported, and the e2e tests find the buttons by name, not by position.

## Use on the floor (UX)

- **Dialog.** `FormModal` uses `modal-dialog-scrollable`, so the footer stays fixed. The suggestions list shows five rows, and *More* opens at most 20, inside the scrolling body. `expectDialogFits` passes with the list showing, on Pixel 7 and iPhone 14.
- **Tap targets.** No `btn-sm`. The two kind choices are full-width buttons. *Change* and *Remove* are normal-size icon buttons.
- **Remove** asks first with the inline *Remove? Yes / No* bar, as labour does. *Yes* is red.
- **Messages** are one short line each, and each says what to do. "Remove the parts first" matches S018's "Add the labour first".
- **States.** The empty card reads "No parts recorded". A reader sees no card on a ticket without lines, and the card with no buttons on a ticket with lines. A closed ticket is read-only.
- **Phone layout.** The cards are `col-md-6 col-xl-3`, so they stack on a phone. The unit select is `flex: 0 0 6rem` beside the quantity field, and nothing has a fixed width beyond that.

## Manual checks in the impl report

- `## Manual checks` is present. The three **important** checks of brief § 8 are `[auto]` with their test names, and so are the four other automated checks. A passing run is behind every one of them; my run confirms all 18.
- The real-device check (the decimal keyboard and *Save* reachable on an iPhone) is row 11 of `docs/steps/device-checks.md`. The brief does not mark it important, and the report says so.

## What still needs a manual check by the user

- On a real device, row 11 of `device-checks.md` (iPhone): the quantity field opens the decimal keyboard, and *Save* stays reachable with the keyboard up.
- Nothing else. Every important check is automated, and it passed.

## Checked and found consistent

- Scope:
  - every item of brief § 1 and § 3 is built;
  - no extra endpoint, flag or layer was added;
  - the Plan.MD and Maintenance-Philosophy edits are left to the planner, as § 3 says;
  - the departures are listed in Decisions taken (3, 8, and the e2e `afterEach`, 11).
- The edit re-checks the node only when `node_id` changes, so an unchanged scrapped node passes (tested). The dialog keeps the line's own node as a choice (`keepChoice`).
- The detail's `parts` come in entry order with the quantity as a string ("1.50"). The panel shows "1.5 m". Its visibility (`showParts`) follows `showLabour`.
- The not-a-fault 409 has no field, so `MoveDialog` shows it at the top and asks the page to reload.
- `conftest._TABLES` lists `ticket_parts` before `ticket_labour` and `tickets`.
- The lock-order note in `tickets.py` and the sentence in `equipment.py` say what the code does.
- The quantity is sent as the trimmed text (`type="text" inputmode="decimal"`), never as a number.
- The suggestions are ordered by `MAX(created_at) DESC, MAX(id) DESC`, so lines added in the same second still come newest first (tested with 22 lines).
- Concurrency:
  - a parts add against a not-a-fault: both take the ticket lock, so they cannot both succeed;
  - a parts write against a close: the close does not read parts, and a write on a closed ticket gets 409.
- The suggestions route uses `get_db()`, so a down database gives 503 and a dead connection is handled there.
- The impl report follows scope A: the point first, short sentences, and one term for one thing.
- The screen texts the brief did not give (decision 9) follow scope B. CR1-04 is the one exception, and its words come from the brief.
