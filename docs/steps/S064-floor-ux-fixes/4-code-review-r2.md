```
Step: S064 — Floor UX fixes
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 28-10-2026
```

# S064 — Code review, round 2 (verify fix round 1)

**Verdict: no `blocker` or `major` finding is open.** Fix round 1 fixes CR1-01, CR1-02, CR1-03, CR1-04, CR1-06 and CR1-07. CR1-05 stays with KLA for gate B, as agreed. This round adds one nit (CR2-01).

I re-read these files: `frontend/src/views/masters/PeoplePanel.vue` (lines 150–310), the new test in `frontend/e2e/masters.spec.js` (lines 646–688), `frontend/e2e/support/dialogs.js`, `frontend/e2e/support/console.js`, the fix round's hunks in `api.js`, `EquipmentView.vue`, `EquipmentClassesPanel.vue`, `EquipmentCategoriesPanel.vue` and `support/nav.js`, and the person routes in `backend/masters.py` (lines 1180–1500) to check the shape of the `POST`/`PUT` response.

## Test runs

- **Unit suites** (`YANTRA_TEST_RUN=s064cr2 tooling/run-tests.bat`): backend **3323 passed**, frontend **265 passed**, tooling **185 passed**. ALL SUITES PASSED.
- **Build** (`npx vite build`, to `scratch/s064cr2-build`): built. Only the chunk-size warning, which was there before.
- **Browser, my run:** the new CR1-01 test alone (`E2E_LANES=1`, `tooling/run-e2e-tests.bat e2e/masters.spec.js --project=phone-chromium -g CR1-01`): **1 passed**. I ran it to confirm that the fix for my own finding is covered.
- **Browser, the coder's run:** targeted at Normal, `masters.spec.js`, `equipment.spec.js` and `screens.spec.js`: 101 passed, 2 skipped, 0 failed. That is the right set. `masters` covers the Team and the two Masters panels, `equipment` covers `EquipmentView.vue`, and `screens` is always added. `api.js` is a shared file, but the change only adds a `console.error` line before the same throw. The console watcher fails a test on an unexpected console error, but only a failed `fetch` reaches that line, and the earlier offline tests already allowed or caused those failures. No new whole-suite run is needed.

## Findings carried from round 1

| ID | Severity | Status |
|---|---|---|
| CR1-01 | major | Fixed (verified) |
| CR1-02 | minor | Fixed (verified) |
| CR1-03 | nit | Fixed (verified) |
| CR1-04 | nit | Fixed (verified) |
| CR1-05 | nit | Open, for KLA at gate B (not re-raised) |
| CR1-06 | nit | Fixed (verified) |
| CR1-07 | nit | Fixed (verified) |

### How each fix was verified

- **CR1-01.** `refreshEditing(person)` (`PeoplePanel.vue:249-257`) now sets `editingId`, `editingLabel` and `editingActive` from the `POST` response whenever `editingId` is `null`, whether or not `reload()` worked. `editing` takes the reloaded record, else the response. The response comes from `_fetch_person` (`masters.py:1201`), the same shape as a list item (`sites` with `editable`, `assignable_site_ids`), so `accessLines` and `saveRows` can read it. A second Save therefore sends a `PUT`. The retry re-sends the row `PUT`, which is safe: `put_person_site` adds or changes the row (`masters.py:1460-1479`). The new test aborts every non-`POST` call after the `POST`, checks *Edit person* and one `POST`, then restores the connection, saves again, and checks one `POST` and one list row. The report gives the red result: with the old code the title stayed "Add person". My run passed.
- **CR1-02.** Both texts now read "Masters › Categories" and "Masters › Classes", and these match the toolbar labels in `MastersView.vue:30-31`. No "Equip Class" or "Equip Category" is left in `frontend/src`. The report adds the two texts to the UX-25 row.
- **CR1-03.** `navItems` is gone. `navItem` stays and is still used.
- **CR1-04.** `send()` logs `console.error("fetch failed", cause)` before it throws. The comment says why.
- **CR1-06.** The comment names Bootstrap 5.3's `.form-control-sm` as the source of the values.
- **CR1-07.** Text 4 now says `SMTW-WebApp-Base.md:1272`.

### Red, then green

Only CR1-01 has a new test. The fix round gives its red result. The other fixes are texts, a comment, a log line and a removed export, so no test was due.

## New findings

No `blocker`, `major` or `minor` finding. The fix round's diff brings in no new fault. A note: the Edit path now falls back to the `PUT` response when the reload fails, where it kept the old record before. That response is at least as fresh as the old record, so the change does no harm. A retry after a failed reload can still re-send a `DELETE` that had already worked and get "Not found" on the row. That was so before this round too, it needs two failures in one save, and the person is not duplicated, so I do not raise it.

## Nits

- **CR2-01** (nit) `frontend/e2e/masters.spec.js:658`: the new CR1-01 flow test opens the Team dialog but does not call `expectDialogFits`, which the repo's S024 convention asks of every flow test. Add `await expectDialogFits(page);` after `openDialog(page)`, as the S064 test at line 704 does.

## Checked and found consistent

- The fix round changed only the files its report section lists. Its diff matches the report line by line.
- The impl report's `### Round 1` gives the run name, each finding's status, the tests run with real counts, the Docs updated line and its own `#### Feedback`. "Docs updated: none" is right: the fixes change no behaviour a doc describes, and no migration was added.
- The new test has no `@device` tag. That is right, because it is a logic test on the logic device. It allows only the two console lines that a dropped connection logs (`fetch failed`, `net::ERR_FAILED`).
- Scope B: the two new screen texts are short, use the toolbar's names, and say where to go.

## Manual browser checks still for the user

- As in round 1: the device rows 44–46 (IT Admin). These cover the phone keyboard over the Equipment and Team dialogs (**important**), gloved taps on Sign out, the pager and the document row's buttons, and a camera photo's empty title plus the iPhone HEIC note.
- KLA's decision on the desktop toolbar order (Decision 5, CR1-05) and his look at the deleted S043 operator test (Decision 9).

## Feedback

- hindrance: `step_snapshot.py diff S064 --from-round 1` crashed again with `UnicodeEncodeError` (cp1252) when its output went to a file. `PYTHONIOENCODING=utf-8` fixed it, the same as in round 1 (1 run lost; the tool should reconfigure stdout to UTF-8).
- idea: `step_snapshot.py diff` takes no path filter, so a verify round reads the impl report and the previous review inside the diff. A `-- <paths>` option, or leaving `docs/steps/` out by default with `--from-round`, would shorten it.
