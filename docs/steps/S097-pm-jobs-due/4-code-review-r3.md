```
Step: S097 — PM jobs come due
Doc: code-review r3
Author: Code reviewer (Opus 5.5)
Date: 02-11-2026
```

# S097 — code review, round 3 (verify fix round 1)

**Verdict: no `blocker` or `major` finding is open.** Findings: 0 blocker, 0 major, 0 minor, 0 nits. The three
round 2 findings are fixed, and the fix round's diff brings in no new fault.

**Scope of the read.** The fix round's diff, `diff S097 --from-round 2`: `frontend/src/utils/pmLabels.js`,
`frontend/tests/pmLabels.test.js`, `frontend/e2e/pm-jobs.spec.js`. Also re-read: `formatReading` in
`frontend/src/utils/meterLabels.js` (to compare the new helper), and the impl report's round 2 § Tests and
`## Fix round 1`. Nothing else of the step was re-read.

**Tests (my run).** `YANTRA_TEST_RUN=s097cr3 tooling\run-frontend-tests.bat tests/pmLabels.test.js`: **PASSED**,
26 passed (log `scratch/frontend-tests-s097cr3.log`). The fix round changed only frontend files, all inside the
frontend suite's folder and one spec, so no full run is due. No browser run: no finding of mine needs one.

**The coder's browser run** is the right targeted run for the change: `pm-jobs.spec.js`, `pm-plans.spec.js` and
`screens.spec.js`, 38 passed, 1 skipped (a phone-only test on desktop). The build check (`npx vite build`) is
recorded as built.

## Round 2 findings

| Finding | Status | Checked |
|---|---|---|
| CR2-01 minor | **Fixed** | `pmLabels.dueValueText` formats with `toLocaleString("en-IN", { maximumFractionDigits: meterType.decimals })` and adds the unit, so a due point shows only the places it has ("at 1,250 h"), as `pm_plans_core.interval_number` does for the interval. `dueText` uses it, so `nextDueText` does too. `meterNowText` keeps `formatReading`, so the readings stay padded ("Run hours now 1,260.0 h"). The three vitest lines and `pm-jobs.spec.js:122` expect the unpadded form. The red result is given: 2 failed without the fix. |
| CR2-02 nit | **Fixed** | `pm-jobs.spec.js:92` reads `due.getByTestId("pm-open-job").locator(".badge")`. |
| CR2-03 nit | **Fixed** | The round 2 § Tests now names `improvement-register.spec.js:83` (S076) earlier in lane 5 as the cause, and notes the correction. |

## Checked and found consistent

- **The new helper's edge cases.** `dueText` calls it only with a `dueMeter` and a `meterType`, so a null due
  meter still gives no meter part. A due point has only a counter meter, so the `yes_no` branch of
  `formatReading` is not needed. The helper drops the unit when the type has none, as `formatReading` would not;
  that is safer, not a change for any counter type in use.
- **No second copy.** The helper is private to `pmLabels.js` and has one caller; it repeats only the
  `toLocaleString` call, with different options from `formatReading`.
- **The report's history.** The round 2 sections (§ 3 and § 4) still describe the padded form as the departure;
  the fix round records that it was reversed. That is the report's round history, not a fault.
- **Docs pass.** `## Docs updated (fix round 1)` says none, with a reason; `Plan.MD` § 4.3 gives no format for the
  due value, so nothing went stale.

## Manual checks

None for the user. Every important check of the brief stays automated and green in the coder's runs. The brief
has no real-device check.

## Feedback

- none
