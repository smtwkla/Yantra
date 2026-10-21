```
Step: S024 — Browser tests (Playwright)
Doc: brief-review r3
Author: Brief reviewer (Fable)
Date: 21-10-2026
```

Reviewed against: 6c58b7a + uncommitted S018 (the working tree also carries uncommitted edits to `docs/steps/README.md`, `.claude/skills/step/SKILL.md`, the S017 docs and `tooling/common/material_icon.py`, none of them files S024 touches)

**Verdict: no `blocker` or `major` finding open.** Every round-2 finding
marked *Accepted* is in the brief text (table below). BR2-01's route holds
against the audit skill as it stands; BR2-02's factory default is in § 3 step
4 and matches the code it leans on. The two revisions left no contradiction
of substance: no `SMTW.TEST`, "four columns" or `dialogs.spec.js` outside the
Review log. Two minors (one S015 check mis-sorted onto the device list; the
dev server has no login, so the Account column needs a rule for its rows) and
two nits. This is the last round before gate A.

## Round 2 — Accepted findings verified in the text

| Finding | Where it now stands in the brief | Verified |
|---|---|---|
| BR2-01 smtw-review is synced | § 3 "Workflow docs": "S024 does **not** edit Yantra's copy"; the `CLAUDE.md` bullet names the phase (`/smtw-review`, Phase 3 item 8 *Tests*) and "in the background"; the generic lines for smtw-common go into the impl report ready to paste; § 7.6 "from `/smtw-review` as part of its audit"; § 9 Q1 | yes — and sound, see below |
| BR2-02 missing `X-Test-User` | § 3 step 4: username defaulted to `e2e_<role>` when the header is missing, "as `conftest.py`'s factory does"; the display name from `seed_e2e.PEOPLE` by login, else the username | yes |
| BR2-03 a person without a login | § 5.2 row `operator_nologin` — Ramesh, operator at SMTW `MCC2`, no login; the paragraph below the table says what he is for | yes |
| BR2-04 print emulation does not paginate | § 1.4 "DOM assertions, since print emulation does not paginate"; § 8 Automated "15 labels per sheet element, two sheets for 16"; Real device: S015's paper checks | yes (see BR3-01 on which S015 checks) |
| BR2-05 `SMTW.TEST` | § 1.6, § 7.10, § 9 Q6: "a machine named TEST in `SMTW.MCC2`", its code written into the rows once created, tickets closed as *Not a fault*; `SMTW.TEST` survives only in the Review log line | yes |
| BR2-06 Done column | § 1.6: five columns, **Done** "who and when, written by the planner" | yes |
| BR2-07 "its body scrolls" | § 1.4: Save and Cancel inside the viewport, dialog no taller than the viewport | yes |
| BR2-08 sys.path, charset, install every run, generic README | § 3 launcher step 1 "put `backend/` on `sys.path` … before `import config`"; step 3 "charset and collation of `init-test-db.sql`"; bat step 3 "every time (a no-op …)"; README "the named person, today IT Admin" | yes |
| BR2-09 the IT-admin-on-mobile-data row | not on § 8's device list; § 1.6's Account rule stands | yes |

**BR2-01's route, checked against the audit skill.** `sync_common.py` still
lists `(".claude/skills", ".claude/skills")` under `DIRS` and overwrites
every file it finds in smtw-common, so leaving `smtw-review/SKILL.md` alone
is right. The `CLAUDE.md` route works with the skill as synced today:

- Phase 1 item 1 reads `.claude/CLAUDE.md` first ("they define the intended
  behaviour"), so the bullet is in the audit's context before any check runs;
- Phase 3 item 8 is *Tests* ("each module has tests covering the happy path
  and key failure modes"), the right place for "run `tooling/run-e2e-tests.bat`
  and report its result";
- the skill's `allowed-tools` includes `Bash`, so it can run the bat, and
  "in the background" is the right instruction for a run of minutes;
- `.claude/agents/` is not in `DIRS`, so the three agent edits of § 3 are safe
  from the sync; `step/` survives because `sync_dir` writes smtw-common's
  files over local ones and never deletes a local extra (r2).

The generic lines for smtw-common ("if the repo has a browser-test command
named in its `CLAUDE.md`, run it under *Tests* and report the result") are
worded so a repo without one is unaffected. Nothing to add.

**BR2-02, checked against the code.** `api_common.actor()` returns
`g.user["username"]`; `masters.py` writes it to `created_by`; `conftest.py`'s
`_test_user_factory` is `harness_user(role_name, username or
f"test_{role_name}")`. The brief's `e2e_<role>` default mirrors it, so the
seed's `X-Test-Role: admin` requests write `created_by = "e2e_admin"`.
`seed_e2e.py` is in the launcher's own folder, so `import seed_e2e` needs no
extra `sys.path` entry (a script's directory is `sys.path[0]`).

## Findings

### BR3-01 — minor — S015's third check is a screen check, put on the device list

**Problem.** § 8 Real device: "S015's three paper checks (print at 100 %, the
header repeats on page 2, parts indented)". S015's third important check
(S015 § 8) is "With **Include parts**, a press shows its component-units and
components indented under it, and the count line reads 'n equipment, m
parts'" — what the screen shows, not what the paper shows. A DOM assertion
covers it exactly (the indented rows under the press, the count line's text),
and BR2-04 said so ("the third can be asserted in the DOM"). The brief's own
new rule for brief reviewers (§ 3, `brief-reviewer.md`) makes "a check put on
the device list that a browser could do" a `minor`, so the rule is applied to
the brief that introduces it.

**Why it matters.** Every row on the device list costs the IT admin a trip;
one that a test already proves is a trip for nothing, and it sets the pattern
for later steps.

**Fix.** § 1.4 and § 8: S015's **two** paper checks on the device list (print
at 100 % with no column cut off and the footer on the sheet; the header
repeating on page 2 and the next unit on a new page); the parts indentation
and count line under Automated, in `asset-list.spec.js`.

### BR3-02 — minor — Device rows on the dev server: there is no login to name

**Problem.** § 1.6's **Account** column says which login each row needs, with
the example "a test login with the Technician role at SMTW (ask KLA)", and
**Where** offers "the dev server at `http://<dev PC>:5176`". The dev server
runs with `DEV_AUTH_BYPASS=1` (CLAUDE.md "Backend" run config): there is no
login screen, every request is the stub user (`DEV_STUB_ROLE`, admin by
default), and the network gate is skipped. So on the dev server the Account
column cannot be met as written — the IT admin would look for a login that
does not exist, or ask for a test login that cannot be used there. The brief
does not say this, and the coder writing the rows would have to work it out.

In practice no dev-server row needs a particular role: the rows that go there
(S014 print, measure and grease; S015's paper checks; S017's camera photo;
S018's iPhone keyboard over the close dialog) are about paper, a camera or a
keyboard, and the stub admin can open every one of those screens. The rows
that need a real account per role are the production ones (the Keycloak
login; the scan on mobile data, which must not be `it_admin`).

**Fix.** In § 1.6 under Account: "`none` for rows on the dev server — it has
no login (the dev auth bypass); you are the dev user and can open every
screen" and keep the test-login example for production rows. Under Where,
one line: a phone reaches the dev server only on the plant Wi-Fi (the dev PC
is on the LAN), so every mobile-data row is a production row — which is what
§ 1.6 already implies but does not say.

### BR3-03 — nit — Leftovers of the two revisions

- Header `Date`: "revised 21-10-2026 after brief-review r1" — now after r2.
- Review log, *User answers*: "Q1 … → § 3 (CLAUDE.md, smtw-review skill)".
  After BR2-01 the skill is not a place the brief edits; the user reads the
  log at gate A, so say "(CLAUDE.md bullet; smtw-common lines in the impl
  report)".
- § 8 first bullet: "The report records the first run's duration (open
  question 1)" — Q1 is decided; the duration informs **Q2** (run time).
- § 3 launcher step 2 reads "`import config`; check the guard (§ 5.1); set
  `config.DB_CONFIG["database"] = "vel_yantra_e2e"`". The guard of § 5.1
  checks that the name ends in `_e2e`; checked before the launcher sets it,
  it sees `secrets_app.DB_NAME` (`vel_yantra_master`) and refuses every time.
  Say the guard takes the host from `config.DB_CONFIG` and the name the
  launcher is about to set (`check_e2e_target(host, "vel_yantra_e2e")`), so
  its pytest test (§ 8) tests exactly that function.

### BR3-04 — nit — `seedIds(request)` in a `beforeAll`

§ 3 `support/people.js`: "`seedIds(request)` — looks up ids … (`request.newContext`
with the same `extraHTTPHeaders`) in a `beforeAll`". Playwright's built-in
`request` fixture is **test-scoped** (one `APIRequestContext` per test) and
`beforeAll` hooks receive worker-scoped fixtures only, so `request` is not
there. The worker-scoped `playwright` fixture is: `test.beforeAll(async ({
playwright }) => { const api = await playwright.request.newContext({
extraHTTPHeaders: ADMIN }); … })`. Name it so the coder does not hit the
fixture error first.

## Checked and found consistent

- **No leftovers of the kind the orchestrator asked about**: `SMTW.TEST` and
  `dialogs.spec.js` appear only in the Review log's history lines; "four
  columns" is gone and § 1.6 lists five; "its body scrolls", "2 pages in print
  emulation", "first use" for the browser install and "this repo's own (not
  synced)" are gone from the text.
- **Round 1's accepted findings** still stand as r2 verified them; the r2
  revision touched none of their anchors except § 1.4 (BR2-04/07 wording)
  and § 3 (BR2-01/02/08), which read consistently with § 5, § 7 and § 8.
- **`harness_user` move**: `conftest.py` already imports `from
  tests.access_helpers import site_rows`, so `from tests.harness import
  harness_user` follows the existing path; `.dockerignore` line 11 excludes
  `backend/tests/`.
- **`DEV_STUB_ROLE = "nobody"`**, the launcher order, `use_reloader=False`,
  the bat's compose call, the seed people against S011/S018's roles, the
  Vitest exclude, two `webServer` entries before `globalSetup`, the two
  re-introducible bugs — unchanged from r2 and still true of the code.
- **§ 1.6 ↔ § 9 Q4**: "the named person, today IT Admin" in the README rule
  and the name in the rows and ticks — the same decision stated at two
  levels, not a contradiction.
- **Standards** (§ 2): ISO 9001 § 8.3.4 (design verification with records —
  a named, repeatable test is the record), ISO 27001:2022 A.8.29 / A.8.31
  (test environments separated from dev and production), Cohn's test pyramid,
  ISO 9241-11. Unchanged and right; no maintenance standard applies to the
  step itself.
- **Manual checks** (§ 8): the two important ones (first green run on the
  user's machine; the IT admin reads `device-checks.md` and says whether he
  could follow it) are the right two; nothing plain is marked important.
- **Track full** still right: new dev dependency, auth-adjacent harness, a new
  database, a workflow rule change.
