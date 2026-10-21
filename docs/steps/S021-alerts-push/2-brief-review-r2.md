```
Step: S021 — Alerts: PWA and web push
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 21-10-2026
```

Reviewed against: 28d3be3 + uncommitted S024

# S021 — Brief review, round 2

**Verdict: one `major` finding is open** (BR2-01: the *down again* send-back,
as written, fires only in the rare case). It changes no decision the user took;
it is a wrong trigger in § 5.3 that the coder would implement as written. The
rest are minor and nits, most of them places where the coder would otherwise
decide alone.

**Round 1.** Every finding marked *Accepted* in the Review log is in the brief
text, not only in the log: BR1-01 (§ 3, § 5.1, decision 9), BR1-02 (§ 3, § 4.2,
§ 8, decision 8), BR1-03 (§ 1.3, § 3, § 8, decision 11), BR1-04 (§ 1.5, § 5.3),
BR1-05 (§ 1.4, § 5.2, § 5.3), BR1-06 (§ 3, § 8), BR1-07 (§ 8), BR1-08 (§ 1.4,
§ 3, § 5.1, § 5.3, decision 10), BR1-09 (§ 1.3, § 6), BR1-10 to BR1-20 as
logged. Checked against the code again: `worker.run_one` / `_task_failed`,
`task_queue.mark_failed`, `task_handlers` (the purge's own commits),
`settings._APP_SETTINGS` / `_validate_app_settings` / `get_setting_int` /
`_save_setting`, `tickets._add_event` (returns nothing today), `_send_back`,
`regrade`, `raise_ticket` with `clean["restore"]`, `tickets_core.MOVES`,
`REGRADE_STATES`, `send_back_intensity`, `ticket_times`, `AppTopbar.vue`,
`stores/auth.js`, `router/index.js`, `navigation.canOpenRoute`, the S024 e2e
stack (`e2e_backend.py`, `playwright.config.js`, `screens.spec.js`), nginx
`location /`.

**Fit with S023** (asked for by the orchestrator). S023 reuses four things of
this brief; all four are specified well enough for both, with the two
wording gaps below (BR2-03, BR2-11):
- **The send-task outcome contract** (§ 5.1, decision 9): `NoRetry`,
  `RetryLater`, "any other exception", the commit-before-raise rule for a
  handler with a row of its own, counted against `max_attempts`,
  `mark_failed(..., delay_seconds=…)`. S023 § 5.2 follows it word for word
  ("no row of its own, so nothing is committed before the raise" is the right
  reading of it). Open: `RetryLater`'s signature is written two ways, and the
  1-hour cap is placed in the push mapping, where S023 cannot reuse it (BR2-03).
- **`alerts_core.py`** channel-neutral (audience, minutes per grade, text,
  `should_escalate`), `push_core.py` push-only: S023 § 3 adds the group text and
  "the kinds that go to the group" to `alerts_core` and imports nothing back.
  Consistent. The ticket facts the text is built from should be named once so
  S023 builds its HTML from the same dict (BR2-11).
- **The settings split** (`_ESCALATION_SETTINGS`, `_validate_int_settings`,
  `escalation_minutes(cur)`, `GET/PUT /api/settings/notifications`): S023 § 3
  extends the same pair with its own dict and a text validator beside it.
  Consistent; the validator's shape and the PUT body's nesting are undecided
  (BR2-02), and S023 inherits whatever is chosen.
- **`ticket_alert`** always enqueued, reads the ticket's site once, carries
  `minutes` for the escalation: S023 § 1.1 and § 5.1 rely on exactly these.
  Consistent.

## Findings

### BR2-01 — `major` — *Down again* fires only when the send-back changes the intensity; the common case sends nothing

**Problem.** § 1.4 and § 5.3 trigger the send-back alert on "`sent_back`
carrying intensity critical". `tickets._send_back` →
`tickets_core.send_back_intensity(current, machine_down)` returns **None when
the ticket is already critical**, and `_send_back` then returns `{}, {}`: the
`sent_back` event carries **no intensity**. So the most common *down again* —
a breakdown that was restored and is down again — writes a `sent_back` with
`intensity NULL`, and the brief's trigger never fires for it. It fires only
for a *defect* restored and then found down (degraded → critical). S018's
downtime does restart in both cases (`ticket_times`: the intensity carries
over from the earlier event, and `sent_back` puts the state back in progress,
a down state), so Yantra would count the machine down while telling nobody.

**Why it matters.** BR1-05 was accepted so the unit's supervisor learns the
machine is down again; as written the coder implements the rare branch and the
test "send back with the machine down → alert only" would be written against
the wrong condition or fail.

**Fix.** The trigger is the move's answer, not the event's intensity: in
§ 5.3, "**send back with *Machine down again?* = yes** (whatever the ticket's
intensity was; the state becomes in progress) → `ticket_alert breakdown`, no
escalation"; in § 1.4 the same words; in § 8 a test for each: a critical
ticket sent back down (no intensity on the event) and a degraded one sent back
down (the event carries critical) both alert; *machine running* sends nothing.
`alerts.py` is called from `_apply_move`'s send-back step with
`clean["machine_down"]`. Nothing else changes: `latest_critical_event_id`
(BR1-12) is unaffected because a send-back never escalates.

### BR2-02 — `minor` — the shared validator's shape and the PUT body's nesting are undecided

**Problem.** § 3 makes `_validate_app_settings` into
`_validate_int_settings(spec, body)` "used by both `/app` and the new pair".
Today it iterates `_APP_SETTINGS` and reads `body[key]` flat
(`{"upload_max_mb": 5}`). § 6 gives the new PUT a **nested** body,
`{"escalate_minutes": {"A": 10, "B": 30, "C": 60}}`, and
`_ESCALATION_SETTINGS` keys by grade (`"A": ("escalate_minutes_a", 10, 5,
1440)`) while `_APP_SETTINGS` keys by setting name with `(default, min, max)`.
One function cannot serve both without the coder choosing the shape, the field
name in the 400 (`escalate_minutes.A`? `A`?), and what a missing or
non-object `escalate_minutes` returns. S023 then adds its two text settings to
the same pair.

**Options.**
1. The validator takes `spec = {field: (minimum, maximum)}` and a dict, returns
   `(clean, errors)` with `field` as the key, as today. `/app` passes
   `{"upload_max_mb": (1, 100)}` and the body; the notifications route passes
   `{"A": (5, 1440), …}` and `body.get("escalate_minutes")` (not a dict → one
   400 on field `escalate_minutes`, "Enter the three times"), and prefixes the
   field errors as `escalate_minutes.A` so the card can show each beside its
   box. Recommended: two lines in § 3 and § 6.
2. A flat PUT body (`escalate_minutes_a` …) and no prefixing. Simpler
   validator, uglier API; S023's `telegram_chats` is nested anyway.

### BR2-03 — `minor` — `RetryLater`'s signature, where the 1-hour cap lives, and `Retry-After` as a date

**Problem.** § 3 writes `RetryLater(after_seconds)`, § 5.1
`RetryLater(message, after_seconds)`, S023 § 5.2 `RetryLater(retry_after)`.
The cap ("capped at 1 hour") is in the push outcome mapping (§ 5.1), so S023's
`telegram_send` would re-implement it or have none. And a `Retry-After`
header may be an HTTP-date, not only seconds (RFC 9110 § 10.2.3).

**Fix.** One signature in § 3, § 5.1 and decision 9: `RetryLater(message,
after_seconds)`, `str(exc)` being what `mark_failed` stores (as
`_task_failed` does for every exception). The cap in **`mark_failed`**:
`delay_seconds` is clamped to a `company_settings.TASK_RETRY_DELAY_MAX_SECONDS
= 3600`, so every send handler gets it; `push_core` only parses. A
`Retry-After` that is not a whole number of seconds counts as absent (the
back-off). `mark_failed` with `delay_seconds` and no attempts left: failed, the
delay ignored — say so, and add it to the `test_task_queue.py` list.

### BR2-04 — `minor` — a late worker sends "Breakdown" for a machine already back in service

**Problem.** § 5.1 has `ticket_alert` skip only a **closed** ticket. The
worker can be down for an hour (`requeue_stale`, a redeploy); when it drains,
a `breakdown` alert for a ticket already **back in service** goes out with its
1-hour TTL, waking the supervisor for a machine that runs. The escalation kind
is safe (`ticket_escalate` re-checked seconds before); `breakdown` and
`defect` are not.

**Fix.** A pure `alerts_core.should_send(kind, state)` beside
`should_escalate`: `breakdown` and `defect` send only while the state is
raised, acknowledged, scheduled (S019) or in progress; `escalation` while not
closed; `test` always. One line in § 5.1 and in the pure tests. (The ticket is
read in the handler already; no extra query.)

### BR2-05 — `minor` — what "on" means, and the bell's dot on devices that will never ring

**Problem.** Two places where the coder would settle a rule alone:
1. § 1.3's state "on" is read "once at start-up from `push.js`" — i.e. from
   the browser. After *Sign out* (§ 1.2) or *Remove* from a desktop (§ 8
   plain), the browser still holds its `PushSubscription` while the server has
   no row: the page would say "on" and the dot stay dark on a phone that gets
   nothing. § 6's `this_device` exists for this but § 1.3 does not use it.
2. The dot shows "while this device is off or blocked", on every screen,
   phone and desktop. An engineer at a desktop PC, a technician (gets nothing
   in this step, § 9 Q3) and IT admin (tests only) carry a dot for ever on a
   device nobody wants to subscribe — a nudge that teaches people to ignore it.

**Fix.**
1. "On" = the browser has a subscription **and** the server lists it as
   `this_device`; otherwise "off" (the page then offers *Turn on*, which
   re-subscribes and upserts). `push.js` reads the browser side, the page
   asks the API; the bell's dot is set from the same answer after `/api/auth/me`
   (one `GET /api/push/subscriptions?endpoint_hash=` at start-up, cheap).
2. The dot only when the person **would get something** (the audience lines
   of BR2-06 are non-empty) and the device is off or blocked. Recommended as
   the smallest rule; a per-device "seen" flag in `localStorage` is the
   alternative (more state, and a reset phone nags again). Desktop keeps the
   dot: an engineer who wants desktop alerts can have them.

### BR2-06 — `minor` — "What you will get" is an audience rule; name the endpoint that gives it

**Problem.** § 1.3 shows the lines "from the person's roles at their sites",
but no route in § 6 returns them. The frontend has `me.sites` (role per site)
and could build them in Vue — the audience per kind and role (§ 5.2) would then
live twice, once in `alerts_core` and once in a `.vue` file (CLAUDE-COMMON:
backend heavy, frontend light).

**Fix.** `GET /api/push/config` returns `{enabled, public_key, you_get:
["Breakdowns and defects at SMTW.MCC2, escalations", …]}`, the lines built by
`alerts_core` from the person's memberships (and "Test messages only — IT
admin holds no site role" / "Nothing yet — ask your engineer" when empty).
One pure function, tested with the audience tests. BR2-05's dot reads the
same field.

### BR2-07 — `minor` — the sender has no timeout

**Problem.** § 5.1 lists "a timeout" among the outcomes, but nothing sets one.
`pywebpush.webpush` passes `timeout` to `requests`, whose default is **no
timeout**: a push service that accepts the connection and never answers holds
the worker's one transaction and the ticket row lock of nothing, but blocks
every other task until the TCP stack gives up.

**Fix.** `push_sender.py` calls `webpush(..., timeout=PUSH_TIMEOUT_SECONDS)`
with the constant in `company_settings.py` (10 s, as S023's Telegram call);
a `requests` timeout or connection error maps to the back-off outcome, as § 5.1
already says. One line in § 3 and § 5.1.

### BR2-08 — `minor` — a user with no Team record meets the rule as a 409 after the tap

**Problem.** § 5.5 gives "You are not in Team — ask IT admin" as a **409 on
subscribe**. On the floor that is: open the page, see *Turn on for this
phone*, tap, answer the browser's permission prompt, then read that it was
never possible. `/api/auth/me` already carries `person_id` (`userPersonId` in
`stores/auth.js`).

**Fix.** The page shows the Team line as its state when `userPersonId` is
null (no *Turn on*, no permission prompt), and the bell shows no dot for such
a user. The 409 stays as the backend's guard. Add the state to § 1.3's list
and to the e2e (a `nobody`-style login with no person is one `X-Test-User`
without a seed row).

### BR2-09 — `nit` — "Settings › Background tasks shows that alerts ran" is not what the card shows

`settings.get_tasks` lists the entries of `SCHEDULE` plus a `failed_count`.
An ad-hoc `ticket_alert` appears there only when it **failed**. Reword § 5.3
and decision 10: "a failed alert shows in the failed count on Settings ›
Background tasks; every alert leaves its `task_queue` row". Adding ad-hoc
types to the card is S023's business if it wants it (its summary task is
scheduled, so it shows anyway).

### BR2-10 — `nit` — the fan-out tests need real membership rows

`tests/harness.py` gives a site role as a **wildcard membership in `g.user`**,
not a `memberships` row; § 5.2's SQL reads the table. Say in § 8 that the
fan-out and audience tests seed `people` + `memberships` (+ `person_units`)
rows for the recipients, and that the acting login is matched through
`X-Test-User` = `people.username`. The e2e seed (`seed_e2e.py`) already has
real rows, so the e2e side is fine.

### BR2-11 — `nit` — whose name is "raised by Ravi"; the ticket facts dict

§ 1.4's body says "raised by Ravi"; S023's message says "Raised by Ravi at
10:42" with "the person is the ticket's *reported by* name, first name only".
`tickets.created_by` is a login; `reported_by_id` is a person. One rule in
`alerts_core`, used by both: the reported-by person's name when set, else the
raiser's Team name, else the login. And name once the dict `ticket_alert`
reads and hands to `alerts_core` (serial, site code, unit code, machine code
and name, component code, intensity, state, symptom label, description cut at
80, the name above, `occurred_at`, `url`), so S023 builds its HTML from the
same input without a second query.

### BR2-12 — `nit` — three wire details the two sides must agree on

- The **private** key's form in `secrets_app.py`: the raw 32-byte P-256
  scalar, base64url without padding (43 characters), as
  `py_vapid.Vapid.from_string` reads and `make_vapid_keys.py` prints; the
  public key's form is already stated (BR1-06).
- `endpoint_hash`: lowercase hex of SHA-256, on both sides (the page's
  `crypto.subtle.digest` → hex; the server's `hashlib`).
- `label` is NOT NULL: "Unknown device" when the user-agent gives nothing.

### BR2-13 — `nit` — two device rows

- "Sign out on the phone, raise a breakdown: that phone gets nothing" names
  no account for the raise; it is a second login (the operator test login, as
  the breakdown row above it).
- iOS and `silent`: the row already asks to note what happens; fine. Add that
  the iPhone row is done **from the Home Screen icon only** (Safari's tab
  shows the explanation, as the row says), so the result is not misread.

### BR2-14 — `nit` — the WebKit e2e asserts the page's rule, not the engine's gap

§ 8 says WebKit shows the Home Screen text because "there is no `PushManager`
outside a Home Screen app". Playwright's WebKit is the desktop engine and may
expose `PushManager`; the page's own rule (§ 1.1) is "an iPhone **not in
standalone mode**" (user-agent + `navigator.standalone` / `display-mode`). Say
the test asserts that rule under the iPhone 14 emulation, whatever the engine
exposes, so it does not break on a Playwright update.

## Checked and found consistent

- **Queue and worker.** `enqueue(cur, …, scheduled_for, max_attempts)`,
  `claim_next` by `scheduled_for`, `mark_done` in the handler's transaction,
  `mark_failed(conn, …)` on its own: the three-transaction shape § 5.1 relies
  on. The purge's `conn.commit()` inside the handler is the precedent for the
  commit-before-raise rule; `db_helpers.transaction` then has nothing to roll
  back. `_task_failed`'s `retry=not isinstance(exc, BadTask)` is the one line
  that grows to the `(BadTask, NoRetry)` tuple plus the `RetryLater` branch.
  Lock order is the same in the request (ticket row, then `task_queue` insert)
  and in `ticket_escalate` (ticket row `FOR UPDATE`, then insert).
- **Tickets.** `raise_ticket` has `clean["restore"]` for *Already fixed*;
  `regrade` runs in one transaction with the locked row and `REGRADE_STATES =
  (raised, acknowledged, in_progress)` (S019 adds scheduled); `_apply_move` is
  the one place a send-back passes, with `clean["machine_down"]` in hand
  (BR2-01). `_add_event` uses `insert_row`, so returning `cur.lastrowid` is a
  one-line change. S025 (not a fault from in progress, no send-back after a
  repeat) changes none of the triggers.
- **Escalation.** `should_escalate` on `state == raised` is right for S019
  (BR1-04); `ticket_events.intensity` is NULL on every event but `raised`,
  `regraded` and a send-back that changes the grade, so "the latest row with
  `intensity = 'critical'`" is well defined. `effective_criticality(own,
  equipment_grade)` exists; the raise reads the machine without its grade, so
  `alerts.py` reads the two grades itself, as § 5.3 says ("read at enqueue
  time").
- **Audience.** `memberships (person_id, site_id, role, all_units)` and
  `person_units (person_id, unit_id)` are the tables; `people.username` the
  login (`current_person_id` normalises it); `it_admin` holds no membership;
  exact-role matching is a deliberate, stated departure from `ROLE_INCLUDES`.
- **RBAC.** `push:subscribe = ('*',)` is global, covered by
  `test_every_role_gets_wildcard_permissions`; `settings:read` (manager, IT
  admin) and `settings:edit` (IT admin) as stated; the `maintenance_team`-only
  user matches no `('*',)` key and never reaches the page.
- **Settings.** `get_setting_int`, `_save_setting` (its INFO line is the audit
  record), `label_base_url`'s default pattern; `/app` and
  `test_settings_api.py` stay as they are once the escalation keys live in their
  own dict (BR1-02); the `(default, minimum, maximum)` tuple is reused.
  `documents.py` and `equipment.py` already import from `settings.py`, so
  `alerts.py` → `settings.escalation_minutes` is the existing direction; the
  worker process importing it pulls Flask, as `task_handlers` already sits
  beside `db_helpers` — no cycle (`settings` imports `task_queue`, never
  `task_handlers`).
- **Frontend.** `AppTopbar.vue` has the name and a logout icon button; the
  bell goes beside them; `/notifications` outside `navItems` passes
  `canOpenRoute`; `stores/auth.logout()` is the one sign-out; `/api/auth/me`
  gives `person_id`. Vite copies `public/` as-is (new folder, fine);
  `127.0.0.1:5177` is a secure context for `serviceWorker` and
  `crypto.subtle`; nginx `location /` serves `/sw.js` and the manifest
  `no-cache`, `/assets/` immutable; a service worker with no `fetch` handler
  leaves the stale-bundle poll untouched.
- **e2e.** `screens.spec.js` is a table of routes per role, so `/notifications`
  for every role is one row; the e2e backend sets `config.*` in-process before
  importing `app`, so generating a VAPID pair there (BR1-06) is the same move
  as `DEV_STUB_ROLE`; no worker runs in the e2e stack, so "Sent to 1 device"
  asserts the count only, as § 8 intends.
- **Standards.** EN 13306 *administrative delay* (part of down time, not of
  active repair time) and SMRP's work-management pillar (emergency work
  dispatched by priority, no response-time metric) are right; ISO 55001 § 6.2
  / § 8.1 (risk-based planning, operational control) and § 7.4 with ISO 9001
  § 7.4 (*Communication*: what, when, to whom, how); ISO/IEC 27001:2022 A 8.24
  (cryptography), A 5.14 (information transfer), A 8.20 (networks security)
  with OWASP's SSRF guidance; RFC 8030 / 8291 / 8292; iOS 16.4 for Home Screen
  push. Maintenance-Philosophy § 9's grade meanings beside A/B/C (BR1-20) are
  quoted correctly.
- **Device checks.** Each important row carries its account, network (mobile
  data or company network) and where (production, TEST machine), matching
  `device-checks.md`'s columns; the `no-cache` header is an after-deploy row
  (BR1-07); nothing on the device list is something a browser could judge,
  except as noted in BR2-13.
- **Track.** Full, as it must be: a migration, a dependency, secrets, an
  outbound call, a timed rule on the queue.
