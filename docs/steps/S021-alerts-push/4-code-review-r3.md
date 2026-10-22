```
Step: S021 — Alerts: PWA and web push
Doc: code-review r3
Author: Code reviewer (Opus)
Date: 22-10-2026
```

# S021 — Code review, round 3

**Verdict: no `blocker` or `major` finding is open.** Every fix of round 2 is in place and works.
One new `minor` finding is open: CR3-01, the "late" line promises a retry that may not come. Four
new nits. The tests are green.

This is a verify round (code-reviewer rule "Round 2 and later verify"). Files re-read: the round's
diff in commit `63eda6c` for `backend/task_handlers.py`, `backend/push_sender.py`,
`backend/pyproject.toml`, `backend/uv.lock`, `sbom/backend.cdx.json`, `backend/tests/test_alerts.py`,
`frontend/src/push.js`, `frontend/src/App.vue` and `frontend/src/views/NotificationsView.vue`; the
working-tree diff of `frontend/src/stores/notifications.js`; `push_send` in full
(`task_handlers.py:157-230`), `push_sender.py` in full, `stores/notifications.js` in full,
`stores/auth.js:16-95`, `NotificationsView.vue:75-175`, and `pywebpush`'s `WebPusher.__init__` and
`WebPusher.send` (2.5.0, installed). The impl report's Fix rounds › Round 2.

## Tests run

| Run | Result |
|---|---|
| `tooling/run-tests.bat` (`YANTRA_TEST_RUN=s021r3`) | **green**: backend 2280 passed (51 s), frontend 114 passed, deps 42 passed, tooling 91 passed |
| `npx vite build` | **clean** (built in 3.9 s) |
| `tooling/run-e2e-tests.bat e2e/notifications.spec.js e2e/screens.spec.js` | **green**: 51 passed, 6 skipped (the same skips as round 2), in 123 s |

**Why targeted e2e and not the full suite** (assessment): the round changed `App.vue`, which every
screen loads. But it is not on the shared-code list (README § Manual checks), and the change is one
argument in the watch that loads the bell's state, behind `push:subscribe`. `screens.spec.js` opens
every route through `App.vue`, so it covers a fault there. `auth.js` is unchanged.

## Verification of the round-2 fixes

| ID | Fix claimed | Verified |
|---|---|---|
| CR1-02 | Only `requests.RequestException` counts as "could not reach"; others `NoRetry` with an ERROR log | **Fixed.** `task_handlers.py:199-210`. `pywebpush` calls `session.post` and does not wrap its errors, so a timeout, a connection error and `TooManyRedirects` all reach the first `except`. A `WebPushException` with no response (missing keys, bad `p256dh`, a VAPID dict without a key) is not a `RequestException`, so it is now a `NoRetry` with the "fault" line. That is right: a retry cannot fix it. The new test checks the `NoRetry`, the log line and the device row. |
| CR1-03 | Four plain lines on the device row | **Fixed**, with CR3-01 below on one text. The scope B check is in the next table. |
| CR1-04 | `navigator.platform` replaced | **Fixed.** `push.js:41` reads `/Macintosh/` in the user agent with `maxTouchPoints > 1`. A Mac has no touch screen, so a desktop Mac still reads as not an iPhone. |
| CR1-05 | Assessed: `pywebpush` stays | **The reasoning holds.** The installed `pywebpush-2.5.0` METADATA lists `Requires-Dist: aiohttp` with no extra (fact). The only other route is the hand-written encryption that decision 3 rejected. The watch points (an `aiohttp`-optional release, `http-ece`, the S022 stale flag) are the right ones. I accept the "assessed" answer; the user decides at gate B. |
| CR1-08 | `stores/notifications.js` no longer imports `auth.js` | **Fixed.** No import of `./auth` is left. `auth.js:94-95` sets `userPermissions` and then `userPersonId` in the same tick, so the `App.vue` watch (flush `pre`) reads the new person id. `NotificationsView` loads again on mount with its own id, so a second user in the same tab also gets the right state. See nit CR3-04. |
| CR2-01 | `urllib3>=2` declared, `uv.lock`, `sbom/` | **Fixed.** `pyproject.toml:17`, the root package's dependencies in `uv.lock`, and `urllib3` in the root component's `dependsOn` in `sbom/backend.cdx.json`. |
| CR2-02 | A `requests.Session` with `max_redirects = 0` | **Fixed.** `push_sender.py:23-29, 47`. `WebPusher.__init__` keeps the session as `mod_or_session`, and `WebPusher.send` posts with it and with the timeout (read in the installed source). A 307 raises `TooManyRedirects`, which the handler counts as "could not reach". See nits CR3-02 and CR3-03. |
| CR2-03 | Report records CR1-06 and CR1-07 | **Fixed.** Fix rounds › Round 2 records both as `Accepted`. |

**The four device-row texts against CLAUDE-COMMON scope B.** The row shows them as
`Last error: <text>` under the device (`NotificationsView.vue:156`).

| Text | What happened | What to do | Verdict |
|---|---|---|---|
| "The last alert did not reach this device. Turn notifications off and on again on it." | yes | yes | Good. "on it" reads oddly on another device's row (nit CR3-05). |
| "The last alert is late. Yantra tries again." | yes | yes (wait) | True on a retry, false after the last one (CR3-01). |
| "Notifications are not set up on this server yet. Ask IT admin." | yes | yes | Good. The same words as the *This device* card (`NotificationsView.vue:88`), so one term for one thing. |
| "The last alert could not be sent. Ask IT admin." | yes | yes | Good. Short, no blame, no internal code. The exception type stays in `task_queue.last_error` and the log. |

"IT admin" matches the other screen texts (`NotificationsView.vue:84`, `EquipmentView.vue:297`).
"Alert" for one message and "notifications" for the feature follow the page's own usage
("Turn them on to get alerts here").

## Findings

### CR3-01 — `minor` — The "late" line promises a retry after the last attempt

- **Where:** `backend/task_handlers.py:163` (`DEVICE_LATE`), used at `:202` and `:223`.
- **Problem:** the handler writes "The last alert is late. Yantra tries again." on every failed
  attempt that the queue may retry: a timeout, a connection error, a redirect, a 429 or a 5xx. The
  handler does not know the attempt count. A `push_send` task has `DEFAULT_MAX_ATTEMPTS = 3`
  (`task_queue.py:18`). On the third failure the task goes to `failed`, and nothing tries again.
  The device row still says "Yantra tries again" until a later alert reaches the device.
- **Failure scenario:** FCM is down for 20 minutes during a breakdown. The three attempts of the
  Assigned alert all fail. The technician opens My notifications and reads "The last alert is
  late. Yantra tries again." He waits for an alert that never comes, instead of opening the
  ticket list.
- **Fix:** use a text that is true on every attempt, for example "The last alert may be late or
  lost. The push service did not answer. Check your tickets." Passing the attempt count into the
  handler would also work, but it is a larger change for one line of text.

## Nits

- **CR3-02** (nit) `backend/tests/test_alerts.py:505`: the test posts with `push_sender._session()`
  directly, so it still passes if `send()` stops passing `requests_session=`. Patch
  `push_sender._session` with a spy, or post through `send()` to the local server, so the test
  checks the wiring too.
- **CR3-03** (nit) `backend/push_sender.py:47`: each send opens a new `requests.Session` and never
  closes it. Close it after the post (`with _session() as session:` around the `webpush` call), so
  its socket is not left to the garbage collector.
- **CR3-04** (nit) `frontend/src/stores/notifications.js:60`: store `ownPersonId ?? null`. A later
  caller that omits the argument then gets "not in Team" and not the "off" state with no person.
- **CR3-05** (nit) `backend/task_handlers.py:162`: end the refused line with "on that device"
  instead of "on it". The row may be another device's, and "it" has no clear noun.

## Earlier findings

| ID | Severity | Status |
|---|---|---|
| CR1-01 | blocker | Fixed (round 2) |
| CR1-02 | minor | **Fixed**, verified above |
| CR1-03 | minor | **Fixed**, verified above; one text reopened as CR3-01 |
| CR1-04 | minor | **Fixed**, verified above |
| CR1-05 | minor | **Assessed, no change**; the reasoning holds. Closed unless the user decides otherwise at gate B |
| CR1-06 | nit | Fixed by the planner (round 2) |
| CR1-07 | nit | Fixed by the planner (round 2) |
| CR1-08 | nit | **Fixed**, verified above |
| CR2-01 | minor | **Fixed**, verified above |
| CR2-02 | nit | **Fixed**, verified above |
| CR2-03 | nit | **Fixed**, verified above |

## Checked and found consistent

- **The payload is built before the `try`** (`task_handlers.py:197`). A `KeyError` there is a fault
  in Yantra's own task, not a device fault, so it does not write a device line. The worker logs it
  and retries it like any task fault. `payload["urgency"]` and `payload["ttl"]` are still read
  inside the `try`; a missing one gives the "fault" line and `NoRetry`. Both outcomes are
  acceptable for a payload the app builds itself.
- **No endpoint in the logs.** The `RequestException` branch raises a new exception with the type
  only (`from None`). The other branch logs the exception message. That message comes from
  `pywebpush`, `py-vapid` or `cryptography`; none of the `WebPushException` texts in the installed
  source carries the endpoint.
- **The order of the checks in `push_send`.** The address check and "push is off" still come
  before the post, each with its own line and `NoRetry`. The tests compare the rows with the
  constants, so a later text change does not break them.
- **`App.vue` and `NotificationsView.vue`** pass `userPersonId.value`. These are the only two
  callers of `loadNotifications` (searched `frontend/src`).
- **The `test_alerts.py` import change** (`TEST_WORKER_LOCK` from `tests/db_names.py`) belongs to the
  parallel-test tooling change. It only moves the lock name, and the suite passes with it.
- **`uv.lock` in `63eda6c`** also carries `pytest-xdist` and `execnet` from the tooling change. Their
  `sbom/` entries are in the working tree, so the user should commit them with that change.
- **The impl report's Fix rounds › Round 2** follows scope A. It names the four texts in a table,
  states which ones the coder chose, and lists the files and the runs.

## Manual checks still needed

None new from this round. The open device rows 14–25 of `docs/steps/device-checks.md` stay as
listed in `4-code-review-r1.md`.
