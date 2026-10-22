```
Step: S020 — Parts used
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 22-10-2026
```

# S020 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** CR1-01 is fixed, and this round adds no finding. CR1-02 (the S003 flake, outside S020) and the nits CR1-03 to CR1-07 are still open, because the user did not ask for them.

Reviewed: only the fix round (impl report § Fix rounds, Round 1), against `4-code-review-r1.md` and the approved brief. The code is the working tree on `3df667c`, with S025, S019 and S020 uncommitted in the same files.

## Test results (my runs, 22-10-2026)

| Suite | Result |
|---|---|
| `tooling/run-tests.bat` | exit 0. Backend: 2003 passed. Frontend: 13 files, 110 tests passed. Deps: 42 passed. Tooling: 22 passed. |
| `tooling/run-e2e-tests.bat e2e/tickets-parts.spec.js e2e/tickets-work.spec.js` | exit 0. 66 passed in 2.7 min (22 tests × 3 projects), 0 failed. All six S020 tests pass in all three projects, including the changed test `tickets-parts.spec.js:268`. |

The fix round changed only a spec file, so I did not run `npx vite build`.

## Status of the round-1 findings

| Finding | Status | Check |
|---|---|---|
| CR1-01 (`minor`) | **Fixed** | `frontend/e2e/tickets-parts.spec.js:293-302`: the test now raises a second ticket, which stays open (raised), and adds a line to it through the API. As the operator, it checks the following on that open ticket: the line shows; there is no *Add part* in the card; the line has no *Change* and no *Remove*. These assertions fail if `PartsPanel` gets `:can-edit="isOpen"`, or if the edit buttons are shown to readers, which was r1's failure scenario. The engineer's checks on the closed ticket and the operator's "no card" check on the *bare* ticket are unchanged. `afterEach` removes the open ticket's line before *Not a fault*, so the tidy-up still succeeds. |
| CR1-02 (`minor`) | Open; outside S020 | Not asked. It is the S003 *Add equipment* flake on iPhone WebKit, queued outside this step. |

## Findings

None in this round.

## Checked and found consistent

- **The test asserts what the user sees.** It checks the visible line and the absence of the three buttons. It does not only check that the page opened.
- **Tidy-up.** The new ticket is pushed to `raised` by `raiseDefect`. `afterEach` deletes its parts, then closes it as not a fault and expects 200. The run shows no failure there in any project.
- **Shared database.** The line is found by a description that is unique to the run (`Gasket <serial>`), as the spec's header comment requires. No assertion counts list rows.
- **The manual-check row.** In `## Manual checks`, the `[auto]` line for this test keeps the same test name, and the name still matches what the test does. The test passes in my run.
- **Impl report (scope A).** The Fix rounds section answers the finding, names the file and the results, and says what it left out. No finding.

## Manual checks still needed (the user's)

These are unchanged from round 1. See the real-device checks in the impl report's `## Manual checks` (row 11 of `docs/steps/device-checks.md`).
