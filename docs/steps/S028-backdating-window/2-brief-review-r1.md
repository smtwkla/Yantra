```
Step: S028 — Back-dating window: admin and backlog entry
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 22-10-2026
```

Reviewed against: d686fcd

# S028 — Brief review, round 1

**Verdict: one `major` finding is open (BR1-01).** The brief's test plan uses
the `admin` fixture as the Keycloak admin, but that fixture is IT admin, who
does not hold `ticket:backdate`. The design (§ 1, § 4) is sound and matches the
code; the user's decisions U1–U4 are not re-asked. Four `minor` findings: two
are consequences of U4 the user may not have seen (a wrong year is no longer
caught; backlog raises send alerts), one is docs the change contradicts, one is
the manual check. Seven nits.

Full track, round 1: every section read; every file:line claim checked against
d686fcd.

## Findings

### BR1-01 — major — The `admin` fixture is IT admin, so the API test plan names the wrong account

**Problem.** § 7 and § 3 build the API tests on the `admin` fixture
(`test_event_time_out_of_the_window_is_400(self, admin, machine)`, "admin,
after the window: raise 30 days back → 201", "admin, +10 min refused and 1096
days back refused"). In `backend/tests/conftest.py:315-317`:

```python
def admin(role_client):
    """IT admin: writes masters and equipment, and sees every unit."""
    return role_client("it_admin")
```

IT admin holds no `ticket:backdate` (§ 5 says so itself). So:

- the brief's reading of the existing test is wrong: "today with admin and 8
  days back, which would now pass" — it passes today only because everyone is
  in the backlog window until 30-11-2026, not because the account is exempt.
  From 01-12-2026 the test passes again unchanged;
- the rewritten test ("admin, 1096 days back refused") would refuse at 8 days,
  not 1096, once the window is over, and the "30 days back → 201" test would
  fail from the first run with `BACKLOG_UNTIL` patched to the past;
- a coder who trusts the brief may "fix" the failures by granting `it_admin`
  the key, which reverses the user's assumption in § 8.

**Why it matters.** The whole admin half of the step would be tested against
the wrong account. The RBAC pattern check (admin bypass, no role holds the key)
would look green while it covers nothing.

**Options.**
- (a) **Recommended.** Add a fixture for the Keycloak admin, named so nobody
  confuses it: `keycloak_admin = role_client("admin")` (`tests/harness.py:24`
  accepts `"admin"` as a token role; `has_perm` then returns on `_is_admin`,
  `auth_utils.py:356`). Rewrite § 7: every "admin" case uses it; keep one
  explicit IT-admin case, "IT admin, after the window, 8 days back → 400",
  since § 5 names IT admin as an edge case. State in § 7 that the `admin`
  fixture is IT admin.
- (b) Rename the existing `admin` fixture to `it_admin` across the suite.
  Correct, but it touches every API test file for no gain in this step.

Also fix the existing-test sentence in § 7: the test needs `BACKLOG_UNTIL`
patched to a past date to keep meaning "8 days back is refused", whatever the
account.

### BR1-02 — minor — Until 30-11-2026 a wrong year or month is accepted for everyone (a consequence of U4)

**Problem.** S017 § 7 decision 9 rejected "no cap" because "typos like a wrong
year go into MTBF". With U4, every user has a 1095-day window for five weeks,
and the screens stay as they are: a `datetime-local` input with no hint of
what was entered (§ 1). A phone picker set to 2025 instead of 2026, or to the
wrong month, is accepted silently and lands in a past month's history. The
brief does not name this trade-off.

**Why it matters.** ISO 14224 § 7 (quality of data) is the reason the cap
existed; the backlog window is the one period where bad dates are most likely,
since users are typing from notebooks. A ticket with a wrong year is hard to
spot later (the list orders by `occurred_at`, `tickets.py:572`).

**Options.** This is the user's call.
- (a) Accept the risk for five weeks; say so in § 4.4 (D-new) and in the
  release note.
- (b) **Recommended.** A one-line hint under *When did it happen?* (and under
  the move time fields) when the entered time is more than 7 days back: "That
  was 412 days ago". Presentational only, computed from the input's value in
  the frontend (CLAUDE-COMMON allows formatting helpers), no API change. It
  turns a silent typo into something the user sees. It makes the step touch the
  three Vue files listed in § 1 and adds one e2e check (the hint shows for a
  date 30 days back, as admin — date-independent).
- (c) A confirm step on save when the time is older than 7 days. More taps on
  every backlog entry; (b) is enough.

### BR1-03 — minor — A backlog raise sends live alerts (a consequence of U1 and U4)

**Problem.** § 1.1 keeps alerts unchanged and relies on a release note telling
users to tick *Already fixed*. A backlog ticket raised **open** (a defect from
the notebook that is still open, or a breakdown where the user forgot the
tick) pushes an alert to every engineer, the unit's supervisor and the manager
and queues an escalation from the moment of entry (`tickets.py:783-788`,
`alerts.enqueue_alert` → `enqueue_escalation`). Thirty notebook entries in an
afternoon are thirty pushes.

**Why it matters.** The alert says "new breakdown" about a failure from
months ago. Engineers learn to ignore pushes during the backlog weeks, which
is the one thing S021 must avoid.

**Options.** The user's call; the brief put alerts out of scope without a
U-decision.
- (a) Accept; keep the release note; ask that the backlog be entered with
  *Already fixed* wherever possible.
- (b) **Recommended.** One rule in the pure core: a raise whose entered time is
  more than `MAX_BACKDATE_DAYS` before `now` is history, not news, so it sends
  no alert and no escalation. `alerts_core.raise_alert` (`alerts_core.py:62`)
  gains the age as an argument, with two unit tests; `raise_ticket` passes
  `now - clean["occurred_at"]`. About ten lines, and it removes the trap. The
  regrade and send-back alerts stay (they are live actions).
- (c) Suppress alerts for every raise during the window. Too broad: a real
  breakdown today must still alert.

### BR1-04 — minor — Three docs still say the backlog is deferred, and § 3 of Plan.MD lists every ticket key

**Problem.** § 9 updates Plan.MD § 4.2 only. These still contradict the step:
- `docs/Plan.MD:65` (§ 2 out of scope): "Backfilling history from the plant's
  notebooks — later.";
- `docs/Maintenance-Philosophy.md:25` (§ 1): "Yantra starts with no history.
  Backfilling from the notebooks is deferred (**Decided**).";
- `docs/Plan.MD:150-166` (§ 3) names every `ticket:*` key with its holders and
  scope; `ticket:backdate` (no role, admin by the bypass, global) belongs in
  that paragraph. The matrix at `:112-117` can stay as it is (a row of blanks
  says nothing) or gain a row with a note.

**Why it matters.** The planner of the later bulk-import step, and the
`/smtw-review` audit, read these lines as decisions.

**Options.**
- (a) **Recommended.** Add the three edits to § 3 *Where* and § 9: Plan.MD § 2
  becomes "Backfilling history from the notebooks: by hand on the ticket
  screens until 30-11-2026 (S028); a bulk import later."; the philosophy line
  the same; § 3 gets one sentence on the key.
- (b) Leave the philosophy doc, update Plan.MD only. The philosophy line is
  marked **Decided**, so it should record the change of decision.

### BR1-05 — minor — The manual check is a browser check, and its place is contradictory

**Problem.** § 7 lists one manual check: "On the dev server, as an operator,
raise a ticket 2 months back: it saves (until 30-11-2026). Either machine."
A browser can do this. The brief's reason for having no e2e test (the cut-off
depends on today's date) holds for the operator case only: an **admin** check
is date-independent, and the e2e harness has the admin role
(`frontend/e2e/support/people.js:8`, `TOKEN_ROLE.admin`). "On the dev server"
and "Either machine" also contradict each other (`device-checks.md` § Where a
row runs).

**Options.**
- (a) **Recommended.** Replace it with an automated check in
  `tickets-raise.spec.js`: as admin, fill *When did it happen?* 30 days back
  (the spec's `istLocal` helper, `:119`), save, the timeline's first line shows
  that time. Keep no device row.
- (b) Keep the operator check as a plain note with a fixed place: "dev server,
  as an operator (any seed operator), on the laptop's network, before
  30-11-2026".

### BR1-06 — minor — § 2 cites the standards loosely; the user is learning them

**Problem.** § 2 leaves the ISO 14224 clause "to verify", and names ISO 9001
§ 7.5.3 "control of records", which is the 2008 edition's term.

**What the standards say** (the planner verifies against the copies held):
- **ISO 14224:2016** collects failure data per failure event, § 9.5 and
  **Table 6** ("Failure date": the date of failure detection), and
  maintenance data per maintenance action, § 9.6 and **Table 8** (date of the
  action, downtime, man-hours). Annex C derives MTBF and MTTR from those dates,
  which is why the real date, not the entry date, must be stored. **§ 7**
  (quality of data) asks for data that is complete, accurate and plausible —
  the reason for S017's cap and for BR1-02.
- **EN 15341:2019** and **SMRP Best Practice metrics** (e.g. 3.5.1 MTBF,
  3.5.2 MTTR) are computed over a reporting period; a late entry moves the
  period's figure. § 2 states this correctly.
- **ISO 9001:2015 § 7.5.3** is "Control of documented information"; records
  are "retained documented information" (§ 7.5.3.2). The traceability point
  (`created_by`, `created_at`) is right.
- **ISO 27001:2022 A.8.2 (privileged access rights)**: the right to write
  history further back than everyone else is a privileged right, held by the
  admin account only and granted by a code change — worth one line, since the
  step introduces an admin-only key, the first in `config_rbac.py`.

**Options.**
- (a) **Recommended.** Replace § 2 with the clauses above, two lines each, and
  drop the "to verify" line from § 8.
- (b) Keep § 2 and move "to verify" to the coder. The coder does not read the
  standards.

## Nits

- **BR1-07** (nit) § 1.1: `REPEAT_WINDOW_DAYS` is at `tickets_core.py:299`,
  not `:824`.
- **BR1-08** (nit) § 3: "7 code and test files" — the table has 6 code and
  test files (plus two docs).
- **BR1-09** (nit) § 7: there is no `technician` fixture; the start move test
  uses `at_unit("maint_technician")` (`conftest.py:534-536`).
- **BR1-10** (nit) § 4.1: "3 years" is written twice, as `3 * 365` and in the
  message text. One `LONG_BACKDATE_YEARS = 3` feeding both keeps them in step.
- **BR1-11** (nit) § 6: add "Enter the backlog oldest first": a repeat needs
  its earlier ticket to exist and to be back in service within 7 days before
  it (`_check_repeat`, `tickets.py:694-708`). And: a backlog deferred ticket
  cannot carry its old planned date — the plan date must be today or later
  (`planned_date_error`, `tickets_core.py:541`); say to enter such tickets as
  raised, or with today's plan date.
- **BR1-12** (nit) § 4.2: `_event_time` computes the limit per entered time,
  so a raise with *Already fixed* calls `has_perm` up to three times; the
  membership cache makes it one query. Say so, or compute once in the route.
- **BR1-13** (nit) § 1, § 4.1 (scope A): "the message is chosen by the limit"
  is clear, but § 4.1's comment says "when `max_back_days ==
  LONG_BACKDATE_DAYS`", a comparison of a number to decide a text. A small
  `too_old_message(max_back_days)` next to the constants reads better.

## Checked and found consistent

- `event_time_error`, `validate_raise`, `validate_event_time` and their
  callers: `tickets_core.py:101`, `:128`, `:168`, `:572`, `:577`;
  `tickets.py:106` (import), `:729`, `:827`; no other caller in `backend/`,
  `frontend/`, `tooling/`. Every move and the raise's *Already fixed* block go
  through `_event_time` (`:881`, `:1004`, `:1043`, `:782`).
- `_now()` at `tickets.py:159`; `FUTURE_SKEW` 5 min and the `<` comparison at
  `tickets_core.py:105-108`; `EVENT_TIME_TOO_OLD` at `:69`.
- `has_perm` (`auth_utils.py:348-358`): admin returns before any read, no
  `g.user` is `False`; `current_memberships` cached in `g` (`:272-289`).
- RBAC: `compute_permissions(["admin"])` returns every key
  (`access_core.py:51-52`); `()` passes `test_permission_values_are_tuples`
  (`:41`), `test_admin_not_in_permission_tuples`, `test_role_matrix` (`:191`);
  no test in `test_rbac.py` requires every key to have a holder; the site-key
  tests (`:96-118`) name their keys explicitly, so a global `ticket:backdate`
  breaks none. `_check_site_args` would assert if the key were ever checked at
  a site without joining `SITE_SCOPED` — D2's note is right.
- The time fields are plain `datetime-local` inputs with no `min` or `max`
  (`RaiseTicketView.vue:453`, `tickets/EventFields.vue:72`,
  `tickets/StartedAtFields.vue`); no frontend or e2e text mentions "7 days".
- `ticket_events.occurred_at`, `created_at`, `created_by`
  (`local_db.py:410-415`); the serial from the month of entry
  (`tickets.py:762`); alerts skipped on *Already fixed* (`:783-788`);
  `validate_labour` measures from the ticket's event date (`:639`, caller
  `:1162-1163`).
- Existing tests named: `test_tickets_core.py:29` (`NOW`), `:100-105`,
  `:159-165`, `:350-351`; `test_tickets_api.py:194-198`. `test_event_time_entered`
  (`:72`, 2 days back) and `test_ticket_work_api.py:1017` (start 2 days back)
  stay inside every window.
- Track: full, correct (an access check and a new permission key).
- D1–D5 follow CLAUDE-COMMON § RBAC and § Pure core: the limit is computed in
  `tickets_core`, the key is read in the route, no role name in route code.
- Writing style (scope A) of the brief: clear; the UI text it specifies (one
  new message) follows the existing message's form.
