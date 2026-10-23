```
Step: S032 — Email to managers when a ticket is closed
Doc: impl-report
Author: Coder (Opus)
Date: 23-10-2026
```

# S032 — Implementation report

**Result.** Email is Yantra's second alert channel. A close (*Close* or *Not a fault*) now queues
*Ticket closed*, and the worker sends one plain-text email to each manager of the ticket's site
who covers its unit and has an address. Addresses come from the login token at every page load.
My notifications, Masters › Team and Settings › Notifications show the channel's state. All four
suites and the full e2e suite are green (numbers in § 7).

## 1. What was built

- **Email channel.** `mail_sender.py` sends one email over SMTP with STARTTLS (certificate
  checked) and a login. It is on only when `SMTP_HOST`, `SMTP_PORT` and `SMTP_FROM` are all set
  (user policy U5, which replaced "host and from"). Sends run in the worker only.
- **Addresses from Keycloak.** `/api/auth/me` copies the token's `email` claim onto the user's
  Team record when it differs. A missing or broken claim clears it. Migration **v27** adds
  `people.email VARCHAR(254) NULL`.
- **The alert *Ticket closed*.** Kind `closed`, audience Manager, channel email. Queued in the
  close's own transaction; not queued for a close dated more than 7 days back. The closer is left
  out, the reporter is not.
- **The email's text.** Subject and body exactly as § 1.4 (one fact per line, a line left out
  when it has no value; the not-a-fault variant).
- **Failures.** `email_core.smtp_outcome` follows the § 5.5 table row by row: a 4xx or a network
  fault retries (3 attempts), anything else fails at once. The text kept in `task_queue.last_error`
  and in the log is the outcome plus the SMTP code or the exception type, never the address.
- **Screens.**
  - My notifications: the *Email* card (after My devices) with its three lines, *Send test email*
    and the success line; *What you will get* gains "Closed tickets at SMTW, by email" for a
    Manager membership.
  - Masters › Team, person dialog (IT admin only): "Email (from Keycloak): …" or "… none yet.
    Filled at the person's next login."
  - Settings › Notifications: "Email: set up, sent from …." or "Email: not set up. Fill the SMTP
    values in the server's secrets."
- **API.** `GET /api/push/config` adds `email: {enabled, address}`; `POST /api/push/test-email`
  (new, 202, refusals in the § 5.8 order); `GET /api/settings/notifications` adds `email_enabled`
  and `email_from`; `GET /api/masters/people` sends `email` to IT admin only.

## 2. How it works

1. **Login.** `validate_keycloak_token` puts `payload["email"]` (or "") into `g.user["email"]`.
   The dev stub uses `DEV_STUB_EMAIL`; the pytest and e2e factories use the `X-Test-Email` header
   (`require_auth` passes it as the factory's third argument). In `auth_me`, after
   `current_person_id`, `store_login_email(cur, person_id, email)` runs one
   `UPDATE people SET email = %s WHERE id = %s AND NOT (email <=> %s)`. The value is
   `email_core.clean_address(raw)`: stripped, lower-cased, and kept only when `valid_address`
   accepts it, else NULL. It returns the row count (1 for a real change, 0 otherwise). The block
   is inside the existing `try … except DBUnavailable`, so a database that is down changes
   nothing in the answer.
2. **Close.** In `tickets._apply_move`, after the event, a move whose `to_state` is `closed`
   (*close* and *not-a-fault*) calls `alerts.enqueue_alert(cur, ticket_id, close_alert(now -
   occurred_at), event_id, current_person_id(cur), None, now)`. `close_alert` returns
   `Alert("closed", False)`, or None past `MAX_BACKDATE_DAYS`. `excluded_people` already leaves
   out the actor only for this kind. The close's transaction gains one `INSERT INTO task_queue`;
   lock order is unchanged.
3. **Fan-out.** `ticket_alert` reads the ticket, checks `should_send` (for `closed`: only while
   the ticket is still closed), then calls `_push_fan_out` and/or `_email_fan_out` by
   `alerts_core.CHANNELS[kind]`. Push is what it was, moved into its own function unchanged. For
   email: skip with a log line when email is off; else `alerts.recipients_with_email` (the S021
   recipient query plus `p.email IS NOT NULL`); only when someone is found,
   `alerts.read_closed_facts` and `email_core.closed_email`, then one `email_send` per person
   through `alerts.enqueue_email`.
4. **The facts.** `read_closed_facts(cur, ticket_id, event_id)` reads `read_alert_ticket`, then the
   component name, cause, action and `not_a_fault`, the events, the labour sum and distinct people,
   and the parts lines. Times come from `tickets_core.ticket_times` (the ticket page's function),
   with the closing event's time as "now" (a closed ticket's figures end at its close), and
   back in service from `latest_restoration`.
5. **Send.** `email_send` reads the person's address and `active` flag now. No address, or
   inactive: done, with a log line. Email off: `NoRetry`. Else `mail_sender.send(to, subject,
   body)`; any exception goes through `smtp_outcome` and is raised again as `RuntimeError`
   (retry) or `NoRetry`, `from None`, with the outcome's own text.

## 3. Files touched

Backend:
- `backend/email_core.py` (new, pure): `closed_email`, `email_for_test`, `duration_text`,
  `one_line`, `valid_address`, `clean_address`, `smtp_outcome`; the cut and parts limits.
- `backend/mail_sender.py` (new): `enabled()`, `send()`; the only module that opens an SMTP
  connection.
- `backend/config.py`: `SMTP_HOST`, `SMTP_PORT` (no default, 0), `SMTP_USER`, `SMTP_PASSWORD`,
  `SMTP_FROM`; `DEV_STUB_EMAIL`.
- `backend/example_secrets_app.py`: the five SMTP names, empty / 0; `DEV_STUB_EMAIL` commented out,
  empty.
- `backend/company_settings.py`: `SMTP_TIMEOUT_SECONDS = 30`.
- `backend/alerts_core.py`: kind `CLOSED`, `AUDIENCE[CLOSED]`, `CHANNELS` with `PUSH` / `EMAIL`,
  `close_alert`, `_SEND_STATES[CLOSED]`, the email line in `you_get`.
- `backend/alerts.py`: `EMAIL_SEND`, `EMAIL_SEND_ATTEMPTS`, `enqueue_email`, `recipients(...,
  with_email)`, `recipients_with_email`, `read_closed_facts`.
- `backend/tickets.py`: the close enqueue in `_apply_move`.
- `backend/task_handlers.py`: `ticket_alert` split by channel (`_push_fan_out`,
  `_email_fan_out`); new handler `email_send`; `HANDLERS` gains it.
- `backend/app.py`: `auth_me` stores the token's email.
- `backend/auth_utils.py`: `make_user(email="")`, the token's claim, the dev stub's email, the
  third factory argument, `store_login_email`.
- `backend/push.py`: the `email` block in `GET /config`; `POST /test-email`.
- `backend/settings.py`: `email_enabled`, `email_from`.
- `backend/masters.py`: `_people_out` removes `email` for anyone but IT admin.
- `backend/local_db.py`: migration v27.

Tests and tooling:
- `backend/tests/test_email_core.py` (new), `test_closed_email.py` (new),
  `test_migration_v27.py` (new).
- `backend/tests/test_alerts_core.py`: `CLOSED`, `CHANNELS`, `close_alert`, `should_send`,
  `you_get`.
- `backend/tests/test_alerts.py`: push kinds queue no `email_send`.
- `backend/tests/test_auth.py`: the claim into `g.user`; `TestLoginEmail` (store, replace,
  clear, no person, database down, row count 1 then 0).
- `backend/tests/test_push_api.py`: `TestEmailConfig`, `TestSendTestEmail`.
- `backend/tests/test_people_api.py`: `TestEmailFromLogin` (IT admin only; POST / PUT never write
  it).
- `backend/tests/test_settings_api.py`: the email status.
- `backend/tests/harness.py`: `harness_user(email="")`.
- `backend/tests/conftest.py`: the factory passes the email; session fixture `smtp_test_values`
  (reserved test values); fixture `email_off`.
- `tooling/e2e/e2e_backend.py`: SMTP test values set, the factory reads `X-Test-Email`,
  `DEV_STUB_EMAIL` emptied.

Frontend:
- `frontend/src/stores/notifications.js`: `sendTestEmail()`.
- `frontend/src/views/NotificationsView.vue`: the *Email* card.
- `frontend/src/views/masters/PeoplePanel.vue`: the read-only email line.
- `frontend/src/views/settings/NotificationsSettings.vue`: the email status line.
- `frontend/e2e/support/people.js`: `EMAILS`, `X-Test-Email` for the manager.
- `frontend/e2e/notifications.spec.js`, `frontend/e2e/masters.spec.js`: the S032 tests.

Docs:
- `docs/steps/device-checks.md`: rows 27–30.
- `docs/steps/README.md` and `1-brief.md`: status only.

## 4. Decisions taken

Departures from the brief text are marked **(departure)**.

1. **Email on needs host, port and sender** (coordinator message, user policy U5, 23-10-2026).
   `SMTP_PORT` has no code default (0 = not set). No real host, port or address appears in code,
   comments, tests or this report; tests use `smtp.example.test`, port 2525 and `@example.test`.
2. **Waiting reasons by their code** (`parts 0 h 20 min`), as in the brief's example; the codes
   are `WAITING_REASONS`' keys, in its order. The labels ("Waiting for parts", "Other (remark
   required)") read badly inside the brackets.
3. **The description cut and the parts limit live in `closed_email`** (pure), not in
   `read_closed_facts`, so `test_email_core.py` can test them as § 8 asks. `read_closed_facts`
   therefore reads every parts line; the email shows the first 10 and "and N more".
4. **`read_closed_facts` keeps the brief's signature** `(cur, ticket_id, event_id)` and calls
   `read_alert_ticket` itself. The ticket row is so read twice per closed alert (once by
   `ticket_alert` for `should_send`); one extra read, kept for a self-contained function.
5. **The closing event's time stands for "now"** in `ticket_times`. For a closed ticket the
   figures do not depend on now, and the worker needs no clock.
6. **A multi-line description or remark keeps the value column** in the body (the next lines are
   indented to it, as the parts lines are). The subject goes through `one_line`.
7. **`valid_address` also refuses** an empty part before `@` and any whitespace (tab included),
   beside the brief's list. A guard against a broken claim, as the brief says.
8. **`email_core` imports smtplib's exception classes** for `smtp_outcome`; `mail_sender` stays
   the only module that opens a connection (CLAUDE.md: "`smtplib` only in `mail_sender.py`" read
   as "calls").
9. **Outcome texts**: "email deferred (SMTP 451)", "email refused (SMTP 550)", "mail server not
   reached (TimeoutError)", "email failed (SMTPNotSupportedError)". A retry raises
   `RuntimeError`, as `push_send` does.
10. **No explicit commit in `auth_me`** **(departure, wording only)**: pool connections are
    autocommit (`db_helpers.transaction` docstring), so the one-row `UPDATE` commits by itself.
    The brief says "then commit".
11. **Shared helper `alerts.enqueue_email`**: the payload `{person_id, subject, body}` is built in
    one place for the alert fan-out and the test email.
12. **`recipients` gained a `with_email` flag**; `recipients_with_email` calls it, so the audience
    query is not copied.
13. **The test email's text** (the brief gives none): subject "Yantra test email", body "This is a
    test email from Yantra. / Yantra can send email to this address." It is in `email_core`
    (`email_for_test`; not `test_email`, which pytest would collect).
14. **The masters tests are in `test_people_api.py`** (where the people tests live), not
    `test_masters_api.py` as § 8 names.
15. **The *Email* card sits after My devices and before What you will get.** "After the push
    cards" read as after the two device cards; *What you will get* lists both channels, so it
    stays last.
16. **Pytest runs with email on** (session fixture `smtp_test_values`, reserved values), as it
    runs with push on, so a local secrets file can never point a test at a real server. Every send
    in the tests is a fake.
17. **e2e backend**: sets host, port and sender (not only `SMTP_HOST` as § 3 says), because
    `enabled()` needs all three; it also empties `DEV_STUB_EMAIL`.
18. **`SMTP_TIMEOUT_SECONDS` is in `company_settings.py`**, beside `PUSH_TIMEOUT_SECONDS`.

## 5. Not done, deferred, assumed

- Nothing of the brief is left out.
- Assumed: `people.updated_at` / `updated_by` stay as they were on the login copy (tested).
- `test_alerts.py::TestSendOutcomes::test_a_redirect_is_never_followed` failed once in a targeted
  run with `ConnectionAbortedError` from its local HTTP server, then passed twice alone. It is
  S021's test, untouched here; it looks flaky on Windows sockets.
- To do by the user before the release (brief § 8 Acceptance): read the real
  `settings_vel_yantra_master.yaml`, and set the Mailgun values or empty host, port and sender to
  ship with email off. A placeholder host and port would turn email on with a dead server.

## 6. Manual checks

Automated:
- [auto] **Important** — the manager sees "Closed tickets at SMTW, by email" and "Email goes to
  e2e_manager@example.test, from your login."; after *Send test email* the card shows "A test
  email is on its way to e2e_manager@example.test. Check your inbox in a few minutes." —
  `frontend/e2e/notifications.spec.js`::"S032: the manager sees the closed-ticket email line and
  their address; Send test email says it is on its way"
- [auto] The technician with no email sees "Your login has no email address, so you get no
  email. Ask IT admin to add an email address to your login." —
  `frontend/e2e/notifications.spec.js`::"S032: a person whose login has no email is told so, and
  gets no Send test email"
- [auto] **Important** — the manager loads a page, then IT admin sees "Email (from Keycloak):
  e2e_manager@example.test" in the manager's Team dialog; the engineer sees no email line —
  `frontend/e2e/masters.spec.js`::"S032: IT admin sees the manager's email from Keycloak in the
  Team dialog; the engineer sees no email line"
- [auto] `screens.spec.js`: unchanged routes, run in the full suite.

On a real device (rows 27–30 of `docs/steps/device-checks.md`):
- [ ] **Important** — production, KLA's login, office network: My notifications shows your
  address; *Send test email* arrives in Outlook within 5 minutes, not in junk, sender `SMTP_FROM`
  (row 27).
- [ ] **Important** — production, office network: a ticket on the TEST machine closed by an
  engineer's login; the email reaches KLA and each other SMTW manager within 5 minutes; the
  figures match the times card; the link opens the ticket after login (row 28).
- Production, IT Admin's login, office network, Masters › Team: each manager shows the address
  from AD (row 29).
- Dev server on KLA's laptop with `DEV_STUB_EMAIL` and local SMTP values: *Send test email* read
  in Outlook before the release (row 30).

## 7. Tests run

- **All four suites** (`YANTRA_TEST_RUN=s032c1 tooling/run-tests.bat`, final run): backend 2453
  passed, frontend 126 passed, deps 42 passed, tooling 106 passed. ALL SUITES PASSED.
- **Frontend build**: `npx vite build` built (only the usual chunk-size warning).
- **e2e, full suite** (`tooling/run-e2e-tests.bat`, 6 lanes, 3 projects): 276 passed, 6 skipped
  (skips already in the specs, per project), 0 failed, 4.6 min. The full suite runs because
  `frontend/e2e/support/people.js` and `tooling/e2e/e2e_backend.py` changed.
  - `notifications.spec.js` and `masters.spec.js`: every test passed on all three projects,
    the three S032 tests included.
  - The three S032 tests first passed alone on desktop Chromium, one lane (3 passed).

## Fix rounds

### Round 1

Scope: the user chose **CR1-04 only**. No e2e run: the change is in the backend sender
(`mail_sender.send`) and its tests; no screen and no API the screens use changed.

- **CR1-01** — Not in this round (user's choice).
- **CR1-02** — Not in this round (user's choice); stays open for gate B.
- **CR1-03** — Not in this round (user's choice); stays open for gate B.
- **CR1-04** — **Fixed.** `mail_sender.send` no longer uses `with smtplib.SMTP(...)`. It opens the
  connection, then runs STARTTLS, login and `send_message` in a `try`. An error there closes the
  socket (`close()`, no QUIT) and is raised as before, so the § 5.5 outcome table is unchanged for
  errors before and during `send_message`. Once `send_message` returns, the email counts as sent:
  `quit()` runs in its own `try`, and an `SMTPException` or `OSError` is logged as a warning with
  the exception type only (no address) and swallowed; `close()` runs in `finally`.
  - Tests (`backend/tests/test_closed_email.py::TestSender`): QUIT failing with 421, 554,
    `SMTPServerDisconnected` and `OSError` does not raise from `send` and the message was sent once;
    through `email_send`, a 421 on QUIT leaves the task done (no exception, so no retry and no
    failure); a login error still raises and QUIT is not called. The existing sender test now also
    asserts QUIT and close ran, and its fake lost the context-manager methods.
  - Fails without the fix: with the `except` made to catch nothing real, the 4 QUIT cases fail with
    the raised `SMTPResponseException(421)`, `SMTPResponseException(554)`, `SMTPServerDisconnected`
    and `OSError`, and the `email_send` test with `RuntimeError: email deferred (SMTP 421)` (5
    failed). Passes with the fix (10 passed in `TestSender`).
- **CR1-05, CR1-06, CR1-07** — Not in this round (user's choice); stay open for gate B.

Decision taken: `send` catches `BaseException` before the message to close the socket, then
re-raises. The code logs with the module's own `log` (as other modules do).

Files touched in this round: `backend/mail_sender.py`, `backend/tests/test_closed_email.py`,
this report.

Tests (`YANTRA_TEST_RUN=s032c2 tooling/run-tests.bat`): backend 2459 passed, frontend 126 passed,
deps 42 passed, tooling 106 passed. ALL SUITES PASSED.
