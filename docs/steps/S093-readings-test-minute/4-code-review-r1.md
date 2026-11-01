```
Step: S093 — The readings tests take the expected time from the reading itself
Doc: code review r1
Author: Code reviewer (Opus)
Date: 01-11-2026
Status: Done — 0 blocker, 1 major, 0 minor, 0 nits
```

# S093 — Code review, round 1

**Verdict: one major finding is open (CR1-01).** The three assertions the brief names are fixed correctly. Three
more tests in the same file read the clock twice for one reading, and the brief told the coder to leave them.

## Test results

- `YANTRA_TEST_RUN=s093cr1 tooling/run-backend-tests.bat tests/test_readings_api.py`: PASSED, 80 passed (17 s).
- The full unit suites: not run again. The coder's run (`s093c1`) was green: backend 4471, frontend 412,
  tooling 231. My finding does not need a full run.
- No browser run: no screen or API changed.
- No migration, so no schema docs check.

## The three fixed assertions

- Fact: `test_the_meters_list_carries_the_last_reading` (line 259), `test_rows_newest_first_a_cell_per_meter_total_counts_minutes`
  (lines 529–542) and `test_page_two_gives_the_next_minutes` (lines 551–559) now keep the `taken_at` of each
  `_log` answer and compare with it. None of them calls `_minutes_ago` after the posts.
- Fact: the comparison is not weaker than before. The answer's `taken_at` is the stored time, and
  `test_an_operator_logs_a_reading_at_their_unit` checks that the stored time is the time sent.
- Fact: the order of the expected lists (`[newest_at, middle_at, oldest_at]`, `[taken[30], taken[40], taken[50]]`)
  matches the old `(10, 30, 60)` and `(30, 40, 50)` lists.

## The red, then green evidence

- Recommendation: accept the coder's recipe. The brief's recipe ("add one minute on the second call for the same
  `minutes`") was wrong: `_post` itself calls `_minutes_ago`, and two meters log at the same `minutes` in these
  tests, so that patch would also move the second meter's post and split one row into two.
- Fact: the coder's patch adds a minute only when the caller is a `test_*` function. In the three old tests,
  the only direct calls are the expected values made after the posts, so the patch moves exactly those. Three
  red on HEAD's file, three green on the new file, and 80 green without the patch is the right evidence.
- Fact: the same patch would also turn `test_an_operator_logs_a_reading_at_their_unit` red, because it calls
  `_minutes_ago(10)` directly (CR1-01). The coder's `-k` filter left that test out of the run.

## Findings

### CR1-01 (major) — three more tests read the clock twice for one reading

- **Where:** `backend/tests/test_readings_api.py:96`, `:172` and `:194`.
- **Problem:** each test computes a reading's time once in the test and once more inside `_post`
  (`_post` calls `_minutes_ago(minutes_ago)`, line 46). The two values differ when a minute ends between them.
  The brief (§ The fix) lists lines 96, 172 and 194 as "compute the time once and use it both ways". They
  do not:
  - line 96: `taken_at = _minutes_ago(10)` runs before `_log(..., 10)`, which computes `_minutes_ago(10)`
    again; the assertion on line 101 compares the answer with the first value.
  - line 172: `test_lower_than_the_reading_before_is_400_with_its_code` logs at 60 minutes, posts once more,
    then computes `when = _minutes_ago(60)` for the expected message. This is the same pattern as the bug, with
    two posts in the window.
  - line 194: `test_a_back_dated_reading_must_fit_between_its_neighbours` logs at 20 minutes, makes three more
    posts, then computes `when = _minutes_ago(20)`.
- **Failure scenario:** the full backend run reaches line 194 at 17:42:59.9. The reading is stored at 17:22,
  the refusal says "later reading of … 17:22", and the expected text says 17:23. The test fails once and
  passes on re-run, as the S092 failure did. A release test run can turn red on it.
- **Suggested fix:** use the stored time in all three tests, as the step did elsewhere:
  - line 96: drop `taken_at = _minutes_ago(10)`, or pass the time it holds to `_post` as `taken_at=local(taken_at)`
    with no `minutes_ago`, so only one clock read happens.
  - lines 172 and 194: keep the `_log` answer of the 60-minute and the 20-minute reading, and build `when` from
    its `taken_at` (parse the ISO time, then `strftime("%d-%m-%Y %H:%M")`).
  - Prove it red with the coder's patch, run on these three tests too.
- **Why major:** the step's purpose is to remove this fault from the file, and three instances stay. The brief
  is the cause, not the coder: the coder followed § The fix. The orchestrator decides whether this round fixes
  them or a brief amendment names them.

The other `_minutes_ago` uses (lines 221, 672, 689, 710, 729, 742, 749) set a ticket time or a direct insert
10 minutes or more from every reading, so a one-minute shift changes no result.

## Manual checks

None needed: the step changes one test file. The impl report's `## Manual checks` says "None", which is right.

## Checked and found consistent

- The diff touches only `backend/tests/test_readings_api.py`; no production code changed, as the brief asks.
- `## Decisions taken` names the option chosen (the logged answers) and that `_minutes_ago` is unchanged.
- `## Docs updated`: none due; a test-only change makes no listed doc wrong.
- Track `fix`: the change meets no full-track criterion.
- The impl report keeps to scope A.

## Feedback

- rule: the brief named lines 96, 172 and 194 as safe without a check, and the coder took it as settled; the
  review then found the same race there (`docs/steps/S093-readings-test-minute/1-brief.md` § The fix). A fix
  brief that says "leave the others" could carry a one-line reason per site, so a wrong claim is visible at
  brief time.
