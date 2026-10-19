```
Step: S016 — Failure codes
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 18-10-2026
```

Reviewed against: a2190f3 + uncommitted S022 (`tooling/deps/`, docs; none of this brief's files)

# S016 — Brief review, round 1

**Verdict: no `blocker` or `major` finding is open.** The design (three tables, modes
scoped by one class or General, API-checked mode labels, a new global
`failure_codes:edit` key, seeds from ISO 14224 Annex B) holds against Plan.MD, the
masters pattern in `backend/masters.py` and the migration conventions in
`backend/local_db.py`. The findings below are seed-text corrections against ISO 14224
Table B.5, a gap in the general mode list that matters for defect tickets, a few rules the
coder would otherwise decide alone (tests, index names, ordering), and what S017/S018
should find settled here. Full track; up to two more rounds if needed.

Where I checked the standard: I compared § 4.3 with ISO 14224:2016 Annex B from memory of
the tables (B.3 failure causes, B.5 maintenance activity, the per-class failure-mode tables
B.6 onward). I am confident of the codes and names; the table numbering range "B.6–B.15"
I can only call plausible. Treat "as far as I can tell" literally.

## Findings

### BR1-01 · minor · Three Table B.5 descriptions do not say what ISO says

**Problem.** § 4.3 *Maintenance actions*: the codes 1–12 and the twelve names match
ISO 14224:2016 Table B.5. Three descriptions do not:

| Code | Brief | ISO 14224 Table B.5 (paraphrased) |
|---|---|---|
| `5` Refit | "Reassemble or refit after removal" | A **minor repair or servicing to bring the item back to an acceptable appearance, inside and out**: re-tightening, touch-up, cleaning up a seat — small work short of a repair. Nothing about reassembly after removal. |
| `6` Check | "Find the cause; no other action" | The cause is investigated but **no maintenance action is done, or it is deferred**; the function may have come back by a **simple action such as a restart or reset**. |
| `9` Inspection | "Inspect, with minor adjustments if needed" | A **careful scrutiny of the item, with or without dismantling, normally by the senses** (look, listen, feel). Adjustments and calibrations belong to `7` Service, not to Inspection. |

`1` Replace is close but ISO says "a new or refurbished item **of the same type and
make**" — that is what separates it from `3` Modify (a different type, make, material or
design). Worth the five words.

**Why it matters.** The description is the help text a technician reads when picking the
action (S018). "Check" is the action S018 will want for "reset and it worked" and for the
frivolous close; if the help text says only "find the cause", nobody picks it. "Refit" as
written would be read as "put back together", which is part of every repair, and the code
loses its meaning. The brief itself asks for exactly this check (§ 4.3, last paragraph).

**In plain terms, what Table B.5 is for.** ISO 14224 wants every maintenance record to
say *what kind of work* was done, with one word from a short fixed list, so that later you
can count how often a thing was replaced versus repaired versus merely reset. The twelve
activities are deliberately coarse; the distinctions that matter are same-type replacement
(Replace) vs. a design change (Modify), and "worked on" (Repair/Refit/Adjust) vs. "looked
at" (Check/Inspection/Test).

**Options.** (a) Correct the three descriptions (and Replace) in § 4.3 to the ISO sense,
in plain words — **recommended**; (b) keep the brief's wording as local meanings — not
recommended, the codes are ISO's numbers and should carry ISO's meanings.

Suggested text: `5` "Small repair or tidy-up short of a full repair: re-tighten, touch up,
clean a seat"; `6` "Looked for the cause; nothing repaired, or the fix was a restart or
reset, or the work is deferred"; `9` "Careful look at the item, with or without opening
it, by eye, ear and hand".

### BR1-02 · minor · The general mode list has no code for the typical *defect* — loose, dirty, minor

**Problem.** § 4.3 seeds 13 general modes. ISO's `SER` *Minor in-service problems*
(loose items, discolouration, dirt, small abnormalities) is left out, and "loose" has been
folded into `STD` *Structural deficiency*, which in ISO is material damage: cracks, wear,
fracture, corrosion.

**Why it matters.** Plan.MD § 4.2 (decided 18-10-2026) makes a *defect* ticket the TPM
abnormality tag: its own examples are "a leak, a noise, a loose guard, a worn scraper".
Leak, noise and worn have a code; the loose guard, a dirty panel (Plant-Facts § 4: press
PLC panels need frequent cleaning), a missing cover, a discoloured cable do not — they
would land in `OTH` or be mis-coded `STD`. Chronic-problem counting (Plan.MD § 4.6, TPM
focused improvement) then loses exactly the early signs TPM wants counted. The operator's
list grows from 13 to 14 rows, which is still short.

**Options.** (a) Add `SER` — label "Loose, dirty or minor problem", description "Minor
in-service problems" — and narrow `STD` to "Broken, cracked or worn part" —
**recommended**; (b) keep 13 and let engineers add it in the screen (the brief's general
rule for additions) — acceptable, but this one is ISO's own code and the seed is the
place for it. The migration test's count becomes 14 if (a).

### BR1-03 · minor · Settle now what S017 must do with a mode's class — it cannot be a foreign key

**Problem.** Decision 1 says S017/S018's ticket columns "get a plain foreign key that
also guarantees the kind". True for the kind. The brief's § 5.4 lists "code frozen once in
use" for S017/S018 but says nothing about the other rule S017 will need from this table:
**the ticket's mode must be General or of the equipment's class**. S004/S012 made such
fits database rules with a composite FK `(type_id, class_id) → equipment_types (id,
class_id)`. That trick does not work here: a General mode has `class_id NULL`, and a
composite FK `(mode_id, equipment_class_id) → failure_modes (id, class_id)` can never match
a NULL on the referenced side. S017 would try the S004 pattern, find it impossible, and
decide alone.

Assumption 5 (§ 9) also needs one more word. A ticket "points at the component" (Plan.MD
§ 4.2), but the symptom list is the **press's**, not the relay board's: the class that
scopes the picker is the class of the ticket's **equipment** (the level-6 ancestor), whatever
node the ticket is on.

**Why it matters.** S017 is the first consumer. Two sentences here save a design detour
there, and the user approves the rule once.

**Options.** (a) Add to § 5.4 (and decision 1's reason): "S017 checks in the API, on the
locked ticket, that the mode is General or of the class of the ticket's equipment (the
level-6 node); not a composite FK, because General modes have `class_id NULL`" and sharpen
assumption 5 to "the class of the ticket's equipment node, even when the ticket is on a
component" — **recommended**; (b) leave it to S017 — the brief then under-delivers on what
the orchestrator asked it to settle.

### BR1-04 · minor · `test_rbac.py::test_role_matrix` breaks; the brief should name it

**Problem.** § 3 *Tests* says `test_rbac.py — the new key`. The existing
`TestComputePermissions.test_role_matrix` asserts the **exact** permission set of every
role (`backend/tests/test_rbac.py` lines 127–144). Adding `failure_codes:edit` to
`("maint_engineer", "it_admin")` changes the sets of `maint_engineer`, `maint_manager` and
`it_admin`; the test fails until those three rows gain the key.

**Why it matters.** "Existing tests the change will break" is a brief's job to list; the
coder should not discover it from a red run, and the fix must be the three rows, not a
loosened assertion. `test_site_checks_api.py:98` and `test_access_core.py:38` compare
against `PERMISSIONS` dynamically and are fine. The frontend `navigation.test.js` lists are
inputs, not derived from the backend; fine too.

**Options.** (a) Name the test and the three rows in § 3 or § 8 — **recommended**.

### BR1-05 · minor · Test isolation with seeded tables is not settled

**Problem.** Four things interact and the brief decides none of them:

1. `conftest._TABLES` empties every master table once per session. The three new tables
   are **not** listed (correctly — listing them would delete the seeds), so rows created
   by `test_failure_codes_api.py` **survive to the next session**. `Uniq` restarts at 0
   each session, so a second `run-backend-tests.bat` would hit 409 on the same codes.
2. `Uniq` has no code generator that fits `^[A-Z0-9][A-Z0-9.]{0,7}$`; the tests need one
   (e.g. `failure_code() -> f"T{n:04d}"`).
3. § 8 asserts seed counts "13 / 15 / 12" — wrong as soon as an API test has created a
   row, unless the count filters on the seeds' `created_by`.
4. The re-run test edits a seed row's label and active flag; unless it restores them in
   `finally` (as `test_migration_v10.py` restores the setting), the manual check "Abnormal
   noise is refused" and any API test relying on a seed label are affected.

**Why it matters.** Each is a decision the coder would take alone, and (1) makes the
suite non-repeatable.

**Options.** (a) In § 8: the session clean-up deletes **non-seed** rows of the three
tables (`DELETE … WHERE created_by <> '<seed actor>'`); `Uniq.failure_code()`; seed
assertions count `created_by = '<seed actor>'`; the re-run test restores the row —
**recommended**; (b) add the tables to `_TABLES` and re-run `init_db` after the wipe —
heavier, and `ensure_schema`'s `_schema_ready` flag means `init_db` must be called
directly.

### BR1-06 · minor · Name every UNIQUE index; the 409 mapping depends on the names

**Problem.** § 4.1 names `uq_failure_modes_code` and leaves the other four as "UNIQUE".
`api_common._integrity_error` turns a duplicate into `409 {error, field}` only through
`UNIQUE_KEY_ERRORS[index_name]`; an unnamed index gives MariaDB's generated name and the
generic "Conflicts with an existing record". § 6 promises "Duplicate code → 409 `code`;
duplicate label → 409 `label`".

**Options.** (a) Name them in § 4.1 — `uq_failure_causes_code`,
`uq_failure_causes_label`, `uq_maintenance_actions_code`, `uq_maintenance_actions_label` —
and add a line to § 3 *masters.py*: "register the five in `UNIQUE_KEY_ERRORS` with plain
messages (field `code` / `label`)" — **recommended**.

### BR1-07 · minor · Order causes by group, then code — or local causes fall outside their group

**Problem.** § 6 orders `/failure-causes` "by code (`1.1` … `5.6`)". That reads grouped
only because ISO's codes start with the group number. Decision 4's whole point is local
causes under a group ("oil contamination" under *operation*); a local code is either
alphabetic (`OILC`, sorts after every digit) or `3.5`-style (then `3.10` sorts between
`3.1` and `3.2`). Either way the list stops reading as five groups.

**Options.** (a) `ORDER BY cause_group, code` — an ENUM orders by its declared position
(design, fabrication, operation, management, misc), so this is one clause and no
`FIELD()` — **recommended**; the Causes panel groups by the same field. (b) keep code
order — accepted only if the panel groups visually anyway.

### BR1-08 · nit · "Unknown class (400 or 404 on the existing pattern)" — it is 400

§ 8 leaves the status open. The existing pattern is fixed: `_lock_active_parent` raises
`400 {"error": "Unknown class", "field": "class_id"}` (`masters.py` line 436;
`test_unknown_class_on_create_is_400`). Say 400.

### BR1-09 · nit · Seed `created_by`: `migration-v11`, not `system`

Migration v8 stamped the rows it created `created_by = 'migration-v8'` and the code finds
them by it. `system` says less (which release? which step?) and could clash with a
future real actor name. Use `migration-v11`; BR1-05's filters then read naturally.

### BR1-10 · nit · The code regex admits `3.` and `1..2`

`^[A-Z0-9][A-Z0-9.]{0,7}$` accepts a trailing dot and runs of dots. Harmless, but a typo
`3.` would be a distinct code from `3.4`. If cheap: `^[A-Z0-9]+(\.[A-Z0-9]+)*$` plus a
length check, or state that the simple form is accepted on purpose.

### BR1-11 · nit · Two words on the mode-label check

§ 5.1: say the comparison is a plain `=` on the `label` column, so the column's
case-insensitive collation applies (as the DB-unique labels do) — otherwise a coder may
write `LOWER()` and defeat the index. And give the one workflow the rule forces: a class
mode cannot later be made General (class is fixed, and the General label would collide
with it, inactive rows included) — the path is "rename or deactivate the class mode, then
create the General one". One sentence in § 5.2 stops a support question.

### BR1-12 · nit · § 5.4: say whether `cause_group` stays editable once tickets reference the cause

§ 5.3 says the group "may be changed later (nothing references a cause yet)". Once S018's
tickets reference it, a group change re-rolls history in the ISO reports. I would keep it
**editable**: it is a reclassification, and applying it to history consistently is what
you want (the same cause should never roll up two ways). Say so in § 5.4 next to "code
frozen", so S018 does not freeze it by analogy.

### BR1-13 · nit · Make the leakage blur explicit; point `NHP` at ISO `INL`

ISO splits external leakage into `ELU` (utility medium: lube/hydraulic oil, cooling water,
air) and `ELP` (process medium). The brief seeds `ELU` only, labelled "Leaking (oil, water,
air)" — right for the operator, but the description should say "External leakage (ISO
`ELU`/`ELP`; one entry here)" so a later reader knows it was deliberate. The press mode
`NHP` *Not holding pressure* is ISO's `INL` *Internal leakage* in a press; its description
in § 4.4 could say so, which is the kind of ISO-learning the project wants.

### BR1-14 · nit · Decision 8's rejected alternative is weaker than stated

The brief rejects a generated column `IFNULL(class_id, 0)` with a unique index as
"clever". It is also **insufficient**: it would stop two General "Noise" rows and two
press "Noise" rows, but not a General "Noise" beside a press "Noise" — the cross-scope rule
is not expressible as a unique index at all. Saying that makes the API check the only
option rather than the simpler one, which is a stronger reason.

### BR1-15 · nit · Standards: one line for ISO 55001

§ 2 covers ISO 14224, EN 13306, TPM and SMRP well and explains them. ISO 55001 § 7.5
(determine the asset information you need and keep it) and § 9.1 (performance evaluation
needs that data) are the "why code at all" standard; one line ties the lists to the
asset-management system the plant is building. ISO 27001 is not relevant here beyond the
least-privilege reason already given for the separate key (A.8.2), which decision 5
covers implicitly.

## Checked and found consistent

- **ISO 14224 Table B.3** (failure causes): the five groups, the numbering `1.1`–`5.6`,
  the names, and the omissions (`x.0 General`, `5.2 Common cause`) match the 2016 table as
  far as I can tell; "Caused by another failure" for `5.4 Other unit/cascading failure` is
  a fair plain-words rendering.
- **ISO 14224 failure-mode codes** `BRD FTS STP UST ELU NOI VIB OHE LOO ERO PDE STD OTH`
  and their ISO names are the standard's; `PDE` (parameter deviation) rather than `AIR`
  (abnormal instrument reading) is the right choice for "reading out of range".
  "Tables B.6–B.15, per class" is plausible; I cannot vouch for the exact numbers.
- **Table B.5** codes 1–12 and names: correct (descriptions: BR1-01).
- **Plan.MD**: § 3 (engineers own codes), § 4.2 *Codes* (decided 15-10-2026), the
  class-scoped modes brought forward for presses (16-10-2026), open question 5 (mechanism
  out). The `codes` table in § 5 is superseded and the brief says it will update the doc.
  `Maintenance-Philosophy.md` § 6 matches.
- **Masters pattern**: `_lock_active_parent` (exists 400 / inactive 409, field = `class_id`
  on create, `active` on reactivation), "class fixed after create" with the `400 Class
  cannot be changed`, plain read of the fixed id before locking the row, `_int_filter`
  for `class_id`, `_include_inactive`, `_list_response`, `insert_row`/`update_row` — the
  brief describes `masters.py` as it is. A General mode needs no parent lock; the brief
  implies it.
- **Migration conventions**: `(11, description, [sql])`, `CREATE TABLE IF NOT EXISTS`,
  `INSERT IGNORE` keyed on the unique code, audit columns, InnoDB utf8mb4 (server default
  collation is case-insensitive, which the existing `uq_manufacturers_name` already relies
  on), ENUM for a fixed small set (as `people.employment`). `cause_group` ENUM mirrored by
  `masters_core.CAUSE_GROUPS` follows the `EMPLOYMENT` precedent.
- **Three tables (decision 1)**: sound. A `cause_id` column can only hold a cause; the
  S004/S012 "database rule" approach. The class fit for modes is the one rule the FK
  cannot carry (BR1-03), and that is a property of NULL, not of the three-table choice.
- **API-checked mode labels (decision 8)**: sound; the race is cosmetic (codes differ).
  The test matrix in § 8 (same class 409; class vs General 409 both ways; two classes
  allowed) is the right set.
- **`failure_codes:edit`** global (not `SITE_SCOPED`) with `("maint_engineer", "it_admin")`:
  consistent with `people:edit` and with how `has_perm` unions site roles; Plan.MD § 3's
  "engineer owns codes". IT admin's inclusion is the user's call (§ 9 Q3) and has the
  `equipment:edit` precedent for classes.
- **Frontend**: `MastersView` sections take `perm: "masters:read"`; `useMasterForm`,
  `FormModal`, `ActiveToggle` exist and the types panel is a direct template (class fixed,
  shown as text on edit). `masters.js` `ensure*/resetMasters` pattern as described;
  `masters.test.js` covers sites/units only, so the hedge in § 3 is right.
- **Track**: full is correct (migration, new permission key).
- **Manual checks**: the three important ones are the right three (engineer flow with
  press modes, operator read-only, phone); the two plain ones are plain.
- **Out of scope** list is honest: nothing listed is needed before S017.
