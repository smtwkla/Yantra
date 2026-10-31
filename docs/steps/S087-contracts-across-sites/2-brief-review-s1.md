```
Step: S087 — Contracts across sites
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 31-10-2026
```

Reviewed against: 26810aa + uncommitted S088 (snapshot `refs/steps/S088`, f5bbb38) + uncommitted edits
outside both steps (`.claude/CLAUDE.md` test-timing and schema-docs lines; `EquipmentPicker.vue` label;
`ContractFields.vue` layout; `contracts.spec.js`, `readings.spec.js`, `screens.spec.js`,
`tickets-raise.spec.js`).

# S087 — Staleness review s1 (after S088)

**Verdict: no blocker or major finding. Two minor findings (a test S088 added that S087 breaks and the
brief does not list; A5's "committed first" against S088's real state), six nits.** The design, the
v50 statements, the three shapes of § 4.2 and the decisions KLA approved all still hold on S088's code.

Scope of this round: § 3 (Backend `local_db.py`, Tests, Docs), § 4.1, § 4.2, § 8.1, § 8.3, § 9 A5, the
`.claude/CLAUDE.md` lines both steps edit, and the frontend anchors KLA's edits could have moved. The
facts file `scratch/brief-facts-S087.md` predates S088 (its re-run crashed on the deleted
`migrations_v13.py`), so every S088-touched claim below was checked in the tree directly.

## Findings

### BS1-01 — minor — S088's production-path test breaks under v50 and is not in § 8.3

**Problem.** S088 added `backend/tests/test_migration_squash_v41.py`. Its
`test_production_s_v41_gets_v42_to_v47` builds v20–v41 from the fixture with rows, runs
`CURRENT = local_db._MIGRATIONS` and asserts `_versions() == [*range(20, 48)]`, then compares the
schema with a fresh `CURRENT` build. After S087, `_MIGRATIONS` is `[v41, v50]`: the versions become
`[*range(20, 42), 50]` and the assertion fails. Its name and docstring ("gets v42 on") are wrong too.
§ 8.3 lists the tests that break by file; this file is missing, and § 3's "19 files written" count does
not include it. The other five tests of the file still pass: the equivalence, half-applied and re-run
tests use `SQUASHED` only; the two refusal tests are refused at v41 before anything runs.

**Why it matters.** The coder would meet a red test the brief says nothing about and decide alone
what the production path should assert.

**Options.**
- (a) **Recommended:** keep the test, redirected: `test_production_s_v41_gets_v50`, assert
  `_versions() == [*range(20, 42), 50]`, the v41 description kept, every row kept, the schema equal to
  a fresh `[v41, v50]` build. It is the strongest production test the step has: a database built from
  the real v20–v41 texts with a ticket, an improvement and a lesson. § 8.1's
  `test_production_at_v41_gets_the_fresh_schema` (from `SQUASHED`, with a site, a person and a
  node document under the five-owner CHECK) stays as the targeted check of what v50 adds there.
- (b) Drop S088's test and rely on § 8.1's. Loses the only production path built from the released
  texts.

Add the file to § 8.3 and the count to § 3.

### BS1-02 — minor — A5 says "committed first"; S088 is coded and snapshotted, not committed

**Problem.** § 9 A5: "S088 is coded and **committed** first … If S088 is not done, S087 waits (the
orchestrator re-checks this brief against S088's commit)". The header says the baseline "moves to
S088's commit when it is coded". S088 is at gate B: coded, reviewed, snapshotted as
`refs/steps/S088` (f5bbb38), uncommitted in the working tree. The staleness check is being made
against that tree, so the coder would start on an uncommitted S088.

**Why it matters.** KLA approved A5 as written. Starting now is allowed by the workflow (snapshots give
each step its own commit while the next is coded, README § Orchestrated mode), but it is a choice
KLA should make, not the coder: S087's diff then sits on S088's uncommitted files (`local_db.py`,
the migration tests, `.claude/CLAUDE.md`), and S088's commit must land before S087's.

**Options.**
- (a) Wait for S088's commit, as A5 says; then `Baseline: <S088 commit>`.
- (b) **Recommended if S088's gate B is passing now:** start on the working tree. Reword A5: "S088 is
  coded (snapshot `refs/steps/S088`) and committed before S087; S087 is coded on S088's working tree
  when KLA says so." Set `Baseline: 26810aa + uncommitted S088`, and note that S088 commits first.

## Nits

- **BS1-03** (nit) § 3 Backend, § 4.1: the `local_db.py` anchors moved with the squash:
  v42–v47 `:1387-1538` → `:1140-1281`; `_PRECONDITIONS` `:1630` → `:1307`; `init_db`'s `pending`
  line `:1735` → `:1412`. Also add the header comment S088 wrote (`local_db.py:52-70`) to the
  docstring list: its "then the later versions run" wording and "New migrations continue after the
  last entry" stay, but any line naming v42–v47 names v50 after this step.
- **BS1-04** (nit) § 4.1: `backend/tests/fixtures/migrations_v13.py` no longer exists (S088 deleted
  it; git keeps v1–v13). Two sentences: "as `fixtures/migrations_v13.py` holds v1–v13 and S088's
  fixture holds v20–v41" → "as S088's `fixtures/migrations_v41.py` holds v20–v41"; "`DROP COLUMN IF
  EXISTS` … the second is in the v13 fixture only" → "neither is in `_MIGRATIONS` or
  `migrations_v41.py`; `DROP COLUMN IF EXISTS` was last used in v1–v13 (git history)".
- **BS1-05** (nit) § 8.1: `tests/migration_helpers.py` verified: `UPGRADE_CONFIG`, `_recreate`,
  `_run`, `_migrate`, `_rows`, `_schema`, `_versions` and **`SQUASHED`** (the v41 entry). Drop the
  "*to verify*" and the brief's own `V41`: import `SQUASHED`, as `test_migration_v36.py` and the
  squash test do. State the order the v47 shape is built in: `_recreate()`, `_migrate(SQUASHED)`,
  then `_migrate(MIGRATIONS_V42_V47)` (or one list `[*SQUASHED, *MIGRATIONS_V42_V47]`); never the
  v42–v47 fixture on an empty database. S088 § 3's one-call rule is about *its* fixture (v41 after
  v20–v40 is refused); S087's fixture holds no v41, and `_v41_squash_check` is keyed on 41 only, so
  it is not consulted once 41 is recorded — checked in `init_db` (`local_db.py:1412-1416`).
- **BS1-06** (nit) § 8.1: `test_a_half_applied_v50_converges` cites `test_migration_v45.py:99-109`
  as its pattern, a file this step removes. Anchor it to a test that survives:
  `test_migration_squash_v41.py::test_a_half_applied_v41_re_runs` (delete the `db_version` row, run
  again, compare `_schema()`), plus the CHECK dropped by hand as v45's did.
- **BS1-07** (nit) § 3 Docs, `.claude/CLAUDE.md`: S088 left the bullet headed **Migrations (S025,
  S088)** with "The old texts live only in `backend/tests/fixtures/migrations_v41.py` (frozen; it starts
  at v20); the migration tests' shared helpers are in `backend/tests/migration_helpers.py`". The
  brief's added sentence is right, but "live only in `migrations_v41.py`" must become "in
  `migrations_v41.py` (v20–v41) and `migrations_v47.py` (v42–v47)", and the heading gains S087.
  § SMTW-Review *Migrations* **does** list S088's squash ("`_MIGRATIONS` starts at v41 … Check both
  on every migration after v41"), so the brief's "if S088 lists its squash there" is settled: add
  "v42–v47 squashed into v50 (S087), their texts in `migrations_v47.py`" there. KLA's edit to the
  *Docs to keep current* row (the code reviewer runs `schema-docs.bat check` only in rounds whose
  diff touches `local_db.py` or `docs/schema/`) changes nothing for S087, which touches both.
- **BS1-08** (nit, in passing, not S088's change) § 3, § 4.1: `LATEST_VERSION = _MIGRATIONS[-1][0]`
  is derived (so at 26810aa too); "`LATEST_VERSION` 50" needs no edit. Say "follows the last entry".

## Checked and found consistent

- **v50 after the squashed v41** (§ 4.1, § 4.2): `_MIGRATIONS` is `[41, 42, …, 47]` with
  `_PRECONDITIONS = {41: _v41_squash_check}`; the six v42–v47 entries are byte-for-byte as at 26810aa
  (S088 impl report § 1), so § 4.1's table of what they did, the texts v50 copies and the frozen
  fixture `migrations_v47.py` are unchanged. The squashed v41's `chk_equipment_documents_owner` has
  the five owners (`local_db.py:990`), so step 8's "a five-owner CHECK at v41 becomes the six-owner
  one" and (b)'s row hold. `DROP CONSTRAINT IF EXISTS` is still v45's form (`:1253`) and `DROP INDEX
  IF EXISTS` v47's.
- **The three shapes** (§ 4.2): (a) fresh = v41 then v50, the v41 precondition passing on an empty
  database; (b) production at v41 recorded = v41 skipped, v50 pending, no precondition; (c) kept dev
  and test databases hold v41 recorded (through v20–v41 or S088's v41) and up to v47, so v50 is the
  only pending entry and step 5 converges `contracts`. "No `_PRECONDITIONS` entry" for v50 is
  consistent with S088's dict, which keeps its v41 entry.
- **S088's precondition and S087's tests**: `_v41_squash_check` refuses only when `db_version` holds
  rows and 41 is pending. Every § 8.1 path records 41 first (from `SQUASHED`) or starts empty, so no
  S087 test meets the refusal. The two refusal tests of S088 still refuse at v41 with `[v41, v50]`
  pending and nothing applied.
- **Removed and moved test files** (§ 3 Tests, § 8.1): `test_migration_v42.py` … `_v47.py` now import
  from `tests.migration_helpers` and `tests.test_migration_v36` (`_keys`, `_foreign_keys` stay there,
  S088 D7), `VERSIONS = [41, *range(42, N)]`; `_v46.py` and `_v47.py` still import
  `_a_v42_database_with_a_site_and_a_vendor` and `_add_contract` from `_v43.py`, so "all six go
  together" holds. S088's D6 (constraint tests stay on a squashed entry) is at S088 § 7.
  `test_modules.py` compares `schema_version` with `LATEST_VERSION`, green at 50.
- **Schema docs** (§ 8.1): `schema.json:3` and `schema-data.js:4` still say `"migration": 47` (S088
  changed no schema), so the expected diff "47 → 50" holds.
- **Frontend anchors after KLA's edits**: `EquipmentPicker.vue:6-8`, `:17-18`, `:39` (the label is now
  "Equipment"; the brief cites no label text); `ContractFields.vue:8`, `:19-20`, `:50-58`, `:172`
  (the layout change is at `:137-142`); `contracts.spec.js:137`, `:151`, `:571`, `:660`, `:701`,
  `:756` all still point at the lines the brief names. The three other e2e specs KLA edited are not
  S087's.
- **Order with S087**: S088 § 5.4 recommended S088 first and expected S087 to replace the v42–v47
  tests; S088's impl report § 5 confirms it left them for S087. Consistent with § 3 and § 8.1.

## Feedback

- hindrance: the facts file given was stale (`brief_facts.py` crashed on the git-tracked but deleted
  `backend/tests/fixtures/migrations_v13.py`), so every S088-touched claim was re-checked by grep
  (about 10 minutes). `check_path` should treat a file deleted in the working tree as "no such file".
- waste: `git diff … | grep -v '^[-+][-+]'` hid the `.claude/CLAUDE.md` bullet lines (`-- **Migrations`),
  one extra run to find S088's Migrations edit.
- idea: a staleness prompt could name the snapshot's diff of the test files that import from the
  changed step (`git grep -l migration_helpers`), since the broken test here (BS1-01) was in a file the
  brief never cites.
