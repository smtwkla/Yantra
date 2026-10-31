```
Step: S087 — Contracts across sites
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 31-10-2026
```

# S087 — code review, round 1

**Verdict: one `blocker` is open (CR1-01): the backend suite was red in my run.** The cause is a test that
depends on test order. The fault is older than S087, but it makes the step's suite red, so the fix round must
fix it. The step's own code has no `blocker`, `major` or `minor` finding. The migration, the global keys, the
gated fields, the reminders, the calls, the renewal, the documents, the screens and the docs follow the brief.
Two nits.

## Tests run

- `YANTRA_TEST_RUN=s087cr1 tooling/run-tests.bat`: **backend 1 failed, 4466 passed (147 s)**; frontend 409
  passed; tooling 231 passed; ALL SUITES FAILED. The failure is
  `tests/test_alerts.py::TestFanOut::test_push_kinds_queue_push_only_even_for_people_with_an_address` (CR1-01).
- Reproduced in one process, in a fixed order:
  `tooling/run-backend-tests.bat tests/test_contract_alerts.py::TestHandler tests/test_alerts.py::TestFanOut::test_push_kinds_queue_push_only_even_for_people_with_an_address -n 0`
  gives 1 failed, 13 passed. `tests/test_alerts.py tests/test_contract_alerts.py -n 0` gives 92 passed, and so does
  the whole `test_contract_alerts.py` file before the test (33 passed): the file's last class empties the queue.
- `YANTRA_TEST_RUN=s087cr1 tooling/schema-docs.bat check`: PASSED at migration v50 (4 passed), exit 0.
- `npx vite build` in `frontend/` (output to the session scratchpad): built in 4.86 s; only the old chunk-size
  warning.
- Browser: none re-run, because no finding of mine needs a run. The coder's runs are the right ones (§ 8.4):
  - targeted: `e2e/contracts.spec.js e2e/notifications.spec.js e2e/screens.spec.js`: 81 passed, 4 skipped;
  - the whole suite at Normal once: 370 passed, 15 skipped, 2 failed. The 2 failures are the known
    `e2e/changelog.spec.js:14` fault on desktop-chromium (S048, the empty 0.1.14 section), outside S087.
  - No shared frontend file changed (`api.js`, `e2e/support/`, the router, the auth store, `FormModal.vue`,
    `useFormModal.js`): `UnderContractCard.vue` only imports `userPermissions`. So no WebKit run is due.

## Findings

### CR1-01 (blocker) — the backend suite is red: a test counts every `email_send` row in the queue

`backend/tests/test_alerts.py:360`

- **Problem:** `test_push_kinds_queue_push_only_even_for_people_with_an_address` asserts that `task_queue` holds
  no `email_send` row at all. The tables are emptied once per session (`conftest.py` `_clean_tables`), and the
  backend wrapper runs `--dist loadscope`, so one worker runs whole classes in any order. `TestHandler` in
  `test_contract_alerts.py` drains contract alerts and leaves `email_send` rows (status `done`). Only that file's
  last class, `TestThroughTheWorker`, empties the queue (`queue_emptied`). When a worker gets `TestHandler`
  without `TestThroughTheWorker` before `TestFanOut`, the test sees those rows and fails.
- **Cause, by reading:** S084's `TestHandler` already left such rows
  (`test_email_to_the_managers_with_an_address`), so the fault is older than S087. S087 added two more email
  tests to `TestHandler` and changed which classes share a worker. I did not run the baseline to prove it.
- **Failure scenario:** my full run put both classes on worker gw2 in that order: 24 `email_send` rows, 1 failed.
  The coder's run happened to place them apart and was green. Gate B, the pre-flight or the release tests can go
  red on the same scheduling, with no code fault behind it.
- **Fix:** scope the assertion to this test's own work. For example, keep only the `email_send` rows whose
  payload `person_id` is the plant's manager or engineer (as `test_contract_alerts.email_sends` filters by
  person). Or empty `task_queue` at the start of the test, as `test_closed_email.py:83` does. Show the red run
  first: the command above fails without the fix and passes with it. Name the change in the fix round's
  "Decisions taken": the file is outside § 3's list.

## Nits

- **CR1-02** (nit) `docs/steps/S087-contracts-across-sites/3-impl-report.md` § 4: § 8.2's
  `test_the_texts_name_the_machine_sites` is not its own test. Its checks live in
  `test_push_to_the_holders_at_each_machine_site`, `test_email_to_the_managers_at_each_machine_site`,
  `test_alerts_core.py::…test_the_title_names_the_machine_sites` and `test_email_core.py::…test_no_machine_no_sites`.
  Say so in "Decisions taken".
- **CR1-03** (nit) `backend/contracts.py:3`, `:62`, `:72`, `:86`: four docstring lines S087 edited now run past the module's
  120-column width after the edit. Re-wrap them.

## The coder's decision on `warning_sites` and `site_codes`

The calls answer carries both, and that is right. Brief § 3 names both ("answers `site_codes` and
`warning_sites` instead of `site_code`"); § 5.7 and § 6 name only the new field the screen needs. The extra field
holds only the machines' site codes, which every `contract:read_basic` reader already gets from the detail, so it
leaks nothing. The report states the choice. No finding.

## Manual browser checks for the user

None. Brief § 8.5 lists no real-device check, and every check of § 8.4 is `[auto]` with a passing run.

## Checked and found consistent

- **Migration v50 (§ 4.1, § 4.2).** The eight steps are in the brief's order. Step 4 creates `contracts` in the
  final shape: no `site_id`; the reminder columns after `to_date`; `ix_contracts_active_to`, `ix_contracts_vendor`
  and `uq_contracts_renewal_of`. Step 5 has the seven one-statement `ALTER TABLE contracts`, with the foreign key
  dropped before its column and `ix_contracts_site` dropped by name. Every statement is safe to run twice. There
  is no `_PRECONDITIONS` entry, and `LATEST_VERSION` follows the last entry.
  `backend/tests/fixtures/migrations_v47.py` holds the six frozen entries.
- **The three shapes and the re-runs (§ 8.1).** `test_migration_v50.py` compares `_schema()` with the fresh build
  for each case: a fresh database, production at v41 with rows, dev at v47 with two sites, a renewal, a marker and
  a contract document (every row kept, `site_id` gone), and dev stopped at v43. It also covers a re-run on each
  shape and a half-applied v50 (the owner CHECK dropped, row 50 deleted). The constraint tests moved from the
  six removed files. `test_migration_squash_v41.py::test_production_s_v41_gets_v50` follows BS1-01.
- **Global keys (§ 5.1).** The four keys left `SITE_SCOPED`. No `has_perm_at`, `require_perm_at` or
  `sites_holding` remains for a contract key in `backend/`, `tooling/` or `frontend/` (git grep). `_flags()`
  replaces `_SiteFlags`. `_lock_contract` keeps the fail-closed `read_basic` 404 and then calls `check_perm`.
  `change_contract` now reuses `_lock_contract`; the report states this, and the behaviour matches § 5.1's table.
  The calls route keeps both decorators (`READ_BASIC`, `TICKET_READ`). `get_contract` and `contract_calls` give
  404 only for a missing contract.
- **ISO 27001 A.5.15, the gated fields.** Every answer still goes through `_contract_out`. The detail goes through
  `_machine_lines`, and the card through `_CARD_KEYS`, which holds no price, total, cost note or site. Every write
  still calls `_drop_gated` (create, change, renew, add machine, change price), now with `has_perm`. A price change
  needs `check_perm(READ_COST)`. IT admin holds neither `contract:read` nor `contract:read_senior`, so it gets no
  call-out number, cost note, price or document. The tests show this: `test_the_list_flags_are_global` (admin
  `(True, False, False)`), `test_it_admin_creates_but_neither_gated_field_is_stored`,
  `test_it_admin_leaves_the_callout_number` and `test_it_admin_may_not_restore_or_purge`. A login with no site role
  still gets 403 (`test_a_login_without_a_site_role_is_refused`).
- **Documents (§ 5.9).** `_owner_key` checks the owner's key by the union first. Then `read_contract`,
  `read_contract_for_change` and `lock_contract_for_change` check `contract:read_senior` with `check_perm` on every
  route, restore and purge included. The removed list adds the contract branch only when
  `has_perm("contract:read_senior")`, with no unit scope (`_scoped_branch(..., None, ..., None)`), and the row's
  `unit` is `None`.
- **Sites from the lines (§ 5.2).** `LINE_SITE_JOINS` and `LINE_SITES_SQL` are the one copy. They follow
  `NODE_JOINS`' COALESCE path with no `c` alias. `contracts.py` and `alerts.py` use them, and `alerts.py` still
  never imports `contracts.py`. `site_codes` comes back sorted, or `[]` when there is no line.
- **Reminders (§ 5.6, Q1 a, Q2 a).** `read_alert_contract` reads `site_ids` and `site_codes` plain. A contract with
  no line goes to every site. `_people_with_role` uses `SELECT DISTINCT` over `ms.site_id IN (…)` and returns `[]`
  for an empty list. The push title, the email subject and the *Sites* line name the codes, and leave them out with
  no line. `contract_facts` still holds no call-out number, cost note or price (`test_no_callout_number_or_cost_note`).
  The tests cover lines at two sites (each person once, not a third site), email per site and the no-line case.
- **Breakdown calls (§ 5.7).** `_sees_covered_sites` needs `ticket:read` at every active unit of each line site,
  and gives True with no line. `_vendor_reach` counts the assignable people per line site. `vendor_warning` returns
  the codes with a count of 0, sorted. `test_complete_needs_every_site_of_the_lines` and
  `test_warning_names_the_sites_without_an_assignable_person` cover both.
- **Renewal (§ 5.5).** `validate_renewal` and the site refusal are gone, and the insert has no `site_id`.
  `renewal_lines` skips only scrapped lines. `test_renewal_skips_scrapped_and_copies_moved_machines` and
  `test_renewal_copies_lines_outside_the_renewers_units` cover it. `can_renew` no longer reads the site.
- **LOCK ORDER (§ 5.8).** The `contracts.py` note has no site lock in Create and Renew, "plain: the node's units" in
  Add machine, and the site-row bullet replaced by "No contract write locks a site row". The `equipment.py` bullet
  and the `alerts.py` docstring match.
- **Add machine and the card (§ 5.4).** `_check_node` keeps rules 2 and 3 and drops the site rule. The card keeps
  every contract on the node or its ancestors. `UnderContractCard.vue` reads the global `userPermissions`.
  `covered_sql(coverage, today)` has no site list.
- **Screens and scope B wording.** Each new text is short, plain and says what to do where needed:
  - "Contract not found." with the link *Open the equipment list*;
  - "Only the managers see this note." and "Only the managers see these documents and photos.";
  - "As in the quote, before GST. Only the managers see it.";
  - "Prices start empty: the managers enter them on the new contract.";
  - "No equipment found at your units.";
  - "No Team record of … can be assigned at BRICKS, SMTW-KP. Give one a Technician role there in Masters › Team.";
  - "Contracts ending for machines at SMTW", and the same with ", by email".

  The *Sites* column hides on a phone, and the phone line carries the codes. The Site filter marks inactive sites
  " (inactive)" and opens on *All sites* (Q6 a). The dialog has no Site field. `EquipmentPicker` lost both props,
  and no caller passes them.
- **Docs pass.** `docs/schema/notes.json` has the three lines, and `schema.json` / `schema-data.js` are
  regenerated (the check exits 0). `docs/Plan.MD` § 2 item 9 and § 6 are updated. `.claude/CLAUDE.md` has the
  *RBAC deviation* sentence, *Files (S006)*, *Migrations (S025, S088, S087)*, *Notifications*
  (`people_with_role_at_sites`), the § SMTW-Review points and the new *Contracts across sites (S087)* point. No row
  in `device-checks.md` is due.
- **Browser tests.** The two **important** checks have tests that assert what the user sees: the header
  "· BRICKS", the call-out number, a saved edit, both machine lines, "· BRICKS, SMTW" and the list's codes. Each
  flow test calls `expectDialogFits` on the dialogs it opens. The new tests are untagged, and the `@device` list
  test keeps its tag. The report's `## Manual checks` lists every check of § 8.4 as `[auto]` with its test.
- **Scope.** Everything in § 3 is built, and nothing outside it except the decisions the report states.

## Feedback

- hindrance: the full backend run went red on an order-dependent test outside the step; telling a step fault from
  an old isolation fault took two extra targeted runs (about 2.5 min) and a read of `conftest.py` and the wrapper's
  `--dist loadscope` (CR1-01).
- idea: a lint or conftest guard could flag a test that asserts on a whole shared table (`SELECT … FROM
  task_queue WHERE task_type = …` with no person or row filter): with session-wide cleanup and `loadscope`, every
  such assertion is a latent order fault.
- waste: the step snapshot diff of `contracts.py` alone was 745 lines; reading docstring re-wraps beside the logic
  cost time. A `diff -w` style option that hides comment-only hunks would help on steps that reword many
  docstrings.
