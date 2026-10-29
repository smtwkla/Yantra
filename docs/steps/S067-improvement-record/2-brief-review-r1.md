```
Step: S067 — Improvement record from tickets
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 30-10-2026
```

Reviewed against: 32eb122 + uncommitted S066

**Verdict:** no `blocker` or `major` is open. Six `minor` findings and eight nits. Two findings
are KLA's to decide by his own rules (BR1-01 the split, BR1-02 the remove rule); neither is
defining: the design, the tables, the keys and the lock sequences stand as written. Facts file
read: `scratch/brief-facts-S067.md`; every `file:line` claim in § 3–§ 8 was opened and holds.

## Judgement on § 9

- **Q1 (split).** Recommendation: **(b), two steps cut at the API.** Reasons: (1) the rule is
  KLA's own, twice: the skill's size rule (`SKILL.md:166`, "more than about 25 files … or a
  backend engine and its screens … The user decides") and R05 § Items ("If a brief passes 25
  files, it splits there"), and the brief trips all three triggers (29 files, ~725 lines, two
  tables and two screens); (2) every risk of this step — the migration, the locks of § 5.4, the
  keys, the race on `uq_improvement_tickets_open` — sits in the backend half and is proved by
  backend tests alone, so that half reviews in one sitting; (3) the frontend half then builds on
  a reviewed API, and each coder run and code-review round stays short (the rule's origin: S021,
  57 files, a 70-minute run). The cost (one more brief cycle, nothing visible after the first)
  is small under KLA's "brief all, then code without stopping". (a) is a departure from the
  approved roadmap line; the orchestrator may take (b) without stopping, and must tell KLA if it
  keeps (a). **Not defining.** See BR1-01.
- **Q2 (Remove ticket).** Recommendation: **(a), yes.** With Q1.4 (one open improvement per
  ticket) a wrong add blocks that ticket for every other analysis until R05.4; a remove with a
  confirm step and "not the last" is small, reversible by an add, and keeps the ticket row
  untouched. It is beyond the roadmap's R05.1, so it goes to KLA at gate B as a scope addition;
  **not defining.** One rule is missing from it: BR1-02.

## Findings

### BR1-01 — minor — § 9 Q1: the brief recommends against the approved size rule

- **Problem.** § 9 Q1 recommends one step with 29 code and test files. R05 § Items (approved
  by KLA at gate R) says "If a brief passes 25 files, it splits there", and the skill's size
  rule says the user decides.
- **Why it matters.** The brief's recommendation departs from a rule KLA set; under "code
  without stopping at gate A" the departure would be taken silently.
- **Options.** (a) One step, as the brief recommends; the orchestrator tells KLA at gate B that
  the 25-file line was passed and why. (b) **Recommended:** split at the API as § 9 Q1 (b)
  describes: S067 = `local_db.py` v36, `tickets_core.py`, `improvements_core.py`,
  `improvements.py`, `app.py`, `config_rbac.py`, `tickets.py` (`_detail`), `equipment.py`
  (docstring), their 7 test files, `docs/schema.*`; S068 = the router, the five Vue files,
  `improvementLabels.js` and its test, `TicketDetailView.vue`, `improvements.spec.js`,
  `screens.spec.js`, the device check. S068's brief is short: § 1 items 1–6, § 5.8, § 8.4
  of this brief, with the API of § 6 as its contract. KLA's decision by his rule; not defining.

### BR1-02 — minor — § 5.3 / D5 / D9: removing the ticket that set the improvement's machine

- **Problem.** D5 fixes `unit_id` and `equipment_id` to the first ticket's. D9 lets any ticket
  but the last be removed, the first included. After that the page's *Where* names a machine
  with no ticket in *Tickets (n)*, and the list files the improvement under a unit none of its
  tickets is in. The brief's assumption in § 9 covers tickets added on other machines, not the
  first one leaving.
- **Why it matters.** A rule the coder would otherwise decide alone; the screen then shows a
  machine the record no longer analyses.
- **Options.** (a) **Recommended:** the improvement keeps at least one ticket on its machine:
  the remove is refused with 409 "An improvement keeps a ticket of HP003" when the ticket is the
  last linked ticket whose `equipment_id` is the improvement's; the remove button is hidden on
  that row as it is on the last ticket. One rule in `improvements_core`, decided from the links
  read under (6b). (b) Allow it and say so in D5 ("the first machine stays as the record's
  anchor"). (c) Re-derive the machine on removal (D5 rejected this; it changes the list's unit
  and the predicate). Not defining; the orchestrator can settle it in the Review log.

### BR1-03 — minor — § 8.2 Start: "an engineer of another site (403)" is a 404 by the brief's own order

- **Problem.** § 5.3 and § 5.4 step 3 put the tickets' access predicate (`read_ticket`, 404)
  before `require_perm_at` (403). An engineer with no membership at the ticket's site holds
  `ticket:read` nowhere there, so `accessible_unit_ids` leaves the unit out and the start
  answers 404, not 403. § 8.2 expects 403.
- **Why it matters.** The coder writes a test that fails, then changes either the test or the
  order; both are guesses.
- **Options.** (a) **Recommended:** keep the order (the ticket is the anchor, as every ticket
  route) and fix the test list: an engineer of another site → 404; a person who is operator at
  this site and engineer at another → 403 (the predicate passes, the key does not). The same
  pair for *Add ticket* and *Leads*. (b) Check the key before the predicate: reveals that the
  ticket exists; rejected by the tickets' own rule.

### BR1-04 — minor — § 5.8 / § 8.4: the *Add ticket* dialog cannot pass `expectDialogFits` as designed

- **Problem.** The dialog's rows are the action (a tap adds) and it has no Save button, so its
  `FormModal` footer is `close-only` (one button, "Close"). `expectDialogFits`
  (`frontend/e2e/support/dialogs.js:33-34`) locates `.modal-footer button[type=submit]` and a
  button named "Cancel" and calls `boundingBox()` on both; with neither present the helper
  throws. § 8.4 says every dialog opened calls it, and the important check 2 opens this one.
- **Why it matters.** The important automated check fails as written; a change to
  `e2e/support/` is shared code (settings: *Shared code*): the whole suite runs again plus the
  WebKit screens run.
- **Options.** (a) **Recommended:** make the dialog a form like every other: a radio list of
  the rows (serial, intensity badge, state, symptom), the search box above, footer `"Cancel"`
  and `"Add ticket"` (`useFormModal.save` with `toBody` → `{ticket_id}`); a refusal shows beside
  the list. One more tap, the same shape as every dialog, and the existing helper fits it.
  (b) Keep the tap-to-add rows and give the helper a `closeOnly` variant that checks the "Close"
  button: shared-code change, the extra runs above. (c) Keep the rows and skip the fit check on
  this dialog: against the S024 convention.

### BR1-05 — minor — § 5.5 / § 5.8: a 403 on the improvements list shows "Retry"

- **Problem.** `/tickets/improvements` is not a nav item, so `canOpenRoute` lets anyone type
  it; the storekeeper's `GET /api/improvements` answers 403 ("You don't have permission for
  this. Ask your engineer or IT."). The list, "on the pattern of `TicketsView.vue`", shows every
  error as the load error with `"Retry"`. The ticket page shows a 403 as its own line without
  Retry (`TicketDetailView.vue:209`), and the brief gives the improvement page that pattern but
  not the list.
- **Why it matters.** A Retry on a refusal tells the user to try again what cannot succeed.
- **Options.** (a) **Recommended:** on a 403 the list shows "You can't see improvements." with
  no Retry, as the ticket page does; the e2e `screens.spec.js` row stays `TICKET_ROLES`.
  (b) Leave it, as the Tickets list leaves it today (reached only by a typed URL).

### BR1-06 — minor — § 5.3: a start from a ticket on a scrapped machine is not decided

- **Problem.** A closed ticket's machine can be scrapped later (`_check_no_open_tickets`
  counts open tickets only). The brief does not say whether such a ticket may start or join an
  improvement; nothing in § 5.4 reads `equipment.lifecycle`, so the coder's default is "allowed",
  unstated.
- **Why it matters.** A rule the coder decides alone; and the improvement page would link a
  scrapped machine as *Where*.
- **Options.** (a) **Recommended:** allowed, stated in § 5.3 and D5: the analysis is about the
  plant and the class (yokoten), the machine's lifecycle does not matter, and no lock is added.
  (b) Refused with 409 "This machine is scrapped": one more plain read of the machine, and a
  rule R05.6's lessons on a class would contradict.

## Nits

- **BR1-07** (nit) § 5.4 Edit step 2: write "the lead (§ 5.6), only when `lead_id` differs from the stored value", so the coder does not validate an unchanged lead who left the site (§ 5.6's last bullet depends on it).
- **BR1-08** (nit) § 5.8 `defaultTitle` / § 9 assumption "one tap": a ticket with a symptom may have no description (`validate_raise`, `description` None), so *Problem* is empty and the engineer must type. Prefill from the symptom label then ("Won't start"), or drop the one-tap claim.
- **BR1-09** (nit) § 5.8 *Add ticket*: leave out rows with `not_a_fault` as the rows already linked are left out; a tap on one only earns the 409 of D7. The list items carry `not_a_fault`.
- **BR1-10** (nit) § 8.4 `screens.spec.js`: its `beforeAll` ticket is `raised` (degraded, no restore), so it cannot start an improvement. The new row needs a second ticket raised with `restore` (*Already fixed*) by the engineer, then the start; say so.
- **BR1-11** (nit) § 1 item 2, § 5.8: give `"Edit"`, `"Add ticket"` and the remove icon button the ticket page's size (`btn btn-outline-primary`, `TicketDetailView.vue:306`), not the mock-up's `btn-sm py-0`: gloved thumbs (settings: *Use on the floor*).
- **BR1-12** (nit) § 5.8 `lossText`: one shape for the loss on the page and in the list; today "1 breakdown, down 2 h 25 min" (page) and "2 tickets · down 31 h" (list) describe the same figures in two ways. Suggest "2 tickets, 1 breakdown · down 31 h" everywhere, with "no downtime" when zero.
- **BR1-13** (nit) § 5.3, § 6: define "newest first" for `improvements` on the ticket detail and for the list: `improvements.id DESC` (the serial order), so the coder does not pick the link's `created_at`.
- **BR1-14** (nit) § 6 `GET /api/improvements/leads`: say the ticket anchor goes through `read_ticket` (404) and the improvement anchor through the improvements' predicate (404) before `require_perm_at`, as `_picker_anchor` (`tickets.py:660`) does; § 5.5 names only the 403.

## Checked and found consistent

- **Facts.** Every cited line holds: `format_ticket_serial` / `serial_scope` at
  `tickets_core.py:82/87` hard-code TK; `tickets.py:820` calls `serial_scope(now.year, now.month)`;
  `_detail` at 404, `read_ticket` 241, `_visible_condition` 180, "The unit never changes" 456,
  the raise's in-transaction detail 847; `equipment.py:9` and `:477`; `masters.py:287/:320`;
  `db_helpers.next_counter:78`; `auth_utils.require_perm_at:451`, `permissions_at_site:466`;
  `access_core.compute_permissions:44`; `api_common.clean_body:121`, `UNIQUE_KEY_ERRORS:26`;
  `config_rbac` 89/166; `app.py:187`; `local_db.py:145`; `conftest._TABLES:162`, `db_down:212`;
  `test_rbac.test_role_matrix` 178–209; `test_auth.py:388`; `test_migration_v35.py:16`
  `VERSIONS = list(range(20, 36))`; `MeView.vue:131`; `navigation.js:55`;
  `TicketDetailView.vue:289`; `useFormModal.js:20`; `seed_e2e.py:42`; `support/tickets.js:27`;
  `support/nav.js:5`; `screens.spec.js:114`. No test asserts the ticket detail's key set
  (`test_tickets_api.py`, `test_ticket_work_api.py` compare sub-objects only). No spec locates a
  link named "Tickets" (`equipment.spec.js` uses a combobox of that name; `floor.spec.js:78` the
  focused element's text).
- **Lock sequences** against both LOCK ORDER notes. Start: (6) `IM:` counter → (7) ticket
  shared → plain reads → inserts; the counter's `SELECT last_value` is the first consistent read,
  so the snapshot starts after the lock; a refused start rolls the bump back. Add and Remove:
  (6b) improvement `FOR UPDATE` → (7) shared → plain reads whose snapshot starts after both
  locks. The one new edge (a shared ticket lock, then the insert's shared FK locks on unit,
  machine and person) meets only `masters.py`'s person-row edit, the same shape as the accepted
  raise deadlock (`tickets.py:61`); the unit edit and the scrap take shared or plain reads of
  tickets, so neither waits for a start. Nothing holds a ticket `FOR UPDATE` and then an
  improvement row. The duplicate-key race on `uq_improvement_tickets_open` ends in 1062 → 409
  for the second writer, as `_integrity_error` maps it.
- **`UNIQUE (ticket_id, open_link)` with NULL** is InnoDB's documented behaviour; the CHECK is
  enforced by `mariadb:11.4` (the dev image); the ENUM append is the S019 pattern. No
  precondition is right for two new tables.
- **Permissions.** `improvement:read` holders equal `ticket:read`'s (operator up, IT admin,
  not the storekeeper); `improvement:edit` engineer and manager; both in `SITE_SCOPED`, which
  `_check_site_args` asserts. IT admin reads every unit through `every_unit_by_token`
  (`improvement:read` + `equipment:read_all_units`). The role-matrix rows in § 3 match; the
  `/api/auth/me` test follows by itself. `can_start_improvement` and the ticket page's
  `improvements` are decided from `permissions_at_site`, so nothing shows to a reader without
  the key at that site.
- **Standards.** TPM focused improvement, ISO 9001 § 10.2.1 (a)(b), § 10.2.2, § 7.5.3 (with the
  history departure recorded), ISO 14224 (no second copy of the failure data), EN 13306 (time to
  restoration, computed never stored), ISO 27001 A.5.15 / A.8.2: each named, explained in plain
  words, and followed as R05 § Standards set out.
- **Use on the floor.** Start is one tap, a glance at filled fields, one tap; `"Start
  improvement"` hidden, not disabled (D10); the remove asks first and names the consequence;
  `"Analysed in …"` in the existing repeats box; the two tabs are router links, so the bottom
  bar's *Tickets* stays lit; empty states for open, closed, filtered and no units; the words are
  the ticket page's. The screens follow mock-ups `02-analysis.html` (left half) and
  `07-improvements.html` (left), minus what § 1 lists as out of scope.
- **Track and checks.** Full is right (a migration, keys, locks). § 8.4 and § 8.5 split
  automated and device checks correctly; the Tamil-font row has its account, network and where.
- **Design and structure.** Rules in `improvements_core.py` (pure), the routes a thin shell,
  the frontend presentational; `format_serial` reuses the TK helper rather than a parallel one;
  `TicketsTabs.vue` has two users; no new abstraction without a second use.

## Feedback

- idea: the facts file lists names and files but not `file:line` claims; this brief makes about
  30 of them and I opened each by hand (about 25 minutes). `brief_facts.py` could print the line
  text behind every `path:NN` the brief cites, so a reviewer checks them in one read.
- waste: the facts file's *Code names* section spends ~60 lines on names the brief marks new
  (`not found`) and on column names (`unit_id`, `updated_at`, `per_page`) with 15–30 test files
  each; none of those lines answered a question (`scratch/brief-facts-S067.md` lines 103–290).
