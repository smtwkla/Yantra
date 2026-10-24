Step: S034 — Defer, hold and follow-up date
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 24-10-2026

# S034 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** One `minor` finding (the quick-pick
buttons are small on a floor dialog) and four nits. The step builds what the brief asks, in
the brief's words, and all the test runs below are green.

## Test runs (Linux cloud sandbox, run name `s034cr1`)

The `tooling/*.bat` wrappers cannot run here, so I ran their commands directly.

| Suite | Command | Result |
|---|---|---|
| Backend, full | `YANTRA_TEST_RUN=s034cr1 uv run pytest -q --tb=short -n 8 --dist loadscope` | **2325 passed** in 25 s |
| Frontend unit | `npx vitest run` | **122 passed**, 14 files |
| Frontend build | `npx vite build` | built, no errors |
| Browser (e2e) | `run_lanes.py e2e/tickets-work.spec.js e2e/screens.spec.js --project=desktop-chromium --project=phone-chromium`, `E2E_LANES=4` | **58 passed** in 98 s |

- **Specs run:** `tickets-work.spec.js`, because the step changes the ticket page, its move
  dialog and the ticket list. `screens.spec.js`, the standing check of every route. The step
  changes no shared frontend code, so the full suite is not needed.
- **Not run: `phone-webkit`.** WebKit is not installed in this sandbox. Chromium is build 1243
  and Playwright wants 1248, so I used a private folder of symlinks in my scratch area
  (nothing in `/opt` or the repo changed). The user's next full run covers WebKit.
- The deps and tooling suites did not run: the step changes no file they test.

## Findings

### CR1-01 (minor) — the quick-pick buttons are `btn-sm` on a floor dialog

- **Where:** `frontend/src/views/tickets/ScheduleFields.vue:71`.
- **Problem:** *In 7 days*, *In 14 days* and *In 30 days* use `btn btn-sm`. The floor checklist
  says tap targets are not shrunk on floor screens. A technician uses this dialog on a phone:
  *Put on hold* on a breakdown in progress, when work stops for a part (S019 U1).
- **Failure scenario:** a technician with gloves taps *In 14 days* and hits *In 7 days*. The
  date is a week early, and the ticket shows *Overdue* before anyone needs to follow it up.
- **Fix:** drop `btn-sm`. Three normal buttons fit in one row at 360 px, and `flex-wrap`
  already handles a narrower screen.

## Nits

- **CR1-02** (nit) `frontend/src/views/tickets/MoveDialog.vue:139`: the empty-field checks
  still test the date before the reason, so an empty Save points at the date below an empty
  reason. Swap lines 139 and 140 to follow the new field order. The backend's order comes from
  the move's field tuple (`tickets_core.py:396`, `:398`); swap it there too, if wanted.
- **CR1-03** (nit) `docs/Maintenance-Philosophy.md:193`: "A stopped machine waiting for parts
  … the button reads *Put on hold*" ties the word to the reason, but the rule is the
  intensity: every breakdown reads *Put on hold*, a production-slot wait too. Write "A
  breakdown (the machine is stopped) waits for resources, not by decision: …". Split the
  sentence at line 195–197 (about 45 words) into two.
- **CR1-04** (nit) `docs/Plan.MD:378`: the S034 words sit in a long parenthesis inside the
  S019 sentence. Move them into the S034 bullet at line 391, so the S019 sentence reads on.
- **CR1-05** (nit) `frontend/src/views/tickets/ScheduleFields.vue:26`: `pickDays()` repeats
  the date arithmetic of `lastDay` (lines 31–35). Use one local `daysFromToday(n)` for both.

## Checked and found consistent

- **Words by intensity (§ 1a).** `moveLabel()` and `moveSaveLabel()` give *Defer* on a
  degraded or initial ticket and *Put on hold* on a critical one. `stateLabel()` gives
  *Deferred* / *Waiting*, and *Overdue* past the date for both. `STATE_FILTERS` reads
  *Deferred / Waiting*. `STATE_LABELS.scheduled`, the frontend `EVENT_LABELS.scheduled` and
  the backend `EVENT_LABELS[SCHEDULED_EVENT]` read *On hold*. *Change plan* and *Plan changed*
  are unchanged. `MoveDialog.vue`'s title and Save already take the intensity.
- **No *Schedule*, *Scheduled* or *planned date* left on screen.** I searched `frontend/src`
  and the backend's messages. What remains is developer text only: code names
  (`ScheduleFields`, `schedule`, `planned_date`), comments, docstrings and a log line in
  `worker.py`. *Planned stop* in the times card is S019's planned downtime, a different
  thing, and stays. The service worker and `alerts_core.py` hold no such words.
- **`planDateKind` (§ 1b).** `slot` → planned; `parts`, `vendor`, `expert`, `approval`,
  `other` → check; an unknown or empty reason → `null`. The unit test lists all six codes
  from `WAITING_REASON_LABELS`, so a new reason must pick a kind.
- **"for" / "check by" (§ 1b).** `planText()` and `planChanges()` put "check by" before the
  date for a check reason and "for" for a slot. `planLine()` uses `planText()` before the
  date. Past the date it still reads "Overdue since DD-MM-YYYY · …" for both kinds. The list
  row of an overdue ticket reads "Overdue · check by …" (`stateLabel` plus `planText`), and
  the red `overdueBadge()` is unchanged. The timeline's "(was …)" keeps the old plan without
  its word, as before (reported in "Decisions taken").
- **The dialog (§ 1c).** The reason comes before the date. The label is *Date* before a reason
  is chosen, *Planned for* for a slot and *Check again by* otherwise. The help line shows
  for check reasons only, in the brief's exact words. The date still opens empty on
  *Defer* / *Put on hold*; *Change plan* opens with its plan, so its label is right at once.
- **Quick picks.** `pickDays()` adds the days to `new Date()` and formats with
  `toLocalDateValue()`, the same local-date basis as the input's `min`. 30 days is well inside
  the 365-day `max`, and the server checks both limits again.
- **Date messages (§ 1d).** The three `tickets_core` messages and `missingField()` read as the
  brief's table. The four backend test literals match. Each message is one short line in
  scope B.
- **The e2e changes.** The S019 assertions at the brief's lines moved to the new words. The
  technician's `toHaveCount(0)` test now looks for *Defer*, and the S034 defect test shows
  *Defer* visible to the engineer, so that check is real. The *In 14 days* test reads the
  input's `min`, adds 14 days in local calendar terms and compares the value; then it saves
  and finds the ticket under *Deferred / Waiting*. Each S034 test asserts what the user sees
  (button, label, help, badge, plan line, timeline line, filter option, list row). Every
  dialog opens through `openAction()`, which calls `expectDialogFits`.
- **`device-checks.md` row 10** carries the new words: *Defer*, *Waiting for parts*, *Check
  again by*, and "check by DD-MM-YYYY · waiting for parts".
- **Docs.** The `Maintenance-Philosophy.md` paragraph and the `Plan.MD` lines state the
  brief's words, the two date kinds, the required date and the quick picks correctly, apart
  from CR1-03 and CR1-04.
- **Scope and track.** Everything in § 3 is built and nothing more. The one extra export,
  `PLAN_DATE_KINDS`, is in "Decisions taken". No migration, data change, RBAC, endpoint or
  dependency, so the light track holds. No business rule moved into a Vue file: the kinds and
  words live in `ticketLabels.js`, and the date rules stay on the server.
- **Impl report.** It has "Decisions taken", real test numbers and a `## Manual checks`
  section that carries every important check of the brief as `[auto]` with its test, all
  backed by the passing run above. Its text follows scope A.

## Manual checks for the user

- None new from S034. Open `device-checks.md` row 10 (S019, now in S034's words) on an
  Android phone and an iPhone.
- The `phone-webkit` project did not run in this review. Run the full e2e suite on the
  Windows machine before the release, as usual.
