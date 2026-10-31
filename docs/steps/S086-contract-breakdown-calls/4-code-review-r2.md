```
Step: S086 — Breakdown calls on the contract
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 31-10-2026
```

# S086 — code review, round 2

**Verdict: no `blocker` or `major` finding is open.** The fix round fixes CR1-02, CR1-03 and CR1-04, and its diff
brings in no new fault. CR1-01 stays open with the user, as the orchestrator decided (it changes behaviour that
the approved brief § 5.6 sets). This round verifies the fix round only.

## Tests run

- `YANTRA_TEST_RUN=s086cr2 tooling/run-backend-tests.bat tests/test_contract_calls_api.py`: PASSED, 27 passed
  (14 s). The new `test_an_inactive_contract_still_lists_its_calls` is among them.
- Browser, targeted, once: `tooling/run-e2e-tests.bat e2e/contracts.spec.js e2e/tickets-work.spec.js` (Normal,
  `YANTRA_TEST_RUN=s086cr2`): exit 0, 85 passed, 1 skipped, 0 failed (86 tests on 4 lanes, 95 s), phone-chromium and the `@device` tests on desktop-chromium. Both changed picker tests (`contracts.spec.js:1015`, `tickets-work.spec.js`) and the new CR1-02 test passed in the set. I ran this set because the coder's targeted run had one red test
  (`contracts.spec.js:1015`, the picker test on the old placeholder) and the coder re-ran it alone only. The two
  specs hold both changed placeholder lines and the new CR1-02 test.
- Not run: the whole unit command and the build. The fix round changed one backend test file, one Vue file's
  condition, one placeholder string and two spec files; no code outside one suite's folder changed. The coder's
  `npx vite build` is clean.
- `grep -rn "Type a name"` over `frontend/` (without `node_modules` and `dist`): three hits, all with the new text
  "Type a name or vendor to filter" (`PersonPicker.vue:56`, `contracts.spec.js:1022`, `tickets-work.spec.js:72`).
  No line with the old text is left.

## Findings

| ID | Severity | Status |
|---|---|---|
| CR1-01 | minor | Open, with the user at gate B (not re-raised) |
| CR1-02 | nit | Fixed |
| CR1-03 | nit | Fixed |
| CR1-04 | nit | Fixed |

No new finding.

## Checked and found consistent

- **CR1-02.** `BreakdownCallsCard.vue:96` now adds `r.call.is_breakdown &&` to the `v-else-if`. The answer sends
  `is_breakdown` (`contracts.py:765`, from `tickets_core.is_breakdown`). The new browser test raises a `degraded`
  ticket (a valid intensity, `tickets_core.INTENSITIES`) on the same covered machine, assigns the vendor's person,
  and asserts that the breakdown row shows "not back in service yet" and the defect row is visible without it.
  The `toBeVisible` check first makes the `not.toContainText` meaningful. The fix round gives the red result
  (with the condition removed, the test fails on the defect row).
- **CR1-03.** The placeholder reads "Type a name or vendor to filter". Both specs that find the box by its
  placeholder use the new text. The text is one plain line (scope B).
- **CR1-04.** The new test covers a machine, makes one call, sets the contract inactive through the API (200), and
  asserts that the call list is still `[ticket id]`. It tests behaviour that already holds, so no red result is
  due; the fix round says so.
- **Docs.** "Docs updated: none" is right: no doc describes the placeholder or the label's condition.

Files re-read: `frontend/src/views/contracts/BreakdownCallsCard.vue` (the changed line), the fix round's diff of
the five files, and the spec helpers the new test uses (`callRow`, `assignByApi`, `callByApi`, `openCallsAs` in
`contracts.spec.js`).

## Manual browser check for the user

None from this round. The brief has no real-device check.

## Feedback

- hindrance: the Bash tool blocks `sleep` before a log read, so waiting for a background browser run took a second
  background `until` loop on its log (one extra call, about 1 min to get right).
