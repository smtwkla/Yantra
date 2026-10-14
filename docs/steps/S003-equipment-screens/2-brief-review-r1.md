```
Step: S003 — Equipment register screens
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 14-10-2026
```

# S003 — Brief review, round 1

**Verdict: one `major` finding is open (BR1-01). No blocker.**

What was checked: the brief against S002's approved brief (§ 5–7, the
*Handover to S003* appendix), the S002 code now in the working tree
(`backend/equipment.py`, `equipment_core.py`, `config_rbac.py`, `auth_utils.py`,
`db_helpers.py`), S001 A1, Plan.MD § 3, § 4.1, § 6, the Maintenance Philosophy,
the base's *Frontend Design*, *Sidebar visibility* and *API Response Conventions*
sections, and the frontend as it is (`stores/navigation.js`, `router/index.js`,
`App.vue`, `AppSidebar.vue`, `AppBottomNav.vue`, `AppTopbar.vue`,
`views/masters/useMasterForm.js`, the three panels that use it,
`UserUnitsPanel.vue`, `components/FormModal.vue`, `ActiveToggle.vue`,
`stores/masters.js`, `api.js`, `utils/datetime.js`, `tests/navigation.test.js`).

S002 is still being coded, so where the working tree and S002's brief differ, I
note it; the brief already says S002's impl report wins.

---

## Findings

### BR1-01 — `major` — "Inherit (A)" shows a grade the API does not provide

**Problem.** § 4.3 says the criticality field on a part offers *Inherit (shows
the grade, e.g. "Inherit (A)")*. The grade a part inherits is its **root
equipment's** grade, at every depth (S002 § 6, decision § 3.1: a component under
a graded component-unit still inherits the equipment's grade). The brief does
not say where the dialog gets that grade from, and the detail API cannot always
supply it:

- `GET /<id>` returns `criticality` (own) and `effective_criticality`, plus
  `ancestors: [{id, code, level, name}]` — **no criticality on the ancestors and
  no root grade** (`_detail` in `equipment.py`; S002 § 7 agrees).
- For **Add part** from a component-unit page, or **Edit** of a node that has
  its own grade, the only grade at hand is the parent's or the node's own
  `effective_criticality`. When a component-unit is graded A while its
  equipment is B, a new component under it inherits **B**, but the dialog would
  show "Inherit (A)".

**Why it matters.** The brief's own § 2 (TPM ranking) says the point of marking
"inherited" is that nobody mistakes an inherited grade for a deliberate one.
A wrong grade in the Inherit label misleads the engineer about the consequence
of choosing it, on the one field the TPM planned-maintenance pillar's ranking
depends on. Left as is, the coder would pick the parent's
`effective_criticality` and the bug would be silent.

**Options.**
- (a) **Expose the root grade in the detail API.** `_detail` adds one field,
  `root_criticality` (the node row already carries it as
  `node["root_criticality"]`; for equipment it equals its own grade). The
  create-part dialog opened from a parent page uses the parent's
  `root_criticality`; the edit dialog uses the node's. Add it to this step's
  small backend part, next to `my-units`, with one test (a graded
  component-unit under a B equipment returns `root_criticality: "B"`).
- (b) Fetch the root ancestor (`ancestors[0]`) when opening the dialog from a
  graded component-unit. A second request for one label.
- (c) Drop the grade from the label: plain "Inherit (the equipment's grade)".

**Recommendation.** (a). It is one line in a shell that is being written now,
it keeps the rule in the backend (the frontend never computes inheritance), and
it is the same size of addition as `my-units`. Record it in § 1 and § 3 as the
second backend addition, and in § 8.

### BR1-02 — `minor` — The criticality event never has an empty side

**Problem.** § 5.5: *"Criticality: B → A (an empty side shows 'inherited')"*.
S002 writes the literal text `inherit` for a NULL own grade
(`equipment_core.INHERIT = "inherit"`, used by `_display`; S002 § 6 Events
table). Neither side of a `criticality` event is ever empty. Only `created` has
an empty (NULL) old side.

**Why it matters.** `describeEvent` is specified against a shape the API does not
produce; the coder would either implement the empty-side rule (dead code) or
show the raw word "inherit".

**Fix.** `describeEvent` maps the value `inherit` → "Inherited" and the grades
as they are; `created` shows "Created" and ignores `old_value`. Add a test row
for `inherit → A` and `A → inherit`.

### BR1-03 — `minor` — `my-units` returns active units only; restate the filter rule and the cache

**Problem.** § 5.6 says inactive units are offered in the **filter** "because
old equipment may sit there". But:

- `_accessible_unit_ids` (which `my-units` reuses) returns the user's
  **active** unit ids only (S002 § 6; verified in `equipment.py`). A user
  without `read_all_units` therefore never receives an inactive unit id, so the
  filter cannot offer one to them.
- A unit can only be deactivated when it holds nothing but scrapped equipment
  (S002 § 4, user decision 2). So "old equipment in an inactive unit" is always
  scrapped, is visible only to `all_units` holders (S002 BR2-09), and only with
  *Show scrapped* ticked.

**Fix.** State the rule exactly: *the unit filter lists the user's active units;
for `all_units: true` users it lists every unit, inactive ones greyed, since a
deactivated unit may still hold scrapped equipment.* Also state the staleness
that `ensureMyUnits()` accepts: after IT admin changes a user's unit access, the
open tab keeps its cached list until reload; a save at a unit just revoked
gets the API's 403 beside the field, which is the designed safety net.

### BR1-04 — `minor` — Standards: two citations overstate or mis-number

**EN 13306.** § 2 says the status dialog "offers only the four use statuses" and
§ 4.5 gives "a short help line per status, from EN 13306". EN 13306 (the
European maintenance-terminology standard) distinguishes an item's *condition*
— **up state** (can perform its function) and **down state** (cannot) — and,
within up, the *use*: **operating**, **idle** and **standby**. Only three of
Yantra's four statuses map: `in_service` (operating or idle), `standby`
(standby), and `scrapped` is end of life (ISO 55000's *dispose* stage). S002
§ 2 explicitly says `out_of_use` "has no EN 13306 term: it is a life-cycle
status". S003 should say the same rather than attribute all four to EN 13306.
The help lines themselves are good; label the last two as Yantra's life-cycle
statuses.

**ISO 55001 (2014 numbering, as S001 and S002 cite it).** § 2 says "§ 7.5
(documented information)". In the 2014 edition **§ 7.5 is *Information
requirements*** (what information the organisation needs about its assets) and
**§ 7.6 is *Documented information*** (how it is controlled). S001 cites
"§ 7.5–7.6" and S002 the same. Cite § 7.6, or § 7.5–7.6 as the earlier briefs
do. § 8.2 *Management of change* is right: changes to assets are assessed and
recorded, and the event history is that record.

The other claims are correct: ISO 14224 levels 6–8 for equipment,
component-unit and component; TPM's planned-maintenance pillar starting with an
A/B/C ranking; ISO 27001:2022 A.5.15 (access control) and A.8.3 (information
access restriction) for showing only the user's units.

### BR1-05 — `minor` — `useFormModal` is under-specified for the equipment dialogs

**Problem.** § 5.7 names the parameters (`path`, `blank`, `fromRecord`,
`afterSave(result)`) but leaves three things the coder would have to decide:

1. **Seeding a create.** Today `openCreate()` takes no argument and `blank()` is
   a closure. The create-part dialog needs the parent (`parent_id`, and the
   parent's level to limit the Level choice) at open time. Say
   `openCreate(seed)` passes `seed` to `blank(seed)`, or the view sets a ref
   before opening. The first is cleaner and keeps `blank` pure.
2. **The response.** Today `save()` discards the API response. "After a create,
   the app opens the new node's page" (§ 4.3) needs the 201 body, so `save()`
   must pass it to `afterSave(result)`. Say so; it is the reason the hook exists.
3. **What stays in the wrapper.** `changeActive` is named, but `editingActive`,
   `editingLabel` and `confirmingDeactivate` are masters-only state too.
   `editingLabel = record.full_code ?? record.code` happens to work for
   equipment (the scrap confirmation names the code), so it can stay generic.
   List which refs move and which stay, so the three panels' destructuring
   lines (`SitesPanel`, `UnitsPanel`, `EquipmentClassesPanel`) keep working
   unchanged.

Also, § 3 and § 5.7 say "the four masters panels" are untouched. Only three use
`useMasterForm`; `UserUnitsPanel.vue` has its own modal logic. Harmless, but say
three.

### BR1-06 — `minor` — URL-query filters: four rules the coder would otherwise decide alone

§ 4.1 puts the filters in the URL for Back and bookmarks, which is right. The
following are not stated:

1. **`router.replace`, not `push`, for filter and search changes.** Otherwise
   every debounced keystroke and every filter click becomes a history entry,
   and Back from the equipment page walks through them. One list visit = one
   history entry; Back from `/equipment/<id>` then returns to the filtered
   page as intended.
2. **Defaults are absent from the URL** (`level=equipment`, `page=1`,
   `include_scrapped` off), so `/equipment` and a bookmark of the default view
   are the same URL.
3. **Clearing the search.** "Typing a search switches level to All" — when the
   search is cleared again, does the level return to Equipment? Either answer
   is fine; say which. Simplest: switch only on the transition empty → non-empty
   while the level is Equipment, and never switch back automatically.
4. **Status = Scrapped without *Show scrapped*.** The API adds
   `status <> 'scrapped'` unless `include_scrapped=1` (verified in
   `list_equipment`), so that combination always returns an empty page. Either
   send `include_scrapped=1` whenever the status filter is Scrapped, or offer
   Scrapped in the status filter only when *Show scrapped* is ticked. The
   second keeps one control meaning one thing.

And one small one: when the site filter changes, clear a unit filter that is not
in that site.

### BR1-07 — `minor` — Status dialog: Save versus the inline Yes/No

**Problem.** § 4.5: choosing Scrapped shows "Scrap VBM001? … Yes/No" *before
saving*. `FormModal.vue` always renders a Save submit button in the footer. With
Scrapped chosen, there would be two ways to submit (Yes, and Save) unless the
brief says otherwise.

**Options.**
- (a) When Scrapped is selected, the Save button is disabled with
  `title="Confirm with Yes below"` (the base's "never leave a disabled submit
  button silent" rule) and Yes performs the save.
- (b) `FormModal` gains a `hideSave` prop; the status dialog hides Save while
  Scrapped is selected and the Yes/No row is the only way through.
- (c) Save is the only submit; choosing Scrapped only shows a warning text.

**Recommendation.** (a) or (b); (c) loses the deliberate confirmation the brief
wants. Say also whether the Yes/No row is inline markup in
`EquipmentStatusModal.vue` or a small shared component. Inline is fine — it is
three lines — as long as `ActiveToggle.vue` is not copy-pasted.

### BR1-08 — `minor` — Sidebar active state, and the navigation test lists

1. `AppSidebar.vue` and `AppBottomNav.vue` mark the active item with
   `route.path === item.path`. On `/equipment/5` the Equipment icon will not be
   highlighted. Say that both use a prefix match (`route.path === item.path ||
   route.path.startsWith(item.path + "/")`), or that routes carry
   `meta.nav: "equipment"` and the components compare that. The first is a
   two-line change in each file.
2. `navigation.test.js` keeps per-role permission lists that "match
   `config_rbac`" (S001 § 8). The brief says the lists "gain `equipment:read`".
   `test_rbac.py`'s matrix now also gives `equipment:read_all_units` to the
   manager and IT admin. Say the lists are updated to the matrix in full, not
   just by one key, so the two tests cannot drift.

### BR1-09 — `minor` — Error and loading states beyond the 404

§ 4.2 names the 404 message. The base's view structure asks for a loading state
and a dismissible error alert for everything else. Say, for the list and the
equipment page: a spinner/“Loading…” while fetching (as the panels do); for any
non-404 error (network, 503 while the DB is unavailable — CLAUDE.md says the app
must serve while the DB is down) an alert with the message and a Retry; and on
the equipment page, 404 only for `err.status === 404`. The move dialog may also
receive a 400 (`parent_id` level rule) if the search list is ever stale; show it
beside the field like the 403/409.

### BR1-10 — `nit` — Reuse the existing date formatter; keep the pure helpers free of `api.js`

- § 4.2 "Dates as DD-MM-YYYY HH:mm": `utils/datetime.js` already has
  `formatDateTime()` for exactly the ISO+05:30 strings `row_to_dict` emits. Name
  it, so the coder does not write a second one.
- § 3 puts `describeEvent` and the label maps in `stores/equipment.js`, which
  also holds `ensureMyUnits()` and therefore imports `api.js` →
  `stores/auth.js` → `keycloak-js`. No existing vitest test imports a module on
  that chain (`appVersion.js` and `navigation.js` import only Vue). It will
  probably load under jsdom, but the brief can remove the doubt by putting the
  pure helpers in `utils/equipmentLabels.js` (matching the test name it already
  chose) and keeping the cache in the store.

### BR1-11 — `nit` — Small picker rules

- **Create equipment:** "default site preselected (S001 A1)" implies a Site
  field and a Unit field narrowed to it (A1.1 preselects *site* pick-one fields).
  Say so, or say it is one unit select grouped by site. Either way, when the
  user has exactly one unit, preselect it.
- **Move equipment:** the current unit should be shown as current and not
  selectable; a PUT with the same `unit_id` is silently dropped by the API
  (`clean[field] == locked[field]`) and writes no event, so Save would appear
  to do nothing.
- **Move a component-unit:** send `level=equipment` to the search rather than
  `level=all` filtered in the browser; with ~500 machines plus parts, a
  50-row page of mixed levels may hold few valid targets. For a component,
  `level=all` with client-side filtering is unavoidable and fine.
- Require a non-empty search before listing targets (the empty query returns
  the first 50 of everything).

### BR1-12 — `nit` — Pager edge cases

"Page 1 of 4 (183)": say what shows at `total = 0` ("No equipment …" only, no
pager) and that pages = `ceil(total / per_page)`. The API returns an empty page
with the true total for a `page` past the end (S002 § 7); say the pager then
offers Prev rather than looping.

---

## Checked and found consistent

- **S002 API contract.** The list row fields (`id, code, level, name, class_id,
  class_code, unit_id, unit, full_path, effective_criticality, status,
  part_count`), paging (`page`, `per_page` default 50, max 200), the filters and
  `level=all`, the detail's `ancestors` / `children` (two levels, scrapped
  included, each with `status`) / `events` (newest first) all match
  `equipment.py` as it stands. Breadcrumbs can be built from `unit`
  (`SITE.UNIT`) plus `ancestors`.
- **Writes.** Edit sending back the current `class_id` is not a
  reclassification (dropped in `update_equipment`); Move sending only `unit_id`
  or `parent_id`, and Change status sending only `status`, are exactly the PUT
  shapes S002 accepts. Create with `status` other than scrapped; `scrapped` on
  create → 400 as the dialog assumes by not offering it. Empty optional text
  sent as `null` is accepted (and `""` would be too — `optional_text_parser`
  turns it into NULL — so the rule is harmless either way).
- **Level choices in Add part** match `check_parent`: component-unit under
  equipment only; component under equipment or component-unit.
- **Permissions.** `equipment:read = ("*",)`, `equipment:edit = (engineer,
  it_admin)` with the manager inheriting through `ROLE_INCLUDES`; the frontend
  check `userPermissions.includes("equipment:edit")` follows the panels'
  pattern; admin receives every key from `/api/auth/me`, so the check holds
  for admin too. `my-units` under `equipment:read` and `read_all_units` not
  used by the frontend are right.
- **Routing.** `canOpenRoute` lets `equipment-detail` through because it is not
  a nav item; the redirect via `landingPath(...) ?? "/equipment"` is the S002
  handover's wording and works before login (`landingPath([])` is null →
  `/equipment`, which every role may open). `GET /my-units` cannot collide with
  `GET /<int:node_id>`.
- **Breaking tests** are named correctly: the three `navigation.test.js` tests
  ("maint_operator sees Masters only", "manager and IT admin see Masters and
  Settings", "everyone … lands on Masters"). No backend test breaks.
- **Scope and size.** Out-of-scope list matches Plan.MD (QR, documents, tickets,
  readings, import, export). The components are proportionate: two badges, a
  pager, five equipment components, one composable generalised rather than
  copied (DRY). "No Add part from the list" and "default level Equipment" are
  reasonable assumptions, correctly flagged for the user.
- **Thin frontend.** Every rule is left to S002 and refusals are shown from
  `{error, field}` as in Masters; the only client-side logic is offering
  sensible choices (active classes, the user's units, valid parent levels).
- **Base patterns.** Server-side pagination with total, filters above the table
  resetting to page 1, modals for create/edit, a dedicated route for the
  equipment page, cached domain store (`ensureMyUnits`), empty states, IST
  timestamps as DD-MM-YYYY HH:MM. The path breadcrumb on the equipment page is
  content, not app navigation, so the base's "no breadcrumbs deeper than one
  level" (a topbar rule) is not contradicted.
- **Plan.MD.** Desktop "equipment register and tree" (§ 6) is what this builds;
  the phone equipment page with tickets/readings/CIL stays for later, as the
  brief says. The planner's note for Plan § 6 at approval is listed.
- **Header block and README index** follow `docs/steps/README.md`.
