# UX audit (20-10-2026) re-checked against the code on 28-10-2026

Companion to `ux-audit.md` (the original items, and UX-13's rewrite table). Read-only re-check by a
Claude agent; line numbers are from the working tree of 28-10-2026 (S063 uncommitted).

**Count: Fixed 0, Partly 3, Open 24, Obsolete 0.** No step took up the audit (its suggested "S023"
became Telegram alerts). The partial fixes came by the way in S017/S018. Several later steps made
items worse (more filters, more Masters sections, more bottom-bar items, more Settings cards).

| ID | Title (short) | Sev | Status | Evidence (file:line) | What remains |
|---|---|---|---|---|---|
| UX-01 | FormModal doesn't scroll; Save below the fold | major | Partly | `FormModal.vue:157` scrollable (S018); e2e `expectDialogFits` on Pixel 7 / iPhone 14 | `modal-fullscreen-sm-down`; keyboard-up case untested for Equipment / Team |
| UX-02 | Kiosk: name small, Sign out tiny icon | major | Open | `AppTopbar.vue:35-38`, `:103-105` | all |
| UX-03 | QR outside your units says "doesn't exist" | major | Open | `EquipmentByCodeView.vue:37` → `NotFoundView.vue:18-20` | own text for `/e/<code>` |
| UX-04 | Network ranges Save has no confirm | major | Open | `SettingsView.vue:159-171`, `:354-357` | inline confirm listing added/removed ranges |
| UX-05 | Save-disabled reason only a tooltip | minor | Open | `FormModal.vue:188`; S026 put it out of scope; local patches in `PropertyFilterModal.vue:320`, ticket Close | visible reason in FormModal for every dialog |
| UX-06 | Dropped connection shows raw browser text | minor | Open | `api.js:22-23`, `:40`, `:66`, `:73` | all |
| UX-07 | Equipment page: Print label first, photos last | minor | Partly | History capped at 10 (`EquipmentHistory.vue:8`); Raise ticket high (`EquipmentDetailView.vue:230-275`) | Print label first for all (`:209-227`); Documents/Photos now even lower (`:359-364`) |
| UX-08 | Equipment list: desktop table, wall of filters | minor | Open (worse) | `EquipmentView.vue:302-350`, `:384-401`; S063 adds Category select | all |
| UX-09 | Photo viewer pushes buttons off phone | minor | Open | `PhotoViewer.vue:100`, `:103`, `:148` | all |
| UX-10 | Four small icon buttons per document | minor | Open | `DocumentsCards.vue:275`, `:281-300` | all |
| UX-11 | Upload asks Kind again; camera file name as title | minor | Partly | photos-only mode (`DocumentUploadModal.vue:109`, S018) | Kind for editors; `IMG_…` title prefill (`:74-77`); iPhone hint always (`:131`) |
| UX-12 | Floor bottom bar offers Masters; tiny labels | minor | Open (worse) | `stores/navigation.js:14`, `config_rbac.py:133`, `main.css:125` | hide Masters from floor; bigger labels |
| UX-13 | Error texts too long / technical | minor | Open | rows of the audit table unchanged (`app.py:66`, `auth_utils.py:277,295,492`, `documents_core.py`, `masters.py:833,835,1216,1219`, `api_common.py`, `stores/auth.js:86,108-111`) | apply the rewrite table |
| UX-14 | Team dialog grows; new person needs two saves | minor | Open | `PeoplePanel.vue:391`, `:395-434` | all |
| UX-15 | Removing a site role: small ✕, no warning | minor | Open | `PeoplePanel.vue:414-416`, `:445-448` | all |
| UX-16 | Deactivate acts at once, drops edits | minor | Open | `useMasterForm.js:42-45`, `ActiveToggle.vue:21-28` | disable while dirty, with reason |
| UX-17 | Label link address saves on one tap | minor | Open | `SettingsView.vue:296-317` | confirm with sample link |
| UX-18 | Team list: no search or site filter | minor | Open | `PeoplePanel.vue:262-283` | all |
| UX-19 | Settings shows DB / worker internals | minor | Open (worse) | `SettingsView.vue:214-252`, `:373-409`, `:413` | edit-only cards; Removed documents first |
| UX-20 | Criticality bare A/B/C | nit | Open | `equipmentLabels.js:36`, `EquipmentFormModal.vue:348-350`, `CriticalityBadge.vue:12-14` | words + title |
| UX-21 | "No units" sends to IT admin | nit | Open | `EquipmentView.vue:378` | wording |
| UX-22 | Bottom-bar items links without href | nit | Open | `AppBottomNav.vue:28-38` | `<router-link>` |
| UX-23 | Pager buttons small | nit | Open | `PagerBar.vue:19`, `:23` | normal size |
| UX-24 | Standards jargon in help texts | nit | Open | `equipmentLabels.js:22-27`, `EquipmentFormModal.vue:293-294` | plain texts |
| UX-25 | Masters toolbar abbreviations, many sections | nit | Open (worse) | `MastersView.vue:26-39` (12 sections); S063 adds "Equip Category" | spell out; group |
| UX-26 | Access log raw role keys, "Let in" | nit | Open | `AccessLog.vue:17`, `:138`, `:148` | `roleLabel`, "Allowed" |
| UX-27 | Task status lower-case code | nit | Open | `SettingsView.vue:393-395` | Done / Failed / Waiting / Running |

## Fix suggestions for today's code

**Major**
- UX-01: add `modal-fullscreen-sm-down` at `FormModal.vue:157` (also eases UX-16's footer).
- UX-02: name in dark text; full-size "Sign out" button with word and icon, ≥ 44 px.
- UX-03: own text in `EquipmentByCodeView.vue`: "<code> — not found, or not at your units. Ask your engineer." plus a large "Go to equipment list" button.
- UX-04: inline "Yes, save / No" listing ranges added and removed.

**Minor**
- UX-05: show `saveDisabledReason` as a small line in FormModal's footer when Save is disabled.
- UX-06: catch fetch's `TypeError` in `request`, `apiUpload`, `apiGetBlob` → "No connection — check Wi-Fi or mobile data"; 5xx without JSON → "Yantra is not answering — try again in a minute".
- UX-07: Print label for editors only; on phones Documents and Photos above Properties, Meters, History.
- UX-08: on phones search first and full width, selects folded into "Filters (n)", no ticks or print buttons, rows as two-line cards. Best after S063 lands.
- UX-09: photo viewer full screen on phones; image sized from `100dvh` minus header and footer.
- UX-10: title opens the PDF; labelled Download; Edit title and Remove in a "⋯" menu.
- UX-11: hide Kind after "Add photo" / "Add document"; empty title for camera names; iPhone hint only after a HEIC refusal.
- UX-12: Masters only for holders of an edit key; bottom-bar labels 0.75 rem.
- UX-13: apply the rewrite table, starting with what a normal user sees.
- UX-14/15/18 (Team): sites in the Add dialog; collapse rows beyond two; "Saving removes access: …" line; ✕ labelled "Remove"; search and site select.
- UX-16: `saving || dirty` on ActiveToggle's `disabled`, reason "Save or undo your changes first".
- UX-17: inline confirm showing a sample label link with a real code.
- UX-19: Database and Background tasks cards for `settings:edit` only; Removed documents first for managers.

**Nits**: UX-20 "A — critical / B — important / C — normal"; UX-21 "No units are given to you yet — ask your engineer or IT."; UX-22 router-links; UX-23 normal-size pager; UX-24 plain lifecycle texts, "The code is given on Save and never changes."; UX-25 "Classes", "Types", "Categories"; UX-26 `roleLabel`, "Needed: ", "Allowed"; UX-27 Done / Failed / Waiting / Running.

## Device checks

Partly covered: Save with keyboard up (e2e without keyboard; device-check rows only for ticket dialogs: 6, 7, 11, 12, open); QR through Keycloak on mobile data (D2, D3, open); labels (rows 1, 2; not text readability at arm's length); camera (row 5, Raise ticket only); thumb targets (rows 26, 32, 33; not gloves on `btn-sm`, document row, pager, Sign out); Sign out (row 21, push only, not next kiosk user); sunlight (row 31, ticket tints only).
Not covered: photo viewer height and pinch-zoom, native `<select>` on long lists, opening a PDF in Chrome/Safari/WhatsApp, the Raspberry Pi kiosk.
