```
Step: S055 — The Full level runs logic once: desktop and iPhone only their @device tests
Doc: code review r1
Author: Code reviewer (Opus)
Date: 25-10-2026
```

# S055 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** One `minor` (a spec comment that still says Full runs on all three projects) and two nits.

**Test result.** `YANTRA_TEST_RUN=s055cr1 tooling/run-tooling-tests.bat`: **PASSED, 260 passed** in 9 s. No browser run of my own (none of my findings needs one). I relied on the coder's Full run (236 passed, 5 skipped, 0 failed of 241; `scratch/s055-full-run.log` shows "All lanes done in 146 s" and every lane exit 0).

**Read-only `--list` checks** (in `frontend/`, 25-10-2026):

| `E2E_LEVEL` | `phone-chromium` | `desktop-chromium` | `phone-webkit` |
|---|---|---|---|
| `full` | 189 | 26 | 26 |
| `normal` (run_lanes then adds the two Normal projects) | 189 | 26 | 189 |
| unset | 189 | 189 | 189 |
| `full`'s case with a named `--project=phone-webkit` (run_lanes sets no level) | | | 189 |

`-g @device` lists 78 (3 × 26). These match the impl report.

## Minor

- **CR1-01** (minor) `frontend/e2e/journeys.spec.js:4-5`: the header comment still says the journeys run "at Full on all three projects". After this step they are untagged `@device`, so at Full they run on `phone-chromium` only.
  - Failure scenario: a coder who reads the journeys spec to decide where a journey is checked believes the release runs it on the iPhone. The coder then leaves out a `@device` test that the iPhone now needs.
  - Fix: "so at Normal and Full they run on phone-chromium only". The brief's § 3 list did not name this file, but the change makes the comment wrong, so the docs pass covers it.

## Nits

- **CR1-02** (nit) `tooling/release-tests.bat:14`, `tooling/run-e2e-tests.bat:11`, `frontend/playwright.config.js:9`: the edited comment lines are now much longer than their neighbours (about 150 and 125 characters), and the config line breaks short at "E2E_LANE_PLAN". Re-wrap them to the block's width.
- **CR1-03** (nit) `docs/steps/S055-full-level-device-only/3-impl-report.md` § 6: "the 5 skips are … by design" does not name them. Name the tests: `notifications.spec.js:104` on `phone-chromium` and desktop, `:112` on `phone-chromium` and the iPhone, and `screens.spec.js:108` on desktop.

## Checked and found consistent

- **`E2E_LEVEL=full` reaches the `--list` run and every lane.** `main()` (`run_lanes.py:562-564`) first removes a caller's `E2E_LEVEL`, then sets the level's value in `os.environ`. `list_groups`, `single_stack` and `run_lanes` (`env = {**os.environ, …}`, `:484`) all inherit it. `E2E_LANES=1` and the `--shard` fallback inherit it too.
- **A named `--project` at Full gets no filter.** `expand_level("full", …)` returns `{}` when `named_projects(args)` finds one. `main()` then removes any inherited `E2E_LEVEL`, so a stale variable cannot filter the run either. The new test `test_a_named_project_at_full_gets_no_device_filter` pins this. The `--list` above shows 189 on a named `phone-webkit`.
- **Basic and Normal are unchanged.** The Basic and Normal branches of `expand_level` are untouched. `DEVICE_ONLY_BY_LEVEL.normal` is `["desktop-chromium"]`, as before. The existing `TestLevels` tests still pass.
- **The container still starts only at Full.** `test_only_full_starts_the_webkit_container` is unchanged and green. Full still lists `phone-webkit`, so `needs_webkit_server` is true.
- **Red, then green.** The report gives the failing assertion of the new Full test against the old code (`{} != {'E2E_LEVEL': 'full'}`). The named-project test pins existing behaviour, and the report says it passed before as well. That is correct for a test of behaviour that does not change.
- **The 5 skips are by design.** Each is a `test.skip` of a `@device` test on a project it does not belong to: `notifications.spec.js:105` (iPhone only), `:113` (desktop only), `screens.spec.js:108` (bottom bar on phones only). This is 2 + 2 + 1 = 5. The iPhone-only skips of the logic tests `:88` and `:153` no longer count, because those tests no longer run on `phone-webkit` at Full.
- **No check is lost on the iPhone.** Every test that branches on `testInfo.project.name` for an assertion is tagged `@device`: `tickets-work.spec.js:129` (`hours` not in view on the iPhone) and `notifications.spec.js:241` (service worker on Chromium only). The project-name uses in `equipment`, `masters` and `journeys` only build unique names.
- **The docs that describe Full now say the new thing, and nothing else changed in those lines.** `.claude/CLAUDE.md` § Release, § Browser tests (the levels and the tag rule's reason), § SMTW-Review; `coder.md` (the levels and the tag reason); `code-reviewer.md`; `SKILL.md`; `docs/steps/README.md` § Manual checks; the two `.bat` headers; the `run_lanes.py` docstrings; the config's header comment. A word-level diff of each line shows only the Full description changed. The other edits in those files (orchestrator rename, roadmapper, `/step feedback`, S049) are not this step's. `CLAUDE.md` § Pre-flight's re-run line (`--level=full … --project=<the failed project>`) is still right, because a named project gets no filter.
- **The tag rule's new reason reads right.** "The Android phone's 412 px checks every dialog in every flow; another device checks a dialog only through a `@device` test" states S047 decision 4's change (brief § 2) and replaces "Full checks those per device", which is no longer true.
- **Design.** A level table in `playwright.config.js` is the smallest form for two levels (the report's decision 4.1; no departure). There is no new layer or flag. It is the same mechanism as Normal (brief decision 2).
- **Scope.** Everything in § 3 is built, and no test was retagged. The one Full run is the brief's named exception (§ 5, BR1-02). Nothing was changed outside the repo.
- **Track: light** fits: test config, tooling and docs only. There is no migration, RBAC or app code.
- **Manual checks.** The brief has none, and the report says so.
- **Writing style.** The report and the doc lines are in scope A. The step has no screen text.

## Manual browser check

None.

## Feedback

- hindrance: the diff of `CLAUDE.md` and the agent files mixes S055's lines with the uncommitted rename and roadmapper edits, so I separated them with a grep on "Full" / "@device" (`git diff -w … | grep`, 1 extra pass).
- idea: a `tooling` check that greps `frontend/e2e/` and the docs for level descriptions ("all three projects") would have caught CR1-01. The brief's file list missed spec comments (`journeys.spec.js:5`).
