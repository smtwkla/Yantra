```
Step: S044 — Property overrides on equipment items
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 25-10-2026
```

**Verdict: no `blocker` or `major` finding is open.** Both round 1 findings are fixed. The fix round brings in one nit.

This is a verify round (round 2 rule). I read the fix round in `3-impl-report.md` (§ Fix rounds › Round 1) and its diff: `git diff -w --ignore-cr-at-eol refs/steps/S046 refs/steps/S044 -- frontend/src/views/masters/PropertiesPanel.vue frontend/src/utils/equipmentLabels.js frontend/tests/equipmentLabels.test.js`. I re-read `equipmentLabels.js` in full (`secondSide` and every case of `describeEvent`), the unit block of `PropertiesPanel.vue`, the `describeEvent` cases of `equipmentLabels.test.js`, and `UNIT_FIXED` in `backend/properties_core.py`. I did not re-read the rest of the step.

## Tests run

- **Frontend** (`YANTRA_TEST_RUN=s044cr2 tooling/run-frontend-tests.bat`): **PASSED, 170 passed** in 16 s. This is round 1's 169 plus the new CR1-02 case.
- **Build, backend and browser tests:** not run, as the orchestrator asked. The round changes no backend code. The coder's run: `npx vite build` built (chunk-size warning only); `masters.spec.js` and `equipment.spec.js` on the three projects, 144 passed, 0 failed. These are the right targeted specs: the round changed the Masters property dialog and the equipment history line, and no shared frontend code.

## Round 1 findings

| ID | Severity | Status |
|---|---|---|
| CR1-01 | minor | Fixed |
| CR1-02 | nit | Fixed |

- **CR1-01: fixed.** `PropertiesPanel.vue:220` now reads "This property has values, so its unit is fixed."
  - It says the same thing as the backend's `UNIT_FIXED` ("The unit cannot be changed: the property has values. …"), and it now covers the items' own values.
  - It follows scope B: one short plain line that says what the user sees and why.
  - No test asserted the old text. The report says why it adds none (the state needs a seeded value, and the change is text only). I accept that for a help line.
- **CR1-02: fixed.** `secondSide` takes the start that both sides share and cuts it back to its last ": ".
  - **Red, then green:** the report gives the red result (the new side lost "Power: ") and the green one. The new test asserts "Property: Power: rated: 7.5 kW → 5.5 kW".
  - **Every earlier history text holds.** Only `meter_limits` and `property` call `secondSide`; the other event kinds are unchanged. I traced the meter texts:
    - "Oil temperature: 10–60 °C" → "Oil temperature: up to 55 °C" gives "up to 55 °C", as before (the existing test is green).
    - "Oil temperature" (no limits) → "Oil temperature: up to 55 °C": the shared start has no ": ", so the whole new side shows, as before.
    - "Oil temperature: 10–60 °C" → "Oil temperature": the shared start is "Oil temperature" with no ": ", so the whole new side shows, as before.
  - **A name with ": " on either side:** a name with ": " on both sides stays whole (tested). If the name changed between the two sides, the shared start stops inside the name, so the new side keeps the whole name.
  - **A shared start that runs into the value:** "Power: rated: 7 kW" → "Power: rated: 75 kW" gives "75 kW", not "5 kW" (tested).
  - **One side empty:** an empty old side gives a shared start of 0, so the whole new side shows. An empty new side gives "". Neither throws.
  - **Both sides equal:** "A: 1" → "A: 1" gives "1". The backend writes no event for an unchanged value, so this case does not show.

## Findings

No `blocker`, `major` or `minor` finding.

## Nits

- **CR2-01** (nit) `frontend/src/utils/equipmentLabels.js:57-61` (`secondSide`): a text or option value that holds ": " now loses its own shared start on the new side. For example, "Bearing: DE: 6205" → "Bearing: DE: 6206" reads "Property: Bearing: DE: 6205 → 6206". Round 1's first-": " cut showed "DE: 6206". The old side shows the dropped part, and the stored texts are complete, so this is cosmetic. If it matters, refuse ": " in property names and go back to the first-": " cut, or show the property's new side in full.

## Manual checks

The fix round adds no manual check. **Nothing is left for the user's manual browser check.**

## Checked and found consistent

- The fix round's report section follows scope A. Its `Docs updated: none` is right: the round changes one help line and one display helper, and no migration, secret, role or module behaviour.
- The comments on `secondSide` and on the `property` case say why, and the file header names S044.
- The data-type help line above (line 213, "has options or values") still agrees with the backend.
- Files re-read: `frontend/src/utils/equipmentLabels.js`, `frontend/src/views/masters/PropertiesPanel.vue` (unit block), `frontend/tests/equipmentLabels.test.js` (`describeEvent` block), `backend/properties_core.py` (`UNIT_FIXED`).
