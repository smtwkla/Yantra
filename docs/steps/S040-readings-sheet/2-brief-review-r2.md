```
Step: S040 — End-of-day readings sheet
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 24-10-2026
```

Reviewed against: e451c33 + uncommitted S035 (`navigation.js`, `router/index.js`, `App.vue`, `navigation.test.js`), S036 (`TicketRow.vue`, `main.css`, `ticketLabels.js`, `TicketDetailView.vue`, `EquipmentDetailView.vue`) and S041 (`equipment.spec.js`); plus the S037 (v29), S038 (v30) and S039 (v31) briefs as of U3 as the assumed baseline (none approved or coded). Facts file: `scratch/brief-facts-S040.md` (its "not found" rows for `backend/meters.py`, `effective_meters`, `formatReading`, `test_readings_api.py`, `readings.spec.js`, `reading_unit_ids` and `readingSites` are expected: S038, S039 and this step create them).

**Verdict: no `blocker` or `major` finding is open.** Round 2 re-read only what U3 changed: the need and the answers, § 1.2, § 1.4, § 1.6, § 1.8, Out of scope, § 3, § 5.1, § 6, decisions 2, 4, 8 and 9, § 8, Acceptance and § 9.1. The move to one sheet per site holds: the unit set `accessible_unit_ids(cur, "reading:log")` gives is exactly the units the sheet lists and the units S039's POST accepts, for a user with some units of a site and for admin. Three `minor` findings: the site's name and active flag are not on the list the brief builds the picker from; the supervisor's e2e case has no machine at MCC1 to show; and "Ask an engineer" repeated on every saved row. Then nits.

## Findings

### BR2-01 — minor — § 1.2, § 3, § 8: the site's name, code and active flag do not come from the units list

**Problem.** § 1.2 says the sites are "read over the masters' units list, whose rows carry `site_id` and `site_code`", and that "the site's name is the heading". `_UNIT_SELECT` (`masters.py:78`) joins `site_code` and `full_code` only: no site name, no site `active`. § 8's `screens.spec.js` locator then calls the heading "SMTW", which is the code, not the name ("Main factory, Pavoorchatram" in the seeds). The picker's option text is not stated either. The Tickets site filter shows `s.code` from the `sites` store (`TicketsView.vue:144`, `ensureSites()`).

The active flag matters too: `user_unit_ids` keeps active **units** (`auth_utils._unit_pools`) but never checks the **site** (`access_core.valid_memberships` checks the role only). A user whose units sit at a deactivated site keeps them in `reading_unit_ids`, so `readingSites` offers the site, and the sheet read answers 404 (§ 5.1 "inactive"), which the page shows as "Readings could not be loaded. Try again in a minute." — a wrong message for a permanent state.

**Why it matters.** The coder would pick the source and the words alone, and the e2e locator depends on them.

**Options.**
- (a) **Recommended.** `readingSites(allUnits, allSites, mine)` takes both cached lists (`ensureUnits()`, `ensureSites()`): the active sites that have an active unit in `reading_unit_ids` (every active site with an active unit when it is `null`), as `{id, code, name}`. The picker shows the code, as the Tickets filter does; the heading shows "SMTW — Main factory, Pavoorchatram" from the sheet GET's `site` (code first, so a phone shows the short part). § 8's locator is the heading with the code. One sentence in § 1.2 and § 3.
- (b) Codes only, everywhere, from the units list plus `ensureSites()` for `active`. Shorter, and the picker and the heading read the same.

### BR2-02 — minor — § 1.4, § 8: a unit with no meter rows, and the supervisor's e2e case

**Problem.** § 1.4 lists "the site's machines that have meters in force … grouped by unit". It does not say whether a unit of the user's set with **no** such machine gets a heading. § 8's set-up makes the test machine at SMTW.MCC2 only (S039 § 8), yet the test "the supervisor sees no site picker and both MCC1 and MCC2 on one sheet" expects MCC1 on the sheet. With an empty MCC1 left out, the test fails; with it shown, the supervisor reads an empty heading every day.

**Options.**
- (a) **Recommended.** Units with no machine with meters are not listed (one line in § 1.4 and § 6: `units` holds only units with at least one machine). The `beforeAll` makes a second machine per project at SMTW.MCC1 with one counter (the `createEquipment` with a unit argument, S039 BR2-04). The supervisor test then sees both units; and a new line in the operator's test asserts MCC2 only, which is the "some units of a site" case of § 5.1 seen in the browser (the backend test has it already).
- (b) List every unit of the set, with "No meters" under an empty heading. No set-up change; noise on the floor.

### BR2-03 — minor — § 1.6, decision 2: "Saved. Ask an engineer to remove it if it is wrong." on every saved row

**Problem.** For an operator or a supervisor every saved row reads "Saved. Ask an engineer to remove it if it is wrong.": on a 40-row sheet, 40 copies of a sentence about a mistake nobody made. On a Yes / No row it stacks under "Saved. Not OK: the expected answer is Yes." (two sentences about one row), and an amount row gets it under its "amount for the period just ended" label. The user's U3 settles who removes; the per-row text is the planner's.

**Why it matters.** Scope B asks for text the user needs for the job; the row's job is done at *Saved*. A judgement call the user should make, so not a nit.

**Options.**
- (a) **Recommended.** A saved row reads *Saved* for everyone. For a user without `equipment:edit` at the row's unit, one line for the whole sheet, shown once after the first save, under the sticky bar on a phone and under the button on desktop: "A wrong reading is removed by an engineer. Ask one." The e2e test "the operator's saved row says Ask an engineer and has no Undo" asserts the one line and the missing *Undo*.
- (b) Keep the sentence per row, as written.

## Nits

- **BR2-04** (nit) § 1.4: with units grouped, say where *Show out of use* sits: at the end of each unit's group, so an idle press stays under its unit, not in one list at the end of the sheet.
- **BR2-05** (nit) § 1.4, § 1.6: "9 of 48 read today" and "3 of 12 rows filled" count the same meter rows; use one denominator and one noun: "3 of 48 filled".
- **BR2-06** (nit) § 1.4: the amount row's label "amount for the period just ended" is S039's help "The amount for the period just ended, such as this shift." in other words; use S039's sentence once, so both screens say the same.
- **BR2-07** (nit) § 1.7: a 404 on the sheet read (access changed or the site deactivated after the lists were cached) is not a "Try again in a minute" case: forget the remembered site and show the picker again, with "This site is no longer available. Pick another site." With BR2-01 (a) it is rare; one line.
- **BR2-08** (nit) § 8 e2e: the S040 cases lean on readings S039's tests logged on the shared machine (the too-low counter, *Today*), which holds only while the whole file runs in order (`workers: 1`, `fullyParallel: false`). Let a S040 `beforeAll` post its own readings, so `--grep S040` passes alone. Name the technique for "Save readings is disabled while saving": a delayed `page.route` on the POST.
- **BR2-09** (nit) § 1.4 phone layout: unit headings `position: sticky; top: 0` inside the scrolling main, so on a long sheet the user always sees which unit the rows belong to. Optional; one line.
- **BR2-10** (nit) § 1.8: say that the site picker stays in the empty state (only *Time taken* and *Save readings* hide); § 8's manager case ("picks BRICKS, reloads") runs in that state, since BRICKS has no meters in the e2e database.

## Checked and found consistent

- **Site scoping, some units of a site.** `access_core.unit_ids_for` gives the user's own active unit rows at each site whose role grants the key (`all_units` → every active unit of that site). The sheet lists units of that set (§ 5.1); S039's POST passes `load_node_for_user` by the same rows (`equipment:read` units, then `reading:log` at the site), so no row the sheet shows is refused with 403 or 404. The supervisor at SMTW with MCC1 and MCC2 sees two groups; the operator with MCC2 sees one.
- **Admin.** `every_unit_by_token` → `None`; `reading_unit_ids` is `null`, the picker offers every site (BR2-01 adds the active filter), and the route checks `active` on the site and its units itself (§ 5.1, BR1-17). `reading:log` is held by site roles only, so `None` means admin.
- **The remembered site.** A key no longer in the offered list falls back to the first site (§ 1.2); no site at all is the `noUnits` state (§ 1.8, `stores/equipment.js:18`, the text of `TicketsView.vue:171`). The 404 edge is BR2-07.
- **Undo.** Shown from `edit_unit_ids` of the row's unit, which matches S039's DELETE (`load_node_for_user` with key `equipment:edit` at the site; the unit through `_can_access`). IT admin holds `equipment:edit` but no `reading:log`, so no sheet and no Undo there, as § 1.1 says.
- **Yes / No on the sheet versus S039's dialog.** The difference is stated, with its reason, in decision 9 (the dialog saves at one tap, S039 decision 11; the sheet has one save action and a stray tap must be clearable). The row sends `value` `"yes"` / `"no"` to S039's POST; *Not OK* comes from the stored `limit_state`; the wording "Saved. Not OK: the expected answer is Yes." and the badge are S039's; no *Meter reset* tick on it. Sound.
- **The amount row.** No reset tick; a value lower than the last one is accepted (S039 § 5.2.4); the e2e case names it.
- **Grouped layout on a phone.** One card per machine, parts inside it (BR1-07), unit headings in code order, the sticky bar inside `main.app-content` above the fixed 56 px nav (`main.css:80`), end padding. The Yes / No buttons at 48 px side by side fit a Pixel 7 row. BR2-09 is the one addition.
- **The e2e seeds.** `e2e_supervisor`: SMTW, MCC1 and MCC2; `e2e_manager`: SMTW and BRICKS, all units (`seed_e2e.py:39`, `:43`). BRICKS.FILTER has a pump with no meters, so the manager's reload case runs in the empty state (BR2-10).
- **Read today.** `toLocalDateValue` gives the phone's local date, and the phones are IST (`ticketLabels.js:124`), so the day test the brief describes is one line.
- **The nav.** S035's working tree has `me` first; `navigation.test.js` has five `visible(...)` lines (operator, engineer, manager, IT admin, storekeeper), three of which gain *Readings*.
- **Round 1 answers in the text.** BR1-01 to BR1-04, BR1-07 to BR1-18 are in the sections the Review log names; BR1-05 and BR1-06 stand as proposals for gate A in § 1.4, § 9.4 and § 9.5.
- **Scope B.** *Save readings*, *Undo*, *Try again*, *Show out of use*, "Pick a site", "Not saved. Try again in a minute." and the empty state are short and plain; BR2-03, BR2-05 and BR2-06 are the exceptions.
- **Track and checks.** Full track still right; the device check names account, network and where; the important automated checks assert what the user sees.
