Step: S030 — Equipment lifecycle
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 23-10-2026

Reviewed against: 4a13de5 (the working tree adds only `docs/steps/README.md`'s index row and this step's folder; no code is uncommitted)

# S030 — Brief review, round 1

**Verdict: one `blocker` open** (BR1-01: the § 4.2 precondition refuses every empty database, so the test suite, every e2e run and a fresh deploy would stop at v25). No `major`. Four `minor`, six nits. U1 (*Lifecycle*) and U2 (full rename) are not re-opened; the review is of how the brief carries them out.

Facts file: `scratch/brief-facts-S030.md` was given and used; every existing name it lists resolved as the brief says. I grepped `status` across `backend/`, `frontend/src`, `frontend/e2e`, `frontend/tests`, `tooling/` and the two docs myself for § 3's completeness.

## Findings

### BR1-01 — blocker — `_v25_shape_check` refuses every empty database

**Problem.** `init_db` checks the precondition of **every pending version before any is applied** (`local_db.py:855-861`). On an empty database the pending list is v20…v25, so `_v25_shape_check` runs while `equipment` does not exist yet. The § 4.2 table says "no `status`, no `lifecycle` → refuse". The check therefore raises `MigrationBlocked` and v20 is never applied.

**Why it matters.** Every fresh database takes this path: a new test database (`conftest.py:154`, `ensure_schema` with the full list), every e2e run (`e2e_backend.py:63-64` drops and recreates the database), every lane database, and a fresh production deploy. § 5 ("An empty database: v20 creates `status`, v25 renames it at once") and § 7.1 test 1 contradict § 4.2 as written; the coder would find it on the first test run, but the user approves § 4.2 verbatim.

**Options.**
- (a) **Recommended.** A missing `equipment` table passes: v20 creates it with `status`, and the rename follows in the same run. This is what `_old_tables_for_v20` does ("A table that is absent passes: v20 creates it", `local_db.py:721-722`): read `information_schema.TABLES` first, then `COLUMNS`. Add the row "table absent → go" to the § 4.2 table, and let § 7.1 test 1 assert it (an empty database reaches v25 with no refusal).
- (b) Register the check so that it runs only when v20 is already applied. More engine code for one case; rejected.

### BR1-02 — minor — D4 departs from the S012 precedent in the same module, without saying so

**Problem.** § 4.4 says an old tab's `PUT` with `status` is ignored, because `validate_equipment` parses only `_fields(…)`. True, but the same function also holds `_REFUSED_FIELDS` (`equipment_core.py:201-208`): `make`, `model`, `class_id` and `type_id` are refused "even as null or unchanged, so such a tab fails loudly instead of having its … ignored" (S012 § 5.4). With D4, an engineer in a stale tab opens *Change status*, picks *Standby*, saves: the API answers 200, the dialog closes, the page shows the old value, no history row is written. The engineer believes the change took.

**Why it matters.** A silent no-op on a save is the case S012 decided against, in this file. The stale-bundle prompt reduces the window but does not close it (the prompt can be dismissed; a tab open across the deploy sends its first request before the check runs).

**Options.**
- (a) **Recommended.** Add `"status": "This field is now called lifecycle. Reload the page."` to `_REFUSED_FIELDS`: one line, the old tab shows it beside its select (`fieldError('status')`), and § 7.1's `test_the_old_status_field_is_ignored` becomes `…_is_refused` (400, `field: "status"`). D4 then says: no alias, and the old name is refused as S012 refuses `make`.
- (b) Keep the ignore, and state in D4 that it departs from S012 § 5.4 and why. The user's call; it is a judgement, so not a nit.

### BR1-03 — minor — The rollback rests on a dump that nothing takes before the deploy

**Problem.** § 4.1 and § 6 say "take the database dump before deploying v25" and that `deploy.py` "already prints that line". `rollback_lines` (`tooling/deploy.py:141-151`) points to "db-server's latest dump of the database (ERP-DB-Backup share)": that is the **daily** dump (`db_dump.sh`, 14-day retention; S025 BR3-01). The pre-deploy backup (S025 BR3-01 option a) is still in the README's Queued list ("Safe migrations"). So the brief names no command for the dump it relies on, and a rollback to the daily dump loses every ticket, note and lifecycle change entered since it ran.

**Why it matters.** v25 is the first migration since v20 that the previous image cannot run on (§ 4.1 says so). It is the first release where this rollback path is real. ISO/IEC 27001 A 8.13 (backup) asks for a backup that is taken and tested before a change of this kind, not for one that exists somewhere.

**Options.**
- (a) **Recommended.** § 6 names the step the user runs on db-server right before `Release`: start the dump unit by hand (S025 r3 option b named `systemctl start mariadb-dump.service`; the coder or planner verifies the unit's name in the devops repo) and check that a `mariadb_dump_vel_yantra_master_*.sql.gz` newer than now exists. § 6 also states what a rollback loses: the rows written between that dump and the restore.
- (b) Deploy right after the nightly dump and accept the loss window. Cheapest; say so in § 6.
- (c) Pull the "Safe migrations" queued item forward before S030. Right in the long run, but a devops-repo step for a rename.

### BR1-04 — minor — § 3.2 misses `test_site_checks_api.py`

**Problem.** `backend/tests/test_site_checks_api.py:54-56` sends `{"status": "standby"}` (`test_status_notes_model_at_b`). It is not in § 3.2's list.

**Why it matters.** After the rename, `status` is an unknown key: the test still passes (the site check refuses before the body matters) but no longer tests a lifecycle write at the wrong site. With BR1-02 (a) it may start to fail (400 before the 403, depending on the order of the checks).

**Options.** **Recommended:** add the file to § 3.2 with `{"lifecycle": "standby"}` and the test renamed `test_lifecycle_notes_model_at_b`. (The other test files I checked — `test_equipment_core.py:131,182,243`, `test_removed_documents_api.py:91,171,174`, `test_labels_core.py:90-91`, `test_asset_list_core.py:12-13` — are covered by the files § 3.2 already names.)

### BR1-05 — minor — The ISO 55000 claim overstates what the standard says

**Problem.** § 2 says ISO 55000 "calls the stages an asset passes through … its *life cycle* (create or acquire, operate and maintain, dispose)". ISO 55000:2014 defines *life cycle* as "stages involved in the management of an asset" and adds a note that the naming and number of the stages, and the activities under each, vary by sector and are **determined by the organization** (the definition is in § 3.2, *life cycle*; *asset life*, "period from asset creation to asset end-of-life", sits beside it). The create / operate / dispose list is a common reading (PAS 55 and the IAM use it), not the standard's text. ISO 55000 was also revised in 2024 (ISO 55000:2024), so a 2014 clause number can mislead.

**Why it matters.** The user is learning the standards and reads § 2 verbatim at gate A. The correct point is stronger for Yantra: the standard leaves the stage names to the organisation, so *in service / standby / out of use / scrapped* as Yantra's stages is within the standard, not a departure from it.

**Options.** **Recommended:** cite "ISO 55000:2014 § 3.2 *life cycle*" by term, say the standard leaves the stages to the organisation, and drop the three-stage list as the standard's. For EN 13306, cite "EN 13306:2017 § 6, item states" without sub-clauses (the terms *up state*, *down state*, *operating state*, *idle state*, *standby state* are all there; *in service* is Yantra's word, as `equipmentLabels.js:13` already says). The *condition* paragraph is right as written: EN 13306 defines *condition monitoring* and *condition based maintenance*, not *condition* itself, and the brief says "uses".

## Nits

- **BR1-06** (nit) § 4.1, comment on step 1 "an append: in place, no rebuild": true on the first run only. On a re-run after step 3, the same `MODIFY` moves `'lifecycle'` from position 4 back to the end — a copy, values kept by name. Say "safe to re-run" rather than "no rebuild".
- **BR1-07** (nit) § 4.1: `RENAME COLUMN IF EXISTS` needs MariaDB ≥ 10.5.2. Production already runs `SKIP LOCKED` (S013, ≥ 10.6), so it holds; one line in § 4.1 or § 8, with the server version Settings › Database shows, closes the question.
- **BR1-08** (nit) § 1 filter: *Any lifecycle* sits beside *All sites*, *All units*, *All classes*, *All types* and *Any criticality*, *Any ticket status* (`EquipmentView.vue:256-276`). Say in § 4.3 why *Any* ("All lifecycles" reads oddly) so the coder does not pick *All*.
- **BR1-09** (nit) § 7.2: scope "no text *Status* in the dialog or the list header" to the dialog and `thead` (the Tickets filter holds "Any ticket status"); and the test makes its own node with `createEquipment` as the S029 tests do (the three projects share one database).
- **BR1-10** (nit) § 3.3 and § 8.4: comments to update that the lists do not name: `DocumentsCards.vue:36` ("whatever the node's status"), `equipmentLabels.js:13`, `test_equipment_api.py:1`, `equipment.py:470`. Assumption 4 covers them as a rule; naming them saves the coder a grep.
- **BR1-11** (nit) § 2: "ISO 55001 § 7.5–7.6": § 7.5 is *Information requirements*, § 7.6 *Documented information*. Only § 7.6 is about records; cite § 7.6.

## Checked and found consistent

- **§ 3 completeness.** My grep of `status` finds every use of the equipment field in the files § 3 names: `equipment.py` (130, 141, 172, 228, 246, 331, 411-419, 435, 470-488, 632, 735, 753), `equipment_core.py`, `documents.py` (116, 125, 446, 452, 459), `tickets.py` (741, 752-754, 1069-1072), `masters.py` (291-293), `labels_core.py` (114, 127), `asset_list_core.py` (23, 31); the twelve frontend files and the three vitest files; `equipment.spec.js` (2, 74, 85, 87), `asset-list.spec.js:68`, `seed_e2e.py:126`. `seed_dev.py`, `alerts_core.py`, `tickets_core.py`, `screens.spec.js` and the e2e support files use no equipment `status`. The only miss is BR1-04.
- **Left alone, rightly.** Ticket `state`, `task_queue.status`, `ApiError.status`, every `status_code`, `/api/health`'s `status`, `db-status`, push statuses and the frozen `fixtures/migrations_v13.py` / `test_migration_v9.py` texts.
- **Nothing else references `equipment.status`.** v20 has no index, CHECK, view, trigger or generated column on it (`chk_equipment_level_place` uses `level`, `unit_id`, `parent_id`; `ix_equipment_model` uses `model_id`, `class_id`). `_old_tables_for_v20` reads `model_id` and `'model'` in the event ENUM only, so v25 does not disturb it.
- **Migration v25.** `RENAME COLUMN` keeps type, default and position. The ENUM order argument is right: in non-strict mode a `MODIFY` that drops a value in use blanks it; step 2 before step 3 makes the mode irrelevant. The re-run holds at every crash point (after step 1, 2, 3 or 4): `IF EXISTS` skips the rename, step 1 restores the both-list, step 2 updates nothing, step 3 drops `'status'`. Autocommit is on (`_connect_kwargs`), so the `UPDATE` is committed before step 3. `local_db.py:72-74` is cited correctly.
- **Existing migration tests.** `test_migration_v20` uses v20 alone (`V20 = …`); v21–v24 select their own versions; `conftest._TABLES` needs no change.
- **§ 4.4 claims.** `validate_equipment` ignores keys outside `_fields(…)` (`equipment_core.py:292-297`); the unknown query key is ignored by `enum_arg`. The S012 exception is BR1-02.
- **Design and layers.** The rule (`check_lifecycle_change`, `_TRACKED`, `LIFECYCLES`) stays in the pure core; the shell and the Vue files change names only. No new abstraction, helper or flag.
- **UI text (scope B).** *Change lifecycle* starts with a verb; "Scrapped is final. The lifecycle cannot change." says what happened and what follows; the help texts and the two glossary rows are plain. The scrap confirmation (inline Yes / No) is unchanged and still names the consequence.
- **Use on the floor.** No new screen or step: the same dialogs, one word changed. Operators read the values (*In service*, *Standby*, …), which do not change; only engineers with `equipment:edit` see the button and the form label.
- **Manual checks.** Automated only, with the one e2e test marked important; "On a real device: none" is right — every check is screen text.
- **Track and coder.** Full track (a migration that rewrites rows); Opus per the skill's rule (D6).
- **Docs.** Plan.MD lines 235 and 773 are the right lines; lines 75 and 816 use *status* in the maintenance sense and stay. Maintenance-Philosophy § 12 is where the two rows belong.
