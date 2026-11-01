```
Step: S093 — The readings tests take the expected time from the reading itself
Doc: impl report
Author: Coder (Sonnet)
Date: 01-11-2026
```

# S093 — Impl report

## What was built

Three readings tests now compare with the `taken_at` of the reading they logged, not with a second clock read. They no longer fail when a minute ends between the post and the assertion. No production code changed.

## How it works

`_log` returns the stored reading, and it carries `taken_at`. The tests keep that value and assert against it.

- `test_the_meters_list_carries_the_last_reading`: `last = _log(... "65", 30)`; the assertion uses `last["taken_at"]`.
- `test_rows_newest_first_a_cell_per_meter_total_counts_minutes`: keeps `oldest_at`, `middle_at`, `newest_at` from the logs at 60, 30 and 10 minutes; the rows are compared with `[newest_at, middle_at, oldest_at]`.
- `test_page_two_gives_the_next_minutes`: a dict `taken[minutes]` of the `hours` logs; the rows are compared with `[taken[30], taken[40], taken[50]]`.

## Files touched

- `backend/tests/test_readings_api.py` (1 file, 9 lines added, 8 removed).

## Decisions taken

- Chose the first option of the brief (use the logged answers) in all three places. A second small choice: no change to `_minutes_ago`; its other uses compute the time once.

## Red, then green

A scratch patch (removed afterwards, not in the tree) made `_minutes_ago` add one minute when its caller is a `test_*` function itself, that is, a call made after the posts. A plain "second call adds a minute" patch was wrong: two meters log at the same minute, so it split their rows.

Run on the three tests (`-k "last_reading or a_cell_per_meter or page_two"`, `YANTRA_TEST_RUN=s093c1`):

- Old test file (from HEAD) with the patch: 3 failed (the three tests above).
- New test file with the patch: 3 passed.
- New test file without the patch, whole file: 80 passed.

## Tests

- `tooling/run-backend-tests.bat tests/test_readings_api.py`: 80 passed.
- `tooling/run-tests.bat` (run name s093c1): backend 4471 passed, frontend 412 passed, tooling 231 passed.
- No browser run: no screen changes.

## Docs updated

None, because this is a test-only fix.

## Not done

Nothing deferred.

## Manual checks

None.

## Feedback

- idea: a "second call adds a minute" clock patch is wrong when two writes share a minute; the brief's red-run recipe could say "patch the call made after the posts" (first patch gave a misleading 2-red result, 1 extra run, about 2 min).

## Fix round 1

Answer to CR1-01 (major): **Fixed.**

- Line 96 (`test_an_operator_logs_a_reading_at_their_unit`): the test now computes `taken_at` once and posts it itself (`operator.post` with `local(taken_at)`), so the sent time and the expected time are one value. The check that the stored time is the time sent stays real.
- Line 172 (`test_lower_than_the_reading_before_is_400_with_its_code`) and line 194 (`test_a_back_dated_reading_must_fit_between_its_neighbours`): the expected time comes from the `taken_at` of the logged reading (`first`, `later`). A new helper `_shown` (in the test file) turns that API time into the `DD-MM-YYYY HH:MM` text of the message. The `datetime` import was added for it.
- The other `_minutes_ago` uses are unchanged.

Files touched: `backend/tests/test_readings_api.py` (1 file).

Red, then green (`YANTRA_TEST_RUN=s093f1`; scratch patch as in round 1: `_minutes_ago` adds a minute when its caller is a `test_*` function; removed afterwards, `_getframe` count in the file is 0):

- HEAD's file with the patch, `-k` the three tests: line 172 and line 194 tests fail (2 failed; the message holds a different minute). Line 96 test run on its own: fails, stored time `18:36` != expected `18:37`.
- New file with the patch: all three pass (2 passed, plus 1 passed).
- New file without the patch: `tooling/run-backend-tests.bat tests/test_readings_api.py`: 80 passed.

No full-suite run (one test file changed); no browser run.

Docs updated: none, because this is a test-only fix.

## Feedback (fix round 1)

- hindrance: the red recipe needs the patch applied to two file versions and a `-k` that matches test names; my first `-k` matched only 2 of 3 tests and the run path needed `tests/...` not `backend/tests/...` (2 wasted runs, about 2 min).

## Fix round 2 (orchestrator)

CR2-01 (nit): the line-96 test now posts through `_log(..., taken_at=local(taken_at), note=...)` instead of its own `operator.post`; the time is still read once. `YANTRA_TEST_RUN=s093f2 tooling/run-backend-tests.bat tests/test_readings_api.py`: 80 passed. Test-only change, so no new review (step skill § Phase 2 step 3). Docs updated: none (test only).
