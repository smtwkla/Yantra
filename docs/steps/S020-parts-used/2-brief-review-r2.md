```
Step: S020 — Parts used
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 21-10-2026
```

Reviewed against: 28d3be3 + uncommitted S024

**Verdict: no `blocker` or `major` finding open. Round 1's major (BR1-01) is
resolved in the text: § 5.2, § 7 decision 8 and the lock-order note now follow
S025 § 1.6 (ticket (7) first, then the node `LOCK IN SHARE MODE` through the
helper shared with `_check_component`), and the refusal order is 404 → 403 →
409 → 400 as on every ticket write. What is left is four minor points — rules
the coder would otherwise settle alone, two of them on the floor — and nits.**

S025 is not yet coded (`local_db.py` still ends at v13; `backend/` carries only
S024's test harness), so the brief's dependence on S025 stands as written and
the baseline is round 1's.

## Round 1 answers, checked in the text

Every `Accepted` answer is in the brief, not only in the log:

| Finding | Where it landed |
|---|---|
| BR1-01 | § 5.2 steps 1–4, § 7.8 (rewritten; the "inversion" sentence gone), § 3 lock-order notes |
| BR1-02 | § 3 core: only `PARTS_HINT_ACTION_CODES`; `_moves` resolves the ids, active or not; the API test |
| BR1-03 | § 5.2 step 3 (add, or edit whose `node_id` changes) and "Scrap does not look at part lines"; `machineParts.js` keeps the line's node |
| BR1-04 | § 1.1, § 3 `showParts`, § 8 (the operator check reworded) |
| BR1-05 | § 1.4 *Fitted here before*: fetched once on open, a row = description · number · maker, five then *More*, narrowed by *Description*, not on *Edit*; in the dialog-fit check |
| BR1-06 | § 1.3: two choice buttons in floor words, default *standard number*, quantity 1 nos, the help line; the important e2e takes the default path |
| BR1-07 | § 1.5: 409 no field, the shorter message, the dialog reloads; *Not a fault* disabled with "Remove the parts first"; all three from-states |
| BR1-08 | § 3 Tests: `conftest._TABLES` |
| BR1-09 | § 3: `utils/machineParts.js`, `EditTicketDialog.vue` uses it; the machine is the first row |
| BR1-10 | § 5.1 table |
| BR1-11 | § 8 device check: network "either" |
| BR1-12 | § 2: ISO 8000 as support for one item master, ISO 14224 Table 8, ISO 55001 § 7.5 |
| BR1-13 | § 9 Q6, left to the user |
| BR1-14 | § 1.2, § 4 (v21 note, the index's reason), § 6 ("the entry whose `name` is `close`", lines by `id`) |

## Findings

### BR2-01 · minor · How the quantity travels: a JSON number through `Decimal` refuses 1.1

**Problem.** § 5.1 says the quantity "arrives as a string or a number and is
parsed as a `Decimal` (no float)". If the dialog sends a JSON number
(`quantity: 1.1`) and the core does `Decimal(value)`, the result is
`Decimal('1.100000000000000088817841970012523233890533447265625')` — a binary
float's expansion — and the "At most two decimals" rule refuses a valid entry.
`1.5` happens to survive (exactly representable), so a quick test would not
catch it. Two smaller cases in the same place: `True` is an `int` in Python
(`isinstance(True, int)`), so a bool would pass as 1 unless refused as
`_is_id` does; and a string `"1e2"` is a valid `Decimal` whose exponent is
positive, so a check written as `exponent >= -2` needs the value normalised
first.

**Why it matters.** This is exactly the kind of rule the coder settles alone,
and the wrong choice is a false refusal on the floor's most ordinary entry.

**Fix** (state in § 5.1 and § 3 Frontend):
- the dialog sends the quantity **as the string typed** (`<input type="text"
  inputmode="decimal">`, trimmed) — `type="number"` would also let the browser
  localise the separator, which § 5.1's comma case then meets; `1,5` is
  refused with the "e.g. 2 or 1.5" message as the table says;
- the core accepts a string or a non-bool `int`/`float`, converts through
  `Decimal(str(value))`, refuses `NaN`/infinity and anything not finite, and
  judges "at most two decimals" on the normalised value (`quantize` or
  `value == value.quantize(Decimal("0.01"))` with `ROUND_DOWN` comparison);
- a core test for `1.1` sent as a number, `True`, `"1e2"`, `"NaN"`.

### BR2-02 · minor · The *kind of number* buttons and the *Maker* label when there is no number

**Problem.** § 1.3 says the kind is "stored when a number is given" and shown
as two large choice buttons, default *standard number*. It does not say whether
the buttons show **before** a number is typed. If they always show, a
description-only line — "Servo 68, 5 L", the case § 5.1 explicitly allows —
presents two large buttons that do nothing, and a *Maker* field whose
"required" state depends on a button the user did not need. On a phone the
dialog is already the longest in the app: a five-row list, five fields, two
big buttons and a select.

**Fix.** Show the two kind buttons (and mark *Maker* as required) only while
*Part number* has text; with the field empty they are not rendered. The
default stays *standard number* when they appear. Say so in § 1.3 and § 3, and
keep the e2e "maker's number without a maker" check as it is (it types a number
first). Not an extra rule for the core: the server already drops a kind sent
without a number.

### BR2-03 · minor · § 5.3's access sentence is not quite what the predicate does

**Problem.** § 5.3 says nothing leaks "since a machine has one unit at a time
and the key is checked at the ticket's site". The ticket access predicate
(`tickets.py:129-139`) is `t.unit_id IN (mine) OR m.unit_id IN (mine)`: a
user sees a ticket when its **raise unit** or the machine's **current unit** is
his. So a technician at the unit a machine was raised in, after the machine
moved to a unit at another site, still sees the old ticket (S017 § 5.3, by
design) and holds `ticket:work` at its site — and the suggestions, which read
every line on the machine's subtree, would offer him the part numbers fitted
on the later tickets at the new site, tickets he cannot open. The reverse holds
too (the new site's technician sees lines from the old site's tickets, which
he *can* open through `m.unit_id`).

**Why it matters.** The statement is a security claim and it is wrong as
worded; the actual exposure is small (description, number, maker of parts on a
machine the user has worked on, no ticket link, no site) and I think it should
be **accepted**, but it should be said rather than argued away.

**Fix.** Reword § 5.3: the lines are read by machine, not through the ticket
predicate; a user who may work a ticket on the machine sees what was fitted to
that machine on any ticket, including ones raised after it moved to a unit he
does not see — accepted, since a part number on a machine he maintains is not
confidential and the line carries no ticket or site. Add it to § 7 as a line
under decision 1 or 4. (Alternative, rejected: filtering the suggestions by the
ticket predicate — one more join for a case that arises only after a machine
moves between sites.) Also say what `total` is in the answer (`{"items",
"total"}`): the count after `LIMIT 20` is just `len(items)`; if `total` is the
count of distinct groups before the limit, say so, else drop it.

### BR2-04 · minor · The close hint lands at the moment it is most expensive to act on

**Problem.** § 1.6 shows the hint when the chosen action is *Replace* or
*Modify* and `parts` is empty — that is, after the engineer has already picked
the symptom, cause and action in the close dialog. Acting on it means Cancel →
"Discard your changes?" → Discard → *Add part* → fill the line → *Close* again
→ symptom, cause, action again. Seven steps, on a phone, for the hint to
achieve its purpose.

**Options.**
- (a) **Accept, and word the hint for the path it implies** (recommended; it
  is a hint, and most engineers will learn to record parts before closing):
  "No parts recorded. If any were fitted, cancel and add them on the ticket
  first." The close is not blocked, so the engineer who knows nothing was
  numbered simply saves. Say in § 1.6 that the dialog's inputs are lost on
  cancel (the FormModal guard) and that this is accepted.
- (b) Open the parts dialog from the hint, on top of the close dialog: two
  stacked modals on a phone — rejected, as the base pattern has none.
- (c) Make it a page-level reminder beside *Close* whenever `parts` is empty,
  the labour pattern: it would nag on every *Adjust* and *Clean* close —
  rejected.

### BR2-05 · nit · The shared node helper: the field and message differ per caller

`_check_component` raises `COMPONENT_OF_MACHINE` on field `component_id`
(`tickets.py:831-839`); the parts line needs "Choose the machine or one of its
parts" on `node_id` (§ 5.1). § 3 says the helper gains "a parameter that
accepts the machine itself"; it also needs the field and message (two
parameters, or the helper returns the row / `None` and each caller raises its
own refusal). One line in § 3 so the coder does not invent a third helper.

### BR2-06 · nit · The stale-page message promises a move that is not on offer

"Parts are recorded, so it was a fault — remove them or close it with cause
and action" is answered to a not-a-fault attempt from *raised*, *acknowledged*
or *in progress*, where *Close* is not available until back in service. Say
"… remove them, or put it back in service and close it with cause and action",
or shorten to "Parts are recorded, so it was a fault — remove them first".

### BR2-07 · nit · Docs and standards wording

- Plan.MD § 5 already has a `parts_used` row ("*Proposed* (§ 4.2): per ticket
  or PM job …", `Plan.MD:759`); § 3 Docs should say that row is **replaced** by
  `ticket_parts`, not that a row is added, and that PM jobs are decided later
  (§ 7 decision 6).
- § 2 ISO 14224: "the component, the level ISO 14224's taxonomy records
  failures at" — ISO 14224 records a failure against the **equipment unit**
  (level 6) and names the **subunit** and **maintainable item** (levels 7–8)
  where it occurred; Yantra's component is that maintainable item. One clause,
  so the owner reads the taxonomy right.
- § 1.2 "the labour panel's pattern … remove asks first": the inline *Remove?
  Yes / No* bar (`LabourPanel.vue:153-157`), not a modal confirm — fine, but
  name it so the coder copies the right one.

### BR2-08 · nit · An empty parts card on every closed ticket a `ticket:work` holder opens

`showParts = can("ticket:work") || parts.length > 0` shows "No parts recorded"
on closed tickets, not-a-fault ones included, where nothing can be added. The
labour panel does the same today (`showLabour`, `TicketDetailView.vue:79`), so
this is consistent; if the user would rather not see two empty cards on every
closed ticket, `(canWork && isOpen) || parts.length > 0` is the one-line
alternative — but then do it for labour too, or not at all.

### BR2-09 · nit · The *Fitted here before* list is narrowed by a field below it

§ 1.4 puts the list at the top of the dialog and narrows it by what is typed in
*Description*, further down. On a phone with the keyboard up, the list may be
scrolled out of view while the user types the thing that narrows it. Two
cheap fixes: put the list **directly under** the *Description* field (the
field first, the five rows under it, the other fields after), or keep it at
the top and say the narrowing is a convenience, not something the e2e asserts.
Either is fine; say which.

### BR2-10 · nit · Two small test gaps

- A PUT or DELETE on a row of **another** ticket → 404 (labour's `_labour_row`
  rule, `tickets.py:932-935`); listed for labour in S018, not here.
- The core cases "`number_kind` without a number is dropped" and "a maker with
  no number is allowed" are in the § 5.1 table but not named in § 3 Tests;
  "each rule and message of § 5.1" covers them — fine if the coder reads it so.

## Checked and found consistent

- **Locks.** `_lock_open_ticket` returns `equipment_id` and `site_id` from the
  locked read (`tickets.py:332-355`), so step 3's "the machine itself or below
  it" is decided from the locked ticket as § 5.2 says. The scrap path never
  takes a ticket lock (`equipment.py:368-394`), so (7) then the node's shared
  lock cannot cycle with it; S025's unit guard (unit `FOR UPDATE`, then tickets
  in share mode) touches neither the ticket row `FOR UPDATE` nor the node — no
  new edge there either.
- **Not a fault.** `_not_a_fault` runs inside `_apply_move` after the ticket
  lock (`tickets.py:752-803`); a 409 with no field reaches `MoveDialog`'s watch
  (`MoveDialog.vue:69-71`), which emits `reload` — the brief's description of
  the stale page holds. `SIGNIFICANT_MOVES` includes `not-a-fault`
  (`ticketLabels.js:108`), so the disabled button sits with *Close* in the
  significant group, apart from the chain buttons.
- **`_moves`.** It is built per entry name (`tickets.py:271-286`); adding
  `parts_hint_actions` to the `close` entry is one `elif`, one query. The S016
  seed codes are `'1'` Replace, `'3'` Modify, `'10'` Overhaul.
- **Keys.** `ticket:work` is technician and up plus IT admin; `ticket:close`
  is engineer and up, and engineer includes technician through
  `ROLE_INCLUDES`, so whoever can press *Not a fault* can also remove the lines
  (`config_rbac.py:82-115`). Both keys are in `SITE_SCOPED`.
- **Detail shape.** `Decimal` columns leave `row_to_dict` untouched and
  `jsonify` makes them strings (`db_helpers.py:105`); `"1.50"` needs nothing
  extra. `clean_body` turns the first core error into `{error, field}` 400
  (`api_common.py:75-83`).
- **Frontend.** `FormModal` is `modal-dialog-scrollable` with the footer
  outside the scrolling body, so the long dialog keeps Save and Cancel on
  screen; `expectDialogFits` measures exactly that
  (`frontend/e2e/support/dialogs.js:19-31`). `EditTicketDialog.vue:36-61` is
  the only source of the two-level component list, and the extraction the
  brief plans changes no behaviour. The send-back choice buttons
  (`MoveDialog.vue:157-175`) are the pattern the kind buttons copy.
- **Tests.** `conftest._TABLES` is the hand-kept FK-ordered list
  (`conftest.py:83-86`); `ticket_parts` before `tickets` is right. The e2e seed
  has a technician with `maint_technician` at all SMTW units, an engineer, and
  an operator limited to MCC2 (`seed_e2e.py:30-39`), enough for every § 8
  automated check.
- **Migration number.** S019's brief states v21 flatly (`S019 § 1`, § 3,
  § 4); S020's "whichever is coded first takes v21, the planner fixes both"
  handles it.
- **Standards.** ISO 14224:2016 Table 8 (maintenance data: man-hours per
  discipline and spare parts used), EN 13460 (the work order's materials),
  ISO 8000 as worded after BR1-12, ISO 9001 § 7.5, ISO 55001 § 7.5, the TPM
  planned-maintenance pillar — all cited correctly, with the one taxonomy
  clause above (BR2-07).
- **Track.** A migration, locks across two tables, a new endpoint beyond CRUD
  — full, correctly.
- **Manual checks.** The device check names account, network and where; the
  automated list has nothing a browser cannot judge.
