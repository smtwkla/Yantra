Step: S100 — Three tests that depend on what other tests left behind
Doc: code-review r1
Author: code reviewer (Opus)
Date: 02-11-2026

# S100 — Code review, round 1

**Verdict: no blocker or major finding is open.** One minor finding and one nit. The unit suites are
green (backend 5165, frontend 451, tooling 239 passed). The three fixes each make their test independent of rows that other tests
leave, as the brief asks. Fixes 1 and 3 check as much as before. Fix 2 checks less than before: see
CR1-01.

## Findings

### CR1-01 (minor) `frontend/e2e/improvements.spec.js:121-124`: the Closed check also passes when the Closed list fails to load

- **Problem.** The old line `getByText("No closed improvements yet.")` proved two things: the Closed
  list loaded, and this test's improvement was not in it. The new `expect(row).toHaveCount(0)`
  proves only the second. In `ImprovementsView.vue:115-126` a load error shows the
  `alert-danger` box and no list, so `row` also has count 0 then. The old rows stay on screen while
  the new page loads (`loading && page`, line 114), so a slow load does not pass the check early.
  Only a failed load does.
- **Failure scenario.** A later change breaks `GET /api/improvements?state=closed` (a 500, or a
  400 for the `closed` value). The Improvements tab shows the error box under *Closed improvements*. S068's test stays green. No other browser test opens this list: `me.spec.js:79`
  is the Me screen, and `improvement-register.spec.js:85` is the printed register. So the Closed
  list on the Improvements tab is no longer checked anywhere in the browser tests.
- **Fix.** After `toHaveCount(0)`, check that the Closed list rendered, whatever other tests left:
  `await expect(page.getByText("No closed improvements yet.").or(page.locator(".list-group-item").first())).toBeVisible();`
  The `.or` passes on the empty text or on another test's closed row, and fails on the error box.
  You can also check `page.locator(".alert-danger")` has count 0.

## Nits

- **CR1-02** (nit) `docs/steps/S100-order-dependent-tests/3-impl-report.md` § Red evidence: you
  could have shown bug 2 red cheaply. Your one-lane run of `improvement-register.spec.js` and
  `improvements.spec.js` puts S076's drop before S068's test, so the old assertion fails there. Run it
  once with the old line and record the result. The brief allows the report as written.

## Tests run (`YANTRA_TEST_RUN=s100cr1`)

- `tooling/run-tests.bat`: ALL SUITES PASSED: backend 5165 passed (158 s), frontend 451 passed, tooling 239 passed.
- No browser run. The coder's targeted runs name the right specs: `improvements.spec.js`,
  `labels.spec.js`, the one-lane order run with `improvement-register.spec.js`, and
  `labels.spec.js` on `desktop-chromium` (the test is `@device` and skips on a phone). The report
  has no run of `screens.spec.js`. That does not matter, because no screen changed. CR1-01 needs
  no run to show: it follows from the view's template.
- No schema docs check: the diff touches neither `backend/local_db.py` nor `docs/schema/`.

## Each fix against the brief

1. **S092, words in any order** (`test_equipment_api.py:1342`). The search is scoped to the test's
   new unit (`unit_id=unit["id"]`), so the `[137]` hit came from the test's own node: its
   generated code held `999`. The word `nomatch` cannot occur in a generated code or in the names
   `250T press` and `Other`. The two positive asserts (both word orders, the tab and the extra
   spaces) are unchanged. So the test still checks "every word must match, in any order". The red
   result is shown (`assert [3] == []` with a node named `… press 999`).
2. **S068, the Unit filter and Closed** (`improvements.spec.js:97-129`). The Unit filter part and
   its "No improvements match these filters." check are unchanged. The added
   `option:checked` line proves the State box shows *Closed improvements*. The row check
   `toHaveCount(0)` waits for the closed page to replace the open one, so it does not pass early.
   It does pass on a failed load (CR1-01). The title is changed to "…Closed leaves it out", as the
   brief asks.
3. **Labels from the list's ticks** (`labels.spec.js:59`). The list opens with
   `?q=<extruder code>`, the same way `equipment.spec.js:164` opens it, so the extruder is on page 1.
   The test still ticks the row in the list, prints with *Print labels (1)*, and checks the one
   label's code. `getByLabel("Select EXT… for labels")` does not match a longer code such as
   `…0010`, because " for labels" follows the code. The `@device` tag and the phone skip are
   unchanged, and they are right (the ticks are hidden on a phone).
4. **S099 CR2-01, `pm-verify.spec.js:12-14`**. `test.use({ serviceWorkers: "block" })` at the file
   level is the same form as in `me.spec.js:14`, `readings.spec.js:22` and `tickets-work.spec.js:16`.
   The reason is in the comment. No pm-verify test needs a push alert or a service worker, so
   blocking it for the whole file takes nothing away from them.

## Manual checks

None. The brief has no check on a real device, and the report says so.

## Checked and found consistent

- Scope: three test files and the one S099 line. No app code changed. No departure is unreported:
  the one addition (the `option:checked` line) is in "Decisions taken".
- Track `fix`: tests only, no migration, no RBAC, no screen.
- Docs: `## Docs updated` says none. That is right: no row of § Docs to keep current is due.
- No skip or known-fault mark was added to hide a fault.
- Writing style: the report and the new code comment are plain. No screen text changed.

## Feedback

- waste: I wrote the review before the unit run ended and filled in its result after, because
  the Bash tool cannot wait on a background run except by a polling script (one extra script, 3 min)
