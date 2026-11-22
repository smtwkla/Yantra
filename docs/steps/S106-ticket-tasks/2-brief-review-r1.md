```
Step: S106 — Tasks on a ticket
Doc: brief-review r1
Author: Brief reviewer (Opus)
Date: 22-11-2026
```

Reviewed against: 8644720

**Verdict:** one `major` finding is open (BR1-01: the recommended answer to Q2 hides a consequence
that the request's own example runs into). The record, the rules, the locks, the RBAC and the
migration are sound. Facts file `scratch/brief-facts-S106.md` was given and used. This is round 1:
the whole brief was read.

## BR1-01 (major) § 1, § 2, § 7 D4, § 9 Q2: the close block and follow-up work that prevents a recurrence

**Problem.** § 2 gives the plant a rule of thumb: "work that finds or fixes **this** fault is a
task; work that stops the fault from coming back is a countermeasure". The request's own second
task, *Schedule a PM visit from the VCB supplier*, sits on the countermeasure side of that rule:
it is preventive work on the panel (Maintenance-Philosophy § 12 defines a *Preventive*
countermeasure as "regular work that stops the failure before it happens"). The brief makes it a
task in § 1 and in its acceptance (§ 8.7) without saying why the rule does not apply.

Under Q2 (a), the recommended answer, every open task blocks *Close* and *Not a fault*. Q2 and D4
do not say what that does to follow-ups that run for days or weeks: a supplier visit, a trial fix
watched for a week ("confirm the panel stays dry for a week", the brief's own D3 example). The
ticket then has two outcomes, and Q2 shows neither:
- it stays in *Back in service* until the follow-up ends, against Plan § 9 Q12 (*Closing
  discipline*: TPM closes within the shift; tickets back in service and not closed are flagged to
  the engineer);
- or the engineer cancels the task to close the ticket, and the follow-up the feature exists to
  track loses its owner and due date (a cancelled task is final, § 5.5).

**Why it matters.** KLA approves Q2 at gate A. The answer is a judgement call for KLA, but it must
be made with this consequence in view, and the glossary row (§ 3, Docs) will teach the plant a rule
that the first real case contradicts.

**Options.**
- **(a) Recommended.** Keep Q2 (a). Make the rule and the example agree: state in § 2, in the
  glossary row and in Q2 that a follow-up that prevents a recurrence (a supplier's PM visit, a
  watch over weeks) goes to an improvement as a countermeasure, which tracks it after the ticket
  closes; and that a task is the work needed before the cause can be coded and the ticket closed.
  Recast § 1's example (*Schedule a PM visit* as the improvement's countermeasure, or as a task
  that is done when the visit is booked, if that is what KLA means). Add the consequence above to
  Q2 (a), with the Q12 link.
- (b) Keep Q2 (a) and widen the rule: a task is any follow-up of this ticket, and the ticket stays
  in *Back in service* until the last one ends. Q2 says so; Plan Q12's flag then shows such tickets
  as waiting on tasks.
- (c) Present Q2 (b), a warning only, as an equal choice, with its added rules (§ 9 lists them).

## BR1-02 (minor) § 2: ISO 9001 § 10.2.1 (b) also covers finding the causes

**Problem.** § 2 puts *fault diagnosis* ("find where the fault is and what caused it") under ISO
9001 § 10.2.1 (a), the correction, and the improvement under (b) and (c). Clause (b) itself
includes "determining the causes of the nonconformity" (b 2), which in Yantra is the improvement's
why-why (S069). EN 13306's fault diagnosis covers fault recognition, localisation and the
*immediate* cause; the root cause is (b).

**Why it matters.** KLA is learning the standards from these sections, and the same text goes to
the glossary. "What caused it" on the task side blurs the line the brief draws in D1.

**Options.**
- **(a) Recommended.** Reword: a task finds where this fault is and its immediate cause, or fixes
  it (§ 10.2.1 a; EN 13306 fault diagnosis and correction); finding the root cause (§ 10.2.1 b,
  the why-why) and removing it (c) stay on the improvement. Use the same words in the glossary row.
- (b) Keep the text and add a sentence that a cause found by a task is the immediate one.

## BR1-03 (minor) § 4.2, § 6: the engineer gets no hint that an owner cannot open the ticket

**Problem.** § 5.3 accepts owners who never see their task: no login, a role without `ticket:read`
(the storekeeper), or units that do not cover the ticket (a technician of the site restricted to
other units by `person_units`). The owner flags in § 6 are `active`, `has_login` and `may_own`
(an active member of the site). None tells the engineer that the third kind of owner will not see
the task on *Me › Open work* and will get no *Task for you* alert (Q6: "only to people who may open
the ticket"). The owner picker (`GET /api/tickets/people?ticket_id=`) lists every member of the
site, so the engineer picks blind. The screens step builds on § 6 "as written here", so the field
belongs in this step's API.

**Why it matters.** A task given to someone who never sees it stays open, blocks the close (§ 5.5)
and is noticed only when it is overdue.

**Options.**
- **(a) Recommended.** Add `owner.can_open` (computed, § 4.2): the owner holds `ticket:read`
  covering the ticket's unit. Compute it with the existing recipient query:
  `alerts.people_at_unit(cur, site_id, [ticket unit], access_core.roles_holding(READ_KEY),
  only_ids=<the tasks' owner ids>)`, one query per detail, the same audience the alerts step will
  use. `tickets.py` already imports `alerts`. Add a test (an owner of the site restricted to
  another unit: `can_open` false, `may_own` true).
- (b) Leave it to the screens step, and say in § 1's *What the next two steps add* that it adds
  this field to the detail.

## Nits

- **BR1-04** (nit) § 4.1, D11: adding `fk_ticket_events_task` with foreign-key checks on is a
  table copy of `ticket_events` in MariaDB (from the MariaDB ALTER TABLE documentation; not run
  here), while widening `remark` from `VARCHAR(1000)` to a longer `VARCHAR` keeps its two length
  bytes and can be done in place. Say in § 4.1 that v59 copies `ticket_events` (small, at release
  start). Correct D11's reason for rejecting the wider remark; 300 characters can stay as the
  choice. Note that a wider `remark` would also fix the description issue in § 9.
- **BR1-05** (nit) § 3, § 5.6: in `tickets.py`, "task rows" already means `task_queue` rows (the
  raise's comment "rolls the task rows back", the docstring's alerts sentence). Write
  "`ticket_tasks` rows" in the LOCK ORDER notes and comments, never "task rows". Ask the alerts step
  to name its queue kind so that "task" never means both.
- **BR1-06** (nit) § 5.7, § 8.3: "IT admin ... has no Team record" is true only for an IT admin
  without one. A person can hold IT admin and a site role (`config_rbac.INTERNAL_ONLY_ROLES`
  comment). Write "IT admin without a Team record" in § 5.7 and in the *Mine* test.
- **BR1-07** (nit) § 8.3: add two tests for the owner rule's edges that § 5.3 and § 5.4 describe:
  an owner at the site whose units do not cover the ticket (*Mark done* 404, the task not in
  *Mine*); and an owner who sees the ticket only through its machine's current unit at another
  site (`can_mark_done` false in *Mine*, *Mark done* 403).
- **BR1-08** (nit) § 7 D4, § 5.7: the close block assumes that whoever may close can also cancel
  the blocking task. Today `ticket:close` and `ticket:assign` have the same holders
  (`config_rbac.py:119-120`), but they may drift, as `ticket:edit_notes`' comment says. Say so in
  D4, so that a later change to either key reconsiders the block.
- **BR1-09** (nit) § 9, *SMTW-Review point*: drop "or adds a key for tasks". A later step may add
  a key on purpose. The audit point should check the invariants only: the lock (7), the timeline
  line in the same transaction, the close block, and owner by data.

## Checked and found consistent

- **Every close path.** Only `tickets._apply_move` writes `tickets.state`. The moves to `closed`
  are `close` (from `back_in_service`) and `not-a-fault` (from raised, acknowledged, scheduled and
  in progress), both through `make_move`. The raise's *Already fixed* applies only `restore`.
  masters, equipment (the scrap refuses machines with open tickets), improvements, contracts and
  the worker never close a ticket. The block in `_apply_move` covers both closing moves.
- **Lock order.** Every task write takes (7) first (`_lock_open_ticket`), and its first plain read
  (`read_ticket`) comes after the lock is granted, so the close's plain count sees every committed
  task. The new edges, (7) to a shared `people` lock and (7) to `ticket_tasks`, match labour and
  assignee writes. masters.py never holds a person and then waits on a ticket (its ticket reads are
  under a unit or a code lock). improvements.py holds tickets only in share mode. No new cycle.
- **RBAC.** No new key, so `test_role_matrix` is unchanged. `ticket:assign` and `ticket:read` are
  site-scoped (`SITE_SCOPED`) and checked at the ticket's site through `_lock_ticket`. *Mark done*:
  `has_perm_at(ASSIGN_KEY, site)` or `current_person_id(cur) == owner_id`, after `ticket:read` at
  the site. `current_person_id` returns None for a user without a Team record and for an inactive
  person, so the rule fails closed. The `is_owner` flag matches the route.
- **Migration v59.** It has the form of v50's `ALTER TABLE people` (`ADD COLUMN IF NOT EXISTS …
  AFTER`, `ADD KEY IF NOT EXISTS`, `FOREIGN KEY IF NOT EXISTS`). It adds a nullable column and a new
  table, so no existing row is converted or refused, and no `_PRECONDITIONS` entry is needed. v58
  is the last migration and is in release v0.1.16 (`d80399d`). `ticket_events.event` is
  `VARCHAR(30)`. The test pattern (`test_migration_v58.py`, `_fill_one_ticket`, `_schema`) exists.
- **Reuse.** `validate_done`, `validate_cancel`, `due_date_error`, `done_time_error`,
  `overdue_days`, `action_counts` and `action_flags` exist with the signatures and messages § 5
  quotes. `contracts_core.iso_date` refuses `20261122`, and `pm_plans_core` imports it. The import
  direction `ticket_tasks_core` → `improvements_core` / `contracts_core` → `tickets_core` has no
  cycle. `_required` and the `is_id = _is_id` alias pattern are as cited.
- **`ticket_times` and the other event readers.** `ticket_times` skips events outside
  `ORDERED_EVENTS`, and so does `_last_ordered_event`. `alerts.read_alert_ticket` and the
  closed-email facts read events by id or for the times only. The detail view and *Me › Activity*
  show an unknown event by its raw name (`EVENT_LABELS[…] ?? e.event`).
- **The remark length.** The longest change line is 855 characters, which fits `remark
  VARCHAR(1000)`.
- **Existing tests.** No test pins the detail's or a move's whole key set. The two monkeypatches
  of `_lock_open_ticket` keep working. `conftest._TABLES` deletes with foreign-key checks off.
  `MAX_PER_PAGE` is 200.
- **Track and size.** Full track is correct (migration, locks, RBAC). The split into three steps
  follows S070 / S071 / S074, and the backend half is about 9 code and test files.
- **Standards.** EN 13306 (terms marked *to verify*), ISO 14224, TPM, ISO 27001 A.5.15 and the
  SMRP KPIs are named and explained in plain words. ISO 9001 § 7.5.3 is right. § 10.2.1: BR1-02.
- **No architecture doc.** The repo has none, and its settings have no *Architecture* entry.

## Feedback

- idea: the facts file's *Code names* could add, for a function the brief calls with arguments
  (`improvements_core.action_flags(ticket_open, …)`), the real signature line, so that parameter
  names and order are checked without opening the module (five functions opened here for that).
- hindrance: the facts file lists where `tickets.state` is read but not every place that writes
  it, and the spawn prompt asked for "every close path"; a grep for writers of a column named in
  the brief (`UPDATE <table>` / `update_row(cur, "<table>"`) would answer that in one place
  (about 5 minutes of greps here).
