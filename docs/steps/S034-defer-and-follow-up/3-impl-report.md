Step: S034 — Defer, hold and follow-up date
Doc: impl-report
Author: Coder (Sonnet)
Date: 24-10-2026

# S034 — Implementation report

## 1. What was built

All of `1-brief.md`; no amendments exist. Labels and messages changed; no state, move, key, figure or API shape changed.

- The `schedule` move reads **Defer** on a defect and **Put on hold** on a breakdown (button and dialog Save).
- The state badge reads **Deferred** on a defect and **Waiting** on a breakdown. *Overdue* is unchanged.
- The ticket list filter reads **Deferred / Waiting**. `STATE_LABELS.scheduled`, the timeline line and the backend `EVENT_LABELS[SCHEDULED_EVENT]` read **On hold**.
- The date now has a meaning by reason. A production slot gives **Planned for**. The other five reasons give **Check again by**, with a help line. Before a reason is chosen the label is **Date**.
- The header line, the list row and the timeline read "check by DD-MM-YYYY · …" for a check reason. A planned reason keeps "for". Past the date both read *Overdue*.
- The dialog asks for the reason first, then the date. Three buttons, **In 7 days**, **In 14 days** and **In 30 days**, fill the date. The date still opens empty.
- The date messages no longer say "planned date" (§ 1d of the brief).

## 2. How it works

- `ticketLabels.js` holds `PLAN_DATE_KINDS` (all six codes), `planDateKind()`, `planDateLabel()`, `PLAN_DATE_HELP` and `PLAN_QUICK_DAYS`. A private `planDateWord()` gives "for" or "check by" to `planText()` and `planChanges()`. `planLine()` calls `planText()` before the date and is unchanged past it.
- `moveLabel()` and `moveSaveLabel()` return "Put on hold" for `schedule` on a critical ticket. The `MOVE_LABELS` and `SAVE_LABELS` tables hold "Defer".
- `ScheduleFields.vue` shows the select, then the date with its label, the help (check reasons only) and the quick-pick buttons. A pick sets today plus N days in local time, built as the input's `min` is.
- `MoveDialog.vue` changes only the empty-date message ("Choose a date") and its header comment. The title and Save already used `moveLabel()` and `moveSaveLabel()` with the intensity.

## 3. Files touched (13, with the report)

- `backend/tickets_core.py`: the three date messages and `EVENT_LABELS[SCHEDULED_EVENT]` = "On hold".
- `backend/tests/test_ticket_work_api.py`: the four message literals (lines 1020, 1023, 1025, 1079).
- `frontend/src/utils/ticketLabels.js`: labels, filter, new plan-date helpers, `planText()`, `planChanges()`, `stateLabel()`.
- `frontend/src/views/tickets/ScheduleFields.vue`: reason before date, label, help, quick picks, header comment.
- `frontend/src/views/tickets/MoveDialog.vue`: "Choose a date", header comment.
- `frontend/src/views/TicketDetailView.vue`, `frontend/src/views/TicketsView.vue`: header comments only.
- `frontend/tests/ticketLabels.test.js`: updated and new unit tests.
- `frontend/e2e/tickets-work.spec.js`: S019 tests moved to the new words; four new `S034:` tests.
- `docs/steps/device-checks.md`: row 10 (S019) with the new words.
- `docs/Maintenance-Philosophy.md`: a paragraph after the *Deferred corrective maintenance* text.
- `docs/Plan.MD`: § 4.2 *Deferred work* words and an S034 bullet.
- `docs/steps/S034-defer-and-follow-up/3-impl-report.md`: this file.

The brief and `docs/steps/README.md` were already modified in the working tree before I started. I did not touch them.

## 4. Decisions taken

- The new e2e tests are four, one per automated check group of the brief. The first one also asserts that the engineer sees *Defer* and no *Schedule* button, as § 5 asks.
- `PLAN_DATE_KINDS` is an exported table (as `WAITING_REASON_DELAYS` is) and `planDateKind()` returns `null` for an unknown or empty reason. Then `planDateLabel()` gives "Date" and `planDateWord()` gives "for". The unit test lists all six codes.
- In the "In 14 days" e2e test, the expected date is computed from the date input's `min`, as the brief says (BR1-09).
- The timeline "(was …)" part keeps the old plan without its "for" / "check by" word, as before.
- No departure from the brief.

## 5. Not done, deferred or assumed

- Nothing deferred. The out-of-scope list of the brief is untouched.
- I did not run the tooling and deps suites of `run-tests.bat`: no file they test changed.
- I did not set the brief's `Status` line, as instructed. The README index row already reads *Implementing*.
- The `docs/Plan.MD` and `docs/Maintenance-Philosophy.md` edits are my wording of the brief's words; please read them.

## 6. Test results (Linux cloud sandbox)

Environment notes. `tooling/*.bat` cannot run here, so I ran their commands directly.
- I started `dockerd` by hand. The first pulls of `mariadb:11.4` hit a registry rate limit (429); the third try worked.
- Playwright wants Chromium build 1248 but `/opt/pw-browsers` holds 1243. I pointed `PLAYWRIGHT_BROWSERS_PATH` at a private folder of symlinks named 1248 that link to the 1243 builds; nothing in the repo or in `/opt` changed.
- WebKit is not installed, so the `phone-webkit` project did **not** run. I ran `desktop-chromium` and `phone-chromium`.
- `run_lanes.py` passes arguments through a shell: `-g "S034|S019"` broke at the `|`. I used `-g S034`.

Results (real numbers):
- Backend, `YANTRA_TEST_RUN=s034c1`, full suite (`pytest -n 8 --dist loadscope`): **2325 passed** in 25 s. The two targeted files first: 415 passed.
- Frontend vitest, full: **122 passed**, 14 files. `npx vite build`: built without errors.
- E2E, `E2E_LANES=4`, `tickets-work.spec.js` + `screens.spec.js`, projects `desktop-chromium` and `phone-chromium`: **58 passed** in 1.7 min. `screens.spec.js` ran because it is the standing screen check. Shared frontend code (`FormModal`, `api.js`, router, auth store, `e2e/support/`) was not changed, so the full suite was not needed.
- Not run: the deps and tooling suites (see § 5), `phone-webkit`.
- Red-then-green does not apply: this is not a fix round.

## Manual checks

- [auto] On a defect the button reads *Defer*; the badge reads *Deferred* and the timeline line *On hold* — `frontend/e2e/tickets-work.spec.js::S034: a defect reads Defer; the badge reads Deferred and the timeline On hold; the engineer sees Defer too`
- [auto] On a breakdown in progress the button reads *Put on hold*; with *Waiting for parts* the date is *Check again by* with the help; the header line reads "check by …" — `frontend/e2e/tickets-work.spec.js::S034: a breakdown reads Put on hold; waiting for parts asks Check again by, with help, and the header says check by`
- [auto] With *Waiting for a production slot* the date is *Planned for*; the reason select is above the date — `frontend/e2e/tickets-work.spec.js::S034: a production slot labels the date Planned for, without the help; the reason is above the date`
- [auto] *In 14 days* fills the date (input `min` plus 14 days) and the save succeeds; the list filter reads *Deferred / Waiting* and lists the ticket — `frontend/e2e/tickets-work.spec.js::S034: In 14 days fills the date (the input's min plus 14 days) and the save succeeds; the list filter reads Deferred / Waiting`
- [auto] The S019 flows with the new words (Defer, Put on hold, Deferred, On hold, "check by", Overdue · check by, no Defer for a technician) — `frontend/e2e/tickets-work.spec.js::S019: …` (five tests)
- On a real device: none new. S019's open row 10 in `docs/steps/device-checks.md` now carries the new words.
