```
Step: S021 — Alerts: PWA and web push
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 22-10-2026
```

# S021 — Code review, round 1

**Verdict: one `blocker` is open (CR1-01). The push address check can be bypassed, so the worker
can be made to post to any host.** No `major` finding is open. The rest of the step matches the
brief and amendment A1, and the tests are green.

Reviewed: the diff `79fc61d..HEAD` limited to the files of the impl report (commit `03ed528`
holds most of S021), plus the working tree (`frontend/src/push.js`,
`frontend/e2e/notifications.spec.js`, the impl report). The non-S021 files in `03ed528`
(`useShowMore.js`, `EquipmentHistory.vue`, `EquipmentDetailView.vue`, `PartsPanel.vue`,
`showMore.test.js`) and S026/S027 code were not reviewed.

## Tests run

| Run | Result |
|---|---|
| `tooling/run-tests.bat` | **green** — backend 2252 passed (5 min 26 s), frontend 114 passed, deps 42 passed, tooling 68 passed |
| `npx vite build` (`frontend/`) | clean, no warnings |
| `tooling/run-e2e-tests.bat` (full suite, 6 lanes, 3 projects) | E2E_RESULT |

The full e2e suite ran because S021 changes shared frontend code: the router, the auth store
and `e2e/support/console.js` (§ 10 BS1-03).

A reproduction of CR1-01 (a scratch script, not committed) ran against the backend's own
`push_core`, `urllib3` and `requests`.

## Findings

### CR1-01 — `blocker` — the push address check can be bypassed with a backslash

- **Where:** `backend/push_core.py:59-75` (`refused_host`), used by `push.py:265` (subscribe)
  and `task_handlers.py` `push_send` (the re-check before the post).
- **Problem:** `refused_host` parses the address with `urllib.parse.urlsplit`. `requests` (through
  `urllib3.util.parse_url`) parses it differently: it ends the host at a backslash, and
  `urlsplit` does not. So the two disagree about which host the worker posts to.
- **Reproduction** (fact, run during this review):

  | Address | `refused_host` | `urllib3` host | `requests` posts to |
  |---|---|---|---|
  | `https://evil.example\.fcm.googleapis.com/x` | `None` (allowed) | `evil.example` | `https://evil.example/%5C.fcm.googleapis.com/x` |

  `pywebpush` calls `requests.post(endpoint, …)` with the stored address as it is
  (`WebPusher.send`).
- **Failure scenario:** any logged-in person with a Team record posts `{endpoint:
  "https://10.24.0.10\\.fcm.googleapis.com/", keys: {…}}` to `POST /api/push/subscriptions` and
  taps *Send a test*. The worker, inside the plant network, then POSTs to `10.24.0.10:443`. The
  answer's status comes back to that person in *My devices* as "Last error: Push service
  answered 404" (or the device row vanishes on a 404/410). That is a blind SSRF with a status
  oracle: it can probe internal HTTPS hosts. The brief's ISO 27001 A 8.20 / OWASP SSRF control
  (§ 2, § 5.4) does not hold.
- **Fix:**
  1. In `refused_host`, refuse any address that holds a character outside the URL's printable
     ASCII set, and in particular `\`, `%` in the authority, whitespace and control characters.
     A simple form: the host must match `[a-z0-9.-]+` and the whole address must match
     `[\x21-\x7e]+` with no `\`.
  2. Also parse with `urllib3.util.parse_url` (the parser `requests` uses) and require the same
     host from both parsers; refuse on any `LocationParseError`.
  3. Add the backslash address, `https://10.24.0.10\.fcm.googleapis.com/` and a `%2f` variant to
     `test_refused_addresses_name_their_host`.

### CR1-02 — `minor` — `push_send` reports every exception as "could not reach the push service"

- **Where:** `backend/task_handlers.py` `push_send`, the `try … except Exception` around `send(…)`.
- **Problem:** the `try` also covers `push_data(payload)` and `payload["urgency"]`, and the
  `except Exception` covers every error inside `pywebpush`. A bad VAPID private key in
  `secrets_app.py` raises inside `Vapid.from_string`. The handler records it as "Could not reach
  the push service (ValueError)" and raises a plain `RuntimeError`, so it retries three times on
  every device. `from None` also drops the cause from the worker's log, so IT admin sees a
  network fault where the real fault is the key.
- **Failure scenario:** production gets a mistyped private key. Every alert fails three times per
  device, the log says "Could not reach the push service (ValueError)", and IT admin checks the
  firewall instead of the secret.
- **Fix:** build the payload before the `try`. Catch `requests.RequestException` (and
  `WebPushException` without a response) for the "could not reach" text. For any other exception,
  record a short text such as "Push could not be sent (a server fault)", log the exception type
  and a message without the endpoint, and raise `NoRetry`: a retry cannot fix it.

### CR1-03 — `minor` — the device row's *Last error* shows status codes and exception names

- **Where:** `frontend/src/views/NotificationsView.vue:155` shows `push_subscriptions.last_error`
  as written by `task_handlers.py` `push_send`: "Push service answered 403", "Could not reach the
  push service (ConnectTimeout)", "Address not allowed", "Push is not set up on this server".
- **Problem:** CLAUDE-COMMON scope B: no internal codes on screen, and an error says what the user
  can do next. A floor user reads "answered 403" or "ConnectTimeout" and does not know what to do.
- **Failure scenario:** a technician sees "Last error: Push service answered 403" under his phone
  and does not know whether to turn it off and on, ask IT admin, or ignore it.
- **Fix:** keep the technical text in `task_queue.last_error` and the log. Store a plain line on the
  device row, one per outcome, for example:
  - refused (400, 403, 413): "The last alert did not reach this device. Turn notifications off
    and on again on it.";
  - retry (5xx, 429, timeout): "The last alert is late. Yantra tries again.";
  - push off: "Notifications are not set up on this server yet. Ask IT admin."

### CR1-04 — `minor` — `push.js` uses the deprecated `navigator.platform`

- **Where:** `frontend/src/push.js:41` (`isIphone`).
- **Problem:** `Navigator.platform` is deprecated (MDN). CLAUDE-COMMON: never use deprecated APIs.
- **Failure scenario:** a browser that drops it or freezes it to `""` stops seeing an iPad as an
  iPhone, and the iPad shows *Turn on*, which iOS then refuses outside the Home Screen.
- **Fix:** `/Macintosh/.test(navigator.userAgent) && navigator.maxTouchPoints > 1` for the iPad case.

### CR1-05 — `minor` — dependency health: `http-ece` is stale and `aiohttp` is unused

- **Where:** `backend/uv.lock` (`pywebpush` 2.5.0 pulls `http-ece` 1.2.1 and `aiohttp` 3.14.5).
- **Problem:** CLAUDE-COMMON *Dependency health* asks to flag a library with no release in 12
  months **and suggest a maintained alternative**. The impl report flags `http-ece` (last release
  08-08-2024) and `aiohttp`, but suggests nothing and asks for no decision.
  - Fact: `http-ece` does the RFC 8291 encryption, the core of every push. No maintained
    alternative exists in Python; the only other route is the hand-written encryption that
    decision 3 rejected.
  - Fact: `aiohttp` is a hard requirement of `pywebpush` 2.x and is never imported by Yantra, but
    it is code in the image and in the S022 audit.
- **Fix:** put the choice to the user at gate B: accept `http-ece` as stale but small and stable
  (watched by `run-deps-audit.bat`), or revisit decision 3. Record the answer in the brief's
  Review log.

### CR1-06 — `nit` — A1 rule 6 and the code state the dot's rule differently

- **Where:** `1-brief.md` § 10 A1 rule 6 ("when none of their devices is turned on");
  `frontend/src/stores/notifications.js:43` (`showDot`: when **this** device is off).
- **Problem:** the code follows § 1.3 for everyone, which is the approved body. A1's wording says
  something else for a technician. Neither the impl report nor the code says which one holds.
- **Failure scenario:** a technician with his phone on opens Yantra on the workshop desktop and
  sees the dot; by A1's words he should not.
- **Fix:** the planner aligns A1's text with § 1.3, or asks the user which rule he meant.

### CR1-07 — `nit` — `docs/Plan.MD` still says the defect alert is open

- **Where:** `docs/Plan.MD:454`: "whether it notifies is settled with the notification step".
- **Fix:** say it is settled: a new defect alerts the engineers quietly (S021).

### CR1-08 — `nit` — `auth.js` and `notifications.js` import each other

- **Where:** `frontend/src/stores/auth.js:16` imports `forgetThisDevice`;
  `frontend/src/stores/notifications.js:17` imports `userPersonId`.
- **Problem:** the cycle works today because each side reads the other's binding only at call
  time. A later top-level use of either import breaks start-up with a TDZ error that is hard to
  trace.
- **Fix:** let `notifications.js` take the person id as an argument, or call `forgetThisDevice()`
  from the Logout button's handler instead of from `logout()`.

## The coder's decisions and departures

Each was judged against the brief; none is a finding except as noted.

| # | Decision | Judgement |
|---|---|---|
| 1 | v24 seeds the three defaults with `INSERT IGNORE` | Accepted. Data only, idempotent, keeps a stored value; the migration test checks the seed, the re-run and a changed value. No `_PRECONDITIONS` entry is needed |
| 2 | e2e stubs of `Notification.permission` and `PushManager` | Accepted. The brief already stubs *denied* (§ 8); the first test still calls the real `subscribe()` and accepts its error line |
| 3 | `allowBrowserError(textPart)` in `e2e/support/console.js` | Accepted. It is named per test and matches Chrome's own incognito line only |
| 4 | A seventh state, *unsupported*, with the dot | Accepted. The text is the server's refusal text, and the person can act on it (use Chrome) |
| 5 | The dismissed-prompt message | Accepted. One line, says what to do |
| 6 | Texts the brief does not give | Accepted, except the *Last error* texts (CR1-03) |
| 7 | `POST /api/push/test` 409 when push is off | Accepted. The tasks would only fail; the text is the brief's |
| 8 | A moved device restarts its times | Accepted. The old owner's last send is not the new owner's |
| 9 | 200 counts as sent | Accepted. A retry would show the alert twice |
| 10 | `NoRetry` for an address no longer allowed, or push off at send | Accepted. A retry cannot change either |
| 11 | A failed post re-raised without its text | Accepted for network errors (the text carries the endpoint); too wide for other errors (CR1-02) |
| 12 | An ungraded item counts as C | Accepted. Criticality is required on equipment; a NULL is a leftover |
| 13–15 | Pure `raise_alert` / `regrade_alert` / `send_back_alert`; `vapid_keys.py`; `_assign` returns the event id | Accepted. Each keeps a rule in the pure core or removes a copy |
| 16 | Sign-out also unsubscribes the browser, bounded to 3 s | Accepted. It makes the hand-over safe even when the server call fails: the next push gets 404/410 and the row goes |
| 17 | The top bar's name truncates | Accepted. The bell and Logout always fit at 360 px |
| 18–20 | Card placement, icons, test placement | Accepted |

## Checked and found consistent

- **Audience per kind** (`alerts_core.AUDIENCE`, `alerts.recipients`): exact roles, the ticket's
  site, unit access by `all_units` or `person_units`, active people only, the left-out people
  (actor; reported-by for breakdown and defect; nobody for an escalation). The fan-out tests
  seed real rows for every case of § 8 (all units, a unit row, another unit, another site,
  inactive, the raiser).
- **A1:** `assigned` is enqueued only from `add_assignee` when `_assign` adds a new assignee;
  `_auto_assign` enqueues nothing; the actor is left out; at send the person must still be in
  `ticket_assignees` and active, and the ticket open. Text "Assigned to you · … — by <first
  name>". *What you will get* lists "Jobs assigned to you" for `ASSIGNABLE_ROLES`.
- **When tickets enqueue** (§ 5.3): raise after the *Already fixed* block and only without it
  (BS1-09); regrade escalates only while raised; send-back in `_apply_move` after `_add_event`,
  decided by `clean["machine_down"]`; all in the ticket's transaction, so a refused raise leaves
  no task (tested).
- **Escalation:** minutes from the component's own grade, else the machine's, read at enqueue;
  `scheduled_for` = IST now + minutes; the handler locks the ticket row, escalates only while
  raised, critical and with the trigger as the latest critical event; once. Scheduled (S019),
  not a fault (S025), acknowledged, started, back in service and closed are all skipped
  (tested). The LOCK ORDER note in `tickets.py` names the worker's lock and adds no edge.
- **Worker contract:** `NoRetry` and `BadTask` fail at once; `RetryLater` passes its delay;
  `mark_failed` caps it at 3600 s and ignores it on the last attempt; `_task_failed` stores
  "NoRetry: …" (BS1-07). `push_send` commits only its `last_error` before raising. Tested through
  the worker for 400 and 429.
- **Send outcomes:** 200/201/202, 404/410, 400/403/413, 429 with and without a whole-number
  `Retry-After`, others; `timeout=10` passed; keys read at call time (tested with a fake
  `webpush`).
- **Migration v24:** new table only, `IF NOT EXISTS`, `INSERT IGNORE`; tested fresh, from v23 with
  data kept, and re-run. `push_subscriptions` is in `conftest._TABLES` before `people`.
- **RBAC:** `push:subscribe = ('*',)`, global (not in `SITE_SCOPED`), and every route carries it.
  The actor and the person come from the session (`current_person_id`), never the body.
  `DELETE …/<id>` deletes only the caller's row (404 otherwise); remove by endpoint deletes
  whoever owns it, as BR3-03 decided. Settings routes use `settings:read` / `settings:edit`.
- **SQL:** every value is a parameter; the `IN (…)` lists build placeholders only.
- **Secrets:** the private key is read from `config` at call time, never logged or served; the
  public key is served only when push is on; `example_secrets_app.py` has the three fields; the
  impl report gives the template lines for the devops repo.
- **Push payload:** title, body, path, tag and silent only (ISO 27001 A 5.14); endpoints and keys
  never go back to the browser.
- **Service worker:** scope `/`, no `fetch` handler, no cache; `skipWaiting` + `clients.claim`;
  `notificationclick` opens only a same-origin path (a `/\host` path falls back to `/`).
- **Settings card:** one PUT, errors on `escalate_minutes.<grade>`, `revealError(form)` after a
  refusal (BS1-04), read-only for the manager; `/app` keeps its contract (tested).
- **UX:** no dialogs are added; *Remove* asks inline with the consequence; *Turn off* has no
  confirm, as the brief says; the bell is 44 px; no fixed widths beyond `max-width`; the not-in-Team,
  not-set-up, iPhone and blocked states are rendered, not blank.
- **E2E:** each *Automated* check of § 8 and A1 has a test that asserts what the user sees (texts,
  the dot, the device row, the saved value after reload, the field message in view). The impl
  report's `## Manual checks` lists every important check, as `[auto]` with its test or as an
  open box, and rows 14–25 are in `docs/steps/device-checks.md`.
- **Docs:** `.claude/CLAUDE.md` *Notifications (S021)* bullet, "PWA shell" removed from *Not yet
  built*, the spec map gains `notifications`; Plan.MD § 4.7 and § 9 Q2; Maintenance-Philosophy.

## Manual checks still needed

On production, on the TEST machine, after the release (rows 14–25 of `device-checks.md`):

- [ ] Android, Chrome, mobile data: *Turn on*, *Send a test*; it rings and opens Yantra (row 14).
- [ ] Samsung Galaxy, Chrome, screen off for an hour; a breakdown rings within a minute (row 15).
- [ ] iPhone from the Home Screen icon: *Turn on*, *Send a test* (row 16).
- [ ] Engineer's and supervisor's phones ring for a breakdown and open the ticket (row 17).
- [ ] A defect arrives without sound on Android (row 18).
- [ ] Escalation after 5 minutes on grade C; an acknowledged one sends nothing (rows 19–20).
- [ ] A signed-out phone gets nothing (row 21).
- Plain: install icon (row 22), `sw.js` `no-cache` and the manifest's `Content-Type` (row 23),
  remove from a desktop (row 24), Samsung Internet's push host (row 25).
- After CR1-01 is fixed: nothing extra on a device; the fix is covered by unit tests.
