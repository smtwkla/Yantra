```
Step: S096 — PM plans on a machine
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 01-11-2026
```

Reviewed against: c9cd091 (S095's code is not in the working tree yet; its brief, revised after its
review r1, was read for the constants and the input rules)

# S096 — brief review, round 1

**Verdict: no `blocker` and no `major` is open.** Seven `minor` findings and a short list of nits.
The migration v51, the key `pm_plan:edit` and its site scoping, the read rule, the lock sequences,
the item sync and the inputs' boundaries hold against the code as it stands. The two things a
coder would otherwise meet alone are an existing test file that turns red when v51 is appended
(BR1-01) and the checks that need the stored row, the meter type or today's date, which
`validate_plan(body, creating)` cannot make (BR1-02). The size question: **no split** (BR1-07).
Facts file read: `scratch/brief-facts-S096.md`; every cited line and name checks out. Full track,
round 1 of up to 3.

## Findings

### BR1-01 — minor — Two migration tests turn red when v51 is appended; the brief calls one green

**Problem.** `backend/tests/test_migration_v50.py` builds `V50 = local_db._MIGRATIONS` (line 25) and
asserts `_versions() == [41, 50]` in four tests (lines 114, 156, 250, and the re-run test asserts
`50 in _versions()`, line 237). `backend/tests/test_migration_squash_v41.py` builds
`CURRENT = local_db._MIGRATIONS` (line 27) and asserts `_versions() == [*range(20, 42), 50]` (line
108). With v51 at the end of `_MIGRATIONS`, `_versions()` ends `…, 50, 51` and the four equality
asserts fail. § 8.3 says the v50 file's "assertions are on the vendor and contract tables; green (to
verify by the run)", and does not name the squash file.

**Why it matters.** The coder sees a red backend run and must decide alone how to edit two frozen
migration tests. The rule for migration tests is that each version's file tests its version.

**Options.**
- **(a) Recommended.** In `test_migration_v50.py`: `V50 = [m for m in local_db._MIGRATIONS if m[0] <= 50]`
  (as `SQUASHED` filters in `migration_helpers.py:20`); the file then tests v50 alone, as before.
  In `test_migration_squash_v41.py`, keep `CURRENT` whole (the test's point is "production's v41
  reaches the current schema") and assert
  `_versions() == [*range(20, 42), *[m[0] for m in CURRENT if m[0] > 41]]`, so no later migration
  edits it again. Name both edits in § 3 Tests and § 8.3.
- (b) Filter both to `<= 50`. The squash test then stops proving production reaches the latest
  version.

### BR1-02 — minor — The checks that need the stored row, the meter type or today cannot live in `validate_plan(body, creating)`

**Problem.** § 5.1 gives `validate_plan(body, creating)` to `clean_body` (`api_common.py:121`), which
calls `validator(body, creating)` before any read. Three rules of § 5.1 need more than the body:
- `meter_every` and `last_done_meter`: "`parse_number(raw, decimals)` of the meter type" — the type
  is known only after the meter choices are read (§ 5.7 step 3);
- `calendar_every` 1 to the unit's maximum: on a `PUT` that sends only `calendar_unit` (month →
  year with 120 stored), the bound must be checked on the merged pair;
- `last_done_on` "to today (IST, passed in by the shell)" — the signature has no `today`.
§ 5.7 step 3 says "the rules of § 5.1 on the merged values", but names only `trigger_error(merged)`,
which checks null-ness.

**Why it matters.** The coder must invent the split. Two coders would split it differently, and the
§ 8.2 core tests ("0.05 with 1 decimal refused", "121 months refused", "tomorrow refused") name no
function for these cases.

**Options.**
- **(a) Recommended.** Two phases, both in `pm_plans_core`: `validate_plan(body, creating)` parses
  `meter_every` and `last_done_meter` with the column's 3 decimals (`parse_number(raw, 3)`),
  `last_done_on` as a date from 2000-01-01, and the per-field rules of the table. Then the shell,
  after its reads, calls `plan_rules_error(merged, meter_type, today)` → `(field, message)` or
  `None`: the null-ness rules of § 5.1 (today's `trigger_error`), the per-unit maximum on the merged
  `calendar_every` / `calendar_unit`, the meter type's decimals on both meter numbers (the same
  `parse_number` texts), and `last_done_on ≤ today`. Move the three test groups to it in § 8.2.
- (b) Give `validate_plan` a third argument with the stored row, the type and today, and wrap it
  for `clean_body`. It then needs the reads before the body is parsed, so a bad body costs a
  transaction.

### BR1-03 — minor — `trigger_text`'s number recipe gives "Every 250.0 h", not "Every 250 h"

**Problem.** § 5.2: "numbers with Indian grouping (`grouped_number` with the type's decimals,
trailing zeros of a whole number dropped through `format_number` first)". `grouped_number(value,
decimals)` (`meters_core.py:390`) formats with `f"{Decimal(value):.{decimals}f}"`, so it puts the
zeros back: *Run hours* has 1 decimal (migration v29 seed), and `grouped_number(Decimal("250"), 1)`
is `"250.0"`. Running `format_number` first changes nothing. The same holds for `item_limits_text`'s
"30–60 °C" on a 1-decimal gauge, and `meters_core._range` (the text the brief copies) is private.

**Why it matters.** Every example of § 5.2 and § 8.2 ("Every 250 h", "5,000 h", "Every 0.5 h") is
wrong under the stated recipe, and the e2e test asserts "Every month or 250 h, whichever comes
first".

**Options.**
- **(a) Recommended.** A 3-line helper in `pm_plans_core`, `interval_number(value, decimals)`: the
  places the value really has (`len(format_number(value).partition(".")[2])`, capped at the type's
  decimals), then `grouped_number(value, places)`. "250" → "250", "0.5" → "0.5", "5000" →
  "5,000". `item_limits_text` uses the same helper for Min and Max with an en dash, so the limits
  line matches the card's wording without importing `_range`.
- (b) Show the type's decimals everywhere ("Every 250.0 h"), as the readings card does
  ("1,996.4 h"). Consistent, but reads oddly for an interval.

### BR1-04 — minor — The roles shown beside names are not in the answers

**Problem.** § 5.8 shows "7 items · Kannan (technician)" on the card, § 5.9 "Created 01-11-2026 by
Priya (engineer) · Changed … by Arun (manager)". § 6.1 and § 6.2 give `assignee: {id, name}`,
`created_by_name` and `updated_by_name`: no role. (The select's "Kannan (technician)" is fine: it
comes from `/api/tickets/people`, which carries `role`.)

**Why it matters.** The coder either adds fields the brief does not define or drops text the brief
specifies; the card's row is what the floor reads.

**Options.**
- **(a) Recommended.** `assignee: {id, name, role}` in § 6.1 and § 6.2, the role from the person's
  membership at the node's current site (`person_at_site` gives it; the list joins `memberships`
  at the site in one query); the card and the page show "Kannan (technician)" from it. Drop the
  role from the Created / Changed line ("Created 01-11-2026 by Priya · Changed … by Arun"), as the
  lesson page shows names only.
- (b) Drop the role from the card too ("7 items · Kannan").

### BR1-05 — minor — A reading item on a gauge meter: where do its Min and Max come from?

**Problem.** § 5.10: with a gauge meter the dialog shows Min and Max; the meter choice (§ 5.5) carries
the meter's `min_value` and `max_value` in force on the node. Nothing says whether the dialog
pre-fills them, and nothing says that an item's limits may differ from the meter's. R03.4 will flag
the value High / Low by the item's limits and also write a meter reading, which gets the meter's own
`limit_state` from `meters.log_reading`.

**Why it matters.** The engineer re-types 30 and 60 for every oil-temperature item, or the coder
pre-fills on its own. Two limit pairs for one quantity is a rule R03.4 inherits; it should be a
sentence here.

**Options.**
- **(a) Recommended.** When a gauge meter is chosen in the dialog, Min and Max are pre-filled from
  the choice's limits in force; the engineer may change or clear them (a check limit may be tighter
  than the alarm limit). The item's limits are the job's (R03.4); the meter reading keeps the
  meter's own state. One line in § 5.10 and one in A6 (notes for R03.4).
- (b) A reading item with a gauge meter has no limits of its own (the meter's apply), with the CHECK
  `meter_type_id IS NULL OR (min_value IS NULL AND max_value IS NULL)`. Simpler, but a job cannot
  hold a tighter check limit.

### BR1-06 — minor — A third copy of `_iso_date`

**Problem.** § 3: "a stated 7-line copy of `contracts_core._iso_date` (`backend/contracts_core.py:46`),
as S080 D9 did". `contracts_core.py:47` says its copy is itself "a copy of
`improvements_core._iso_date`" (`improvements_core.py:394`). S096 would be the third copy; R03.3
and R03.9 (reschedule dates) will want a fourth. S095 D6 met the same rule (cores do not import
each other's private helpers) by making `_add_months` public as `add_months`.

**Why it matters.** CLAUDE-COMMON *DRY*: one rule, one place; `masters_core.py:377–382` is the
pattern for publishing a core's helper by name.

**Options.**
- **(a) Recommended.** Add `iso_date = _iso_date` to `contracts_core.py` beside its parser (one
  line, after S095's rename lands) and import `iso_date` in `pm_plans_core`; § 3 lists
  `contracts_core.py` as touched.
- (b) Keep the copy, as S080 did. Three copies of one parser.

### BR1-07 — minor — Size: keep one step (recommended), with the coding order the brief already gives

**Problem.** The orchestrator asked for a judgement. The brief is 995 lines; 21 code and test files
plus 5 docs; two tables, two screens and one dialog; one key.

**Judgement.** No split. The roadmap's rule (R03 "Size and the step rule": a record and its lines
are one concern; a split at 25 files) is not met: 21 code and test files, and the docs are
housekeeping. The halves do not stand alone: the API without the card and the page has no
acceptance on the floor, and the screens without the API cannot be coded. The brief's length is
the field tables and the lock text, which the coder needs in one place. What keeps the code review
to one sitting is the order the brief already fixes (core tests → shell → screens): the coder hands
back in that order, and the code reviewer reads the backend before the frontend.

**Options.**
- **(a) Recommended.** One step; add to § 9 that the coder's hand-back lists the files in the
  order backend, tests, frontend, and that the code review reads them so.
- (b) Split: S096 the migration, core and API with its tests; S097 the card, the page, the dialog
  and the e2e tests. Two gate A's and two code reviews for one concern.

## Nits

- **BR1-08** (nit) § 4.1 bullet "The ENUMs equal S095's constants" and § 9 A6: "the core's plan
  mapping names the key `kind`; R03.3's shell passes `kind=row["trigger_kind"]`" is stale. S095
  BR1-01 (accepted) renamed the input key to `trigger_kind` (S095 § 5.1), so the shell passes the
  row as it is. Replace both; A1 already covers a rename of the tuple.
- **BR1-09** (nit) § 3 Docs, `notes.json`: the planned `pm_plans` line reads "kind (PM / CIL), …
  source template, … before use". Say the new line drops `kind` (CIL is a plan whose performer is
  the operator, Plan § 4.4) and `source template` (R03.8's migration), so R03.8 and R03.12 know.
- **BR1-10** (nit) § 4.1 `uq_pm_plans_title`: inactive plans count, so the 409 should say so:
  "This machine already has a plan with this title, active or inactive. Choose another title, or
  reactivate that plan."
- **BR1-11** (nit) § 5.1 `before_use` message: "come in a later step" is workflow jargon on a screen.
  "Before-use plans are not available yet. Choose a calendar or meter interval."
- **BR1-12** (nit) § 5.10 call contract: `useFormModal`'s default `label` reads `record.full_code ??
  record.code` (`useFormModal.js:18`); an item has neither. Pass `label: (item) => item.text`, or say
  the dialog never shows `editingLabel` (its title uses the index).
- **BR1-13** (nit) § 9 A6, for R03.3: S095 needs `created_on` (an IST `date`); S096 stores
  `created_at`. Add "`created_on` is the IST date of `created_at`".
- **BR1-14** (nit) § 5.9 Deactivate: `ActiveToggle`'s line "Deactivate **Monthly hydraulic check**?"
  names no consequence (CLAUDE-COMMON scope B). Either accept the shared component's form (say so)
  or put "It makes no more jobs." under it.

## Checked and found consistent

- **Migration v51.** Column types, NULL rules and defaults match the API rules of § 5.1 and § 5.4;
  `trigger_kind` and `calendar_unit` list S095's `KINDS` and `CALENDAR_UNITS` in order. The four
  table-level CHECKs of `pm_plans` and the four of `pm_plan_items` are each a valid MariaDB
  expression over NOT NULL and NULL columns (the `(x IS NOT NULL) = (…)` form compares 0/1, never
  NULL); together they give exactly the § 8.1 refusals and passes listed. `uq_pm_plans_title
  (equipment_id, title)` and `ix_pm_plan_items_plan (plan_id, active, position)` serve the two
  first foreign keys as leftmost prefixes, so MariaDB adds indexes only for the assignee and the
  two meter keys; the items read (`plan_id, active = 1 ORDER BY position, id`) uses the index.
  `CREATE TABLE IF NOT EXISTS` twice is re-run safe; no `_PRECONDITIONS` entry is right (new tables).
  v50 ends `_MIGRATIONS` today (`local_db.py:1158–1257`); `LATEST_VERSION` follows.
- **S095 fit.** `calendar_every` int ≥ 1 and not bool, `meter_every` Decimal > 0, `last_done_meter`
  ≥ 0, `calendar_unit` set exactly with `calendar_every`, `meter_every` exactly with
  `meter_type_id`: S096's parsers and CHECKs give S095 § 5.1's inputs. The bound of 10 years (day
  3650, week 520, month 120, year 10) is far below `add_interval`'s overflow at 9999; S096 never
  calls the core (D7 of S095). `before_use` is in the ENUM and refused by the API (D6).
- **`pm_plan:edit`.** `("maint_engineer",)` → the manager through `ROLE_INCLUDES`, not IT admin, not
  the supervisor; Plan.MD's matrix (line 140) already shows it so. In `SITE_SCOPED`, so
  `load_node_for_user(…, key="pm_plan:edit")` passes `_check_site_args` (`auth_utils.py:435`) and
  `require_perm_at` answers "You can't do this at BRICKS" for an engineer of A on a node of B where
  they are operator; `require_perm` answers 403 first when the key is held nowhere (IT admin). The
  `test_role_matrix` rows and `test_pm_plan_keys` are the right always-check tests.
- **Read rule.** `equipment:read` is `("*",)` and in `SITE_SCOPED`; `load_node_for_user` gives the
  404 outside the units and all units to IT admin (`equipment:read_all_units`). Every ancestor of a
  node is in the root's unit (`NODE_JOINS`, `equipment.py:195–199`), so reading the parent and
  grandparent with the same call is the same access, as `_ticket_path` says (`meters.py:588`).
- **Locks.** (6e) is the next free number after (6d) in `equipment.py:9–28`. Create: node LOCK IN
  SHARE MODE first (as `contracts._check_node`, `contracts.py:520`), then plain reads, then the
  inserts' shared FK locks. Change: the plan row FOR UPDATE first, then the node shared, then plain
  reads, then `update_row` / the item writes. No module holds another lock and waits on a
  `pm_plans` row; the node writers (`equipment.py`, `meters.py`, `item_properties.py`) hold the node
  exclusive and never touch plans; masters' person and meter-type writes never wait on a plan row.
  The one deadlock (a part's plan write holding the part shared, its insert waiting on the machine's
  FK lock, against a scrap locking the subtree top-down) is the accepted case of `equipment.py:105–112`.
  Two creates of one title meet `uq_pm_plans_title` → 409. "A locking read does not start the
  snapshot; the first plain read does" is InnoDB's rule under REPEATABLE READ.
- **Item sync.** Insert / update of changed fields and position / deactivate, positions 1..n over
  the sent order, an unknown or foreign id 400, a duplicate id 400, inactive rows keeping their
  position with no unique key on it: sound, and every case is in § 8.2. `MAX_ITEMS` 50 over the
  sent list.
- **Inputs.** Each bound of § 5.1 and § 5.4 has both sides in § 8.2 (100 / 101, 120 / 121, 3650 /
  3651, 10 / 11, 0 / 1, −1 / 0, today / tomorrow, 50 / 51, Min = Max). `parse_number` refuses a
  bool and a float and bounds by `LIMIT_MAX`; `optional_text_parser` keeps line breaks in help text;
  `collapsed` on title and item text; `flag_parser` on the two flags; `int_arg`'s 400 for the query.
- **Reuse.** `person_at_site` + `ASSIGNABLE_ROLES` + `ASSIGNEE_AT_SITE` (the ticket rule, D7);
  `/api/tickets/people` (D11; `ticket:raise` is held by every `pm_plan:edit` holder through the
  ladder); `effective_meters`, `read_models_meters`, `_nodes_rows`, `_last_readings`, `_add_last`
  behind the new `meters_with_last`, and `readings_sheet.meters_of` (`meters.py:502`) does exactly
  that per node; `UNIQUE_KEY_ERRORS`, `clean_body`, `insert_row`, `update_row` (stamps `updated_*`
  only when something is sent), `row_to_dict`, `people.username` joins as `_LESSON_SELECT`;
  `ActiveToggle` with `FORM_DIRTY` (`FormModal.vue:44` provides it today; the page will);
  `FormModal`'s `footer-left` slot exists (`FormModal.vue:194`); `useFormModal.send` closes the
  modal then calls `afterSave`, as § 5.10 relies on.
- **Layering.** Rules and texts in `pm_plans_core` (pure; imports only other cores' public names);
  `pm_plans.py` a thin shell; `pmLabels.js` presentational helpers only (`kindFromTicks`,
  `planBody`, `moveItem`). The one frontend copy of a rule (the verification default by performer)
  is a form default, not a decision.
- **Screens on a phone.** The page, not a dialog (D1), so the 50-item list and the item dialog
  never nest modals; one column in the order Plan, When due, Items, buttons full width; the item
  dialog is five to seven fields with the save button in the FormModal footer and
  `expectDialogFits` in every flow test; large *Move up* / *Move down* buttons (D9); *Cancel* and
  *Remove item* ask in place; the disabled *By meter* tick carries its reason; the 404 and 403
  screens have a way back; the floor reader sees the card only where a plan exists, the technician
  and IT admin read the page without controls. The card's place (after *Open tickets*, `order-0`)
  keeps the two order tests at `contracts.spec.js:586` and `lessons.spec.js:258` green.
- **Tests named.** `make_meter_type`, `give_site_role`, `user_at_sites`, `db_rows`, `db_down`,
  `meterMachine` (`modelMeters` as `[[name, limits]]`), `noModelPart`, `apiAs`, `expectDialogFits`,
  `expectFieldMessage`, `expectNoSidewaysScroll`, `screens()`: all exist with the shapes the brief
  uses. *Oil temperature* is a seeded 1-decimal gauge and *Run hours* a 1-decimal counter
  (`local_db.py:1067–1075`), as the e2e set-up needs. `conftest._TABLES` takes the two new tables
  first (`conftest.py:186`). No device check is right: nothing needs a camera, a printer, Keycloak
  or a real keyboard.
- **Standards.** TPM planned maintenance, EN 13306 (task, inspection, predetermined), ISO 55001
  § 7.5, ISO 9001 § 7.5.3 with the recorded departure, ISO 14224 (the meter at the level where
  hours differ) and ISO 27001 A.5.15 are named and explained in plain words; the *to verify* marks
  are kept. Plant-Facts § 6 ("no PM schedule to migrate", line 169) is cited right.
- **Plan.MD.** Q2.1 a (the item shape), Q2.2 a (IT admin reads only), Q5.1 a (verification
  default), Plan § 4.3 *Which meter a plan uses* (D5), *Performer* (the contractor as assignee),
  *Both triggers, whichever first*; the one departure (years, D8) is recorded for the Plan note.

## Feedback

- hindrance: the brief is 995 lines (29.5k tokens), over the Read tool's cap, so it took two reads
  and the second half had to be requested by offset (`1-brief.md`, lines 715–995).
- idea: the facts file marks `pm_schedule_core` "planned in S080, S095; S080 now coded — re-check"
  (`scratch/brief-facts-S096.md` line 418): S080 never planned it; a name planned in a step that
  is Done should not be flagged as that step's.
- idea: the facts file's *Screen text in the tests* lists `"weekly"` (a refused API value in § 8.2),
  not a screen text; quoted strings inside a tests section could be skipped there.
