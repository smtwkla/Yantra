```
Step: S021 — Alerts: PWA and web push
Doc: brief
Author: Planner (Opus)
Date: 21-10-2026 (revised 21-10-2026 after brief-reviews r1, r2 and r3)
Track: full
Status: Approved 21-10-2026 (coded after S025)
Baseline: 28d3be3 + uncommitted S024
```

# S021 — Alerts: PWA and web push

Yantra rings the right phones when a breakdown is raised, and escalates it
when nobody acknowledges it in time. Today nobody hears about a ticket until
they open the list (S017, S018). This step also makes Yantra an
**installable app** (a PWA). An iPhone needs that before it can receive web
push at all.

The user split the old queued item *S021 Alerts* in two on 21-10-2026. This
step covers the PWA, web push and escalation. **S023 — Alerts: Telegram and
end-of-shift list** reuses this step's alerts and recipients.

User decisions taken before this brief (21-10-2026):
1. **A new breakdown** alerts the **engineers**, the **supervisor of that
   unit** and the **maintenance manager**. Each must have access to the unit
   (§ 5.2).
2. **A new defect** (degraded or initial) alerts the **engineers, quietly**:
   no sound and no escalation.
3. **Split in two**: PWA, web push and escalation here; Telegram and the
   end-of-shift list in S023.
4. **Push alone, for now** (U1, 21-10-2026): S023 is parked, so push is the
   only channel. The team mostly uses **Samsung Galaxy** phones; the user has
   an **iPhone**. Every phone installs Yantra from **Chrome** (Android) or the
   **Home Screen** (iPhone). Where this brief says S023 adds or uses
   something, that holds only if S023 is taken up again.

**Track: full.** The step adds a migration and a new dependency. It handles
keys and posts to an address a browser supplies. It adds a timed rule on the
job queue and touches more than 10 files.
**Depends on:** S017 and S018 (tickets, states, regrade), and S013 (job queue
and worker).
**Coded after S025** is committed. S025 squashes the schema into v20; this
step's migration is the next free version after it.

## 1. What will be built

**Terms used in this brief** (BR3-09):
- **Alert**: a message Yantra sends about a ticket (a breakdown, a defect,
  *down again*, an escalation), or a test message.
- **Push**: the channel that carries an alert to a phone or computer (web
  push). S023 adds Telegram as a second channel.
- **Device**: one browser on one phone or computer. A device that has turned
  alerts on has a **subscription**: the push address and two keys the browser
  gives. Yantra stores one row per subscription.
- **Acknowledged**, for escalation: the ticket is **no longer raised**.
- On screen the word is **notifications** (*My notifications*, *Turn on for
  this phone*), because that is what phones call them.

1. **An installable app (PWA shell).**
   - A web app manifest, `manifest.webmanifest`. It names the app *Yantra*,
     starts at `/`, opens `standalone` and sets the theme colour. It has icons
     of 192 and 512 px and a 180 px Apple touch icon. `index.html` links it,
     with the iOS meta tags.
   - A **service worker**, `sw.js`. It has two jobs only: show a pushed
     alert, and open the ticket when the alert is tapped.
   - The service worker **caches nothing** and has no `fetch` handler. Yantra
     stays online-only (Plan.MD § 1), and the stale-bundle check works exactly
     as today (§ 7.2).
   - On Android, Chrome offers *Install app*. On an iPhone, the person adds
     Yantra to the Home Screen (*Share › Add to Home Screen*).
   - **iOS delivers web push only to a Home Screen app, on iOS 16.4 or
     later.** Safari in a tab cannot subscribe. The notifications page says so
     when it finds an iPhone that is not running from the Home Screen.
2. **Subscriptions per person and device.**
   - A logged-in person with a Team record turns alerts on **for this phone**.
     The browser asks for permission; on iOS the request must come from a
     tap.
   - The browser gives Yantra a subscription, and Yantra stores it against the
     person. A person may have several devices.
   - **Sign out removes this device's subscription.** A phone that changes
     hands then stops getting the previous person's alerts. The removal works
     whoever owns the row (§ 5.5, BR3-03).
3. **A *My notifications* page** (`/notifications`).
   - It opens from a **bell icon button** in the top bar, on every screen, on
     phone and desktop (BR1-03). The bell shows only to people with
     `push:subscribe`, so the "no access yet" screen has none (BR3-13).
   - The bell shows a small **dot** when this device is in one of three
     states: *off*, *blocked*, or *iPhone not on the Home Screen* (BR3-06).
   - It shows the dot only when the person **would get alerts**, that is, when
     the *What you will get* list below is not empty (BR2-05).
   - So a technician, IT admin and a person without a Team record never see
     the dot. Nobody sees it when push is not set up on the server, since
     nobody on the floor can fix that. The dot never becomes a nag that people
     learn to ignore.
   - The page clears the dot at once when *Turn on* succeeds. It sets the dot
     again on *Turn off* or on removing this device. No reload is needed
     (BR3-06).

   The page shows the **state of this device** (BR2-05, BR2-08, BR3-01):
   - **On**: the browser holds a subscription **and** the server lists it as
     this device (`this_device`). The page checks both at start-up, after
     `/api/auth/me`.
   - **Off**: anything else. This includes a browser that still holds a
     subscription the server removed, after *Sign out* or *Remove*. *Turn on*
     subscribes again.
   - **Blocked**: the browser has refused permission. The page says how to
     unblock it.
   - **iPhone not on the Home Screen**: the page says "Add Yantra to the Home
     Screen, then open it from the icon."
   - **Not set up on this server**: the server has no push keys. The page says
     "Notifications are not set up on this server yet. Ask IT admin."
     (BR3-09).
   - **Not in Team**: the person has no Team record (`person_id` is empty in
     `/api/auth/me`). The page offers no *Turn on*, so the browser never asks
     for a permission that cannot be used. The text depends on who reads it
     (BR3-01):
     - IT admin: "You are not in Team. Add yourself in Masters › Team to get
       test messages."
     - anyone else: "You are not in Team. Ask IT admin to add you."

   The page has these parts:
   - **Turn on for this phone** and **Turn off**. *Turn off* asks nothing,
     because *Turn on* undoes it in one tap.
   - **Send a test**: a test alert to all the person's devices.
   - **My devices**: each device with its label as the browser gives it (e.g.
     "Android · Chrome"; not editable, BR1-09), when it was added, the last
     send, and the last error if any.
   - **Remove** on each device row. It asks first, inline, as the labour rows
     do (BR3-07): "Remove Android · Chrome? That device gets no alerts until
     it turns them on again. — Yes / No".
   - **What you will get**: plain lines built from the person's roles at their
     sites, e.g. "Breakdowns and defects at SMTW.MCC2, escalations".
     - A person in Team with nothing to get reads "Nothing yet. Ask your
       engineer." A technician reads this today (§ 9 Q3).
     - IT admin with a Team record reads "Test messages only. IT admin holds
       no site role." (BR1-19, BR3-01).
     - The server builds these lines (`alerts_core.you_get`, from the person's
       memberships) and returns them in `GET /api/push/config`. The audience
       rule lives in one place (BR2-06).
4. **The alerts** (Plan.MD § 4.7). The worker sends them; a request never
   does.

   | Event | Who gets it (with access to the ticket's unit, § 5.2) | How |
   |---|---|---|
   | **New breakdown** (raised critical) | engineers, the unit's supervisors, managers | normal: sound and vibration, `Urgency: high` |
   | **Defect became a breakdown** (*Machine stopped*, S018 regrade) | same as a new breakdown | same |
   | **Down again** (*Send back* with the machine down, S018) | same as a new breakdown | same, but no escalation: someone is already working on it (BR1-05) |
   | **New defect** (raised degraded or initial) | engineers | **quiet**: `silent`, `Urgency: low`; no escalation |
   | **Breakdown not acknowledged in time** | engineers and managers (§ 9 Q2) | normal, titled "Not acknowledged after 10 min · …" with the minutes it waited (BR1-08) |
   | **Test** | the person asking | normal |

   - Two people are left out of an alert (BR1-05, BR1-13). One is the person
     whose action caused it: the raiser, or whoever regraded the ticket or
     sent it back. The other is the ticket's *reported by* person.
   - A ticket raised **already fixed** sends nothing (S018 A1: it goes
     straight to back in service). Nothing needs a response, and the ticket
     reaches the engineer's list to close as today.
   - An alert reads, for example: title **"Breakdown · SMTW.MCC2 · VBM001"**,
     body "TK-2026-10-012 · Not building pressure — raised by Ravi". The body
     uses the symptom label, else the first 80 characters of the
     description.
   - A *Down again* alert's title starts **"Down again"**. Its body ends "—
     sent back at 14:05" (BR2-01).
   - Tapping an alert opens `/tickets/<id>`. If the session has ended,
     Keycloak asks for a login first.
   - **The name** after "raised by" is a first name. It is the ticket's
     *reported by* person; without one, the raiser's Team name; without that,
     the raiser's login. S023's group message uses the same rule (BR2-11).
5. **Escalation** of a breakdown that nobody acknowledged (Plan.MD Q2;
   Maintenance-Philosophy § 6: "escalation time per criticality").
   - The time limit depends on the **criticality grade of the ticket's
     item**. That is the component's own grade when the ticket names a
     component, else the machine's. So a press safety-door ticket, graded A,
     escalates first (decided 16-10-2026).
   - **Proposed defaults: A 10 minutes, B 30 minutes, C 60 minutes.** The
     user decides (§ 9 Q1).
   - The times are settings, not code. IT admin edits them in **Settings ›
     Notifications** (`settings:edit`); the manager sees them
     (`settings:read`).
   - The clock starts when the ticket **becomes a breakdown in Yantra**: at
     the raise, or at the *Machine stopped* regrade. It does not start at the
     typed event time. A supervisor who records a stop two hours late should
     not set off an escalation in the same second (§ 7.5).
   - A ticket counts as acknowledged once it is **no longer raised**:
     acknowledged, scheduled (S019), started, back in service or closed. The
     rule tests `state == raised`, so S019's new *scheduled* state needs no
     change here (BR1-04).
   - One escalation per breakdown, with no repeats (§ 9 Q2).
6. **Settings › Notifications**: a new **card** on the Settings page, like
   Labels and Network (BR1-20).
   - It holds the three escalation times. Each time sits beside its grade's
     meaning from Maintenance-Philosophy § 9: "A — stops a line or a safety
     risk", "B — slows production, repair within the shift", "C — no direct
     impact".
   - A line says whether push is set up on this server (the keys are present)
     and how many devices are subscribed.
   - Nothing else on the card can be edited in this step.
   - The card has **one Save**. It sends one `PUT /api/settings/notifications`
     with every value on the card.
   - S023 adds its Telegram groups and shift ends as **blocks of this card**,
     under the same Save (S023 BR2-01).

### Out of scope

- **Telegram** and the **end-of-shift list**: S023.
- *Job assigned to you*, PM due or overdue, out-of-limit readings, and the
  daily summary email (Plan.MD § 4.7). Their modules do not exist yet. Each
  later step adds its alert to the same machinery. § 9 Q3 asks whether *Job
  assigned to you* comes now.
- A per-person choice of which alerts to get, beyond on or off per device.
- Quiet hours, a duty roster or an on-call rota. Plant-Facts § 5 says the
  shift pattern and on-call are still to be decided.
- Offline use, caching and background sync: Yantra stays online-only.
- Kiosks (Plan.MD § 1: not in v1).
- The devops template change for the new secrets. That edit is the user's
  (§ 5.6).

## 2. Standards and practice

- **TPM — breakdown response.** In TPM, the operator's red tag is our ticket.
  It works only if maintenance responds fast. A breakdown-reduction programme
  first watches the time from report to acknowledgement. S018 already
  measures it per ticket as *response time*. This step is what shortens it.
- **EN 13306 — administrative delay.** A failed item can wait before anyone
  starts on it, for organisational reasons. EN 13306 calls that wait
  *administrative delay*. It is part of down time, but not of active repair
  time. Alerts and escalation shorten exactly that part.
- **SMRP.** SMRP's Body of Knowledge (work management pillar) asks that
  emergency work is sent out at once, by priority. SMRP has no response-time
  metric of its own, so response time stays the plant's own measure (Plan.MD
  § 4.2, BR1-14).
- **Criticality-based response** (ISO 55001 § 6.2 and § 8.1: risk-based
  planning and operational control; Maintenance-Philosophy § 8). The response
  to a failure follows the risk of the item. That is why the escalation time
  is set per grade A, B and C, and why a safety function (grade A) escalates
  first.
- **ISO 55001 § 7.4 and ISO 9001 § 7.4 — communication.** Both ask the
  organisation to decide what it communicates, when, to whom and how. § 1.4's
  table is that decision. Each person sees their part of it on *My
  notifications*.
- **ISO/IEC 27001:2022:**
  - **A 8.24 (use of cryptography)**, with the base's Secrets pattern. The
    VAPID private key signs every push. It is a secret in `secrets_app.py`,
    never in the repo or the browser. Only the public key is served.
  - **A 5.14 (information transfer).** A push passes through Google's or
    Apple's push service, **encrypted end to end** (RFC 8291), so they cannot
    read it. Even so, the text carries only what a person at the plant needs:
    unit, machine code, ticket number, symptom and the raiser's first name.
  - **A 8.20 (networks security)**, with OWASP's guidance on *server-side
    request forgery*. The push address comes from a browser, and the worker
    posts to it. So Yantra accepts only HTTPS addresses at the known push
    services (§ 5.4). It refuses anything else when a device subscribes
    (BR1-14).
- **W3C Push API, Notifications API and Web App Manifest; RFC 8030 (Web
  Push), RFC 8291 (message encryption), RFC 8292 (VAPID).** These are the
  standard browser parts. No third-party notification service is used
  (Plan.MD § 4.7: "no third party").

## 3. Where

### Backend

- `local_db.py`: the next migration, with the table `push_subscriptions`
  (§ 4).
- `alerts_core.py` (new, pure, **the same for every channel**; S023 adds to
  it, BR1-08). It holds:
  - the audience per alert kind and role (§ 5.2);
  - the minutes for a grade, from the settings dict;
  - the alert's title and body;
  - `should_escalate` (§ 5.1, § 5.3) and `should_send(kind, state)` (§ 5.1,
    BR2-04);
  - the name rule (§ 1.4, BR2-11);
  - `you_get(memberships)`, the *What you will get* lines (BR2-06).

  Every text is built from one dict, **`ticket_facts`** (§ 5.1). S023's group
  message reads the same dict (BR2-11).
- `push_core.py` (new, pure, push only): the address check (§ 5.4), the label
  from a user-agent string, and how the push service's answer maps to an
  outcome (§ 5.1).
- `push.py` (new blueprint `/api/push`): config with the *What you will get*
  lines, subscribe, list, remove and test (§ 6). It reads `config.VAPID_*` at
  call time, not at import, as `auth_utils._get_dev_stub_user` reads
  `config.DEV_STUB_ROLE`. The pytest fixture and the e2e backend set the keys
  after import (BR3-11).
- `alerts.py` (new, thin shell), called inside the ticket's transaction:
  - `enqueue_ticket_alert(cur, ticket_id, kind, event_id, exclude_person_ids,
    minutes=None)`. `event_id` is the event that caused the alert, so the
    text can say *Down again* and give its time (BR2-01);
  - `enqueue_escalation(cur, ticket_id, trigger_event_id, minutes)`;
  - `recipients(cur, ticket, kind, exclude_person_ids)`, the SQL of § 5.2;
  - `latest_critical_event_id(cur, ticket_id)` (§ 5.1).
- `task_handlers.py`:
  - three handlers: `ticket_alert` fans out, `ticket_escalate` checks and
    then fans out, and `push_send` sends to one device (§ 5.1);
  - two exceptions beside `BadTask`, for how a send task reports its outcome
    (§ 5.1, decision 9): `NoRetry(message)` and `RetryLater(message,
    after_seconds)`. This is the one signature, here and in S023 (BR2-03).
- `worker.py`: `_task_failed` treats `BadTask` and `NoRetry` as "failed, no
  retry". It treats `RetryLater` as a retry after its delay, and anything else
  as a retry with the existing back-off.
- `task_queue.py`: `mark_failed(conn, task_id, error, retry=True,
  delay_seconds=None)`.
  - A given delay replaces the back-off for that retry: here for a push 429
    with `Retry-After`, and in S023 for Telegram's 429.
  - The delay is **capped here**, at
    `company_settings.TASK_RETRY_DELAY_MAX_SECONDS = 3600`. Every send task
    gets the cap without code of its own.
  - With no attempt left, the task fails and the delay is ignored (BR2-03).
- `push_sender.py` (new): the one place that calls `pywebpush`.
  - It returns the push service's status and `Retry-After`. The handler takes
    it as a parameter, so tests use a fake.
  - It reads `config.VAPID_*` at call time (BR3-11).
  - It calls `webpush(..., timeout=PUSH_TIMEOUT_SECONDS)`, with
    `company_settings.PUSH_TIMEOUT_SECONDS = 10`, because `requests` has no
    timeout by default (BR2-07). S023's Telegram call has a timeout too.
- `tickets.py` (§ 5.3). No other ticket path changes.
  - `_add_event` **returns the new event's id** (BR1-12).
  - The raise and the regrade call `alerts.enqueue_*` after their event is
    written.
  - The send-back call sits in **`_apply_move`, after `_add_event`** has
    returned the `sent_back` event's id. It runs only when `move ==
    "send-back"` and `clean["machine_down"]` is yes (BR2-01, BR3-04).
  - `_send_back` itself is unchanged: it runs before the event is written, so
    it has no id yet. S025 adds its repeat refusal there, with no clash.
- `settings.py` (BR1-02, BR2-02):
  - A **second settings dict**, `_ESCALATION_SETTINGS = {"A":
    ("escalate_minutes_a", 10, 5, 1440), "B": (…, 30, …), "C": (…, 60, …)}`.
    The existing `get_setting_int` reads it; `_save_setting` writes it, with
    its audit log line.
  - `_validate_app_settings` becomes `_validate_int_settings(spec, values)`.
    `spec` is `{field: (minimum, maximum)}` and `values` is a dict. It returns
    `(clean, errors)` keyed by field, as today.
  - `/app` passes `{"upload_max_mb": (1, 100)}` and the body, so its contract
    is unchanged.
  - The notifications route passes the grade bounds and
    `body.get("escalate_minutes")`. When that is not an object, it answers
    one 400 on the field `escalate_minutes`: "Enter the three times."
    Otherwise each error is prefixed, e.g. `escalate_minutes.A`, so the card
    shows it beside its box.
  - `escalation_minutes(cur)` returns `{"A": 10, "B": 30, "C": 60}`.
    `alerts.py` calls it and passes the dict to `alerts_core`, which stays
    pure.
  - A `GET` and `PUT /api/settings/notifications` pair, like the label
    settings, plus the "set up / devices" line.
  - S023's settings use the same pattern: its own dict and validator call.
- `config.py` and `example_secrets_app.py`: `VAPID_PUBLIC_KEY`,
  `VAPID_PRIVATE_KEY` and `VAPID_SUBJECT` (a `mailto:` address), each read
  with an empty default.
  - Empty means **push is off**. The page then shows *not set up on this
    server*, and `ticket_alert` fans out no `push_send`.
  - The impl report gives the field names for the devops template (§ 5.6).
  - The public key's wire form is the raw 65-byte uncompressed P-256 point,
    base64url without padding (87 characters). That is what the browser's
    `applicationServerKey` takes (BR1-06).
- `config_rbac.py`: `push:subscribe` = `('*',)`, any logged-in role. The
  routes also need a Team record (§ 6).
- `pyproject.toml`, `uv.lock`, `sbom/`: **`pywebpush`** (§ 7.3), regenerated
  and committed with it.
- `tooling/dev/make_vapid_keys.py` (new): prints a fresh key pair as the three
  lines to paste into `secrets_app.py`, for dev and once for production. It
  prints the public key in the wire form above.
- `tooling/e2e/e2e_backend.py`: generates a key pair at start and sets the
  `config.VAPID_*` values in-process, so the e2e stack has push **on**
  (BR1-06).
- Wire forms both sides must agree on (BR2-12):
  - the **private** key in `secrets_app.py` is the raw 32-byte P-256 scalar,
    base64url without padding (43 characters), as
    `py_vapid.Vapid.from_string` reads it and `make_vapid_keys.py` prints it;
  - `endpoint_hash` is the lowercase hex of SHA-256 on both sides: the page's
    `crypto.subtle.digest` and the server's `hashlib`.

### Frontend

- `public/manifest.webmanifest`, with `id: "/"` and `scope: "/"`, so Chrome
  treats later versions as the same app (BR1-15). Also `public/sw.js` and
  `public/icons/*.png`. All are new; `public/` is new in this repo, and Vite
  copies it as it is.
- `index.html`: the manifest link, `theme-color`, `apple-touch-icon`,
  `mobile-web-app-capable` beside the older `apple-mobile-web-app-capable`,
  and `apple-mobile-web-app-title`.
- `sw.js` (BR1-16, BR3-02, BR3-12):
  - `push` shows the alert with `tag: "ticket-<id>"` and `renotify: true`.
    The escalation then replaces the breakdown's alert instead of stacking a
    second one.
  - `notificationclick` focuses an open Yantra window and navigates it to the
    ticket (`clients.matchAll` → `focus()` + `navigate(path)`), else calls
    `openWindow(path)`. The payload carries a **path**, which resolves against
    the service worker's own origin.
  - `install` calls `self.skipWaiting()` and `activate` calls
    `clients.claim()`. A new `sw.js` then takes over at once, instead of
    waiting until every Yantra tab is closed. With no `fetch` handler, this
    cannot break a page.
- `src/push.js` (new): registers the service worker at start-up, subscribes
  and unsubscribes, and reads the permission and standalone state. It is the
  only file that touches `navigator.serviceWorker` or `PushManager`.
- `src/views/NotificationsView.vue` (new) and its route `/notifications`.
- `src/components/AppTopbar.vue`: the bell icon button (44 px) with its dot
  (BR1-03).
  - The bell shows only with `push:subscribe` in `userPermissions`, as the
    nav items do (BR3-13).
  - The dot is set at start-up, after `/api/auth/me`, from `GET
    /api/push/config` (`enabled`, `you_get`) and `GET
    /api/push/subscriptions?endpoint_hash=` (`this_device`), by the rule of
    § 1.3 (BR2-05, BR3-06).
  - The dot's flag is shared state. *My notifications* updates it on *Turn
    on*, *Turn off* and *Remove* of this device (BR3-06).
  - The page finds `this_device` itself: the SHA-256 of
    `pushManager.getSubscription().endpoint`, made with `crypto.subtle` and
    sent as the `endpoint_hash` query (BR1-18). `crypto.subtle` exists under
    HTTPS and on `localhost`, the only places push works.
- `src/views/settings/NotificationsSettings.vue` (new): the card on the
  Settings page.
- `stores/auth.js`: sign-out first removes this device's subscription. This
  is best effort: a failure never blocks sign-out.

### Tests

- `backend/tests/test_alerts_core.py` and `test_push_core.py` (pure).
- `test_push_api.py` and `test_alerts.py`: enqueue on raise, regrade and
  send-back; fan-out; escalation; send outcomes with a fake sender.
- `test_worker.py`: `NoRetry`, `RetryLater` and `mark_failed`'s delay.
- `test_rbac.py` (the new key) and `test_settings_api.py` (the three
  settings; `/app` unchanged).
- A migration test, `test_migration_<n>.py`, for the table.
- A session fixture generates a VAPID pair with `py_vapid` and monkeypatches
  `config.VAPID_*`. One test runs with them empty, for `enabled: false`
  (BR1-06).
- S025's v20 equivalence and dev-path tests must build v20 alone. If they
  still run the full list when this step is coded, pin them to v20 without
  loosening their assertions (S019 BR2-01, BR3-08).
- `frontend/e2e/notifications.spec.js` (new), and a few lines in
  `settings.spec.js` and `screens.spec.js` (§ 8).

### Docs

- `.claude/CLAUDE.md`: a *Notifications (S021)* bullet — PWA without caching,
  the push tasks, the address allow-list, the VAPID secrets.
- `docs/Plan.MD` § 4.7 (who gets what, as decided), § 9 Q2 (decided values).
- `docs/Maintenance-Philosophy.md` § 8: the escalation values once decided.

## 4. Data model (the next free migration version when coded, BR1-17)

### 4.1 `push_subscriptions`

| Column | Type | Notes |
|---|---|---|
| `id` | INT PK | |
| `person_id` | INT NOT NULL | FK `people.id` — whose alerts this device gets |
| `endpoint` | VARCHAR(1000) NOT NULL | the push address the browser gave |
| `endpoint_hash` | CHAR(64) NOT NULL | SHA-256 of `endpoint`, lowercase hex, **UNIQUE** — one row per device (endpoints are too long for a unique index) |
| `p256dh` | VARCHAR(200) NOT NULL | the browser's public key (base64url) |
| `auth` | VARCHAR(100) NOT NULL | the browser's auth secret (base64url) |
| `label` | VARCHAR(100) NOT NULL | "Android · Chrome", from the user-agent; "Unknown device" when it gives nothing (BR2-12) |
| `created_at` | DATETIME NOT NULL | |
| `last_sent_at` | DATETIME NULL | last successful send |
| `last_error` | VARCHAR(255) NULL | last failed send's reason, cleared on success |

Index `ix_push_subscriptions_person (person_id)`.

The `p256dh` and `auth` values are the browser's keys for encrypting *to* it:
they let someone send to that device, nothing more, so they are stored like
any other row (not secrets), and they are never sent back to the browser.

### 4.2 Settings (`app_settings`, no schema change)

`escalate_minutes_a` 10, `escalate_minutes_b` 30, `escalate_minutes_c` 60 —
each 5 to 1440, through their own dict `_ESCALATION_SETTINGS` (§ 3; not
`_APP_SETTINGS`, whose `/app` route validates every key it holds, BR1-02).

## 5. Rules

### 5.1 Tasks and sends (job queue, S013)

- **`ticket_alert`** `{ticket_id, kind, event_id, exclude_person_ids,
  minutes?}`.
  - `kind` is `breakdown`, `defect` or `escalation`. `event_id` is the event
    that caused the alert (BR2-01). `minutes` comes only with an escalation,
    carried from `ticket_escalate`'s payload, so the text says how long the
    ticket waited (BR1-08).
  - The handler reads the ticket, its unit, its **site** and the causing
    event once. It puts them into the **`ticket_facts`** dict, which every
    text is built from (BR2-11).
  - `ticket_facts` holds: serial, site code, unit code, machine code and
    name, component code, intensity, state, symptom label, description cut at
    80, the display name (§ 1.4), the causing event's type, time and remark
    (cut at 80), and `occurred_at`.
  - It also holds two links (BR3-02):
    - `path` is `/tickets/<id>`. The push carries it, and the service worker
      resolves it against its own origin. So it works on production, on the
      dev server and on the e2e stack.
    - `url` is `label_base_url(cur)` plus `path`, read once here. S023's
      group message uses it, with no second read.
  - It sends only when **`alerts_core.should_send(kind, state)`** allows it
    (BR2-04). `breakdown` and `defect` send while the ticket is raised,
    acknowledged, scheduled (S019) or in progress. `escalation` sends while
    the ticket is not closed. So a worker that drains its queue an hour late
    does not wake the supervisor for a machine already back in service.
  - Otherwise it finds the recipients (§ 5.2) and their subscriptions. It
    enqueues one **`push_send`** per subscription, with the text already
    built.
  - The fan-out runs in the worker's transaction. So it is all or nothing,
    and a retry of `ticket_alert` never doubles it.
  - With push off (no keys), it finds no channel and is done. S023 adds the
    group as a second channel here.
- **`push_send`** `{subscription_id, title, body, path, urgency, silent, tag,
  ttl}`, with `max_attempts = 3`.
  - A send to a subscription that no longer exists is done.
  - The push service's answer gives the outcome, under the rules in the next
    bullet:
    - 201 or 202: done. `last_sent_at` is set and `last_error` is cleared,
      committed with `mark_done`.
    - **404 or 410** (the device unsubscribed, or its browser data was
      cleared): the subscription row is **deleted**; done.
    - 400, 403 or 413 (our fault: the payload or the keys): `last_error` is
      recorded, then **`NoRetry`**.
    - 429 with `Retry-After` as a whole number of seconds: `last_error` is
      recorded, then `RetryLater(message, that many seconds)`. The cap is
      `mark_failed`'s (§ 3). A `Retry-After` given as an HTTP date, or
      anything else that is not a whole number, counts as absent (BR2-03).
    - 429 without it, 5xx, a timeout (10 s, BR2-07) or a connection error:
      `last_error` is recorded, then an ordinary exception, which uses the
      existing back-off.
  - An alert's push lives for 1 hour, and the test's for 5 minutes. A
    breakdown alert that reaches a phone switched on the next morning helps
    nobody.
- **How a send task reports its outcome** (BR1-01; S023's `telegram_send`
  follows the same rules):
  - The worker runs a task in one transaction and rolls it back when the task
    raises.
  - So a task that must keep a failure record on its own row (here the
    subscription's `last_error`) **writes it and commits before raising**.
    That is the only write it makes before the raise. The access-log purge
    already commits on its own; it is the documented exception in
    `task_handlers`.
  - It does this on **every** failed attempt, so it needs no attempt number.
    The task row's `last_error` keeps the history.
  - The exception it raises says what happens next:
    - `NoRetry(message)`: the task fails at once, with no retry. The other
      side refused the request as given. `BadTask` stays for "the task itself
      is malformed".
    - `RetryLater(message, after_seconds)`: retry after that delay instead of
      the back-off, through `mark_failed(..., delay_seconds=…)`, capped at 1
      hour there. It still counts against `max_attempts`. With no attempt
      left, the task fails and the delay is ignored.
    - any other exception: retry with the existing back-off.
  - In each case `str(exc)` is what `mark_failed` stores, as `_task_failed`
    does for every exception today.
- **`ticket_escalate`** `{ticket_id, trigger_event_id, minutes}`, enqueued
  with `scheduled_for` = now + the grade's `minutes` (§ 5.3).
  - The handler locks the ticket row.
  - It escalates only if `alerts_core.should_escalate(state, intensity,
    latest_critical_event_id, trigger_event_id)` is true. To escalate, it
    enqueues a `ticket_alert` of kind `escalation`, with `minutes`.
  - The test is: the ticket is still **raised**, still **critical**, and
    **the latest `ticket_events` row with `intensity = 'critical'` has `id =
    trigger_event_id`** (BR1-12). The events that carry an intensity are
    `raised`, `regraded` and `sent_back`.
  - So a defect regraded critical, then down to degraded, then critical
    again, escalates once, from the last time. Otherwise the task is done.
- Retries: these are internal, idempotent tasks, and the base allows
  automatic retry only for those. At worst, a push resent after a timeout
  shows twice.

### 5.2 Who gets an alert

A person gets an alert when **all** of these hold:
- They are active in Team. (`people.username IS NOT NULL` is for `you_get`
  and the tests. In the fan-out, the join to `push_subscriptions` already
  ensures a login, BR3-15.)
- They have a membership at the **ticket's site** (the site of
  `tickets.unit_id`, as for every ticket check), and its role is in the
  kind's audience:
  - `breakdown`: `maint_engineer`, `maint_supervisor`, `maint_manager`;
  - `defect`: `maint_engineer`;
  - `escalation`: `maint_engineer`, `maint_manager`.
- That membership covers the ticket's unit (`all_units`, or a `person_units`
  row for it). This is the same unit access that lets them see the ticket.
- They are not in `exclude_person_ids` (BR1-05, BR1-13). That list holds the
  person whose action set off the alert: the raiser, or whoever regraded the
  ticket or sent it back (`people.username` = the acting login). For
  `breakdown` and `defect` it also holds the ticket's `reported_by_id`. An
  escalation leaves nobody out.

Roles are matched **exactly**, not through the ladder (`ROLE_INCLUDES`). A
manager inherits the engineer's *permissions*, but the audience is a list of
roles the user chose. So "engineers quietly" does not reach managers (§ 9
Q4). `it_admin` (a token role) gets no ticket alerts.

### 5.3 When tickets enqueue

Tickets enqueue in the same transaction as the ticket change (base:
auto-enqueue on a status change). They enqueue **always**, whether or not push
is set up (BR1-08). The handler finds the channels, so `tickets.py` has no
`if` for them, and S023 needs no change here. Every alert leaves its
`task_queue` row, and a failed alert shows in the failed count on Settings ›
Background tasks (BR2-09).

- **Raise**, state raised, intensity **critical** → `ticket_alert breakdown`,
  and `ticket_escalate` at now + the minutes for the item's grade.
- **Raise**, intensity degraded or initial → `ticket_alert defect`.
- **Raise with *Already fixed*** (back in service at once) → nothing.
- **Regrade to critical** (*Machine stopped*):
  - while **raised** → `ticket_alert breakdown` and `ticket_escalate`;
  - while acknowledged, scheduled (S019) or in progress → `ticket_alert
    breakdown` only. Someone already owns it, and a scheduled ticket never
    escalates (BR1-04).
- **Send back with *Machine down again?* = yes**, whatever the ticket's
  intensity was → `ticket_alert breakdown` only, with no escalation (BR1-05,
  BR2-01). The state becomes in progress.
  - The trigger is the move's answer, `clean["machine_down"]`, not the
    event's intensity. A ticket that was already critical gets a `sent_back`
    event with no intensity, and that is the commonest *down again*.
  - The call sits in `_apply_move`, after `_add_event` (§ 3, BR3-04).
  - *Machine running* sends nothing.
- Every other move → nothing.

The grade is the effective criticality of the ticket's item: the component's
own grade, if the ticket names a component and it has one, else the
machine's (`equipment_core.effective_criticality`). It is read at enqueue
time, so a setting changed later does not move an escalation already queued.

### 5.4 The push address check

At subscribe, the address must be `https://`, with no user-info and no port.
Its host must be one of these, or a sub-domain of one:
- `fcm.googleapis.com`: Chrome and Edge on Android;
- `push.apple.com`: Safari and iOS;
- `push.services.mozilla.com`: Firefox;
- `notify.windows.com`: Windows.

Anything else gets a 400: "This browser cannot get notifications. Use Chrome
on Android, or open Yantra from the Home Screen on an iPhone." (BR3-09). The
server logs the refused host, never the full address, so a refused browser
can be added later. The sender checks the address again before it posts. The
list is a constant in `push_core.py`, with a comment naming each browser.

**Samsung Internet** (BR3-05) is the default browser on Samsung phones, and it
may use a push service of its own. Its host goes on the list only once a real
subscription shows it. A device row (§ 8) turns alerts on in a Samsung
phone's default browser. If Yantra refuses it, the log gives the host, and
adding it is a one-line amendment. Until then the refusal tells the person to
use Chrome (§ 9, assumption 8).

### 5.5 Who may do what

- Subscribe, list and remove **their own** devices, and send themselves a
  test: any logged-in role with a Team record (`push:subscribe`).
- A person without a Team record sees that state on the page first (§ 1.3,
  BR2-08). The backend still guards subscribe with a 409, since they would
  get nothing: "You are not in Team. Ask IT admin to add you."
- `DELETE /api/push/subscriptions/<id>` removes only the caller's own rows.
  Someone else's id gets a 404, not a 403, so nobody can tell which ids
  exist.
- `POST /api/push/subscriptions/remove` with an endpoint removes that row
  **whoever owns it** (BR3-03). Presenting the endpoint proves the caller
  holds the device: the endpoint is the browser's own address, and nobody
  else has it. This is what makes a handed-over phone go quiet. A's session
  ended without sign-out; B signs in on the phone and signs out; A's row goes.
- Re-subscribing a device already in the table (same endpoint) **moves it**
  to the current person and refreshes its keys. The phone now belongs to
  whoever signed in last.
- Escalation times: `settings:edit` to change them (IT admin), and
  `settings:read` to see them (manager, IT admin).

### 5.6 Secrets and set-up

- `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY` and `VAPID_SUBJECT` live in
  `secrets_app.py`. Dev and test get their own pair from
  `make_vapid_keys.py`.
- **Production's pair is made once and never rotated casually.** A new pair
  silently invalidates every subscription, and each phone must turn
  notifications on again.
- The impl report gives the three field names and placeholder lines for
  `smtw_erp_devops/erp_server/yantra/secrets_app.py.j2`. The user adds them
  there (CLAUDE-COMMON: production is the user's).
- The worker container needs **outbound HTTPS** to the push services (§ 9
  Q5).
- **Phone set-up** (U1). The impl report gives a short set-up list, also added
  to `docs/steps/device-checks.md` for IT Admin:
  1. On Android, open Yantra in **Chrome**, not Samsung Internet, and tap
     *Install app*.
  2. On a Samsung phone, open Settings › Battery › Background usage limits.
     Check that Chrome is not in *Sleeping apps* or *Deep sleeping apps*.
     A sleeping Chrome holds alerts back.
  3. On an iPhone (iOS 16.4 or later), open Yantra in Safari, tap *Share ›
     Add to Home Screen*, and open it from the icon.
  4. In Yantra, open *My notifications*, tap *Turn on for this phone*, then
     *Send a test*.

## 6. API

| Method and path | Key | Does |
|---|---|---|
| `GET /api/push/config` | `push:subscribe` | `{enabled, public_key, you_get: ["Breakdowns and defects at SMTW.MCC2, escalations", …]}`. `enabled` is false when the keys are missing; `you_get` comes from `alerts_core.you_get` (BR2-06) |
| `GET /api/push/subscriptions` | `push:subscribe` | `{items: [{id, label, created_at, last_sent_at, last_error, this_device}], total}`, mine only. `this_device` is true on the row whose hash matches the `endpoint_hash` query. A query that is not 64 lowercase hex characters gives `this_device` false on every row, not a 400 (BR3-15) |
| `POST /api/push/subscriptions` | `push:subscribe` | `{endpoint, keys: {p256dh, auth}}` → 201 with the row (upsert by endpoint, § 5.5). The server makes the label from the request's `User-Agent`; the body carries none (BR3-10) |
| `DELETE /api/push/subscriptions/<id>` | `push:subscribe` | removes one of mine; someone else's → 404 |
| `POST /api/push/subscriptions/remove` | `push:subscribe` | `{endpoint}`: removes that device's row, **whoever owns it** (sign-out, *Turn off*; § 5.5, BR3-03); 204 also when there is none |
| `POST /api/push/test` | `push:subscribe` | enqueues a test to my devices → `{devices: N}`; 409 "Turn notifications on first." when N = 0 |
| `GET /api/settings/notifications` | `settings:read` | `{escalate_minutes: {A, B, C}, push_enabled, devices}` |
| `PUT /api/settings/notifications` | `settings:edit` | `{escalate_minutes: {A, B, C}}`; errors on `escalate_minutes` or `escalate_minutes.A` … (BR2-02). One PUT for the whole card, which S023 extends |

## 7. Design decisions

1. **Web push, with no third party** (Plan.MD § 4.7). *Rejected:* Firebase
   Cloud Messaging's own SDK or OneSignal (an account, a tracker in the page,
   data with a vendor); SMS (cost, a gateway, no tap-to-open).
2. **A service worker that caches nothing.** Push needs a service worker. But
   any caching would fight the stale-bundle rule (base § Stale bundle
   detection) and the online-only decision: an old cached `index.html` is the
   exact problem that rule exists for. With no `fetch` handler, every page
   load goes to the network as today. nginx's existing `location /` serves
   `sw.js` with `no-cache`, and `skipWaiting` lets a new one take over at once
   (BR3-12). *Rejected:* `vite-plugin-pwa` or Workbox, a new npm dependency
   whose main feature, precaching, we do not want.
3. **`pywebpush` for sending.** It is the reference Python library of the W3C
   web-push-libs group. It does the RFC 8291 encryption and the RFC 8292
   VAPID signature.
   - It is **a new dependency** (CLAUDE-COMMON *Dependency health*). The
     coder adds it only if S022's check passes: a release within 12 months,
     and no open high vulnerability. The impl report lists what it pulls in
     (py-vapid, http-ece and an HTTP client).
   - If it fails the check, the coder stops and asks.
   - *Rejected:* writing the encryption and signing by hand on `cryptography`.
     That is security code the project would own. It is an option only if
     `pywebpush` fails the check, and then it is the user's decision.
4. **Fan-out in the worker, one task per device.** The request only enqueues
   (base: never make the user wait for an external call). With one
   `push_send` per device, one dead phone retries alone and the others are
   not sent again. *Rejected:* one task sending to everyone (a retry resends
   to all); sending from the request (a slow push service delays the raise).
5. **Escalation counts from the time the breakdown is recorded.** It is a
   delayed task (`scheduled_for`) that checks the ticket again when it runs.
   *Rejected:* counting from the typed event time (a late entry escalates at
   once, waking the manager for a stop already handled); a job every minute
   over all open tickets (more queries, same result).
6. **The audience by exact role** (§ 5.2), from the user's answer, so
   "engineers quietly" means engineers. *Rejected:* the role ladder (managers
   would get every quiet defect too).
7. **Subscriptions belong to the person, and the device follows the last
   sign-in.** *Rejected:* subscriptions per username (a renamed login would
   orphan them); keeping the old owner on re-subscribe (a handed-over phone
   would ring for two people).
8. **Escalation times are settings in Settings › Notifications** (Plan.MD Q2:
   "stored as settings, not code"). IT admin edits them like the other
   settings, in their own settings dict (BR1-02). *Rejected:*
   `company_settings.py` constants (a change would need a release); adding
   them to `_APP_SETTINGS` (it breaks the Uploads card's save); a `/app` route
   that takes partial bodies (it changes an existing contract for no reason of
   its own).
9. **One set of rules for how a send task reports its outcome** (BR1-01;
   S023 uses it too). The task commits its own failure record before it
   raises. The exception's type says what happens next: `NoRetry`,
   `RetryLater`, or any other. *Rejected:* passing the attempt number to the
   task so it decides "last attempt" (more change to S013's worker for little
   gain); a task that never raises and enqueues itself again (it duplicates
   the queue's retry).
10. **Always enqueue the alerts** (BR1-08). The ticket path does not know
    which channels exist; the task does. *Rejected:* enqueuing only when push
    is set up. S023 would have to change it to "push or Telegram", and an
    alert with no channel would leave no trace.
11. **A bell in the top bar** for *My notifications* (BR1-03). It has a dot
    only when the person would get alerts and this device is off, blocked or
    an iPhone not on the Home Screen (BR2-05, BR3-06). *Rejected:* a
    bottom-nav item (every item shrinks on a 360 px phone); a user dropdown
    (a new component for two items); a dot for everyone whose device is off
    (a technician's or IT admin's dot would never go out); a dot when push is
    not set up on the server (nobody on the floor can fix it); a "seen" flag
    per device in `localStorage` (more state, and a reset phone nags again).

## 8. Tests and acceptance

### Pure (`test_alerts_core.py`, `test_push_core.py`)
- The audience per kind; exact-role matching; the left-out persons (actor,
  reported-by).
- Escalation minutes per grade, defaults and bounds; the component's grade
  wins over the machine's; NULL inherits.
- The address check: each allowed host and a sub-domain pass. `http://`, an
  IP, a look-alike host (`fcm.googleapis.com.evil.example`), a port and
  user-info are refused.
- Alert text: symptom label, description cut at 80, no description; the
  escalation's title with its minutes; `path` and `url` (BR3-02).
- `should_escalate`: raised + critical + the same trigger → yes.
  Acknowledged, scheduled, started, back in service, closed, regraded down,
  or a later trigger → no.
- `should_send`: `breakdown` and `defect` in raised, acknowledged, scheduled
  and in progress → yes; back in service and closed → no; `escalation` until
  closed (BR2-04).
- `you_get`: engineer, supervisor and manager at one and two sites;
  technician; IT admin; the empty list (BR2-06).
- The display name: reported-by first, then the raiser's Team name, then the
  login (BR2-11).
- The push service's answers: 201, 404, 410, 400, 403, 413, 429 with and
  without `Retry-After`, 429 with an HTTP-date `Retry-After` (counts as
  absent), 503.
- The label from a few real user-agent strings.

### API and tasks (`test_push_api.py`, `test_alerts.py`; fake sender)
- Subscribe, list (mine only), remove. Someone else's id → 404. No Team
  record → 409. A bad address → 400, and the log names the host only. A
  re-subscribe moves the row.
- `remove` by endpoint deletes the row of **another** person too (BR3-03).
- An `endpoint_hash` query that is not 64 hex characters → 200 with
  `this_device` false everywhere (BR3-15).
- The test send → N devices, or 409 with none.
- Push off (no keys) → `enabled: false`; an alert's `ticket_alert` runs and
  enqueues no `push_send`. `GET /api/push/config`'s `public_key` is 87
  characters.
- Raise critical → `ticket_alert breakdown` + `ticket_escalate`, with the
  grade's delay and minutes. Raise a defect → `ticket_alert defect` only.
  Raise *Already fixed* → nothing.
- Regrade to critical while raised → both; while in progress → the alert
  only.
- Send back with *Machine down again?* = yes → the alert only, tested twice:
  on a **critical** ticket (its event carries no intensity) and on a
  **degraded** one (its event carries critical). The alert's `event_id` is the
  `sent_back` event's (BR2-01, BR3-04). *Machine running* → nothing.
- Fan-out: the right people per kind at the unit each get one `push_send` per
  device. The cases: an all-units membership, a `person_units` row, a person
  at another unit, at another site, an inactive person, and the raiser.
  - These tests seed real `people`, `memberships` and `person_units` rows for
    the recipients, because the harness's site role is a wildcard in
    `g.user`, not a row (BR2-10).
  - The acting login is matched through `X-Test-User` = `people.username`.
- A `breakdown` alert drained after the ticket went back in service sends
  nothing (BR2-04).
- Escalation fires when the ticket is still raised. It is skipped after
  acknowledge, start, back in service, not a fault, regrade down, and a newer
  trigger.
- Send outcomes:
  - 201 sets `last_sent_at`; 410 deletes the row;
  - 400 sets `last_error`, which is still there after the rollback, and the
    task fails without retry;
  - 429 with `Retry-After: 120` is pending again about 120 s later;
  - 503 retries with the back-off;
  - a closed ticket's alert sends nothing.
- Worker: `NoRetry` → failed after one attempt; `RetryLater` → pending with
  its delay; a delay over 3600 s is capped; `RetryLater` on the last attempt
  → failed, delay ignored (`test_task_queue.py`, BR2-03); `BadTask`
  unchanged.
- The sender passes `timeout=10` to `webpush` (BR2-07). It reads the keys at
  call time: a test sets `config.VAPID_*` after import and the send uses them
  (BR3-11).
- Settings: read and edit by key, and bounds. `PUT /api/settings/app` with
  `upload_max_mb` alone still gives 200 (BR1-02). RBAC rows in
  `test_rbac.py`.

### Automated (e2e)
What each S024 project checks (BR1-10):
- **Desktop and Pixel 7 Chromium**: *My notifications* opens for every seed
  person with a Team record and shows *Turn on for this phone* (BR3-01).
  - With `grantPermissions(["notifications"])` the page reaches the subscribe
    call.
  - Headless Chromium usually has no push account, so `subscribe()` may
    fail. The test accepts the error line, and seeds the device row through
    the API instead.
- **iPhone 14 WebKit**: the page's own rule, "an iPhone not running from the
  Home Screen", shows the *Add to Home Screen* explanation under the iPhone 14
  emulation. The bell shows its dot for an engineer there (BR3-06). The test
  checks that rule, not whether the engine exposes `PushManager`, so a
  Playwright update does not break it (BR2-14).
- **Denied**, on desktop Chromium: `page.addInitScript` redefines
  `Notification.permission` as `"denied"`, and the page shows how to unblock.
  Playwright cannot deny a permission, so it is stubbed.

And on every project:
- The **bell** shows on every screen, and tapping it opens *My
  notifications*.
- The dot shows for an engineer whose device is off, and not for a
  technician or IT admin (BR2-05). After *Turn on* succeeds (the device row
  seeded through the API), the dot goes out without a reload (BR3-06).
- IT admin (`e2e_it_admin`, who has no seed Team record) sees "You are not in
  Team. Add yourself in Masters › Team to get test messages." and no *Turn
  on*. A non-IT login with no Team record (an `X-Test-User` with no seeded
  person) sees "You are not in Team. Ask IT admin to add you." (BR2-08,
  BR3-01).
- A device seeded through the API shows in *My devices*. *Remove* asks
  "Remove …? — Yes / No", and *Yes* removes it (BR3-07). *Send a test*
  reports "Sent to 1 device".
- Settings › Notifications: IT admin changes B to 20, and it stays after a
  reload. The manager sees the values read-only. 4 is refused on the field.
- The manifest is served and parses. The service worker registers
  (Chromium).

The `no-cache` header on `sw.js` is nginx's, which Vite does not serve, so it
is an after-deploy row instead (BR1-07).

### On a real device
These need **HTTPS**, so they run on **production, on the TEST machine**
(`SMTW.MCC2`, S024 § 1.6), after the release. The dev server on KLA's laptop
is plain HTTP over the LAN, where browsers refuse push (`localhost` only).

Important:
- [ ] **Android, Chrome**, as an engineer test login, on **mobile data**:
  *Turn on for this phone*, then *Send a test*. It arrives with sound, and
  tapping it opens Yantra.
- [ ] **Samsung Galaxy, Chrome**, set up as in § 5.6, as an engineer test
  login. Leave the phone untouched, with the screen off, for at least one hour.
  Then the operator test login raises a breakdown on the TEST machine. The
  phone rings within a minute. This proves the battery setting holds (U1).
- [ ] **iPhone (iOS 16.4+)**, KLA's own, as an engineer test login, on **mobile data**:
  *Add to Home Screen*, open from the icon, log in through Keycloak, *Turn
  on*, then *Send a test*. It arrives, and tapping it opens Yantra. Do this
  check **from the Home Screen icon only**. In a Safari tab the page explains
  the Home Screen step instead, which is not a failure (BR2-13).
- [ ] The engineer's and the supervisor's phones are turned on as in the two
  rows above, on **mobile data**. The **operator test login**, on any
  network, raises a **breakdown** on the TEST machine. Both phones ring within
  a minute, and tapping opens that ticket. This proves the path from outside
  the plant (BR3-14).
- [ ] The operator test login, on any network, raises a **defect**. The
  engineer's phone gets it **without sound** on Android. iOS may show it with
  sound; note what it does.
- [ ] **IT admin**, on the **company network** (S013), on production: in
  Settings › Notifications, set grade C (the TEST machine's grade) to 5
  minutes (BR1-11).
- [ ] Then the **engineer and manager test logins**, phones on mobile data,
  and the **operator test login** raising on the TEST machine: raise a
  breakdown and wait 6 minutes. Both phones ring "Not acknowledged after 5
  min". A second breakdown acknowledged before the time sends nothing. IT
  admin then sets C back (BR3-14).
- [ ] **Sign out** on the engineer's phone. Then the **operator test login**,
  on another device, raises a breakdown on the TEST machine. The signed-out
  phone gets nothing (BR2-13).

Plain:
- Install on Android (*Install app*) shows the Yantra icon, and the app opens
  without the browser bar.
- After deploy: open `<production address>/sw.js` in the browser's network
  panel and read `Cache-Control: no-cache` (BR1-07). In the same panel, read
  the manifest's `Content-Type`. If it is `application/octet-stream`, add
  `types { application/manifest+json webmanifest; }` to `nginx.conf`
  (BR3-12).
- From a desktop, remove the phone in *My devices*. The phone gets nothing
  after.
- **Samsung phone, default browser (Samsung Internet)**, as an engineer test
  login: *Turn on for this phone*. Note whether it is refused. If it is, the
  server log names the push host, for a one-line amendment (BR3-05).

### Acceptance
`tooling/run-tests.bat` is green. `tooling/run-e2e-tests.bat` is green. `npx
vite build` shows no new errors. `tooling/run-deps-audit.bat` exits 0 with
`pywebpush` added and `sbom/` regenerated.

## 9. Open questions and assumptions

1. **Escalation times** (Plan.MD Q2). Proposed: **A 10, B 30, C 60
   minutes** after the breakdown is recorded. Are these right, or do you want
   other values?
2. **Who gets the escalation, and how often.** Proposed: **engineers and
   managers** of the unit, **once**.
   - Alternative: managers only. The engineers already had the first alert.
   - Alternative: a second escalation after twice the time, e.g. to all
     managers of the site.
3. **Technicians get nothing in this step.** Your list names engineers,
   supervisors and managers, so this is assumed deliberate: the engineer
   assigns (S018). Should technicians get *Job assigned to you* now? Plan.MD
   § 4.7 lists it, and assignment exists since S018. Proposed: **yes, as a
   fourth kind**; it is small and uses the same machinery. Otherwise it waits.
4. **Managers and quiet defects.** By exact role, managers get no defect
   alerts (§ 5.2). Assumed right; say if managers should get defects too.
5. **Assumption: outbound network.** The worker container on customer7 can
   reach `fcm.googleapis.com` and `web.push.apple.com` over HTTPS. Confirm
   before the release; the device checks prove it.
6. **The app icon.** Proposed: the coder makes plain PNG icons with Pillow, a
   "Y" on the theme colour. Do you have a logo to use instead?
7. **Order.** This step is coded after S025 is committed. S023 is parked
   (U1).
8. **Samsung Internet** (BR3-05, settled by U1): every Android phone
   installs from Chrome (§ 5.6), so the refusal "Use Chrome on Android" is the
   intended answer there. The plain device row in § 8 still notes the host,
   in case Samsung Internet is wanted later.

## 10. Amendments

(none)

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 21-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR1-01 `push_send`'s outcomes cannot be recorded under the worker contract | major | **Accepted** (option 1, with `NoRetry`): the handler commits its failure record before raising, on every failed attempt; `NoRetry` and `RetryLater(after_seconds)` beside `BadTask`; `mark_failed` gains `delay_seconds`. One contract, which S023's `telegram_send` uses (§ 3, § 5.1, decision 9) |
| BR1-02 escalation minutes in `_APP_SETTINGS` break `PUT /app` | major | **Accepted** (option 1): `_ESCALATION_SETTINGS`, `_validate_int_settings(spec, body)` for both routes, `escalation_minutes(cur)`; a test that `/app` with `upload_max_mb` alone still saves (§ 3, § 4.2, § 8, decision 8) |
| BR1-03 there is no user menu | major | **Accepted** (option 1): a bell icon button in the top bar, with a dot when this device is off or blocked; the e2e line replaced (§ 1.3, § 3, § 8, decision 11) |
| BR1-04 S019's *scheduled* state and escalation | minor | **Accepted**: scheduled counts as acknowledged; a regrade to critical while scheduled alerts without escalating; `should_escalate` tests `== raised` (§ 1.5, § 5.3) |
| BR1-05 send back with the machine down notifies nobody | minor | **Accepted** (option 1): `ticket_alert breakdown`, no escalation; the actor of the triggering event is excluded, not only the creator (§ 1.4, § 5.2, § 5.3) |
| BR1-06 VAPID pair for dev, pytest, e2e; the key's wire form | minor | **Accepted**: pytest fixture with `py_vapid`, the e2e backend generates a pair, dev uses `make_vapid_keys.py`; raw uncompressed P-256 point, base64url, 87 characters (§ 3, § 8) |
| BR1-07 the `no-cache` check is nginx's | minor | **Accepted**: moved to an after-deploy device row (§ 8) |
| BR1-08 fit with S023: enqueue condition, module name, minutes | minor | **Accepted** (all three, plus the site read once): always enqueue; `alerts_core.py` channel-neutral, `push_core.py` push only; `minutes` carried into the escalation alert and its title (§ 1.4, § 3, § 5.1, § 5.3, decision 10) |
| BR1-09 renaming a device | minor | **Accepted** (option 1): rename dropped (route, dialog, test); the label is the browser's (§ 1.3, § 4.1, § 5.5, § 6) |
| BR1-10 the e2e states per project; how "denied" is produced | minor | **Accepted**: per-project assertions, the denied state stubbed, `subscribe()` may fail headless (§ 8) |
| BR1-11 the escalation device check needs IT admin on the plant network | minor | **Accepted**: two rows; mobile data on the Android and iPhone rows (§ 8) |
| BR1-12 "latest event that made it critical"; `_add_event` id | minor | **Accepted**: defined as the latest event with `intensity = 'critical'`; `_add_event` returns the id (§ 3, § 5.1) |
| BR1-13 who "raised it" is | nit | **Accepted**: the acting login's person and the reported-by person are excluded (§ 5.2) |
| BR1-14 standards wording | nit | **Accepted**: A 8.20 with OWASP; SMRP worded without a metric it does not have (§ 2) |
| BR1-15 manifest `id`/`scope`, `mobile-web-app-capable` | nit | **Accepted** (§ 3) |
| BR1-16 `notificationclick` focus, a `tag` per ticket | nit | **Accepted** (§ 3, § 5.1 payload) |
| BR1-17 migration number wording | nit | **Accepted**: "the next free version when coded", `test_migration_<n>.py` (§ 3, § 4) |
| BR1-18 who hashes the endpoint | nit | **Accepted**: the page, with `crypto.subtle` (§ 3) |
| BR1-19 IT admin and `maintenance_team`-only users | nit | **Accepted**: "Test messages only" for IT admin; the login-only user cannot reach the page, nothing to hide (§ 1.3) |
| BR1-20 grade meanings beside A/B/C; a card, not a tab | nit | **Accepted** (§ 1.6, § 3) |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 21-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR2-01 *Down again* fires only when the send-back changes the intensity | major | **Accepted**: the trigger is the move's answer `clean["machine_down"]`, whatever the intensity; called from `_apply_move`'s send-back step; `ticket_alert` carries `event_id`, so the text says *Down again* with its time; two tests, critical and degraded (§ 1.4, § 3, § 5.1, § 5.3, § 8). S023's group row follows (S023 BR2-04) |
| BR2-02 the shared validator's shape and the PUT body | minor | **Accepted** (option 1): `_validate_int_settings(spec, values)` with `{field: (min, max)}`; the nested body; a non-object `escalate_minutes` gives one 400; errors prefixed `escalate_minutes.A`. One card, one Save, one PUT, which S023 extends (§ 1.6, § 3, § 6) |
| BR2-03 `RetryLater`'s signature, the cap, `Retry-After` as a date | minor | **Accepted**: one signature `RetryLater(message, after_seconds)`; the cap in `mark_failed` (`TASK_RETRY_DELAY_MAX_SECONDS = 3600`); a `Retry-After` that is not a whole number counts as absent; on the last attempt the task fails and the delay is ignored, with a test (§ 3, § 5.1, § 8) |
| BR2-04 a late worker sends "Breakdown" for a machine back in service | minor | **Accepted**: pure `alerts_core.should_send(kind, state)`, with tests (§ 3, § 5.1, § 8) |
| BR2-05 what "on" means; the dot on devices that never ring | minor | **Accepted** (both, the recommended rule): "on" means a browser subscription **and** `this_device`; the dot shows only when *What you will get* is not empty and the device is off or blocked (§ 1.3, § 3, decision 11, § 8) |
| BR2-06 "What you will get" needs an endpoint | minor | **Accepted**: `you_get` in `GET /api/push/config`, built by `alerts_core.you_get` (§ 1.3, § 3, § 6, § 8) |
| BR2-07 the sender has no timeout | minor | **Accepted**: `webpush(..., timeout=PUSH_TIMEOUT_SECONDS)`, 10 s, a constant in `company_settings.py` (§ 3, § 5.1, § 8) |
| BR2-08 a user with no Team record meets the rule as a 409 after the tap | minor | **Accepted**: the page shows the *not in Team* state up front from `person_id`, with no *Turn on* and no dot; the 409 stays as the backend's guard; an e2e row (§ 1.3, § 5.5, § 8) |
| BR2-09 Background tasks does not show every alert | nit | **Accepted**: reworded. Every alert leaves its `task_queue` row; a failed one shows in the failed count (§ 5.3) |
| BR2-10 fan-out tests need real membership rows | nit | **Accepted** (§ 8) |
| BR2-11 whose name; the ticket facts dict | nit | **Accepted**: the name rule (reported-by, else the raiser's Team name, else the login; first name) and the `ticket_facts` dict, named once for both steps (§ 1.4, § 3, § 5.1, § 8) |
| BR2-12 wire details | nit | **Accepted**: the private key's form, `endpoint_hash` as lowercase hex, "Unknown device" as the label fallback (§ 3, § 4.1) |
| BR2-13 two device rows | nit | **Accepted**: the operator test login raises for the sign-out row; the iPhone row is done from the Home Screen icon only (§ 8) |
| BR2-14 the WebKit e2e asserts the page's rule | nit | **Accepted** (§ 8) |

### Round 3 — `2-brief-review-r3.md` (Fable), answered 21-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR3-01 IT admin is the *not in Team* user; two pages for her | minor | **Accepted** (option 1): the rule is by `person_id` only. IT admin with a Team record reads "Test messages only"; without one, she gets the *not in Team* state, worded for her ("Add yourself in Masters › Team to get test messages."). The e2e "every role" row covers seed persons with a Team record; the *not in Team* rows use `e2e_it_admin` and a login with no seeded person (§ 1.3, § 8) |
| BR3-02 `ticket_facts["url"]`: path or absolute address | minor | **Accepted**: `ticket_facts` carries `path` (`/tickets/<id>`, which the push and the service worker use) and `url` (`label_base_url(cur)` + path, read once in `ticket_alert`, for S023). The `push_send` payload carries `path` (§ 3 Frontend `sw.js`, § 5.1, § 8). S023 updated to read `url` from the dict |
| BR3-03 whose row `remove` by endpoint deletes | minor | **Accepted**: it deletes the row whoever owns it, since presenting the endpoint proves the caller holds the device; `DELETE …/<id>` stays mine-only with the 404; an API test (§ 1.2, § 5.5, § 6, § 8) |
| BR3-04 the send-back enqueue must follow `_add_event` | minor | **Accepted**: the call sits in `_apply_move` after `_add_event` returns the id, only when `move == "send-back"` and `clean["machine_down"]`; `_send_back` is unchanged (§ 3, § 5.3, § 8) |
| BR3-05 the allow-list refuses Samsung Internet | minor | **Accepted, both options in order**: the refusal says "Use Chrome on Android, or open Yantra from the Home Screen on an iPhone" and the server logs the refused host (host only). A device row turns alerts on in a Samsung phone's default browser; if it is refused, the logged host is added by a one-line amendment. The coder cannot subscribe from a real Samsung phone, so option 1 alone is not possible at coding time (§ 5.4, § 8, § 9 assumption 8) |
| BR3-06 the bell's dot on an iPhone in Safari; clearing it | minor | **Accepted**: the dot shows for *off*, *blocked* and *iPhone not on the Home Screen*, never for *not set up on this server* or *not in Team*; the page clears it when *Turn on* succeeds and sets it on *Turn off* or *Remove* of this device, through shared state (§ 1.3, § 3, decision 11, § 8) |
| BR3-07 *Remove* a device is one tap | minor | **Accepted**: the inline Yes/No confirm of the labour rows, with the consequence in the question; *Turn off* needs no confirm (§ 1.3, § 8) |
| BR3-08 S025's v20 tests and this step's migration | minor | **Accepted**: the S019 line added to § 3 Tests |
| BR3-09 writing style | minor | **Accepted**: the gate-A sections (§ 1, Out of scope, § 2, § 7, § 9) and § 3, § 5, § 8 rewritten to scope A: one idea per sentence, lists for parallel facts, finding tags at the end. A *Terms* block fixes one word each: *alert* (the message), *push* (the channel), *device* (a browser) with its *subscription* (the row), *acknowledged* = no longer raised; *notifications* stays as the screen word. "Send-handler outcome contract" became "how a send task reports its outcome". Scope-B messages now say what to do: "…Use Chrome on Android, or open Yantra from the Home Screen on an iPhone.", "Notifications are not set up on this server yet. Ask IT admin.", "Add Yantra to the Home Screen, then open it from the icon." |
| BR3-10 `label?` in the subscribe body | nit | **Accepted** (drop it): the server makes the label from the `User-Agent` header (§ 6) |
| BR3-11 read the VAPID keys at call time | nit | **Accepted** (§ 3 `push.py`, `push_sender.py`; a test in § 8) |
| BR3-12 `sw.js` take-over; the manifest's content type | nit | **Accepted** (both): `skipWaiting` on install and `clients.claim` on activate (§ 3, decision 2); the after-deploy row reads the manifest's `Content-Type` and names the nginx `types` line if needed (§ 8) |
| BR3-13 the bell on the "no access yet" screen | nit | **Accepted**: the bell shows only with `push:subscribe` in `userPermissions` (§ 1.3, § 3) |
| BR3-14 account and network for the raise rows | nit | **Accepted**: the operator test login raises, on any network; the engineer's and supervisor's phones are on mobile data (§ 8) |
| BR3-15 small cross-step and API details | nit | **Accepted** (all three): S023 § 9 Q7 now says card (S023's edit); a bad `endpoint_hash` query gives `this_device` false everywhere, no 400; the `people.username` condition is stated as for `you_get` and the tests (§ 5.2, § 6, § 8) |

### U1 — user decision, 21-10-2026 (before gate A)

"lets not do telegram now … for now, its PWA alone"; the team mostly uses
Samsung Galaxy, the user an iPhone → S023 parked; decision 4 in the header;
§ 5.6 phone set-up (Chrome, Samsung battery setting, iPhone Home Screen); § 8
a Samsung idle-phone device check, the iPhone row on KLA's phone; § 9 Q7 and
Q8. Not re-reviewed: no design change, set-up text and checks only.

### Gate A — approved 21-10-2026

"yes, approve S021 as proposed" → every § 9 answer as proposed: Q1 escalation
after A 10, B 30, C 60 minutes; Q2 once, to the engineers and managers of the
unit; Q3 *Job assigned to you* to the technician, as a fourth kind; Q4 no
defect alerts for managers; Q5 the worker reaches `fcm.googleapis.com` and
`web.push.apple.com` (proved by the device checks); Q6 a plain "Y" icon until
a logo exists; Q7 coded after S025, S023 parked; Q8 settled by U1 (Chrome on
Android). Baseline from r3's *Reviewed against:*.

