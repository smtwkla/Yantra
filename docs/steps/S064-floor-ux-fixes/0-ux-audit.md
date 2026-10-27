# UX audit — screens built so far (20-10-2026)

Read-only audit of every screen under `frontend/src/views/` and `frontend/src/components/`,
plus the user-visible error strings in `backend/*.py` and the frontend. The checklist is the
"Use on the floor (UX)" bullet in `.claude/agents/brief-reviewer.md`, with the code-level checks
from `.claude/agents/code-reviewer.md`. Who uses what comes from `docs/Plant-Facts.md` § 5 and
`docs/Plan.MD` § 3 and § 6.

- **Floor**: operators, technicians, supervisors — phones (some gloved), shared kiosks, some
  low-literacy or Tamil-speaking. Today they reach: the equipment list, the equipment page (from
  the QR label `/e/<code>`), documents and photos (view only), Masters (read, `masters:read` is
  `*`), and the no-access / not-found pages.
- **Office**: engineers, managers, IT admin — desktop, sometimes a phone. Everything above, plus
  the edit dialogs, Masters editing, Team, Settings, Removed documents, the access log and the
  two print views.

Severity: **major** — the floor would not use it as built, or a significant action has no
confirm; **minor** — real friction; **nit** — polish. Ordered by severity, then floor before
office. Line numbers are as of today's working tree.

---

## Major

### UX-01 — `FormModal` does not scroll inside; Save can sit below the fold (major)

- **Screen**: every dialog (equipment add/edit/move/status, upload, edit title, all Masters and
  Team dialogs) — `frontend/src/components/FormModal.vue:108`
- **Who**: floor and office (any dialog opened on a phone)
- **Problem**: the dialog is a plain `modal-dialog`: the whole modal scrolls with the page and
  the footer (Cancel / Save, the discard bar, Deactivate) is at the bottom of the content. On a
  phone with the keyboard up, the Equipment dialog (Level, Site, Unit, Class filter, Model, Code,
  Name, Serial, Year, Criticality, Status, Notes) and the Team dialog push Save well off screen;
  the user must close the keyboard and scroll to find it.
- **Fix**: `modal-dialog modal-dialog-scrollable modal-fullscreen-sm-down` on line 108, so the body
  scrolls and the header and footer stay fixed, and the dialog uses the whole phone screen.
  Already planned in S018 (`docs/steps/S018-work-tickets/1-brief.md`, BR3-03, § 7 decision 12);
  it is recorded here because it is the single most important fix for phones, and **it may move
  into S023** so it lands before the ticket screens.

### UX-02 — Shared kiosk: who is signed in is small, and Sign out is a tiny icon (major)

- **Screen**: layout top bar — `frontend/src/components/layout/AppTopbar.vue:19-23`, `:50-57`
- **Who**: floor (kiosks on the extrusion line, sorting supervisors' shared devices)
- **Problem**: Plan.MD § 3 ("Shared-device login") decides that the screen *always shows who is
  logged in, with a large logout button*. As built, the name is grey text at 0.8 rem on phones and
  Sign out is a `btn-sm` icon (`fa-right-from-bracket`) with only a `title` tooltip — no word, a
  small target for gloved hands, and easy to miss, so the next person acts as the last one.
- **Fix**: on every width show the person's name in normal-weight dark text next to a full-size
  button with icon **and** the word "Sign out" (`btn btn-outline-secondary`, at least 44 px high);
  keep it in the top bar so it is on every page. No confirm needed (signing out loses nothing).

### UX-03 — QR label for a machine outside the user's units says the address "doesn't exist" (major)

- **Screen**: QR landing `/e/<code>` — `frontend/src/views/EquipmentByCodeView.vue:37`, rendering
  `frontend/src/views/NotFoundView.vue:18-22`
- **Who**: floor (the QR scan is the floor's main way in, Plan.MD § 6)
- **Problem**: an unknown code and a code at a unit the user cannot see both fall to the generic
  "Page not found — The address **/e/MCC2CMP001** doesn't exist in Yantra". A technician covering
  another unit, scanning a real label on a real machine, is told it does not exist and will
  report the label as broken. The URL echo is meaningless to a low-literacy user.
- **Fix**: give `/e/<code>` its own not-found text: "**MCC2CMP001** — not found, or not at your
  units. Ask your engineer if you should see it." with a large "Go to equipment list" button. Keep
  the single 404 (no leak of which case it is), just word it for both cases, as the equipment page
  already does (`EquipmentDetailView.vue:97-100`).

### UX-04 — Network ranges save has no confirm, though a wrong list locks IT admin out (major)

- **Screen**: Settings › Network — `frontend/src/views/SettingsView.vue:334-356`
- **Who**: office (IT admin)
- **Problem**: one tap on Save replaces the plant's internal ranges. The server only protects the
  saver's own address; IT admin at another site (or on the VPN) can be locked out within 5 minutes.
  The help text itself says "check each before saving", which is a confirm the screen leaves to
  memory.
- **Fix**: an inline confirm in the card, in the same style as Scrap and Delete for good:
  "Save these ranges? IT admin outside them will be refused within 5 minutes. **Yes, save** / No",
  listing the ranges removed and added compared with the stored list.

---

## Minor — floor

### UX-05 — Why Save is greyed out is shown only as a tooltip, which phones never show (minor)

- **Screen**: every dialog with `saveDisabledReason` — `frontend/src/components/FormModal.vue:136`;
  used by `EquipmentStatusModal.vue:28-31` ("Confirm with Yes", "No change"),
  `EquipmentMoveModal.vue:50-53` ("Choose a unit"), `DocumentUploadModal.vue:54-57` ("Choose a file")
- **Who**: floor and office on phones
- **Problem**: the reason sits in the button's `title`. On touch screens a disabled button with a
  tooltip just looks broken.
- **Fix**: render the reason as a small line of text in the footer, left of Cancel, when Save is
  disabled (`<span class="small text-secondary me-auto">{{ saveDisabledReason }}</span>`); keep
  the `title` for desktop.

### UX-06 — A dropped mobile-data connection shows the browser's raw text (minor)

- **Screen**: every load and save — `frontend/src/api.js:40` (the `fetch` call), `:22-23`
- **Who**: floor (phones on mobile data, Plant-Facts § 5)
- **Problem**: when the network drops, `fetch` throws a `TypeError` whose text is browser-specific
  ("Failed to fetch", "Load failed" on iPhone, "NetworkError when attempting to fetch resource.")
  and that is what the red alert shows. A proxy error without JSON shows "Bad Gateway" or "HTTP 502".
- **Fix**: in `request`, `apiUpload` and `apiGetBlob`, catch the `TypeError` from `fetch` and throw
  "No connection — check Wi-Fi or mobile data and try again"; in `throwIfFailed`, when the body is
  not JSON and the status is 5xx, use "Yantra is not answering — try again in a minute".

### UX-07 — The equipment page on a phone puts Print label first and the photos last (minor)

- **Screen**: equipment page (the QR target) — `frontend/src/views/EquipmentDetailView.vue:120-138`
  (Print label), `:157-193` (Details / Parts / History cards), `:201-206` (Documents and Photos);
  `frontend/src/views/equipment/EquipmentHistory.vue:11-16`
- **Who**: floor
- **Problem**: on a phone the cards stack: Details (11 rows), Parts, History, then Documents and
  Photos. History lists every event with no limit, so on an older machine the manual and the photos
  are several screens down — and they are what a technician scanning the label most wants today.
  The only button above the fold is "Print label", which no floor user needs.
- **Fix**: on narrow screens order the cards Documents/Photos → Parts → Details → History; show
  the last 5 history events with "Show all"; show "Print label" only to `equipment:edit` holders,
  or move it into the Details card. (Raise breakdown, which Plan.MD § 6 puts at the top of this
  page, comes with S017 — leave room for it.)

### UX-08 — The equipment list is a desktop table with a wall of filters at phone width (minor)

- **Screen**: equipment list — `frontend/src/views/EquipmentView.vue:246-288` (filters and
  buttons), `:303-317` (table head), `frontend/src/components/PagerBar.vue:19-26`
- **Who**: floor (technicians looking a machine up by name)
- **Problem**: at 360 px the first screen is seven `form-select-sm` selects, the search box, and
  three buttons (Print labels, Print asset list, Add equipment) before any row; the table has nine
  columns plus a label tick box and scrolls sideways. Every control is `-sm` (about 31 px high).
  The label ticks and print buttons are office jobs shown to everyone.
- **Fix**: on narrow screens put the search box first and full-width, fold the selects into a
  "Filters" collapse showing the count of active filters, hide the tick column and the two print
  buttons below `md`, and render each row as a two-line card (code + name, then status, unit).
  Drop `-sm` on the search box and pager buttons.

### UX-09 — The photo viewer can push its own buttons off a phone screen (minor)

- **Screen**: photo viewer — `frontend/src/components/documents/PhotoViewer.vue:100`, `:146-149`,
  `:111-135`
- **Who**: floor (looking at a machine's photos)
- **Problem**: `modal-xl modal-dialog-centered` with the image at up to 75 vh, plus header and
  footer, is taller than a phone screen, so Prev / Next fall below; there is no swipe, and the
  title is cut to one line.
- **Fix**: `modal-fullscreen-sm-down`, image `max-height` computed from the space left
  (e.g. `calc(100dvh - 9rem)`), large Prev / Next buttons beside the counter; swipe can wait.

### UX-10 — Four small icon buttons per document, the bin next to Download (minor)

- **Screen**: Documents card — `frontend/src/components/documents/DocumentsCards.vue:273-292`
- **Who**: floor (view) and office (edit) on phones
- **Problem**: on a phone each document row has Open, Download, Edit title and Remove as `btn-sm`
  icons with no words (`d-none d-sm-inline` hides "Open" / "Download"). A low-literacy user must
  guess the icons; the bin sits beside Download. Remove does confirm, so nothing is lost by
  accident, but the row is cramped.
- **Fix**: make tapping the title open the PDF (the main job); keep Download as one labelled
  button; move Edit title and Remove into a "⋯" menu at the row's end so the everyday and the
  destructive buttons are apart.

### UX-11 — The upload dialog asks again what the user just chose, and prefills a camera file name (minor)

- **Screen**: Add document / Add photo — `frontend/src/components/documents/DocumentUploadModal.vue:111-117`
  (Kind), `:72-80` (title prefill), `:133-135` (iPhone hint)
- **Who**: office on a phone at the machine (uploads need `equipment:edit`); floor once technicians
  may add photos
- **Problem**: the user tapped "Add photo" yet must see a Kind choice (radio buttons, small);
  a camera photo prefills the title with "IMG_20261020_143512", which is then saved as the title
  everyone sees; the iPhone line ("Camera › Formats › Most Compatible") is a support note, shown
  on every photo upload.
- **Fix**: drop the Kind radios (the button chose it; the title already says "Add photo"); when
  the file name looks like a camera name (`IMG_`, `PXL_`, `image`, digits only), leave Title empty
  and focus it with the placeholder "What does the photo show?"; show the iPhone note only after
  the server refuses a HEIC file.

### UX-12 — The floor's bottom bar offers Masters, which is not their job (minor)

- **Screen**: navigation — `frontend/src/stores/navigation.js:10`; bottom bar text size
  `frontend/src/assets/main.css:78`
- **Who**: floor
- **Problem**: `masters:read` is `*`, so every operator's bottom bar shows Equipment and Masters;
  Masters opens nine reference sections (sites, units, classes, models, failure codes, Team…)
  that an operator never needs ("nothing on it the user doesn't need"). The bar's labels are
  0.65 rem (about 10 px).
- **Fix**: show the Masters nav item only to holders of an edit key (`masters:edit`,
  `equipment:edit`, `people:edit`, `failure_codes:edit`) — the key `masters:read` still guards the
  API reads that pick-lists use. Bottom-bar labels at 0.75 rem.

### UX-13 — Error messages that are too long or too technical (minor)

- **Screen**: any — the backend's `ApiError` messages and validator messages, and the frontend's
  own
- **Who**: floor and office
- **Problem**: most messages are already short and plain (e.g. "Pick a model", "Scrap or move its
  parts first", "The unit is inactive"). The ones below show field names, internal ids, codes or
  developer wording, or explain a rule. "Reachable" says whether a normal use of the screens can
  show it; the unreachable ones are seen only after a bug or a hand-made request, so they rank
  lower but are cheap to fix together.
- **Fix**: replace with the rewrites in the table (one line: what is wrong, what to do).

| # | Where | Current text | Reachable | Rewrite |
|---|---|---|---|---|
| 1 | `backend/auth_utils.py:432` | Forbidden: requires 'equipment:edit' | Yes (stale screen, role changed) | You don't have permission for this. Ask your engineer or IT. |
| 2 | `backend/app.py:66` | Database unavailable: (2003, "Can't connect to MySQL server on 'db' …") | Yes | Yantra can't reach its database. Try again in a few minutes. |
| 3 | `backend/auth_utils.py:230`, `:242` | Unauthorized | Yes (expired session) | Your sign-in has expired. Sign in again. |
| 4 | `frontend/src/api.js:22-23` | HTTP 502 / Bad Gateway | Yes | Yantra is not answering. Try again in a minute. |
| 5 | `frontend/src/api.js:40` (browser text) | Failed to fetch / Load failed | Yes (mobile data) | No connection. Check Wi-Fi or mobile data and try again. |
| 6 | `frontend/src/stores/auth.js:104` | Cannot reach the server (Backend returned 502). Try again shortly. | Yes | Cannot reach Yantra. Check the network and try again. |
| 7 | `frontend/src/stores/auth.js:80` | Could not load your profile: Database unavailable: (2003, …) | Yes | Could not load your account. Try again in a few minutes. |
| 8 | `backend/access_control.py:34` | Yantra can be used from the plant network only for your role | Yes (IT admin off site) | Your role can use Yantra only on the plant network. |
| 9 | `backend/settings.py:211` | This would block your own address (1.2.3.4) — check every site's range before saving | Yes | Your own address 1.2.3.4 is not in the list. Add its range. |
| 10 | `backend/documents_core.py:32` | Only PDF documents and JPEG, PNG or WebP photos | Yes | This file can't be added. Use a PDF, or a JPEG or PNG photo. |
| 11 | `backend/documents_core.py:164`, `:170` | Photo too large (52.3 megapixels) | Yes | Photo too large. Take it at a lower resolution. |
| 12 | `backend/documents.py:66` | Retry the upload | Rare | The upload failed. Try again. |
| 13 | `backend/documents.py:78-79` | The record is deleted, but its file could not be removed from storage. Ask IT to remove it; the path is in the server log. | Rare | Deleted, but its file is still on the server. Tell IT. |
| 14 | `backend/equipment.py:73` | Code collision — retry | Rare | Could not give a code. Press Save again. |
| 15 | `backend/masters_core.py:194-195` | Code must be 1–8 characters: letters and digits, parts joined by single dots (e.g. NOI, 3.4) | Yes | Use up to 8 letters or digits, e.g. NOI or 3.4. |
| 16 | `backend/masters_core.py:95` | The name "none" is reserved; history uses it for no type | Yes | Choose another name; "none" is reserved. |
| 17 | `backend/masters.py:702` | Unit 12 is inactive and cannot be newly granted | Yes (two editors) | Unit FWMILL is inactive. Untick it or reactivate it. (use the code, not the id) |
| 18 | `backend/masters.py:700` | Unknown unit 12 | Rare | That unit no longer exists. Reload and try again. |
| 19 | `backend/masters.py:886`, `:889` | A login change must carry the person's sites / Sites are saved one site at a time, except with a login change | No | Reload the page and try again. |
| 20 | `backend/masters_core.py:282` | Site id is required / Class id is required | Yes (Save with an empty select) | Choose a site. / Choose a class. (name the field as the label does) |
| 21 | `backend/masters_core.py:141`, `backend/equipment_core.py:69` | Class must be a record id | No | Choose a class from the list. |
| 22 | `backend/equipment_core.py:55`, `backend/masters_core.py:210` | Status must be one of: in_service, standby, out_of_use, scrapped / Cause group must be one of: design, fabrication, … | No | Choose a status from the list. / Choose a cause group. |
| 23 | `backend/masters_core.py:250`, `:352`, `:368`, `:392`, `:396`, `:399` | trade_ids must be a list of trade ids / unit_ids must be a list of unit ids / sites must be a list / site_id must be a site id | No | Reload the page and try again. |
| 24 | `backend/masters_core.py:373` | Unknown role maint_xyz | No | Choose a role from the list. |
| 25 | `backend/api_common.py:79` | Request body must be a JSON object | No | Reload the page and try again. |
| 26 | `backend/api_common.py:100`, `:107`, `:130`; `backend/masters.py:128` | page must be a whole number from 1 … / status must be one of: … / from must be a date, DD-MM-YYYY or YYYY-MM-DD / site_id must be a number | Only via an edited URL | This link is not valid. Clear the filters and try again. |

The frontend validation texts ("Choose a file", "Larger than 20 MB", "60 labels at most — print
this group first", "Save the person first, then add their sites and roles.") are short and plain;
none need rewording beyond UX-05 (where they are shown).

## Minor — office

### UX-14 — The Team dialog grows with every site and unit, and a new person needs two saves (minor)

- **Screen**: Masters › Team — `frontend/src/views/masters/PeoplePanel.vue:387`, `:391-426`
- **Who**: office (engineers adding technicians, IT admin)
- **Problem**: each site row adds a role select, an All-units switch and a checkbox per unit; a
  manager with three sites makes the dialog several screens tall (worse with UX-01). Adding a
  technician is: Add person → name → Save → find them in the list → Edit → Add a site → choose →
  Add → tick units → Save — about ten taps for the commonest Team job.
- **Fix**: let the Add dialog take sites and roles at once (the server saves rows one by one after
  the person anyway, `saveRows`), and preselect the engineer's own site with Technician; when the
  person has more than two site rows, collapse each to its one-line text (`rowText`) with an Edit
  link that expands it.

### UX-15 — Removing a person's site role is a small ✕ with no warning of what Save will revoke (minor)

- **Screen**: Team dialog site row — `frontend/src/views/masters/PeoplePanel.vue:410-412`, `:441-444`
- **Who**: office
- **Problem**: the ✕ (`btn-sm`, icon only) sits right of the All-units switch; tapping it drops the
  row at once and Save revokes that access with no line saying so. Adding a login gets a clear
  warning ("Adding this login gives access as: …"); removing access gets none.
- **Fix**: when rows were removed or roles lowered, show the same kind of yellow line above the
  footer: "Saving removes access: SMTW Technician." Give the ✕ the word "Remove" and space it from
  the switch.

### UX-16 — Deactivate acts at once and silently drops other edits in the dialog (minor)

- **Screen**: every Masters edit dialog — `frontend/src/views/masters/useMasterForm.js:42-45`,
  `frontend/src/components/ActiveToggle.vue:22-29`
- **Who**: office
- **Problem**: Deactivate (after its Yes / No) sends only `{active}` and closes the dialog; a name
  the user had just corrected is thrown away with no "Discard your changes?" — the one path past
  the dirty guard other than Save. The inline "Deactivate X? Yes No" also crowds a phone footer
  that already holds Cancel and Save.
- **Fix**: when the form is dirty, disable Deactivate with the visible reason "Save or undo your
  changes first" (see UX-05); with UX-01's fixed footer, let the confirm wrap onto its own line.

### UX-17 — The label link address saves on one tap, though every later label carries it (minor)

- **Screen**: Settings › Labels — `frontend/src/views/SettingsView.vue:293-315`
- **Who**: office (IT admin)
- **Problem**: a typo saved here prints a wrong address on every label made afterwards, and labels
  are stuck on machines for years; the help text explains it, but Save is one tap.
- **Fix**: an inline confirm: "Labels printed from now on will open **https://…/e/…**. Save?
  Yes / No", showing a sample link with a real code.

### UX-18 — Team list has no search or site filter (minor)

- **Screen**: Masters › Team — `frontend/src/views/masters/PeoplePanel.vue:262-325`
- **Who**: office
- **Problem**: every person (direct staff and contractors, all sites) is one unfiltered table;
  with a plant's worth of people an engineer must scroll to find one technician, on a phone
  sideways too (seven columns).
- **Fix**: a search box (name or login) and a site select in the card header, as the Units and
  Models panels have.

### UX-19 — Settings shows a manager database and worker internals they cannot act on (minor)

- **Screen**: Settings — `frontend/src/views/SettingsView.vue:211-249` (Database), `:368-404`
  (Background tasks)
- **Who**: office (maintenance manager: `settings:read` for Removed documents and the access log)
- **Problem**: a manager opening Settings to restore a document first sees the database host and
  port, the MariaDB version, schema versions and the worker's task runs; Removed documents is the
  last card on the page.
- **Fix**: show the Database and Background tasks cards only with `settings:edit` (IT admin);
  for a manager put Removed documents first. A level-2 toolbar (as Masters has) would also do.

---

## Nits

### UX-20 — Criticality is a bare A / B / C (nit)

- **Screen**: list, page, parts tree and form — `frontend/src/utils/equipmentLabels.js:35`,
  `frontend/src/views/equipment/EquipmentFormModal.vue:266-268`
- **Who**: floor (reading the badge), office (choosing it)
- **Problem**: nothing on screen says A is the most critical; the form's options are bare letters.
- **Fix**: options "A — critical", "B — important", "C — normal" (wording to match
  `docs/Maintenance-Philosophy.md`'s criticality rule), and the same words as the badge's `title`.

### UX-21 — "No units" empty state sends people to the wrong person (nit)

- **Screen**: equipment list — `frontend/src/views/EquipmentView.vue:297`
- **Who**: floor
- **Problem**: "ask IT admin for unit access" predates S011; units now come from Team, which an
  engineer may change for technicians (the no-access page already says "ask IT or your engineer
  to add you in Team").
- **Fix**: "No units are given to you yet — ask your engineer or IT."

### UX-22 — Bottom-bar items are links with no href (nit)

- **Screen**: `frontend/src/components/layout/AppBottomNav.vue:28-38`
- **Who**: floor (kiosks with a keyboard)
- **Problem**: `<a role="button">` without `href` or `tabindex` cannot be reached with Tab or
  opened with Enter.
- **Fix**: use `<router-link>` (or `<button>`), as the sidebar uses buttons.

### UX-23 — Pager buttons are small on floor lists (nit)

- **Screen**: `frontend/src/components/PagerBar.vue:19`, `:23`
- **Who**: floor
- **Fix**: plain `btn` size (part of UX-08 if done together).

### UX-24 — Standards jargon in the everyday help texts (nit)

- **Screen**: Change status and the equipment form — `frontend/src/utils/equipmentLabels.js:21-26`,
  `frontend/src/views/equipment/EquipmentFormModal.vue:237`
- **Who**: office
- **Problem**: "In use (EN 13306 operating or idle)", "Laid up; no PM due (Yantra life-cycle
  status)", "A model of another class later keeps the code" read as notes to the developer. The
  standard is worth naming, but in the docs and Masters, not in the line the user reads to choose.
- **Fix**: "Running or ready to run", "Ready, kept as a spare", "Not in use for now — no PM is
  due", "Gone from the plant for good — cannot be undone"; the code line: "The code is given on
  Save and never changes."

### UX-25 — Masters toolbar: abbreviations and nine sections (nit)

- **Screen**: Masters — `frontend/src/views/MastersView.vue:25-26`
- **Who**: office
- **Problem**: "Equip Class" / "Equip Type" are abbreviations; nine sections wrap to three rows on
  a phone.
- **Fix**: "Classes" and "Types"; consider grouping Classes, Types, Manufacturers and Models under
  one "Equipment types" section with a switch, as Failure codes already does.

### UX-26 — Access log shows raw keys and "Let in" (nit)

- **Screen**: Settings › Access log — `frontend/src/views/settings/AccessLog.vue:17`, `:138`, `:148`
- **Who**: office
- **Problem**: the role shows as `maint_engineer`, a refusal's detail as `equipment:edit`, and the
  success badge reads "Let in".
- **Fix**: role through `roleLabel` (`utils/siteRoles.js`); detail prefixed "Needed: "; badge
  "Allowed".

### UX-27 — Background task status is a lower-case code (nit)

- **Screen**: Settings › Background tasks — `frontend/src/views/SettingsView.vue:388-390`
- **Who**: office
- **Fix**: "Done", "Failed", "Waiting", "Running".

---

## Already good

- **Typed input is never lost by accident**: a click outside does not close a dialog, and Esc / ✕ /
  Cancel on a changed form ask "Discard your changes? Keep editing / Discard" in the footer
  (`FormModal.vue`).
- **Irreversible actions confirm inline, naming the thing**: Scrap ("Scrap **X**? This is final —
  the record becomes read-only", and Save is replaced by Yes), document and photo Remove, Delete
  for good ("The file cannot be recovered"), Deactivate ("Deactivate **X**? Yes / No"). Remove is a
  soft delete that a manager can restore.
- **Controls the user may not use are hidden, never a 403**: edit buttons follow the node's site
  permissions; the equipment page says "Scrapped — this record is read-only" instead of offering
  buttons.
- **Empty, loading and error states are rendered everywhere**, each with Retry where a reload can
  help; filtered and unfiltered empty lists say different things.
- **No-access page** explains what to do ("ask IT or your engineer to add you in Team"), inside
  the normal shell with Sign out; a database outage says so instead.
- **The equipment list's filters live in the URL**, so Back returns to the same filtered page; the
  first search widens the level so a motor is found by its code.
- **Defaults instead of questions**: the only unit is preselected, the default site is preselected,
  a new part inherits criticality, the upload title is prefilled, the code is issued on save.
- **Uploads check size before sending**, saving mobile data; the PDF opens in a tab before the
  fetch so it is not blocked, and falls back to a download inside WhatsApp's browser.
- **Print views** open in a new tab, keep their switches in the link, and tell the user exactly how
  to print (100 %, portrait, measure one square).
- **Most backend messages are already one plain line** that says what to do ("Scrap or move its
  parts first", "Deactivate this class's models first", "Pick a model").
- **Update toast** prompts rather than reloading, so a half-typed entry on the floor is not lost.

## Needs a real phone to confirm

- Whether Save is reachable with the keyboard up in the Equipment and Team dialogs today (UX-01),
  on a small Android (360 × 640) and an iPhone SE.
- Tap accuracy with gloves on `btn-sm` buttons (31 px): the document row (UX-10), the pager, the
  top-bar Sign out (UX-02), the list's tick boxes.
- The photo viewer's height and whether Prev / Next stay on screen (UX-09); pinch-zoom on a photo.
- The native `<select>` pickers for long lists (models, units) on Android and iOS: searchable or not.
- The camera / gallery choice on "Add photo" on Android and iOS, and the file name the camera gives
  (UX-11); HEIC from an iPhone.
- PDF open in Chrome on Android, Safari on iOS and inside WhatsApp's in-app browser.
- The QR scan path from the phone camera app through Keycloak sign-in back to `/e/<code>`, and how
  long it takes on mobile data.
- Label legibility: the 2.6 mm site and name lines (`LabelsPrintView.vue:177-190`) read at arm's
  length on a machine, and whether a QR at 38 mm scans through grime and plastic sleeves.
- The Raspberry Pi kiosk: screen size, touch vs. mouse, whether the on-screen keyboard covers
  dialogs, and Sign out followed by the next person's sign-in.
- Readability in sunlight and with the grey `text-secondary` texts used for many hints.

## Count per severity

| Severity | Count | IDs |
|---|---|---|
| major | 4 | UX-01 to UX-04 |
| minor | 15 | UX-05 to UX-19 |
| nit | 8 | UX-20 to UX-27 |
| **Total** | **27** | |

## Suggested scope for a fix step — S023 (light track)

Vue and message wording only: no migration, no new endpoint, no permission key change.

**In**

1. `FormModal` scrollable with a fixed footer and full screen on phones (UX-01) — moved here from
   S018 BR3-03 if the user agrees, so S018 only relies on it; plus the visible disabled-Save reason
   (UX-05) and the dirty-form guard on Deactivate (UX-16), which touch the same footer.
2. Top bar: name and a large "Sign out" on every width (UX-02).
3. `/e/<code>` not-found text (UX-03).
4. Inline confirms on Settings › Network and Labels (UX-04, UX-17).
5. Network and 5xx messages in `api.js` and `stores/auth.js` (UX-06, table rows 4–7).
6. Equipment page order on phones and a short history (UX-07); Print label for editors only.
7. Photo viewer full screen on phones (UX-09); document row buttons (UX-10); upload dialog
   without Kind, camera-name title (UX-11).
8. The message rewrites in UX-13's table — backend strings and constants only (they are plain
   text, but the tests that assert them change too).
9. Nits UX-20 to UX-27 where they are one-line edits.

**Separate or later** (a design choice each, worth a brief of its own)

- The equipment list's phone layout (UX-08): card rows and a Filters collapse — a larger Vue change,
  best done with S017's "scan / find equipment" flow.
- Team: sites in the Add dialog, collapsed rows, the revoke warning, search (UX-14, UX-15, UX-18).
- Masters nav for edit-key holders only (UX-12) and the Settings card split (UX-19) — they change
  who sees what, so they need the user's call even though no key changes.
