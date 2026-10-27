```
Step: S064 — Floor UX fixes
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 28-10-2026
```

# S064 — Code review, round 1

**Verdict: one `major` finding is open (CR1-01).** If a row fails on Add person and the list reload fails too, the dialog stays *Add person*, so a second Save creates the person twice. Also open: one `minor` (CR1-02, "Equip Class" / "Equip Category" left in two screens) and five nits. Everything else matches the brief, and the unit suites and the build are green.

## Test runs

- **Unit suites** (`YANTRA_TEST_RUN=s064cr1 tooling/run-tests.bat`): backend **3323 passed**, frontend **265 passed**, tooling **185 passed**. ALL SUITES PASSED.
- **Build** (`npx vite build`, to `scratch/s064cr1-build`): built. Only the chunk-size warning, which was there before.
- **Browser tests:** I ran none. No finding of mine needs a run, because CR1-01 is visible in the code. I rely on the coder's runs. Its whole-suite Normal run had 257 passed, 2 failed and 12 skipped. Both failures were fixed (Decisions 7 and 9), and a targeted run of `readings`, `masters` and `screens` then gave 99 passed and 1 skipped. That is the right targeted set for those two fixes. No shared frontend file changed after the whole-suite run.

## Findings

### CR1-01 (major) — Add person: a failed row plus a failed reload leaves the dialog as *Add person*, so a retry creates a duplicate

`frontend/src/views/masters/PeoplePanel.vue:247-255` (`refreshEditing`), called from `saveRows` (`:257`) on Add.

- **Problem.** Brief § 5.6 rule 2: if a row's `PUT` fails, set `editingId`, `editing`, `editingLabel` and `editingActive` to the new person. `refreshEditing` sets them only when `reload()` finds the person in the reloaded list. `reload()` catches its own error. If the list `GET` fails, `people` keeps the old list, `editing` stays `null`, and `editingId` stays `null`.
- **Failure scenario.** An engineer on mobile data adds a technician with one site row. The `POST` succeeds, then the connection drops. The row `PUT` fails with "No connection…" (status 0), and the list `GET` in `refreshEditing` fails the same way. The dialog still reads *Add person*. When the connection is back, the engineer presses Save again. `save()` sends a second `POST` (`editingId === null`). The Team list now holds two people with the same name. People have no delete route, so the extra record can only be deactivated. A dropped connection is the floor's most likely cause of a failed row, so this case is not rare.
- **Fix.** Make the switch to Edit independent of the reload. Pass the `POST` response (`person`, which `_fetch_person` returns with `sites` and `assignable_site_ids`) into `saveRows` / `refreshEditing`. When `editingId` is `null`, set `editingId = personId` and the label and active flag from that response. Use the reloaded record for `editing` when the reload finds it, else the `POST` response. Add a test: a browser test that aborts the row `PUT` and the next `GET /api/masters/people`, then checks the title *Edit person* and that a second Save sends no `POST`. A unit test of the save sequence would also do.

### CR1-02 (minor) — UX-25: "Equip Class" and "Equip Category" are still on two screens

`frontend/src/views/masters/EquipmentClassesPanel.vue:140` and `frontend/src/views/masters/EquipmentCategoriesPanel.vue:64`.

- **Problem.** Brief § 5.6 rule 6 and § 3 (which names `EquipmentClassesPanel.vue`) say the screens that name the sections use the toolbar's terms. Two screen texts still use the old names: the class dialog's help line "Add categories in Equip Category." and the empty Categories list "…pick it for each class in Equip Class.". The impl report's UX-25 row does not list these two files.
- **Failure scenario.** An engineer opens *Classes* › Edit and reads "Add categories in Equip Category". No toolbar button carries that name now (it is *Categories*), so the engineer has to guess where to go. This breaks scope B's rule "same word for the same thing".
- **Fix.** Write "Add categories in Masters › Categories." and "…pick it for each class in Masters › Classes." (the form `ModelPropertiesModal.vue` and `PropertiesPanel.vue` already use). The code comment at `EquipmentCategoriesPanel.vue:4` may follow. List the two texts in the report.

## Nits

- **CR1-03** (nit) `frontend/e2e/support/nav.js:12`: `navItems` is exported, but no spec uses it. Remove it, or use it.
- **CR1-04** (nit) `frontend/src/api.js:21`: every `TypeError` from `fetch` becomes "No connection…", also a coding error such as a bad header value. The cause is attached but never logged. Add `console.error("fetch failed", cause)` before the throw, so a real bug is still visible in the console.
- **CR1-05** (nit) Impl report Decision 5 and `EquipmentView.vue:377-381`: the desktop order change was not forced. The children of a `display: contents` block take their own `order-md-*` classes. With `order-md-2` on *Filter by property* and *Show scrapped*, and print and *Add equipment* moved after them, the search would again come before *Filter by property*. KLA can keep the new order: in that case reword the decision ("chosen", not "forced").
- **CR1-06** (nit) `frontend/src/views/EquipmentView.vue:542-549`: the `md`-up `.search-box` rule copies Bootstrap's `form-control-sm` values by hand (height, padding, font size, radius). Use a class binding, or a comment that names the Bootstrap version the values come from.
- **CR1-07** (nit) Impl report § For smtw-common, text 4: the sentence it replaces is at `SMTW-WebApp-Base.md:1272`, not 1273 (the brief had the same number). The exact quoted sentence is right, so only the line number needs a fix.

## The points the orchestrator named

- **Decision 6 (App.vue top margin): correct.** `.app-content` has a 0.5rem top padding (`App.vue:109`). The old `-1.5rem` top margin pulled the phone top bar 1rem above the scroll area. The new `-0.5rem` cancels the padding exactly. The fault is older than S064, and UX-02 needs the full button on screen. Keep it.
- **Decision 9 (one S043 test deleted, two operator tests rewritten): correct.** `config_rbac.py:96,134,140,148` give `masters:edit` to IT admin, and `equipment:edit`, `people:edit` and `failure_codes:edit` to engineer and IT admin (manager inherits). So every role that can open Masters holds `equipment:edit`, and the read-only Properties view cannot be reached. The report lists the now-dead read-only code under § 5, so the queued *Tidy-up* can take it.
- **Decision 5 (desktop toolbar order): reported, but not forced.** See CR1-05.
- **Decision 7 (status 0 as unavailable in `meterLabels`): correct and needed.** Without it, the S040 sheet would show the new no-connection text instead of its approved "Not saved. Try again in a minute." `meterLabels.test.js` covers status 0.
- **Permission-scoped field (§ 5.6.1, § 5.9): correct.** `list_people` adds `assignable_site_ids` only when `viewer.editor` (`has_perm("people:edit")`). `grantable_site_ids()` is split out with no person and no `_is_own`. The per-person field is that list minus the person's rows, and empty for one's own record. The four § 8.1 cases are tested: IT admin gets every active site and no inactive one, an engineer only their assigning site, an editor with no grant `[]`, and a floor role gets no key. No route check and no key changed.
- **Add-person flow:** with a login, the rows go in the `POST`, as the server requires. Without a login, the rows are saved one by one after the `POST`. The § 8.4.22 test checks a refusal from the real server (a unit deactivated through the API). A retry after the switch to Edit sends no `username` (`toBody` drops it when it equals the stored `null`), so it does not take the login path. The one open gap is CR1-01.
- **FormModal provide/inject:** `provide(FORM_DIRTY, computed(() => props.dirty))` uses a Symbol key (`utils/formDirty.js`). `ActiveToggle` injects it with a clean default. A slot child's instance parent is FormModal, so the inject works, and the S064 Deactivate test shows it.
- **api.js:** `send()` wraps all three helpers, an `AbortError` passes through, and a non-JSON 5xx becomes `NOT_ANSWERING_TEXT`. `getToken()` catches a failed refresh itself, so `authHeaders()` cannot leak the browser's text. `api.test.js` covers the five § 8.2 cases plus a JSON 503.
- **Message rewrites against the access log:** both callers of `FORBIDDEN_TEXT` call `_log_denied` first. `test_rbac.py` now checks `g.access_detail == "settings:edit"`. A denied network request still logs the gate's text (`NETWORK_DENIED_MESSAGE`). The access log shows a non-key text without the "Needed: " prefix (`AccessLog.vue`, the regex `^[a-z_]+:[a-z_]+$`). No backend or frontend code compares the old texts: I grepped "Forbidden", "Unauthorized", "Database unavailable", "Code collision", "Unknown unit" and "Let in". The only remaining hit is a mocked 503 body in `tickets-work.spec.js:663`, which is test data.
- **Phone layout:** dialogs have `modal-fullscreen-sm-down` together with `modal-dialog-scrollable`, so the footer stays fixed and the body scrolls. Floor buttons use `.tap-target` (44 px): Sign out, pager, Download, "⋯" and *Filters (n)*. The list cards wrap and truncate. `expectNoSidewaysScroll` runs in the phone list test.
- **Scope:** nothing beyond the brief was added. `isHeicFile`, `formDirty.js`, `support/nav.js` and `support/equipmentList.js` serve the items, and the report names each one. The `RaiseTicketView.vue` iPhone note and the `.touch-target` copies are left as they were, and § 5 of the report says so.
- **For smtw-common texts:** eight texts, one per § 5.10 point, each under the right heading (`### Form / Modal Pattern` 1342, `### Table / List Pattern` 1333, `### Topbar Design Principles` 1269, `### Navigation Hierarchy` 1215, `### Design Tone` 1370, `## Frontend API Helper Pattern` 1382). Text 4 quotes the base's sentence exactly; only the line number is off (CR1-07).

## Checked and found consistent

- Every UX-01…UX-27 item is built as § 5 says. I checked the § 5.7 rows one by one against the diff (rows 1–3, 6–18, 20). Row 20 rightly leaves `_id_parser` alone, because it never says "is required" (`equipment_core.py:71-77`). Decision 15 is right.
- `NO_UNITS_TEXT` is used on the four screens, and the old text is gone from `frontend/src`.
- UX-07: *Print label* is on the bare node key and stays disabled while loading. The phone order uses one flex column with `order-*` reset at `md`. `MetersCard` has one root, so its order class applies.
- UX-19: `loadStatus` and `loadTasks` run only with `settings:edit`. `RemovedDocuments` renders in one of two places, never both.
- UX-04 and UX-17: the confirms are inline. Typing closes them. *Yes, save* is red for Network and blue for Labels. The sample link joins as `labels_core.label_url` does.
- Security: no route's key changed, no actor comes from the client, and no new SQL was added. `_check_grantable` still takes `table` from code only. Its texts now show the unit's code or the trade's name, never the id.
- Pure core and thin shell: the text helpers (`_choose_text`, `_missing_text`) sit in `masters_core.py`. The frontend holds no business rule. `filterCount`, `accessLines` and `isCameraName` are display logic.
- Browser tests: each *Automated* check of § 8.4 has a test that asserts what the user sees (the footer text, geometry, URL, titles, the rows). The `@device` tags follow the rule: layout tests, and tests skipped below `md` that run only on desktop. Logic tests are untagged. Flow tests call `expectDialogFits`. The § 8.3 adaptations are listed line by line in the report.
- Docs pass: `device-checks.md` rows 44–46 match § 8.5. The `INDEX.md` queue row marks [18] done. The `.claude/CLAUDE.md` spec-to-step map adds S064 and the two new specs. No migration, so no schema doc is due. The `docs/Plan.MD` § 3 paragraph matches the gate-A decisions and the build.
- Impl report `## Manual checks`: every **important** check of § 8.4 is `[auto]` with its test. § 8.5.1 is an unticked box. The other two device checks are plain items.
- UI text, scope B: the new texts are short, plain and say what to do. Buttons start with a verb, except the *Yes, save* / *No* pairs, which the brief prescribed. Only CR1-02 breaks "one word for one thing".

## Manual browser checks still for the user

- The device rows 44–46 (IT Admin): the phone keyboard over the Equipment and Team dialogs (**important**), gloved taps on Sign out, the pager and the document row's buttons, and a camera photo's empty title plus the iPhone HEIC note.
- KLA's look at the desktop toolbar order (Decision 5, CR1-05) and the deleted S043 operator test (Decision 9).

## Feedback

- hindrance: `step_snapshot.py diff S064` crashed with `UnicodeEncodeError` (cp1252, "→" in a brief) when its output went to a file; `PYTHONIOENCODING=utf-8` fixed it (1 run lost).
- idea: `step_snapshot.py diff` could take `--exclude docs/steps/` (or code folders only), since 2 000 of its 5 900 lines were this step's own brief, audit and reviews.
