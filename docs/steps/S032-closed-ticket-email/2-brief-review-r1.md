```
Step: S032 — Email to managers when a ticket is closed
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 23-10-2026
```

Reviewed against: aad833a + uncommitted S031

# S032 — Brief review, round 1

**Verdict: one `major` finding is open (BR1-01, the SMTP failure table cannot be
coded as written). No blocker.** Five `minor` findings and ten nits. The
design (email as a second channel in the existing alert path, addresses from
the token at login, one email per manager per close) holds against the code;
U1 and U2 are not reopened. Facts file `scratch/brief-facts-S032.md` was given
and used.

What I read: the brief; Plan.MD § 4.7; Maintenance-Philosophy (roles, the
ticket chain); Plant-Facts; CLAUDE-COMMON and CLAUDE.md; `alerts_core.py`,
`alerts.py`, `task_handlers.py`, `push.py`, `push_sender.py`, `config.py`,
`example_secrets_app.py`, `app.py` (`auth_me`), `auth_utils.py` (`make_user`,
`validate_keycloak_token`, the dev stub, `current_person_id`), `tickets.py`
(`raise_ticket`, `make_move`, `_apply_move`, `_close`, `_not_a_fault`),
`tickets_core.py` (`MOVES`, `ticket_times`, `WAITING_REASONS`), `settings.py`
(`_notifications_body`), `masters.py` (`_people_out`, `_SiteViewer`),
`local_db.py` (people, ticket_labour, ticket_parts, v26), `task_queue.py`,
`worker.py`, `company_settings.py`, `tests/conftest.py`, `tests/harness.py`,
`test_alerts.py`, `test_alerts_core.py`, `test_push_api.py`,
`test_settings_api.py`, `test_migration_v26.py`, `tooling/e2e/e2e_backend.py`,
`seed_e2e.py`, `frontend/e2e/support/people.js`, `NotificationsView.vue`,
`stores/notifications.js`, `NotificationsSettings.vue`, `PeoplePanel.vue`,
`TicketDetailView.vue` (the times card), and in the sibling repo
`secrets_app.py.j2` and `vars/example_settings_vel_yantra_master.yaml`.

## Major

### BR1-01 — major — § 5.5: the `smtp_outcome` table contradicts itself and names an attribute that does not exist

**Problem.** The table puts `SMTPConnectError` in the retry row and "other
`SMTPResponseException` with a 5xx code" in the NoRetry row. `SMTPConnectError`
is a subclass of `SMTPResponseException`, so a 5xx greeting matches both rows.
The table also decides `SMTPRecipientsRefused` as NoRetry outright, but that
exception has no `smtp_code`: it carries `recipients`, a dict
`address -> (code, message)`. A 4xx recipient refusal (450 or 451, greylisting,
"mailbox busy") is temporary, and the table fails it for good. Likewise
`SMTPSenderRefused` can carry a 4xx (452). The coder cannot implement the table
as given and would have to decide the rule alone.

**Why it matters.** A greylisted manager never gets the email: the first
attempt fails with NoRetry. The whole point of the retry rule is this case.

**Options.**
- (a) **Recommended.** Decide by the code wherever there is one, subclasses
  first. Replace the table with:

  | Exception | Outcome |
  |---|---|
  | `SMTPConnectError`, `SMTPServerDisconnected`, `OSError` (timeout, refused connection, DNS, TLS: `ssl.SSLError` is an `OSError`) | retry (back-off) |
  | `SMTPRecipientsRefused`: the code of the one recipient, `exc.recipients[address][0]` | 4xx retry; else NoRetry |
  | `SMTPSenderRefused`, `SMTPAuthenticationError`, `SMTPDataError`, `SMTPHeloError`, any other `SMTPResponseException`: `exc.smtp_code` | 4xx retry; else NoRetry |
  | any other `SMTPException` (for example `SMTPNotSupportedError`: no STARTTLS) and anything else | NoRetry, logged with its type |

  State the check order: `SMTPConnectError` before the generic
  `SMTPResponseException` row. State that the text raised (`NoRetry(...)`,
  `RuntimeError(...)`) is `smtp_outcome`'s own, "outcome + code", raised
  `from None`, as `push_send` does: `str(SMTPRecipientsRefused)` carries the
  address, and `mark_failed` writes `str(exc)` into `task_queue.last_error`.
  Update the `test_email_core.py` rows in § 8 to one per table row, with a 4xx
  and a 5xx recipient refusal.
- (b) Keep one rule: every `SMTPException` retries up to the 3 attempts.
  Simpler, but a wrong password or a refused sender then retries three times
  for every manager of every close.

## Minor

### BR1-02 — minor — § 8 Acceptance: placeholder SMTP values in production turn email "on" with a dead host

**Problem.** The Ansible template renders the five `smtp_*` vars without a
default, so the real `settings_vel_yantra_master.yaml` already defines them
(an earlier deploy would otherwise have failed). The example file holds
`smtp_host: xxx`. If the real file holds placeholders too, the release ships
`SMTP_HOST = "xxx"`, `enabled()` is true, and every close queues one
`email_send` per manager that fails three times on DNS. The brief's
"Without them the release runs with email off" holds only when `smtp_host` is
empty.

**Why it matters.** Failed tasks for every close from the first day, and a
manager who reads "Email goes to …, from your login" on My notifications gets
nothing.

**Options.**
- (a) **Recommended.** In Acceptance: before the release the user reads the
  real vars and sets either the Mailgun values or `smtp_host: ""`. Also make
  `mail_sender.enabled()` need both `SMTP_HOST` and `SMTP_FROM` (push needs
  all three VAPID values); a From that is empty fails every send anyway.
- (b) Code only: `enabled()` as in (a), and the user checks nothing. A
  placeholder host still passes.

### BR1-03 — minor — § 1.5: where the email lines and the test button sit on My notifications is not decided

**Problem.** The page today is built around push: the *This device* card
shows "Notifications are not set up on this server yet" whenever
`pushConfig.enabled` is false (`deviceState` = `not_set_up`), and *Send a
test* sits in the *My devices* card header. The brief puts the address line
"under" *What you will get* and does not say where *Send test email* goes, or
what a manager sees when push is off and email is on (the page would say
"not set up" at the top and "Email goes to …" lower down).

**Why it matters.** The coder places a button and a message without a rule,
and the two channels' states can read as a contradiction on one screen. One
main job per card.

**Options.**
- (a) **Recommended.** A third card **Email**, shown when `inTeam`: one line
  (the address, or "Your login has no email address …", or "Email is not set
  up on this server yet …") and, in its header, **Send test email** when email
  is set up and the user has an address; its success message in the card, as
  `testSent` is for push. *What you will get* keeps only the audience line
  "Closed tickets at SMTW, by email". The push cards are untouched.
- (b) Put the address line and the button inside *What you will get*. Fewer
  cards, but that card then mixes a statement of policy with an action.

### BR1-04 — minor — § 3, § 5.4, § 8: how the tests give the user an email is not specified

**Problem.** The brief says the e2e `_user_factory` reads an optional
`X-Test-Email` header, and lists pytest tests for `auth_me` ("a token email is
stored lower-cased"). It does not say how a pytest request carries an email:
`auth_utils.require_auth` calls `factory(test_role, X-Test-User)` with two
arguments, `conftest._test_user_factory` and `harness_user` have no email, and
`frontend/e2e/support/people.js` `headersFor` sends only `X-Test-Role` and
`X-Test-User`. The `masters.spec.js` check "after the manager's page load"
also depends on another test having run first; lanes and workers do not
promise that order.

**Why it matters.** Two harnesses with two ways to set the same claim, or a
test that reads `g` by hand: the coder decides alone, and the e2e check can
be flaky.

**Options.**
- (a) **Recommended.** `require_auth` passes a third argument,
  `request.headers.get("X-Test-Email")`, to the factory; `harness_user` gains
  `email=""` and both factories (`conftest`, `e2e_backend`) pass it through.
  `people.js` `headersFor(key)` adds `X-Test-Email` for the seed people that
  have one (the manager). The `masters.spec.js` test loads a page as the
  manager itself before IT admin opens the dialog. Add `conftest.py`,
  `harness.py`, `auth_utils.require_auth` and `people.js` to § 3.
- (b) Each harness reads `flask.request` itself. Works, but two copies of one
  rule.

### BR1-05 — minor — § 8 On a real device: two checks lack account or network

**Problem.** README § Manual checks asks for account, network and where on
every device check. The second check names "an engineer" with no login and no
network; the third names IT Admin with no network. The first is complete.

**Why it matters.** IT Admin gets the rows from `device-checks.md` and should
not have to ask.

**Options.**
- (a) **Recommended.** Second check: "production, TEST machine ticket closed
  by `<engineer login>` on the office network; KLA's Outlook and each
  manager's". Third: "production, IT Admin's login, office network, Masters ›
  Team".
- (b) Drop the third check: the `masters.spec.js` test already shows the line
  in a browser; only "the address in production is the AD one" needs a person.

### BR1-06 — minor — § 5.4: on the dev server nobody can ever have an address, so the channel cannot be tried before release

**Problem.** The dev stub (`_get_dev_stub_user`) has no email, and the brief
has it pass an empty one. `auth_me` then clears the dev person's address on
every load. In dev the page always says "Your login has no email address", the
test button never shows, and the first time anyone sees a real email is in
production (the device check). A judgement call for the user, not a nit.

**Options.**
- (a) **Recommended.** `DEV_STUB_EMAIL` beside `DEV_STUB_ROLE` in
  `example_secrets_app.py` (empty by default, one `getattr` in `config.py`),
  carried into the stub's `g.user`. With the local `SMTP_*` filled, the user
  can send a test email and a closed-ticket email from the laptop and read the
  text before approving the release. Mirrors `DEV_STUB_ROLE`; dev only.
- (b) Accept: the text is checked by `test_email_core.py`, the delivery in
  production. State it under § 9.

## Nits

- **BR1-07** (nit) § 7 decision 9 and § 5.5: done task rows are kept 90 days
  (`company_settings.DONE_TASK_RETENTION_DAYS`), not 30.
- **BR1-08** (nit) § 5.8: `push._own_person` raises `NOT_IN_TEAM` as **409**,
  not 403; say 409 "as `send_test`".
- **BR1-09** (nit) § 1.5 UI text (scope B): "Ask IT admin to add one in
  Keycloak." names a system the user never sees. Use "Ask IT admin to add an
  email address to your login." The Team dialog's "Email (from Keycloak)" is
  IT admin's screen and can stay.
- **BR1-10** (nit) § 1.5 toast (scope B): "Test email queued for …" says what
  the system does. Use "A test email is on its way to `<address>`. Check your
  inbox in a few minutes."
- **BR1-11** (nit) § 1.4 and § 8: `ticket_times` gives `downtime_minutes` = 0
  on a defect, never None (only a not-a-fault gives None), and the ticket page
  shows "Downtime 0 h 00 min" too. Say the email's line reads `Downtime: 0 h
  00 min` on a defect and name the test that way, not "a defect with no
  downtime".
- **BR1-12** (nit) § 5.3: the waiting-reason words ("parts") come from
  `tickets_core.WAITING_REASONS` (`code -> (label, kind)`); name it, so the
  coder does not add a second table.
- **BR1-13** (nit) § 3 and § 6: say that `POST`/`PUT /api/masters/people`
  never accept `email` (the validation spec drops unknown keys) and add the
  one test; the column is written by `auth_me` only.
- **BR1-14** (nit) § 5.5: the `email_send` payload holds the body for the
  retention period, with first names and the close remark, as the `push_send`
  payload does today. Say so beside the A.5.34 line, so the claim "the address
  is not stored" is not read as "nothing personal is stored".
- **BR1-15** (nit) § 5.1: in `ticket_alert` for `CLOSED`, find the recipients
  with an address first and read the extra facts (`read_closed_facts`) only
  when there is at least one; a site with no manager on email reads nothing.
- **BR1-16** (nit) § 2: ISO/IEC 27001 **A.5.16 (identity management)** backs
  decision 3: one identity source for a person's attributes, no second copy to
  keep right. One line, beside A.5.34.

## Checked and found consistent

- **Every close goes through `_apply_move`.** `tickets.state` is written in
  one place, `update_row(... {"state": spec.to_state, ...})` in `_apply_move`;
  `make_move` is the only caller for `close` and `not-a-fault`. The raise's
  *Already fixed* path calls `_apply_move` with `restore`, never a close, so
  it enqueues nothing new. The hook after the event, as the send-back hook
  sits, is right; `occurred_at` there is the close event's time, so
  `close_alert(now - occurred_at)` applies the 7-day rule to the typed close
  time, as `raise_alert` does for the raise.
- **The alert path.** `ticket_alert` checks `kind in KINDS` (so `CLOSED` must
  join `KINDS`), `should_send` through `_SEND_STATES`, then `push_sender.enabled()`
  before the recipients: the channel split replaces that one check, and
  `test_push_off_finds_no_channel` still holds for push kinds. `enqueue_alert`
  with `reported_by_id=None` and `excluded_people(CLOSED, actor, None)` gives
  `[actor]` with no code change beyond the docstring. `recipients` with
  `AUDIENCE[CLOSED] = (MANAGER,)` matches the role exactly, as S021 does.
- **S021 § 7 decision 10** ("Always enqueue the alerts", BR1-08) is cited
  correctly.
- **`auth_me`.** The write fits inside the existing `try … except
  DBUnavailable`; `current_person_id` is already read there; `test_auth.py`
  has a `db_down` fixture for the "answer as today" case. `make_user` gains a
  keyword with a default, so `harness.py` and `test_rbac.py` keep working.
- **Personal data.** `email` reaches clients through `SELECT * FROM people`
  in `masters.py` only (two places, both through `_people_out`), where
  `viewer.senior` (`masters:read_senior`) already gates `username`; the same
  gate for `email` is right. `GET /api/push/config` returns the caller's own
  address only; the test email goes to the caller's own person only.
- **Migration v27.** A NULLable column with `IF NOT EXISTS`, no
  `_PRECONDITIONS` entry, on the v21/v23 precedent; the previous release
  ignores the column, so a rollback needs no restore. `test_migration_v26.py`
  is a fit pattern (fresh, from v26 with rows, re-run no-op).
- **Tests the change breaks are listed.** `test_alerts_core.py` line 188 (the
  manager's `you_get` list) and the exact-body asserts in `test_push_api.py`
  are in § 3; `test_settings_api.py` asserts keys only, so it needs no change.
- **Facts for the text exist.** `ticket_labour.minutes` and `person_id`
  (distinct count), `ticket_parts.description`, `quantity`, `qty_unit`,
  `failure_causes.label`, `maintenance_actions.label`, `latest_restoration`,
  `ticket_times(events, now)` as the page uses it; the closing event is the
  `event_id` passed, so `facts["actor_name"]` is already the closer's first
  name.
- **Header injection.** `email.message.EmailMessage` refuses a header with a
  line break; `one_line` on the subject's parts is the right guard.
- **Mailgun over SMTP** accepts login on 587 with STARTTLS; `smtplib` is in
  the standard library; no dependency change, so `sbom/` is untouched.
- **Standards.** ISO 9001 § 7.4 and ISO 55001 § 7.4 are both *Communication*
  (what, when, to whom, how); the audience table as the written decision is a
  fair reading. ISO/IEC 27001:2022 A.5.34 (privacy and PII) and A.5.14
  (information transfer) are the right controls, and the brief explains each.
  EN 13306 terms (time to restoration, active corrective maintenance time,
  logistic and administrative delay) are used as `ticket_times` defines them.
  ISO 14224 asks for the failure cause and maintenance action per corrective
  job; showing them to the manager is in its spirit. "Close-out review" is
  stated as plain practice, correctly without a clause.
- **Track full** is right: a migration, a secret, a write on a GET, a new
  endpoint.
- **Right-sized.** `CHANNELS` is one small table beside `AUDIENCE`, a pure
  `email_core`, one sender module, no new abstraction; the test button reuses
  the queue. Nothing over-engineered.
- **Light wording.** The brief reads in scope A; the UI texts are in scope B
  apart from BR1-09 and BR1-10.
