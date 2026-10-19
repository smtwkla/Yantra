```
Step: S022 — Software inventory and vulnerability check
Doc: brief
Author: Planner (Opus)
Date: 18-10-2026 (revised 18-10-2026 after brief-reviews r1 and r2, and for portability, U1)
Track: full (switched from light after BR1-01, a major finding)
Baseline: 167e178 (stale brief check s1, 18-10-2026: no findings)
Status: In code review (approved 18-10-2026 by KLA)
```

# S022 — Software inventory and vulnerability check

The user wants every repo's libraries listed in a standard file, a warning when a
CVE affects one of them, and later a check across all repos. Decisions
(18-10-2026):
1. **Build it in Yantra first**; the cross-repo report and the release-script
   step follow once it works here.
2. **Not part of the test run**; the user schedules runs later (Open question 1).
3. **Portable (U1):** the same files must work in any SMTW repo unchanged, and
   later move to `smtw-common` (synced into `tooling/common/`). The cross-repo
   report will be a separate **scanner bot in aibots** that reads every app's
   SBOMs (queued). A second SBOM per container image, made at build time, covers
   base images and OS packages (queued).

**Track: full** since review r1 (BR1-01). Tooling only: no app code, migration,
auth or data change; no new dependency (Python standard library, `uv` and npm,
already used; the tests run with `pytest` fetched by `uv run --with`, U1).

## 1. What will be built

1. **The inventory, in a standard format:** `sbom/` at the repo root, committed,
   one **CycloneDX 1.5** JSON file per lockfile. The lockfiles are **found, not
   listed** (U1): every `uv.lock` and `package-lock.json` that git tracks, at
   any depth. Each file is named after its folder (§ 5.1). In Yantra today:
   - `sbom/backend.cdx.json` from `backend/uv.lock`;
   - `sbom/frontend.cdx.json` from `frontend/package-lock.json`;
   - `sbom/root.cdx.json` from the root `uv.lock` (today only `deploy.py`'s
     `python-dotenv`).

   Generated from the lockfiles, never written by hand, and **byte-stable**: the
   same lockfile always gives the same file, whatever tool version made it
   (BR1-01, BR2-02). This is the file the aibots scanner bot will read in every
   repo later.
2. **The check:** `uv run tooling/deps/audit.py` (any OS; on Windows also
   `tooling/run-deps-audit.bat`) regenerates the SBOMs, then:
   - **known vulnerabilities:** every library (direct and indirect, exact
     version) is looked up in **OSV** (api.osv.dev), the open database that
     collects GitHub, PyPI and npm advisories with their CVE numbers;
   - **maintenance:** for each **direct** dependency, the date of its latest
     release; no release in **12 months** is flagged (CLAUDE-COMMON "Dependency
     health");
   - **the report:** `scratch/dependency-report.md` (gitignored) and a console
     summary: per vulnerability the library, installed version, CVE (or the
     advisory id when there is no CVE), the advisory ids, severity, fix
     versions, SBOM, and **runtime / dev**;
   - **exit codes:** **0** clean; **1** any vulnerability rated critical, high
     or unknown; **2** the check could not be completed. Stale dependencies are
     reported, not gating.
3. **Docs:** a section in `.claude/CLAUDE.md`: where the SBOMs are, how to run
   the check, the exit codes, and "commit `sbom/` with every dependency
   change".

**Out of scope:**
- SBOMs of the container images (base images, OS packages, `uv` itself) —
  queued: "image SBOM at build";
- the cross-repo report, alerts, LLM advice, a schedule — queued: "aibots
  scanner bot" (the user schedules runs later);
- moving the files to `smtw-common` (after it works here);
- a release-script step (`tooling/common/` is synced from `smtw-common` and
  changed there);
- end-of-life checks of runtimes;
- updating any library;
- the PEP 723 inline dependencies of `tooling/common/release.py` and
  `sync_common.py`, which are in no lockfile (an accepted gap; they belong to
  `smtw-common`; BR1-09).

## 2. Standards and practice

- **ISO 27001:2022 A.8.8 (management of technical vulnerabilities):** know what
  software runs, learn of its weaknesses quickly, act within a set time. The
  SBOM is the "know", the OSV lookup the "learn"; the response times come with
  the devops report.
- **ISO 27001:2022 A.5.9 (inventory of assets):** the SBOM is the inventory of
  the software parts.
- **CycloneDX 1.5 (OWASP)** is the SBOM format both tools write (1.6 is
  published as ECMA-424; 1.5 files are read by every 1.6 tool). **Package URL
  (purl, ECMA-427)** names each library (`pkg:pypi/flask@3.1.2`,
  `pkg:npm/%40vue/shared@3.5.13`); OSV takes purls directly. **SPDX (ISO/IEC
  5962)** is the other standard; CycloneDX is chosen because `uv` and npm both
  write it without extra tools.
- **One vulnerability, several advisories:** the same CVE is often published by
  GitHub (GHSA) and by the PyPI advisory database (PYSEC). Findings are grouped
  by CVE so each weakness is counted once (BR1-03).
- **Severity** is GitHub's advisory rating (critical / high / moderate / low)
  from the GHSA record; when no advisory in the group has one, "unknown",
  which **gates** (fail closed: an unrated weakness is not assumed harmless;
  BR1-05).

## 3. Where

- `tooling/deps/audit_core.py` (pure; `today` passed in):
  - `stable_sbom(doc)` → the document without `serialNumber`,
    `metadata.timestamp` and `metadata.tools` (the exporter's version: `npx
    npm@11` picks the newest 11.x at run time, so it changes with no lockfile
    change; BR2-02), components sorted by `bom-ref` (a canonical form; uv
    already sorts, npm is deterministic) (BR1-01);
  - `check_spec(doc)` → error unless `bomFormat == "CycloneDX"` and
    `specVersion == "1.5"` (BR1-07, BR2-05);
  - `packages(doc)` → purls; `direct(doc)` → the `dependsOn` of the
    `dependencies[]` entry whose `ref` is `metadata.component.bom-ref`;
  - `dev_flags(full_doc, runtime_doc)` → the dev purls (§ 5.2);
  - `findings(osv_records, packages)` → grouped by CVE, severity, fix versions
    (§ 5.3);
  - `stale(direct_deps, latest_dates, today)` (stale = more than 365 days;
    no date → "release date unknown", reported, not gating; BR2-05);
    `render_report(...)`;
    `exit_code(...)`.
- **Portable (U1):** nothing in `tooling/deps/` names Yantra, its folders or
  its projects; the files can be copied into another repo as they are.
- `audit_core.py` also: `sbom_name(lock_path, other_locks_in_folder)` → the
  SBOM file name (§ 5.1).
- `tooling/deps/audit.py` (shell): a PEP 723 script header
  (`requires-python = ">=3.12"`, `dependencies = []`), so `uv run
  tooling/deps/audit.py` runs it without any project's `pyproject.toml`. It
  finds the repo root and the lockfiles with `git` (§ 5.1), runs the exports,
  writes `sbom/` (created if missing), calls OSV, PyPI and npm with `urllib`
  (timeout 20 s each, a `User-Agent: <repo folder name>-deps-audit` header, as
  PyPI asks), writes the report, exits. Exports run with `subprocess.run(..., capture_output=True)` (uv also
  prints the document to stdout); `npx` is found with `shutil.which("npx")`
  (it is `npx.cmd` on Windows) and run with `--yes` (BR2-04), looked up only
  when an npm lockfile was found, so a repo without one needs no Node; not
  found then → exit 2 (BR3-05).
- `tooling/deps/tests/test_audit_core.py` with recorded OSV, PyPI and npm
  responses as fixtures (no network in tests).
- `tooling/deps/pytest.ini`: `testpaths = tests`, `pythonpath = .`. pytest
  takes the first `pytest.ini` found walking up from the tests, so this one
  governs only these tests; no project's `pyproject.toml` changes (U1; replaces
  the root and backend pytest tables of BR1-04 and BR2-01).
- `tooling/run-deps-tests.bat`: `uv run --no-project --with "pytest>=8,<10"
  pytest tooling\deps\tests` from the repo root (the range keeps a future major
  pytest out; BR3-02); `tooling/run-tests.bat` gains a third
  line calling it (the tests only; the audit itself is never in the test run;
  BR1-04).
- `tooling/run-deps-audit.bat` (`@echo off`, `cd /d "%~dp0.."`, `uv run
  tooling\deps\audit.py`, `exit /b %ERRORLEVEL%`; BR1-08). No committed run
  config: `.idea/` is gitignored, so the user adds a local one if wanted.
- `sbom/*.cdx.json`, `.claude/CLAUDE.md`.

## 4. Data

No database. Files: `sbom/*.cdx.json` (committed), `scratch/dependency-report.md`
(gitignored; `scratch/` created if missing).

## 5. Rules

### 5.1 Making the SBOMs
- **Finding the lockfiles (U1):** the repo root from `git rev-parse
  --show-toplevel`; the lockfiles from `git ls-files -z` **run with
  `cwd=root`** (git lists only the current folder's subtree, relative to it;
  BR3-01), tracked files only, so `node_modules/` and untracked copies are
  never picked up: every path whose file name is `uv.lock` or
  `package-lock.json`, in sorted order. Every path the script uses (`sbom/`,
  `scratch/`, the export folders) is `root / …`, never relative to where it
  was started. A listed lockfile that no longer exists on disk (deleted, not
  yet `git rm`-ed) → exit 2 naming it (BR3-04).
- **Names:** the lockfile's folder relative to the root, with `/` replaced by
  `-`; the root itself is `root` (`backend/uv.lock` → `backend.cdx.json`,
  `tools/x/uv.lock` → `tools-x.cdx.json`, `uv.lock` → `root.cdx.json`). When
  one folder holds both a `uv.lock` and a `package-lock.json`, both names get
  `-py` / `-npm` added. Two lockfiles that would get the same name
  (`a-b/` and `a/b/`, or a folder named `root`) → exit 2 naming both, never a
  silent overwrite (BR3-04).
- **No lockfile found** → exit 2 (nothing checked is not clean).
- **A lockfile removed:** an `sbom/*.cdx.json` that no lockfile produces any
  more is deleted, so `sbom/` always matches the repo.
- uv lockfiles: `uv export --format cyclonedx1.5 --frozen
  --preview-features sbom-export` in the lockfile's folder (`--frozen` so the
  lockfile is never rewritten; the preview flag silences the "experimental"
  warning; BR1-07).
- npm lockfiles: `npx npm@11 sbom --sbom-format cyclonedx --package-lock-only`
  in the lockfile's folder (Yantra CLAUDE.md: npm 10.9 crashes; npx needs the registry on a cold
  cache — a failure there is exit 2).
- Each output passes `check_spec`, then `stable_sbom`, and is written as JSON
  with 2-space indent, UTF-8, a final newline. Written only if the content
  differs, so an unchanged lockfile leaves `git status` clean (BR1-01).

### 5.2 Runtime or dev (BR1-02)
- npm marks dev packages (`cdx:npm:package:development` property).
- "Runtime" for uv means what `--no-dev` leaves, the same set Yantra's
  `Dockerfile.backend` installs (`uv sync --frozen --no-dev`). A repo with
  other default groups would need `--no-default-groups`; none has one today
  (BR3-05).
- uv does not: for **every uv lockfile**, a second export
  with `--no-dev` gives the runtime set; packages only in the full export are
  dev, compared **by purl** (uv renumbers `bom-ref`s between exports; BR2-03).
  The `sbom/` file is the full export; the dev mark appears only in the
  report.
- Dev findings **gate like runtime ones**: build tools run on developer
  machines and in the Docker build. The report shows which is which. (To revisit
  when the check gates a release.)

### 5.3 OSV (BR1-03)
- `POST /v1/querybatch` with `{"queries": [{"package": {"purl": …}}, …]}` in
  chunks of 1 000. A result without `vulns` is clean. A result with
  `next_page_token` is queried again with that token until none is left.
- Each advisory id found is fetched once: `GET /v1/vulns/<id>`. Records with
  `withdrawn` are skipped.
- **Grouping:** advisories sharing a CVE in `aliases` (or the id itself if it
  is a CVE) are one finding; no CVE → the advisory stands alone.
- **Severity:** the highest `database_specific.severity` in the group (GHSA
  records carry it); none → `unknown`. `severity[]` holds CVSS vectors only and
  is not scored.
- **Fix versions:** every `fixed` event in the `ranges[].events[]` of the
  `affected[]` entries for that package, listed as found (there is no version
  comparator in the standard library, and several release lines may each have
  a fix).

### 5.4 Latest release (BR1-06)
- PyPI: `GET https://pypi.org/pypi/<name>/json` → `info.version` and the
  `upload_time_iso_8601` of `urls[0]` (the latest release's files, which skips
  pre-releases); an empty `urls` list → date unknown (BR2-05).
- npm: `GET https://registry.npmjs.org/<name>` (full document; scoped names as
  `%40scope%2Fname`) → `time[dist-tags.latest]`.
- Stale: that date more than 365 days before `today`.

### 5.5 Exit codes (BR1-05)
- **2** whenever any step did not complete: an export failed, OSV or a
  registry unreachable or answering an error. The report says which step.
- **1** otherwise, if any finding is critical, high or unknown.
- **0** otherwise.
- Only public package names and versions leave the machine.

## 6. API

None (it calls OSV, PyPI and npm; § 5).

## 7. Design decisions

| Decision | Reason | Rejected alternative |
|---|---|---|
| CycloneDX files from the lockfiles, committed in `sbom/` | A standard file every repo can carry; the aibots bot reads it without the repo's tools | A hand-kept list (drifts); SPDX (needs extra tools) |
| Strip serial number, timestamp and tool version, sort, write only on change (BR1-01, BR2-02) | Same lockfile → same bytes; `git status` and the release script's clean-tree check stay true | Commit the raw output (dirty on every run) |
| OSV API from the standard library | No new dependency; covers PyPI and npm with CVE aliases | `pip-audit` + `npm audit` (two tools, two formats); OSV-Scanner (a binary; right for devops later) |
| Group advisories by CVE (BR1-03) | One weakness counted once | One line per advisory (doubles) |
| Unknown severity gates (BR1-05) | Fail closed | Unknown passes |
| Dev findings gate (BR1-02) | Build tools run on our machines and in the build | Runtime only |
| Maintenance on direct dependencies only, not gating | Those we chose and can replace; staleness is a judgement, not an emergency | Every indirect library (noise) |
| Exit codes 0 / 1 / 2 | Usable for a schedule or release gate later; "not checked" is never "clean" | Report only |
| Lockfiles found by `git ls-files`, SBOMs named after their folder (U1) | The same files work in any repo with no list to keep; a new lockfile is covered at once | A list of lockfiles in the script (one copy per repo); a config file (one more file to keep per repo) |
| A self-contained script: PEP 723 header, its own `pytest.ini`, tests via `uv run --with pytest` (U1) | Runs in any repo whatever its `pyproject.toml` holds; ready to move to `smtw-common` | pytest in the root project's dev group (ties it to Yantra's project files) |
| Not in the test run (user, 18-10-2026) | Tests must not depend on the network (fetching pytest once is the accepted exception, Open question 4); runs are scheduled later | Run on every `run-tests.bat` |

## 8. Tests and acceptance

- Pure (`test_audit_core.py`, fixtures recorded from real responses):
  `stable_sbom` (fields removed, order stable, same input → same bytes);
  `check_spec` (CycloneDX 1.5 passes; another format or version fails); `packages` and `direct` for a uv and
  an npm SBOM; `sbom_name` (root, one folder, nested folder, both kinds in one
  folder); dev marking both ways; OSV grouping (GHSA + PYSEC for one CVE →
  one finding with the GHSA severity; no-CVE advisory alone; withdrawn
  skipped); dev by purl although `bom-ref`s differ; fix versions over several
  ranges; stale at 364 / 366 days and with no date; exit
  codes (clean, high, unknown, a failed step).
- Acceptance: `tooling/run-tests.bat` green including the new tests.

### Manual checks
Important:
- [ ] Run `tooling\run-deps-audit.bat`: `sbom/` holds three files (`backend`,
  `frontend`, `root`); the report
  lists the libraries checked and any findings with CVE numbers and fix
  versions; running it again leaves `git status` unchanged.
- [ ] Disconnect the network and run it again: it says which step failed and
  exits with 2 (`echo %ERRORLEVEL%`).

## 9. Open questions and assumptions

1. ~~**In the test run?**~~ Decided 18-10-2026: no; the user schedules runs
   later.
2. **Assumption:** `uv` ≥ 0.10 (CycloneDX export, preview) on every machine that
   runs the check.
3. **Assumption:** `git` is on the path wherever the check runs (it finds the
   lockfiles; U1).
4. **Accepted:** the tests' `pytest` is fetched by `uv run --with` within
   `>=8,<10` and not locked; it only runs the tests and never ships (U1,
   BR3-02). The tests themselves never use the network, but **fetching pytest
   does** when uv's cache is empty or refreshed (a new machine, `uv cache
   clean`); on a warm cache it runs offline. So `run-tests.bat`, and a release
   through it, needs the network once per machine (BR3-02).

## 10. Amendments

(none)

## Gate A — 18-10-2026 (KLA)

Approved after round 3. At the gate: keep **both** checks — the repo SBOMs of
this step (frontend libraries, build and dev tools, before a release) and, later,
the SBOM of the deployed image (what runs in prod; queued "image SBOM at
build").

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 18-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR1-01 serial number and timestamp change every run | major | **Accepted**: stripped, sorted, written only on change (§ 5.1); track switched to full |
| BR1-02 uv has no dev marking | minor | **Accepted**: `--no-dev` export and set difference; dev gates like runtime (§ 5.2) |
| BR1-03 OSV details | minor | **Accepted**: empty result, pagination, withdrawn, grouping by CVE, GHSA severity, all fixed events (§ 5.3) |
| BR1-04 tests not collected | minor | **Accepted**: third line in `run-tests.bat`; the audit stays out (§ 3). The root dev group and pytest config are superseded by U1 (`run-deps-tests.bat`, `tooling/deps/pytest.ini`) |
| BR1-05 exit codes | minor | **Accepted**: 2 for any incomplete step; unknown gates (§ 5.5) |
| BR1-06 registry lookups | minor | **Accepted**: the fields named, scoped names, `today` passed in, timeouts (§ 5.4, § 3) |
| BR1-07 `--frozen`, preview flag, spec 1.5 | minor | **Accepted** (§ 5.1, § 2, § 3) |
| BR1-08 run config, `.bat` conventions, `scratch/` | nit | **Accepted**: no committed run config (`.idea/` gitignored) (§ 3, § 4) |
| BR1-09 inline deps of `tooling/common` | nit | **Accepted** as a named gap (out of scope) |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 18-10-2026

No blocker or major finding; the loop ends here.

| Finding | Severity | Answer |
|---|---|---|
| BR2-01 root pytest table governs the backend suite | minor | **Superseded** by U1: no project file gains a pytest table, so the problem cannot arise |
| BR2-02 tool version drifts in the npm SBOM | minor | **Accepted** (alternative): `metadata.tools` stripped too, so only a lockfile change changes the file (§ 1, § 3) |
| BR2-03 dev marking for the root project; compare by purl | minor | **Accepted** (§ 5.2, § 8) |
| BR2-04 stdout, `npx.cmd`, `--yes`, `sbom/` creation | nit | **Accepted** (§ 3) |
| BR2-05 `bomFormat`, User-Agent, 365 days, empty `urls` | nit | **Accepted** (§ 3, § 5.4, § 8); empty `urls` taken as the alternative "release date unknown, reported, not gating" rather than exit 2 (staleness never gates); User-Agent from the repo name since U1 |

### U1 — user change, 18-10-2026 (before approval)

"Want it to be portable to ai-bots repo": the cross-repo report becomes a
scanner bot in aibots, and the same files must work in every repo. Changed:
lockfiles found by `git ls-files` and SBOMs named after their folder (§ 1,
§ 5.1), so `sbom/tooling.cdx.json` becomes `root.cdx.json`; a PEP 723 script and
its own `pytest.ini` instead of the root and backend pytest tables (§ 3; the
BR1-04 and BR2-01 answers change accordingly); the User-Agent from the repo
name; image SBOMs and the aibots bot queued (out of scope). Reviewed in round 3.

### Round 3 — `2-brief-review-r3.md` (Fable), answered 18-10-2026

Reviewed against c2c45d2 + uncommitted S013, S014. No blocker or major finding;
the loop ends here.

| Finding | Severity | Answer |
|---|---|---|
| BR3-01 `git ls-files` is relative to the current folder | minor | **Accepted**: `-z`, run with `cwd=root`, all paths from the root (§ 5.1) |
| BR3-02 the test wrapper fetches pytest over the network on a cold cache | minor | **Accepted**: stated in Open question 4 and § 7; range `>=8,<10` (§ 3) |
| BR3-03 log rows describe superseded mechanisms | nit | **Accepted**: BR1-04, BR2-01, BR2-05 rows updated |
| BR3-04 name collisions; listed lockfile missing on disk | nit | **Accepted**: both → exit 2 naming the files (§ 5.1) |
| BR3-05 `npx` only when needed; meaning of "runtime" | nit | **Accepted** (§ 3, § 5.2) |

### Stale brief check s1 — `2-brief-review-s1.md` (Fable), 18-10-2026

Before coding. Changed since the baseline: S014's `qrcode` in `backend/uv.lock` and
`backend/pyproject.toml` (already in the reviewed tree, then uncommitted). No findings;
`Baseline:` set to 167e178.
