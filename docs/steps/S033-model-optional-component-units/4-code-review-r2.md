```
Step: S033 — Model optional on component-units
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 24-10-2026
```

# S033 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** All three findings of round 1 are fixed.
The fix round brings in no new fault, and every suite is green. This round has no new findings.

Files re-read in this round, as the fix round lists them:
- `frontend/src/utils/modelPicker.js` (whole file);
- `frontend/src/views/equipment/EquipmentFormModal.vue` (the script part, lines 38-200, and the three `@change` bindings);
- `frontend/tests/modelPicker.test.js` (the `noModelDefaults` cases);
- `backend/tests/test_equipment_api.py` (`TestNoModel::_node` and the two "unchanged inactive" tests);
- `backend/equipment_core.py` (`_check_class_and_type`, lines 318-324).

## Test runs (this review)

| Run | Result |
|---|---|
| `YANTRA_TEST_RUN=s033cr2 tooling/run-tests.bat` | backend 2520 passed, frontend 135 passed, deps 42 passed, tooling 106 passed — ALL SUITES PASSED |
| `npx vite build` (frontend) | built; only the existing chunk-size warning |
| `tooling/run-e2e-tests.bat e2e/equipment.spec.js e2e/screens.spec.js` | 60 passed, all three projects. These are the targeted specs: the fix round changed the equipment form and no shared frontend code. |

## Round 1 findings

| ID | Status | Check |
|---|---|---|
| CR1-01 (minor) | Fixed | See below. |
| CR1-02 (nit) | Fixed | `test_an_unchanged_inactive_type_is_kept` creates a node with a type, deactivates the type, then saves with the same `class_id` and `type_id`. It expects 200 and the same `type_id`. It mirrors the class test beside it. |
| CR1-03 (nit) | Fixed | The comment at `equipment_core.py:321` says why the call is made and that it never returns `None` there. |

### CR1-01 in detail

- **Helper.** `noModelDefaults` is pure and sits beside `noModelClassChoices`, as suggested. It
  gives the same results as the old handler code for every input:
  - a class filter wins; else the node's class; else `""`;
  - the type is kept only when the chosen class equals the node's class (Decision 4);
  - on create, `currentClassId` is `null`, so `"" === null` is false and the type is `""`;
  - a node without a type gives `""` through `?? ""`.
- **Handler.** `onModelChange` now only assigns the helper's result. It still returns early
  unless *No model* is picked.
- **Tests.** The five vitest cases cover the four inputs named in round 1, plus a node without a
  type. Each case asserts the whole `{ class_id, type_id }` result.
- **Red, then green.** The report gives the red result: with the condition set to `true`, the
  first case fails with the exact diff. This satisfies the coder's rule.
- **`onClassChange` and `onLevelChange` without tests: accepted.** Round 1 asked only for the
  prefill to move into a tested helper, and named the prefill condition as the likely regression.
  - `onClassChange` is one unconditional assignment (`type_id = ""`).
  - `onLevelChange` has one condition (*No model* and a level other than component-unit).
  - A helper for either would be a one-line wrapper, which is over-engineering on its own.
  - The backend still refuses a wrong body in both cases. A type of another class gives "Pick a
    type of the new class, or No type". *No model* on a component gives "Pick a model". So a
    regression there shows as a clear message, never as bad data.

### CR1-02: no red result

The report states the reason: the test covers behaviour that was already correct, and no code
changed for it. A reason is given, so this is not a finding.

## Fix round diff: new faults

None found.
- The default parameters of `noModelDefaults` handle a missing argument object and `undefined`
  values. `NO_CONTEXT` and `openCreatePart` both pass `null` for the three current ids.
- `Object.assign` on `form.value` sets only `class_id` and `type_id`, as the old code did.
- No user-visible text changed in this round.

## Nits

None.

## Checked and found consistent

- Each fixed finding matches its entry in the impl report's *Fix rounds › Round 1*.
- The impl report's test table matches this review's runs (2520 / 135 / 42 / 106; e2e 60 of 60).
- The fix round touched only the five files it lists. It changed no behaviour, as it says.
- The impl report's *Fix rounds* section follows scope A.

## Manual browser check for the user

None required by the brief. The optional check of round 1 stays optional: on a phone, add a part
to a machine with *No model*, then edit it and pick a model again. Check that the history shows
the *model*, *class* and *type* lines.
