```
Step: S023 — Alerts: Telegram and end-of-shift list
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 21-10-2026
```

Reviewed against: 28d3be3 + uncommitted S024

**Verdict: two `major` findings open (BR1-01, BR1-02); no blocker.** The brief
is consistent with S021 as written (its kinds, its `ticket_alert` task, its
Settings › Notifications pair, its audience) and with Plan.MD § 4.7 and Q12.
The two majors are rules the coder would otherwise settle alone: which units
the end-of-shift list counts, and how three shift ends share one task type on
S013's scheduler (the brief's claim about that code does not hold as written).

Read for this review: the brief; S021's brief (draft, in review); Plan.MD
§ 4.2, § 4.7, § 9 Q2/Q12; Maintenance-Philosophy § 6, § 9; Plant-Facts § 2,
§ 5; base § Telegram Notification Pattern, § Job queue; S019's and S025's
briefs where they touch this step; the code: `task_queue.py`,
`task_handlers.py`, `scheduled_tasks.py`, `worker.py`, `settings.py`,
`tickets.py` (list route, `_visible_condition`), `tickets_core.py`
(`latest_restoration`, states), `config_rbac.py`, `auth_utils.user_unit_ids`,
`local_db.py` (tickets, ticket_events, app_settings), `config.py`,
`example_secrets_app.py`, `TicketsView.vue`, `SettingsView.vue`,
`frontend/e2e/support/`.

## Findings

### BR1-01 · major · The end-of-shift list is scoped to the wrong permission

**Problem.** § 5.6 and § 6 put the banner, the count and the filter under
"the ticket list's existing unit visibility". That visibility is
`_visible_condition` → `accessible_unit_ids(cur, READ_KEY)`, i.e.
`ticket:read`. But `ticket:close` is **site-scoped** (`SITE_SCOPED` in
`config_rbac.py`) and roles are per site (S011): an engineer at SMTW who is a
supervisor at BRICKS reads BRICKS tickets but cannot close them. With the brief
as written, the banner would say "3 tickets … not closed" and *Show them* would
list tickets the person cannot close — the one thing the list is for.

**Why it matters.** It is the rule of the feature, and the brief leaves it
implicit; the obvious reading (reuse `_visible_condition`) is wrong.

**Options.**
1. *(Recommended)* The `to_close` filter and the count use
   `accessible_unit_ids(cur, CLOSE_KEY)` (the helper exists; `user_unit_ids`
   asserts the key is in `SITE_SCOPED`, which `ticket:close` is) **and** the
   read condition. An empty close set → empty result, no banner (the control
   hidden, never a 403). State it in § 5.6 as: "the tickets the person may
   close, at the units where they hold `ticket:close`".
2. Keep `ticket:read` scope and show a disabled close on the row — more
   screen, same confusion.

Also say the route behaviour: the list route keeps `require_perm(ticket:read)`
and adds the close predicate only when `to_close` is asked; the count route
(if kept, BR1-05) is `require_perm(ticket:close)`.

### BR1-02 · major · Three shift ends on one task type do not fit S013's "once per entry" rule as claimed

**Problem.** § 5.3 says each shift end becomes a daily entry
`("shift_end_summary", "HH:MM")` and that S013's rule ("decided from the last
time one was enqueued") gives once per shift end, once after a gap, never
twice. I checked `scheduled_tasks.due_tasks` and `worker.enqueue_scheduled`:

- `last_enqueued` is keyed by **task type**, and `due_tasks` returns the type
  once **per due entry**. With entries 06:00, 14:00, 22:00 and a worker down
  from 13:00 to 23:00, both the 14:00 and the 22:00 entries are due at the
  first poll → `due = ["shift_end_summary", "shift_end_summary"]` → **two
  summaries**, same content, enqueued in the same transaction. The brief's
  test "once after a worker gap" cannot pass with the code as it is.
- A time **added** to the setting that lies between the last summary and now
  (say 10:00 saved at 15:00, the last summary at 06:00) is due at the next
  poll → a summary posts the moment IT admin saves. The brief says "the new
  times apply from the next poll", which is true but not what the admin
  expects.
- `settings.get_tasks` (the Background tasks card) iterates the fixed
  `SCHEDULE`; the dynamic entries would not show there, so an overdue
  summary (the worker down) is invisible on the one card made for it.

**Why it matters.** The one-per-shift-end rule is the design; the group gets
duplicates or a stray summary, and the brief tells the coder the existing
code already does it.

**Options.**
1. *(Recommended)* Keep one task type and **de-duplicate**: `enqueue_scheduled`
   (or `due_tasks`) returns each type once per poll, so a gap over two ends
   gives one summary (the list at that moment is the same list). Make the
   rule explicit: "after a gap, one summary, not one per missed end". For a
   changed setting, state the behaviour plainly in § 5.3 — either accept the
   immediate summary (one line in the card: "Saving a time earlier than now
   sends today's summary at once") or treat the save as "enqueued now" for
   entries already passed (write nothing; simplest is to accept and say so).
   Add the dynamic entries to `get_tasks` (one line per shift end, or one
   line "Shift-end summary · 06:00, 14:00, 22:00" with the next run), and say
   in § 3 that `settings.py` changes for it.
2. One task type per slot (`shift_end_summary_1/2/3`): keeps S013's code
   untouched but leaks the slot into the queue and the card; rejected.

### BR1-03 · minor · A reply to a deleted breakdown message fails for good

**Problem.** § 5.1: the escalation is sent with `reply_to_message_id`. If
someone deleted the breakdown message in the group (it happens in chats),
Telegram answers **400 "message to be replied not found"**, which § 5.2
classes as failed, no retry — the escalation never reaches the group, and
only the Background tasks card knows.

**Options.**
1. *(Recommended)* Use the Bot API 7.0 form `reply_parameters:
   {message_id, allow_sending_without_reply: true}` — a missing original
   degrades to a plain message. (`reply_to_message_id` /
   `allow_sending_without_reply` are the pre-7.0 parameters, still accepted
   but superseded; CLAUDE-COMMON *Deprecation*.) Name it in § 5.1 and test it
   in `test_telegram.py` by asserting the request body.
2. Catch that one 400 description and resend plain — a second call and
   string-matching an error text; rejected.

### BR1-04 · minor · How the handler tells the worker "retry after N s" and "no retry" is not named

**Problem.** § 3 adds a delay to `mark_failed`, but the decision to retry is
made in `worker._task_failed` from the exception type
(`retry=not isinstance(exc, BadTask)`); the handler cannot reach
`mark_failed`. The brief does not say what `telegram_send` raises for a 429
(carrying `retry_after`) or for 400/403 (no retry). S021 has the same gap for
its 400/403/410 outcomes and does not name a mechanism either, so the coder of
whichever lands first decides.

**Options.**
1. *(Recommended)* Two exceptions in `task_handlers.py`, used by both steps:
   `RetryLater(message, after_seconds)` → `mark_failed(..., delay=…)`;
   `PermanentFailure(message)` → `retry=False` (or reuse `BadTask`, whose
   docstring is "can't be run as given" — acceptable if the docstring is
   widened). Say "as S021 adds; if S021 lands without them, this step adds
   them". `BadTask` for a missing payload stays as is.
2. Return a status from the handler — changes `run_task`'s contract for every
   handler; rejected.

Also state that with **push off** (no VAPID keys) and Telegram on, S021's
`ticket_alert` fans out **no** `push_send` (today S021 § 5.3 enqueues nothing
at all when push is off, so its handler never meets that case); the brief's
test "Telegram on and push off still enqueues" needs this said.

### BR1-05 · minor · `GET /api/tickets/to-close-count` duplicates the list's `total`

**Problem.** The list route already returns `total` for any filter. A second
route with its own visibility SQL is a parallel path (CLAUDE-COMMON *DRY*).

**Recommended.** Drop the route; the banner calls
`GET /api/tickets/?state=to_close&per_page=1` and reads `total` (one request,
the same cost). If it stays, say why.

### BR1-06 · minor · The filter as a separate parameter, and what a row shows

**Problem.** § 6 adds `to_close=past_shift` beside `state`. S019 (same
phase, coded before or after) adds its filters as **values of `state`**
(`scheduled`, `overdue`) and of the one State dropdown. Two mechanisms for one
dropdown is friction for the user and the coder (what does
`state=closed&to_close=past_shift` mean?). § 1.2 also says the list shows "how
long each has waited" without saying where: today's row shows the raise age
("Stopped for …") on the right.

**Recommended.** `state=to_close` ("To close — past shift end") in
`STATE_FILTERS`, the dropdown's last entry; *Show them* sets that value. Order:
oldest restoration first (as proposed). The row, for that filter only, shows
"Back in service 09:15 · 5 h ago" in place of the raise age. State the SQL
source of the restoration time: the latest `ticket_events.back_in_service`
row of the ticket (a correlated `MAX(occurred_at)`), since the table has no
`restored_at` column and `latest_restoration` is Python over the events.

### BR1-07 · minor · "Not acknowledged after 10 minutes" — the minutes are not in the task

**Problem.** S021's `ticket_escalate {ticket_id, trigger_event_id}` → `ticket_alert
{ticket_id, kind: escalation}` carries no minutes. Reading the setting when
the message is built shows a changed value; S021 § 5.3 itself says a changed
setting "does not move an escalation already queued".

**Options.** *(Recommended)* Word it without the number: "⏰ Not acknowledged
— raised at 10:42" (the group can count). Or S021 adds `minutes` to both
payloads — ask S021's planner only if the number is wanted.

### BR1-08 · minor · `shift_ends`: no default, and the empty case

**Problem.** § 4 gives the format and "1 to 6 times" but not the value when
no row exists (the first install, the e2e DB) nor what an empty field means.
The e2e check "shift ends `06:00, 14:00, 22:00` saves" implies something is
there before.

**Recommended.** A default in code as `DEFAULT_LABEL_BASE_URL` is (the user's
answer to Q3, placeholder `06:00,14:00,22:00` until then); a stored value that
no longer parses falls back to it with a warning (the `label_base_url`
pattern); the field refuses empty with "Enter at least one time, e.g. 06:00".
`last_shift_end` still tolerates an empty list (returns None → nothing is
past its shift) so a bad row can never raise.

### BR1-09 · minor · *Send test* gives the admin nothing to see

**Problem.** The test is enqueued; the request returns before anything is
sent. The admin presses the button and the screen shows nothing — on
production she then waits, or presses again. Also the worst case (a wrong chat
id → 400, failed) is visible only as a count on the Background tasks card.

**Recommended.** Say what the screen says on 202: "Sent to the queue — it
should appear in the group within a few seconds. If it doesn't, see
Background tasks below." The button disabled for a few seconds after the
press. (Sending it synchronously from the request would be the better feel
for a test button, but it departs from the base rule that the Bot API call
happens in the worker; if the planner prefers it, say so as a recorded
departure for the test only.)

### BR1-10 · minor · Chat id rule, and one group shared by several sites

**Problem.** "Bad chat id refused" without the rule. And Q1's per-site groups
meet Plant-Facts § 2: BRICKS, SMTW-KP and the two farms are stock yards and
farms with a handful of pumps — they will most likely share SMTW's group. If
the setting forbids the same chat id on two sites, the answer to Q1 is forced.

**Recommended.** Rule: optional `-`, then 1–20 ASCII digits (supergroups are
`-100…`, basic groups a shorter negative number), stored as text; the same
chat id allowed on several sites (a ticket has one site, so no message
doubles; the shift-end summary is one message per site, which a shared group
then sees twice — say "one message per group, listing its sites" or accept
it). Add the shared-group case to Q1 so the user's answer covers it.

### BR1-11 · minor · Standards: two citations to fix, one to add

- **ISO 14224** data quality is **clause 6** ("Quality of data"), not § 7
  (clause 7 is equipment boundary, taxonomy and time definitions). S004 cites
  clause 6 correctly. The point made (cause and action coded while the memory
  is fresh) is clause 6's: it asks that data be collected close to the event
  by the people who did the work, with the coding checked.
- **ISO/IEC 27001:2022 A 8.24** is *use of cryptography* (key management);
  the bot token is not a key. **A 5.17 *Authentication information*** is the
  control for secrets like it: issued and stored securely, not shared, changed
  when compromised. S021 cites A 8.24 for the VAPID keys, which is right there.
- Add **A 8.15 *Logging***, which is what "no token in a log line" implements
  (logs must not expose authentication information), beside A 5.17.

### BR1-12 · minor · Where the pure functions live is left to the coder

**Problem.** § 3: "`alerts_core.py` or S021's `push_core.py` (whichever S021
ended with)"; the tests name `test_shift_core.py` but no `shift_core.py`.

**Recommended.** `shift_core.py` (new, pure): parse/format `shift_ends`,
`last_shift_end`, "past its shift"; imported by `settings.py`, `tickets.py`,
the handler and the scheduler glue. The group message text and HTML escaping
go beside S021's notification text (it builds the same title/body from the
same ticket fields — one place), in whatever pure module S021 ends with; the
Telegram-specific parts (`parse_mode`, `reply_parameters`) stay in
`telegram_notifier.py`. Imports: `telegram_notifier` ← `task_handlers`;
nothing imports `task_handlers` back.

### BR1-13 · minor · The shift-end summary can outgrow a Telegram message

**Problem.** The summary lists one line per ticket. A site that lets closing
slip (the brief's own reason for the list) can have dozens; Telegram cuts a
message at 4096 characters with a 400 ("message is too long") → failed, no
retry.

**Recommended.** At most 10 lines, then "… and N more — see Yantra ›
Tickets › To close", with the link to the filtered list. Test the cut in the
pure tests.

### BR1-14 · nit · Times and cuts in the message text

Say the time shown ("Raised by Ravi at 10:42", "back in service 09:15") is the
event time (`occurred_at`), IST, with the date when it is not today; the
description cut uses S021's 80 characters; the raiser is the ticket's
`reported_by` name, first name only (as § 2 promises).

### BR1-15 · nit · Idempotency note, as S021 has

§ 5.2: a `telegram_send` resent after a timeout may post twice (the message
went but the reply did not) — say so as S021 § 5.1 does for push; the base's
"mark done only on a verified send" is the reason it is accepted.

### BR1-16 · nit · The e2e seed for the banner

"A seeded ticket restored before the last shift end" needs either a
restoration time 8 h or more back (allowed: `MAX_BACKDATE_DAYS` is 7) or the
test setting `shift_ends` to a minute just passed. Say which, since the e2e
backend's clock is real. Also `test_ticket_list` → the file is
`test_tickets_api.py`.

### BR1-17 · nit · Cross-references

S019's brief § Out of scope calls this step "S026"; the index says S023 —
for S019's planner. Banner wording for the floor: "3 tickets fixed in an
earlier shift, not closed yet — Show" reads easier than "back in service
from an earlier shift and not closed".

## Checked and found consistent

- **Against S021 as written:** the kinds (`breakdown` covers the raise and
  the *Machine stopped* regrade; `defect`; `escalation`; test), the audience
  decisions (defects to engineers quietly → not to the group), the
  `ticket_alert` task and its closed check, "push set up" as S021's enqueue
  condition (which § 3 widens to "push or Telegram"), the
  `GET/PUT /api/settings/notifications` pair and its keys, the
  `NotificationsSettings.vue` file, S021 decision 5 (escalation from the
  record time) against this step's decision 6 (shift from the restoration
  time) — opposite choices, each with its reason stated.
- **Plan.MD:** § 4.7's table (new breakdown and escalation → maintenance
  group; Telegram "group-routed, sent from the job queue"); Q12 (list on the
  engineer's view, no approval step); § 1 online-only untouched.
- **Base § Telegram Notification Pattern:** worker send, retry on 5xx,
  `Retry-After` honoured, route by group; the departure (chat ids as settings,
  not `TELEGRAM_GROUPS` in `company_settings.py`) is recorded in decision 1.
  The `threading.Lock` line of the base does not apply (one worker,
  `GET_LOCK`).
- **Job queue code:** `enqueue` in the caller's transaction, `mark_failed` in
  its own after the rollback (a delay parameter fits), `max_attempts` per
  task, `BadTask` → no retry; the handler runs inside the worker transaction,
  so "both or neither are enqueued" (§ 5.1) holds.
- **Shared bot (§ 5.4):** send-only is the right call; `getUpdates` would
  consume the other apps' updates and `setWebhook` would break their polling.
- **Secrets:** `config.py` reads `secrets_app` with `getattr` defaults
  already (`KEYCLOAK_HOST_IP`); an empty-default `TELEGRAM_BOT_TOKEN` follows
  that; `example_secrets_app.py` names the devops template.
- **RBAC:** `settings:read` (manager, IT admin) / `settings:edit` (IT admin)
  as in `config_rbac.py`; `ticket:close` is `maint_engineer` (manager by the
  ladder) and site-scoped — hence BR1-01.
- **Track full** is right: a secret, an outbound call, a migration, a
  scheduler change.
- **Manual checks:** the device rows name account, network and where; the
  automated ones are things a browser can judge; "the other apps still work"
  is rightly the user's.
- **Right-sized:** one small table, stdlib HTTP, no new dependency, no new
  abstraction; the dynamic schedule is the one piece of generality, and it has
  a second real use coming (PM due/overdue in Plan.MD § 4.7).
