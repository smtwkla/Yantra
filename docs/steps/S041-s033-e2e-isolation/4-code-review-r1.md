```
Step: S041 — S033's e2e test isolated from the seed extruder
Doc: code review r1
Author: Code reviewer (Opus)
Date: 24-10-2026
```

# S041 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** One `minor` finding, no nits.
The fix is correct, inside the brief and inside the fix-lane limits.

## Test results (my own runs, `YANTRA_TEST_RUN=s041cr1`)

- `tooling/run-tests.bat`: backend 1 failed, 2519 passed; frontend 142, deps 42,
  tooling 106 passed.
  - The one failure is `tests/test_alerts.py::TestSendOutcomes::test_a_redirect_is_never_followed`.
    It failed with `ConnectionAbortedError [WinError 10053]` on a local socket, a
    Windows network flake. S041 changes no backend code.
  - A re-run of `tests/test_alerts.py`: 60 passed. I judge the suite green for this step.
- `npx vite build`: not run. No file under `frontend/src/` changed in this step.
- `E2E_LANES=1 tooling/run-e2e-tests.bat e2e/equipment.spec.js e2e/labels.spec.js
  e2e/screens.spec.js e2e/tickets-parts.spec.js`: **90 passed** (3 projects, 4.3 min).
  - Why these specs: `equipment.spec.js` holds the changed test.
    `labels.spec.js` and `screens.spec.js` hold the checks that the bug broke.
    `tickets-parts.spec.js` holds the coder's one failure.
  - Why one lane: one lane runs the files in name order on one database. So
    `equipment.spec.js` runs before `labels.spec.js` and `screens.spec.js`. This
    is the order that made the bug show. The label count "2 labels on 1 sheet"
    (`labels.spec.js:69`) and `/labels?ids=1&parts=1` in `screens.spec.js:69`
    are green on all three projects after the S033 test ran.
  - The full suite was not needed: the step changes no shared frontend code.

## The coder's failure at `tickets-parts.spec.js:129` (phone-webkit)

**Judgement: a flake, not caused by S041.** The reasons:

- Fact: S041 changes only one test in `equipment.spec.js`. It touches no ticket,
  part or app code.
- Fact: the change makes the seed extruder have *fewer* nodes during a run. The
  test at `tickets-parts.spec.js:129` picks the gearbox by its label in *Fitted to*,
  so one node less cannot break it.
- Fact: the test passed in my run on all three projects, and in the coder's re-run.
- Assumption: the "Yes" button of the inline Remove confirm
  (`PartsPanel.vue:189`) was re-rendered while Playwright clicked it. The line is
  keyed by the part's id (`PartsPanel.vue:171`), so the confirm state survives a
  re-render. A rare WebKit timing race fits the evidence.
- Recommendation: no action now. If it fails again, open a fix-lane step for it.

## Findings

### CR1-01 (minor) — The impl report has no header block

- **Where:** `docs/steps/S041-s033-e2e-isolation/3-impl-report.md:1`.
- **Problem:** the file starts with `# S041 — Impl report`. `docs/steps/README.md`
  § Header block says every step file starts with the header block (`Step`, `Doc`,
  `Author`, `Date`).
- **Failure scenario:** `tooling/step-check.bat` and `/step stats` read the
  header to find the role, the model and the date. They miss or misreport this
  report.
- **Fix:** add the header block: `Step: S041 — S033's e2e test isolated from the
  seed extruder`, `Doc: impl-report`, `Author: Coder (<model>)`, `Date: 24-10-2026`.

## Manual checks

None. The brief has no manual checks, and the report's `## Manual checks` says
"None".

## Checked and found consistent

- The fix matches the brief. The S033 test makes its own machine through the
  spec's existing `createEquipment` helper (`equipment.spec.js:238`, admin API,
  unit SMTW.MCC1). It adds the No-model part under that machine. The rest of the
  test is unchanged.
- The unused `seedIds` import was removed. No other use of it is left in the spec.
- The new comment at `equipment.spec.js:198` says why the test needs its own machine.
- The test names its parent machine with the project name, like the other tests
  in the spec, so the three projects do not collide on one database.
- The final list check (`level=component_unit&q=<name>`, `toHaveCount(1)`) still
  finds one row. The part name carries the project name.
- The brief's grep task is done and reported. I repeated it: no other test in
  `frontend/e2e/` adds a node under a seed node. `labels.spec.js` posts
  equipment at the spare unit. The "Add part" in `tickets-parts.spec.js` is a
  parts-used line, not a node.
- Red, then green: the red run is S035 CR2-01's run (10 failed), which the brief
  names. The coder said they did not re-run the old code. That is acceptable here,
  because the brief names that run as the red result.
- Scope: one test file changed. No app code, no migration, no new helper. The
  "Decisions taken" section lists the one choice (`createEquipment`).
- I read the full diff of `frontend/e2e/equipment.spec.js`, the S033 test and
  `createEquipment` in full, and `PartsPanel.vue` (remove confirm) to judge the flake.
