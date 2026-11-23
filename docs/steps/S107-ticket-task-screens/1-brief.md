```
Step: S107 — Ticket tasks: screens
Doc: brief
Author: Brief writer (Opus 5.5)
Date: 22-11-2026
Track: full
Baseline: 0bf95b3 (S106 adopted; stale check 22-11-2026: none of the brief's files changed since its review)
Status: Gate B 22-11-2026 (code review r1: 1 minor, 3 nits, fixed in fix round 1; verify review r2: 1 nit, fixed by the orchestrator; device checks rows 71–72 for IT Admin after the release; gate B answers by KLA 22-11-2026: adoption waits, feedback triage after the alerts step); was approved 22-11-2026 by KLA (Q1 (b))
```

# S107 — Ticket tasks: screens

## 1. What will be built

**The request** (KLA, 22-11-2026): "plan ticket tasks screens". It is the second of the three
steps KLA chose at S106's gate A (backend S106, then screens, then alerts). The case is
TK-2026-11-008: an HT cable termination on a VCB failed, moisture is the suspected cause, and the
follow-up work goes to people: *Check the space heater circuit diagram and find any fuse* for a
technician, *Get the VCB supplier to inspect the panel* for an engineer.

**This step builds the screens** on S106's API (`docs/steps/S106-ticket-tasks/1-brief.md` § 6) as
built (`backend/tickets.py` section *Tasks (S106)*, `backend/ticket_tasks_core.py`). It adds no
route, table or key. It changes two backend texts: the timeline line of an owner change between
two people of the same name (§ 5.8, Q1; KLA's gate B point for S106), and the refusal of an empty
due date, "Choose the due date" (§ 5.3).

1. **The card *Tasks*** on the ticket page: "Tasks (1 of 3 done)", one row per task with its
   state (*Open*, *Done*, *Cancelled*, or *Overdue 2 days* in red), the text, the owner and the
   due date. `"Add task"` for the holders of `ticket:assign` while the ticket is open.
2. **Add / change a task** in one dialog: *What to do*, *Owner* (the ticket's people picker),
   *Due date* with the quick picks `"Today"`, `"Tomorrow"`, `"In 7 days"`.
3. **Cancel** an open task with a reason, asked on its row.
4. **Mark done**: *What did you do?*, *Done on* (the time field with *Now*) and photos, which go
   to the ticket's photos (S106 D7). The owner does it on the phone, from the ticket page or from
   *Me*; an engineer does it for an owner without a login.
5. **A mark on a task whose owner cannot act on it** (`owner.can_open` false): "No login: mark
   it done for them." or "May not see this ticket. Mark it done for them, or choose another
   owner.", shown to the people who can change the task.
6. **The timeline** names the four task lines (*Task added*, *Task changed*, *Task done*, *Task
   cancelled*) and shows the task's text on each.
7. ***Close* and *Not a fault* say why they wait**: disabled, with the server's
   `blocked_reason` under them ("This ticket has 1 open task. Mark it done or cancel it first.").
8. ***Me › Open work*** lists my open tasks, by due date, each with the ticket and `"Mark done"`.

**After S106 and S107** (KLA's gate B acceptance for S106, here as § 8.1 test 1): on a ticket
like TK-2026-11-008 the engineer adds the two tasks; the technician marks his done from *Me* with
a photo; *Close* is refused while the other is open; the engineer marks his done and closes the
ticket. (*Not a fault* waits the same way, on a ticket not yet back in service: § 8.1 test 2.)

### Out of scope

- Everything S106 built, and the alerts *Task for you* and *Task overdue* (the third step).
- A count of tasks on the ticket list or on the *Open work* tab label (S106 § 1, *Out of scope*;
  the tab labels stay, `frontend/e2e/me.spec.js:146-152` checks they fit).
- A photo owned by a task, reopening a done task, deleting a task (S106 D7, § 1).
- The task's text on *Me › My activity*: the activity API sends no `task_id`, so a *Task done*
  line there shows the done text only (`list_activity`'s columns; § 5.6).
- Any change to `FormModal.vue` or `useFormModal.js` (shared code).

## 2. Standards and practice

- **TPM — the abnormality tag and visual control.** In plain words: every defect found gets a
  tag that names who acts and by when, and the tag stays until the work is finished; the state
  of the work is visible at a glance, so a late job is seen without asking. The defect ticket is
  the tag (Plan § 4.2); the card *Tasks* shows its "who, what, by when", and *Overdue 2 days* in
  red is the visual control. *Close* shows why it waits instead of failing after a tap.
- **EN 13306** (maintenance terms; term numbers *to verify*). In plain words: corrective
  maintenance has steps, among them *fault diagnosis* (find where the fault is and its cause)
  and *fault correction*; corrective work that waits for a part, a slot or a vendor is
  *deferred*. A task is one such step given to one person (S106 § 2). The screens keep the
  ticket as the one work order: the tasks live on its page, not on a page of their own.
- **ISO 9001 § 7.5.3** (control of documented information). In plain words: records are kept,
  protected from change and show who did what and when. A cancel asks for the reason and keeps
  the row; *Done* shows "recorded by <name>" when someone other than the owner recorded it; every
  change is a timeline line. `ticket_tasks` keeps only the current owner, so the owner-change
  line is the only record of the old one: Q1 decides how it tells two people of one name apart
  (§ 9; under (a) only while their roles stay as they were).
- **ISO 27001 A.5.15** (access control). In plain words: each person gets only what their work
  needs. Every button follows the server's flags (`can_add_task`, `can_change`,
  `can_mark_done`, `blocked_reason`), so no button ends in a refusal. The owner records their own
  work without the engineer's key. Q1's role word is shown to readers of the ticket, who already
  see each person's role in the people picker (§ 5.8).
- **SMRP KPIs and ISO 14224**: nothing changes; the times card reads the ticket's own events
  (S106 § 2).

## 3. Where

S106's files are not committed yet (S106 is at gate B; KLA: "adoption waits"). This step is coded
after S106 is adopted. Files that S106 changes are anchored by name; the others by `file:line`.

### Frontend

- New: `frontend/src/views/tickets/TasksCard.vue` (the card, § 5.1),
  `frontend/src/components/TaskItem.vue` (a row, § 5.2), `frontend/src/views/tickets/TaskDialog.vue`
  (add / change, § 5.3), `frontend/src/components/CancelAsk.vue` (the inline cancel, taken out of
  `frontend/src/components/CountermeasureItem.vue:130-151`, § 5.4, D3).
- `frontend/src/components/CountermeasureItem.vue`: uses `CancelAsk`; same texts and markup.
- `frontend/src/views/improvements/MarkDoneDialog.vue`: `open(target)` instead of `{ improvementId,
  action }` (§ 5.5, D4); its callers `frontend/src/views/ImprovementDetailView.vue:424` and
  `frontend/src/views/MeView.vue:199` pass `countermeasureDoneTarget(…)`.
- `frontend/src/views/TicketDetailView.vue`: the card, the close reasons (§ 5.7), the timeline's
  task lines (§ 5.6), a `ref` on `DocumentsCards`.
- `frontend/src/views/MeView.vue`: *Tasks* on *Open work* (§ 5.9).
- `frontend/src/views/tickets/ScheduleFields.vue`: its local `daysFromToday` gives way to the
  shared `dateInDays` (DRY with the quick picks); no behaviour change.
- `frontend/src/utils/ticketLabels.js` and `frontend/src/utils/improvementLabels.js`: the labels
  and pure helpers of § 5.10.

### Backend

- `backend/ticket_tasks_core.py`: `validate_task` refuses an empty due date with "Choose the due
  date" (§ 5.3, any Q1 answer); under Q1 (a) or (a2), `task_change_line` tags two owners of the
  same name with their role at the ticket's site (§ 5.8).
- `backend/config_rbac.py` (Q1 (a) or (a2)): new `ROLE_WORDS` beside `SITE_ROLES` (§ 5.8).
- `backend/tickets.py` (Q1 (a) or (a2)): `edit_task` passes the old and the new owner's role at
  the ticket's site to `task_change_line` (the old one through `person_at_site`, only when the
  two names match).

### Tests

- `frontend/e2e/tickets-tasks.spec.js` (**new**): § 8.1.
- `frontend/e2e/me.spec.js`: the S107 *Me* tests; its `afterEach` cancels a test ticket's open
  tasks before *Not a fault* (§ 8.2).
- `frontend/e2e/support/tickets.js`: `taskByApi`, `markTaskDoneByApi`, `cancelOpenTasksByApi`
  (shared e2e support: § 8.3 names what that runs again).
- `frontend/tests/ticketLabels.test.js`, `frontend/tests/improvementLabels.test.js`: § 8.2.
- `backend/tests/test_ticket_tasks_core.py`, `backend/tests/test_ticket_tasks_api.py`: the empty
  due date and the same-name tests (§ 8.2).
- `backend/tests/test_rbac.py` (Q1 (a) or (a2)): `ROLE_WORDS` (§ 8.2).

### Docs (housekeeping, by the coder)

- `docs/Plan.MD`: § 2 item 8 (*Me*, `docs/Plan.MD:47`): *Open work* lists my open tasks too
  (S107); § 4.2 the bullet *Ticket tasks (S106 …)* (`docs/Plan.MD:518`): "Nothing shows to users
  until the screens step" becomes what S107 shows; § 6 *Screens*: the *Me* line
  (`docs/Plan.MD:1144`) and the *Ticket* line (`docs/Plan.MD:1149`) gain the card *Tasks*.
- `docs/steps/device-checks.md`: the rows of § 8.5.
- `help/`: nothing in the step (retaken before a release on KLA's word).
- No schema doc (no migration), no `.claude/CLAUDE.md` point (§ 9).

**File count:** 23 code and test files (15 code, 4 of them new, 3 of them backend; 8 tests, 1
new), 2 docs; 20 under Q1 (b).

## 4. Data model

None. No migration. Under Q1 (a) or (a2) one stored text changes: the `remark` of a
`task_changed` line for an owner change between two people of the same name (§ 5.8). S106 is
not released, so no such line exists in production.

## 5. Rules

### 5.1 The card *Tasks* (`TasksCard.vue`)

- **Where:** on the ticket page after the row *Details / Times / Assigned*
  (`frontend/src/views/TicketDetailView.vue:330-437`) and before the meters card (`:440`), full
  width, `mb-3`. The tasks are the ticket's "who does what by when", so they sit beside
  *Assigned* (D6).
- **Shown** when `tasks.length > 0` or `can_add_task` (as *Labour* shows to workers or when not
  empty, `:127`).
- **Header:** "Tasks" and, when any task is open or done, " (1 of 3 done)" through
  `actionCountsText(task_counts)` (`frontend/src/utils/improvementLabels.js:117`; cancelled ones
  in neither number; `task_counts` has the shape of `action_counts`). `"Add task"`
  (`btn btn-outline-primary`, icon `fa-solid fa-plus`) when `can_add_task`.
- **Rows:** a `list-group list-group-flush`, one `TaskItem` per entry of `tasks`, in the
  server's order (as added), `number` = its place in the list.
- **Empty:** "No tasks yet." and, when `can_add_task`, "Give each check or follow-up job to one
  person, with a date."
- **The card's contract:** props `ticket`, `people`, `ownPersonId`; it holds `cancellingId`,
  `cancelBusy`, `cancelError` (one row asks at a time, as S071 § 5.2); it makes the cancel call
  and emits `saved(detail)` with the answer; the two dialogs live inside it. It emits `reload`
  when the page behind is stale (a 409 with no field) or a photo went up; the page then reloads
  the detail and the photos card (`DocumentsCards`' exposed `reload`,
  `frontend/src/components/documents/DocumentsCards.vue:239`).
- **A stale cancel ask closes itself:** the card watches its `ticket` prop; when the task of
  `cancellingId` is missing or no longer `can_change` in the new copy, it sets `cancellingId` and
  `cancelError` to null. This covers the reload after a 409 (the page's `load()` gives a new
  `ticket`) and a `saved` from another control. It does the work of S071 CR2-01's
  `closeStaleCancel` (`frontend/src/views/ImprovementDetailView.vue:178-182`), which the card
  cannot call: the page, not the card, reloads.
- `data-testid="tasks"` on the card.

### 5.2 One task (`TaskItem.vue`)

**Two answer shapes**: a detail entry (S106 § 6 `tasks`) and a `mine` item (no `state`, `owner`,
`done_*`, `cancelled_*`, no flags but `can_mark_done`, plus `ticket`). The row reads `state ??
"open"`, shows the owner line only when `owner` is there, and the ticket line only with
`showTicket` (as `CountermeasureItem`, S071 § 5.2).

- **Line 1:** the state badge, its words from `ACTION_STATE_LABELS`
  (`frontend/src/utils/improvementLabels.js:108`): *Open* (`text-bg-secondary`), *Done*
  (`text-bg-success`), *Cancelled* (`text-bg-light border`), and for an open task with
  `overdue_days > 0` `overdueText(overdue_days)` (`text-bg-danger`, `:111`) instead of *Open*; at
  the right "due 24-11-2026" (`formatDateTime` of `due_date`).
- **Line 2:** the text (`white-space: pre-wrap; overflow-wrap: anywhere`).
- **Line 3:** "Owner: <name>" (`owner.name`; the API sends no role here: the role in the e2e
  seed's names, such as "Kannan (technician)", is part of the name); " (not at this site now)"
  when `owner.active` or `owner.may_own` is false (S071's words).
- **The owner mark** (`taskOwnerMark(task)`, § 5.10), only when `can_change` (the people who can
  act on it): a `small` line with `fa-solid fa-circle-exclamation`, `text-warning-emphasis`:
  - `owner.can_open` false and `owner.has_login` false: "No login: mark it done for them.";
  - `owner.can_open` false and `owner.has_login` true: "May not see this ticket. Mark it done for
    them, or choose another owner.";
  - none when the owner line already says "(not at this site now)", or `can_open` is true.
  "May not" because the flag is a hint that can be wrong both ways (S106 § 4.2).
- **Done:** "Done 23-11-2026 10:15 · recorded by <name>" (the "recorded by" part only when
  `done_by_name` differs from `owner.name`), then the done text.
- **Cancelled:** "Cancelled 23-11-2026 11:52 by <name>: <reason>", the row in `text-secondary`.
- **With `showTicket`** (on *Me*): a link "TK-2026-11-008 · VCB-01 — Vacuum circuit breaker" to
  `/tickets/<id>`; an overdue row gets `list-group-item-danger` (as S071's *Me* row).
- **Buttons** (the ticket page's size, gloved thumbs; none when the row is asking to cancel):
  - `"Mark done"` (`btn btn-success`, full width on a phone) when `can_mark_done`;
  - change (icon `fa-solid fa-pen`, `aria-label` "Change task 2") and cancel (icon
    `fa-solid fa-ban`, `btn-outline-danger`, `aria-label` "Cancel task 2") when `can_change`;
    never with `showTicket` (*Me* is for doing the work, S071 D5).
- **Its contract:** it makes no call. Props `task`, `number`, `showTicket`, `cancelling`,
  `cancelBusy`, `cancelError`; emits `change`, `ask-cancel`, `keep`, `cancel(reason)`,
  `mark-done`. `data-task="<id>"` on the `li`.
- **Layout:** a wide screen (`lg`) puts badge, text and owner, due date and buttons side by side,
  as `CountermeasureItem`'s scoped CSS does
  (`frontend/src/components/CountermeasureItem.vue:158-210`); a phone stacks them. The row keeps
  its own scoped CSS (D3).

### 5.3 The dialog *Add task* / *Change task* (`TaskDialog.vue`)

`useFormModal` (`frontend/src/composables/useFormModal.js:20`), props `ticket`, `people`,
`ownPersonId`; `openAdd()`, `openChange(task)`; emits `saved(detail)` and `reload`.

- **The call contract** (`useFormModal` calls `blank()` with no argument at set-up,
  `frontend/src/composables/useFormModal.js:22`): `path: null`; `blank: () => ({ text: "",
  owner_id: null, due_date: "" })`; `openAdd` → `openCreate()`; `openChange(task)` →
  `openEdit(task)` with `fromRecord: (t) => ({ text: t.text, owner_id: t.owner.id, due_date:
  t.due_date })`. The dialog saves through `send` with its own URLs, `apiPost` to
  `/api/tickets/<id>/tasks` or `apiPut` to `/api/tickets/<id>/tasks/<task_id>` (`editingId`), as
  `ActionDialog` does (`frontend/src/views/improvements/ActionDialog.vue:72-73`), since
  `useFormModal`'s own save builds `${path}/${id}` from one fixed path. The form's keys are the
  API's fields, so `modalError` shows a refusal of any other field at the top (`:52-54`).
- **Fields:**
  - **`"What to do"`**: textarea, 2 rows, `maxlength` `TASK_TEXT_MAX` (300), placeholder "Check
    the space heater fuse in the panel.", `autofocus`; its `fieldError('text')`.
  - **`"Owner"`**: `PersonPicker` (`frontend/src/views/tickets/PersonPicker.vue`) with the page's
    `people` (`GET /api/tickets/people?ticket_id=`, loaded for `ticket:assign` holders,
    `frontend/src/views/TicketDetailView.vue:141`), `ownPersonId`, `assigneeIds` = the ticket's
    assignees, not `assignableOnly` (any active member of the site may own a task, S106 D3);
    `idPrefix` `task-owner`, so the label is `<label for="task-owner-filter">`. The picker groups
    *You*, *Assigned*, *Maintenance*, *Others at the site*, with each person's role and vendor.
    On *Change*, an owner who is not in `people` (left the site, inactive) gets a line above the
    picker: "Owner now: <name> (not at this site now). Choose another person, or keep them."; the
    form keeps their id until another is picked. Its `fieldError('owner_id')`.
  - **`"Due date"`**: `type="date"`, `min` = the ticket's `occurred_at.slice(0, 10)` (the floor
    the server checks, S106 § 5.3), `max` = `dateInDays(PLANNED_DATE_MAX_DAYS)` (365,
    `frontend/src/utils/ticketLabels.js:350`, the server's bound too); under it three buttons
    (`btn btn-outline-secondary`, from `TASK_DUE_PICKS`): `"Today"` (0 days), `"Tomorrow"` (1),
    `"In 7 days"` (7), each setting the date to `dateInDays(n)`; help "By when it should be
    done". No default on *Add* (D5). Its `fieldError('due_date')`.
- **Save:** FormModal's own buttons, `"Add task"` / `"Save task"` (`saveLabel`) and `"Cancel"`.
  The body is `{ text, owner_id, due_date }`, all three on *Change* too (the server writes only
  what differs, S106 § 5.2). The dialog checks nothing itself: every rule is the server's, and
  `clean_body` sends the first refusal in field order: "Enter what to do", "Choose the owner",
  "Choose the due date", then "Choose a person from this site", "Choose a date from …, the day
  the problem happened", "Choose a date within a year".
- **"Choose the due date" is new on the server** (`ticket_tasks_core.DUE_NEEDED`, a departure
  from S106 § 5.2's table, which gives "Enter the date as YYYY-MM-DD"): in `validate_task`, a
  `due_date` missing on an add, `null`, or a string that is empty after trim gets "Choose the due
  date"; any other value that is not `YYYY-MM-DD` keeps `LABOUR_DATE_FORMAT`. The format words
  fit an API caller, not a field with quick picks; a dialog check of its own would answer before
  the fields above it.
- **A 409 with no field** ("A ticket holds up to 30 tasks…", "This ticket is closed", "Only an
  open task can be changed"): the message at the top, and the dialog emits `reload` through a
  watcher on `error` (`value && !value.field && value.status === 409`), as `MoveDialog` does
  (`frontend/src/views/tickets/MoveDialog.vue:92-93`), since the page behind is stale.
- **The common case:** one line of text, a tap on the assigned technician (under *Assigned*), a
  tap on `"Tomorrow"`, `"Add task"`.

### 5.4 Cancel, inline on the row (`CancelAsk.vue`)

No dialog, as S071 § 5.4 (no FormModal "Cancel" beside "Cancel task"). A tap on the row's cancel
icon replaces its buttons with `CancelAsk`:

- the line "Cancel this task? It stays on the record with your reason.";
- **`"Why cancel it?"`** (textarea, 2 rows, `maxlength` `CANCEL_REASON_MAX` 500,
  `frontend/src/utils/improvementLabels.js:90`, focused), help "For example: moved to the
  improvement as a countermeasure, or added by mistake." (S106 § 9 Q2's remedy);
- `"Cancel task"` (`btn-danger`, disabled while the reason is empty after trim) and `"Keep it"`.

`"Cancel task"` sends `POST /api/tickets/<id>/tasks/<task_id>/cancel` `{reason}`; the answer
replaces the page's copy. A refusal shows under the field (`reason`) or under the row (no field);
a 409 with no field also emits `reload`, and the ask closes when the reloaded task can no longer
be changed (the card's watcher on `ticket`, § 5.1); a refusal of a task still open (a 400 on the
reason) keeps the ask.

**`CancelAsk`'s contract:** props `question`, `help`, `confirmLabel`, `busy`, `error` (`{field,
message}` or null), `idSuffix`; emits `cancel(reason)` and `keep`; it holds the reason and
focuses the field when it mounts. `CountermeasureItem` passes its own texts ("Cancel this
countermeasure? …", "For example: done by another countermeasure, or added by mistake.",
"Cancel countermeasure"), so its markup, ids (`cancel-reason-<id>`) and texts stay as they are.

### 5.5 *Mark task done* (`MarkDoneDialog.vue`, generalized)

- **`open(target)`**, `target = { title, text, donePath, photosPath, placeholder, photoNote }`,
  built by two pure helpers so no caller writes a path:
  - `countermeasureDoneTarget(improvementId, action)`: "Mark countermeasure done", the action's
    text, `/api/improvements/<id>/actions/<action_id>/done`,
    `/api/improvements/actions/<action_id>/documents`, "New gasket fitted.", no note: today's
    values (`frontend/src/views/improvements/MarkDoneDialog.vue:43`, `:86`, `:125`, `:146`);
  - `taskDoneTarget(ticketId, task)`: "Mark task done", the task's text,
    `/api/tickets/<ticket_id>/tasks/<task_id>/done`, `/api/tickets/<ticket_id>/documents`,
    "Fuse F3 was blown. Fitted a new one.", "The photos go to the ticket's photos."
- Everything else stays (S071 § 5.5): the done `POST` first, `saved(detail)` at once, the photos
  one at a time with `saving` true, the close-only phase on a failed photo, `reload` after a
  photo went up or on a 409 with no field. The upload limit is read from `GET <photosPath>`
  (`upload_max_mb`, `backend/documents.py:306`).
- **Who may add the photo:** the ticket's photos are written with `ticket:raise` at the ticket's
  site, on an open ticket (`backend/documents.py:202-204`, module docstring `:24-26`).
  `ticket:raise` and `ticket:read` have the same holders (their entries in `PERMISSIONS`,
  `backend/config_rbac.py`), and
  `can_mark_done` needs `ticket:read` at the site or `ticket:assign` there (S106 § 5.4), so
  everyone offered `"Mark done"` may add the photo.
- **One race:** a photo sent after the last open task is done can meet a ticket that someone
  closed in between; the upload then fails with the server's "closed" message and the dialog
  stays in its close-only phase. Accepted: the done is saved, and the photo can no longer be
  added to a closed ticket by any path.
- **Callers:** `TasksCard` (saved → the page's copy; reload → the page's `load()` and the photos
  card's `reload()`); *Me* (both → reload the tab); the improvement page and *Me*'s
  countermeasures as today.
- **The one-tap path:** type what was done, keep *Now*, `"Add photos"` → the camera →
  `"Mark done"`.

### 5.6 The timeline (`TicketDetailView.vue`)

- `EVENT_LABELS` (`frontend/src/utils/ticketLabels.js:76`) gains the four labels of § 5.10.
  *Me › My activity* uses the same labels (`frontend/src/views/MeView.vue:220`).
- **The task's text** on a *Task changed*, *Task done* or *Task cancelled* line: a `small
  text-break` line "Task: <text>" above the remark, from `taskEventText(event, tasks)` (the
  current text of the task `e.task_id` names; "" when none). A *Task added* line's remark holds
  the text already (`task_line`), so it gets none.
- The remark shows as today (`:499`, `pre-wrap`): the change lines, the done text, the reason.
- Order: the API sends the events by `occurred_at` (`_event_rows`), so a *Task done* with a
  back-dated *Done on* sits at its own time.

### 5.7 *Close* and *Not a fault* (`TicketDetailView.vue`)

Today the significant moves have two disabled cases, each with one reason
(`frontend/src/views/TicketDetailView.vue:288-309`). They become one rule:

- `moveBlocks(move, { labourCount, partCount })` (pure) → the reasons, in this order:
  `move.blocked_reason` (S106, *Close* and *Not a fault*); "Add the labour first" (*Close*, no
  labour); "Remove the parts first" (*Not a fault*, parts recorded). Empty → the button as
  today.
- With reasons: the button disabled (`btn-outline-secondary btn-lg`), each reason a `small
  text-secondary` line under it, and `"Add labour"` beside *Close* when the labour is missing and
  the user may work (as `:293`).
- The texts "Add the labour first" and "Remove the parts first" and their markup stay, so
  `tickets-work.spec.js:94-95` and `tickets-parts.spec.js:229-231` read them as before.

### 5.8 The owner-change line of two people with the same name (Q1, KLA's gate B point)

S106 CR1-03 writes "Owner: Ravi K (person 12) → Ravi K (person 15)". A floor user cannot read a
person id alone. Under **Q1 (a2)** (recommended) or **(a)**, `task_change_line` tags each name
the way the owner picker tells two people apart, by the role at the ticket's site. Both answers:

- the tag is the person's role at the ticket's site: "Ravi K (Technician) → Ravi K (Operator)";
- an old owner who is not an active member of the site now: "Ravi K (not at this site now)",
  the words the task's row uses for the same person (§ 5.2);
- names that differ: no tag, as today.

They differ in when the person id is added as the last part of the tag:

- **(a2)** whenever the names match: "Ravi K (Technician, person 12) → Ravi K (Operator, person
  15)", "Ravi K (not at this site now, person 12) → …". The floor user reads the role; the record
  keeps the person, also after a role changes. One rule.
- **(a)** only when the two tags are the same too (two technicians of one name): "Ravi K
  (Technician, person 12) → Ravi K (Technician, person 15)"; else no id. The line then names the
  old owner by name and by the role he held on the day: after a later role change it no longer
  says which of the two people had the task (ISO 9001 § 7.5.3, § 9 Q1).

**Where the parts live.** `ROLE_WORDS` sits beside `SITE_ROLES` in `backend/config_rbac.py` (the
single source of roles; plain data, which `access_core` and `masters_core` already import): the
six site roles' words, the same as the Team dialog's (`frontend/src/utils/siteRoles.js`,
`SITE_ROLES`): Manager, Engineer, Supervisor, Technician, Operator, Storekeeper; a test in
`backend/tests/test_rbac.py` pins its keys to `SITE_ROLES`. A later step that applies Q1 to
countermeasures (§ 9) reads the same words from there, with no import cycle
(`ticket_tasks_core` imports `improvements_core`). `task_change_line(old, new)` gets
`owner_role` beside `owner_id` in both (the site role, or None for an old owner not at the site)
and words the tags itself, so the rule is unit-tested in `ticket_tasks_core`. `edit_task` takes
the new owner's role from `_check_person` (it returns `role`) and, only when the names match, the
old owner's from `person_at_site(cur, task["owner_id"], ticket["site_id"])` (`backend/tickets.py`,
by name): it asks `p.active = 1` too, so `None` gives "not at this site now", the same rule as
the screen. A plain read under the ticket's lock (7), as `_check_person`'s own read; no new lock
and no new edge (S106 § 5.6).

**Length:** the longest change line is "What to do: " 12 + 300 + 3 + 300, "Due: " 28, two line
breaks, and the owner part. Under (a): "Owner: " 7 + 2 × (100 + 2 + 30 + 1) + 3 = 276 (a tag of
at most "Storekeeper, person 4294967295", 30): 921 characters. Under (a2) the old tag can be "not
at this site now, person 4294967295" (39): 285, so 930. Both inside the remark's 1000 (S106
§ 5.5). The vendor is left out of the tag: with a 100-character vendor name the line could reach
1087.

**Who sees the role:** every reader of the ticket. Every holder of `ticket:read` holds
`ticket:raise` (their entries in `PERMISSIONS`, `backend/config_rbac.py`), and the people picker
already gives every `ticket:raise` holder each person's role at the site (`people_at_site`, S106
§ 5.7). Nothing new is shown.

### 5.9 *Me › Open work* (`MeView.vue`)

- **Load:** `GET /api/tickets/tasks/mine` in the same `Promise.all`
  (`frontend/src/views/MeView.vue:123`), on page 1 of *Open work* only, when the user has a Team
  record (`userPersonId`; the server answers an empty list without one), as `loadPmJobs`
  (`:109-113`). The tab watcher (`:79-83`) empties it with the others.
- **Order:** *PM jobs*, then **Tasks**, then *Countermeasures*, then *Tickets* (D7). Heading
  "Tasks (n)" (`h6`, `data-testid="me-tasks"`, `n` = `total`); one `TaskItem` per item with
  `showTicket`, in the server's order (by due date, so overdue first). The heading *Tickets*
  shows when any of the three lists shows (`:203`).
- **Mark done:** `markDoneDialog.open(taskDoneTarget(item.ticket.id, item))`; both events reload
  the tab; the row is gone.
- **Empty:** no tasks shows nothing for them; the tickets' empty text and the *not in Team* line
  stay (`:205-209`).
- **The default tab** stays `defaultMeTab` (`frontend/src/utils/ticketLabels.js:522`): an
  operator who owns a task lands on *Raised by me* and taps *Open work* (§ 9, assumption).
- **A load error** shows as the tab's error with `"Retry"`, as today.

### 5.10 The pure helpers (`ticketLabels.js`, `improvementLabels.js`)

- `TASK_TEXT_MAX = 300` (`ticket_tasks_core.TASK_TEXT_MAX`); `TASK_DUE_PICKS = [[0, "Today"],
  [1, "Tomorrow"], [7, "In 7 days"]]`.
- `EVENT_LABELS` gains `task_added: "Task added"`, `task_changed: "Task changed"`, `task_done:
  "Task done"`, `task_cancelled: "Task cancelled"` (§ 5.6).
- `dateInDays(days, from = new Date())` → "YYYY-MM-DD" through `toLocalDateValue`
  (`frontend/src/utils/ticketLabels.js:313`), the phone's local date, the same basis as the date
  input's `min` (as `ScheduleFields`).
- `moveBlocks(move, { labourCount, partCount })` → `[reason, …]` (§ 5.7).
- `taskEventText(event, tasks)` → the task's text or "" (§ 5.6).
- `taskOwnerMark(task)` → the mark's text or "" (§ 5.2).
- `taskDoneTarget(ticketId, task)`, `countermeasureDoneTarget(improvementId, action)` (§ 5.5).

### 5.11 Words for the floor

KLA's word *Task* (S106 D12). Plain verbs: *What to do*, *Owner*, *Due date*, *Today*,
*Tomorrow*, *In 7 days*, *Mark done*, *What did you do?*, *Done on*, *Why cancel it?*, *Keep
it*. The refusals are S106's, which say what to do next ("This ticket has 1 open task. Mark it
done or cancel it first."). The owner mark tells the engineer what to do, not why the flag is
false. Every text is short enough for a phone row; no "action item", no "CAPA".

**Against the plant** (settings: *Use on the floor*). Fault diagnosis today goes test by test,
guided by phone, and some faults take months (`docs/Plant-Facts.md:122`): each test becomes a
task with a person and a date, visible on the ticket instead of in a call. Technicians are
phone-first and engineers use phone and desktop (`:149`), mostly Android, KLA on an iPhone
(`:158`): the card and the dialogs are phone-first, with the row laid out in a line from `lg`
up. A user with no Team record owns no task: *Me* shows no *Tasks* heading and keeps its *not in
Team* line; the ticket page shows the card to them like any reader. A Tamil task text is shown
as typed (`pre-wrap`; the server counts characters, S106 § 4.1).

### 5.12 The database down

The calls go to S106's routes, which answer 503 while the database is down. The ticket page and
*Me* show their load error with `"Retry"`; a dialog shows the error at the top; the inline cancel
shows it under the row; a photo upload's 503 shows on its photo row (§ 5.5).

## 6. API

None new. S106 § 6 as built: the detail's `tasks`, `task_counts`, `can_add_task`,
`events[].task_id`, `moves[].blocked_reason`; the four task routes; `GET /api/tickets/tasks/mine`;
`GET /api/tickets/people`; the ticket's documents routes. Two texts change: an empty due date
on the add and change routes is refused with "Choose the due date" (`due_date`, 400; § 5.3), and
under Q1 (a) or (a2) the `task_changed` remark of a same-name owner change reads as § 5.8.

## 7. Design decisions

- **D1. The screens follow S071's countermeasure screens** (a card of rows, one add/change
  dialog, *Mark done* with photos, the inline cancel, the same rows on *Me*). The plant learns one
  pattern for "work given to a person with a date". Rejected: a page of its own for tasks (the
  ticket stays the one work order, EN 13306).
- **D2. Cancel asks on the row, not in a dialog.** S106 § 1's outline names a *Cancel task*
  dialog; S071 D7's reason holds here too: a dialog's FormModal `"Cancel"` would sit beside
  `"Cancel task"`. A departure from the outline, not from a decision.
- **D3. A new `TaskItem`, with the inline cancel taken out into `CancelAsk`.** A task has no
  kind, no photos of its own and no lesson, and has the owner mark and the ticket line; one
  component for both would branch on most of its lines. The cancel block is the one part that
  would be copied, so it becomes a component both rows use (DRY). The row's layout CSS (about 40
  lines) is the row's own, as each list row in the app has its own scoped CSS. Rejected:
  `CountermeasureItem` with a `task` mode; a copy of the cancel block.
- **D4. One *Mark done* dialog for both, opened with a target.** The dialog's done-then-photos
  sequence (about 200 lines, S071 BR1-02, BR2-01, BR2-03) is the same; only the title, the text,
  the two paths and the hints differ. It stays in `views/improvements/`. Rejected: a copy in
  `views/tickets/`; moving it to `components/` (it imports `views/tickets/EventFields.vue`, and
  the move changes two more imports for nothing the user sees).
- **D5. No default due date; three quick picks.** A task is near-term diagnosis, and a default
  the engineer never looked at would make the overdue mark (and the third step's alert) fire on a
  date nobody chose. *Today / Tomorrow / In 7 days* make the date one tap (S106 § 9
  assumption). Rejected: a default of 7 days (S071 D6's two weeks suits countermeasures, which
  run for weeks); no picks (a date picker on a phone takes three taps).
- **D6. The card sits after *Details / Times / Assigned*, before the meters and parts.** It is
  the plan of the work, next to who is assigned. Rejected: above the details (pushes the machine
  and the symptom below the fold for everyone); after the timeline (a technician scrolls past
  the history to find his job).
- **D7. On *Me*, tasks come after PM jobs and before countermeasures.** A task holds its ticket
  open (S106 D4) and is due in days; a countermeasure runs for weeks after the ticket is closed.
  Rejected: after the countermeasures (the most urgent list below the least urgent one).
- **D8. The owner mark only for the people who can change the task.** It tells the engineer to
  record for the owner or pick another (`docs/Plant-Facts.md:156`: the fitter without a phone, a
  supervisor or engineer records for him); to a technician it would be noise. Rejected: for every reader.
- **D9. The owner is picked with the ticket's people picker**, not a plain select as on a
  countermeasure: a site can have a hundred names, and the picker puts the ticket's assignees
  and the user first (S018 § 5.8). The list is already loaded for `ticket:assign` holders.
- **D10. Q1: the role tells two owners of one name apart** (§ 5.8), as the picker does; the
  person id stays always (a2, recommended: the record keeps the person after a role change) or
  only when the roles match too (a). KLA picks at gate A (§ 9 Q1).
- **D11. Close reasons in one pure function** (`moveBlocks`), so *Close* can say both "open
  tasks" and "no labour" at once, and the three reasons are unit-tested in one place.
- **D12. `e2e/support/tickets.js` gains the task set-up helpers.** Two specs add tasks by API
  and tidy them up; one copy (DRY). It is shared e2e code, so it runs the WebKit screens check
  once (§ 8.3). Rejected: a helper copied into each spec.
- **D13. The server says "Choose the due date"** (§ 5.3), so the dialog has no rule of its own
  and the refusals come in field order. Rejected: a check in the dialog (it answered the last
  field first); the same check of all three fields in the dialog (two of S106's messages
  would exist twice).

## 8. Tests and acceptance

Seed people (`tooling/e2e/seed_e2e.py:37-48`; the role in brackets is part of each seed name):
"Muthu (operator)" (MCC2), "Kannan (technician)" and "Ravi (technician)" (all units), "Priya
(engineer)", "Devi (storekeeper)" (a login, no `ticket:read`), "Ramesh (operator, no phone)" (no
login). The extruder is at SMTW.MCC2. Each test makes its own tickets and finds its tasks by
`data-task` or text, never by position or a count (own records only, S100). Every dialog a test
opens calls `expectDialogFits`. One test is `@device` (test 8, a layout check); the others are
logic tests (a fit helper in a flow test does not tag it).

### 8.1 Automated: `frontend/e2e/tickets-tasks.spec.js` (new)

Set-up, two helpers of the spec, each pushing the ticket's id onto `raised`:
- `fixedTicket(description)`: `raiseFixed(seed.extruder.id, …)`
  (`frontend/e2e/support/improvements.js:19`, a back-in-service defect, as TK-2026-11-008; it
  offers *Close*, never *Not a fault*: `tickets_core.MOVES`) and a labour row by API (`POST
  /api/tickets/<id>/labour`, as `labourByApi` in `tickets-parts.spec.js`), so only the tasks block
  *Close*;
- `raisedDefect(description, extra)`: `raiseByApi("operator", …)` on the extruder, state
  *Raised* (it offers *Not a fault*, never *Close*).

The `afterEach`, as the `afterEach` of `tickets-parts.spec.js`, which looks at the state: for
each ticket not closed, `cancelOpenTasksByApi(id)` (as admin), then a ticket back in service is
closed with `close` (cause 3.4, action 1, the first failure mode; it has its labour row), any
other with `not-a-fault` (cause 5.1).

1. **important** S107: the TK-2026-11-008 flow (KLA's gate B acceptance for S106), on a
   `fixedTicket`. The engineer opens the ticket: *Tasks* reads "No tasks yet." `"Add task"` →
   "Check the space heater circuit diagram and find any fuse", Kannan in the picker,
   `"Tomorrow"`, `"Add task"`: the row shows the text, "Owner: Kannan (technician)", "due
   <tomorrow>", *Open*; the header "Tasks (0 of 1 done)". The second: "Get the VCB supplier to
   inspect the panel", Priya (under *You*), `"In 7 days"`: "Tasks (0 of 2 done)". *Close* is
   disabled with "This ticket has 2 open tasks. Mark them done or cancel them first." The
   timeline has two *Task added* lines. Kannan opens *Me*: his row under "Tasks (n)" with the
   ticket's serial; `"Mark done"`, title "Mark task done", "Fuse F3 was blown. Fitted a new
   one.", keeps *Now*, adds `TEST_PHOTO`, `saveDialog(page, "Mark done")`: the row leaves *Me*.
   The engineer opens the ticket: Kannan's row *Done* with the text; "Tasks (1 of 2 done)"; the
   *Photos* card holds `test-photo`; *Close* says "This ticket has 1 open task. Mark it done or
   cancel it first."; the timeline's *Task done* line shows "Task: Check the space heater…" and
   the done text. The engineer marks his own task done on the ticket page; *Close* is enabled;
   he closes the ticket (cause, action, symptom as `tickets-work.spec.js:116-121`): *Closed*, and
   no task row has a button.
2. **important** S107: change and cancel; *Not a fault* waits for the task. On a
   `raisedDefect`, the engineer adds a task for "Ramesh (operator, no phone)": its row shows "No
   login: mark it done for them."; *Not a fault* is disabled with "This ticket has 1 open task.
   Mark it done or cancel it first." `"Change task 1"`: picks Ravi, `"In 7 days"`, `"Save
   task"`: "Owner: Ravi (technician)", the mark gone; the timeline's *Task changed* line holds
   "Owner: Ramesh (operator, no phone) → Ravi (technician)". `"Cancel task 1"`: "Why cancel it?"
   "Moved to the improvement as a countermeasure", `"Cancel task"` (`exact: true`): *Cancelled*
   with the reason; the header reads "Tasks"; the *Task cancelled* line shows the reason; *Not a
   fault* is enabled, with no reason under it.
3. S107: the owner marks, on a `raisedDefect`. A task for "Devi (storekeeper)" shows "May not see
   this ticket. Mark it done for them, or choose another owner."; a task for Ramesh marked done by
   the engineer (`markTaskDoneByApi`) shows "recorded by Priya (engineer)". The operator Muthu
   opens the ticket: Devi's row shows no owner mark (he cannot change the task).
4. S107: who sees which buttons. A task of Kannan's: Ravi (a technician, not the owner) sees the
   row and no `"Mark done"`, change or cancel button and no `"Add task"`; Kannan sees `"Mark
   done"` on it and no change or cancel; the operator Muthu sees the card and no button.
5. S107: refusals, in field order. `"Add task"` on the empty form: "Enter what to do" beside
   *What to do* (`expectFieldMessage`); with a text and Kannan picked, no date: "Choose the due
   date" beside *Due date* (the server's, § 5.3). The test allows the 400
   (`consoleWatch.allowFailedRequest("/tasks", 400)`).
6. S107: overdue. A `raisedDefect` 3 days back (`occurred_at: istLocal(3 * 24 * 60)`; the raise
   allows 7 days back, `tickets_core.MAX_BACKDATE_DAYS`), a task due `istDay(-2)` by API: the row
   shows "Overdue 2 days" (`text-bg-danger`). Real data, no `page.route`.
7. S107: a cancel refused because the owner marked the task done meanwhile shows the row done,
   with no cancel ask left (the twin of S071's test in `improvements.spec.js`). On a
   `raisedDefect` with Kannan's task by API, the engineer taps `"Cancel task 1"` and types a
   reason; Kannan marks it done by API (`markTaskDoneByApi`, as `"technician"`); `"Cancel task"`
   (`exact: true`): the row reads *Done*, has no "Cancel this task?" and no "Why cancel it?"
   field. The test allows the 409 on `/api/tickets/<id>/tasks/<task_id>/cancel`.
8. S107: the ticket page with the Tasks card has no sideways scroll (`@device`, as S052's test of
   the Meters card in `tickets-work.spec.js`). Set-up by API: a `raisedDefect` with a task of
   Kannan's whose text is 300 characters without spaces. The engineer opens the ticket: the row
   shows `"Mark done"`, change and cancel; `expectNoSidewaysScroll`; `"Cancel task 1"`: the ask
   is open; `expectNoSidewaysScroll` again. It runs on the desktop at Normal and on the iPhone at
   Full, where the row has its `lg` layout and Safari's widths.

### 8.2 Automated: `frontend/e2e/me.spec.js` and the unit suites

`me.spec.js` (each S107 test raises through `raiseDefect`, state *Raised*; the overdue one through
`raiseByApi` with `occurred_at`, its id pushed onto `raised`; so the changed `afterEach`, cancel
then *Not a fault*, fits them all). A task's row is found by `li[data-task="<id>"]` inside
`me-tasks`, never by the file's `rowOf(page, serial)`, which also matches a task row (a
`.list-group-item` holding the serial):
- S107: Kannan's task on *Me › Open work*: "Tasks (n)" (`me-tasks`) above the heading *Tickets*;
  his row shows the text, the ticket's serial and machine, `"Mark done"`, no change or cancel
  button; the serial link opens the ticket page.
- S107: an overdue task (set-up as § 8.1 test 6): "Overdue 2 days" on a `list-group-item-danger`
  row.
- The `afterEach` (`frontend/e2e/me.spec.js:23-38`) cancels the open tasks of each raised ticket
  before *Not a fault*, which S106's close block refuses otherwise.

`frontend/tests/ticketLabels.test.js`: the four task labels; `dateInDays` (0, 1, 7, across a
month end); `moveBlocks` (each reason alone, *Close* with tasks and no labour gives both, a move
with `blocked_reason: null` and labour gives none); `taskEventText` (a known id, an unknown id,
an event without `task_id`); `taskOwnerMark` (no login, no access, not at the site, can open,
`can_change` false); `taskDoneTarget`'s paths.
`frontend/tests/improvementLabels.test.js`: `countermeasureDoneTarget` gives today's title, paths
and placeholder.

Backend, any Q1 answer (the empty due date, § 5.3):
- `backend/tests/test_ticket_tasks_core.py`, `TestValidateTask`:
  `test_a_missing_field_on_an_add_gives_its_first_message` and
  `test_null_is_refused_on_add_and_change` expect `DUE_NEEDED`; `test_the_due_date_is_yyyy_mm_dd`
  loses its `""` case; a new test: `""`, `"   "`, `None` and a missing field on an add give
  "Choose the due date", and a change without the field stays valid.
- `backend/tests/test_ticket_tasks_api.py::TestAdd::test_a_bad_body_is_400` gains `due_date=""`
  → (400, `due_date`, "Choose the due date").

Backend, Q1 (a) or (a2) (§ 5.8):
- `backend/tests/test_ticket_tasks_core.py`, `TestLines`:
  `test_an_owner_of_the_same_name_is_told_apart_by_the_person_id` becomes the cases of § 5.8 for
  the answer KLA picks (different roles, same roles, old owner not at the site, different names
  untagged); `test_the_longest_change_line_with_ids_fits_the_remark` checks the longest line (921
  under (a), 930 under (a2)).
- `backend/tests/test_ticket_tasks_api.py::TestChange::test_an_owner_of_the_same_name_keeps_both_in_the_line`
  (two technicians) expects "(Technician, person …)" on both; two new cases: a technician → an
  operator of the same name ("Same Name (Technician) → Same Name (Operator)" under (a), each with
  ", person …" under (a2)), and an old owner made inactive ("Same Name (not at this site now…)").
- `backend/tests/test_rbac.py::TestRoleSources`: a new test pins `ROLE_WORDS`' keys to
  `SITE_ROLES` and its six words.

### 8.3 Existing tests that run again, and the runs

- `frontend/e2e/tickets-work.spec.js:94-95` and `frontend/e2e/tickets-parts.spec.js:229-231`:
  the close reasons keep their text, markup and disabled button (§ 5.7).
- `frontend/e2e/improvements.spec.js:451-456` and `frontend/e2e/me.spec.js:175-181`: *Mark done*
  of a countermeasure through the generalized dialog (same title, text and button); the S071
  cancel tests (`"Cancel countermeasure"`, "Why cancel it?") through `CancelAsk`.
- `frontend/e2e/tickets-raise.spec.js`, `journeys.spec.js`: untouched screens; `screens.spec.js`
  runs again because the ticket page and *Me* changed.
- "S034: In 14 days fills the date …" (`tickets-work.spec.js`) taps a `ScheduleFields` quick
  pick, now through `dateInDays`.
- `frontend/tests/ticketLabels.test.js:130`: every move's event has a label; the four new keys
  add to it.
- **Targeted runs:** `tooling/run-e2e-tests.bat e2e/tickets-tasks.spec.js e2e/me.spec.js
  e2e/improvements.spec.js e2e/tickets-work.spec.js e2e/tickets-parts.spec.js e2e/screens.spec.js`.
- **Shared code:** `e2e/support/tickets.js` changes, so the whole suite runs at Normal once at the
  end (which the step's coding asks anyway) and `tooling/run-e2e-tests.bat e2e/screens.spec.js
  --project=phone-webkit` once (Docker Desktop running).
- Unit: `tooling/run-frontend-tests.bat`, `tooling/run-backend-tests.bat
  tests/test_ticket_tasks_core.py tests/test_ticket_tasks_api.py tests/test_rbac.py` while
  coding; all suites once at the end; `npx vite build`.

### 8.4 Acceptance

- All unit suites green; `npx vite build` clean; the targeted specs green; the whole browser
  suite at Normal green once at the end; the WebKit screens run green.
- § 8.1 test 1, the TK-2026-11-008 flow, passes on `phone-chromium` (KLA's gate B condition for
  S106).
- Every new dialog fits a phone (`expectDialogFits` in the flows).

### 8.5 On a real device

- **important** *Mark task done* with the camera, gloved. On an **Android phone**, as a
  technician: open *Me*, the task row's `"Mark done"`, `"Add photos"` → the camera → a photo of
  a panel; the thumbnail shows; `"Mark done"`; the photo shows in the ticket's *Photos* card.
  With a work glove on: `"Mark done"` on the row, the *Now* tick and the dialog's `"Mark done"`
  hit at the first tap. Account: a technician's login at the site. Network: the plant Wi-Fi.
  Where: either; on production, KLA prepares an open ticket on the TEST machine with a task owned
  by the test login. Row 51 of `docs/steps/device-checks.md` (S071, a countermeasure's *Mark
  done* with the camera and a glove) is the same dialog: both can be done in one sitting.
- The iPhone keyboard over *Add task*. On the **iPhone**, as an engineer: `"Add task"`, type in
  *What to do*, then in the owner filter: the field being typed in stays in view above the
  keyboard, and `"Add task"` is reachable by scrolling the dialog. Account: an engineer's login.
  Network: any. Where: the dev server on KLA's laptop.

## 9. Open questions and assumptions

**Q1. The owner-change line when two people share a name** (KLA's gate B point 1 for S106: "this
step decides what the screen shows"). Today: "Owner: Ravi K (person 12) → Ravi K (person 15)".
- **(a2) Recommended:** the role at the ticket's site and the person id, whenever the names
  match: "Ravi K (Technician, person 12) → Ravi K (Operator, person 15)" (§ 5.8). The floor user
  reads the role; the record keeps the person, also after a role changes. One rule. Costs a
  small change in `ticket_tasks_core.py`, `tickets.py` and `config_rbac.py` and their tests; the
  line stays within 1000 characters (930).
- (a) The role only, and the id only when the roles match too: "Ravi K (Technician) → Ravi K
  (Operator)". Easier to read, the same files. What it gives up: `ticket_tasks` keeps only the
  current owner, so this line is the only record of the old one. It names him by name and by the
  role he held on the day; after a later role change (an operator becomes a technician) the line
  no longer says which of the two people had the task. ISO 9001 § 7.5.3 asks that the record
  shows who did what; under (a) it does so only while both roles stay as they were.
- (b) Keep the line as written; the screen shows the id. No change for Q1; a floor user reads
  two equal names and two numbers.
- (c) The screen hides the ids ("Ravi K → Ravi K"): the record then shows no change at all.
  Rejected (ISO 9001 § 7.5.3).
Under (b) `tickets.py`, `config_rbac.py` and `test_rbac.py` drop out, and the same-name tests of
§ 8.2 (20 files).

**Gate A answer, Q1** (KLA, 22-11-2026): "too rare a case. keep the code." — option **(b)**: the owner-change line stays as S106 writes it (with the person ids); no change in `tickets.py`, `config_rbac.py` or `test_rbac.py` for Q1, and § 5.8's same-name rules and tests drop out (20 files). D10 is answered by (b).

**Size.** 23 code and test files, one concern (the screens); under the 25-file mark. No split.

**SMTW-Review point:** none proposed. The screens add no invariant beyond S106's point *Ticket
tasks (S106)*; every control follows the server's flags, which the audit checks on the API.

**Assumptions**
- S106 is adopted (committed) before S107 is coded; this brief cites S106's code as it stands in
  the working tree on 22-11-2026.
- An operator who owns a task lands on *Raised by me* (`defaultMeTab`: *Open work* only for
  `ticket:work` holders) and taps *Open work*; the third step's *Task for you* alert brings them
  to the ticket. Not changed, as S071 § 9.
- The task's text is not on *Me › My activity* (§ 1, *Out of scope*).
- EN 13306 term numbers are *to verify*.
- No architecture doc: the repo's step settings have no *Architecture* entry.

**Found while checking, not part of this step:** a countermeasure's owner change between two
people of the same name writes no owner line at all: `improvements._action_edit_line` shows the
owner by name only and hands both to `edit_lines`, which drops an unchanged value
(`backend/improvements.py:1335-1350`). This is the case S106 CR1-03 fixed for tasks. A candidate
for a small step that applies Q1's answer to countermeasures too.

## 10. Amendments

None.

## Review log

| Finding | Severity | Answer |
|---|---|---|
| BR1-01 | minor | Accepted (a). Test 1 stays on a back-in-service ticket and asserts *Close* only; test 2 runs on a raised defect and asserts *Not a fault* disabled with the reason, then enabled after the cancel. The spec's `afterEach` follows `tickets-parts.spec.js`' (close a back-in-service ticket, *Not a fault* for the rest); § 8.2 says why `me.spec.js`' `afterEach` fits its S107 tests. § 1, § 8, § 8.1, § 8.2. |
| BR1-02 | minor | Deferred — to the user. (a2) added to § 9 Q1 and recommended; (a)'s consequence under ISO 9001 § 7.5.3 stated; § 5.8 gives both rules and both lengths (921, 930: (a2)'s "not at this site now, person …" tag is 39 characters); D10 names the choice. KLA picks at gate A. |
| BR1-03 | minor | Accepted (a), for both (a) and (a2). `ROLE_WORDS` beside `SITE_ROLES` in `config_rbac.py`, its test in `test_rbac.py::TestRoleSources`; `task_change_line` gets `owner_role` and words the tags; the old owner is read through `person_at_site` (active members only), so `None` gives "not at this site now", as the row does. § 3, § 5.8, § 8.2. |
| BR1-04 | minor | Accepted (a). The card watches its `ticket` prop and closes a stale ask (§ 5.1, § 5.4); new § 8.1 test 7, the twin of S071's test. |
| BR1-05 | minor | Accepted (a). `validate_task` refuses a missing, null or blank due date with "Choose the due date" (`DUE_NEEDED`); the dialog has no rule of its own; refusals come in field order. § 1, § 3, § 5.3, § 6, D13 (new), § 8.1 test 5, § 8.2 backend tests. |
| BR1-06 | minor | Accepted (a). New `@device` test 8 with the 300-character text, the three buttons and the cancel ask; the check is out of test 2; § 8's intro no longer says "no `@device`". |
| BR1-07…BR1-15 | nit | Accepted: `PLANNED_DATE_MAX_DAYS` (§ 5.3); seed names marked as names, rules use "<name>", badge words from `ACTION_STATE_LABELS` (§ 2, § 5.2, § 5.3, § 8); `EVENT_LABELS` at `ticketLabels.js`, the four labels in § 5.10; `path: null`, `send` with its own URLs, the 409 watcher on `error` (§ 5.3); Muthu's no-mark check on Devi's open task (test 3), `can_change` false in `taskOwnerMark`'s tests; `li[data-task]` and why not `rowOf` (§ 8.2); the S034 "In 14 days" test (§ 8.3); `config_rbac.py` anchored by name (§ 5.5, § 5.8); device row with S071's row 51 (§ 8.5). |

## Feedback

- hindrance: the facts run reported `TestChange::test_an_owner_of_the_same_name_keeps_both_in_the_line`
  as "4 test files define it": it matched the class `TestChange` in four files, while the method is
  in one; a test id written with its file path is needed to read it right
  (`scratch/brief-facts-S107.md`, *Test ids*; one extra grep, about 2 minutes).
- rule: the size rule's 600 lines meets a screens brief that follows its pattern step (S071, 529
  lines) and adds a gate-B question with a backend change; the draft is 640 lines with one concern
  and nothing to cut apart. Whether a brief over 600 lines with one concern still needs a split
  proposal is not said (`.claude/agents/brief-writer.md`, *Size*).
- hindrance (round 1 answers): the facts run does not list a code name written right after a
  possessive on a backticked file ("`tickets-parts.spec.js`' `labourByApi`"): `labourByApi` was in
  neither the defined nor the not-found list; rephrased to "`labourByApi` in `tickets-parts.spec.js`"
  (`scratch/brief-facts-S107.md`, *Code names*; about 2 minutes).
- idea (round 1 answers): BR1-01 came from a move's states (`tickets_core.MOVES`) that the
  self-check did not read; self-check item 5 could ask, for each set-up helper a test plan uses
  (`raiseFixed`, `raiseDefect`), which state the ticket is in and which moves that state offers.
