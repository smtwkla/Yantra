```
Step: S031 — Me: my open work, tickets I raised, my activity
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 23-10-2026
```

Reviewed against: aad833a (working tree clean apart from this step's folder and its README index row)

**Verdict: no `blocker` or `major` finding. Six `minor` findings and a list of nits.**

Facts file used: `scratch/brief-facts-S031.md`. Every file, route and code name it lists checks out: the new files are the ones the brief creates, and `erp_server/yantra/compose.yml.j2` is in the devops repo. I opened the code for behaviour and rules only (`tickets.py`, `local_db.py` v20–v25, `config_rbac.py`, `auth_utils.current_person_id`, `navigation.js`, the router, `TicketsView.vue`, `ticketLabels.js`, `datetime.js`, `PagerBar.vue`, `AppBottomNav.vue` and its CSS, `NotificationsView.vue`, `TicketDetailView.vue`'s timeline, the test fixtures and e2e helpers the brief names, Plan.MD § 3, § 4.2, § 4.6, § 6, Maintenance-Philosophy, Plant-Facts, the base's § Sidebar visibility and § Frontend Design).

**Decision 7.2 (the orchestrator's question).** The reasoning holds, and the code makes it stronger than the brief says. A site role's keys come from `memberships`, which hang on `people`, and `current_person_id` reads only `active = 1` rows; so every `ticket:read` holder from a site role has an active Team record. The only `ticket:read` holders without one are the token roles `it_admin` and `admin`. The reverse case is the storekeeper: a Team record and no ticket key. "Has a Team record" would have shown *Me* to the storekeeper (nothing to show) and hidden it from IT admin (who raises tickets). `ticket:read` is also the base's rule (§ Sidebar visibility: the lowest permission that gives meaningful content). Two consequences for the brief: the "not linked" message is read by IT admin and admin only (BR1-02), and decision 7.2 can state this fact for gate A (nit).

## Findings

### BR1-01 — minor — The default tab is empty for everyone who raises but is never assigned

**Problem.** § 1.2 makes *Open work* the default tab for every role. Only `ASSIGNABLE_ROLES` (technician, engineer, manager) are ever assigned (`config_rbac.py`; `_auto_assign` and the Assign dialog). An operator or supervisor opens *Me* and always lands on "No open tickets are assigned to you." The useful tab for them is *Raised by me*, one tap further, every time.

**Why it matters.** Plant-Facts § 5: the sorting-line supervisor and the extrusion operators are the phone users who raise. The page's one job for them is "what happened to my report", and the brief's own § 2 (the TPM tag follow-up) names that as the point. A permanently empty landing tab is the kind of friction that stops a floor user opening the page.

**Options.**
- (a) Default by permission: `ticket:work` held → *Open work*; not held → *Raised by me*. A one-line pure helper (`defaultTab(permissions)`) in `ticketLabels.js` or `MeView.vue`, with a unit test; the URL rule stays (the default tab is left out of the query). The supervisor's bottom bar then opens on their reports. **Recommended.**
- (b) Keep *Open work* first for everyone, and make the empty text for a non-worker say so: "Tickets are assigned to maintenance staff. Your reports are under Raised by me." Simpler, but still a dead tab first.
- (c) Put *Raised by me* first for everyone. Wrong for technicians, the main audience of *Open work*.

### BR1-02 — minor — The "not linked" message is written for the wrong reader

**Problem.** § 1.3: "Your login is not linked to a person in Team, so no tickets can be assigned to you. Ask IT admin to link it in Masters › Team." As shown under Decision 7.2 above, the only users who can see this are IT admin and admin. The message tells IT admin to ask IT admin. It is also three clauses with an explanation of the rule (scope B: one line, what is wrong and what to do).

**Why it matters.** The one person who reads it is the person who can fix it; the text sends them nowhere. `NotificationsView.vue` already solved the same state with two short lines: "You are not in Team. Add yourself in Masters › Team to get test messages." (IT admin) and "You are not in Team. Ask IT admin to add you." (others).

**Options.**
- (a) Reuse the Notifications pattern: IT admin (`userRoles` has `it_admin`, or admin) sees "You are not in Team. Add yourself in Masters › Team to be assigned tickets."; anyone else (defence in depth; today nobody) sees "You are not in Team. Ask IT admin to add you." Same words for the same state across the app (scope B). **Recommended.**
- (b) One text for all: "You are not in Team, so nothing can be assigned to you. IT admin adds people in Masters › Team." Shorter than today's, still two sentences.

### BR1-03 — minor — The `EXPLAIN` acceptance criterion cannot be met on the test database

**Problem.** § 4 and § 8 Acceptance: "The impl report shows the `EXPLAIN` of both new queries using the v26 indexes." On the dev and test databases the tables hold a few dozen rows. MariaDB's optimizer chooses a table scan over an index for a table that small, and for the `OR` in § 5.2 an index merge is chosen only when both sides are selective. The coder will run `EXPLAIN`, see `ALL`, and either fail the criterion or pad the data to pass it.

**Why it matters.** An acceptance criterion the coder cannot meet honestly is noise at gate B. The indexes are still right (decision 7.7); the check of them belongs in the migration test (§ 8 Migration already asserts both indexes by name and columns).

**Options.**
- (a) Drop the `EXPLAIN` line from Acceptance; keep the indexes and the migration test's assertion. Have the coder report the `EXPLAIN` output as information, with the note that small tables scan. **Recommended.**
- (b) Keep it as "the indexes appear in `possible_keys`". Weak: `possible_keys` lists an index whenever the predicate matches a column, so it proves little more than the migration test.
- (c) Keep the criterion and have the coder run it on a database padded to a few thousand events. Work with no lasting value.

Also in § 4: "to verify with `EXPLAIN` in the coder's run, and reported in the impl report" is a sentence fragment (scope A); the fix above removes it.

### BR1-04 — minor — The no-units state is not what the Tickets list does

**Problem.** § 5.1: "A user who may see no ticket at all (`_visible_condition` returns None) gets an empty list on every tab, as the Tickets list does." The Tickets list does not show an empty list for that user: `TicketsView.vue` reads `ensureMyUnits()` and shows "You have no units assigned — ask IT admin for unit access." (`noUnits`) in place of the list. The brief's tabs would show "No open tickets are assigned to you." / "You have not raised any tickets." / "No activity yet." for a person whose real problem is unit access.

**Why it matters.** Empty and edge states are the coder's to decide if the brief is silent, and the text they would show is wrong for the cause. The case is rare (a membership with chosen units that were all deactivated) but it is the one case where the user needs to be told what to ask for.

**Options.**
- (a) `MeView.vue` loads `ensureMyUnits()` with each tab, as `TicketsView.vue` does, and shows the same `noUnits` text in place of all three tabs. One shared computed, the same wording. **Recommended.**
- (b) State in § 5.1 that the Me page shows its plain empty texts in this case, and why. Acceptable, but say it.

### BR1-05 — minor — Part of the device check is a browser check

**Problem.** § 8 On a real device: "open *Me* on a phone, switch the three tabs with a thumb, open a ticket and come Back to the same tab." A browser engine judges "open a ticket and come Back to the same tab" (navigate to `/me?tab=activity`, click a row, `page.goBack()`, assert the tab). README § Manual checks puts such a check on the automated list. The thumb part is the only device part.

**Why it matters.** The Back behaviour is the one rule § 1.2 states about the URL (the tab in the query so Back returns to it), and it is cheap to pin in `me.spec.js`. Left on the device list it waits for IT Admin.

**Options.**
- (a) Add to Automated: "From *My activity*, a row opens the ticket; Back returns to *My activity*, not to *Open work*." Keep the device row as: "open *Me* on a phone and switch the three tabs with a thumb" (plain, IT Admin, production on the TEST machine, a technician account, plant Wi-Fi: as written). **Recommended.**
- (b) Keep as is and accept the gap in the e2e suite.

### BR1-06 — minor — Plan.MD § 6 calls this screen "Home: my jobs"; the Docs section does not touch § 6

**Problem.** Plan.MD § 6 Screens, Phone: "Home: 'my jobs' (assigned tickets and PM jobs due; CIL jobs for operators), 'raise breakdown', 'scan equipment'." The brief's *Open work* is the first form of that list, and U1 decided it is a nav item, not the landing page. § 3 Docs updates "the module list" only. After approval Plan.MD would say the phone home is "my jobs" while the built app lands on Equipment with *Me* as the third nav item.

**Why it matters.** Plan.MD is the record of decisions; the next planner reads § 6 when the PM work orders come (phase 4, which the brief's Out of scope says will "join *Open work*"). The U1 decision belongs there.

**Options.**
- (a) In § 3 Docs, name Plan.MD § 6 as well: the Home line becomes "*Me* (S031): open work assigned to me, tickets I raised, my activity; PM jobs due and CIL jobs join *Open work* in phase 4; the landing page stays Equipment (U1, 23-10-2026)". Also one line in § 4.6: *My activity* is the per-person view of the Daily work log, which stays a phase 5 report. **Recommended.**
- (b) Leave § 6 and let the phase 4 planner reconcile. Cheaper now, costlier later.

## Nits

- **BR1-07** (nit) § 4 index: make it `ix_ticket_events_created_by (created_by, created_at, id)`, as `ix_ticket_events_ticket (ticket_id, occurred_at, id)` does, so the `ORDER BY e.created_at DESC, e.id DESC` tiebreak is served by the index too.
- **BR1-08** (nit) § 5.2 collation: `utf8mb4_uca1400_ai_ci` is the dev server's (MariaDB 11.4) default; production's version is unknown (§ 4 says so) and its default may be `utf8mb4_general_ci`. Say "a case-insensitive collation (the dev server's is `utf8mb4_uca1400_ai_ci`)", so the claim is not tied to one server. The test still pins the behaviour.
- **BR1-09** (nit) § 5.1 "A request with no identity holds no key, so `require_perm` refuses it with 403": in production the auth hook answers 401 before any route (`auth_utils`); the 403 is the e2e stub's case. Say both.
- **BR1-10** (nit) § 1.3: say the order of the "not linked" decision: the tab calls the API; after a successful load with `userPersonId` null it shows the message. Otherwise a 503 (DB down) could be masked by the message, since `/api/auth/me` also answers `person_id: null` while the database is down.
- **BR1-11** (nit) § 1.4 empty text "You have not raised any tickets." misses the `reported_by_id` half of § 5.2. "No tickets raised by you or for you." (scope B, same state, one line). Consider the same for the tab name at gate A (*Raised by me* hides the reported-by inclusion; *My tickets* is the alternative), under open question 4.
- **BR1-12** (nit) § 7.2: add the fact from the Decision 7.2 check above, so gate A has it in one sentence: "the only `ticket:read` holders without a Team record are the token roles `it_admin` and `admin`; the only Team-record holders without `ticket:read` are storekeepers".
- **BR1-13** (nit) § 8 Automated, *Raised by me*: name the close path the test uses. `close` needs cause, action, symptom and a labour row after back in service; *not a fault* from `raised` needs a cause and a remark (`moveByApi(engineer, id, "not-a-fault", …)`) and is the shortest. The row then reads "Closed · Not a fault"; assert that text, not only *Closed*.
- **BR1-14** (nit) § 8 Automated: add "the storekeeper typing `/me` lands on Equipment" (the router guard, `canOpenRoute`), beside "sees no *Me* in the nav".
- **BR1-15** (nit) § 1.5 / § 5.3: a `raised` row shows label, serial, badge and machine, but not what was wrong. Consider `problemText`-style detail for `raised` (the activity API would add `description` and `failure_mode` label to `ticket`). Optional; say yes or no.
- **BR1-16** (nit) Header: `Date: 23-10-2026 (user answers U1 before drafting)` departs from the template; the note is already in the Review log. Keep `Date: 23-10-2026`.

## Standards

- **TPM autonomous maintenance, the tag.** Cited correctly and explained in plain words: the finder follows the tag until the fault is fixed; *Raised by me* is that follow-up. Plan.MD § 4.2 ("Keeps operator ownership visible (TPM)") and Maintenance-Philosophy § 6 agree.
- **EN 13306.** Correct: the page adds no term; it reuses *breakdown*, *defect*, *back in service*, *corrective maintenance* from the glossary.
- **ISO 9001 § 7.5.3 (control of documented information).** Correctly cited: records stay available and protected; the page reads and changes nothing, and S027's earlier text stays on the ticket page. For the owner: § 7.5.3 asks that documented information be available where needed and protected from loss and improper change; a read-only view of one's own records is the "available" half.
- **ISO/IEC 27001 A.5.15 (access control).** Correct: the same unit predicate as the Tickets list, so a person moved off a unit no longer sees that unit's tickets, even ones they raised. For the owner: A.5.15 asks that access to information follow business and security requirements; here the requirement is "my units", already decided in S011.
- **SMRP / planned maintenance.** "One visible job list per person" is sound practice; the brief rightly cites no clause. SMRP's work-management guidance (a schedule per craftsperson, priority order) is the reference if one is wanted later, with phase 4's PM jobs.
- Not needed here: ISO 14224 (no failure data changes), ISO 55000 (no asset data changes).

## Checked and found consistent

- `list_tickets` order, filters and the `assigned=me` block (`tickets.py:511–586`); `enum_arg` 400 text "raised must be one of: me" with field `raised` (`api_common.enum_arg`); `int_arg`, `DEFAULT_PER_PAGE` 50, `MAX_PER_PAGE` 200, `MAX_PAGE`.
- `/api/tickets/activity` cannot collide with `/<int:ticket_id>` (digits only) nor with `/modes`, `/people`.
- `_visible_condition` returns None for "no unit at all"; the brief's empty-list behaviour matches the API (the screen text is BR1-04).
- `actor()` is `g.user["username"]`, written to every `created_by` by `insert_row`; `_add_event` and `_assign` stamp the acting user, and `person_id` is the person the line is about (decision 7.5 is right).
- `_auto_assign` on acknowledge adds the e2e technician (maint_technician at SMTW, all units), so the first important e2e check is reachable as written.
- `edit_note` rewrites `ticket_events.remark` in place and keeps the old text in `ticket_note_edits`, so *My activity* shows the current text, as § 2 says.
- v20: `ticket_events` has `ix_ticket_events_ticket (ticket_id, occurred_at, id)` and the FK index on `person_id`, nothing on `created_by`; `tickets` has no index on `created_by`; `reported_by_id`'s only index is the one InnoDB makes for `fk_tickets_reported_by`. `created_at` is `DEFAULT CURRENT_TIMESTAMP` on both tables.
- v26 is index-only: no `_PRECONDITIONS` entry is right (CLAUDE.md § Migrations); the previous release runs on v26 unchanged. `test_migration_v24.py` is the right pattern (`_recreate`, `_migrate`, `_fill_one_ticket`, `information_schema.STATISTICS`).
- `config_rbac.PERMISSIONS["ticket:read"] = ("maint_operator", "it_admin")`, in `SITE_SCOPED`; the supervisor inherits through `ROLE_INCLUDES`; the storekeeper holds no ticket key.
- `canOpenRoute(name)` follows the nav item of the same name, so route name `me` = nav name `me` is what the guard needs; the router redirects a refused route to `landingPath`.
- `navigation.test.js` lists `["equipment", "tickets", "masters"]` etc.: they change exactly as § 3 Tests says; the storekeeper's and the landing page stay.
- The bottom bar is `flex: 1` per item (`main.css`): five items (manager, IT admin) fit a 390-px phone; the e2e `expectNoSidewaysScroll` check covers it.
- `TicketsView.vue`'s row uses `IntensityBadge`, `overdueBadge`, `ageText`, `problemText`, `stateLabel`, `planText`, `firstName` and `t.assignees`: all in the list API's item, so `TicketRow` with props `ticket`, `now` is a clean cut. `tickets-work.spec.js:424` finds rows by `.list-group-item` and text, which the move keeps.
- `EVENT_LABELS` (`ticketLabels.js`) covers every event name in `tickets_core.py`, `note` included. `formatDateTime` gives `DD-MM-YYYY HH:MM` for a datetime and `DD-MM-YYYY` for a date, so `planText` works on the activity item's `planned_date`. `row_to_dict` emits `+05:30` strings, so `isBackdated` can compare `slice(0, 10)`.
- `/api/auth/me` sends `person_id` from `current_person_id` (active only), so `userPersonId` null means "no active Team record" when the database is up.
- `db_down` fixture: local to `test_access_control_api.py` and `test_auth.py` as stated (`test_health.py` monkeypatches its own reference).
- The e2e seed's IT admin (`IT_ADMIN`, outside `PEOPLE`) has no Team record; `raiseByApi`, `moveByApi`, `causeId` exist in `e2e/support/tickets.js`.
- Track: full is right (a migration, a new endpoint). The e2e full suite is right (the router changes).
- Scope A: the brief leads with the point and keeps one term per thing (*tab*, *row*, *line*); § 4's fragment is covered by BR1-03.
