```
Step: S018 — Work the ticket
Doc: brief-review r4
Author: Brief reviewer (Fable)
Date: 20-10-2026
```

Reviewed against: 3e22573 + uncommitted S015, S016 + the S017 brief (`docs/steps/S017-raise-tickets/1-brief.md`, Approved 20-10-2026; no S017 code exists yet)

# S018 — Brief review, round 4

**Verdict: no `blocker` or `major` finding is open.** This extra round (the
user asked for it because round 3's answers changed much of the screen
behaviour) checked two things: that every round-3 answer marked *Accepted* is
in the brief text and says the same thing in every section it touches, and
that the revised screens hold together on the floor. The first holds for all
eleven accepted findings (the list is under *Checked and found consistent*).
The second turned up six places where the new pieces rub against each other
or against a rule elsewhere in the brief — none changes a decision, each is a
rule the coder would otherwise settle alone — and two nits. BR3-01 (rejected
by the user) and open questions 1–4 and 6 are not re-raised. Full track.

Findings: 0 blocker, 0 major, 6 minor, 2 nit.

## Findings

### BR4-01 · minor · The remark is "behind *Add remark*" on every move, but three moves require it

**Problem.** § 1 (BR3-09): "Every move dialog is short: the time shows as
*Now · Change*, the remark is behind *Add remark*, and Save is the one
action." § 5.2 then requires the remark on **send back** ("`machine_down` and a
remark, both required"), on **not a fault** ("`cause_id` and remark required")
and on a **lowering re-grade** ("Say why the machine runs"). § 3 `MoveDialog`
repeats "remark behind *Add remark*" without an exception. Taken literally, the
engineer opens *Send back*, answers Yes / No, presses *Send back*, and gets a
400 on a field he never saw; `useFormModal` then shows it as `modalError` at
the top, since the field is not rendered.

**Why it matters.** A required field must be visible before Save (checklist:
nothing a user cannot fill at that moment; errors that say what to do next).
The collapsed remark is right for acknowledge, start and back in service, where
it is optional.

**Options.** (a) § 1 and § 3 say: the remark is **open and required** on send
back, not a fault, and *Change severity* when the chosen grade is lower (the
help text of BR3-10 sits under it on send back); collapsed behind *Add remark*
on acknowledge, start, back in service, close and a raising re-grade —
**recommended**; (b) always open — loses the one-tap feel of BR3-09 on the
common moves.

### BR4-02 · minor · "Add the labour first" as a disabled button's reason is invisible on a phone

**Problem.** § 1 (BR3-05): "*Close* is disabled with the reason 'Add the labour
first' while the ticket has no labour row." The only pattern in the app for a
disabled button's reason is `saveDisabledReason` → the button's `title`
(`FormModal.vue`), which round 3 pointed at. A `title` shows on mouse hover
only; on a phone a greyed *Close* with no visible reason is a silent disabled
button, which the base § Form / Modal forbids ("never leave a disabled submit
button silent"). The r3 suggestion was too short; this corrects it.

A second step in the same flow: with the action bar now first (BR3-03), the
labour panel is below it, so the engineer reads the reason at the top and
must find the panel further down.

**Options.** (a) The reason is **visible text** under the disabled *Close*
("Add the labour first"), and the way forward is one tap: an *Add labour*
button beside it (or the text itself opens the labour dialog), so the engineer
does not scroll to the panel; `title` may stay for desktop — **recommended**;
(b) move the labour panel above the action bar when the ticket is back in
service — works for the engineer, but puts a panel the technician does not
need on the common path for every ticket in that state.

### BR4-03 · minor · The default person can be someone the server will refuse

**Problem.** Two rules disagree for one user:
- § 5.2: `default_person` on the `restore` move = `current_person_id(cur)`
  "when the user holds `ticket:work` at the ticket's site"; § 1 *Labour*: a new
  row "defaults to the user's own person (when he has a Team record)";
- § 5.7: IT admin "holds no role at a site, so it is never assignable … and
  must name the person on back in service and labour"; § 5.8: the person named
  must have a membership at the ticket's site (under either answer to open
  question 4).

An IT admin with a Team record (BR3-12's case) holds `ticket:work` at every
site as a token role, so § 5.2 pre-fills **him**; the server then refuses its
own default with 400 "Who did the work? Pick a name". The same for the labour
default, computed on the page from `/auth/me`'s `person_id` with no knowledge
of the picker's list. Rare, but the brief contradicts itself, and the fix is
the one BR3-12 already applied to auto-assign.

**Options.** (a) One rule for every default: the user's own person is offered
**only when he qualifies for that field at the ticket's site** — the same check
the server applies on save (§ 5.8) — else null. For the restore move the route
computes it (it already does); for labour the page offers the own person only
when `person_id` is in the picker's list for the ticket — **recommended**;
(b) keep the rules and accept the 400 for IT admin — not recommended, § 5.7
says he must name someone, so the page should not pre-fill him.

Related, same section: `PersonPicker.vue` could place the **user's own person
first** (from `person_id`) whenever he is in the list, before the assignees
group — under answer (a) of open question 4 the operator who fixed his own
defect presses *Fixed* and finds himself at the top instead of typing his name
into "everyone else". One line in § 3; it does not touch the question.

### BR4-04 · minor · `recording_as` is defined two ways, and its null text is wrong for one user

**Problem.** § 1 and § 6: `recording_as` is "the person who will be
auto-assigned" (null → "No Team record — nobody will be assigned"). § 8 *API*:
"`recording_as` the user's person or null". For an IT admin with a Team record
these differ: § 5.8 never auto-assigns him, so by § 1 the field is null and
the dialog says "No Team record", which is false; by § 8 it carries his name,
and the dialog says "Recording as <IT admin>", which promises an assignment
that will not happen. The coder has to pick one, and the test in § 8 would
assert the other.

**Options.** (a) One definition in § 1, § 6 and § 8: `recording_as` = **the
person who will be auto-assigned by this move, else null** (computed in the
route with the same role check as auto-assign); the null line reads **"Nobody
will be assigned"** without a reason — true for a user with no Team record, an
IT admin and an operator alike — **recommended**; (b) carry the person and a
separate `will_assign` flag — two fields for one line of text.

### BR4-05 · minor · Three controls have no place in the new layout, and "apart (left)" means nothing once the buttons stack

**Problem.** § 1 *The ticket page on a phone* places the moves (action bar,
first), *Edit* and *Assign* (with the panels), repeats, photos, timeline. Not
placed:
- **"Machine stopped"** (BR3-08) — for the operator on a defect it is one of
  his two actions (*Fixed*, *Machine stopped*); if it lands with the panels he
  does not see it (the panels are for `ticket:work` holders or non-empty);
- **"Change severity"** — the technician's control;
- **"Not fixed — raise again"** — on a ticket back in service or closed it is
  the operator's one action on that page, and the engineer's path to a repeat.
Also: "set apart (left, outline style)" describes a row of buttons; § 1 says
the bar is "full-width stacked buttons at phone width", where there is no left.
And a technician holds both `ticket:raise` and `ticket:work`: § 1 gives
"Machine stopped" to `ticket:raise` holders and "Change severity" to
`ticket:work` holders, so he would get both.

**Options.** (a) § 1 (and § 3 `TicketDetailView`) say: the action bar holds
the moves, then **"Machine stopped"** (operator on a defect) or **"Change
severity"** (`ticket:work` holders see this one only), then **"Not fixed —
raise again"** when it applies; at phone width the order is the chain move
first, these next, and *Close* / *Not a fault* / *Send back* **last, after a
gap**, outline style (the "apart" of BR3-02 becomes vertical); on a wider
screen the same buttons in one row, the significant ones on the left —
**recommended**; (b) "Change severity" with *Edit* and *Assign* — fine for the
technician, but "Machine stopped" and "Not fixed" must still be in the bar for
the operator, so (a) is simpler to state.

### BR4-06 · minor · The after-the-fact "started" field cannot be "today's date with the time empty" in one `datetime-local` input

**Problem.** § 1 (BR3-11): "both times default to today's date, the started
time empty, so the supervisor types two times, not two dates and two times."
An `<input type="datetime-local">` holds a whole value or nothing: it cannot
hold a date with the time blank, so "date pre-filled, time empty" needs
another control, and the brief does not say which. Two cases the control must
cover: the common one (started and restored on the same day) and the night
shift (started 23:40 yesterday, back in service 00:30 today).

**Options.** (a) **started** = a `date` input pre-filled with the back-in-service
date plus an empty `time` input; the pair is sent as `started_at` only when the
time is filled (so an untouched field sends nothing, as the rule of § 5.1);
the supervisor types one time in the common case and changes the date for a
night shift; the back-in-service time stays behind *Now · Change* (after the
fact he presses *Change* and gets the phone's now to edit, as S017's raise
screen does) — **recommended**; (b) a single `time` input with the date taken
from the back-in-service date — one control fewer, but a start before
midnight cannot be entered and the server would refuse "started after
restored"; (c) two `datetime-local` inputs — the two-picker problem BR3-11
raised.

### BR4-07 · nit · Two small shapes in the new dialogs

- **Send back's Yes / No.** § 1 has "two large Yes / No buttons, each with its
  consequence", and § 3 a Save labelled *Send back*. In `EquipmentStatusModal`
  (the S003 pattern BR3-02 cites) *Yes* **is** the submit. Here it cannot be
  (the remark is required, BR4-01), so say the two buttons are a **choice with
  a selected state** (the raise screen's intensity buttons are that shape) and
  *Send back* is the one submit; otherwise a coder may make Yes submit and the
  remark rule bites.
- **"Machine stopped" opens `RegradeDialog` "with critical chosen"** (§ 3).
  For the operator the three grade buttons are then clutter (critical is the
  whole point, BR3-08); say the dialog hides the grade buttons when opened
  from *Machine stopped* and shows "Breakdown from: Now · Change" plus Save
  *Machine stopped*. And `regrade_options` gives an operator on an *initial*
  ticket `[degraded, critical]` (§ 8) while the page offers him critical only:
  say that is accepted (the API allows degraded; the page does not need to).

### BR4-08 · nit · Small gaps in the files and the manual checks

- **`frontend/src/stores/auth.js`** is not in § 3 *Where*: `loadProfile`
  copies the `/auth/me` fields into refs (`userName`, `userPermissions`, …),
  so `person_id` needs a `userPersonId` ref there for `TicketsView` and the
  labour default. One line.
- **`/auth/me` when the database is down** (`app.py`'s `DBUnavailable` branch
  answers with the token's permissions only): `person_id` is `null` there. Say
  it, so the test for "null" has its second case.
- ***Assigned to me* for an IT admin with a Team record**: `person_id` is set,
  so the toggle shows and the list is always empty (he is never assigned,
  § 5.8). Accepted and harmless, worth one word so it is not read as a bug.
- **`PersonPicker` in the Assign dialog**: "the ticket's assignees first" is
  the wrong first group there; say the assigned people are left out (or shown
  as already assigned), and the ladder leads.
- **The scrollable-dialog manual check** (§ 8, fifth important box): do it on
  an **Android phone and an iPhone**. `modal-dialog-scrollable` caps the dialog
  at the layout viewport; Android shrinks that viewport when the keyboard
  opens, iOS Safari overlays the keyboard and does not, so the footer can still
  sit under the keyboard there. The check is the right one; it should name
  both.
- **"Now · Change"**: say that pressing *Change* fills the input with the
  phone's now (S017's raise-screen rule), so the user edits a time rather than
  typing one from blank.

## Checked and found consistent

- **Round-3 answers in the text, section by section**:
  - BR3-02 — *Close* / *Not a fault* / *Send back* set apart, Save labelled
    (*Close ticket*, *Close as not a fault*, *Send back*) under a consequence
    line; inline "Remove? Yes / No" on labour rows and "Remove <name>? Yes /
    No" on assignees: § 1 (moves, assign, labour), § 3 (`MoveDialog`,
    `LabourPanel`), § 7 decision 11, § 8 (manual check 3: "the Save reads
    *Close ticket*"; plain: "remove a labour row asks first"). The stacked
    order is BR4-05.
  - BR3-03 — `FormModal` gains `modal-dialog-scrollable` (every dialog
    inherits it, said as wanted): § 3 *Frontend* first entry, § 7 decision 12,
    § 8 manual check 5. The page: action bar first under the header, then
    times / assignees / labour **only to `ticket:work` holders or when not
    empty**, *Edit* and *Assign* with the panels, then repeats (hidden when
    none), photos, timeline: § 1, § 3 `TicketDetailView`. `FormModal.vue`
    today renders a plain `modal-dialog` with the footer inside the form, so
    the one-class change is exactly as described.
  - BR3-04 — detail carries `permissions` (keys at the ticket's site,
    `permissions_at_site`, as S017's node detail) and `regrade_to`;
    `regrade_options(current, lowering_allowed)` in the core; `/api/auth/me`
    gains `person_id`: § 1 (re-grade, assign), § 3 (`app.py`, `tickets_core`,
    `tickets.py`, `TicketDetailView`, `TicketsView`), § 6, § 7 decision 13,
    § 8 (pure `regrade_options` cases; API `permissions` cross-site case,
    `regrade_to` empty for an operator on critical, `person_id` set and null).
    `permissions_at_site` and `EquipmentDetailView`'s `node.permissions`
    pattern exist in the code.
  - BR3-05 — *Close* disabled with "Add the labour first", the 409 kept: § 1,
    § 8 manual check 3. How the reason shows is BR4-02.
  - BR3-06 (a) — labour defaults (own person with a Team record, today, the
    only trade), hours and minutes as two inputs, zero refused in the dialog:
    § 1 *Labour*, § 3 `LabourPanel` ("the defaults of § 1"), § 8 manual check
    3 ("own name and today pre-filled"). (b) is open question 6, not re-raised.
  - BR3-07 — `PersonPicker.vue` grouped (assignees, then technicians /
    engineers / managers incl. contractor firms, then everyone the field
    allows) with a type-to-filter box, used by back in service, labour and
    assign; works under either answer to open question 4: § 3, § 5.8, § 9 Q4.
  - BR3-08 — "Machine stopped" for `ticket:raise` holders on a defect
    (critical, "Now · Change", the same `/regrade`); "Change severity" with the
    raise screen's three large buttons for `ticket:work` holders, remark when
    lowering; `ticketLabels.js`: § 1, § 3 `RegradeDialog`, § 8 plain check.
    Placement is BR4-05.
  - BR3-09 — "Now · Change" (input only on *Change*, sent only when changed),
    remark behind *Add remark*, "Recording as <name>" on acknowledge and start
    from `recording_as` in `moves`: § 1, § 3 `MoveDialog`, § 6, § 8 (API and
    plain check). The required-remark exception is BR4-01; the definition is
    BR4-04.
  - BR3-10 — "Machine down again?" on a breakdown / "Has the machine stopped?"
    on a defect, two large buttons with "Yes — it becomes a breakdown; downtime
    runs from now" / "No — the machine runs; downtime stops" (the second on a
    breakdown only); the send-back-vs-raise-again line and its place in the
    remark's help text: § 1, § 3 `MoveDialog` and `ticketLabels.js`.
  - BR3-11 — started-at shown only from raised / acknowledged, both dates
    default to today (§ 1, § 3; the control is BR4-06); the supervisor's check
    says "on a phone" (§ 8 box 2); "No labour yet" / "Nobody assigned", repeats
    hidden when none, times row hidden on not a fault (§ 1, § 3); the
    component list from the machine's detail `children`, two levels,
    non-scrapped (§ 3 — `equipment._children` does return two levels);
    "Who did the work? Pick a name" (§ 5.2), "Say why the machine runs" and
    "Already a breakdown / defect" (§ 1); assignees' first names on list rows
    (§ 1, § 3, § 6).
  - BR3-12 — auto-assign applies the manual assignment's role check
    (technician, engineer or manager at the ticket's site), so IT admin is
    never auto-assigned, Team record or not: § 5.7, § 5.8, § 8 ("IT admin with
    a Team record starts → not assigned"); open question 1 names IT admin; the
    r2 remark on `test_role_matrix` is superseded, and § 8 *RBAC* now lists
    it_admin among the rows that gain all four — consistent with § 5.7.
  - BR3-01 — rejected by the user; Out of scope states the gap, open
    question 5 marked decided, the button stays on the old ticket's page.
    Not re-raised.
- **Round-1 and round-2 answers** were verified in rounds 2 and 3 and are
  unchanged in the text.
- **Code claims** (re-checked against the working tree): `FormModal.vue`
  exposes `saveLabel`, `saveDisabledReason` (as `title`), a `footer-left` slot
  (room for the consequence line) and the dirty guard, and renders
  `modal-dialog` without `-scrollable`; `useFormModal` exposes `send` and
  `toBody`, which is where "send `occurred_at` only when changed" fits without
  a new pattern; `_children` gives two levels; `/auth/me` already resolves the
  person through `current_memberships()` → `_person_id`, so `person_id` is a
  read of what is cached; `permissions_at` in `access_core` includes token
  keys, so `permissions` on the detail shows IT admin all four; the inline
  Yes / No confirm exists in `EquipmentStatusModal.vue`, `DocumentsCards.vue`
  and `PhotoViewer.vue`; `AppBottomNav` is CSS-only below 576 px and sits at
  z-index 1040 under Bootstrap's modal; `_update_plain_master(table,
  record_id, validator)` locks the row before `update_row`; `conftest._TABLES`
  is the flat tuple § 3 extends; `equipment.py`'s lock-order note runs (1)–(6),
  so S017's (7) and S018's "(7) only" fit.
- **Use on the floor, the revised flows**: technician on a phone —
  *Acknowledge* → Save (two taps, name shown), *Start* → Save, *Back in
  service* with himself pre-filled → Save, *Add labour* with himself, today
  and his trade pre-filled → minutes → Save: within Plan.MD § 6's "act on the
  next step, add photos, labour". Supervisor after the fact — *Back in
  service*, assignees first in the picker, type to filter, *Change* the time,
  one started time (the control is BR4-06). Operator — *Fixed* on a defect,
  *Machine stopped* when it stops (placement BR4-05), nothing else on his
  page. Engineer — *Close* refused visibly before the dialog (BR4-02), three
  selects and *Close ticket* under "TK-… becomes read-only"; *Send back* with
  a question in his words and the consequence beside each answer. Shared
  kiosk — "Recording as <name>" on the two moves that showed nothing, the
  person field on the third. No permission → no control (`moves`,
  `permissions`, `regrade_to`), never a 403.
- **Standards (§ 2)**: unchanged since round 2 and still right; the UX changes
  do not alter them. One reading worth noting for the user: the "Recording as
  <name>" line and the person field are what make the timeline's `created_by`
  / `person_id` trustworthy on a shared device — ISO 27001 A.8.15 (logging)
  only helps when the log names the right person, and A.5.16 (identity
  management) is why a kiosk left logged in must show whose name goes on the
  record. EN 13460's work order "who did what" (§ 2) is the same point from
  the maintenance side.
- **Manual checks**: the five important ones are the right five (three on a
  phone, one as an engineer, one the repeat link); the three plain ones are
  plain. The scrollable check should name both phone platforms (BR4-08).
- **Track**: full, rightly.
