```
Step: S059 — Token checks
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 26-10-2026
```

# S059 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** One `minor` finding and one nit. The token
checks match the brief and PyJWT 2.15.1's real behaviour. Two rare key-fetch failures still answer
500 instead of 503 (CR1-01).

## Tests run

- `YANTRA_TEST_RUN=s059cr1 tooling/run-tests.bat`: all suites PASSED.
  - backend: 3095 passed (104 s)
  - frontend: 189 passed (17 s)
  - tooling: 185 passed (2 s)
- No frontend change in S059, so no build check.
- Browser tests: none re-run. The coder ran the whole suite at Normal once (214 passed, 7 skipped).
  The brief (BR1-12) says no browser run proves anything about tokens: the browser tests sign in
  by `X-Test-Role`, which `require_auth` answers before the token path. No finding of mine needs a
  browser run.
- A read-only check against the installed PyJWT 2.15.1 (a local throwaway HTTP server in the
  session scratchpad, `s059_fetch.py`):

  | What the key-list URL returned | What `get_signing_key_from_jwt` raised | S059's answer |
  |---|---|---|
  | 200 with an HTML page | `json.JSONDecodeError` (a `ValueError`, not a `PyJWTError`) | 500 |
  | 200, the connection reset mid-body | `ConnectionResetError` (an `OSError`) | 500 |
  | 200 with a JSON list | `PyJWKClientError` | 401 `invalid_token` |
  | 200 with `{"keys": []}` | `PyJWKSetError` | 401 `invalid_token` |
  | no server, a timeout, an HTTP error status, a redirect (read in the source) | `PyJWKClientConnectionError` | 503 |

## Findings

### CR1-01 (minor) — Two key-fetch failures still answer 500, not 503

- **Where:** `backend/auth_utils.py:107` (the key lookup in `_decode`) and `:162` (the one `except`
  for an outage).
- **Problem:** `PyJWKClient.fetch_data` (`jwt/jwks_client.py`, installed 2.15.1) wraps only
  `URLError`, `TimeoutError` and `http.client.HTTPException` in `PyJWKClientConnectionError`. Two
  failures escape unwrapped:
  - an HTML page with status 200 raises `json.JSONDecodeError`;
  - a connection that drops while the body is read raises `ConnectionResetError`, an `OSError`
    (an `ssl.SSLError` during the read is an `OSError` too).

  Neither is a `PyJWTError`, so `validate_keycloak_token` does not catch it. The `before_request`
  hook raises, and Flask answers 500 (`app.py` has only a `DBUnavailable` handler). This is
  fail-closed: nobody gets in. It was the same before S059. But the step's point is that "a
  Keycloak outage answers 503 with its own message", and the orchestrator asked for every fetch
  failure to map to 503.
- **Failure scenario:** someone restarts Keycloak, or the front proxy in front of it serves a
  maintenance page with status 200. Each request whose key list is not cached gets a 500 with no
  message of its own. The start screen shows a generic error instead of "Sign-in cannot be checked
  right now". The log shows a traceback instead of the `login_server_down` row in the access log.
- **Suggested fix:** in `_decode`, wrap only the key lookup (line 107), not `jwt.decode`:
  `except (json.JSONDecodeError, OSError) as exc: raise jwt.exceptions.PyJWKClientConnectionError(f"key list unreadable: {exc!r}") from exc`.
  The existing `except` at `:162` then turns it into the 503. Keep the catch that narrow, so
  that no junk-token path can become a 503. Add one test that sets a stub client raising
  `ConnectionResetError`, one that raises `json.JSONDecodeError`, and assert 503 with
  `login_server_down` for each. Record the red result on the current code.

## Nits

- **CR1-02** (nit) `docs/Keycloak.md:51`, `backend/auth_utils.py:52`: urllib's `timeout` limits
  each connect and each read, not the whole fetch, and a DNS lookup is not limited at all. Write
  "a 5 s limit on each connect and read" in the doc and the comment, so that nobody reads it as a
  hard total.

## Manual browser check (for the user)

- No screen changed, so there is no browser check.
- **Important, open:** device-checks row 39 (brief § 5 check 1). KLA decodes one real production
  token. Pass: `typ` is `Bearer`, and `iss` equals `KEYCLOAK_REALM_URL` character for character.
  It must pass before the release. If either differs, every user gets 401.
- Row 40: after the deploy, a normal user signs in on production and the start screen opens.

## Checked and found consistent

- **Decode options**, against the installed PyJWT 2.15.1:
  - `require` is in `options`, not a keyword;
  - `algorithms=["RS256"]` only;
  - `issuer=realm_url` is the public URL, also when the keys come from the LAN address;
  - `leeway=30`;
  - `verify_aud: False`.

  The tests run the real `jwt.decode`, so each rule is shown working.
- **The retry is gone:** a bad token makes one key lookup.
  - PyJWT refetches by itself for an unknown or missing `kid`, once per 30 s after the last good
    fetch, under the client's own lock.
  - A failed fetch does not clear the cache (`fetch_data` stores only a good result).
  - A rotated key is found by that refetch.
- **`timeout=5`:** the real `PyJWKClient` is checked. The test bypasses the autouse stub and pops
  its URL before and after (BR1-11).
- **503 path:**
  - `PyJWKClientConnectionError` is caught before `PyJWTError`, and the validator raises
    `LoginServerUnavailable`;
  - the handler sets `auth_failed` / `login_server_down` and answers 503 with
    `LOGIN_SERVER_DOWN_TEXT`;
  - the network gate and the later hooks are skipped, because the handler returned a response;
  - the access-log row is checked through the app;
  - `frontend/src/api.js` and `stores/auth.js` have no handling of their own for a 503, so the
    brief's "Could not load your profile: …" holds.
- **Fail-closed:** every path is closed.
  - A `typ` other than `Bearer`, or none, is refused (`wrong_type`), after `azp` and before the
    roles.
  - An unexpected exception gives a 500 (CR1-01), never a 200.
- **Logging:** no token or key is logged.
  - The outage warning names the URL and urllib's error.
  - The `typ` warning logs `repr(...)[:20]`, which escapes newlines.
  - The test checks that the token is not in the line.
- **The `DEV_AUTH_BYPASS` refusal:**
  - the test runs a subprocess with a copy of `os.environ` (keeps `YANTRA_TESTING=1`, BR1-02);
  - it asserts a non-zero exit and the message;
  - it matches `config.py:76-78`.
- **The tests would fail on the old code:**
  - decoded once: 2 calls before;
  - issuer, required claims and `typ`: the old code accepts those tokens;
  - leeway: the old code had none, so `iat` +20 s and `exp` −20 s were refused;
  - the 503: the old code gave 401;
  - the timeout: 30 s before.

  Only the HS256 test and the config test pass on the old code too: both guard rules that were
  already there. The coder checked the config test both ways by hand. A round-1 implementation has
  no fix-round red rule, and the report gives its reasons.
- **Tests:** they cover every item of the brief's § 5, the junk-during-outage case (BR1-03), and
  the failure codes.
  - `access_log` is in `conftest.py` `_TABLES`, so the access-log test's one-row assertion holds
    on a re-run.
  - The always-check tests pass in the full run.
- **Scope:** everything in the brief is built and nothing beyond it. The impl report's
  "Decisions taken" covers the test-only choices. There is no departure.
- **Docs pass:**
  - `docs/Keycloak.md` § 1 lists every check (BR1-04);
  - device-checks rows 39 and 40 are added;
  - `Plan.MD` has the S059 clause (gate A);
  - no migration and no secret, so no schema doc or `CLAUDE.md` change is due;
  - the base doc text is in the impl report, as § 1.5 asks.
- **Manual checks:** the impl report's `## Manual checks` carries important check 1 as an unticked
  box.
- **Design:** the changes stay in the auth shell, with no new layer. The constants are named
  beside the cache. The comments say why.

## Feedback

- idea: the brief and the review prompt list "which exceptions a fetch failure raises" as checked, but the brief's check tried only an unreachable URL; a short table of the odd responses (HTML 200, reset, empty keys) at brief time would have caught CR1-01 earlier (`scratch` check, 1 run, 1 min)
- none further
