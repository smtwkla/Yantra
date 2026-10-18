```
Step: S022 — Software inventory and vulnerability check
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 18-10-2026
```

# S022 — Brief review, round 1 (light track: the only round)

**Verdict: one `major` finding is open (BR1-01); no `blocker`.** The shape is
right — CycloneDX from the lockfiles, OSV from the standard library, exit codes a
release can gate on — and both export commands work on this repo as the brief
says. But the files the tools write are not reproducible (a fresh UUID and
timestamp on every run), which makes Rule 1 false and would dirty the tree
before every release. Six `minor` findings record the OSV / registry / test
details the coder would otherwise decide alone.

**Track.** Every light criterion holds: no migration or data change, no auth or
security-sensitive *app* code (this is a tool that reads public package names),
no transactions or locking, no new dependency (stdlib, `uv`, npm), about ten
files. Per `README.md` § Tracks a `major` finding switches the step to full
unless the user decides otherwise; the fix for BR1-01 is a few lines in the
brief and in `audit.py`, so that is the user's call.

Reviewed against: the brief; `docs/Plan.MD` (§ 1 Repos, Hosting);
`CLAUDE-COMMON.md` (Dependency health, Pure core, Wrapper scripts, Release
workflow); `CLAUDE.md`; `SMTW-WebApp-Base.md` § Shared Tooling Sync, § Testing
Pattern, § Versioning & Release; the repo: `pyproject.toml` + `uv.lock` (root),
`backend/pyproject.toml` + `backend/uv.lock`, `frontend/package.json`,
`.gitignore`, `tooling/*.bat`, `tooling/deploy.py`, `tooling/common/*`
(`sync_common.py` FILES list), `tooling/build/Dockerfile.*`,
`.idea/runConfigurations/*.xml`. Ran, into the scratchpad only:
`uv export --format cyclonedx1.5 --frozen` (uv 0.10.10) in `backend/` and at
the root; `npx npm@11 sbom --sbom-format cyclonedx --package-lock-only` in
`frontend/` (npm 11.21.0 fetched by npx; local npm is 10.9.2); OSV
`POST /v1/querybatch` and `GET /v1/vulns/<id>` for PyPI and npm records; PyPI
JSON and the npm registry for `flask-cors`, `@vitejs/plugin-vue`, `vue`.

---

## Findings

### BR1-01 — `major` — The generated SBOMs change on every run, so "a changed `sbom/` means a dependency changed" is false

**Problem.** Both tools stamp each file with a random `serialNumber`
(`urn:uuid:…`) and `metadata.timestamp` (now). Verified on this repo: two runs
of `uv export` seconds apart differ in both fields; npm does the same. Rule 1
("a changed `sbom/` in `git status` means a dependency changed and is committed
with that change") and Decision 1 ("committed in `sbom/`") assume the output is
a pure function of the lockfile. It is not.

**Why it matters.** Every "Dependency audit" run dirties three tracked files
with no real change. `release.py` step 1 aborts on a dirty tree
(CLAUDE-COMMON § Release workflow), so running the check before a release —
the whole point of the exit codes — would block the release until the noise is
committed or reverted. And `git log sbom/` stops meaning anything.

**Options.**
1. **Normalise after export.** `audit.py` loads each generated file, deletes
   `serialNumber` and `metadata.timestamp` (both optional in CycloneDX 1.5),
   and rewrites it with `json.dump(..., indent=2, sort_keys=False)` and a
   trailing newline. The output is then a function of the lockfile and the
   tool version only; the git commit date stands in for the timestamp. The
   `metadata.tools[].version` field still changes when uv or npm is upgraded —
   that is a real change and should be committed.
2. **Regenerate only when the lockfile changed**, by storing the lockfile's
   SHA-256 in a `properties` entry and comparing. More logic, and a stale
   `sbom/` after a tool upgrade goes unnoticed.
3. **Accept the noise** and tell the user to `git checkout sbom/` when nothing
   changed. Rejected: breaks the release gate and the rule.

**Recommendation.** Option 1, stated in § Rules ("the exporter's serial number
and timestamp are removed so the file depends only on the lockfile") and in
§ Where for `audit.py`. A pure helper `normalise_sbom(dict) -> dict` in
`audit_core.py` is testable. For the user's learning: the NTIA "minimum
elements" for an SBOM list a timestamp; here the commit that carries the file
supplies it, which is the right trade for a file kept in git.

---

### BR1-02 — `minor` — uv's CycloneDX output does not mark dev dependencies; Rule 2 cannot be met for the backend as written

**Problem.** Rule 2 says dev dependencies "are included and marked". npm does
mark them (`properties: [{"name": "cdx:npm:package:development", "value":
"true"}]`, verified on `vite`, `vitest`, `jsdom`, `@vitejs/plugin-vue` and
their closure). uv does not: `pytest` and its five dependencies appear as plain
components, and `pytest` is listed as a direct dependency of `yantra-backend`
next to `flask`. The only properties uv writes are `uv:package:marker` and
`uv:package:is_project_root`.

**Why it matters.** Without a dev marking the report cannot say "this finding
is in a build-machine tool only". That distinction is real here:
`Dockerfile.backend` installs with `uv sync --frozen --no-dev` and the
frontend image ships only the built bundle, so `pytest`, `vite`, `vitest`,
`jsdom` never reach production. Whether a dev-only `high` should gate a release
is a decision the brief should take (it currently gates everything; that is
defensible — the build runs on the developer's machine with the same supply
chain — but say so).

**Options.**
1. **Second export, set difference.** `audit.py` also runs
   `uv export --format cyclonedx1.5 --frozen --no-dev` to a temporary path;
   dev-only = purls in the full export that are absent from the `--no-dev`
   export. Exact (handles `colorama`, which `qrcode` and `pytest` both need and
   which is therefore *not* dev-only). Marked in the report, not in the
   committed file.
2. Read `[dependency-groups]` from `backend/pyproject.toml` with `tomllib`
   (stdlib) and walk the SBOM's `dependencies` graph in `audit_core` to find
   what is reachable only from dev roots. Pure and testable, but it re-implements
   what uv already knows.
3. Add a property to uv's file during normalisation (BR1-01) so the committed
   SBOM carries the mark, as npm's does. Tempting for `smtw_erp_devops` later,
   but it is our invention, not a CycloneDX convention.

**Recommendation.** Option 1 for the report; keep the committed files as the
tools write them (minus BR1-01's two fields). State in § Rules that dev-only
findings still set the exit code, or say they don't.

---

### BR1-03 — `minor` — OSV record handling: five rules the coder would otherwise decide alone

Checked against the live API; all of these are facts of the data, not guesses.

1. **An empty result is `{}`.** `querybatch` returns one object per query, in
   order; a package with no advisories gives `{}` — no `vulns` key at all. Use
   `result.get("vulns", [])`.
2. **Duplicates across databases.** For `jinja2 3.1.4` OSV returns six ids:
   `GHSA-q2x7-8rv6-6q7h`, `GHSA-gmj6-…`, `GHSA-cpwx-…` *and* `PYSEC-2026-1471`,
   `-1472`, `-1475` — the same three CVEs twice, because PyPI advisories exist in
   both the GitHub and the PyPA databases and each lists the other as an alias.
   PYSEC records carry **no** severity (`severity` absent, `database_specific`
   empty), so a naive report shows each CVE once as `moderate` and once as
   `unknown`. Group records whose alias sets (ids + `aliases`) overlap; show
   the CVE, the GHSA id, and the highest known severity in the group.
3. **Severity** is `database_specific.severity` on GHSA records (`CRITICAL`,
   `HIGH`, `MODERATE`, `LOW`), as the brief says. `severity[]` holds only CVSS
   v3/v4 **vectors**, not scores — the brief is right not to compute them.
4. **Fixed version** is `affected[].ranges[].events[].fixed` (range type
   `ECOSYSTEM` for PyPI, `SEMVER` for npm). A record can have several
   `affected` entries (other packages, or several branches: "1.x fixed in
   1.2.3, 2.x fixed in 2.0.1"). Choosing *the* fix for the installed version
   needs PEP 440 / semver comparison, which the stdlib does not have
   (`packaging` is not stdlib). Rule: take the `affected` entries whose
   `package.ecosystem` and `package.name` match (OSV already matched the
   installed version to the range), list **all** their `fixed` versions, no
   version arithmetic; "none" when a record has no `fixed` event.
5. **Withdrawn and paging.** Skip records with a `withdrawn` field. OSV
   paginates a *query* only beyond 1000 matches (`next_page_token` inside that
   result) and caps a batch at 1000 queries; neither bites here (179 purls,
   none with hundreds of advisories), but the code must not truncate silently:
   if a `next_page_token` appears, follow it or exit 2.

Also verified, no change needed: querying by purl works for both ecosystems,
including npm scoped names in either form (`pkg:npm/%40babel/traverse@7.22.0`
and `pkg:npm/@babel/traverse@7.22.0` both return `GHSA-67hx-6x53-jw92`) and
PyPI names in either case (`Flask-Cors` and `flask-cors` give the same
records). `audit_core` can hand the SBOM's purls to OSV unchanged.

**Recommendation.** Add these five as bullets under § Rules (or a short
"OSV" sub-list); each is one unit test in `test_audit_core.py`.

---

### BR1-04 — `minor` — `tooling/run-tests.bat` does not run `tooling/deps/tests`, and the root environment has no pytest

**Problem.** § Where says the test is "run by `tooling/run-tests.bat`". That
script calls `run-backend-tests.bat` (`cd backend && uv run pytest`) and
`run-frontend-tests.bat` (`npm test`); pytest's rootdir is `backend/`, so a
test under `tooling/deps/tests/` is never collected. The root project
(`pyproject.toml`: `yantra`, dependency `python-dotenv` only) has no pytest,
and `audit_core.py` is not importable from a test without a path tweak.

**Why it matters.** `release.py` runs `run-tests.bat` as `TEST_CMD`; a test
that is not wired in is not a gate. The coder has to pick an environment,
a rootdir and an import path — three small decisions, none in the brief.

**Options.**
1. **Root project owns the tooling tests.** Add `pytest` to a `dev`
   dependency group in the root `pyproject.toml` (the root `uv.lock` changes —
   that is the lockfile `sbom/tooling.cdx.json` covers, so the SBOM grows by
   pytest and its five dependencies, consistent with the backend), and
   `[tool.pytest.ini_options] testpaths = ["tooling/deps/tests"]
   pythonpath = ["tooling/deps"]`. `run-tests.bat` gets a third line:
   `cd /d "%~dp0.." && uv run pytest || exit /b 1`. No `sys.path` hacks.
2. `uv run --with pytest pytest tooling/deps/tests` from the root: no lockfile
   change, but an ephemeral environment (network on a cold cache) and the
   import path still needs solving.
3. Run them from the backend environment (`cd backend && uv run pytest
   ../tooling/deps/tests`). Mixes two projects' environments; rejected.

**Recommendation.** Option 1; list `pyproject.toml`, `uv.lock` and
`run-tests.bat` under § Where. Answer Open question 1 at the same time: the
audit itself stays out of `run-tests.bat` (agreed — a test run must not need
OSV), only its unit tests go in.

---

### BR1-05 — `minor` — Exit codes: "not checked" is wider than a network failure, and `unknown` severity falls through to 0

**Problem.** § Rules gives exit 2 for "OSV or a registry unreachable" only. The
run can also fail to *produce* the SBOMs: `uv` or `npx` not on PATH, a
lockfile missing, `uv export` failing on a stale lock, or — relevant to the
second manual check — `npx npm@11` needing the registry to resolve `npm@11`
when its cache is cold, so the offline run would fail at SBOM generation
rather than at OSV. Separately, § What says exit 1 "when any finding is
critical or high, else 0": a record whose severity is `unknown` (no GHSA in
the alias group, see BR1-03.2) exits 0, which is the "no findings means not
checked" trap the brief itself warns against.

**Options.**
1. Exit **2** for any step that did not complete (export, OSV, registry), with
   the step named on the console; exit **1** for `critical`, `high` **and**
   `unknown`; 0 otherwise. `unknown` will be rare after alias grouping (GHSA
   rates nearly every PyPI and npm advisory), and when it happens a person
   should look.
2. As 1, but `unknown` does not gate — listed prominently in the report.

**Recommendation.** Option 1 (fail-closed, in line with the brief's own
principle); write the three codes with their exact conditions in § Rules. Note
in the second manual check that generation may be the step that fails offline;
the expected result (exit 2, a message naming the step) is the same.

---

### BR1-06 — `minor` — Registry lookups for the 12-month rule are unspecified

**Problem.** "The date of its latest release (PyPI, npm registry)" leaves the
endpoints and the meaning of "latest" to the coder. Checked:

- **PyPI**: `GET https://pypi.org/pypi/<name>/json`. `info.version` is the
  latest **non-pre-release**; its upload date is `urls[0].upload_time_iso_8601`
  (all files of that release are within seconds). The maximum over
  `releases[*][*].upload_time_iso_8601` is different — it includes alphas and
  betas, which would hide a library whose last stable release is years old.
  The purl's normalised name (`flask-cors`) is accepted. PyPI asks for a
  `User-Agent` naming the tool.
- **npm**: `GET https://registry.npmjs.org/<name>`, scoped names encoded
  `%40scope%2Fname`; date = `time[dist-tags.latest]`. The abbreviated document
  (`Accept: application/vnd.npm.install-v1+json`) has **no** `time` field, so
  the full document is needed (`vue`'s is a few MB; nine direct packages,
  fine).
- The pure core must receive **today** as a parameter (CLAUDE-COMMON "Pure
  core": no `datetime.now()` in `audit_core`); the 12-month rule is then one
  testable function.
- Timeouts (`urllib` has none by default) and a sensible failure path per
  package: one unreachable registry record → exit 2 (BR1-05), not a traceback.

**Recommendation.** Put the two endpoints, "latest = latest non-pre-release",
`today` as an input and a timeout (say 20 s) in § Rules.

---

### BR1-07 — `minor` — `uv export` flags and the experimental status of the CycloneDX format

**Problem.** Without `--frozen`, `uv export` may **rewrite `uv.lock`** when
`pyproject.toml` has drifted — a side effect an audit must not have — and may
touch the network. The format itself prints `warning: uv export
--format=cyclonedx1.5 is experimental and may change without warning` (pass
`--preview-features sbom-export` to silence it). Both tools emit **spec 1.5**
today; the brief's § Standards cites ECMA-424 "for 1.6", which is correct but
the files are 1.5.

**Recommendation.** In § What, write the exact commands:
`uv export --format cyclonedx1.5 --frozen --preview-features sbom-export -o …`
and `npx npm@11 sbom --sbom-format cyclonedx --package-lock-only > …`. In
`audit_core`, assert `bomFormat == "CycloneDX"` and `specVersion == "1.5"`
and exit 2 otherwise, so a silent format change is caught rather than parsed
wrongly. Say in § Standards that the files are CycloneDX 1.5 (1.6 is the
ECMA-424 edition; 1.5 is what uv and npm write).

---

### BR1-08 — `nit` — The run config is not a committed file; `.bat` conventions

`.idea/` is gitignored (`.gitignore` line 2), so "the run config" under
§ Where is a local file like the existing `Tests.xml`, not part of the commit.
Say "local run config, `ShConfigurationType`, `cmd.exe /c
$PROJECT_DIR$/tooling/run-deps-audit.bat`, like Tests". The `.bat` follows
the siblings: `@echo off`, `cd /d "%~dp0.."`, then `uv run python
tooling/deps/audit.py %*` and `exit /b %ERRORLEVEL%` so PyCharm and
`release.py` see the code. `audit.py` creates `scratch/` if absent (the folder
is gitignored and may not exist on a fresh clone).

---

### BR1-09 — `nit` — Two things the root lockfile does not cover; say so

The root `uv.lock` covers the `yantra` project: `python-dotenv` only, used by
`tooling/deploy.py`. `tooling/common/release.py` and `sync_common.py` declare
their own dependency (`python-dotenv`, PEP 723 inline metadata) and run in an
isolated environment, so they are in **no** lockfile and no SBOM. Trivial
here (same library, same version range), but the brief should name it as an
accepted gap next to the container images, so `smtw_erp_devops` does not
assume `sbom/` is everything a repo runs. `uv export --script <file>` could
cover them later if wanted.

---

## Light-track check

| Criterion | Holds? |
|---|---|
| No migration, no change to existing data | Yes — no app code at all |
| No auth, RBAC or security-sensitive code | Yes — reads public names and versions; writes under `sbom/` and `scratch/` |
| No transactions, locking, concurrency | Yes |
| Existing pattern, no new dependency, no new endpoint | Yes — stdlib + `uv` + npm; pure core / thin shell as the tooling scripts already do |
| About 10 files | Yes — `audit_core.py`, `audit.py`, test, `.bat`, 3 SBOMs, `CLAUDE.md`, plus `run-tests.bat`, root `pyproject.toml` and `uv.lock` if BR1-04 option 1 is taken |

## Checked and found consistent

- `uv export --format cyclonedx1.5` works with uv 0.10.10 on both lockfiles:
  backend → 24 components, root → 1 (`python-dotenv`), every component has a
  purl, `dependencies[]` present.
- `npx npm@11 sbom --sbom-format cyclonedx --package-lock-only` works in
  `frontend/` without `node_modules` being consulted: exit 0, 154 components
  (including the per-platform `@esbuild/*` and `@rollup/*` binaries the lock
  carries), every component has a purl, hashes and dev marks present.
- **Direct dependencies are readable from both outputs** the same way: the
  `dependencies[]` entry whose `ref` equals `metadata.component["bom-ref"]`
  lists them — 10 for the backend (the 9 runtime libraries plus `pytest`),
  9 for the frontend (5 runtime, 4 dev). uv's `bom-ref` is `name-N@version`,
  npm's is `name@version`; resolve through `components[].bom-ref`, not the
  purl.
- The two `uv.lock` files: `backend/uv.lock` is the application
  (`yantra-backend`, what `Dockerfile.backend` installs with `--no-dev`);
  the root `uv.lock` is the tooling project (`deploy.py`). Naming them
  `backend.cdx.json` and `tooling.cdx.json` is right.
- `tooling/common/` is synced from `smtw-common` (`sync_common.py` FILES:
  `bump_ver.py`, `release.py`, `ccssh.py`, `ccloki.py`); the brief changes
  nothing there and puts the new code in `tooling/deps/`, which is not in the
  sync inventory. Correct. `CLAUDE.md` is repo-specific (not synced), so the
  doc line goes in the right file.
- `scratch/` is gitignored; `sbom/` is not and does not exist yet.
- Standards: ISO 27001:2022 A.8.8 (management of technical vulnerabilities —
  know what you run, learn of weaknesses, act in a set time) and A.5.9
  (inventory of information and associated assets) are the right controls and
  correctly described; CycloneDX (OWASP, ECMA-424), purl (ECMA-427) and SPDX
  (ISO/IEC 5962) are correctly named. The maintenance standards (ISO 14224,
  EN 13306, SMRP) do not apply to a tooling step and are rightly absent.
- Severity source: `database_specific.severity` on GHSA records, `unknown`
  otherwise, no CVSS computation — matches what OSV serves (BR1-03.3).
- Out of scope is right: images, the cross-repo report, alerts, schedule,
  runtime end-of-life, and the `release.py` step (synced file).
- Manual checks: both are correctly marked important (the offline run is the
  one a person must do); none is over-marked.
- Open question 1: agree with "on its own for now" — see BR1-04.
