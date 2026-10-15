```
Step: S003 — Equipment register screens
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 15-10-2026
```

# S003 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** There is 1 `nit` (CR2-01). All seven
round-1 findings the user chose (CR1-01, 02, 04, 05, 06, 07, 09) are fixed. CR1-07 is fixed
except for one leftover detail, which is CR2-01. CR1-03 and CR1-08 stay unfixed by the user's
choice (brief, Gate B).

## Scope of this review

- **Which round-1 answers I checked.** The fix round in `3-impl-report.md` ("Fix rounds" → "Round 1"),
  against `4-code-review-r1.md` and the brief's Gate B.
- **S002 is unchanged.** I diffed `backend/` against the pre-S003 snapshot
  (`scratchpad/s002_baseline/backend`) with `diff -r --strip-trailing-cr`.
  - Only `backend/equipment.py` and `backend/tests/test_equipment_api.py` differ. These are the same hunks as in round 1:
    - `GET /my-units`;
    - `out["root_criticality"]` in `_detail`;
    - the `_accessible_unit_ids` section comment;
    - `TestMyUnits` and `TestRootCriticality`.
  - No other S002 line changed.
  - `pyproject.toml` and `uv.lock` are not in the snapshot, but git shows both unchanged from HEAD.
- **Frontend.** The set of changed and new files matches round 1. The only new file is
  `src/composables/useDebounced.js`. By modification time, the fix round touched only these files:
  - `FormModal.vue`, `router/index.js`;
  - `EquipmentView.vue`, `EquipmentDetailView.vue`;
  - `EquipmentFormModal.vue`, `EquipmentMoveModal.vue`;
  - `useDebounced.js`.

  This matches the report. The masters panels and S002's frontend baseline did not change. The brief's
  only change is the Gate B record.

## Test run (run by the reviewer)

- `tooling/run-tests.bat`: green.
  - Backend: **462 passed**.
  - Frontend (vitest): **23 passed** in 4 files.

  Both counts are unchanged from round 1. The fix round added no tests, which is consistent: the
  fixes are view code, and CR1-08, the URL-rule tests, was declined.
- `npx vite build` in `frontend/`: clean, with no warnings. It builds 133 modules: round 1's 132 plus `useDebounced.js`.

## Verification of round-1 fixes

| Finding | Status | What I checked |
|---|---|---|
| CR1-01 | **Fixed** | See below. |
| CR1-02 | **Fixed** | `EquipmentFormModal.vue:23`: `CREATE_STATUSES = Object.entries(STATUS_LABELS).filter(([value]) => value !== "scrapped")`. The options keep the same order (In service, Standby, Out of use). `status: "in_service"` is still the default. No status text is typed anywhere else in the frontend. |
| CR1-03 | Not fixed, by the user's choice | — |
| CR1-04 | **Fixed** | See below. |
| CR1-05 | **Fixed** | See below. |
| CR1-06 | **Fixed** | See below. |
| CR1-07 | **Fixed in substance**; leftover is CR2-01 | See below. |
| CR1-08 | Not fixed, by the user's choice | — |
| CR1-09 | **Fixed** | `FormModal.vue:3` now says "shared by the masters panels and the equipment dialogs". |

### CR1-01 — the move dialog's parent search

`EquipmentMoveModal.vue:56-87`, `:176-178`

- **Two searches.**
  - A component-unit searches `["equipment"]`. A component searches
    `["equipment", "component_unit"]`, each with `per_page=20`.
  - S002's list accepts `level=component_unit` (`_enum_arg("level", (*LEVELS, "all"))`) and hides
    scrapped nodes by default.
  - Components are never requested, so they can no longer use up the limit. The old client-side
    component filter is gone.
  - The two levels can't overlap, so the merge (`flatMap`) has no duplicates. Equipment is listed first,
    then component-units.
- **The "more matches" hint.** It shows when `pages.some((p) => p.total > p.items.length)`. This
  compares with the rows the API returned *before* the dialog filters out the node itself and its
  current parent, which is right: those two rows are hidden on purpose, not cut off.
  - With `total > 20`, a page has 20 rows, and the filter removes at most 2. So the dialog can't show
    "No matching parent." while the hint is on.
  - The hint is hidden while a search is running. It is reset on an empty search, on an error and when
    the dialog opens.
- **Error handling.**
  - If either request fails, `Promise.all` rejects. The dialog then shows the error message and clears
    both the list and the hint. The other request's rows are dropped rather than shown as an
    incomplete list, which is the honest choice.
  - `Promise.all` handles a second rejection, so it is not an unhandled rejection.
  - A late response is dropped by `searchSeq`, both for success and for error, and `searching` is
    cleared only by the latest search.
  - A 503 (DB down) arrives as an error message under the search box.
- **Departure from the brief.** Brief § 4.4 says `level=all` for a component. The two-search
  approach was round 1's suggested fix, the user chose it at Gate B, and the report's fix round
  records it. It is not an unreported departure.
  - The report's original decision 3 still says "at most 20 matches". With two searches it is now 20 per
    search. The fix round says so, so I did not raise a finding.

### CR1-04 — "Loading…" while fetching

- **List.** `EquipmentView.vue:199` shows a small "Loading…" above the table while `loading && page`. The
  first load still uses the existing `loading && !page` branch. The old rows stay visible, so the
  table doesn't flicker, and a click on an old row only opens that row.
- **Equipment page.** `EquipmentDetailView.vue:97` shows "Loading…" beside the header.
  - `canEdit` (`:36`) now includes `!loading.value`, so Edit, Add part, Move and Change status
    are hidden until the new node has arrived.
  - Round 1's failure scenario is closed: the status dialog can no longer open for the node that is
    still on screen.
  - **Side effect.** The button row also disappears for a moment during the reload after every
    save. This makes a small vertical jump. It is cosmetic; see manual check 5.

### CR1-05 — non-numeric ids

`router/index.js:18`: `path: "/equipment/:id(\\d+)"`, which is the regex `\d+`, anchored by the router.

**What `/equipment/my-units` shows now.** No route matches, so the following happens:
- `beforeEach` gets `to.name === undefined`. `canOpenRoute(undefined, …)` returns true ("routes outside the nav are allowed"), so there is no redirect.
- `App.vue`'s re-check does the same.
- `<router-view>` renders nothing. The user sees the normal layout (top bar and sidebar, with Equipment highlighted because `isActivePath` uses a prefix match) and an **empty content area**.
- Vue Router logs a "No match found" warning in the console.
- No API call is made and nothing throws.

The same happens for `/equipment/12abc` and `/equipment/`. A numeric id that doesn't exist, or
is at another unit, still gets the not-found message from the API's 404.

**This is acceptable.** Round 1's finding was a crash: a TypeError, and `my-units` data rendered as a
node. That is gone. A blank content area for a malformed URL is the app's general behaviour today:
`/anything` behaves the same, because the app has no catch-all route. Adding a catch-all route that
redirects to the landing page, or shows a "page not found", would be an app-wide change outside
S003's brief. If the user wants it, it should be raised as a separate small change, not added here.

### CR1-06 — leaving a bookmarked `status=scrapped`

`EquipmentView.vue:91-96`: `chooseStatus(value)` adds `scrapped: "1"` to the same `update()` when the
current query has `status=scrapped` and no `scrapped=1`. I traced these cases:
- **`/equipment?status=scrapped`, then "All statuses".** The URL becomes `?scrapped=1`. The box stays
  ticked, Scrapped stays in the status filter, and the scrapped rows stay listed. This is the round-1
  failure scenario, now fixed.
- **`status=scrapped`, then "Standby".** The URL becomes `?status=standby&scrapped=1`. The box stays
  ticked.
- **`status=scrapped&scrapped=1`, then any status.** No extra change is needed or made.
- **Unticking the box while on `status=scrapped`.** `toggleScrapped(false)` still clears both values,
  as BR2-01 requires.
- **Changing another filter (site, class, …) while on a bookmarked `status=scrapped`.** The status
  stays, so the box stays ticked.

The change goes through `update()`, so the page still resets to 1 and the defaults still stay out
of the URL. It is one `router.replace`, so Back steps over it as before.

### CR1-07 — the debounce

`composables/useDebounced.js` holds the logic once:
- the timer;
- `schedule()`, which cancels and restarts it;
- `cancel()`;
- `onBeforeUnmount(cancel)`.

Both callers use it: `EquipmentView.vue:120-121` and `EquipmentMoveModal.vue:89-90`. Neither file
has a `setTimeout`, a `clearTimeout` or its own unmount clean-up any more (I grepped `src/`).
`watch(search, scheduleSearch)` passes the watcher's arguments to `schedule()`, which ignores them.
`clearTimeout(null)` on the first call is harmless.

**Is the duplication gone?** The copied *mechanism* was most of what the finding was about: the
timer handling and the unmount clean-up. That copy is gone.

**What is left.** `SEARCH_DELAY_MS = 300` is still defined twice (`EquipmentView.vue:22`,
`EquipmentMoveModal.vue:18`). This is one UX rule ("a search waits 300 ms after the last keystroke",
brief § 4.1) written in two places. The next search box would make a third copy. It is small, and
CR2-01 records it.

## Findings

### CR2-01 — nit — the 300 ms search delay is still defined in two files

`frontend/src/views/EquipmentView.vue:22`, `frontend/src/views/equipment/EquipmentMoveModal.vue:18`

**Problem.** Round 1 moved the debounce mechanism into `useDebounced`, but each caller still declares
`const SEARCH_DELAY_MS = 300` and passes it in. The delay is one rule for every search box.

**Failure scenario.** Someone tunes the list search to 400 ms because it fires too often on a slow
phone. The move dialog keeps 300 ms, and the two search boxes now feel different. The planned phase-3
parts picker would copy whichever value it finds first.

**Suggested fix.** Give the composable the shared value, for example
`export const SEARCH_DELAY_MS = 300;` in `useDebounced.js`, and
`useDebounced(callback, delayMs = SEARCH_DELAY_MS)`. Then drop both local constants and the second
argument at the two call sites. Alternatively, leave it and record the choice.

## Checked and found consistent

- **The rest of the fix round touched nothing else.**
  - `useFormModal.js`, `EquipmentStatusModal.vue`, `PartsTree.vue`, `EquipmentHistory.vue`, the
    stores and the label helpers are unchanged since round 1, judging by their modification times.
  - In `EquipmentFormModal.vue`, the only change is the `CREATE_STATUSES` line. The create-part
    default level stays *Component-unit*, as the user decided at Gate B.
- **Backend.** Only S003's allowed additions differ from the S002 baseline (see Scope). Round 1's
  checks still hold:
  - `GET /my-units` is gated by `equipment:read`;
  - the actor comes from the session;
  - the SQL is parameterised;
  - the DB access goes through `get_db()`, so a dead connection is handled and an unreachable DB gives
    a 503.
- **Move dialog, other paths.**
  - The search is still empty until text is typed.
  - The dialog resets the search, the list, the hint, the error and the chosen parent each time
    it opens.
  - Save stays disabled with "Choose a new parent" until a parent is picked.
  - The API's 400, 403 and 409 refusals still show under the search box (`fieldError("parent_id")`).
  - **A response from the previous opening can show briefly.** If a search was still running when the
    dialog closed, its response can arrive within the 300 ms after the dialog reopens. It then shows
    until the debounced empty search clears it. This lasts at most 300 ms, and any pick is still
    checked by the server. Not worth a finding.
- **Equipment page.** It still loads with `watch(() => route.params.id, load, { immediate: true })`.
  - The 404 and the other errors are handled as before.
  - A non-numeric id no longer reaches `load()` at all, because no route matches it.
- **Engineering rules.**
  - No exception is swallowed: both `catch` blocks in the move search show the message.
  - No deprecated APIs.
  - The new comments explain *why*:
    - the separate searches per level;
    - why the action buttons are hidden while loading;
    - the bookmarked `status=scrapped`;
    - the limit per search.
  - No migrations.

## Manual browser checks for the user (final list)

The coder has still not driven the screens in a browser, so all of these are open.

1. **As engineer** with access to `SMTW.FWMILL` only:
   - Add `VBM001`. The unit picker offers only `SMTW.FWMILL`, preselected with its site. The status
     choices are In service, Standby and Out of use.
   - Add a drive `DRV001` under it, a motor under the drive, and a motor directly under `VBM001`.
   - Edit the drive's criticality to A, then back to "Inherit (X)", where X is `VBM001`'s grade.
   - **Move (CR1-01):** move the motor from `VBM001` to the drive.
     - The search finds the drive even when many components share the word you type.
     - Equipment is listed before component-units.
     - When there are more than 20 hits at a level, the "More matches — type more…" line appears.
   - Scrap the motor:
     - Save is greyed with "Confirm with Yes";
     - No returns to the old status;
     - Yes scraps it;
     - the page shows the read-only banner.
   - Try to scrap the drive while it has a live part. The refusal shows under the status select.
   - The history shows each step in plain words with DD-MM-YYYY HH:mm dates.
2. **As IT admin:** move `VBM001` to another unit. As the engineer, the list no longer shows it, and
   its URL gives "Equipment not found, or not at your units".
3. **As operator:** the list and pages are visible, with no Add, Edit, Move or Status buttons.
4. **List:**
   - each filter;
   - a search by a motor's code, where the level switches to *All levels*;
   - paging;
   - open a row, then Back returns to the same filtered page in one step;
   - a middle-click on a code opens a new tab;
   - "Show scrapped" together with the Scrapped status;
   - **(CR1-06)** open `/equipment?status=scrapped` and switch the status to "All statuses". "Show
     scrapped" stays ticked, the scrapped rows stay listed, and the URL now has `scrapped=1`;
   - a site change clears a unit outside it;
   - an old bookmark with `page=99` shows "No equipment on this page" with Prev only.
5. **Loading (CR1-04):** throttle the network in DevTools ("Slow 3G").
   - On the list, change a filter: "Loading…" appears above the old rows.
   - On an equipment page, click a part. "Loading…" appears beside the header, and the action
     buttons are hidden until the part's page arrives.
   - After a save, the brief jump as the button row hides and returns is acceptable to you.
6. **Bad URL (CR1-05):** open `/equipment/my-units`.
   - You get the normal layout with an empty content area: no crash, and no "not-found" alert.
   - `/equipment/999999` gives the not-found message.
   - Decide whether you want an app-wide "page not found" route later. That would be a separate
     change.
7. **Sidebar and landing:** Equipment stays highlighted on `/equipment/5`, and `/` lands on Equipment.
8. **Masters regression** (`useMasterForm` was refactored in this step): create, edit, deactivate
   and reactivate a site, a unit and a class. Refusals show beside the field.
9. **Phone width:** the list table scrolls sideways, and the equipment page stacks Details, Parts and
   History.
10. **DB down:** stop the dev DB.
    - The list and an equipment page show the error with Retry. Start the DB again, and Retry works.
    - In the move dialog, a search while the DB is down shows the error under the box.
