```
Step: S055 — The Full level runs logic once: desktop and iPhone only their @device tests
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 25-10-2026
```

Reviewed against: 01d3566 + uncommitted S049 (`.claude/CLAUDE.md`, `.claude/agents/coder.md`,
`.claude/agents/code-reviewer.md`, `.claude/skills/step/SKILL.md`, `docs/steps/README.md`,
`tooling/release-tests.bat`; the brief's code files `run_lanes.py`, `test_run_lanes.py`,
`playwright.config.js`, `run-e2e-tests.bat` are unchanged since HEAD).

# S055 — Brief review, round 1

**Verdict: no blocker or major finding. Two minor findings and four nits.** Light track, so this is
the only round. The light criteria hold: no migration, no auth or RBAC, no locking, the pattern of
S047's Normal level, 10 files. The mechanism the brief relies on is as it says: `main()` pops the
caller's `E2E_LEVEL` and puts the level's own into `os.environ` before the `--list` run and the
lanes (`run_lanes.py:559-560`), so the lane plan and every lane see the same `E2E_LEVEL`; the
project `grep` in `playwright.config.js:35` is applied before the lane-plan filter, so a planned
lane keeps it. `test_only_full_starts_the_webkit_container` stays green: `expand_level("full", [])`
still returns no `--project`, so `needs_webkit_server` is true. No screen changes, so the UX
checks do not apply.

Facts file: `scratch/brief-facts-S055.md`, read first. It does not scan `playwright.config.js`
(`DEVICE_ONLY` is at line 17 there, as the orchestrator said).

## Minor

### BR1-01 — minor — The `@device` list is 26 tests today, not 23

**Problem.** § 1 ("23 today") and § 5 item 2 ("the 23 `@device` tests on the other two") carry
S047's count. `npx playwright test --list -g @device` on HEAD gives **26 per project**. Three
tests were tagged after S047: `readings.spec.js:871` (S051, the Now box), `readings.spec.js:1159`
(S050, the register's sideways scroll) and `tickets-work.spec.js:709` (S052, the Meters card).
Also: every project lists 189 tests today, so Full is 567 now (the intro says 560) and after
this step 189 + 26 + 26 = **241** ("about 240" is right).

**Why it matters.** § 5 item 2 is the acceptance check. A coder who reads "23" and sees 26
either reports a mismatch or, worse, looks for three tests to untag. The number drifts with
every step that adds a layout test.

**Options.**
- (a) Write 26 (and 567 / 241) with "on 25-10-2026", and make § 5 item 2 say: the other two
  projects list the same count as `--list -g @device` gives, whatever it is that day;
  the coder reports the numbers. **Recommended.**
- (b) Drop the counts and keep only the pointer to `--list -g @device`.

### BR1-02 — minor — The coder's one Full run is this brief's exception, not S047's rule

**Problem.** § 5 item 3 says "(S047's rule: the coder never runs Full, except for a step that
changes the Full level itself, as this one does)". S047's rule has no such exception
(`coder.md:140`: "never the Full level: it runs only in the release and when KLA asks";
`README.md:168`; `SKILL.md:348`). The exception is this brief's own.

**Why it matters.** Whether the coder may start a Full run (Docker, the WebKit container, the
machine at its limit for a few minutes) is KLA's call, and the light-track gate A shows only a
bullet summary. Worded as an existing rule, the summary may leave it out.

**Options.**
- (a) Keep the run and word it as this brief's request: "This step changes the Full level, so
  the coder makes one Full run to prove it (an exception to S047's rule, approved with this
  brief)". Name it in the gate A bullets. **Recommended**: the `--list` counts prove the
  selection, but only a run proves that the iPhone's 26 tests pass alone (for example a test
  that relied on state left by an earlier, now unselected test in the same file).
- (b) No coder run: the unit tests and the `--list` counts suffice, and the next release proves
  it. Cheaper, but a fault surfaces in the release, as S054's did.

## Nits

- **BR1-03** (nit) § 3 Docs: add `.claude/CLAUDE.md` § SMTW-Review, whose line "at `--level=full`
  to report the suite's state on every device" now means every test on the Android phone and
  the `@device` tests on the other two; say so there, or say in the brief that it stays.
- **BR1-04** (nit) § 3 Docs: S049 is editing the same six files now (`CLAUDE.md`, `coder.md`,
  `code-reviewer.md`, `SKILL.md`, `README.md`, `release-tests.bat` are modified in the working
  tree). Say that the coder edits them as they stand after S049's gate B, and that `Baseline:`
  will read `01d3566 + uncommitted S049`.
- **BR1-05** (nit) § 6 assumption 1 is a fact; write it so: `notifications.spec.js:104`
  (iPhone only), `:112` (desktop only) and `:241` (branches on the iPhone) are `@device`; the
  untagged `:88` and `:153` skip only on the iPhone, so they still run on `phone-chromium`. No
  other spec branches on the project outside a `@device` test (`tickets-work.spec.js:147` is
  inside the `@device` test at `:129`).
- **BR1-06** (nit) § 2: add S047's line "No maintenance standard (TPM, ISO 14224, EN 13306)
  applies: this is development tooling", so the reader does not look for one. ISO/IEC/IEEE 29119
  is cited as S047 did (Part 1 concepts, no clause number): consistent.

## Checked and found consistent

- `expand_level` (`run_lanes.py:150-161`): Full returns `(args, {})` today; the change to
  `{"E2E_LEVEL": "full"}` when no project is named mirrors Normal's branch. A named `--project`
  at Full keeps every matching test (S047 BR1-01), as the brief says.
- `E2E_LEVEL` reaches the `--list` run and every lane through `os.environ`
  (`run_lanes.py:559-560`, `:458-460`, `:480`); `test_an_inherited_level_does_not_filter_an_explicit_project`
  keeps the pop.
- `playwright.config.js:17,35`: `DEVICE_ONLY` is the only place the level is read; the `grep`
  is set before `E2E_LANE_PLAN` filters projects, so a lane keeps it. Today `E2E_LEVEL=full`
  lists 189 / 189 / 189 (no filter), `E2E_LEVEL=normal` lists 189 / 26 / 189: the mechanism
  works for desktop and will for `phone-webkit` the same way.
- `TestLevels` (`test_run_lanes.py:158-226`): only `test_full_adds_nothing` changes; the brief
  names it and the new test. `TestWebkitServer::test_a_full_run_needs_it` (`:48`) is unaffected.
- `tooling/steps/step_stats.py` counts runs by the `--level` flag, not by what Full runs:
  unaffected.
- The group weights (`group_weights`, S047 BR2-02) are tests listed now × measured seconds per
  test, so the smaller desktop and iPhone groups at Full are weighed right from the first run.
- `screens.spec.js` is `@smoke` + `@device`: it still runs on all three at Full;
  `journeys.spec.js` is `@smoke` only, so at Full it runs on the Android phone once, as the
  decision wants.
- Every doc line that describes Full is in the brief's list: `run_lanes.py:9,52` (docstring),
  `run-e2e-tests.bat:11`, `release-tests.bat:14`, `CLAUDE.md` § Browser tests (Full and the tag
  rule's reason), `coder.md:116-117,123-124`, `code-reviewer.md:54-55`, `SKILL.md:340-341`,
  `README.md:157-158`. Only § SMTW-Review is missing (BR1-03).
- Light track: all five criteria hold; the brief uses the short template.
- Manual checks: none, rightly; the `--list` counts and the one run are automated checks.
- Writing style: scope A throughout; no UI text in this step.

## Feedback

- hindrance: the facts script does not scan `frontend/playwright.config.js`, so `DEVICE_ONLY` came
  back "not found" and the orchestrator had to point to line 17 by hand (`scratch/brief-facts-S055.md`).
- idea: `step_facts.py` could scan the frontend's root config files (`playwright.config.js`,
  `vite.config.js`, `playwright.merge.config.js`) as code files; three of S046–S055's briefs cite them.
