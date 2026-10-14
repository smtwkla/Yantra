```
Step: S003 — Equipment register screens
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 15-10-2026
```

# S003 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** There are 2 `minor` and 7 `nit` findings.

## Scope of this review

S002 is still uncommitted in the working tree, which the user decided at Gate A (15-10-2026). I isolated S003's change by diffing the current tree against
the snapshot taken just before S003 coding began (`scratchpad/s002_baseline/`), with
`diff --strip-trailing-cr` because the working files use CRLF line endings:

- **Backend.** Only `backend/equipment.py` and `backend/tests/test_equipment_api.py` differ. The
  `equipment.py` hunk contains only what the brief allows (§ 3):
  - `GET /my-units`;
  - `root_criticality` in `_detail` (one line);
  - the `_accessible_unit_ids` section comment, which now names `/my-units` (BR2-06).

  No other S002 code changed.
- **Frontend.** Six files were modified: `FormModal.vue`, `AppSidebar.vue`, `AppBottomNav.vue`,
  `router/index.js`, `stores/navigation.js` and `views/masters/useMasterForm.js`. There is also
  `tests/navigation.test.js`, and the new files listed in the report. All are in the brief's § 3.
  The three masters panels (`SitesPanel`, `UnitsPanel`, `EquipmentClassesPanel`) are unchanged.

## Test run (run by the reviewer)

- `tooling/run-tests.bat`: green.
  - Backend: **462 passed**.
  - Frontend (vitest): **23 passed** in 4 files.
- `npx vite build` in `frontend/`: clean. 132 modules, no warnings.
- **Test counts.** The S002 baseline had 448 backend tests. S003 adds **14**:
  - `TestMyUnits`: 1 + 1 + 3 (parametrised) + 1 + 6 (parametrised);
  - `TestRootCriticality`: 2.

  That makes 448 + 14 = 462. The report's "436 before, +26 new" is wrong (CR1-03). The total of 462
  is right. Frontend: 15 before, 23 now (+7 in `equipmentLabels.test.js`, +1 `isActivePath` test).

## Findings

### CR1-01 — minor — the move dialog's parent search can silently hide valid parents

`frontend/src/views/equipment/EquipmentMoveModal.vue:18`, `:66-72`

**Problem.** For a component, the dialog asks the API for
`level=all&per_page=20`. It then drops components, the node itself and its current parent on the
client. Components can take up most or all of the 20 rows. The dialog never says the list was
cut short: `page.total` is ignored.

**Failure scenario.** A technician moves a motor and searches "drive". The register has ~25
components named "… drive …" (drive motors, drive couplings), and they sort ahead of the
component-unit `DRV002`. All 20 returned rows are components and are filtered out. The dialog then shows
"No matching parent", although `DRV002` exists and is a valid target. The same can happen with
fewer hits. If 15 of the 20 rows are components, only 5 parents show, with no hint that there are more.

**Suggested fix.** Either of these, or both:
- For a component, run two searches, `level=equipment` and `level=component_unit`, so
  components never use up the limit. Merge the results.
- When `page.total` is more than what was returned, show "More matches — type more of the code or
  name".

The 20-row limit is reported as decision 3. It is fine as a size, but the list must not end
silently.

### CR1-02 — minor — the create dialog repeats the status labels (§ 5.4 "one place")

`frontend/src/views/equipment/EquipmentFormModal.vue:22`

**Problem.**
`CREATE_STATUSES = [["in_service", "In service"], ["standby", "Standby"], ["out_of_use", "Out of use"]]`
retypes the label texts. `utils/equipmentLabels.js` already owns them as `STATUS_LABELS`. The
brief's § 5.4 and § 6 put the labels in one place, "so every screen says the same". The status dialog and the
list filter do use `STATUS_LABELS`.

**Failure scenario.** Someone renames "Out of use" to "Laid up" in `STATUS_LABELS`. The badge, list
filter, status dialog and history all change, but the create dialog still offers "Out of use".

**Suggested fix.** Derive the list:
`Object.entries(STATUS_LABELS).filter(([value]) => value !== "scrapped")`. This is the same shape
`EquipmentView.vue:72-74` already uses.

### CR1-03 — nit — the impl report's backend test counts are wrong

`docs/steps/S003-equipment-screens/3-impl-report.md:14-15`, `:57`

**Problem.** The report says "462 backend tests (436 before, +26 new)" and "26 new tests in total".
The S002 baseline had 448 tests and S003 adds 14 (see Test run above). The total of 462 is right.

**Failure scenario.** A later reader uses the report to check coverage and looks for 12 tests that
don't exist.

**Suggested fix.** Correct both lines to "448 before, +14 new".

### CR1-04 — nit — "Loading…" shows only on the first load, and the old data stays clickable meanwhile

`frontend/src/views/EquipmentView.vue:200`, `frontend/src/views/EquipmentDetailView.vue:73`

**Problem.** Both pages show "Loading…" only while there is nothing to display yet
(`loading && !page` / `loading && !node`).
- On a filter change, the old rows stay up with no sign that a fetch is running.
- On the equipment page, following a parts or breadcrumb link keeps node A on screen until node B
  arrives. During that time, A's Edit, Move and Status buttons are live.

The brief (§ 4.1, BR1-09) asks for "Loading…" while fetching.

**Failure scenario.** On a slow link, a user clicks part `MOT017` on `DRV002`'s page. They then
click "Change status" before the page swaps, and the dialog opens for `DRV002`.

**Suggested fix.**
- Show a small "Loading…" or spinner beside the header while `loading` is true, keeping the
  current content to avoid flicker.
- On the equipment page, either hide the action buttons while `loading`, or clear `node` when
  `route.params.id` changes.

### CR1-05 — nit — `/equipment/my-units` as a page URL crashes the equipment page

`frontend/src/router/index.js:18`, `frontend/src/views/EquipmentDetailView.vue:36`

**Problem.** The route `/equipment/:id` accepts any segment. For `/equipment/my-units`, the page calls
`GET /api/equipment/my-units`, which returns 200 with `{all_units, unit_ids}`. The page then renders
that as a node, and `node.unit.split(".")` throws.

**Failure scenario.** Someone types or pastes that URL. They get a blank page and a console
`TypeError` instead of the not-found message.

**Suggested fix.** `path: "/equipment/:id(\\d+)"`. A non-numeric id then matches no route, so it no
longer reaches the API as a node id.

### CR1-06 — nit — a bookmarked `status=scrapped` doesn't keep "Show scrapped" ticked

`frontend/src/views/EquipmentView.vue:47`

**Problem.** `showScrapped` is computed from `scrapped=1 || status=scrapped`. A bookmark with only
`status=scrapped` ticks the box, as the brief asks (BR2-01). But changing the status filter to anything
else then unticks the box by itself, and the Scrapped option disappears. The user didn't untick it.

**Failure scenario.** A user opens a colleague's link `/equipment?status=scrapped` and switches the
status to "All statuses" to compare. The scrapped rows vanish, although "Show scrapped" was showing
as ticked a moment before.

**Suggested fix.** When the user changes the status away from `scrapped` while `scrapped` is not
in the query, add `scrapped: "1"` to the same `update()`. Alternatively, normalise the query once on
load with `router.replace`.

### CR1-07 — nit — the 300 ms debounce is written twice

`frontend/src/views/EquipmentView.vue:21`, `:114-117`, `:122`;
`frontend/src/views/equipment/EquipmentMoveModal.vue:17`, `:82-86`

**Problem.** Two copies of `SEARCH_DELAY_MS = 300` and the same `setTimeout`/`clearTimeout` and
unmount-cleanup pattern. Each copy is small, but it is the kind of repetition CLAUDE-COMMON's DRY rule
targets. The next search box (the parts picker in phase 3) would make three.

**Suggested fix.** Add a tiny `composables/useDebounced.js` (a ref plus a delayed callback with
cleanup). Alternatively, leave it and record that it was a deliberate choice.

### CR1-08 — nit — the list's URL-query rules have no unit tests

`frontend/src/views/EquipmentView.vue:52-61` (`update`), `:104-112` (`applySearch`), `:93-97`

**Problem.** The rules in § 4.1 are among the most rule-dense parts of the step:
- defaults are dropped;
- a filter change resets the page;
- the level switches only on empty → non-empty while at *Equipment*;
- unticking "Show scrapped" clears a Scrapped status;
- changing the site clears a unit outside it.

They live inside the view, so only the build exercises them. The brief's test list didn't
require them, so this is not a gap against the brief.

**Failure scenario.** A later change to `update()` makes `level=equipment` appear in the URL, or
stops resetting the page. Nothing fails until a user notices.

**Suggested fix.** Move the query computation into pure functions in a small module, for example
`nextQuery(query, changes)` and `searchChanges(query, text)`, and test them in vitest. The view
keeps only the `router.replace`.

### CR1-09 — nit — `FormModal`'s doc comment is out of date

`frontend/src/components/FormModal.vue:3`

**Problem.** The comment says "shared by the masters panels". It now also serves the three equipment
dialogs, and it has the new `saveDisabledReason` prop.

**Suggested fix.** Change it to "shared by the masters panels and the equipment dialogs".

## The coder's choices not in the brief

All of them are listed in the report's "Decisions taken", so none is an unreported departure.

| # | Choice | Judgement |
|---|---|---|
| 1 | `useFormModal` takes an optional `toBody(form)` and exposes `send(request)` | **Sound.** `toBody` keeps the form holding plain input values and puts the § 5.3 wire rules (empty text → `null`, the year as a number, Inherit → `null`) in one function per dialog. `send` lets the masters' `changeActive` reuse the saving/error/close handling instead of repeating the try/catch (DRY). The default `toBody` is the identity, so the masters behave exactly as before. |
| 2 | `isActivePath` in `navigation.js` | **Sound.** One prefix rule for the sidebar and the bottom nav. It is tested, including the `/equipmentx` case. |
| 3 | Move dialog: Save disabled ("Choose a unit" / "Choose a new parent") until a target is picked | **Sound.** It uses the brief's own `saveDisabledReason`, and it avoids a pointless PUT with `parent_id: null` (a 400) or a no-op. The 20-row limit is fine as a size (but see CR1-01). |
| 4 | `PartsTree` recursive, with a `nested` prop | **Sound.** The depth is bounded by the API (two levels), and the row markup isn't duplicated. |
| 5 | The edit dialog shows the parent's code only, or the unit for equipment | Acceptable. The brief says "shown, read-only" without fixing the text. |
| 6 | The create-part dialog defaults the level to *Component-unit* under equipment | Acceptable. The brief is silent. Motors directly under equipment are also common, so the **user** may prefer *Component*. It is one word in `blank()`. |
| 7 | No "Equipment" list link in the breadcrumb | Acceptable. It matches the § 4.2 sketch. Browser Back, the sidebar and the 404 link return to the list. |
| 8 | A dialog opens even when the masters or `my-units` fail, showing the error at the top | **Sound.** The user sees why the pickers are empty instead of getting no reaction. |
| 9 | Extra backend test: an inactive unit is left out of `my-units` | **Sound.** It pins down BR1-03's "active units only". |
| 10 | List filters use `v-model` through computed get/set | **Sound.** `vModelSelect` re-applies the value when the options render later (the masters load), whereas a one-time `:value` would show a blank select for a bookmarked filter. The getters return query strings and the options carry numbers. That still selects correctly, because Vue compares select values loosely (`String(a) === String(b)`). Vue Router normalises the numbers written back into strings. |

## Checked and found consistent

- **Backend (`equipment.py`).**
  - `GET /my-units` is gated by `equipment:read`.
  - The actor comes from the session (`actor()` inside `_accessible_unit_ids`), never from the client.
  - The SQL is parameterised.
  - The DB access goes through `get_db()`, so a dead connection is retried and an unreachable DB
    gives a 503 (`DBUnavailable`).
  - `all_units` is true exactly when the helper returns `None`, which covers the
    `read_all_units` holders and admin.
  - `unit_ids` is sorted, which makes the test deterministic.
  - `/my-units` doesn't clash with `/<int:node_id>`.
  - `root_criticality` comes from the node row, so inheritance stays a server rule (§ 5.8).
- **Backend tests.** They cover every item in brief § 8:
  - two units;
  - manager, IT admin and admin get all units;
  - no rows gives an empty list;
  - all six roles get 200;
  - B at every depth, and equipment returns its own grade.
- **Permissions in the UI.**
  - The edit buttons and "Add equipment" are shown only with `equipment:edit`, and are hidden on a
    scrapped node.
  - `read_all_units` is unused in the frontend (§ 5.2).
  - The detail route is outside the nav and is gated by the API's 404.
- **Routing and navigation.**
  - `/` redirects through `landingPath(...) ?? "/equipment"`.
  - Equipment is the first nav item, with the `fa-gears` icon.
  - The prefix-match active state is used in both nav bars.
  - `navigation.test.js` role lists equal `test_rbac.py`'s matrix (operator, engineer, manager,
    IT admin).
- **List (§ 4.1).**
  - The route is the single source of truth, and controls write it with `router.replace`.
  - Defaults are left out of the URL, and a filter or search change resets the page.
  - The search waits 300 ms on the trimmed text. The level switches only on empty → non-empty
    at *Equipment* and never switches back.
  - Scrapped appears in the status filter only with "Show scrapped". Unticking clears a Scrapped
    status, and a `status=scrapped` URL ticks the box.
  - A site change clears a unit outside the site.
  - Inactive sites, units and classes are marked "(inactive)", and the class filter lists active
    classes first.
  - Columns: Unit, or Path when the level isn't *Equipment*.
  - The code cell is a `router-link` with `@click.stop`, so a middle-click opens a new tab.
  - The pager: `ceil(total / 50)`; hidden at total 0; past the end, Prev goes back to the last page
    and Next is disabled.
  - Empty states: "No equipment yet", "No equipment matches these filters" and the no-units
    message.
  - Errors show an alert with Retry.
  - Late responses are dropped by a sequence counter, and the list doesn't reload when leaving the
    route.
- **Equipment page (§ 4.2).**
  - It loads with `watch(() => route.params.id, load, { immediate: true })` (BR2-02).
  - It shows the not-found message only on `err.status === 404`, and an alert with Retry for
    other errors.
  - Breadcrumbs: site and unit are plain text, ancestors are links. Splitting `node.unit` on "." is
    safe because site and unit codes can't contain dots.
  - The "inherited" marker shows when `criticality === null`.
  - The details show the unit for equipment only, and dates go through `formatDateTime()`.
  - Scrapped parts are struck through and stay listed.
  - The scrapped banner shows with no buttons, and "Add part" is hidden on a component.
  - After an edit, move or status change the page reloads. After a create it pushes the new node's
    page, so Back returns to the parent.
- **Dialogs (§ 4.3–4.5, § 5.3).**
  - Edit sends only `class_id`, the fields and `criticality`.
  - Create sends `level`, `unit_id` or `parent_id`, the fields, `criticality` and `status`.
  - Move sends only `unit_id` or only `parent_id`, and Status sends only `status`.
  - Empty text is sent as `null`, the year as a number or `null`, and Inherit as `null`.
  - **`fieldError` is rendered for every field each dialog sends:**
    - create-part: `level` and `parent_id`;
    - create-equipment: `unit_id`;
    - move: `unit_id` and `parent_id`;
    - status: `status`;
    - all dialogs: `class_id`, `name`, `make`, `model`, `serial_no`, `year`, `criticality`.
  - S002's 409 "Scrap or move its parts first" carries `field: "status"`, so it shows under the
    status select.
  - Site and unit picks follow § 4.3 / BR2-04: a single unit wins over the default site.
  - The current class stays listed on edit, and "Inherit (X)" comes from `root_criticality`
    (the parent's on create, the node's on edit).
  - The move unit list is grouped by site and excludes the current unit (BR1-11). The parent
    search returns nothing before text is typed, uses the right `level`, and leaves out the node
    and its current parent (the API already hides scrapped nodes).
  - The status dialog:
    - Save is disabled with "Confirm with Yes" or "No change";
    - the Yes/No row is inline and `ActiveToggle.vue` isn't copied;
    - No resets the choice to the current status;
    - Yes is disabled while saving;
    - the help text per status matches § 4.5.
- **`useFormModal` / `useMasterForm` (§ 5.7).**
  - `useFormModal` has the brief's state and functions, `openCreate(seed)` → `blank(seed)`, and
    closes the dialog before `afterSave(result)` (BR2-03).
  - `useMasterForm` returns exactly the same names as before.
  - Its `openCreate`, `openEdit`, `save` and `changeActive` behave as before: the deactivate
    confirmation is reset, `resetMasters()` and `reload()` run after a save, and the dialog closes
    first.
- **Pure helpers.** `utils/equipmentLabels.js` has no imports, and its maps cover every S002 enum
  value (tested). `describeEvent` covers all six events, both "inherit" directions and `created`
  ignoring `old_value` (tested).
- **Engineering rules.**
  - The frontend holds no business rules beyond offering sensible choices: the level choices,
    excluding components as parents, and the unit narrowing. All are enforced again by S002.
  - No exception is swallowed: every `catch` shows the message.
  - No deprecated APIs.
  - Comments explain *why*.
  - No migrations in this step.
- **Scope.** Nothing is built beyond the brief and the reported decisions. No QR, documents, export
  or bulk import, and no other S002 API change.

## Manual browser checks for the user

The coder didn't drive the screens in a browser, so all of these are still open:

1. **As engineer** with access to `SMTW.FWMILL` only:
   - Add `VBM001`. The unit picker offers only `SMTW.FWMILL`, preselected with its site.
   - Add a drive `DRV001` under it, a motor under the drive, and a motor directly under `VBM001`.
     Check the level default (CR choice 6) suits you.
   - Edit the drive's criticality to A, then back to "Inherit (X)", where X is `VBM001`'s grade.
   - Move the motor from `VBM001` to the drive. The search finds the drive (see CR1-01).
   - Scrap the motor:
     - Save is greyed with "Confirm with Yes";
     - No returns to the old status;
     - Yes scraps it;
     - the page shows the read-only banner.
   - Try to scrap the drive while it has a live part. The refusal shows under the status select.
   - The history shows each step in plain words with DD-MM-YYYY HH:mm dates.
2. **As IT admin:** move `VBM001` to another unit. As the engineer, the list no longer shows it,
   and its URL gives "Equipment not found, or not at your units".
3. **As operator:** the list and pages are visible, with no Add, Edit, Move or Status buttons.
4. **List:**
   - each filter;
   - a search by a motor's code, where the level switches to *All levels*;
   - paging;
   - open a row, then Back returns to the same filtered page in one step;
   - a middle-click on a code opens a new tab;
   - "Show scrapped" together with the Scrapped status;
   - a site change clears a unit outside it;
   - an old bookmark with `page=99` shows "No equipment on this page" with Prev only.
5. **Sidebar and landing:** Equipment stays highlighted on `/equipment/5`, and `/` lands on
   Equipment.
6. **Masters regression** (`useMasterForm` was refactored): create, edit, deactivate and reactivate
   a site, a unit and a class. Refusals show beside the field.
7. **Phone width:** the list table scrolls sideways, and the equipment page stacks Details, Parts
   and History.
8. **DB down:** stop the dev DB. The list and an equipment page show the error with Retry. Start
   the DB again, and Retry works.
