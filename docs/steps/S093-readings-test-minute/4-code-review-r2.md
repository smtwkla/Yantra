```
Step: S093 — The readings tests take the expected time from the reading itself
Doc: code review r2
Author: Code reviewer (Opus)
Date: 01-11-2026
Status: Done — 0 blocker, 0 major, 0 minor, 1 nit
```

# S093 — Code review, round 2

**Verdict: no blocker or major finding is open.** CR1-01 is fixed in all three places. The fix round brings in no
new fault.

## Test results

- `YANTRA_TEST_RUN=s093cr2 tooling/run-backend-tests.bat tests/test_readings_api.py`: PASSED, 80 passed (10 s).
- No full suite: the fix round changed one test file only.
- No browser run: no screen or API changed.

## Earlier findings

| ID | Severity | Status |
|---|---|---|
| CR1-01 | major | Fixed (verified below) |

## CR1-01 verified

- Fact: line 101 (`test_an_operator_logs_a_reading_at_their_unit`) computes `taken_at` once and sends
  `local(taken_at)` itself. The assertion compares the answer with `api_time(taken_at)`, the same value. The check
  that the stored time is the time sent stays real.
- Fact: line 175 (`test_lower_than_the_reading_before_is_400_with_its_code`) builds `when` from `first["taken_at"]`.
  Line 197 (`test_a_back_dated_reading_must_fit_between_its_neighbours`) builds it from `later["taken_at"]`. Neither
  test reads the clock after its posts.
- Fact: `_shown` parses the first 16 characters of the API time (`YYYY-MM-DDTHH:MM`) and prints `DD-MM-YYYY HH:MM`,
  the format of the old `strftime`. The message checks therefore stay as strict as before.
- Fact: no other `_minutes_ago` call is made after a post for the same reading; the remaining uses keep the margin
  that round 1 checked.

## Red, then green

- Fact: the fix round records a red run for each fixed test with the caller-based patch: lines 172 and 194 failed
  on HEAD's file (2 failed), and line 96 failed alone (stored `18:36`, expected `18:37`). All three passed on the
  new file with the patch, and the whole file passed without it (80 passed). The patch was removed (no `_getframe`
  in the file). This meets the *Red, then green* rule.

## Nits

- **CR2-01** (nit) `backend/tests/test_readings_api.py:101`: the test inlines the post; `_log(operator, node, hours,
  "12345.6", taken_at=local(taken_at), note="  end of shift ")` does the same through the helper (`_post` passes
  `**body` through) and keeps the line under the file's width.

## Manual checks

None needed: the step changes one test file.

## Checked and found consistent

- The fix round's diff touches only `backend/tests/test_readings_api.py`; no production code changed.
- The fix round's `Docs updated: none` is right for a test-only change.
- The new `datetime` import is used only by `_shown`.
- The fix round's section keeps to scope A.

Files re-read: the fix round's diff of `backend/tests/test_readings_api.py`, and its lines 20–112 (the helpers and
the line-96 test).

## Feedback

- none
