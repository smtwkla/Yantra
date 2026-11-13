```
Step: S104 — PM templates: one path
Doc: code-review r7
Author: Code reviewer (Opus)
Date: 13-11-2026
```

# S104 — code review, round 7 (amendment A1)

**Verdict: no `blocker` or `major` finding is open.** Amendment A1 is built as approved. Meter links work as A1.6
says: the link rules, the PM match through a link in use, the hidden *Last done* value, the move that asks first, the
key at the part's site, and the lock order with no node write waiting on a plan. Migration v58 is appended and v57 is
untouched. The tick, the seed note and *Clear old meter value* are gone everywhere. CR6-01 is fixed. I found three
`minor` findings: `docs/Plan.MD` still describes the tick in two places (CR7-01); *Remove link* has no tests of its
refusals (CR7-02); and in one rare state the move's question names plans that do not use the link (CR7-03).

This round is a full review of A1 (`step_snapshot.py diff S104 --from-round 7`: 52 files, 2,119 lines added and 541
removed), plus a check of CR6-01.

## Test runs (this review, `YANTRA_TEST_RUN=s104cr7`)

| Run | Result |
|---|---|
| `tooling\run-tests.bat` (background, alone) | line width passed; **backend 5385 passed** (152 s), **frontend 472 passed**, **tooling 258 passed**; ALL SUITES: PASSED |
| `tooling\schema-docs.bat check` (after the suites, alone) | migrations up to **v58**, 4 passed, **exit 0** |
| Build | not re-run. The coder's `npx vite build` passed after the last frontend edit (report, *Runs (A1)* row 11). |
| Browser | not run. The coder's whole-suite run gave **433 passed**, 15 skipped (device skips of other steps). The WebKit run of `screens.spec.js` gave **10 passed**. Both runs were owed because `e2e/support/` changed. None of my findings needs a browser re-run. |

## Findings of earlier rounds

| ID | Status | Verified by |
|---|---|---|
| CR1-01 to CR5-02 | Fixed (earlier rounds) | not re-checked |
| CR6-01 (nit) | **Fixed** | `backend/pm_templates.py` `settle_template_plans`: on a lost connection, `logger.error(..., exc_info=exc)` runs before `raise DBUnavailable(...)`. The traceback holds the `InterfaceError` and its `__context__` (the 2013), as `worker._log_lost` does. `test_a_lost_connection_while_settling_answers_503_and_the_template_stands` stays green in my run. |

## Findings

### CR7-01 (minor) — `docs/Plan.MD` still describes the parent tick in two places

`docs/Plan.MD:29` and `docs/Plan.MD:683`.

- **Problem.** Line 29, the Preventive maintenance row of the module table, says "meters matched by type on the
  machine's own meters (a parent's only when ticked on the template)". Line 683, in the paragraph *Decided
  04-11-2026 (S104 gate A …)*, says "When the trigger and an item name the same meter type, the stricter parent tick
  wins". A1.3 removes both: the tick is gone, and D11 no longer applies because one type has one meter on a node. The
  coder updated § 4.1, § 4.3 *Meters*, § 4.3 *Which meter a plan uses*, the PM template paragraph and § 4.5. These
  two lines were missed.
- **Failure scenario.** A reader of the module table, or of § 4.3 from the gate A record, learns that a template tick
  takes a parent's meter. They plan R03.19's class links or R03.21's reading hook on a column that v58 dropped.
- **Fix.** Line 29: replace the parenthesis with "(or a node above's meter through a meter link on the part, S104
  A1)". Line 683 is a dated gate A record and may stay as history. Add one sentence after it: "(Replaced 13-11-2026,
  S104 A1: no tick; one meter per type on a node.)". If the orchestrator owns these records, it makes the edit.

### CR7-02 (minor) — *Remove link* has no tests for its refusals

`backend/tests/test_meters_api.py:389` (`test_remove_the_link`); the route is `backend/meters.py:427`
(`remove_meter_link`).

- **Problem.** `TestMeterLinks` tests each refusal of the add route: technician 403, another site 403, outside the
  units 404, scrapped 409. The DELETE route is tested only for the engineer's 200, the second 404 and the database
  down 503. A1.6.5 gives *Remove link* the same key as add (`equipment:edit` at the part's site, through
  `meters.lock_node`). No test pins that key for DELETE.
- **Failure scenario.** A later change gives the DELETE route `equipment:read`, or takes it outside `lock_node`, for
  example to let a reader clear a link that is not in use. A technician can then remove a link. That stops the PM
  plans of the part, and the suite stays green.
- **Fix.** Add one test, `test_who_may_remove_a_link`. Set a link as the engineer. Then:
  - `at_unit("maint_technician").delete(...)` gives 403;
  - an engineer of another unit (`user_with_units`) gives 404;
  - the mixed user of `test_who_may_link` gives 403;
  - after each refusal, the link row is still there and the part's history has no `meter_unlinked` line;
  - after the part is scrapped, DELETE gives 409 with `SCRAPPED`.

### CR7-03 (minor) — the move's question can name plans that do not use the link

`backend/equipment.py:668` (`_links_a_move_removes`).

- **Problem.** The move asks `link_plan_names` about every broken link, including a link that is not in use. A link
  is not in use when the part now has its own meter of that type (`own`, A1.6.1 item 1: its model gained the type in
  Masters), or when its source is not above the part (`not_above`). `LINK_PLANS_SQL` matches on the part and the
  meter type only. So it names the part's plans for that type even when they run on the part's own meter. The card's
  `used_by` (`meters._meters_out`) asks only about links in use, which is right.
- **Failure scenario.** Gearbox GBX003 links PR-07's Run hours. Later its model gains Run hours in Masters, so the
  gearbox's own meter wins (the link shows "Not in use: GBX003 has its own Run hours meter."). An engineer moves the
  gearbox to PR-08. The question says "PM plans that use it make no job until the part has the meter again: Gearbox —
  greasing (GBX003)". This is false: the plan keeps running on the gearbox's own meter. The engineer may cancel a
  correct move, or add a meter that is already there.
- **Fix.** In `_links_a_move_removes`, call `link_plan_names` only for the broken links that are in use. Judge them
  with `meters_core.link_states`, as `meters_on_paths` does: the part's types in force, its parent and grandparent
  before the move, and the sources' types. Still list and delete every broken link. Add one case to
  `TestReparentMeterLinks`: a part with its own meter of the linked type moves. The 409 then names the link and no
  plan.

## Nits

None.

## The A1 decisions, judged (the report's *Decisions taken (A1)*; it lists 10 items, not 9)

| # | Decision | Judgement |
|---|---|---|
| 1 | `needed_meters` returns a plain list of type ids | Matches A1.6.2 ("the meter types … each once"). |
| 2 | A link not in use answers no limits, no last reading, no `used_by` | Consistent with A1.7 ("last … null when not in use"). The plans do not use such a link, so *Remove link* naming none is right. |
| 3 | `linked_by` lists only parts that use the meter through a link in use | Right: the *Remove* question names only the parts that lose the meter. The filter is `_linked_by`'s SQL (parent or grandparent, not scrapped) plus the part's own meters. |
| 4 | Singular wording; the plans and *Last done* sentences left out together | A scope B improvement on the brief's plural example. Unit-tested (`TestMoveWarning`, `meterLabels.test.js`). |
| 5 | The guard text of `uq_node_meter_links` | A guard only. Every link write holds the part (1) and reads its links first. |
| 6 | The machine refusal carries no field; the two fields show beside the list | Matches A1.6.1. `:error="listError ? '' : modalError"` stops the message showing twice. The call contract `blank(seed)` is unchanged. |
| 7 | The PM card and the Meters card reload after a write and after a move | Needed. The browser tests found both faults. Two small additions (`defineExpose({ load })`, the `parent_id` watch). No new pattern. |
| 8 | `linkedReadOnText` not a label function | Right: the line holds a router link. |
| 9 | `lastDoneHint()` keeps its name | Harmless. |
| 10 | `meterTypeIdByApi` in `e2e/support/meters.js` | A small shared helper that `linkMeterByApi` uses. The coder ran the whole suite and the WebKit screens run for `e2e/support/`, as the settings ask. |

No departure from A1 that the report does not state.

## Checked and found consistent

- **Link rules (A1.6.1).** `add_meter_link` reads the body first (`parse_link_body`: a boolean, a string, 0 or null
  each give 400 "Pick a meter" on its field). Then, in order:
  1. (1) `lock_node` (404, 403, 409 scrapped).
  2. A machine: 400 with no field.
  3. `_lock_up_to`: at most two rows, `LOCK IN SHARE MODE`, nearest first. A sibling, a child, another machine,
     itself or an unknown id: 400 on `source_equipment_id`.
  4. Unknown type: 400.
  5. Own or model meter of the type on the part: 409 `ALREADY_ON_NODE`.
  6. A link of the type already: 409 "already uses".
  7. The source without that meter in force (`meter_in_force`, which never sees a link, so there are no chains): 409.

  Then the insert and the `meter_linked` line. `add_node_meter` refuses a linked type, and `change_node_meter`
  answers `linked_limits`. Logging a reading of a linked type stays S039's `NOT_ON_NODE`. `link_states` checks
  `own`, then `not_above`, then `no_source_meter`. `test_meters_core` tests each reason and the order. Every refusal
  of A1.9 has an API test, apart from CR7-02's.
- **PM match (A1.6.2).** `resolve_meters(needs, node_id, types_by_node, links)` takes the node's own meter, else the
  link in use, else None. Nothing walks up the tree. `meters_on_paths` reads the links in one more query for any
  number of plans, which `test_the_card_resolves_every_plan_in_one_pass` counts. *Start* and the item saves use
  `plan_resolutions`. A linked reading is saved on the source through `meters.lock_node` / `write_reading`. The
  report's A1.10 item 6 confirms that `pm_work.py` needs no change, and
  `test_a_linked_meter_logs_on_the_press_s_meter` shows it.
- **The *Last done* value (A1.6.3).** `pm_plans._seed_shown` answers `last_done_meter` only while `seed_matches`.
  `planSettingsBody` sends the meter value only when it differs from what the page loaded. So an assignee save keeps
  a hidden value, an emptied field sends null, and a typed value is stored for the meter in use. `test_the_seed_
  follows_the_meter` covers each case, including the same link set again bringing the value back.
  `schedule_changed` is unchanged.
- **The move (A1.6.4).** `_links_a_move_removes` runs after (1) and (2). It reads the node's two levels of parts and
  their links plainly, and keeps the moved node, the new parent and the new parent's parent (from the locked row
  (2)). Only JSON `true` confirms. The 409 has the field `remove_meter_links`, the code `meter_links` and the
  server's words. With the flag, the DELETE runs before `update_row` and one `meter_unlinked` line goes on each
  link's part in the move's transaction. A machine moved to another unit breaks nothing. `TestReparentMeterLinks`
  tests each case of A1.9.
- **Permissions (A1.6.5).** The list and the choices use `equipment:read` through `load_node_for_user` (404 outside
  the units). Add and remove use `@require_perm("equipment:edit")` plus `lock_node` at the part's site. The move is
  unchanged. No new key. `test_rbac.py`'s role matrix is unchanged. IT admin may link (A1.10 item 3, tested 201).
- **Locks (A1.6.6).** A link write takes the part (1) `FOR UPDATE` first, then share-locks only nodes above it,
  child first, the re-parent's order. Its plain reads come after the lock, so the part's own rows are current. The
  link routes and the move lock and write no plan, job or template row: `link_plan_names` is a plain read. A PM item
  save holds (6e), (6f), then the source (1). A link write never waits on (6e) or (6f), so there is no cycle. The two
  accepted deadlocks and the move's plain-read residual are written in `equipment.py`'s LOCK ORDER note and in
  `meters.py`'s module note. No locking read of a row that may not exist.
- **Migration v58.** Appended after v57, and v57's text is unchanged. It runs CREATE TABLE IF NOT EXISTS, then the
  ENUM MODIFY (v50's 14 values plus the two at the end; no migration between v50 and v57 changed that ENUM), then
  DROP CHECK, DROP COLUMN and ADD CHECK on each PM table, each step safe to run twice. **No precondition is needed.**
  Production at v50 has empty PM tables. The new table, a dropped column and a weaker CHECK refuse no stored row. An
  ENUM that only gains values at its end keeps every row. `test_migration_v58.py` covers:
  - a fresh build: keys, foreign keys, the CHECK, 1062;
  - the two events;
  - the rewritten CHECKs;
  - a v57 database with ticked rows;
  - MariaDB refusing the DROP COLUMN while the CHECK names it (A1.10 item 6);
  - a re-run and a half-applied v58.

  `conftest._TABLES` puts `node_meter_links` before `node_meters`. `test_migration_v9` pins the new ENUM.
- **Removals.** Searched the code folders (untracked files included) for `meter_from_parent`, `from_parent`,
  `seed_note`, `PARENT_TICK`, `clearSeedBody`, `Clear old meter`, `seed_not_used` and `TICK_BY_METER`. Only these
  hits are left, all on purpose:
  - v57's own text in `local_db.py`;
  - v58's DROP statements;
  - the docstrings that say a sent `meter_from_parent` is ignored;
  - tests that assert the field is absent or ignored;
  - `test_migration_v57.py` and `test_migration_v58.py`, which insert the old column;
  - one browser assertion that *Clear old meter value* is gone.
- **Screens (A1.6.7).** The card's linked row has the badge "From PR-07", the source's limits and last reading (its
  History opens the source), and "Read on … Log readings there." with a link. It has no *Log reading* and no *Set
  limits*. A link not in use shows the three reasons. *Remove link* asks in the row and names the plans: the button
  is `btn-danger`, apart from *Keep*. The own meter's *Remove* names the parts that link it. *Open register* shows
  only with a meter of the node's own. Rows are keyed by type and source. The dialog: `FormModal`, radio rows at
  least 44 px (a `@device` test checks this), one choice picked in advance, save disabled with "Pick a meter" or "No
  meter to use". The move dialog: the warning box, *Move and remove links*, and picking a parent clears both. The
  plan page has the linked-meter wording and the hint line on a part. The template page note and the item help text
  match A1.6.7. Every error line a user can see is one short plain line that says what to do.
- **Browser tests.** Each A1.9 *Automated* check has a test that asserts what the user sees: the row text, the
  badge, the missing buttons, the question's full text, "Does not apply", the history lines, the empty field, and
  the absence of the tick. Every dialog the flows open gets `expectDialogFits`. The move's 409 is passed to the
  console guard. Each test makes its own machine and part. The new `screens.spec.js` test is tagged `@device`, and
  the tag's rule holds: it checks a fit and the 44 px geometry. The flow tests are untagged. The report names the
  targeted specs and the reasons for the whole-suite and WebKit runs.
- **Manual checks.** *Manual checks (A1)* lists the three important checks and the four others as `[auto]`, each
  with its test, all from passing runs. A1.9 has no real-device check, so `device-checks.md` gets no row.
- **Docs.** `notes.json` (the new table, the Equipment area, the `equipment_events`, `pm_templates` and
  `pm_template_items` notes), `schema.json` and `schema-data.js` at v58 (`check` exit 0 in my run). `.claude/CLAUDE.md`
  § SMTW-Review: the S104 point's sentence and the new *Meter links (S104 A1)* point, word for word as A1.9; the
  self-check (2) lock note. `docs/Maintenance-Philosophy.md` § 8. `docs/Plan.MD` § 4.1, § 4.3 and § 4.5, apart from
  CR7-01's two lines. No secret, Keycloak role or real-device check, so those docs are not due.
- **Design and layers.** The rules and the words are in the pure `meters_core` (`link_states`, `broken_links`,
  `move_warning`, `parse_link_body`) and `pm_links_core` (`resolve_meters`, `needed_meters`; `IN_FORCE_SQL` and
  `LINK_PLANS_SQL` as texts beside them, as `contracts_core` does). The routes are a thin shell. The frontend only
  shows the API's states, through `meterLabels.js`. `read_meter_links` and `link_plan_names` live in `equipment.py`
  (AD9), with no import cycle. There is no architecture doc in this repo, so no ARCHITECTURE UPDATE NEEDED.
- **Track and scope.** A full-track step. A1 builds what A1.1 lists and nothing out of scope: no settle at the act,
  no refusal in *Masters › Models*, no linked rows on the reading sheet, the register or the ticket card. The help
  tour stays broken, as decided at gate A.

**Files re-read in full or by section:** `backend/meters.py` (the module note, `_meters_out`, `_linked_out`,
`_linked_by`, the three link routes, `add_node_meter`, `change_node_meter`, `lock_node`, `meter_in_force`,
`meters_in_force`), `backend/meters_core.py` (the link block), `backend/equipment.py` (`load_node_for_user`,
`_load_target_node`, `LOCK_EQUIPMENT`, the link helpers, the move in `update_equipment`, the LOCK ORDER paragraph),
`backend/pm_links_core.py`, `backend/pm_jobs.py` (`meters_on_paths`, `plan_resolutions`, `plan_meters_out`),
`backend/pm_plans.py`, `backend/pm_templates.py`, `backend/pm_templates_core.py`, `backend/pm_work.py` (the lock
note and `_resolved_items`), `backend/local_db.py` (v57, v58 and the ENUM migrations), `backend/api_common.py`
(`ApiError`), `backend/tests/test_migration_v58.py`, the A1 diffs of `test_meters_api.py`,
`test_equipment_api.py`, `test_pm_plans_api.py` and `pm_helpers.py`, `MeterLinkDialog.vue`, the diffs of
`MetersCard.vue`, `EquipmentMoveModal.vue`, `EquipmentDetailView.vue`, `PmPlansCard.vue`, `PmPlanView.vue`,
`PmTemplateView.vue`, `PmItemDialog.vue`, `meterLabels.js`, `pmLabels.js`, `equipmentLabels.js`,
`useFormModal.js` (`modalError`), `ReadingHistoryModal.vue`, the e2e diffs and `e2e/support/`, the docs diffs.

## Still to check by hand in a browser

Nothing new. A1 has no real-device check (A1.9), and the browser tests cover the card, the dialog, the move and the
plan page.

## Feedback

- idea: the snapshot diff of a round that adds an untracked file is not seen by `git grep` (it searches tracked files
  only), so a removal sweep with `git grep` misses `MeterLinkDialog.vue` and `test_migration_v58.py`. The ripgrep
  tool sees them. A line in the code reviewer's instructions ("search removals with the Grep tool, not `git grep`")
  would prevent a false "clean" (my first sweep).
- idea: an amendment that changes a rule which a gate record in `docs/Plan.MD` states (here the gate A paragraph
  of § 4.3 and the module table row) could list those lines in its *Docs* bullet. The brief named § 4.1, § 4.3 and
  § 4.5 but not the two records, and both were missed (CR7-01).
