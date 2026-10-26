```
Step: S059 — Token checks
Doc: impl-report
Author: Coder (Opus)
Date: 26-10-2026
```

# S059 — Implementation report

**Result:** the token checks of the brief are built in `backend/auth_utils.py`, with 20 new
backend tests (19 in `test_auth.py`, 1 in `test_config.py`). All unit suites and the whole browser suite at Normal are green. Important
check 1 (a real production token's `typ` and `iss`) is still open and is KLA's: it must pass
before the release, because a mismatch would refuse every user.

## 1. What was built

- **No evict-and-retry.** A token that fails to decode is decoded once. Key rotation is left to
  PyJWT's own refetch on an unknown key id (at most once per 30 s).
- **A 5 s key-fetch timeout** (`JWKS_TIMEOUT_S = 5`) on the cached `PyJWKClient`.
- **Stricter decode:** `RS256` only (unchanged), the issuer must equal the public realm URL,
  `exp`, `iat` and `iss` are required (in `options["require"]`), and a 30 s leeway
  (`TOKEN_LEEWAY_S`) applies to `exp` and `iat`.
- **The token's kind:** the payload claim `typ` must be `"Bearer"`. Otherwise the answer is 401,
  with detail `wrong_type`.
- **Keycloak down answers 503** with `LOGIN_SERVER_DOWN_TEXT` ("Sign-in cannot be checked right
  now. The login server does not answer. Try again in a minute."). The access log row is
  `auth_failed` with detail `login_server_down`.
- **A test for the `DEV_AUTH_BYPASS` refusal** in `config.py`, in a subprocess.

## 2. How it works

1. `validate_keycloak_token` calls `_decode(token, jwks_url, realm_url)`. `jwks_url` is still the
   LAN address when one is set; the issuer passed is always the public `realm_url` (decision 5).
2. `_decode` gets the signing key from the cached client, then calls `jwt.decode` with
   `algorithms=["RS256"]`, `issuer=issuer`, `leeway=30` and
   `options={"verify_aud": False, "require": ["exp", "iat", "iss"]}`. The old explicit
   `verify_exp: True` is dropped: it is PyJWT's default.
3. Errors are caught in this order:
   - `PyJWKClientConnectionError` (the key list cannot be fetched): a warning
     `"Keycloak key list not reachable at %s: %s"` with the URL, then
     `raise LoginServerUnavailable(jwks_url)`;
   - any other `PyJWTError`: a warning, `g.access_detail = "invalid_token"`, `None`.
4. After the `azp` check and before the roles, a `typ` other than `"Bearer"` (or none) logs
   `"Token typ %s is not Bearer"` with `repr(typ)[:20]`, sets `wrong_type` and returns `None`.
5. `require_auth`'s handler catches `LoginServerUnavailable`, sets
   `g.access_outcome = "auth_failed"` and `g.access_detail = "login_server_down"`, and answers
   `503 {"error": LOGIN_SERVER_DOWN_TEXT}`. `classify_outcome` lets the marked outcome win, so the
   access log writes that row. No migration.

## 3. Files touched

| File | Change |
|---|---|
| `backend/auth_utils.py` | `JWKS_TIMEOUT_S`, `TOKEN_LEEWAY_S`, `LOGIN_SERVER_DOWN_TEXT`, `LoginServerUnavailable`; `timeout=` on the client; `_decode(token, jwks_url, issuer)`; the retry removed; the `typ` check; the 503 in `require_auth`; the docstring lists `wrong_type` and says the validator raises |
| `backend/tests/test_auth.py` | `_token` gives `iss` (= `config.KEYCLOAK_REALM_URL`), `iat` and `typ`, each changeable or left out by `OMIT`, plus `headers` (for a `kid`); the stub counts its calls; `_DownJWKClient` and the `jwks_down` fixture; `_validate` and the failure-code test pass `ISSUER`; new classes `TestTokenChecks` and `TestLoginServerDown` |
| `backend/tests/test_config.py` | new: the `DEV_AUTH_BYPASS` refusal in a subprocess |
| `docs/Keycloak.md` | § 1: the full list of token checks, the key-list fetch and the 503 |
| `docs/steps/device-checks.md` | rows 39 and 40 (S059) |
| `docs/steps/S059-token-checks/1-brief.md`, `docs/steps/INDEX.md` | status `In code review` |

## 4. Decisions taken

1. **`_token`'s `exp` is left out by `exp_in=OMIT`**, the same sentinel as `iat_in`, `iss` and
   `typ`. One way to drop any claim.
2. **The algorithm-confusion token is built by hand** (`_hs256_token_keyed_by_public_pem`, about
   10 lines with `hmac` and `base64`), as the brief says: PyJWT refuses to sign HMAC with an
   asymmetric key.
3. **The access-log test uses addresses in `198.18.0.0/15`**, made from the `uniq` counter. It
   does not reuse `test_access_log_api.py`'s `ip` fixture: moving that fixture to `conftest.py`
   would change a shared fixture file for one test. The two-line formula is a small near-copy;
   the other range keeps the two files' addresses apart in the same worker database.
4. **The 503 test calls the handler directly** (`require_auth(ISSUER, CLIENT_ID)()` in a request
   context) to read `g.access_outcome` and `g.access_detail`, and a second test goes through the
   app and reads the row from `access_log`. The brief asks for both.
5. **Leeway tests:** besides the brief's three cases, `exp` 40 s past is refused, so the test also
   shows the leeway's upper side for `exp`.
6. **`typ` cases:** `Refresh` added beside `ID` and a missing `typ`.
7. **`test_config.py` is new**: no test file covered `config` before.

No departure from the brief.

## 5. Not done, deferred or assumed

- **Important check 1 is open** (KLA, a real production token's `typ` and `iss`). The step
  rests on it: if production's `typ` is not `Bearer`, or `iss` differs from
  `KEYCLOAK_REALM_URL` by one character, every user gets 401 after the deploy. It must pass
  before the release.
- **Red runs:** the new tests were not run against the old code. The task is an implementation,
  not a fix round; the old code also lacks the names the tests import (`LOGIN_SERVER_DOWN_TEXT`,
  `JWKS_TIMEOUT_S`). By reading: `test_a_bad_token_is_decoded_once` would count 2 calls on the
  old code; the issuer, required-claim and `typ` tests would pass the token. The subprocess test
  was checked both ways by hand: `FLASK_DEBUG=1` imports with exit 0, `FLASK_DEBUG=0` exits 1
  with the `RuntimeError`.
- **Assumption 2 of the brief** holds: only `auth_utils.py` calls `_decode` and uses
  `_jwk_clients` (grep of `backend/`, apart from `tests/test_auth.py`).
- `test_access_log_api.py` sends `Bearer not-a-jwt` through the real client: PyJWT fails on the
  header before any fetch, so it is still `invalid_token` with no network call (its tests pass).

## Tests

- Targeted while coding: `tests/test_auth.py` (59 passed), `tests/test_config.py` and
  `tests/test_access_log_api.py` (37 passed).
- Final full run, `YANTRA_TEST_RUN=s059c1 tooling/run-tests.bat`:
  - `backend: PASSED in 118 s: 3095 passed`
  - `frontend: PASSED in 33 s: 189 passed`
  - `tooling: PASSED in 2 s: 185 passed`
- Browser tests: the whole suite at Normal once (`tooling/run-e2e-tests.bat`, no flag), as the
  orchestrator asked: `214 passed, 7 skipped (2.3m)`, `All lanes done in 152 s`. It proves
  nothing about tokens (the browser tests sign in by `X-Test-Role`, BR1-12); it shows that the
  screens still work.
- Always-check tests: `test_rbac.py` (no key change), `conftest.py` `_TABLES` (no table),
  `TestDatabaseDown` and the migration tests: all in the green full run.

## Manual checks

The step changes no screen, so it has no *Automated* browser check.

- [x] **Important — KLA, before the release** (brief § 5 check 1, device-checks row 39): decode
  one real production access token in your own terminal. Pass: `"typ": "Bearer"`, `"iss"` equal
  to `KEYCLOAK_REALM_URL` in the production secrets, `"iat"` and `"exp"` present. Report only
  `typ` and `iss`.
  Done by KLA, 26-10-2026: `typ` and `iss` both OK (KLA ran `scratch/check_token.py`, which reads only those two claims; `iat` and `exp` were not read — Keycloak sets both on every access token).
- After the deploy, sign in on production as a normal user; the start screen opens
  (device-checks row 40).

## Docs updated

- `docs/Keycloak.md` § 1: the token checks (RS256, issuer, required claims with 30 s leeway,
  `typ` = `Bearer`, `azp`, not `aud`), the 5 s key fetch and PyJWT's refetch, and the 503.
- `docs/steps/device-checks.md`: rows 39 and 40.
- `docs/Plan.MD`: no change by the coder; the Security hardening row already has the S059 clause
  (recorded at gate A, BR1-14).
- `.claude/CLAUDE.md`: none, because the step adds no invariant, command, port or secret.
- `docs/schema.md`, `docs/schema.html`: none, because there is no migration.
- `.claude/SMTW-WebApp-Base.md`: not edited (synced from smtw-common); the text for it is below.

## Base doc text (for smtw-common)

For KLA to paste into `SMTW-WebApp-Base.md` in smtw-common.

**§ Keycloak Token Validation Pattern › Token decode flow** — replace steps 2–5 with:

```markdown
2. Use one cached `jwt.PyJWKClient` per JWKS URL, built with `timeout=5` (PyJWT's default is
   30 s, so a slow Keycloak would hold a worker that long). Keep PyJWT's own caching: the key
   list for 300 s (`lifespan`), and one forced refetch for a key id it does not hold, at most
   once per `cooldown_duration` (30 s). That refetch covers signing-key rotation.
3. Decode with `algorithms=["RS256"]` (pinned: never take the algorithm from the token),
   `issuer=<the public realm URL>` (the URL the browser signs in at, also when the keys are
   fetched from a LAN address), `leeway=30` (clock difference), and
   `options={"verify_aud": False, "require": ["exp", "iat", "iss"]}`. Keycloak sets
   `aud="account"`, not the client_id, so the audience is not checked.
4. Check the `azp` (authorized party) claim matches the expected `client_id` — this replaces the
   audience check. Then check the payload claim `typ` is `"Bearer"`: Keycloak's ID and refresh
   tokens are signed by the same realm key and carry `ID` or `Refresh`, and must not open the
   API. Log the claim's value cut short, never the token.
5. Do **not** evict the cached client and retry on a decode failure: a fresh client has an empty
   cache, so every bad token from the internet would cost a fetch of the key list. When the key
   list cannot be fetched (`jwt.exceptions.PyJWKClientConnectionError`, caught before
   `PyJWTError`), log a warning with the JWKS URL and answer **503** with a message of its own
   ("Sign-in cannot be checked right now. The login server does not answer. Try again in a
   minute."), not 401: an outage must not read as "you have no access". Log it as a failed
   login with its own detail code (Yantra: `auth_failed` / `login_server_down`).
```

**§ Common Pitfalls** — one row:

```markdown
| `jwt.decode(..., require=[...])` ignored                  | PyJWT 2.x takes the `require=` keyword with only a deprecation warning and ignores it, so a token without `exp` passes. Use `options={"require": ["exp", "iat", "iss"]}` |
```

## Feedback

- waste: the first test edit, a Python script in a Bash heredoc, failed on bash quoting and changed nothing; redone with Edit (1 run, 2 min)
- hindrance: the whole browser run is asked for although the brief says it proves nothing about tokens (BR1-12); the brief and the coder rules disagree on whether it is due (2.5 min machine time)
- none further

## Fix rounds

### Round 1

Both findings of `4-code-review-r1.md` are fixed. Test run name `s059f1`.

- **CR1-01 (minor) — Fixed.** `_decode` (`backend/auth_utils.py`) now wraps only the key lookup
  (`get_signing_key_from_jwt`) in `except (json.JSONDecodeError, OSError)` and raises
  `PyJWKClientConnectionError("key list unreadable: …") from exc`. The existing handler in
  `validate_keycloak_token` turns it into `LoginServerUnavailable`, so a 200 HTML page or a
  connection reset mid-body now answers 503 with `login_server_down`. `jwt.decode` stays outside the
  catch. A token error stays a 401: PyJWT reads the token header before any fetch and turns a bad
  header into `DecodeError` (a `PyJWTError`, not a `ValueError` that reaches the catch).
  New tests in `backend/tests/test_auth.py`, class `TestLoginServerDown`:
  - `test_an_unreadable_key_list_answers_503[connection_reset]` and `[html_page]` (a stub client
    `_RaisingJWKClient` raises `ConnectionResetError` / `json.JSONDecodeError`; asserts 503, the
    text and `auth_failed` / `login_server_down`). Fails without the fix: the exception escapes
    `require_auth` (`E ConnectionResetError: [Errno 10054] connection reset mid-body`,
    `E json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)`; 2 failed); passes
    with it (3 passed with the guard below).
  - `test_a_token_with_a_junk_header_stays_401`: the guard the orchestrator asked for. It uses the
    real `PyJWKClient` (an `example.test` URL that is never fetched) and a token whose header is not
    JSON; asserts `None` and `invalid_token`. It passes on the old code as well, because it guards
    a rule that was already there: the new catch must not turn this into a 503.
- **CR1-02 (nit) — Fixed.** The comment at `JWKS_TIMEOUT_S` and `docs/Keycloak.md` § 1 now say
  the 5 s is urllib's limit on each connect and each read, not on the whole fetch, and that a DNS
  lookup has none. The doc also names the fetch failures that answer 503 (no answer, an error
  status, a page that is not JSON, a connection that drops). No test: wording only.

Tests:
- targeted `tooling/run-backend-tests.bat tests/test_auth.py tests/test_config.py`: PASSED, 63 passed.
- full `YANTRA_TEST_RUN=s059f1 tooling/run-tests.bat`: backend PASSED 3098 passed (60 s); frontend
  PASSED 189 passed (16 s); tooling PASSED 185 passed (1 s); ALL SUITES PASSED.
- No browser run: no screen changed, and fix rounds make targeted runs only.

Files: `backend/auth_utils.py` (the catch, `import json`, the timeout comment),
`backend/tests/test_auth.py` (`_RaisingJWKClient`, three tests), `docs/Keycloak.md` (the timeout and
503 wording).

Docs updated: `docs/Keycloak.md` (CR1-02). No other doc is due: no migration, secret, role or rule.

#### Feedback (round 1)

- hindrance: the orchestrator asked for `## Fix round 1`, the coder definition for `### Round N` under `## Fix rounds`; I used the latter (this file)
