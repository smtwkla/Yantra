```
Step: S021 — Alerts: PWA and web push
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 22-10-2026
```

# S021 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open. CR1-01 is fixed.** The new address check
held against every bypass I tried, by hand and by a fuzz run of 400 000 addresses. One new
`minor` finding is open (CR2-01, `urllib3` is not declared). CR1-02 to CR1-05 and CR1-08 stay
open for the user at gate B. CR1-06 and CR1-07 are fixed in the brief and in Plan.MD.

This is a verify round (code-reviewer rule "Round 2 and later verify"). Files re-read:
`backend/push_core.py` (whole file to `refused_host`), the fix round's test hunks in
`tests/test_push_core.py`, `tests/test_push_api.py` and `tests/test_alerts.py`, the two call
sites (`push.py:96`, `task_handlers.py:180`), `push_sender.py:27-37`, `pywebpush`'s
`WebPusher.send`, the docs diff (`1-brief.md` § 10 A1 rule 6, `Plan.MD:454`) and the impl
report's Fix rounds.

## Tests run

| Run | Result |
|---|---|
| `tooling/run-tests.bat` | **green**: backend 2275 passed (8 min 35 s), frontend 114 passed, deps 42 passed, tooling 82 passed |
| `npx vite build` | not run: the fix round changed no frontend file |
| `tooling/run-e2e-tests.bat` | not run: the fix round changed no screen and no API that a screen uses. The subscribe route now refuses more addresses, but no real browser sends one of them |
| Fuzz script (scratchpad, not committed) | **0 bypasses**: see below |

## CR1-01: how I tried to break the check

The script compared `refused_host(endpoint)` with the host that `requests` really posts to. It
used `requests.Request("POST", endpoint).prepare()` and then `urllib3.util.parse_url` on the
prepared URL, the same steps the connection pool takes. A bypass is an address that
`refused_host` allows while `requests` posts to a host outside `ALLOWED_PUSH_HOSTS`, or to a
port other than 443.

- **Hand-written cases (40), all refused or safe** (fact):
  - suffix and prefix tricks: `fcm.googleapis.com.evil.example`, `evilfcm.googleapis.com`,
    `xfcm.googleapis.com`: refused. The `host.endswith(f".{allowed}")` rule needs a dot;
  - ports: `:443`, `:8443`, and an empty port `:`: refused;
  - user-info: `a@fcm…`, `fcm…@evil`, `fcm…;@evil`, `fcm…"@evil`, `fcm…'@evil`, and
    `%40` in the host: refused;
  - `@` after the authority (`fcm…?@evil.example`, `fcm…#@evil.example`): allowed, and
    `requests` posts to `fcm.googleapis.com`, so these are safe;
  - backslash anywhere, in the host or the path: refused;
  - IDNA and Unicode: a full-width `ｆ`, the ideographic full stop `。`, the full-width full
    stop `．`, a zero-width space: refused. `_ADDRESS_RE` allows ASCII only, so no IDNA mapping
    can happen;
  - upper case: `FCM.googleapis.com` and `HTTPS://` are allowed. Both parsers make the host
    lower case, so the posted host is the allowed one;
  - trailing dot, a leading `-`, a NUL, `|`, `^`, `{`, `` ` ``: refused;
  - IP forms: `127.0.0.1`, `[::1]`, `0x7f000001`, `2130706433`: refused, because they are not
    under an allowed host. `127.0.0.1.fcm.googleapis.com` is allowed. That is safe: it is a DNS
    name in Google's zone, and Google's DNS answers for it;
  - a missing or broken authority (`https:fcm…`, `https:/fcm…`, `https:///fcm…`,
    `https://[fcm…]`): refused with an empty host.
- **Random cases (400 000), 0 bypasses** (fact): each case was a real address with 1 to 4
  random inserts, swaps or deletes, or random characters on both sides of `fcm.googleapis.com`.
  The characters included `@ \ % ? # [ ] ; : /`, space, tab, newline, NUL, `。`, `．`, `ä`,
  `%2f`, `%40`, `%5c` and `%2e`.
- **Real addresses still pass** (fact): FCM with a `:` in the token, Apple, Mozilla, a WNS
  query with `%2b`/`%3D`, and FCM with no path.
- **Both points run the check** (fact, read in the code): `push.py:96` refuses before the row is
  stored, and `task_handlers.py:180` refuses before the post, with `NoRetry`. The new tests
  prove both: `test_an_address_the_parsers_read_differently_is_400_and_not_stored` (subscribe)
  and the backslash case of `test_an_address_no_longer_allowed_is_not_posted` (send).
- **Redirects** (assessment): `pywebpush` calls `requests.post`, which follows a 307 or 308 to
  any host. Only the push service can send that redirect, and the check trusts that service
  already. So this does not reopen CR1-01. The nit CR2-02 below closes it anyway.

## Findings

### CR2-01 — `minor` — `push_core` imports `urllib3` without declaring it

- **Where:** `backend/push_core.py:19-20`; `backend/pyproject.toml` (dependencies, near line 15).
- **Problem:** the code imports `urllib3` directly, but the project gets it only through
  `requests` (through `pywebpush`). The coder's reason is that the check must use the
  `urllib3` that `requests` uses. A declaration with no upper bound (`"urllib3>=2"`) does not
  pin anything: uv still resolves the one copy that `requests` uses. So the reason does not
  hold.
- **Failure scenarios:**
  - The S022 audit flags stale libraries only for **direct** dependencies. `urllib3` is now
    used directly, but the audit treats it as an indirect one, so a stale `urllib3` is not
    flagged.
  - If a later `pywebpush` or `requests` drops `urllib3`, `push_core` fails at import. `push.py`
    imports it at start-up, so the whole backend does not start, and nothing in `pyproject.toml`
    shows why.
- **Fix:** add `"urllib3>=2"` to `backend/pyproject.toml`, run `uv lock`, and run
  `tooling/run-deps-audit.bat` to regenerate `sbom/`. Commit `sbom/` with the change
  (`.claude/CLAUDE.md` § Software inventory).

## Nits

- **CR2-02** (nit) `backend/push_sender.py:27`: pass `webpush(…, requests_session=s)` with a
  `requests.Session` that has `max_redirects = 0`. Then a redirect from a push service fails as
  a "could not reach" retry and is never followed to another host.
- **CR2-03** (nit) `docs/steps/S021-alerts-push/3-impl-report.md`, Fix rounds › Round 1: it
  says CR1-02 to CR1-08 are left for gate B. CR1-06 and CR1-07 are now fixed by the planner.
  Record them as `Accepted` (fixed in the brief and in Plan.MD) so the report matches the files.

## Earlier findings

| ID | Severity | Status |
|---|---|---|
| CR1-01 | blocker | **Fixed**, verified above |
| CR1-02 | minor | Open: left for the user at gate B |
| CR1-03 | minor | Open: left for the user at gate B |
| CR1-04 | minor | Open: left for the user at gate B |
| CR1-05 | minor | Open: left for the user at gate B |
| CR1-06 | nit | **Fixed** by the planner: `1-brief.md` § 10 A1 rule 6 now states § 1.3's rule ("when this device is not turned on"). A1 is approved text, so the user should see this wording change at gate B |
| CR1-07 | nit | **Fixed** by the planner: `Plan.MD:454` now states the S021 audience per kind, the escalation times and the A1 alert |
| CR1-08 | nit | Open: left for the user at gate B |

## Checked and found consistent

- **The order of the checks in `refused_host`.** The cheap type and length checks come first,
  then `urlsplit`, then the two patterns, then `parse_url`. A `LocationParseError` refuses. Each
  refusal returns the host for the log, never the full address. The shell logs it with `%r`, so
  a control character shows escaped.
- **`_HOST_RE` against `netloc`, not `hostname`.** This is what rules out user-info, ports and
  IPv6 literals. `_HOST_RE` needs at least one dot, so a bare label is refused.
- **`_ADDRESS_RE` over the whole address** allows `%` and `@` after the authority. WNS needs
  this for its encoded token. The fuzz run shows that `requests` still posts to the allowed
  host in those cases.
- **The second parser agrees.** It compares the scheme, user-info, port and host. On the
  ASCII-only addresses left after the patterns, I found no case where the two parsers differ.
- **Test quality.** The 17 refused forms cover each rule of the new check. The 2 passing forms
  guard against refusing too much (WNS, `#@`). The API test checks the status, the message and
  that no row is stored. The send test checks that the sender is never called.
- **The impl report's Fix rounds** follows scope A. It lists the files, the tests, the decisions
  (the `urllib3` import, the logged host) and the first, failed run with its cause.

## Manual checks still needed

None new from this round. The fix is covered by unit tests. The open device rows 14–25 of
`docs/steps/device-checks.md` stay as listed in `4-code-review-r1.md`.
