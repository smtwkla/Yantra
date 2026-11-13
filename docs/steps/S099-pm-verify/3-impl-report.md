```
Step: S099 — Verify and send back a PM job
Doc: impl report
Author: coder (Opus)
Date: 02-11-2026
```

# S099 — Implementation report

**Result:** the engineer can verify a done PM job or send it back with a remark, from the job page and the
new *To verify* tab. Migration v54 copies the plan's setting onto the job at *Mark job done*. All unit
suites, the targeted browser run, the Normal whole suite and the `phone-webkit` run are green (numbers in
§ Tests). Two departures from the brief's text, both forced (§ 4, D-1 and D-2).

## 1. What was built

- **Migration v54**: `pm_jobs.needs_verification TINYINT(1) NULL` after `timeliness`, and the CHECK
  `chk_pm_jobs_verification`. No `_PRECONDITIONS` entry (every existing row gets NULL).
- **Mark job done** copies the plan's `needs_verification` onto the job. A job with 1 waits on *To verify*; a
  job with 0, and a job done before S099 (NULL), is final at `done`.
- **Verify job** (`POST /api/pm/jobs/<id>/verify`, optional remark): `done` → `verified`, final.
- **Send back** (`POST /api/pm/jobs/<id>/send-back`, required remark): `done` → `in_progress`; the done time,
  meter, judgement and copy are cleared. The plan's open job is cancelled when it is due, and send back is
  refused when it is started. A scrapped machine refuses send back, not verify.
- **The second *Done*** may not be dated before the latest send-back ("Done must be at or after it was sent
  back, …").
- **New key** `pm_job:verify`: the engineer, so the manager; in `SITE_SCOPED`.
- **The PM list**: a tab *To verify (n)* between *Upcoming* and *Done* (oldest done first, paged, with the
  findings); *Done* lists only the finished jobs (verified, or final). Badges *To verify*, *Verified*, *Sent
  back*.
- **The job page**: the *Verify* card (*Send back*, *Verify job*), each opening `PmJobVerifyDialog.vue`;
  "Waiting for an engineer to verify." for the others; the *Verified by …* line; the send-back remark above the
  items; the history lines *Verified* and *Sent back*, with "the person who did the work" on a self-verified line.
- **The done dialog**'s last line depends on the plan's setting (BS1-08).

## 2. How it works

- **The pure core** (`pm_work_core.py`): `awaits_verification`, `verify_error` (one table for both actions),
  `verify_remark`, `clean_remark` (S098's `_remark` renamed; `validate_result` passes the needed message),
  `done_time_error` (the window, then the send-back floor, then *Started*), `self_verified`, the texts
  `open_job_started`, `open_job_cancelled`, `done_before_send_back`, and `SEND_BACK_CHANGES`.
- **Verify** (`pm_work.verify_job`): pre-read of `plan_id` and `equipment_id`; in one transaction (6e) the plan
  FOR UPDATE, (6f) the job FOR UPDATE, `SELECT NOW()`, then plain: `load_node_for_user(…, key=VERIFY_KEY)` (404
  by `equipment:read`'s units, 403 without the key at the site), `verify_error`, the remark, the job update to
  `verified`, the `verified` event with the verifier's person (`current_person_id`; NULL for admin without a
  Team record).
- **Send back** (`pm_work.send_back_job`): (6e), (6f), the node `LOCK IN SHARE MODE`, `NOW()`, then the access
  check, `verify_error`, the scrapped refusal (from the locked node), the required remark, the plan's open job
  (plain): started → 409 `open_job_started`; due → `pm_jobs.cancel_job` with `open_job_cancelled(<this serial>)`.
  Then `update_row(SEND_BACK_CHANGES)` and the `sent_back` event. A refusal rolls everything back.
- **Mark done** (S098's route): reads the job's latest `sent_back` time after the locks (`_sent_back_at`) and
  passes it to `_event_time`, which now calls `done_time_error` (one place judges a time; Start passes neither).
  The update gains `needs_verification` from the locked plan row.
- **The list** (`pm_jobs.list_jobs`): `_PAGED_TABS` maps `to_verify` (`state = 'done' AND needs_verification =
  1`, `done_at ASC, id ASC`) and `done` (`verified`, or `done` with `COALESCE(needs_verification, 0) = 0`, newest
  first). `counts.to_verify` is one `COUNT` with the same filters, on every tab. `add_sign_off` fills
  `findings` (one `GROUP BY job_id` over `pm_job_results`, on the paged tabs), `verification` and `sent_back`
  (one query over the page's `verified` / `sent_back` events; the last per job and event kept in Python). No
  query per row.
- **The job page** (`pm_work.job_detail`): the same `add_sign_off` with findings, then `open_job` (only while
  the job waits), `can_verify` = waiting and `has_perm_at(VERIFY_KEY, site)`, `can_send_back` = `can_verify`,
  not scrapped, and no open job or a due one; each event gains `self_verified` (a bool on a verified line, null
  on others).
- **The frontend**: `pmLabels.js` holds the texts (`findingsText`, `verifiedText`, `sentBackText`,
  `sendBackBlockedText`, the badges, the tab list, `jobsQuery`, `countText`); `PmJobVerifyDialog.vue` is one
  `FormModal` component with `mode` `verify` or `send_back`, mounted twice by the page; a 409 shows above the
  field and the page reloads the job when the dialog closes (`stale`).

## 3. Files touched

Backend (7):

- `backend/local_db.py`: migration v54 (two statements, comment).
- `backend/pm_work_core.py`: the S099 constants, messages and functions; `_remark` renamed `clean_remark`.
- `backend/pm_work.py`: the routes *verify* and *send back*; Mark done's copy and floor; `_event_time` through
  `done_time_error`; `job_detail`'s new fields; `_open_job`, `_sent_back_at`; the docstring's ACCESS and LOCK
  ORDER lines.
- `backend/pm_jobs.py`: `_cancel` renamed `cancel_job`; the *To verify* tab, the narrowed *Done*, `counts.to_verify`,
  the item fields (`needs_verification`, `awaits_verification`, `findings`, `verification`, `sent_back`),
  `add_sign_off`, `sign_off_out`; the LOCK ORDER line.
- `backend/pm_jobs_core.py`: `TAB_TO_VERIFY`, `TABS`.
- `backend/config_rbac.py`: `pm_job:verify` with its comment; in `SITE_SCOPED`.
- `backend/equipment.py`: both (6f) places of the LOCK ORDER note (docstring only).

Backend tests (6):

- `backend/tests/test_migration_v54.py` (new): § 8.1.
- `backend/tests/test_pm_work_core.py`: the S099 core tests.
- `backend/tests/test_pm_verify_api.py` (new): § 8.2.
- `backend/tests/test_pm_jobs_api.py`: the changed lines (below) and the class `TestToVerify`.
- `backend/tests/test_rbac.py`: `test_role_matrix` rows and comment; `test_pm_job_verify_key`.
- `backend/tests/test_pm_jobs_core.py`: one assert, `TABS` now has four tabs (not named in the brief; § 4 D-4).

Frontend (9):

- `frontend/src/views/PmJobView.vue`: the *Verify* card, the waiting line, the verified line, the sent-back
  alert, the history's self-verified text, the two dialogs.
- `frontend/src/views/pm/PmJobVerifyDialog.vue` (new).
- `frontend/src/views/PmJobsView.vue`: the four tabs with the count, the paged tabs, the empty text, the pager
  shown only with a paged answer (§ 4 D-5).
- `frontend/src/components/PmJobRow.vue`: the *To verify* row (time, findings), "Verified by …".
- `frontend/src/utils/pmLabels.js`: the labels and helpers of § 3.
- `frontend/src/views/pm/PmJobDoneDialog.vue`: the last line.
- `frontend/tests/pmLabels.test.js`: the new helpers and cases.
- `frontend/e2e/pm-verify.spec.js` (new): § 8.4.
- `frontend/e2e/pm-job.spec.js`: one line (`/pm?tab=done` → `/pm?tab=to_verify`).

Docs: `docs/schema/notes.json`, `docs/schema/schema.json`, `docs/schema/schema-data.js` (generated),
`docs/Plan.MD`, `.claude/CLAUDE.md`; step files `1-brief.md` (status), `docs/steps/INDEX.md` (status), this
report.

**Changed lines in existing tests** (§ 8.3 "the coder names every changed line"):

- `test_pm_jobs_api.py::TestList::test_the_operator_sees_the_overdue_job`: the expected item gains
  `needs_verification`, `awaits_verification`, `findings`, `verification`, `sent_back`.
- `test_pm_jobs_api.py::TestList::test_the_upcoming_tab_and_the_counts` and
  `TestStartedAndDone::test_a_started_upcoming_job_is_on_due_and_counted_apart`: `counts` gains `"to_verify": 0`.
- `test_pm_jobs_api.py::TestList::test_an_unknown_tab_is_refused`: "tab must be one of: due, upcoming,
  to_verify, done".
- `test_pm_jobs_api.py::TestStartedAndDone::test_the_done_tab_newest_first_and_paged`: its plans are made with
  `needs_verification=False` (BS1-06).
- `test_pm_jobs_core.py::test_the_constants`: `TABS` has four tabs.
- `test_rbac.py::test_role_matrix`: `pm_job:verify` on the engineer and manager rows, and the S099 comment.
- `frontend/e2e/pm-job.spec.js` (S098 flow test): the last step opens `/pm?tab=to_verify`.

## 4. Decisions taken

- **D-1. The CHECK uses `<=>` (departure from § 4.1's SQL text, forced).** The brief's `(state <> 'verified'
  OR needs_verification = 1)` is NULL for a verified job with NULL, and a CHECK passes on NULL, so the row was
  accepted. § 8.1 says the CHECK must refuse it (the migration test showed it red). `needs_verification <=> 1`
  refuses it and changes nothing else. The comment in v54 says why.
- **D-2. The two-waiting-jobs test counts J4 from J1's second done (departure from § 8.2's last sentence,
  forced).** § 8.2 says "J1 done again with a `done_at` before J2's", but BR1-02's floor makes that
  impossible: J1's second done must be at or after its send-back, which comes after J2's done. The test instead
  checks the general rule (D3): J4 counts from the plan's latest done time, J1's new one. The case "a later job
  of the plan stays the base" is the same `ORDER BY done_at DESC` S097 already tests.
- **D-3. Verify and send-back times are stored to the minute** (`to_minute(NOW())`), as every other job time
  (*Started*, *Done*). With seconds, a *Done* typed in the send-back's minute sorted before the *Sent back*
  line and was refused by the floor. D9 (the server's now, no back-dating) holds.
- **D-4. One shape for `verification` and `sent_back` on the list and the page**: `{at, by_name, remark}`, plus
  `self_verified` on a verified line. § 6.3 names fewer list fields; one helper (`sign_off_out`) avoids two
  shapes, and every list reader may open the page anyway. `test_pm_jobs_core.py` needed its `TABS` assert
  changed, a sixth backend test file.
- **D-5. The PM list's pager shows only with a paged answer** (`answer.per_page` set). The browser test caught
  a Vue warning on a tab switch: the previous tab's answer has no `per_page`. S098's *Done* tab had the same gap.
- **D-6. `sendBackBlockedText` in `pmLabels.js`** builds the reason under the disabled *Send back* from
  `open_job` and the machine's lifecycle. Its scrapped text equals `pm_work_core.SCRAPPED_NO_SEND_BACK`, kept in
  the core as § 5.1 lists it; no route sends it.
- **D-7. The page's latest-event pick**: `add_sign_off` reads the page's `verified` and `sent_back` lines in
  time order and keeps the last per job and kind in Python, in place of a `GROUP BY` with a self-join; still
  one query for the page.
- **D-8. The phone tab-fit test** sets the viewport to 360 × 780 on a phone project (`isMobile`), the width
  BR1-05 names; the desktop runs at its own size. The label carries the lane's real count ("To verify (n)"),
  not 12.
- **Reuse**: `pm_jobs.cancel_job` (S097's `_cancel`, renamed), `pm_jobs.add_event`, S098's pre-read, `_lock_job`,
  `_share_node`, `_answer`, `load_node_for_user`, `current_person_id`, `FormModal` / `useFormModal`.

## 5. Not done, deferred or assumed

- **Fact found, not fixed (S097/S098):** the plan save's *Created* line has the time with seconds, while
  *Started* and *Done* are to the minute, so in a test where all happen in one minute *Created* sorts last on the
  page's history. On the floor a job is started minutes or days after it is made. The S099 tests find a line by
  its event name.
- **The tab-fit fallback** ("Verify (12)") was not needed: the test passed on `desktop-chromium` and
  `phone-webkit` (360 px).
- Q9 (keep the first round's item answers) stays as decided: overwritten in place.

## 6. Tests

Run name `YANTRA_TEST_RUN=s099c1`.

- Core first: `test_pm_work_core.py` and `test_pm_jobs_core.py` red at collection (the names did not exist),
  then green (214 passed).
- Migration test: red on the brief's CHECK (verified with NULL accepted), green with D-1 (8 passed with v53's).
- Targeted backend while coding: the PM tests and `test_rbac.py`, 431 passed.
- **All unit suites** (`tooling/run-tests.bat`): ALL SUITES PASSED: backend 5165 passed (158 s), frontend 451
  passed, tooling 239 passed. Two lines over 120 characters (two test imports) were wrapped while the run went
  on; the tooling suite (239 passed) and the two files (122 passed) were run again after it.
- **Schema docs**: `tooling\schema-docs.bat write` (4 passed), `git diff docs/schema/` read (v54's column and
  CHECK; the rest is S095–S098's uncommitted tables); `check` at the end: exit 0 (4 passed).
- **Build**: `npx vite build` passed (the usual chunk-size note).
- **Browser, new tests alone** (`E2E_LANES=1`, `phone-chromium`, `-g S099`): 6 passed (after two fixes of my
  own: the tab locator matched rows too, and the pager warning, D-5).
- **Browser, targeted** (`pm-verify`, `pm-job`, `pm-jobs`, `me`, `screens`): 56 passed, 1 skipped, 80 s.
- **Browser, whole suite at Normal** (`tooling/run-e2e-tests.bat`, once): 416 passed, 15 skipped, 0 failed,
  222 s. None of the three known order-dependent faults failed.
- **Browser, `phone-webkit`** (`--project=phone-webkit e2e/pm-verify.spec.js -g S099`, the container): 6 passed,
  29 s; the tab-fit test passed at 360 px, so no fallback label.

## Manual checks

- [auto] An engineer verifies a done job from the To verify tab — `frontend/e2e/pm-verify.spec.js::S099: an engineer verifies a done job from the To verify tab`
- [auto] Send back needs a remark; the technician sees it and marks the job done again — `frontend/e2e/pm-verify.spec.js::S099: send back needs a remark, and the technician sees it and marks the job done again`
- [auto] A job whose plan needs no verification ends at Done — `frontend/e2e/pm-verify.spec.js::S099: a job whose plan needs no verification ends at Done`
- [auto] An engineer verifying his own job is recorded — `frontend/e2e/pm-verify.spec.js::S099: an engineer verifying his own job is recorded`
- [auto] The technician and IT admin see no Verify job — `frontend/e2e/pm-verify.spec.js::S099: the technician and IT admin see no Verify job`
- [auto] The four PM tabs fit the phone width on one row — `frontend/e2e/pm-verify.spec.js::S099: the four PM tabs fit the phone width on one row`

On a real device: none (§ 8.5); no row added to `docs/steps/device-checks.md`.

## Docs updated

- `docs/schema/notes.json`: the `pm_jobs` line gains `needs_verification` (S099, v54) and S099's states.
- `docs/schema/schema.json`, `docs/schema/schema-data.js`: generated by `tooling\schema-docs.bat write`.
- `docs/Plan.MD`: § 3 a paragraph for `pm_job:verify` and the A.5.3 departure; § 4.3 the *Needs-verification
  flag* bullet says "Built (S096, S099)", and a *Built (S099)* paragraph under *PM job* (with the sentence on
  the item answers the brief gives).
- `.claude/CLAUDE.md` § SMTW-Review: the point *PM verification (S099)*, word for word from § 8.6.
- `docs/Keycloak.md`, `docs/steps/device-checks.md`: no change (no Keycloak role; no real-device check).

## Feedback

- rule: the brief's SQL and its own test disagreed (§ 4.1's CHECK `= 1` passes NULL; § 8.1 wants it refused),
  and § 8.2's two-waiting-jobs sentence cannot happen under BR1-02's floor; a reviewer check "run each CHECK
  against the test rows the brief lists" would catch the first (1 red run, 5 min).
- hindrance: `admin` in the backend fixtures is IT admin, the bypass is `keycloak_admin`; the names invite the
  wrong pick (1 red run).
- waste: a long brief (66 KB, 899 lines) took two reads before any code; a short "what changes in which file"
  table at the top would cut that (≈5 min).
- idea: `tooling/run-tests.bat` could fail fast on the line-width test before the 3-minute backend suite, so a
  long line is found before the run, not during it.

## Fix rounds

### Round 1

- **CR1-01 Fixed.** `pm-verify.spec.js` (self-verify test) calls `expectDialogFits(page)` on the *Verify job*
  dialog with its extra line, before `openDialog`. Red run: not possible, since the fix adds a check to a
  dialog that fits today; the check passes on both devices.
- **CR1-02 Fixed.** `job_time_error(moment, now)` no longer has `not_before`; its docstring says the floors are
  `done_time_error`'s. The two `not_before` cases are gone from `test_job_time_error` and
  `test_job_time_error_bad_input` (`backend/pm_work_core.py`, `backend/tests/test_pm_work_core.py`).
- **CR1-03 Fixed.** `open_job_started` now reads "... Verify this job, or raise a ticket for what is wrong."
  The core test and the brief's § 5.1 table follow. Red run: the text test fails without the change by
  construction (an exact string compare), not run separately.
- **CR1-04 Fixed.** The tab-fit test sets `counts.to_verify` to 12 with `page.route` on `/api/pm/jobs` (the
  real answer, one field changed; the default tab's request has no query, so the pattern is `jobs(\?|$)`),
  asserts the tab reads "To verify (12)", and also checks that the four tabs have the same height (no wrap).
  It no longer creates a job. First run failed (route missed the query-less request); after the pattern fix it
  passes on `phone-chromium` and `desktop-chromium`.
- **Tests:** `tests/test_pm_work_core.py` + `tests/test_pm_verify_api.py` 134 passed (`YANTRA_TEST_RUN=s099f1`);
  `npx vite build` built; `e2e/pm-verify.spec.js` + `e2e/screens.spec.js` 24 passed, 1 skipped, 0 failed.
- **Docs updated:** the brief's § 5.1 text only; no other doc is touched by this round.

### Feedback

- hindrance: a `page.route` regex with `\?` missed the query-less default-tab request; it cost two e2e runs
  (3 min) before I read the view's URL building.

## Verify review r2 (02-11-2026)

- CR2-01 (blocker, test only): `pm-verify.spec.js` now blocks the service worker (`test.use({ serviceWorkers: "block" })`, as `me.spec.js` and `readings.spec.js`), so the tab-fit test's `page.route` also answers on `phone-webkit`. Fixed by the orchestrator after the gate B snapshot, so it lands in S100's snapshot (step skill § Async verify review). Red: `tooling/run-e2e-tests.bat e2e/pm-verify.spec.js --project=phone-webkit` 1 failed, 5 passed without the line; green: 6 passed with it; at Normal 7 passed.
