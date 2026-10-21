```
Step: S023 — Alerts: Telegram and end-of-shift list
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 21-10-2026
```

Reviewed against: 28d3be3 + uncommitted S024

**Verdict: no `blocker` or `major` finding open.** Every round-1 finding marked
`Accepted` is in the brief text, not only in the Review log (checked one by
one, list at the end). The brief now matches S021 as revised: the send-handler
outcome contract (`NoRetry`, `RetryLater(after_seconds)`,
`mark_failed(..., delay_seconds=…)`), `alerts_core.py` as the channel-neutral
module, the `_ESCALATION_SETTINGS` / `_validate_int_settings(spec, body)`
split, "always enqueue" (S021 § 5.3, decision 10), the site read once in
`ticket_alert`, and `minutes` carried into the escalation alert. What is left
are five `minor` points the coder would otherwise settle alone (how two cards
share one PUT, where the worker reads the settings, *Send test* on an unsaved
line and in the e2e stack, the *Down again* case, one device row's network)
and three nits.

Read for this round: the brief; S021's brief as revised after its round 1;
S019 (its `state=` filters) and S025 (the squashed v20, the send-back rule)
where they touch this step; Plan.MD § 4.7 and Q12; Plant-Facts § 2, § 5;
Maintenance-Philosophy § 6; base § Telegram Notification Pattern; the code:
`task_queue.py`, `task_handlers.py`, `scheduled_tasks.py`, `worker.py`,
`settings.py`, `tickets.py`, `tickets_core.py`, `config_rbac.py`,
`auth_utils.user_unit_ids`, `equipment.accessible_unit_ids`, `local_db.py`
(sites, app_settings, tickets, ticket_events), `config.py`,
`example_secrets_app.py`, `company_settings.py`, `TicketsView.vue`,
`utils/ticketLabels.js`, `SettingsView.vue`, `tooling/e2e/e2e_backend.py`,
`frontend/e2e/support/tickets.js`, `tests/test_scheduled_tasks.py`,
`tests/test_worker.py`.

## Findings

### BR2-01 · minor · Two cards, one PUT: what a Save sends is not decided

**Problem.** § 1.3 and § 3 add a *Telegram groups* **card** and a *Shift ends*
**field** to Settings › Notifications; § 6 extends S021's single
`PUT /api/settings/notifications` with `telegram_chats` and `shift_ends`.
S021's validator (`_validate_int_settings`, built on today's
`_validate_app_settings`) refuses a body that lacks a key, so a PUT must carry
`escalate_minutes`, `telegram_chats` and `shift_ends` together. Every other
card on the Settings page is one card = one route pair (`/app`, `/labels`,
`/network`, each with its own Save). A separate Telegram card with its own
Save would have to send the escalation values as they stand in the other card
— and a bad value there fails the Telegram Save with the error shown on the
wrong card. Also unsaid: the PUT body's shape for `telegram_chats` (the GET
returns a list `[{site_id, site_code, chat_id}]`; the field errors are named
`telegram_chats.<site_id>`, which suggests a dict), and what a `site_id` in
the body that is not an active site does.

**Why it matters.** The coder picks one of three layouts; the user sees a
different screen for each.

**Options.**
1. *(Recommended)* **One card, one Save.** S021's Notifications card grows two
   blocks — *Telegram groups* (one line per active site: code, chat id,
   *Send test*) under the escalation times, then *Shift ends* — with the one
   Save at the bottom, and one PUT carrying all keys (as § 6 already says).
   Say so in § 1.3 and § 3 ("block", not "card"). Body shape: `telegram_chats`
   as `{"<site_id>": "<chat_id>"}` (the stored shape; a blank string clears
   the site); an id that is not an active site → 400 on
   `telegram_chats.<site_id>` "Not a site". `shift_ends` as the text typed
   (`"06:00, 14:00, 22:00"`), as `/network` takes its ranges.
2. Its own route pair (`/api/settings/telegram`) and card, like Labels and
   Network — one more pair, but each card saves itself. Fine if preferred;
   then § 6 changes.

### BR2-02 · minor · Where the worker reads the settings from, and the fallback warning every poll

**Problem.** Three worker paths read `app_settings` in this step: `ticket_alert`
(the site's chat id, the label base URL for the link), `shift_end_summary`
(chat ids, shift ends) and `enqueue_scheduled` (shift ends, each poll). The
brief names the settings dict in `settings.py` but not what the worker calls.
Today nothing in the worker imports `settings.py` (only `app.py`,
`documents.py`, `equipment.py` do): it is the Flask blueprint module, and it
pulls `access_control`, `api_common` and `auth_utils` with it. Importing it
from `task_handlers.py` / `worker.py` works (no cycle: `settings` imports
`scheduled_tasks` and `task_queue`, neither imports back; the readers never
touch `g`), but it should be a stated choice, not a discovery.

Second, § 4 says a stored `shift_ends` that no longer parses "falls back with
a warning in the log (the `label_base_url` pattern)". In a request that is one
line; in the worker, which reads it **every poll** (`WORKER_POLL_SECONDS` = 5),
a bad row writes ~17,000 warnings a day until IT admin fixes it.

**Options.**
1. *(Recommended)* State: the worker and handlers import the **read helpers**
   from `settings.py` (`telegram_chats(cur)`, `shift_ends(cur)`,
   `label_base_url(cur)`), and `settings.py` never imports `task_handlers` or
   `worker`. In `enqueue_scheduled`, keep the last raw `shift_ends` text on
   the `Worker` and re-parse (and warn) only when it changes — one SELECT per
   poll stays, the warning fires once per bad value. Test: a bad row logs one
   warning over several polls.
2. A thin `settings_store.py` with only the readers — a new module for three
   functions; not needed at this size.

### BR2-03 · minor · *Send test* on a line not yet saved; and in the e2e stack

**Problem.** The test posts `{site_id}` and the handler reads the **stored**
chat id. The natural flow on the card is: paste the chat id, press *Send test*
— before Save. The admin then gets 409 "No group for this site", which is
true of the database and false of the screen. The brief does not say what
the line does while unsaved.

Also § 8's e2e check "*Send test* shows the queued message and disables the
button briefly": the e2e backend has an empty `TELEGRAM_BOT_TOKEN`, so the
route answers 409 "Telegram is not set up on this server" and the check
cannot pass as written. S021 handles the same for push by having
`tooling/e2e/e2e_backend.py` set its `config.VAPID_*` in-process. The e2e
stack runs **no worker** (`e2e_backend.py`, `playwright.config.js`), so a
dummy token is safe: the task is enqueued and never sent.

**Options.**
1. *(Recommended)* *Send test* is **disabled while the line is unsaved**
   (dirty), with the hint "Save first" beside it; after Save it is enabled.
   The e2e backend sets `config.TELEGRAM_BOT_TOKEN` to a dummy value
   (`"e2e-dummy"`) so the card shows "set up" and the test sees the 202
   message; say in § 8 that nothing is sent because no worker runs there.
2. Let the test post `{site_id, chat_id}` and send to the typed id — tests
   what is typed, but a test to a chat id that was never saved is a stray
   post; rejected.

### BR2-04 · minor · *Down again* goes to the group as a "Breakdown", unsaid

**Problem.** S021 § 1.4 and § 5.3 send a `ticket_alert` of kind **`breakdown`**
for three events: a new breakdown, *Machine stopped* (regrade) and **Down
again** (*Send back* with the machine down, S021 BR1-05). § 1.1's table here
lists the first two under "New breakdown, *Machine stopped*" and not the
third; § 3 keys the group on **kind**, so *Down again* reaches the group
too. Two consequences the brief should state: the message's wording
("🔴 Breakdown … Raised by Ravi at 10:42" names the original raise, not the
send-back), and the `ticket_telegram_messages` upsert replaces the first
breakdown message with the send-back's, which is harmless (a send-back never
escalates, S021 § 5.3) but should be the stated intent.

**Options.**
1. *(Recommended)* Add the row "Down again (send back, machine down) → yes" to
   § 1.1's table, with a first line "🔴 Down again" and the send-back's event
   time and remark's first 80 characters in place of "Raised by … at"; the
   kind stays `breakdown` (the handler reads the triggering event from the
   payload — S021's `ticket_alert` carries no event id, so say the text is
   chosen from the ticket's latest `sent_back` event when it is newer than
   the raise, or add the triggering event to the alert text in S021's
   `alerts_core` — the planner's call, as `alerts_core` is S021's). The
   upsert replacing the message: say it in § 4.
2. Send nothing to the group for *Down again* (the group already saw the
   stop). Simpler; then the table says so and `alerts_core` needs the
   triggering event anyway to tell the two apart.

### BR2-05 · minor · One device row without its network

**Problem.** The first important device row, "IT admin pastes the maintenance
group's chat id for SMTW and presses *Send test*", runs on production too
(§ 8's heading allows either). IT admin is in `INTERNAL_ONLY_ROLES` (S013):
on production the row works only from the **company network**. S021's
equivalent row says so; this one does not (README § Manual checks: a device
check names its account, network and where).

**Recommended.** Add "on the company network (S013) when on production" to
the row, and to the `device-checks.md` row the coder writes.

### BR2-06 · nit · The boundary of "before its shift end", and the row

§ 5.3: "the restoration event time is **before** `last_shift_end`". A ticket
restored at exactly 14:00:00, the shift that ends at 14:00: by decision 6 (the
shift whose people did the work) it belongs to that shift, so the predicate
is `restored_at <= last_shift_end`. Say which; the pure tests list "at an
exact end" for `last_shift_end` but not for the predicate. On the Tickets
page: hide the banner while the State filter is already *To close* (it
would restate the list), and show the date in "Back in service 09:15" when it
is not today, as § 1.1 does for the messages.

### BR2-07 · nit · Two Bot API options worth setting

- The message carries a Yantra link. Telegram shows a **link preview** for
  it, and a Yantra URL without a session previews the Keycloak sign-in page —
  a "Sign in" card under every stop. Send with
  `link_preview_options: {is_disabled: true}` (Bot API 7.0; the older
  `disable_web_page_preview` is superseded), in `telegram_notifier.py` beside
  `parse_mode`.
- The shift-end summary at 06:00 and 22:00 rings every phone in the group.
  The stops are loud on purpose; the list is housekeeping. Consider
  `disable_notification: true` for the summary (and the test message), as
  S021 sends defects quietly. One line in Q4 for the user.

### BR2-08 · nit · Wording and small gaps

- § 5.1 "This step changes nothing in `tickets.py` or `alerts.py`" against
  § 3, which changes `tickets.py` (the `to_close` filter): say "nothing in the
  enqueue path".
- `STATE_FILTERS` lives in `tickets_core.py`, not `tickets.py` (§ 3); the
  frontend has its own list in `utils/ticketLabels.js`, which the coder also
  extends.
- The Background tasks line's next run is the **earliest** of the shift
  entries' `next_run` values (§ 3, `get_tasks`).
- "Raised by Ravi" when the ticket's *reported by* is empty (it is optional):
  say what shows — the raiser's login name, or the line without a name.
- The escalation device row "past the grade's time" can point at S021's row
  that sets grade C of the TEST machine to 5 minutes, so the tester does not
  wait an hour.
- `test_worker.py::test_due_task_enqueued_once_and_run` monkeypatches
  `worker_module.SCHEDULE`; the new scheduler glue should keep that seam (or
  the test changes with it) — note it in § 3 Tests.

## Checked and found consistent

- **Round 1 answers in the text:** BR1-01 (§ 1.2, § 3, § 5.6, § 6, decision 10:
  `accessible_unit_ids(cur, CLOSE_KEY)` plus the read condition; empty → no
  banner; `require_perm(ticket:read)` kept); BR1-02 (§ 3, § 5.3, decision 9:
  each type once per poll, one summary after a gap, the save-sends-now line on
  the card, `get_tasks`); BR1-03 (`reply_parameters` with
  `allow_sending_without_reply`, § 3, § 5.1, tested on the body); BR1-04
  (decision 8, § 5.2 under S021's contract; push off + Telegram on, § 5.1);
  BR1-05 (count route gone, `per_page=1`); BR1-06 (`state=to_close`, the
  row's line, the correlated `MAX`); BR1-07 (solved in S021: `minutes` in
  both payloads, S021 § 5.1); BR1-08 (`DEFAULT_SHIFT_ENDS`, fallback, empty
  refused, `last_shift_end` tolerates `[]`); BR1-09 (the 202 message, button
  disabled); BR1-10 (chat-id rule, sharing allowed, one summary per group,
  Q1); BR1-11 (ISO 14224 clause 6; A 5.17, A 8.15); BR1-12 (`shift_core.py`,
  the text in `alerts_core.py`, import direction); BR1-13 (10 lines, "… and
  N more"); BR1-14, BR1-15, BR1-16, BR1-17 as logged.
- **Against S021 as revised:** the contract's words and the `mark_failed`
  delay (S021 § 3, § 5.1, decision 9) are what § 5.2 uses; "no row of its own,
  nothing committed before the raise" is the right reading of S021's "commit
  the failure record before raising" for a task that has no row; the
  `ticket_alert` payload `{ticket_id, kind, exclude_person_ids, minutes?}` and
  its site read; the kinds (`breakdown`, `defect`, `escalation`) and the
  defect-not-to-the-group decision; `alerts_core.py` (channel-neutral) and
  `push_core.py` (push only); `_ESCALATION_SETTINGS` with its own validator
  call, which § 3 mirrors; `NotificationsSettings.vue`; S021 decision 5 (the
  escalation from the record time) beside decision 6 here (the shift from the
  restoration time), each reasoned.
- **The scheduler rule, re-checked on the code:** with `due_tasks` returning
  each type once, three entries of `shift_end_summary` and `last_enqueued` by
  type give once per end in normal running (06:00 → 14:00 → 22:00 → next
  06:00 each due exactly once), one after a gap over two ends, none twice
  after a restart; a time added earlier than now is due at the next poll, as
  § 5.3 now says. `purge_access_log` keeps the last row per type, so the
  scheduler's read survives the purge.
- **The `to_close` predicate on the code:** `ticket:close` is in `SITE_SCOPED`
  (`user_unit_ids` asserts it); `_visible_condition` is on `t.unit_id OR
  m.unit_id`, the close set goes on `t.unit_id` (the ticket's site is
  `tickets.unit_id`'s site in every write check); `tickets` has no
  `restored_at`, so the correlated `MAX(occurred_at)` over
  `ticket_events.event = 'back_in_service'` is the right source
  (`latest_restoration` is Python over the events); not-a-fault closes, so
  it is excluded by `state = back_in_service`; S019's `scheduled` state is
  excluded the same way; S025's send-back rule does not touch it.
- **Plan.MD:** § 4.7 (new breakdown and escalation → maintenance group;
  group-routed, from the job queue); Q12 (the engineer's view, no approval
  step); § 1 online-only.
- **Standards:** TPM close-within-the-shift; ISO 14224 clause 6; EN 13306
  administrative delay; ISO 55001 § 7.4 and ISO 9001 § 7.4; ISO/IEC
  27001:2022 A 5.14, A 5.17, A 5.18, A 8.15 — all cited correctly and
  explained.
- **Layering:** `shift_core.py` and the text in `alerts_core.py` pure; the
  Bot API in `telegram_notifier.py` only; the route and handlers thin; no new
  abstraction; stdlib HTTP; one small table with a stated reason.
- **Data model:** `chat_id VARCHAR(30)` holds the rule's `-` + 20 digits; PK
  `(ticket_id, kind, chat_id)` with upsert; `shift_ends` 1–6 distinct `HH:MM`;
  the e2e seed's 8-hour-back restoration always crosses one of the default
  ends (the longest gap between them is 8 h) and is within `MAX_BACKDATE_DAYS`.
- **Bot API facts:** `reply_parameters` (7.0), `parameters.retry_after` on
  429, the 4096-character limit, HTML `<b>`, `<i>`, `<a>`.
- **RBAC and screens:** `settings:read` (manager, IT admin) / `settings:edit`
  (IT admin); the banner and filter shown from the union of `ticket:close`
  (`userPermissions`), scoped by the server; a technician sees neither; IT
  admin (token role, every site) sees both; no 403 anywhere.
- **Track full** stands; **manual checks:** the automated ones are things a
  browser judges; the device rows (but BR2-05) name account, network and
  where; "the other apps' use of the bot" rightly the user's.
