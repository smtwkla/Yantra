```
Step: S055 — The Full level runs logic once: desktop and iPhone only their @device tests
Doc: impl report
Author: Coder (Sonnet)
Date: 25-10-2026
```

# S055 — Implementation report

## 1. What was built

The Full level now runs every test on `phone-chromium` and only the `@device` tests on
`desktop-chromium` and `phone-webkit`. A named `--project` still runs every matching test there.

## 2. How it works

- `run_lanes.expand_level("full", args)` returns `{"E2E_LEVEL": "full"}` when the caller named no
  project (as Normal does). With a named project it returns no environment.
- `main()` already puts that variable into `os.environ` before the `--list` run and the lanes, so the lane plan and every
  lane see the same filter. No change was needed there.
- `playwright.config.js` reads `E2E_LEVEL` from a small table (`normal` → desktop; `full` → desktop and
  `phone-webkit`) and sets `grep: /@device/` on those projects.

## 3. Files touched (code and tests: 4; docs: 7 more, § Docs updated)

- `tooling/e2e/run_lanes.py`: the Full branch of `expand_level`; the docstrings.
- `tooling/tests/test_run_lanes.py`: `test_full_adds_nothing` became `test_full_adds_no_project_and_sets_the_full_level`; new `test_a_named_project_at_full_gets_no_device_filter`.
- `frontend/playwright.config.js`: `DEVICE_ONLY_BY_LEVEL` table; header comment.
- `tooling/run-e2e-tests.bat`, `tooling/release-tests.bat`: header comments.

## 4. Decisions taken

- `DEVICE_ONLY` is a lookup table by level, not two `if`s. It is the smallest form that holds both levels. No departure from the brief.

## 5. Not done, deferred, assumed

- No tag was added or removed (out of scope).
- Observation, not a fault: the Full plan's longest lane is `phone-webkit screens.spec.js` alone (162 s planned, lane 1). Lane time is now bound by that one group, not by the sum. Packing cannot split a spec file, so more lanes would not shorten the run.

## 6. Tests

**Red, then green (unit).** With the old code the new Full test failed:
`assert (['e2e/a.spec.js'], {}) == (['e2e/a.spec...VEL': 'full'})` (`{} != {'E2E_LEVEL': 'full'}`). After the change: `tooling/run-tooling-tests.bat`
(`YANTRA_TEST_RUN=s055c1`) gave **260 passed** (259 passed + 1 failed before). The new named-project test passes before and after (it
pins unchanged behaviour).

**`--list` counts (§ 5), run in `frontend/` on 25-10-2026:**

| | `phone-chromium` | `desktop-chromium` | `phone-webkit` | Total |
|---|---|---|---|---|
| `E2E_LEVEL=full npx playwright test --list` | 189 | 26 | 26 | **241** |
| the same with `-g @device` | | | | 78 (= 3 × 26) |

So the two device projects list the same 26 tests as `-g @device` gives, as the brief expects. Full went from 567 to 241.

**The one Full run** (`tooling/run-e2e-tests.bat --level=full`, this brief's own exception to "never Full", the iPhone in its container
`mcr.microsoft.com/playwright:v1.64.1-noble`): exit 0, **236 passed, 5 skipped, 0 failed**, of 241 tests; 146 s of tests ("All lanes done in
146 s"), 2 min 33 s wall from 19:21:29 to 19:24:02 including the container start. The 5 skips are the tests that skip by design on a project (S047 notes; unchanged by this step). Before the step the same level was 567 tests in about 6 minutes (brief).
No test failed alone on the iPhone, so none relied on state from an unselected test.

## Docs updated

- `.claude/CLAUDE.md`: § Release (the Full level's description), § Browser tests (the levels line and the tag rule's reason), § SMTW-Review (the audit's `--level=full` line). Only those lines; the uncommitted workflow edits are kept.
- `.claude/agents/coder.md`, `.claude/agents/code-reviewer.md`, `.claude/skills/step/SKILL.md`, `docs/steps/README.md` § Manual checks: the Full level's description, and the tag rule's reason in `coder.md`.
- The brief's `Status` and the README index row: `In code review`.
- Not due: `docs/schema.*` (no migration), `Plan.MD`, `device-checks.md` (no real-device check), secrets, Keycloak.
- The README S047 index row still says "layout on every device"; it is history and stays.

## Shared docs

(Not a worktree.) None.

## Manual checks

None in the brief. The `--list` counts and the Full run above are the automated checks of § 5.

## Feedback

- hindrance: `Edit`-style multi-line replacements failed on CRLF files (`code-reviewer.md`, `coder.md`, `SKILL.md`); I had to redo them with a CRLF-aware script (1 retry, ~2 min).
- idea: `run_lanes.py` could print the plan's longest single group, so a Full level bound by one group (`phone-webkit screens.spec.js`, 162 s) is visible as the critical path (`scratch/s055-full-run.log`, lane 1 plan).
- waste: the six "describes Full" docs are scattered in 8 files and found only by grep; a single "levels" paragraph that the others link to would cut this edit (8 files, ~10 edits).

## Fix rounds

### Round 1 (code review r1)

Fixed by the orchestrator, 25-10-2026 (comments and this report only: no new review, no new run):
- **CR1-01 (minor) — Fixed:** the header of `frontend/e2e/journeys.spec.js` says the journeys run on `phone-chromium` only, at Normal and at Full.
- **CR1-02 (nit) — Fixed:** the edited comments in `tooling/release-tests.bat`, `tooling/run-e2e-tests.bat` and `frontend/playwright.config.js` are re-wrapped to their blocks.
- **CR1-03 (nit) — Fixed:** the 5 skips of the Full run are `notifications.spec.js:104` and `:112` (each on two projects, by its own project check) and `screens.spec.js:108` (on desktop: the bottom bar is a phone screen).

#### Feedback

- none
