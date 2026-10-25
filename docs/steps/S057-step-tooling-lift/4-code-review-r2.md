```
Step: S057 — The step tools name no repo, and the lift list
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 25-10-2026
```

# S057 — Code review, round 2 (verify)

**Verdict: no `blocker` or `major` finding is open.** All five round-1 findings are fixed. The fix round's diff adds 2 nits and no fault.

Reviewed against: snapshot `refs/steps/S057` (e4fe8df, parent db5b803). The working tree equals it. The unrelated `docs/roadmap/` files were left out.

## Tests run

- `YANTRA_TEST_RUN=s057cr2 tooling/run-tooling-tests.bat`: **173 passed** (the five files left in `tooling/tests`). The fix round's "263 passed" is wrong; 173 is the right count (see CR2-01).
- The staged tests, from a copy laid out like `smtw-common` in the session scratchpad (the impl report's commands), `uv run --no-project --with "pytest>=8,<10" pytest tooling/common/tests -rs`: **114 passed, 3 skipped**. The three skips are the renderer tests, which need `frontend/node_modules/playwright`. The copy was deleted after the run.
- Yantra's own settings, read by the new `e2e_config`: levels `basic normal targeted full`, default `normal`, history `full` before `2026-10-25T05:50Z`, the lanes total line, letters `b/n/t/f`. The new checks do not refuse Yantra's entries.
- Full unit suite and browser tests: not run. The fix round changed no backend, frontend or screen file.

## Round-1 findings

| ID | Status | Verified by |
|---|---|---|
| CR1-01 (minor) | **Fixed** | `e2e_config` (`tooling/steps/step_stats.py:224-244`) stops with one line, exit 2, for a default or history level that is not a level, a total line that does not compile, and a total line without exactly one group. `stop()` inside the `try` raises `SystemExit`, which the `except ValueError` / `except re.error` does not catch. Two new tests (`test_a_default_level_that_is_not_a_level_is_refused`, `test_a_total_line_without_one_group_is_refused`) cover both cases, including two groups and an unclosed group. The fix round gives their red result (2 failed without the fix). |
| CR1-02 (minor) | **Fixed** | The docstring (`step_stats.py:25`) names no repo. A grep of the synced tools finds no "Yantra" in `step_stats.py`. |
| CR1-03 (nit) | **Fixed** | The S057 row in `docs/steps/INDEX.md` says six entries and that the tests leave Yantra through the staging folder. |
| CR1-04 (nit) | **Fixed** | The README row *Browser-test spec files* says what happens when `targeted` is not a level. |
| CR1-05 (nit) | **Fixed** | `render_mockups.mjs:44-51` rethrows every error except `MODULE_NOT_FOUND` / `ERR_MODULE_NOT_FOUND`. No test, as the fix round says: the renderer tests skip without Playwright in the copy. |

## Findings

### CR2-01 (minor) The fix round reports a tooling-test count that no run gives

`docs/steps/S057-step-tooling-lift/3-impl-report.md:244`.

**Problem.** The fix round says `run-tooling-tests.bat` gave "263 passed". The suite has 173 tests (round 1, the orchestrator's re-run and this round all give 173). 263 is not a real result.

**Failure scenario.** `/step stats` and a later reader trust the report's counts. A wrong count hides whether the coder ran the suite, or which folder it ran. The rule says to record the real result.

**Fix.** Correct the line to "173 passed", or name the command that gave 263.

## Nits

- **CR2-02** (nit) `tooling/steps/step_stats.py:224-232`: a default-level entry with a trailing level and no time (`` `normal` `full` ``) passes the new level check, then `zip` drops `full` without a word. Stop when `len(words)` is even (an unpaired history level).
- **CR2-03** (nit) `tooling/steps/step_stats.py:25`: the rewritten docstring line is 139 characters. Re-wrap it to the width of the lines around it.

## Manual browser checks for the user

None. The brief lists no manual checks, and no screen changed.

## Files re-read

`tooling/steps/step_stats.py` (the diff and `e2e_config` in full), `tooling/roadmap/render_mockups.mjs` (the diff), the new tests in the staged `test_step_stats.py`, the S057 row of `docs/steps/INDEX.md`, and the settings part of `docs/steps/README.md`.

## Checked and found consistent

- The new level check covers both the default level (`words[:1]`) and every history level (`words[1::2]`).
- The total-line check runs before `E2eConfig` is built, so `e2e_seconds` never gets a pattern without a group.
- The fix round wrote nothing to `smtw-common` and staged nothing in git.
- The tests for the two new stops check exit code 2 and the message, not only that the call fails.

## Feedback

- waste: the fix round's wrong "263 passed" made the orchestrator re-run the tooling suite, and made me check the count again (1 extra run each).
- none other.
