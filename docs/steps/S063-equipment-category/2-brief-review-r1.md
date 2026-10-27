```
Step: S063 — Equipment category above the class
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 27-10-2026
```

Reviewed against: c9142b4 (no uncommitted step code; the working tree's changes are workflow files and the R02 roadmap)

# S063 — Brief review, round 1

**Verdict: no `blocker` or `major` finding is open.** Nine `minor` findings and five nits. The design (a category table, one nullable `category_id` on the class, the filter through `NODE_JOINS`) fits the code as it stands. The lock order of § 5.3 is sound. Two rules in § 5.2 and the class dialog need tightening before the coder starts, and three standards claims need a fix of wording. Facts file read: `scratch/brief-facts-S063.md`.

## Findings

### BR1-01 — minor — § 5.2: an unknown category on an inactive class answers 500

**Problem.** The rule reads the category only when the save *ends* with the class active. A `POST` with `active: 0` and `category_id: 999`, or a `PUT` on an inactive class with `category_id: 999`, skips the check and hits the foreign key. `api_common._integrity_error` re-raises every error but 1062 (duplicate), so the answer is the plain 500 "Something went wrong — try again".

**Why it matters.** A 500 from a request the API accepts by its own rules is a fault, and the brief's own rule produces it. The rule is also hard to state: three conditions, and the exception "an inactive class may stay in an inactive category" exists only to serve the deactivation rule of § 5.1.

**Options.**
- (a) **Recommended.** Lock and check the category (exists → 400 "Unknown category", active → 409 "The category is inactive") whenever a save sets a non-null `category_id` that differs from the stored one, and on a reactivation that keeps a category. An inactive class keeps an inactive category (so § 5.1's deactivation still works), but nobody can *move* a class into an inactive or unknown category. One sentence, no 500.
- (b) Keep the rule and map foreign-key error 1452 to a 400 in `_integrity_error`. New error handling for one case; rejected.

### BR1-02 — minor — § 5.3 / § 3: the class create needs a transaction for its category lock

**Problem.** `create_equipment_class` (masters.py 329–335) runs on the pooled autocommit connection: `clean_body`, `insert_row`, `fetch_one`, no `transaction()`. A `SELECT … FOR UPDATE` on that connection releases its lock when the statement ends, so step (1) of "Class create" in § 5.3 would lock nothing.

**Why it matters.** The deactivation rule of § 5.1 relies on the class write holding the category lock until it commits ("Why the count is safe"). Without the transaction, a deactivation can pass its count while a class create with that category commits a moment later.

**Fix.** Say in § 3 (masters.py) that the create route gains `with transaction(conn), conn.cursor() as cur:` around the lock and the insert, on the shape of `create_equipment_model` (masters.py 512–524), and that the re-read after the insert happens outside it as there.

### BR1-03 — minor — § 5.1, § 8.2: "beside the Active toggle" is not where the dialog shows it

**Problem.** The brief says the deactivation refusal shows "beside the Active toggle". The panels render `fieldError(name)` only for fields in the form; `useFormModal.js` (lines 51–53) shows a refusal whose field is *not* in the form at the top of the dialog (`modalError`). `active` is not in the form, so the class's own "Deactivate this class's models first" shows at the top of the dialog today, and the category's refusal would too.

**Why it matters.** The coder could build a new message slot by the toggle to match the brief, and the e2e assertion would look in the wrong place.

**Fix.** Write "at the top of the dialog, as a class's 'Deactivate this class's models first' shows today (field `active`, `modalError`)" in § 5.1, and the same in § 8.4's first check if it asserts the refusal.

### BR1-04 — minor — § 1.3, § 3: the class dialog's Category select has no rules

**Problem.** The brief says the dialog gets "a *Category* select, with *No category* first" and nothing more. Three things the coder would decide alone:
- which categories it lists: active ones only (the `ModelsPanel.vue` pattern for classes and types, lines 63–67) hides the current category of a class whose category was deactivated (allowed by § 5.1 when the class is inactive). The select then shows *No category*, and a Save of the name alone would clear the category;
- what *No category* sends: `v-model` on a select gives `""`, and `_parse_optional_id` refuses `""` with 400 "Category must be a record id". `ModelsPanel.vue` solves it with `toBody` (lines 83–86, `"" → null`);
- `fromRecord` must carry `category_id`, else every edit of an existing class sends the blank's value.

**Why it matters.** A silent clear of a category on an unrelated edit, or a 400 the user cannot read, on the one screen the mapping job uses.

**Fix.** State: the select lists the active categories by name, plus the class's current category when inactive, marked "(inactive)" (the equipment list's rule); `toBody` sends `null` for `""`; `fromRecord` carries `category_id`. Follow `ModelsPanel.vue` for all three.

### BR1-05 — minor — § 5.4: a category of part-level classes shows nothing at the default level

**Problem.** The equipment list opens at the *Machines* level. *Drives and transmission* (motors, gearboxes) and most *Power tools* are component-units or components, so the engineer who picks that category sees "No equipment matches these filters." until they also change *Level*. The brief states the rule ("at the default level this is the machine's class") but not what the user sees.

**Why it matters.** The category filter is the step's main screen change, and this is the case the user asked about (power tools). The class filter behaves the same today, so this is a known cost, but it is a judgement call.

**Options.**
- (a) **Recommended.** Keep the rule (one behaviour for class and category), and say in § 5.4 that the level stays, as for the class filter, so the coder does not invent a widening.
- (b) Widen the level to *All levels* on the first category pick, as the first search (`applySearch`) and the first property filter (S062 D11) do. More consistent with the two newest filters, but the class filter would then differ from the category filter.

### BR1-06 — minor — § 2: ISO 14224's "equipment category" is not a taxonomy level

**Problem.** "ISO 14224 puts the category one level above the class." In the standard's taxonomy (Figure 3, nine levels) the level above *equipment unit* (level 6, the class) is *section/system* (level 5): where the equipment sits in the plant, not what kind it is. The *equipment category* is the grouping of equipment classes used in Annex A's tables (Table A.4, "Equipment class – level 6", has an *equipment category* column: rotating, mechanical, electrical, safety and control, and the oil-and-gas-specific ones). Fact by my reading of ISO 14224:2016; the brief's "to verify" stands.

**Why it matters.** The project owner learns the standard from these sections (settings: *Standards*). "One level above the class" would be read as a taxonomy level, and the plant's units already fill level 5.

**Fix.** "ISO 14224 groups its equipment classes into *equipment categories* in Annex A (Table A.4). The category is a grouping of classes, not a level of the taxonomy; the level above the class in the taxonomy is the plant section, which Yantra's units are."

### BR1-07 — minor — § 2: the Factories Act 1948 has been replaced; name the law in force

**Problem.** The brief cites the Factories Act 1948, ss. 28–29. **Assumption, to confirm by the user:** the Occupational Safety, Health and Working Conditions Code, 2020 came into force on 21-11-2025 and repeals the Factories Act 1948; the hoist, lift and lifting-machine examinations now live in the rules under the Code (central and state), which carry the same intervals (6 months for hoists and lifts, 12 months for lifting machines, chains, ropes and tackle). The intervals themselves are right.

**Why it matters.** Plan.MD § 4.3 (*Certification plans*) also says "the Factories Act examinations"; the compliance register is for an inspector, who will name the Code.

**Fix.** "The OSH Code 2020 and its rules (formerly the Factories Act 1948, ss. 28–29): …", and mark the clause of the rules *to verify*. If the user confirms the Code is not yet in force in Tamil Nadu, keep the Act.

### BR1-08 — minor — § 4.2 (Q2): two statutory and audit groups of the plant have no category

**Problem.** The list is built on the plant's statutory checks ("lifting, material handling, vehicles"), but two groups the plant already names are hidden or missing:
- **Pressure vessels.** `docs/Plant-Facts.md` line 126: "pressure vessels examined periodically by a government official against a fee" (the Factories Act's *pressure plant*, s. 31, now the Code's rules). The list puts "air receivers" inside *Utilities*, so the one statutory plan for pressure plant has no category to apply to.
- **Measuring instruments.** Plan.MD § 4.3 *Calibration*: "Instruments are equipment of class *measuring instrument*", ISO 9001 § 7.1.5. None of the twelve names fits them; *Safety and fire* is the nearest and is wrong.

**Why it matters.** The main later use (§ 2) is one plan per category. A category the engineer has to add by hand on day one is the blank screen D4 wants to avoid. This is the user's call (Q2), so it is not a nit.

**Options.**
- (a) **Recommended.** Add *Pressure vessels* (compressor air receivers, boilers, autoclaves) and *Measuring instruments* (verniers, multimeters, weigh scales, moisture analysers); keep *Utilities* for compressors, pumps, blowers, water treatment.
- (b) Keep twelve names; the engineer adds the two in Masters.

### BR1-09 — minor — § 8: the tests share a database with the twelve seed rows

**Problem.** `conftest._clean_tables` deletes from a seeded table only the rows whose `created_by` is not a seed creator, once per session, and the worker's database is kept between runs. So: a test category named like a seed (*Utilities*) is a 409 on its first run; a test that renames or deactivates a seed row changes it for every later test and every later run of that worker. The brief's § 8.2 ("rename", "deactivate … reactivate") does not say which rows.

**Why it matters.** A flaky suite, found a day later, is the usual cost.

**Fix.** Add to § 8.2: tests create their own categories with names that cannot clash (the file's own prefix), and never rename, deactivate or map a class to a seed row; the seed is asserted only in `test_migration_v35.py` (its own database).

## Nits

- **BR1-10** (nit) § 4.1: the `FOREIGN KEY IF NOT EXISTS` form is MariaDB's documented one and the coder verifies it, as the brief says. Name the fallback now, so the coder does not stop: `DROP FOREIGN KEY IF EXISTS fk_equipment_classes_category` then `ADD CONSTRAINT … FOREIGN KEY`, the shape v34 uses for its CHECKs. The re-run test compares `_schema()` (`test_migration_v20.py` 65–79: REFERENTIAL_CONSTRAINTS and STATISTICS), so a doubled key or index fails it.
- **BR1-11** (nit) § 5.2, § 5.3: on a reactivation, pass `"active"` as the field to `_lock_active_parent`, the model's convention (masters.py 550–553): the refusal then belongs to what the user touched. § 5.2 says `category_id` for both cases.
- **BR1-12** (nit) § 3: three docstrings to update with the code: `_lock_active_parent` ("the manufacturer or class a model is created … under"), `_list_filters` (the filter list), and the `_SEEDED_TABLES` comment in `conftest.py` (the seeds by migration).
- **BR1-13** (nit) § 5.1, scope B: "Move its classes to another category first (N active)" names the action but not what happened. "3 active classes are in this category. Move them to another category first."
- **BR1-14** (nit) § 2: ISO 55001 § 7.5 is *Information requirements* (§ 7.6 is *Documented information*). The brief's point, "know what assets you have", is 7.5's; fix the title in brackets. Plan.MD § 4.1 cites 7.5 the same way.

## Checked and found consistent

- **Migration v35.** No migration after v20 adds a foreign key to an existing table (v21–v34: columns, CHECKs, indexes, new tables). `ADD COLUMN IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS` and `INSERT IGNORE` on a unique name are the v31 and v34 patterns. No precondition is right: a new table and a nullable column meet no production row. Rollback holds: `list_equipment_classes` is `SELECT *` and the screens ignore an extra key. `test_migration_v34.py` slices `range(20, 35)` (lines 19–21), so v35 leaves it untouched.
- **Locks, § 5.3.** masters.py's order is manufacturer → model → class → type; equipment.py's is model (4) → class (5). The category comes after the class in a class update, alone in a category update, alone in a class create. No model, equipment or type write takes the category, so no cycle. The REPEATABLE READ argument holds: a `FOR UPDATE` read creates no read view, so the category update's count, its first plain read, starts its snapshot after the lock; a class write's `_lock_active_parent` is a locking read and sees the committed `active = 0`.
- **Filter, § 5.4.** `NODE_JOINS` joins `equipment_classes c` (equipment.py 149–158); `_list_filters` is the one place both the list and `/asset-list` read (lines 536–560, 577, 747); `int_arg(name, None, minimum=1)` gives exactly "category_id must be a whole number at least 1". The class and type selects' rules the brief copies are in `EquipmentView.vue` 88–105 and 123; `FILTER_KEYS` and `filtersLabel` in `assetList.js`.
- **Permissions, § 5.5.** `equipment:edit` is in `SITE_SCOPED`; the class routes use `require_perm`, so a category at no site follows them. `masters:read` is `('*',)`. No new key, so `test_role_matrix` is untouched.
- **Tests.** `_SEEDED_TABLES` is keyed by creator, and `_clean_tables` runs with `FOREIGN_KEY_CHECKS = 0`, as § 3 says. `db_down` is a shared fixture. The masters e2e loop (`masters.spec.js` 120–141) takes a new entry with `message: "Name is required"`, as § 8.4 says.
- **Store and panel.** `TradesPanel.vue` and `useMasterForm` are the right pattern (name and Active only). `MastersView.vue` sections are a plain list; a section before `classes` is a one-line insert.
- **Plan.** Plan.MD § 2 *Not in v1* rules out hand-picked equipment groups; a category groups classes, so D1 and the out-of-scope line are consistent with it. § 4.1 says a class is a kind at any level, which § 4.2's *Drives and transmission* follows.
- **Track and checks.** Full track is right (a migration, locking). § 8.4's four checks are browser-judgeable and the two important ones are marked; § 8.5 none is right; no `@device` tag is right (no layout check).

## Feedback

- hindrance: a Bash call chaining several `grep`s with `&&` stopped at the first empty result, so one batch had to be re-run with `;` (1 run, 2 min).
- idea: the facts file could list, for each masters section label the brief names ("Equip Class"), where the e2e specs use it; I grepped `masters.spec.js` and `screens.spec.js` by hand for the section loop.
