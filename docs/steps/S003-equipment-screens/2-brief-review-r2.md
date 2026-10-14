```
Step: S003 — Equipment register screens
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 14-10-2026
```

# S003 — Brief review, round 2

**Verdict: no `blocker` or `major` finding is open.** Four `minor` and four `nit`
findings, all small spec gaps the revisions left or introduced.

What was checked: the revised brief against round 1 (every `Accepted` answer
verified in the brief text, not only in the Review log); S002's brief (§ 5–7,
Handover appendix) and S002's `3-impl-report.md` (its departures win);
the S002 code in the working tree (`backend/equipment.py`, `equipment_core.py`,
`api_common.py`, `config_rbac.py`, `auth_utils.py`, `tests/conftest.py`,
`tests/test_equipment_api.py`, `tests/test_rbac.py`); S001 A1; Plan.MD § 4.1
and § 6; Maintenance-Philosophy § 9; the base's *Frontend Design*, *Sidebar
visibility*, *API Response Conventions* and *Frontend API Helper* sections; and
the frontend as it is (`router/index.js`, `App.vue`, `stores/navigation.js`,
`stores/masters.js`, `api.js`, `utils/datetime.js`, `AppSidebar.vue`,
`AppBottomNav.vue`, `AppTopbar.vue`, `MastersView.vue`, `FormModal.vue`,
`ActiveToggle.vue`, `views/masters/useMasterForm.js`, the three panels that use
it, `UserUnitsPanel.vue`, `tests/navigation.test.js`, `vite.config.js`).

---

## Round-1 findings: verified in the brief text

| Finding | Where it now stands in the brief | Verified |
|---|---|---|
| BR1-01 `root_criticality` | § 1, § 3 Backend, § 5.8, § 8 Backend, § 9.1; `_detail` builds from the node row, which already carries `root_criticality` (`_NODE_COLUMNS`), so "one line in `_detail`" is right | yes |
| BR1-02 `inherit` → "Inherited"; `created` ignores `old_value` | § 5.5 table and text; § 8 Frontend tests | yes |
| BR1-03 active units only; cache staleness | § 5.6 "Which units each picker offers" and "The cache is per tab" | yes |
| BR1-04 EN 13306 / ISO 55001 citations | § 2 (EN 13306 mapped; `out_of_use`, `scrapped` as Yantra life-cycle statuses; ISO 55001 § 7.5–7.6, 2014 numbering); § 4.5 help lines labelled | yes |
| BR1-05 `useFormModal` | § 5.7: `openCreate(seed)` → `blank(seed)`, `afterSave(result)` gets the response, the refs that stay in the wrapper; § 3 says "three panels" | yes (one gap left, BR2-03) |
| BR1-06 URL-query rules | § 4.1: `router.replace`, defaults left out, empty → non-empty only, Scrapped only with "Show scrapped", site change clears a foreign unit | yes (one gap left, BR2-01) |
| BR1-07 Save vs Yes/No | § 3 `FormModal` `saveDisabledReason`; § 4.5; § 6 decision row | yes |
| BR1-08 prefix match; test lists in full | § 3 Frontend (both layout files) and § 3 Tests | yes |
| BR1-09 loading / error / 404 | § 4.1, § 4.2 (`err.status === 404` only), § 4.4 (400 beside the field) | yes |
| BR1-10 `formatDateTime()`; helpers in `utils/` | § 3 and § 4.2 | yes in § 3/§ 4.2; the § 6 table still says "one store" (BR2-05) |
| BR1-11 picker rules | § 4.3 (site + unit, single unit preselected), § 4.4 (current unit not pickable; `level=equipment`; no list before a search) | yes |
| BR1-12 pager edge cases | § 4.1 page-size paragraph | yes |

---

## Findings

### BR2-01 — `minor` — Status = Scrapped can still reach the API without `include_scrapped`

**Problem.** § 4.1 now offers *Scrapped* in the status filter only while "Show
scrapped" is ticked (BR1-06). Two paths still produce the always-empty page that
rule was meant to remove:

1. the user picks Status = Scrapped, then **unticks** "Show scrapped": the
   status stays `scrapped`, the option it was chosen from disappears, and the
   request goes out as `status=scrapped` without `include_scrapped=1`. The API
   adds `e.status <> 'scrapped'` (`list_equipment`, verified), so the page is
   empty for no visible reason;
2. a bookmarked or hand-edited URL `?status=scrapped` without
   `include_scrapped=1` (the filters live in the URL, so this is a supported
   entry point).

**Why it matters.** It is exactly the silent empty page BR1-06 was about, now
reachable only through the two paths the brief does not cover; the coder would
have to invent the rule.

**Options.**
- (a) Two lines in § 4.1: *unticking "Show scrapped" while Status is Scrapped
  clears the status filter; on reading the URL, `status=scrapped` without
  `include_scrapped=1` ticks "Show scrapped" (the URL is normalised with
  `router.replace`).*
- (b) Send `include_scrapped=1` whenever the status filter is Scrapped (the
  S002 impl report's decision 9 suggests this), and keep "Show scrapped" for
  the other statuses only.

**Recommendation.** (a); it keeps the "one control, one meaning" choice of
round 1 and closes both paths.

### BR2-02 — `minor` — The equipment page must reload when only `:id` changes

**Problem.** Several of the brief's own flows navigate from `/equipment/<a>` to
`/equipment/<b>`: Add part → "the app opens the new node's page" (§ 4.3), the
breadcrumb links to ancestors (§ 4.2), and the parts-tree rows (§ 4.2). Vue
Router **reuses** the mounted `EquipmentDetailView` instance when only the
param changes, so an `onMounted` fetch runs once and the page keeps showing
node *a* under URL *b*. The brief says nothing about it.

**Why it matters.** This is the standard detail-page trap; the first manual check
in § 8 (add `VBM001`, then a drive, then a motor under it) walks straight into
it. Left unsaid, the coder would discover it in the browser or not at all.

**Fix.** One sentence in § 4.2: *the view loads on `route.params.id` with
`watch(..., { immediate: true })`, not only on mount; a change of id resets the
page to "Loading…" first.* Say also that a dialog open in the view is closed
before the navigation (see BR2-03 for the order).

### BR2-03 — `minor` — `useFormModal`: who closes the modal, and errors on fields with no input

Two things § 5.7 still leaves to the coder:

1. **Close order.** Today `finish()` in `useMasterForm` closes the modal, then
   resets the masters cache, then reloads. § 5.7 moves the masters-specific part
   into the wrapper's `afterSave` but does not say whether the generic
   `save()` closes the modal before calling `afterSave(result)`. It should
   (close, then `afterSave`), because the equipment `afterSave` navigates
   (BR2-02) and the Bootstrap backdrop must be gone first. One line.
2. **Field errors on read-only fields.** `modalError` shows a refusal at the top
   of the dialog only when `error.field` is **not** a key of `form`. The
   create-part dialog carries `parent_id` and `level` in the form (they are
   sent, § 5.3) but shows them read-only, with no input and therefore no
   `invalid-feedback` slot. A 403 "You have no access to the parent's unit", a
   409 "The parent is scrapped" or a 400 level-rule refusal, all with
   `field: parent_id` (verified in `_load_target_node`), would then be shown
   **nowhere**. The same holds for `unit_id` on Move-equipment if the unit is
   rendered as a list rather than a select, and for `status` on the status
   dialog if the choice is radio buttons.

**Why it matters.** CLAUDE-COMMON: never silently swallow an error. These are the
refusals the brief itself lists in § 4.4 and § 4.5 as "shown beside the field".

**Fix.** Add to § 5.1 or § 5.7: *every field the form sends has a place to show
`fieldError(name)`, including read-only ones (the Parent, Level and Unit rows
of the create-part and edit dialogs render it under the value).* That keeps
`modalError`'s rule unchanged.

### BR2-04 — `minor` — Site pick-lists are not defined; "greyed" options in a `<select>`

§ 4.1 (filter) and § 4.3 (create) define the **unit** lists per kind of user
(§ 5.6) but not the **site** lists they are narrowed by:

- an engineer whose units are all at `SMTW` would see `BRICKS` and `SSVT` in
  the site filter and get an empty page on picking them, which contradicts
  § 2's "users aren't offered choices that would be refused" in spirit;
- § 4.3 preselects the default site (S001 A1) *and* the single unit when the
  user has one. If that unit is not at the default site, the two rules
  conflict. Say the single unit wins and its site is preselected.
- § 5.6 says inactive units are "greyed" in the filter for `all_units` users.
  An `<option>` cannot reliably be styled across browsers, and `disabled`
  would make it unpickable, the opposite of the intent. Use a text marker,
  "(inactive)", as `UserUnitsPanel` leaves inactive units pickable by listing
  them plainly.

**Fix.** Two sentences: *the site filter and the create dialog's Site field list
the sites that hold at least one unit in that picker's unit list (derived from
the unit list, no extra call); a user with exactly one unit gets that unit and
its site preselected, which overrides the default site; inactive units in the
`all_units` filter carry an "(inactive)" suffix.*

### BR2-05 — `nit` — The § 6 decision table still says "Labels and badge colours in one store"

BR1-10 moved the label maps and `describeEvent` to `utils/equipmentLabels.js`
(§ 3, § 4.2, § 5.4 agree). The decision row's wording is the only leftover.
Change it to "in one pure module (`utils/equipmentLabels.js`)".

### BR2-06 — `nit` — `my-units` is a new caller of `_accessible_unit_ids`

S002 § 6 and the comment at `equipment.py` line 175 ("only these helpers and
the list touch `_accessible_unit_ids`") state an invariant that the code
reviewer will check. `my-units` is a legitimate new reader of the same rule,
not a new rule, but the brief should say the comment is updated to name it, so
the S003 code review does not flag it as a departure. The endpoint shape is
straightforward: `{all_units: ids is None, unit_ids: sorted(ids) if ids else []}`.

### BR2-07 — `nit` — Search trimming; the row link

- The API strips `q`. Say the list trims it too before the empty → non-empty
  test in § 4.1, so a space-only search neither switches the level nor
  appears in the URL.
- "A row click opens the equipment page" (§ 4.1): make the code cell a
  `<router-link>` so middle-click / open-in-new-tab work, with the row click
  as the convenience. It costs nothing and the brief's own § 6 reason for the
  dedicated route is "it can be linked".

### BR2-08 — `nit` — Status dialog: the no-change case

With the dialog opened at the current status, Save sends `{status: <same>}`;
the API accepts it, writes no event (`tracked_changes` sees no change) and
returns 200, so the dialog closes and nothing happens. Either say that is
acceptable, or disable Save with `saveDisabledReason = "No change"` while the
choice equals the current status. The latter reuses the prop BR1-07 added and
is one computed.

---

## Standards: checked and correct

For the project owner, what each cited standard says and how § 2 now uses it:

- **ISO 14224** (reliability and maintenance data collection for the petroleum
  and process industries, widely used as the generic equipment taxonomy) defines
  a nine-level hierarchy. Levels 6–8 are *equipment unit*, *subunit* and
  *maintainable item*; the brief maps them to equipment, component-unit and
  component, as Plan § 4.1 does. Correct.
- **EN 13306** (maintenance terminology) separates an item's *state* — up (able
  to perform) or down (unable) — from how it is used while up: *operating*,
  *idle* or *standby*. § 2 now maps `in_service` to operating/idle and
  `standby` to standby, calls `out_of_use` and `scrapped` Yantra life-cycle
  statuses, and says "down" will come from breakdowns, never typed by hand.
  Correct, and consistent with S002 § 2.
- **ISO 55001:2014** (asset management system requirements): § 7.5
  *Information requirements* and § 7.6 *Documented information* ask that the
  organisation decides what it needs to know about its assets and controls
  that information; § 8.2 *Management of change* asks that changes to assets
  are assessed and recorded. The event history and "no delete" follow this.
  Citation now matches S001 and S002.
- **ISO 55000** *dispose* stage for `scrapped`: correct use of the life-cycle
  vocabulary (acquire, operate, maintain, dispose).
- **TPM planned-maintenance pillar**: starts by ranking equipment A/B/C so
  effort goes to the critical machines; the badge and the "inherited" marker
  follow it, and Philosophy § 9 gives the VEL meaning of each grade. Correct.
- **ISO 27001:2022** A.5.15 (access control) and A.8.3 (information access
  restriction): users are offered only the units they may work at; the server
  (S002) enforces it and the screens follow. Correct.

---

## Checked and found consistent

- **Round 1 is in the text.** All twelve findings verified above; the one
  residual is the § 6 wording (BR2-05).
- **S002 as delivered.** The brief builds on the impl report, not only the
  brief: `unit_id`/`unit` as the root's for parts (decision 6) is what § 4.1's
  unit column and § 4.2's "the unit (equipment only)" assume; the target-unit
  order 400 → 409 → 403 (decision 4) does not matter to a dialog that offers
  active, accessible units only; `status=scrapped` hiding (decision 9) is
  handled by § 4.1 (and BR2-01); `_load_target_node(cur, id, child_level)`
  gives the 400/403/409 with `field: parent_id` that § 4.4 shows.
- **`root_criticality`.** `_ROOT_CRITICALITY` is a CASE on the root row, so for a
  component under a graded component-unit it is the equipment's grade, exactly
  the § 5.8 example; for equipment it equals its own grade. The § 8 tests
  (`B` under `A`-graded component-unit; equipment returns its own) can be
  written with `make_equipment(parent=…, criticality="A")`. `root_criticality`
  comes through `row_to_dict(node)` already used in `_detail`.
- **`my-units`.** `GET /my-units` under `require_perm("equipment:read")` cannot
  collide with `GET /<int:node_id>`; the § 8 cases map onto existing fixtures
  (`user_with_units(role, units)`, `role_client(role, uniq.username())`, the
  parametrised senior-roles test). `all_units` for admin holds because
  `has_perm` bypasses for the `admin` role.
- **Permissions and nav.** `equipment:read = ("*",)`, so Equipment is visible to
  every role and the landing redirect `landingPath(...) ?? "/equipment"` is
  valid before login (`[]` → null → `/equipment`) and after it. `equipment:edit`
  reaches the manager through `ROLE_INCLUDES`, and admin receives every key from
  `/api/auth/me` (`compute_permissions(["admin"]) == set(PERMISSIONS)`), so the
  frontend `includes("equipment:edit")` check holds for all editors. The
  `test_rbac.py` matrix the navigation test lists must match: operator /
  technician / storekeeper `{equipment:read, masters:read}`; engineer adds
  `equipment:edit`; manager adds `equipment:read_all_units`, `settings:read`;
  IT admin the full eight.
- **Breaking tests** are the three named in § 3; the other three navigation
  tests and the backend suite are untouched.
- **Forms send only what they own** (§ 5.3) matches `update_equipment`: an
  unchanged `class_id` is dropped, so Edit cannot reclassify by accident; Move
  sends one of `unit_id` / `parent_id`; a part's `criticality: null`
  re-inherits (`_parse_criticality`); equipment's `null` is a 400 the dialog
  can't produce because it offers A/B/C only.
- **Level choices in Add part** match `_ALLOWED_PARENTS`; Add part hidden on a
  component matches "component has no parts". Move target searches
  (`level=equipment` for a component-unit; `level=all` filtered to equipment
  and component-units for a component) match the same table; scrapped targets
  are already absent from the search because `include_scrapped` is off.
- **Scrap confirmation** reuses the inline Yes/No shape, Save disabled through
  `saveDisabledReason` bound to `title` — the base's "never leave a disabled
  submit button silent" rule, and the prop name the base itself suggests.
- **Dates and labels.** `formatDateTime()` handles the `+05:30` ISO strings
  `row_to_dict` emits; `utils/equipmentLabels.js` imports nothing from
  `api.js`, so `equipmentLabels.test.js` loads under jsdom like
  `datetime.test.js` does.
- **Base patterns.** Server-side paging with the total; filters above the table
  resetting to page 1; modals for create/edit on the list; a dedicated route for
  the detail page; cached domain store (`ensureMyUnits`) next to
  `ensureUnits`; loading, error and empty states; IST `DD-MM-YYYY HH:MM`;
  sidebar most-used-first (Equipment before Masters). The in-page path
  breadcrumb is content, not topbar navigation.
- **Plan.MD and Philosophy.** Desktop "equipment register and tree" (Plan § 6)
  is this step; phone QR/home pages are correctly out of scope; the four
  statuses, A/B/C with inheritance, "scrapped is final and read-only" and
  "only equipment has a unit" match Plan § 4.1 and Philosophy § 9.
- **Scope and size.** Two small backend additions, both put to the user (§ 9.1);
  no S002 API change otherwise; no over-engineering (two badges, a pager, five
  equipment components, one composable generalised).
- **Header block** follows `docs/steps/README.md`; the index row reads
  "In review — r2".
