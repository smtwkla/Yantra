```
Step: S037 — Meters master
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 24-10-2026
```

Reviewed against: e451c33 + uncommitted S035, S036, S041 (none touches a file this brief names)

# S037 — Brief review, round 2

**Verdict: no blocker or major finding is open.** Four minor findings and seven
nits. Round 2 re-read only what U3 changed: § 1.1, § 1.3, § 1.4, Out of scope,
§ 2, § 3 (`METER_KINDS`, Docs), § 4, § 5.1, § 7 (decisions 6–8), § 8 and § 9,
plus the code those changes now rely on. Every round-1 finding marked
`Accepted` is in the brief's text (checked: BR1-01 wording, BR1-02 `{items,
total}`, BR1-03 seed rule, BR1-04 *Active*, BR1-05–BR1-12). § 6 was not on the
list of changed sections, but the U3 change reaches it (BR2-03).

The four kinds hold together: the CHECK of § 4 passes every seed row and
refuses every wrong shape; S038 and S039 read the same fields. The minors are
places where the two new kinds leave a decision to the coder: where the
kind-dependent rules run, what the panel sends for the hidden fields, the API
shape, and three messages. Facts file `scratch/brief-facts-S037.md` read; it
lists `yes_no`, `expected_answer` and `_parse_decimals` as not found, which is
right for new names.

Full track, round 2 of up to 3.

## Minor

### BR2-01 — minor — § 5.1 and § 3: where the kind-dependent rules run is not said

**Problem.** Six rows of § 5.1 depend on `kind` and on another field together
("unit missing … for a kind other than Yes / No", "expected answer missing …
for a Yes / No type", "decimals other than 0 for a Yes / No type"), and the
PUT row says they "apply to the row after the write (body merged over the
stored row)". The brief names the `validate_trade` pattern for
`validate_meter_type`. That pattern is `_validate(data, fields, creating)`
(`masters_core.py:280`): one parser per field, no field sees another, and no
stored row. Today a rule that needs the stored row lives in the route, as
`clean.get("code", site["code"]) != site["code"]` (`masters.py:207`, `:277`,
`:333`). The brief does not say which function merges and checks.

**Why it matters.** A coder who follows the two patterns as written puts the
kind rules in the route (a business rule in the shell, CLAUDE-COMMON *Pure
core, thin shell*), or invents a shape on his own. § 8 asks
`test_masters_core.py` for "a `PUT` from gauge to Yes / No without the expected
answer", which only a core function that sees the stored row can test.

**Options.**
- (a) **Recommended.** `validate_meter_type(data, creating, stored=None)` in
  `masters_core.py`: first `_validate` on a field table where `unit`,
  `expected_answer` and `decimals` are all "not required on create" (the kind
  decides), then the kind rules of § 5.1 on the merged row `{**defaults,
  **stored, **clean}` (`defaults`: `unit None`, `expected_answer None`,
  `decimals 0`), each error with its field. The route passes `_lock_row`'s row
  as `stored` on PUT, nothing on POST. Both passes pure; one function to test.
- (b) A second pure function, `meter_type_shape_errors(row)`, that the route
  calls after merging. Two names for one validation; the route grows a merge
  it does nowhere else.

### BR2-02 — minor — § 1.4 and § 5.1: what the panel sends for the fields it hides

**Problem.** For *Yes / No* the panel hides *Unit* and *Decimals*; for the
other kinds it has no *Expected answer*. With the merge rule of § 5.1, a PUT
that changes a gauge (°C, 1 decimal) to *Yes / No* and omits `unit` and
`decimals` keeps "°C" and 1 in the merged row, so it is refused with "A Yes /
No meter has no unit". The same the other way: a *Yes / No* type changed to a
gauge keeps its expected answer and is refused. The brief does not say what
the panel sends, and the rows "`unit` sent (not empty)" and "`expected_answer`
sent for another kind" do not say what "sent" means for `null` and `""`.

**Why it matters.** The user sees a refusal about a field that is not on the
screen, and the coder decides alone whether the client or the server clears
it.

**Options.**
- (a) **Recommended.** The panel always sends the five fields: for *Yes / No*
  `unit: null` and `decimals: 0`, for the other kinds `expected_answer: null`.
  § 5.1 then says: "sent" means not `null` and not empty; `null` or `""` for
  `unit` or `expected_answer` store NULL. One line in § 1.4, one in § 5.1; the
  rule table stays as it is.
- (b) The server clears what the new kind lacks whenever `kind` changes. One
  call fewer for an API user, but a hidden side effect of a PUT, and the
  "sent for another kind" rows of § 5.1 lose their meaning on a PUT.

### BR2-03 — minor — § 6: the API table was not updated for U3

**Problem.** § 6 gives the GET item as `{id, name, unit, kind, decimals,
active}` and the POST body as `name, unit, kind, decimals?`. Neither has
`expected_answer`. The edit dialog needs it to pre-select the *Yes* / *No*
radio, and § 8 asserts "its row read back (U3)". `unit` may also be `null`
now.

**Why it matters.** The trades routes return `SELECT *`, so the coder who
copies them returns the field by accident; a coder who follows § 6 literally
builds the item list without it and the edit dialog cannot show the answer.

**Fix.** GET item `{id, name, unit (null for Yes / No), kind, expected_answer
(null unless Yes / No), decimals, active}`; POST body `name, kind, unit?,
expected_answer?, decimals?` with the kind rules of § 5.1; PUT "any of the
fields".

### BR2-04 — minor — § 5.1: three messages break the brief's own wording rules

**Problem.**
1. "Pick the expected answer" is the "Enter a …" style that BR1-01 (a)
   rejected for this step (accepted in the Review log). The masters' wording,
   and what `_validate` itself says for a missing field (`masters_core.py:285`),
   is "Expected answer is required".
2. "A Yes / No meter has no unit", "Only a Yes / No meter has an expected
   answer" and "A Yes / No meter has no decimals" say *meter*. § 2 fixes the
   terms: *meter type* is the catalogue entry, *meter* is S038's row on a model
   or a machine (where S038 rightly says "A Yes / No meter has no limits").
3. "Kind must be counter, gauge, amount per period or yes / no" names the
   labels where the API takes `amount` and `yes_no`. Only an API caller can
   see it (the radios cannot send a wrong value), and that caller needs the
   values. The `_parse_cause_group` shape the brief cites gives "Kind must be
   one of: counter, gauge, amount, yes_no".

**Why it matters.** Scope B: one wording for one thing across the Masters
tabs (BR1-01), and one term for one thing (§ 2). The coder copies the table
as written.

**Fix.** "Expected answer is required"; "A Yes / No meter type has no unit",
"Only a Yes / No meter type has an expected answer", "A Yes / No meter type
has no decimals"; "Kind must be one of: counter, gauge, amount, yes_no".

## Nits

- **BR2-05** (nit) § 3 Tests: "`SEED_CREATOR` made a tuple" breaks
  `test_migration_v11.py`, which imports it and binds it as one value in
  `created_by = %s` (`:40`, `:44`, `:74`, `:80`, `:84`). Take the other form:
  `_SEEDED_TABLES` becomes a dict table → creator (`"meter_types":
  "migration-v29"`), and `SEED_CREATOR` stays a string.
- **BR2-06** (nit) § 8 `test_migration_v29.py`: add one refused insert per
  branch of `chk_meter_types_yes_no` (a `yes_no` row with a unit, with
  decimals 1, without an expected answer; a `counter` row without a unit, with
  an expected answer), so the guard is shown to hold on MariaDB 11.4 rather
  than assumed. Read-through: `kind` and `decimals` are NOT NULL and the
  nullable columns are only tested with `IS NULL` / `IS NOT NULL`, so the
  expression is never UNKNOWN and no row slips through the NULL-passes rule
  of CHECK; the eight seeds take the second branch and pass.
- **BR2-07** (nit) § 1.4 table: say what a *Yes / No* row shows. *Unit* and
  *Decimals* read "—", not blank and "0"; and the expected answer shows in the
  row, e.g. the *Kind* cell "Yes / No, expects Yes": the catalogue is where an
  engineer checks which answer is the good one.
- **BR2-08** (nit) § 1.4: say the Add dialog's starting kind. The pattern
  pre-selects one (`blank()` sets `employment: "direct"`,
  `PeoplePanel.vue:173`); *Counter* is the common case. The sections-loop test
  (`masters.spec.js:115`) passes either way: it checks only "Name is required".
- **BR2-09** (nit) § 1.4 help text: four sentences under the radios are about
  six lines at phone width, read in full to find one kind. Put each kind's
  sentence under its own radio as `form-text`, and add one line under
  *Expected answer*: "The answer that means all is well." The label alone does
  not say which way.
- **BR2-10** (nit) § 3 Docs: `docs/Maintenance-Philosophy.md` § 8 (lines
  295–296) and its glossary row *Meter* (line 441, "counter or gauge") define
  two kinds; add them to the Docs list beside Plan.MD § 4.5.
- **BR2-11** (nit) scope A, § 1 first paragraph: one sentence of 45 words
  ("Meters master, meter link … S040 (U2).") Split at "as three steps:".

## Checked and found consistent

- **The CHECK against every kind** (§ 4). Counter, gauge and amount: `kind <>
  'yes_no'` true, a unit present, `expected_answer` NULL → the second branch
  is true. Yes / No: unit NULL, an answer present, `decimals = 0` → the first
  branch is true. A yes_no row with a unit, or a counter without one, is
  refused (4025). Table-level CHECKs over several columns are already in use
  (`chk_equipment_level_place`, `local_db.py:341`; `chk_ticket_parts_kind`,
  `:652`), so MariaDB 11.4 enforces the form. `INSERT IGNORE` on the unique
  name keeps the seed re-runnable, as v11's (`:524`, `:541`); no
  `_PRECONDITIONS` entry is right for a new table.
- **The seed** (§ 1.3, § 4). Eight rows: five counters, two gauges, one amount;
  every one has a unit and no expected answer, so all pass the CHECK. The
  count matches § 4 and § 8. `created_by 'migration-v29'` tells them from test
  rows; with a per-table creator (BR2-05) `_clean_tables` keeps them and the
  `uniq` rule of § 8 keeps the tests from changing them.
- **`METER_KINDS = ("counter", "gauge", "amount", "yes_no")`** is the ENUM's
  order, as `CAUSE_GROUPS` follows `failure_causes.cause_group`
  (`masters_core.py:38`).
- **The PUT that changes kind.** With BR2-01 (a) and BR2-02 (a): gauge → Yes /
  No sends `kind`, `expected_answer`, `unit: null`, `decimals: 0` and passes;
  Yes / No → counter sends `kind`, `unit`, `expected_answer: null` and passes;
  Deactivate (`{active: 0}`, what `useMasterForm` sends) leaves the merged row
  as stored and passes for every kind. Kind is editable only until S038
  freezes it (§ 1.5, S038 § 1.5 and decision 5 agree, the expected answer
  included).
- **Scope B words.** *Counter*, *Gauge*, *Amount per period*, *Yes / No*,
  *Expected answer*, radios *Yes* / *No*: plain, one term each, the same words
  S038 and S039 use. The help text's sentences are short and name an example
  each. The e2e title "a Yes / No type hides Unit and Decimals and asks for the
  expected answer" says what the user sees.
- **Decisions 6–8** fit the next steps: S039 stores a Yes / No reading as
  `value` 1 / 0 and `limit_state 'not_ok'` from the type's expected answer; S038
  gives amount and Yes / No meters no limits and freezes the expected answer.
  No Yes / No seed: S039's e2e creates its own type by this API (S039 § 8).
- **Out of scope.** ISO 4406 stays in Plan.MD § 4.5 (line 715) as a phase-4
  gauge fed by a sampling plan; nothing here closes that door. Shifts as such
  are S039's *Time taken*.
- **Standards** (§ 2). ISO 22400-2 defines produced quantity (PQ) per time
  period as an element of its KPIs: an *amount per period* is that element.
  EN 13306 defines *inspection* as examination for conformity by measuring,
  observing or testing a characteristic of an item: a Yes / No reading is the
  observing case, an attribute (go / no-go) check against the variable
  (measured) check of a gauge. Both marked "to verify", rightly. ISO 14224,
  ISO 50001 and ISO 9001 § 7.1.5 unchanged from round 1.
- **Tests the change touches.** `masters.spec.js`'s sections loop takes a new
  row without change to the loop; `test_rbac.py` unchanged (no new key);
  `test_migration_v11.py` safe with BR2-05.
- **Manual checks.** Still nothing on the device list; the Yes / No dialog is
  a browser check (`expectDialogFits`), correctly automated.
