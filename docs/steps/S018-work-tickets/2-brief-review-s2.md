```
Step: S018 — Work the ticket
Doc: brief-review s2
Author: Brief reviewer (Fable)
Date: 20-10-2026
```

Reviewed against: cfedc46 + uncommitted S018 (code-review r2)

# S018 — Staleness review s2 (amendment A1 only)

**Verdict: no `blocker` or `major` finding is open.** A1 was written against
the S018 *brief*; S018's *code* now exists in the working tree. What the user
approved holds against it: the checkbox for `ticket:restore` holders, one
transaction that raises and then applies the back-in-service move, no
`acknowledged` event, the person rule, the time rules, and the honest times
with and without a start time. Five `minor` findings name places where A1's
statements about the code's shape no longer match it (what "one function" is,
how the `restore` block is parsed and its refusals named, which frontend
pieces exist to reuse, where the raise screen gets the default person, and a
test that cannot be written because two keys have the same holders). The rest
are nits. The planner can fix these in A1's text and the coder can start.

What was compared: `git diff cfedc46 -- backend frontend/src`, the untracked
files under `frontend/src/views/tickets/` and `backend/tests/`, and
`3-impl-report.md` § 4 *Decisions taken* and *Fix rounds › Round 1*. Only
A1 (§ 10) was reviewed.

## Findings

### BS2-01 — `minor` — "the same back-in-service code … one function, called by both" has no single function to call

**What changed.** In `tickets.py` the back-in-service move is not one
function. It is `_restore(cur, ticket, clean, occurred_at, last, now)` —
the person check (`_check_person`, anyone at the ticket's site) and the
optional `started` event — plus the generic tail of `make_move`
(lines 772–784): `_lock_open_ticket` (which also does the key check with
`require_perm_at(key, site_id)`), the from-state check (409),
`_last_ordered_event`, `_event_time` (the default `max(now, last)`,
decision 2), the `_MOVE_STEPS` dispatch, `_add_event` of the move's own
event and `update_row(state)`. `_restore` alone writes neither the
`back_in_service` event nor the state.

**What in A1 is now wrong.** *What changes* 2 and *Where* say "the
back-in-service logic of the `restore` move is extracted into one function
used by both". As the code stands, a coder has to decide what that function
is, and could end up calling `_restore` and re-typing the event write and
the state update in `raise_ticket` — the copy A1 forbids.

**Fix.** Name the extraction: the body of `make_move` after the lock becomes
`_apply_move(cur, ticket, move, clean, now)` (from-state check →
`_last_ordered_event` → `_event_time` → the step → `_add_event` →
`update_row` → auto-assign for acknowledge/start), called by `make_move`
after `_lock_open_ticket` and by `raise_ticket` after its insert and
`raised` event, with `ticket = read_ticket(cur, ticket_id)` (the row carries
the `id`, `state` and `site_id` that `_restore` reads). `raise_ticket` does
the key check itself — `require_perm_at(RESTORE_KEY, node["site_id"])`,
before the insert — since the fresh row is in its own transaction and needs
no `_lock_ticket`. Options: (a) as above; (b) call `_restore` and repeat the
two writes in `raise_ticket` — rejected, it is the copy. Recommend (a).

### BS2-02 — `minor` — the `restore` block's shape check exists (`validate_move`), and its refusal fields collide with the raise's

**What changed.** `tickets_core.validate_move("restore", body)` already
does exactly what A1's *Where › tickets_core.py* describes: `occurred_at`
and `remark` through `_event_fields`, `person_id` through `_optional_id`,
`started_at` through `_optional_time`, and the required `person_id` with
`PERSON_NEEDED` ("Who did the work? Pick a name"). And every refusal is one
`{field, message}` (`clean_body` raises the first; `ApiError(message, 400,
field)`), which the raise screen shows beside the field of that name
(`fieldErrors[err.field]`, `RaiseTicketView.vue` line 201).

**What in A1 is now wrong.** (1) "person id via `_optional_id`-style
parsing; times parsed as the move's" reads as a second parser; the first
exists. (2) The block's time is `occurred_at` — the same name as the raise's
own `occurred_at` — so a refusal on the back-in-service time ("Must be at or
after Raised, 20-10-2026 10:04", or the window) would be shown under
*When did it happen?*, not under *Back in service at*. `person_id` and
`started_at` do not collide (the raise has `reported_by_id`).

**Fix.** `validate_raise` calls `validate_move("restore", body["restore"])`
when `restore` is given (a non-object → 400 on `restore`), and prefixes the
block's errors `restore.` (`restore.occurred_at`, `restore.person_id`,
`restore.started_at`); the shared function of BS2-01 takes the same prefix
for the `ApiError`s it raises (`_event_time(..., field)` already takes the
field name; `_restore`'s two `ApiError`s need it). The raise screen shows
`restore.*` refusals beside the three new fields. Options: (a) the prefix,
as above; (b) tell the two `occurred_at` refusals apart by message text on
the page — brittle. Recommend (a).

### BS2-03 — `minor` — "reusing the move dialog's time control … (no copies)": the time control is `EventFields.vue` (time **and** remark), and the *started* pair is not a shared piece

**What changed.** The coder added `views/tickets/EventFields.vue`
(decision 17): one component with "Now · Change" (`time` stays `null`
until the user edits the input *Change* opens, pre-filled with the phone's
now) **and** the remark (*Add remark* when optional, open when required).
The *When work started* pair — a date input that follows the
back-in-service date until touched, an empty time input, `started_at` sent
only when the time is filled — lives inline in `MoveDialog.vue` (the
watcher lines 70–76, the template lines 204–223, the body line 129), not in
a component.

**What in A1 is now wrong.** *Where › RaiseTicketView.vue* says "reusing
the move dialog's time control and `PersonPicker.vue` (no copies)". With
`EventFields` the raise screen would also get *Add remark*, which A1's
"shows the fields of … back in service after the fact, and nothing else"
excludes, and the `restore` body A1 defines has no `remark`. And the
started pair would have to be copied.

**Fix.** Say which pieces: `EventFields` with a prop that hides the remark
(e.g. `withRemark: false`), and the started pair extracted into a small
`StartedAtFields.vue` (props: the back-in-service time; v-model date and
time; the follow-the-date watcher inside) used by `MoveDialog` and the raise
screen — two real uses, so the extraction is right-sized. Options: (a) as
above; (b) accept one copy of the started pair on the raise screen and
state it; (c) let the raise screen send a `remark` on the `restore` block
(the move accepts it; the shared function would write it) and show
`EventFields` as is. Recommend (a); (c) only if the user wants a remark
there — the raise screen already has *What is wrong?*.

### BS2-04 — `minor` — the default person: where the raise screen gets it, and the rule in full

**What changed.** On the ticket page the default comes from the server: the
detail's `moves[restore].default_person`, computed in `tickets._moves` as
the user's own person at the ticket's site **and only when `ticket:work`
is among his keys there** (`entry["default_person"] = _person_ref(own) if
WORK_KEY in keys else None`). The raise screen has no ticket and no
`moves`; the node detail carries `permissions` only
(`equipment.py` line 513, `permissions_at_site`). `LabourPanel.vue` (line
79) shows the page-side pattern: own person offered when `userPersonId` is
in the `people` list.

**What in A1 is now wrong.** "pre-filled by § 5.2's one rule for the user's
own person (offered only when he qualifies at the site)" leaves out the
`ticket:work` half of the rule and does not say where the raise screen gets
the value. A coder could pre-fill every operator with himself, which the
page never does (§ 5.2, BR4-03).

**Fix.** State it: pre-filled with `userPersonId` (`stores/auth.js`) when
`node.permissions` includes `ticket:work` **and** that id is in the
`people` list the screen already loads (`/api/tickets/people?equipment_id=`,
the same `_people_at_site` rows — `role`, `assignable`, `trades` — that
`PersonPicker` takes); else empty. An operator who fixed his own defect is
not pre-filled but is first in the picker (`ownPersonId`), one tap.
Options: (a) page-side as above, no new API; (b) a `default_person` on the
node detail — a ticket rule on an equipment endpoint, rejected. Recommend
(a).

### BS2-05 — `minor` — the 403 test cannot be written: `ticket:raise` and `ticket:restore` have the same holders

**What changed.** `config_rbac.PERMISSIONS`: `"ticket:raise":
("maint_operator", "it_admin")` and `"ticket:restore": ("maint_operator",
"it_admin")`, both in `SITE_SCOPED`. Every user who may raise at a site
holds `ticket:restore` there; a user without it cannot reach the raise
(the storekeeper is refused by `@require_perm("ticket:raise")`, a user with
no role at the site by `load_node_for_user`).

**What in A1 is now wrong.** *Tests*: "the user without `ticket:restore` at
the site (403)" has no subject. *What changes* 1 "for a user who holds
`ticket:restore` at the node's site" is, today, every user who sees the
form.

**Fix.** Keep the server check `require_perm_at(RESTORE_KEY, site)` (one
line; the keys may diverge later, e.g. if a reporter-only role is ever
added) and the page condition on `node.permissions`, but drop the 403 line
from A1's tests and say why in one sentence. Options: (a) drop it; (b)
monkeypatch `PERMISSIONS` in a test to make the keys differ — over-built.
Recommend (a).

### BS2-06 — `nit` — HEAD is 6c58b7a, not cfedc46

`git rev-parse --short HEAD` is `6c58b7a` ("fix raise tickets": the
`watch(nodeId, …, { immediate: true })` fix in `RaiseTicketView.vue` that
the impl report calls "the uncommitted S017 post-commit fix" — committed at
23:15). S018 is uncommitted on top of it. This review's line is written as
the orchestrator asked; when A1's check is answered, set `Baseline:` to
`6c58b7a + uncommitted S018`, and the impl report's first paragraph can say
the fix is committed.

### BS2-07 — `nit` — labels that exist, and the time label on a defect

`ticketLabels.moveSaveLabel("restore", intensity)` gives "Back in service" /
"Fixed", and `MoveDialog` labels the time "Back in service at" / "Fixed
at". A1 names the Save labels ("Raise and mark back in service" / "Raise and
mark fixed") but the time label as "Back in service at" only. Say: the time
label as the dialog's (by intensity); the Save label built on
`moveSaveLabel` (or one new entry in `ticketLabels.js`, with a line in
`ticketLabels.test.js`).

### BS2-08 — `nit` — a node change resets the restore fields too

A1: "Unticking hides the fields and keeps what was typed until the screen
is left." The screen's `watch(nodeId)` runs `resetForm()` on every node
change (*Change* on the equipment card), which rebuilds the whole form from
`blankForm()`. The three restore fields and the checkbox belong in
`blankForm()` and are cleared with the rest on a node change; say so (one
clause).

### BS2-09 — `nit` — A1's *Where › Docs* is already done

`docs/Plan.MD` § 4.2 (line 421, *Work done without a ticket* — "*Decided*
20-10-2026 as S018 A1 …") and Q23 (line 851), and `docs/steps/README.md`
Queued S020 ("Parts used … the raise-and-close half (Q23) is done by S018
A1") already carry it. Mark the Docs line as done so the coder does not look
for it.

### BS2-10 — `nit` — two styles of the same control on one screen

With A1 the raise screen has a pre-filled `datetime-local` for *When did it
happen?* and "Now · Change" for *Back in service at*; a `<select>` for
*Found by* and a `PersonPicker` for *Who did the work?*. The user approved
reusing the move dialog's controls, so this stands; worth one line in A1
saying it is accepted, or a queued tidy-up to put the raise screen's own two
fields on the same controls later.

## Checked and found consistent

- **The move allows it.** `MOVES["restore"].from_states` is `(raised,
  acknowledged, in_progress)`: back in service straight from raised, no
  `acknowledged` event (A1 *What changes* 2).
- **The events and the person.** `_restore` writes `started` with
  `from_state = raised`, `to_state = in_progress` and the named person,
  then the `back_in_service` event carries `person_id`; both name the
  person, as A1 says.
- **The time rules.** `_event_time(entered, last, now, field)` with `last =
  (raised, raise time)`: a typed back-in-service time before the raise →
  "Must be at or after Raised, DD-MM-YYYY HH:MM"; untyped → `max(now, raise
  time)`. `started_at` goes through the same lower bound and
  `started_at_error(started_at, raised, restored_at)` → "Work cannot start
  after the machine was back in service". That is exactly "back in service
  at or after the raise time; `started_at` between the raise time and the
  back-in-service time". Decision 7 (`started_at` 400 from in progress)
  never applies: the state is always raised here.
- **The times.** `ticket_times` on `raised → back_in_service`: response
  `None`, repair `None` (`repair_known` false), downtime raise → back in
  service on a breakdown; with `started`: response = started − raised,
  repair = back in service − started. A1 *What changes* 4 holds. The
  ORDERED_EVENTS question in the impl report does not touch A1 (the only
  earlier event is `raised`).
- **Rollback.** `next_counter` and the insert run inside `transaction(conn)`;
  any `ApiError` after them rolls back row, event and counter ("a failed
  raise leaves no gap").
- **Repeat.** `_check_repeat` runs on the raise's `occurred_at` before the
  insert; A1 adds nothing after it that changes that (*What changes* 6).
- **Photos after Save.** `can_add_photos` = open and `ticket:raise`; back
  in service is open, so the photo step works on the new ticket.
- **The checkbox's condition.** The node detail returns `permissions =
  permissions_at_site(node.site_id)`; the screen already reads it
  (`canRaiseHere`).
- **`EventFields` sends no time unless changed**: `time` is `null` until
  the input is edited; *Change* opens it filled with the phone's now; a
  cleared input is "now" again (§ 5.1).
- **`PersonPicker`** takes `people` (the raise screen's list has the same
  shape), `modelValue`, `ownPersonId`; required-ness is the parent's check
  ("Who did the work? Pick a name", as `MoveDialog.missingField`).
- **Test helpers.** `make_ticket(node, client=, **overrides)` takes any body
  field, so `restore={...}` fits; `refusal`, `local`, `now_ist`, `api_time`
  are in `tests/ticket_helpers.py`; `operator`, `machine`, `give_site_role`
  in `conftest.py`; `tech`, `eng`, `detail`, `events` in
  `test_ticket_work_api.py`. A1's test list is writable with them (BS2-05
  aside).
- **Standards.** A1's ISO 14224 line (every maintenance event recorded,
  whoever asked for it) still describes what the code does; the engineer's
  close with cause and action is unchanged, so the ISO 14224 coding and the
  EN 13460 sign-off stay where S018 put them.
