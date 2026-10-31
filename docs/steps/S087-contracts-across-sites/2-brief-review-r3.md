```
Step: S087 — Contracts across sites
Doc: brief-review r3
Author: Brief reviewer (Fable)
Date: 31-10-2026
```

Reviewed against: 26810aa + uncommitted edits outside a step (`EquipmentPicker.vue`, `ContractFields.vue`, the four e2e specs, `docs/steps/INDEX.md`; the untracked S087 and S088 folders are docs only)

**Verdict: no `blocker` or `major` finding is open.** One `minor` (constraint and half-applied tests of the removed files that § 8.1 does not carry), six nits. BR2-01 and BR2-02 are in the brief's text (§ 8.3, `TestCoveredSql::test_no_site`; `:534` / `:539`). Diffed `scratch/S087-brief-r2.md` against the brief (`git diff --no-index -w`) and re-read the changed text: the header, § 1 item 1, § 2 (ISO 9001), § 3 (`local_db.py`, Tests, Docs version mentions, file count), § 4.1, § 4.2, § 7 F2 and F12, § 8.1, § 8.3 (`test_modules.py`), § 8.6, § 9 Q5, A1, A5 and the Review log. The other sections were not re-reviewed. Facts file read: `scratch/brief-facts-S087.md`. S088's brief (`docs/steps/S088-migrations-squash-v41/1-brief.md`, in review) was read for the helper and fixture names S087 depends on. The decision to squash and the number 50 were not re-opened.

**v50 checked statement by statement, and by experiment.** The v42–v47 table of § 4.1 matches `local_db.py:1399-1538` entry for entry; steps 1–8 carry every statement of the six entries (the `vendors` table, `people.vendor_id` with its key, foreign key and CHECK, `contracts` in its final shape, `contract_equipment`, the `equipment_events` ENUM, `equipment_documents.contract_id` with its key, foreign key and the six-owner CHECK); nothing is lost. I ran step 5 read-only in the dev container (MariaDB 11.4) on four scratch databases of my own (`vel_yantra_test_s087r3_v47`, `_v43`, `_fresh`, `_combo`, dropped at the end; the script is `scratch/s087r3-v50-check.sql`): a `contracts` at v47 with two rows (one a renewal, one with a reminder marker), one stopped at v43, one in v50's step-4 shape (step 5 run twice on it), and one with step 5's four site statements in a single `ALTER TABLE`. Results (facts): every `IF [NOT] EXISTS` form the brief uses is a Note, not an error (`1060`, `1061`, `1091`), including `DROP FOREIGN KEY IF EXISTS` and `DROP COLUMN IF EXISTS`; all four tables end with the same 28 columns in the same order, the same keys (`PRIMARY`, `uq_contracts_renewal_of`, `ix_contracts_vendor`, `ix_contracts_active_to`), the same two foreign keys (`RESTRICT`) and the same four CHECK clauses (compared as MD5s over `information_schema`); the rows and their markers are kept. `SHOW CREATE TABLE` lists the keys in a different order on the converged table, which `_schema()` does not see (it sorts its rows). A4 is therefore a fact, not an assumption.

## Findings

### BR3-01 — minor — § 8.1 drops constraint and half-applied tests that the removed files hold

**Problem.** § 8.1 moves "the CHECK refusals of v42–v45's tests" and `test_a_second_renewal_of_one_contract_is_refused`. The six files hold more behaviour tests than that, and § 3 says "§ 8.1 covers what they checked":
- `test_migration_v42.py`: `test_an_unknown_vendor_is_refused` (`fk_people_vendor`), `test_the_name_is_unique_in_any_case` (`uq_vendors_name`, case-insensitive), `test_a_half_applied_v42_adds_the_check`;
- `test_migration_v44.py`: `test_a_node_twice_and_unknown_rows_are_refused` (`uq_contract_equipment`, the two foreign keys), `test_the_new_history_kinds_are_stored` (a row with each new ENUM value);
- `test_migration_v45.py`: `test_a_half_applied_v45_adds_the_owner_check_again` (the CHECK dropped, the row deleted, the re-run adds it back);
- `test_migration_v47.py`: `test_many_contracts_renew_nothing` (many NULLs pass the unique key).

**Why it matters.** S025's rule, which S088 § 7 D6 follows, keeps a constraint test on the squashed entry; dropping these loses the only tests of `uq_vendors_name`, `uq_contract_equipment` and `fk_people_vendor` in the migration suite. The half-applied case matters more for v50 than for v45: step 8 drops the owner CHECK before it adds the six-owner one, and step 5 is several statements, so a v50 that stops in between leaves a table with no owner CHECK or a half-converged `contracts`. § 8.1's `test_a_rerun_changes_nothing` runs v50 again on a *complete* result, which does not cover that window.

**Options.**
- (a) **Recommended.** List them in § 8.1 as moved to `test_migration_v50.py`, run on the fresh build, with one half-applied test: v50 applied, the owner CHECK dropped by hand and the `db_version` row 50 deleted, v50 run again: `_schema()` equals the reference and the CHECK clause names `contract_id` (the pattern of `test_migration_v45.py:99-109`). Note for the coder: `test_migration_v43.py`'s `_add_contract` inserts `site_id`; the moved tests need a helper without it.
- (b) Drop them, with the reason in § 8.1 (the API tests exercise the same keys).

## Nits

- **BR3-02** (nit) § 4.1 step 5: say how many statements it is. The text runs seven pieces together after one `ALTER TABLE contracts`, so the coder decides between one statement and seven; both work on MariaDB 11.4 (the `_combo` run above), so state the choice: one statement each, as the v48 draft had ("four statements, each safe to run twice") and as every entry writes them.
- **BR3-03** (nit) § 4.1 last bullet, § 9 A4: "the forms v45 and v47 already use" is not exact. `DROP FOREIGN KEY IF EXISTS` and `DROP COLUMN IF EXISTS` appear in no entry of `_MIGRATIONS` (v45 uses `DROP CONSTRAINT IF EXISTS`, v47 `DROP INDEX IF EXISTS`; `DROP COLUMN IF EXISTS` is only in the v13 fixture). Both are verified now (this review): a Note `1091`, no error. A4 can cite this round instead of "*to verify*", or keep the test as the record.
- **BR3-04** (nit) § 8.1 Schema docs: `git diff docs/schema/schema.json` also shows `"migration": 47` → `50` (`schema.json:3`, and `schema-data.js:4`), not only the `contracts` lines.
- **BR3-05** (nit) § 8.1 first paragraph: S088's brief now names where it leaves the helpers: `tests/migration_helpers.py` (`UPGRADE_CONFIG`, `_recreate`, `_run`, `_migrate`, `_rows`, `_schema`, `_versions`; S088 § 3) and `test_migration_v36.py` (`_keys`, `_foreign_keys` stay there; S088 § 7 D7). Name them, keeping "(to verify after S088)".
- **BR3-06** (nit) § 4.2 row (c): "a database stopped at v43–v46 also gains the v46 columns and v47's key" — the v46 columns are gained at v43–v45 only; v47's key at v43–v46.
- **BR3-07** (nit) `docs/steps/INDEX.md:96`: the S087 row still says "the site leaves the contract (v48)"; the orchestrator's to update with the status.

## Checked and found consistent

- **§ 4.1, the runner and the gap.** `init_db` applies every entry whose version is not in `db_version` (`local_db.py:1735`), in list order, and checks a precondition only for a pending version; with `_MIGRATIONS` = [v41, v50] a dev database recorded to 47 gets only v50, a fresh one v41 then v50, production (41 recorded) only v50. The rows 42–47 stay in `db_version`. `db_status` reads `ORDER BY version DESC LIMIT 1` (`local_db.py:1831-1836`), so Settings › Database and `test_modules.py:40` see 50; `schema_docs.py:134` compares the fresh build's version with `LATEST_VERSION` (50 = 50).
- **§ 4.1 step 4 and step 5, the final shape.** Columns in v47's order less `site_id`, with the reminder columns after `to_date`; keys and CHECK names as the fresh CREATE; equal across the three shapes (the experiment above). The foreign key goes before the index and the column; `ix_contracts_site` is dropped by name; the unique key is added before `ix_contracts_renewal_of` goes, v47's order, so `fk_contracts_renewal_of` always has an index.
- **§ 4.1 steps 1–3, 6–8.** v42's three texts, v44's two and v45's three are already `IF [NOT] EXISTS` or a MODIFY that is a no-op on a re-run; a six-owner CHECK re-added over a five-owner one is what v45 does today, and a converged dev table gets the same clause.
- **§ 4.2 (b).** On a v41 database `people.vendor_id` and `equipment_documents.contract_id` arrive NULL; `chk_people_vendor` holds for NULL and the six-owner CHECK holds for every row with one of the five owners; no `_PRECONDITIONS` entry is needed, as S088 § 5.2's check covers the one shape (a recorded database without v41) v50 cannot handle.
- **§ 3 Tests / § 8.1 Removed.** `test_migration_v46.py` and `_v47.py` import from `test_migration_v43.py` (`:9`, `:14`), and all six slice `_MIGRATIONS` by a range that v50 is not in, so the six go together; S088 § 8.3 changes only their import and `VERSIONS` before that. The count 19 written (2 new, 14 backend, 3 frontend) and 6 removed is right.
- **§ 3 Docs, version mentions.** The same rule as S088 § 3 Docs ("Comments citing old versions stay"); `notes.json`'s `contracts` line names `ix_contracts_site`, which § 3 rewrites.
- **§ 2, § 7 F2 and F12, § 8.6, § 9 Q5, A1, A5.** Consistent with § 4; F12's rejected options match § 4.2's; the SMTW-Review point names v50.
- **Seeds and kept databases.** `tooling/dev/seed_dev.py` and `tooling/e2e/seed_e2e.py` insert no contract; `conftest.py` runs `ensure_schema` (`:208`) on the kept worker databases, so they converge through v50, and `_TABLES` already holds `contracts` and `contract_equipment` (`:186`).

## Feedback

- idea: a `tooling/dev/dev-db-sql.bat <file>` wrapper (the compose exec with the root password from CLAUDE.md's drop procedure) would make a read-only SQL experiment on a scratch database one whitelisted command; this round built the `docker compose … exec -T mariadb mariadb …` line by hand from the drop procedure.
- rule: the agent instructions say "scripts only in `scratch/`" and § Shell on Windows covers Python scripts run with `uv run`; a SQL file run through the container's client is covered by neither, so it was a judgement call whether it counts as an allowed read-only experiment (it touched only databases named for this round and dropped them).
- hindrance: the brief (878 lines) and the facts file (870 lines) each passed the Read tool's token cap, so each took two reads; the facts file's *Code names* section repeats "used in N code files" for names the brief marks **(new)**, which a reviewer never needs.
