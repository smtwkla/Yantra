```
Step: S099 — Verify and send back a PM job
Doc: code-review r1
Author: code reviewer (Opus)
Date: 02-11-2026
```

# S099 — Code review, round 1

**Verdict: no blocker or major finding is open.** One minor finding and three nits. All unit suites are
green, the schema docs check exits 0, and the build passes. The step builds what the brief asks; the
departures D-1…D-8 are reported and each one holds.

## Test runs (this round)

- `YANTRA_TEST_RUN=s099cr1 tooling\run-tests.bat`: **ALL SUITES PASSED**. Backend 5165 passed (142 s),
  frontend 451 passed, tooling 239 passed.
- `YANTRA_TEST_RUN=s099cr1 tooling\schema-docs.bat check`: exit 0, 4 passed, at migration v54. It ran
  alone, after the unit suites.
- `npx vite build` in `frontend/`: built. Only the usual chunk-size note.
- Browser: I did not run the specs again. No finding of mine needs a run. The coder's runs, as the impl
  report records them: new tests alone 6 passed; targeted (`pm-verify`, `pm-job`, `pm-jobs`, `me`,
  `screens`) 56 passed, 1 skipped; the whole suite at Normal once, 416 passed, 15 skipped, 0 failed;
  `phone-webkit` `pm-verify.spec.js -g S099` 6 passed. These are the specs § 8.4 names. No shared
  frontend file changed, so no extra WebKit run of `screens.spec.js` is due.

## Findings

### CR1-01 (minor) `frontend/e2e/pm-verify.spec.js:147` — the self-verify dialog is not fit-checked

- **Problem:** `S099: an engineer verifying his own job is recorded` opens the *Verify job* dialog and
  does not call `expectDialogFits`. The repo's convention is that a flow test calls `expectDialogFits`
  on every dialog it opens (settings: *Browser tests*).
- **Why it matters:** this is the one variant of the dialog with the extra bold line ("You did this
  job. The record will say you verified your own work."), so it is the tallest *Verify job* dialog.
  The first test checks only the shorter variant.
- **Failure scenario:** a later change makes the facts line or the extra line longer. On a 360 px phone
  the self-verify dialog then pushes its footer, and the *Verify job* button, out of view. No test sees
  it, because the only fit check is on the dialog without the extra line.
- **Fix:** add `await expectDialogFits(page);` after the click on line 147, before `openDialog`.

## Nits

- **CR1-02** (nit) `backend/pm_work_core.py:291`: `done_time_error` checks `started_at` itself, so the
  shell no longer passes `job_time_error`'s `not_before` anywhere (`pm_work.py:333`, `:506`). Remove
  `not_before` from `job_time_error` (and its test cases), or say in its docstring that only the core
  tests use it.
- **CR1-03** (nit) `backend/pm_work_core.py:301`: in `open_job_started`, "Verify it, or raise a ticket"
  can be read as "verify the open job". Write "Verify this job, or raise a ticket for what is wrong."
  (the brief's text; change § 5.1 with it in a fix round).
- **CR1-04** (nit) `frontend/e2e/pm-verify.spec.js:175`: the tab-fit test uses the lane's real count
  (D-8), often one digit, while BR1-05 asks for "To verify (12)". It also checks only the tabs' `y`,
  so a label that wraps inside its tab would pass. Set the count with `page.route` on `/api/pm/jobs*`
  (`counts.to_verify: 12`), and also check that the four tabs have the same height. With `px-1` the
  four labels need about 260 px of the 336 px, so the step's result does not change.

## The departures (impl report § 4)

- **D-1 (`<=>` in the CHECK): accepted, forced.** A CHECK passes when its result is NULL, so the brief's
  `needs_verification = 1` let a verified job with NULL through, against § 8.1. `<=> 1` refuses it and
  changes nothing else. `test_the_check_refuses` pins all four refusals, and the v54 comment says why.
- **D-2 (J4 counts from J1's second done): accepted, forced.** After J1's send-back, J1 is the plan's
  only open job. No other job can be done before J1's second done, and that done is at or after the
  send-back (BR1-02). So "J1 done again before J2's done" cannot happen. The test checks the general
  rule (the plan's latest done time).
- **D-3 (verify and send-back times to the minute): accepted.** Every other job time is to the minute.
  With seconds, a *Done* in the send-back's own minute would be refused by the floor. D9 still holds:
  the time is the server's.
- **D-4 (one shape for `verification` and `sent_back`): accepted.** It is a superset of § 6.3. Every
  list reader may open the page and see the same fields.
- **D-5 (the pager only with a paged answer): accepted.** It fixes S098's gap on a tab switch. It is a
  one-condition change in `PmJobsView.vue`.
- **D-6, D-7, D-8:** consistent with the brief. D-8: see CR1-04.

## Manual checks still for the user

None. § 8.5 has no real-device check, and the impl report's `## Manual checks` carries the four
**important** checks of § 8.4 (and the other two) as `[auto]`, each with its passing test.

## Checked and found consistent

- **Migration v54:** two re-runnable statements (`IF NOT EXISTS`), appended after v53. No row is
  updated, so no `_PRECONDITIONS` entry is due. The migration test covers a fresh database, a v53
  database with a due, an in-progress and a done job, the CHECK's refusals and passes, and a re-run.
  `LATEST_VERSION` is 54.
- **Docs pass:** `notes.json` gains the column; `schema.json` and `schema-data.js` are generated, and
  `check` exits 0. Plan.MD § 3 has the key and the ISO 27001 A.5.3 departure. Plan.MD § 4.3 has the
  *Built (S099)* paragraph, with the brief's sentence on the item answers, and the flag bullet says
  "Built (S096, S099)". `.claude/CLAUDE.md` § SMTW-Review has § 8.6's point word for word. Keycloak and
  `device-checks.md` correctly have no change.
- **Mark done** copies `needs_verification` from the plan row locked under (6e). It reads the latest
  `sent_back` time after the locks, and `_event_time` judges it through `done_time_error`. Start passes
  neither value, so its behaviour is unchanged. The second done is judged again against the job's own
  frozen due point (`due_from_job`); the test asserts `late`.
- **D1:** a job with 0 or NULL is final at `done`. `verify_error` answers `NO_VERIFICATION` for it. Only
  `verify_job` writes `verified`, and the CHECK refuses `verified` without 1.
- **Verify** is `done` → `verified` with an optional remark. It leaves `done_at`, `done_meter`,
  `timeliness` and the copy as they are, and it makes no `settle_plan_job` call. The event names
  `current_person_id` (NULL for the admin bypass). It is allowed on a scrapped machine (D7).
- **Send back** needs a remark (`SEND_BACK_REMARK`; empty and spaces are refused). It clears the four
  columns (`SEND_BACK_CHANGES`) and keeps `started_at`, the performer and the results. It refuses a
  scrapped machine from the node row it locked. The plan's open job is handled plainly after (6e):
  when it is started, the route answers 409 `open_job_started` and writes nothing (the test counts the
  events); when it is due, `cancel_job` cancels it with `open_job_cancelled(<this serial>)`. Both job
  rows are written under one (6e). A refusal rolls everything back.
- **The checks' order** is 401 → 403 `require_perm` → 404 (pre-read, then `load_node_for_user` by
  `equipment:read`'s units) → 403 at the site → 409 `verify_error` → (send back: 409 scrapped) → 400
  remark → 409 open job started. This matches § 5.2 and § 5.4.
- **Locks:** verify takes (6e) → (6f) → `NOW()` → plain reads. Send back takes (6e) → (6f) → (1) shared
  → plain reads → the open job's UPDATE → this job's UPDATE. This matches § 5.6 and the LOCK ORDER
  notes, which are updated in `pm_work.py`, both (6f) places of `equipment.py`, and `pm_jobs.py`. No
  second `FOR UPDATE` on a job row. `test_verify_waits_for_the_plan_lock` proves that (6e) comes first.
- **Permissions:** `pm_job:verify` is held by `("maint_engineer",)`, so also the manager; it is in
  `SITE_SCOPED`. `test_role_matrix` has the new rows, and `test_pm_job_verify_key` pins the holders,
  the scope and `pm_job:read`. The actor and the verifier's person come from the session, never from
  the body. All SQL uses parameters; the f-strings put in only constants and `marks(...)`.
- **The renames:** `clean_remark(value, needed_message)` is used by `validate_result`, and S098's remark
  tests stay green. `cancel_job` is called by `settle_plan_job` with the same behaviour.
- **The list:** `to_verify` is `state = 'done' AND needs_verification = 1`, oldest done first, paged.
  *Done* is `verified`, or `done` with `COALESCE(needs_verification, 0) = 0`. `counts.to_verify` is one
  `COUNT` with the same filters on every tab. `findings` and the sign-off lines take one query each per
  page; there is no query per row. The 400 text names the four tabs.
- **The screens:** the *Verify* card has two 48 px buttons (`big-button`) side by side with `gap-2`:
  *Send back* (`btn-outline-danger`, left) and *Verify job* (`btn-success`, right). Each opens a
  `FormModal` dialog with the facts, the consequence and the remark, so a mis-tap does not close a job
  (D6). A disabled *Send back* shows its reason as text under it, not in a tooltip. Readers without
  the key see "Waiting for an engineer to verify.". The sent-back alert and the verified line are
  shown. The history shows "the person who did the work" on a self-verified line. The 409 path reloads
  the job on close (`stale`). The tab label reads "To verify (n)". The done dialog's last line follows
  the plan's setting. The call contract of `useFormModal` is as § 5.8 says.
- **Texts (style B):** the buttons start with a verb ("Verify job", "Send back job"). The confirmations
  state the consequence. The refusals are one short plain line each and use the words *Send back* and
  *Sent back* that tickets use.
- **Tests:** the § 8.2 list is covered, including the failure modes: each role refused, another site,
  every state refusal, the remark refusals, scrapped, an open job started, two waiting jobs, the floor,
  the plan lock and the database down. The § 8.3 changed lines are named in the report. The four
  **important** checks of § 8.4 assert what the user sees (badges, lines, history order, rows on tabs).
  The tab-fit test alone carries `@device`, which is right for a layout test.
- **Line width:** the tooling suite (`test_line_width.py`) is green.

## Feedback

- waste: the brief is 66 KB (899 lines), so the Read tool cut it at line 671 and I needed a second
  read; the reviewer reads it in full every round (`1-brief.md`, 2 reads).
- idea: `step_snapshot.py diff --stat` could print the file count per code folder from the repo's
  settings (backend, frontend/src, tests), so a reviewer can check the brief's "21 code and test
  files" at once (counted by hand from the stat).
