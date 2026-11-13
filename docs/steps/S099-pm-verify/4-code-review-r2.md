```
Step: S099 — Verify and send back a PM job
Doc: code-review r2
Author: code reviewer (Opus)
Date: 02-11-2026
```

# S099 — Code review, round 2

**Verdict: one blocker is open (CR2-01).** The fix round's new `page.route` makes the `@device`
tab-fit test red on `phone-webkit`, so the release's Full level fails. CR1-01, CR1-02 and CR1-03 are
fixed. CR1-04 is fixed on the two Chromium projects only.

## Test runs (this round)

- `YANTRA_TEST_RUN=s099cr2 tooling\run-backend-tests.bat tests/test_pm_work_core.py
  tests/test_pm_verify_api.py tests/test_pm_work_api.py`: **PASSED**, 169 passed (15 s). The fix round
  changed only `pm_work_core.py` and its test in the backend, so the full command was not due.
- `YANTRA_TEST_RUN=s099cr2 tooling\run-e2e-tests.bat e2e/pm-verify.spec.js --project=phone-webkit -g fit`:
  **1 failed** (`pm-verify.spec.js:168`, `S099: the four PM tabs fit the phone width on one row`). The
  run was needed: the test is `@device`, so the release runs it on the iPhone, and the fix round ran it
  only on the two Chromium projects.
- The coder's targeted run (`pm-verify.spec.js` + `screens.spec.js`, 24 passed, 1 skipped) names the
  right specs for a fix round.
- Schema docs check: not due. The diff touches neither `backend/local_db.py` nor `docs/schema/`.

## Findings

### CR2-01 (blocker) `frontend/e2e/pm-verify.spec.js:172` — the tab-fit test is red on `phone-webkit`

- **Problem:** the CR1-04 fix answers `/api/pm/jobs` through `page.route`. WebKit does not route a
  request while the app's service worker (S021) controls the page. `me.spec.js:12` and
  `readings.spec.js:20` record this fact, and both specs set `test.use({ serviceWorkers: "block" })`
  for it. `pm-verify.spec.js` has no such line.
- **Failure scenario:** seen in this round's run. On `phone-webkit` the route never fires, the real
  answer arrives with `to_verify` 0, and the tab reads "To verify". The assertion
  `toHaveText("To verify (12)")` at line 180 times out after 10 s. The release (`release-tests.bat`,
  Full level) runs `@device` tests on `phone-webkit`, so the release turns red.
- **Fix:** add `test.use({ serviceWorkers: "block" });` near the top of `pm-verify.spec.js`, with the
  same one-line reason as `me.spec.js:12`. No test in the file needs the service worker. Then run
  `tooling\run-e2e-tests.bat e2e/pm-verify.spec.js --project=phone-webkit` once (the whole file, since
  the line changes every test in it on WebKit), and the targeted run on the other projects.

## Earlier findings

| ID | Severity | Status |
|---|---|---|
| CR1-01 | minor | **Fixed.** `expectDialogFits(page)` is called after the click on *Verify job* in the self-verify test (line 148). `expectDialogFits` opens the dialog itself, as in the first test (line 76). The missing red result has its reason: the check passes on a dialog that fits today. |
| CR1-02 | nit | **Fixed.** `job_time_error(moment, now)` has no `not_before`; the docstring names `done_time_error` for the floors. No caller passes it (`done_time_error` at `pm_work_core.py:285` is the only one). The two test cases are gone. |
| CR1-03 | nit | **Fixed.** The text reads "Verify this job, or raise a ticket for what is wrong." in `pm_work_core.py:301`, its test and the brief's § 5.1 table (line 269). |
| CR1-04 | nit | **Fixed on Chromium; red on `phone-webkit`: see CR2-01.** The count is set to 12 through `page.route`, the label is asserted exactly, and the four tabs' heights are compared. The regex `jobs(\?|$)` matches the default tab's request without a query, and not `/api/pm/jobs/<id>`. |

## Nits

- none

## Manual checks still for the user

None, as in round 1.

## Checked and found consistent

- Files re-read: `backend/pm_work_core.py` (the changed functions and their callers),
  `backend/tests/test_pm_work_core.py` (the changed tests), `frontend/e2e/pm-verify.spec.js` (lines 1–30
  and the changed tests), `frontend/e2e/support/dialogs.js` (`expectDialogFits`), the URL building in
  `PmJobsView.vue:85`, and the brief's § 5.1 table.
- The diff's changes to `improvements.spec.js` and `labels.spec.js` are S100's (the fix lane), not
  this round's, and are not judged here.
- The tab-fit test no longer makes a job, so `press`, `jobFor` and `doneByApi` keep their other users
  and nothing is left unused.

## Feedback

- idea: a fix round that adds `page.route` to a spec could be told to check the spec's
  `serviceWorkers: "block"` line, since WebKit skips the route otherwise; the fact lives only in two
  spec comments (`me.spec.js:12`, `readings.spec.js:20`), and the coder's Chromium runs could not show it
  (1 WebKit run, about 2 min).
- rule: the fix-round rule "targeted runs only" says nothing of a changed `@device` test, which the
  release runs on `phone-webkit`; naming the iPhone run for it would have caught CR2-01 in the fix round
  (`docs/steps/README.md`, the coder's fix-round runs).
