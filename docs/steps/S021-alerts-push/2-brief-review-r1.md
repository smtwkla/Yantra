```
Step: S021 — Alerts: PWA and web push
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 21-10-2026
```

Reviewed against: 28d3be3 + uncommitted S024

# S021 — Brief review, round 1

**Verdict: three `major` findings are open** (BR1-01 to BR1-03). None changes
the user's three decisions (who gets a breakdown, defects quietly, the split
with S023); each is a design point the coder would otherwise settle alone. The
rest are minor and nits. I also read S023's brief for the fit (BR1-08).

The brief is well grounded: every claim I checked about tickets.py, the S013
queue and worker, the settings module, RBAC and nginx holds, except the three
below.

## Findings

### BR1-01 — `major` — `push_send`'s outcomes cannot be recorded the way § 5.1 says under the S013 worker contract

**Problem.** § 5.1 has the `push_send` handler (a) set `last_sent_at` / clear
`last_error` on success, (b) delete the row on 404/410, (c) fail **without
retry** on 400/403/413 with `last_error` set, (d) retry on 429/5xx/timeout and
set `last_error` "on the last attempt". The worker as built
(`worker.py` `run_one`, `task_handlers.py`) runs the handler inside one
transaction with `mark_done`; a failure is signalled only by **raising**, the
worker **rolls that transaction back**, then calls `mark_failed` on its own
connection; "no retry" exists only as `BadTask` ("can't be run as given"); and
the handler signature is `handler(conn, payload, should_stop)` — it is never
told the attempt number. So, as written:

- any `last_error` the handler writes on the subscription row before raising
  is rolled back with the transaction (c and d lose their record);
- "on the last attempt" cannot be decided inside the handler;
- "failed, no retry" has no vehicle except raising `BadTask`, which the brief
  does not say.

(a) and (b) work: they end in `mark_done` and commit together.

**Why it matters.** The device list's "last send and its error" (§ 1.3) is the
only way a person sees that their phone is dead to Yantra; and S023's
`telegram_send` needs the same contract (400/403 no retry; 429 with a delay),
so this is decided once here.

**Options.**
1. The handler writes the subscription row's `last_error` in its **own short
   committed transaction** before raising (the precedent is the purge, which
   commits per batch: § `task_handlers` docstring "the one exception"), and
   writes it on **every** failed attempt, cleared on success — no attempt
   number needed; the task row's `last_error` keeps the history anyway. For
   "no retry" the brief names the exception: raise `BadTask` (documented as
   "the push service refused our request: payload or keys") or add a sibling
   `NoRetry(Exception)` beside `BadTask` in `task_handlers.py` that
   `_task_failed` treats the same. Recommended, with `NoRetry` (the name says
   what it means; one `isinstance` tuple in `worker._task_failed`).
2. Widen the contract: `run_task` passes the task row (attempts,
   max_attempts) and the handler decides "last attempt". More change to S013's
   code for little gain.
3. `push_send` never raises: it records the outcome and re-enqueues itself
   with its own back-off. Duplicates what the queue does.

Add to § 5.1 (and § 3 `task_handlers.py` / `worker.py`) which one; S023's
§ 5.2 then uses the same words.

### BR1-02 — `major` — the escalation minutes in `_APP_SETTINGS` break `PUT /api/settings/app`

**Problem.** § 3 puts `escalate_minutes_a/b/c` "in `_APP_SETTINGS` (§ 4.2;
the S013 pattern)". `settings._validate_app_settings` iterates **every** key
of `_APP_SETTINGS` and returns a field error for each one missing or not an
int; `put_app_settings` (`PUT /api/settings/app`) uses it. With three more
keys, the Uploads card's save (`SettingsView.vue`:
`apiPut("/api/settings/app", { upload_max_mb })`) and
`test_settings_api.py` (`admin.put(APP, json={"upload_max_mb": 5})` → 200) fail
with 400. `_APP_SETTINGS` is S006's upload limit, not S013's (S013 gave the
networks their own route, as S014 the label address).

**Why it matters.** A coder following the brief breaks an existing screen and
test, then has to redesign the validator alone.

**Options.**
1. A second dict for the notifications pair, e.g.
   `_ESCALATION_SETTINGS = {"A": ("escalate_minutes_a", 10, 5, 1440), …}`,
   read with the existing `get_setting_int` and written with `_save_setting`;
   the validator becomes `_validate_int_settings(keys)` used by both routes.
   Recommended: the reads and the audit log line stay the one path.
2. Make `/app` accept partial bodies. Changes an existing contract for no
   reason of its own.

Also name the reader: `escalation_minutes(cur)` → `{"A": 10, "B": 30, "C": 60}`
in `settings.py`, which `alerts.py` calls; `push_core` gets the dict and the
grade (pure), as § 3 says.

### BR1-03 — `major` — there is no "user menu": where *My notifications* lives is undecided

**Problem.** § 1.3, § 3 and § 8 put the page "in the user menu" and test that
"the user menu shows *My notifications* on a phone without overflowing".
`AppTopbar.vue` has the user's name and a logout icon button, no menu;
`AppBottomNav.vue` mirrors `navItems` on the phone; the sidebar does the same
on desktop. `canOpenRoute` allows routes outside `navItems`, so the route
itself is fine; the entry point is not designed.

**Why it matters.** This is the screen a technician must find once, on a
phone, to turn alerts on; an entry nobody finds means phones that never ring.
The coder would invent the UI alone.

**Options.**
1. A **bell icon button** in the topbar right, next to the name, on every
   screen, phone and desktop, opening `/notifications`. Its state doubles as
   the nudge: a small dot when this device is **off** or **blocked** (read
   once from `push.js` at start-up), nothing when on. One tap, 44 px, no menu
   to overflow. Recommended.
2. A nav item in `navItems` (`perm: "push:subscribe"`): the bottom nav has
   room for one more on a 360 px phone but every item shrinks.
3. A real user dropdown (name → *My notifications*, *Sign out*): a new
   component for two items.

Replace the e2e line with the bell: "the bell is visible on every screen in
the three projects; tapping it opens *My notifications*".

### BR1-04 — `minor` — S019's *scheduled* state and the escalation rule

**Problem.** S019 § 9 Q6 assumes "S021 treats *scheduled* as acknowledged;
S021's brief will state it". § 1.5's wording ("the ticket has left raised")
covers it, but S019 is coded in the same window and its `REGRADE_STATES`
gains `SCHEDULED`; a regrade to critical while *scheduled* would, by § 5.3,
be "while acknowledged or in progress → alert only" by analogy, not by text.

**Fix.** One sentence in § 5.3: "*scheduled* (S019) counts as owned: a
regrade to critical there sends the alert without an escalation, and a
scheduled ticket never escalates." And `should_escalate` tests the state by
`== raised`, not by a list of the others, so S019's new state needs no change
here.

### BR1-05 — `minor` — *send back* with "machine down again" makes a breakdown that nobody hears about

**Problem.** `tickets_core.send_back_intensity`: a send-back from
*back in service* with `machine_down` sets the intensity to critical (the
`sent_back` event carries it) and the state to *in progress*. § 5.3 says "the
raise and the regrade … no other ticket path changes" and "every other move
→ nothing", so this breakdown-again sends nothing, although by § 1.5's own
rule the ticket "becomes a breakdown in Yantra" at that moment and the
downtime restarts (S018 § 5.4).

**Options.**
1. Treat it as "defect became a breakdown, owned": `ticket_alert breakdown`,
   no escalation (someone is in progress). Recommended: the unit's supervisor
   learns the machine is down again; the engineer who sent it back is the
   actor, so § 5.2 should exclude **the actor of the triggering event**, not
   only the ticket's creator (that also removes the raiser from a regrade he
   made himself; BR1-13).
2. Nothing, stated: the engineer sending back has just talked to the
   technician. Then say so in the table.

### BR1-06 — `minor` — where dev, pytest and the e2e backend get a VAPID pair

**Problem.** § 3 reads the three keys "with an empty default: empty means
push is off", and `example_secrets_app.py` is what dev without a
`secrets_app.py`, pytest (`IS_TESTING`) and `tooling/e2e/e2e_backend.py` run
on. Yet § 8 tests subscribe, "test → N devices", and the e2e "*Send a test*
reports Sent to 1 device", all of which need push **on**.

**Fix.** Say: pytest — a session fixture generates a pair with `py_vapid`
and monkeypatches `config.VAPID_*` (plus one test with them empty for
`enabled: false`); the e2e backend generates a pair at start the same way
(`e2e_backend.py`); dev — `make_vapid_keys.py` into `secrets_app.py`. Also
state the public key's wire form, since the two sides must agree: the browser's
`applicationServerKey` is the raw 65-byte uncompressed P-256 point,
base64url, which is what `py_vapid`'s `Vapid.public_key` must be exported as
(`public_bytes(X962, UncompressedPoint)`); the `GET /api/push/config` test
asserts that length (87 chars without padding).

### BR1-07 — `minor` — "`sw.js` is served with `no-cache`" is not something the e2e run can see

**Problem.** The e2e stack serves the frontend from Vite (5177); the
`no-cache` header is nginx's (`tooling/build/nginx.conf` `location /`, which
does cover `/sw.js` and `/manifest.webmanifest` via `try_files $uri` — the
claim in § 7.2 is right). A browser test asserting that header would test
Vite.

**Fix.** Keep "the manifest parses and the service worker registers" as e2e;
move the header to the **after-deploy** section of `device-checks.md` as a
one-line row ("open `<address>/sw.js` in the browser's network panel:
`Cache-Control: no-cache`"), or drop it, since the nginx block is unchanged
by this step.

### BR1-08 — `minor` — the fit with S023: decide three shared points here

S023 reuses this step's task, pure module, settings pair and enqueue
condition. Three places where S023 would otherwise have to change S021's
code:

1. **The enqueue condition.** § 5.3 enqueues "only when push is set up";
   S023 § 3 rewrites it to "push **or** Telegram". Simpler and final: **always
   enqueue** `ticket_alert` and `ticket_escalate`; the handler finds no channel
   and is done. One `if` fewer in `tickets.py`, nothing for S023 to touch,
   and Settings › Background tasks shows that alerts ran. Recommended.
2. **The pure module's name.** S023 § 3 says "`alerts_core.py` or S021's
   `push_core.py` (whichever S021 ended with)". Name it now: the
   channel-neutral rules (audience per kind, the text, `should_escalate`,
   minutes per grade) in **`alerts_core.py`**; only the push-specific parts
   (endpoint check, user-agent label, outcome mapping) in `push_core.py`.
   S023 then adds to `alerts_core`.
3. **The escalation's minutes.** S023's group message says "Not acknowledged
   after 10 minutes". Carry `minutes` from `ticket_escalate`'s payload into
   the `ticket_alert escalation` payload, and let § 1.4's push title say it
   too ("Not acknowledged after 10 min · SMTW.MCC2 · VBM001"): the reader
   learns at once how long it has waited.

Also for S023: `ticket_alert` already reads the ticket inside the handler;
have it read `unit_id` → `site_id` once, as S023 needs the site for the chat
id. One sentence in § 5.1.

### BR1-09 — `minor` — renaming a device is more than the floor needs

**Problem.** § 1.3 and § 6 add an editable label (`PUT
/api/push/subscriptions/<id>`, a dialog, an e2e). The label from the
user-agent ("Android · Chrome") plus "added 21-10-2026" tells a person which
row is which phone; with one or two devices per person, a rename is never
needed, and it is one more dialog to fit a phone.

**Options.** 1. Drop rename (route, dialog, test); keep the label as the
browser gives it. Recommended. 2. Keep it. The user's call; say which.

### BR1-10 — `minor` — the e2e states per project, and how "denied" is produced

**Problem.** § 8 Automated: "*My notifications* opens for every role; with
the browser's permission denied it shows how to unblock". The three S024
projects see three different pages: desktop and Pixel Chromium have
`PushManager` (state off/on), **iPhone 14 WebKit has no `PushManager` outside
a Home Screen app**, so the page shows the Home Screen explanation there.
Playwright can `grantPermissions(["notifications"])` but cannot deny; the
denied branch must be stubbed (`page.addInitScript` redefining
`Notification.permission` to `"denied"`).

**Fix.** List in § 8 what each project asserts: Chromium — the *Turn on*
button; after `grantPermissions`, subscribing against the e2e backend works
(Chromium headless gives a real `fcm.googleapis.com` endpoint only when
signed in to a push account — it usually does **not**, so plan for
`subscribe()` to fail and seed the row through the API as § 8 already says);
WebKit — the Home Screen text; denied — stubbed. The notifications-page test
is then a real test, not three skips.

### BR1-11 — `minor` — the escalation device check needs a second account and the plant network

**Problem.** The row "A breakdown left unacknowledged … (set the TEST
machine's grade's minutes to 5)" needs `settings:edit`, i.e. the IT admin
account **on the plant network** (S013), before the engineer's phone check on
mobile data; the TEST machine starts at grade **C** (60 min). The row names
one account.

**Fix.** Split it as two rows in the device list: (1) IT admin, company
Wi-Fi, production: set C to 5 minutes in Settings › Notifications; (2) the
engineer and manager test logins, mobile data, TEST machine: raise, wait
6 minutes, both phones ring "Not acknowledged"; then set C back. Each other
row already carries its account; add **network: mobile data** to the Android
and iPhone rows (it proves the path from outside the plant, which is the
case that matters).

### BR1-12 — `minor` — define "the latest event that made it critical", and `_add_event` must return the id

**Problem.** § 5.1 `ticket_escalate` fires only if `trigger_event_id` "is
still the latest event that made it critical". The events that carry an
intensity are `raised`, `regraded` and `sent_back` (`ticket_events.intensity`,
S018 § 4.3). `tickets._add_event` does not return the inserted id today, so
the raise and regrade cannot pass `trigger_event_id` without a small change
the brief does not list.

**Fix.** In § 5.1: "the latest `ticket_events` row of the ticket with
`intensity = 'critical'` has `id = trigger_event_id`" (one query in
`alerts.py`; `alerts_core.should_escalate(state, intensity,
latest_critical_event_id, trigger_event_id)` is the pure part). In § 3
`tickets.py`: `_add_event` returns the event id.

### BR1-13 — `nit` — who is "the person who raised it"

`tickets.created_by` is a username; the person is `people.username =
created_by`. `reported_by_id` (the operator a supervisor names) is another
person. Say both are excluded for `breakdown` and `defect` (cheap, and the
operator who found it needs no alert about it). With BR1-05 option 1 the
rule becomes "the actor of the triggering event and the reported-by person".

### BR1-14 — `nit` — standards wording

- ISO/IEC 27001:2022 **A 8.22** is *segregation of networks*; the outbound
  allow-list is A 8.20 (networks security) plus OWASP's SSRF guidance (and
  A 8.26, application security requirements, if a second control is wanted).
  Drop 8.21–8.22.
- "SMRP work-management practice tracks … time from request to response":
  SMRP's metric set has no response-time metric; Plan.MD § 4.2 already calls
  response time "the plant's own measure". Keep EN 13306's *administrative
  delay* (correct and well put) and say SMRP's Body of Knowledge, work
  management pillar, asks that emergency work be dispatched by priority — the
  same idea, without naming a metric that does not exist.
- The rest is right: ISO 55001 § 7.4 and ISO 9001 § 7.4 are *Communication*;
  A 8.24 cryptography; A 5.14 information transfer; RFC 8030/8291/8292; iOS
  16.4 for Home Screen push.

### BR1-15 — `nit` — manifest and meta tags

Add `scope: "/"` and `id: "/"` to the manifest (Chrome treats updates as the
same app by `id`), and `mobile-web-app-capable` beside the legacy
`apple-mobile-web-app-capable` (Chrome warns on the Apple tag alone).

### BR1-16 — `nit` — `sw.js` behaviour and a `tag` per ticket

State that `notificationclick` focuses an already open Yantra window and
navigates it (`clients.matchAll` → `focus()` + `navigate(url)`), else
`openWindow`; and give each push a `tag: "ticket-<id>"` with `renotify:
true`, so the escalation replaces the breakdown's notification on the phone
instead of stacking two. `push_send`'s payload gains `tag`.

### BR1-17 — `nit` — the migration number

§ 4's heading says "the next migration after S025's v20"; S019 claims v21 and
S020 "whichever is coded first". Write "the next free version when coded"
and name the test file `test_migration_<n>.py` accordingly.

### BR1-18 — `nit` — `this_device` by `endpoint_hash` query

Say who hashes: the page computes SHA-256 of
`pushManager.getSubscription().endpoint` with `crypto.subtle` (available
under HTTPS and `localhost`, the only places push works). Fine as designed;
one sentence.

### BR1-19 — `nit` — IT admin on *My notifications*

`push:subscribe = ('*',)` lets IT admin (a token role) subscribe and get
only tests; "What you will get" should say so ("Test messages only — IT
admin holds no site role"), as it says "nothing yet" for a technician. Also
state the `maintenance_team`-only user: `LOGIN_ROLE` matches no `('*',)` key,
so the page is not reachable and nothing needs hiding — consistent.

### BR1-20 — `nit` — Settings › Notifications: show what A, B, C mean

Beside each minutes field, the grade's meaning from Maintenance-Philosophy
§ 9 ("A — stops a line or a safety risk", "B — slows production, repair
within the shift", "C — no direct impact"), so the manager reading it needs
no second page. Also "Settings › Notifications (new tab)": `SettingsView.vue`
is one page of **cards**; make it a card like Labels and Network.

## Checked and found consistent

- `tickets.py` raise and regrade are the two paths that set an intensity by
  the user's choice; both run in one transaction with a locked ticket row, so
  `enqueue(cur, …)` inside them commits with the ticket (base: auto-enqueue
  on status transition). A1 *Already fixed* goes through `_apply_move`
  inside the raise, so "sends nothing" is one check on `clean["restore"]`.
- `task_queue.enqueue` takes `scheduled_for`; `claim_next` orders by it; the
  worker polls every 5 s; `requeue_stale` and `max_attempts` behave as § 5.1
  assumes. Fan-out inside the handler's transaction is all-or-nothing as
  claimed.
- `config_rbac`: `push:subscribe = ('*',)` is a global key (not site-scoped),
  `test_rbac.test_every_role_gets_wildcard_permissions` covers it without a
  change; `it_admin` is a token role with no membership, so § 5.2 gives it no
  ticket alerts.
- `auth_utils.current_person_id` and `/api/auth/me`'s `person_id` give the
  Team record the routes need; `people.username` is the login; `memberships`
  (`role`, `all_units`) and `person_units` are the audience's tables; sites
  come from `units`, as `_lock_ticket` joins them.
- `equipment_core.effective_criticality(own, equipment_grade)` exists and
  does what § 5.3 says.
- nginx `location /` serves `/sw.js` and `/manifest.webmanifest` with
  `Cache-Control: no-cache`; `/assets/` stays immutable; a service worker
  with no `fetch` handler leaves the stale-bundle check untouched.
- `stores/auth.js` `logout()` is the one place to hook the best-effort
  remove; `keycloak-js` with `login-required` returns to the tapped URL after
  login.
- Settings: `get_setting_int`, `_save_setting` (with its audit log line) and
  the `GET/PUT` pair pattern are the right things to reuse; `settings:read`
  (manager, IT admin) and `settings:edit` (IT admin) as stated.
- Plan.MD § 4.7 and Q2, Maintenance-Philosophy § 6 and § 9 (A/B/C, safety
  function graded A, escalation per criticality) agree with the brief; the
  user's three decisions are carried verbatim.
- `pywebpush` is new to `backend/pyproject.toml` (no HTTP client there today
  beyond urllib; it will pull `requests`, `cryptography`, `py-vapid`,
  `http-ece`), and the S022 check is the right gate.
- Device checks run on production over HTTPS (the dev server is HTTP over the
  LAN); the TEST machine in `SMTW.MCC2` from S024 § 1.6 is the right place.
