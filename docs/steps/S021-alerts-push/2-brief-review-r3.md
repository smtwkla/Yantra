```
Step: S021 — Alerts: PWA and web push
Doc: brief-review r3
Author: Brief reviewer (Fable)
Date: 21-10-2026
```

Reviewed against: 28d3be3 + uncommitted S024

# S021 — Brief review, round 3

**Verdict: no `blocker` or `major` finding is open.** The brief can go to
gate A once the minors below are answered. None of them changes a decision the
user took; each is a rule the coder would otherwise settle alone, or a place
where the brief contradicts itself.

**Round 2.** Every finding marked *Accepted* in the Review log is in the brief
text: BR2-01 (§ 1.4 table and bullet, § 3 `tickets.py`, § 5.1 `event_id`,
§ 5.3, § 8 two tests), BR2-02 (§ 3 `settings.py`, § 6), BR2-03 (§ 3
`task_queue.py`, § 5.1 one signature, § 8), BR2-04 (§ 3, § 5.1 `should_send`,
§ 8), BR2-05 (§ 1.3 on/off, § 3, decision 11, § 8), BR2-06 (§ 1.3, § 3, § 6,
§ 8), BR2-07 (§ 3 `push_sender.py`, § 5.1, § 8), BR2-08 (§ 1.3 *not in Team*,
§ 5.5, § 8), BR2-09 to BR2-14 as logged.

**Code read again this round:** `worker.py` (`run_one`, `_task_failed`),
`task_queue.py` (`mark_failed`, `enqueue`), `task_handlers.py` (`BadTask`, the
purge's own commits), `settings.py` (`_APP_SETTINGS`, `_validate_app_settings`,
`get_setting_int`, `_save_setting`, the label and network routes),
`tickets.py` (`raise_ticket`, `_add_event`, `_apply_move`, `_send_back`,
`regrade`, `_lock_ticket`), `tickets_core.py` (`MOVES`, `REGRADE_STATES`,
`send_back_intensity`, `ticket_times`), `config_rbac.py`, `auth_utils.py`
(`current_person_id`, `('*',)` handling in `access_core.compute_permissions`),
`config.py`, `example_secrets_app.py`, `company_settings.py`, `app.py`
(`/api/auth/me`), `local_db.py` (`ticket_events`, `app_settings`,
`task_queue`), `AppTopbar.vue`, `App.vue`, `stores/auth.js`,
`router/index.js`, `stores/navigation.js`, `SettingsView.vue`, `index.html`,
`vite.config.js`, nginx `location /`, `Dockerfile.frontend`, the S024 e2e
stack (`e2e_backend.py`, `seed_e2e.py`, `support/people.js`,
`screens.spec.js`, `playwright.config.js`), `tests/harness.py`,
`test_settings_api.py`, `test_worker.py`, `test_task_queue.py`,
`device-checks.md`; Plan.MD § 4.7 and Q2; Maintenance-Philosophy § 6, § 9,
§ 10, § 11; Plant-Facts § 4, § 5; the base's Job queue, Telegram, Secrets,
Stale bundle and Topbar sections; the S019, S020, S025 briefs.

## Fit with S023 (asked for by the orchestrator)

S023's brief references nine things of S021. Each matches what S021 says:

| S023 reference | S021 text | Match |
|---|---|---|
| The send-handler outcome contract: `NoRetry(message)`, `RetryLater(message, after_seconds)`, the cap in `mark_failed`, any other exception (S023 § 3, § 5.2, decision 8) | § 3 `task_handlers.py` / `task_queue.py`, § 5.1, decision 9 | yes |
| "No row of its own, so nothing is committed before the raise" (S023 § 5.2) | § 5.1: the failure record is "the only write it makes before the raise" | yes |
| `alerts_core.py` channel-neutral; S023 adds the group text to it (S023 § 3) | § 3 `alerts_core.py` "S023 adds to it" | yes |
| `ticket_facts` with the causing event's type, time and remark, the 80-character cut, the name rule (S023 § 1.1, § 3) | § 1.4 name rule, § 5.1 `ticket_facts` | yes |
| `minutes` in the escalation's `ticket_alert` payload (S023 § 1.1, decision 11) | § 5.1 `minutes?` | yes |
| `ticket_alert` always enqueued; reads the ticket's site; finds the channels (S023 § 3, § 5.1) | § 5.1, § 5.3, decision 10 | yes |
| An escalation never follows a *Down again* (S023 § 4) | § 5.3: a send-back enqueues no escalation; a pending one re-checks `state == raised`, and a send-back puts the ticket in progress | yes |
| One Notifications card, one Save, one PUT; `_validate_int_settings` with prefixed field errors; a body without `escalate_minutes` → 400 (S023 § 1.3, § 3, § 6, § 8) | § 1.6, § 3 `settings.py`, § 6 | yes |
| The e2e backend sets `config.*` in-process "as S021 does for its VAPID keys"; S021's device row sets grade C to 5 minutes (S023 § 3, § 8) | § 3 `e2e_backend.py`, § 8 | yes |

Two wording gaps, both nits (BR3-15): S023 § 9 Q7 still says "its settings
**tab**" (S021 made it a card, BR1-20), and the two briefs read
`ticket_facts["url"]` differently (BR3-02).

## Findings

### BR3-01 — `minor` — IT admin is the *not in Team* user; § 1.3 and § 8 give her two different pages

**Problem.** § 1.3 says IT admin reads "Test messages only. IT admin holds no
site role." and may subscribe. § 1.3 also says a person with no Team record
(`person_id` empty in `/api/auth/me`) gets the *not in Team* state with no
*Turn on*. IT admin is a token role and normally has no `people` row
(`seed_e2e.py`: "no Team record is needed"; `current_person_id` is None for
her), and `push_subscriptions.person_id` is NOT NULL (§ 4.1). So in practice
IT admin lands on the *not in Team* page, which tells her "Ask IT admin to add
you." § 8 then asserts both "*My notifications* opens for every role and shows
*Turn on for this phone*" (IT admin included) and "a login with no Team record
sees 'You are not in Team' and no *Turn on*", with the e2e IT admin
(`e2e_it_admin`) being exactly that login.

**Why it matters.** The coder cannot write both e2e assertions; one page text
is wrong for its reader.

**Options.**
1. State the rule by `person_id` only: IT admin **with** a Team record gets
   "Test messages only. IT admin holds no site role."; IT admin without one
   gets the *not in Team* state, worded for her: "You are not in Team. Add
   yourself in Masters › Team to get test messages." (the operator's line
   stays "Ask IT admin to add you."). § 8: "every role" becomes every seed
   person with a Team record; the *not in Team* row uses `it_admin`
   (`e2e_it_admin`, no seed row) and asserts her wording. Recommended.
2. Seed a Team record for IT admin in the e2e and say IT admin must be in
   Team to use the page. More seed for a marginal user.

### BR3-02 — `minor` — which `url` `ticket_facts` carries: the push wants a path, S023 wants an absolute address

**Problem.** § 5.1 puts "the ticket's `url`" in `ticket_facts` and in the
`push_send` payload; `sw.js` opens it with `clients.matchAll` → `navigate(url)`
or `openWindow(url)`. S023 § 1.1 says its link "uses the label base URL that
S014 already holds" and § 3 lists `label_base_url(cur)` among the helpers its
handlers import — so S023 reads `url` as something it must build, while S021
never says who reads `label_base_url`. A path (`/tickets/412`) works in the
service worker on every stack (production, the dev server, the e2e's
`127.0.0.1:5177`); an absolute production address does not navigate a dev or
e2e tab (`WindowClient.navigate` is same-origin).

**Fix.** Two fields, named once: `ticket_facts["path"]` = `/tickets/<id>`,
which the push payload carries as `url` and the service worker resolves
against its own origin; and `ticket_facts["url"]` = `label_base_url(cur)` +
the path, read once in `ticket_alert`, which S023's message uses with no
second read. One line in § 5.1; S023 § 3 then drops `label_base_url` from its
handler imports (its planner's edit).

### BR3-03 — `minor` — `POST /api/push/subscriptions/remove`: whose row it removes decides whether a handed-over phone goes quiet

**Problem.** § 6 says the route removes "this device's row (sign-out, *Turn
off*); 204 also when there is none". § 5.5 says "a row of someone else's:
404". The case § 1.2 exists for: A subscribes on a phone and her session ends
without sign-out; B signs in on the same phone, never turns notifications on,
and signs out. The browser still holds A's subscription, and the server's row
is A's. If `remove` touches only the caller's rows, A's row stays and A's
breakdown alerts keep ringing on a phone B carries. If it removes the row
**whoever owns it**, the hand-over is clean.

**Why it matters.** This is the one sentence the coder would decide alone,
and the safe answer differs from the general "mine only" rule.

**Fix.** Say in § 5.5 and § 6: `remove` by endpoint deletes the row **whoever
it belongs to** — presenting the endpoint proves the caller holds the device,
and the endpoint is the browser's own capability URL, so nobody else has it.
`DELETE /api/push/subscriptions/<id>` stays mine-only with the 404. Add the
case to § 8's API tests.

### BR3-04 — `minor` — the send-back enqueue must run after `_add_event`, not inside `_send_back`

**Problem.** § 3 says the send-back call "sits in `_apply_move`'s send-back
step and reads `clean["machine_down"]`". In `tickets.py` the "send-back step"
is `_MOVE_STEPS["send-back"]` = `_send_back`, which `_apply_move` runs
**before** it writes the `sent_back` event (`_add_event`, line 800). The alert
needs that event's id (`event_id`, BR2-01), which does not exist yet inside
`_send_back`.

**Fix.** Word § 3 as: in `_apply_move`, after `_add_event` returns the id and
only when `move == "send-back"` and `clean["machine_down"]`, call
`alerts.enqueue_ticket_alert(cur, ticket_id, "breakdown", event_id, …)`.
`_send_back` itself is unchanged (S025 adds its repeat refusal there; no
clash).

### BR3-05 — `minor` — the push-service allow-list refuses Samsung Internet, the default browser on Samsung phones

**Problem.** § 5.4 allows four hosts: FCM (Chrome, Edge on Android), Apple,
Mozilla, Windows. Samsung Internet — the browser a Samsung phone opens links
in unless the person has changed it, and Samsung phones are common on an
Indian shop floor (Plant-Facts § 5: staff use their phones on mobile data) —
runs web push through Samsung's own push service, not FCM, so its endpoint
host is not on the list. Such a person taps *Turn on*, grants permission, and
reads "This browser's push service is not supported".

**Why it matters.** Phones that never ring, for a reason the person cannot
see. The allow-list is a security control (A 8.20, SSRF), so it should be
right rather than loosened.

**Options.**
1. The coder subscribes once from a real Samsung Internet (a device the user
   has), reads the endpoint host, and adds it to the list with its comment,
   as for the other four; the page's *not possible* text names the browsers
   that work. Recommended.
2. Say in § 1.1 and on the page: "On Android use Chrome", and add a device
   row that a Samsung phone's default browser is refused with that text.
   Simpler, but every Samsung user must switch browsers.

### BR3-06 — `minor` — the bell's dot on an iPhone in Safari, and clearing it after *Turn on*

**Problem.** Decision 11 shows the dot when the person would get something
and the device is **off or blocked**. § 1.3's fifth state, *not possible*
(an iPhone not on the Home Screen, or push not set up on the server), is
neither. So the engineer who opens Yantra in Safari on his iPhone — the one
person the Home Screen explanation exists for — never sees the dot, while a
server with no keys would (if it counted as off) nag everyone for a reason
nobody on the floor can fix. And the dot is "set once at start-up": after
*Turn on* succeeds, the page must put it out without a reload, or the nag
outlives the fix.

**Fix.** Two lines in § 1.3 and decision 11: the dot shows for *off*,
*blocked* and *iPhone not on the Home Screen*; never for *push not set up on
this server* or *not in Team*. The notifications page clears the shared flag
when *Turn on* succeeds and sets it on *Turn off* / *Remove* of this device.

### BR3-07 — `minor` — *Remove* a device is one tap

**Problem.** § 1.3 lists *Remove* on each row of *My devices* with no confirm.
From a desktop it silences a phone until someone picks that phone up and turns
notifications on again; on the phone itself, beside *Turn off*, a mis-tap on
the wrong row removes another device. The review rules put *remove* among
the actions that never run on a single tap.

**Fix.** The inline confirm the ticket page already uses
(`LabourPanel.vue` / `TicketDetailView.vue`: the row's buttons swap for a
line "Remove Android · Chrome? That phone gets no alerts until it turns them
on again. — Yes / No"). *Turn off* on this phone needs no confirm: *Turn on*
undoes it in one tap. One sentence in § 1.3; the e2e row "*Remove* works"
clicks through the confirm.

### BR3-08 — `minor` — S025's v20 tests and this step's migration

**Problem.** S025's `test_migration_v20.py` compares a database built by the
frozen v1–v13 fixture with one built by the migration list; S019 § 3 Tests
records that a later migration breaks that equivalence unless the tests build
and compare **v20 alone**, and S019 pins them "if they run the full list".
S019, S020 and S021 are all "coded after S025" in no fixed order, so S021 may
be the first to add a version after v20. § 3 Tests here says nothing.

**Fix.** One line in § 3 Tests, as S019's: "S025's v20 equivalence and
dev-path tests must build v20 alone; if they still run the full list when
this step is coded, pin them to v20 (S019 BR2-01) without loosening their
assertions."

### BR3-09 — `minor` — writing style (CLAUDE-COMMON § Writing style)

The sections the user reads verbatim at gate A (§ 1, Out of scope, § 2, § 7,
§ 9) carry sentences well past the 20-word aim, with nested clauses and
cross-reference tags inside them, and the brief alternates terms for one
thing. The content is right; it is hard to read on a phone.

- **Long sentences (rule 2).** § 1.3 first paragraph (the bell) is one
  70-word sentence with a colon list inside it. § 1.4 bullet "The person
  whose action caused the alert — the raiser, or whoever regraded or sent it
  back — and the ticket's *reported by* person are left out of it". § 1.5
  bullet 3 ("The clock starts when …"). § 3 `settings.py` is a 130-word
  paragraph; § 5.1's first bullet about 150 words. Split: one fact per
  sentence; the finding tags `(BR2-01)` can move to the end of the sentence
  or go, since the Review log records them.
- **One term for one thing (rule 4).** "device" / "phone" / "subscription"
  for the same row (§ 1.2 "removes this device's subscription", § 1.3 "Turn
  on for this phone", "My devices"); "alert" / "notification" / "push" for
  the message; "acknowledged" / "left raised" / "owned" for the same test
  (§ 1.5, § 5.3). Pick one each for the text; the UI words (*device*,
  *notification*) can stay as labels.
- **Noun stacks (rule 6).** "the send-handler outcome contract" (§ 3, § 5.1,
  decision 9), "the push outcome mapping" (§ 8). "How a send handler reports
  its outcome" reads at once.
- **Scope B, messages.** "This browser's push service is not supported"
  (§ 5.4) says what happened but not what to do: add "Use Chrome." (or the
  browsers of BR3-05). The page's "not set up on this server" state should
  end with "Ask IT admin." The 409 "Turn notifications on first" and "Enter
  the three times" are fine.

Severity `minor` because the orchestrator asked for it and the text goes to
the user verbatim; no design content changes.

### BR3-10 — `nit` — `label?` in the subscribe body

§ 6 `POST /api/push/subscriptions` takes `{endpoint, keys, label?}`, while
§ 1.3 and § 4.1 say the label is the browser's, from the user-agent, not
editable (BR1-09). Drop `label?` from the body, or say the page sends it from
`navigator.userAgentData` (Chrome's reduced user-agent string no longer names
the phone model) and the server falls back to the header.

### BR3-11 — `nit` — read the VAPID keys through `config.` at call time

§ 3 and § 8 set the keys after import: the pytest fixture monkeypatches
`config.VAPID_*`, the e2e backend sets them in-process. Code that does
`from config import VAPID_PUBLIC_KEY` would hold the empty value. Say
`push.py` and `push_sender.py` read `config.VAPID_PUBLIC_KEY` at call time, as
`auth_utils._get_dev_stub_user` reads `config.DEV_STUB_ROLE`.

### BR3-12 — `nit` — `sw.js` take-over, and the manifest's content type

- Decision 2 says a new `sw.js` "is picked up on the next visit". It is
  installed then, but stays *waiting* until every Yantra tab is closed. With
  no `fetch` handler there is nothing to break, so `self.skipWaiting()` on
  `install` and `clients.claim()` on `activate` let the new worker take over
  at once. One line in § 3.
- The after-deploy row (`Cache-Control: no-cache` on `sw.js`) can also read
  the manifest's `Content-Type`: `nginx:alpine` serves an unknown extension as
  `application/octet-stream`; Chrome still parses it, but if that is what
  shows, a `types { application/manifest+json webmanifest; }` line in
  `nginx.conf` is the fix.

### BR3-13 — `nit` — the bell on the "no access yet" shell

`App.vue` shows the top bar for every authenticated user, including the
`maintenance_team`-only user who sees "You have no access yet". § 1.3 puts
the bell "on every screen". Say it shows only with `push:subscribe` in
`userPermissions` (the control hidden, as the nav items are), so that user
sees no bell leading to a page the API refuses.

### BR3-14 — `nit` — three device rows name no account or network for the raise

The rows "An operator raises a breakdown / a defect on the TEST machine" and
"Then the engineer and manager test logins … raise a breakdown" say who hears
it but not who raises it or from where. Add "operator test login, any
network" to the raise, and that the engineer's and supervisor's phones were
turned on in the rows above, **on mobile data**, so the row proves the path
from outside the plant.

### BR3-15 — `nit` — small cross-step and API details

- S023 § 9 Q7 says "its settings **tab**"; it is a card (BR1-20). S023's
  planner edits it.
- `GET /api/push/subscriptions?endpoint_hash=`: validate the query as 64 hex
  characters; anything else → `this_device` false for every row, no 400 (a
  stray value must not blank the list).
- `recipients` reads `people.username IS NOT NULL` (§ 5.2 "with a login"):
  the join to `push_subscriptions` enforces it anyway, so say the condition
  is for `you_get` and the tests, not the fan-out.

## Checked and found consistent

- **Queue and worker.** `enqueue(cur, task_type, payload, scheduled_for,
  max_attempts)`; `claim_next` by `scheduled_for`; `mark_done` inside the
  handler's transaction; `mark_failed(conn, task_id, error, retry=True)` on
  its own, growing `delay_seconds` and the cap; `_task_failed`'s one
  `isinstance` line growing to `(BadTask, NoRetry)` plus the `RetryLater`
  branch; the purge's `conn.commit()` as the precedent for commit-before-raise.
  `test_task_queue.py` and `test_worker.py` keep passing as they are.
- **Tickets.** `raise_ticket` (`clean["restore"]` for *Already fixed*),
  `regrade` with `REGRADE_STATES = (raised, acknowledged, in_progress)`,
  `_apply_move` with `clean["machine_down"]` in hand; `_add_event` uses
  `insert_row`, which returns `cur.lastrowid`; `_LOCK_TICKET` gives
  `component_id` and `equipment_id` for the grade read; the regrade's and
  send-back's actor through `current_person_id`. S025's send-back refusal
  after a repeat and *not a fault* from in progress change no trigger.
- **Escalation.** `ticket_events.intensity` is set only by `raised`,
  `regraded` and a send-back that changes the grade, so "the latest row with
  `intensity = 'critical'`" is well defined; `should_escalate` on
  `state == raised` is right for S019's *scheduled*; the three re-checks
  (state, intensity, trigger id) cover acknowledge, start, restore, not a
  fault, regrade down and a newer trigger. `scheduled_for` as a naive IST
  datetime matches the session's NOW().
- **Audience and RBAC.** `memberships (person_id, site_id)` PK gives one role
  per site; `person_units` and `all_units` as § 5.2 reads them;
  `people.username` is the login; `push:subscribe = ('*',)` grants every role
  in `ROLES` (IT admin included) and nothing to `maintenance_team`, which is
  not in `ROLES`; `settings:read` / `settings:edit` as stated; the key is
  global, so `SITE_SCOPED` is untouched.
- **Settings.** `clean_body(validator, creating)` calls `validator(body,
  creating)`, so `_validate_int_settings(spec, values)` wraps in a lambda for
  both routes; `test_settings_api.py` (`{"upload_max_mb": 5}` → 200, unknown
  keys ignored, `{}` → 400) still holds with the escalation keys in their own
  dict; `get_setting_int`'s warning-and-default is the right reader;
  `settings.py` never imports `tickets` or `task_handlers`, so
  `tickets → alerts → settings` is cycle-free; the worker can import
  `settings` (Flask is installed; no `g` is touched on the read path).
- **Frontend.** `AppTopbar.vue` has the name and a logout icon button;
  `/notifications` outside `navItems` passes `canOpenRoute`; `logout()` is
  the one sign-out and can become async; `/api/auth/me` returns `person_id`
  (`userPersonId`); `apiPost` / `apiDelete` exist; `public/` is new and Vite
  copies it; `127.0.0.1:5177` is a secure context for `serviceWorker` and
  `crypto.subtle`; nginx `location /` serves `/sw.js` and the manifest
  `no-cache` with `try_files $uri`; the inline Yes/No confirm pattern exists
  for BR3-07.
- **e2e.** `asPerson("it_admin")` sends `X-Test-Role: it_admin` and the seed
  has no `people` row for her (BR3-01); `screens.spec.js` is a route table,
  so `/notifications` is one row; the e2e backend sets `config.*` before
  importing `app`; no worker runs there, so "Sent to 1 device" asserts the
  count only; Pixel 7 Chromium has `PushManager` and `grantPermissions`
  works; the iPhone 14 project is desktop WebKit with an iPhone user-agent,
  so the page's own "not in standalone mode" rule is the right assertion.
- **Standards.** TPM breakdown response; EN 13306 *administrative delay*
  (part of down time, not of active repair time); SMRP's work-management
  pillar without a metric it lacks; ISO 55001 § 6.2 (objectives and
  planning), § 8.1 (operational control), § 7.4 and ISO 9001 § 7.4
  (communication: what, when, to whom, how); ISO/IEC 27001:2022 A 8.24
  (cryptography), A 5.14 (information transfer), A 8.20 (networks security)
  with OWASP's SSRF guidance; RFC 8030 (urgency values very-low / low /
  normal / high), RFC 8291, RFC 8292; iOS 16.4 for Home Screen push;
  Maintenance-Philosophy § 9's grade meanings and the safety-function rule;
  Plan.MD § 4.7 and Q2 ("stored as settings, not code").
- **Device checks.** They need HTTPS, so production on the TEST machine is
  right; the important rows carry account, network and where, except the
  raise rows (BR3-14); nothing on the list is something a browser could
  judge; the `no-cache` header is an after-deploy row.
- **Track.** Full, as it must be: a migration, a dependency, secrets, an
  outbound call to a browser-supplied address, a timed rule on the queue.
