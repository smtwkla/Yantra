```
Step: S037 — Meters master
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 24-10-2026
```

# S037 — Meters master: code review, round 2

**Verdict: no `blocker` or `major` finding is open.** All six findings of
round 1 are fixed. The fix round brings in no new fault. This round has no
new findings.

## Test runs (this review, `YANTRA_TEST_RUN=s037cr2`)

| Run | Result |
|---|---|
| `tooling/run-tests.bat` | All four suites PASSED: backend 2596 passed (126 s), frontend 143, deps 42, tooling 106 |
| `npx vite build` in `frontend/` | Built in 3.99 s; only the usual chunk-size warning |
| `tooling/run-e2e-tests.bat e2e/masters.spec.js` | **48 passed** (1.6 min, 6 lanes, all three projects) |

`masters.spec.js` is the targeted spec: the fix round changed only help text
in `MeterTypesPanel.vue`. It changed no route and no shared frontend code, so
`screens.spec.js` and the full suite are not needed.

## Round 1 findings

| ID | Severity | Status | Checked |
|---|---|---|---|
| CR1-01 | minor | Fixed | `masters_core.py:102`: `optional_text_parser` has `collapse=False`, which calls `_collapsed` in place of `strip()`. `:336`: `_parse_meter_unit = optional_text_parser("Unit", METER_UNIT_MAX, collapse=True)`, and the copy is gone. The type check still comes before `_collapsed`, so `_collapsed`'s `""` for a non-string is never reached. The other callers keep the default. |
| CR1-02 | minor | Fixed | `docs/schema.md:39` names the stored values `counter` / `gauge` / `amount` (*Amount per period*) / `yes_no` and `yes` / `no`, and "NULL exactly when the kind is `yes_no`". |
| CR1-03 | nit | Fixed | `conftest.py:168-170`: `SEED_CREATOR` comes first, with the v11-only comment, and the three v11 entries use it. |
| CR1-04 | nit | Fixed | `Maintenance-Philosophy.md:295-304`: Counter, Gauge, Amount per period, Yes / No, the order of the kind radios. |
| CR1-05 | nit | Fixed | `MeterTypesPanel.vue:131`, `:164` use "such as", and so do the quotes in "Decisions taken". |
| CR1-06 | nit | Fixed | `.claude/CLAUDE.md:50`: "`masters` S016/S037". |

**Red, then green (CR1-01).** The fix round gives the red result. With the
collapse branch reduced to `strip()`, the test fails with
`assert 'a   b' == 'a b'`, and it passes with the fix. The three tests of
`TestOptionalTextParser` (`test_masters_core.py:290`) cover both modes, an
empty or null value, a non-text value and the length limit after the
collapse.

The impl report's "Decisions taken" now says "Five small choices", and it
lists five.

## Nits

None.

## Checked and found consistent

- **The fix round's diff:** `masters_core.py`, `test_masters_core.py`,
  `conftest.py`, `MeterTypesPanel.vue`, `docs/schema.md`,
  `docs/Maintenance-Philosophy.md`, `.claude/CLAUDE.md`, and the impl report.
  Each change matches round 1's suggested fix, and nothing else changed.
- **The behaviour is the same:** the unit is still trimmed, inner runs of
  spaces become one space, the limit is 20 characters, and an empty unit
  becomes NULL. The existing `TestMeterType` cases and the API tests pass.
- **Docs pass:** the impl report's `## Docs updated` names the round 1
  changes (CR1-02, CR1-04, CR1-06), and they are in the diff.
- **Manual checks:** the four `[auto]` checks pass in this run. There is
  still no real-device check.
- **Writing style:** the fix round section keeps scope A. The help lines keep
  scope B.

**Files re-read:** `backend/masters_core.py` (lines 60–140, 325–365),
`backend/tests/test_masters_core.py` (290–320), `backend/tests/conftest.py`
(165–192), `frontend/src/views/masters/MeterTypesPanel.vue` (help lines),
`docs/schema.md:39`, `docs/Maintenance-Philosophy.md` § 8, `.claude/CLAUDE.md`
§ SMTW-Review, and `3-impl-report.md` § 4 and § Fix rounds.

## Manual browser check for the user

None is required. The brief has no real-device check. If you want to look
yourself, open Masters › Meter types on a phone. Check that the help lines
scroll in the dialog and that *Save* stays in view.
