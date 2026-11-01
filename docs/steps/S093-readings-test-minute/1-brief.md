```
Step: S093 — The readings tests take the expected time from the reading itself
Doc: brief
Author: Orchestrator (Opus)
Date: 01-11-2026
Track: fix
Baseline: 45ae23d
Status: Gate B 01-11-2026 (code review r1: 1 major, CR1-01, fixed; r2: 1 nit, CR2-01, fixed)
```

# S093 — The readings tests take the expected time from the reading itself

Found by the S092 code review r1 (`docs/steps/S092-equipment-search-wider/4-code-review-r1.md:18-21`, queued in
`docs/steps/INDEX.md`). KLA, 01-11-2026 (feedback triage, change 1): fix it on the fix lane.

## The bug

`backend/tests/test_readings_api.py::TestOtherKinds::test_the_meters_list_carries_the_last_reading` failed once in
the full backend run (expected 17:43, got 17:42) and passed on re-run. The app is right; the test is not.

## Steps to see it

1. Run the test so that a minute ends between the `_log` call of line 258 and the assertion of line 263.
2. The reading was stored at "now minus 30 minutes" of the old minute; the assertion works out "now minus 30
   minutes" again in the new minute, one minute later.

## Cause

`backend/tests/test_readings_api.py:263`: the expected `taken_at` is `api_time(_minutes_ago(30))`, computed again
after the post. `_minutes_ago` (line 38) rounds *now* down to the minute, so its value moves when the clock passes
a minute. Its docstring ("so the server's clock never ticks past it mid-test") covers the server's check of a
future time, not a second call. The same pattern is at line 542
(`test_rows_newest_first_a_cell_per_meter_total_counts_minutes`, `[api_time(_minutes_ago(m)) for m in (10, 30, 60)]`) and line 558
(`test_page_two_gives_the_next_minutes`, `for m in (30, 40, 50)`).

## The fix

- Take the expected times from what the test logged, not from a second clock read: keep the `_log` answers (each
  carries `taken_at`, as line 97 shows) and compare with their `taken_at`; or compute each `_minutes_ago(m)` once,
  before the posts, and pass that time to the post. The coder picks one and uses it in all three places.
- No production code changes. Lines 96, 172 and 194 have the same race (CR1-01: `_post` reads the clock again, or
  the test reads it after its posts); fix them the same way. The other `_minutes_ago` uses (221, 671–748) leave 10
  minutes or more of margin; leave them.

## Files

- `backend/tests/test_readings_api.py`

## The test that fails on the bug

A minute boundary cannot be forced without a clock fake. Red, then green: for one run only, make `_minutes_ago`
add one minute on its second call for the same `minutes` (a local scratch patch, not committed), and show the
three tests red with the old assertions and green with the new ones; record both runs in the impl report, then
remove the patch. Runs: `YANTRA_TEST_RUN=s093c1 tooling/run-backend-tests.bat tests/test_readings_api.py`, then
the unit suites `YANTRA_TEST_RUN=s093c1 tooling/run-tests.bat`. No browser run (no screen changes).

## Review log

| ID | Finding | Answer |
|---|---|---|
| CR1-01 | Lines 96, 172, 194 read the clock twice too; the brief wrongly said to leave them | Accepted (orchestrator's error in the brief; same bug, same file, so it stays on the fix lane): fix round 1 fixes them. The brief's red recipe was also wrong (two meters share a minute); the coder's caller-based patch replaces it |
