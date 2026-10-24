```
Step: S041 — S033's e2e test isolated from the seed extruder
Doc: brief
Author: Planner (Opus)
Date: 24-10-2026
Track: fix
Status: Done (committed 7618839; no checks)
Baseline: e451c33
```

# S041 — S033's e2e test isolated from the seed extruder

**The bug (found by S035 CR2-01, 24-10-2026).** The full e2e suite is red: 10
tests fail. These are `labels.spec.js:69` on all three projects and
`screens.spec.js:69` at `/labels?ids=1&parts=1` for all seven roles on
phone-webkit.

**How to see it.** Run `tooling/run-e2e-tests.bat` (full). The failures appear
when a lane runs `equipment.spec.js` before `labels.spec.js` or `screens.spec.js`
on the same database. Which lane does this depends on how the tests are split.

**The cause.** `frontend/e2e/equipment.spec.js:196`, the S033 test "engineer adds
a component-unit with No model …", adds a part under the **shared seed
extruder** (`seedIds()` → `extruder`). The seed then has 3 nodes, but
`labels.spec.js:78` expects "2 labels on 1 sheet" (extruder + gearbox), and the
`/labels?ids=1&parts=1` screen check expects the same.

The S024 conventions say a test that adds data sets it up for itself, by API.
The S033 test broke that rule. It added its part to a node that other specs
read.

**The fix.** The S033 test first creates its own equipment by API (follow the
helpers `equipment.spec.js` already uses for its own machines, e.g.
`lightMachines` or the API set-up of S029), and adds the No-model part under
that equipment. Nothing else in the test changes. No app code changes.

**Files.** `frontend/e2e/equipment.spec.js` only, plus this step's files.

**The failing test.** The full e2e suite. Red: today's run (S035 CR2-01: 10
failed). Green: the full suite passes, with the S033 test still passing on all
three projects. Also grep `frontend/e2e/` for any other test that adds nodes
under a seed node (`seedIds()` / `seed.extruder` followed by an *Add part* or a
POST of a child), and report each one found. Fix only those that break a
count elsewhere.

## Manual checks

None.

## Review log

None (fix lane).
