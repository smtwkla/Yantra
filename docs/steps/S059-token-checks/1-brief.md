```
Step: S059 — Token checks
Doc: brief
Author: Orchestrator (Opus)
Date: 26-10-2026
From: R01.2
Track: full
Status: Done (committed 6b72834; checks: 1 important done by KLA; device-checks row 40 after the deploy)
Baseline: c7803b1
```

# S059 — Token checks

**The point:** a bad token no longer makes Yantra fetch Keycloak's keys, a slow Keycloak holds a
request for at most 5 seconds (not 30), a token from the wrong issuer or of the wrong kind is
refused, and a Keycloak outage answers 503 with its own message instead of "not in the maintenance
team". Audit 21-10-2026 [7], [16] and the token tests of [28]; roadmap item R01.2, which KLA
accepted as written at gate R (26-10-2026, R01 § Decisions). Backend only.

**Track: full.** It changes auth code (`backend/auth_utils.py`): an auth change is never light.
Small: two backend files and one test file.

## 1. What will be built

### 1.1 No evict-and-retry; a key-fetch timeout

Today `validate_keycloak_token` (`backend/auth_utils.py:134-145`) drops the cached `PyJWKClient`
and decodes again on **any** decode failure. A fresh client has an empty cache, so every bad token
from the internet costs a fetch of Keycloak's key list. `_get_jwk_client` (`:75-80`) creates the
client with PyJWT's default timeout of 30 s.

- **Remove the retry** (`:134-145` becomes one `try`). Key rotation still works without it,
  because PyJWT 2.15.1 (`backend/uv.lock:1173-1174`) refetches the key list itself when a token
  names a key id the cache does not hold, at most once per `cooldown_duration` (default 30 s)
  (fact: `jwt/jwks_client.py`, `get_signing_key`, read in the installed source 26-10-2026;
  docstring "Unknown key IDs can trigger one forced refresh after the cooldown"). So junk tokens,
  with an unknown key id or none, cost at most **one key fetch per 30 s** together, not one each.
  A token with a known key id but a bad signature costs none.
- **Accepted limit** (BR1-07): within 30 s after a junk-triggered refetch, a token signed by a
  key Keycloak rotated in just then is refused (401) until the cooldown passes. Keycloak keeps the
  old key valid through a rotation, and rotations are done by hand, so this costs a few 401s once.
- **`timeout=5`** on the client: `jwt.PyJWKClient(jwks_uri, timeout=5)` (the parameter exists,
  `jwks_client.py:43`, default 30). A name for it, `JWKS_TIMEOUT_S = 5`, beside `_jwk_clients`.
- The cache lifespan stays PyJWT's default, 300 s (`lifespan`, `jwks_client.py:41`).

### 1.2 A key-list fetch failure answers 503

When the key list cannot be fetched (Keycloak down, the LAN address wrong, the 5 s timeout),
PyJWT raises `jwt.exceptions.PyJWKClientConnectionError` (a subclass of `PyJWKClientError` and of
`PyJWTError`; checked 26-10-2026: an unreachable URL raised it for a token with and without a key
id). Today that is caught as a bad token: 401, and the start screen says "Your account is not in
the maintenance team" (`frontend/src/stores/auth.js:83-86`).

- `validate_keycloak_token` catches `PyJWKClientConnectionError` **before** `PyJWTError`, logs a
  warning naming the URL itself: `"Keycloak key list not reachable at %s: %s", jwks_url, exc`
  (PyJWT's own message carries the urllib error, not the URL, BR1-09; never the token), and
  **raises** a new exception `LoginServerUnavailable` (defined in `auth_utils.py`) instead of
  returning `None`.
- `require_auth`'s handler catches it, sets `g.access_outcome = "auth_failed"` and
  `g.access_detail = "login_server_down"`, and answers **503** with
  `{"error": LOGIN_SERVER_DOWN_TEXT}`.
- `LOGIN_SERVER_DOWN_TEXT` (a constant in `auth_utils.py`, scope B, as R01.2 gives it):
  "Sign-in cannot be checked right now. The login server does not answer. Try again in a minute."
- **The access log** keeps its `outcome` ENUM (`backend/local_db.py:497`: `ok`, `auth_failed`,
  `denied_network`, `denied_perm`): the outage is `auth_failed` with the new detail code
  `login_server_down` in the `detail` column (`VARCHAR(255)`, `:501`). The roadmap's "its own
  code" is this detail code. `classify_outcome` (`backend/network_core.py:83-94`) already lets a
  marked outcome win. **No migration.** The docstring of `validate_keycloak_token` (`:120-123`)
  lists the codes; it gains `wrong_type`, and says the function **raises**
  `LoginServerUnavailable` on a fetch failure (BR1-08); `require_auth` sets `login_server_down`.
- **What IT Admin sees** (BR1-10): Settings › Access log shows the badge "Login failed"
  (`frontend/src/views/settings/AccessLog.vue:18`, outcome `auth_failed`) with
  `login_server_down` as the detail, one row per client address per day (no user: the token was not
  checked). A stated choice: an outage reads as failed logins with their own reason.
- **During an outage** (BR1-03): while the cached key list is within its 300 s, a token with a
  known key id is checked against it and nothing changes for the user. A token with an unknown key
  id or none (junk) still tries a fetch, because PyJWT's 30 s cooldown counts from the last
  **successful** fetch: it waits up to 5 s and gets the 503, even inside the 300 s. After the 300 s,
  every request waits up to 5 s and gets the 503 (PyJWT caches only a successful fetch). With
  gunicorn's sync workers (`tooling/build/gunicorn.conf.py`), a burst of junk during an outage can
  hold workers 5 s each: accepted, because it is bounded by the timeout (today 30 s), and only
  during an outage.
- **What the user sees today with a 503:** `loadProfile` shows "Could not load your profile:
  " followed by the message (`auth.js:83-86`), so the start screen already reads "Could not load
  your profile: Sign-in cannot be checked right now. …". R01.3 shows the message alone; this step
  changes no frontend file.

### 1.3 Issuer, required claims, a small clock leeway, the token's kind

`_decode` (`auth_utils.py:83-89`) checks only the signature and `exp` today.

- `jwt.decode(token, key, algorithms=["RS256"], issuer=issuer, leeway=TOKEN_LEEWAY_S,
  options={"verify_aud": False, "require": ["exp", "iat", "iss"]})`.
  - **`require` goes in `options`**, not as a keyword: PyJWT 2.15.1 takes a `require=` keyword
    with a `RemovedInPyjwt3Warning` ("Unsupported kwargs: ('require',)") and **ignores it**: a
    token without `exp` or `iat` passed (checked 26-10-2026, `scratch/s059_check.py`). With
    `options={"require": [...]}` a missing `exp`, `iat` or `iss` raises
    `MissingRequiredClaimError` (`scratch/s059_check2.py`). The roadmap item's wording
    (`require=[…]`) is corrected here.
  - **`issuer`** = the public realm URL, `config.KEYCLOAK_REALM_URL` (the `realm_url` argument of
    `require_auth`), never the internal one: the browser signs in at the public URL, so the token's
    `iss` is that URL. `_decode` gains an `issuer` parameter. A wrong `iss` raises
    `InvalidIssuerError` (checked).
  - **`leeway`** `TOKEN_LEEWAY_S = 30`: the server's and Keycloak's clocks may differ by a few
    seconds. Checked: `iat` 20 s ahead passes, 60 s ahead raises `ImmatureSignatureError`; `exp`
    20 s past passes, 40 s past raises `ExpiredSignatureError`.
- **`typ` must be `"Bearer"`**, checked after `azp` and before the roles (claim check, not a
  library option): a Keycloak ID token or refresh token signed by the same realm key has another
  `typ` (`ID`, `Refresh`) and must not open the API. A token whose `typ` is missing or other is
  refused: `g.access_detail = "wrong_type"`, 401, and a warning that logs the claim's value
  (`repr`, cut to 20 characters), never the token (BR1-13). That `typ` is `Bearer` in Yantra's real access
  tokens, and that `iss` equals `KEYCLOAK_REALM_URL` character for character, is **to verify** by
  KLA **at gate A** (§ 5, important check 1, BR1-05): decision 5 and this check rest on it, and a
  mismatch would refuse every user.
- **The algorithm stays pinned** to `RS256` (unchanged): a token signed `HS256` with the realm's
  public key as the secret is refused with `InvalidAlgorithmError` (checked, by a token made by
  hand, since PyJWT refuses to sign HMAC with an asymmetric key).

### 1.4 The `DEV_AUTH_BYPASS` refusal gets its test

`backend/config.py:76-78` raises `RuntimeError` when `DEV_AUTH_BYPASS=1` without `FLASK_DEBUG=1`.
No test covers it (R01 § What exists, [28]). The test imports `config` in a **subprocess**
(`sys.executable -c "import config"`, `cwd` = `backend/`) with an environment that is a **copy of
`os.environ`** (so `YANTRA_TESTING=1` stays and `config.py:30-38` falls back to the example secrets
where `secrets_app.py` is absent, as in the release worktree, BR1-02) plus `DEV_AUTH_BYPASS=1` and
`FLASK_DEBUG=0`, and asserts a non-zero exit and "DEV_AUTH_BYPASS=1 is only
allowed" in stderr. A subprocess, because `config` runs the check at import and is already
imported by the test session.

### 1.5 The base doc text (for KLA, in the impl report)

`SMTW-WebApp-Base.md` § Token decode flow step 5 (`.claude/SMTW-WebApp-Base.md:116`) still says
"On decode failure, evict the cached JWKS client and retry once (handles signing-key rotation)."
The file is synced from smtw-common, so the coder writes the replacement steps 2–5 in the impl
report under `## Base doc text`, for KLA to paste there (as S025 item 9 and S058 did): the 5 s
timeout, the issuer, `options["require"]`, the leeway, `typ`, the 503 on a fetch failure, and
PyJWT's own refetch on an unknown key id instead of the retry. It also writes one entry for the
base's § Common Pitfalls (`.claude/SMTW-WebApp-Base.md:1449`): PyJWT 2.x ignores the
`require=[...]` keyword of `jwt.decode` (deprecated, no error), so a token without `exp` passes;
use `options={"require": [...]}`. CLAUDE-COMMON gets nothing: its rules are not about login.

### Out of scope

- The start screen's text for the 503 and keeping typed input: R01.3.
- The route walk with a role that has no access: R01.6.
- Keeping an expired key list during an outage (PyJWT has no "use stale keys on error"; it would
  need a cache of our own). Rejected in § 4.
- Any frontend file, any migration.

## 2. Standards and practice

- **RFC 8725, JSON Web Token Best Current Practices** (section numbers to verify): pin the
  accepted algorithms (§ 3.1), validate the issuer (§ 3.8), use explicit typing so one kind of
  token cannot stand in for another (§ 3.11). This step does all three: `RS256` only, `iss`
  checked, `typ` = `Bearer`. § 3.11 means the JOSE **header** `typ` (`at+jwt`, RFC 9068); Keycloak
  puts `JWT` there for every kind of token, so the step follows § 3.11's intent with Keycloak's
  payload claim `typ` (BR1-06). **Departure** from § 3.9 (use and validate the audience): `aud` is
  not checked, because Keycloak sets `aud=account`; `azp` = the client id stands in (unchanged,
  the base pattern).
- **OWASP ASVS 5.0, V9 Self-contained Tokens** (to verify): a server that accepts a signed token
  checks the issuer, the expiry and the token's kind. Same three checks, plus `exp`, `iat` and
  `iss` required.
- **ISO/IEC 27001:2022 A.8.5 Secure authentication** (to verify): sign-in failures are handled
  safely. A login-server outage reads as an outage (503), not as a refusal of the person.
- **ISO 27001 A.8.29 Security testing in development and acceptance** (to verify): the token
  rules each get a test (§ 5).

## 3. Where

| File | Change |
|---|---|
| `backend/auth_utils.py` | § 1.1–1.3: no retry; `timeout=5`; `LoginServerUnavailable` and `LOGIN_SERVER_DOWN_TEXT`; `_decode(token, jwks_url, issuer)` with `issuer`, `leeway`, `options["require"]`; the `typ` check (`wrong_type`); `require_auth` answers 503 (`login_server_down`); docstrings |
| `backend/tests/test_auth.py` | `_token` gains `iss`, `iat` and `typ` (defaults valid, each can be left out or changed); the default `iss` is **`config.KEYCLOAK_REALM_URL`**, never a literal, and `_validate` passes that same value (BR1-01: the `client` tests go through `app.py`'s `require_auth(config.KEYCLOAK_REALM_URL, …)`, and the laptop's `secrets_app.py` may differ from the example the release worktree uses); the new tests of § 5 |
| `backend/tests/test_config.py` (new, or the file that already tests `config`; the coder checks) | § 1.4 the `DEV_AUTH_BYPASS` refusal |

### Docs (housekeeping, by the coder)

- `.claude/CLAUDE.md`: none due (no new invariant, command, port or secret).
- `docs/Keycloak.md:40-42` **is due** (BR1-04): "checks the token's signature …, its expiry, and
  that `azp` …" becomes the full list: signature (`RS256` only), issuer = the public realm URL,
  `exp`, `iat` and `iss` required with 30 s leeway, `typ` = `Bearer`, `azp`; not `aud`; a key-list
  fetch failure answers 503.
- The base doc text: in the impl report (§ 1.5), not in the synced file.

## 4. Design decisions

1. **Remove the evict-and-retry and rely on PyJWT's refetch on an unknown key id.** It covers
   key rotation (the new key's id is unknown, so it refetches) and caps junk at one fetch per
   30 s. Rejected: keep the retry but only for "unknown key id" errors — PyJWT already does that,
   so it would be a second fetch for the same token.
2. **A fetch failure is 503 with outcome `auth_failed`, detail `login_server_down`.** No new
   ENUM value, so no migration. Rejected: a new outcome `login_server_down` (a migration of
   `access_log` for one code that the detail column already carries).
3. **A dedicated exception (`LoginServerUnavailable`) carries the 503** from the validator to the
   handler. `validate_keycloak_token` keeps returning `None` for a refused token. Rejected:
   returning a sentinel or reading `g.access_detail` in the handler to pick the status (a status
   chosen by a log code).
4. **`typ` checked in our code**, not by PyJWT: PyJWT's `typ` support is for the header, while
   Keycloak puts `typ: Bearer` in the payload.
5. **The issuer is the public realm URL** (`realm_url`), also when the keys come from the LAN
   address (`internal_realm_url`). The token names who issued it; where we fetch keys is ours.
   address (`internal_realm_url`). The token names who issued it; where we fetch keys is ours.
6. **No stale-key fallback during an outage.** Rejected: our own cache that keeps the last good
   key list past 300 s. More code in the security path for an outage that the 5 s timeout and the
   503 message already make clear.

## 5. Tests and acceptance

All in `backend/tests/test_auth.py` (`TestValidateToken`, `TestMiddleware`, `TestAccessLogMarks`)
unless named. The existing tests keep passing once `_token` gives `iss`, `iat` and `typ`.

- **Issuer:** a token with `iss` = another realm → `None`, `g.access_detail == "invalid_token"`.
- **Required claims:** no `exp` → refused; no `iat` → refused; no `iss` → refused (each
  `invalid_token`).
- **`typ`:** `typ` = `"ID"` → refused, `wrong_type`; no `typ` → refused, `wrong_type`.
- **Algorithm pinning:** a hand-made `HS256` token whose HMAC secret is the stub key's public PEM
  → refused, `invalid_token`.
- **Leeway:** `iat` 20 s ahead → accepted; `iat` 60 s ahead → refused; `exp` 20 s past →
  accepted.
- **No retry:** a token signed by another key is decoded **once**: the stub client counts its
  `get_signing_key_from_jwt` calls and the count is 1 (today 2).
- **Fetch failure:** the stub client raises `PyJWKClientConnectionError` →
  `/api/auth/me` answers 503 with `LOGIN_SERVER_DOWN_TEXT`; `g.access_outcome == "auth_failed"`,
  `g.access_detail == "login_server_down"`; and through the access log (`TestAccessLogMarks`, the
  `db_rows` fixture as `test_the_session_id_is_logged` uses it) a row with that detail.
- **Timeout:** `_get_jwk_client` builds its client with `timeout == 5` (assert the attribute of
  the real `PyJWKClient`, created without a network call). The autouse `stub_jwks` fixture replaces
  `_get_jwk_client`, so the test keeps a module-level reference to the real function taken at
  import, and pops its URL from `_jwk_clients` before and after (BR1-11).
- **Junk during an outage** (BR1-03): with the stub client raising `PyJWKClientConnectionError`
  for any token, a token with an unknown key id also gets the 503 (the brief's stated behaviour).
- **`DEV_AUTH_BYPASS`:** § 1.4.
- **Always-check tests** (settings: *Self-check, repo items*): `test_rbac.py` (no key changes),
  `conftest.py` `_TABLES` (no table), `db_down` (`TestDatabaseDown` still passes), the migration
  tests (no migration). The browser tests sign in through `X-Test-Role`, which `require_auth`
  answers before the token path, so they prove nothing about tokens: no browser run is due (BR1-12).
- **Full unit suites** green (`tooling/run-tests.bat`).

**On a real device / by a person:**

1. **Important — at gate A, KLA** (BR1-05): check one real access token's claims. **Account:**
   KLA's own login; **network:** the plant network or mobile data, either; **where:** production
   (`https://vel-yantra.mspv.app`) in a desktop browser. DevTools › Network, any `/api/` request,
   copy the `Authorization` header's token (a **live credential**: paste it only into your own
   terminal, never into a chat or a file; it expires within minutes), then in a terminal:
   `uv run --no-project python -c "import sys,json,base64;p=sys.argv[1].split('.')[1];print(json.dumps(json.loads(base64.urlsafe_b64decode(p+'='*(-len(p)%4))),indent=1))" <token>`.
   Pass: `"typ": "Bearer"`, `"iss"` equal to `KEYCLOAK_REALM_URL` in the production secrets,
   `"iat"` and `"exp"` present. Report only the values of `typ` and `iss`. A mismatch changes the
   design before coding (every user would get 401).
2. After the deploy: sign in on production as a normal user; the start screen opens. (Not
   important: the release's own check covers it.)

## 6. Open questions and assumptions

1. **Assumption (to verify, check 1):** Keycloak's access tokens carry `typ: "Bearer"`, `iat`,
   and `iss` equal to the public realm URL. Keycloak documents `typ` for access tokens as
   `Bearer`; Yantra's own tokens were never decoded in this repo.
2. **Assumption:** no other code calls `_decode` or reads the JWKS cache (`_jwk_clients`); the
   facts run lists the users.

## 7. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 26-10-2026

| Finding | Answer |
|---|---|
| BR1-01 minor: the test tokens' `iss` must be `config.KEYCLOAK_REALM_URL` | Accepted (§ 3, `test_auth.py` row) |
| BR1-02 minor: the subprocess must keep `YANTRA_TESTING=1` | Accepted: a copy of `os.environ` (§ 1.4) |
| BR1-03 minor: junk tokens during an outage still try a fetch | Accepted: § 1.2 corrected, the worker cost stated and accepted, a test added (§ 5) |
| BR1-04 minor: `docs/Keycloak.md` is due | Accepted (§ 3, Docs) |
| BR1-05 minor: do check 1 at gate A, with account, network and a credential warning | Accepted (§ 1.3, § 5 check 1) |
| BR1-06…BR1-14 nits | Accepted, all: § 3.11 and the § 3.9 departure stated; the rotation limit; the docstring says it raises; the warning names the URL; what the Access log shows; the timeout test bypasses the stub; no browser run; `typ` logged by value only; Plan.MD's Security hardening row gains a clause at approval (BR1-14) |

### Gate A — 26-10-2026

KLA: "S059 approved". Important check 1 (a real token's `typ` and `iss`) was not reported at the
gate: it stays open and must pass before the release (a mismatch refuses every user). Coder: Opus
(sign-in code). Plan.MD § 1 Security hardening row gains the clause (BR1-14).

### Code review r1 — `4-code-review-r1.md` (Opus), 26-10-2026

0 blocker, 0 major, 1 minor, 1 nit; both fixed in fix round 1 (Opus). CR1-01: a key list that is
not JSON, or a connection reset mid-body, now answers 503 `login_server_down` (the catch wraps only
the key fetch; a junk token header stays 401, tested). CR1-02: the 5 s limit is per connect and per
read, stated in the comment and `docs/Keycloak.md`. Unit suites green (`s059f1`: backend 3098,
frontend 189, tooling 185). The orchestrator checked the fix; no second review round (minor only).
