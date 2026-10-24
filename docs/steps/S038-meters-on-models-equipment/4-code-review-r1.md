```
Step: S038 — Meters on models and equipment
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 24-10-2026
```

# S038 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The step builds what the
brief asks for, and every test run is green. There are 2 minor findings and 2 nits.
One minor finding (CR1-01) is a design choice for the user at gate B.

Reviewed: S038's files as listed in the impl report § 3, on top of S037
(v29), against HEAD ff9ddb3. The snapshot tooling (`tooling/steps/step_snapshot.py`,
`step-snapshot.bat`, `step_ls.py`, `test_step_snapshot.py`, the SKILL.md and
CLAUDE.md lines) is not part of this review.

## Tests run

Run name `s038cr1`.

| Run | Result |
|---|---|
| `tooling/run-tests.bat` | ALL SUITES PASSED: backend 2713 passed (175 s), frontend 149, deps 42, tooling 115 |
| `npx vite build` (frontend) | built in 4.21 s; the usual chunk-size warning only |
| `tooling/run-e2e-tests.bat e2e/masters.spec.js e2e/equipment.spec.js e2e/screens.spec.js` | 123 passed in 5.2 min (6 lanes; Pixel 7, iPhone 14, desktop) |

Why these specs: the step changes the Masters › Models panel (`masters.spec.js`)
and the equipment page (`equipment.spec.js`); `screens.spec.js` opens every
route. The step changes no shared frontend code (`FormModal.vue`,
`useFormModal.js`, `api.js`, the router, the auth store, `e2e/support/`), so
the full suite is not needed. `frontend/src/stores/masters.js` changed, but
that is S037's `ensureMeterTypes`.

## Findings

### CR1-01 (minor) — An own meter added over a stale override deletes the override: the user should confirm it

`backend/meters.py:115-122`; also `backend/local_db.py:805` (the v30 comment)
and `docs/schema.md:43` (the `node_meters` row).

- **Problem.** Decision 3 covers a case the brief does not: a node holds an
  `own = 0` override of a type that its current model no longer has, and the
  engineer adds that type as an own meter. The code deletes the override row
  and inserts an `own = 1` row. The choice is sound: the unique key allows one
  row, refusing the add would be worse, and flipping `own` would break BR1-04.
  But it changes § 1.6 for this type: "an override … comes back if the model
  returns". After the add, the own meter's limits come back instead. The
  README (gate 2) says that a case the brief does not cover goes to the user,
  and the report lists it only as a decision.
- **Failure scenario.** Press P1 has an override "Oil temperature: up to 55 °C"
  on model A. P1 moves to model B, which has no oil meter. An engineer adds Oil
  temperature as an own meter with no limits. P1 moves back to model A. The
  card shows model A's 10–60 °C, not the earlier 55 °C. Nothing in the history
  says that the 55 °C override is gone. (The override was not in force when it
  was deleted, so no history line is correct by § 5.5.)
- **Also.** The v30 comment says "Rows are never deleted, only set inactive,
  except an own = 0 override that equals the model again". That is now one of
  two cases. The `node_meters` row in `schema.md` says the same in other words.
- **Suggested fix.** Ask the user at gate B to confirm decision 3 as built.
  Then name the second delete in the v30 comment (v30 is not applied in
  production yet, so the comment may change) and in the `schema.md` row.

### CR1-02 (minor) — The Meters card reloads on every page reload, not only on a node or model change

`frontend/src/views/equipment/MetersCard.vue:143-147`.

- **Problem.** The watch source is a getter that returns a new array,
  `() => [props.node.id, props.node.model_id]`. Vue compares the new array with
  the old one by identity, so the callback runs each time the getter re-runs.
  The getter re-runs whenever the page replaces `node` (`load()` sets
  `node.value = loaded`). After every meter save the card emits `changed`, the
  page calls `load()`, and the card sets `meters` to `null` and fetches again.
  The comment on the watch says it runs only for another node or a model
  change.
- **Failure scenario.** An engineer saves a limit. The card shows the saved list
  (from the PUT), then at once "Loading…", then the same list from a second
  GET. On the plant's slow Wi-Fi the card flickers after every save, and an
  open *Remove* confirmation on another row closes. Any other page reload (an
  edit of the details, a lifecycle change) also blanks the card.
- **Suggested fix.** Watch the two values as a multi-source watch, which
  compares each value: `watch([() => props.node.id, () => props.node.model_id], …)`.
  The e2e tests stay valid.

## Nits

- **CR1-03** (nit) `frontend/src/views/equipment/MetersCard.vue:195,203`: a model
  meter shows a red *Remove* that can never remove, and the help text lives
  twice (here and `backend/meters.py:154`). Consider no *Remove* on a model
  meter, with the help as a small line under it, so the words live once in the
  card; or keep decision 7 and leave it.
- **CR1-04** (nit) `backend/masters.py:890`: "The meter type is inactive" does
  not say what to do (scope B). Use "This meter type is inactive. Pick another
  meter type." It shows only on a race, since the select offers active types.

## Checked and found consistent

- **Migration v30** (`local_db.py`): both tables as § 4, with `ENGINE=InnoDB`,
  the unique keys, the FKs and the limits CHECKs; the ENUM widened at its end,
  so no row changes; no `_PRECONDITIONS` entry, as the brief says. IF NOT
  EXISTS and the same MODIFY make a re-run safe. `test_migration_v30.py` checks
  from v29: the old event rows kept, the three new values, both unique keys,
  both CHECKs, a one-sided limit, and a re-run.
- **`test_migration_v9.py`**: the change only updates the expected latest ENUM,
  as v25 and v28 did. It edits no applied migration.
- **Pure core** (`meters_core.py`): no DB, clock or Flask. `validate_limits`
  follows § 5.1: the kind check first, an explicit `null` on a non-gauge passes,
  `Decimal` never `float`, bools and floats refused, the column bound, the
  merged pair checked on `max_value`. `effective_meters` and `override_of`
  follow § 5.2, including the own row the model gains later (active or not) and
  the stale override left out. `limits_text` and `tracked_meter_change` are the
  one source of the wording; both sides of a history line are the limits in
  force.
- **Lock order.** Node writes take (1) the node (`load_node_for_user`,
  `equipment:edit` at the site, scrapped from the locked row) → (4b) the meter
  type `FOR UPDATE` → the `node_meters` row by its unique key `FOR UPDATE`.
  Model meter writes take (4) the model (`_lock_row`, an inactive model
  allowed) → (4b) → the `model_meters` row. A meter type update takes (4b),
  then counts both link tables `LOCK IN SHARE MODE`. No path takes (4b) and
  then (1) or (4); a model change on a node (`update_equipment`, (1) → (4))
  takes no meter lock. The new step (4b) in `equipment.py`'s LOCK ORDER and the
  notes in both docstrings say the same.
- **The model id** of a node write comes from the locked row (BR1-17), and the
  model's meters are read plainly (decision 6).
- **Rules of § 5.3**: 409 on a duplicate on the model and on the node (and the
  two `UNIQUE_KEY_ERRORS` entries); reactivation by POST only; a removed own
  meter's limits cleared; an override equal to the model leaves no `own = 0` row
  and NULLs on an `own = 1` row; a limits write never changes `active`;
  *Set limits* over a removed own row writes it and leaves it inactive; a model
  meter not removable on a node (409, the brief's text); "no longer on the
  model" 409; a deactivated type stays where it is linked.
- **The freeze** (`_check_meter_type_frozen`): a change is a value that differs
  from the stored one, so a re-sent dialog passes; inactive links count; the
  expected answer is frozen too.
- **Permissions.** Model meter reads `masters:read`, writes `equipment:edit`
  (as models, U4 D6). Node reads `equipment:read` at the node's site, writes
  `equipment:edit` at the site; 404 outside the user's units. The actor comes
  from `actor()`, never the client. No SQL is built from client strings (the
  two f-strings interpolate fixed table names and fixed WHERE fragments).
- **`SCRAPPED_MESSAGE`** is defined in `equipment.py` and imported by
  `documents.py` and `meters.py` (BR1-16); `update_equipment` uses it too.
- **`write_events` rename** (decision 10): forced by the cross-module import;
  the two monkeypatches follow.
- **Decision 11** (helpers in `masters.py`): forced by the import direction
  `meters.py` → `equipment.py` → `masters.py`; no cycle.
- **History**: one line per node write in the same transaction, none on a
  refused write or an unchanged pair; `describeEvent` names the meter once.
- **`MeterFormFields.vue`** (decision 9): a presentational component with only
  the select and Min / Max; the rules stay in the backend. It removes a
  near-copy between the two dialogs, and both dialogs keep their own requests.
  It is not shared frontend code in the e2e sense (only the two new dialogs use it).
- **Use on the floor.** Both dialogs are `FormModal` (`modal-dialog-scrollable`,
  the footer stays on a phone). *Use the model's limits* sits in
  `#footer-left`, only while overridden. *Remove* asks first, inline, with
  *Remove* / *Keep* and the brief's texts on the node and on the model. Empty
  states ("No meters.", the "Every meter type is on … already" text with *Save*
  disabled), the load error and the operator view without buttons are
  rendered. The `btn-sm` buttons match the rest of the equipment page.
- **Scope**: the six routes of § 6, the two screens, the kind labels read by
  S037's panel (BR3-04), the three event names. Nothing built beyond the brief;
  the eleven decisions are listed and none changes the approved design (CR1-01
  aside).
- **The docs pass**: `schema.md` (header, `meter_types`, `model_meters`,
  `node_meters`, `equipment_events`, the planned `meters` row removed, the
  Mermaid entities and four links) and `schema.html` (the meta line "Migration
  v30 … 32 tables, 45 links", both entities with every column on the Equipment
  tab, keyed columns on the Overview, the four links on both) match the v30
  text. `Plan.MD` § 4.1 and § 4.5 say what was built. `.claude/CLAUDE.md` maps
  `masters` and `equipment` to S038. No other listed doc is due.
- **Tests** cover the brief's § 8 list: the core's every § 5.1 row and § 5.2
  case; model meters (add, limits, remove, reactivate, non-gauge refusals,
  inactive type, duplicate, operator); node meters (list, own, override set and
  clear, equal to the model, the own row the model gains, removed own row,
  model change, 403 at another site, storekeeper read, scrapped, history per
  write and none on refusal); the freeze with an inactive link and the expected
  answer. The e2e tests assert what the user sees (the rows' texts, the history
  lines, the confirm texts, no buttons for the operator), call
  `expectDialogFits` on the dialogs they open, and keep off `SMTW-HYP-01`.
- **Manual checks**: the impl report's `## Manual checks` carries both
  important checks as `[auto]` with their tests, and the brief has no
  real-device check, so `device-checks.md` needs no row.

## Manual browser check (user)

None is required: the brief has no real-device check, and the two important
checks are automated. Optional, at gate B: on a phone, open a press's page,
save a limit, and watch the Meters card (CR1-02's flicker until it is fixed).
