```
Step: S064 — Floor UX fixes
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 28-10-2026
```

Reviewed against: 0e4d215

**Verdict: no `blocker` or `major` finding is open.** 4 `minor`, 4 nits. Round 2 re-read only the sections the Review log names, by `git diff --no-index -w scratch/S064-brief-r1.md …/1-brief.md`: § 1 (A, B, C, D, E, F, G, H), Out of scope, § 2, § 3, § 5.1.3, § 5.2.1, § 5.3, § 5.4.2–5.4.3, § 5.5, § 5.6, § 5.7 rows 2, 3, 7, 9, 17, 18, 20, § 5.8.1, § 5.9, § 5.10.4, § 6, § 7 (D6, D11, D12), § 8.1, § 8.3, § 8.4 tests 1, 3, 21, 22. Every round-1 finding marked `Accepted` is in the brief's text, not only in the log (checked one by one against the diff). Facts file `scratch/brief-facts-S064.md` used; `openFilters`, `displayRoleLabel`, `isCameraName`, `CRITICALITY_OPTIONS` and the constants are rightly "not found" (new names).

Baseline note: the orchestrator's prompt said `c9142b4 + uncommitted S063`, but S063 is committed as `0e4d215` (`git log -1`); the working tree holds only step docs (`INDEX.md`, S063's brief, this folder). The brief's `Baseline:` line should read `0e4d215` at approval.

The four `minor` findings are about the two places where the new text leaves a rule to the coder: the test list of § 8.3 for the equipment list on the phone (two findings), the flex column of § 5.3.3, and the shape of the new `assignable_site_ids` field for a viewer who is not an editor.

---

## Minor

### BR2-01 — minor — § 8.3 misses about fourteen more lines of `equipment.spec.js` that use controls folded into *Filters (n)* or the hidden table

**Problem.** § 8.3 group 1 lists `rowOf` and its uses, `:169, 174, 192, 876–884` for the selects, and `:745`. On the Pixel 7 these also break, and none is in the list or in the coder's grep words (*Print asset list*, `Select … for labels`, `Tickets`, `Category`, `Class`, `Logout`, `Let in`, `Equip `):

| Lines | What | Why it breaks |
|---|---|---|
| `:116–118` (S030 U1) | `thead th` *Lifecycle* `toBeVisible`; the *Lifecycle* combobox | the table is `d-none` below `md`; the select is inside the closed block |
| `:195` (the test at `:191–195`; § 8.3 says 190–194) | `combobox Tickets` `toHaveCount(0)` for a storekeeper | passes for the wrong reason while the block is closed — the same trap as `:745` |
| `:718`, `:725` | `combobox Level` `toHaveValue` | inside the closed block |
| `:719, 771, 797, 812, 858` | `openPropertyFilter(page)` with its default opener `filterButton` (`:681`, *Filter by property* / *Properties (n)*) | the property-filter button is inside the block (§ 5.3.4) |
| `:731, 736, 781` | `filterButton(page)` `toHaveText` | same |
| `asset-list.spec.js:81, 101` | `tbody tr` on `/equipment` | they are in the tests that go desktop-only with `:86, 105` (D12); say so, or the coder wonders |

`:747` and `:783` open the dialog from the applied-filter line, which stays visible (§ 5.3.4): fine.

**Why it matters.** The coder's whole-suite run goes red in the S030 and S062 tests, and the brief's list claims to be the list ("twenty-odd lines … listed"); a `toHaveCount(0)` that passes with the block closed hides a regression.

**Options.**
- a) **Recommended.** Add the lines to group 1. Make `openPropertyFilter` (`:695`) call `openFilters(page)` once before `opener.click()` when the opener is `filterButton` (one place, eight tests fixed), and call `openFilters` before `:118, 195, 718, 725, 731, 736, 781`. The S030 header check (`:116`) asserts the table header at `md` and up and the card's lifecycle badge below (or becomes desktop-only `@device`: it is a wording check, so keep it on the phone with the badge). Add `Filter by property`, `Properties (`, `Level`, `Lifecycle`, `thead` to the coder's grep words. Correct 190–194 to 191–195.
- b) Keep the list as it is and rely on the red run. Not recommended: the brief promised the list, and `:195` would never go red.

### BR2-02 — minor — two adaptations in § 8.3 do not fit the test's device or purpose

**Problem.**
1. Group 1: "The S029 `@device` fit test (`:178-189`) asserts that *Filters (n)* and a row's bulb fit." The test is `@device`, so at the Normal level it also runs on `desktop-chromium` (768 px and up), where there is no *Filters (n)*: the selects show directly. As written the desktop run fails on `getByRole("button", { name: /Filters/ })`.
2. Group 2 sends `asset-list.spec.js:57` to desktop only. That line is in the @page-rule test (`:45–60`: "Leaving the page takes its A4 @page rule away"); the *Print asset list* assertion there only waits for `/equipment` to render before counting `<style>` tags. Making the whole test desktop-only takes the asset-list print page's phone checks (Include parts, Checklist columns, print media) off the logic device for no reason.

**Options.**
- a) **Recommended.** (1) The fit test branches on `page.viewportSize().width < 768`: below `md` it measures *Filters (n)*, at `md` and up the *Tickets* select as today; the bulb in both. (2) `asset-list.spec.js:57` asserts the *Search* box (as `screens.spec.js:34` will) and the test stays on the phone; group 2 keeps `:86, 105` (with `:81, 101`).
- b) Make the fit test skip on desktop (`test.skip(width >= 768)`). Loses today's desktop check of the *Tickets* select for nothing.

### BR2-03 — minor — § 5.3.3's flex column changes the desktop look it says is unchanged, and leaves two blocks without a rule

**Problem.** `d-flex flex-column` has `align-items: stretch`, so every child fills the width. The *Raise ticket* link is `router-link.btn.btn-danger.mb-3` (`EquipmentDetailView.vue:230`), today an inline-block button as wide as its text; in the column it becomes a full-width red bar on every width, desktop included. § 5.3.3 says "desktop keeps today's order", and the user approves the look from that line. Two more gaps: the *Scrapped — this record is read-only* alert (`:234`) is the `v-if` sibling of the button row (`:235`) and gets no `order`; and `DocumentsCards` (`order-1`) sits directly above the Details `.row.g-3` (`order-2`), whose `margin-top: -1rem` (`g-3`) eats the gap: Photos and Details touch on a phone.

**Why it matters.** The coder sees the stretched button in the first run and chooses alone: keep it (a look change the user did not see) or fix it (how?). The alert's slot and the spacing are small, but they are the kind of thing the brief exists to decide.

**Options.**
- a) **Recommended.** The *Raise ticket* link gets `align-self-stretch align-self-md-start`: a full-width 44 px-plus target on a phone (the floor's main action on this page; TPM: the operator's way in), today's size on desktop. Say it in § 5.3.3 and § 1 C. The Scrapped alert takes `order-0` with the button row. `DocumentsCards` takes `mb-3 mb-md-0` (its own `.row.g-3.mt-0` root keeps the inner gaps).
- b) `align-self-start` on the link everywhere: no look change at all, but the phone keeps a small button for the page's main action.
- c) Wrap only the blocks after the Open tickets card and leave the link and the button row outside the column. Fewer classes; the Open tickets card's `mb-3` and the column's start then need a look; the order rule in § 5.3.3 is rewritten.

### BR2-04 — minor — the new `assignable_site_ids` field: for whom it is sent, and how it is computed, are not stated

**Problem.** § 6 says "list of site ids, possibly empty" and § 8.1 "a viewer with no grant: empty". Two things the code decides differently today:
1. `_people_out` (`masters.py:1178-1187`) computes site data only `if viewer.editor` (`people:edit`); for a floor role the per-person `sites` and `assignable_site_ids` are **absent**, and `test_site_roles_api.py:471-473` (`test_floor_roles_see_no_sites`) asserts that. A top-level field sent to every `masters:read` caller as `[]` would run one sites query plus `has_perm_at` per active site for operators who cannot open the Team dialog, and break the pattern the test guards.
2. `_SiteViewer.assignable_site_ids(person, present_site_ids)` (`:1131`) takes a person for `_is_own(person)` (`:1096`, reads `person["username"]`); "the same computation for a person with no rows" means passing a fake `{"username": None}`. The viewer is built inside `_people_out`; `list_people` (`:1231`) has no handle on it, so the coder either builds a second `_SiteViewer` (a second sites query) or changes `_people_out`'s return.

**Options.**
- a) **Recommended.** § 6: the field is sent only to holders of `people:edit`, as the per-person `sites` and `assignable_site_ids` are (absent otherwise). § 8.1's cases: IT admin every active site; an engineer their assigning sites; an engineer with no `people:assign_technicians` anywhere `[]`; a floor role: key absent. § 5.6.1: split the viewer's rule into `grantable_site_ids()` (active sites where IT admin, or `assigns_at`) used by both the per-person method (minus the present rows, `[]` for one's own record) and the list's field; `_people_out` returns the viewer with the items (or `list_people` builds the one viewer and passes it in). No fake person dict. The frontend reads the field only when `canEdit`.
- b) Send `[]` to everyone and compute it always. Simpler to write; the extra queries are small; the floor-role test's pattern is then half kept.

---

## Nits

- **BR2-05** (nit) § 5.6.2: `editingActive` (`useMasterForm.js:15`) is set only by `openEdit`; `openCreate` does not reset it. On the create → edit switch set it `true` too, else a stale `false` from an earlier edit of an inactive person shows *Reactivate* for the new, active person. A `switchToEdit(record)` in `useMasterForm` (sets `editingId`, `editingLabel`, `editingActive`, leaves the form) keeps the four refs in one place.
- **BR2-06** (nit) § 8.4.22: say how the test forces a row failure against the real server (the S024 convention: no stubbed response): deactivate the unit the row ticks through the API (admin) after the dialog opens and before Save, so `_check_grantable` refuses the `PUT` — which also asserts row 17's new text ("Unit … is inactive. Untick it or reactivate it.").
- **BR2-07** (nit) § 5.7 row 20: `_parse_optional_id` never says "is required" (`masters_core.py:148-156`: "{label} must be a record id"); drop it from the rule. `equipment_core` uses `_id_parser` (`:239-240`, `Parent`, `Unit`), not `_parse_id`, and its only required `*_id` is `model_id` (`PICK_A_MODEL`), so row 20 changes nothing there unless `:270` "Unit is required for equipment" is meant — say so (recommended: `:270` → "Choose a unit."; `:272` "Criticality is required for equipment" → "Choose a criticality grade."; `test_equipment_core.py` follows).
- **BR2-08** (nit) § 3 Tests and § 8.1: the `assignable_site_ids` tests live in `test_site_roles_api.py::TestVisibility` (`:431-473`), not `test_people_api.py`; put the new test there, one place for the rule.

---

## Checked and found consistent

- `_SiteViewer.assignable_site_ids` with an empty row set returns the active sites where the viewer is IT admin or `assigns_at(site)` (`masters.py:1131-1140`); `has_perm_at` (`auth_utils.py:435-444`) is the viewer's own grant. The site ids are already readable through `/api/masters/sites` (`masters:read`), so § 5.9's claim holds: the field leaks nothing.
- § 5.6.2 reads the code right: `toBody` sends `sites: []` on create with a login (`PeoplePanel.vue:163`); `save()` runs `saveRows` only on edit (`:227-228`); `_login_save_sites` requires `sites` with a login on POST (`masters.py:1216-1222`). Rows from `addSite` carry `editable: true` (`:114-116`), so `saveRows` sends them with `editing.value?.sites ?? []` as the original. `send` keeps the dialog open on a thrown row error with `field: "sites"` (`useFormModal.js:74-82`), and `refreshEditing` already sets `editing` to the new person (`:194-197`); the switch adds `editingId` and `editingLabel` (and `editingActive`, BR2-05). `rowError` shows on its row (`:433`).
- `--topbar-height` is used only by `AppTopbar.vue:45-46`; the bar is in normal flow (`position: relative`, `:73`); `.topbar-mobile`'s margins (`App.vue:121`) do not depend on it. 48 px needs no other layout edit. `App.vue:53,78` are the two `btn-sm` *Sign out* buttons.
- `PagerBar.vue:19,23` are `btn btn-sm btn-outline-secondary`, as § 5.3.5 assumes.
- Every key in `config_rbac.py` matches `/^[a-z_]+:[a-z_]+$/` (§ 5.5.5), including `equipment:purge_documents`, `people:assign_technicians`, `masters:read_senior`, `access_log:view`.
- `_parse_id` labels are *Site*, *Class*, *Manufacturer* (`masters_core.py:169,191,204,206`): "Choose a site / class / manufacturer." — no a/an problem. The missing-field branch (`:303`) gives "Class id is required" for the same fields.
- `test_errors.py:44` asserts the literal "Database unavailable — try again shortly"; `_db_unavailable` (`app.py:66`) formats the exception into the body. § 3 and § 8.1 cover both.
- `modal-fullscreen-sm-down` applies below 576 px (the Pixel 7 at 412 px); Bootstrap's `.modal-fullscreen .modal-body { overflow-y: auto }` — § 8.4.1's two assertions hold on `phone-chromium`.
- `test.skip(testInfo.project.name !== DESKTOP, …)` is the suite's existing form for a desktop-only `@device` test (`changelog.spec.js:15`, `notifications.spec.js:113`); § 8.3 group 2 can use it or the viewport width. `screens.spec.js:108` already skips by visibility.
- *Add equipment* stays beside the search box (§ 5.3.4), so `journeys.spec.js:63` and `equipment.spec.js:39,48,66,120,234` are unchanged. `journeys.spec.js` opens the list only for that button, and the equipment page by URL; it needs no change, so dropping `journeys` from the Docs map line (BR1-25) is right.
- `getByRole("row")` at `equipment.spec.js:24,34` and `journeys.spec.js:216,224` are Masters tables; `masters.spec.js:20` too. Untouched by UX-08.
- `stores/auth.js:84-86`: the 401 branch is separate; the other branch prefixes `err.message`. Row 7's fix is one line.
- ISO 9241-110:2020's seven principle names in § 2 are the standard's; WCAG 2.2 SC numbers and levels and ISO/IEC 27001:2022 Annex A 8.1 are right.
- D11 and § 2 name the departure from `SMTW-WebApp-Base.md:1273`; § 5.10.4 replaces the sentence. § 5.10.8 says "floor targets 44 px".
- New UI texts (scope B): "Save your changes first, or cancel them", "Saving changes access: … → …", "Your sign-in has expired. Sign out, then sign in again.", "Yantra cannot see your address. Save from a computer on the plant network.", "That unit no longer exists. Reload and try again.", "Enter a title" — each says what happened and what to do, no codes.

---

## Feedback

- hindrance: the prompt's baseline (`c9142b4 + uncommitted S063`) did not match the tree (`0e4d215` is S063's commit); `git rev-parse` and `git status` settled it in one call, but the brief's `Baseline:` carries the stale value too (1 check).
- idea: for a step that hides or folds controls, the orchestrator's grep of `frontend/e2e` should include every control the brief moves, not only the ones it hides — here `Filter by property`, `Level`, `Lifecycle`, `thead` found 14 more lines than § 8.3 lists (3 greps, 5 min).
- waste: the diff output (51 KB) exceeded the tool's inline limit and had to be read from the saved file; a `--stat` first and then per-section diffs would have cost less (1 extra read).
