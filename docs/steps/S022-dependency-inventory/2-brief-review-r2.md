```
Step: S022 — Software inventory and vulnerability check
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 18-10-2026
```

# S022 — Brief review, round 2 (full track; round 2 of up to 3)

**Verdict: no `blocker` or `major` finding is open.** Every round-1 finding
marked `Accepted` is in the brief text, not only in the Review log (two small
details slipped — BR2-05). The r1 answers were re-tested on this machine, in the
scratchpad only: stripping `serialNumber` and `metadata.timestamp` makes the uv
and npm exports byte-identical across runs; `--preview-features sbom-export` is
the right flag for uv 0.10.10; `--no-dev` gives the backend runtime set; the root
pytest configuration collects the tooling tests. Three `minor` findings and two
`nit`s are new: the root pytest table silently becomes the backend suite's
configuration too (verified), the npm tool version drifts with `npx npm@11`, and
the tooling SBOM gets dev packages with no dev mark once pytest joins the root
project.

Reviewed against: the brief; `2-brief-review-r1.md`; `docs/Plan.MD` § 1 Repos
and phase 1; `CLAUDE-COMMON.md` (Dependency health, Pure core, Testing, Wrapper
scripts, Release workflow); `CLAUDE.md`; `SMTW-WebApp-Base.md` § Versioning &
Release, § Shared Tooling Sync, § Testing Pattern, § Pre-flight;
`docs/steps/README.md` (full-track template, index row). The repo: root
`pyproject.toml` + `uv.lock`, `backend/pyproject.toml` (+ `uv.lock`, pytest
9.1.1), `backend/tests/conftest.py`, `tooling/run-tests.bat`,
`run-backend-tests.bat`, `run-frontend-tests.bat`, `.gitignore`,
`tooling/common/release.py`. Ran, into the scratchpad only: `uv export --format
cyclonedx1.5 --frozen [--preview-features sbom-export] [--no-dev]` (uv 0.10.10)
three times in `backend/` and twice at the root; `npx npm@11 sbom --sbom-format
cyclonedx --package-lock-only` three times in `frontend/` (npm 11.21.0); a
normalise-and-hash script over all outputs; a pytest rootdir simulation with the
brief's `[tool.pytest.ini_options]`; OSV `querybatch` and two `GET /v1/vulns`;
PyPI JSON for `flask-cors`; the npm registry for `@vitejs/plugin-vue`; a Python
`subprocess` check of `npx` on Windows.

---

## Round-1 answers, verified in the text

| Finding | In the brief? | Note |
|---|---|---|
| BR1-01 strip + sort + write on change | § 1.1, § 5.1, § 7 | Verified byte-stable, see Checked |
| BR1-02 `--no-dev` set difference; dev gates | § 5.2, § 7 | Backend only — see BR2-03 for the tooling SBOM |
| BR1-03 empty result, paging, withdrawn, grouping, severity, fixed events | § 5.3 | All five rules present; re-checked live |
| BR1-04 root dev group, pytest config, third line | § 3 | Works from the root; side effect on the backend suite — BR2-01 |
| BR1-05 exit 2 for any incomplete step; unknown gates | § 5.5, § 2 | |
| BR1-06 endpoints, latest = non-pre-release, `today` in, 20 s timeout | § 5.4, § 3 | `User-Agent` for PyPI not carried over — BR2-05 |
| BR1-07 `--frozen`, preview flag, spec 1.5 | § 5.1, § 2, § 3 | `check_spec` tests `specVersion` only, not `bomFormat` — BR2-05 |
| BR1-08 no committed run config, `.bat` shape, `scratch/` | § 3, § 4 | |
| BR1-09 inline deps of `tooling/common` named as a gap | § 1 Out of scope | |

---

## Findings

### BR2-01 — `minor` — The root `[tool.pytest.ini_options]` becomes the backend suite's configuration too

**Problem.** pytest finds its config by walking **upward** from the invocation
directory until it meets a `pyproject.toml` that has a `[tool.pytest.ini_options]`
table. `backend/pyproject.toml` has none, so once the root one gains the table
from § 3, `cd backend && uv run pytest -v` (what `run-backend-tests.bat` does)
picks the **root** file: `rootdir` becomes the repo root and `configfile` the
root `pyproject.toml`. Verified in a scratchpad replica with the backend's pytest
9.1.1: from `backend/` with no arguments, `rootdir: …\pyt`, `configfile:
pyproject.toml` (the root one); the backend test was still collected, because
`testpaths` only applies when pytest is started *from* the rootdir.

**Why it matters.** Nothing breaks today, which is why it would go unnoticed:
node ids become `backend/tests/test_x.py::…`, `.pytest_cache` moves to the repo
root, `pythonpath = ["tooling/deps"]` is prepended to every backend run, and any
option added to the root table later (`addopts`, `filterwarnings`, markers)
silently governs the backend suite as well. Two projects, one unintended config.

**Options.**
1. **Give the backend its own table.** Add to `backend/pyproject.toml`:
   `[tool.pytest.ini_options]` with `testpaths = ["tests"]`. Verified: the
   walk-up then stops at `backend/`, `rootdir: …\backend`, and the root table
   governs only the root run. One more file under § 3; no behaviour change for
   the backend tests.
2. Put the tooling config in a `pytest.ini` under `tooling/deps/` and run
   `uv run pytest -c tooling/deps/pytest.ini` from the root. Works, but a
   second config format in the repo and a longer `.bat` line.
3. Accept the shared rootdir. Rejected: an invisible coupling.

**Recommendation.** Option 1; list `backend/pyproject.toml` under § 3 with the
one-line reason ("so the root pytest table does not become the backend's").

---

### BR2-02 — `minor` — "The same lockfile always gives the same file" is not quite true: `metadata.tools[].version` follows `npx npm@11`

**Problem.** After stripping, the only run-dependent content left is
`metadata.tools`: uv writes `{"vendor": "Astral Software Inc.", "name": "uv",
"version": "0.10.10"}`, npm writes `{"vendor": "npm", "name": "cli", "version":
"11.21.0"}`. `npx npm@11` resolves to the **newest 11.x on the registry at run
time**, so the day npm publishes 11.22.0 `sbom/frontend.cdx.json` changes with
no change to `package-lock.json`, on whichever machine runs the check first. A
uv upgrade does the same for the two uv files, but that is a deliberate local
action. § 1.1 promises "the same lockfile always gives the same file" and § 7
"same lockfile → same bytes"; the real statement is "same lockfile **and same
tool version**".

**Why it matters.** The purpose of BR1-01 was a clean `git status` before a
release. A tool-version drift is rare (a few times a year) and small (one line),
but it is exactly the kind of surprise the user asked the brief to rule out,
and the CLAUDE.md section should tell the user what such a diff means.

**Options.**
1. **Keep `metadata.tools`, state the rule honestly.** § 1.1 and § 7: "the same
   lockfile and tool versions give the same bytes; a uv or npm upgrade changes
   `metadata.tools` and is committed like any dependency change". One line in
   the CLAUDE.md section. Keeps the generator provenance, which is what the
   field is for.
2. **Strip `metadata.tools` as well** in `stable_sbom`. The file is then a pure
   function of the lockfile. Loses "which tool wrote this"; CycloneDX treats
   the field as optional, and the commit records who ran what. Simplest rule,
   least provenance.
3. Pin `npx npm@11.21.0` in `audit.py`. Turns the drift into a deliberate edit,
   but departs from the repo's `npx npm@11` convention (CLAUDE.md) and adds a
   version to keep.

**Recommendation.** Option 1 — the same position r1 took ("a real change and
should be committed"); it only needs the sentence corrected and the doc line.
For the user's learning: the NTIA "minimum elements" of an SBOM include the
author of the SBOM data and a timestamp; here the git commit supplies both, and
`metadata.tools` is the one piece of provenance that stays inside the file.

---

### BR2-03 — `minor` — Dev marking is specified for the backend only; the tooling SBOM gains five unmarked dev packages

**Problem.** BR1-04 adds `pytest` to a dev group of the **root** project, so
`sbom/tooling.cdx.json` grows from one component (`python-dotenv`) to six
(`pytest`, `iniconfig`, `packaging`, `pluggy`, `pygments`, the same five the
backend export marks as dev-only — verified by the `--no-dev` set difference:
exactly those five, and `colorama` correctly not among them). § 5.2 says "a
second **backend** export with `--no-dev`", so the report would show pytest as
a *runtime* dependency of the tooling.

Also, uv renumbers `bom-ref`s between the two exports (`pillow-16@12.3.0` in the
full export, `pillow-14@12.3.0` in `--no-dev`), so the set difference must be
taken on **purls**, which § 3's `packages(doc) → purls` implies but § 5.2 does
not say.

**Options.**
1. Generalise § 5.2: "for each uv project (backend and root), a second export
   with `--no-dev`; dev = purls in the full export absent from the `--no-dev`
   export". Two more subprocess calls, no new logic.
2. Leave the tooling SBOM unmarked (everything in it is "tooling" anyway).
   Rejected: the report would say runtime where it is not.

**Recommendation.** Option 1, and add "compared by purl, not `bom-ref`" to
§ 5.2 so the coder does not trip on the renumbering.

---

### BR2-04 — `nit` — Three facts of the tools the coder would otherwise find by trial

1. **`uv export -o` also prints to stdout.** With uv 0.10.10 and the CycloneDX
   format, `-o file` writes the file *and* writes the same 7 747 bytes to
   stdout (verified both from the shell and from `subprocess.run`). Harmless,
   but say which the coder reads: simplest is no `-o`, capture stdout, parse.
2. **`npx` from Python on Windows.** `subprocess.run(["npx", …])` fails with
   `WinError 2` because `npx` is `npx.CMD` and `CreateProcess` does not search
   for `.cmd`; `shutil.which("npx")` returns the full path and that runs
   (verified). Same would apply to `npm`; `uv` is an `.exe` and is fine. Say
   "resolve with `shutil.which`, exit 2 with a clear message when it is
   `None`".
3. **`npx --yes`.** On a cold cache npx prints a "will be installed" notice;
   with stdin not a TTY it proceeds, but `--yes` makes that explicit and keeps
   the command identical in a run config, a terminal and a subprocess. Also:
   `sbom/` does not exist yet, so `audit.py` creates it like `scratch/` (§ 4
   says so for `scratch/` only).

---

### BR2-05 — `nit` — Two accepted r1 details not in the text, and two small edges

1. **`bomFormat`** (BR1-07, accepted): § 3 `check_spec` tests `specVersion ==
   "1.5"` only; also assert `bomFormat == "CycloneDX"` so a non-SBOM JSON (an
   error document, say) is an exit 2, not a `KeyError` later.
2. **`User-Agent`** (BR1-06, accepted): PyPI asks clients to identify
   themselves; one header on the three `urllib` calls, e.g.
   `yantra-deps-audit (<repo>)`.
3. **"12 months"** (§ 5.4) needs one boundary for the test: say `> 365 days
   before today` (the 11 / 13-month tests in § 8 then sit either side of it).
4. **A PyPI release with no files**: `urls` can be empty (a release yanked or
   with no uploads), so `urls[0]` would raise. Rule: no `urls` → "latest date
   unknown" and exit 2 with the package named, consistent with § 5.5 ("the
   check could not be completed"), rather than a traceback.

---

## Checked and found consistent

- **Byte stability (BR1-01), tested.** Three uv exports in `backend/`, two at
  the root and three `npx npm@11 sbom` runs in `frontend/`: the raw files all
  differ (serial number, timestamp); after removing `serialNumber` and
  `metadata.timestamp` and dumping with `indent=2`, every run of each tool
  hashes identically. uv's `components[]`, `dependencies[]` and `dependsOn` are
  already sorted; npm's are not sorted but are deterministic, so the sort in
  `stable_sbom` is not needed for stability — it is still right to keep, as a
  canonical form if a tool changes its ordering. The sort changes npm's file
  once, on first generation only.
- **`--preview-features sbom-export`** is the flag for uv 0.10.10: without it
  the export prints `warning: uv export --format=cyclonedx1.5 is experimental
  … Pass --preview-features sbom-export to disable this warning`; with it,
  nothing. An unknown feature name is rejected (`error: invalid value …
  Unknown feature flag`, exit 2), so when a future uv graduates the format and
  drops the flag, the audit fails loudly into the exit-2 path rather than
  silently. `--frozen` left both `uv.lock` files untouched (`git status`
  clean). Running `uv export` under a foreign `VIRTUAL_ENV` (as it will inside
  `uv run python tooling/deps/audit.py`) prints no warning.
- **`--no-dev` export** works on the backend: 19 components against 24;
  `pytest` leaves the root's `dependsOn` (9 direct runtime libraries remain).
- **Spec check.** Both tools: `bomFormat` `CycloneDX`, `specVersion` `1.5`.
  npm's document also carries `$schema` and `metadata.lifecycles`;
  `stable_sbom` leaves them in, which is fine.
- **`direct(doc)`** as specified works for both: `metadata.component.bom-ref`
  is `yantra-backend-1@0.1.0` / `yantra-1@0.1.0` / `yantra-frontend@0.0.0`;
  the matching `dependencies[]` entry lists 10 / 1 / 9 direct dependencies.
  Every component in all three files has a purl; npm scoped purls are written
  `pkg:npm/%40scope/name@v`, as § 2 shows.
- **npm dev marks**: `cdx:npm:package:development` is the only property npm
  writes; 125 of 154 components carry it.
- **OSV (BR1-03), re-checked live.** A clean package returns `{}` (no `vulns`
  key); `querybatch` entries carry only `id` and `modified`, so the per-id
  `GET /v1/vulns/<id>` in § 5.3 is needed, not optional. `GHSA-q2x7-8rv6-6q7h`
  has `database_specific.severity: MODERATE` and aliases `CVE-2024-56326`,
  `PYSEC-2026-1475`; `PYSEC-2026-1471` has no severity and aliases
  `CVE-2025-27516`, `GHSA-cpwx-vrp4-4pq7` — grouping by CVE works as written.
  `withdrawn` is absent on live records. Fixed versions sit in
  `affected[].ranges[].events[].fixed` (`ECOSYSTEM` ranges for PyPI).
- **Registries (BR1-06).** PyPI `flask-cors`: `info.version` 6.0.5,
  `urls[0].upload_time_iso_8601` present. npm `@vitejs/plugin-vue` fetched as
  `%40vitejs%2Fplugin-vue`: `time[dist-tags.latest]` present. (The lock has
  5.2.4 while latest is 6.0.10 — the rule measures the project's release
  activity, not how far behind we are, which is the right reading of
  CLAUDE-COMMON "Dependency health".)
- **Root pytest config (BR1-04), tested.** `testpaths = ["tooling/deps/tests"]`
  with `pythonpath = ["tooling/deps"]` collects and runs a test that imports
  `audit_core` without any `__init__.py` or `sys.path` edit. `uv run pytest`
  at the root will sync the dev group into the existing root `.venv`
  (gitignored). `run-tests.bat`'s third line after backend and frontend is the
  right order (the backend line needs the dev DB; the new one needs nothing).
- **`release.py`** runs `TEST_CMD` and checks `git status --porcelain`; the
  audit stays out of `run-tests.bat`, so the network never enters the release
  test step (Decision "Not in the test run").
- **Full-track sections** are all present: 1 What + out of scope, 2 Standards,
  3 Where, 4 Data, 5 Rules, 6 API, 7 Design decisions, 8 Tests and acceptance
  with manual checks, 9 Open questions, 10 Amendments, Review log — the same
  shape as S013's brief. Header `Track: full` and the index row in
  `docs/steps/README.md` ("In review (full track since BR1-01)") agree.
- **Standards.** ISO 27001:2022 **A.8.8** (management of technical
  vulnerabilities: obtain information about vulnerabilities of the software in
  use, evaluate exposure, take measures) and **A.5.9** (inventory of
  information and other associated assets) are the right controls and are
  described correctly. **CycloneDX 1.5** is what both tools write; **1.6** is
  the edition standardised as **ECMA-424** and reads 1.5 files; **purl** is
  **ECMA-427**; **SPDX** is **ISO/IEC 5962**. The GitHub advisory severity
  scale (critical / high / moderate / low) is cited correctly, and
  `severity[]` holding CVSS vectors rather than scores is right. The
  maintenance standards (ISO 14224, EN 13306, ISO 55000, SMRP, TPM) do not
  bear on a tooling step and are rightly absent.
- **Manual checks**: both important, both genuinely need a person (a full run
  reading `git status`; an offline run reading `%ERRORLEVEL%`); nothing is
  over-marked. § 5.1 already notes that on a cold npx cache the offline run
  fails at export rather than at OSV — the expected result is the same.
- **Out of scope** still right; the `tooling/common/` files are synced from
  `smtw-common` and untouched; `tooling/deps/` is outside the sync inventory.
- **Scope and size**: no over-engineering; the pure core / thin shell split
  (`audit_core.py` / `audit.py`) follows CLAUDE-COMMON "Pure core, thin
  shell", with `today` passed in.
