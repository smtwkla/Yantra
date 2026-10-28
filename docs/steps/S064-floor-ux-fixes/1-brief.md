```
Step: S064 — Floor UX fixes
Doc: brief
Author: Orchestrator (Opus)
Date: 28-10-2026
Track: full
Baseline: 0e4d215 (S063 committed; brief review r2)
Status: Committed 33ce411 (28-10-2026); checks: 20 auto; important check pending: row 44 of device-checks.md (IT Admin); rows 45, 46 open — approved 28-10-2026 by KLA ("ok, start coding when the review is done"; Q1 a, Q2 a, Q3 recommended — taken as the recommended answers)
```

# S064 — Floor UX fixes

The UX audit of 20-10-2026 (`0-ux-audit.md` (this folder), 27 items UX-01…UX-27) was never taken up: its
suggested fix step "S023" became Telegram alerts. A re-check against the code on 28-10-2026
(`0-ux-audit-recheck.md` (this folder)) found **0 fixed, 3 partly fixed, 24 open**, and several items
made worse by later steps (more filters, more Masters sections, more bottom-bar items, more
Settings cards). KLA asked for **one step** that fixes all 27 (28-10-2026), and for the lasting
lessons to be written for `SMTW-WebApp-Base.md`, so later generated code follows them.

**Sequencing.** Coded after S063 is committed (it is: `0e4d215`): S063 changes `EquipmentView.vue` (a Category
select) and `MastersView.vue` (an "Equip Category" section), which UX-08 and UX-25 rework.

**Size.** About 40 production files and 20 test files: over the skill's 25-file mark. KLA chose
one step (28-10-2026); most changes are a few lines each. The split, if wanted at gate A: S064a
everything but UX-08 and UX-14/15/18; S064b the equipment list on a phone and the Team screen.

The audit's IDs are kept as the item IDs. "Audit" below means `0-ux-audit.md` (this folder); its file:line
references are from 20-10-2026, the ones in this brief from the working tree of 28-10-2026.

## 1. What will be built

**A. Dialogs (every dialog on `FormModal`)**
- **UX-01** — on a phone (below Bootstrap's `sm`, 576 px) every dialog uses the whole screen
  (`modal-fullscreen-sm-down`), as well as scrolling inside (S018). Header and footer stay put;
  the body scrolls.
- **UX-05** — when Save is disabled, the reason shows as a short line of text in the footer,
  left of Cancel, on every width. The `title` stays for desktop.
- **UX-16** — in a Masters edit dialog, *Deactivate* is disabled while the form has unsaved
  changes, with the visible reason "Save your changes first, or cancel them". *Reactivate*
  likewise (it also closes the dialog). The inline
  "Deactivate X? Yes / No" may wrap onto its own line in the footer.

**B. Top bar and navigation**
- **UX-02** — the top bar shows the signed-in person's name in dark text on every width, beside
  a **Sign out** button with icon and word, at least 44 px high; the top bar grows from 42 to
  48 px to hold it. The two *Sign out* buttons of the no-access and network-refused screens
  (`App.vue:53,78`) get the same size. No confirm. A deliberate departure from the base's
  Topbar rule (D11).
- **UX-12** — the *Masters* nav item shows only to holders of an edit key on masters data:
  `masters:edit`, `equipment:edit`, `people:edit` or `failure_codes:edit` (today: engineer,
  manager, IT admin, admin). Operators, technicians, supervisors and storekeepers no longer see
  it. Bottom-bar labels grow from 0.65 rem to 0.75 rem.
- **UX-22** — bottom-bar items become links a keyboard can reach (`<router-link>`).

**C. Equipment page and list**
- **UX-03** — a QR link `/e/<code>` that finds nothing says "**<code>** — not found, or not at
  your units. Ask your engineer if you should see it." with a large *Go to equipment list*
  button, instead of the generic "The address … doesn't exist in Yantra".
- **UX-07** — on the equipment page, *Print label* shows only to `equipment:edit` holders at the
  node's site, also on a scrapped node. On a phone, *Documents* and *Photos* come right after the *Open tickets* card,
  above Details, Properties, Meters, Notes and History. On wider screens the order is unchanged.
- **UX-08** — on a phone (below `md`, 768 px) the equipment list puts the search box first and
  full width; the selects and the property filter fold into one *Filters (n)* button that
  opens and closes them (n = filters set); the label ticks and the two print buttons are
  hidden; each row shows as a two-line card that links to the equipment page: the ticket
  light, code and name, then the lifecycle badge, criticality and unit (or path). Desktop
  keeps the table. Existing browser tests are adapted per § 8.3.
- **UX-23** — pager buttons at least 44 px high (not `btn-sm`).

**D. Documents and photos**
- **UX-09** — the photo viewer uses the whole screen on a phone; the photo is sized to the
  space left, so *Previous* / *Next* stay on screen; the title may wrap to two lines.
- **UX-10** — in each document row the title opens the PDF; *Download* is one labelled button;
  *Edit title* and *Remove* move into a "⋯" menu at the row's end, apart from Download.
- **UX-11** — the upload dialog loses its *Kind* radios: *Add photo* and *Add document*
  already pass the kind (`DocumentsCards.vue:253,325`), and the title names it. A camera file name (`IMG_…`, `PXL_…`, `image…`, digits only)
  leaves *Title* empty with the placeholder "What does the photo show?". The iPhone note
  (Most Compatible) shows only after the server refuses a HEIC file.

**E. Settings**
- **UX-04** — *Save* on Settings › Network first shows, inside the card: "Save these ranges? IT
  admin outside them will be refused within 5 minutes." with the ranges **added** and
  **removed** compared with the stored list, and *Yes, save* / *No*.
- **UX-17** — *Save* on Settings › Labels first shows "Labels printed from now on will open
  **<sample link>**. Save?" with *Yes, save* / *No*; the sample is the new address with the code
  `MCC2CMP001` (the audit's example; any fixed sample code).
- **UX-19** — the *Database* and *Background tasks* cards show only to `settings:edit` holders
  (IT admin, admin); their data is then not fetched for others. For a manager, *Removed
  documents* comes first on the page.
- **UX-27** — a task's last status reads Done / Failed / Waiting / Running.
- **UX-26** — the access log shows a role by its label (site roles as the Team dialog names
  them, and "IT admin", "Admin"), a refusal's permission key as "Needed: <key>", and the
  success badge "Allowed" instead of "Let in".

**F. Team and Masters**
- **UX-14** — the *Add person* dialog takes sites and roles at once (today: "Save the person
  first"). The sites it offers are the viewer's: the Team list's response gains one field,
  `assignable_site_ids` (§ 6). When a person has more than two site rows, each row folds to
  its one-line text with an *Edit* link that opens it.
- **UX-15** — removing a site row shows a yellow line above the footer: "Saving removes access:
  <row text>."; changing a row's role shows "Saving changes access: <old row text> → <new
  role>." (as the login warning does today). The ✕ becomes a labelled *Remove* button, spaced
  from the All-units switch.
- **UX-18** — the Team list gets a search box (name or login) and a site select in the card
  header, as the Units and Models panels have.
- **UX-25** — the Masters toolbar spells the sections out: *Categories*, *Classes*, *Types*
  (today "Equip Category", "Equip Class", "Equip Type"). No regrouping.

**G. Messages (UX-06, UX-13, UX-21)**
- **UX-06** — a dropped connection shows "No connection. Check Wi-Fi or mobile data and try
  again." instead of the browser's text ("Failed to fetch", "Load failed"). A 5xx reply without
  JSON shows "Yantra is not answering. Try again in a minute." instead of "Bad Gateway" or
  "HTTP 502".
- **UX-13** — the reachable messages of the audit's table (rows 1–18 and 20) are rewritten as
  § 5.7 lists. The database error is no longer in the 503 body, and both database-down 503s
  say the same thing (also audit 21-10-2026 [18] in the queued *Auth hardening*).
- **UX-21** — "You have no units assigned — ask IT admin for unit access." (four screens)
  becomes "No units are given to you yet. Ask your engineer or IT." from one constant.

**H. Nits**
- **UX-20** — criticality options (the form and the list's filter) read "A — critical",
  "B — important", "C — normal"; the badge carries the same words as its `title`; the form
  shows the grade's meaning under the select.
- **UX-24** — plain lifecycle help texts (§ 5.8) and "The code is given on Save and never
  changes."

**I. Lessons for `SMTW-WebApp-Base.md`**
- Ready-to-paste texts for the base's § Frontend Design (Form / Modal, Table / List, Topbar,
  Navigation) and § Frontend API Helper Pattern, in the impl report under `## For smtw-common`.
  KLA pastes them into `smtw-common` and syncs (as S058). § 5.10 lists the points.

### Out of scope
- No migration, no new endpoint, no new permission key, no change to who may call which API.
  One field is added to an existing response (§ 6, for UX-14). UX-12 and UX-19 change only
  what the screens show; `masters:read` stays `*` for the pick-lists.
- Swipe in the photo viewer (audit UX-09: "swipe can wait").
- Grouping Masters sections under one switch (UX-25's second idea).
- Preselecting the engineer's site in *Add person* (UX-14's second idea; Q2).
- Rewording the developer-only messages of the audit's rows 19 and 21–26 (D7).
- The real-device questions of the audit's "Needs a real phone" list that no item here
  changes (PDF in WhatsApp, native selects, the Raspberry Pi kiosk): rows in
  `docs/steps/device-checks.md` only where § 8.5 says.
- Editing `.claude/SMTW-WebApp-Base.md` in this repo: it is synced and would be overwritten (D9).

## 2. Standards and practice

- **ISO 9241-110:2020 (interaction principles)** — seven principles for screens: suitability
  for the user's tasks, self-descriptiveness, conformity with user expectations, learnability,
  controllability, use error robustness, user engagement. The ones this step applies:
  *self-descriptiveness* (the screen says why Save is off, what a role, grade or status means:
  UX-05, UX-20, UX-26, UX-27), *use error robustness* (a confirm before a setting that can lock
  people out or misprint every label: UX-04, UX-17; Deactivate cannot drop edits: UX-16),
  *conformity with user expectations* (a QR label that exists is never called non-existent:
  UX-03).
- **WCAG 2.2** — SC 2.5.8 *Target Size (Minimum)*, level AA: a target at least 24 × 24 CSS px;
  SC 2.5.5 *Target Size (Enhanced)*, level AAA: 44 × 44. Yantra aims at 44 px for the floor's
  main controls (gloves: Plant-Facts § 5) through one class `.tap-target` (`min-height: 44px`):
  Sign out, pager, document Download and "⋯", *Filters (n)*. Bootstrap's `btn` alone is 38 px.
  SC 2.1.1 *Keyboard* (UX-22). SC 3.3.1 *Error Identification* and 3.3.3 *Error Suggestion*:
  each message says what is wrong and what to do (UX-06, UX-13).
- **ISO/IEC 27001:2022 Annex A 8.1 (user endpoint devices)** — information on shared devices
  is protected; a clear Sign out on a kiosk keeps the next person from acting as the last
  (UX-02; Plan.MD § 3 *Shared-device login*: "the screen always shows who is logged in, with a
  large logout button").
- **Departure from `SMTW-WebApp-Base.md` § Topbar Design Principles** (line 1273: "logout as an
  icon button or small link, not a prominent button"): Yantra runs on shared devices, so Sign
  out is a labelled button (D11). The base text of § 5.10 replaces that sentence.
- **TPM, autonomous maintenance** — operators take part only if the tool is easy on the floor:
  the QR page (UX-03, UX-07) and the phone list (UX-08) are the operator's way in.
- **CLAUDE-COMMON § Writing style, scope B** — error messages say what happened, why, what to
  do; buttons start with a verb; one word for one thing ("Sign out" everywhere, not "Logout").

## 3. Where

### Frontend
| File | Items | Change |
|---|---|---|
| `frontend/src/components/FormModal.vue` | UX-01, UX-05, UX-16 | `modal-fullscreen-sm-down`; the reason line; `provide` of `dirty` |
| `frontend/src/components/ActiveToggle.vue` | UX-16 | `inject`s the dialog's `dirty`; disabled with the reason; wraps |
| `frontend/src/components/layout/AppTopbar.vue` | UX-02 | name in dark text; a *Sign out* button with word |
| `frontend/src/App.vue` | UX-02 | the two *Sign out* buttons (`:53`, `:78`) `.tap-target`, not `btn-sm` |
| `frontend/src/components/layout/AppBottomNav.vue` | UX-22 | `<router-link>` items |
| `frontend/src/stores/navigation.js` | UX-12 | the Masters item takes `perms` (any of four keys) |
| `frontend/src/assets/main.css` | UX-02, UX-08, UX-12 | `--topbar-height` 48 px; `.tap-target`; bottom-bar label size; the list's phone card rows |
| `frontend/src/views/EquipmentByCodeView.vue` | UX-03 | its own not-found text and button |
| `frontend/src/views/EquipmentDetailView.vue` | UX-07 | Print label for editors; phone order of the cards |
| `frontend/src/views/EquipmentView.vue` | UX-08, UX-20, UX-21 | phone layout; the criticality filter's words; the no-units text |
| `frontend/src/components/PagerBar.vue` | UX-23 | `.tap-target` buttons |
| `frontend/src/components/documents/PhotoViewer.vue` | UX-09 | full screen on a phone; image height |
| `frontend/src/components/documents/DocumentsCards.vue` | UX-10, UX-11 | row buttons and "⋯" menu; drops `:photos-only` (`:365`) |
| `frontend/src/components/documents/DocumentUploadModal.vue` | UX-11 | Kind block, `photosOnly` prop and kind watch removed; camera-name title; "Enter a title" reason; HEIC note on refusal |
| `frontend/src/utils/documentTypes.js` | UX-11 | `isCameraName(name)`; the title rule |
| `frontend/src/views/SettingsView.vue` | UX-04, UX-17, UX-19, UX-27 | two confirms; cards for `settings:edit`; card order; status words |
| `frontend/src/views/settings/AccessLog.vue` | UX-26 | `displayRoleLabel`, "Needed: " on keys, "Allowed" |
| `frontend/src/utils/siteRoles.js` | UX-26 | `displayRoleLabel(role)`: the site roles' labels plus "IT admin", "Admin" |
| `frontend/src/views/masters/PeoplePanel.vue` | UX-14, UX-15, UX-18 | sites in Add; folded rows; the removal and change lines; search and site select |
| `frontend/src/views/MastersView.vue` | UX-25 | section labels |
| `frontend/src/views/masters/PropertiesPanel.vue`, `ClassPropertiesView.vue`, `ModelPropertiesModal.vue`, `EquipmentClassesPanel.vue` | UX-25 | "Equip Class" / "Equip Type" / "Equip Category" wording in these screens follows the toolbar (one term) |
| `frontend/src/utils/equipmentLabels.js` | UX-20, UX-24 | criticality words; lifecycle help |
| `frontend/src/views/equipment/EquipmentFormModal.vue` | UX-20, UX-24 | criticality options; the code line |
| `frontend/src/components/CriticalityBadge.vue` | UX-20 | `title` |
| `frontend/src/views/MeView.vue`, `TicketsView.vue`, `readings/ReadingsSheet.vue` (in `frontend/src/views/`) | UX-21 | the shared no-units constant |
| `frontend/src/utils/messages.js` (new) | UX-06, UX-21 | `NO_UNITS_TEXT`, `NO_CONNECTION_TEXT`, `NOT_ANSWERING_TEXT` |
| `frontend/src/api.js` | UX-06 | catch fetch's `TypeError`; 5xx without JSON |
| `frontend/src/stores/auth.js` | UX-13 rows 6, 7 | two messages |

### Backend (UX-13 message text; UX-14 one response field)
`backend/masters.py` also: the people list response gains `assignable_site_ids` (§ 6).
`backend/auth_utils.py` (`_forbidden_message`, the two `Unauthorized`), `backend/app.py`
(`_db_unavailable`), `backend/api_common.py` (`DB_LOST_TEXT` takes the new text and is used by
`_db_unavailable` too), `backend/access_control.py` (`NETWORK_DENIED_MESSAGE`),
`backend/settings.py` (own-address refusal), `backend/documents_core.py` (`TYPE_REFUSED`,
`PhotoTooLarge` texts), `backend/documents.py` (upload retry, `FILE_LEFT_BEHIND`),
`backend/equipment.py` (code collision, unknown unit), `backend/masters_core.py` (failure code,
reserved type name, "Choose a …"), `backend/equipment_core.py` ("Choose a …"),
`backend/masters.py` (`_check_grantable`: inactive or unknown unit, trade or site: the code or
name, not the id).

### Tests
- Backend, assertions on changed texts: `backend/tests/test_documents_api.py` (lines 88, 102,
  616), `backend/tests/test_documents_core.py` (62, 158), `backend/tests/test_access_control_api.py`
  (200), `backend/tests/test_equipment_api.py` (130), `backend/tests/test_masters_api.py` (740:
  "Database unavailable" in the 503), `backend/tests/test_errors.py:44` (`DB_LOST_TEXT`'s new
  text), and any further hit of the coder's grep for each old text (§ 8.1), including
  `backend/tests/test_masters_core.py` and `backend/tests/test_equipment_core.py` (row 20).
  New: a test in `backend/tests/test_site_roles_api.py::TestVisibility` for the top-level
  `assignable_site_ids` (§ 8.1).
- Frontend unit: new `frontend/tests/api.test.js` (UX-06), `frontend/tests/documentTypes.test.js`
  (UX-11, new), `frontend/tests/navigation.test.js` (UX-12: lines 31 and 53 expect
  `"masters"` for the operator and the storekeeper, which changes; new cases),
  `frontend/tests/siteRoles.test.js` (UX-26, `displayRoleLabel`).
- Browser: the existing tests of § 8.3 (twenty-odd lines in `equipment.spec.js`,
  `labels.spec.js`, `asset-list.spec.js`, `screens.spec.js`, `masters.spec.js`,
  `readings.spec.js`), a helper `openFilters(page)` in `frontend/e2e/support/`, and the new
  tests of § 8.4.

### Docs (housekeeping, by the coder)
- `docs/Plan.MD` § 3 — the decisions were recorded at gate A (Masters nav for editors, Settings cards by key, Sign out on shared devices); update only if the build departs.
- `docs/steps/device-checks.md` — the rows of § 8.5.
- `docs/steps/INDEX.md` queue — *Auth hardening*'s [18] (503 body) marked done by S064.
- `.claude/CLAUDE.md` § SMTW-Review — the spec-to-step map adds S064 to `screens`,
  `equipment`, `labels`, `asset-list`, `masters`, `readings` (and to any new spec).
- No schema doc (no migration).

## 4. Data model

None. No migration, no setting.

## 5. Rules

### 5.1 Dialogs (UX-01, UX-05, UX-16)
1. `FormModal.vue:157`: `modal-dialog modal-dialog-scrollable modal-fullscreen-sm-down`. Every
   dialog on FormModal gets it; dialogs not on FormModal are not changed, except the photo
   viewer (5.4).
2. The reason line: when `saveDisabledReason` is not empty and the footer shows Save, the left
   footer shows `<span class="small text-secondary">{{ saveDisabledReason }}</span>` before the
   `footer-left` slot's content. The Save button keeps `title`. A dialog that today shows its
   own phone-only line (`PropertyFilterModal.vue:320`) drops it, so the reason shows once.
3. FormModal `provide`s a read-only `dirty` (its prop). `ActiveToggle` `inject`s it (default
   `false`, so it works outside a FormModal). When dirty and the record is active, *Deactivate*
   is disabled and the reason "Save your changes first, or cancel them" shows beside it as a small line
   (the same style as rule 2). *Reactivate* is blocked the same way: `useMasterForm.changeActive`
   (`useMasterForm.js:42-45`) sends `{active}` only through `send`, whose `finish` closes the
   dialog (`useFormModal.js:74-76`), so it would drop the edits too. The confirm span gets
   `flex-wrap` so Yes / No wrap on a phone.
4. No panel file changes for UX-16 (the 14 panels pass `:disabled="saving"` today and keep it).

### 5.2 Top bar and navigation (UX-02, UX-12, UX-22)
1. `main.css:9`: `--topbar-height` 48 px (the layout follows the variable). `main.css` gets
   `.tap-target { min-height: 44px; }`. `AppTopbar.vue:35-38`: the name in `text-body` (not
   `text-secondary`), normal weight, cut with an ellipsis when long; the button
   `btn btn-outline-secondary tap-target` with `fa-right-from-bracket` and the word **Sign out**
   on every width. The `title="Logout"` goes. On a phone narrower than 360 px the name may drop
   to one line with ellipsis; the button never loses its word. `App.vue:53,78`: the same
   classes instead of `btn-sm`.
2. `navigation.js`: the Masters item becomes
   `perms: ["masters:edit", "equipment:edit", "people:edit", "failure_codes:edit"]`
   (`canSeeNavItem` already handles `perms`). The router's guard `canOpenRoute` follows the nav
   item, so a typed `/masters` sends a non-editor to their landing page (`router/index.js:122`);
   the router (`frontend/src/router/index.js`) does not change. `MastersView.vue`'s sections keep `masters:read`.
3. Holders today (`config_rbac.py`): `masters:edit` IT admin; `equipment:edit` engineer, IT
   admin (manager inherits); `people:edit` and `failure_codes:edit` engineer, IT admin. The
   site-scoped `equipment:edit` is in the user's permission list when held at any site:
   `/api/auth/me` sends `global_permissions()` (`app.py:157`, `auth_utils.py:423`, "every key
   the user holds somewhere").
4. `main.css:125`: bottom-bar label 0.75 rem; the six-item bar of the manager must still fit
   (the S040 test, `screens.spec.js:105-115`).
5. `AppBottomNav.vue:28-38`: each item a `<router-link :to="item.path">` with the same classes;
   the active state unchanged.

### 5.3 Equipment page and list (UX-03, UX-07, UX-08, UX-23)
1. `EquipmentByCodeView.vue:37`: replace `NotFoundView` with its own block inside the shell:
   heading "<code>" upper-cased as the label prints it (`labels_core.py:45`), the line "Not found, or not at your units. Ask your engineer if you
   should see it.", and a `btn btn-primary btn-lg` *Go to equipment list* (`/equipment`). One
   text for both cases: no leak of which case it is (as `EquipmentDetailView.vue:187`).
2. `EquipmentDetailView.vue:209-227`: *Print label* inside `v-if` on the bare key,
   `node.permissions.includes("equipment:edit")` (as `canSeeRemovedReadings`, `:87`), not
   `canEdit` (`:78-80`, false on a scrapped node and while loading). A scrapped node keeps
   *Print label* (a label may be reprinted for the scrap record); it stays disabled while
   loading as today.
3. Phone order: the page's blocks are plain siblings in `div.py-3` (`:184-365`). Wrap them,
   from the Raise ticket link to `DocumentsCards`, in one `d-flex flex-column` container. Below
   `md`: the Raise ticket link, the Scrapped alert (`:234`), the button row and the Open
   tickets card `order-0`;
   `DocumentsCards` (one root, `div.row`) `order-1`; every other block `order-2`. At `md` and up
   all orders reset (`order-md-0`), so desktop keeps today's order. No second copy of a card.
   A flex column stretches its children: the Raise ticket `router-link.btn` (`:230`) gets
   `align-self-stretch align-self-md-start` (full width on a phone, a bigger target; as today
   on desktop); `DocumentsCards` gets `mb-3 mb-md-0` so it does not touch the Details row's
   negative top margin on a phone.
4. List on a phone (`EquipmentView.vue:302-401`), below `md`:
   - the search box first, full width, not `-sm`; *Add equipment* right of it for editors;
   - a *Filters (n)* button (`btn btn-outline-secondary tap-target`) toggles a block holding
     the selects, the property-filter button and *Show scrapped*; n counts the filters set:
     each set select, *Show scrapped* when on, and `props` as one; search, page and the level
     default are not counted. The block starts closed (D5);
   - the property-filter line with its ✕ (`:351-364`, shown when `props` is set) stays visible
     above the cards: it is the applied filter and its ✕ is the way out;
   - the label tick column, *Print labels* and *Print asset list* hidden below `md`;
   - each row as a two-line card, a `router-link` to the equipment page: line 1 the ticket
     light, code (bold) and name; line 2 the lifecycle badge, criticality badge, then the unit
     code at the `equipment` level and the path (`full_path`, as the table, `:430`) at other
     levels. The table markup stays for `md` and up; the cards are a second loop over the same
     rows, shown `d-md-none` (one data source, two templates). Both the `<tr>` and the card
     carry `data-test="equipment-row"` for the tests (§ 8.3).
5. `PagerBar.vue:19,23`: `btn btn-outline-secondary tap-target` instead of `btn-sm`.

### 5.4 Documents and photos (UX-09, UX-10, UX-11)
1. `PhotoViewer.vue:100`: add `modal-fullscreen-sm-down`; `:148` image
   `max-height: calc(100dvh - 9rem)` on a phone, 75vh above; title `text-wrap` up to two
   lines (`-webkit-line-clamp: 2`).
2. `DocumentsCards.vue:275-300`: the title a link/button that does what *Open* does today; a
   labelled *Download* button (`tap-target`); a `dropdown` "⋯" (`aria-label="More actions"`,
   `tap-target`) with *Edit title* and *Remove*. Choosing *Remove* closes the menu and shows
   today's inline confirm in the row, below the title (`:302-306`). *Open* as a separate button
   goes.
3. Both upload buttons already open the dialog with their kind (`uploadModal.open('document')`,
   `open('photo')`, `DocumentsCards.vue:253,325`; `open(kind)` seeds `form.kind`,
   `DocumentUploadModal.vue:82-86`), and no other caller exists. So the Kind block
   (`DocumentUploadModal.vue:107-114`), the `photosOnly` prop, its consumer
   `:photos-only="!canEditDocs"` (`DocumentsCards.vue:365`) and the `watch(() => form.kind,
   clearFile)` are removed. Who may add which kind is unchanged: the buttons shown already
   follow `canEditDocs` (S018). The dialog adds `saveDisabledReason` "Enter a title" when the
   title is empty (shown by § 5.1 rule 2).
4. Title: when the file name matches `isCameraName` — `^(IMG|PXL|DSC|image)[_-]?\d*` (case
   insensitive), or the name without extension is digits, `_` and `-` only — the title stays
   empty with placeholder "What does the photo show?" and focus goes to it. Other names prefill
   as today (`documentTypes.js:15`). Title is still required where it is today.
5. The iPhone note (`documentTypes.js:13`) shows only after a refusal whose file was HEIC/HEIF
   (by extension or type), under the file field.

### 5.5 Settings (UX-04, UX-17, UX-19, UX-26, UX-27)
1. Network: *Save* (still disabled while `!networksChanged`) sets `confirmingNetwork`; the card
   then shows the warning, two lists — **Added**: ranges in the input not in
   `network.networks`; **Removed**: the reverse (compare trimmed lines; empty lines dropped) —
   and *Yes, save* (`btn-danger`, a lock-out risk) / *No*. Yes calls today's `saveNetwork`; No
   returns to the form with the input kept. Editing the text while confirming closes the
   confirm. A range typed in another form than the server stores it (`10.24.0.1/16` vs
   `10.24.0.0/16`) shows as both added and removed: accepted, the lists are a reminder, the
   server normalises.
2. Labels: the same shape, with *Yes, save* `btn-primary` (no lock-out); the sample link joins as the server does,
   `label_url` (`labels_core.py:49-52`): the input with trailing slashes removed, then
   `/e/MCC2CMP001`.
3. Cards: `v-if="canEditSettings"` on Database (`SettingsView.vue:214-252`) and Background
   tasks (`:373-409`); `onMounted` calls `loadStatus` and `loadTasks` only then. For a holder
   of `settings:read` without `settings:edit`, *Removed documents* renders first (before
   Uploads); for IT admin the order is unchanged.
4. Task status words: `{done: "Done", failed: "Failed", pending: "Waiting", running: "Running"}`;
   an unknown value shows as is.
5. Access log (`AccessLog.vue:17,138,148`): badge "Allowed"; role through a new
   `displayRoleLabel(role)` in `frontend/src/utils/siteRoles.js`: `roleLabel` (`:23`) for the
   six site roles, "IT admin" for `it_admin`, "Admin" for `admin`, any other value as is
   (`roleLabel` stays the Team dialog's). The access log's role is `display_role`
   (`access_core.py:130`). Detail: prefixed "Needed: " only when it is a permission key
   (`/^[a-z_]+:[a-z_]+$/`, the mark of `_log_denied`, `auth_utils.py:486`); a business
   refusal's text (a bare 403, `network_core.py:93`) shows as it is. UX-13 row 1 does not change
   the logged key.

### 5.6 Team and Masters (UX-14, UX-15, UX-18, UX-25)
1. Where Add gets its sites. In Edit, `addableSites` reads the person's
   `assignable_site_ids` (`PeoplePanel.vue:102-108`), computed per person and viewer
   (`masters.py:1131-1140`: active sites minus the person's rows, where the viewer is IT admin
   or `assigns_at(site)`). On Add there is no person, so `GET /api/masters/people` gains one
   top-level field, `assignable_site_ids`, **sent only to `people:edit` holders** (absent for
   others, as `_people_out` already sends site data only to editors; `test_site_roles_api.py:471-473`
   asserts floor roles get no such key). The computation is split out of
   `_SiteViewer.assignable_site_ids(person, …)` as `grantable_site_ids()` (active sites where the
   viewer is IT admin or `assigns_at(site)`, no person and no `_is_own`), used by both the
   per-person field (minus the person's rows) and the new top-level field; `_people_out`
   returns the viewer so `list_people` can use it. On Add the dialog reads the top-level field;
   on Edit the per-person field as today. The field adds no data a viewer could not already
   learn: site ids are readable through `/api/masters/sites` (`masters:read`), and the set is the
   viewer's own grant.
2. Add person, Save. `toBody` (`:163`) sends the typed rows on create when a login is set
   (today it sends `sites: []` on create, which would drop them; the server requires `sites`
   with a login, `masters.py:1216-1221`). Without a login: `POST` the person, then
   `saveRows(newId)` (`:199`), the per-site `PUT`s Edit uses (`saveRows` already treats
   `editing.value?.sites ?? []` as the original). `save()` (`:227-228`) runs `saveRows` on
   create too when `sites` is not in the body. If a row's `PUT` fails: set `editingId`,
   `editing`, `editingLabel` and `editingActive` (`useMasterForm.js:15`) to the new person, the title reads *Edit person*, the form
   stays dirty (the failed row is unsaved, so Cancel still asks), the error shows on that row,
   and the list reloads. The text "Save the person first…" (`:391`) goes.
3. Folded rows: with more than two rows, each row shows its `rowText` with an *Edit* link;
   a new row and a row with an error are open. One row open at a time is not required.
4. Access lines: compare the rows as loaded with the rows now. For each removed row: "Saving
   removes access: <rowText of the old row>."; for each row whose role changed: "Saving
   changes access: <rowText of the old row> → <new role label>." No ranking of roles
   (`SITE_ROLES` is the dialog's order, not a ladder: `config_rbac.py:44`, `ROLE_INCLUDES`).
   Shown in `alert alert-warning py-2` above the footer, as the login line (`:445-448`). The ✕
   becomes `btn btn-outline-danger btn-sm` "Remove" with `ms-3` (an office dialog).
5. Team list: a search box (name or login, case-insensitive, on the client: the list is
   already loaded whole) and a site select (*All sites* + each site) filtering people with a
   visible row at that site (rows an engineer may not see are masked by the server, `sees`,
   `masters.py:1121`). Same header layout as `UnitsPanel.vue`.
6. `MastersView.vue:26-39`: labels *Categories*, *Classes*, *Types*. The four other screens of
   § 3 that say "Equip Class" / "Equip Type" / "Equip Category" say "class" / "type" /
   "category" in the same way (the coder lists each changed text in the report).

### 5.7 Messages (UX-06, UX-13, UX-21)
1. `api.js`: in `request`, `apiUpload`, `apiGetBlob`, wrap `fetch` in `try`; a `TypeError`
   becomes `Error(NO_CONNECTION_TEXT)` with `status = 0`; an `AbortError` is re-thrown as is.
   In `throwIfFailed`, when the body is not JSON and `status >= 500`, the message is
   `NOT_ANSWERING_TEXT`; a 4xx without JSON keeps `statusText`.
2. The rewrites (backend unless named; audit table row numbers):

| Row | Where (today) | New text |
|---|---|---|
| 1 | `auth_utils.py:492` `_forbidden_message` | You don't have permission for this. Ask your engineer or IT. |
| 2 | `app.py:66` and `api_common.py:79` (`DB_LOST_TEXT`, one constant for both 503s) | Yantra can't reach its database. Try again in a few minutes. (the exception goes to the log, not the body) |
| 3 | `auth_utils.py:277`, `:295` | Your sign-in has expired. Sign out, then sign in again. |
| 4, 5 | `api.js` | rule 1 |
| 6 | `stores/auth.js:111` | Cannot reach Yantra. Check the network and try again. |
| 7 | `stores/auth.js:86` | `err.message` as it is, no prefix: every text that reaches it is plain after this step (rule 1, row 2, S059's `LOGIN_SERVER_DOWN_TEXT`, `auth_utils.py:61`). The 401 branch (`:84-85`) stays. |
| 8 | `access_control.py:34` | Your role can use Yantra only on the plant network. |
| 9 | `settings.py:285` | Your own address {ip} is not in the list. Add its range. — with no address known: "Yantra cannot see your address. Save from a computer on the plant network." |
| 10 | `documents_core.py:32` | This file can't be added. Use a PDF, or a JPEG, PNG or WebP photo. |
| 11 | `documents_core.py:164`, `:170` | Photo too large ({n} megapixels). Take it at a lower resolution. (the first, without a count: "Photo too large. Take it at a lower resolution.") |
| 12 | `documents.py:75` | The upload failed. Try again. |
| 13 | `documents.py:86` | Deleted, but its file is still on the server. Tell IT. (the path stays in the log) |
| 14 | `equipment.py:131` | Could not give a code. Press Save again. |
| 15 | `masters_core.py:212` | Use up to {max} letters or digits, parts joined by a dot, e.g. NOI or 3.4. |
| 16 | `masters_core.py:104` | Choose another name; "none" is reserved. |
| 17 | `masters.py:835` (`_check_grantable`, shared by units and trades: `:1253,1292,1355`), `:1350` | {Unit\|Trade} {code, or name for a trade} is inactive. Untick it or reactivate it. / Site {code} is inactive. Remove the row or reactivate the site. (never the id) |
| 18 | `masters.py:836` (`_check_grantable`) and `equipment.py:386` | That {unit\|trade} no longer exists. Reload and try again. |
| 20 | the `*_id` fields parsed by `_parse_id` (`masters_core.py`) and `_id_parser` (`equipment_core.py:71`) when they say "{label} is required" (e.g. `masters_core.py:143`; `_parse_optional_id` never does), `equipment_core.py:270` ("Unit is required for equipment" → "Choose a unit.") and `:272` ("Criticality is required for equipment" → "Choose a criticality."), and the missing-field branch of those same fields ("Class id is required", `masters_core.py:303`, `equipment_core.py:360`) | Choose a {label}. — label = the field name without `_id`, in lower case ("Choose a class."). `model_id` keeps `PICK_A_MODEL`. Fields that are not record selects ("Unit is required", "Kind is required", "Expected answer is required", `test_masters_core.py:385-404`) keep their texts. The coder lists every changed text. |

   Row 2 keeps the 503 status. The access-log outcome of a 401 or 403 is unchanged (it reads
   the status and the gate's mark, `network_core.classify_outcome`, not these texts, except a
   bare 403 without a mark, which row 1 never is: § 9 item 4).
3. `NO_UNITS_TEXT` in `frontend/src/utils/messages.js`, used by the four screens of § 3.

### 5.8 Nits (UX-20, UX-24)
1. `equipmentLabels.js:36`: `CRITICALITY_LABELS` stays A / B / C for badges; a new
   `CRITICALITY_OPTIONS` = "A — critical", "B — important", "C — normal" for the form's select
   and the list's criticality filter (`EquipmentView.vue:329`), and as the badge's `title`;
   `CRITICALITY_HELP` = the three lines of `docs/Maintenance-Philosophy.md:357-359` ("Stops a
   production line or is a safety or environment risk; no standby", "Slows production or has a
   standby; repair within the shift", "No direct production impact; repair when convenient")
   as `form-text` under the form's select, for the grade chosen (a `title` never shows on a
   phone).
2. `LIFECYCLE_HELP` (`equipmentLabels.js:22-27`): in service "Running or ready to run.";
   standby "Ready, kept as a spare, e.g. a spare pump."; out of use "Not in use for now — no PM
   is due."; scrapped "Gone from the plant for good. You cannot undo this."
3. `EquipmentFormModal.vue:293-294`: "The code is given on Save and never changes."

### 5.9 Permissions
No key added or changed; no route's check changed. One read gains a field: the people list's
`assignable_site_ids` (§ 5.6 rule 1), behind the route's existing key (`masters:read`) and
computed by the existing per-viewer rule, so a viewer learns only where they may grant. What
else changes is visibility only:
- Masters nav and route (5.2) — editors only; the `masters:read` APIs unchanged.
- Settings Database and Background tasks cards (5.5) — `settings:edit` only; the APIs
  (`settings:read`) unchanged, so a manager could still call them: no data is hidden by this,
  the screen is only made simpler.
- Print label button (5.3) — node `equipment:edit`; `/labels` stays open to every
  `equipment:read` holder as today.

### 5.10 Lessons for `SMTW-WebApp-Base.md` (ready-to-paste, impl report)
One short paragraph each, under the base's existing headings:
1. *Form / Modal*: dialogs scroll inside and are full screen below `sm`; a disabled Save shows
   its reason as text, not only a tooltip; Deactivate is blocked while the form is dirty.
2. *Form / Modal*: a setting that can lock people out or change every later print gets an
   inline confirm showing the effect (added / removed, a sample).
3. *Table / List*: below `md` a list becomes cards, search first, filters folded behind a
   counted button, office-only columns and buttons hidden.
4. *Topbar*: **replaces** the sentence at `SMTW-WebApp-Base.md:1273` with "Username as plain
   text; logout a labelled button of at least 44 px when the app runs on shared devices, else
   an icon button or small link." (D11)
5. *Navigation*: a reference module shows in the nav only to its editors; pick-lists keep the
   wide read key.
6. *Frontend API Helper*: a network failure and a 5xx without JSON get plain messages; the
   browser's own text never reaches the user. Backend: a 503 body never carries the exception.
7. *Design Tone*: a QR/link landing page words "not found" for both missing and not-yours.
8. *Design Tone*: floor targets 44 px (WCAG 2.2 SC 2.5.5); `btn-sm` only for office tables.

## 6. API

- `GET /api/masters/people` — the response gains one top-level field, `assignable_site_ids`
  (list of site ids, possibly empty), sent only to `people:edit` holders: the sites where the
  viewer may add a row for a new person (§ 5.6 rule 1). Nothing else in the body changes. The only body change of the step.
- No URL, request body or status changes. Response **texts** change for the rows of § 5.7.

## 7. Design decisions

- **D1 One step** (KLA, 28-10-2026). Rejected: two steps (Size, top).
- **D2 Masters nav for editors only** (UX-12). The four edit keys decide. Rejected: keep it for
  everyone (an operator's bar has five items, one they never use); a new key `masters:browse`
  (a key for a nav item is RBAC work this step avoids). Consequence: a technician can no longer
  browse models or failure codes in Masters; they still see them where they work (equipment
  page, ticket pick-lists). **For KLA to confirm.**
- **D3 `provide`/`inject` for the dirty flag** (UX-16). FormModal already knows `dirty`.
  Rejected: a `dirty` prop through 14 panels (14 files for one attribute). First use of
  `provide` in the repo (`grep -rn "provide(" frontend/src` finds none; confirmed in review r1).
- **D4 Phone cards as a second template over the same rows** (UX-08). Rejected: a CSS-only
  table-to-card trick (hard to read, breaks the ticket light column); a separate phone view
  (two screens to keep in step).
- **D5 Filters folded, closed on load** (UX-08). The count says filters are set. Rejected:
  open when any filter is set (the first screen would be the wall again after a QR-to-list
  hop).
- **D6 Add person with sites in one Save, partial failure turns into Edit** (UX-14). Uses the
  existing routes in order; the Add dialog's sites come from one new field on the people list
  (§ 6). Rejected: a new combined endpoint (out of scope: no endpoint); rolling back the person
  on a row failure (a delete route for people does not exist, and the person is valid without
  rows); sites in Add for IT admin only (engineers adding technicians is the commonest Team job
  the audit names); deferring "sites in Add" (KLA asked for all 27).
- **D7 Only reachable messages rewritten** (UX-13). Rows 19, 21–26 are seen only after a bug or
  a hand-edited request; their generic validators (`api_common.py:146,153,176`) feed many
  fields and tests. Rejected: rewriting all (many test edits, small gain). **For KLA to
  confirm.**
- **D8 Settings cards hidden, APIs unchanged** (UX-19). Rejected: narrowing the APIs to
  `settings:edit` (an RBAC change; the manager may want the DB state when IT is away).
- **D9 Base lessons as ready-to-paste text** (S058's way). `SMTW-WebApp-Base.md` is synced from
  smtw-common and says "maintained in smtw-common"; an edit here is lost at the next sync.
  Rejected: editing the synced file here.
- **D10 Print label for editors only** (UX-07). Labels are printed by the office. Rejected:
  moving it into the Details card (still shown to all).
- **D11 Sign out a labelled button, against the base's Topbar rule** (UX-02). The base says
  "not a prominent button" (`SMTW-WebApp-Base.md:1273`); Yantra's shared devices need the
  opposite (Plan.MD § 3). The lesson text replaces the base's sentence (§ 5.10.4). Rejected:
  recording only a Yantra deviation in `.claude/CLAUDE.md` (every app with kiosks has the same
  need).
- **D12 Office-only list controls are desktop tests** (UX-08, BR1-01). On the logic phone the
  rows and filters stay tested (adapted); the tick, *Print labels* and *Print asset list*
  tests run on `desktop-chromium` only. Rejected: keeping the print buttons inside the phone's
  Filters block (the lesson "office-only buttons hidden" would not hold).

## 8. Tests and acceptance

### 8.1 Backend
- For each old text of § 5.7, the coder greps `backend/tests` and `frontend/e2e` and updates
  every assertion; known: § 3 *Tests*. A new test in `backend/tests/test_errors.py`: a
  `DBUnavailable` 503 body has the new text and not the exception's text.
- `test_site_roles_api.py::TestVisibility`: the list's top-level `assignable_site_ids` — IT
  admin: every active site; an engineer: only the sites where they assign technicians; an
  editor with no grant: `[]`; a floor role: the key absent.
- `test_errors.py`: both 503 paths (`_db_unavailable` and the mid-query loss) give the one
  `DB_LOST_TEXT`.
- `test_network_core.py:101` passes `"Unauthorized"` as the error text to `classify_outcome`;
  the outcome is by status, so it stays green (rename the literal for clarity, optional).
- Always-check tests (settings): `test_role_matrix` unchanged (no key changed); no `_TABLES`,
  `db_down` or migration change.

### 8.2 Frontend unit
- `api.test.js`: a rejected `fetch` (`TypeError`) → `NO_CONNECTION_TEXT`, `status` 0; a 502
  with an HTML body → `NOT_ANSWERING_TEXT`; a 404 without JSON → its `statusText`; a JSON
  refusal unchanged (error, field, code).
- `documentTypes.test.js`: `isCameraName` true for `IMG_2034.jpg`, `PXL_20261020_143512.jpg`,
  `image.jpg`, `20261020_143512.jpg`; false for `Pump manual.pdf`, `motor-nameplate.jpg`.
- `navigation.test.js`: Masters visible with each of the four keys, hidden with only
  `masters:read`; `canOpenRoute("masters", …)` follows.

### 8.3 Existing browser tests to change
On the logic device (`phone-chromium`, 412 px, below `md`) UX-08 hides the table, folds the
selects and hides the office controls. Per group (D12):
1. **Rows and filters, adapted, stay on the phone.** `equipment.spec.js:154` `rowOf` matches
   `[data-test="equipment-row"]` (the `<tr>` and the card) instead of `tbody tr`; the uses at
   157–162, 165–176, 190–194, 226, 729, 737, 756, 830–842, 880, 885 follow; line 745
   (`page.locator("table")).toHaveCount(0)`) asserts the rows' absence instead. A helper
   `openFilters(page)` in `frontend/e2e/support/` (a no-op at `md` and up) is called before a
   select is used: `equipment.spec.js:169, 174, 192, 876–884` (`Tickets`, `Category`, `Class`).
   Also `:116–118` (S030: `thead th` Lifecycle and the Lifecycle select), `:191–195` (Tickets;
   `:195`'s `toHaveCount(0)` must not pass because the select is folded), `:718, 725` (Level),
   `:731, 736, 781` (the property-filter button's text). `openPropertyFilter` (the default
   opener `filterButton`, used at `:719, 771, 797, 812, 858`) calls `openFilters` once first.
   The S029 `@device` fit test (`:178-189`) also runs on `desktop-chromium`, so it branches by
   viewport width: below `md` *Filters (n)* and a row's bulb fit; at `md` and up the Tickets
   select fits, as today.
2. **Office controls, desktop only.** `labels.spec.js:59, 62` (the tick and *Print labels*),
   `asset-list.spec.js:81, 86, 101, 105` (*Print asset list*): tagged `@device` with
   `test.skip` below `md` (the settings' tag rule: a test that runs only on a project other
   than `phone-chromium`). `asset-list.spec.js:57` is only a page-loaded wait in the @page-rule
   test: it waits for the Search box instead and the test stays on the phone.
3. **Screens.** `screens.spec.js:34` (`/equipment`, `@smoke`) asserts the *Search* box;
   `:70` (`/masters`) → the editor roles; `:71` (Settings) a text every settings role sees,
   "Removed documents" or the Uploads heading; `:110` stays (six items).
4. **Texts.** `masters.spec.js:124-128, 364, 408, 451, 511, 549-563` (section names);
   `readings.spec.js:643` (no-units text); any test that clicks *Open* on a document row or a
   Kind radio (coder greps `Kind`, `name: "Open"` in `frontend/e2e`).
The coder greps `frontend/e2e` for every control this step hides or renames (*Print asset
list*, `Select … for labels`, `Tickets`, `Category`, `Class`, `Level`, `Lifecycle`, `thead`,
`Filter by property`, `Properties (`, `Logout`, `Let in`, `Equip `)
and lists each line changed.

### 8.4 Automated (new browser tests, targeted: the changed specs plus `screens.spec.js`)
Logic tests untagged; layout tests `@device` (settings: *Browser tests*).
1. **important** S064: a dialog on a phone is full screen (`modal-fullscreen-sm-down` in
   effect: the dialog's width equals the viewport) and its body scrolls (`overflow-y: auto`)
   (Equipment and Team dialogs) — `@device`. Save on screen is already asserted by
   `expectDialogFits` in every flow.
2. **important** S064: a disabled Save shows its reason as text (e.g. Move without a unit).
3. S064: Deactivate is disabled with "Save your changes first, or cancel them" after editing a name;
   enabled again after Cancel/undo.
4. **important** S064: the top bar shows the name and a *Sign out* button with its word, at
   least 44 px high, on a phone — `@device`.
5. **important** S064: an operator's nav has no Masters; an engineer's has it; an operator
   typing `/masters` lands on their landing page.
6. **important** S064: `/e/<code>` of a node outside the user's units shows the code, "Not
   found, or not at your units", and *Go to equipment list*.
7. S064: Print label hidden for a technician, shown for an engineer on the equipment page.
8. S064: on a phone, Documents comes before Details on the equipment page — `@device`.
9. **important** S064: on a phone the equipment list shows search first, *Filters (n)* with the
   count, cards not the table, no print buttons — `@device`.
10. S064: the photo viewer's Next button is on screen on a phone — `@device`.
11. S064: a document title opens the PDF; Remove is in the "⋯" menu and still asks.
12. S064: *Add photo* shows no Kind choice; a file `IMG_1234.jpg` leaves Title empty.
13. **important** S064: Network Save asks first, lists added and removed ranges; *No* saves
    nothing; *Yes, save* saves.
14. S064: Labels Save asks first with the sample link.
15. S064: a manager's Settings has no Database or Background tasks card and shows Removed
    documents first; IT admin sees both cards.
16. S064: the access log shows "Allowed", a role label, and "Needed: <key>".
17. **important** S064: Add person with a site and role saves both in one Save; the list shows
    the role.
18. S064: removing a site row shows "Saving removes access: …".
19. S064: Team search and site select filter the list.
20. S064: a dropped connection (route aborted) shows "No connection. Check Wi-Fi or mobile
    data and try again."
21. S064: the bottom bar is reachable by Tab and opens with Enter — on `phone-chromium`,
    untagged (the bar is hidden on desktop).
22. S064: Add person as an engineer offers only the engineer's site; a row's failure leaves
    the dialog as *Edit person* with the error on the row. The failure is forced against the
    real server: after ticking a unit, the test deactivates that unit through the API, then
    presses Save; the row shows row 17's text ("Unit … is inactive. Untick it or reactivate
    it.").

### 8.5 On a real device (rows in `docs/steps/device-checks.md`; IT Admin)
1. **important** With the phone keyboard up, Save is reachable in the Equipment and the Team
   dialogs — Android and iPhone, engineer account, dev server or TEST, mobile data.
2. A gloved thumb hits Sign out, the pager and the document row's buttons — Android, operator /
   engineer account, either machine.
3. A camera photo from *Add photo* (Android and iPhone) gets an empty title; an iPhone HEIC
   from Files shows the note — engineer account, either machine.

### 8.6 Acceptance
All unit suites green; targeted browser runs green; the coder's one whole-suite Normal run
green; every item UX-01…UX-27 named in the impl report with its file:line and its test or
device row; the base texts of § 5.10 in the impl report.

## 9. Open questions and assumptions

1. **Q1 (D2)** Masters nav for editors only: confirm. Option a (recommended): as § 5.2.
   Option b: keep it for all.
2. **Q2** Preselect the engineer's own site with *Technician* in *Add person* (UX-14's second
   idea): option a (recommended): no, out of scope (the frontend does not hold "my sites" in a
   form ready for it); option b: yes, adds work in `PeoplePanel.vue`.
3. **Q3 (D7)** Rewrite only the reachable messages: confirm (recommended), or all 26 rows.
4. **Fact** A bare 403 without a gate mark logs the start of its message as the access-log
   detail (`network_core.py:93`). Both callers of `_forbidden_message` (`require_perm`,
   `auth_utils.py:505`; `check_perm`, `:517`) call `_log_denied` first, which marks the key
   (`:486`), so row 1's new text never reaches the log. Other bare 403s (business refusals)
   keep their own texts.
5. **Assumption** the sample code `MCC2CMP001` in the Labels confirm is only text; no lookup.

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 28-10-2026
| Finding | Answer |
|---|---|
| BR1-01 major | Accepted (option a): § 8.3 per group — rows and filters adapted on the phone (`data-test="equipment-row"`, `openFilters`), tick and print tests desktop-only `@device`, `screens.spec.js:34` asserts Search; D12 added; the grep list for the coder. |
| BR1-02 major | Accepted (option a): `assignable_site_ids` on the people list (§ 5.6.1, § 6, § 5.9, test in `test_people_api.py`); `toBody` sends rows on create with a login; `saveRows` on create; a row failure turns the dialog into *Edit person*, dirty. D6 and the out-of-scope line updated. |
| BR1-03 minor | Accepted (a): `.tap-target` (44 px) on Sign out (top bar and `App.vue:53,78`), pager, Download, "⋯", *Filters (n)*; `--topbar-height` 48 px. |
| BR1-04 minor | Accepted (a): one flex-column wrapper with `order-*` reset at `md`; Print label on the bare key, kept on a scrapped node. |
| BR1-05 minor | Accepted (a): "Needed: " only on a permission key. |
| BR1-06 minor | Accepted (a): `displayRoleLabel` in `siteRoles.js`, with a unit test. |
| BR1-07 minor | Accepted (a): one `DB_LOST_TEXT` for both 503s; `test_errors.py` changes. |
| BR1-08 minor | Accepted (a): "removes" and "changes" lines, no ranking. |
| BR1-09 minor | Accepted (a): the Kind block, `photosOnly` and the kind watch go; "Enter a title" reason added. |
| BR1-10 minor | Accepted (a): rows 17, 18, 20 stated (trades, `_check_grantable`, the `*_id` rule); test files named. |
| BR1-11 minor | Accepted (a): D11; § 2 names the departure; § 5.10.4 replaces the base sentence. |
| BR1-12 minor | Accepted: test 21 on `phone-chromium`, untagged. |
| BR1-13 minor | Accepted: § 5.3.4 places Show scrapped, the property line, Add equipment; `props` counts as one; line 2 unit or path; the card a `router-link`. |
| BR1-14 minor | Accepted: row 7 shows `err.message` as it is. |
| BR1-15 minor | Accepted: `navigation.test.js:31,53` in § 3 Tests. |
| BR1-16…BR1-27 (nits) | Accepted: ISO 9241-110:2020 wording; badge `title` = option words, help as `form-text`, the list filter too; row 3 "Sign out, then sign in again"; row 9 no-address wording; code upper-cased; Labels confirm `btn-primary`; "Save your changes first, or cancel them"; Remove's confirm in the row; the network compare caveat; CLAUDE.md spec-to-step map in Docs; Team site filter on visible rows; test 1 asserts full screen and scroll. |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 28-10-2026
| Finding | Answer |
|---|---|
| BR2-01 minor | Accepted: § 8.3 adds `equipment.spec.js:116–118, 191–195, 718, 725, 731, 736, 781` and `openPropertyFilter` → `openFilters`; `asset-list.spec.js:81, 101` desktop-only; grep words added. |
| BR2-02 minor | Accepted: the S029 fit test branches by width; `asset-list.spec.js:57` waits for Search and stays on the phone. |
| BR2-03 minor | Accepted: Scrapped alert `order-0`; Raise ticket `align-self-stretch align-self-md-start`; `DocumentsCards` `mb-3 mb-md-0`. |
| BR2-04 minor | Accepted: the top-level field only for `people:edit` holders; `grantable_site_ids()` split out; `_people_out` returns the viewer; § 6 and § 8.1 cases (floor role: absent). |
| BR2-05…BR2-08 (nits) | Accepted: `editingActive` on the switch; § 8.4.22 forces the failure by deactivating the unit through the API; row 20 names `_id_parser` and decides `equipment_core.py:270/272`; the test in `test_site_roles_api.py::TestVisibility`. |

### Approval — gate A, 28-10-2026
KLA: "ok, start coding when the review is done" (after round 1), given with the three open
questions shown with their recommended answers. Recorded as: Q1 a (Masters nav for editors
only), Q2 a (no preselected site in *Add person*), Q3 the recommended (only the reachable
messages rewritten). Round 2 left no blocker or major. Baseline `0e4d215`; the staleness
check is empty (round 2 reviewed `0e4d215`, which is HEAD). Coder: Opus (§ Gate notes:
about 40 files of UI logic across shared components, plus one change to a permission-scoped
response).
