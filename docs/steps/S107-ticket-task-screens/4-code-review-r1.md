```
Step: S107 — Ticket tasks: screens
Doc: code-review r1
Author: Code reviewer (Opus 5.5)
Date: 22-11-2026
```

# S107 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** One `minor` (a stated behaviour with no test)
and three nits. The screens follow the approved brief under Q1 (b), every button follows the
server's flags, the shared-component changes keep the countermeasure screens as they were, and
all unit suites and the build are green.

**Tests run by the reviewer** (`YANTRA_TEST_RUN=s107cr1`):
- `tooling/run-tests.bat`: backend PASSED 5491 passed (134 s), frontend PASSED 495 passed, tooling
  PASSED 253 passed; ALL SUITES PASSED.
- `npx vite build` (output to the session scratchpad): built, only the existing chunk-size warning.
- Browser tests: not re-run. The coder's runs are in the report: targeted Normal 108 passed /
  2 skipped (the right six specs, brief § 8.3), whole suite at Normal 444 passed / 15 skipped /
  0 failed, and `screens.spec.js --project=phone-webkit` 10 passed (needed because
  `e2e/support/tickets.js` changed). No finding of mine needs a run.
- No schema docs check: the diff touches neither `backend/local_db.py` nor `docs/schema/`.

KLA's own uncommitted files in the snapshot diff (`.claude/CLAUDE.md`, `backend/example_secrets_app.py`,
`.claude/skills/read-prod-data/`, `tooling/dev/prod_query.py`, `tooling/run-dev-query.bat`,
`tooling/run-prod-query.bat`, `tooling/tests/test_prod_query.py`) were left out of the review, as
the orchestrator asked.

## Findings

### CR1-01 (minor) — the ticket page's photo reload after *Mark task done* has no test

`frontend/src/views/TicketDetailView.vue:210-213` (`reloadWithPhotos`),
`frontend/src/views/tickets/TasksCard.vue:119` (`MarkDoneDialog @reload`),
`frontend/e2e/tickets-tasks.spec.js:147-162`.

**Problem.** Brief § 5.1 and § 5.5 say that a photo sent from *Mark task done* on the ticket page
makes the page reload its detail and its *Photos* card (`DocumentsCards`' exposed `reload`, through
the new `ref="documentsCards"`). No test exercises this path. Test 1 adds its photo from *Me*, and
then `asPerson` opens the ticket page fresh, so the Photos card is loaded from scratch. The
engineer's own *Mark done* on the ticket page (`:162`) sends no photo. The call is
`documentsCards.value?.reload()`, so a broken ref (a renamed `ref`, the card moved under a `v-if`)
would fail silently.

**Failure scenario.** A later change renames the ref or wraps `DocumentsCards` in a component.
An engineer marks a task done on the ticket page for "Ramesh (operator, no phone)" and adds a
photo of the panel. The dialog closes, but the *Photos* card does not show the photo until the
page is reloaded by hand. The engineer thinks the photo was lost and sends it again, so the ticket
holds two copies. Every browser test stays green.

**Suggested fix.** In test 1, give the engineer's own *Mark done* (`:162`) the test photo too
(`markDone(page, …, { photo: true })`), then assert that the Photos card holds two
`.photo-tile[title="test-photo"]` tiles, with no navigation in between. Record the red result
(for example with the `@reload` wire on `MarkDoneDialog` in `TasksCard.vue` removed) as the
*Red, then green* rule asks.

## Nits

- **CR1-02** (nit) `frontend/src/views/TicketDetailView.vue:305`, `:314` and `:514`:
  `blocksOf(m)` and `taskEventText(e, ticket.tasks)` are each computed twice per row (once in the
  `v-if`, once in the body). Compute each once, for example a computed map of the blocks by move
  name, so the two reads cannot drift apart.
- **CR1-03** (nit) `frontend/src/views/tickets/ScheduleFields.vue:24`: the comment ("Today plus
  `days`, …") sits above `today` and describes `dateInDays`'s argument, which `today` does not
  have. Say what `today` is for (the input's `min`), or drop the comment, since `dateInDays`
  documents itself.
- **CR1-04** (nit) `frontend/src/components/CountermeasureItem.vue:12`: the inserted "CancelAsk
  since S107" makes this docstring line much longer than its neighbours. Re-wrap the paragraph.

## Checked and found consistent

- **Shared components, effect on the countermeasure screens.** `CancelAsk.vue` holds the exact
  markup, classes, texts and `cancel-reason-<id>` id that `CountermeasureItem` had. The old watcher
  on `cancelling` (reset the reason, focus the field) is replaced by mounting under `v-if` and
  focusing in `onMounted`. Each ask still starts empty and focused, and the reason survives a 400
  because the component stays mounted. Nothing in `CountermeasureItem.vue` still refers to the
  removed `reason`, `reasonField` or `reasonError`. `MarkDoneDialog.open(target)`:
  `countermeasureDoneTarget` gives today's title, both paths and placeholder (unit-tested); every
  former `target.value.id` and `improvementId` use is gone; the done-then-photos sequence, the
  close-only phase and the 409 `reload` are unchanged. Both callers (`ImprovementDetailView.vue:424`,
  `MeView.vue:226`) pass the target. `improvements.spec.js` and `me.spec.js` ran green in the
  coder's targeted run.
- **Every button follows the server's flags.** `Add task` and the empty-state help appear only
  with `can_add_task`. *Mark done* appears only with `can_mark_done`. Change and cancel appear
  only with `can_change`, never on *Me*. The owner mark appears only with `can_change`
  (`taskOwnerMark`). *Close* and *Not a fault* show `moves[].blocked_reason` through `moveBlocks`.
  I checked against S106's `_tasks` and `my_tasks` (`backend/tickets.py`): the `mine` item sends
  `can_mark_done` and no `can_change`. The cancel route needs `ticket:assign`, as `can_change`
  does. The done route accepts the owner or a `ticket:assign` holder, as `can_mark_done` does.
  The photo goes to `/api/tickets/<id>/documents`, written with `ticket:raise`, which has the same
  holders as `ticket:read` (brief § 5.5).
- **The stale-cancel watcher** (`TasksCard.vue:44-51`). It watches the `ticket` prop; the page
  replaces the object on every `load()` and `onSaved`, so the watcher fires. It closes the ask and
  clears the error only when the asking task is gone or no longer `can_change`. Every 409 the
  cancel route can answer (done, already cancelled, ticket closed) leaves the reloaded task
  without `can_change`, so the ask always closes. A 400 on `reason` keeps the ask. Test 7 covers
  the done-meanwhile case.
- **D13 in `validate_task`** (`backend/ticket_tasks_core.py:78-87`). These give `DUE_NEEDED`: a
  missing date on an add, `null` on either (`required_field` returns missing), and a blank string
  after trim. A missing field on a change is valid. Any other value that is not `YYYY-MM-DD` keeps
  `LABOUR_DATE_FORMAT`. Every case of brief § 8.2 is tested (core: the parametrized `""`, `"   "`,
  `None` × add/change, and missing on add/change; API: `due_date=""` → 400 `due_date`). The
  dialog sends `""` from its blank form, so field order holds (e2e test 5).
- **Dialogs.** `TaskDialog` follows the `useFormModal` call contract (`blank()` takes no argument,
  `path: null`, saves through `send` with its own URLs). The 409 watcher on `error` matches
  `MoveDialog`. `FormModal`'s form is `novalidate`, so the date's `min`/`max` never block a
  submit, and the server answers instead. The "Owner now: … (not at this site now)" line uses the
  same rule as the server's `may_own` (`people_at_site`: active and a member of the site). Both
  dialogs live outside the card's `v-if`, so a 409 reload that hides the card does not tear down a
  modal. The page's `load()` keeps the same ticket on a reload (CR5-02/CR4-03), so `TasksCard` is
  not unmounted either.
- **Ticket page.** The card sits after *Details / Times / Assigned* and before the meters (D6).
  The timeline still shows a note's remark only in the note block and every other remark once
  (`v-if="e.event !== 'note' && e.remark"` matches the old `v-else-if`). "Task: …" shows on the
  change, done and cancel lines, not on *Task added*. `moveBlocks` keeps "Add the labour first" and
  "Remove the parts first" with the same classes, and *Add labour* stays beside a *Close* that
  lacks labour. Dates come from `formatDateTime`, which gives DD-MM-YYYY for the detail's and
  `mine`'s `YYYY-MM-DD`.
- **Me.** Tasks load in the same `Promise.all`, on page 1 of *Open work* only, with a Team record,
  and the tab watcher empties them. The order is PM jobs, Tasks, Countermeasures, Tickets (D7).
  The *Tickets* heading counts the three lists. The no-Team-record state is unchanged: no *Tasks*
  heading, and the *not in Team* line stays.
- **Browser-test conventions (S024).** Each test raises its own ticket and finds its tasks by
  `data-task` or by its own text; no test asserts a count shared across the lane. Every dialog
  opened calls `expectDialogFits` (`addTask`, `markDone`, *Change task*, the refusal test, and
  `openAction` for *Close*). Allowed failures are named exactly (the 400 on `/tasks`, the 409 on
  `…/cancel`). `@device` is on test 8 only, whose title names no sideways scroll. The `afterEach`
  of both specs reads the state, cancels the open tasks as admin, then closes a back-in-service
  ticket or uses *Not a fault*. `page.route` is not used. The new support helpers assert their
  status codes.
- **UI wording (scope B).** The texts are those of the brief: short, plain verbs, no jargon. The
  owner mark tells the engineer what to do. Buttons start with a verb ("Add task", "Save task",
  "Cancel task", "Keep it", "Mark done").
- **Phone layout.** No fixed widths. A 300-character word wraps (`overflow-wrap: anywhere`; test 8).
  Floor buttons are full size (no `btn-sm`), and *Mark done* is full width on a phone. Cancel
  goes through an inline confirm step with a reason.
- **Docs pass.** `docs/Plan.MD` § 2 item 8, § 4.2 and § 6 (*Me*, *Ticket*) describe what was built.
  `docs/steps/device-checks.md` rows 71 and 72 carry brief § 8.5 with account, network and where.
  No migration, so no schema docs. No new invariant, so no `.claude/CLAUDE.md` point (brief § 9).
- **Scope.** Nothing beyond the brief. Q1 (b) is respected: `tickets.py`, `config_rbac.py` and
  `test_rbac.py` are untouched. The report states the small choices (photo note place, test
  hooks, dialogs outside the `v-if`, the task's cancel id). The `TaskItem` / `CountermeasureItem`
  likeness is D3's approved choice, so it is not a DRY finding.
- **Manual checks in the report.** Both **important** browser checks (§ 8.1 tests 1 and 2) are
  `[auto]` with a passing run. The important Android check is an unticked box (row 71). The
  iPhone check is a plain line (row 72).

## What still needs a manual check on a real device

- Row 71 (**important**): *Mark task done* from *Me* with the camera and a work glove, on an
  Android phone, as a technician; the photo shows in the ticket's *Photos* card. It can be done
  together with row 51.
- Row 72: the iPhone keyboard over *Add task* (the field being typed in stays in view, *Add task*
  can be reached by scrolling).

## Feedback

- idea: the snapshot diff showed 7 of KLA's uncommitted files that are not part of the step. I
  listed the step's own folders after `--` to leave them out (`step_snapshot.py diff S107 --
  backend frontend/src …`). An `--exclude <path>` option, or a note in the spawn prompt giving the
  include list, would save building that list by hand (about 2 minutes).
