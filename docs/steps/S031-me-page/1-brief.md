```
Step: S031 — Me: my open work, tickets I raised, my activity
Doc: brief
Author: Planner (Opus)
Date: 23-10-2026
Track: full
Status: Done (committed 33c3a4b; checks: 8 auto; row 26 of device-checks.md, not important, still open for the user)
Baseline: aad833a
```

# S031 — Me: my open work, tickets I raised, my activity

**The need (KLA, 23-10-2026).** A person opens Yantra to find *their* work.
Today the Tickets list has an *Assigned to me* checkbox (S018) and nothing
else is personal. There is no page that answers "what is mine to do", "what
happened to the tickets I reported" and "what have I done".

This step adds a **Me** page with three tabs (U1):

1. **Open work** — the open tickets assigned to me, most urgent first;
2. **Raised by me** — the tickets I raised or that name me as the reporter,
   newest first;
3. **My activity** — every timeline line I recorded on any ticket, newest
   first.

It is read-only. It adds one API route, one filter on the existing ticket
list and one index-only migration (v26).

## 1. What will be built

1. **The nav item *Me*** — in the sidebar and the phone bottom bar, after
   *Tickets* and before *Masters*: icon `fa-solid fa-user`, label *Me*,
   route `/me`, permission `ticket:read` (§ 5.1, § 7.2). The landing page does
   not change: *Equipment* stays first (U1: "New nav item", not "landing
   page").
2. **The page `/me`** (`MeView.vue`), top bar title *Me*. Under it, three tabs
   as Bootstrap `nav nav-pills nav-fill`, full width, so all three fit a
   phone: **Open work**, **Raised by me**, **My activity**. The tab is in the
   URL query (`?tab=open`, `?tab=raised`, `?tab=activity`), as the Tickets
   filters are, so Back returns to the same tab. Changing the tab drops
   `page` and `state` from the query.
   - **The default tab** (BR1-01) depends on the user: `ticket:work` held →
     *Open work*; not held → *Raised by me*. Only technicians and the roles
     above them are ever assigned (`config_rbac.ASSIGNABLE_ROLES`), so an
     operator or supervisor opens *Me* on their reports. A pure helper
     `defaultMeTab(permissions)` in `ticketLabels.js` decides it. The default
     tab is left out of the URL; a missing or unknown `tab` shows the default.
   - **No units** (BR1-04): when the user has no unit to see tickets at
     (`ensureMyUnits()` from `stores/equipment.js`, the same `noUnits`
     computed as `TicketsView.vue`), the page shows the Tickets list's text
     "You have no units assigned — ask IT admin for unit access." in place of
     the tabs' lists.
3. **Open work** — the list from the existing
   `GET /api/tickets?assigned=me&state=open` (S018), in the server's order:
   breakdowns first, then defects; within an intensity the scheduled tickets
   after the ones to act on now; the oldest first (`tickets.py`
   `list_tickets`, the `state == "open"` order). Each row is the Tickets
   list's row (§ 7.3): intensity badge, serial, overdue badge, age, machine,
   problem, unit, state, plan, assignees. A row opens the ticket. Above the
   list: "`<n>` open tickets assigned to you" (`1 open ticket …` for one).
   - Empty: "No open tickets are assigned to you."
   - No Team record (BR1-02, BR1-10): the tab calls the API as usual (it
     answers an empty list, `tickets.py` `list_tickets` `if assigned:`
     block). Only after a successful load, and when `userPersonId` is null,
     it shows the message of `NotificationsView.vue`'s same state. So a 503
     still shows the error and *Retry* (`/api/auth/me` also answers
     `person_id: null` while the database is down). The text:
     - IT admin (`userRoles` has `it_admin`): "You are not in Team. Add
       yourself in Masters › Team to be assigned tickets."
     - anyone else: "You are not in Team. Ask IT admin to add you."

     Today only IT admin and admin can reach this state: every site role
     comes from a membership on an active Team record (§ 7.2). The other two
     tabs still work by login.
4. **Raised by me** — the list from `GET /api/tickets?raised=me&state=<s>`
   (new filter, § 6), newest first (the server's order for `closed` and
   `all`; for `open` the order of item 3). A *State* select above the list
   with **All** (default, left out of the URL), **Open** and **Closed**, in
   `?state=`. The same row as item 3, which shows each ticket's state. Above
   the list: "`<n>` tickets".
   - Empty with *All*: "No tickets raised by you or for you." (BR1-11)
   - Empty with *Open* or *Closed*: "No tickets match this filter."
5. **My activity** — the list from `GET /api/tickets/activity` (new, § 6):
   each timeline line I recorded, newest first by the time it was recorded.
   One row per line, the whole row a link to its ticket:
   - line 1: the recorded time `DD-MM-YYYY HH:MM` (`formatDateTime`), the
     line's label from `EVENT_LABELS` (`ticketLabels.js`: *Raised*,
     *Acknowledged*, *Work started*, *Note*, …), the ticket's serial and its
     intensity badge;
   - line 2: the machine, `<code> — <name>`;
   - line 3, small and secondary, the detail from the pure helper
     `activityDetail(item)` (§ 5.3), when there is one;
   - when the line's own time (`occurred_at`) falls on an earlier IST day
     than the time it was recorded (a back-dated entry, S028), line 1 adds
     "· happened `DD-MM-YYYY HH:MM`".

   Paged with the existing `PagerBar`, 50 a page. Empty: "No activity yet.
   What you record on tickets shows here."
6. **Loading and errors** on each tab follow `TicketsView.vue`: "Loading…",
   and a failed load shows the API's message with a *Retry* button. The
   database down gives the usual 503 message.
7. **One row component** — the ticket row is moved out of `TicketsView.vue`
   into `components/TicketRow.vue`, used by the Tickets list and by the two
   ticket tabs (§ 7.3). Its look and text do not change.

### Out of scope

- **Time booked** (my labour per day or week): not chosen at U1. Labour rows
  are not timeline lines, so they are not in *My activity* either.
- Parts added, photos and documents added, and note corrections in *My
  activity*: none of them is a timeline line (`ticket_events`). A later step
  can add them if wanted.
- Lines recorded *about* me by someone else (an engineer assigning me): they
  show as tickets in *Open work*, not as activity. *My activity* is what I
  recorded.
- Counts on the tabs, a home-screen badge, or *Me* as the landing page.
- Another person's page (an engineer viewing a technician's work). That is a
  team report, later.
- Any change to *My notifications* (it stays under the bell, S021).
- PM work orders: they do not exist yet (Plan phase 4). When they come, they
  join *Open work*.

## 2. Standards and practice

- **TPM, autonomous maintenance and the defect tag.** In TPM the operator who
  finds an abnormality hangs a tag on the machine, and the tag stays until the
  fault is fixed. The finder follows the tag to the end. *Raised by me* is that
  follow-up on screen: the operator or supervisor sees whether their report was
  acknowledged, worked and closed, without asking.
- **Planned maintenance practice: one visible job list per person.** Good
  maintenance planning gives each craftsperson a clear list of assigned work,
  in priority order, so nobody has to search for the next job. *Open work*
  uses the priority the Tickets list already has: breakdowns first, then the
  oldest (S017 § 5.3, S019 § 1.6). Plain practice; no clause number.
- **EN 13306 (maintenance terminology).** The page uses the step's existing
  standard terms: *breakdown*, *defect*, *back in service*, *corrective
  maintenance*. It adds no new term.
- **ISO 9001 § 7.5.3 (control of documented information).** Records must stay
  available and protected. *My activity* reads the existing ticket timeline;
  it changes nothing, and it shows the current text of a corrected note
  (S027 keeps the earlier text on the ticket page).
- **ISO/IEC 27001 A.5.15 (access control).** The page shows only tickets the
  person may open today: every list goes through the same unit-access rule as
  the Tickets list (§ 5.1). A person moved off a unit no longer sees that
  unit's tickets, even ones they raised or worked.

## 3. Where

### Backend

- `backend/tickets.py`
  - `list_tickets`: a new query argument `raised` (`enum_arg("raised",
    ("me",))`): `(t.created_by = %s OR t.reported_by_id = %s)` with `actor()`
    and `current_person_id(cur)`; when the person is None, only
    `t.created_by = %s` (§ 5.2). It combines with every other filter by AND.
  - a new route `GET /api/tickets/activity` (`list_activity`,
    `@require_perm(READ_KEY)`), § 6, on `tickets_bp`. It cannot collide
    with `/<int:ticket_id>`, which matches digits only.
  - a module docstring line for S031.
- `backend/local_db.py`: migration **v26** "Indexes for the Me page (S031)",
  two statements (§ 4). `LATEST_VERSION` follows from `_MIGRATIONS`.

### Frontend

- `frontend/src/stores/navigation.js`: the *Me* item after *Tickets* (§ 1.1).
- `frontend/src/router/index.js`: route `/me`, name `me`, `MeView`, meta
  title *Me*. `canOpenRoute("me", …)` then follows the nav item's
  `ticket:read`.
- `frontend/src/views/MeView.vue` (new): the page and its three tabs.
- `frontend/src/components/TicketRow.vue` (new): the row moved out of
  `TicketsView.vue` (props `ticket`, `now`).
- `frontend/src/views/TicketsView.vue`: uses `TicketRow`; nothing else
  changes.
- `frontend/src/utils/ticketLabels.js`: `activityDetail(item)`,
  `isBackdated(item)` (pure, § 5.3) and `defaultMeTab(permissions)` (§ 1.2).

### Tests

- `backend/tests/test_my_tickets_api.py` (new): § 8 API.
- `backend/tests/test_migration_v26.py` (new): § 8 Migration.
- `frontend/tests/navigation.test.js`: the expected nav lists gain `me` after
  `tickets` for every role holding `ticket:read`; the storekeeper's stays
  `["equipment", "masters"]`; the landing page stays Equipment.
- `frontend/tests/ticketLabels.test.js`: `activityDetail`, `isBackdated`,
  `defaultMeTab`.
- `frontend/e2e/me.spec.js` (new): § 8 Automated.
- `frontend/e2e/screens.spec.js`: a `/me` row for `TICKET_ROLES`, showing
  the *My activity* tab button (present for every role, whatever the
  default tab).

### Docs (at approval, by the planner)

- `docs/Plan.MD` (BR1-06):
  - the Me page in the module list, with what it holds and what it leaves
    out;
  - § 6 Screens, the phone *Home: "my jobs"* line becomes: "*Me* (S031): open
    work assigned to me, tickets I raised, my activity; PM jobs due and CIL
    jobs join *Open work* in phase 4; the landing page stays Equipment (U1,
    23-10-2026)";
  - § 4.6: *My activity* is the per-person view of the Daily work log, which
    stays a phase 5 report.
- `.claude/CLAUDE.md` § SMTW-Review: the spec map gains `me` S031.

## 4. Data model (migration v26)

No new table and no new column. Two indexes, so the two new queries read an
index instead of the whole table:

```sql
CREATE INDEX IF NOT EXISTS ix_ticket_events_created_by ON ticket_events (created_by, created_at, id);
CREATE INDEX IF NOT EXISTS ix_tickets_created_by ON tickets (created_by);
```

- `ticket_events` has only `ix_ticket_events_ticket (ticket_id, occurred_at,
  id)` and the FK index on `person_id` (`local_db.py` v20). *My activity*
  filters on `created_by` and orders by `created_at, id`, so without the
  index every page view reads every event and sorts them. With `id` last,
  the index also serves the tiebreak (BR1-07), as `ix_ticket_events_ticket`
  does.
- `tickets` has no index on `created_by`. `reported_by_id` already has one
  (the index InnoDB creates for `fk_tickets_reported_by`). With both, MariaDB
  can answer the `OR` of § 5.2 from two indexes (index merge) once the table
  is large. On the small test databases the optimizer scans instead, so the
  coder reports the `EXPLAIN` output as information only (BR1-03); the
  migration test checks the indexes.
- `IF NOT EXISTS` makes a re-run of a half-applied v26 safe: on the dev
  image `mariadb:11.4` (`tooling/dev/docker-compose.dev.yml`) a second
  `CREATE INDEX IF NOT EXISTS` of the same name is a no-op (checked
  23-10-2026). Production's MariaDB runs on db-server and its version is not
  in the devops repo (`erp_server/yantra/compose.yml.j2` has no database
  service); the syntax exists since MariaDB 10.1 (to verify on db-server).
- **No `_PRECONDITIONS` entry**: adding an index reads the rows but changes
  none, and it cannot fail on any value the columns can hold (CLAUDE.md
  § Migrations asks for one only for a migration that cannot run on existing
  data). The upgrade test still starts from a v25 database with rows.
- The previous release runs on v26 unchanged (it ignores the indexes), so a
  rollback needs no restore.

## 5. Rules

### 5.1 Who sees what

- Every route is `@require_perm("ticket:read")`. `ticket:read` is in
  `SITE_SCOPED`; as on the Tickets list, the decorator checks the union and
  `_visible_condition(cur)` limits the rows to the units where the user holds
  `ticket:read` (`accessible_unit_ids(cur, READ_KEY)`). No new key, no new
  role.
- Holders (`config_rbac.py` `PERMISSIONS["ticket:read"]`): every maintenance
  site role and the supervisor (through the role ladder from
  `maint_operator`), and `it_admin`; admin bypasses. The storekeeper holds no
  ticket key: no *Me* item, and `/me` typed in redirects to the landing page,
  Equipment (`canOpenRoute` in the router guard).
- A user who may see no ticket at all (`_visible_condition` returns None)
  gets an empty list from every route, as from the Tickets list; the page
  shows the *no units* text (§ 1.2, BR1-04).
- **Identity.** "Me" is always the validated token's user: `actor()`
  (`g.user["username"]`, the value every `created_by` holds) and
  `current_person_id(cur)` (the active Team record with that login). Nothing
  in the request names the person. A request with no valid token gets 401
  from the auth hook before any route (`auth_utils.py`); the e2e stub user
  "nobody" holds no key, so `require_perm` refuses it with 403 (BR1-09).
  Never admin.
- An inactive Team record counts as none (`current_person_id` filters
  `active = 1`): *Open work* shows the "not in Team" message; the other two
  tabs still match by login.

### 5.2 Which rows

- **Open work**: the existing `assigned=me` filter, unchanged.
- **Raised by me**: tickets whose `created_by` is my login (I pressed
  *Raise*), or whose `reported_by_id` is my Team record (someone raised it
  for me and named me as the reporter, S017). Both, because an operator
  without a phone often reports through the supervisor, and the supervisor's
  own raises carry the supervisor's login.
- **My activity**: `ticket_events` rows whose `created_by` is my login, on a
  ticket that passes `_visible_condition`, ordered `e.created_at DESC, e.id
  DESC`. All event kinds count, including the `assigned` line written when
  my *Start* or *Acknowledge* assigned me (`_assign`, `tickets.py`), and the
  `raised` line of each ticket I raised.
- `created_by` is compared with `actor()` exactly as stored. The tables use a
  case-insensitive collation (on the dev server `utf8mb4_uca1400_ai_ci`,
  checked 23-10-2026: `information_schema.TABLES`; `SELECT 'Kla' = 'kla'`
  → 1; production's server version is to verify, § 4), so a login in another
  case still matches (BR1-08). The API test pins it with an upper-case
  `created_by`.

### 5.3 What each activity row says (`activityDetail`, Scope B)

Pure: one item of the activity API in, one string or null out.

| Event | Detail |
|---|---|
| `assigned`, `unassigned`, `started` | the person's name (`item.person.name`), when present |
| `regraded` | "Now " + the intensity's label (`INTENSITY_LABELS`) |
| `scheduled`, `rescheduled` | `planText(item.planned_date, item.waiting_reason)` |
| `note`, `edited`, and any event with a `remark` | the remark, cut to 120 characters with "…" |
| any other | null |

`isBackdated(item)`: true when the IST date of `occurred_at` is before the
IST date of `created_at` (both are ISO strings with `+05:30`, `db_helpers.py`
`row_to_dict`), so the row adds "· happened …" (§ 1.5).

### 5.4 Transactions, locks and the database down

- Read-only: plain `SELECT`s, no transaction of their own, no lock. Nothing
  to order against the LOCK ORDER notes in `tickets.py`.
- The database down: `get_db()` raises `DBUnavailable` → 503, as on every
  route; the page shows the message and *Retry*. The worker is not touched.

## 6. API

**`GET /api/tickets?raised=me`** — the existing list with one more filter.
`raised` other than `me` → 400 "raised must be one of: me" (`enum_arg`).
The answer's shape is unchanged.

**`GET /api/tickets/activity?page=&per_page=`** — `page` and `per_page` as on
the list (`int_arg`, `DEFAULT_PER_PAGE` 50, `MAX_PER_PAGE` 200, `MAX_PAGE`).

```json
{
  "items": [{
    "id": 812, "event": "note", "occurred_at": "2026-10-23T10:42:00+05:30",
    "created_at": "2026-10-23T10:42:05+05:30", "intensity": null,
    "remark": "Belt loose, tightened", "planned_date": null, "waiting_reason": null,
    "person": null,
    "ticket": {"id": 41, "serial": "TK-0041", "intensity": "critical", "state": "in_progress",
               "machine": {"id": 7, "code": "EXT01", "name": "Extruder 1"}}
  }],
  "total": 1, "page": 1, "per_page": 50
}
```

- `person` is `{id, name}` of `ticket_events.person_id`, or null.
- `intensity` is the event's (set on `raised` and `regraded`), not the
  ticket's.
- Errors: 400 for a bad `page` / `per_page` (`int_arg`), 403 without
  `ticket:read`, 503 with the database down.

## 7. Design decisions

1. **One page with tabs, not three nav items or one long page.** On a phone a
   long page buries *My activity* under two lists. Tabs keep one nav item and
   one tap per list. Rejected: three stacked sections (scrolling, and three
   API calls on every open).
2. **Nav permission `ticket:read`, not "has a Team record".** I offered "shown
   to anyone with a Team record" at U1. Two of the three tabs work by login
   alone (an IT admin without a Team record still raises tickets), and the
   nav filter is permission-based (`canSeeNavItem`). Adding a person check
   would change `canSeeNavItem` and the router guard for one item. So: shown
   with `ticket:read`, and *Open work* explains a missing Team record.
   The code supports it (BR1-12): the only `ticket:read` holders without a
   Team record are the token roles `it_admin` and admin; the only
   Team-record holders without `ticket:read` are storekeepers. "Has a Team
   record" would show *Me* to the storekeeper (nothing to show) and hide it
   from IT admin (who raises tickets). It is also the base's rule: the lowest
   permission that gives the page meaningful content.
   **A departure from the U1 option text**; the user confirms at gate A.
3. **Reuse the ticket list API for the two ticket tabs.** `assigned=me`
   exists; `raised=me` is one more condition on the same query, with the same
   paging, order, row shape and access rule. Rejected: a separate `/api/me`
   blueprint, which would copy the list query.
4. **The ticket row becomes a component.** The tabs show the same row as the
   Tickets list; copying its template breaks DRY (CLAUDE-COMMON). Moving it
   touches `TicketsView.vue`; the existing tickets e2e specs check the row.
5. **Activity = what I recorded (`created_by`), not lines naming me
   (`person_id`).** `ticket_events.person_id` is the person a line is about
   (the assignee, the technician who started), not the one who pressed the
   button (`_add_event` and `_assign`, `tickets.py`). Lines about me already
   show as tickets in *Open work*.
6. **Order by the time recorded, show the line's own time only when it is on
   an earlier day.** A log of what I did reads in the order I did it. A
   back-dated entry (S028 backlog, until 30-11-2026) would otherwise drop far
   down the list. Rejected: ordering by `occurred_at` (the timeline's order),
   and a minutes threshold for "happened" (a magic number).
7. **Add the two indexes (v26).** CLAUDE-COMMON asks to avoid needless
   full-table scans, and the events table grows with every move. The cost is
   an index-only migration with no data change. Rejected: no migration, and
   the step would read the whole events table on every *My activity* view.
8. **No date limit on *My activity***; paging is enough at 50 users.
9. **The default tab follows the work the user does** (BR1-01). Rejected:
   *Open work* first for everyone (an operator would always land on an empty
   tab), and *Raised by me* first for everyone (wrong for technicians).

## 8. Tests and acceptance

### API (`test_my_tickets_api.py`)

Fixtures as `test_ticket_work_api.py` (`role_client`, `make_person`,
`give_site_role`, `make_ticket`, `machine`, `uniq`; the `tech` fixture's
pattern for a client with a Team record). The session database gives the
schema; each test makes its own people and tickets and asserts only on them.

- `raised=me`: my raise is listed; a ticket another user raised with me as
  `reported_by_id` is listed; another user's ticket without me is not; a user
  with no Team record gets the tickets raised by their login only; a ticket
  at a unit I no longer hold `ticket:read` at is not listed; `raised=you` →
  400 with field `raised`; `raised=me&state=closed` lists only closed ones.
- `activity`: after I raise and acknowledge a ticket, my items are
  `acknowledged`, `assigned`, `raised` (newest first; same `created_at` →
  higher `id` first); another user's lines on the same ticket are absent; a
  note shows its current text after an engineer corrects it; `person` and
  `ticket` are filled; `total` and paging (`per_page=1`, `page=2`); a ticket
  at a unit I lost drops out; an IT admin without a Team record sees their
  own lines; a stored `created_by` in upper case still matches (§ 5.2);
  storekeeper → 403; `page=0` → 400.
- The database down: `/api/tickets/activity` → 503. The `db_down` fixture is
  local to `test_access_control_api.py` and `test_auth.py`, not in
  `conftest.py`; the new file defines the same two-line fixture
  (`monkeypatch` of `db_helpers.ensure_schema` and
  `access_control.ensure_schema`), as `test_auth.py` does.
- Existing tests: `test_rbac.py` `test_role_matrix` is unchanged (no new
  key); `conftest.py` `_TABLES` is unchanged (no new table);
  `test_modules.py` reads `LATEST_VERSION`, so it follows v26; the
  `test_migration_v2*` tests pin their own version lists and stay green.

### Migration (`test_migration_v26.py`)

On the pattern of `test_migration_v24.py`:
- a fresh database gets v26 and both indexes (`information_schema.STATISTICS`,
  name, columns in order);
- a v25 database with a ticket, events and a person gets v26 and keeps every
  row of `tickets` and `ticket_events`;
- running v26's statements again changes nothing.

### Frontend unit

- `navigation.test.js`: the updated lists (§ 3 Tests); `canOpenRoute("me",
  STOREKEEPER)` is false.
- `ticketLabels.test.js`: each row of the § 5.3 table, a 121-character remark
  cut to 120 + "…", null for `acknowledged`; `isBackdated` true for the day
  before, false for the same day at an earlier time; `defaultMeTab` →
  `open` with `ticket:work`, `raised` without it (the operator's list).

### Automated (e2e, `me.spec.js`; the full suite, because the router changes)

Set-up by API (S024 convention); each test makes its own ticket and finds it
by serial, because other specs in the same lane add tickets.

- **important** — A technician acknowledges a new ticket (by API), opens *Me*
  from the bottom bar (phone) or sidebar (desktop): *Open work* lists the
  ticket's serial, and a tap opens the ticket page.
- **important** — An operator raises a ticket and opens *Me*: the page opens
  on *Raised by me* (the default without `ticket:work`), and the serial is
  listed with state *Raised*. After the engineer closes it as not a fault
  (by API: `moveByApi(engineer, id, "not-a-fault", …)` with a cause and a
  remark, the shortest close from *Raised*; BR1-13), *State: Closed* lists
  it, and the row reads "Closed · Not a fault".
- **important** — The technician's *My activity* shows *Acknowledged* with the
  ticket's serial as its first row. The operator's *Raised* line on the same
  ticket is not listed there.
- The IT admin seed person (`e2e_it_admin`, no Team record:
  `tooling/e2e/seed_e2e.py` `IT_ADMIN`, kept out of `PEOPLE`) sees the "not
  in Team" message on *Open work*, and their own raise on *Raised by me*.
- From *My activity*, a row opens the ticket; Back returns to *My activity*,
  not to the default tab (BR1-05).
- The storekeeper sees no *Me* in the nav, and typing `/me` lands on
  Equipment (BR1-14).
- On Pixel 7 and iPhone 14 the three tabs fit the width with no horizontal
  page scroll (the `pageWidth` check of `frontend/e2e/support/dialogs.js`).
- `screens.spec.js`: `/me` opens for every ticket role, title *Me*.

### On a real device

- Plain, IT Admin, production on the TEST machine, a technician account,
  plant Wi-Fi: open *Me* on a phone and switch the three tabs with a thumb.

### Acceptance

- `tooling/run-tests.bat`: all four suites green.
- The e2e full suite green.
- The impl report shows the `EXPLAIN` of both new queries, as information
  (§ 4, BR1-03).

## 9. Open questions and assumptions

1. **Tab names** (assumption): *Open work*, *Raised by me*, *My activity*.
   Alternatives: *Assigned to me* for the first (the Tickets checkbox's
   words). Recommended: *Open work*, shorter on a phone.
2. **Nav label *Me*** (assumption, the user's word). Alternative: *My work*.
3. **Decision 7.2** — nav shown with `ticket:read`, not "has a Team record":
   confirm at gate A.
4. **Raised by me includes `reported_by_id`** (§ 5.2): assumed wanted, so an
   operator named as reporter follows the ticket too. The tab name hides
   that half; the alternative is *My tickets* (BR1-11). Recommended: keep
   *Raised by me*, with the empty text "No tickets raised by you or for
   you."
5. Assumption: the *Raised by me* tab defaults to *All* (open and closed,
   newest first), so a recently closed report is in view.

**Answered at gate A (KLA, 23-10-2026):** the brief was approved as it
stands, so every recommendation above holds: tab names *Open work*, *Raised
by me*, *My activity*; nav label *Me*; decision 7.2 confirmed (nav shown with
`ticket:read`); *Raised by me* includes `reported_by_id`; the tab defaults to
*All*.

## 10. Amendments

None.

## Review log

### U1 — user answers, 23-10-2026 (before drafting)

- Content: *My open work*, *Tickets I raised*, *My activity log*. Not *My time
  booked*.
- Placement: a new nav item *Me*; not the landing page; *My notifications*
  stays under the bell.

### Round 1 — `2-brief-review-r1.md` (Fable), answered 23-10-2026

0 blocker, 0 major, 6 minor, 10 nits.

| Finding | Answer |
|---|---|
| BR1-01 minor — default tab empty for operators | Accepted (a): default by `ticket:work` (`defaultMeTab`), § 1.2, decision 7.9, unit test, e2e check |
| BR1-02 minor — "not linked" text for the wrong reader | Accepted (a): the `NotificationsView.vue` texts, IT admin vs others, § 1.3 |
| BR1-03 minor — `EXPLAIN` criterion not met on small tables | Accepted (a): `EXPLAIN` reported as information only; § 4 fragment rewritten; Acceptance changed |
| BR1-04 minor — no-units state | Accepted (a): `ensureMyUnits()` and the Tickets list's `noUnits` text, § 1.2, § 5.1 |
| BR1-05 minor — Back is a browser check | Accepted (a): new e2e check; the device row keeps only the thumb part |
| BR1-06 minor — Plan.MD § 6 "Home: my jobs" | Accepted (a): § 3 Docs names Plan.MD § 6 and § 4.6 |
| BR1-07…BR1-16 nits | Accepted, except BR1-15. BR1-07: `id` added to the events index. BR1-08: collation claim not tied to one server. BR1-09: 401 and 403 cases stated. BR1-10: message only after a successful load. BR1-11: empty text changed; tab name in open question 4. BR1-12: fact added to decision 7.2. BR1-13: not-a-fault close path named, "Closed · Not a fault" asserted. BR1-14: `/me` as storekeeper lands on Equipment. BR1-16: header date. **BR1-15 rejected**: *My activity* says what I did; the row opens the ticket for what was wrong, and adding the problem text would widen the activity API for little gain. |

### Gate A — approved 23-10-2026 by KLA

Approved as it stands, with the recommendations of § 9 (answers there).
Coder: Sonnet. Baseline: aad833a (the round 1 review's `Reviewed against:`).
