```
Step: S032 — Email to managers when a ticket is closed
Doc: brief-review r3
Author: Brief reviewer (Fable)
Date: 23-10-2026
```

Reviewed against: aad833a + uncommitted S031

# S032 — Brief review, round 3

**Verdict: no `blocker` or `major` finding is open.** One `minor` (BR3-01:
`store_login_email` is named only in § 8; § 3 and § 5.4 do not say where it
lives or what it takes), two nits. Every round 2 finding marked `Accepted` is
reflected in the brief's text. No leftover old phrase found. Facts file
`scratch/brief-facts-S032.md` (re-run on this draft) was given and used. This
is the last round of the full track (3 of 3).

Sections re-read, as the round 2 answers changed them: § 5.5 (the
`smtp_outcome` table and the sentence before it), § 7 decisions 9–11, § 8
`test_email_core.py` (the `smtp_outcome` cases), § 8 the `auth_me` test, § 8
Automated (the first `notifications.spec.js` check), § 8 On a real device (the
dev row), and the Review log. For BR3-01, § 3 `app.py` / `auth_utils.py` and
§ 5.4 were read against the new § 8 text. Code read: the `smtplib` class tree
on the project's Python (3.12.2, the `uv` environment), `app.py` `auth_me`,
`auth_utils.current_person_id`, `task_handlers.push_send`. Nothing else was
re-reviewed.

## Minor

### BR3-01 — minor — `store_login_email` is named in § 8 only; § 3 and § 5.4 do not place it or define what it takes

**Problem.** § 8 says "The copy is one helper, `store_login_email(cur,
person_id, email)`, which returns the `UPDATE`'s row count" (BR2-05). § 3
lists `backend/app.py`: "`auth_me` stores the token's email (§ 5.4)" and
`backend/auth_utils.py` with the `make_user` and `require_auth` changes; the
helper is in neither line. § 5.4 describes the `UPDATE` inline in `auth_me`
and does not name the helper. Two things are left to the coder:

- the module: `app.py` (beside `auth_me`) or `auth_utils.py` (beside
  `current_person_id`, which already reads `people` through `cur`);
- the argument: the token's raw email (the helper lower-cases, strips and
  runs `valid_address`, NULL when it fails) or the cleaned value (the caller
  does that). The § 8 test "calls it twice with the same email and asserts
  1, then 0" works either way, so it does not settle it.

**Why it matters.** § 3 is the file list the coder and the code reviewer
work from; a function missing from it is a decision taken in code. And the
place of the validation decides whether `app.py` imports `email_core`.

**Options.**
- (a) **Recommended.** Put `store_login_email(cur, person_id, email)` in
  `auth_utils.py` beside `current_person_id`: it takes the token's raw
  email, cleans it (strip, lower-case, `email_core.valid_address`, else
  NULL), runs the one `UPDATE … AND NOT (email <=> %s)` and returns
  `cur.rowcount`. `auth_me` calls it inside the existing `with
  get_db().cursor() as cur:` block after `current_person_id`, when the person
  is not None, then `get_db().commit()`. Add the helper to § 3's
  `auth_utils.py` line and name it in § 5.4. The § 8 test then covers the
  cleaning through the helper as well as through `/api/auth/me`.
- (b) Keep the helper in `app.py` next to `auth_me`, taking the cleaned
  value; `auth_me` does the cleaning. Fewer imports in `auth_utils.py`, but
  `app.py` gains a database function it has none of today.

## Nits

- **BR3-02** (nit) § 5.5 row 2: say what the outcome is when
  `exc.recipients` is empty — NoRetry, logged with the type, as round 2's
  BR2-06 text said. `next(iter({}))` raises `StopIteration` inside the
  handler. `smtplib.sendmail` raises `SMTPRecipientsRefused` only with a
  non-empty dict, so this is a guard, not a path the server takes.
- **BR3-03** (nit) § 5.5, the sentence before the table: "checked on Python
  3.12.2, 23-10-2026, as is `TimeoutError`" is ambiguous (checked too, or an
  `OSError` too; both are true). Row 5 already says `TimeoutError` is an
  `OSError`, so drop the clause here.

## Checked and found consistent

- **BR2-01 (major) is in the text.** § 5.5 now has 6 rows in the order
  `SMTPConnectError` / `SMTPServerDisconnected` (1), `SMTPRecipientsRefused`
  (2), the other `SMTPResponseException`s (3), any other `SMTPException` (4),
  any other `OSError` (5), anything else (6), with the one-line reason for
  the order. The class tree the brief states holds on the project's Python
  3.12.2: `SMTPConnectError`, `SMTPSenderRefused`, `SMTPAuthenticationError`,
  `SMTPDataError` and `SMTPHeloError` are `SMTPResponseException`s;
  `SMTPServerDisconnected`, `SMTPRecipientsRefused` and
  `SMTPNotSupportedError` are plain `SMTPException`s; `SMTPException` is an
  `OSError`; `TimeoutError`, `ConnectionRefusedError`, `ssl.SSLError` and
  `socket.gaierror` (DNS) are `OSError`s. So each exception the brief names
  meets the row it is given, and no row above it catches it first. § 1.8
  ("a refused address or login fails at once; a network fault or a 4xx
  retries") matches the table.
- **BR2-06.** Row 2 takes the dict's only value,
  `next(iter(exc.recipients.values()))[0]`, not a lookup by address;
  `SMTPRecipientsRefused.recipients` is `{address: (code, message)}`, so
  `[0]` is the code (run: 550).
- **§ 8 `smtp_outcome` cases.** One per row, plus the `SMTPConnectError`
  554 greeting (row 1, not 3), the 450 / 550 recipient and 452 / 550 sender
  refusals, the 535 login refusal (row 3, "not row 5"),
  `SMTPNotSupportedError` (row 4), a plain `TimeoutError` and a
  `ConnectionRefusedError` (row 5), and the no-address assertion: the order
  proof BR2-01 asked for.
- **BR2-02, BR2-04.** Decisions run 9 (address at send time), 10 (test
  button), 11 (dev stub). Decision 11 says "a test email from the laptop"
  only, and that the closed-ticket text is unit-tested and checked in
  production, which matches § 8's dev row. No text cites a decision number
  that moved: the only "decision 10" left is S021's, in § 5.1, which is
  right. "BR1-06" is the cross-reference used in § 3, § 7 and § 8.
- **BR2-03.** § 8's first automated check reads the success line in the
  *Email* card, as § 1.5 specifies; "toast" appears only in the Review log.
- **BR2-05.** § 8 names the helper and the 1-then-0 row-count assertion,
  and says `updated_at` / `updated_by` stay as they were (§ 4 agrees). The
  placement gap is BR3-01 above.
- **No leftover old phrase.** `exc.recipients[address]`, "updated_at
  unchanged", "closed-ticket email from the laptop" and an `OSError` row 1
  survive only in the Review log's record of the earlier answers.
- **`auth_me` as the brief reads it.** The route has the `try … except
  DBUnavailable` and the `with get_db().cursor() as cur:` block the brief
  relies on (§ 5.4, § 5.7); `current_person_id(cur)` is read there, so the
  helper of BR3-01 slots in after it with one commit.
- **Scope A / B.** The changed text reads in scope A; no UI text changed
  this round.
