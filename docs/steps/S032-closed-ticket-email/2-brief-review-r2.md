```
Step: S032 — Email to managers when a ticket is closed
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 23-10-2026
```

Reviewed against: aad833a + uncommitted S031

# S032 — Brief review, round 2

**Verdict: one `major` finding is open (BR2-01: the re-ordered `smtp_outcome`
table of § 5.5 still cannot be coded as written, because `OSError` in row 1
catches every `SMTPException`). No blocker, no minor.** Five nits. Every
round 1 finding marked `Accepted` is reflected in the brief's text. Facts file
`scratch/brief-facts-S032.md` (re-run on this draft) was given and used.

Sections re-read, as the round 1 answers changed them: § 1.1 (`enabled()`),
§ 1.5 (the *Email* card), § 2 (A.5.16), § 3 (the test-user factory chain,
`DEV_STUB_EMAIL`, masters POST/PUT), § 5.1, § 5.3 (`WAITING_REASONS`), § 5.4,
§ 5.5 (the table, the raised text, retention), § 5.8, § 7 decision 11, § 8
(tests, e2e, device checks, acceptance), § 9 open question 2, and the Review
log. Code read for them: `auth_utils.py` (`make_user`,
`validate_keycloak_token`, `_get_dev_stub_user`, `require_auth`,
`current_person_id`), `tests/harness.py`, `tests/conftest.py`
(`_test_user_factory`), `tooling/e2e/e2e_backend.py` (`_user_factory`, lines
97–101), `frontend/e2e/support/people.js`, `push.py` (`_own_person`,
`send_test`), `push_sender.enabled`, `task_handlers.py` (`ticket_alert`,
`push_send`), `NotificationsView.vue`, `tickets_core.WAITING_REASONS`,
`masters_core.validate_person`, `app.py` `auth_me`, `local_db.py` (`people`),
and the `smtplib` class tree on the project's Python (3.12.2). The unchanged
sections were not re-reviewed.

## Major

### BR2-01 — major — § 5.5: row 1 of the `smtp_outcome` table (`OSError`, checked first) catches every `SMTPException`

**Problem.** The brief says the rows are checked in the order given, and row 1
retries on `SMTPConnectError`, `SMTPServerDisconnected` **and `OSError`**.
`smtplib.SMTPException` has been a subclass of `OSError` since Python 3.4
(checked on this project's 3.12.2: `issubclass(smtplib.SMTPException,
OSError)` is `True`). So an `isinstance(exc, OSError)` test in row 1 is met by
a 535 login refusal, a 550 recipient refusal, a refused sender and
`SMTPNotSupportedError` too: rows 2–4 are never reached, and every SMTP
failure retries three times per manager. That is the outcome BR1-01 was
raised to prevent. A coder who follows the order as written builds it wrong;
one who notices has to decide the rule alone.

**Why it matters.** A wrong password or a dead sending domain fails 3 attempts
per manager per close, with the back-off, and the fault shows late.

**Options.**
- (a) **Recommended.** Put the SMTP rows first and the plain `OSError` row
  after them. Replace the table with:

  | # | Exception | Outcome |
  |---|---|---|
  | 1 | `SMTPConnectError`, `SMTPServerDisconnected` | retry (back-off) |
  | 2 | `SMTPRecipientsRefused`: the code of the one recipient | 4xx → retry; else NoRetry |
  | 3 | any other `SMTPResponseException` (`SMTPSenderRefused`, `SMTPAuthenticationError`, `SMTPDataError`, `SMTPHeloError`, …): `exc.smtp_code` | 4xx → retry; else NoRetry |
  | 4 | any other `SMTPException` (e.g. `SMTPNotSupportedError`: no STARTTLS) | NoRetry, logged with its type |
  | 5 | `OSError` that is not an `SMTPException` (timeout, refused connection, DNS; `ssl.SSLError` is an `OSError`) | retry (back-off) |
  | 6 | anything else | NoRetry, logged with its type |

  State why the order matters in one line ("`SMTPException` is an
  `OSError`, so the plain `OSError` row comes after the SMTP rows"). In § 8
  `test_email_core.py`, add the case that proves the order: a plain
  `TimeoutError` (row 5, retry) beside `SMTPNotSupportedError` (row 4,
  NoRetry) and the 535 login refusal (row 3, NoRetry).
- (b) Keep the row order and write row 1 as "`OSError` that is not an
  `SMTPException`". Same result, but a reader of the table has to know the
  class tree to see why; (a) reads correctly without that.

## Nits

- **BR2-02** (nit) § 7 decision 11 says the stub lets the user send "a test
  email and a closed-ticket email from the laptop"; § 8's dev check says a
  closed-ticket email cannot reach the dev stub (the closer is left out, and
  the stub is the only login). § 8 is right. Make decision 11 say "a test
  email", and that the closed-ticket text is checked by `test_email_core.py`
  and in production.
- **BR2-03** (nit) § 8 Automated, first check: "*Send test email* shows the
  toast". § 1.5 puts the success text as a line in the *Email* card, as
  `testSent` is for push, not a toast. Say "shows 'A test email is on its way
  to e2e_manager@example.test. …' in the card".
- **BR2-04** (nit) § 7: the decisions run 9, 11, 10. Number them in order
  (the stub as 10, the test button as 11, or swap the texts) and fix the two
  references (§ 3 `config.py` line and § 8's dev check cite "decision 11").
- **BR2-05** (nit) § 8 `auth_me` test: "the same email again writes nothing
  (row's `updated_at` unchanged)" cannot fail. `people.updated_at` is
  `DATETIME NULL` with no `ON UPDATE` (v20), and § 4 says the copy never
  writes it, so it is unchanged whether or not the `UPDATE` ran. Either drop
  the claim and assert the stored value only, or put the one `UPDATE` in a
  small function that returns `cur.rowcount` (0 on the second call) and test
  that.
- **BR2-06** (nit) § 5.5 row 2: `exc.recipients[address][0]` raises
  `KeyError` inside the handler if the key is not the exact string given
  (`send_message` takes the address from the header through
  `email.utils.getaddresses`). There is one recipient, so take the dict's
  one value: `next(iter(exc.recipients.values()))[0]`; a missing or empty
  dict falls to NoRetry.

## Checked and found consistent

- **Round 1 answers are in the text.** BR1-01: the ordered table, the
  recipient code, the raised text `from None` (as `push_send` raises, lines
  204 and 211 of `task_handlers.py`), one test per row. BR1-02: § 1.1
  `enabled()` needs `SMTP_HOST` and `SMTP_FROM`, and `push_sender.enabled`
  does need all three VAPID values as the brief says; § 8 Acceptance has the
  user read the real vars. BR1-03: a third card *Email*, button in its
  header, success line in the card; the push cards unchanged. BR1-04: § 3,
  § 5.4 and § 8. BR1-05: the three production checks name account, network
  and where. BR1-06: `DEV_STUB_EMAIL` in `config.py` and the example file,
  decision 11, a dev check. BR1-07 (90 days), BR1-08 (409), BR1-09 and
  BR1-10 (the texts), BR1-11 (`Downtime: 0 h 00 min`), BR1-12
  (`WAITING_REASONS`), BR1-13 (POST/PUT never take `email`), BR1-14 (the
  payload keeps the body for 90 days), BR1-15 (facts read only with a
  recipient), BR1-16 (A.5.16) are all in the text. No leftover old phrase
  found ("in Keycloak" survives only in Out of scope, where it is right: IT
  admin removes the address in Keycloak).
- **The test-user factory chain.** `require_auth` calls
  `factory(test_role, request.headers.get("X-Test-User"))` with two
  positional arguments; both factories, `conftest._test_user_factory(role_name,
  username)` and `e2e_backend._user_factory(...).factory(role_name, username)`,
  take two. A third positional argument needs both changed, and § 3 lists
  both. `harness_user(role_name, username, name=None)` gains `email=""` as a
  keyword, so the e2e factory's positional `name` keeps working; `make_user`
  gains a keyword with a default, so `test_rbac.py`'s direct calls keep
  working. `people.js` `headersFor(key)` returns the whole header set, and
  `asPerson` replaces it with `setExtraHTTPHeaders`, so a switch from the
  manager to the technician drops `X-Test-Email`: the technician's page load
  clears the address, as the second e2e check needs. The e2e stack sets
  `TESTING` and the factory, so the header path is the one taken; the dev
  stub (`DEV_STUB_ROLE = "nobody"`) is only the fallback.
- **§ 5.8 order** matches `send_test`: `_own_person` first (409
  `NOT_IN_TEAM`), then `enabled()` (409), then the person's own state; the
  texts follow push's `NOT_SET_UP` form.
- **§ 1.5 fits the page.** `inTeam` is a computed on `deviceState`, true for
  anyone with a Team record, whatever the push state; the two existing cards
  show on it, so the third does too. `testSent` is a line inside the card
  (line 141), the pattern the brief names.
- **§ 5.3** `WAITING_REASONS` is `code -> (label, kind)` as cited, and the
  "parts" label comes from it.
- **§ 3 masters.** `validate_person` runs `_validate(data, _PERSON_FIELDS,
  creating)`, which keeps the listed fields only, so `email` in a POST or PUT
  body is dropped as the brief says; `masters:read_senior` is `it_admin` only,
  so `_people_out`'s gate on `email` matches the login's.
- **§ 1.1 the dev stub.** `_get_dev_stub_user` is built once per process from
  `config.DEV_STUB_ROLE`; `DEV_STUB_EMAIL` read the same way fits.
- **§ 9 open question 2.** The brief keeps "smtw.im" as given and flags the
  spelling against the realm's `smtw.in`; U4's "domain already verified" is
  recorded without naming the domain, so the question is right to stay open.
- **§ 2 A.5.16** is ISO/IEC 27001:2022 *Identity management*; cited
  correctly beside A.5.34 and A.5.14.
- **Scope A / B.** The changed text reads in scope A; the new UI texts
  (§ 1.5, § 5.8) are in scope B.
