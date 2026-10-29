```
Step: S068 — Improvement record: screens
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 30-10-2026
```

Reviewed against: 32eb122 + uncommitted S066 (S067 is not coded: its § 5 and § 6 were read as brief text, not code)

**Verdict:** no `blocker` or `major` is open. Four `minor` findings and five nits. None needs KLA's
decision and none is defining: the two routes, the tab, the dialogs and the server-driven controls
stand as written. BR1-04 asks for one field in S067's API; the orchestrator can settle it in S067's
round 2. Facts file read: `scratch/brief-facts-S068.md`; every `file:line` claim in § 3, § 5 and § 8
was opened and holds.

## Findings

### BR1-01 — minor — § 5.4 *Remove*: the confirmation's form is not stated

- **Problem.** § 5.4 says the remove "asks first" with the text, `"Remove ticket"` and `"Cancel"`, and
  "a refusal shows in the confirmation". It does not say whether that is a modal or an inline bar on
  the row. The app's own remove pattern is inline: `LabourPanel.vue:153-156` and
  `PartsPanel.vue:187-190` replace the row's buttons with "Remove?" `Yes` / `No`. A modal would be
  one more dialog that must pass `expectDialogFits` (§ 8.1 "each dialog opened").
- **Why it matters.** The coder decides the form alone; the test it writes depends on it; and a
  third confirmation style on the ticket pages breaks "same word for the same thing".
- **Options.** (a) **Recommended:** inline on the row, the panels' pattern (`confirmingRemoveId`):
  the row's remove button gives way to the brief's line "Remove TK-2026-10-005 from IM-2026-10-001?
  The ticket stays as it is." with `"Remove ticket"` (`btn-danger`) and `"Cancel"`; a refusal shows
  under it, as `unassignError` does on the ticket page. No dialog, no fit check. The brief's wording
  is better than the panels' "Remove?" (it names the consequence, CLAUDE-COMMON B); keep it. (b) A
  modal through `FormModal` with no fields and `"Remove ticket"` as its submit: one more dialog on a
  phone for a two-button question. Not defining.

### BR1-02 — minor — § 5.6 `lossText`: "down 31 h" contradicts `minutesText`'s default

- **Problem.** § 5.6 says the duration uses the ticket page's `minutesText` and gives the example
  "2 tickets, 1 breakdown · down 31 h". `minutesText(1860)` returns "1 d 7 h": from 24 h on it
  counts days (`ticketLabels.js:272-283`, S019 BR2-03); only `{ days: false }` gives "31 h" (labour
  hours). The example comes from mock-up 07.
- **Why it matters.** The unit test in § 8.2 ("several") is written to one of the two; the coder
  picks.
- **Options.** (a) **Recommended:** the default (days), so the loss reads as the ticket page's *Down
  for* and the ticket rows' "down …" on the same page; change the example to "down 1 d 7 h".
  (b) `{ days: false }` everywhere on the improvement screens: the same minutes then read
  differently on the ticket page and the improvement page. Not defining.

### BR1-03 — minor — § 5.5 empty state: operators are told to do what they cannot

- **Problem.** The *Open* empty text is "No open improvements. Start one from a ticket that is back
  in service or closed." It shows to every `improvement:read` holder; operators, supervisors and
  technicians never see `"Start improvement"` (§ 5.1, `can_start_improvement` needs
  `improvement:edit`).
- **Why it matters.** Scope B: the text tells a user what to do next, and for most readers it is
  not possible; on the floor they go looking for a button that is not there.
- **Options.** (a) **Recommended:** the second sentence only when `userPermissions` holds
  `improvement:edit`; others see "No open improvements." (b) Drop the second sentence for everyone.

### BR1-04 — minor — § 5.3 / § 9: the site id for the *Add ticket* search is looked up by code

- **Problem.** The search needs `site_id`; the brief derives it from `unit.site_code` through
  `ensureSites` (the masters store), and § 9 carries an assumption for it. S067's detail already
  reads `units.site_id` for its predicate and `permissions_at_site` (S067 § 5.5, § 5.7) but sends
  only `site_code`.
- **Why it matters.** One more store load and a code-to-id lookup in a dialog, for a value the
  server has in hand (CLAUDE-COMMON *Simplicity first*); the assumption would be gone.
- **Options.** (a) **Recommended:** S067 § 6 adds `site_id` to `unit{}` in the detail (and the
  list item, the same shape); S068 passes `unit.site_id` and § 9's assumption goes. S067 is in
  round 2, so the orchestrator can add it there. (b) Keep the lookup; the assumption holds today
  (`/api/masters/sites` is every role's). Not defining.

## Nits

- **BR1-05** (nit) § 3 `TicketsTabs.vue`: say how the *Tickets* tab is marked active. A
  `router-link to="/tickets"` is `router-link-active` on `/tickets/improvements` too (prefix match)
  and Bootstrap wants the class `active`; use the route name (`active` when `route.name === "tickets"`
  / `"improvements"`), with `aria-current="page"` as `MeView.vue:131-138`.
- **BR1-06** (nit) § 8.4: "the improvement page has no sideways scroll (`expectDialogFits` in the
  flows)" — that helper checks dialogs only. Call `expectNoSidewaysScroll(page)`
  (`e2e/support/dialogs.js:49`) once on the improvement page in the first flow (a fit helper inside a
  flow test does not tag it), or drop the claim.
- **BR1-07** (nit) § 8.1 `screens.spec.js`: no spec raises with *Already fixed* through the API
  today. Say the body: `restore: { person_id: <kannan> }` (`tickets_core._restore_block`, the restore
  move's fields), posted as the engineer (`ticket:restore` at SMTW).
- **BR1-08** (nit) § 5.5 row line 1 "lead Priya": the API's name is "Priya (engineer)" in the seed.
  Say whether it is `firstName(lead.name)` (as `TicketRow.vue` shows assignees) or the full name;
  the header line of § 5.4 the same.
- **BR1-09** (nit) § 1 item 2 / § 5.4: the header's "Started … by <created_by_name>" and the page's
  state badge are fine; add that the loss line and the *Tickets* rows both come from the one
  detail answer, so an add or remove replaces the whole page copy (as `onSaved` on the ticket page),
  not the card alone.

## Checked and found consistent

- **Facts.** `router/index.js`: `/tickets/:id(\d+)` does not match `improvements`; `canOpenRoute`
  (`navigation.js:34`) lets a route outside `navItems` through; `isActivePath` (`:55`) is a prefix
  match, so *Tickets* stays lit on both new paths. `MeView.vue:131` is the `nav nav-tabs`.
  `TicketDetailView.vue:204-212` the three states, `:289` the repeats box, `:306` the `Edit` size;
  `load()` tells 404 from 403 by `err.status` (`:164-165`), the pattern the list can copy.
  `useFormModal.js:20` and its `modalError` for a field not in the form (`:52`); `openCreate(seed)`
  → `blank(seed)` (`:56-59`). `backend/tickets.py:510` the list; `state=all` is in
  `tickets_core.STATE_FILTERS:47`; `q` matches serial or description (`:577-579`);
  `equipment_id` of a machine filters `t.equipment_id` (`_equipment_filter`). `minutesText`
  `:272`. `seed_e2e.py:42` Priya, all units. `tickets-work.spec.js:97/:100/:140` use `.action-bar`
  for one button or its top; `:161` clicks the repeat link as the operator; `:168/:177/:180/:298`
  read "Repeat of" / "Came back as". `nav.js:5`; `floor.spec.js:78` and `screens.spec.js:114` are
  scoped to the bottom bar. `playwright.config.js`: `workers: 1`, `fullyParallel: false`, so the
  "newest 10 of the machine" list is deterministic inside a lane.
- **Every field the screens use is in S067 § 6.** Detail: `serial, state, is_open, title, problem,
  machine{id,code,name}, unit{code,site_code}, lead{id,name,active,may_lead}, created_at,
  created_by_name, tickets[{id,serial,intensity,occurred_at,failure_mode,cause,downtime_minutes,
  removable}], loss{tickets,breakdowns,downtime_minutes}, permissions`. List item: `serial, state,
  title, lead, loss`. Ticket detail: `improvements[{id,serial,state}]`, `can_start_improvement`.
  Leads: `{items:[{id,name}]}` by `ticket_id` or `improvement_id`. The refusal fields (`ticket_id`,
  `title`, `problem`, `lead_id`) match the form's field names, so each lands beside its field; the
  Start dialog's `ticket_id` refusals land at the top as § 5.2 says.
- **Routes, tabs and the nav.** D1 holds: two routes under `/tickets/`, the filters never share a
  query, the nav lit by prefix, no nav item (the bottom bar stays at six). The 403 and 404 states
  of the page copy the ticket page's; the list's 403 shows a line without `"Retry"` (BR1-05 of
  S067); the no-Team state is `NO_UNITS_TEXT` through `noUnits`, rendered, not blank.
- **Use on the floor.** Start is one tap, a glance, one tap (D4, BR1-08 of S067); the button is
  hidden, not disabled (D3); every control follows the server's flags (D6); the page's buttons are
  the ticket page's size (BR1-11); *Add ticket* is a form with a footer, so `expectDialogFits`
  fits it unchanged (D5); rows already linked and not-a-fault rows are left out (BR1-09); the
  remove names what will happen; the ticket page gains one button and one line; the words are the
  ticket page's and Q0.1's "Improvement". One column on a phone, the right half kept for R05.2.
- **Browser tests.** Titles start with `S068:`; no test is `@device` (none checks a layout, by the
  rule in `.claude/CLAUDE.md`); every dialog opened calls `expectDialogFits`; the storekeeper's 403
  and the operator's read-only page are covered; `screens.spec.js` rows use `TICKET_ROLES`, which
  equals the `improvement:read` holders (operator up and IT admin, not the storekeeper), and the
  seed operator at MCC2 can see the extruder's improvement. The router is shared code, so the whole
  suite runs once at Normal (§ 8.4); `api.js` and `e2e/support/` are untouched, so no WebKit run.
- **Manual checks.** Split into automated and device; the Tamil-font row has account, network and
  where, and is rightly not important.
- **Standards.** TPM focused improvement (the team sees the analysis of its own losses: the tab
  beside the tickets, the line on the ticket page) and ISO 27001 A.5.15 (each person sees only what
  their role allows: controls from `permissions`, `is_open`, `removable`,
  `can_start_improvement`) are named and explained in plain words; the record's standards are
  S067 § 2 by reference, which is right for a screens-only step.
- **Design and structure.** Pure helpers in `improvementLabels.js` with unit tests; the views
  presentational; `useFormModal`, `PagerBar`, `IntensityBadge`, `useDebounced`, `filterableUnits`,
  `NO_UNITS_TEXT`, `minutesText` reused; `TicketsTabs.vue` has two users; no new abstraction.
- **Track.** Full is right: the step follows S067's new endpoints and is 13 code and test files.

## Feedback

- idea: the facts file names files and symbols but not the `file:line` claims; this brief makes
  about 25 and each was opened by hand (about 15 minutes). Printing the line behind every
  `path:NN` the brief cites would make them one read (the same idea as S067's review).
- rule: a screens brief reviewed before its backend step is coded can be checked only against the
  backend brief's text; the stale check before `/step implement S068` must compare against S067's
  real code, not only the files S068 names (S067's § 6 is the contract, and a round-2 change there
  changes this brief).
- waste: `scratch/brief-facts-S068.md` *Code names* spends about 30 lines on column names
  (`ticket_id`, `site_id`, `unit.site_code`) with 11–23 test files each; none answered a question.
