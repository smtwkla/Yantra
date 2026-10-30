```
Step: S068 — Improvement record: screens
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 30-10-2026
Track: full
Baseline: 32eb122 + uncommitted S066 + S067 (coded first)
Status: Done (committed 84c7d05, adopted 30-10-2026; checks: 8 auto; row 49 optional)
From: R05.1 (second half; backend in S067)
```

# S068 — Improvement record: screens

## 1. What will be built

R05.1 was split at the API (S067 § 9, *The split*). **S067** builds the improvement record, its
rules and its API (`docs/steps/S067-improvement-record/1-brief.md`). **This step builds the
screens** on that API, exactly as S067 § 6 states it. It adds no route, table or key.

1. **`"Start improvement"` on the ticket page.** Shown when the ticket detail says
   `can_start_improvement` (S067 § 5.3: back in service or closed, not a not-a-fault, in no open
   improvement, and `improvement:edit` at the ticket's site). It opens the dialog *Start
   improvement*: **Title** (filled from the machine code and the symptom), **Problem** (filled from
   the ticket's *What is wrong?*, else the symptom), **Lead** (the user, when the user may lead).
   *Start improvement* saves it and opens the improvement page.
2. **The improvement page** (`/tickets/improvements/<id>`, mock-up
   `docs/roadmap/R05-mockups/02-analysis.html`, left half):
   - the header: the serial, the state badge *Analysing*, the title, and "Started 29-10-2026 11:40
     by Priya (engineer) · lead Priya (engineer)" (the full `name`, as the app shows names
     elsewhere; BR1-08);
   - the card *The problem* with `"Edit"`: *Where* (the machine, linked, and its unit), *What
     happened* (the problem text), *Loss* ("1 ticket, 1 breakdown · down 2 h 25 min");
   - the card *Tickets (n)* with `"Add ticket"`: one row per linked ticket: the serial (linked),
     the intensity badge, the time it happened, and "symptom · cause · down 2 h 25 min". A remove
     button shows on each row the detail marks `removable` (S067 § 5.3).
3. **Add ticket.** A dialog with a search box and a radio list of tickets: with no search, the
   newest tickets of the improvement's machine; with text, any ticket of the site (serial or text).
   `"Add ticket"` adds the chosen one (BR1-04).
4. **Remove ticket** (a scope addition beyond R05.1, S067 D9): a confirmation, then the ticket is
   off the improvement. The machine's last ticket shows no remove button (S067 § 5.3, BR1-02).
5. **The ticket page shows the link:** "Analysed in IM-2026-10-001 · Analysing", in the box where
   *Repeat of* shows.
6. **A tab *Improvements* on the Tickets page** (Q1.2 a; mock-up `07-improvements.html`, left). Two
   tabs above the ticket list, *Tickets* and *Improvements*. The *Improvements* tab lists the
   improvements, *Open* or *Closed*, with a *Unit* filter. Each row: serial, state, lead, title,
   and the loss. No new nav item.

**After it:** the team starts IM-2026-10-001 from TK-2026-10-002 (the dusty contactor) on a phone
and writes the problem down. R05.2 adds the why-why in the page's right half.

### Out of scope

- Everything S067 builds (tables, rules, API, keys), and everything S067 § 1 *Out of scope*
  leaves to later items (why-why R05.2, countermeasures R05.3, states, history and close R05.4,
  alerts R05.5, lessons R05.6, register R05.10, *Suggested* R05.8).
- The yellow hint on the ticket page (mock-up 01, R05.8, deferred).
- The help box "Ticket's cause and root cause are different things" (R05.2).
- A mark on the ticket list's rows; the machine's criticality on the improvement page; counts on
  the *Open* / *Closed* choice.

## 2. Standards and practice

The standards behind the record are S067 § 2 (TPM focused improvement, ISO 9001 § 10.2.1 (a)(b),
§ 10.2.2, § 7.5.3 with its recorded departure, ISO 14224, EN 13306, ISO 27001 A.5.15 / A.8.2).
This step adds the screens, where two practices apply:

- **TPM — focused improvement, visible to the floor.** In plain words: TPM wants operators to see
  the analysis of the losses on their machines, not only engineers. The tab sits beside the
  tickets the operators already use, and the ticket page tells them its failure is being analysed
  ("Analysed in …"). Q1.2 a and Q1.3 a.
- **ISO 27001 A.5.15 (access control)**, on screen. In plain words: show each person only what
  their role allows. Every control follows the API's `permissions`, `is_open`, `removable` and
  `can_start_improvement`, so no button ends in a refusal; a refused page shows a plain line
  (BR1-05).

## 3. Where

### Frontend

- `frontend/src/router/index.js`: routes `improvements` (`/tickets/improvements`, title
  "Tickets") and `improvement-detail` (`/tickets/improvements/:id(\\d+)`, title "Improvement").
  Both paths start with `/tickets/`, so the *Tickets* nav item stays lit (`isActivePath`,
  `frontend/src/stores/navigation.js:55`). Neither is a nav item, so `canOpenRoute` lets them
  through; the API's 403 / 404 is the gate, as for `/tickets/:id`.
- `frontend/src/components/TicketsTabs.vue` (new): the two tabs `"Tickets"` and `"Improvements"`
  as `router-link`s in `nav nav-tabs` (the Me page's look, `frontend/src/views/MeView.vue:131`).
  Shown only when the user holds `improvement:read` somewhere (`userPermissions`). The active tab
  is chosen by the route name (BR1-05): *Tickets* gets the class `active` when `route.name ===
  "tickets"`, *Improvements* when it is `"improvements"` or `"improvement-detail"`, with
  `aria-current="page"` as `MeView.vue:131-138`. Not by `router-link-active`, which matches
  `/tickets` on `/tickets/improvements` too (a prefix match).
- `frontend/src/views/TicketsView.vue`: `TicketsTabs` above the filter row.
- `frontend/src/views/ImprovementsView.vue` (new): the list (§ 5.5), on the pattern of
  `TicketsView.vue` (filters in the URL query, `PagerBar`).
- `frontend/src/views/ImprovementDetailView.vue` (new): the page (§ 5.4), on the pattern of
  `TicketDetailView.vue` (not found, forbidden, load error).
- `frontend/src/views/improvements/ImprovementDialog.vue` (new): *Start improvement* and *Edit
  improvement*, one `useFormModal` (§ 5.2).
- `frontend/src/views/improvements/AddTicketDialog.vue` (new): the ticket picker (§ 5.3).
- `frontend/src/views/TicketDetailView.vue`: `"Start improvement"` in the action bar; the
  "Analysed in …" line in the repeats box (`frontend/src/views/TicketDetailView.vue:289`).
  S066's uncommitted `TicketShare` lines in the same file stay as they are.
- `frontend/src/utils/improvementLabels.js` (new, pure): `IMPROVEMENT_STATE_LABELS`,
  `improvementStateLabel`, `lossText`, `defaultTitle`, `defaultProblem`,
  `IMPROVEMENT_STATE_FILTERS`.

### Tests

- `frontend/tests/improvementLabels.test.js` (new).
- `frontend/e2e/improvements.spec.js` (new), § 8.1.
- `frontend/e2e/screens.spec.js`: the two routes (§ 8.1, BR1-10).
- `frontend/e2e/tickets-work.spec.js`: runs again (§ 8.2); no line is expected to change.

### Docs (housekeeping, by the coder)

- `docs/Plan.MD` § 6 *Screens*: the *Improvements* tab of *Tickets* and the improvement page.
- `.claude/CLAUDE.md` § SMTW-Review: the spec map gains `improvements` S067/S068, and `screens`
  keeps "every route".
- `docs/steps/device-checks.md`: the row of § 8.3.

**File count:** 13 code and test files (9 code, 4 tests), 3 docs. The router is shared code (settings:
*Shared code*), so the whole browser suite runs again at the end (§ 8.4).

## 4. Data model

None. The screens read and write only through S067 § 6.

## 5. Rules

### 5.1 The ticket page

- **`"Start improvement"`**: in the action bar, `btn btn-outline-primary btn-lg`, icon
  `fa-solid fa-magnifying-glass`, after the chain moves and before `"Not fixed — raise again"`.
  Shown only when `ticket.can_start_improvement` is true; hidden, not disabled, otherwise (D3). On
  a closed ticket it is usually the only button.
- **The line**: in the box of *Repeat of* / *Came back as*, one `div` per entry of
  `ticket.improvements`: "Analysed in <router-link IM-2026-10-001> · Analysing" (the state through
  `improvementStateLabel`). The box shows when any of the three has content. A `div` of its own,
  so the specs that read "Repeat of" and "Came back as" (`frontend/e2e/tickets-work.spec.js:168`,
  `:177`, `:180`, `:298`) keep matching one element each.
- **Lead default**: when the dialog opens it loads `GET /api/improvements/leads?ticket_id=<id>`; the
  lead is the user's person (`userPersonId`) when it is in that list, else none.

### 5.2 The dialog *Start improvement* / *Edit improvement*

`ImprovementDialog.vue`, one `useFormModal({ path: "/api/improvements", … })`
(`frontend/src/composables/useFormModal.js:20`):

- *Start*: `openCreate(seed)` with `seed = {ticket, leadId}`; `blank(seed)` gives `{ticket_id,
  title: defaultTitle(ticket), problem: defaultProblem(ticket), lead_id: leadId ?? ""}`.
  `ticket_id` is not a rendered field, so its refusals (S067 § 5.3) show at the top (`modalError`).
- *Edit*: `openEdit(improvement)`; `fromRecord` gives `{title, problem, lead_id}`; leads from
  `GET /api/improvements/leads?improvement_id=<id>`. When the current lead is not in that list
  (`lead.may_lead` false or `lead.active` false), the select lists them last, marked "(not a lead
  now)", so an edit of the text alone keeps them (S067 § 5.6 does not check an unchanged lead).
- Fields: **Title** (input, `maxlength` 120, help "The machine and what went wrong, in one line"),
  **Problem** (textarea, 5 rows, `maxlength` 2000, help "What happened, as you saw it. The cause
  comes later."), **Lead** (select, "Choose a lead" first, then the leads by name).
- Buttons: `"Start improvement"` / `"Save improvement"`; `"Cancel"`. After a start the router goes
  to the new improvement's page; after an edit the page takes the answer.
- **`defaultTitle(ticket)`**: `"<machine code>: <symptom label>"`, or the first line of the
  description when there is no symptom, cut to 120 characters. Example: "HP003: Won't start".
- **`defaultProblem(ticket)`** (BR1-08): the ticket's description; when it has none (a ticket with
  a symptom may have no description), the symptom label ("Won't start"); cut to 2000. So the
  common case is one tap on the ticket page, a glance at the filled fields, one tap on
  `"Start improvement"`.
- A load error of the lead list shows at the top of the dialog; the save still sends what is chosen.

### 5.3 The dialog *Add ticket* (BR1-04)

`AddTicketDialog.vue`, a form like every other dialog, so `expectDialogFits` applies unchanged:

- A search box `"Search serial or text…"` (debounced, as the Tickets list), then a radio list of up
  to 10 tickets:
  - no search: the newest tickets of the improvement's machine
    (`GET /api/tickets?equipment_id=<machine>&state=all&per_page=10`);
  - with text: `GET /api/tickets?site_id=<unit.site_id>&state=all&q=<text>&per_page=10`. The site
    id is the detail's `unit.site_id` (S067 § 6, added for this; BR1-04).
- Rows already in this improvement and rows with `not_a_fault` (BR1-09) are left out. Each row: a
  radio, the serial, the intensity badge, the state, the symptom. Empty: "No tickets match."
- Footer: `"Cancel"` and `"Add ticket"` (disabled until a row is chosen). `useFormModal`'s `save`
  with `path` `/api/improvements/<id>/tickets` and `toBody` → `{ticket_id}`. The form's field is
  `ticket_id`, so a refusal (S067 § 5.3, e.g. "TK-… is already in IM-…") shows beside the list.
- After an add the dialog closes and the page takes the answer.
- The list API is the Tickets list's (`backend/tickets.py:510`); it needs `ticket:read`, which every
  `improvement:edit` holder has.

### 5.4 The improvement page

- **Layout**: one column on a phone: the header, *The problem*, *Tickets*. On a wide screen the two
  cards sit in a `col-lg-6` column, leaving the right half for R05.2's why-why (mock-up 02).
- **Buttons** (BR1-11): `"Edit"`, `"Add ticket"` and the remove icon button use the ticket page's
  size, `btn btn-outline-primary` (`frontend/src/views/TicketDetailView.vue:306`), not the
  mock-up's small buttons: gloved thumbs.
- **Who sees them**: `"Edit"` and `"Add ticket"` when `permissions` holds `improvement:edit` and
  `is_open` is true; the remove button on a row when `removable` is true.
- **A ticket of another machine** (S067 BR2-01): the row shows the ticket's `machine.code` before
  the symptom ("HP005 · Door not sensed · …") when it differs from the improvement's machine. So
  the user sees why the improvement's machine's last ticket has no remove button.
- **Remove** (BR1-01), inline on the row, the panels' pattern (`confirmingRemoveId`, as
  `LabourPanel.vue:153-156` and `PartsPanel.vue:187-190`): icon `fa-solid fa-link-slash`,
  `aria-label` "Remove TK-2026-10-005 from this improvement". A tap replaces the row's button with
  the line "Remove TK-2026-10-005 from IM-2026-10-001? The ticket stays as it is." and
  `"Remove ticket"` (`btn-danger`) and `"Cancel"`. A refusal shows under it, as `unassignError` does
  on the ticket page. No dialog, so no fit check.
- **One answer, one page copy** (BR1-09): every write (start, edit, add, remove) answers with the
  whole detail (S067 § 6), which replaces the page's copy, as the ticket page's writes do. So the
  loss line, the header and the *Tickets* rows always agree.
- **The header line**: "Started <created_at, DD-MM-YYYY HH:MM> by <created_by_name> · lead
  <lead.name>".
- **Not found** (404): "Improvement not found, or not at your units." with a link "Back to the
  list"; **forbidden** (403): "You can't see this improvement."; a load error with `"Retry"`; all as
  the ticket page (`frontend/src/views/TicketDetailView.vue:204-212`).

### 5.5 The list (the *Improvements* tab)

- `TicketsTabs`, then a filter row: a select `aria-label` "State" (`"Open improvements"`,
  `"Closed improvements"`), a select `aria-label` "Unit" (`"All units"`, then the user's units as
  on the Tickets list, `filterableUnits`). The state, unit and page live in the URL query.
- Rows as a `list-group`, each a link to the page: line 1 the serial, the state badge, "lead
  Priya (engineer)" at the right (the full `name`, BR1-08); line 2 the title; line 3 the loss
  (`lossText`).
- Empty: *Open*: "No open improvements." and, only when `userPermissions` holds
  `improvement:edit` (BR1-03), "Start one from a ticket that is back in service or closed.";
  *Closed*: "No closed improvements yet."; filtered: "No improvements match these
  filters."; no units: `NO_UNITS_TEXT`.
- **A 403** (BR1-05; the route is not a nav item, so a storekeeper can type it): "You can't see
  improvements." with no `"Retry"`, as the ticket page shows its 403. Other errors: the load error
  with `"Retry"`.

### 5.6 One loss text (BR1-12)

`lossText(loss)` gives one shape on the page and in the list: "2 tickets, 1 breakdown · down
1 d 7 h"; "1 ticket, 0 breakdowns · no downtime" when the downtime is 0. The duration is
`minutesText` with its default (BR1-02), which counts days from 24 h on
(`frontend/src/utils/ticketLabels.js:272`), so the loss reads as the ticket page's *Down for* and
the ticket rows' "down …" on the same page.

### 5.7 Words for the floor

The page uses the ticket page's words (symptom, cause, down, breakdown). "Improvement" is the
plain word chosen at Q0.1 (not "RCA"). The ticket page gains only "Analysed in …" and one button.
The state label is "Analysing".

### 5.8 The database down

Every call goes to S067's routes, which answer 503 while the database is down (S067 § 5.8). The
list and the page show the load error with `"Retry"`; a dialog shows the error at the top.

## 6. API

None new. The screens use S067 § 6 as it stands: `GET /api/improvements`,
`GET /api/improvements/<id>`, `POST /api/improvements`, `PUT /api/improvements/<id>`,
`POST /api/improvements/<id>/tickets`, `DELETE /api/improvements/<id>/tickets/<ticket_id>`,
`GET /api/improvements/leads`, the ticket detail's `improvements` and `can_start_improvement`, and
the existing `GET /api/tickets` for the *Add ticket* list. If S067's review rounds change § 6,
this brief follows before it is coded.

## 7. Design decisions

- **D1. A tab on Tickets through two routes under `/tickets/`** (Q1.2 a). Each tab is its own route,
  so the ticket filters and the improvement filters never mix in one URL query, and the nav keeps
  *Tickets* lit by its path prefix. Rejected: a `?tab=` query on `/tickets` (one view with two
  filter sets and two loaders); a nav item *Improve* (Q1.2 b, not chosen).
- **D2. One dialog for start and edit.** The fields are the same; `useFormModal` already switches
  between create and edit. Rejected: two dialogs.
- **D3. `"Start improvement"` is hidden, not disabled, when not allowed.** A disabled button would
  need a reason on a phone for five different cases; the common one (already analysed) shows as the
  "Analysed in …" line. Rejected: disabled with a reason.
- **D4. Fields prefilled from the ticket.** Title from the machine and symptom; problem from *What
  is wrong?*, else the symptom. The engineer edits rather than retypes. Rejected: empty fields.
- **D5. *Add ticket* is a form with radio rows and a footer** (BR1-04). It has the shape of every
  other dialog, so the shared `expectDialogFits` fits it with no change to `e2e/support/`.
  Rejected: tap-to-add rows (one tap less, but a `close-only` footer the helper cannot measure,
  and a shared-code change).
- **D6. The controls follow the server's flags** (`can_start_improvement`, `is_open`, `removable`,
  `permissions`). The frontend decides nothing about states or the removal rule. Rejected:
  rebuilding the rules in the frontend (CLAUDE-COMMON *Backend heavy, frontend light*).

## 8. Tests and acceptance

### 8.1 Automated (e2e, targeted: `improvements.spec.js`, `screens.spec.js`, `tickets-work.spec.js`)

Set-up by API: a ticket raised on the seed extruder with *Already fixed* (S018 A1), so it is back
in service (`raiseByApi`, `frontend/e2e/support/tickets.js:27`). The seed engineer is "Priya
(engineer)" at SMTW, all units (`tooling/e2e/seed_e2e.py:42`). Each test makes its own tickets and
improvements.

- **important** S068: the engineer opens a back-in-service ticket, taps `"Start improvement"`,
  sees the title and problem filled, saves, lands on the improvement page with *Analysing* and the
  ticket in *Tickets (1)*; back on the ticket, "Analysed in IM-… · Analysing" shows and
  `"Start improvement"` is gone.
- **important** S068: the engineer adds a second ticket of the same machine through *Add ticket*
  (chooses its row, taps `"Add ticket"`); *Tickets (2)* and the *Loss* line change, and both rows
  show a remove button (two tickets of the machine). The engineer removes the second through the
  inline confirmation; the one row left shows no remove button (the machine's last ticket). The
  test calls `expectNoSidewaysScroll(page)` (`frontend/e2e/support/dialogs.js:49`) once on the
  improvement page (BR1-06); a fit helper inside a flow test does not tag it `@device`.
- S068: the *Improvements* tab on Tickets lists the improvement under *Open improvements*; the
  *Unit* filter to another unit hides it; *Closed improvements* shows "No closed improvements yet."
- S068: the operator opens the improvement page: no `"Edit"`, no `"Add ticket"`, no remove
  button; the ticket page shows the "Analysed in" line and no `"Start improvement"`.
- S068: *Add ticket* with a ticket already in another open improvement shows "TK-… is already in
  IM-…" beside the list.
- S068: the storekeeper types `/tickets/improvements` and sees "You can't see improvements." with
  no `"Retry"`.
- `screens.spec.js` (BR1-10): its `beforeAll` ticket is raised without *Already fixed*, so it
  cannot start an improvement. The `beforeAll` raises a second ticket as the engineer (who holds
  `ticket:restore` at SMTW) with the body's `restore: { person_id: <kannan> }` (*Already fixed*,
  `tickets_core._restore_block`, `backend/tickets_core.py:207`: the restore move's fields; BR1-07),
  then starts an improvement from it by API. The same body sets up the tickets of
  `improvements.spec.js`. Two rows:
  `/tickets/improvements` (title "Tickets", shows the combobox "State", `TICKET_ROLES`) and
  `/tickets/improvements/<id>` (title "Improvement", shows the serial, `TICKET_ROLES`).
- Each dialog opened calls `expectDialogFits`. No test is `@device`: none checks a layout.

### 8.2 Existing tests that run again

- `frontend/e2e/tickets-work.spec.js` (S066's uncommitted share test included): a back-in-service
  or closed ticket's action bar gains `"Start improvement"` for the engineer. Checked: no spec
  counts the action bar's buttons (`.action-bar` is used at `tickets-work.spec.js:97`, `:100`,
  `:140` and `tickets-parts.spec.js:228`, each for one named button or the bar's top). The test
  at `tickets-work.spec.js:161` clicks the neighbouring `"Not fixed — raise again"` by its role and
  name, as the operator, who never sees `"Start improvement"`, so the new button does not touch it. The
  "Analysed in" line is its own `div` (§ 5.1), so `getByText("Repeat of")` and `getByText("Came
  back as")` still match one element.
- **The tab label `"Tickets"`** is also the nav item's. On `/tickets` a locator `getByRole("link",
  { name: "Tickets", exact: true })` would match two visible links (the bottom bar's and the tab).
  Checked: no spec uses `navItem(page, "Tickets")` or such a link locator today
  (`frontend/e2e/support/nav.js:5`; `frontend/e2e/floor.spec.js:78` reads the bottom bar's own
  element, `frontend/e2e/screens.spec.js:114` the bottom bar's items). A later spec scopes such a
  locator to the bar or the tabs.

**Frontend unit** (`frontend/tests/improvementLabels.test.js`): `improvementStateLabel` (a known and
an unknown state); `lossText` (one ticket, several, no downtime); `defaultTitle` (symptom, no
symptom, a long description cut at 120); `defaultProblem` (description, no description with a
symptom, neither).

### 8.3 On a real device

- A Tamil problem text typed on an Android phone's keyboard shows the same on the improvement page
  on the phone and on a desktop. Account: an engineer (Priya's role). Network: the plant Wi-Fi.
  Where: either (the dev server on KLA's laptop, or production on the TEST machine). Not important:
  the browser tests cover the save, and the risk is only the phone's font.

### 8.4 Acceptance

- The frontend unit suite green; `npx vite build` clean; the targeted specs green; the whole
  browser suite at Normal once at the end (the router is shared code).
- On a phone (`phone-chromium`) every dialog fits (`expectDialogFits` in the flows) and the
  improvement page has no sideways scroll (`expectNoSidewaysScroll`, § 8.1).

## 9. Open questions and assumptions

- **The split** (S067 BR1-01, accepted 30-10-2026): R05.1 was cut at the API by the approved
  roadmap's rule. This step holds the screens; S067 is coded first, and this brief builds on S067
  § 6 as written.
- ***Remove ticket*** is a scope addition beyond R05.1 (S067 § 9 Q2, accepted (a)), for KLA at
  gate B. Its rule (the machine's last ticket stays) is S067's; this step only shows the button
  where the server says `removable`.
- **Doubt:** the mock-up the R05.1 task named `02-improvement.html` is `02-analysis.html`; this
  brief cites the file that exists.

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 30-10-2026

Sections changed: header (Status, Baseline), § 1 item 2, § 3 (`TicketsTabs.vue`), § 5.3, § 5.4,
§ 5.5, § 5.6, § 8.1, § 8.4, § 9 (the `ensureSites` assumption removed).

| Finding | Answer |
|---|---|
| BR1-01 minor | Accepted (a): the remove asks inline on the row, the panels' pattern, with the brief's wording, `"Remove ticket"` and `"Cancel"`; no dialog (§ 5.4, § 8.1). |
| BR1-02 minor | Accepted (a): `minutesText`'s default (days from 24 h); the example reads "down 1 d 7 h" (§ 5.6). |
| BR1-03 minor | Accepted (a): the empty *Open* text's second sentence only for `improvement:edit` holders (§ 5.5). |
| BR1-04 minor | Accepted (a): S067 § 6 adds `unit.site_id` (S067 BR2-06); the search passes it and the § 9 assumption is gone (§ 5.3). |
| BR1-05…BR1-09 nits | Accepted: BR1-05 § 3 the active tab by route name; BR1-06 § 8.1, § 8.4 `expectNoSidewaysScroll`; BR1-07 § 8.1 the `restore` body; BR1-08 § 1, § 5.5 the full `name`; BR1-09 § 5.4 one answer replaces the page copy. Also S067 BR2-01: § 5.4 shows another machine's code on its row. |
