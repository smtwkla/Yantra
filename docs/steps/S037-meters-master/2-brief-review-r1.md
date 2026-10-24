```
Step: S037 — Meters master
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 24-10-2026
```

Reviewed against: e451c33 + uncommitted S035

# S037 — Brief review, round 1

**Verdict: no blocker or major finding is open.** Four minor findings and nine
nits. The design is right-sized: one table, a pure validator on the
`validate_trade` pattern, three thin routes, one panel on the `TradesPanel.vue`
pattern. The minors are about wording the coder would otherwise decide alone
(validation messages, the list response shape, the *Status* header) and a test
design that would break on the second run. Facts file `scratch/brief-facts-S037.md`
read; every file, line and name it lists checks out.

Full track, round 1 of up to 3. S038 and S039 were read only for fit (one fit
nit, BR1-13).

## Minor

### BR1-01 — minor — § 5.1: the validation messages break the masters' wording and the `_validate` machinery

**Problem.** The brief's messages are "Enter a name", "Use 60 characters or
fewer", "Enter a unit, such as h or kWh", "Pick counter or gauge", "Enter 0, 1,
2 or 3". Every master today says "Name is required" and "Name must be at most
50 characters" (`_parse_bounded_name`, `masters_core.py:51`), and a field
missing on create gets "<Field> is required" from `_validate` itself
(`masters_core.py:290`). The e2e "Masters sections" loop asserts "Name is
required" (`masters.spec.js:120`).

**Why it matters.** CLAUDE-COMMON scope B: the same word for the same thing in
the whole app. Two wordings for "you left the name empty" on neighbouring
Masters tabs is the inconsistency the rule forbids. To produce "Enter a name"
for a missing field the coder must special-case `_validate` or write a parallel
validator: a decision the brief leaves to the coder.

**Options.**
- (a) **Recommended.** Keep the masters' wording: "Name is required", "Name
  must be at most 60 characters", "Unit is required", "Unit must be at most 20
  characters", "Kind must be counter or gauge", "Decimals must be a whole
  number from 0 to 3". Reuse `_parse_bounded_name(…, 60)` on `_collapsed`
  input, `_parse_cause_group`'s shape for `kind`, and a new `_parse_decimals`.
  A re-wording of every master's messages in the "Enter a …" style is the
  queued *Tidy-up*'s job, done once for all.
- (b) Keep the brief's wording and add a per-field "required" message to
  `_validate` (an optional third tuple member). Nicer text, but the Meter types
  tab then speaks differently from Trades beside it.

### BR1-02 — minor — § 6: the GET response shape is not what the store reads

**Problem.** § 6 gives `GET /api/masters/meter-types` → `[{id, name, …}]`, a
bare list. Every master list route returns `{items: [...], total}`
(`_list_response`, `masters.py:136`), and `stores/masters.js:29` reads
`.items`. The brief names `ensureTrades` as the pattern, which needs `.items`.

**Why it matters.** A coder who follows § 6 literally writes a route the store
cannot read, or a store entry that differs from its nine siblings.

**Fix.** Write the response as `{items: [{id, name, unit, kind, decimals,
active}], total}`, via `_list_response`, as trades.

### BR1-03 — minor — § 8: tests that edit a seed row fail on the second run

**Problem.** § 8 asks for "list: the seeds, active only" and "update kind,
unit, decimals; deactivate; reactivate" without saying which rows the update
tests use. `_clean_tables` keeps the seed rows between runs (it deletes only
rows whose `created_by` is not the seed creator, `conftest.py:188`). A test that
deactivates "Fuel level", or renames "Run hours", leaves the seed row changed,
and the next run's "the seeds, active only" fails; in a lane of the e2e suite
the three browser projects share one database too.

**Why it matters.** A flaky suite on the second run, found by whoever runs
tests next, not by the coder.

**Fix.** State the rule `test_failure_codes_api.py:3` already follows: "the
seed rows are read, never changed; test rows take names from the `uniq`
fixture". The seed check asserts the seven names are present and active; the
update tests create their own row first.

### BR1-04 — minor — § 1.4: the table's active column is headed *Status*

**Problem.** § 1.4 lists the columns *Name*, *Unit*, *Kind*, *Decimals*,
*Status*. The user decided on 23-10-2026 (S030 CR1-04; README › Queued,
*Tidy-up*) that the Masters tables' active / inactive column is headed
*Active*, not *Status*: *Status* is reserved for down / working / degraded /
PM due since S030.

**Why it matters.** A new panel built with *Status* adds one more table to the
tidy-up, and shows the reserved word on a screen the user reads.

**Fix.** Head the column *Active* in this panel (the badge text *Active* /
*Inactive* stays). The other panels change in the tidy-up.

## Nits

- **BR1-05** (nit) § 1.1: "Decimals: 0 to 3, required, default 0" — "required"
  and "default 0" contradict; § 5.1 says absent → 0. Write "optional, default 0".
- **BR1-06** (nit) § 1.1 vs § 1.3: the example name is "Oil temperature (max of
  day)", the seed is "Oil temperature". One name; the "max of day" is a rule of
  the reading (S039), not of the type.
- **BR1-07** (nit) § 1.4: say the controls. *Kind* as two radios with the help
  line (the `PeoplePanel.vue:348` employment pattern; a select hides the two
  choices behind a tap); *Decimals* as a select 0 / 1 / 2 / 3 (a number input
  opens a keypad on a phone and accepts 7).
- **BR1-08** (nit) § 3 frontend: `resetMasters()` (`masters.js:85`) must also
  null `meterTypes`, or a saved type never refreshes the other lists' cache.
- **BR1-09** (nit) § 5.1: say the unit keeps its case as typed ("kWh", "°C"):
  `_collapsed` only, no upper-casing (`_code_parser` upper-cases, and the coder
  may reach for it). Name the bool guard for `decimals`
  (`isinstance(raw, bool)`, as `_parse_id`, `masters_core.py:132`).
- **BR1-10** (nit) § 8 e2e: the added type's name must carry the project name
  (the three Playwright projects share one database, `masters.spec.js:28`).
  Add a *Meter types* row to the existing "Masters sections" loop
  (`masters.spec.js:115`) for the empty-save refusal; the operator test stays.
- **BR1-11** (nit) § 3 Docs: Plan.MD § 4.5 says "a unit of measure and a
  **type**: counter or gauge". The update at approval should say *kind* there
  and introduce *meter type* for the catalogue entry, or the two texts use
  "type" for two things.
- **BR1-12** (nit) § 1.1 and § 4: "case-insensitive, the table's collation" —
  the table sets only `CHARSET utf8mb4`; the collation comes from the
  database (`utf8mb4_unicode_ci`, `conftest.py:53`, `e2e_backend.py:64`, and
  the production init script). Write "the database's collation, as
  manufacturers".
- **BR1-13** (nit) fit with S038: S038 § 3 Tests puts `meter_types` among the
  tables `_TABLES` empties ("before `equipment`, `equipment_models`,
  `meter_types`"); S037 § 3 puts it in `_SEEDED_TABLES`. S038's text is the
  one to fix (for the planner, not this brief). S038 § 1.5 and § 3 otherwise
  match S037 (kind, unit, decimals editable here, frozen there;
  `validate_meter_type` unchanged; `MAX_DECIMALS` 3 = `DECIMAL(14,3)`).

## Checked and found consistent

- `equipment:edit` is `("maint_engineer", "it_admin")`, manager inherits
  engineer (`config_rbac.py:96`, `ROLE_INCLUDES`); it edits manufacturers and
  models at `masters.py:500` and `:515`; it is in `SITE_SCOPED`, and
  `require_perm` checks the union (`auth_utils.py:449`), as the brief says.
  `masters:read` is `('*',)`. Plan.MD § 3 matrix agrees. No new key, so
  `test_rbac.py` is unchanged.
- Pure core, thin shell: `validate_meter_type` on `_validate` + a field table,
  as `_TRADE_FIELDS`; the routes on `list_trades` / `create_trade` /
  `update_trade` (`masters.py:741–767`): `_include_inactive`, `_lock_row`,
  `insert_row`, `update_row`, `UNIQUE_KEY_ERRORS` for the 409. No parallel
  helper planned.
- Migration v29: `CREATE TABLE IF NOT EXISTS` + `INSERT IGNORE` on the unique
  name, re-runnable as v11's seeds (`local_db.py:524`, `:541`); no
  `_PRECONDITIONS` entry is right for a new table (as v22, v24); v28 is the
  last version (`local_db.py:760`). `test_migration_v29.py` fits the
  `test_migration_v28.py` shape (`_recreate`, `_migrate(V28)`, `_migrate(V29)`,
  `_schema()` for the re-run).
- The frontend places: `MastersView.vue:28` is the *Models* tab, `:39` its
  panel entry; `ModuleToolbar` wraps (`flex-wrap`), so a tenth tab fits a
  phone. `masters.js:62` is `ensureTrades`. `useMasterForm` gives create, edit,
  deactivate with confirm, reactivate; the `TradesPanel.vue` dialog (one field
  plus the toggle) fits a phone, so four fields and the toggle will too, to be
  shown by `expectDialogFits`.
- Seven seeds against the plant: strokes, run hours, kWh and the day's oil
  temperature (Plant-Facts line 129), genset run hours and fuel level (line
  130), odometer for the fleet (Plan.MD § 4.1), production count (§ 8 of the
  philosophy). `created_by 'migration-v29'` tells them apart, as v11's.
- Standards: counter and gauge as the philosophy § 8 defines them; ISO 14224
  operating time and demands as reliability denominators; EN 13306
  condition-based maintenance; ISO 50001 § 6.4 / § 6.5 (energy performance
  indicators and the baseline — § 6.6 is the data collection plan, S039 cites
  it); ISO 9001 § 7.1.5. Clause numbers are marked "to verify", rightly. The
  catalogue itself is the ISO 8000 point already in the code (`_collapsed`,
  `masters_core.py:63`: one spelling per real thing).
- Out of scope is right: limits on the meter (U1), text-valued meters (§ 9.2 to
  the user), PM triggers (phase 4).
- Manual checks: nothing a browser can judge is on the device list; the device
  list is empty, correctly. `screens.spec.js` needs no change (a Masters tab,
  not a route).
- Writing: scope A in the brief; the help line under *Kind* (§ 1.4) and the
  409 text (§ 5.2) follow scope B.
