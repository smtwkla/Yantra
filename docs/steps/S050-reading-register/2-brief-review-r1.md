```
Step: S050 — Meter reading register
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 25-10-2026
```

Reviewed against: 4d89084 (the uncommitted changes in the working tree are step documents only; no code)

**Verdict: one `major` finding is open (BR1-01, typed readings lost on a tab switch). No blocker.**
Six `minor` findings and a list of nits follow. U1–U3 are respected; nothing in the brief
contradicts them. The facts file `scratch/brief-facts-S050.md` was used; its row for
`/api/equipment/<id>/readings/register` ("called in 25 test files") is a prefix match on
`/api/equipment` and says nothing about the new route.

## Findings

### BR1-01 — major — Typed, unsaved readings are lost when the user taps the *Register* tab

**Problem.** § 1.1 makes `ReadingsView.vue` a tab shell and moves the sheet into
`ReadingsSheet.vue` "unchanged". The brief says nothing about what happens to typed rows when
the user switches tab. With the `MeView.vue` pattern (one child per tab, `v-if`), tapping
*Register* unmounts the sheet and every typed value goes.

**Why it matters.** The floor case is exactly this: a press supervisor types a round of
readings at shift end, taps *Register* to compare with yesterday, taps back, and the round is
empty. The app treats lost typed input as a defect (S007; the sheet itself asks before a site
switch discards typed readings, S040 CR1-02). A coder following the Me pattern would ship the
loss without noticing.

**Options.**
- (a) **Recommended.** Keep the sheet mounted while the *Register* tab shows: render the sheet
  with `v-show` (or `<KeepAlive>` around the tab components), so its state survives a tab
  switch. No new dialog, no change to the sheet. State it in § 1.1 and decision 4, and add an
  e2e test: type a value on the sheet, open *Register*, come back, the value is still there.
- (b) Ask before switching, as the site picker does ("Discard 3 typed readings?"). More code
  and one more question for the user.
- (c) Accept the loss and say so. Not recommended.

### BR1-02 — minor — `register_rows(readings, meter_type_ids)` cannot word a Yes / No cell

**Problem.** § 5.2.2 says each cell's value is "as `reading_out` gives it (a Yes / No meter
"yes" / "no")", and § 8.1 tests that "a Yes / No value comes back as words" from the core. But
`reading_out` lives in `meters.py` (the shell), and the core signature carries only
`meter_type_ids`, not the kind of each meter. The core cannot know which cells are Yes / No.

**Why it matters.** The coder must decide alone whether the shell formats each reading first
(`reading_out` per row, then the pivot) or the core takes the columns and calls
`meters_core.answer_word` / `format_number` itself. Both work; the brief's tests assume the
second, its signature the first.

**Options.**
- (a) **Recommended.** `register_rows(readings, columns)`: the columns (§ 5.1, each with its
  `meter_type`) decide the kind; the core words the value with `answer_word` and
  `format_number`, which are already in `meters_core`. § 8.1's test then holds as written.
- (b) The shell runs `reading_out` on each row first and the core only pivots. Then drop the
  Yes / No case from § 8.1 and move it to § 8.2.

### BR1-03 — minor — A stale `meters=` in the URL turns into a 400 the screen has no words for

**Problem.** § 5.5: an id "that is not a column of this node → 400 'Pick a meter'". The ids
live in the URL (§ 1.6, decision 7), so a bookmark or a link from a chat keeps them. An
engineer later removes that own meter (S038) and its readings are removed: it is no longer a
column, and the saved link answers 400. § 1.7 lists no state for it; the user sees a refusal
about a field he never typed.

**Options.**
- (a) **Recommended.** The route ignores an id that is not a column of this node, as it ignores
  duplicates, and answers with `shown` = the ids it used (all columns when none is left). The
  400 stays for a malformed list ("3,x", "0", "-1"): that is an API caller's error, not a
  stale link. The screen takes `shown` as the ticked set. Change § 5.5, § 6 and the § 8.2 case.
- (b) Keep the 400 and have the screen drop the ids and retry without them. Two requests for
  one stale link, and more code in the component.

### BR1-04 — minor — A third equipment search is planned where one exists

**Problem.** § 1.3 and decision 8 describe a new search ("Find equipment", `level=all`, `q`,
20 matches, "code — name" with the level, "Type more of the code to narrow the list").
`RaiseTicketView.vue` lines 139–168 and 351–367 already hold this picker: `level: "all"`,
`q`, `PICKER_SIZE = 20`, `useDebounced`, rows with `full_path`, "No equipment found at your
units.", "More found — type more of the code or name.". `EquipmentMoveModal.vue` is a second
copy (per level). The brief plans a third, with new wording.

**Why it matters.** DRY (CLAUDE-COMMON), and scope B's "same word for the same thing": the
register would say "Type more of the code to narrow the list" where the raise screen says
"More found — type more of the code or name.". Showing the level instead of `full_path` also
loses the one thing a component-unit's row needs: which machine it belongs to (two motors can
both be "Main motor").

**Options.**
- (a) **Recommended.** Extract the raise screen's picker into
  `frontend/src/components/EquipmentPicker.vue` (the field, the debounced search, the result
  list with `full_path`, the "More found" line, the empty text) and use it on both screens.
  Add it to § 3 and a line to § 8.4 that the raise flow still picks equipment. The move
  dialog stays as it is (its per-level searches are a different rule).
- (b) Keep a separate search in `ReadingsRegister.vue` but reuse the raise screen's exact
  wording and show `full_path`. Less work, the duplicate stays.

### BR1-05 — minor — Where the `meter_type_ids` list is parsed is not said

**Problem.** § 5.5 gives the rule (comma list, positive integers, duplicates ignored, three
malformed shapes refused with `PICK_A_METER`), but § 3 names no function for it and § 8.1 has
no test. `int_arg` takes one integer, so the coder writes new parsing and must choose where.

**Why it matters.** A parsing rule in the route is the kind of logic the project keeps in the
pure core (`parse_meter_type_id`, `parse_reading_request` are in `meters_core`); and an
untested parser on a public query string is where "3," or " 3" slips through.

**Options.**
- (a) **Recommended.** `meters_core.parse_meter_type_ids(raw) -> (ids, error)` next to
  `parse_meter_type_id`, with the cases of § 5.5 in `test_meters_core.py` (absent, empty,
  "3,7", "3,3", "3,x", "0", "-1", " 3 , 7 "); the route maps `error` to 400 on
  `meter_type_ids`. The "not a column of this node" check stays in the route (it needs the
  columns).
- (b) Parse in the route with a one-line comprehension and test only through the API (§ 8.2).

### BR1-06 — minor — § 2 carries "to verify" twice and cites the overview standard for a requirement

**Problem.** The ISO 17359 and EN 13306 lines end with "(Clause number: to verify.)" and
"(Clause number and exact wording: to verify.)". The ISO 55000 line cites the overview
standard for "records of an asset should be easy to find".

**Why it matters.** The project owner is learning the standards from these briefs; a
placeholder reaches gate A as if it were a citation, and a guessed clause number is worse
than none.

**What the standards say, in short.**
- *ISO 17359* (condition monitoring and diagnostics of machines, general guidelines): set
  measuring points and parameters, take readings at set intervals, record them with their
  time, compare with earlier values and with alert limits (trending), and act on a change.
  The register is the "compare with earlier values" step on screen.
- *EN 13306* defines *condition monitoring* as a maintenance activity that measures an
  item's parameters at set intervals, by hand or automatically. The quoted wording is close
  to the definition; cite it as "EN 13306:2017, the definition of *condition monitoring*"
  without a clause number unless the text is at hand.
- *ISO 55001* (the requirements; ISO 55000 is the overview) § 7.5 *Information
  requirements*: the organisation decides which asset information it needs, and keeps it
  of a quality and in a form that the people who decide on the asset can use. That is the
  line for "every role that may see the equipment gets the same view".

**Options.**
- (a) **Recommended.** Drop the two "to verify" notes and the clause numbers; cite the
  standards by name and year; change "ISO 55000 (asset information)" to "ISO 55001 § 7.5".
- (b) Verify the clause numbers against the texts before approval and keep them.

### BR1-07 — minor — The device check of § 8.5 is a layout check a browser engine runs

**Problem.** § 8.5 lists "the register on KLA's iPhone … reads clearly and scrolls sideways
with a thumb", and says itself that a browser engine runs the same check. The rule
(`docs/steps/README.md` § Manual checks, this agent's brief) puts a check a browser could do
on the automated list, not the device list. The row also names no account.

**Options.**
- (a) **Recommended.** Drop the row. The sideways-scroll test of § 8.4 runs on `phone-webkit`
  in the full suite the user runs before each deploy (S046; S047's *Full* level), which is
  the iPhone check.
- (b) Keep it as a plain row with the account (KLA's own login), network (mobile data) and
  place (production) filled in, as the rule asks.

## Nits

- **BR1-08** (nit) § 1.4, § 8.4: the card's button reads *Register*, a noun; scope B wants a
  verb that names the result. Use *Open register* (the tab keeps *Register*).
- **BR1-09** (nit) § 1.5 column header: "Run hours (h) (removed)" is two brackets in a row.
  Use a small badge under the name, "No longer on this machine", in the wording of the card's
  source badges; or "Run hours (h) · removed".
- **BR1-10** (nit) § 1.5 cell: `formatReading` appends the unit ("12,345.6 h") that the header
  already carries; on a phone four such cells use the width twice. Show the number only in
  the cells (a `formatReading(value, type, { unit: false })` option or a sibling helper, with
  a unit test), the marks beside it.
- **BR1-11** (nit) § 1.1: say that `?tab=sheet` typed by a user without `reading:log` opens
  *Register* (the only tab he has), so the sheet never mounts for him.
- **BR1-12** (nit) § 1.7: a 403 on the register (listed in § 6) has no screen text. Treat it as
  the 404 case; `equipment:read` is `("*",)`, so a 403 cannot happen for a site role today.
- **BR1-13** (nit) § 3 Tests: `navigation.test.js` line 54 (`visible(STOREKEEPER)` →
  `["equipment", "readings", "masters"]`) changes too, not only line 38; name both. Lines
  63 and 84 (the storekeeper lands on Equipment) stay true because *Equipment* precedes
  *Readings*; say so.
- **BR1-14** (nit) § 3 Docs: `docs/Plan.MD` § 6 *Screens*, the *Readings* line (797: "for roles
  with `reading:log`"), must change with § 4.5; add it to the list.
- **BR1-15** (nit) decision 3 and § 1.4: a node whose only meter was removed has no *Register*
  button (the card shows "No meters."); its readings are still reached by the *Register* tab's
  search. Say so in decision 3, so the coder does not try to detect readings from the card.
- **BR1-16** (nit) § 5.3.4 "Two queries for the rows plus one count" leaves out the column
  reads (`_meters_of`: model meters and node rows; plus one for the removed-from-node types).
  Say "a fixed handful of queries, none per meter or per row".
- **BR1-17** (nit) § 1.3 and § 9.3: the result count message is settled by BR1-04; whichever
  option is taken, drop the second wording from § 9.3.

## Checked and found consistent

- U1–U3 are carried into § 1, decisions 2, 4, 5 and § 1 Out of scope; nothing contradicts
  them. The brief's header lists what U1 changes from S040 (decision 5).
- `meters.py`: `list_readings` uses `load_node_for_user(cur, node_id, for_update=False,
  key="equipment:read")` as the brief says; `_meters_of`, `reading_out`, `_marks`, `int_arg`,
  `MAX_PAGE`, `MAX_PER_PAGE`, `HISTORY_PER_PAGE` (30) and `PICK_A_METER` exist with the stated
  meaning. `effective_meters` orders by meter type name, so "the order of the *Meters* card"
  is well defined.
- `SITE_SCOPED` holds `equipment:read`; `equipment:read` is `("*",)`, so the storekeeper and
  IT admin hold it (§ 5.4, § 8.2).
- `meter_readings` v32 index `ix_meter_readings_meter_time (equipment_id, meter_type_id,
  taken_at)` serves the `DISTINCT taken_at` page and the `IN (…)` read; no migration is needed.
- `navigation.js`: the *Readings* item's `perm` is `reading:log` today; `canOpenRoute` follows
  the item, so `App.vue`'s redirect opens for `equipment:read` holders with the one-word
  change. The landing page is unchanged (*Me* and *Equipment* come first). IT admin's bottom
  bar grows to six items, the count the manager already has (the S040 e2e test).
- `navigation.test.js` line 41 is the test the brief names; `screens.spec.js` line 51 is the
  `/readings` row with `READING_ROLES`; `test_rbac.py` holds no route-to-key list (no "route").
- `MeView.vue` keeps the tab in the URL query with `router.replace` and leaves the default
  out: the pattern the brief names.
- `ReadingHistoryModal.vue` drops rows already shown by id after *Show more* (line 49–52), the
  pattern § 5.3.5 names; the brief's time-keyed version is a fair match.
- The e2e seed's storekeeper holds `maint_storekeeper` at every SMTW unit, so the § 8.4
  storekeeper test can open a machine's register; `meterMachine` and `logByApi` exist for the
  API set-up.
- Pure core / thin shell: the pivot and the column rule are in `meters_core`; the route reads
  and calls. The frontend adds no rule (BR1-02 and BR1-05 tighten the placement, they do not
  question it).
- Scope B of the empty states (§ 1.7): one line, what is wrong and what to do, no codes; the
  load-failure line and *Try again* are the sheet's own.
- No new permission key, no write path, no locking: § 5.4 and § 5.6 cover access and the
  database down. No new abstraction beyond the two pure functions and (BR1-04) a picker
  component with two uses.
