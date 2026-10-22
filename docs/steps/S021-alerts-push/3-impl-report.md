```
Step: S021 — Alerts: PWA and web push
Doc: impl-report
Author: Coder (Opus)
Date: 22-10-2026
```

# S021 — Implementation report

**Result: S021 and amendment A1 are built.** `tooling/run-tests.bat` is green, `npx vite build`
is clean, `tooling/run-deps-audit.bat` exits 0 with `pywebpush` added, and the full e2e suite
result is under *Tests run*. No real push has been sent yet: the device checks (§ 8 *On a real
device*) need HTTPS and run on production after the release.

## 1. What was built

- **An installable app (PWA).** `manifest.webmanifest` (id and scope `/`, standalone, theme
  colour `#1e293b`, icons 192, 512 and a 180 px Apple touch icon), the iOS meta tags in
  `index.html`, and a service worker `sw.js` that only shows a pushed alert and opens its
  ticket. It caches nothing and has no `fetch` handler.
- **Subscriptions per person and device** (`push_subscriptions`, migration **v24**), with the
  `/api/push` routes: config with *What you will get*, list, subscribe, remove one of mine,
  remove by endpoint (whoever owns it), and a test send.
- **My notifications** (`/notifications`), opened from a **bell** in the top bar on every
  screen. The bell has a **dot** when the person would get alerts and this device is off,
  blocked, an iPhone not on the Home Screen, or a browser without push.
- **The alerts**: new breakdown, defect became a breakdown, *down again*, new defect (quiet),
  escalation of a breakdown not acknowledged in time, a test, and (A1) *Job assigned to you*.
- **Escalation** per criticality grade of the ticket's item, after A 10, B 30, C 60 minutes,
  once, to the unit's engineers and managers.
- **Settings › Notifications**: a card with the three escalation times beside each grade's
  meaning, one Save, and a line saying whether push is set up and how many devices are on.
- **Sign-out removes this device's subscription**, best effort and bounded to 3 seconds.
- **`tooling/dev/make_vapid_keys.py`** prints a key pair for `secrets_app.py`.

## 2. How it works

### Backend

- **Pure core.**
  - `alerts_core.py` holds every rule about alerts, the same for every channel: the audience
    per kind (by exact role), what each ticket change enqueues (`raise_alert`,
    `regrade_alert`, `send_back_alert`, `ASSIGNED_ALERT`), who is left out, `should_send`,
    `should_escalate`, the minutes for the item's grade, the name rule, the `ticket_facts`
    dict, the alert texts and *What you will get* (`you_get`).
  - `push_core.py` holds the push-only rules: the address allow-list, the endpoint hash, the
    device label from the User-Agent, the mapping of the push service's answer to an outcome,
    and the push payloads.
- **Enqueue, in the ticket's transaction** (`tickets.py` → `alerts.enqueue_alert`).
  - The raise enqueues after the *Already fixed* block, and only when there is no *Already
    fixed* restore (BS1-09). A refused raise rolls its tasks back with it.
  - The regrade enqueues after its `regraded` event; the send-back in `_apply_move`, after
    `_add_event` returns the `sent_back` event's id, when `move == "send-back"`
    (`send_back_alert` decides from `machine_down`).
  - The *Assign* route enqueues `assigned` only when `_assign` added a new assignee (it now
    returns the event id, or None when the person was already assigned). `_auto_assign`
    (acknowledge, start) enqueues nothing.
  - An escalation reads the item's grades (plain read), the times from the settings, and
    queues `ticket_escalate` with `scheduled_for` = now + minutes.
- **Worker tasks** (`task_handlers.py`).
  - `ticket_alert` reads the ticket, unit, site and causing event once into `ticket_facts`.
    It stops when `should_send` says no, or when push is not set up. Otherwise it finds the
    recipients (`alerts.recipients`, or the one assignee for A1) and enqueues one `push_send`
    per device, in its own transaction.
  - `ticket_escalate` locks the ticket row and escalates when the ticket is still raised,
    still critical, and its latest critical event is the trigger.
  - `push_send` sends to one device through `push_sender.send` (the only `pywebpush` call,
    timeout 10 s). 201/202 sets `last_sent_at`; 404/410 deletes the device; 400/403/413
    records `last_error`, commits, raises `NoRetry`; 429 with a whole-number `Retry-After`
    raises `RetryLater(seconds)`; anything else raises an ordinary exception (back-off).
  - `worker._task_failed` treats `NoRetry` like `BadTask`, and passes `RetryLater`'s delay to
    `mark_failed(..., delay_seconds=…)`, which caps it at 3600 s and ignores it on the last
    attempt.
- **Settings.** `_validate_app_settings` became `_validate_int_settings(spec, values)`, used by
  `/app` (unchanged contract) and the new `/notifications` routes. The escalation times are
  their own dict `_ESCALATION_SETTINGS`; errors come back on `escalate_minutes.A` …, or on
  `escalate_minutes` when the value is not an object.
- **Keys.** `config.VAPID_*` are read at call time. Empty means push is off. The pytest session
  and each e2e lane make their own pair with `vapid_keys.make_key_pair()`.

### Frontend

- `src/push.js` is the only file that touches `navigator.serviceWorker`, `PushManager` and
  `Notification`. It registers `sw.js` at start-up (`main.js`) and turns every failure into a
  message for the page; it never logs to the console (BS1-08).
- `src/stores/notifications.js` holds the shared state: the config, my devices, whether this
  device is on, the device state and `showDot`. `App.vue` loads it once the user is known;
  *My notifications* loads it again and updates it on Turn on, Turn off and Remove.
- `AppTopbar.vue` shows the bell (44 px) with `push:subscribe`, and its dot from `showDot`.
- `NotificationsView.vue` shows the device state, Turn on / Turn off, My devices with Send a
  test and an inline Remove confirm, and What you will get.
- `views/settings/NotificationsSettings.vue` is the Settings card; after a refused save it
  calls `revealError(form)` (BS1-04).
- `stores/auth.js`: `logout()` first calls `forgetThisDevice()`.

## 3. Files touched

New (backend):
- `backend/alerts_core.py` — the pure alert rules (all channels).
- `backend/push_core.py` — the pure push rules.
- `backend/alerts.py` — enqueue shell; worker-side reads (recipients, facts, devices).
- `backend/push_sender.py` — the one `pywebpush` call; `enabled()`.
- `backend/push.py` — the `/api/push` blueprint.
- `backend/vapid_keys.py` — a fresh VAPID pair in the wire forms (dev tool, pytest, e2e).
- `backend/tests/test_alerts_core.py`, `test_push_core.py` — pure tests.
- `backend/tests/test_alerts.py` — enqueue, fan-out, escalation, send outcomes, sender.
- `backend/tests/test_push_api.py` — the `/api/push` routes.
- `backend/tests/test_migration_v24.py` — v24 on a fresh and a v23 database; re-run.

Changed (backend):
- `backend/local_db.py` — migration v24 (`push_subscriptions`; escalation defaults seeded).
- `backend/tickets.py` — `_add_event` returns the id; `_assign` returns the event id; the
  four enqueue calls; LOCK ORDER note gains the alert tasks and the worker's lock (BS1-06).
- `backend/task_handlers.py` — `NoRetry`, `RetryLater`; `ticket_alert`, `ticket_escalate`,
  `push_send`; the outcome rules in the module text.
- `backend/worker.py` — `_task_failed` handles `NoRetry` and `RetryLater`.
- `backend/task_queue.py` — `mark_failed(..., delay_seconds=None)` with the cap.
- `backend/settings.py` — `_validate_int_settings`; `_ESCALATION_SETTINGS`;
  `escalation_minutes(cur)`; `GET`/`PUT /api/settings/notifications`.
- `backend/config.py`, `backend/example_secrets_app.py` — `VAPID_PUBLIC_KEY`,
  `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`.
- `backend/config_rbac.py` — `push:subscribe = ('*',)`.
- `backend/company_settings.py` — `TASK_RETRY_DELAY_MAX_SECONDS = 3600`,
  `PUSH_TIMEOUT_SECONDS = 10`.
- `backend/app.py` — registers `push_bp` at `/api/push`.
- `backend/pyproject.toml`, `backend/uv.lock` — `pywebpush>=2.5.0`.
- `backend/tests/conftest.py` — `push_subscriptions` in `_TABLES` before `people`; the
  session VAPID pair; `push_off`.
- `backend/tests/test_rbac.py` — `push:subscribe` in every row of the role matrix.
- `backend/tests/test_task_queue.py` — the delay, the cap, the last attempt; `NoRetry` and
  `RetryLater` through the worker.
- `backend/tests/test_settings_api.py` — the notifications card; `/app` unchanged.

New (frontend):
- `frontend/public/manifest.webmanifest`, `frontend/public/sw.js`,
  `frontend/public/icons/icon-192.png`, `icon-512.png`, `apple-touch-icon.png`.
- `frontend/src/push.js` — the browser's push parts.
- `frontend/src/stores/notifications.js` — the shared device state and the dot.
- `frontend/src/views/NotificationsView.vue` — My notifications.
- `frontend/src/views/settings/NotificationsSettings.vue` — the Settings card.
- `frontend/e2e/notifications.spec.js` — the S021 browser tests.

Changed (frontend):
- `frontend/index.html` — manifest link and the iOS / theme meta tags.
- `frontend/src/main.js` — registers the service worker at start-up.
- `frontend/src/App.vue` — loads the notification state once the user is known.
- `frontend/src/router/index.js` — `/notifications`.
- `frontend/src/stores/auth.js` — `logout()` removes this device first.
- `frontend/src/components/layout/AppTopbar.vue` — the bell and its dot; a long name truncates.
- `frontend/src/views/SettingsView.vue` — places the Notifications card.
- `frontend/e2e/screens.spec.js` — `/notifications` for every role.
- `frontend/e2e/support/console.js` — `allowBrowserError(textPart)`.

Tooling, docs, inventory:
- `tooling/dev/make_vapid_keys.py` (new) — prints the three secrets lines.
- `tooling/e2e/e2e_backend.py` — a VAPID pair per lane process.
- `sbom/backend.cdx.json` — regenerated by `run-deps-audit.bat` (commit it with the lockfile).
- `.claude/CLAUDE.md` — *Notifications (S021)* bullet replaces "Not yet built: PWA shell";
  the spec map gains `notifications` S021.
- `docs/Plan.MD` § 4.7 — a *machine down again* row (the other rows were already updated).
- `docs/Maintenance-Philosophy.md` — the decided escalation times (§ 9 and the § 6 line).
- `docs/steps/device-checks.md` — the phone set-up list and rows 14–25.
- `docs/steps/README.md`, `1-brief.md` — status.

## 4. Decisions taken

Departures from the brief are marked **Departure**.

1. **Departure — v24 seeds the three escalation defaults** (`INSERT IGNORE` into
   `app_settings`, as v20 seeds `upload_max_mb`). § 4.2 says "no schema change"; this is
   data only. Without it, `get_setting_int` would log three warnings at every breakdown
   raise. `INSERT IGNORE` keeps a stored value, so no `_PRECONDITIONS` entry; the migration
   test checks both.
2. **Departure — e2e permission and push stubs.** Headless Chromium answers
   `Notification.permission` "denied" even after `grantPermissions(["notifications"])`, so the
   tests stub the permission (`askablePermission`), as § 8 already stubs *denied*. "On" needs a
   browser subscription by the brief's own rule, so the *dot goes out after Turn on* test
   stubs `PushManager` and lets the page post the stubbed subscription itself (the API then
   holds the row). The real `subscribe()` is still exercised in the first test, which accepts
   the error line.
3. **Departure — `allowBrowserError` in `e2e/support/console.js`.** In a Playwright context
   (always incognito) Chrome logs its own console error "does not support the Push API in
   incognito mode" when the page subscribes. The page logs nothing; one test names that line.
4. **A seventh device state, *unsupported*** (no service worker, PushManager or Notification,
   and not the iPhone case). The page shows "This browser cannot get notifications. Use
   Chrome on Android, or open Yantra from the Home Screen on an iPhone." (the server's refusal
   text). It counts as needing attention for the dot, like *off*.
5. **A dismissed permission prompt** (neither allowed nor blocked) shows "Notifications were
   not turned on. Tap Turn on for this phone again, then choose Allow."
6. **Texts the brief does not give.** A defect's title is "Defect · SMTW.MCC2 · VBM001"; a
   *Machine stopped* regrade uses the breakdown text ("Breakdown · …", "— raised by …"). The
   test alert reads "Yantra test" / "Notifications work on this device." and opens
   `/notifications`. The Settings line reads "Push notifications work on this server. N
   devices have them turned on." or "…are not set up on this server: the push keys are
   missing."
7. **`POST /api/push/test` answers 409 "Notifications are not set up on this server yet. Ask
   IT admin."** when push is off; otherwise its tasks would only fail. The page hides *Send a
   test* then anyway.
8. **A device moved to another person** (re-subscribe of the same endpoint) also restarts its
   *added* time and clears its last send and last error; the brief says "moves it and
   refreshes its keys". The move is logged.
9. **200 counts as sent**, with 201 and 202 (the message was taken; retrying would show it
   twice).
10. **`push_send` also fails with `NoRetry`** when the stored address is no longer allowed or
    push is not set up at send time, after recording `last_error`.
11. **A failed post is re-raised without its text** ("Could not reach the push service
    (ConnectTimeout)"): `requests`' messages carry the endpoint, which identifies the device.
12. **An ungraded item counts as C.** Criticality is required on equipment (new equipment
    starts at C); a NULL machine grade is a leftover.
13. **The § 5.3 decisions are pure functions** (`raise_alert`, `regrade_alert`,
    `send_back_alert` in `alerts_core`), so `tickets.py` makes one call per change.
    `alerts.py` gained helpers beyond the brief's list: `enqueue_alert`, `read_alert_ticket`,
    `assignee`, `subscription_ids`, `person_memberships` (*What you will get* reads the
    memberships there).
14. **`vapid_keys.py`**, a small backend module without config or Flask, shared by
    `make_vapid_keys.py`, the pytest fixture and the e2e backend (instead of three copies).
15. **`_assign` returns the new event's id, or None** (was True/False), so *Assign* can name
    the event. `_auto_assign` ignores it as before.
16. **Sign-out also unsubscribes the browser**, not only the server row, and waits at most
    3 seconds.
17. **The top bar's name truncates** with an ellipsis on a narrow phone, so the bell and
    Logout always fit.
18. **Placement**: the Settings card sits between Network and Background tasks; the device
    rows of *My devices* show "Added …", "Last sent …" and "Last error: …".
19. **Icons**: a plain white "Y" on `#1e293b`, drawn with Pillow (§ 9 Q6). The generator was
    a scratch script, not committed; a logo replaces the three PNGs.
20. **Test placement**: the worker's `NoRetry` / `RetryLater` tests are in
    `test_task_queue.py`, where the worker-run tests live.

## 5. Not done, deferred or assumed

- **No real push was sent.** The e2e stack runs no worker, and headless browsers have no
  push account. The sending path is tested with a fake sender and a fake `webpush`; the
  device rows prove the rest on production.
- **Dependency health.** `pywebpush` 2.5.0 (30-08-2026) passes S022's check; the audit found
  no vulnerability in the backend. It pulls in 17 packages: `py-vapid` 1.9.6, `http-ece`
  1.2.1, `requests` 2.34.2 (with `urllib3`, `idna`, `charset-normalizer`, `certifi`) and
  `aiohttp` 3.14.5 (with `aiohappyeyeballs`, `aiosignal`, `attrs`, `frozenlist`, `multidict`,
  `propcache`, `yarl`, `typing-extensions`).
  - Flag: **`http-ece` had its last release on 08-08-2024**, over 12 months ago. It is a
    transitive dependency (the RFC 8291 encryption), so the audit does not gate on it.
  - Flag: `aiohttp` is a hard requirement of `pywebpush` (its async API); Yantra never uses it.
- **Production secrets** (the user's edit, § 5.6). Add to
  `smtw_erp_devops/erp_server/yantra/secrets_app.py.j2`, with your own variable names:
  ```
  VAPID_PUBLIC_KEY = "{{ yantra_vapid_public_key }}"
  VAPID_PRIVATE_KEY = "{{ yantra_vapid_private_key }}"
  VAPID_SUBJECT = "{{ yantra_vapid_subject }}"
  ```
  Make the pair once with `uv run --project backend python tooling/dev/make_vapid_keys.py
  mailto:<address>`. Never rotate it casually: a new pair ends every phone's subscription.
- **Assumed: outbound HTTPS** from the worker container to `fcm.googleapis.com` and
  `web.push.apple.com` (§ 9 Q5). Rows 14–21 prove it.
- **Samsung Internet's push host** is unknown; row 25 finds it if it is wanted.
- **The dev database** had already applied v24 (the dev backend reloaded) before the seed of
  decision 1 was added. I added the same three rows there with `INSERT IGNORE`. The test
  database's v24 was dropped and re-applied.
- **The first `run-tests.bat` run** failed with a deadlock and duplicate codes on
  `vel_yantra_test`, which points to a second pytest session on the same database at the
  time. No such process was left; the rerun was green. Another session works in this
  repository: commit `03ed528` (the user's, 11:08) also holds frontend changes that are not
  S021's (`useShowMore.js`, `EquipmentHistory.vue`, `EquipmentDetailView.vue`,
  `PartsPanel.vue`, `showMore.test.js`).
- **Most of S021 is already in commit `03ed528`** (the user's, "S027, S021: …", 11:08), made
  while I was still working. After it, only `frontend/src/push.js` (decision 5),
  `frontend/e2e/notifications.spec.js` (decision 3) and this report changed.
- **The backend suite takes about 6 minutes now** (was about 3.6): `test_alerts.py` builds a
  site with eight people and devices for each test.
- **`nginx.conf`** is unchanged: `location /` already sends `no-cache` for `sw.js`; the
  manifest's content type is checked after deploy (row 23).

## Tests run

- `tooling/run-tests.bat`: **green** — backend 2252 passed, frontend 114 passed, deps 42
  passed, tooling 68 passed.
- `npx vite build` (in `frontend/`): clean; `dist/` carries `manifest.webmanifest`, `sw.js`
  and `icons/`.
- `tooling/run-deps-audit.bat`: exit **0**; `sbom/backend.cdx.json` regenerated. The two
  moderate findings are the existing frontend dev dependency `@vitest/mocker` 4.1.11, not this
  step's.
- `tooling/run-e2e-tests.bat` (full suite, lanes): see below. The full suite, because the step
  changes the router, the auth store, the top bar and `e2e/support/console.js` (shared code).

- **Full suite** (22-10-2026, 6 lanes, 3 projects): **231 passed, 6 skipped, 0 failed** (247 s).
  The 6 skips are this step's own project skips in `notifications.spec.js` (an iPhone-only
  test on the Chromium projects, and so on), each with its reason in the test.
- **Targeted rerun on the final code** (`e2e/notifications.spec.js e2e/screens.spec.js`, after
  the last `push.js` change, decision 5): **51 passed, 6 skipped, 0 failed**.
- Earlier targeted runs failed on two things the tests had to learn (decisions 2 and 3):
  headless Chromium's "denied" permission, and Chrome's own incognito console error.

## Manual checks

Automated (from the passing run above):

- [auto] My notifications opens for every seed person in Team and shows *Turn on for this phone*; with the permission given, the page reaches the subscribe call and shows its result (desktop and Pixel 7 Chromium) — frontend/e2e/notifications.spec.js::S021: My notifications opens for every seed person in Team and offers Turn on for this phone
- [auto] iPhone 14: the *Add to Home Screen* explanation, and the bell's dot for an engineer — frontend/e2e/notifications.spec.js::S021: on an iPhone outside the Home Screen the page explains Add to Home Screen, and the bell has its dot
- [auto] Denied (stubbed): the page says how to unblock — frontend/e2e/notifications.spec.js::S021: a browser that blocked notifications is told how to unblock them
- [auto] The bell shows on every screen, and tapping it opens My notifications — frontend/e2e/notifications.spec.js::S021: the bell shows on every screen and opens My notifications
- [auto] The dot shows for an engineer, a technician (A1), a manager and a supervisor whose device is off; not for IT admin or a storekeeper — frontend/e2e/notifications.spec.js::S021: the dot shows to people who would get alerts on a device that is off — not to IT admin or a storekeeper
- [auto] After *Turn on* succeeds the dot goes out without a reload; *Turn off* sets it again (Chromium) — frontend/e2e/notifications.spec.js::S021: Turn on clears the dot at once, and Turn off sets it again, without a reload
- [auto] IT admin without a Team record reads "You are not in Team. Add yourself in Masters › Team to get test messages."; another login without one reads "…Ask IT admin to add you."; no *Turn on* — frontend/e2e/notifications.spec.js::S021: without a Team record the page says so and offers no Turn on — IT admin and anyone else
- [auto] A device seeded through the API shows in My devices; *Send a test* reports "Sent to 1 device"; *Remove* asks "Remove …? That device gets no alerts until it turns them on again." and *Yes* removes it — frontend/e2e/notifications.spec.js::S021: a device seeded through the API is listed; Send a test reports it; Remove asks first, then removes it
- [auto] A1: a technician's *What you will get* lists "Jobs assigned to you"; the engineer's lists breakdowns and defects — frontend/e2e/notifications.spec.js::S021 A1: What you will get — the engineer's breakdowns and defects, the technician's assigned jobs
- [auto] Settings › Notifications: IT admin changes B to 20 and it stays after a reload; 4 is refused beside its box, in view, with the cursor in it; the manager sees the values read-only — frontend/e2e/notifications.spec.js::S021: Settings › Notifications — IT admin changes B, it stays after a reload; 4 is refused on its box; the manager reads
- [auto] The manifest is served and parses, its icons load; the service worker registers (Chromium) — frontend/e2e/notifications.spec.js::S021: the manifest is served and parses; the service worker registers
- [auto] `/notifications` opens for every role — frontend/e2e/screens.spec.js::every screen opens as <role>

On a real device (production, TEST machine, after the release; rows 14–25 of
`docs/steps/device-checks.md`). Important:

- [ ] Android, Chrome, engineer test login, mobile data: Turn on, Send a test; it arrives with
  sound, and tapping opens Yantra (row 14).
- [ ] Samsung Galaxy, Chrome, set up as in § 5.6, screen off for an hour; the operator raises
  a breakdown; the phone rings within a minute (row 15).
- [ ] iPhone (iOS 16.4+), KLA's own, from the Home Screen icon, mobile data: Turn on, Send a
  test; it arrives, and tapping opens Yantra (row 16).
- [ ] Engineer's and supervisor's phones on mobile data; the operator raises a breakdown on
  TEST; both ring within a minute and open that ticket (row 17).
- [ ] The operator raises a defect; the engineer's Android phone gets it without sound (row 18).
- [ ] IT admin, company network: Settings › Notifications, grade C to 5 minutes (row 19).
- [ ] Engineer's and manager's phones; an unacknowledged breakdown rings "Not acknowledged
  after 5 min" after about 6 minutes; one acknowledged in time sends nothing; C back to 60
  (row 20).
- [ ] Sign out on the engineer's phone; a new breakdown reaches it no more (row 21).

Plain:
- Install on Android shows the Yantra icon and opens without the browser bar (row 22).
- After deploy: `sw.js` answers `Cache-Control: no-cache`; the manifest's `Content-Type` is
  read (row 23).
- Remove the phone from a desktop; it gets nothing after (row 24).
- Samsung Internet: Turn on; note whether it is refused (row 25).
