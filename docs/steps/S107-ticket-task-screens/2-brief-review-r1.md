```
Step: S107 — Ticket tasks: screens
Doc: brief-review r1
Author: Brief reviewer (Fable 5.2)
Date: 22-11-2026
```

Reviewed against: 8644720 + uncommitted S106

**Verdict:** no `blocker` or `major` finding is open. Six `minor` findings and nine nits. The
field names, the routes, the flags and the messages the brief takes from S106 match S106's code as
it stands in the working tree. The two shared-component changes (`CancelAsk`, `MarkDoneDialog.open(target)`)
keep the markup and texts the S071 specs read. The largest finding is in the test plan: the
acceptance test and the new spec's tidy-up expect *Close* and *Not a fault* on the same ticket,
which the app never offers (BR1-01). The facts file `scratch/brief-facts-S107.md` was given and
used. This is round 1: the whole brief was read. The repo's settings have no *Architecture* entry,
so nothing was checked against an architecture doc.

## BR1-01 (minor) § 8.1 set-up and test 1: *Close* and *Not a fault* are never on the same ticket

**Problem.** `tickets_core.MOVES` offers `close` only from *Back in service*, and `not-a-fault`
only from *Raised*, *Acknowledged*, *On hold* and *In progress*. A ticket never shows both buttons.
The new spec raises its tickets with `raiseFixed`, which makes a ticket that is back in service.
Two statements of § 8.1 then cannot hold:

- Test 1: "*Close* is disabled with … ; *Not a fault* too." The page has no *Not a fault* button
  on that ticket.
- The set-up: "An `afterEach` cancels each test ticket's open tasks … and closes it with *Not a
  fault*, as `me.spec.js:23-38`." The server refuses `not-a-fault` on a ticket that is back in
  service, so the `afterEach` fails after every test of the spec. `me.spec.js` gets away with it
  because its `raised` list holds only tickets from `raiseDefect` (state *Raised*); its
  `raiseFixed` tickets (`kannansMeasure`) are not in the list.

**Why it matters.** Test 1 is KLA's acceptance for S106 and S107 (§ 8.4). As written it cannot
pass, and the coder would have to decide alone where *Not a fault*'s reason is tested. § 1 item 7
and § 5.7 are right (each button waits in its own states); only the tests are wrong.

**Options.**
- (a) **Recommended.** Test 1 stays on a `raiseFixed` ticket and asserts *Close* only. A second
  test on a plain raised defect (test 2 already needs a ticket; `raiseByApi` as `me.spec.js`'s
  `raiseDefect`) asserts *Not a fault* disabled with the reason, and enabled after the task is
  cancelled. The `afterEach` follows `tickets-parts.spec.js`'s `afterEach`, which already looks
  at the state: after `cancelOpenTasksByApi`, a ticket that is back in service is closed with
  `close` (cause, action, symptom; it has the labour row), any other with `not-a-fault`.
- (b) The `afterEach` only cancels the open tasks and leaves the tickets open, as `me.spec.js`
  leaves its `raiseFixed` tickets. Shorter, but the tickets pile up on the extruder.

Also say in § 8.2 that the S107 tests of `me.spec.js` raise through `raiseDefect`, so the changed
`afterEach` there (cancel, then *Not a fault*) is right for them.

## BR1-02 (minor) § 9 Q1, § 5.8: option (a) drops the one thing that identifies the old owner

**Problem.** The three options are sound in their mechanics. I checked (a): `_check_person`
returns the role; `memberships` has one row per person and site; `people.name` has no unique
index, so the case is real; the role already goes to every `ticket:raise` holder through
`people_at_site`; the 921 characters are right. One consequence of (a) is not stated. `ticket_tasks`
keeps only the current owner, so the old owner's identity lives only in this line. Under (a) the
line names him by name and by the role he held on the day of the change. Roles change (an
operator becomes a technician). After such a change "Ravi K (Technician) → Ravi K (Operator)" no
longer says which of the two people had the task.

**Why it matters.** § 2 cites ISO 9001 § 7.5.3 for this line: "the record still says which person
had the task". Under (a) that holds only while both roles stay as they were. KLA decides Q1 at
gate A and should see this.

**Options.**
- (a) As written, with the consequence stated in Q1.
- (a2) **Recommended.** The role and the id whenever the names match: "Ravi K (Technician, person
  12) → Ravi K (Operator, person 15)". The floor user reads the role; the record keeps the person.
  It is one rule instead of two (no "only when the roles match too" branch), and § 5.8's length
  figure already counts this form.
- (b), (c) as in the brief.

Add (a2) to Q1, or state under (a) what it gives up.

## BR1-03 (minor) § 3 Backend, § 5.8: where `ROLE_WORDS` lives, and how the old owner's role is read

Applies under Q1 (a) or (a2).

**Problem 1.** The brief puts `ROLE_WORDS` in `ticket_tasks_core.py`. The role words are not a
task rule: they name `config_rbac.SITE_ROLES`, and the repo's rule is that `config_rbac.py` is the
single source of roles. § 9 already names a second use: the candidate step that applies Q1's
answer to countermeasures. That code is `improvements.py` / `improvements_core.py`, and
`ticket_tasks_core` imports `improvements_core` (its docstring: `ticket_tasks_core ->
improvements_core -> tickets_core`). `improvements_core` cannot import the words back without a
cycle.

**Problem 2.** The brief reads the old owner's role with a new query, `SELECT role FROM
memberships WHERE person_id = %s AND site_id = %s`. `tickets.person_at_site(cur, person_id,
site_id)` already does this and also asks `p.active = 1`. With the new query an inactive old owner
who still has his membership row gets his role as the tag, while the task's row on the screen
calls the same person "(not at this site now)" (`!owner.active || !owner.may_own`, § 5.2). An
owner who left is the usual reason for an owner change.

**Options.**
- (a) **Recommended.** `ROLE_WORDS` beside `SITE_ROLES` in `config_rbac.py` (plain data;
  `access_core` and `masters_core` already import that module), its test in `test_rbac.py`;
  `task_change_line` takes the two tags as arguments. The old owner through `person_at_site`:
  `None` gives "not at this site now", the same rule as the screen.
- (b) Keep both as written, and move the words when the countermeasure step comes.

## BR1-04 (minor) § 5.1, § 5.4, § 8.1: the stale cancel crosses a component boundary and has no test

**Problem.** § 5.4 points at `closeStaleCancel` (`ImprovementDetailView.vue`). There the page
makes the cancel call and reloads itself, so it runs `load().then(() => closeStaleCancel(id))`. In
this step the card makes the call and the page reloads (`emit("reload")`). The card cannot wait
for the page's `load()`. The brief does not say how the card learns that the reload is done.
§ 8.1 has no test of this path, and none of any other 409 (a task done or cancelled meanwhile, a
ticket closed meanwhile).

**Why it matters.** S071 got this logic from a code-review finding (CR2-01): without it the row
reads *Done* and still shows "Cancel this task?". The card holds a second copy of that logic, with
a different trigger, and nothing checks it.

**Options.**
- (a) **Recommended.** State the mechanism: the card watches its `ticket` prop, and when the task
  of `cancellingId` is no longer `can_change` it closes the ask (this covers the reload and a
  `saved` from another control). Add one test, the twin of "S071: a cancel refused because the
  owner marked it done meanwhile …" (`improvements.spec.js`): the engineer opens the ask, Kannan
  marks the task done by API, `"Cancel task"` → the row reads *Done* and has no ask; the test
  allows the 409.
- (b) A small composable for the ask's state, used by `TasksCard` and `ImprovementDetailView`.
  One copy, but it changes the improvement page for no gain the user sees. Not recommended now.

## BR1-05 (minor) § 5.3: the dialog's own due-date check answers before the fields above it

**Problem.** The dialog refuses an empty due date itself, before any request. The server checks
the text first, then the owner, then the date (`validate_task`; `clean_body` sends the first
error). A user who taps `"Add task"` on an empty form reads "Choose the due date" (the last
field), fixes it, then "Enter what to do" (the first field), then "Choose the owner". The
messages come in an order that does not follow the form. The reason for the dialog's own check is
real: the server's words for an empty date are "Enter the date as YYYY-MM-DD", wrong for a field
with quick picks.

**Options.**
- (a) **Recommended.** The server says it: in `validate_task`, a missing, null or empty due date
  gets "Choose the due date"; a value that is not a date keeps the format message. The dialog has
  no rule of its own, and the three messages come in field order. Cost: one branch and its unit
  test in `ticket_tasks_core.py`, a file this step already changes under Q1 (a), and S106 § 5.2's
  line on that message changes. Test 5 then allows the 400 for both cases.
- (b) The dialog checks the three empty fields itself, in field order, with the server's words (a
  pure helper with a unit test). No backend change; two of S106's messages then exist twice.
- (c) Keep it as written.

## BR1-06 (minor) § 8: the new row's layout is checked on the Android phone only

**Problem.** § 8 says no test is `@device`. The only layout check, `expectNoSidewaysScroll` after
a 300-character text, sits inside flow test 2, so it runs on `phone-chromium` alone. `TaskItem`
has a second layout from `lg` up (about 40 lines of scoped CSS with flex order, § 5.2), and
engineers use the desktop (`docs/Plant-Facts.md:149`). No test opens the card on
`desktop-chromium` or on the iPhone.

**Why it matters.** The settings' *Layout tag* rule is made for this: a test whose purpose is a
layout check is tagged, and runs on the desktop at Normal and on the iPhone at Full. S052 did it
for its new card on the same page ("S052: the ticket page with the Meters card has no sideways
scroll", `tickets-work.spec.js`).

**Options.**
- (a) **Recommended.** Move the check into its own `@device` test: "S107: the ticket page with
  the Tasks card has no sideways scroll", with a 300-character text without spaces, an open row
  with its three buttons, and the cancel ask open. Set-up by API.
- (b) Keep it in the flow test, and accept that the desktop row is seen first by a user.

## Nits

- **BR1-07** (nit) § 5.3: `max` is `dateInDays(PLANNED_DATE_MAX_DAYS)`, the constant
  `ticketLabels.js` already exports and `ScheduleFields` uses, not a literal 365.
- **BR1-08** (nit) § 2, § 5.2: "Owner: Kannan (technician)", "recorded by Priya (engineer)" and
  "by Priya (engineer)" read like a name with a role tag, next to § 5.8's real role tags. The
  role is part of the seed's names; `tasks[].owner` sends no role. Use a plain name in the rules,
  or say so once. Name the badge's label map too: reuse `ACTION_STATE_LABELS`.
- **BR1-09** (nit) § 5.6, § 5.10: `EVENT_LABELS` is in `ticketLabels.js`, not in
  `TicketDetailView.vue`; list the four labels in § 5.10.
- **BR1-10** (nit) § 5.3: say that the dialog passes `path: null` and saves through `send` with
  its own URLs, as `ActionDialog` does (`useFormModal.save()` builds `${path}/${id}` from one
  fixed path), and that the 409 reload is a watcher on `error`, as in `MoveDialog`.
- **BR1-11** (nit) § 8.1 test 4, § 8.2: Muthu's "no owner mark" is checked on Kannan's task, which
  has no mark for anyone. Check it on Ramesh's or Devi's task (test 3). Add the case "`can_change`
  false" to `taskOwnerMark`'s unit tests.
- **BR1-12** (nit) § 8.2: the S107 tests of `me.spec.js` find the task's row by `li[data-task]`.
  The file's `rowOf(page, serial)` also matches a task row (a `.list-group-item` that holds the
  serial).
- **BR1-13** (nit) § 8.3: the existing test that taps a quick pick of `ScheduleFields` is "S034:
  In 14 days fills the date …" (`tickets-work.spec.js`), not an "In 7 days" one; no test line
  uses that text today.
- **BR1-14** (nit) § 5.5, § 5.8: `backend/config_rbac.py:105-106` is a line anchor in a file
  S106 changes; anchor by name (the `"ticket:read"` and `"ticket:raise"` entries of
  `PERMISSIONS`), README § Anchors by name.
- **BR1-15** (nit) § 8.5: row 51 of `docs/steps/device-checks.md` (S071) is the same dialog with
  the camera and a glove. Say in the new row that both can be done in one sitting.

## Standards (settings: *Standards*)

The brief names four and cites each correctly.
- **TPM, the abnormality tag and visual control**: a found defect carries a tag with who acts and
  by when until it is fixed, and its state shows at a glance. The card and the red *Overdue* badge
  follow it.
- **EN 13306**: corrective maintenance has the steps *fault diagnosis* and *fault correction*;
  work that waits is *deferred*. A task is one such step. The term numbers stay "to verify".
- **ISO 9001 § 7.5.3**: records are kept, protected from change and show who did what and when.
  Cancel keeps the row with its reason; "recorded by" names the recorder. BR1-02 is about this
  clause.
- **ISO 27001 A.5.15**: each person gets only the access the work needs. Every control follows a
  server flag; the claim "everyone offered *Mark done* may add the photo" holds (below).

## Checked and found consistent

- **S106's API as built** (`backend/tickets.py`, `backend/ticket_tasks_core.py`): the detail's
  `tasks` entries (`owner.{id, name, active, has_login, may_own, can_open}`, `due_date`, `state`,
  `overdue_days`, the done and cancelled fields, `can_change`, `can_mark_done`), `task_counts`
  (`{open, done, cancelled, overdue}`, the shape `actionCountsText` reads), `can_add_task`,
  `events[].task_id`, `blocked_reason` on `close` and `not-a-fault`; the four routes and their
  bodies; the `mine` item (`id, text, due_date, overdue_days, can_mark_done, ticket{…machine}`);
  every message § 5.3 quotes.
- **Photos at *Mark done***: the ticket's documents are written with `ticket:raise` at the
  ticket's site, never on a closed ticket; `ticket:read` and `ticket:raise` have the same holders;
  engineers and IT admin hold both. `usePhotoUploads` posts kind `photo` to the path it is given.
- **`CancelAsk`**: the block it replaces renders under `v-if="cancelling"`, so "holds the reason
  and focuses the field when it mounts" equals today's watcher. The S071 specs read the label,
  the button, the question and the row; all stay.
- **`MarkDoneDialog.open(target)`**: the two callers and the four values it replaces are as cited;
  `data-testid="done-target"`, the save label and the done-then-photos order stay.
- **Shared code** (settings: *Shared code*): `FormModal.vue`, `useFormModal.js`, `api.js`, the
  router and the auth store are not touched. `e2e/support/tickets.js` is; § 8.3 names the whole
  suite at Normal and the one `phone-webkit` run of `screens.spec.js`.
- **§ 5.7**: the two texts and their markup stay, so `tickets-work.spec.js` and
  `tickets-parts.spec.js` read them as before. The helpers `card(page, …)` and `timeline(page)`
  do not match a card headed "Tasks".
- **§ 5.3 dates**: the API sends IST times as `YYYY-MM-DDTHH:MM:SS+05:30`, so
  `occurred_at.slice(0, 10)` is the IST day (as `ActionDialog`); the form is `novalidate`, so
  `min` and `max` only guide the picker.
- **§ 5.8 length**: 615 + 276 + 28 + 2 = 921; `remark` is `VARCHAR(1000)`, `people.name`
  `VARCHAR(100)`.
- **Tests**: the seed people, their units and logins; `raiseFixed`, `TEST_PHOTO`, `istDay`,
  `saveDialog`; test 6's ticket 3 days back with a task due 2 days back passes the server's floor;
  the S024 conventions (own records, `expectDialogFits`, the allowed 400, set-up by API).
- **Use on the floor**: one job per control; the common add is a line of text and two taps; no
  default date to explain; cancel asks for a reason on the row; *Mark done* is a dialog with a
  required text; "recorded by" shows who acted for whom; the no-Team-record state keeps its line;
  no button without its flag. The operator who owns a task and lands on *Raised by me* is stated
  as an assumption for KLA.
- **Device checks**: both are kinds a browser cannot judge, and each has its account, network and
  place. The file count (21) and the docs list are right.

## Feedback

- rule: the brief reviewer's instructions define `blocker` and `major` only for staleness mode
  ("when the design or a decision the user approved must change"); for a normal round nothing
  says whether a test plan that cannot pass is `major` or `minor`. I read S106's review r1 to
  calibrate (`.claude/agents/brief-reviewer.md`, *How to write findings*; about 3 minutes).
- idea: the facts run could list, for each move the brief names in backticks or as a button, the
  states it is offered from (`tickets_core.MOVES`): BR1-01 needed a read of the moves table that
  the brief writer's self-check did not make (`scratch/brief-facts-S107.md` has no such section).
