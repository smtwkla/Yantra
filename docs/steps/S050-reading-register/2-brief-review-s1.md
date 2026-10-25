```
Step: S050 — Meter reading register
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 25-10-2026
```

Reviewed against: 4d89084 + uncommitted S047 (refs/steps/S047, 1a34660), S051 (refs/steps/S051, ecbd1b7)

**Verdict: no `blocker` or `major` is open.** The brief's design holds. Three `minor` findings
(the e2e run instruction, the tag of the sideways-scroll test, and what S051 really changed in the
two views S050 edits) and five nits, all fixed in the brief text. The coder can start once they
are answered.

This is a staleness review (round s1): one question, does each statement of the brief still hold
for the code changed since its baseline. I read the brief's `Baseline:` 4d89084 against the S051
snapshot (`git diff 4d89084 refs/steps/S051`) for the five files the orchestrator named, plus
`EventFields.vue`, `e2e/support/tickets.js`, `journeys.spec.js`, `playwright.config.js`,
`run-e2e-tests.bat`, `.claude/agents/coder.md`, `.claude/CLAUDE.md` § Browser tests, `docs/Plan.MD`
and `docs/steps/README.md` § Manual checks, and the S047 and S051 briefs. No facts file was given
for this round; I checked the names and line references in the snapshot myself.

## Findings

### BS1-01 — minor — § 8.6 and § 8.5: the e2e run instruction names the wrong run

**What changed.** S047 (1a34660) gives `tooling/run-e2e-tests.bat` three levels. No flag is
**Normal**: every test on `phone-chromium`, the `@device` tests on `desktop-chromium`. "Full"
now names a level (`--level=full`, all three devices) that only the release and KLA run. And an
explicit `--project` **turns the `@device` filter off**: every matching test runs on every named
project (S047 § 1.1, BR1-01). The run rules in `.claude/agents/coder.md`, `.claude/CLAUDE.md`
§ Browser tests and `docs/steps/README.md` § Manual checks now say: targeted runs at Normal as
often as needed, the whole suite at Normal once when the coding is done, never Full.

**What in the brief is now wrong.**
- § 8.6: "the targeted e2e specs and the full e2e run once at the end of coding
  (`--project=phone-chromium --project=desktop-chromium`)". That command now runs **every** test
  on both projects, more than Normal, and the word "full" points the coder at the Full level.
- § 8.5: "runs on `phone-webkit` in the full suite the user runs before each deploy (S046)". The
  iPhone run is now the release's own Full run (`tooling/release-tests.bat` runs
  `run-e2e-tests.bat --level=full` after the unit suites, S047 § 1.6).
- § 8.4's heading says "targeted" without the level.

**Why it matters.** The coder follows § 8.6 literally and either runs the wrong set or the Full
level, which the run rules forbid for a step.

**Fix (recommended).** § 8.6: "the targeted specs at Normal (`tooling/run-e2e-tests.bat
e2e/readings.spec.js e2e/tickets-raise.spec.js e2e/screens.spec.js`) as often as needed; the
whole suite at Normal once when the coding is done (`tooling/run-e2e-tests.bat`, no flag, no
`--project`); never `--level=full`". § 8.5: "The sideways-scroll test of § 8.4 runs on
`phone-webkit` in the release's Full run (`tooling/release-tests.bat`, S047), which is the iPhone
check." § 8.4 heading: "(e2e, `frontend/e2e/readings.spec.js`, targeted at Normal; set-up by API)".

### BS1-02 — minor — § 8.4 and § 9 item 6: the sideways-scroll test is a `@device` test, so it must hold on desktop too

**What changed.** S047 § 1.3 (approved by KLA, "by purpose") tags a test `@device` when its title
names a layout check ("in view", "no sideways scroll", …) or its main assertion is a geometry.
At Normal a `@device` test runs on `phone-chromium` **and** `desktop-chromium` (viewport
1366 × 768, `playwright.config.js:33`); untagged tests run on the phone only. S051's staleness
round settled the same point for its layout test (S051 § 5, BS1-02): tagged `@device`, titled as
a layout check, no "on a phone (Pixel 7)" in the title.

**What in the brief is now wrong.** § 9 item 6 still says "S047 (gate A) may tag … the
stale-brief check at implement time covers it" — this is that check. § 8.4 names no tag, and
its layout test reads "S050: on a phone (Pixel 7) the meter columns scroll sideways inside the
table, the page does not (`scrollWidth` of the page ≤ its width), and the time column stays in
view". Written as it stands, two of its assertions can fail on desktop: with three or four
meters a 1366 px table does not overflow, so "the meter columns scroll sideways inside the
table" has nothing to scroll.

**Why it matters.** A layout test left untagged is a `minor` code-review finding
(`code-reviewer.md`, S047); tagged and written for the Pixel 7 only, it is red on desktop at
Normal.

**Options.**
- (a) **Recommended.** Tag it `@device`; title it as a layout check without a device ("S050: the
  meter columns scroll sideways inside the table, not the page, and the time column stays in
  view"); set the node up with enough meters that the table overflows at 1366 px too (about
  twelve meters of 110–130 px each; the coder measures and states the count), then assert on
  both devices: the table frame's `scrollWidth` > its `clientWidth`, the page's
  `scrollWidth` ≤ its width, and the time column's left edge does not move after
  `frame.scrollLeft` is set. One test, the same assertions on every device.
- (b) Tag it `@device` and keep three meters; assert only what holds at any width (no page
  sideways scroll, time column in view) and skip the overflow assertion when the frame does not
  overflow. Weaker: on desktop it proves nothing about the frame.
- (c) Leave it untagged (phone only at Normal, all three at Full). Against S047's rule by
  purpose.

**And the rest of the S050 tests.** State in § 8.4 that the other eight `S050:` tests are
untagged logic tests, and that the `screens.spec.js` tests already carry `@smoke` and
`@device` (the `/readings` row change inherits them). The storekeeper nav test (§ 8.4, seventh
bullet) should find *Readings* by role in whichever nav is visible (bottom bar on the phone,
sidebar on desktop) so it stays a logic test; the S040 bottom-bar test in `screens.spec.js`
already covers the bar's width.

### BS1-03 — minor — intro and § 9 item 7: S051 changed code in both views S050 edits, not only `EventFields.vue` and a comment

**What changed** (ecbd1b7). Beyond `EventFields.vue` and the comment headers, S051's CR1-01 fix
keyed the time field per round or per form:
- `ReadingsView.vue`: a new `const rounds = ref(0)` (line 44), `rounds.value++` in `enterMore()`
  (line 290), and `:key="rounds"` on the sheet's `<EventFields>` (line 350);
- `RaiseTicketView.vue`: `const restoreFieldKey = ref(0)` (line 186), `restoreFieldKey.value++`
  in `resetForm()` (line 198), and `:key="restoreFieldKey"` on the *Already fixed*
  `<EventFields>` (line 489);
- `ReadingFormModal.vue` keyed per opening; `e2e/support/tickets.js` `setEventTime` unticks
  *Now*; `readings.spec.js` gains six `S051:` tests, two of which drive the sheet
  (`openSheet(page, "engineer")`, the page's *Now* check box, *Enter more readings*).

**What in the brief is now wrong.** The intro says S051 "changes the shared time field the
sheet uses, not the sheet's code", and § 9 item 7 says S051 changes "`EventFields.vue`, the
comment header of `RaiseTicketView.vue`, `tickets-raise.spec.js` and the S040 e2e tests that
click *Change*". Both understate it. Nothing in S050's design changes: the brief already says
the sheet moves "unchanged except its import paths" and the raise screen's "behaviour and
wording" stay, so the moved sheet carries `rounds` and its `:key`, and the picker extraction
leaves `restoreFieldKey` alone.

**Why it matters.** The coder must not take the sheet or the raise screen from an older copy,
and must keep the S051 tests green after the move: "S051: Enter more readings starts the next
round with Now ticked" opens `/readings` as an engineer and expects the sheet (the default tab
for a `reading:log` holder, § 1.1, so it holds) and finds the *Now* check box by role on the
page, so the *Register* tab must add no check box named *Now* (its chooser's boxes carry meter
names and *Show all*; fine as specified).

**Fix (recommended).** Intro: "S051 (refs/steps/S051, ecbd1b7) changed `EventFields.vue` and
keyed the time field in `ReadingsView.vue` (`rounds`) and `RaiseTicketView.vue`
(`restoreFieldKey`); S050 moves and edits the files as they stand there." § 9 item 7: the same
list, and "the six `S051:` tests in `readings.spec.js` must pass after the move; the sheet stays
the default tab for `reading:log` holders, so they do." § 3, `ReadingsSheet.vue`: "the sheet as
it stands after S051 (with the `rounds` key on `EventFields`) moved out unchanged".

## Nits

- **BS1-04** (nit) § 1.3: the `RaiseTicketView.vue` template range "341–368" is now 344–371
  (S051 added three script lines above it); the script range 139–168 and the
  `tickets-raise.spec.js` lines 58, 80, 90 still hold. Update the one range.
- **BS1-05** (nit) § 3 Docs: `docs/Plan.MD` § 6's *Readings* line is now line 799 (the planner
  added the "Decided (S050)" and "Decided (S052)" lines in § 4.5 at gate A). And § 4.5 already
  holds "**Decided (S050, approved 25-10-2026)**": say the coder turns that line into the
  "Built (S050)" line rather than adding a second one. S051 also added a "Time field (S051)"
  note to the S039 and S040 lines there; no S050 change to those.
- **BS1-06** (nit) header and intro: "S047 is at gate A" and "S051 (in review)" are stale; both
  are at gate B as snapshots `refs/steps/S047` (1a34660) and `refs/steps/S051` (ecbd1b7),
  uncommitted. § 9 items 6 and 7 are now settled (BS1-02, BS1-03): write them as facts, not open
  questions.
- **BS1-07** (nit) § 3 Tests / § 8.6: `journeys.spec.js` (S047, `@smoke`) journey 3 opens
  `/readings` as a supervisor and expects `sheet-heading` — it holds with *Sheet* as the default
  tab; journey 2 raises from the equipment page, so it does not use the picker. Add
  `e2e/journeys.spec.js` to the targeted set, or note that the whole-suite Normal run covers
  it. Also add to § 3's `readings.spec.js` line: "the S040 and S051 tests open `/readings` and
  must still land on the sheet".
- **BS1-08** (nit) § 3 Docs: the snapshot's `.claude/CLAUDE.md` § SMTW-Review map still reads
  `readings` S039/S040 (S051 did not add itself, though its tests are in that file). Since the
  coder edits that entry, write `readings` S039/S040/S050/S051, and leave `journeys` S047 as it
  is.

## Checked and found consistent

- `ReadingsView.vue` (snapshot): the S051 change is three lines (`rounds`, `enterMore()`,
  `:key`); the sheet's script, template and styles move to `ReadingsSheet.vue` as the brief
  says. `EventFields.vue`'s 30-second `setInterval` is cleared in `onBeforeUnmount`; with the
  sheet kept mounted across a tab switch (`<KeepAlive>` or the seen-flag, § 1.1) it keeps
  ticking while *Register* shows, which only refreshes the shown time, and it is cleared when
  the user leaves `/readings`. No change to the BR1-01 design.
- `RaiseTicketView.vue` (snapshot): the picker's script (lines 139–168: `searchText`,
  `results`, `searching`, `searchError`, `searchSeq`, `search()`, `useDebounced`,
  `PICKER_SIZE`) and template (label *Which equipment?*, input id `raise-search`, placeholder
  "Code or name", "Searching…", "No equipment found at your units.", "code — name" with
  `full_path`, "More found — type more of the code or name.") are as § 1.3 describes;
  `chooseEquipment(id)` still sets `?equipment=`. The S051 edits touch the *Already fixed*
  block only.
- `tickets-raise.spec.js` (snapshot): the three picks by `getByLabel("Which equipment?")` at
  lines 58, 80, 90 hold; S051 changed line 155 (`#raise-restore-now`) and tagged two tests
  `@device`; S050 leaves the file unchanged, as § 3 says.
- `screens.spec.js` (snapshot): `READING_ROLES` (line 13) and the `/readings` row (line 51,
  `shows:` the site picker for the manager, `sheet-heading` "SMTW — " for the others) are as the
  brief says; the row's `shows` needs the third branch the brief names (the picker's search field
  for the storekeeper and IT admin). The nine tests already carry `@smoke` and `@device`.
- `readings.spec.js` (snapshot): the S040 tests still open `/readings` and expect the sheet;
  the two S040 A1 tests now assert the *Now* check box instead of *Change* (S051); S050 only
  adds tests.
- `navigation.test.js` (not changed since the baseline): lines 38, 41, 54, 63, 84 are as § 3
  cites them.
- Backend: nothing S050 touches (`meters.py`, `meters_core.py`, `test_readings_api.py`,
  `test_meters_core.py`) changed between 4d89084 and the S051 snapshot.
- `navigation.js`, `MetersCard.vue`, `meterLabels.js`, `MeView.vue` (the tab-in-URL pattern):
  unchanged since the baseline.
- `.claude/CLAUDE.md` § SMTW-Review and the brief's § 3 Docs: the map entry S050 edits exists
  at the snapshot (`readings` S039/S040), BS1-08 aside.
