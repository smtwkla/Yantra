```
Step: S038 — Meters on models and equipment
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 24-10-2026
```

# S038 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** CR1-02, CR1-03 and
CR1-04 are fixed. CR1-01 stays open for the user at gate B. This round has
2 minor findings and 2 nits. All of them are about the fix round's tests and
comments, not its behaviour.

Re-read in this round: `frontend/src/views/equipment/MetersCard.vue` (in full),
the four S038 tests in `frontend/e2e/equipment.spec.js` (lines 253–368),
`backend/masters.py:870-892`, the changed lines in
`backend/tests/test_meters_api.py` and `backend/tests/test_models_api.py`,
decision 7 and the "Fix rounds" section of `3-impl-report.md`, and the brief's
§ 1.2 and § 1.3. No snapshot of round 1 exists under `refs/steps/`, so I read
these files as they are now, not as a diff against round 1.

## Tests run

Run name `s038cr2`.

| Run | Result |
|---|---|
| `tooling/run-tests.bat` | ALL SUITES PASSED: backend 2713 passed (163 s), frontend 149, deps 42, tooling 115 |
| `npx vite build` (frontend) | built in 4.14 s; the usual chunk-size warning only |
| `tooling/run-e2e-tests.bat e2e/equipment.spec.js e2e/masters.spec.js e2e/screens.spec.js` | 122 passed, 1 failed, in 5.1 min (6 lanes) |
| `E2E_LANES=1 tooling/run-e2e-tests.bat e2e/masters.spec.js:62` (the failed test alone) | 3 passed (Pixel 7, iPhone 14, desktop) |

Why these specs: the fix round changed `MetersCard.vue` (the equipment page)
and a Masters message, so `equipment.spec.js` and `masters.spec.js` run.
`screens.spec.js` runs with every targeted run. The fix round changed no
shared frontend code, so the full suite is not needed.

The one failure is a flake outside S038. The failed test is
`[phone-chromium] masters.spec.js:62 › engineer: a deactivated mode is hidden
unless Show inactive, and comes back on reactivate` (failure modes, S016). After
the click on *Reactivate*, the dialog stayed open and still offered
*Reactivate*. The test passes alone on all three projects. Neither S037 nor
S038 changes the failure-code screens. A likely cause is that the test clicks
*Reactivate* before the dialog has finished opening (it does not call
`openDialog` first), on a loaded machine. I raise no finding against S038 for
it. The orchestrator may want to note it for the tidy-up step.

## Findings of round 1

| ID | Severity | Status |
|---|---|---|
| CR1-01 | minor | Open: held for the user at gate B (decision 3 as built; the v30 comment and the `schema.md` row then name the second delete) |
| CR1-02 | minor | Fixed (see below) |
| CR1-03 | nit | Fixed (see below) |
| CR1-04 | nit | Fixed (see below) |

- **CR1-02.** `MetersCard.vue:44` now watches
  `[() => props.node.id, () => props.node.model_id]`. Vue compares each source
  value, so a `load()` that replaces `node` with the same id and model does
  not run the callback. The comment on lines 41–43 says why. The new e2e check
  (`equipment.spec.js:317-324`) counts `GET /api/equipment/<id>/meters` from
  just before the save until the History card shows the new line. The History
  card reads `node.events`, which the same `load()` sets, so at that point the
  old watch would already have sent its request. The report gives the red
  result: "Expected length: 0, Received length: 1".
- **CR1-03.** A model meter has no *Remove* button (`MetersCard.vue:96`).
  Editors see the brief's help line under it (`MetersCard.vue:102-104`), with
  the model's label. Operators do not see it. The inline "Close" branch is
  gone. The brief's § 1.3 gives the help words but not where they show, so
  this is within the brief, and decision 7 now says so. The 409 in
  `backend/meters.py:154` keeps the same words for a direct API call.
- **CR1-04.** `backend/masters.py:890` now says "This meter type is inactive.
  Pick another meter type." This follows scope B: what is wrong and what to
  do. `test_meters_api.py:135` and `test_models_api.py:348` assert the new text.

## Findings

### CR2-01 (minor) — The fix round did not run `screens.spec.js`

`docs/steps/S038-meters-on-models-equipment/3-impl-report.md:179-181`.

- **Problem.** The fix round changed a screen (`MetersCard.vue`). The rule in
  `.claude/CLAUDE.md` (Browser tests) is the targeted specs **plus**
  `screens.spec.js`. The report ran `equipment.spec.js` and `masters.spec.js`
  only, and says `screens.spec.js` "was not needed".
- **Failure scenario.** A fix that breaks the equipment page's first render
  for a role the targeted tests do not use (for example the storekeeper)
  passes the fix round's run. `screens.spec.js` opens every route as every
  role, and would catch it.
- **Suggested fix.** No re-run is needed: this round ran `screens.spec.js`,
  and it passed. In later fix rounds, add `e2e/screens.spec.js` to every
  targeted run.

### CR2-02 (minor) — The changed tests of CR1-03 and CR1-04 carry no red result

`docs/steps/S038-meters-on-models-equipment/3-impl-report.md:170-171`.

- **Problem.** The coder's *Red, then green* rule asks for a failing run
  without the fix for each new or changed test of a fixed fault. CR1-02 gives
  one. CR1-03 changes `equipment.spec.js:346-350` (no *Remove* on the model
  meter, and the help line). CR1-04 changes two backend assertions. Neither
  gives a red result or a reason for its absence.
- **Failure scenario.** A test that passes with and without the fix proves
  nothing. For example, if `getByRole("button", { name: "Remove" })` had not
  matched the old button, the `toHaveCount(0)` check would pass on the old
  code too. (I read the old card in round 1; the old button was a real
  "Remove" button, so the check is sound. The report should say so itself.)
- **Suggested fix.** In the next report section, give the red result of each
  changed test, or one line on why it is not needed. For example: "the
  assertion names the new text, which the old code did not return".

## Nits

- **CR2-03** (nit) `frontend/src/views/equipment/MetersCard.vue:24`: the comment
  "the meter type whose Remove asks first, or tells why not" is stale, because
  the "tells why not" branch is gone. Drop the last four words.
- **CR2-04** (nit) `frontend/e2e/equipment.spec.js:325`: this line repeats the
  History assertion of line 323. Delete line 325.

## Checked and found consistent

- The watch still resets the card on a real change. A model change on the
  node changes `model_id`, so the card blanks, clears an open confirmation and
  fetches the list again (§ 1.6).
- A model meter with a gauge keeps *Set limits*. A model meter of another
  kind now shows no button, so the `ms-auto` span is empty, and the layout
  does not change.
- The confirmation (*Remove* / *Keep*, the brief's text) still shows only for
  an own meter, and the `remove()` request is unchanged.
- The operator test (`equipment.spec.js:359-368`) still asserts no buttons in
  the card. The help line is shown only to editors, so the operator sees no
  instruction that names a screen they cannot change.
- The help line and the backend 409 use the same words and the same model
  label (`model_label`, maker and designation).
- The new message of CR1-04 shows only on a race, as round 1 said: the select
  offers active types only.
- Decision 7 in the report now matches the code.
- The fix round changed no migration, no schema, and no doc in the docs list,
  so the docs pass of round 1 still holds.

## Manual browser check (user)

None is required: the brief has no real-device check, and its two important
checks are automated. Optional, at gate B: on a phone, open a press's page,
save a limit, and check that the Meters card does not flash "Loading…" after
the save (CR1-02).
