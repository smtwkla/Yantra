Step: S035 — Equipment properties: master, classes and models
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 24-10-2026

Reviewed against: 06e16e4 + uncommitted S035 (the brief and its README index row)

**Verdict: one `major` finding is open (BR1-01); no `blocker`.** Round 1, full track.
Facts file read: `scratch/brief-facts-S035.md`; the names it marks "not found" are new in
this step by design. The split (S035 master, links, model values, seed, read-only card;
S036 overrides with history) is right: S035 stands alone and each half is reviewable. The
seven `minor` findings are rules the coder would otherwise decide alone, one misleading
standards claim, and one screen flow; none changes the user's decisions U1–U5.

## Findings

### BR1-01 — major — the seed makes properties of what Yantra already keeps as the equipment *type*

**Problem.** Six seed rows (§ 4.6) are *kinds* of equipment, not data about it: *Pump
type*, *Compressor type*, *Motor type*, *Valve type*, and *Execution* (Open, Closed).
Yantra already has that concept: the **equipment type** master (S004), defined per class,
fixed on the model (`equipment_models.type_id`), and shown on the equipment page's Details
card as *Type*. Plan.MD § 4.1 names exactly this example: "Equipment type (S004): how
equipment of a class is built, e.g. `RPP` → closed / open execution (ISO 14224 class →
type)". The S004 brief (lines 25–29, 59–60) decided *Closed execution* / *Open execution*
as the types of `RPP`. ISO 14224's class → type pairs (pump: centrifugal, reciprocating,
rotary; compressor: reciprocating, screw, centrifugal; valve: ball, gate, …) are its
*equipment type*, which S004 built. Open question § 9.2 asks the user what *Execution*
means; S004 and Plan.MD § 4.1 already answer it.

**Why it matters.** One fact in two places: a pump's kind on its model's `type_id` and
again in a *Pump type* property, with nothing keeping them equal. The failure-code scoping
and the MTBF "like with like" comparisons of S004/S016 read `type_id`, not a property. The
engineer who sets up the masters sees two lists asking the same question.

**Options.**
- (a) **Recommended.** Drop *Pump type*, *Compressor type*, *Motor type*, *Valve type* and
  *Execution* from the seed (26 rows remain; § 8.3's count follows). Add one rule to § 1 or
  § 10: "how equipment of a class is built is its *type* (S004, ISO 14224 class → type); a
  property is a datum about it (a rating, a dimension, a design choice such as *Drain*)". Close
  § 9.2: *Execution* is the `RPP` type pair of S004. Keep *Shaft sealing*, *Shaft orientation*,
  *Coupling*, *Actuation*, *Drain*: Annex A lists them as attributes, not as the type.
- (b) Keep the rows and say why both exist — rejected: the overlap stays, and the help text
  would have to explain it on the floor.
- (c) Replace the type master by properties — rejected: it undoes S004 and S012's composite
  FKs for no gain.

### BR1-02 — minor — § 2 "design and operating values" mis-states what S036's override is

**Problem.** § 2 bullet 2 says ISO 14224 keeps the design value apart from "the value at
the installation", and maps design → model (S035) and the installation's value → the item
(S036). In ISO 14224 Annex A, *design* is the maker's rating (nameplate, data sheet) and
*operating* is the actual service condition (the pressure and flow the pump runs at). An
operating value changes in service: in Yantra it is a reading (Plan.MD § 6), which the
brief's own *Out of scope* says. S036's override is not an operating value: it is the
item's own **nameplate** value where it differs from its model (a rewound motor now 5.5 kW,
a pump fitted with a different displacement cartridge).

**Why it matters.** The project owner is learning the standard from these briefs; this
line teaches the wrong distinction, and a coder in S036 could label the override
"operating". The glossary entry in § 11 repeats it ("the item its own where it differs" is
right; the standards framing above it is not).

**Options.**
- (a) **Recommended.** Reword bullet 2: the seed names say "– design" because Annex A
  records the maker's rating; the model holds that rating; an item holds its own rating
  only where its nameplate differs (S036); *operating* values are readings (Plan.MD § 6),
  not properties.
- (b) Drop the bullet — loses a useful point.

Also mark as unverified (the brief does this for the names, § 2 bullet 1; extend it to the
option lists): *Coupling: Direct*, *Shaft sealing: Lip seal, Seal-less*, and the valve and
actuation lists. I cannot check them against the standard's text either.

### BR1-03 — minor — changing `data_type` leaves the unit and the options undefined

**Problem.** § 5.1 fixes `data_type` and `unit` only once a model holds a value. Two cases
are not covered:
1. A choice property with options, no values, changed to *number* or *text*: its
   `property_options` rows stay. "Only a choice has options" (§ 6.1) is then false for this
   row; the list's *Type* column and the GET's `options` show options on a number; a later
   change back to *choice* finds them again.
2. A number with `unit = 'kW'` changed to *text* by a `PUT {"data_type": "text"}`: the
   stored unit stays, `chk_property_unit` fails, and the `IntegrityError` is not 1062, so
   `_integrity_error` re-raises it → 500 (`api_common.py` lines 49–58).

**Why it matters.** Both are one PUT away on the edit dialog; the coder would pick a rule
alone.

**Options.**
- (a) **Recommended.** `data_type` is fixed once the property has **any option or any
  value** (one rule, one message: "The data type cannot be changed: the property has options
  or models hold values of it. Make a new property instead."). A `PUT` that changes
  `data_type` away from *number* sets `unit` to NULL in the same UPDATE; a `PUT` that sends a
  non-empty `unit` for a property whose (stored or new) `data_type` is not *number* is a 400
  on `unit` "Only a number has a unit". State that the route checks the **combined** record
  (stored row + changed fields), because `validate_property` sees only the fields sent.
- (b) Deactivate the options on the change — more code, and the rows still show under *Show
  inactive*.

### BR1-04 — minor — "Edit model values" sends the engineer to Masters; the link has no target today

**Problem.** § 7.4: the card's link "opens *Masters › Models* filtered to the model".
`MastersView.vue` switches sections as local state (no route or query parameter), and
`ModelsPanel.vue` filters by class and manufacturer only. So § 3.3 lacks the changes this
link needs (a query parameter read by `MastersView`, a model filter or a scroll-to in
`ModelsPanel`). On the floor it is also the long way: equipment page → Masters → Models →
find the row → *Properties* → edit → back to the equipment page.

**Options.**
- (a) **Recommended.** Open `ModelPropertiesModal` from the card itself for users with
  `equipment:edit` (button **Edit model values**), reload the node on save. The component is
  already planned as reusable (§ 3.3); no new route or filter. Decision 8 then reads "the
  model's values are edited through the one `ModelPropertiesModal`, from Masters or from the
  card". The dialog title "Properties of <model label>" already says what is being edited.
- (b) Keep the link and specify the mechanism (`/masters?section=models&model=<id>`, read
  in `MastersView` and `ModelsPanel`), adding both files to § 3.3 — more code for a worse
  flow.
- (c) Drop the link in S035 — the engineer then finds the dialog in Masters unaided.

### BR1-05 — minor — the 409s for a duplicate name and a duplicate option label need `UNIQUE_KEY_ERRORS` entries

**Problem.** § 5.1 and § 8.2 expect 409 "A property with this name exists" and a 409 for
a duplicate option label. In this code base a duplicate is caught by the UNIQUE index and
mapped by `api_common._integrity_error` through `UNIQUE_KEY_ERRORS`, which each module fills
at import (`masters.py` lines 48–69). The brief names neither the entries nor the option
label's message.

**Options.**
- (a) **Recommended.** Add to § 5.1 / § 6.1: `properties.py` registers
  `uq_property_definitions_name` → `("name", "A property with this name exists")` and
  `uq_property_options_label` → `("label", "An option with this label exists")`; no
  pre-check query. Case-insensitive through the column's collation, as the brief says.
- (b) A `SELECT` before the insert — a race, and a second code path for the same rule.

### BR1-06 — minor — seed and test clean-up mechanics are not stated

**Problem.**
1. The option seed rows need their `property_id`. The brief says only "INSERT IGNORE on the
   property's name". The options must resolve the property by name at run time
   (`INSERT IGNORE INTO property_options (property_id, label, created_by) SELECT id,
   'Internal', 'migration-v26' FROM property_definitions WHERE name = 'Drain'`), keyed on
   `uq_property_options_label (property_id, label)`.
2. § 8.2 turns `SEED_CREATOR` into "a creator per table". `backend/tests/test_migration_v11.py`
   imports `SEED_CREATOR` from `conftest` (lines 10, 40, 44, 74, 80, 84). It is not in § 3.2.

**Options.**
- (a) **Recommended.** Write the option statement form in § 4.6. In § 3.2 keep
  `SEED_CREATOR = "migration-v11"` as it is and add a mapping
  `_SEED_CREATORS = {"failure_modes": SEED_CREATOR, …, "property_definitions":
  "migration-v26", "property_options": "migration-v26"}` used by `_clean_tables`; or list
  `test_migration_v11.py` as changed.
- (b) One creator string for every seed — would mean re-labelling the v11 rows; no.

### BR1-07 — minor — how the two set dialogs are wired to `useFormModal` and the `values.<id>` field

**Problem.** `ClassPropertiesModal` (PUT `property_ids`) and `ModelPropertiesModal` (PUT
`values`) are not a REST create/edit, so `useMasterForm`/`useFormModal.save()` (POST or
PUT `${path}/${id}` with the form as body) does not fit. § 6.2 says `ModelPropertiesModal`
"maps" `values.<id>` to its input but not how. `useFormModal.modalError` shows a refusal at
the top of the dialog when `error.field` is not a key of `form` (`useFormModal.js` lines
46–48); with a form shaped `{values: {12: …}}` the message "Enter a number" would show at
the top **and** `fieldError("values.12")` would be empty.

**Options.**
- (a) **Recommended.** State in § 7.2 / § 7.3: both dialogs use `useFormModal` for the
  modal, dirty guard and `send(request)` (as the Team dialog, `useMasterForm.js` line 46),
  with a custom request; the model dialog keeps its form keyed by the literal strings
  `"values.<property_id>"` (and builds `{"values": {...}}` in the request), so
  `fieldError("values.12")` and `modalError` work unchanged, and `PropertyInput` takes
  `fieldError` for its message. The class dialog's form has one key `property_ids`.
- (b) A new composable — a third pattern for one dialog.

### BR1-08 — minor — input edge cases the brief leaves to the coder

**Problem.** Missing or unstated cases (one line each is enough):
- `validate_option`: § 3.1 names it; § 5.1 has no rule for an option's label (recommend:
  required, trimmed and collapsed, 1–60 characters, "Enter a label" / "Use 60 characters
  or fewer").
- `PUT /equipment-classes/<id>/properties`: duplicates in `property_ids` (recommend: a set);
  an **inactive class** (recommend: allowed, as the inactive model in § 5.3, for the same
  reason).
- `PUT /equipment-models/<id>/properties`: `values` missing or not an object → 400 on
  `values`; a key that is not a positive whole number string (`"abc"`, `"12.0"`) → the § 5.3
  message on `values.<key>`; `{}` → 200, nothing changes.
- `parse_value` number: the accepted form in one line (optional `-`, digits, optional `.`
  and up to 4 digits; no `+`, spaces inside, `e`), since § 5.2 says "numeric string" and
  § 9.8 "plain digits".
- Deactivating the **last active option** of a choice that is linked: allowed (the link and
  values stay; nothing new can be picked) — say so under § 5.4, it follows from the rules
  but a coder may add a refusal.

**Why it matters.** Each is a decision the coder would take alone; two of them change what
a request returns.

**Options.** Add the lines above (recommended); or state that `tickets_core.part_quantity`'s
behaviour is the model for the number and the rest follows the masters' validators.

## Nits

- **BR1-09** (nit) header: `Baseline: c707dda + S034 fixes (06e16e4)` is not the README's
  form; the planner sets `Baseline` at approval from this review's `Reviewed against:` line.
- **BR1-10** (nit) § 6.2, § 6.3: say that a number's `value` is sent as the normalised string
  ("62.5"), not as the DECIMAL ("62.5000", which `jsonify` would also stringify).
- **BR1-11** (nit) § 8.4 "the model dialog fits a phone": `expectDialogFits` needs a Save and a
  Cancel button (`dialogs.js` lines 33–35); the no-properties state has only **Close**. Say
  the check is on a model whose class has properties.
- **BR1-12** (nit) § 1.2 says the dialog lists "the active properties"; § 7.2 adds linked
  inactive ones, ticked and disabled. Align § 1.2.
- **BR1-13** (nit) § 7.1 *Type* column "Choice · 2 options": say whether the count is of
  active options (recommend yes).
- **BR1-14** (nit) § 4.6: seed rows have no `description`, though § 1.1 defines it as "what
  the property means, where to read it". Give the number rows a one-line description
  ("Rated power on the nameplate, kW"), the help a learning engineer needs most.
- **BR1-15** (nit) § 2: one line for ISO 55001 § 7.5 (the organisation decides which asset
  information it keeps, and its quality) would place the property master in the asset
  management standard the plan already cites.
- **BR1-16** (nit) § 8.2 `db_down`: a third copy of the fixture (`test_access_control_api.py`,
  `test_auth.py`); moving it to `conftest.py` is a one-line change the step could make.
- **BR1-17** (nit) § 3.2 `_TABLES`: name the two rows and their place — `model_property_values`
  and `class_properties` before `equipment_models` and `equipment_classes` (the DELETEs run
  with `FOREIGN_KEY_CHECKS = 0`, so this is for reading order only).
- **BR1-18** (nit) § 7.1 and § 7.3 (scope B): "Models hold values of this property, so its
  type and unit are fixed." reads well; "The class <code> has no properties yet. Add them in
  Equip Class." — fine. § 6.2 "Choose active properties" is reachable only by API (the
  inactive boxes are disabled): fine as is, no change asked.

## Checked and found consistent

- **Permissions.** `equipment:edit` is in `SITE_SCOPED` (`config_rbac.py` line 162);
  `require_perm` → `has_perm` checks the union over the user's sites
  (`auth_utils.py` lines 348–358, 433–445). Classes and models are guarded the same way
  today (`masters.py` lines 317, 498), so a global master on this key is the existing
  pattern. `masters:read` is `('*',)`; no new key, `test_role_matrix` unchanged.
- **Locks (§ 5.6).** The order model/class (1) → properties ascending (2) → option (3) has
  no cycle with `masters.py` (manufacturer → model → class → type) or `equipment.py` (node
  → unit → model → class): `properties.py` never locks a class after a model (it reads the
  model's class plainly; `class_id` is fixed, `update_equipment_model` lines 527–531), and
  no other module locks property rows. The FK reasoning holds for InnoDB: an insert into
  `model_property_values` takes a shared lock on the referenced `property_definitions` row,
  so it waits while the edit holds it `FOR UPDATE`; a locking read sees the latest committed
  rows under REPEATABLE READ. `LOCK IN SHARE MODE` is MariaDB's syntax.
- **Schema (§ 4.1).** MariaDB enforces CHECK constraints (since 10.2.1); `(a IS NOT NULL) +
  (b IS NOT NULL) … = 1` is integer arithmetic on booleans and is valid; a CHECK cannot read
  another table, as the brief says. The composite FK `(option_id, property_id)` →
  `property_options (id, property_id)` follows `fk_equipment_models_type`
  (`local_db.py` lines 195–196); with `option_id` NULL the FK is not checked (MATCH SIMPLE),
  so non-choice rows pass. `uq_property_options_id_property` is the referenced index.
  `DECIMAL(16,4)` matches the ±10¹² bound. v26 touches no existing row: no
  `_PRECONDITIONS` entry needed, as v22 and v24.
- **Seed.** `INSERT IGNORE` keyed on the UNIQUE name, `created_by 'migration-v26'`, as v20's
  failure-code seed (`local_db.py` line 541). The table has 31 rows, as § 8.3 counts.
  Insulation classes A, B, E, F, H (IEC 60034-1), IP codes (IEC 60529) and IM mounting codes
  (IEC 60034-7) are cited correctly.
- **Standards.** ISO 14224:2016 Annex A is the equipment-class-specific data (the tables of
  attributes per class, with design values); the brief's use of it is right apart from
  BR1-02. IEC 61360 is the data-element dictionary model ECLASS builds on; the departure (no
  external property codes) is stated.
- **Plan.MD departures.** § 1 *Not in v1* "Per-class custom fields" and § 4.1 "No
  class-specific custom fields in v1" are both named and replaced (§ 11). The rotables
  paragraph (§ 4.1) wants nameplate data (kW, rpm, frame, mounting, make) as attributes to
  find interchangeable spares: the seed's *Frame size*, *Mounting*, *Power*, *Speed* serve it.
- **Layer placement.** Rules in `properties_core.py` (pure), routes and SQL in
  `properties.py`, the card's view built in the core and rendered by Vue; the detail reads
  through one helper. `format_value`'s `format(value.normalize(), "f")` gives "100" for
  `Decimal("100.0000")`, as stated.
- **References checked** against the facts file and the code: `_detail` line 266,
  `app.py` line 173, `ApiError` line 32, `conftest.py` lines 139–146, `db_down` line 42,
  `test_rbac.py` line 198, `part_quantity` line 885, `_include_inactive` line 108,
  `expectDialogFits` in `dialogs.js`, the *Parts* card in `EquipmentDetailView.vue`.
- **Manual checks.** Every check is a browser check (§ 8.5 "none" is right); the two
  **important** ones are the ones that matter (the end-to-end flow, the formatted value).
- **UX.** One job per dialog; the class dialog's search box answers the 30-row list on a
  phone; yes/no as three buttons avoids a half-state; no irreversible action (nothing is
  deleted, unticking keeps values); the card hides itself when the class has no property;
  `inputmode="decimal"` for numbers. The flow finding is BR1-04.
