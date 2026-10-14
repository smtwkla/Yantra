```
Step: S003 — Equipment register screens
Doc: impl-report
Author: Coder (Sonnet)
Date: 15-10-2026
```

# S003 — Implementation report

Implemented per the approved brief (`1-brief.md`, approved 15-10-2026 by KLA), on top of the
uncommitted S002. Nothing is committed.

**Test result.**
- `tooling/run-tests.bat` is green: **462 backend tests** (436 before, +26 new in
  `test_equipment_api.py`) and **23 frontend tests** (15 before).
- `npx vite build` in `frontend/` is clean (132 modules, no warnings).
- The screens have **not** been driven in a browser; see "Not done".

## What was built

- **Backend (two additions in `equipment.py`):**
  - `GET /api/equipment/my-units` returns `{all_units, unit_ids}`;
  - `GET /api/equipment/<id>` now carries `root_criticality`.
- **Equipment module** in the sidebar and bottom nav, first item, with:
  - the **list** `/equipment`: filters kept in the URL, search, paging, "Show scrapped", Add equipment;
  - the **equipment page** `/equipment/<id>`: breadcrumbs, badges, details, parts tree, history, and the buttons Edit, Add part, Move, Change status;
  - three dialogs: create/edit, move, change status (with the inline Yes/No scrap confirmation).
- Everyone now **lands on Equipment** instead of Masters.
- Shared pieces: `StatusBadge`, `CriticalityBadge`, `PagerBar`, `utils/equipmentLabels.js`, `FormModal`'s `saveDisabledReason`, and `composables/useFormModal.js` (with `useMasterForm` as a thin wrapper).

## How it works

- **Server decides.** The screens only offer sensible choices; every refusal arrives as `{error, field}` and is shown beside the field (or at the top when the field is not in the form). Every field a dialog sends renders `fieldError(name)`, read-only ones included.
- **List.** `route.query` is the single source of truth.
  - Controls write the query with `router.replace` through one `update()` function: defaults are dropped, a filter change resets the page.
  - The view reloads when `route.fullPath` changes.
  - Typing a search waits 300 ms; the first non-empty search while the level is *Equipment* switches it to *All levels*.
  - `status=scrapped` in a URL ticks "Show scrapped". Unticking it clears a Scrapped status.
  - Changing the site clears a chosen unit outside it.
  - Out-of-date responses are dropped with a sequence counter.
- **Unit pickers.** `stores/equipment.js` caches `my-units`. `pickableUnits` = active units the user can work at (create and move); `filterableUnits` = every unit for all-units users (inactive marked), else the same as pickable.
- **Equipment page.** Loads with `watch(() => route.params.id, load, {immediate: true})`, so it follows the route when only `:id` changes. 404 gives the not-found message; any other error gives an alert with Retry. After a save it reloads (after a create it opens the new node).
- **Dialogs.** All three use `useFormModal`.
  - Edit sends only `class_id`, the fields and `criticality`.
  - Move sends only `unit_id` or only `parent_id`.
  - Status sends only `status`.
  - Create sends `level`, `unit_id`/`parent_id`, the fields, `criticality` and `status`.
  - Empty optional text goes as `null`, the year as a number or `null`, "Inherit" as `null`.
  - The create-part and edit dialogs show "Inherit (X)" from the root equipment's `root_criticality`.
  - Scrapping: choosing Scrapped disables Save ("Confirm with Yes") and shows Yes/No inline; Yes calls save. "No change" disables Save while the status equals the current one.
- **Move dialog.** Equipment: unit picker grouped by site, current unit not offered. Parts: debounced search (`level=equipment`, or `all` for a component), results exclude the node itself, its current parent and components.

## Files touched (S003 only)

Backend:
- `backend/equipment.py`: `GET /my-units`; `root_criticality` in `_detail`; the invariant comment above `_accessible_unit_ids` names `/my-units`.
- `backend/tests/test_equipment_api.py`: `TestMyUnits` and `TestRootCriticality` appended (26 new tests in total, counting parametrised cases).

Frontend, modified:
- `frontend/src/stores/navigation.js`: Equipment nav item first; `isActivePath` helper.
- `frontend/src/router/index.js`: `/equipment`, `/equipment/:id`; `/` redirects through `landingPath`.
- `frontend/src/components/layout/AppSidebar.vue`, `AppBottomNav.vue`: prefix-match active state via `isActivePath`.
- `frontend/src/components/FormModal.vue`: `saveDisabledReason` prop.
- `frontend/src/views/masters/useMasterForm.js`: now a wrapper over `useFormModal`.
- `frontend/tests/navigation.test.js`: updated lists and expectations, `isActivePath` test.

Frontend, new:
- `frontend/src/composables/useFormModal.js`
- `frontend/src/stores/equipment.js`
- `frontend/src/utils/equipmentLabels.js`
- `frontend/src/components/StatusBadge.vue`, `CriticalityBadge.vue`, `PagerBar.vue`
- `frontend/src/views/EquipmentView.vue`, `EquipmentDetailView.vue`
- `frontend/src/views/equipment/EquipmentFormModal.vue`, `EquipmentMoveModal.vue`, `EquipmentStatusModal.vue`, `PartsTree.vue`, `EquipmentHistory.vue`
- `frontend/tests/equipmentLabels.test.js`

Docs: this report; the brief's `Status` and the README index row (`In code review`).

## Decisions taken

None departs from the brief. Small forced choices:
1. `useFormModal` takes an optional `toBody(form)` (default identity) besides the brief's four parameters, and exposes `send(request)`, used by the masters wrapper's `changeActive`. `toBody` turns empty text into `null`, the year into a number, and "Inherit" into `null` (§ 5.3), so the form holds plain input values.
2. `isActivePath(routePath, itemPath)` in `navigation.js`, so the sidebar and bottom nav share one prefix rule (DRY), with a test.
3. Move dialog: Save is disabled with a reason ("Choose a unit" / "Choose a new parent") until a target is picked, using the new `saveDisabledReason`. The part search lists at most 20 matches.
4. `PartsTree` renders itself recursively for the second level rather than duplicating the row markup.
5. The edit dialog shows the parent as its code only; for equipment it shows the unit.
6. In the create-part dialog the level defaults to *Component-unit* under equipment (the brief does not say).
7. The breadcrumb has no "Equipment" list link, as in the brief's sketch; the sidebar and the 404 message link back.
8. If the masters or `my-units` fail to load when a dialog opens, the dialog still opens with the error at the top.
9. The backend tests also cover an inactive unit being left out of `my-units`, which the brief did not list.
10. The list's filter selects use `v-model` through small computed wrappers (not a plain `:value`), so a bookmarked filter shows correctly once the options arrive.

## Not done / deferred / assumed

- **No browser check.** I did not run the app against the dev server; only the build and unit tests ran. The manual checks below are for the user.
- No component tests (the brief asks for helper tests only); the list and dialog logic is covered only by the build.

### Manual browser checks (brief § 8, for the user)

1. As **engineer** with unit access to `SMTW.FWMILL` only:
   - add `VBM001` there with a drive `DRV001` and a motor under it, and a motor directly under the equipment;
   - the unit picker offers only `SMTW.FWMILL` (preselected);
   - edit; set the drive's criticality to A, then back to Inherit (the "Inherit (X)" label shows the root equipment's grade);
   - move the motor from the equipment to the drive;
   - scrap the motor (Yes/No), then try to scrap the drive while it has a live part (refused, shown in the dialog);
   - the history shows each step in plain words.
2. As **IT admin:** move `VBM001` to another unit; the engineer no longer sees it, and its page gives the not-found message.
3. As **operator:** sees the list and pages, no edit buttons.
4. Filters, search (a motor found by its code), paging, Back to the same filtered page; "Show scrapped" together with the Scrapped status filter; a site change clearing a unit outside it.
5. Phone width: list and equipment page readable.
6. Stop the dev DB: the list shows the error with Retry; start it, Retry works.
7. The sidebar highlights Equipment on `/equipment/5`; `/` lands on Equipment; the masters panels still create, edit and deactivate (`useMasterForm` was refactored).

## Fix rounds

### Round 1

Fixes for `4-code-review-r1.md`, limited to the findings the user chose (15-10-2026).

**Test result.** `tooling/run-tests.bat` green: 462 backend, 23 frontend (unchanged; no new tests, as no pure logic was added). `npx vite build` clean.

- **CR1-01 — Accepted.** `EquipmentMoveModal.vue`: for a component the parent search now runs two requests, `level=equipment` and `level=component_unit` (a component-unit still searches `equipment` only), so components can no longer use up the 20 rows. The client-side component filter is gone. When any response has `total` above the rows returned, the dialog shows "More matches — type more of the code or name to refine the search."
- **CR1-02 — Accepted.** `EquipmentFormModal.vue`: `CREATE_STATUSES` is now `Object.entries(STATUS_LABELS)` without `scrapped`.
- **CR1-03 — Not fixed — user's choice.**
- **CR1-04 — Accepted.** The list shows a small "Loading…" above the table while a fetch runs and rows are on screen (old rows stay, no flicker). The equipment page shows "Loading…" beside the header while loading with a node on screen, and hides Edit/Add part/Move/Change status until the load ends.
- **CR1-05 — Accepted.** Route is now `/equipment/:id(\d+)`; `/equipment/my-units` matches no route.
- **CR1-06 — Accepted.** Changing the status away from `scrapped` while `scrapped=1` is not in the query adds `scrapped=1` in the same `update()` (new `chooseStatus` in `EquipmentView.vue`).
- **CR1-07 — Accepted.** New `composables/useDebounced.js` (`schedule`, `cancel`, cleanup on unmount), used by the list search and the move dialog; both local timers and `onBeforeUnmount` code removed. The two 300 ms constants remain, one per file (the delay is passed in).
- **CR1-08 — Not fixed — user's choice.**
- **CR1-09 — Accepted.** `FormModal.vue` comment now says "shared by the masters panels and the equipment dialogs".

Decisions: none beyond the above. The create-part default level is unchanged (Component-unit, user decision). Manual browser checks listed above still apply, especially: the move search for a motor with many "drive" matches, and the `status=scrapped` bookmark switched to "All statuses".
