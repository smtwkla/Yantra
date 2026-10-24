```
Step: S045 — The known flaky tests made steady
Doc: code review r1
Author: Code reviewer (Opus)
Date: 25-10-2026
```

# S045 — Code review, round 1

**Verdict: three `major` findings are open.** The fixes for #2 and #3 do not
change what the tests do, and the causes the report gives for them do not match
the code. The guard (#6) makes every e2e run on this PC red. Fixes #1, #4 and #5
are sound. Also: one `minor` finding and three nits.

## Scope and test runs

- **Diff reviewed:** the working tree against `refs/steps/S040`, limited to the
  six files of the report (`git diff -w --ignore-cr-at-eol`). The seed rename in
  `local_db.py`, the S044 brief and the skill edits are out of scope.
- **App code:** none changed by this step. This is right for the fix lane.

| Run | Result |
|---|---|
| `YANTRA_TEST_RUN=s045cr1 tooling/run-tests.bat` | ALL SUITES PASSED: backend 2964, frontend 168, deps 42, tooling 115 |
| `npx vite build` | not run: no app code changed |
| e2e | not re-run (standing rule). The coder's full run: 290 passed, 147 failed (all phone-webkit, at the guard), 4 skipped. The full suite is the right choice, because `e2e/support/test.js` changed. |
| My own check (scratchpad script, WebKit) | Bootstrap's rule on `:root` gives `scroll-behavior: smooth` on `<html>` and `auto` on an inner `overflow-y: auto` scroller. This is the basis of CR1-01. |

## Findings

### CR1-01 (major) — #2: the smooth-scroll cause does not apply to this screen, so the fix changes nothing

- **Where:** `frontend/e2e/tickets-raise.spec.js:160-164`; report § 1 row 2.
- **Problem:** the report says Bootstrap's `:root { scroll-behavior: smooth }`
  animates each `fill`'s scroll, so the *Save* button moves. That rule sets the
  value on the root element only. `scroll-behavior` is not inherited. The raise
  screen does not scroll the document. It scrolls `main.app-content`, which has
  `overflow-y: auto` (`App.vue:106-108`), inside `.app-shell`
  (`height: 100vh; overflow: hidden`, `App.vue:92-95`). That element's
  `scroll-behavior` is `auto`. I checked this in WebKit: the root element gives
  `smooth` and the inner scroller gives `auto`. The scrolls that the fills cause
  are therefore instant, and nothing animates.
- **Second point:** the new line replaces `scrollIntoViewIfNeeded` (which waits
  for the button to be stable) with an `evaluate` (which does not wait). The
  next line, `saveButton(page).click()`, then runs the same actionability checks
  again: scroll into view, wait until stable, check the hit target. If the button
  was really unstable, the wait has only moved down one line.
- **Failure scenario:** the next full run under load stops at the `click()` on
  line 165 with the same "waiting for element to be stable". The code comment
  then sends the next reader to a cause that does not exist.
- **Fact:** `playwright.config.js` sets no `actionTimeout`, so Playwright's
  default of 0 applies: an action has no time limit of its own. The S039 timeout
  was therefore the test's 60 s limit. The element stayed "not stable" for
  close to a minute, while the test normally takes 1–2 s. A scroll animation
  takes under a second, so it cannot explain the timeout.
- **Fix:**
  1. Remove the smooth-scroll comment, and either revert the line or keep it
     with a comment that names no cause.
  2. In the report, mark #2 as **not fixed**, with the cause unknown.
  3. Record the assumption that fits #2 and #3 (CR1-02): WebKit draws no frames
     for a long time under a 6-lane load. Playwright's "stable" check needs
     frames (`requestAnimationFrame`), so it waits.
  4. Next time it fails, read the action log in the retained trace
     (`trace: retain-on-failure` is on) before writing another fix.

### CR1-02 (major) — #3: the "fresh" locator is the same locator, so the fix is a no-op

- **Where:** `frontend/e2e/tickets-parts.spec.js:167-170`; report § 1 row 3.
- **Problem:** `line` is `partsCard(page).locator("li", { hasText: description })`
  (line 151). The new `yes` is
  `partsCard(page).locator("li", { hasText: description }).getByRole("button", …)`.
  This is the same selector chain as the old `line.getByRole("button", …)`.
  Playwright locators are lazy: they find the element again on every attempt,
  and `click()` already finds it again after a "detached" retry. `click()` also
  waits for visible, stable and enabled, so the added `toBeVisible()` adds no
  new condition. The step's behaviour is unchanged.
- **The stated cause:** the code does not support it. The report says "the
  ticket reloads after each save, so the element the test held could be
  replaced". But:
  - each line is keyed by the part's id (`PartsPanel.vue:171`);
  - `onSaved` assigns the new ticket in place (`TicketDetailView.vue:178-179`);
  - the panel is not mounted again.
  Vue therefore patches the same `<li>`, and the confirm block stays (the
  S041 reviewer reached the same conclusion). The S041 failure was a timeout
  (as in CR1-01, the 60 s test limit), so the click failed to complete for
  close to a minute. One re-render cannot explain that.
- **Failure scenario:** the flake comes back in a later full run on
  phone-webkit. The step is recorded as having fixed it, so the next agent trusts
  a false comment ("the line re-renders").
- **Fix:** revert the change, or keep it with a neutral comment. Mark #3 as not
  fixed in the report, with the assumption from CR1-01 point 3.

### CR1-03 (major) — #6: the guard fails every phone-webkit test, so every e2e run on this PC is red

- **Where:** `frontend/e2e/support/test.js:11-27`; report § 5, decision 3.
- **Problem:** at 125 % scale the guard **fails** each of the 147 phone-webkit
  tests. The brief's § Files expected a run "with phone-webkit named as skipped
  by the guard". The report states that the guard fails tests. It does not say
  that this departs from the brief's "skipped".
- **Effect:** the step workflow treats a red e2e run as a `blocker`. From now
  on, every coder and reviewer run of a WebKit-touching spec on this PC is red:
  - Either every step stops at a `blocker` the step did not cause.
  - Or the agents learn to discount phone-webkit red. A real WebKit fault then
    shows in the same colour as the guard and is waved through. That is how the
    guard would hide real faults.
- **Second effect:** the PC loses all WebKit coverage. Before S045, phone-webkit
  ran at 312 px and passed most tests. The S040 CR r2 failure was the one known
  test that the narrow window broke. The step chose this trade-off. The report
  should state it, and the user should decide it.
- **Fix (recommended):** in the fixture, call
  `testInfo.skip(true, "<message>")` instead of throwing. The run is then green
  with 147 skipped, and the reason appears on each skipped test. Name the skip
  count in every run's report. **Alternative:** fail one test (for example the
  first phone-webkit test of `screens.spec.js`) and skip the rest. This keeps one
  red line as a reminder but blocks every step the same way. In either case,
  the coder states the choice, and it goes to the user at the gate.

### CR1-04 (minor) — the guard was never seen to pass, so it may fail on a 100 % host too

- **Where:** `frontend/e2e/support/test.js:16-18`; report § 6.
- **Problem:** the coder could run phone-webkit only at 125 %. On a 100 % host,
  nobody has checked that `innerWidth` on the `width=device-width` page equals
  exactly 390. The 312 px figure is 390 / 1.25, which suggests it does. This
  is an assumption, not a run.
- **Failure scenario:** the user runs the full suite before a release, on a
  host at 100 %. If WebKit reports 389 or 391 there (rounding, or a scrollbar),
  the guard fails all 147 phone-webkit tests. The guard was meant to prevent
  exactly this kind of false red.
- **Fix:** before the step is committed, run one phone-webkit test on a host at
  100 % (for example `screens.spec.js`, `E2E_LANES=1`). Add it to the report's
  `## Manual checks` as an unticked box, not only as a note.

## Nits

- **CR1-05** (nit) `frontend/e2e/support/test.js:20-21`: the message says what
  happened and what to do, but not why. "Sign in again" is also unclear (sign
  in to what?). Suggested text: "The phone-webkit window is 312 px wide, not
  390, because Windows display scale is above 100 %. Set it to 100 %, then sign
  out of Windows and sign in again."
- **CR1-06** (nit) `frontend/e2e/masters.spec.js:69`: `expectDialogFits` on line 67
  already calls `openDialog`, so the first `openDialog` only gets the locator.
  Use `page.locator(".modal.show .modal-dialog")`, or say so in the comment. The
  `openDialog` before *Reactivate* (line 79) is the real fix and is right.
- **CR1-07** (nit) `docs/steps/S045-flaky-tests/3-impl-report.md:5`: the header carries
  `Track: fix`. README § Header block puts `Track` in the brief only.

## The points the orchestrator asked about

- **#2 cause:** wrong for this screen (CR1-01).
- **#3 cause:** not supported by the code, and the fix is a no-op (CR1-02).
- **#6 message:** clear about what to do, missing the why (CR1-05).
- **#6 effect:** as built, it does not hide faults in a single run, but it
  makes phone-webkit red by design. That trains the workflow to ignore WebKit
  red (CR1-03).
- **#4 approach (planned date read from the API):** sound.
  - The test filters by `state=overdue` and `q` (the list supports `q`,
    `tickets.py:522`), and keeps the one row whose description matches exactly.
  - It checks that the date is before today, so the Overdue meaning is still
    tested.
  - The badge and the line are both expected from the API's date, which is the
    date the screen shows.
  - The red run with `istDay(-2)` shows the old failure mode.
- **`readings.spec.js:362`:** do not copy the #2 change there. The readings
  sheet also scrolls inside `main.app-content`, so smooth scrolling does not
  apply to it either. The copied change would carry the same wrong cause.
  Leaving it alone was right.

## Checked and found consistent

- **#5 (`test_alerts.py:519-521`):** the test server reads `Content-Length`
  bytes before it answers 307. This fits the WinError 10053 mechanism, and the
  test still asserts `TooManyRedirects`. The red result is given: without the
  fix, 6 of 20 runs failed; with it, 20 of 20 passed.
- **#1 (`masters.spec.js:62`):** clicking *Reactivate* inside the dialog after
  `openDialog` matches the S038 CR r2 observation (the dialog stayed open and
  still offered *Reactivate*). It follows the S024 open-dialog wait.
- **The guard's mechanics:**
  - it runs only for WebKit projects with a viewport width;
  - it runs before `consoleWatch`, so its `setContent` page raises no console
    problem;
  - each test's `page.goto` replaces that page;
  - the one `goBack` in the specs (`me.spec.js:106`) comes after two in-app
    navigations.
- **Scope:** only test files and step files changed. No app code. The step
  stayed in the fix lane.
- **Docs pass:** "None" is right. A test-only change makes no listed doc wrong.
- **Manual checks:** the brief has none. The report's note on a 100 % host
  belongs as a box (CR1-04).

## Manual browser checks for the user

- [ ] Run one phone-webkit spec (for example `e2e/screens.spec.js`,
      `E2E_LANES=1`) on a host at 100 % display scale. Check that the guard lets
      it through (CR1-04).
- [ ] Decide CR1-03: when the window is narrow, should the guard skip
      phone-webkit (recommended) or fail it?
