```
Step: S028 — Back-dating window: admin and backlog entry
Doc: brief
Author: Planner (Opus)
Date: 22-10-2026 (revised 22-10-2026: brief-review r1, r2; user answers Q1 (b), Q2 (b))
Track: full
Baseline: d686fcd
Status: Done (committed 12a1238, with S029; checks: 2 auto; CR r1: 5 nits left; approved 22-10-2026 by KLA; Q1 (b), Q2 (b), A1, A2 confirmed)
```

# S028 — Back-dating window: admin and backlog entry

**The request (KLA, 22-10-2026).** An entered ticket time may be at most 7 days
back (S017 § 7 decision 9). Two changes:

- **admin** is exempt from the 7 days;
- **until 30-11-2026**, everyone may enter older times, so the plant can enter
  its backlog (breakdowns and defects kept in notebooks) with their real dates.

The user's answers (22-10-2026, before this brief):

| # | Question | Answer |
|---|---|---|
| U1 | Which entered times? | **Every entered time**: the raise's *When did it happen?* and every move's time (start, back in service, close, send back, regrade, and the raise's *Already fixed* times). They all pass `tickets_core.event_time_error`. |
| U2 | How far back in the backlog window? | **3 years** |
| U3 | Admin limit | Exempt from the 7 days, but **the same 3-year floor**, always (also after 30-11-2026) |
| U4 | Who may make backlog entries? | **Everyone who may raise or move** the ticket, until 30-11-2026 |

## 1. What will be built

One rule for the oldest time a user may enter:

| Who | Entered on or before 30-11-2026 (IST) | Entered from 01-12-2026 |
|---|---|---|
| admin | 3 years back | 3 years back |
| everyone else, IT admin included | 3 years back | 7 days back (as today) |

- "3 years" is **1095 days** (`LONG_BACKDATE_DAYS = LONG_BACKDATE_YEARS * 365`,
  `LONG_BACKDATE_YEARS = 3`). A leap day makes it one day short of three
  calendar years; that is harmless and keeps the rule one subtraction like the
  7 days.
- The day of the cut-off is the **IST date of the server's clock at entry**
  (`now.date()`, `tickets._now()` at `backend/tickets.py:159`). 30-11-2026 is the
  last day of the window (inclusive).
- The other two limits stay as they are: at most `FUTURE_SKEW` (5 min) ahead,
  and never before the ticket's last ordered event (S018).
- The refusal names the limit that applies to the user:
  - 7 days: `When did it happen? Up to 7 days back` (unchanged,
    `tickets_core.py:69`);
  - 3 years: `When did it happen? Up to 3 years back` (new).
- **Admin through a permission key, not a role name.** A new global key
  `ticket:backdate` is granted to no role (`()`). Admin holds it through the
  admin bypass (`compute_permissions(["admin"])` gives every key,
  `access_core.py:51-52`, tested at `test_rbac.py:153`), so only admin has it
  today. A later step can grant it to, say, the maintenance manager by editing
  `config_rbac.py` only.
- The time fields stay plain `datetime-local` inputs with no `min` or `max`
  (`RaiseTicketView.vue:453`, `tickets/EventFields.vue:72`,
  `tickets/StartedAtFields.vue`); the refusal comes from the server and already
  shows beside the field.
- **How far back (Q1 (b), § 4.5).** Under each of those time fields, when the
  entered time is more than 7 days before now, a muted one-line hint shows
  `That was 412 days ago` (`That was 1 day ago` is never shown: the hint starts
  at 8 days). Display only, for every user; the server's rule is unchanged.
- **No alerts for history (Q2 (b), § 4.6).** A raise whose entered time is more
  than 7 days before now sends no alert and queues no escalation. A raise
  within 7 days alerts as today; regrade, send-back and assignment alerts are
  unchanged.
- Docs: Plan.MD and the maintenance philosophy record that the backlog is now
  entered by hand until 30-11-2026 (§ 9).

### 1.1 Out of scope

- A bulk import of the notebooks (CSV or Excel). Entry stays one ticket at a
  time on the existing screens.
- A mark on a ticket that says "backlog entry". The two times already tell it
  apart: `ticket_events.occurred_at` is the entered time, `created_at` the
  moment of entry (`local_db.py:410`, `:414`).
- The repeat window (`REPEAT_WINDOW_DAYS = 7`, `tickets_core.py:299`) and the
  labour date rule (not before the raise date, `validate_labour`,
  `tickets_core.py:639`). Both measure from the entered times, so they work
  for old tickets unchanged.
- The planned date of a deferred ticket: it must be today or later
  (`planned_date_error`, `tickets_core.py:541`); a backlog ticket cannot carry
  its old plan date (§ 6).
- The serial. It takes the month of entry (`tickets.py:762`), so a ticket for
  a breakdown of 2024 entered now is `TK-2026-10-…`. The serial is a number to
  find the ticket by, not its date (S017).

## 2. Standards and practice

- **ISO 14224:2016 § 9.5 and Table 6** record each failure with its **failure
  date** (when it was detected); **§ 9.6 and Table 8** record each maintenance
  action with its date, downtime and man-hours. Annex C computes MTBF and MTTR
  from those dates. So the backlog must carry the real dates, not the date of
  entry — that is what this step allows.
- **ISO 14224 § 7 (quality of data)** asks for data that is complete, accurate
  and plausible. This is why S017 capped back-dating: a wrong year typed by
  mistake goes into MTBF. The backlog window lifts the cap for five weeks;
  Q1 asks how to keep typos visible meanwhile.
- **EN 15341:2019 and SMRP Best Practice metrics** (e.g. 3.5.1 MTBF, 3.5.2
  MTTR) are computed over a reporting period; a late entry moves that period's
  figure. The backlog window is a **deliberate, dated departure** from S017
  § 7 decision 9: old entries land in their own months, where they belong. No
  KPI is built yet, so nothing shown today changes.
- **ISO 9001:2015 § 7.5.3 (control of documented information)**: records are
  retained documented information (§ 7.5.3.2). Who entered what and when stays
  traceable through `created_by` and `created_at` on every event, so a backlog
  entry is never mistaken for a live one.
- **ISO 27001:2022 A.8.2 (privileged access rights)**: writing history further
  back than everyone else is a privileged right. It is held by the admin
  account only, and granting it to anyone else takes a code change.

## 3. Where

| File | Change |
|---|---|
| `backend/tickets_core.py` | `LONG_BACKDATE_YEARS`, `LONG_BACKDATE_DAYS`, `BACKLOG_UNTIL`; `EVENT_TIME_TOO_OLD_LONG`; pure `backdate_days(now, may_backdate)` and `too_old_message(max_back_days)`; `event_time_error`, `validate_raise` and `validate_event_time` take `max_back_days` |
| `backend/tickets.py` | `BACKDATE_KEY`; `_max_back_days(now)`; `raise_ticket` and `_event_time` pass it |
| `backend/config_rbac.py` | `"ticket:backdate": ()` with a comment; not in `SITE_SCOPED` |
| `backend/tests/conftest.py` | new `keycloak_admin` fixture (`role_client("admin")`) |
| `backend/tests/test_tickets_core.py` | the window tests with the new argument; new `backdate_days` and `too_old_message` tests |
| `backend/tests/test_tickets_api.py` | `test_event_time_out_of_the_window_is_400` changed; new API tests (§ 7) |
| `backend/tests/test_rbac.py` | `ticket:backdate` held by admin only, global |
| `frontend/e2e/tickets-raise.spec.js` | one admin test: raise 30 days back (§ 7) |
| `backend/alerts_core.py` | `raise_alert(intensity, age)`: `None` when `age` is more than `MAX_BACKDATE_DAYS` (§ 4.6) |
| `backend/tests/test_alerts_core.py` | `raise_alert` age cases |
| `frontend/src/utils/ticketLabels.js` | `MAX_BACKDATE_DAYS = 7` (mirror) and pure `daysAgoHint(entered, now)` (§ 4.5) |
| `frontend/tests/ticketLabels.test.js` | `daysAgoHint` cases |
| `frontend/src/views/RaiseTicketView.vue` | the hint under *When did it happen?* and under the *Already fixed* time |
| `frontend/src/views/tickets/EventFields.vue` | the hint under the move's time |
| `frontend/src/views/tickets/StartedAtFields.vue` | the hint under *Started* |
| `docs/Plan.MD` | § 2 (`:65`), § 3 (`:150-166`), § 4.2 (`:328`) (§ 9) |
| `docs/Maintenance-Philosophy.md` | § 1 (`:25`) (§ 9) |
| `docs/steps/README.md` | index row |

15 code and test files, 3 docs. No migration, no new table, no API change.

## 4. Design

### 4.1 The pure core (`tickets_core.py`)

```python
MAX_BACKDATE_DAYS = 7                                   # unchanged
LONG_BACKDATE_YEARS = 3                                 # S028: admin always; everyone in the backlog window
LONG_BACKDATE_DAYS = LONG_BACKDATE_YEARS * 365          # a leap day short of the calendar years, on purpose
BACKLOG_UNTIL = date(2026, 11, 30)                      # S028: last IST day of the backlog window (inclusive)

EVENT_TIME_TOO_OLD = f"When did it happen? Up to {MAX_BACKDATE_DAYS} days back"          # unchanged
EVENT_TIME_TOO_OLD_LONG = f"When did it happen? Up to {LONG_BACKDATE_YEARS} years back"

def backdate_days(now, may_backdate):
    """How many days back an entered time may lie: LONG_BACKDATE_DAYS for a holder of
    ticket:backdate, and for everyone while now's date is on or before BACKLOG_UNTIL;
    otherwise MAX_BACKDATE_DAYS."""

def too_old_message(max_back_days):
    """The refusal for a time older than the limit: EVENT_TIME_TOO_OLD_LONG for the long
    limit, EVENT_TIME_TOO_OLD for the 7 days."""

def event_time_error(event_time, now, max_back_days, not_before=None):
    # too old: event_time < now - timedelta(days=max_back_days) -> too_old_message(max_back_days)
```

- `max_back_days` is a **required** argument, so no caller can forget it and
  fall back to 7 days silently.
- `backdate_days` reads `BACKLOG_UNTIL` at call time (a module global), so a
  test can move the cut-off with `monkeypatch.setattr(tickets_core,
  "BACKLOG_UNTIL", …)`.
- `too_old_message` takes only `MAX_BACKDATE_DAYS` or `LONG_BACKDATE_DAYS`;
  any other value is a programming error (`assert`, as `_check_site_args`
  does).
- The message follows the limit, not the role: a user in the backlog window
  sees "3 years" like admin.
- `validate_raise(body, now, max_back_days)` and
  `validate_event_time(event_time, last_event, now, max_back_days, labels=…)`
  pass it on. Their other behaviour is unchanged.

### 4.2 The shell (`tickets.py`)

- `BACKDATE_KEY = "ticket:backdate"` next to the other key constants.
- `_max_back_days(now)` returns `backdate_days(now, has_perm(BACKDATE_KEY))`.
- `raise_ticket` (`tickets.py:728-729`) computes it once and passes it to
  `validate_raise`.
- `_event_time` (`tickets.py:819`) computes it and passes it to
  `validate_event_time`. Every move goes through `_event_time` (start `:881`,
  every move `:1004`, regrade `:1043`), and so does the raise's *Already fixed*
  block (`_apply_move` with `RESTORE_FIELD_PREFIX`, `:782`). A raise with
  *Already fixed* calls `has_perm` up to three times; `current_memberships`
  caches the memberships in `g` (`auth_utils.py:272-289`), so it is one query
  at most, and none for admin (`auth_utils.py:356`).
- With the DB down, the request is a 503 at or before that read, as every
  ticket route is today.

### 4.3 The key (`config_rbac.py`)

```python
# Back-dating beyond the 7 days (S028): no role holds it, so only admin does (the bypass;
# ISO 27001 A.8.2, a privileged right).  A role granted it later enters times up to
# LONG_BACKDATE_DAYS back.  Global: if a site role is ever granted it, it joins SITE_SCOPED
# and is checked at the ticket's site.
"ticket:backdate": (),
```

- `test_role_matrix` (`test_rbac.py:191`) is unchanged: no role gets the key.
- `test_admin_gets_all_permissions` (`test_rbac.py:153`) still passes: admin's
  list now includes the key.
- `test_permission_values_are_tuples` (`:41`): `()` is a tuple.
- Admin's key list from `/api/auth/me` grows by one key; no screen reads it.
- `it_admin` does **not** get the key (§ 8 assumption A1).

### 4.5 The hint (Q1 (b))

- `ticketLabels.js`: `export const MAX_BACKDATE_DAYS = 7;` with the comment
  "tickets_core.MAX_BACKDATE_DAYS; the server checks the limit", as
  `PLANNED_DATE_MAX_DAYS` does (`ticketLabels.js:293-294`).
- `daysAgoHint(entered, now)`: `entered` is the field's value
  (`YYYY-MM-DDTHH:MM`, local), `now` a `Date`. Returns `That was N days ago`
  with N = whole days (`Math.floor`) between them when N > `MAX_BACKDATE_DAYS`;
  otherwise `""`. Empty, unparsable or future values → `""`. Pure, so
  vitest can pass a fixed `now`.
- Each of the three components shows it as `<div class="form-text">` under the
  field (below the refusal, when both show), computed from the field's value
  with `new Date()` at render. The phone's clock is good enough for a hint;
  the server's clock still decides.
- It shows for every user, admin included: its purpose is to make a wrong
  year or month visible, not to refuse.

### 4.6 No alerts for history (Q2 (b))

- `alerts_core.raise_alert(intensity, age)`: `age` is a `timedelta`
  (`now - occurred_at`). More than `timedelta(days=MAX_BACKDATE_DAYS)` (imported
  from `tickets_core`, which `alerts_core` already imports from,
  `alerts_core.py:15`) → `None` (nothing, as *Already fixed*). Otherwise as
  today: a breakdown alerts and escalates, a defect alerts quietly.
- `raise_ticket` (`tickets.py:787`) passes `now - clean["occurred_at"]`.
  `occurred_at` is `now` when none was entered, so the age is 0.
- Exactly 7 days back still alerts (`>`, the same boundary as the window's
  accepted 7 days).
- `enqueue_alert` already does nothing for `None` (`alerts.py:65-66`).

### 4.7 Design decisions

| # | Decision | Why | Rejected alternative |
|---|---|---|---|
| D1 | Admin's exemption is a key granted to no role | CLAUDE-COMMON RBAC: code names keys, never roles; admin bypasses in code. A later grant needs no code change. | `is_admin()` in `tickets.py`: names a role in route code |
| D2 | The key is global, not site-scoped | Only admin holds it; the raise validates the time before it loads the node (`tickets.py:729` vs `:733`), so a site check would move the validation into the transaction | Site-scoped now: more code for a holder that does not exist yet |
| D3 | The cut-off is a dated constant in code | One date, known now; it ends on its own on 01-12-2026 with no deploy. Removing the constant later is a tidy-up, not a fix. | A setting in Settings › Tickets: a migration and a screen for a one-off window |
| D4 | 3 years as 1095 days | Same shape as the 7 days; one day of difference in a leap year does not matter | Calendar years (`date.replace(year=…)`): a 29 Feb special case for nothing |
| D5 | Every entered time, not only the raise (U1) | A backlog ticket must also get its real start, back-in-service and close times | Raise only: old tickets could be raised but not completed |

## 5. Edge cases

- **Exactly 7 days / 1095 days back**: accepted (`<`, as today,
  `tickets_core.py:107`). 7 days and 1 minute back: refused outside the window.
- **30-11-2026 23:59 IST**: in the window. **01-12-2026 00:00 IST**: out of it
  for non-admin.
- **A ticket raised in the window, moved after it**: the move's time must be
  within 7 days of now (non-admin) and not before the last event. A backlog
  ticket left open at 01-12-2026 can still be worked with current times.
- **No identity**: `require_perm` refuses the route first; `has_perm` with no
  `g.user` is `False` (`auth_utils.py:352-355`), never admin.
- **IT admin** (`it_admin`) is not admin and does not hold the key: 7 days after
  30-11-2026, like everyone else.
- **Missing `occurred_at`**: the server's clock, as today; the window plays no
  part.

## 6. Notes for users (for the release notes, not built)

- Until 30-11-2026 you can enter breakdowns and defects up to 3 years back.
- Enter the backlog **oldest first**. A repeat ("the same fault again") needs
  the earlier ticket to exist and to be back in service within 7 days before
  the new one (`_check_repeat`, `tickets.py:694-708`).
- For a breakdown that is already fixed, tick *Already fixed* on the raise
  screen and enter the times it happened and went back in service. No alert is
  sent.
- A deferred job from the notebook cannot keep its old plan date: plan it for
  today or later, or leave it raised.
- From 01-12-2026 only admin can enter times older than 7 days.

## 7. Tests

**Fixture note.** The `admin` fixture is **IT admin**
(`conftest.py:315-317`, `role_client("it_admin")`). This step adds
`keycloak_admin` = `role_client("admin")` (`tests/harness.py:24` accepts the
`admin` token role). Every "admin" case below uses `keycloak_admin`; the
`admin` fixture appears only as IT admin.

**Unit (`test_tickets_core.py`, NOW = 20-10-2026 14:30 at `:29`):**
- `backdate_days`: may_backdate → 1095; not, on 30-11-2026 23:59 → 1095;
  not, on 01-12-2026 00:00 → 7; may_backdate on 01-12-2026 → 1095.
- `too_old_message`: 7 → `EVENT_TIME_TOO_OLD`; 1095 → `EVENT_TIME_TOO_OLD_LONG`,
  which contains "3 years".
- `event_time_error` with 7: 7 days back accepted, 8 refused with
  `EVENT_TIME_TOO_OLD` (the existing tests at `:100-105`, given the argument).
- `event_time_error` with 1095: 1095 days back accepted, 1096 refused with
  `EVENT_TIME_TOO_OLD_LONG`.
- `validate_raise` `test_occurred_at_refused` (`:159-165`) and
  `validate_event_time` (`:350-351`): pass 7 and keep their cases.

**API (`test_tickets_api.py`)**, independent of today's date: each test sets
`tickets_core.BACKLOG_UNTIL` with `monkeypatch` — a date before today for
"after the window", a date after today for "in the window":
- `test_event_time_out_of_the_window_is_400` (`:194-198`, IT admin): today it
  passes only because the 8-day case is refused; until 30-11-2026 it would
  fail. It gets `BACKLOG_UNTIL` patched to a past date and keeps its two cases
  (+10 min, 8 days back → 400). It now also stands as the IT-admin case.
- `keycloak_admin`, after the window: raise 30 days back → 201;
  1096 days back → 400 on `occurred_at` with "Up to 3 years back";
  +10 min → 400.
- operator, after the window: raise 8 days back → 400 on `occurred_at` with
  "Up to 7 days back".
- operator, in the window: raise 400 days back → 201; 1096 days back → 400 with
  "Up to 3 years back".
- operator, in the window: raise with *Already fixed* 100 days back, restore
  time 99 days back → 201 (the restore block passes the same limit).
- a move (start, as `at_unit("maint_technician")`, `conftest.py:534-536`) 30
  days back on a ticket raised 31 days back: after the window → 400; in the
  window → 200. The ticket is raised with
  `make_ticket(machine, client=keycloak_admin, …)` in both cases: `make_ticket`
  posts as the `admin` fixture (IT admin) by default, whose 31-days-back raise
  would be refused after the window before the move is tested (BR2-01).

**RBAC (`test_rbac.py`):** `ticket:backdate` is held by no role and by admin;
it is not in `SITE_SCOPED`.

**Existing tests affected (to change):** `test_tickets_core.py:100-105`,
`:159-165`, `:350-351` (new argument); `test_tickets_api.py:194-198`
(`BACKLOG_UNTIL` patched). No other caller of `event_time_error`,
`validate_raise` or `validate_event_time` (grep: `tickets.py:106`, `:729`,
`:827`; tests). `test_event_time_entered` (`test_tickets_api.py:72`, 2 days
back) and `test_ticket_work_api.py:1017` (a raise 2 days back) stay inside
every window.

**e2e (automated check, important):** in `tickets-raise.spec.js`, as admin
(`frontend/e2e/support/people.js:8`), fill *When did it happen?* 30 days back
(the spec's `istLocal` helper, `:119`), save; the timeline's first line shows
that time. Admin's limit does not depend on today's date, so the test holds
after 30-11-2026. It is the first spec acting as `admin` in the browser;
`seed_e2e.py` gives `e2e_admin` no display name, so the top bar shows the
login. That is enough for the test; no seed change. Targeted run:
`tickets-raise` plus `screens.spec.js`.

**Hint (Q1):** vitest `daysAgoHint`: 7 days back → `""`; 8 days →
`That was 8 days ago`; 412 days → `That was 412 days ago`; empty, garbage and
future → `""`. e2e (automated, important), in the admin raise test above: after
filling 30 days back, `That was 30 days ago` shows under the field.

**Alerts (Q2):** `test_alerts_core.py`: `raise_alert("critical", timedelta(0))` and at
exactly 7 days → `Alert(BREAKDOWN, True)`; 7 days and 1 minute → `None`;
`"degraded"` 8 days → `None`. The existing cases (`:49-51`) gain `timedelta(0)`.
API: `keycloak_admin` raises a breakdown 30 days back → no `task_queue` row
for the ticket; a breakdown 1 day back → the `ticket_alert` and
`ticket_escalate` rows as today (`BACKLOG_UNTIL` patched to the past, so
admin's key is what lets the raise in).

**Real-device checks:** none.

## 8. Open questions and assumptions

**Answered 22-10-2026 by KLA: Q1 (b), Q2 (b); A1 and A2 confirmed.** The
text below is kept as asked; the decisions are built into § 1, § 3, § 4.5,
§ 4.6 and § 7.

**Q1 — Should the screens show how far back an entered time is?** (BR1-02, a
consequence of U4.) Until 30-11-2026 a wrong year or month picked on a phone is
accepted silently and lands in a past month's history (ISO 14224 § 7).
- (a) Accept the risk for five weeks; say so in the release note. No more code.
- (b) **Recommended.** A one-line hint under each time field when the entered
  time is more than 7 days back: "That was 412 days ago". Display only,
  computed in the frontend from the field's value; no API change. Adds the
  three Vue files above and one helper in `frontend/src/utils/ticketLabels.js`,
  plus an e2e check (as admin, 30 days back, the hint shows).
- (c) A confirm step on save when the time is older than 7 days. More taps on
  every backlog entry.

**Q2 — Should a backlog raise send alerts?** (BR1-03, a consequence of U1 and
U4.) A backlog ticket raised **open** (a still-open defect from the notebook,
or a fixed breakdown where *Already fixed* was not ticked) pushes "new
breakdown" or "new defect" to engineers, the unit's supervisor and the manager,
and a breakdown queues an escalation (`tickets.py:783-788`). Thirty entries in
an afternoon are thirty pushes about old failures, and people learn to ignore
pushes (S021).
- (a) Keep alerts as they are; rely on the release note (*Already fixed*).
- (b) **Recommended.** One pure rule: a raise whose entered time is more than
  `MAX_BACKDATE_DAYS` before now is history, not news; it sends no alert and
  no escalation. `alerts_core.raise_alert` (`alerts_core.py:62`) takes the
  event's age; `raise_ticket` passes `now - occurred_at`. Two unit tests and
  one API test (no task row). Regrade and send-back alerts stay: they are live
  actions. Adds `alerts_core.py` and `test_alerts_core.py`.
- (c) No alerts for any raise during the window. Too broad: a real breakdown
  today must still alert.

**Assumptions:**
- **A1**: "admin" is the Keycloak admin role (`mspv-apps-admin`), not
  `it_admin`. IT admin gets the 7 days after 30-11-2026.
- **A2**: the window is decided by the date of **entry**, not the date of the
  event. A 2024 breakdown entered on 30-11-2026 is accepted; on 01-12-2026 it
  is refused for non-admin.

## 9. Docs (at approval)

- `docs/Plan.MD` § 2 (`:65`): "Backfilling history from the plant's notebooks —
  later." → "Backfilling history from the notebooks: by hand on the ticket
  screens until 30-11-2026 (S028); a bulk import later."
- `docs/Plan.MD` § 3 (`:150-166`): one sentence: "`ticket:backdate` (S028): no
  role; admin through the bypass; global."
- `docs/Plan.MD` § 4.2 (`:328`): "Raising may be back-dated up to 7 days." →
  "Entered times may be back-dated up to 7 days; admin (key `ticket:backdate`)
  up to 3 years; everyone up to 3 years until 30-11-2026 for the backlog
  (S028)."
- `docs/Maintenance-Philosophy.md` § 1 (`:25`): "Backfilling from the notebooks
  is deferred (**Decided**)." → "Backfilling from the notebooks is by hand on
  the ticket screens until 30-11-2026 (**Decided** 22-10-2026, S028); a bulk
  import is deferred."

## 10. Amendments

None.

## Review log

| Finding | Severity | Answer |
|---|---|---|
| BR1-01 `admin` fixture is IT admin | major | **Accepted** (option a): new `keycloak_admin` fixture; § 7 rewritten, every admin case on it; the existing test gets `BACKLOG_UNTIL` patched and stands as the IT-admin case; fixture note in § 7; `conftest.py` in § 3 |
| BR1-02 a wrong year is accepted for five weeks | minor | **For the user**: Q1 in § 8, recommended (b) the "That was N days ago" hint |
| BR1-03 a backlog raise sends live alerts | minor | **For the user**: Q2 in § 8, recommended (b) no alert for a raise older than 7 days; removed from § 1.1 |
| BR1-04 docs still say the backlog is deferred | minor | **Accepted** (option a): § 9 lists Plan.MD § 2, § 3, § 4.2 and the philosophy § 1; § 3 *Where* |
| BR1-05 the manual check is a browser check | minor | **Accepted** (option a): an admin e2e test in `tickets-raise.spec.js`, date-independent; no device row |
| BR1-06 standards cited loosely | minor | **Accepted** (option a): § 2 rewritten with ISO 14224 § 9.5/Table 6, § 9.6/Table 8, Annex C, § 7; EN 15341, SMRP; ISO 9001 § 7.5.3 "documented information"; ISO 27001 A.8.2; "to verify" dropped |
| BR1-07…BR1-13 | nit | **Accepted**: `:299` (07); file count (08); `at_unit("maint_technician")` (09); `LONG_BACKDATE_YEARS` feeds both (10); § 6 oldest first and the plan date (11, and § 1.1); § 4.2 says the cache makes it one query (12); `too_old_message` (13) |
| BR2-01 the start-move test's set-up raise is refused | minor | **Accepted**: § 7 raises with `make_ticket(machine, client=keycloak_admin, …)` in both cases |
| BR2-02…BR2-04 | nit | **Accepted**: 8 code and test files (02); `:1017` is a raise (03); § 7 notes the admin e2e user has no display name, no seed change (04) |
