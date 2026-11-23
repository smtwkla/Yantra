```
Step: S107 — Ticket tasks: screens
Doc: impl-report
Author: Coder (Opus 5.5)
Date: 22-11-2026
```

# S107 — Ticket tasks: screens — implementation report

**Outcome.** The screens for S106's ticket tasks are built as the brief says, under KLA's gate A
answer Q1 (b): the *Tasks* card on the ticket page, the *Add task* / *Change task* dialog with three
quick picks, the inline cancel, *Mark task done* (the countermeasure dialog, generalized), the owner
mark, the four task lines on the timeline, the reasons under a disabled *Close* / *Not a fault*, and
my open tasks on *Me › Open work*. One backend text changed: an empty due date is refused with
"Choose the due date" (D13). Q1's same-name owner tags are **not** built (Q1 (b)): `tickets.py`,
`config_rbac.py` and `test_rbac.py` are untouched. 20 code and test files (13 code, 4 of them new;
7 tests, 1 new) and 2 docs. All tests green: all three unit suites, the build, the targeted and whole browser runs and the WebKit screens run (§ Tests run).

## 1. What was built

1. **The card *Tasks*** on the ticket page, after *Details / Times / Assigned* and before the meters
   card: "Tasks (1 of 3 done)" (cancelled ones in neither number), one row per task in the order
   added, *Add task* for `can_add_task`; "No tasks yet." and, for those who may add, "Give each check
   or follow-up job to one person, with a date." Shown when the ticket has a task or the user may add
   one.
2. **A task's row**: the state badge (*Open*, *Done*, *Cancelled*, or *Overdue N days* in red), "due
   DD-MM-YYYY", the text (`pre-wrap`), "Owner: <name>" with " (not at this site now)" when the owner
   left; *Done* with "recorded by <name>" when someone else recorded it, then the done text;
   *Cancelled … by <name>: <reason>*. Buttons by the server's flags: *Mark done* (`can_mark_done`),
   change and cancel icons (`can_change`, `aria-label` "Change task N" / "Cancel task N"). Side by
   side from `lg`, stacked on a phone.
3. **The owner mark** under the owner line, only for those who can change the task: "No login: mark
   it done for them." or "May not see this ticket. Mark it done for them, or choose another owner."
4. ***Add task* / *Change task***: *What to do* (300 characters), *Owner* (the ticket's people
   picker: *You*, *Assigned*, *Maintenance*, *Others at the site*), *Due date* (min the day the problem
   happened, max a year ahead) with *Today*, *Tomorrow*, *In 7 days*; no default date. On *Change*, an
   owner not in the site's list shows "Owner now: <name> (not at this site now). Choose another
   person, or keep them." The dialog checks nothing: the server's refusals show beside their fields.
5. **Cancel on the row**: "Cancel this task? It stays on the record with your reason.", *Why cancel
   it?* with its help line, *Cancel task* and *Keep it*.
6. ***Mark task done***: the countermeasure dialog, opened with a target: *What did you do?*, *Done
   on* (Now), photos; "The photos go to the ticket's photos." The photos go to the ticket's documents.
7. **The timeline** names *Task added*, *Task changed*, *Task done*, *Task cancelled*; a change, done
   or cancel line shows "Task: <text>" above its remark.
8. ***Close* and *Not a fault*** are disabled with each reason on its own line under them: the
   server's `blocked_reason` (open tasks), then "Add the labour first" or "Remove the parts first".
9. ***Me › Open work*** lists "Tasks (n)" between *PM jobs* and *Countermeasures*, by due date, each
   row with its ticket link ("TK-… · <code> — <name>") and *Mark done*; an overdue row is red.
10. **Backend**: `validate_task` refuses a missing (on add), null, or blank due date with
    `DUE_NEEDED` "Choose the due date"; any other non-`YYYY-MM-DD` value keeps "Enter the date as
    YYYY-MM-DD".

## 2. How it works

- **Pure helpers first** (`frontend/src/utils/ticketLabels.js`): `TASK_TEXT_MAX`, `TASK_DUE_PICKS`,
  `dateInDays(days, from)` (the phone's local date, now also behind `ScheduleFields`' quick picks and
  bounds), `moveBlocks(move, {labourCount, partCount})`, `taskEventText(event, tasks)`,
  `taskOwnerMark(task)`, `taskDoneTarget(ticketId, task)`, and the four `EVENT_LABELS`;
  `countermeasureDoneTarget(improvementId, action)` in `improvementLabels.js`. All unit-tested.
- **`TasksCard.vue`** holds the cancel state (`cancellingId`, `cancelBusy`, `cancelError`; one row
  asks at a time), makes the cancel call, and hosts `TaskDialog` and `MarkDoneDialog` (outside the
  card's `v-if`, so a reload that hides the card cannot tear down an open dialog). Each answer goes
  up as `saved(detail)`, which the page puts in place of its copy. A 409 with no field, or a photo
  that went up, emits `reload`: the page reloads its detail and its photos card (a new `ref` on
  `DocumentsCards`, whose exposed `reload` it calls). A watcher on the `ticket` prop closes a cancel
  ask whose task is gone or no longer `can_change` (the reload after a refused cancel).
- **`TaskItem.vue`** makes no call; it reads either answer shape (the detail entry, or a `mine` item
  with `ticket` and no `state`/`owner`). `CancelAsk.vue` is the inline cancel taken out of
  `CountermeasureItem.vue`; the countermeasure row passes its old texts and id, so its markup and
  texts are unchanged.
- **`TaskDialog.vue`** uses `useFormModal` with `path: null` and saves through `send` with its own
  URLs (POST `/api/tickets/<id>/tasks`, PUT `…/tasks/<task_id>`), sending all three fields; a watcher
  on `error` emits `reload` on a 409 with no field, as `MoveDialog` does.
- **`MarkDoneDialog.vue`** now takes `open(target)`; its done-then-photos sequence, close-only phase
  and events are unchanged. The improvement page and *Me* pass `countermeasureDoneTarget(…)`.
- **`TicketDetailView.vue`**: one `blocksOf(m)` (through `moveBlocks`) replaces the two disabled
  cases; *Add labour* stays beside a *Close* that lacks labour. The timeline's remark line lost its
  `v-else-if` chain (a `v-if` on `e.event !== 'note'`), so the "Task: …" line could sit between.
- **`MeView.vue`**: `loadTasks()` in the same `Promise.all`, page 1 of *Open work* only, when the user
  has a Team record; the tab watcher empties it; the heading *Tickets* shows when any of the three
  lists shows.
- **Backend**: `ticket_tasks_core.validate_task` adds one branch through `_blank`; nothing else.

## 3. Files touched

Backend
- `backend/ticket_tasks_core.py` — `DUE_NEEDED`, the empty-due-date branch and `_blank`.
- `backend/tests/test_ticket_tasks_core.py` — missing and null expect `DUE_NEEDED`; `""` left the
  format test; new tests for `""`, `"   "`, `None` on add and change, and a missing field (add
  refused, change valid).
- `backend/tests/test_ticket_tasks_api.py` — `TestAdd::test_a_bad_body_is_400` gains `due_date=""`.

Frontend (code)
- `frontend/src/views/tickets/TasksCard.vue` (new) — the card (§ 5.1).
- `frontend/src/components/TaskItem.vue` (new) — a row (§ 5.2).
- `frontend/src/views/tickets/TaskDialog.vue` (new) — add / change (§ 5.3).
- `frontend/src/components/CancelAsk.vue` (new) — the inline cancel (§ 5.4).
- `frontend/src/components/CountermeasureItem.vue` — uses `CancelAsk`; same texts, markup and ids.
- `frontend/src/views/improvements/MarkDoneDialog.vue` — `open(target)`: title, text, paths,
  placeholder and photo note from the target.
- `frontend/src/views/ImprovementDetailView.vue` — passes `countermeasureDoneTarget(…)`.
- `frontend/src/views/MeView.vue` — the *Tasks* list on *Open work*; the countermeasure *Mark done*
  through `countermeasureDoneTarget`.
- `frontend/src/views/TicketDetailView.vue` — the card, `moveBlocks`, the "Task: …" line, the
  `DocumentsCards` ref and `reloadWithPhotos`.
- `frontend/src/views/tickets/ScheduleFields.vue` — `dateInDays` in place of its local `daysFromToday`.
- `frontend/src/utils/ticketLabels.js` — the task helpers and labels (§ 5.10).
- `frontend/src/utils/improvementLabels.js` — `countermeasureDoneTarget`.

Tests
- `frontend/tests/ticketLabels.test.js` — the four labels, `dateInDays`, `moveBlocks`,
  `taskEventText`, `taskOwnerMark`, `taskDoneTarget`.
- `frontend/tests/improvementLabels.test.js` — `countermeasureDoneTarget`.
- `frontend/e2e/tickets-tasks.spec.js` (new) — § 8.1 tests 1–8.
- `frontend/e2e/me.spec.js` — the two S107 tests; `afterEach` cancels a ticket's open tasks before
  *Not a fault*.
- `frontend/e2e/support/tickets.js` — `taskByApi`, `markTaskDoneByApi`, `cancelOpenTasksByApi`.

Docs: `docs/Plan.MD`, `docs/steps/device-checks.md` (§ Docs updated).

## 4. Decisions taken

- **`dateInDays` beside `toLocalDateValue`** in `ticketLabels.js`, and `ScheduleFields`' `today` is
  `dateInDays(0)` (the same value as before). As the brief asks; no behaviour change.
- **`taskDoneTarget` in `ticketLabels.js`, `countermeasureDoneTarget` in `improvementLabels.js`**:
  each with its own module's words; `improvementLabels.js` already imports `ticketLabels.js`, so not
  the other way round.
- **`photoNote` placement**: at the start of the hint under *Add photos* ("The photos go to the
  ticket's photos. At most N MB each."). The brief names the text, not its place.
- **`CancelAsk` mounts with the ask** (`v-if`) and focuses its field on mount; `CountermeasureItem`'s
  old watcher on `cancelling` (reset and focus) is replaced by that. Same behaviour: each ask starts
  empty and focused.
- **The task's cancel field id** is `cancel-reason-task-<id>` (`idSuffix` `task-<id>`), so it can
  never equal a countermeasure's `cancel-reason-<id>`.
- **The card's dialogs sit outside its `v-if`** (a wrapping `div`): a 409 "This ticket is closed" on
  *Add task* reloads a ticket that may no longer show the card, and an unmounted Bootstrap modal would
  leave its backdrop.
- **`TaskItem` draws no button bar** when it has no button (a reader's row), so an empty flex row adds
  no gap.
- **Test hooks**: `data-testid="tasks-title"` on the card's title and `data-testid="owner-mark"` on the
  owner mark, so the tests read the header text and the mark without the *Add task* button's text.
- **`.action-bar`-scoped locators for *Close* and *Not a fault*** in the new spec: a dialog fading out
  still holds its own "Close" (the X), which made `getByRole("button", {name: "Close"})` match twice
  in test 1's first run.
- **Q1 (b)** (KLA, gate A): no change to `task_change_line`, `edit_task`, `config_rbac.py` or
  `test_rbac.py`; § 5.8 and its tests are not built. Not a departure: the brief records the answer.

No departure from the brief.

## 5. Not done, deferred or assumed

- § 5.8 (same-name owner tags) not built: Q1 (b).
- The task's text on *Me › My activity* (out of scope, § 1).
- The alerts *Task for you* and *Task overdue*: the third step.
- The countermeasure owner-change line for two people of the same name (brief § 9, *Found while
  checking*): still a candidate for its own step.
- Assumed: the photo note's place (§ 4 above).

## Tests run

All with `YANTRA_TEST_RUN=s107c1`; the final numbers of each run.

- **Unit, while coding**: `tooling/run-backend-tests.bat tests/test_ticket_tasks_core.py
  tests/test_ticket_tasks_api.py` 94 passed; `tooling/run-frontend-tests.bat tests/ticketLabels.test.js
  tests/improvementLabels.test.js` 138 passed.
- **All unit suites once** (`tooling/run-tests.bat`): backend PASSED 5491 passed (163 s), frontend
  PASSED 495 passed, tooling PASSED 253 passed; ALL SUITES PASSED.
- **Build**: `npx vite build` in `frontend/`: built, only the existing chunk-size warning.
- **New tests alone** (`E2E_LANES=1`, `phone-chromium`): `tickets-tasks.spec.js -g S107` 7 passed and
  test 1 failed on its first run (a test fault: `getByRole("button", {name: "Close"})` also matched a
  fading dialog's X; fixed by scoping to `.action-bar`), then test 1 alone passed; `me.spec.js -g S107`
  2 passed; test 8 on `desktop-chromium` 1 passed.
- **Targeted run** (Normal): `e2e/tickets-tasks.spec.js e2e/me.spec.js e2e/improvements.spec.js
  e2e/tickets-work.spec.js e2e/tickets-parts.spec.js e2e/screens.spec.js`: 108 passed, 2 skipped (the
  existing project skips: S040/S097's manager bottom bar on desktop, S066's desktop Copy link on the
  phone), 121 s.
- **Whole suite at Normal once**, at the end of the coding: 444 passed, 15 skipped, 0 failed, 296 s.
- **WebKit screens run** (shared `e2e/support/tickets.js` changed): `e2e/screens.spec.js
  --project=phone-webkit`: 10 passed (1.9 min).
- No schema docs check: no migration and no change under `docs/schema/`.

## Manual checks

Automated (each from a passing run):

- [auto] **important** The TK-2026-11-008 flow: two tasks, the technician marks his done from Me with a photo, Close waits for the other, then the ticket closes — `frontend/e2e/tickets-tasks.spec.js`::`S107: the TK-2026-11-008 flow: two tasks, the technician marks his done from Me with a photo, Close waits for the other, then the ticket closes`
- [auto] **important** Change and cancel a task; Not a fault waits for the open task — `frontend/e2e/tickets-tasks.spec.js`::`S107: change and cancel a task; Not a fault waits for the open task`
- [auto] The owner marks: no access, recorded by; a reader who cannot change the task sees none — `frontend/e2e/tickets-tasks.spec.js`::`S107: the owner marks: no access, recorded by; a reader who cannot change the task sees none`
- [auto] Who sees which buttons — `frontend/e2e/tickets-tasks.spec.js`::`S107: who sees which buttons: the owner marks done, another technician and the operator only read`
- [auto] Refusals in field order — `frontend/e2e/tickets-tasks.spec.js`::`S107: Add task refuses in field order: what to do first, then the due date`
- [auto] Overdue in red — `frontend/e2e/tickets-tasks.spec.js`::`S107: an overdue task shows Overdue 2 days in red`
- [auto] A stale cancel ask closes when the task was done meanwhile — `frontend/e2e/tickets-tasks.spec.js`::`S107: a cancel refused because the owner marked the task done meanwhile shows the row done, with no ask left`
- [auto] No sideways scroll with the Tasks card (`@device`) — `frontend/e2e/tickets-tasks.spec.js`::`S107: the ticket page with the Tasks card has no sideways scroll`
- [auto] My task on Me › Open work — `frontend/e2e/me.spec.js`::`S107: Kannan's task shows on Me › Open work above the tickets, with its ticket and Mark done; the serial opens the ticket`
- [auto] An overdue task on Me — `frontend/e2e/me.spec.js`::`S107: an overdue task shows Overdue 2 days on a red row on Me`

On a real device (rows 71 and 72 of `docs/steps/device-checks.md`):

- [ ] **important** *Mark task done* with the camera, gloved, on an Android phone as a technician
  (row 71; can be done with row 51 in one sitting).
- The iPhone keyboard over *Add task* (row 72).

## Fix rounds

### Round 1

Review: `4-code-review-r1.md` (0 blocker, 0 major, 1 minor, 3 nits). All four fixed; the round changes
four frontend files (`frontend/e2e/tickets-tasks.spec.js`, `TicketDetailView.vue`,
`ScheduleFields.vue`, `CountermeasureItem.vue`) and no backend file.

- **CR1-01 (minor) — Fixed.** In test 1 of `tickets-tasks.spec.js` the engineer's own *Mark done* on
  the ticket page (the supplier task) now sends the test photo too (`markDone(…, { photo: true })`).
  The test then asserts, with no navigation in between, that the Photos card holds two
  `.photo-tile[title="test-photo"]` tiles (the first came from *Me*). Fails without the fix: with the
  ticket page's ref renamed (`ref="documentsCardsBROKEN"`, so `documentsCards.value?.reload()` does
  nothing) the run failed at `tickets-tasks.spec.js:165`, `toHaveCount(2)`: expected 2, received 1
  (`phone-chromium`, test run alone). Passes with the ref restored: 1 passed. I broke the ref rather than
  the `@reload` wire the review named, because the ref is the silent path the finding describes; the
  `@reload` wire is what calls it, so either break reaches the same line.
- **CR1-02 (nit) — Fixed.** `TicketDetailView.vue`: `blocksOf(m)` is replaced by the computed
  `blocksByMove` (the blocks of each significant move by name, built once), read by both the `v-if`
  and the reasons list. `taskEventText(e, ticket.tasks)` is computed once per load in the computed
  `taskTexts` (one entry per event, read by the row's index `i`, which is the row's key). The two
  reads in each place can no longer drift apart.
- **CR1-03 (nit) — Fixed.** `ScheduleFields.vue`: the comment above `today` now says what it is for:
  the input's `min`, in the phone's local date, the same basis as the quick-pick buttons.
- **CR1-04 (nit) — Fixed.** `CountermeasureItem.vue`: the docstring paragraph is re-wrapped at the
  same width as its neighbours; the wording is unchanged but for "made by CancelAsk since S107".

Tests run (`YANTRA_TEST_RUN=s107f1`):

- No unit-tested file changed (`ticketLabels.js`, `improvementLabels.js` untouched), so no unit suite
  was run; no Python file changed.
- `npx vite build` in `frontend/` (output to the session scratchpad): built, only the existing
  chunk-size warning.
- Browser, targeted at Normal:
  `tooling\run-e2e-tests.bat e2e/tickets-tasks.spec.js e2e/tickets-work.spec.js e2e/screens.spec.js`:
  66 selected, 64 passed, 2 skipped, 0 failed (100 s). No `@device` test and no `page.route` was
  added, so no WebKit run.

Docs updated: none, because the round changes one test, two comments and an internal computed; no
behaviour, route, key or command changed.


### Round 2 (orchestrator, 22-11-2026)

- **CR2-01 (nit), fixed:** the missing space before `:key` in `frontend/src/views/TicketDetailView.vue:320`. One character; `npx vite build` built (the existing chunk-size warning only). No new review: the change is whitespace in a template attribute list.

## Docs updated

- `docs/Plan.MD` — § 2 item 8 (*Me*): *Open work* lists my open ticket tasks (S107); § 4.2 *Ticket
  tasks*: "Nothing shows to users until the screens step" removed, and the orchestrator's *Screens
  (S107 …)* paragraph extended with what was built; § 6 *Screens*: the *Me* line and the *Ticket*
  line gain the tasks.
- `docs/steps/device-checks.md` — rows 71 and 72 (§ 8.5).
- Not due: the schema docs (no migration), `.claude/CLAUDE.md` (no new invariant, command or review
  point; brief § 9), `help/` (retaken before a release on KLA's word).

## Feedback

- hindrance: an edit script that matched multi-line text failed on a CRLF file
  (`ScheduleFields.vue`, one retry with the Edit tool), and an appended block left
  `frontend/e2e/support/tickets.js` with mixed line endings until normalized; the repo's files are a
  mix of CRLF and LF working copies, so every scripted edit has to detect and keep each file's own ending
  (about 5 minutes).
- idea: `getByRole("button", { name: "Close", exact: true })` on the ticket page also matches a
  dialog's X while it fades out; an e2e support helper for the action bar's buttons
  (`actionButton(page, name)`, scoped to `.action-bar`) would stop the next spec from meeting the same
  strict-mode failure (`tickets-tasks.spec.js` test 1, first run).
- hindrance (round 1): `cmd //c "…run-e2e-tests.bat … -g \"two words\""` passes the quoted `-g` through
  cmd, which splits it, and the run answers "No tests found" after a 12 s seed (one lost run). The
  settings note warns of this for pytest `-k` only; naming a single-word fragment of the title
  (`-g TK-2026-11-008`) worked. Worth one line in the settings' *A new test alone* entry.
