```
Step: S023 — Alerts: Telegram and end-of-shift list
Doc: brief
Author: Planner (Opus)
Date: 21-10-2026 (revised 21-10-2026 after brief-reviews r1 and r2, and S021 r3)
Track: full
Status: Parked 21-10-2026 by the user (PWA push alone for now; brief kept for later, after review r2)
```

# S023 — Alerts: Telegram and end-of-shift list

This step adds a maintenance Telegram group as a second channel for S021's
alerts, and a list of tickets left unclosed at the end of a shift. It is the
second half of the old *S021 Alerts*, which the user split on 21-10-2026.
S021 rings individual phones by web push. This step adds:

- **The maintenance Telegram group.** The whole team sees each new breakdown
  and each escalation there. Joining the group is the subscription, so
  nothing needs managing in Yantra (base § Telegram Notification Pattern).
- **The end-of-shift list**: tickets that are back in service but were not
  closed when the shift ended (Plan.MD Q12).

This brief uses S021's terms (S021 § 1): an **alert** is the message, a
**channel** carries it (push, and now Telegram), and **acknowledged** means
the ticket is no longer raised.

User facts and decisions taken before this brief (21-10-2026):
1. **A SMTW Telegram bot already exists**, and other apps use it. **No
   maintenance group** exists yet.
2. The alerts and their recipients are S021's (§ 1 there). This step adds the
   group as a channel for them.

**Track: full.** The step adds a secret and an outbound call from the
worker. It changes the scheduler, and it uses a shared bot that must not be
disturbed (§ 5.4).
**Depends on:** S021 (the `ticket_alert` task and its kinds, Settings ›
Notifications), S013 (job queue, scheduler) and S018 (back in service,
close).
**Coded after S021 is committed.**

## 1. What will be built

1. **Telegram as a second channel for S021's alerts.**
   - The existing bot's token is a secret, `TELEGRAM_BOT_TOKEN`, in
     `secrets_app.py`. An empty value means Telegram is off.
   - **One group per site** is proposed (§ 9 Q1). IT admin sets the groups in
     **Settings › Notifications**, in a *Telegram groups* block of S021's
     Notifications card:
     - The block has one line per active site. IT admin pastes the site's
       group chat id there; a blank line means the site has no group.
     - IT admin saves the card, then presses **Send test**.
     - *Send test* is disabled while the line has unsaved changes, with "Save
       first" beside it, because the test goes to the stored chat id (BR2-03).
     - A site with no group sends nothing to Telegram. Push still works.
     - **Several sites may share one group**: the same chat id on two lines.
       The stock yards and farms of Plant-Facts § 2 will most likely post into
       SMTW's group (BR1-10).
   - What goes to the group (proposed, § 9 Q2):

     | S021 alert (kind) | To the site's group |
     |---|---|
     | New breakdown, *Machine stopped* (`breakdown`) | yes |
     | **Down again**: *Send back* with the machine down (`breakdown`, S021 § 5.3) | yes, headed "🔴 Down again" (BR2-04) |
     | Breakdown not acknowledged in time | yes, as a reply to the breakdown's message |
     | New defect | **no**. Engineers get it quietly by push (S021, user decision 2); the group is for stops |
     | Test | yes, from the *Send test* button |

   - A message reads, for example:
     > 🔴 **Breakdown** · SMTW.MCC2 · VBM001 Vacuum brick machine
     > TK-2026-10-012 · Not building pressure
     > Raised by Ravi at 10:42
     > https://vel-yantra.mspv.app/tickets/412
   - The link is S021's `ticket_facts["url"]`: the label base URL that S014
     holds in Settings › Labels, plus the ticket's path. `ticket_alert` reads
     it once, so the link is right on every instance (S021 § 5.1, BR3-02
     there).
   - Every message goes with the link preview off (`link_preview_options:
     {is_disabled: true}`). Without a session, a Yantra link would preview
     the Keycloak sign-in page under every stop (BR2-07).
   - For **Down again**, the first line is "🔴 Down again". The third line
     gives the send-back's event time and the first 80 characters of its
     remark ("Sent back at 14:05 · Pressure drops again"), in place of "Raised
     by … at". The text comes from S021's `ticket_facts`, which carries the
     event that caused the alert (S021 § 5.1, BR2-04).
   - The escalation goes **as a reply** to the breakdown's message, so the
     group sees one thread per stop: "⏰ Not acknowledged after 10 minutes".
     The minutes come in S021's `ticket_alert` payload, so the text shows the
     value the escalation was scheduled with (BR1-07). Yantra keeps the
     message id of each breakdown's group message for this (§ 4).
   - Times in the messages are the **event time** (`occurred_at`) in IST, with
     the date when it is not today (BR1-14).
   - The description is cut at S021's 80 characters.
   - The name follows S021's rule (S021 § 1.4): the first name of the ticket's
     *reported by* person; without one, the raiser's Team name; without that,
     the raiser's login (BR1-14, BR2-08).
2. **The end-of-shift list** (Plan.MD Q12; TPM practice: close within the
   shift).
   - **Shift ends** are a setting in Settings › Notifications: the times the
     shifts end, in IST, e.g. `06:00, 14:00, 22:00` (proposed, § 9 Q3). This
     step has one list for the whole plant.
   - A ticket is **"not closed after its shift"** when it is back in service,
     not closed, and a shift end has passed since its restoration time. The
     restoration time is the *back in service* event time.
   - **On the Tickets page**, for anyone who can close tickets:
     - The list counts and shows only the tickets **the person may close**.
       Those are at the units where they hold `ticket:close` (site-scoped,
       S011), among the tickets they can read (BR1-01).
     - Someone who can close nowhere sees no banner and no filter.
     - A banner above the list reads: "3 tickets fixed in an earlier shift,
       not closed yet — Show" (BR1-17). It is hidden while the State filter
       already shows *To close* (BR2-06).
     - The existing State filter gains a value, *To close — past shift end*
       (`state=to_close`). It is the dropdown's last entry, as S019 adds
       *Scheduled* and *Overdue* (BR1-06). It shows the oldest restoration
       first.
     - For this filter only, each row shows "Back in service 09:15 · 5 h ago"
       in place of the raise age. It adds the date when it is not today:
       "Back in service 20-10 22:40" (BR2-06).
   - **At each shift end**, the worker posts a short summary to each group,
     only when its sites have such tickets (proposed, § 9 Q4):
     - It sends **one message per group, listing its sites**, so a shared
       group gets one summary, not one per site (BR1-10).
     - It lists at most 10 tickets, then "… and N more — see Yantra › Tickets
       › To close" with the link to the filtered list. So a message never
       passes Telegram's limit of 4096 characters (BR1-13).
     - It is sent **silently** (`disable_notification: true`): the stops
       ring, but the housekeeping list does not (BR2-07, § 9 Q4).
     > 📋 Not closed this shift — SMTW: 3
     > TK-2026-10-009 VBM001 · back in service 09:15
     > …
3. **Settings › Notifications** (S021's one card) gains two **blocks** under
   the escalation times: *Telegram groups* and *Shift ends*.
   - Both need `settings:edit` (IT admin).
   - The card's one Save sends both in its one PUT (S021 § 1.6, BR2-01).
   - The status line says whether Telegram is set up (the token is present).

### Out of scope

- Direct messages to people. The base routes by group, not by user, and push
  already reaches individuals (S021).
- Reading anything from Telegram: no commands, no buttons, no polling and no
  webhook (§ 5.4).
- Shift patterns per site or per unit, and a shift calendar (planned stops,
  holidays). Plant-Facts § 5 has the shift pattern as still to be decided, so
  there is one plant-wide list until it is known.
- An engineer's dashboard page. None exists yet, so the list lives on the
  Tickets page until a dashboard step.
- Email and the daily summary (Plan.MD § 4.7): a later step.
- The devops template change for the token. That edit is the user's (§ 5.5).

## 2. Standards and practice

- **TPM — close within the shift.** TPM's breakdown-maintenance practice asks
  that the failure analysis (cause and action) is written while the people
  who did the work are still on site. By the next shift, memories fade and
  the technician has gone home. The end-of-shift list is the visible nudge
  for that, with no approval step (Plan.MD Q12: "no extra approval step").
- **ISO 14224 clause 6 (quality of data).** It asks that data is collected
  close to the event, by the people who did the work, and that the coding is
  checked. Cause and action coded the same day from the technician's own
  account are more accurate than codes filled in days later. The failure
  history that MTBF and MTTR come from depends on it (BR1-11).
- **EN 13306 and SMRP — administrative delay** (as in S021). The group puts a
  stop in front of everyone, so the stop is seen even when the right person's
  phone is off. The escalation reply shows the whole team a stop that nobody
  took up.
- **ISO 55001 § 7.4 and ISO 9001 § 7.4 (communication).** What is sent, to
  whom and when is written down in § 1.1's table, and it is visible in
  Settings.
- **ISO/IEC 27001:2022:**
  - **A 5.17 (authentication information)**, with the Secrets pattern. The bot
    token is authentication information. It is stored in `secrets_app.py`,
    never in the repo or the page, and it is changed if it leaks.
  - **A 8.15 (logging).** Logs must not expose authentication information,
    so no log line or task error carries the token (§ 5.2, BR1-11).
  - **A 5.14 (information transfer).** Telegram group messages are **not**
    encrypted end to end, unlike web push: Telegram's servers can read them.
    So a message carries only what the team needs: unit, machine, ticket
    number, symptom, the raiser's first name and the link. The link needs a
    Yantra login.
  - **A 5.18 (access rights).** The group's admin decides in Telegram who is
    in the group, outside Yantra. The user should keep the group private
    (invite link off) and remove people who leave, as with any team chat.

## 3. Where

### Backend

- `telegram_notifier.py` (new; base § Telegram Notification Pattern):
  `send(chat_id, html, reply_to=None, silent=False)` over the Bot API's
  `sendMessage`, with the stdlib `urllib.request` — **no new dependency**;
  one place that knows the token. Every message goes with
  `link_preview_options: {is_disabled: true}` (Bot API 7.0; the older
  `disable_web_page_preview` is superseded); `silent` sets
  `disable_notification` (the shift-end summary, BR2-07). The reply uses the Bot API 7.0 form `reply_parameters:
  {message_id, allow_sending_without_reply: true}` (the older
  `reply_to_message_id` is superseded; CLAUDE-COMMON *Deprecation*), so a
  deleted original degrades to a plain message (BR1-03). It returns the
  outcome; `parse_mode` and `reply_parameters` stay here.
- `alerts_core.py` (S021's channel-neutral pure module): the group message
  text and its HTML escaping beside S021's title and body, built from S021's
  **`ticket_facts`** dict with S021's name rule (S021 § 1.4, § 5.1; BR2-04),
  and the kinds that go to the group (BR1-12).
- `shift_core.py` (new, pure): parse and format `shift_ends`,
  `last_shift_end`, "past its shift", the summary's 10-line cut (§ 5.3);
  imported by `settings.py`, `tickets.py`, the handler and the scheduler glue.
  Imports run `telegram_notifier` ← `task_handlers`; nothing imports
  `task_handlers` back (BR1-12).
- `task_handlers.py`:
  - S021's `ticket_alert` also enqueues one `telegram_send` when the kind goes
    to the group and the ticket's site (which S021's handler already reads)
    has a chat id;
  - `telegram_send` `{chat_id, html, ticket_id?, kind, reply_to_kind?,
    silent?}`, under **S021's rules for how a send task reports its
    outcome** (S021 § 5.1:
    `NoRetry(message)`, `RetryLater(message, after_seconds)` with the cap in
    `mark_failed`, any other exception; BR1-04);
  - `shift_end_summary` (no payload): one message per group with tickets to
    close at its sites.
- `scheduled_tasks.py` and `worker.py` (BR1-02): the shift ends are read from
  the settings each poll and become daily entries for `shift_end_summary`; the
  fixed `SCHEDULE` stays as it is; `due_tasks` returns **each task type at most
  once per poll**, so a gap over two shift ends gives one summary (§ 5.3).
  The `Worker` keeps the last raw `shift_ends` text and re-parses it, and
  logs a bad value, **only when the text changes**: one SELECT per poll
  stays, and a bad row logs one warning, not one every 5 seconds (BR2-02).
  The worker still reads the fixed list through `worker_module.SCHEDULE`, so
  `test_worker.py::test_due_task_enqueued_once_and_run` keeps its
  monkeypatch seam (BR2-08).
- `settings.py`: `telegram_chats` (site id → chat id) and `shift_ends`, in
  their own settings dict, with a text validator for each beside S021's
  `_validate_int_settings` (S021 § 3: the same `(clean, errors)` result, the
  errors prefixed by field, `telegram_chats.<site_id>`, BR2-01). The **read
  helpers** `telegram_chats(cur)` and `shift_ends(cur)` are what the worker
  and the handlers import from `settings.py`. `label_base_url(cur)` is
  imported only by `shift_end_summary`, for its link to the filtered list;
  the alert messages take the link from S021's `ticket_facts["url"]`, with no
  second read (S021 BR3-02);
  `settings.py` never imports `task_handlers` or `worker`, so there is no
  cycle (BR2-02);
  `DEFAULT_SHIFT_ENDS = "06:00,14:00,22:00"` in code, like
  `DEFAULT_LABEL_BASE_URL`; `GET/PUT /api/settings/notifications` (S021)
  extended; `POST /api/settings/notifications/telegram-test` `{site_id}`;
  `get_tasks` (the Background tasks card) adds one line "Shift-end summary ·
  06:00, 14:00, 22:00" with its next run, the **earliest** of the entries'
  next runs (BR1-02, BR2-08).
- `tickets_core.py`: `to_close` joins `STATE_FILTERS` (BR2-08).
- `tickets.py`: with `to_close`, the list adds the
  close predicate (`accessible_unit_ids(cur, CLOSE_KEY)`, on top of the read
  condition) and the restoration time (the latest `back_in_service` event's
  `occurred_at`, a correlated `MAX`, since `tickets` has no `restored_at`).
  The banner reads the list's `total` with `per_page=1`; no count route
  (BR1-01, BR1-05, BR1-06).
- `config.py`, `example_secrets_app.py`: `TELEGRAM_BOT_TOKEN` (empty default
  = off); the field name for the devops template in the impl report.
- `tooling/e2e/e2e_backend.py`: sets `config.TELEGRAM_BOT_TOKEN` to a dummy
  value (`"e2e-dummy"`) in-process, as S021 does for its VAPID keys, so the
  card shows "set up" and *Send test* answers 202. No worker runs in the e2e
  stack, so nothing is ever sent (BR2-03).
- `local_db.py`: the next migration — `ticket_telegram_messages` (§ 4).

### Frontend

- `views/settings/NotificationsSettings.vue` (S021's card): the *Telegram
  groups* block (a chat id per site, *Send test* per line, disabled with
  "Save first" while the line is unsaved) and the *Shift ends* block, under
  the card's one Save (BR2-01, BR2-03).
- `views/TicketsView.vue`: the banner (hidden while the filter is already
  *To close*) and the *To close — past shift end* State value, shown to
  `ticket:close` holders; the row's "Back in service …" line for that filter.
  `utils/ticketLabels.js` gains the filter's label (BR2-06, BR2-08).
- *Send test* on 202 shows "Sent to the queue — it should appear in the group
  within a few seconds. If it doesn't, see Background tasks below.", and the
  button is disabled for a few seconds (BR1-09).

### Tests

- `test_telegram.py` (the notifier with a fake opener: success, 429 with
  `retry_after`, 400 chat not found, 403 bot removed from the group, 5xx,
  timeout; the request body carries `reply_parameters` with
  `allow_sending_without_reply`; the token never in a log line or task error),
  `test_alerts.py` (fan-out adds the group message; defect does not;
  escalation replies), `test_shift_core.py` (pure), `test_tickets_api.py`
  additions (BR1-16), settings tests, scheduler tests for the dynamic entries.
- e2e: Settings › Notifications cards; the Tickets banner and filter with
  seeded tickets (§ 8).

### Docs

- `.claude/CLAUDE.md`: the *Notifications* bullet gains Telegram (shared bot,
  send-only) and the shift ends.
- `docs/Plan.MD` § 4.7 and Q12 (decided); `docs/Plant-Facts.md` § 5 the
  shift ends once the user gives them.

## 4. Data model (the next free migration version when coded)

`ticket_telegram_messages` — where each ticket's group message went, so the
escalation can reply to it:

| Column | Type | Notes |
|---|---|---|
| `ticket_id` | INT NOT NULL | FK `tickets.id` |
| `kind` | VARCHAR(20) NOT NULL | `breakdown` |
| `chat_id` | VARCHAR(30) NOT NULL | the group it went to |
| `message_id` | BIGINT NOT NULL | Telegram's id of the message |
| `sent_at` | DATETIME NOT NULL | |

PK `(ticket_id, kind, chat_id)`. A later `breakdown` message for the same
ticket and group **replaces** the stored one (upsert): a regrade or a *Down
again* is the newest message about the stop, and an escalation never follows
a *Down again* (S021 § 5.3), so nothing replies to the old one (BR2-04).

Settings (`app_settings`, no schema change):
- `telegram_chats` — JSON `{"<site_id>": "<chat_id>"}`, the same shape the
  PUT takes (§ 6). A chat id is an
  optional `-` then 1 to 20 ASCII digits (supergroups are `-100…`, basic
  groups a shorter negative number), stored as text; blank means no group;
  the same chat id is allowed on several sites (BR1-10).
- `shift_ends` — text `"06:00,14:00,22:00"`, 1 to 6 times, `HH:MM`, distinct.
  With no row (a first install, the e2e database) the code default
  `DEFAULT_SHIFT_ENDS` applies (placeholder until § 9 Q3); a stored value that
  no longer parses falls back to it with a warning in the log (the
  `label_base_url` pattern), logged once per bad value in the worker (§ 3,
  BR2-02); the field refuses empty with "Enter at least one
  time, e.g. 06:00". `last_shift_end` tolerates an empty list (returns None:
  nothing is past its shift), so a bad row can never raise (BR1-08).

## 5. Rules

### 5.1 What is sent, and when

- S021's `ticket_alert` decides, per kind, the push fan-out **and** the group
  message, in the same worker transaction, so both or neither are enqueued.
- The group message for an escalation is sent with `reply_parameters` naming
  the stored breakdown message for that ticket and chat, and
  `allow_sending_without_reply: true`; when none is stored (the breakdown
  message failed, or the group was set after), it is sent as a plain message.
- **Telegram is on for a site** when the token is set and the site has a chat
  id. S021 enqueues the alerts **always** (S021 § 5.3); its `ticket_alert`
  finds the channels, so with push off and Telegram on it fans out no
  `push_send` and one `telegram_send` (BR1-04). This step changes nothing in
  the enqueue path (`alerts.py`, and the ticket moves in `tickets.py`); its
  only `tickets.py` change is the `to_close` filter (BR2-08).

### 5.2 Sending (`telegram_send`)

`max_attempts = 3`, under S021's rules for how a send task reports its outcome
(S021 § 5.1).
Bot API outcomes:
- `ok: true`: done; for a breakdown, store `message_id` (§ 4);
- **429** with `parameters.retry_after`: `RetryLater(message, retry_after)` —
  retried after that many seconds, not the fixed back-off, capped at 1 hour by
  `mark_failed` (S021 § 3, BR2-03 there);
- **5xx**, a timeout (10 s) or a connection error: an ordinary exception —
  retried with the existing back-off;
- **400** (chat not found, bad HTML) or **403** (bot removed from the group,
  or blocked): `NoRetry` — failed at once; the error is kept on the task and
  shown in Settings › Background tasks (S013) as for any failed task. There is
  no row of its own to record it on, so nothing is committed before the raise.

A `telegram_send` retried after a timeout may post twice (the message went,
the reply did not): accepted, as S021 accepts it for push, since the base's
"mark done only on a verified send" is what makes the retry safe otherwise
(BR1-15).

The token is part of the API URL, so **no URL is ever logged**: errors are
logged and stored as "Telegram: <description from the API>" only.

The HTML uses only `<b>`, `<i>` and links; every value from the database
(machine name, symptom, description, person) is HTML-escaped first.

### 5.3 Shift ends

Pure functions, IST, naive datetimes as S013's scheduler:
- `last_shift_end(now, ends)`: the latest shift end at or before `now`
  (yesterday's last one when `now` is before today's first);
- **not closed after its shift**: state `back_in_service` and the restoration
  event time is **at or before** `last_shift_end(now, ends)` (`<=`). A ticket
  restored at exactly 14:00:00 belongs to the shift that ends at 14:00, the
  shift whose people did the work (decision 6, BR2-06);
- the scheduler treats each shift end as a daily entry
  `("shift_end_summary", "HH:MM")`. S013's `due_tasks` keys the last run by
  **task type** and returns the type once per due entry, so three entries of
  one type could be due together; this step makes `due_tasks` return **each
  type at most once per poll** (BR1-02). The rules that follow:
  - once per shift end in normal running;
  - **after a worker gap, one summary**, not one per missed end — the list at
    that moment is the same list;
  - never twice after a restart (S013's rule, unchanged);
  - **a changed setting**: a newly added time earlier than now, after the last
    summary, is due at the next poll, so saving it sends a summary at once.
    Accepted and said on the card: "Saving a time earlier than now sends a
    summary at once."
  The entries also show on Settings › Background tasks (`get_tasks`), so an
  overdue summary is visible there.

### 5.4 The shared bot

The bot also serves other SMTW apps. Yantra therefore **only sends**: it never
calls `getUpdates`, never sets or deletes a webhook, and never changes the
bot's name, commands or settings — any of these would take updates away from,
or break, the other apps. The chat id is found outside Yantra (e.g. adding a
helper bot to the group, or from the other app's logs) and pasted in; *Send
test* proves it. The impl report gives the steps.

### 5.5 Secrets and set-up

- `TELEGRAM_BOT_TOKEN` in `secrets_app.py` (dev and test: empty, or a separate
  test bot; never the production bot on a laptop without the user's say).
- The impl report gives the field name and placeholder line for
  `smtw_erp_devops/erp_server/yantra/secrets_app.py.j2`; the user adds it (the
  same bot token the other apps already hold in the devops vault).
- The worker needs outbound HTTPS to `api.telegram.org` (§ 9 Q5).

### 5.6 Who may do what

- Telegram groups, shift ends, *Send test*: `settings:edit` (IT admin); read:
  `settings:read` (manager, IT admin). A chat id is not a secret, but it lets
  anyone holding the token post there, so it is shown only in Settings.
- The banner and the filter: the tickets the person may close, at the units
  where they hold `ticket:close` (`accessible_unit_ids(cur, CLOSE_KEY)`; the
  key is site-scoped), and may read. An empty close set gives an empty result
  and no banner — the control hidden, never a 403. The list route keeps
  `require_perm(ticket:read)` and adds the close predicate only for
  `state=to_close` (BR1-01).

## 6. API

| Method and path | Key | Does |
|---|---|---|
| `GET /api/settings/notifications` | `settings:read` | S021's body plus `telegram_enabled`, `telegram_chats: [{site_id, site_code, chat_id}]`, `shift_ends: ["06:00", …]` |
| `PUT /api/settings/notifications` | `settings:edit` | One PUT for the whole card (BR2-01): S021's body plus `telegram_chats: {"<site_id>": "<chat_id>"}` (a blank string clears the site; an id that is not an active site → 400 on `telegram_chats.<site_id>`, "Not a site") and `shift_ends` as the text typed, `"06:00, 14:00, 22:00"`, as `/network` takes its ranges; field errors `telegram_chats.<site_id>`, `shift_ends` |
| `POST /api/settings/notifications/telegram-test` | `settings:edit` | `{site_id}` → enqueue a test message; 409 "Telegram is not set up on this server" / "No group for this site" |
| `GET /api/tickets/?state=to_close` | `ticket:read`, filtered by where the person holds `ticket:close` | the existing list, oldest restoration first, each row with `restored_at`; the banner calls it with `per_page=1` and reads `total` |

## 7. Design decisions

1. **One group per site, with chat ids as settings** (proposed). Sites are
   data in Yantra, created by IT admin, so their groups are data too.
   *Rejected:* the base's `TELEGRAM_GROUPS` dict in `company_settings.py`
   (every new site or group would need a release; this is a recorded
   departure from the base); one plant-wide group (SSVT's and the farms'
   stops would land in SMTW's chat, § 9 Q1).
2. **Send-only on the shared bot** (§ 5.4). *Rejected:* a new bot for Yantra
   alone (cleaner, and free to read updates later, but one more token to
   manage, and the user said a bot exists; it stays an option, § 9 Q6);
   finding the chat id with `getUpdates` (it would take the other apps'
   updates away from them).
3. **The escalation as a reply** to the breakdown's message, so each stop has
   one thread. It costs one small table. *Rejected:* a separate message (the
   group cannot see at a glance which stop it is about).
4. **The end-of-shift list on the Tickets page**, with a banner. No dashboard
   exists, and a page of its own for one list is premature. *Rejected:* a
   dashboard page now (it is its own step, Plan.MD § 6); a push to engineers
   at shift end (a nag for each person, while the group summary reaches the
   team once).
5. **Shift ends as one plant-wide list** until the shift pattern is known
   (Plant-Facts § 5: still to be decided). *Rejected:* per site or per unit
   now. The facts are not in yet, and the setting can become per site later
   without changing the rule.
6. **The restoration time decides the shift, not the time it was recorded.**
   A ticket restored at 13:50 and recorded at 14:10 belongs to the shift that
   ended at 14:00. That is the shift whose people did the work. *Rejected:*
   the time of the *back in service* entry (late recording would hide the
   delay).
7. **Stdlib HTTP for the Bot API**, so no new dependency: it is one POST with
   JSON. *Rejected:* `python-telegram-bot` (a large framework for one call);
   `requests` (fine, but not needed).
8. **S021's rules for how a send task reports its outcome, not a second set**
   (BR1-04): `RetryLater` for a 429, `NoRetry` for a 400 or 403. *Rejected:* a
   status returned by the task (it changes `run_task`'s contract for every
   task).
9. **One shift-end task type, returned once per poll** (BR1-02). *Rejected:*
   one task type per shift end (`shift_end_summary_1/2/3`). That leaves S013's
   code untouched, but the slot number leaks into the queue and the card.
10. **The to-close list as a State value, scoped by `ticket:close`** (BR1-01,
    BR1-05, BR1-06). *Rejected:* the read scope with a disabled close on the
    row (more screen, same confusion); a separate `to_close` parameter and a
    count route (two mechanisms for one dropdown, and a second path for
    visibility).
11. **The minutes in the group message come from the payload** (BR1-07),
    which S021 carries. *Rejected:* wording without the number (the reader
    would have to count).

## 8. Tests and acceptance

### Pure (`test_shift_core.py`, alerts core)
- `last_shift_end` across midnight, at an exact end, before the first end of
  the day, one end only;
- "not closed after its shift": restored before / after the last end, and
  **exactly at** it (counts, `<=`, BR2-06); closed → no; still in progress →
  no;
- the group message: escaping of `<`, `&`, quotes in names and symptoms;
  description cut; each kind's text, *Down again* with the send-back's time
  and remark; the name rule with *reported by* empty (the raiser's Team name,
  then the login, BR2-08); the defect kind goes nowhere;
- the summary: one message per group listing its sites; the 10-line cut with
  "… and N more"; `shift_ends` parsing, the default, a bad stored value, an
  empty list.

### API and tasks
- the notifier: success stores `message_id`; 429 retries after
  `retry_after`; 400 and 403 fail without retry; 5xx and timeout retry; the
  token is absent from every log line and task error (asserted on the
  captured log and the row); every body carries `link_preview_options`; the
  summary carries `disable_notification` (BR2-07);
- fan-out: a breakdown at a site with a group enqueues push sends and one
  `telegram_send`; a site without a group only push; Telegram on and push off
  still enqueues; escalation replies to the stored message, or plain when none;
  a *Down again* goes to the group and replaces the stored message (BR2-04);
- shift summary: one message per group with tickets to close, none when zero;
  enqueued once per shift end; **one** after a worker gap over two ends; not
  twice after a restart; the entries appear in `get_tasks` with the earliest
  next run; a bad stored `shift_ends` logs one warning over several polls
  (BR2-02);
- settings: chat ids per active site, the chat-id rule (a letter, 21 digits,
  `--1` refused; the same id on two sites allowed), shift ends parsed and
  validated (bad time, duplicates, more than 6, empty); a site id that is not
  an active site → 400; a body without `escalate_minutes` → 400 (one PUT for
  the card); test message 409s; `PUT /api/settings/app` unchanged;
- the `to_close` filter: an engineer at SMTW who is a supervisor at BRICKS sees
  SMTW's tickets only; someone with no close site gets an empty list; the row
  carries `restored_at`.

### Automated (e2e)
- Settings › Notifications as IT admin: a chat id per site saves; shift ends
  `06:00, 14:00, 22:00` saves and stays after reload; `25:00` is refused on the
  field; the manager sees them read-only.
- Tickets page as an engineer with a seeded ticket restored before the last
  shift end: the banner shows the count; *Show* filters to it; a technician
  sees no banner. The seed restores the ticket **8 hours back** (allowed:
  `MAX_BACKDATE_DAYS` is 7), so with the default shift ends a shift end has
  passed whatever the e2e clock says (BR1-16).
- *Send test* is disabled with "Save first" while the line is unsaved; after
  Save it shows the queued message and disables the button briefly. The e2e
  backend's dummy token makes the route answer 202; no worker runs there, so
  nothing is sent (BR2-03).
- The banner is hidden once *Show* has set the filter to *To close*
  (BR2-06).

### On a real device
Telegram needs only outbound internet, so these can run on **the dev server on
KLA's laptop with a test group**, or on **production** after the release.

Important:
- [ ] IT admin pastes the maintenance group's chat id for SMTW, saves, and
  presses *Send test*: the test message appears in the group. On production
  this runs from the **company network** (S013: IT admin works only from the
  plant network); on the dev server, from KLA's laptop (BR2-05).
- [ ] An operator raises a **breakdown** on the TEST machine: the group gets
  the message within a minute; its link opens the ticket after login.
- [ ] Leave it unacknowledged past the grade's time: the group gets "Not
  acknowledged" **as a reply** to the breakdown's message. To avoid an hour's
  wait, use S021's device row that sets grade C (the TEST machine's) to 5
  minutes first (BR2-08).
- [ ] The **other apps' use of the bot still works** after Yantra has sent
  (the user checks one of them).

Plain:
- A defect raised: nothing in the group.
- At a shift end with a ticket back in service and not closed: the summary
  appears in the group.

### Acceptance
`tooling/run-tests.bat` green; `tooling/run-e2e-tests.bat` green; `npx vite
build` with no new errors; no new dependency.

## 9. Open questions and assumptions

1. **One group per site, or one for all?** Proposed: **one per site, with
   sharing allowed**. Each site's line takes a chat id, and blank means no
   group. Several sites may name the same group, e.g. the stock yards and
   farms in SMTW's group, and SSVT in its own.
   - Alternative: one group for every site. It is simpler, and everyone sees
     every site's stops.
   - Which sites get their own group?
2. **What goes to the group?** Proposed: breakdowns and escalations, **not
   defects**.
   - Alternative: defects too, sent silently (`disable_notification`), so the
     group sees the backlog grow.
3. **Shift ends.** Proposed: `06:00, 14:00, 22:00` IST, as a placeholder.
   What are the real times? Plant-Facts § 5 has the shift pattern as still to
   be decided. Are they the same at every site?
4. **The shift-end summary in the group.** Proposed: yes, only when there is
   something to close, and **sent silently**, so it does not ring every phone
   at 06:00 and 22:00 (BR2-07).
   - Alternative: send it with sound.
   - Alternative: no summary; the Tickets banner only.
5. **Assumption: outbound network.** The worker container can reach
   `api.telegram.org` over HTTPS, as the other apps' containers do.
6. **The bot.** Proposed: reuse the existing bot, send-only (§ 5.4). Which
   bot is it (its username), and may Yantra post as it? A bot for Yantra alone
   is the alternative, if the other apps' owners object.
7. **Order.** This step is coded after S021 is committed. It reuses S021's
   task, its Notifications card and its alert kinds.

## 10. Amendments

(none)

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 21-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR1-01 the end-of-shift list is scoped by `ticket:read` | major | **Accepted** (option 1): the tickets the person may close, `accessible_unit_ids(cur, CLOSE_KEY)` plus the read condition; empty → no banner, never a 403 (§ 1.2, § 3, § 5.6, § 6, decision 10) |
| BR1-02 three shift ends on one task type | major | **Accepted** (option 1): `due_tasks` returns each type once per poll; one summary after a gap; a time added earlier than now sends at once, said on the card; the entries shown in `get_tasks` (§ 3, § 5.3, decision 9) |
| BR1-03 a reply to a deleted message fails for good | minor | **Accepted** (option 1): `reply_parameters` with `allow_sending_without_reply`; tested on the request body (§ 3, § 5.1) |
| BR1-04 how "retry after N s" and "no retry" reach the worker | minor | **Accepted**: S021 now defines one contract (`NoRetry`, `RetryLater(after_seconds)`, `mark_failed(delay_seconds=…)`), which this step uses; S021 always enqueues, so push off + Telegram on fans out no push send (§ 3, § 5.1, § 5.2, decision 8) |
| BR1-05 the count route duplicates `total` | minor | **Accepted**: route dropped; the banner reads `total` with `per_page=1` (§ 3, § 6) |
| BR1-06 the filter as a separate parameter; what a row shows | minor | **Accepted**: `state=to_close` in `STATE_FILTERS`; the row shows "Back in service 09:15 · 5 h ago"; the restoration time from the latest `back_in_service` event (§ 1.2, § 3, § 6) |
| BR1-07 the minutes are not in the task | minor | **Rejected the rewording**, solved at the source instead: S021 (its BR1-08) carries `minutes` in `ticket_escalate` and the escalation's `ticket_alert` payload, so the text keeps the number (§ 1.1, decision 11) |
| BR1-08 `shift_ends` default and empty case | minor | **Accepted**: `DEFAULT_SHIFT_ENDS` in code, fallback with a warning, empty refused, `last_shift_end` tolerates an empty list (§ 3, § 4) |
| BR1-09 *Send test* shows nothing | minor | **Accepted**: the queued message and a briefly disabled button; the send stays in the worker (no departure from the base) (§ 3, § 8) |
| BR1-10 chat-id rule; shared groups | minor | **Accepted**: the rule in § 4; the same chat id allowed on several sites; one summary per group listing its sites; Q1 now asks which sites get their own group (§ 1.1, § 1.2, § 4, § 9 Q1) |
| BR1-11 standards citations | minor | **Accepted**: ISO 14224 clause 6; A 5.17 and A 8.15 for the token in place of A 8.24 (§ 2) |
| BR1-12 where the pure functions live | minor | **Accepted**: `shift_core.py`; the group text in S021's `alerts_core.py`; Telegram specifics in `telegram_notifier.py`; the import direction stated (§ 3) |
| BR1-13 the summary can outgrow a message | minor | **Accepted**: at most 10 lines, then "… and N more" with the link; tested (§ 1.2, § 8) |
| BR1-14 times and cuts in the text | nit | **Accepted**: event time, IST, date when not today; 80 characters; reported-by first name (§ 1.1) |
| BR1-15 idempotency note | nit | **Accepted** (§ 5.2) |
| BR1-16 the e2e seed; the test file name | nit | **Accepted**: restored 8 hours back; `test_tickets_api.py` (§ 3, § 8) |
| BR1-17 cross-references; banner wording | nit | **Accepted** the wording (§ 1.2). S019's "S026" is for S019's planner (its brief is revised separately) |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 21-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR2-01 two cards, one PUT | minor | **Accepted** (option 1): one card, one Save, one PUT. The Telegram groups and shift ends are blocks of S021's Notifications card; `telegram_chats` as `{"<site_id>": "<chat_id>"}` (blank clears; a non-site → 400 "Not a site"); `shift_ends` as the text typed. Settled in S021 § 1.6, § 3 and § 6 and referenced here (§ 1.1, § 1.3, § 3, § 6) |
| BR2-02 where the worker reads the settings; the warning every poll | minor | **Accepted** (option 1): the worker and handlers import the read helpers from `settings.py`, which never imports them back; the `Worker` re-parses and warns only when the raw text changes; a test (§ 3, § 4, § 8) |
| BR2-03 *Send test* on an unsaved line; the e2e token | minor | **Accepted** (option 1): disabled with "Save first" while unsaved; the e2e backend sets a dummy token, and nothing is sent since no worker runs there (§ 1.1, § 3, § 8) |
| BR2-04 *Down again* goes to the group, unsaid | minor | **Accepted** (option 1): a table row; headed "🔴 Down again" with the send-back's time and remark. The text comes from S021's `ticket_facts`, which now carries the causing event (S021 BR2-01); the upsert replacing the stored message is stated (§ 1.1, § 3, § 4, § 8) |
| BR2-05 the *Send test* device row has no network | minor | **Accepted**: the company network on production (§ 8) |
| BR2-06 the boundary at a shift end; the banner and the row | nit | **Accepted**: `<=`, tested; the banner hidden on the *To close* filter; the date in the row when not today (§ 1.2, § 5.3, § 8) |
| BR2-07 link preview; a silent summary | nit | **Accepted**: the link preview off on every message; the summary sent silently, and a line in § 9 Q4. The test message keeps its sound, since it proves the group rings (§ 1.1, § 1.2, § 3, § 8, § 9) |
| BR2-08 wording and small gaps | nit | **Accepted**, all six: "nothing in the enqueue path"; `STATE_FILTERS` in `tickets_core.py` and the label in `ticketLabels.js`; the card's next run is the earliest; the name rule when *reported by* is empty (S021's rule); the escalation row points at S021's 5-minute row; the `SCHEDULE` seam kept for `test_worker.py` (§ 1.1, § 3, § 5.1, § 8) |

### From S021 r3 — `S021-alerts-push/2-brief-review-r3.md` (Fable), applied 21-10-2026

| Finding | Severity | Answer |
|---|---|---|
| S021 BR3-02 `ticket_facts["url"]` read two ways | minor | **Accepted**: the alert messages use S021's `ticket_facts["url"]`, which `ticket_alert` builds once from the label base URL; `label_base_url(cur)` stays only for the shift-end summary's link (§ 1.1, § 3) |
| S021 BR3-15 "settings tab" in § 9 Q7 | nit | **Accepted**: "Notifications card" (§ 9 Q7) |
| S021 BR3-09 writing style (asked for this brief too) | minor | **Accepted**: the gate-A sections (§ 1, Out of scope, § 2, § 7, § 9) rewritten to scope A, one idea per sentence and lists for parallel facts; S021's terms adopted (*alert*, *channel*, *acknowledged*); "send-handler outcome contract" became "S021's rules for how a send task reports its outcome" (§ 3, § 5.2, decision 8). No content changed |

### U1 — user decision, 21-10-2026: parked

"lets not do telegram now. keep the brief written, for later. for now, its PWA
alone". The team mostly uses Samsung Galaxy phones, and the user an iPhone; on
those, push through Chrome and the Home Screen app is expected to be enough.
The whole brief is parked, the end-of-shift list included. Before it is taken
up again: run a staleness check against S021 as committed, and decide whether
the end-of-shift list goes ahead without the Telegram group.

