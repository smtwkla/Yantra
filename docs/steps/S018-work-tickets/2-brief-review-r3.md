```
Step: S018 — Work the ticket
Doc: brief-review r3
Author: Brief reviewer (Fable)
Date: 20-10-2026
```

Reviewed against: 90284ec + uncommitted S016, S015 + the S017 brief (`docs/steps/S017-raise-tickets/1-brief.md`, Approved 20-10-2026; no S017 code exists yet)

# S018 — Brief review, round 3

**Verdict: one `major` finding is open (BR3-01: the "Not fixed — raise again"
link sits on a page the operator never reaches once the ticket is closed, so
the repeat mechanism the user decided on would mostly go unused).** The focus
of this round is use on the floor; the rules, locking, times and standards were
settled in rounds 1 and 2 and are unchanged. Every round-1 and round-2 answer
marked *Accepted* is in the brief text (list under *Checked and found
consistent*). The one change since round 2 — IT admin holds all four keys — is
consistent across § 1, § 5.2, § 5.7, § 5.8, § 8 and the code's token-role
mechanics, with one small gap (BR3-12). Full track; this is round 3 of 3.

Findings: 0 blocker, 1 major, 8 minor, 3 nit.

The screens were judged as the people who must use them (Plant-Facts § 5:
technicians phone-first, some with no phone; a floor supervisor with a phone
who records at shift end; press and sorting-line operators, some phone-less, on
a shared kiosk; engineers on phone and desktop) against Plan.MD § 6 ("Ticket:
timeline, act on the next step, add photos, labour" on the phone; "four taps
for the common case"). Where a simpler version exists it is the recommended
option.

## Findings

### BR3-01 · major · The repeat link is only on the old ticket's page, which the operator does not reach after closure

**Problem.** § 1 and § 5.5: "Not fixed — raise again" is a button **on the old
ticket's page**, shown while its latest back-in-service time is within 7 days.
Follow the operator: the press stops again the morning after the fix. He scans
the QR → equipment page → *Open tickets* (S017: states raised to back in
service) → *Raise ticket*. The old ticket was closed by the engineer the same
shift (TPM closing discipline, Plan.MD Q12, § 2 of this brief), so it is **not
in *Open tickets***, not in the Tickets list's default view (open), and not in
the raise screen's "already reported" list (S017 § 1: open tickets only). To
link the repeat he must know the serial, open the Tickets list, switch the
state filter to closed, find the ticket, open it, press the button. A
low-literacy operator at the machine will not do that; he raises a new ticket,
and `repeat_of_id` stays NULL on exactly the tickets it was made for.

On a ticket still *back in service* (not yet closed) the path works: it is in
*Open tickets*. But the engineer closes the same shift, so the common repeat
comes after closure.

**Why it matters.** User decision 1 chose "a new ticket, linked" over a reopen
so that repeats are counted and visible (§ 2 TPM: the focused-improvement
signal; ISO 9001 § 10.2 "review the effectiveness"). A link that is only made
when the engineer thinks of it from the desktop gives a repeat count that is
mostly wrong. This is the flow the floor would not use as described.

**Options.**
(a) **Offer the repeat where the operator already is: on the raise screen.**
S017's pre-save list ("the machine's open tickets") also shows the machine's
tickets restored in the last `REPEAT_WINDOW_DAYS` (back in service or closed,
not not-a-fault), each with a control "It's this again" that sets `repeat_of`
and pre-fills symptom, component and intensity as § 1 says — the same screen,
one more tap. Backend: the raise screen's fetch gains
`GET /api/tickets?equipment_id=<machine>&repeatable=1` (or a `repeat_candidates`
list beside S017's open-tickets query): tickets of that machine whose latest
`back_in_service` event lies within the window against `now`, by the same
`is_repeat_candidate`, readable by the user; the row carries
`back_in_service_at`. The button on the old ticket's page stays (the engineer's
path). Also handles the ticket raised from a QR on a **component**: the list is
by the machine, as S017's open-tickets warning is — **recommended**;
(b) keep the button on the old ticket and make closed tickets of the last 7 days
appear in *Open tickets* on the equipment page under a "Recently fixed" line —
smaller, but the operator still has to open the old ticket, then the raise
screen; two pages instead of one;
(c) keep the brief as is and accept that repeats are linked by engineers only —
not acceptable, the decision's purpose is lost.

**Bears on open question 3 (7 or 30 days):** with (a) the window also decides
how long "It's this again" is offered on the raise screen for that machine, so
the user should know that 30 days means the sorting line's packing machines,
which get many small tickets, will show a longer "recently fixed" list on every
raise. 7 days keeps it short; the server rule governs either way.

### BR3-02 · minor · Close, not a fault, send back, remove labour and unassign are single-tap and sit among the everyday buttons

**Problem.** The brief gives every move the same shape: a button in the action
bar, a dialog, Save. For *Close* ("closed is final and read-only", § 1) and
*Not a fault* the dialog is a form, not a confirmation: nothing on it says
"this is final" and Save is the same blue button as on *Acknowledge*. *Send
back* undoes a restoration that production confirmed. *Remove* on a labour row
is a hard delete with no timeline line (§ 4.2, BR1-16 accepted) — one mis-tap
on a phone and the row is gone with nothing to show it was there. *Unassign*
writes an event, so it is visible, but it is still one tap. The base's rule for
`EquipmentStatusModal` (S003 § 4.5) is the pattern here: choosing *scrapped*
replaces Save with an inline "Scrap X? This is final — Yes / No".

**Why it matters.** Checklist: irreversible or significant actions never on a
single tap, named for what they do, and kept apart from the everyday buttons so
a gloved thumb does not hit them.

**Options.** (a) **Close** and **Not a fault**: the dialog's Save reads *Close
ticket* / *Close as not a fault* and is preceded by one line "TK-2026-10-014
becomes read-only" (the S003 inline confirm, or simply the labelled button
plus the line — the required fields already make it a deliberate act); both
buttons sit apart from the chain buttons (left, outline style; base
§ Mutually Exclusive Action Buttons puts secondary / destructive on the left).
**Send back**: the same labelled Save with the consequence line of BR3-10.
**Remove labour** and **Unassign**: an inline "Remove? Yes / No" on the row,
no second dialog — **recommended**; (b) an undo toast after remove — nicer
on a phone, but the app has no toast/undo pattern yet and the row is a hard
delete, so a confirm is the smaller change.

### BR3-03 · minor · Dialogs that may not fit a phone, and a ticket page that shows everyone everything

**Problem.**
- `FormModal` renders a plain `modal-dialog` (not `modal-dialog-scrollable`),
  so a dialog grows with its content and the whole modal scrolls; on a phone
  with the keyboard up the footer with Save is below the fold. The **close
  dialog** has up to five fields (symptom when empty, cause, action, remark,
  time); the **supervisor's after-the-fact restore** has four, two of them
  `datetime-local` pickers; the **labour row** has four. These are the
  dialogs the floor uses; the checklist says the action buttons must stay
  visible and a dialog must not grow until it shows only part of itself.
- The **ticket page** (§ 3 Frontend) carries the action bar, the three times,
  assignees, the labour panel, repeat links, the timeline, photos, *Edit*,
  *Assign*. Plan.MD § 6 wants it on the phone for "act on the next step, add
  photos, labour". For an operator (his job: see the state, *Fixed* /
  *Machine stopped*, *It's this again*) and a technician (*Start*, *Back in
  service*, his labour) most of it is noise, and the move buttons risk
  landing under the timeline.

**Options.** (a) `FormModal` gains `modal-dialog-scrollable` (one class; the
body scrolls, header and footer stay — name it in § 3 as a change to the
shared component, since every dialog in the app inherits it); the move
dialogs keep to the fields of the move, time and remark collapsed (BR3-09), so
the close dialog is three selects and Save. The ticket page: the action bar
**first, under the header**, full-width stacked buttons at phone width, the
next move in the chain first; the **times, assignees and labour panel shown
only to `ticket:work` holders or when non-empty**; the *Edit* and *Assign*
buttons with the secondary controls, not in the action bar — **recommended**;
(b) make close a page (`/tickets/:id/close`) rather than a dialog — fits the
"split it or make it a page" rule, but a page for three selects is more than
needed once the footer stays visible.

### BR3-04 · minor · How the page knows which controls to show: the detail carries `moves`, nothing for assign, edit, labour and re-grade

**Problem.** § 6: the detail gains `moves` (= `allowed_moves` for this user).
The page also has *Assign* (`ticket:assign`), *Edit* and *Add labour*
(`ticket:work`), *Re-grade* (`ticket:raise`, lowering only with `ticket:work`),
and *Not fixed — raise again* (`ticket:raise`). The brief does not say how the
page learns the user's keys **at the ticket's site** for those. S017's node
detail sends `permissions` (= `permissions_at_site`) for exactly this reason
(S017 § 3, BR2-04 there); the ticket detail does not, so the coder would either
copy that or read the global `/auth/me` list (wrong after a cross-site
membership: an engineer at SSVT holding operator rights at SMTW would see
*Assign* on an SMTW ticket and get 403). The UX rule is "no permission → the
control hidden, not a 403".

Two particular cases:
- **Re-grade for an operator on a critical ticket**: he may only raise the
  grade, and there is nothing above critical, so the dialog would offer nothing.
  The button must not show. Likewise a technician's dialog may offer every other
  grade, an operator's only the higher ones. The page needs to know which
  intensities the user may set, not just "may re-grade".
- ***Assigned to me*** for a user with no Team record returns an empty list
  (§ 5.8). The toggle should not show for him (IT admin, an engineer entered in
  Keycloak before Team); the page needs to know whether the user has a person.

**Options.** (a) The detail carries `permissions` (the user's keys at the site
of `tickets.unit_id`, as the node detail does) and `regrade_to: [intensities]`
(empty → no button; computed in the route from the keys, as `default_person`
is); `/auth/me` carries `person_id | null` so *Assigned to me* shows only for
users with a Team record — **recommended**; (b) a `can_*` flag per control —
the same thing with more names.

### BR3-05 · minor · The engineer learns "add the labour first" only after filling the close dialog

**Problem.** § 5.2: close without a labour row → 409 "Add the labour before
closing". The page shows *Close* whenever `moves` allows it; the engineer opens
the dialog, picks cause, action, maybe the symptom, types a remark, presses
Save, and gets the 409. `FormModal` keeps the modal open with the error, but
the way forward is: Cancel (the form is dirty → "Discard your changes?") →
Discard → *Add labour* → fill that dialog → *Close* again → pick everything
again. On the floor the engineer is often the one typing the labour (Plant-Facts
§ 4: technicians without phones; the engineer guided by phone), so this is the
normal close, not the exception.

**Why it matters.** Base § Form / Modal: "never leave a disabled submit button
silent: tell the user why"; and the checklist's "errors that say what to do
next". The server 409 is right as the rule; the page should not rely on it.

**Options.** (a) The page knows `labour` from the detail: *Close* is disabled
with the reason "Add the labour first" (`title`, as `saveDisabledReason` does)
while `labour` is empty, and the labour panel sits above the action bar on the
close path; the 409 stays as the server's word — **recommended**; (b) the close
dialog embeds one labour row (person, trade, minutes) when none exists, written
in the same transaction before the close — fewer dialogs, but a second write
path for labour and a bigger dialog (BR3-03); (c) leave it to the 409 — not
recommended.

### BR3-06 · minor · The labour row asks four fields of which three can be defaulted

**Problem.** § 1 *Labour*: "rows of person, trade worked, date and time spent";
only the trade is said to be pre-filled (when exactly one). A technician who
just restored the machine opens *Add labour* on his phone and must pick
himself from the people list, pick the date, enter hours and minutes. The
checklist: nothing asked that could be defaulted (the user's own person,
today).

**Options.** (a) Say the defaults: **person** = the user's own person when he
has a Team record (the same `current_person_id` the restore dialog uses — a
`default_person` for labour in the detail, or one `me` field), **date** =
today, **trade** = the person's only trade (as now), minutes empty; the engineer
changes any of them. Hours and minutes as two number inputs, a row with 0 total
refused in the dialog before the request — **recommended**; (b) in addition,
the **technician's back-in-service dialog** offers an optional *Time spent*
(minutes) that writes a labour row for the person named, with that person's
only trade and the restoration date, so the common flow (acknowledge → start →
back in service → labour) is three dialogs instead of four and the engineer
finds the labour already there at close. Decision 6 (labour required at close,
not at back in service) is untouched: the field is optional. The simpler
version for the technician; a small addition the user should see. If not
wanted, (a) alone is enough.

### BR3-07 · minor · The person pickers on back in service and labour list the whole site; order and search decide whether a supervisor can use them

**Problem.** § 5.8 (proposed, open question 4 (a)): the person named on back in
service and on a labour row is **any active person with a membership at the
ticket's site, operators included**. At SMTW that is every operator of every
unit (presses with 4–5 workers each, the sorting line's packing-machine
operators, extrusion, kiln, workshops) — a plain `<select>` of a hundred or
more names on a supervisor's phone at shift end, with the person he wants
(the technician who came) somewhere in the middle. S017's *reported by* picker
has the same shape (a nit against S017 under BR3-11), but there the operator is
usually his own and the field is optional; here the field is required on every
restoration a supervisor records.

**Options.** (a) The picker is **grouped and ordered**: the ticket's
**assignees** first, then people on the maintenance ladder at the site
(technician, engineer, manager — including contractor firms), then everyone
else; with a type-to-filter box (the equipment picker of the raise screen
already searches by text). The picker endpoint already returns each person's
role, so this is page-side; the assignees come from the detail —
**recommended**; (b) option (b) of open question 4 (ladder only) shortens the
list but loses the operator-fixed defect, as BR2-01 said.

**Bears on open question 4:** choice (a) stays usable on a phone only with the
ordering above; the user should know that when choosing, so it is not a reason
to pick (b).

### BR3-08 · minor · The operator's re-grade is one case — "the machine has stopped" — and should be one plain button

**Problem.** § 1 *Re-grade*: `RegradeDialog.vue`, "raising by `ticket:raise`
holders: the operator who sees the leaking machine stop re-grades it". For the
operator that is the whole use: a defect ticket on his machine, and now it has
stopped (Plan.MD § 4.2: "a defect that gets worse is re-graded critical with
the event time; downtime starts then"). "Re-grade" is maintenance jargon; a
dialog with a choice of three intensities, a time and a remark is a form for a
case that has one answer. Lowering, the technician's case, is where a choice
and a remark belong.

**Options.** (a) On a defect ticket, holders of `ticket:raise` see a large
button **"Machine stopped"** (critical with the event time, default now; the
same `/regrade` call; a dialog only for the time, as BR3-09); the general
*Change severity* dialog — the three large intensity buttons of the raise
screen, reused, with the remark field shown only when lowering — is offered to
`ticket:work` holders. Labels in `ticketLabels.js` — **recommended**; (b) one
dialog for all, with "Re-grade" renamed *Change severity* and the intensity as
the three large buttons — acceptable, one more tap for the operator and a
choice he does not need.

### BR3-09 · minor · Acknowledge and Start open a dialog that has nothing required in it; make the common case one tap and the auto-assign visible

**Problem.** § 3: one `MoveDialog` for every move, "event time (sent only when
the user changed it), remark". For *Acknowledge* and *Start* nothing is
required, so the technician's common case is: tap the button, see a dialog with
a time he leaves alone and a remark he leaves empty, tap Save. Plan.MD § 6 asks
for "act on the next step" on the phone. The dialog is still needed for the
after-the-fact case (the supervisor or engineer typing a time), so it should not
go away — it should not be in the way.

A second point for shared kiosks and phones left logged in (Plant-Facts § 5:
the extrusion line's shared kiosk; Plan.MD § 3 shared-device login): § 5.8
auto-assigns the acknowledging or starting user silently. If the kiosk is still
logged in as the previous technician, the ticket is assigned, and later the
labour defaulted, to the wrong person, and nothing on the screen said so. The
restore dialog shows the person (changeable); these two moves show nothing.

**Options.** (a) The dialog for every move shows the time as **"Now"** with a
*Change* link that reveals the `datetime-local` input, and the remark collapsed
behind *Add remark*; Save is the one visible action, so the common case is
button → Save. For acknowledge and start the dialog's first line reads
**"Recording as <name>"** (from the auto-assign's person; "No Team record —
nobody will be assigned" when null) — **recommended**; (b) skip the dialog for
acknowledge and start (one tap, server time) and reach the after-the-fact form
through a second, smaller control — fewer taps, but two ways to do one thing
and no place for the "Recording as" line.

### BR3-10 · nit · Send back: the dialog's wording and what each answer does; when to send back and when to raise a repeat

- "Machine down again?" is the right question on a breakdown. On a **defect**
  that was *Fixed* (the machine never stopped) "down again" misleads; the
  dialog should ask "Has the machine stopped?" there (`ticketLabels.js`, as
  *Fixed* already varies by intensity).
- Yes / No as two large buttons, not a select; and the consequence stated
  beside each, since § 1's rule is not obvious to an engineer on a phone: "Yes —
  the ticket becomes a breakdown; downtime runs from this time" / "No — the
  machine runs; a breakdown becomes a defect, downtime stops".
- A ticket *back in service* offers the engineer **Send back** and, within
  7 days, **Not fixed — raise again** (his `ticket:raise`); both fit "it is not
  done". One line in § 1 saying which is which — send back when the work is
  not finished or not accepted (the machine has not run as repaired); a repeat
  when the machine ran and the same fault came back — keeps the record
  consistent across engineers, and the remark fields' help text can say it.

### BR3-11 · nit · Small floor-use items across the dialogs and the page

- **After the fact, two times.** The supervisor's restore dialog from raised /
  acknowledged has two `datetime-local` inputs (started, back in service). On
  Android each opens a date picker then a time picker. Say that both default
  to today's date with the time empty for *started*, so the supervisor types
  two times, not two dates and two times; and that `started_at` is shown only
  when the ticket is raised or acknowledged (§ 1 says it; the dialog section
  of § 3 does not).
- **The manual check for the supervisor** (§ 8, important, second box) should
  say "on a phone": the floor supervisor records from one (Plant-Facts § 3,
  § 5), and the two-picker point above is what that check would catch.
- **Empty states**: the labour panel ("No labour yet"), assignees ("Nobody
  assigned"), repeats (section hidden when none); the times row hidden on a
  not-a-fault ticket (three "—" read as "unknown", which it is not).
- **Edit dialog's component list**: name the source — the machine's
  `GET /api/equipment/<id>` detail, whose `children` carry the two levels under
  it (equipment.py `_children`), non-scrapped ones offered.
- **Messages the brief does not quote**, for the 400s a non-engineer meets —
  one line, what is wrong and what to do: `person_id` on restore → "Who did
  the work? Pick a name"; lowering without remark → "Say why the machine
  runs"; same intensity → "Already a breakdown" / "Already a defect". The
  quoted ones are fine (see *Checked*).
- **Tickets list row**: with assignment in this step, an engineer scanning the
  open list wants to see who is on a ticket; one short column (assignees'
  first names, or a count) is worth saying, and stays optional.
- **S017 (nit, not for S018 to fix):** the *reported by* picker is the same
  whole-site `<select>`; the grouping and filter of BR3-07 would serve it too.

### BR3-12 · nit · IT admin with a Team record, and two wording spots

- § 5.7 says IT admin "with no Team record … is never auto-assigned"; § 5.8
  auto-assigns "every `ticket:work` holder who … has a Team record". An IT admin
  who **does** have a Team row (a person record with his username, no site
  role) would be auto-assigned on acknowledge or start, although he could not
  be assigned by hand (§ 5.8: assignees are technician, engineer or manager at
  the ticket's site). Say that auto-assign applies the same role check as a
  manual assignment (the person's role at the ticket's site qualifies), so an
  IT admin is never auto-assigned, Team record or not — one `if`, and the
  timeline never shows an assignee who could not be picked.
- Open question 1 ("may an engineer close a ticket he worked himself")
  names engineer and manager for `ticket:close`; IT admin now holds it too (and
  Plan.MD § 3 already records that departure from A.5.3 for him). One word so
  the user's answer covers him.
- § 8 *RBAC*: round 2 verified `test_role_matrix` with "it_admin does not
  change"; the brief's text now rightly says it_admin gains all four. Fine;
  only noting that the r2 review's statement is superseded.

## Checked and found consistent

- **Round-2 answers in the text**: BR2-01 (§ 5.8 proposed (a), decision 8, open
  question 4 as the (a)/(b) choice, § 8 follows the answer); BR2-02 (`?ticket_id=`
  anchor in § 3, § 5.8, § 6; the cross-site picker test in § 8); BR2-03 (person
  always shown and required, `default_person` on the `restore` entry in § 1, § 3,
  § 5.2, § 6, § 8; no `needs_person`); BR2-04 (§ 3 `documents.py` conditional on
  open question 2, write key stays `ticket:raise`); BR2-05 (latest
  `back_in_service`, 0 ≤ new − restoration ≤ 7 days, server rule governs — § 1,
  § 3, § 5.5, § 8); BR2-06 (auto-assign for every holder with a Team record, the
  *assigned* event, 200 idempotent, 404 — § 1, § 5.8, § 8); BR2-07 (close
  overwrites the mode with an *edited* line; modes from S017's endpoint;
  `/regrade` keyed `ticket:raise` with lowering inside; `used_by`; the wrapper's
  one addition; the raiser cannot edit, accepted — § 1, § 3, § 5.2, § 5.6, § 6);
  BR2-08 (Baseline names S015; S017 § 3 now states the "sent only when changed"
  rule, so § 5.1's claim holds); BR2-09 (ISO 9001 § 10.2 and ISO 27001 A.5.15 /
  A.8.15 in § 2). Round-1 answers were verified in round 2 and are still in the
  text.
- **IT admin holds all four keys (S017 user decision 7)**: § 5.7 table and
  text; § 8 *RBAC* (it_admin gains all four on top of `ticket:read` /
  `ticket:raise`; holders tests); § 1 and § 5.2 (a `ticket:work` holder with no
  Team record must name the person — covers him); § 5.8 (not auto-assigned
  without a Team record; the gap with one is BR3-12). In the code:
  `access_core.every_unit_by_token` gives a token role every unit for a key
  only when it also holds `equipment:read_all_units`, which `it_admin` does, so
  S017's predicate (`accessible_unit_ids(cur, "ticket:read")`) and
  `has_perm_at` for the four keys pass for him at every site, as § 5.7 says;
  `permissions_at` includes token keys, so `allowed_moves` sees them. The
  pickers anchored on `?ticket_id=` check `ticket:read` at the ticket's site,
  which he passes. S013's gate (IT admin from the plant network only) is S017
  § 5.6's note and needs nothing here.
- **Error texts the brief quotes** are one line, plain, and say what to do:
  "Must be at or after *Acknowledged*, 20-10-2026 10:04"; "This ticket changed
  — reload"; "Add the labour before closing"; and the 403 from
  `require_perm_at` ("You can't do this at SMTW"). The ones it does not quote
  are BR3-11.
- **Who is acting** is visible: the topbar shows the user's name at phone width
  (`AppTopbar.vue`), the restore dialog shows the person; the two moves that
  show nothing are BR3-09. The bottom nav (z-index 1040) sits under Bootstrap's
  modal, so a dialog is never covered by it.
- **Screens that fit the floor as written**: the technician's back in service
  (person pre-filled, one Save) and *Fixed* on a defect; the supervisor's
  restore naming the technician with an optional start time (the after-the-fact
  case Plan.MD § 4.2 asked for; the picker's order is BR3-07); not a fault with
  the suggested default *5.1 No cause found*; the close dialog's fields (the
  precondition is BR3-05, the confirm BR3-02); assign after back in service;
  `MoveDialog` on `FormModal`, so typed input survives a stray tap (S007); the
  move buttons driven by `moves` (hidden, not 403); the default time = the
  server's clock (no false "before the last event" on a fast phone); the Tickets
  list order (critical first, oldest first) still serving the technician;
  *Assigned to me* as a query-string filter like the others.
- **Rules, locking, times, data model, standards**: unchanged since round 2 and
  still consistent with Plan.MD § 3 / § 4.2, Philosophy § 6, `config_rbac.py`,
  `auth_utils.py` and the S017 brief as approved (`event_time_error(…,
  not_before)`, events' `intensity`, the `Owner` keys, `_people_at_site`
  site-first, `current_person_id` left to S018).
- **Manual checks**: the four important ones are the right four; the
  supervisor's should say "on a phone" (BR3-11). The two plain ones are plain.
- **Track**: full, rightly.
