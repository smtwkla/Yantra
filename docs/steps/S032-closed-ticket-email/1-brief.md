```
Step: S032 — Email to managers when a ticket is closed
Doc: brief
Author: Planner (Opus)
Date: 23-10-2026
Track: full
Status: Committed; device checks pending (rows 27-30 of device-checks.md)
Baseline: 33c3a4b
```

# S032 — Email to managers when a ticket is closed

**The need (KLA, 23-10-2026).** "I would like to receive email when a ticket
is closed. With relevant info. May be email should go to managers." Today a
close sends nothing (S021 alerts cover a new breakdown, a new defect, *down
again*, an escalation and *assigned to you*). The managers learn of a
finished job only by opening Yantra.

This step adds **email** as Yantra's second alert channel, beside web push,
and one alert on it: **Ticket closed**, to the maintenance managers of the
ticket's site. The email carries what a manager needs to judge the job:
machine, problem, downtime, cause, action, labour, parts, who closed it.

User answers before drafting (U1, U2, below): the site's managers; every
close, *not a fault* included; one email per close, not a digest; addresses
from Keycloak, kept on login; sent through Mailgun (the plant also has
Office 365).

Planned on top of S031 (uncommitted, in code review), which takes migration
v26. This step's migration is **v27**.

## 1. What will be built

1. **The email channel.** One module sends mail over SMTP with Python's
   standard `smtplib` (STARTTLS), through **Mailgun** (U2). The
   settings are the five values the production template already renders:
   `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`
   (sibling repo `smtw_erp_devops`, `erp_server/yantra/secrets_app.py.j2`
   lines 32–37,
   commented "daily summary"). Email is on only when `SMTP_HOST`,
   `SMTP_PORT` and `SMTP_FROM` are all set (BR1-02, U5), as push needs all three VAPID values
   (`push_sender.enabled`); otherwise it is off. Every send runs
   in the worker from the job queue, never in a request (Plan.MD § 4.7: "All
   sends go through the DB-backed job queue").
2. **Addresses from Keycloak (U2).** Each person's email comes from the
   `email` claim of their login token. At every `/api/auth/me` call (the
   de-facto login, once per page load, `app.py` `auth_me`), Yantra copies
   the token's email onto the person's Team record when it differs. A token
   with no email, or one that fails the address check (§ 5.4), clears it.
   Nobody types an address in Yantra.
3. **The alert *Ticket closed*.** When a ticket is closed (*Close* or *Not a
   fault*, `tickets_core.MOVES`), one alert task is queued in the close's own
   transaction. The worker sends one email to each recipient:
   - **recipients:** the active people with a **Manager** membership
     (`maint_manager`) at the ticket's site that covers the ticket's unit
     (all units, or that unit), with an email address — the same rule as
     S021's audiences (`alerts.recipients`). A manager who closed the ticket
     is left out (§ 5.2);
   - **not sent** for a close dated more than `MAX_BACKDATE_DAYS` (7) back:
     back-entered history (S028), as a back-dated raise sends nothing
     (`alerts_core.raise_alert`).
4. **The email's text** (Scope B; one pure function, § 5.3). Subject:
   - `Closed · SMTW.MCC2 · VBM001 · TK-2026-10-012`
   - `Closed as not a fault · SMTW.MCC2 · VBM001 · TK-2026-10-012`

   Body, plain text, one fact per line, a line left out when it has no value:
   ```
   TK-2026-10-012 — Breakdown, closed
   Machine:          VBM001 — Vertical ball mill
   Component:        GBX01 — Gearbox
   Unit:             SMTW.MCC2
   Problem:          Not building pressure — oil leak at the gearbox seal
   Raised:           20-10-2026 09:12 by Ravi
   Back in service:  20-10-2026 11:40
   Downtime:         2 h 28 min
   Repair time:      1 h 50 min
   Waiting:          0 h 20 min (parts 0 h 20 min)
   Cause:            Wear
   Action:           Replace
   Labour:           3 h 15 min, 2 people
   Parts:            Oil seal 45x62x8 — 1 nos
                     Gear oil EP 220 — 2 l
   Closed:           20-10-2026 14:05 by Priya
   Remark:           Seal changed, watch for 2 days

   Open the ticket: https://vel-yantra.mspv.app/tickets/123
   ```
   For *not a fault* the first line reads `TK-… — Defect, closed as not a
   fault`; the time, cause-of-close and remark lines stay; downtime, repair,
   waiting, action, labour and parts lines are left out (`ticket_times` gives
   None for all times of a not-a-fault ticket, and a not-a-fault close
   refuses parts, `_not_a_fault`). Words: *Breakdown* for `critical`,
   *Defect* for `degraded` and `initial`, as the alerts say.
5. **My notifications** (`NotificationsView.vue`, every user, `push:subscribe`
   `("*",)`):
   - *What you will get* gains the line "Closed tickets at SMTW, by email"
     for a Manager membership (built from the audience table by
     `alerts_core.you_get`, so the page and the sending cannot disagree).
     It holds only that audience line;
   - a third card, **Email** (BR1-03), after the push cards, shown when the
     user is in Team (`inTeam`, as the other cards). The push cards do not
     change. The card holds one line, the first that applies:
     - email off on this server: "Email is not set up on this server yet.
       Ask IT admin."
     - no address: "Your login has no email address, so you get no email.
       Ask IT admin to add an email address to your login."
     - with an address: "Email goes to `<address>`, from your login."
   - in the card's header, the button **Send test email**, shown when email
     is set up and the user has an address. It sends one test email to the
     user's own address through the queue. On success the card shows, as
     `testSent` does for push: "A test email is on its way to `<address>`.
     Check your inbox in a few minutes."

   The card shows to every user in Team, not only to managers, because the
   test button lets IT admin (with a Team record) check the channel with
   their own login.
6. **Masters › Team** (`PeoplePanel.vue`), IT admin only (the same rule as
   the login, `_people_out`): the person dialog shows a read-only line under
   *Login*: "Email (from Keycloak): `<address>`", or "Email (from Keycloak):
   none yet. Filled at the person's next login." So IT admin sees which
   manager would get no email.
7. **Settings › Notifications** (`NotificationsSettings.vue`, IT admin):
   one status line, "Email: set up, sent from `<SMTP_FROM>`." or "Email: not
   set up. Fill the SMTP values in the server's secrets."
8. **Failures** are kept on the task row and in the log, as for push
   (`task_handlers` docstring). A refused address or login fails at once; a
   network fault or a temporary refusal (4xx) retries with the back-off, 3
   attempts (§ 5.5). Nothing is shown to the recipient; IT admin sees failed
   tasks where the job queue shows them today.

### Out of scope

- Email for the other alerts (breakdown, defect, escalation, assigned): they
  stay push only. The channel table (§ 5.1) makes adding one a one-line
  change in a later step.
- The **daily summary** email (Plan.MD § 4.7, engineers and manager). It
  will use this channel; it is its own step.
- Push for *Ticket closed*: email only, as asked.
- A per-person setting to turn the email off. A manager who does not want it
  asks IT admin to remove the email in Keycloak. Later, if asked.
- HTML email, attachments, photos.
- Office 365 / Microsoft Graph sending (§ 7.2).
- Typing an address in Yantra (U2).

## 2. Standards and practice

- **ISO 9001 § 7.4 and ISO 55001 § 7.4 (communication).** The organization
  decides what it communicates, when, to whom and how. The audience table
  (`alerts_core.AUDIENCE`, now with a channel per alert) is that decision,
  written once; *What you will get* shows each person their part of it. This
  step adds one row: *ticket closed → site managers, by email*.
- **Close-out review of work orders (maintenance management practice).** In
  good practice a supervisor or manager reviews finished work orders: was
  the cause found, was the right action taken, how long was the machine
  down, what was used. Reviewing them closes the loop for planning and for
  repeat failures. The email puts that review in the manager's inbox. Plain
  practice; no clause number.
- **EN 13306 (maintenance terminology).** The email uses the times Yantra
  already computes under their EN 13306 meaning (`tickets_core.ticket_times`):
  *downtime* = time to restoration, *repair time* = active corrective
  maintenance time, *waiting* = logistic and administrative delay. No new
  term.
- **ISO 14224 (failure and maintenance data).** The email shows the coded
  failure cause and maintenance action that ISO 14224 asks to record for
  every corrective job, so a manager sees at a glance a close with a weak
  code.
- **ISO/IEC 27001 A.5.34 (privacy and protection of personal data).** An
  email address is personal data. It is shown only to its owner and to IT
  admin, who maintains logins; queue rows carry the person's id, not the
  address (§ 5.5). **A.5.16 (identity management):** a person's identity
  attributes come from one source, Keycloak, with no second copy to keep
  right (decision 3, BR1-16). **A.5.14 (information transfer):** the email leaves the
  plant through Mailgun, a third party. It carries ticket facts and first
  names, nothing else (no photos, no files, no phone numbers). The user
  accepts this transfer at gate A (open question 1).

## 3. Where

### Backend

- `backend/email_core.py` (new, pure): `closed_email(facts)` → `(subject,
  body)`; `duration_text(minutes)` (`2 h 28 min`); `valid_address(text)`;
  `one_line(text)` (removes CR and LF from header text); `smtp_outcome(exc)`
  (§ 5.5); the test email's text.
- `backend/mail_sender.py` (new, the only module that calls `smtplib`, as
  `push_sender.py` is for `pywebpush`): `enabled()`, `send(to, subject,
  body)`.
- `backend/config.py`: `SMTP_HOST`, `SMTP_PORT` (no default: 0 = not set, U5), `SMTP_USER`,
  `SMTP_PASSWORD`, `SMTP_FROM` by `getattr(secrets_app, …, "")`, read at call
  time like `VAPID_*`; `DEV_STUB_EMAIL` (default "") beside `DEV_STUB_ROLE`
  (BR1-06, dev only).
- `backend/example_secrets_app.py`: the five SMTP names, empty, with a
  comment (CLAUDE.md: keep its field names in step with the Ansible
  template, which has them already); `DEV_STUB_EMAIL`, commented out like
  `DEV_STUB_ROLE`. `DEV_STUB_EMAIL` is not added to the Ansible template:
  production never uses the stub.
- `backend/alerts_core.py`: kind `CLOSED`; `AUDIENCE[CLOSED] = (MANAGER,)`;
  a channel table `CHANNELS` (§ 5.1); `close_alert(age)`; `excluded_people`
  for `CLOSED`; `_SEND_STATES[CLOSED] = (CLOSED,)`; `you_get` adds the email
  line.
- `backend/alerts.py`: `EMAIL_SEND` task name and attempts;
  `read_closed_facts(cur, ticket_id, event_id)` (the extra facts of § 5.3:
  times, cause, action, labour, parts, closer); `recipients_with_email`.
- `backend/tickets.py`: in `_apply_move`, after the event, for the moves
  `close` and `not-a-fault`: `alerts.enqueue_alert(cur, ticket_id,
  close_alert(now - occurred_at), event_id, current_person_id(cur), None,
  now)`.
- `backend/task_handlers.py`: `ticket_alert` sends by the kind's channels;
  new handler `email_send`; `HANDLERS` gains it.
- `backend/app.py`: `auth_me` stores the token's email (§ 5.4).
- `backend/auth_utils.py`: `store_login_email(cur, person_id, email)`
  beside `current_person_id` (§ 5.4, BR3-01); `make_user` gains `email=""`;
  `validate_keycloak_token` passes `payload.get("email", "")`; the dev stub
  passes `config.DEV_STUB_EMAIL`; `require_auth` passes a third argument,
  `request.headers.get("X-Test-Email", "")`, to the test user factory
  (BR1-04).
- `backend/tests/harness.py`: `harness_user` gains `email=""`;
  `backend/tests/conftest.py`: `_test_user_factory` passes it through.
- `backend/push.py`: `GET /api/push/config` adds `email` (§ 6);
  `POST /api/push/test-email` (new).
- `backend/settings.py`: `_notifications_body` adds `email_enabled` and
  `email_from` (§ 6).
- `backend/masters.py`: `_people_out` removes `email` for anyone but IT
  admin, as it removes `username` (`viewer.senior`). `POST` and
  `PUT /api/masters/people` never accept `email` (BR1-13): `validate_person`
  drops unknown keys, so `auth_me` is the only writer; one test proves it.
- `backend/local_db.py`: migration v27 (§ 4).

### Frontend

- `frontend/src/views/NotificationsView.vue`: the address line and *Send test
  email* (§ 1.5).
- `frontend/src/views/masters/PeoplePanel.vue`: the read-only email line
  (§ 1.6).
- `frontend/src/views/settings/NotificationsSettings.vue`: the status line
  (§ 1.7).

### Tests and tooling

- `backend/tests/test_email_core.py` (new), `backend/tests/test_closed_email.py`
  (new, API to queue to send with a fake sender), `backend/tests/test_migration_v27.py`
  (new).
- `backend/tests/test_alerts_core.py`: `CLOSED`, `close_alert`, `you_get`.
- `backend/tests/test_alerts.py` (holds the `ticket_alert` tests today):
  the channel split; push kinds unchanged.
- `backend/tests/test_auth.py`: the email claim into `g.user`.
- `backend/tests/test_push_api.py`: the config's `email` block and
  `POST /api/push/test-email`, including a user with no Team record.
  (Yantra has no per-route permission matrix test; `test_rbac.py` checks
  `config_rbac` only, and no key changes.)
- `tooling/e2e/e2e_backend.py`: `SMTP_HOST` set to a dummy value, as it
  sets the VAPID values (lines 97–101); the user factory
  (`_user_factory`) reads an optional `X-Test-Email` header into the
  user's email. The e2e stack runs no worker, so nothing is ever sent.
- `frontend/e2e/support/people.js`: `headersFor(key)` adds `X-Test-Email`
  for the seed people that have one (the manager, BR1-04).
  This is e2e support code → full e2e run.
- `frontend/e2e/notifications.spec.js`, `frontend/e2e/masters.spec.js`:
  § 8.

### Docs (at approval, by the planner)

- `docs/Plan.MD` § 4.7: the table gains *Ticket closed → site managers, by
  email (S032)*; the *Email* bullet names Mailgun over SMTP and Keycloak as
  the source of addresses.
- `docs/Keycloak.md` "What the token must carry": the `email` claim (client
  scope `email`) for anyone who should get email.
- `.claude/CLAUDE.md` Notifications paragraph: email channel, `smtplib` only
  in `mail_sender.py`, `SMTP_*` secrets, empty host = off.

## 4. Data model (migration v27)

```sql
ALTER TABLE people ADD COLUMN IF NOT EXISTS email VARCHAR(254) NULL;
```

- 254 characters: the longest address SMTP carries (RFC 5321 path limit).
- NULL = no address. No index: it is read by person id.
- No `_PRECONDITIONS` entry: a NULLable new column needs no value from any
  existing row. `IF NOT EXISTS`, so a half-applied v27 re-runs, as v21–v26.
- No `updated_at` / `updated_by` change on the copy at login (§ 5.4): it is
  a cached value from Keycloak, not an edit of the Team record.
- `conftest.py` `_TABLES` needs no change (no new table) — to verify by the
  facts run.

## 5. Rules

### 5.1 Channels per alert

`alerts_core.CHANNELS`, beside `AUDIENCE`:

| Kind | Channels |
|---|---|
| breakdown, defect, escalation, assigned | push |
| closed | email |

`ticket_alert` (`task_handlers.py`) reads the kind's channels. For push it
does what it does today. For email it first finds the recipients with an
address; only when there is at least one does it read the extra facts
(`read_closed_facts`) and enqueue one `email_send` per recipient (BR1-15). A channel that is not set up is skipped with a
log line, as push is today (§ 7 decision 10 of S021: the alert task is
queued always; the task finds the channels).

### 5.2 Who gets *Ticket closed*

- People: active, with a `maint_manager` membership at the ticket's site,
  covering the ticket's unit (`alerts.recipients` with `AUDIENCE[CLOSED]`),
  with `people.email` not NULL.
- Roles are matched exactly, as S021 does: an engineer does not get it
  through `ROLE_INCLUDES`.
- Left out: the person who closed it (`excluded_people`: the actor, for
  every kind but escalation). The reported-by person is **not** left out
  (they are rarely a manager; the rule for breakdown and defect does not
  apply).
- IT admin and admin (token roles, no membership) get nothing, as in S021.
- A manager with no address gets nothing; My notifications tells them why
  (§ 1.5).

### 5.3 The email's facts

`read_closed_facts` reads, plain, in the worker:
- the ticket's facts (`read_alert_ticket`: serial, site, unit, machine,
  component, intensity, state, symptom, description, raiser);
- the machine's and component's names (the push text has codes only);
- the full description, cut to `EMAIL_DESCRIPTION_CUT` = 500 characters
  with "…" (the push cut of 80 is for a phone banner);
- the events, for `ticket_times(events, now)` — the same function the ticket
  page uses, so the figures match the page — and the latest back-in-service
  time (`latest_restoration`); the waiting-reason words come from
  `tickets_core.WAITING_REASONS` (`code -> (label, kind)`), no second table
  (BR1-12);
- cause and action labels (`failure_causes.label`, `maintenance_actions.label`);
- labour: the sum of `ticket_labour.minutes` and the count of distinct
  people;
- parts: up to `EMAIL_PARTS_MAX` = 10 lines `<description> — <quantity>
  <qty_unit>`, then "and `<n>` more" when there are more;
- the closing event: its time, its remark (cut to 500), and the closer's
  first name (as the push texts name people, `first_name`).

`closed_email(facts)` builds the text of § 1.4. Times as `DD-MM-YYYY HH:MM`
(IST, as stored). `duration_text`: `0 h 05 min`, `2 h 28 min`, `26 h 00
min` (hours do not roll into days: a manager compares downtimes by hours).
A time that is None leaves its line out. `one_line` removes CR and LF from
every text that goes into the subject (checked: `EmailMessage` raises
`ValueError` on a header with a line break, run 23-10-2026).

`should_send(CLOSED, state)`: only while the ticket is still closed. (A
closed ticket stays closed today; this guards a future reopen.)

### 5.4 The address from the token

- `validate_keycloak_token` puts `payload.get("email", "")` into `g.user`
  (`make_user(..., email=...)`). The dev stub passes `DEV_STUB_EMAIL`
  (empty by default); the pytest and e2e harnesses pass the `X-Test-Email`
  header, empty when absent (§ 3).
- In `auth_me`, inside the existing `try` and `with get_db().cursor()`
  block (the database may be down), after `current_person_id`: when there
  is a person, call `store_login_email(cur, person_id, g.user["email"])`,
  then commit. `store_login_email` (`auth_utils.py`, BR3-01) takes the raw
  token email, strips and lower-cases it, keeps it when `valid_address`
  accepts it (else NULL), runs `UPDATE people SET email = %s WHERE id = %s
  AND NOT (email <=> %s)` and returns `cur.rowcount`.
- `valid_address(text)`: 3–254 characters, exactly one `@`, no space, comma,
  semicolon, angle bracket, CR or LF, a dot in the part after `@`. It is a
  guard against a broken claim, not full RFC 5322 (`email.utils.parseaddr`
  is too lenient: it accepts `bad` and splits `a@b, c@d`, checked
  23-10-2026).
- No person (`current_person_id` None), or the database down: nothing is
  written; `auth_me` answers as today.
- A GET that writes: deliberate, `auth_me` is already the login moment
  (S011 § 5.1 logs stale roles there). The `<=>` condition makes it a no-op
  write on every load after the first. No lock beyond the one row's.
- `email_verified` is not checked: AD-federated addresses come from AD
  (`mail`), which IT controls — to verify on the realm (open question 3).

### 5.5 Sending and failures

- `email_send` payload: `{"person_id", "subject", "body"}`. The address is
  read at send time from `people.email`, so it is not stored in
  `task_queue` (A.5.34) and a changed address is used. No address now, or
  the person inactive → done, with a log line.
- Attempts: `EMAIL_SEND_ATTEMPTS` = 3, the same as push.
- `mail_sender.send`: `smtplib.SMTP(host, port, timeout=SMTP_TIMEOUT_SECONDS)`
  (30), `starttls()` with the default SSL context (certificate checked),
  `login(user, password)`, `send_message(EmailMessage)`. From: `SMTP_FROM`.
  To: the one recipient (one email per person, so no address sees another).
- `smtp_outcome(exc)` (pure) decides by the SMTP code wherever there is
  one (BR1-01). The rows are checked **in this order**, so a subclass meets
  its own row first: `SMTPConnectError` is an `SMTPResponseException`, and
  every `SMTPException` is an `OSError` (BR2-01; checked on Python 3.12.2,
  23-10-2026):

  | # | Exception | Outcome |
  |---|---|---|
  | 1 | `SMTPConnectError`, `SMTPServerDisconnected` | retry (back-off) |
  | 2 | `SMTPRecipientsRefused`: the code of its one recipient, the dict's only value (`next(iter(exc.recipients.values()))[0]`; not looked up by address, whose case the server may change, BR2-06). An empty dict: NoRetry, logged with the type (BR3-02) | 4xx → retry; else NoRetry |
  | 3 | `SMTPSenderRefused`, `SMTPAuthenticationError`, `SMTPDataError`, `SMTPHeloError`, any other `SMTPResponseException`: `exc.smtp_code` | 4xx → retry; else NoRetry |
  | 4 | any other `SMTPException` (e.g. `SMTPNotSupportedError`: no STARTTLS) | NoRetry, logged with its type |
  | 5 | any other `OSError` (timeout, refused connection, DNS; `ssl.SSLError` and `TimeoutError` are `OSError`s) | retry (back-off) |
  | 6 | anything else | NoRetry, logged with its type |

  So a greylisted recipient (450, 451) retries; a wrong password (535) or a
  refused sender (550) fails at once instead of 3 times per manager.
- The handler raises `smtp_outcome`'s own text, "`<outcome>` (SMTP
  `<code>`)" or "`<outcome>` (`<exception type>`)", `from None`, as
  `push_send` does: `str(SMTPRecipientsRefused)` carries the address, and
  `mark_failed` writes `str(exc)` into `task_queue.last_error`. So
  `last_error` and the log hold the outcome and the code, never the address,
  the password or the body. The log line names the task, the person id and
  the code.
- The payload holds the subject and body for the queue's retention
  (`company_settings.DONE_TASK_RETENTION_DAYS`, 90 days for a done row):
  ticket facts, first names and the close remark, as the `push_send` payload
  does today. Not the address (BR1-14).
- Email not set up when `email_send` runs (the secrets were emptied after
  queueing): NoRetry "email is not set up on this server".
- The close's transaction only inserts the `ticket_alert` row. A send that
  fails never touches the ticket.

### 5.6 Locks

- The close (`make_move`): unchanged lock order (`_lock_open_ticket`, then
  the rows `_apply_move` already writes); the new `INSERT INTO task_queue`
  is the same statement `enqueue_alert` already runs on send-back and
  regrade. No new lock.
- `ticket_alert` for `CLOSED`: plain reads, inserts into `task_queue` in the
  worker's transaction, as today.
- `auth_me`: one `UPDATE` of the user's own `people` row, autocommit-style
  in its own short transaction. A Team save of the same person by IT admin
  (`_lock_row(cur, "people", …)`) waits for it or it waits; no deadlock, one
  row.
- `POST /api/push/test-email`: one `INSERT` into `task_queue`.

### 5.7 The database down

- `auth_me`: the email copy is inside the existing `try … except
  DBUnavailable`, so it is skipped and the answer is as today.
- `GET /api/push/config`, `POST /api/push/test-email`: 503 as every route.
- The worker does not run its tasks without the database (S013).

### 5.8 Input checks

- `POST /api/push/test-email`: no body. 409 "Your login has no email address.
  Ask IT admin to add an email address to your login." when the user's
  person has none (BR1-09); 409 "Email is not set up on this server yet.
  Ask IT admin." when off; 409 "You are not in Team. Ask IT admin to add
  you." when there is no person (`push.NOT_IN_TEAM` through
  `push._own_person`, as `send_test`, BR1-08). Checked in this order: not in
  Team, email off, no address.

## 6. API

- `GET /api/push/config` (`push:subscribe`): adds `"email": {"enabled":
  bool, "address": "<own address>" | null}`. `you_get` gains the email line
  for managers.
- `POST /api/push/test-email` (`push:subscribe`, new): queues one
  `email_send` to the user's own person → `{"address": "<address>"}`, 202.
  Refusals § 5.8.
- `GET /api/settings/notifications` (`settings:read`, `settings.py`
  `get_notifications`, the route behind Settings › Notifications): adds
  `"email_enabled": bool, "email_from": "<SMTP_FROM>"`.
- `GET /api/masters/people`: `email` per person for IT admin only; removed
  for everyone else.
- `POST /api/tickets/<id>/moves/close` and `…/not-a-fault`: response
  unchanged.

## 7. Design decisions

1. **Email joins the existing alert path, not a new one.** *Ticket closed*
   is one more kind in `alerts_core`, with an audience and a channel. The
   `ticket_alert` task fans out by channel. Rejected: a separate
   `closed_email` task with its own recipient query (a second audience rule
   that could drift from *What you will get*).
2. **Mailgun over SMTP, with `smtplib`** (U2: "O365, mailgun available").
   The production template already has the five SMTP values; Mailgun
   accepts SMTP login with STARTTLS; `smtplib` is in the standard library, so no
   new dependency. Rejected: Office 365 through Microsoft Graph (an Azure
   app registration, admin consent, client secrets and an HTTP client —
   Office 365 refuses basic SMTP login, as plant3i found); Mailgun's HTTP
   API (`requests` is there, but it ties the code to one provider, where
   SMTP works with any server).
3. **Addresses from Keycloak, kept on login** (U2, replacing the earlier
   "email field on Team"). No second copy to maintain; a changed address
   follows at the next login. The cost: a manager who has not opened Yantra
   since the release has no address yet, and the Team dialog shows it.
   Rejected: a typed Team field (a second copy); the Keycloak admin API at
   send time (a service account and its secret, and a network call per
   send).
4. **One email per recipient, To: one address.** Nobody sees the other
   recipients, and a refused address fails only its own task. Rejected: one
   email with all managers in To (one failure stops all; addresses shown).
5. **Plain text only.** Every mail client shows it; it is easy to test; the
   fixed-width layout lines up in Outlook's plain view. Rejected: HTML (a
   template, escaping, and a second body to test) — later, if asked.
6. **Every close, *not a fault* included, with its own subject** (U1). A
   manager sees frivolous reports too; the subject tells them apart.
7. **The closer is left out.** A manager who closed the ticket knows. Same
   rule as every S021 alert. Rejected: send to them too (a copy of what they
   just did).
8. **No email for back-entered history.** The S028 backlog (until
   30-11-2026) would otherwise mail managers about closes weeks old. Same
   7-day rule as the raise alert.
9. **Address read at send time, not stored in the queue.** Keeps the
   address out of `task_queue` (a done row is kept 90 days) and uses a
   corrected address on a retry.
10. **A test button on My notifications.** Without it, the only way to check
    the mail server is to close a real ticket. It sends to the user's own
    address only, so it cannot be used to mail anyone else.
11. **A dev-only stub email** (BR1-06). `DEV_STUB_EMAIL` beside
    `DEV_STUB_ROLE`, so the user can send a test email from the laptop
    through the real mail server before the release. (A closed-ticket email
    cannot reach the dev stub, § 8; its text is unit-tested, BR2-02.)
    Rejected: no stub, so the first real email is seen in production.

## 8. Tests and acceptance

### Backend (pytest)

- `test_email_core.py`: `closed_email` for a breakdown with every line, a
  defect (`Downtime: 0 h 00 min`, BR1-11), a not-a-fault close (subject, first line, the
  left-out lines), 0 and 11 parts ("and 1 more"), a 600-character
  description (cut with "…"), a description with CR/LF (subject clean);
  `duration_text` 0, 5, 148, 1560 minutes; `valid_address` good, empty,
  no `@`, two `@`, a space, a comma, 255 characters; `smtp_outcome`: one
  case per row of the § 5.5 table, plus `SMTPConnectError` with a 554
  greeting (row 1, not row 3), a 450 and a 550 recipient refusal, a 452 and
  a 550 sender refusal, a 535 login refusal (NoRetry, not row 5),
  `SMTPNotSupportedError` (row 4), a plain `TimeoutError` and a
  `ConnectionRefusedError` (row 5); and that the raised text holds no
  address.
- `test_alerts_core.py`: `close_alert` inside and past 7 days;
  `CHANNELS[CLOSED] == ("email",)`; `excluded_people(CLOSED, …)` leaves out
  the actor only; `you_get` for a manager (the email line), an engineer
  (none).
- `test_closed_email.py` (with the session DB and a fake sender):
  - close → one `ticket_alert` of kind `closed` in `task_queue`, in the same
    commit; a refused close (400) queues nothing;
  - not-a-fault close → the same, and the email's subject says so;
  - a close back-dated 8 days → no task;
  - drain: two managers at the site (one all units, one other unit only),
    one engineer, one manager without email, the closer a manager → exactly
    one `email_send`, to the right person;
  - `email_send` with the fake sender: sent; each `smtp_outcome` path
    (NoRetry, retry); no address now → done, not sent; email off → NoRetry;
  - email off at `ticket_alert` time → no `email_send`, done.
- `test_auth.py` / an `auth_me` test: a token email is stored lower-cased;
  a changed email replaces it; an invalid one or none clears it; no person
  → nothing; database down → the answer as today. The copy is one helper,
  `store_login_email(cur, person_id, email)`, which returns the `UPDATE`'s
  row count; a test calls it twice with the same email and asserts 1, then
  0 (BR2-05: `people.updated_at` has no `ON UPDATE`, so it cannot show a
  write). `people.updated_at` and `updated_by` stay as they were.
- `test_push_api.py`: the config's `email` block; `POST /api/push/test-email`
  202 with one `email_send` queued, and the three refusals.
- `test_masters_api.py`: IT admin sees `email` in `GET /api/masters/people`;
  an engineer does not.
- `test_alerts.py`: the existing push kinds still queue `push_send` only.
- `test_migration_v27.py`: on the pattern of `test_migration_v26.py`: from
  v26 to v27, the column exists and is NULL for existing rows; re-run is a
  no-op.

### Automated (e2e)

- **Important** — `notifications.spec.js`: the manager (seed `e2e_manager`,
  `X-Test-Email: e2e_manager@example.test`) opens My notifications and sees
  "Closed tickets at SMTW, by email" and "Email goes to
  e2e_manager@example.test, from your login."; after *Send test email* the
  *Email* card shows "A test email is on its way to
  e2e_manager@example.test. Check your inbox in a few minutes." (BR2-03).
- `notifications.spec.js`: the technician with no email sees "Your login has
  no email address, so you get no email. Ask IT admin to add an email
  address to your login."
- **Important** — `masters.spec.js`: in the same test, the manager first
  loads a page (which stores the address), then IT admin opens the
  manager's Team dialog and sees "Email (from Keycloak):
  e2e_manager@example.test"; the engineer opening the same dialog sees no
  email line. The test does not depend on another test's order (BR1-04).
- `screens.spec.js`: unchanged routes; runs as part of the full suite.
- The e2e backend sets `SMTP_HOST` to a dummy value, so email counts as set
  up; it runs no worker, so the test email stays a queued task and no mail
  leaves the machine. The full e2e suite runs (e2e support changed).

### On a real device

- **Important** — production, KLA's Keycloak login (a manager membership at
  SMTW), office network: open Yantra, then My notifications shows your
  address; press *Send test email*; the email arrives in Outlook within 5
  minutes, not in junk, sender `SMTP_FROM`.
- **Important** — production, office network: a ticket on the TEST machine
  closed by an engineer's login (`<engineer login>`, named when the row is
  handed over); in KLA's Outlook and each other SMTW manager's, the email
  arrives within 5 minutes; the figures match the ticket page's times card;
  the link opens the ticket after login (BR1-05).
- Production, IT Admin's login, office network, Masters › Team: each
  manager shows the address from AD; a manager with none is told to open
  Yantra once, or IT fixes the address in AD.
- Dev server on KLA's laptop, `DEV_STUB_EMAIL` and the local `SMTP_*` set
  to Mailgun, the dev stub in Team: *Send test email* and read it in
  Outlook before the release (BR1-06). A closed-ticket email cannot reach
  the dev stub (the closer is left out, and in dev the stub is the only
  login), so its text is checked by `test_email_core.py` and in production.

### Acceptance

- All four suites green; the full e2e suite green.
- Releasing needs, before the deploy (by the user, outside Claude): the
  Mailgun SMTP values in the Ansible vars `settings_vel_yantra_master.yaml`
  (`smtp_host`, `smtp_port`, `smtp_user`, `smtp_password`, `smtp_from`), and
  the sending domain verified in Mailgun (SPF and DKIM records), so mail is
  not marked as junk.
- **Before the release, the user reads the real
  `settings_vel_yantra_master.yaml`** (BR1-02). The template renders the
  five `smtp_*` keys without defaults, so they exist there already, perhaps
  as placeholders (`xxx`, as in the example file). Set either the real
  Mailgun values, or `smtp_host: ""` and `smtp_from: ""` to ship with email
  off. A placeholder host would turn email on with a dead server, and every
  close would fail 3 attempts per manager.

## 9. Open questions and assumptions

1. **Mailgun as a third party** (decision for the user): ticket facts and
   first names pass through Mailgun's servers (§ 2, A.5.14). Recommended:
   accept; the content is operational, with no photos or contact data.
2. **Sending address and server** (U3, U4, U5): answered. The domain is
   verified in Mailgun. The sender address, server and port are set only in
   the Ansible vars (`smtp_from`, `smtp_host`, `smtp_port`), never in the
   repo: no code default, no example value, no doc (user policy, U5). A
   *noreply* sender means a reply bounces, so the email's last line points
   to the ticket, not to a reply.
3. **Keycloak email claim** (to verify): the client's default scopes include
   `email`, and the LDAP federation maps AD's `mail` to the user's email.
   If not, IT adds the mapper; until then no one gets email (Masters › Team
   shows it).
4. **Closer left out** (assumption, decision 7). Alternative: a manager gets
   the email even for a ticket they closed.
5. **Engineers not included** (U1: managers only). Plan.MD's daily summary
   will reach engineers later.
6. **Plain text** (decision 5). Alternative: a simple HTML table.

## 10. Amendments

None.

## Review log

### U1 — user answers, 23-10-2026 (before drafting)

- Recipients: the site's managers. Which closes: every close, *not a
  fault* included. Timing: one email per close, not a digest.
- Addresses: first "email field on Team"; replaced by U2.

### U2 — user answers, 23-10-2026 (before drafting)

- "Keycloak email also is a good alternative I have to consider", then:
  addresses from Keycloak, kept on login.
- Mail server: "O365, mailgun available" → Mailgun over SMTP (§ 7.2).

### U3 — user, 23-10-2026 (during review round 1)

- The user named the sender address for Mailgun (kept in the Ansible vars, not here, U5) → open question 2.

### U4 — user, 23-10-2026 (during round 1 answers)

- "Domain already verified", with the server and port (kept in the Ansible vars, not here, U5) → open question 2.

### Round 1 — `2-brief-review-r1.md` (Fable), answered 23-10-2026

0 blocker, 1 major, 5 minor, 10 nits.

| Finding | Answer |
|---|---|
| BR1-01 major — `smtp_outcome` table contradicts itself | Accepted (a): ordered table decided by the code, `SMTPConnectError` first, recipient code from `exc.recipients[address][0]`; raised text is the outcome + code, `from None`; § 5.5, § 8 tests one case per row |
| BR1-02 minor — placeholder SMTP values turn email on | Accepted (a): `enabled()` needs `SMTP_HOST` and `SMTP_FROM` (§ 1.1); Acceptance: the user reads the real vars before release |
| BR1-03 minor — place of the email lines and button | Accepted (a): a third card *Email*, button in its header, success line in the card; § 1.5 |
| BR1-04 minor — how tests carry the email claim | Accepted (a): `require_auth` passes `X-Test-Email` as a third argument; `harness_user`, `conftest`, `e2e_backend`, `people.js` follow; the masters e2e loads the manager's page first; § 3, § 5.4, § 8 |
| BR1-05 minor — device checks lack account and network | Accepted (a): § 8 On a real device |
| BR1-06 minor — no email in dev | Accepted (a): `DEV_STUB_EMAIL`, dev only; decision 11; a dev device row (test email only) |
| BR1-07…BR1-16 nits | All accepted (round 2 checked the answers). BR1-07: 90 days. BR1-08: 409. BR1-09: "add an email address to your login". BR1-10: "A test email is on its way …". BR1-11: defect downtime `0 h 00 min`. BR1-12: `WAITING_REASONS`. BR1-13: people POST/PUT never take `email`, one test. BR1-14: the payload keeps the body for 90 days, stated. BR1-15: extra facts read only when a recipient has an address. BR1-16: A.5.16 in § 2. |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 23-10-2026

0 blocker, 1 major, 0 minor, 5 nits.

| Finding | Answer |
|---|---|
| BR2-01 major — `OSError` row first catches every SMTP error | Accepted (a): SMTP rows 1–4 first, then plain `OSError` (row 5, retry), then anything else; checked on Python 3.12.2 (`issubclass(smtplib.SMTPException, OSError)` is True); § 8 adds `TimeoutError`, `ConnectionRefusedError` and the 535-not-row-5 case |
| BR2-02…BR2-06 nits | All accepted. BR2-02: decision 11 names the test email only. BR2-03: § 8 checks the card's line, not a toast. BR2-04: decisions in order 9, 10, 11. BR2-05: `store_login_email` returns the row count, asserted 1 then 0. BR2-06: the recipient code is the dict's only value. |

### Round 3 — `2-brief-review-r3.md` (Fable), answered 23-10-2026

0 blocker, 0 major, 1 minor, 2 nits. Review loop complete.

| Finding | Answer |
|---|---|
| BR3-01 minor — where `store_login_email` lives and what it takes | Accepted (a): `auth_utils.py` beside `current_person_id`; takes the raw token email, cleans and checks it, one `UPDATE`, returns the row count; § 3, § 5.4 |
| BR3-02, BR3-03 nits | Accepted. BR3-02: an empty `recipients` dict is NoRetry. BR3-03: the ambiguous clause dropped. |

### Gate A — approved 23-10-2026 by KLA ("Code S032")

Approved as it stands, with the recommendations: Mailgun as a third party
accepted (open question 1); the closer left out (open question 4); one
step, not split. Open question 2's domain spelling was answered after
approval (U5); it is an Ansible value and does not change the code.
Coder: Opus. Baseline: 33c3a4b (the review's `aad833a + uncommitted S031`,
now committed as S031). Stale brief check: no code changed since.

### U5 — user, 23-10-2026 (after approval, during coding)

- The domain spelling answered. Policy: "the SMTP addresses, port, email
  addresses do not get committed. They come from ansible vars." So: no host,
  port or address in code, examples, tests or docs; `SMTP_PORT` has no code
  default, and email is on only when host, port and from are all set
  (§ 1.1, § 3). Sent to the coder at once. This tightens the approved brief
  and changes no design; recorded here, not as an amendment.
