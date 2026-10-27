```
Step: S064 — Floor UX fixes
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 28-10-2026
```

Reviewed against: c9142b4 + uncommitted S063

**Verdict: two `major` findings are open** (BR1-01: UX-08 hides, on the logic device, the controls that many existing browser tests use; BR1-02: the Add person dialog has no source for the sites it may offer). 13 `minor`, 12 nits. Facts file `scratch/brief-facts-S064.md` used; the three "no such file" rows (`readings/ReadingsSheet.vue`, `router/index.js`, `stores/auth.js`) are paths the brief gives relative to a folder named in prose, and all three files exist.

Size alone is not a finding (KLA's decision, D1). The 27 items are each a few lines; the findings below are about rules the coder would otherwise decide alone, tests the brief does not list, and three claims about the code that do not hold.

---

## Major

### BR1-01 — major — UX-08 hides, on the logic device, the controls that about twenty existing browser tests use; § 8.3 lists none of them

**Problem.** `phone-chromium` (Pixel 7, 412 px) is the logic device: every test runs there at the Normal level. § 5.3.4 puts the selects and the property-filter button behind *Filters (n)* (closed on load, D5), hides the tick column and both print buttons below `md`, and hides the table (`d-none d-md-block`) in favour of cards. On the Pixel 7 these tests then fail:

| Spec | Lines | What breaks |
|---|---|---|
| `screens.spec.js` | 34 | `/equipment` "shows" is the *Print asset list* button, for EVERYONE, `@smoke` — hidden on a phone |
| `equipment.spec.js` | 154 (`rowOf` = `tbody tr`), 157–162, 165–176, 190–194, 226, 729, 737, 745, 756, 830–842, 880, 885 | the table is gone on a phone; `page.locator("table")).toHaveCount(0)` at 745 passes for the wrong reason |
| `equipment.spec.js` | 169, 174, 192, 876–884 | `getByRole("combobox", { name: "Tickets" })`, `getByLabel("Category")`, `getByLabel("Class")` are inside the closed Filters block |
| `equipment.spec.js` | 178–189 (S029 `@device`) | asserts the *Tickets* select fits the screen — it is not on the screen any more |
| `labels.spec.js` | 59, 62 | `Select <code> for labels` tick and *Print labels (1)* — hidden |
| `asset-list.spec.js` | 57, 86, 105 | *Print asset list* — hidden; the first is the S015 test's only assertion |

§ 8.3 names only `screens.spec.js:70,71,110`, `masters.spec.js`, `readings.spec.js:643` and the Kind / Open greps.

**Why it matters.** The coder's whole-suite run goes red in five specs, and the coder then decides alone, per test, whether to rewrite it, skip it on phones, or put the control back. The second choice changes what the Normal level covers; the third changes the screen the user approved.

**Options.**
- a) **Recommended.** Decide in the brief, per group: (1) row and filter tests stay on the phone and are adapted — a shared `data-test="equipment-row"` on both the `<tr>` and the card, so `rowOf` matches either; an `openFilters(page)` helper in `e2e/support/` (a no-op above `md`) called before a select is used; the S029 fit test asserts the *Filters (n)* button and the row's bulb fit; (2) the tick and print tests (`labels.spec.js:59`, `asset-list.spec.js:57,86,105`) become desktop-only, tagged `@device` with `test.skip` on phones — the settings' tag rule allows a test that "runs only on a project other than phone-chromium"; (3) `screens.spec.js:34` asserts the *Search* box instead. List every line above in § 8.3.
- b) Keep *Print labels*, *Print asset list* and the tick column reachable on a phone inside the Filters block (an office job, but still there). Fewer test changes; the folded block grows; the brief's "office-only buttons hidden" lesson (§ 5.10.3) weakens.
- c) Leave it to the coder. Not recommended: the rule says anything the brief does not cover goes to the user, not into code.

### BR1-02 — major — the Add person dialog has no source for the sites it may offer, and the login path saves no rows on create

**Problem.** § 5.6.1: "the site rows show in the Add dialog as in Edit". In Edit, the sites a user may add come from the person's record: `addableSites` reads `editing.value?.assignable_site_ids` (`PeoplePanel.vue:102-108`), which the server computes per person and viewer (`masters.py:1131-1140`: active sites minus the person's present rows, where the viewer is IT admin or `assigns_at(site)`). On Add `editing.value` is `null`, so `addableSites` is empty: the *Add a site…* select never shows. The frontend holds no "sites where I may assign" (the brief's own Q2 says so), and `userPermissions` is the global union, with no site in it.

Second gap: § 5.6.1 says "A login set in Add keeps today's path (`sites` in the body)". Today's `toBody` sends `body.sites = editing.value ? rows : []` (`PeoplePanel.vue:163`): on create it sends an **empty** list, so IT admin's rows typed in Add would be dropped silently, and `save()` would not PUT them either (`:228` runs `saveRows` only when `editingId !== null`). The server does require `sites` with a login (`masters.py:1219-1221`), so this path must carry the rows.

**Why it matters.** UX-14 cannot be built as written. The coder would have to invent the data source, and the obvious guess (take `assignable_site_ids` from another person's row) is wrong for a person with rows at those sites and fails on an empty Team.

**Options.**
- a) **Recommended.** The list response (`GET /api/masters/people`) gains one top-level field, `assignable_site_ids`, the viewer's sites for a **new** person (`viewer.assignable_site_ids({...no rows...}, set())`, with `_is_own` false). The frontend uses it on Add and the per-person field on Edit. One field on an existing endpoint, no new route or permission; § 6 says so as the one body addition; a backend test in `test_people_api.py` (IT admin: every active site; an engineer: their own sites only). `toBody` sends the typed rows on create; `save()` runs `saveRows` on create too when `sites` is not in the body (`saveRows` already treats `editing.value?.sites ?? []` as the original). After a row failure: set `editingId`, `editing`, `editingLabel` to the new person, leave the form dirty (the failed row is unsaved, so Cancel still asks), and the title reads *Edit person*.
- b) Sites in Add for IT admin only (all active sites, no server field); engineers keep the two saves. Half of UX-14's gain is lost: engineers adding technicians is the commonest Team job the audit names.
- c) Defer "sites in Add" to a later step and keep UX-14's folded rows only. The step then does not fix all 27 items, which KLA asked for.

---

## Minor

### BR1-03 — minor — the 44 px targets the brief promises are not reached by `btn`, and the top bar is 42 px tall

**Problem.** § 2 says "Yantra aims at 44 px for the floor's main controls: Sign out, pager, document Download, list filters." § 5.3.5 makes the pager `btn` (Bootstrap's `btn` is 38 px tall: 0.375 rem × 2 padding + 24 px line + 2 px border), § 5.4.2 says "labelled Download" without a size, and § 5.2.1 asks for a `min-height: 44px` Sign out inside a bar whose height is `--topbar-height: 42px` (`main.css:9`; `AppTopbar.vue:71` draws the bell borderless for that reason). A 44 px button in a 42 px bar overflows or is clipped. `App.vue:53,78` keep two more `btn-sm` *Sign out* buttons on the no-access and network-refused screens — the kiosk case the brief argues from (a person with no access must sign out for the next one).

**Why it matters.** The brief cites WCAG 2.2 SC 2.5.5 (44 × 44) for these controls; the browser test § 8.4.4 would fail as specified, and the coder decides the heights alone.

**Options.**
- a) **Recommended.** One utility class in `main.css` (e.g. `.tap-target { min-height: 44px }`), applied to Sign out (top bar and `App.vue`), the pager buttons, Download, *Filters (n)*, and the document "⋯" button; grow `--topbar-height` to 48 px (one variable, the layout follows it). Say so in § 5.2.1, § 5.3.5, § 5.4.2 and § 5.10.8.
- b) Use `btn-lg` (48 px) for those controls; heavier, and the words grow too.
- c) Drop the 44 px claim for the pager and Download and keep 38 px. Then § 2 and § 5.10.8 must say "38 px, above the AA minimum of 24 px".

### BR1-04 — minor — UX-07: the equipment page is not a flex column, and "the same check as the other edit buttons" hides Print label on a scrapped node

**Problem.** § 5.3.3 says "the page's cards are in a flex column; below `md` the Documents and Photos block gets `order`". The page's blocks are plain siblings inside `div.py-3` (`EquipmentDetailView.vue:184-365`): the Raise ticket link, the edit button row, the Open tickets card, a `.row.g-3` (Details, Properties, Parts), `MetersCard`, Notes, History, `DocumentsCards`. `order-*` works only on flex items. § 5.3.2 says Print label follows "the same check the page uses for its other edit buttons": that is `canEdit` (`:78-80`), which is false on a scrapped node and while loading — so Print label would vanish on a scrapped machine and flicker on every reload. `canSeeRemovedReadings` (`:87`) is the bare permission check.

**Options.**
- a) **Recommended.** Wrap the node's blocks (from the Raise ticket link to `DocumentsCards`) in one `d-flex flex-column` container; give `DocumentsCards` the class `order-first order-md-last`-style placement **after** Open tickets: the Raise ticket link, the button row and the Open tickets card get `order-0`, Documents `order-1`, the rest `order-2`, all reset at `md`. Print label: `v-if` on `node.permissions.includes("equipment:edit")` (the bare key, as `canSeeRemovedReadings`), disabled while loading as today. Say whether a scrapped node keeps Print label (recommended: yes — the label on a scrapped machine may need reprinting for the scrap record).
- b) Move the `DocumentsCards` call up in the template and hide the duplicate at `md` — a second copy of the cards, which § 5.3.3 forbids.

### BR1-05 — minor — "Needed: <key>" would also prefix business refusals in the access log

**Problem.** § 5.5.5: "detail of a `denied_perm` row prefixed 'Needed: '". A `denied_perm` row has two sources: `_log_denied` marks the key (`auth_utils.py:488`), and a bare 403 without a mark logs the start of its message (`network_core.py:93`; § 9.4 names it). The second gives rows such as "Needed: You have no access to this unit" (`equipment.py:389`).

**Options.**
- a) **Recommended.** Prefix only when the detail is a permission key (`/^[a-z_]+:[a-z_]+$/`); show other details as they are. One line in `AccessLog.vue`, one unit-free rule the coder can read.
- b) Prefix every `denied_perm` detail and accept the odd rows.

### BR1-06 — minor — `roleLabel` leaves `it_admin` and `admin` as raw keys, which is UX-26's own complaint

**Problem.** § 5.5.5: "role through `roleLabel` … `it_admin` and `admin` labelled as `roleLabel` does, else as is". `roleLabel` (`siteRoles.js:23`) knows the six site roles and returns any other non-empty value unchanged, so the log keeps showing `it_admin` and `admin`. The access log's `role` is `display_role` (`access_core.py:130`): `admin`, a token role or a site role.

**Options.**
- a) **Recommended.** Add the two labels ("IT admin", "Admin") in `siteRoles.js`, as a small `OTHER_ROLE_LABELS` map read by a `displayRoleLabel(role)` the access log uses (`roleLabel` itself stays the Team dialog's, where those two never occur); one assertion in `siteRoles.test.js`.
- b) Keep raw keys for the two; say so in UX-26's text.

### BR1-07 — minor — two texts for one condition: the DB-down 503

**Problem.** § 5.7 row 2 gives `_db_unavailable` (`app.py:66`) "Yantra can't reach its database. Try again in a few minutes." and § 3 says `DB_LOST_TEXT` ("Database unavailable — try again shortly", `api_common.py:79`, the 503 of a connection lost mid-query) "stays". The same outage would show the user two different lines depending on when the connection died. CLAUDE-COMMON scope B: the same word for the same thing.

**Options.**
- a) **Recommended.** One constant in `api_common.py` with the new text, used by both handlers; `test_errors.py:44` changes with `test_masters_api.py:740`; the new test of § 8.1 covers both handlers.
- b) Keep two texts and accept it.

### BR1-08 — minor — UX-15's "lowered role = later in `SITE_ROLES` order" is not a privilege order

**Problem.** § 5.6.3 defines a lowered role as "later in `SITE_ROLES` order". `SITE_ROLES` is "the order the Team dialog offers them" (`config_rbac.py:44`): manager, engineer, supervisor, technician, operator, storekeeper. The supervisor and the storekeeper are off the maintenance ladder (`ROLE_INCLUDES`): engineer → supervisor is not "lower", technician → storekeeper is not either, and operator → storekeeper is counted as lower though it is a different job.

**Options.**
- a) **Recommended.** Show the line for every role change, worded as a change: "Saving changes access: <old row text> → <new role>." and, for a removed row, "Saving removes access: <row text>." No ranking needed; the user reads what changes.
- b) Define the ladder explicitly (manager > engineer > technician > operator; supervisor and storekeeper as side roles) in `siteRoles.js`. More rule for little gain.

### BR1-09 — minor — UX-11's premise does not hold: `DocumentsCards` already passes the kind; the Kind block can simply go

**Problem.** § 5.4.3: "`DocumentsCards.vue` passes the kind the user chose … to `DocumentUploadModal`; the modal shows no Kind radios when a kind is given." Both buttons already call `uploadModal.open('document')` and `uploadModal.open('photo')` (`DocumentsCards.vue:253,325`), and `open(kind)` seeds `form.kind` (`DocumentUploadModal.vue:82-86`). The only other upload path, `RaiseTicketView`, does not use this dialog. So a kind is always given: "when a kind is given" is always true, the Kind block (`:107-114`), the `photosOnly` prop and its consumer `:photos-only="!canEditDocs"` (`:365`), and the `watch(() => form.kind, clearFile)` become dead code.

**Options.**
- a) **Recommended.** Say it plainly: remove the Kind block, the `photosOnly` prop, and the kind watch; the title ("Add photo" / "Add document") names the kind. Also add `saveDisabledReason` "Enter a title" when the title is empty, so UX-05's new reason line explains the disabled *Upload* before a server round trip ("Title is required").
- b) Keep `photosOnly` as a guard against a future caller without a kind. A guard with no second use (CLAUDE-COMMON: no abstraction without a second real use).

### BR1-10 — minor — § 5.7 rows 17, 18 and 20 leave the rule to the coder, and two of them do not match the code

**Problem.**
- Row 20 says 'the "… id is required" texts of required selects → "Choose a {label}."' and "the coder finds each by grep". The code has two forms: `_parse_id(label)` gives "{label} is required" ("Class is required", `masters_core.py:143`), and the missing-field branches give "{Field} is required" ("Class id is required", `masters_core.py:303`, `equipment_core.py:360`, except `model_id` → `PICK_A_MODEL`). Which fields count as a select (every `*_id` field? `kind`, `unit`, `data_type`?) and which label each gets is not stated; `test_masters_core.py:385-404` asserts "Unit is required", "Kind is required", "Expected answer is required" for fields that are **not** record selects.
- Row 17: `_check_grantable` (`masters.py:826`) is shared by units **and trades** (`:1253,1292,1355`); trades have a `name`, not a `code`. "Unit {code} is inactive. Untick it or reactivate the unit." needs a per-table word and `row.get("code") or row["name"]`.
- Row 18 maps to `equipment.py:386` ("Unknown unit"), but the audit's row 18 was `_check_grantable`'s "Unknown {label} {record_id}" (`masters.py:836`, the id in the text), which the brief leaves as is.

**Options.**
- a) **Recommended.** State the rule: row 20 applies to the `*_id` fields parsed by `_parse_id` / `_parse_optional_id` and to the missing-field branch for those same fields, label = the field name without `_id`, capitalised ("Choose a class."); the non-select "is required" texts stay. Row 17: "{Unit|Trade} {code or name} is inactive. Untick it or reactivate it." Row 18: both `masters.py:836` ("That {label} no longer exists. Reload and try again.") and `equipment.py:386`. List `test_masters_core.py` and `test_equipment_core.py` in § 3 Tests as files the coder greps.
- b) Keep "the coder greps and lists" and accept the risk that the coder rewrites "Unit is required" too.

### BR1-11 — minor — § 5.10.4 departs from the base's Topbar rule without saying so

**Problem.** `SMTW-WebApp-Base.md:1273` (§ Topbar Design Principles) says: "Username shown as plain text; logout as an icon button or small link, **not a prominent button**." UX-02 does the opposite, on purpose and for a good reason (Plan.MD § 3 *Shared-device login*). CLAUDE-COMMON § Reference architecture: a departure from the base is pointed out; and the paste text of § 5.10.4 added beside that sentence would make the base contradict itself.

**Options.**
- a) **Recommended.** Name the departure in § 2 or D-list (a D11), and make § 5.10.4's paste text a **replacement** of the sentence at line 1273: "Username as plain text; logout a labelled button of at least 44 px when the app runs on shared devices, else an icon button or small link."
- b) Keep the base rule and make Yantra's top bar a recorded deviation in `.claude/CLAUDE.md` only. Then § 5.10.4 goes.

### BR1-12 — minor — § 8.4.21 cannot run where the brief puts it

**Problem.** "The bottom bar is reachable by Tab and opens with Enter — desktop logic test." The bottom bar is `display: none` above 576 px (`main.css:92-105`); on `desktop-chromium` there is nothing to Tab to. Playwright drives the keyboard on the phone emulation too.

**Fix.** Run it on `phone-chromium`, untagged (a logic test); drop "desktop".

### BR1-13 — minor — § 5.3.4 leaves the phone list's remaining controls and the card's second line to the coder

**Problem.** Not stated for below `md`: where *Show scrapped* (`EquipmentView.vue:365-368`), the property-filter line with its ✕ (`:351-364`, shown when `props` is set) and *Add equipment* go; whether `props` counts as one filter or as its condition count in *Filters (n)*; what the card's line 2 shows at a level other than `equipment` (the table shows `full_path` there, `:430`); whether the card keeps `role="link"`.

**Fix (recommended).** *Show scrapped* inside the Filters block; the property-filter line stays visible above the cards (it is the applied filter, and its ✕ is the way out); *Add equipment* right of the search box for editors; `props` counts as one filter; line 2 shows the unit at the `equipment` level and the path otherwise; the card is a `router-link` to the page (so it is a real link, UX-22's point).

### BR1-14 — minor — § 5.7 row 7 hides the server's own plain texts

**Problem.** Row 7 replaces "Could not load your profile: {err.message}" with a fixed "Could not load your account. Try again in a few minutes." After this step every message that can reach that line is already plain: the network failure (UX-06, `NO_CONNECTION_TEXT`), a 5xx without JSON (`NOT_ANSWERING_TEXT`), the DB 503 (row 2) and S059's `LOGIN_SERVER_DOWN_TEXT` (`auth_utils.py:61,291`: "Sign-in cannot be checked right now. The login server does not answer. Try again in a minute."). The fixed text would hide the last one, which S059 wrote for exactly this screen.

**Fix (recommended).** Row 7 shows `err.message` as it is (no prefix). The 401 branch (`stores/auth.js:84-85`) stays.

### BR1-15 — minor — § 3 Tests misses the frontend unit tests UX-12 changes

**Problem.** `frontend/tests/navigation.test.js:31` expects the operator's nav to include `"masters"`, `:53` the storekeeper's; both change. § 3 and § 8.2 say "new or extended" only.

**Fix.** List the two lines in § 3 Tests.

---

## Nits

- **BR1-16** (nit) § 2: ISO 9241-110's 2020 edition names the principles *suitability for the user's tasks, self-descriptiveness, conformity with user expectations, learnability, controllability, use error robustness, user engagement*; "error tolerance" is the 2006 edition's name. Name the edition and use its words. The WCAG 2.2 numbers (2.5.8 AA 24 px, 2.5.5 AAA 44 px, 2.1.1, 3.3.1, 3.3.3) and ISO/IEC 27001:2022 Annex A 8.1 *User endpoint devices* are right; drop "to verify".
- **BR1-17** (nit) § 1 H says the criticality badge "carries the same words as its `title`" (the option words), § 5.8.1 makes the `title` the long `CRITICALITY_HELP` line. Pick one (recommended: the option words as the badge `title`; the help lines under the form's select as `form-text`, where a phone shows them — a `title` never shows on touch, UX-05's own point). The list's criticality filter (`EquipmentView.vue:329`) also shows bare A / B / C: use `CRITICALITY_OPTIONS` there too.
- **BR1-18** (nit) § 5.7 row 3: "Your sign-in has expired. Sign in again." — while signed in there is no Sign in button. "Your sign-in has expired. Sign out, then sign in again."
- **BR1-19** (nit) § 5.7 row 9: today's text uses `{ip or 'unknown'}`; the new text with no address would read "Your own address unknown is not in the list". Keep a second wording for the unknown case.
- **BR1-20** (nit) § 5.3.1: the route accepts `[A-Za-z0-9]`; show the code upper-cased, as the label prints it (`labels_core.py:45`).
- **BR1-21** (nit) § 5.5.2: `btn-danger` for the Labels *Yes, save* marks a non-destructive save as dangerous; `btn-primary` there, `btn-danger` only on Network (a lock-out).
- **BR1-22** (nit) § 5.1.3: "Save or undo your changes first" — there is no Undo. "Save your changes first, or cancel them."
- **BR1-23** (nit) § 5.4.2: say where Remove's inline confirm shows after it is chosen from the "⋯" menu (recommended: in the row, below the title, as today's `:302-306`), since the menu closes on the tap.
- **BR1-24** (nit) § 5.5.1: a range typed as `10.24.0.1/16` and stored as `10.24.0.0/16` shows as both added and removed. Acceptable; say so, or compare after the same trim and lower-case the server uses before `parse_networks`.
- **BR1-25** (nit) § 3 Docs: `.claude/CLAUDE.md` § SMTW-Review's spec-to-step map needs S064 on `screens`, `equipment`, `labels`, `masters`, `readings`, `journeys` and a `settings` entry if the Settings tests get their own spec; the brief says "none expected".
- **BR1-26** (nit) § 5.6.4: the Team list's site select filters "people with a row at that site" — rows an engineer cannot see are masked by the server (`sees`, `masters.py:1121`), so the filter is on visible rows; say so.
- **BR1-27** (nit) § 8.4.1 and § 8.5.1: `expectDialogFits` (`e2e/support/dialogs.js:30`) already asserts Save and Cancel inside the viewport on every dialog a flow test opens, on both phones; test 1 can assert the full-screen class and the body's `overflow-y`, not fit alone.

---

## Checked and found consistent

- `FormModal.vue:157` has `modal-dialog modal-dialog-scrollable`; adding `modal-fullscreen-sm-down` is compatible with `expectDialogFits` (the dialog is no taller than the viewport; Save and Cancel inside it). No e2e test clicks outside a dialog or measures its margins.
- `provide`/`inject` is unused in `frontend/src` (D3's claim holds); slot content injects from the component whose subtree renders it, so `ActiveToggle` in `#footer-left` can inject FormModal's `dirty`.
- `useMasterForm.changeActive` sends `{active}` through `base.send`, whose `finish` closes the dialog (`useFormModal.js:74-92`): Reactivate drops edits as Deactivate does.
- `canSeeNavItem` handles `perms` (`navigation.js:20`); `canOpenRoute` follows the nav item and the router guard sends a non-editor to `landingPath` (`router/index.js:120-125`). The holders of the four edit keys are as § 5.2.3 says (`config_rbac.py`); the manager's six items stay (`screens.spec.js:110`); `/api/auth/me` sends the global union (`auth_utils.py:423`).
- `/masters` is linked only from the nav; the "Managed in Masters" hint follows `canEditModels` (`EquipmentDetailView.vue:363`).
- `_log_denied` marks `denied_perm` with the key before `_forbidden_message` is used (`auth_utils.py:483-517`); `classify_outcome` reads the mark first (`network_core.py:83-95`); `test_network_core.py:101` passes the literal and stays green.
- The old texts' test hits are as § 3 lists them: `test_documents_api.py:88,102,616`, `test_documents_core.py:62,158`, `test_access_control_api.py:200`, `test_equipment_api.py:130`, `test_masters_api.py:740`; `readings.spec.js:643`; `masters.spec.js:124-128,364,408,451,511,549-563` ("Equip Class" / "Equip Category"). No test asserts "Let in", "Unauthorized" in a body, "Retry the upload", the lifecycle help texts or "Logout". `equipmentLabels.test.js` checks keys only, so UX-20 / UX-24 do not break it.
- `settings:edit` is IT admin's; `settings:read` and `access_log:view` the manager's and IT admin's; `equipment:purge_documents` both (`config_rbac.py`), so § 5.5.3's card split and `screens.spec.js:71`'s replacement text ("Removed documents" or "Uploads") hold for both settings roles. `SettingsView.vue` already has `canEditSettings`; `onMounted` calls `loadStatus` and `loadTasks` today.
- Access-control's 5-minute claim: the Network card's own help text says "everywhere within 5 minutes" (`SettingsView.vue:336-338`, `NETWORKS_CACHE_SECONDS`).
- `label_url` strips trailing slashes and appends `/e/<code>` (`labels_core.py:49-52`); the sample code is text only (§ 9.5).
- `DocumentsCards` has one root (`div.row.g-3.mt-0`), so it can take a placement class once the parent is a flex column (BR1-04).
- `apiUpload` and `apiGetBlob` call `fetch` directly (`api.js:66,73`); `throwIfFailed` falls back to `statusText` for a non-JSON body (`:22`); an `AbortError` is a `DOMException`, not a `TypeError`, so the `TypeError` catch leaves it alone.
- The device checks of § 8.5 are the kinds the settings name (a phone's own keyboard, a gloved thumb, a real camera and HEIC) with account, network and machine; none is a check a browser could do.
- Track: full, as the brief says — RBAC-visible changes, more than 10 files.

---

## Feedback

- idea: `brief_facts.py` reported `readings/ReadingsSheet.vue`, `router/index.js` and `stores/auth.js` as "no such file" because the brief gives the folder in prose ("in `frontend/src/views/`"); resolving a trailing path against the code folders would cut three false rows (`scratch/brief-facts-S064.md:32,63,66`).
- idea: the facts file lists tests by code name, not by UI control; for a step that hides or renames controls, a grep of `frontend/e2e` for the aria-labels and button names the brief names (here *Print asset list*, `Select … for labels`, `Tickets`, `Category`) would have surfaced BR1-01's twenty lines in the orchestrator's own run (6 greps, about 10 minutes in this review).
- hindrance: a 27-item brief needs about 40 file reads to verify its claims; most time went to the claims that turned out false (BR1-02, BR1-04, BR1-09). A § "Verified in code" line per rule, saying which file:line the orchestrator opened, would let the reviewer skip the ones it did.
