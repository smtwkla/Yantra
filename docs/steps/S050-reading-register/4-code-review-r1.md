```
Step: S050 — Meter reading register
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 25-10-2026
```

# S050 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** Three findings are `minor` and three are nits. The route, the pure core, access, the tab shell and the moved sheet match the brief. The suites are green.

## Tests run

- `YANTRA_TEST_RUN=s050cr1 tooling/run-tests.bat`: backend 3054 passed, frontend 174 passed, deps 42 passed, tooling 168 passed. ALL SUITES: PASSED.
- `npx vite build` in `frontend/`: built; only the existing chunk-size warning.
- Browser tests: not re-run (standing rule). The coder's runs are in the report (§ 6): targeted at Normal (`readings`, `screens`, `tickets-raise`, `journeys`) 83 passed and 1 skipped (S040's bottom-bar guard on desktop); the whole suite at Normal once, 200 passed and 4 skipped (device guards, each named). These are the right specs: the readings and raise screens changed, the nav changed, and journey 3 opens `/readings`. No finding of mine needs a browser run.

## Findings

### CR1-01 (minor) — the shared picker forgets the search after *Change*: a raise-screen regression

`frontend/src/components/EquipmentPicker.vue:16-19`, used at `frontend/src/views/RaiseTicketView.vue:313` and `frontend/src/views/readings/ReadingsRegister.vue:147`

- **Problem.** Before S050, `searchText` and `results` lived in `RaiseTicketView.vue`. A pick unmounted the search input but kept that state. When the user tapped *Change*, the old search text and its list of matches came back. Now the state lives in `EquipmentPicker.vue`. The picker unmounts on a pick (`v-else-if="!nodeId"` on the raise screen, `v-if="nodeId === null"` on the register), so *Change* shows an empty search. The brief says the raise screen's behaviour is unchanged (§ 1.3, § 3), and the report does not list this change.
- **Failure scenario.** An operator types "PR-0", gets five presses, and taps PR-04 by mistake. On the form he taps *Change* and must type the search again. Before S050 the five matches were still on screen and one tap fixed the mistake. On gloves and a phone keyboard, that is real friction on the most-used flow.
- **Why minor and not major.** This is a side effect of the extraction, not a design choice, and the fix is small.
- **Fix.** Keep the picker mounted and hide it with `v-show` while a node is picked, in both screens. Another way: lift `searchText` with a `v-model` on the picker. Add an assertion to the S050 *Change* e2e test, or to a raise test, that the search text is still in the field after *Change*.

### CR1-02 (minor) — a failed *Show more* shows its message at the top of the page, out of view

`frontend/src/views/readings/ReadingsRegister.vue:157-160` and `:239`

- **Problem.** If page 2 or a later page fails to load, `loadError` puts its alert above the node card. The *Show more* button at the foot of the table then hides (`!loadError`).
- **Failure scenario.** A supervisor scrolls 30 rows down on a phone and taps *Show more* while the DB is restarting (503). The button goes away and nothing else changes in view. The message "Readings could not be loaded. Try again in a minute." and *Try again* sit about two screens up. The user thinks the list has ended. This breaks the "a refusal is always in view" rule of S026, in spirit.
- **Fix.** When `rows.length > 0`, show the failure line and *Try again* in the place of *Show more*, under the table. Keep the top alert for a failure of the first page.

### CR1-03 (minor) — the badge colour helper is copied from the History dialog

`frontend/src/views/readings/ReadingsRegister.vue:141`; the same line is at `frontend/src/views/equipment/ReadingHistoryModal.vue:101`

- **Problem.** `badgeClass = (label) => (label === RESET_LABEL ? "text-bg-info" : "text-bg-warning")` is a new helper that repeats an existing one (CLAUDE-COMMON DRY).
- **Failure scenario.** A later step changes the colour of the *Reset* badge in the History dialog only. The register and the History dialog then show one reading with two colours.
- **Fix.** Export one `readingBadgeClass(label)` from `utils/meterLabels.js`, next to `readingBadges`, and use it in both files.

## Nits

- **CR1-04** (nit) `frontend/src/views/equipment/MetersCard.vue:119`: *Open register* is `btn-sm` on the equipment page, which is a floor screen (QR). It follows the card header's *Add meter*, but it is the register's main entry point from the floor. Consider the normal size, or `min-height: 44px` as the register's own rows have.
- **CR1-05** (nit) `frontend/src/views/readings/ReadingsRegister.vue:185`: `aria-controls="register-chooser"` names an element that does not exist while the panel is closed (`v-if`). Use `v-show` on the panel, or drop the attribute.
- **CR1-06** (nit) `frontend/e2e/readings.spec.js`: no test shows the § 1.7 not-found text ("This machine was not found, or you have no access to it. Find another machine.") with the picker under it. One short test that opens `/readings?tab=register&node=999999999` would cover it.

## Decisions taken (report § 4): my view

None of the ten changes approved behaviour. None needs the user beyond a mention at gate B.

1. `shown_meter_ids` in the core: right. The stale-id rule is a business rule, and it has its tests.
2. `full_path` and `expected_answer` in the answer: these are additions, not changes. The node card needs `full_path` when the user comes from a link. `expected_answer` is the shape `meter_type_of` already gives.
3. A seen-flag with `v-show`: § 1.1 lets the coder choose. A user who comes from the card never mounts the sheet (`ReadingsView.vue:62`, `canLog && seen.sheet`).
4. The register query is kept while *Sheet* shows: this is needed because a tab tap replaces the query, and it is consistent with § 1.1.
5. "Meters: 1 of 2": plain wording, scope B. Show it to KLA at gate B as the one label the brief did not name.
6. The URL helpers are in `meterLabels.js`, with tests: § 9 item 4.
7. *Show more* by the server's pages: the reasoning is correct. A reading logged between two pages would leave a rows-based button on screen that loads nothing. The e2e test covers that case.
8. A *Time* header, 9. the id `equipment-search`, 10. the picker under the 404 message: all fine.

## Manual checks (for the user)

- None on a real device (§ 8.5). The sideways-scroll test runs on `phone-webkit` only in the release's Full run.
- At gate B, if KLA wants to: open a press's *Open register* on a real phone and swipe the table sideways. This is not required, because it is covered by the `@device` test.

The impl report's `## Manual checks` carries every important check of § 8.4 as `[auto]`, each with its test, and the coder's run passed.

## Checked and found consistent

- **Access (§ 5.4).** The route is `@require_perm("equipment:read")`, so a request with no identity is refused. `load_node_for_user(..., for_update=False, key="equipment:read")` gives 404 for an unknown node and for a node outside the user's units. It checks the key at the node's site with `require_perm_at`. `equipment:read` is in `SITE_SCOPED` and is `("*",)`. The API tests cover the storekeeper (`at_unit`) and IT admin (the `admin` fixture is `it_admin`), and the 404 for an outsider and for an unknown id. The answer has no `created_by`, no note and no removed reading.
- **The nav change.** *Readings* needs `equipment:read` (`navigation.js`), as U1 and § 1.2 say. `canOpenRoute` follows it. `navigation.test.js` holds IT admin's and the storekeeper's new lists, and *Readings* follows *Tickets*. `test_rbac.py` needs no change: no new key, and no route-to-key list.
- **The pure core.** `parse_meter_type_ids` handles absent, empty and blank input (all), trims, drops duplicates in first-named order, and refuses "3,x", "3,", "0", "-1", "3.5" and non-ASCII digits. `register_columns` puts the meters in force in `effective_meters` order, then the removed-from-node types by name, with no limits. `register_rows` puts the newest minute first, words each value by its column's kind, keeps the higher id on a duplicate (with the comment), and leaves out a reading that is not a column. Every rule of § 8.1 has a test.
- **The shell.** It uses a fixed number of queries (node, `_meters_of`, read types, count, minutes, readings), none per meter or per row. The SQL is parameterised, and the f-strings put in only `%s` placeholders. The reading queries are skipped when the node has no column. Paging uses `int_arg` with `MAX_PAGE` / `MAX_PER_PAGE`, and `per_page` defaults to 30. Times go out through `rows_to_list`. There is no write, so it needs no lock or transaction. `get_db()` gives 503 when the DB is down, and a test covers it.
- **The moved sheet.** `ReadingsSheet.vue` is the S051 snapshot's `ReadingsView.vue`, byte for byte except the seven import paths (checked with `diff -w`). S051's `rounds` and `enterMore()` come with it.
- **The picker extraction.** The wording, the 20 matches, `level=all` and the debounce are unchanged. `RaiseTicketView.vue` keeps `restoreFieldKey`, raised in `resetForm()` and used as EventFields' `:key`. `useDebounced` and `PICKER_SIZE` moved with the search (but see CR1-01).
- **The tab shell.** A user without `reading:log` always gets *Register* and no tab bar, and `?tab=sheet` opens *Register* for them. The register's watch is idle while *Sheet* shows and after the route leaves `/readings`. A node change clears the screen, and a tick change keeps the table until the answer comes.
- **The register screen.** The § 1.7 empty states and messages match the brief word for word. A 403 shows the 404 text. Removed readings are absent. A row's time is never shown twice. The last tick is disabled. The URL holds `node` and `meters`. The time column is sticky, and the frame scrolls (`overflow-x: auto`). The chooser rows and *Show more* are at least 44 px high.
- **E2E.** Nine `S050:` tests assert what the user sees: headers, row times, cell text, the *High* badge, the URL after a reload, `Meters: 1 of 2`, the typed value kept, the full path, no alert on a stale id, 32 rows with no time twice, the storekeeper's nav with no tab bar, and *Change*. Only the sideways-scroll test is `@device`, with the reason (layout), and it has enough meters to overflow at 1366 px. The storekeeper test finds *Readings* in whichever nav is visible. `screens.spec.js` opens `/readings` for `EVERYONE`, the storekeeper and IT admin see *Which equipment?*, and `READING_ROLES` is gone. No dialog is opened, so `expectDialogFits` does not apply.
- **The docs pass.** `docs/Plan.MD` § 4.5 turns "Decided (S050)" into "Built (S050)", and the § 6 *Readings* line is updated. `.claude/CLAUDE.md` maps `readings` to S039/S040/S050/S051. There is no migration, so no schema doc is due. `docs/Keycloak.md` and `device-checks.md` need no change.
- **Scope and track.** Everything in § 1 is built, and nothing outside it. Track: full. There is no migration, no new key and no write.
- **Writing style.** Screen text follows scope B. The buttons start with a verb (*Open register*, *Open equipment page*, *Show more*, *Show all*, *Try again*), and the messages are the brief's. The impl report follows scope A.

## Summary for the orchestrator

- Wrote `docs/steps/S050-reading-register/4-code-review-r1.md`.
- Tests: `run-tests.bat` (s050cr1) all four suites PASSED (3054 / 174 / 42 / 168); `vite build` OK; e2e not re-run.
- Findings: 0 blocker, 0 major, 3 minor (CR1-01 picker search lost after *Change*, CR1-02 *Show more* failure out of view, CR1-03 copied `badgeClass`), 3 nits (CR1-04…06).
- No blocker or major finding is open.
