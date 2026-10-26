```
Step: S059 — Token checks
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 26-10-2026
From: R01.2
```

Reviewed against: c7803b1 + uncommitted S048 and S059 step files, `docs/steps/INDEX.md`, the R01 roadmap row (no code change uncommitted)

# S059 — Brief review, round 1

**Verdict: no `blocker` or `major` finding is open.** Five `minor` findings and nine nits. The design
holds: I re-ran both check scripts and read PyJWT 2.15.1's installed `jwks_client.py`; every library
claim in § 1.1–1.3 is right. The minors are rules the coder would otherwise settle alone (the test
tokens' issuer, the subprocess test's environment), one incomplete statement about an outage, one
doc the step makes due, and the timing of the important check.

Facts file used: `scratch/brief-facts-S059.md`.

## Findings

### BR1-01 — minor — The test tokens' `iss` must be `config.KEYCLOAK_REALM_URL`, not a literal

**Problem.** § 3 says `_token` gains `iss` and "`_validate` passes the same issuer". Two paths check
the issuer in the tests: `_validate` (`test_auth.py:58-61`, realm `https://sso.example/realms/R`) and
every `client.get(..., headers=_bearer(_token(...)))` test, which goes through `app.py:53`'s
`require_auth(config.KEYCLOAK_REALM_URL, ...)` (fact: the `client` fixture is `app.py`'s app,
`conftest.py:132`). Today the two realm URLs differ and nobody checks `iss`, so it does not matter.
After this step, one default `iss` must satisfy both.

**Why it matters.** A literal (`https://sso.mspv.app/realms/Office.smtw.in`, the example secrets'
value) passes in the release worktree, which has only `example_secrets_app.py`, and on the laptop only
if `secrets_app.py` holds the same URL. `config.KEYCLOAK_REALM_URL` is right in both places.

**Options.**
- (a) **Recommended:** `_token(..., iss=config.KEYCLOAK_REALM_URL)` as the default, and `_validate`
  passes `config.KEYCLOAK_REALM_URL` as `realm_url` (the `TestAccessLogMarks.test_failure_codes`
  call at `:243` too). Write it so in § 3.
- (b) Keep `https://sso.example/realms/R` in `_validate` and give the middleware tests their own
  `iss`. Two values for one thing; rejected.

### BR1-02 — minor — The `DEV_AUTH_BYPASS` subprocess must keep `YANTRA_TESTING=1`

**Problem.** § 1.4 says the subprocess runs `import config` "with `DEV_AUTH_BYPASS=1` and
`FLASK_DEBUG=0` in its environment". `config.py:30-38` imports `secrets_app` first and falls back to
the example only when `IS_DEV or IS_TESTING`; the `DEV_AUTH_BYPASS` check is later (`:76-78`). The
tests set `YANTRA_TESTING=1` in `conftest.py:20`.

**Why it matters.** A subprocess with a fresh environment (only the two variables) finds no
`secrets_app.py` in the release worktree (gitignored) and exits with "secrets_app.py not found",
not with the bypass message: the test passes on the laptop and turns the release tests red. A
fresh environment on Windows also drops `SYSTEMROOT` and `PATH`, which Python needs.

**Options.**
- (a) **Recommended:** state in § 1.4: `env = {**os.environ, "DEV_AUTH_BYPASS": "1",
  "FLASK_DEBUG": "0"}` (so `YANTRA_TESTING=1` stays and the secrets fallback works where
  `secrets_app.py` is absent); `cwd` = `backend/`; assert exit code 1 and the message in stderr.
- (b) Also assert the happy path: `FLASK_DEBUG=1` with the bypass exits 0. Cheap; optional.

### BR1-03 — minor — § 1.2's "during an outage" statement is incomplete

**Problem.** § 1.2 says: while the cached key list is within its 300 s, "tokens keep being checked
against it and nothing changes for the user"; after that each request waits up to 5 s. That is right
for tokens with a known key id. A token whose key id the cache does not hold (junk, a token of another
realm, a token with no `kid`) is different (fact, `jwks_client.py` `get_signing_key`): the cooldown is
measured from the **last successful fetch**, and a failed fetch does not reset it. So during an outage
every such request, inside the 300 s too, tries a fetch, waits up to 5 s, and gets the 503 (not 401).
The cached list survives (PyJWT writes the cache only on success), so real users keep working.

**Why it matters.** Production runs 3 **sync** gunicorn workers (`tooling/build/gunicorn.conf.py`):
three junk requests at once hold the whole app for 5 s. The 5 s timeout bounds it, and the design is
still right, but the brief's statement is what the coder tests and what KLA approves. A probe can also
tell that Keycloak is down from the 503; that is acceptable and should be said.

**Options.**
- (a) **Recommended:** correct the bullet: during an outage a token with a known key id is checked
  from the cache for up to 300 s; a token with an unknown or missing key id waits up to 5 s and gets
  the 503 at once (the cooldown counts from the last successful fetch); after 300 s every token waits
  and gets the 503. Add one test: the stub raises on `get_signing_key_from_jwt` only for an unknown
  key id → 503, while a known key id still passes (if the coder can stub that cheaply; else state it
  as a fact from the source).
- (b) `cooldown_duration` larger, to shield the workers. It also delays a real key rotation; rejected.

### BR1-04 — minor — `docs/Keycloak.md` is due, not "none due"

**Problem.** § 3 *Docs* says `docs/Keycloak.md`: "none due … the coder adds one line under the token
section if one exists". The section exists: `docs/Keycloak.md:28-42`, "What the token must carry",
ending "The backend checks the token's signature against the realm's keys, its expiry, and that `azp`
… is `vel-yantra-master`. It does not check `aud`." After this step that paragraph is wrong: the
backend also checks `iss`, requires `iat`, requires `typ` `Bearer`, allows 30 s of clock difference,
and answers 503 when the key list cannot be fetched within 5 s.

**Why it matters.** CLAUDE.md § Docs to keep current names `docs/Keycloak.md` for a change of "token
claims"; this step changes which claims a token must carry. IT admin reads this file when a login
fails.

**Options.**
- (a) **Recommended:** list `docs/Keycloak.md:40-42` in § 3 as due, with the new paragraph's content
  (the checks above and the two new access-log codes `wrong_type`, `login_server_down`); the coder
  reports it in `## Docs updated`.
- (b) Leave it; the R01 roadmap already records the change. The doc then contradicts the code.

### BR1-05 — minor — Do important check 1 now, and give the row its account and network

**Problem.** § 5 puts check 1 (a real token's `typ`, `iss`, `iat`, `exp`) "before the release". § 1.3
and design decision 5 rest on it: a different `iss` (Keycloak's frontend URL setting, a trailing
slash) would refuse every user, and the brief itself says "a mismatch would refuse every user". The
check needs only a browser signed in to production and two minutes. The row also lacks the account
and the network (settings: *Device checks*: account, network, where).

**Why it matters.** Found after coding, a mismatch means a design change (decision 5) and a round
through gate A, not a release stop. Found now, it costs nothing.

**Options.**
- (a) **Recommended:** ask KLA to run check 1 at gate A (approval), and record the result in § 6
  assumption 1 as a fact. Keep the row in `device-checks.md` as the record. Give the row: account
  "any Yantra user (your own)", network "any (plant Wi-Fi or mobile data)", where "production or the
  TEST machine". Note that the token is a live sign-in: paste it only into the local command, and it
  expires in minutes.
- (b) Keep "before the release" as written. The risk stays open through coding and code review.

## Nits

- **BR1-06** (nit) § 2: RFC 8725 § 3.11 "explicit typing" means the JOSE **header** `typ` (`at+jwt`,
  RFC 9068). Keycloak's header `typ` is `JWT` for every token kind, so the payload `typ` claim is what
  tells them apart; say that the step follows § 3.11's intent with Keycloak's claim. Also state the
  departure from § 3.9 "Use and Validate Audience": `aud` is not checked, `azp` stands in (Keycloak
  sets `aud=account`; the base pattern), as the standards rule asks for departures.
- **BR1-07** (nit) § 1.1: add the accepted limit of relying on PyJWT's refetch: within 30 s after a
  junk-triggered refetch, a token signed by a freshly rotated key is refused (401) until the cooldown
  passes. Keycloak keeps the old key valid during a rotation, so it costs a few 401s once, by hand.
- **BR1-08** (nit) § 1.2, docstring: `validate_keycloak_token` now **raises** `LoginServerUnavailable`
  on a fetch failure instead of returning `None`; the docstring says so, not only "gains the code".
- **BR1-09** (nit) § 1.2: the warning names the JWKS URL itself (`jwks_url`): PyJWT's message is
  'Fail to fetch data from the url, err: "…"' with the urllib error, not the URL.
- **BR1-10** (nit) § 1.2: say what IT admin sees in Settings › Access log during an outage: the
  `auth_failed` badge "Login failed" (`AccessLog.vue:18`) with `login_server_down` as the detail, one
  row per client address per day (`who` is None without a user). Acceptable; it should be a stated
  choice.
- **BR1-11** (nit) § 5 *Timeout*: the autouse `stub_jwks` fixture replaces `_get_jwk_client` for every
  test in `test_auth.py`; the test keeps a reference to the real function (module level, before the
  fixtures run) or uses `monkeypatch.undo()`, and pops its URL from `_jwk_clients` so the test does
  not depend on order.
- **BR1-12** (nit) § 5 *Always-check tests*: the Basic browser run proves nothing about tokens (the
  e2e stack signs in through `X-Test-Role`, which `require_auth` answers before the token path). Say
  it checks only that the app still starts and serves, or drop it.
- **BR1-13** (nit) § 1.3: a refused `typ` logs the claim's value, never the token; say so, as the
  other warnings do.
- **BR1-14** (nit) Plan.MD § 1 *Security hardening* row names R01's other items but not the token
  checks; the orchestrator adds one clause at gate A (issuer, `typ`, 5 s timeout, 503 on an outage).

## Checked and found consistent

- **PyJWT refetch** (`backend/.venv/.../jwt/jwks_client.py`, `get_signing_key`): an unknown key id
  forces one refresh when `time.monotonic() - _last_successful_fetch >= cooldown_duration` (30 s);
  every successful fetch starts the cooldown. The retry can go.
- **Timeout:** `PyJWKClient(uri, timeout=30)` exists; `__init__` makes no network call, so the
  attribute test works. `lifespan` default 300.
- **Exceptions:** `PyJWKClientConnectionError(PyJWKClientError(PyJWTError))` (`exceptions.py:96,100`);
  raised from `fetch_data` for `URLError`, `TimeoutError`, `HTTPException`. An unknown key id raises
  `PyJWKClientError` → still `invalid_token`. A malformed token (`Bearer not-a-jwt`,
  `test_access_log_api.py:81,149`) fails in `decode_complete` before any fetch, so those tests are
  unaffected.
- **Check scripts** re-run (`uv run python ../scratch/s059_check2.py`): `require` in `options` refuses
  a missing `exp`, `iat`, `iss`; `require=` as a keyword is ignored with `RemovedInPyjwt3Warning`;
  `exp -20` passes, `-40` fails; the forged HS256 token raises `InvalidAlgorithmError`; an unreachable
  JWKS URL raises `PyJWKClientConnectionError` with and without a key id.
- **503 path:** `require_auth`'s `handler()` returns the response from `before_request`, so the route
  is skipped and the after-request hooks run; `classify_outcome` (`network_core.py:88-89`) lets the
  marked `auth_failed` / `login_server_down` win; `OUTCOMES` and the ENUM (`local_db.py:497`) need no
  change; `detail` is `VARCHAR(255)`. `LoginServerUnavailable` has one caller (`require_auth`);
  `validate_keycloak_token` and `_decode` have no other users (facts file).
- **Frontend today:** `api.js:22-24` makes `err.message` the body's `error`, and `auth.js:84-86` shows
  "Could not load your profile: " + the message for a non-401, as § 1.2 says. R01.3 refines it.
- **Issuer:** the base doc already says "Issuer validation still uses the public `realm_url`"
  (`SMTW-WebApp-Base.md:126`); decision 5 follows it. The internal URL is for the fetch only.
- **Existing tests:** `test_expired_token_is_rejected` (`exp_in=-60`) still fails with a 30 s leeway;
  `test_bad_signature_is_rejected` and the `invalid_token` row of `test_failure_codes` hold (known key,
  bad signature → `InvalidSignatureError`); `TestDatabaseDown` and `TestLoginEmail` need only the
  `_token` defaults. `test_rbac.py`, `_TABLES`, `db_down` and the migration tests are untouched.
- **Layering:** the checks are PyJWT options and one claim test in the auth shell; no business rule,
  no new module or flag. The `_client_lock` RLock in `get_signing_key` does not matter with sync
  workers.
- **Scope B text:** the 503 message says what happened, why and what to do, no code or field name.
- **Track:** full is right (auth code).

## Feedback

- idea: the facts file reports `jwt/jwks_client.py` as "no such file"; a cited path with no repo
  folder and a library name could be marked "outside the repo (library)" instead (`scratch/brief-facts-S059.md:10`).
- hindrance: the Bash hook blocked a read-only command because it contained `ls backend/secrets_app.py`
  (an existence check only); one re-run without it.
- waste: `uv run` in `backend/` prints a `VIRTUAL_ENV` mismatch warning on every run (2 runs); noise
  only.
