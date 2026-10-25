```
Step: S052 — Meter readings on the ticket
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 25-10-2026
```

Reviewed against: 4d89084 + uncommitted S047, S051, S050 (snapshots `refs/steps/S047` 1a34660, `refs/steps/S051` 2dbd791, `refs/steps/S050` 2e0e28f; the working tree equals `refs/steps/S050` for the files named here)

**Verdict: no `blocker` or `major` is open.** The design holds: nothing S047, S051 or S050 changed touches a decision KLA approved. Four `minor` findings and two nits, all wording and reuse: S050 now provides the *Register* URL helper and the badge colour helper the card should reuse; the e2e run rule in § 8.6 is the pre-S047 one; the width test needs its `@device` tag and S047's helper; and the link's label differs from S050's button. Facts file used: `scratch/brief-facts-S052.md` (run on the working tree).

Staleness mode: I re-read only the brief's statements about the changed files (`meters.py`, `meters_core.py`, `meterLabels.js`, the two backend test files, `meterLabels.test.js`, `screens.spec.js`, `tickets-work.spec.js`, `e2e/support/tickets.js`) and the e2e section against S047's levels and tags. The rest of the brief is as round 1 left it.

## Findings

### BS1-01 — minor — § 1.5, § 3 (frontend): the *Register* URL now has a helper, `registerQuery`

**What changed.** S050 added `registerQuery(nodeId, meterIds = null)` to `frontend/src/utils/meterLabels.js` (and `parseRegisterQuery`, its reverse). `MetersCard.vue:119` builds its button's target with it: `:to="{ path: '/readings', query: registerQuery(node.id) }"`.

**What in the brief is now wrong.** § 1.5 and § 8.4 give the URL as a literal, `/readings?tab=register&node=<id>`. The coder would write that string a second time in `TicketMetersCard.vue`; a change to the register's query (S050 already added `meters=`) would then miss the ticket card.

**Fix.** § 3 (frontend) and § 1.5: the link's target is `{ path: '/readings', query: registerQuery(node.id) }`, as `MetersCard.vue` does. The § 8.4 test keeps asserting the resulting URL, `/readings?tab=register&node=<id>`, which is unchanged. **Recommended.** (Alternative: keep the literal; a planned duplicate, not recommended.)

### BS1-02 — minor — § 8.6: the end-of-coding e2e run names projects; S047 made that a different level

**What changed.** S047 defined the levels (`docs/steps/README.md` § Manual checks, `.claude/agents/coder.md`): targeted runs are **Normal with spec files**; the whole suite runs **at Normal once** when the coding is done, with no spec file and no `--project`; a `--project` the caller names turns the `@device` filter off and runs every test there; the Full level runs only in the release.

**What in the brief is now wrong.** § 8.6 says "the full e2e run once at the end (`--project=phone-chromium --project=desktop-chromium`)". Under S047 that command runs every test on the desktop as well, which is the Full level minus the iPhone: slower than Normal and outside the coder's rule.

**Fix.** § 8.6: "the targeted runs during coding (`tooling/run-e2e-tests.bat e2e/tickets-work.spec.js e2e/screens.spec.js`, Normal) and the whole suite at Normal once at the end (`tooling/run-e2e-tests.bat`, no spec file, no `--project`, no `--level`); never Full." **Recommended.**

### BS1-03 — minor — § 8.4: which new test carries `@device`, and the width check's helper

**What changed.** S047 § 1.3 (approved by purpose): a test gets `@device` when its title names a layout check (fits, in view, no sideways scroll, …) or its main assertion is a geometry; a logic test stays untagged and runs on `phone-chromium` only at Normal. `expectNoSidewaysScroll(page)` exists in `frontend/e2e/support/dialogs.js:49`.

**What in the brief is now wrong.** § 8.4 names no tag. Its fifth test, "on a phone (Pixel 7) the card fits the width: `scrollWidth` of the page ≤ its width", is a layout check by rule 1, so it is `@device` and runs on the desktop too at Normal; the words "(Pixel 7)" read as a phone-only test and could lead the coder to skip it elsewhere or to hand-write the geometry.

**Fix.** § 8.4: the fifth test becomes "S052: the ticket page with the *Meters* card has no sideways scroll (`expectNoSidewaysScroll`)", tagged `@device`; the other four are logic tests, untagged; none is `@smoke` (that tag is the journeys' and `screens.spec.js`'s). **Recommended.**

### BS1-04 — minor — § 1.2, § 1.5: the link reads *Register*; S050's button reads *Open register*

**What changed.** S050 settled its button's label as *Open register* (S050 § 1.4, BR1-08; `MetersCard.vue:120`), the one way into the register from an equipment page.

**What in the brief is now wrong.** § 1.2 and § 1.5 name the per-node link *Register*. The same action would have two labels on two pages, and *Register* alone is a noun (scope B: a button or link that acts starts with a verb).

**Fix.** Name the link *Open register* in § 1.2, § 1.5 and the § 8.4 test. **Recommended.** A judgement call on wording, so not a nit; the alternative is to keep *Register* and accept the two labels.

## Nits

- **BS1-05** (nit) § 9 item 3: `READING_BACKDATE_DAYS` is at `meters_core.py:280` now (S050's docstring lines moved it from 276).
- **BS1-06** (nit) § 1.3, § 3 (frontend): colour the marks with `readingBadgeClass(label)` (S050 CR1-03, `meterLabels.js`), as the register and the history do, instead of a class chosen in the card.

## Checked and found consistent

- `_last_readings(cur, node_ids)` (`meters.py:271`), `reading_out` (`:262`) and `_meters_of` (`:97`) are unchanged by S050; the `NOT EXISTS` neighbour is as § 3 describes, so the `until` rule (BR1-02) still applies as written. S050's new route and helpers (`readings_register`, `_read_meter_types`, `register_columns`, `register_rows`, `shown_meter_ids`, `parse_meter_type_ids`) group readings by minute; none picks a reading at or before a time, so `readings_at_ticket`, `mark_window` and `_mark_counts` are still new.
- `formatReading(value, meterType, { unit })` keeps its default (`unit: true`), so § 1.3's use is unchanged; `readingBadges` and `ageText` (`ticketLabels.js:106`) are unchanged.
- `test_the_meters_list_carries_the_last_reading` is still at `test_readings_api.py:258`; `test_a_moved_machine_shows_to_the_old_and_the_new_unit` at `test_tickets_api.py:375`; S050's tests were appended after both.
- The other line references hold: `local_db.py:995`, `equipment.py:150`, `:164`, `:346`, `:473`, `tickets_core.py:100`, `TicketDetailView.vue:208`, `:309`, `:315`, `tickets.py` 1418 lines.
- § 1.5: *Readings* opens to every role (`screens.spec.js` row `/readings` `who: EVERYONE`; `ReadingsView.vue:31` gives a user without `reading:log` the *Register* tab), and the register URL `?tab=register&node=<id>` is what S050 built.
- § 3: `screens.spec.js`'s ticket row is unchanged by S047 (tags only), so "no change expected" holds.
- S051 changed `EventFields.vue` and `setEventTime` (unticks *Now*) only. S052's e2e set-up goes through the API: `raiseByApi` accepts `occurred_at` (as `raiseBreakdown` in `tickets-work.spec.js:21` does) and `logByApi(machine, name, value, takenAt)` takes the reading's time, so nothing in S052 touches the time field.
- `journeys.spec.js` journey 3 uses `card(page, "Meters")` on the equipment page only; the ticket page's new *Meters* card cannot make it match two cards.
- The conftest fixtures § 8.2 names (`make_ticket`, `node`, `at_unit`, `user_with_units`, `make_meter_type`, `db_down`) are not in the diff.
