```
Step: S032 — Email to managers when a ticket is closed
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 23-10-2026
```

# S032 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The implementation follows the brief,
its three review rounds and U5. All four suites are green in my own run. I found 1 `minor`
finding (a port number in a step file, U5) and 6 nits.

## Test runs

- `YANTRA_TEST_RUN=s032cr1 tooling/run-tests.bat`: **ALL SUITES PASSED.** Backend 2453
  passed, frontend 126 passed, deps 42 passed, tooling 106 passed.
- `npx vite build` in `frontend/`: built in 3.4 s, with only the usual chunk-size warning.
- `tooling/step-check.bat`: no S032 issue.
- e2e: **not re-run.** The orchestrator asked for an e2e run only if a finding needed one,
  and no finding does. I rely on the coder's full run (276 passed, 6 skipped, 0 failed). The
  full suite was the right choice because `frontend/e2e/support/people.js` changed. I read the
  three S032 tests (below).

## Findings

### CR1-01 (minor) — a port number in a step file, against U5

**Where:** `docs/steps/S032-closed-ticket-email/2-brief-review-r1.md:263`.

**Problem.** The line reads "Mailgun over SMTP accepts login on 587 with STARTTLS". U5 (user
policy, 23-10-2026) says that no SMTP host, port or address goes into the repo, docs included.
The review was written before U5, so the reviewer did not break a rule at the time. The step
folder is committed with the step, so the line would be committed too.

**Failure scenario.** Production uses that port. The commit then records the production
port, which the user decided should live only in the Ansible vars.

**Fix (planner).** Change "on 587" to "on its submission port", and add a one-line note in
the brief's Review log under U5 that the line was redacted. Nothing else in the step folder,
the code, the tests or the docs names a real host, port or address (checked below).

## Nits

- **CR1-02** (nit) `backend/email_core.py:112-117`: the *Waiting* line shows the reasons by
  their code (`parts`, `vendor`, `expert`, `slot`, `approval`, `other`), not by the
  `WAITING_REASONS` label (decision 2). This matches the brief's example (`parts 0 h 20 min`),
  and it uses no second table, as BR1-12 asks. But `slot` and `approval` are not the words the
  ticket page shows. Ask the user at gate B whether the codes read well enough in a manager's
  email; no code change unless the user wants one.
- **CR1-03** (nit) `frontend/src/views/masters/PeoplePanel.vue:385`: for a person with no login
  (an operator, a contractor firm), "none yet. Filled at the person's next login." promises
  something that cannot happen. Show the line only when `editing.has_login` is true, or say
  "none (no login)" when there is no login.
- **CR1-04** (nit) `backend/mail_sender.py:32-35`: `with smtplib.SMTP(...)` sends `QUIT` in
  `__exit__` and raises `SMTPResponseException` when the answer is not 221. That happens after
  `send_message` has already delivered the email, so a 4xx answer resends it and a 5xx answer
  marks a delivered email as failed. Send `smtp.quit()` in its own `try` after `send_message`
  and log a failure there, or accept it and say so in the docstring ("arrives twice at worst"
  already covers the resend).
- **CR1-05** (nit) `backend/task_handlers.py:280-285`: row 6 of § 5.5 ("anything else") logs
  only the exception's type, so a programming fault in `send` (a `TypeError`, say) leaves no
  file and line in the log. Add the failing frame's file and line for row 6 only (from
  `exc.__traceback__`), which holds no address.
- **CR1-06** (nit) `backend/alerts.py:10, 187-189`: the changed module docstring has one line
  of 146 characters, and three blank lines come before `read_closed_facts`. Re-wrap the
  docstring at 100 characters and keep two blank lines.
- **CR1-07** (nit) `docs/steps/S032-closed-ticket-email/3-impl-report.md:173-182` and
  `backend/tests/conftest.py:101`, `tooling/e2e/e2e_backend.py:105`: decisions 14 (the masters
  tests are in `test_people_api.py`) and 17 (the e2e backend sets host, port and sender) depart
  from the brief's text but are not marked **(departure)**, as decision 10 is. Mark them. Also,
  the test port 2525 is a port Mailgun really offers. Under U5, prefer a test port with no SMTP
  meaning, so a test value can never be read as the production one.

## Checks the orchestrator asked for

1. **No explicit commit in `auth_me` (decision 10): true.** `local_db._connect_kwargs` sets
   `"autocommit": True` (`backend/local_db.py:853`). `init_pool` passes those settings to
   `PooledDB` (`local_db.py:871-879`), and `get_db()` returns a connection from that pool. The
   one-row `UPDATE` therefore commits by itself, as `db_helpers.transaction`'s docstring and
   `access_control.py:186` already rely on. The departure is wording only, as reported.
2. **Waiting reasons by code (decision 2):** see CR1-02. The choice is consistent with the
   brief's example and reported; it is a question for the user, not a fault.
3. **`valid_address` stricter than the brief (report decision 7):** it also refuses an empty
   part before `@` and any whitespace (tab included). Both are broken claims, and the brief
   calls the check "a guard against a broken claim". The stricter rule cannot refuse a real AD
   address. Consistent.
4. **The § 5.5 table, in order:** `email_core.smtp_outcome` checks rows 1–6 exactly in the
   brief's order. `SMTPConnectError` meets row 1 before row 3 (`SMTPResponseException`), and
   every SMTP row comes before the plain `OSError` row. `test_every_smtp_error_is_an_os_error`
   pins the reason. An empty `recipients` dict is NoRetry with the type (BR3-02). The recipient
   code is the dict's only value, not looked up by address (BR2-06). `test_email_core.py` has
   one case per row plus the 554 greeting, 450/451/550 recipient, 452/550 sender, 535,
   `SMTPNotSupportedError`, `TimeoutError`, `ConnectionRefusedError` and `SSLError` cases.
5. **No address in `task_queue.last_error` or the logs:** `email_send` raises the outcome's own
   text `from None`; the worker writes `f"{type(exc).__name__}: {exc}"`, so `last_error` reads
   e.g. "NoRetry: email refused (SMTP 550)" (tested through the real worker). The log lines name
   the person id and the outcome only. The payload holds the person id, subject and body, never
   the address (tested: no `@` in the queued payloads). `auth_me` logs nothing about the email.
6. **Existing push alerts unchanged:** `ticket_alert`'s push branch moved into `_push_fan_out`
   word for word; `CHANNELS` gives push to breakdown, defect, escalation and assigned only.
   `you_get`'s refactor (`continue` on no place) gives the same lines as before plus the email
   line. `test_alerts.py` gains a test that a push kind queues no `email_send` even for people
   with an address, and every S021 test still passes.
7. **U5 — no real host, port or address:** I searched the code, tests, comments and docs.
   `config.py` reads all five `SMTP_*` names with an empty or 0 default (`SMTP_PORT` has no
   default); `example_secrets_app.py` holds empty values; `mail_sender.enabled()` needs host,
   port and sender. Tests and the e2e backend use `smtp.example.test`, `@example.test` and
   2525 (see CR1-07). The only real-looking port is CR1-01. The app's own URL
   (`vel-yantra.mspv.app`) in the brief's example and in `test_email_core.py` is the public app
   address, already in the repo since S014, and not an SMTP value.
8. **Planner edits (brief § 3 Docs):**
   - `docs/Plan.MD` § 4.7: the table gains *Ticket closed* in the Email column, and the
     *Email* bullet names Mailgun over SMTP and Keycloak as the source of addresses. As asked.
   - `docs/Keycloak.md`: the `email` claim (client scope `email`) and the AD `mail` mapper. As
     asked; no address.
   - `.claude/CLAUDE.md` Notifications: the channel, `smtplib` only in `mail_sender.py`, the five
     secrets, off unless host, port and from are set (U5 tightens "empty host = off"), and the
     U5 policy itself. As asked.
   - `docs/steps/README.md`: the S032 index row only. Correct.

## Checked and found consistent

- **Migration v27:** one `ALTER TABLE people ADD COLUMN IF NOT EXISTS email VARCHAR(254) NULL`,
  appended after v26; no `_PRECONDITIONS` entry, as § 4 decides. `test_migration_v27.py` covers
  a fresh database, a v26 database with people (every row kept, email NULL) and a re-run.
- **The close enqueue:** in `_apply_move`, for every move whose `to_state` is `closed` (only
  `close` and `not-a-fault` in `MOVES`), after the event, in the close's own transaction; no new
  lock. `close_alert` returns None past `MAX_BACKDATE_DAYS` (tested at 7 days and at 7 days and
  1 minute). The closer is left out, the reporter is not; `excluded_people` drops a None actor.
- **Recipients:** `recipients(..., with_email=True)` adds `p.email IS NOT NULL` to the S021
  query, so the audience rule is not copied. The fan-out test covers the manager for all units,
  the manager for the unit, the manager at another unit, the engineer, the manager without an
  address, the inactive manager and the closer.
- **Facts read only when someone gets the email** (BR1-15): tested by a monkeypatched
  `read_closed_facts` that must not be called.
- **The figures:** `read_closed_facts` reads the events in the ticket page's order
  (`occurred_at, id`) and calls `ticket_times` with the closing event's time (decision 5).
  The worker reads the events at drain time, so an event dated after the close would not
  count; a closed ticket takes no new ordered events today (`_lock_open_ticket`). A test
  compares the email's downtime with the ticket page's.
- **The text:** `closed_email` gives the § 1.4 body exactly (one full-body test), the
  not-a-fault variant without times, action, labour and parts, `Downtime: 0 h 00 min` for a
  defect, the 500-character cut with "…", 10 parts and "and 1 more", and a subject without line
  breaks. `To` is a checked address; `From` is `SMTP_FROM`; one recipient per email.
- **`email_send`:** reads the address and `active` at send time; no address or inactive is done;
  email off is NoRetry; a malformed payload is `BadTask`. STARTTLS uses
  `ssl.create_default_context()` (certificate checked, tested as `CERT_REQUIRED`); the 30 s
  timeout is in `company_settings.py` beside the push timeout.
- **`auth_me`:** the copy is inside the existing `try … except DBUnavailable`, after
  `current_person_id`, and only when there is a person. `store_login_email` strips,
  lower-cases, checks and runs the `<=>` update; the row count is tested 1 then 0. `updated_at`
  and `updated_by` stay unchanged (tested). Database down: the answer is as before (tested).
- **Permissions:** `POST /api/push/test-email` has `require_perm("push:subscribe")`, sends only
  to the caller's own person, and refuses in the § 5.8 order with the brief's messages (all
  three tested, and a login with no role gets 403). No permission key changed.
- **Privacy:** `_people_out` deletes `email` for anyone but IT admin; it is the only place that
  returns whole `people` rows (`SELECT *`), and every other query names its columns. People
  `POST` and `PUT` never write `email` (tested). The address reaches only its owner
  (`/api/push/config`) and IT admin.
- **Layers:** the rules are in pure modules (`email_core`, `alerts_core`); `mail_sender` is the
  only module that opens an SMTP connection; routes and the handler are thin. The import
  direction is shell → core. No new dependency, so `sbom/` is untouched.
- **Screens (scope B and floor use):** the *Email* card shows the three brief lines, the
  button "Send test email" (a verb, no `btn-sm`, disabled while busy), the success line in the
  card, and the server's refusal in the card. `text-break` keeps a long address inside the
  card on a phone. Settings › Notifications shows both status lines. No dialog was added; the
  Team dialog only gains one read-only line.
- **e2e tests:** the three S032 tests assert the text the user sees (the *What you will get*
  line, the address line, the success line, the no-address line, the absent button, the Team
  dialog line for IT admin and its absence for the engineer). The masters test loads the
  manager's page first, so it does not depend on test order, and it calls `expectDialogFits`
  on the dialog it opens.
- **Impl report:** `## 6. Manual checks` holds the two important automated checks as `[auto]`
  with their tests, and the two important real-device checks as unticked boxes; rows 27–30 are
  in `device-checks.md` with account, network and place. Decisions are listed, and the report
  is in scope A.

## Manual browser checks for the user

These are the brief's real-device checks, rows 27–30 of `docs/steps/device-checks.md`:

- [ ] **Important** — row 27: production, KLA's login, office network. My notifications shows
  your address; *Send test email* arrives in Outlook within 5 minutes, not in junk, from
  `SMTP_FROM`.
- [ ] **Important** — row 28: a ticket on the TEST machine closed by an engineer's login. Each
  SMTW manager gets the email within 5 minutes; its figures match the times card; the link
  opens the ticket.
- Row 29: IT Admin sees each manager's address in Masters › Team.
- Row 30: dev server, `DEV_STUB_EMAIL` and local Mailgun values: *Send test email* reaches
  Outlook before the release.

Before the release, the user also reads the real `settings_vel_yantra_master.yaml` and sets
either the Mailgun values or an empty host, port and sender (brief § 8 Acceptance).
