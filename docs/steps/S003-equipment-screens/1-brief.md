```
Step: S003 — Equipment register screens
Doc: brief
Author: Planner (Opus)
Date: 14-10-2026 (revised 14-10-2026 after brief-reviews r1 and r2)
Status: Done (committed 6d58ce5, 15-10-2026)
```

# S003 — Equipment register: the screens

Third slice of Plan.MD phase 2. S002 builds the equipment register's backend and
API (`/api/equipment`). This step builds the screens on top of it, so engineers
can enter and maintain the roughly 500 pieces of equipment and their parts.

**Depends on:** S002 committed. S003's code starts only after that, and it builds
on the API **as S002 actually delivers it**. Where S002's `3-impl-report.md`
records a departure from S002's brief, the report wins.

Background reading:
- `docs/steps/S002-equipment-register/1-brief.md`: § 5 data model, § 6 rules, § 7
  API, and the appendix *Handover to S003*, which this brief takes over and
  completes;
- `docs/steps/S002-equipment-register/3-impl-report.md`;
- `docs/steps/S001-basic-masters/1-brief.md` A1 (default site, the deactivate
  pattern in the edit dialog);
- `docs/Plan.MD` § 4.1, § 6;
- `.claude/SMTW-WebApp-Base.md` § Frontend Design (layout, navigation hierarchy,
  view structure).

## 1. What will be built

A new **Equipment** module in the sidebar, with two pages:

1. **Equipment list** (`/equipment`):
   - a paged table of equipment, with filters;
   - search on code and name;
   - "Add equipment".
2. **Equipment page** (`/equipment/<id>`), one per node at any level:
   - the full path, with each ancestor a link;
   - the fields;
   - its parts as a tree, two levels deep;
   - its history;
   - buttons: Edit, Add part, Move, Change status.

Three dialogs: **create/edit**, **move** and **change status**. Scrapping asks
for an inline Yes/No confirmation, as deactivating does in Masters.

Two small backend additions:
- **`GET /api/equipment/my-units`**, so the unit pickers offer only the units the
  user can work at (§ 5.6);
- **`root_criticality`** in `GET /api/equipment/<id>`, so the dialogs can show the
  grade a part would inherit (§ 5.8, BR1-01).

**Who sees what:**
- Everyone with `equipment:read` (all roles) sees the list and the pages, limited
  to their units by the S002 API.
- The edit buttons show only with `equipment:edit` (engineer, manager, IT admin).

**Out of scope:**
- QR labels and the "scan equipment" phone page (the documents/QR step);
- documents and photos;
- open tickets, due PMs and readings on the equipment page (phases 3–4);
- bulk import (not needed now, user 14-10-2026);
- exporting the list;
- any change to S002's API, other than these two additions.

## 2. Standards and practice

- **ISO 14224 taxonomy (levels 6–8).** ISO 14224 is the international standard
  for collecting reliability and maintenance data. It arranges a plant in levels:
  installation, plant/unit, section, **equipment unit (6)**, **subunit (7)** and
  **maintainable item (8)**. The equipment page shows exactly that: the path down
  from site and unit, and the parts below in the same levels. The screen uses our
  names: *equipment*, *component-unit*, *component* (Plan § 4.1).
- **EN 13306 (maintenance terminology).** EN 13306 separates an item's
  *condition* (**up state**: it can do its job; **down state**: it can't) from
  its *use* within the up state (**operating**, **idle**, **standby**). Yantra's
  `in_service` is operating or idle, and `standby` is EN 13306's standby. The
  other two are **Yantra's life-cycle statuses**, not EN 13306 terms (as S002
  § 2 says): `out_of_use` (laid up) and `scrapped` (the end of life, ISO 55000's
  *dispose* stage). The status dialog never offers "down": that will come from
  breakdowns in phase 3, never from a status typed by hand (BR1-04).
- **ISO 55001 § 7.5–7.6 (information requirements, documented information; 2014
  numbering, as S001 and S002 cite it) and § 8.2 (management of change).**
  The asset register must be controlled and its changes traceable. The equipment
  page shows the history of every move and change, who made it and when. The
  screens never offer a way to delete; scrapping is final and shown as such.
- **TPM equipment ranking.** TPM's planned-maintenance pillar starts by ranking
  equipment A/B/C, so effort goes to the critical machines first. Criticality is
  shown as a coloured badge in the list and can be filtered. A part that inherits
  its grade is marked "inherited", so nobody mistakes an inherited A for a
  deliberate one.
- **ISO 27001 A.5.15 / A.8.3 (access control, least privilege).** Users see and
  pick only the units they work at. The server already enforces this (S002); the
  screens follow it, so users aren't offered choices that would be refused.
- **Visual management (TPM / lean).** The plant should be able to read status at a
  glance. Status and criticality use the same badge colours everywhere (§ 5.4).

## 3. Where

### Backend (small)

- **`backend/equipment.py`:**
  - `GET /my-units`, permission `equipment:read` (§ 5.6). It reuses S002's
    `_accessible_unit_ids`, becoming a new caller of it, so the invariant comment
    above that helper is updated to name it (BR2-06);
  - `GET /<id>` adds `root_criticality` to its response (§ 5.8). The node row
    already carries it; it is one line in `_detail`.
- **`backend/tests/test_equipment_api.py`:** tests for both.

### Frontend

- **`frontend/src/stores/navigation.js`:** a nav item **Equipment** (`/equipment`,
  icon `fa-solid fa-gears`, perm `equipment:read`), placed **before** Masters.
- **`frontend/src/router/index.js`:**
  - routes `/equipment` (name `equipment`, title "Equipment") and
    `/equipment/:id` (name `equipment-detail`, title "Equipment"). The detail
    route is outside the nav, so `canOpenRoute` lets it through and the API's 404
    gates it;
  - `/` changes from `redirect: "/masters"` to
    `redirect: () => landingPath(userPermissions.value) ?? "/equipment"`, so the
    landing rule lives in one place (`landingPath`).
- **`frontend/src/components/layout/AppSidebar.vue`** and **`AppBottomNav.vue`:**
  the active item matches by prefix, `route.path === item.path ||
  route.path.startsWith(item.path + "/")`, so Equipment stays highlighted on
  `/equipment/5` (BR1-08).
- **`frontend/src/views/EquipmentView.vue`** (new): the list.
- **`frontend/src/views/EquipmentDetailView.vue`** (new): the equipment page.
- **`frontend/src/views/equipment/`** (new):
  - `EquipmentFormModal.vue`: create and edit (§ 5.3);
  - `EquipmentMoveModal.vue`: move to a unit, or to a parent;
  - `EquipmentStatusModal.vue`: change status, with the scrap confirmation;
  - `PartsTree.vue`: the parts, two levels;
  - `EquipmentHistory.vue`: the events.
- **`frontend/src/components/FormModal.vue`:** a `saveDisabledReason` prop
  (§ 4.5, BR1-07). When set, Save is disabled and shows the reason as its
  `title`.
- **`frontend/src/components/`** (new, shared):
  - `StatusBadge.vue` and `CriticalityBadge.vue` (§ 5.4);
  - `PagerBar.vue`: previous/next, "page n of m", the total.
- **`frontend/src/composables/useFormModal.js`** (new): `useMasterForm.js` is
  generalised (§ 5.7).
- **`frontend/src/views/masters/useMasterForm.js`:** becomes a thin wrapper over
  `useFormModal` that adds `changeActive`. The three masters panels that use it
  (Sites, Units, Equipment classes) don't change.
- **`frontend/src/stores/equipment.js`** (new): the `ensureMyUnits()` cache.
- **`frontend/src/utils/equipmentLabels.js`** (new, pure, no imports from
  `api.js`): the label maps for levels, statuses and criticality, and
  `describeEvent` (§ 5.4, § 5.5, BR1-10).

### Tests

- `frontend/tests/navigation.test.js`: the three tests named in S002's handover
  change (Equipment is now first, and the landing page is `/equipment`). The
  per-role permission lists are brought up to `test_rbac.py`'s matrix **in
  full** (`equipment:read`, and `equipment:read_all_units` for the manager and
  IT admin), so the two can't drift (BR1-08).
- `frontend/tests/equipmentLabels.test.js` (new): the pure helpers of § 5.4–5.5.
- Backend: § 8.

### Docs

None for the coder. At approval the planner notes in Plan § 6 that the desktop
equipment register and tree are built.

## 4. Screens

### 4.1 Equipment list (`/equipment`)

```
[Site ▾] [Unit ▾] [Class ▾] [Status ▾] [Criticality ▾] [Level ▾]  [Search…]   [+ Add equipment]
☐ Show scrapped
Code     Name                 Class  Unit           Crit.  Status       Parts
VBM001   Vertical blade mill  VBM    SMTW.FWMILL    A      In service   3
…
                                         ‹ Prev   Page 1 of 4 (183)   Next ›
```

- **Filters:**
  - site, unit, class, status, criticality, level, search, "Show scrapped";
  - **level** defaults to *Equipment*; the choices are Equipment / Component-units
    / Components / All levels;
  - typing a search switches level to *All levels*, so a motor is found by its
    code (S002 handover). It switches only when the trimmed search goes from
    empty to non-empty while the level is *Equipment*, and never switches back by itself;
    the user can change it (BR1-06);
  - the unit filter lists the user's units (§ 5.6), narrowed to the chosen site.
    Changing the site clears a chosen unit that isn't in it;
  - the class filter lists all classes, active ones first;
  - the search waits 300 ms after the last keystroke;
  - the status filter offers **Scrapped** only while "Show scrapped" is ticked.
    The API hides scrapped nodes unless `include_scrapped=1`, so the two
    controls would otherwise give an always-empty page (BR1-06). To keep them
    consistent (BR2-01):
    - unticking "Show scrapped" while Scrapped is chosen clears the status
      filter;
    - a URL with `status=scrapped` (e.g. a bookmark) ticks "Show scrapped" on
      load;
  - the site filter lists all sites, inactive ones marked "(inactive)" (BR2-04);
    inactive units in the unit filter are marked the same way, not greyed,
    since a greyed `<option>` doesn't show reliably;
- **The filters live in the URL query** (`/equipment?unit_id=4&q=mot&page=2`):
  - so Back from an equipment page returns to the same filtered page;
  - and a filtered list can be bookmarked or sent to a colleague.
  - A filter change resets to page 1.
  - Filter, search and page changes use `router.replace`, not `push`, so they
    don't pile up history entries: Back from an equipment page lands on the
    filtered list in one step.
  - Defaults are left out of the URL (`level=equipment`, `page=1`, scrapped
    hidden), so `/equipment` is the default view.
- **Columns:** code, name, class, unit, criticality (effective), status, parts.
  When the level is not *Equipment*, the unit column shows the full path
  instead, so a part's place is visible.
- A row click opens the equipment page. The code cell is a `<router-link>`, so a
  middle-click opens it in a new tab (BR2-07).
- **Page size** 50, the API default. The pager shows "Page n of m (total)", with
  m = ceil(total / 50). At total 0 there is no pager, only the empty state. A
  page past the end (e.g. from an old bookmark) shows "No equipment on this
  page" and the pager offers Prev only (BR1-12).
- **Loading and errors** (BR1-09): "Loading…" while fetching, as the masters
  panels do. Any error (network, 503 while the database is unavailable) shows an
  alert with the message and a **Retry** button.
- **Empty states:** "No equipment yet" when nothing exists and no filter is set;
  "No equipment matches these filters" otherwise. A user with no units and
  without all-units access sees "You have no units assigned — ask IT admin for
  unit access".
- "Add equipment" shows with `equipment:edit` and opens the create dialog at
  level *equipment*.

### 4.2 Equipment page (`/equipment/<id>`)

```
SMTW › FWMILL › VBM001 › DRV002                                    ← links
DRV002 — Main drive                       [In service] [Crit. A · inherited]
[Edit] [Add part] [Move] [Change status]

Details                 Parts                          History
Class   DRV — Drive     MOT017 Motor 30 kW   In serv.  14-10-2026 10:12 kla  Status: In service → Standby
Make    …               GBX003 Gearbox       In serv.  …
Model   …
Serial  …
Year    2019
```

- **Header:** the path as breadcrumbs; site and unit are plain text, ancestors are
  links. Then the code, name, status badge and criticality badge (marked
  "inherited" when the part has no own grade).
- **Details:** level, class (code and name), make, model, serial number, year,
  the unit (equipment only), created and last updated (who, when).
- **Parts:** the `children` from the API, two levels, indented. Scrapped nodes are
  greyed and struck through, and stay listed (S002: visible on the parent's page).
  Each row is a link. A component-unit's components appear under it.
  "No parts yet" when empty.
- **History:** newest first, in plain words (§ 5.5). Dates as DD-MM-YYYY HH:mm,
  through the existing `formatDateTime()` in `utils/datetime.js` (BR1-10).
- **Buttons** (with `equipment:edit`, hidden on a scrapped node):
  - **Edit:** the create/edit dialog;
  - **Add part:** the create dialog with this node as parent. Hidden on a
    component, which can't have parts;
  - **Move:** to a unit (equipment) or to another parent (parts);
  - **Change status.**
- **Scrapped node:** a grey banner "Scrapped — this record is read-only", and no
  buttons.
- **404** (unknown, or outside the user's units; only `err.status === 404`):
  "Equipment not found, or not at your units", with a link back to the list. The
  two cases look the same, as the API intends.
- **Other errors and loading:** as on the list (§ 4.1): "Loading…", then an
  alert with the message and Retry.
- After any save, the page reloads the node from the API, so the path, the parts
  and the history are current.
- **The page follows its route** (BR2-02). Vue Router reuses the component when
  only `:id` changes (a breadcrumb link, a parts-tree link, opening a new part),
  so the page loads with `watch(() => route.params.id, load, { immediate: true })`
  rather than only on mount.

### 4.3 Create / edit dialog

| Field | Create equipment | Create part | Edit |
|---|---|---|---|
| Level | fixed: equipment | pick: component-unit or component (only *component* under a component-unit) | shown, read-only |
| Site, Unit | two picks: site (active sites that hold one of the user's active units), then the unit narrowed to it (the user's active units). The default site is preselected (S001 A1). When the user has exactly one unit, it and its site are preselected, and that wins over the default site (BR2-04) | — (its parent's) | shown, read-only; changed by **Move** |
| Parent | — | fixed: the node it was opened from | shown, read-only; changed by **Move** |
| Class | pick (active classes) | pick | pick (the current class stays listed even if inactive) |
| Code | "issued on save" | "issued on save" | shown, read-only |
| Name | required | required | editable |
| Make, model, serial no. | optional | optional | editable |
| Year | optional | optional | editable |
| Criticality | A / B / C, default C | Inherit (shows the grade, e.g. "Inherit (A)") / A / B / C, default Inherit. The grade shown is the **root equipment's**, from `root_criticality` (§ 5.8) | as on create |
| Status | In service / Standby / Out of use, default In service | same | not here; **Change status** |

- After a create, the app opens the new node's page.
- The class field explains: "The class sets the code prefix. Changing it later
  keeps the code."

### 4.4 Move dialog

- **Equipment:** pick a unit from the user's active units, grouped by site. The
  current unit is shown as current and can't be picked: the API silently ignores
  a move to the same unit, so Save would seem to do nothing (BR1-11). The note:
  "Its parts move with it."
- **Component-unit or component:** pick a new parent.
  - A search box lists the matches that may be parents. Nothing is listed until
    the search is non-empty.
    - For a component-unit: `GET /api/equipment?level=equipment&q=…`.
    - For a component: `GET /api/equipment?level=all&q=…`, keeping equipment and
      component-units.
    - Scrapped nodes, the node itself and its current parent are left out.
  - Each match shows its code, name and full path.
- The API's refusals (400 level rule, 403 at a unit the user can't access, 409 at
  a scrapped target) show beside the field.

### 4.5 Change status dialog

- Choices: In service, Standby, Out of use, **Scrapped**.
- Choosing Scrapped shows, before saving: "Scrap **VBM001**? This is final — the
  record becomes read-only." with Yes/No, in the same inline shape as
  `ActiveToggle.vue`.
  - **Yes** is then the only way to save. Save is disabled through
    `saveDisabledReason` ("Confirm with Yes"), so there aren't two submit paths
    (BR1-07). **No** sets the choice back to the current status.
  - The Yes/No row is a few lines of inline markup in
    `EquipmentStatusModal.vue`; `ActiveToggle.vue` is not copied.
- While the chosen status equals the current one, Save is disabled with
  `saveDisabledReason` "No change" (BR2-08).
- The API's 409 "Scrap or move its parts first" shows in the dialog.
- A short help line per status (§ 2 on which are EN 13306 terms):
  - In service: in use (EN 13306 operating or idle);
  - Standby: ready to run, not running, e.g. a spare pump (EN 13306 standby);
  - Out of use: laid up; no PM due (Yantra life-cycle status);
  - Scrapped: removed from the plant for good (Yantra life-cycle status).

## 5. Rules

### 5.1 The server decides

The screens hold no business rules beyond what's needed to offer sensible
choices. Every rule (levels, scrapped targets, access, inactive classes and units,
year range) is enforced by S002. A refusal arrives as `{error, field}` and is shown
beside the field, or at the top of the dialog when no field is named, as in
Masters.

### 5.2 Permissions

- `equipment:read`: the list, the pages, `my-units`.
- `equipment:edit`: Add equipment, Edit, Add part, Move, Change status.
- `equipment:read_all_units` is not used in the frontend; `my-units` already
  reflects it.

### 5.3 Forms send only what they own

- Create sends `level`, `unit_id` or `parent_id`, `class_id`, the fields,
  `criticality` and `status`.
- Edit sends `class_id`, the fields and `criticality`; not `status`, `unit_id` or
  `parent_id`.
- Move sends only `unit_id` or only `parent_id`. Change status sends only
  `status`.
- So one dialog can't undo another's change by sending a stale value.
- Empty optional text is sent as `null`; year as a number or `null`.

### 5.4 Badges and labels (one place)

`utils/equipmentLabels.js` holds the display labels, so every screen says the same:

| Value | Label | Badge |
|---|---|---|
| `in_service` | In service | green |
| `standby` | Standby | blue |
| `out_of_use` | Out of use | grey |
| `scrapped` | Scrapped | dark, struck through |
| `A` | A | red |
| `B` | B | amber |
| `C` | C | grey outline |
| `equipment` / `component_unit` / `component` | Equipment / Component-unit / Component | — |

### 5.5 History in plain words

| Event | Shown as |
|---|---|
| `created` | Created |
| `moved_unit` | Moved: SMTW.FWMILL → SSVT.SHOP |
| `moved_parent` | Moved: SMTW.FWMILL.VBM001.DRV002 → SMTW.FWMILL.VBM002.DRV005 |
| `status` | Status: In service → Standby |
| `criticality` | Criticality: B → A. S002 writes the literal `inherit` for no own grade; it is shown as "Inherited" (Inherited → A, A → Inherited) |
| `class` | Class: VBM → HP |

The texts come from S002's old/new snapshots. `created` shows "Created" and
ignores `old_value` (BR1-02). A pure helper `describeEvent(event)`
turns an event into that line, so it can be unit-tested.

### 5.6 `GET /api/equipment/my-units`

- **Why:** the masters API lists every unit to every role. Offering units the user
  can't access would lead to a 403 on save.
- **Returns** `{all_units: bool, unit_ids: [...]}`:
  - `all_units: true` for holders of `equipment:read_all_units` (and admin), with
    `unit_ids` empty;
  - otherwise the user's unit ids from `user_units`.
- The frontend combines it with the cached masters units (`ensureUnits()`) to
  build its pickers: the unit filter, the create dialog and the move dialog.
- **Which units each picker offers** (BR1-03). `_accessible_unit_ids` returns
  only **active** units, so:
  - users with unit rows: their active units, in the filter and the pickers;
  - `all_units: true` users: the **filter** lists every unit, inactive ones
    greyed, because a deactivated unit may still hold scrapped equipment. The
    create and move pickers list active units only.
- **The cache is per tab.** After IT admin changes a user's unit access, an open
  tab keeps its list until reload. A save at a unit just revoked gets the API's
  403 beside the field, which is the designed safety net.

### 5.7 `useFormModal` (S002 handover, BR1-12 there)

- **`composables/useFormModal.js`** keeps the generic part (BR1-05):
  - state: `modal`, `form`, `editingId`, `editingLabel`, `saving`, `error`;
  - `fieldError`, `modalError`, `openEdit(record)`, `save()`;
  - `openCreate(seed)` passes `seed` to `blank(seed)`, so the create-part dialog
    gets its parent (id, level, root grade) at open time and `blank` stays pure;
  - its parameters: `path`, `blank(seed)`, `fromRecord`, and `afterSave(result)`;
  - `save()` closes the modal, then passes the API's response body to
    `afterSave(result)`. After a create the equipment page opens the new node
    from `result.id`; closing first means the modal isn't left open over the
    new page (BR2-03);
  - `modalError` shows a refusal at the top only when its field is not in the
    form. So **every field a dialog sends must render `fieldError(name)`
    somewhere**, read-only ones included: `parent_id` and `level` in the
    create-part dialog, `unit_id` in the move dialog, `status` in the status
    dialog. Otherwise a 400/403/409 on that field would be shown nowhere
    (BR2-03).
- **`useMasterForm`** stays the masters' wrapper: `useFormModal` plus the
  masters-only state and actions (`editingActive`, `confirmingDeactivate`,
  `changeActive`) and the masters' after-save (`resetMasters()` + `reload()`).
  Its returned names stay the same, so the three panels' destructuring lines
  don't change.

### 5.8 `root_criticality` in `GET /api/equipment/<id>` (BR1-01)

- A part inherits its **root equipment's** grade at every depth (S002 § 6). A
  component under a component-unit graded A, inside equipment graded B, inherits
  **B**.
- The detail response doesn't carry the root's grade today: `ancestors` has no
  grades. So `_detail` adds `root_criticality`, which the node row already holds.
  For equipment it equals its own grade.
- The create-part dialog uses the **parent's** `root_criticality`; the edit
  dialog uses the **node's**. The frontend never computes inheritance itself.

## 6. Design decisions

| Decision | Reason | Rejected alternative |
|---|---|---|
| Detail page as its own route `/equipment/<id>` | It can be linked, bookmarked and later opened from a QR code | A side panel on the list |
| Filters in the URL query | Back returns to the same page; a list can be shared | Keeping them in a store (lost on reload) |
| Separate Move and Change status dialogs; Edit sends only its own fields | A move or a scrap is a deliberate act with its own history event; no dialog overwrites another's change | One big edit form |
| A new `my-units` endpoint | Pickers offer only what the server will accept (ISO 27001 least privilege) | Listing all units and letting the save fail with 403 |
| `root_criticality` in the detail API | The rule stays in the backend; the "Inherit (X)" label is right at every depth (BR1-01) | Fetching the root separately; a label without the grade |
| Scrap confirmed only by Yes; Save disabled with a reason | One submit path for a final act (BR1-07) | A `hideSave` prop; a warning text only |
| Typing a search switches the level to All | A motor is usually searched by its code | Searching equipment only |
| Labels and badge colours in one place, `utils/equipmentLabels.js` | One vocabulary on every screen | Labels per component |
| Parts tree two levels, as the API returns it | Three levels is the whole tree from equipment down | A lazily expanding tree |

## 7. Phone use

- Operators and technicians have `equipment:read`. The pages work on a phone: the
  list table scrolls sideways; the equipment page stacks Details, Parts and
  History in one column.
- The phone home page and QR scanning are not part of this step.

## 8. Tests and acceptance

### Backend

- `GET /my-units`:
  - an engineer with two units gets those two ids, `all_units: false`;
  - a manager and IT admin get `all_units: true`;
  - a user with no rows gets `[]`, `all_units: false`;
  - every role can call it.
- `GET /<id>` `root_criticality`: a component-unit graded A under equipment
  graded B returns `root_criticality: "B"`, and a component under it too;
  equipment returns its own grade.

### Frontend (vitest)

- `navigation.test.js`: Equipment is first for every role; the landing page is
  `/equipment`; an operator sees Equipment and Masters.
- `equipmentLabels.test.js`: `describeEvent` for each event kind, including
  `inherit → A` and `A → inherit`; `created` ignores `old_value`; the label maps
  cover every enum value of S002.

### Manual checks in the browser (user)

- As **engineer** with unit access to `SMTW.FWMILL` only:
  - add `VBM001` there with a drive `DRV001` and a motor under it, and a motor
    directly under the equipment;
  - the unit picker offers only `SMTW.FWMILL`;
  - edit, set the drive's criticality to A, back to inherited;
  - move the motor from the equipment to the drive;
  - scrap the motor (Yes/No), then try to scrap the drive while it has a live
    part (refused);
  - the history shows each step in plain words.
- As **IT admin:** move `VBM001` to another unit; the engineer no longer sees it,
  and its page gives the not-found message.
- As **operator:** sees the list and pages, no edit buttons.
- Filters, search (a motor found by its code), paging, Back to the same filtered
  page.
- Phone width: list and equipment page readable.
- Stop the dev DB: the list shows the error with Retry; start it, Retry works.

### Acceptance

- `tooling/run-tests.bat` green; `npx vite build` clean.
- An engineer can enter a machine with its parts entirely through the screens.

## 9. Open questions and assumptions

1. **Decided (user, 15-10-2026, approved as recommended) — two small backend additions** in a screens step: the
   `my-units` endpoint and `root_criticality` in the detail (BR1-01). The
   alternatives are to list all units and let a save fail with 403, and to show
   "Inherit" without the grade. Recommended: add both.
2. **Decided (user, 15-10-2026, approved as recommended) — landing page.**
   Everyone lands on **Equipment** instead of Masters, since it is the page used
   daily.
3. **Assumption:** the list's default is equipment only (level 6); parts are found
   by search or from their machine's page.
4. **Assumption:** no "Add part" from the list; parts are added from their parent's
   page, which keeps the tree in view.

## 10. Amendments

(none)

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 14-10-2026

| Finding | Severity | Response |
|---|---|---|
| BR1-01 "Inherit (A)" shows a grade the API doesn't provide | major | **Accepted, option (a).** `root_criticality` added to `GET /<id>` (§ 1, § 3, § 5.8, § 8); the dialogs use the parent's or node's value. Put to the user with `my-units` (§ 9.1). |
| BR1-02 The criticality event never has an empty side | minor | **Accepted.** `inherit` is shown as "Inherited"; `created` ignores `old_value`; tests added (§ 5.5, § 8). |
| BR1-03 `my-units` returns active units only | minor | **Accepted.** The picker rule restated per kind of user; the per-tab cache staleness and the 403 safety net stated (§ 5.6). |
| BR1-04 Standards citations | minor | **Accepted.** EN 13306 mapped exactly; `out_of_use` and `scrapped` called Yantra life-cycle statuses; ISO 55001 § 7.5–7.6 (§ 2, § 4.5). |
| BR1-05 `useFormModal` under-specified | minor | **Accepted.** `openCreate(seed)`, the response passed to `afterSave(result)`, and which refs stay in the masters wrapper; "three panels" (§ 3, § 5.7). |
| BR1-06 URL-query rules | minor | **Accepted.** `router.replace`; defaults left out of the URL; the level switches only on empty → non-empty; Scrapped in the status filter only with "Show scrapped"; a site change clears a unit outside it (§ 4.1). |
| BR1-07 Save versus Yes/No | minor | **Accepted, option (a).** `FormModal` gains `saveDisabledReason`; Yes is the only way to scrap; the Yes/No row is inline (§ 3, § 4.5, § 6). |
| BR1-08 Sidebar active state; navigation test lists | minor | **Accepted.** Prefix match in `AppSidebar` and `AppBottomNav`; the test lists follow `test_rbac.py` in full (§ 3). |
| BR1-09 Loading and error states | minor | **Accepted.** "Loading…", an alert with Retry for any non-404 error, 404 only on status 404, a 400 in the move dialog beside the field (§ 4.1, § 4.2, § 4.4, § 8). |
| BR1-10 Reuse the date formatter; pure helpers without `api.js` | nit | **Accepted.** `formatDateTime()` named; labels and `describeEvent` in `utils/equipmentLabels.js` (§ 3, § 4.2, § 5.4). |
| BR1-11 Picker rules | nit | **Accepted.** Site + unit fields on create, a single unit preselected; the current unit not pickable on move; `level=equipment` for a component-unit's parent; no list before a search (§ 4.3, § 4.4). |
| BR1-12 Pager edge cases | nit | **Accepted.** m = ceil(total/50); no pager at 0; a page past the end offers Prev (§ 4.1). |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 14-10-2026

All twelve round-1 answers were verified in the text. No blocker or major finding.

| Finding | Severity | Response |
|---|---|---|
| BR2-01 Scrapped status can still reach the API without `include_scrapped` | minor | **Accepted.** Unticking "Show scrapped" clears a Scrapped status; a `status=scrapped` URL ticks it on load (§ 4.1). |
| BR2-02 The equipment page must reload when `:id` changes | minor | **Accepted.** `watch(() => route.params.id, load, { immediate: true })` (§ 4.2). |
| BR2-03 `useFormModal`: close before `afterSave`; refusals on read-only fields | minor | **Accepted.** `save()` closes, then calls `afterSave(result)`; every sent field renders `fieldError` (§ 5.7). |
| BR2-04 Site pick-lists; single unit vs default site; greyed options | minor | **Accepted.** Site lists defined; a single unit wins over the default site; "(inactive)" suffix instead of grey (§ 4.1, § 4.3). |
| BR2-05 § 6 still says "one store" | nit | **Accepted.** Now `utils/equipmentLabels.js`. |
| BR2-06 `my-units` is a new caller of `_accessible_unit_ids` | nit | **Accepted.** The invariant comment is updated (§ 3). |
| BR2-07 Trim `q` before the level switch; code cell as a link | nit | **Accepted** (§ 4.1). |
| BR2-08 Status dialog with no change | nit | **Accepted.** Save disabled with "No change" (§ 4.5). |

### Gate A — user decision, 15-10-2026

- **Approved** as written, with the recommendations of § 9: both backend
  additions (`my-units`, `root_criticality`) and Equipment as the landing page.
- Coder: Sonnet (UI on the masters pattern; two one-line backend additions).
- **15-10-2026, user:** S003 is coded on top of the **uncommitted** S002
  (clean after code review r2); both are committed together at the end. S003's
  code review must tell S002's files apart from S003's (§ 3 lists S003's).

### Gate B — user decision, 15-10-2026

- Code review r1 was clean (0 blocker, 0 major). The user first closed the step
  without a fix round, then (same day) asked for a fix round on **CR1-01, CR1-02,
  CR1-04, CR1-05, CR1-06, CR1-07 and CR1-09**. CR1-03 (report test counts) and
  CR1-08 (URL-rule unit tests) are not fixed.
- The create-part dialog keeps the coder's default level, Component-unit, under
  equipment.
- Class codes stay 2–4 letters (S001 rule); `PP01` is entered as class `PP`.
