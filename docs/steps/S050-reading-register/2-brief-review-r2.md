```
Step: S050 — Meter reading register
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 25-10-2026
```

Reviewed against: 4d89084 (the uncommitted changes in the working tree are step documents and
agent files only; no code)

**Verdict: no `blocker` or `major` finding is open.** Three `minor` findings and a list of nits
follow. Every round-1 finding marked *Accepted* is in the brief's text, not only in the Review
log. Re-read: § 1.1, § 1.3–§ 1.7, § 2, § 3, § 5.2, § 5.3.4, § 5.5, § 6, § 7 decisions 3, 4 and
8, § 8.1–§ 8.5, § 9 items 3 and 7, and the S051 brief. The facts file
`scratch/brief-facts-S050.md` was used; the code it did not settle (`ReadingsView.vue`'s
mount and imports, the raise screen's picker and its e2e selectors, `MetersCard.vue`'s header,
`navigation.test.js`, `screens.spec.js`, Plan.MD line 797) was read.

## Findings

### BR2-01 — minor — "`v-show` or `<KeepAlive>`" are not the same: one loads the whole site's sheet behind the register

**Problem.** § 1.1 leaves the coder the choice between `v-show` and `<KeepAlive>` and says
only "the coder states which". The two differ in when the sheet mounts. `ReadingsView.vue`
runs `onMounted(init)` (line 215): it loads the sites, the units, my-units and then
`GET /api/readings/sheet?site_id=` for the whole site. With `v-show`, the sheet mounts as soon
as the page opens, also when an engineer arrives at `?tab=register&node=12` from the *Open
register* button and never looks at the sheet. With `<KeepAlive>`, the sheet mounts the first
time its tab shows and stays mounted after.

**Why it matters.** The brief says "The register mounts when its tab first shows" but says
nothing of the sheet. A supervisor's phone on the floor would fetch the site's full sheet
(S040: "a few queries for the whole site") for a register he opened from a machine's card.
Small for 50 users, but it is the "obvious waste" CLAUDE-COMMON names, and a coder who picks
`v-show` ships it without a word.

**Options.**
- (a) **Recommended.** State the rule: each tab mounts the first time it shows and stays
  mounted after. `<KeepAlive>` around the tab component gives this directly; `v-show` with a
  one-way "seen" flag (`v-if="sheetSeen" v-show="tab === 'sheet'"`) gives the same. Either is
  fine; the behaviour is the rule. One line in § 1.1 and decision 4.
- (b) Keep the free choice and accept the eager load with `v-show`. Say so in § 1.1.

### BR2-02 — minor — After a pick on the register, the search field and its result list stay above the table

**Problem.** § 1.3: "Under the field, the picked node's heading: 'code — name', its
`full_path`, and a link *Open equipment page*." The field stays on screen with its typed text,
and the brief says nothing about the result list. On the raise screen the picker vanishes once
a node is picked (`v-else-if="!nodeId"`, line 341), and a card with the node's "code — name",
`full_path` and a *Change* button takes its place (lines 379–387). The register would differ
from that for no stated reason, and the coder must decide alone whether the list of up to 20
rows (`py-3`, about 60 px each on a phone) closes after a pick.

**Why it matters.** On a phone the table is the job; a search field, a result list and a
heading above it push the first rows below the fold. One behaviour for one control (scope B)
also says the two screens should pick and re-pick the same way. A user who arrives from the
*Open register* button should see the node card and the table, not an empty search field.

**Options.**
- (a) **Recommended.** Follow the raise screen: while `node=` is in the URL the picker is
  hidden, and the node card shows "code — name", `full_path`, *Change* (clears `node` and
  `meters` from the URL, shows the picker again) and the link *Open equipment page*. With no
  `node=` the picker shows with the empty state "Find a machine or part to see its readings."
  under it. Say so in § 1.3 and in § 8.4's picker test.
- (b) Keep the field visible and say that a pick clears the text and the list. Two
  behaviours for one control; the empty field takes phone height for nothing.

### BR2-03 — minor — The picker's label and `id` are not named; the raise e2e tests find the field by its label

**Problem.** § 1.3 names the placeholder ("Code or name") and the result wording, but not the
field's label. `RaiseTicketView.vue` line 342 has `<label for="raise-search">Which equipment?`,
and `tickets-raise.spec.js` finds the field three times with
`getByLabel("Which equipment?")` (lines 58, 80, 90). The brief's line range for the template,
351–367, starts after the label and the input (342–350), so a coder who extracts exactly those
lines leaves the label and input in the raise screen and must invent a label for the register.

**Why it matters.** § 3 and § 8.4 say the raise e2e tests stay unchanged and must pass. They
pass only if the extracted picker keeps the label text. And the register's label is a scope B
choice the coder would otherwise make alone; a second wording ("Find equipment") is the
duplicate BR1-04 removed.

**Options.**
- (a) **Recommended.** The picker owns the label *Which equipment?* and one fixed `id`
  (`equipment-search`; one picker per page), on both screens. Correct the line range to
  341–368. One sentence in § 1.3.
- (b) The label is a prop; the raise screen passes *Which equipment?* and the register passes
  the same text. More code for no second wording.

## Nits

- **BR2-04** (nit) § 3 `ReadingsSheet.vue` "moved out of `ReadingsView.vue` unchanged": the
  folder changes, so the relative imports change too (`../api` → `../../api`,
  `./tickets/EventFields.vue` → `../tickets/EventFields.vue`,
  `./readings/ReadingSheetRow.vue` → `./ReadingSheetRow.vue`). Say "unchanged but for its
  import paths", so the code reviewer does not read the import diff as a change.
- **BR2-05** (nit) § 3, § 5.5 `parse_meter_type_ids(raw) -> (ids, error)`: its sibling
  `parse_meter_type_id` returns `(id, errors)` with a list of `{field, message}`. Use the same
  shape, and say what "absent or empty = all" returns (`None`, never `[]`), so the route cannot
  read an empty list as "no columns".
- **BR2-06** (nit) § 1.5 column header "Run hours (h)": say the header is the name alone when
  the type has no unit (a Yes / No meter), as `unitAndKind` does; no empty brackets.
- **BR2-07** (nit) § 5.2.2 cell `is_reset`: the database gives 0 / 1; say the core sends a
  boolean, as `reading_out` does (`bool(row["is_reset"])`).
- **BR2-08** (nit) § 8.4 storekeeper test: add that `/readings?tab=sheet` opens the register
  for him (§ 1.1, BR1-11 has no test).
- **BR2-09** (nit) § 9 item 7: S051 also edits `RaiseTicketView.vue` (the comment header,
  S051 § 3) and `tickets-raise.spec.js` line 155, a file S050 changes and a spec it runs. Name
  both, so the stale-brief check before coding looks there whichever step goes first.
- **BR2-10** (nit) § 3 Tests `screens.spec.js`: with `who: EVERYONE` the constant
  `READING_ROLES` (line 13) has no use left; remove it with the row.

## Checked and found consistent

- Every round-1 *Accepted* answer is in the brief's text: BR1-01 in § 1.1, § 3, decision 4 and
  the important test of § 8.4; BR1-02 in § 3, § 5.2.2 and § 8.1; BR1-03 in § 1.6, § 5.5, § 6
  (`shown`), § 8.2 and § 8.4; BR1-04 in § 1.3, § 3, decision 8 and § 8.4; BR1-05 in § 3, § 5.5
  and § 8.1; BR1-06 in § 2 and decision 3; BR1-07 in § 8.5; the nits BR1-08 to BR1-17 each at
  the place the log names.
- § 1.1: a user without `reading:log` never mounts the sheet, so `/api/readings/sheet` is
  never called for him; the S040 e2e tests open `/readings` as `reading:log` holders and
  expect `sheet-heading`, which the default tab keeps true. The sheet reads no route query
  (its site lives in `localStorage`), so the register's `router.replace` of `tab`, `node` and
  `meters` does not disturb it.
- § 1.3: `RaiseTicketView.vue` lines 139–168 hold the search state and the debounced call
  (`level: "all"`, `q`, `PICKER_SIZE` 20, `useDebounced`); the wording the brief lists is the
  code's ("Searching…", "No equipment found at your units.", "More found — type more of the
  code or name.", "code — name" with `full_path`). `chooseEquipment(id)` sets the URL, so
  "each screen decides what a pick does" matches.
- § 1.4: `MetersCard.vue` reads "No meters." when `meters.length === 0` and its header holds
  *Add meter* for `canEdit`; the card's `meters` are the meters in force (`_meters_out`), so
  "at least one meter in force" is what the card already knows. *Open register* starts with a
  verb (scope B).
- § 1.5: `formatReading(value, meterType)` returns `"${number} ${unit}"` for a number and
  "Yes" / "No" for a Yes / No meter, so `{ unit: false }` is one line and a unit test;
  `readingBadges` exists and gives High / Low / Not OK then Reset. "No longer on this
  machine" uses the card's word *machine* ("This machine only", "Remove … from this
  machine?").
- § 1.7: the 404 / 403 line says what happened and what to do, no code, no field name
  (scope B).
- § 2: ISO 17359 is the general guideline for condition monitoring (measuring points,
  intervals, trending against earlier values and alert limits); EN 13306:2017 defines
  condition monitoring as measuring an item's parameters at set intervals, by hand or
  automatically; ISO 55001 § 7.5 *Information requirements* is the requirements clause (ISO
  55000 the overview); TPM pillar 1 is autonomous maintenance with the operator's check and
  reading log. No guessed clause numbers remain.
- § 3 Tests: `navigation.test.js` line 38 (`visible(IT_ADMIN)`) and line 54
  (`visible(STOREKEEPER)` → `["equipment", "masters"]`) gain `"readings"` after `"tickets"` /
  before `"masters"`; line 41's test changes; lines 63 and 84 stay true because *Equipment*
  precedes *Readings*. `screens.spec.js` line 51 is the `/readings` row; the S040 bottom-bar
  test checks the manager only, who has six items today. `docs/Plan.MD` line 797 is the
  *Readings* screen line ("for roles with `reading:log`"); § 4.5 starts at line 714.
- § 5.2 / § 5.5: `answer_word`, `format_number`, `PICK_A_METER` and `parse_meter_type_id` are
  in `meters_core`, so the core can word a cell from its column's kind and the new parser has
  a sibling to sit beside. `reading_out` (`meters.py` line 257) is the shell's wording the
  core copies. `_meters_of`, `_marks`, `int_arg`, `MAX_PAGE`, `MAX_PER_PAGE`,
  `HISTORY_PER_PAGE` are as § 3 says.
- § 5.3.4: "a fixed handful of queries, none per meter or per row" matches the five reads
  listed.
- § 7 decisions 3, 4 and 8 match § 1.4, § 1.1 and § 1.3; the rejected alternatives are
  stated.
- § 8.5: no device check; the sideways-scroll test runs on `phone-webkit` in the user's full
  run (S046), which is the rule of README § Manual checks.
- § 9 item 7 and S051 § 6.3 agree: S051 changes `EventFields.vue` and the S040 tests at
  `readings.spec.js` lines 669, 683 and 756 (they assert the *Change* button, as the lines
  show); S050 moves the sheet's code; the two are coded one after the other. (BR2-09 adds the
  two files the item leaves out.)
- Pure core / thin shell holds after the changes: the pivot, the column rule and the id
  parser are in `meters_core`; the route reads and maps; the screen adds no rule. No new
  abstraction beyond the two pure functions, the parser and a picker component with two uses.
