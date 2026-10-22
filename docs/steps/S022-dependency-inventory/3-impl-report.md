```
Step: S022 — Software inventory and vulnerability check
Doc: impl-report
Author: Coder (Sonnet)
Date: 18-10-2026
```

# S022 — Implementation report

## 1. What was built

- **SBOMs:** `sbom/backend.cdx.json`, `sbom/frontend.cdx.json`, `sbom/root.cdx.json` (CycloneDX 1.5), generated from `backend/uv.lock`, `frontend/package-lock.json`, `uv.lock`. Committed by the user later; not hand-written.
- **The check** `uv run tooling/deps/audit.py` (also `tooling/run-deps-audit.bat`): finds the lockfiles with git, regenerates the SBOMs, looks every library up in OSV, reads the latest release date of every direct dependency from PyPI / npm, writes `scratch/dependency-report.md` and a console summary, exits 0 / 1 / 2.
- **Tests:** 38 unit tests of the pure core with recorded fixtures; `tooling/run-deps-tests.bat`; third line in `tooling/run-tests.bat`.
- **Docs:** a bullet in `.claude/CLAUDE.md` (Yantra Specifics).

## 2. How it works

- `audit_core.py` is pure (no network, files or clock; `today` is passed in):
  - `stable_sbom` strips `serialNumber`, `metadata.timestamp`, `metadata.tools` and sorts components by `bom-ref`;
  - `check_spec`, `packages`, `direct`, `dev_flags` read an SBOM (dev by purl when a `--no-dev` export is given, else by npm's development property);
  - `sbom_name` / `sbom_names` name the files after the folder and report collisions;
  - `findings` groups OSV records by CVE, takes the highest GHSA severity (else `unknown`), skips withdrawn records, lists every `fixed` event for that package;
  - `stale`, `parse_iso_date`, `exit_code`, `render_report`.
- `audit.py` is the shell:
  - root and lockfiles from `git rev-parse` / `git ls-files -z` (cwd = root);
  - `uv export … --frozen --preview-features sbom-export` (full and `--no-dev`) or `npx --yes npm@11 sbom …`, each in the lockfile's folder;
  - each output passes `check_spec` and `stable_sbom`, and is written only if the bytes differ;
  - orphan `sbom/*.cdx.json` files are deleted;
  - OSV `querybatch` in chunks of 1000 with `next_page_token` follow-up, then `GET /v1/vulns/<id>` once per id;
  - PyPI / npm per direct dependency, timeout 20 s, `User-Agent: <repo>-deps-audit`;
  - any failed step is put in `errors` and the exit code becomes 2.

## 3. Files touched

New (13 non-fixture files plus 12 fixtures):
- `tooling/deps/audit_core.py`, `tooling/deps/audit.py`, `tooling/deps/pytest.ini`;
- `tooling/deps/tests/test_audit_core.py`;
- `tooling/deps/tests/fixtures/*.json` (12 files);
- `tooling/run-deps-tests.bat`, `tooling/run-deps-audit.bat`;
- `sbom/backend.cdx.json`, `sbom/frontend.cdx.json`, `sbom/root.cdx.json`.

Changed:
- `tooling/run-tests.bat` (third line and comment);
- `.claude/CLAUDE.md` (S022 bullet);
- `docs/steps/S022-dependency-inventory/1-brief.md` and `docs/steps/README.md` (status `In code review`).

## 4. Decisions taken

None departs from the brief. Small, forced choices:
- **Extra helpers in the core:** `sbom_names` (applies `sbom_name` to all lockfiles and finds collisions), `purl_base`, `purl_name_version`, `parse_iso_date`.
- **`findings(hits, records, purls)`** signature: `hits` is `{purl: [advisory ids]}` as OSV returned it, `records` is `{id: record}`, `purls` the libraries of one SBOM. The shell queries OSV once for all SBOMs and calls it per SBOM, adding the SBOM name and runtime/dev scope.
- **`dev_flags(full_doc, runtime_doc=None)`:** with no runtime export it uses npm's property; one function for both kinds.
- **Fix versions:** taken from the `affected[]` entries whose package purl matches the library; if none matches, from all entries.
- **Grouping:** records are merged when their CVE sets overlap, so a record with two CVEs joins both.
- **Registry errors:** a single package failing (HTTP error, timeout) is an exit-2 step, as the brief says for "answering an error"; with the network down this prints one FAILED line per direct dependency (20 lines) plus the OSV one.
- **Console encoding:** stdout is reconfigured to UTF-8 with `errors="replace"`, so a Windows console cannot crash the summary.
- **Check not in release path:** `tooling/run-deps-tests.bat` passes extra arguments (`%*`) on to pytest.

## 5. Not done, deferred, assumed

- **Fixtures** are real recordings (OSV 18-10-2026; `uv export`; `npm sbom`; PyPI / npm responses), with these exceptions:
  - the npm SBOM and the PyPI/npm registry answers are cut down to the fields and components the tests use;
  - the "withdrawn" case is a real record with a `withdrawn` field added in the test (no withdrawn record is returned by OSV queries, and none was found to fetch by id);
  - the no-CVE case is a real pillow advisory (`GHSA-4fx9-vc88-q2xc`).
- **Not tested:** the shell (`audit.py`) has no automated tests (brief § 8 lists the pure core only); it was exercised by the real runs below. OSV pagination (`next_page_token`) was never seen in a real response and is untested.
- **Assumptions:** `uv` 0.10 or later, `git` and (for npm lockfiles) `npx` on the path, as in the brief.
- Windows `.bat` files only; the Python script itself is OS-independent.
- The first full audit found **0 vulnerabilities** (178 libraries) and two stale direct dependencies: `bootstrap` 5.3.8 (latest release 26-08-2025) and `qrcode` 8.2 (01-05-2025). Reported, not gating.

## Test results

- `tooling/run-deps-tests.bat`: **38 passed**.
- `tooling/run-tests.bat`: backend **1287 passed**, frontend **57 passed** (10 files), deps **38 passed**.
- `tooling/run-deps-audit.bat`: exit 0; `sbom/` holds the three files; run again twice more, the files were not rewritten (same modification times; `sbom/` is untracked until the user commits, so `git status` could not be used to show it).
- Network failure simulated with `HTTPS_PROXY=http://127.0.0.1:9`: FAILED lines for OSV and every registry lookup, exit code 2.
- `npx vite build` not run: no frontend change.

## Manual checks

Important:
- [x] (by KLA, 21-10-2026: 3 SBOMs, 9 Pillow 12.3.0 CVEs listed with fix version 13.0.0, exit 1; after the Pillow 13.0.0 bump a re-run gave 0 vulnerabilities, exit 0, and `sbom/` changed only by the bump) Run `tooling\run-deps-audit.bat`: `sbom/` holds three files (`backend`, `frontend`, `root`); the report lists the libraries checked and any findings with CVE numbers and fix versions; running it again leaves `git status` unchanged. (After committing `sbom/`; the coder ran it twice more and the files were not rewritten.)
- [x] (covered by `tooling/deps/tests/test_audit_core.py::test_exit_codes`; accepted by KLA, 21-10-2026) Disconnect the network and run it again: it says which step failed and exits with 2 (`echo %ERRORLEVEL%`).

## Fix rounds

### Round 1

The user asked for CR1-01 and CR1-02, and later added CR1-03.

- **CR1-01 (minor): Fixed.**
  - `audit.py`: the work in `main()` (SBOM build, OSV lookup, release dates, grouping) runs in a `try/except Exception`. An unexpected error prints its traceback to stderr and is added to the step errors ("unexpected <Type> in the audit, results are incomplete"). The report is still written and the exit code is 2.
  - `audit_core.pair_batch_results(owners, results)` (pure) replaces the bare `zip()`: a different number of OSV results and queries raises `ValueError`. `osv_hits` turns that (and a missing `results` key) into `StepFailed`, which `lookup_vulnerabilities` now catches, so the OSV step is reported as failed instead of the extra libraries passing as clean.
  - Tests: pairing in order, and count mismatch (none and one result for two queries) raises.
- **CR1-02 (nit): Fixed.** New pure `audit_core.finding_id(row)` (CVE, else first advisory id); the report table and the console line both use it. Test: a row without CVE shows its advisory id in the CVE column.
- **CR1-03 (nit): Fixed** (added by the user during the round). `%*` removed from `tooling/run-deps-audit.bat`; it now runs `uv run tooling/deps/audit.py` as the brief says.
- **CR1-04:** rejected by the user (19-10-2026): ignore. **CR1-05:** left as it is by the user (19-10-2026).

Decision taken: the catch-all wraps the processing in `main()` and leaves `find_root` and the report writing outside it. If the report itself cannot be written (e.g. disk full), the error still escapes. Not covered by a test: the shell has no automated tests (brief § 8).

Tests: `tooling/run-deps-tests.bat` 42 passed (was 38). `tooling/run-tests.bat`: exit 0; backend 1287 passed, frontend 57 passed, deps 42 passed. `tooling/run-deps-audit.bat`: exit 0 (3 SBOMs, 178 libraries, 0 vulnerabilities, 0 failed steps).

### Round 2

The user asked for CR2-01 (nit) only.

- **CR2-01 (nit): Fixed.** In `tooling/deps/audit.py` `main()`, rendering and writing the report (`core.render_report`, `mkdir`, `write_text`) is now inside a `try/except Exception`. On failure it prints `deps audit: writing the report failed (<Type>: <message>)` to stderr, adds "the report could not be written" to the step errors (so the console summary counts it as a failed step) and sets the exit code to 2. The summary line and findings are still printed to the console. The exit code is computed by the pure `core.exit_code` first and only overridden to 2 on a write failure; the core is unchanged. Not covered by a test (the shell has no automated tests, brief § 8; failure not simulated).

Tests: `tooling/run-deps-tests.bat` 42 passed. `tooling/run-tests.bat`: exit 0; backend 1287 passed, frontend 57 passed, deps 42 passed. `tooling/run-deps-audit.bat`: exit 0 (3 SBOMs, 178 libraries, 0 vulnerabilities, 0 failed steps); `sbom/` files keep their old timestamps, so they were not rewritten.
