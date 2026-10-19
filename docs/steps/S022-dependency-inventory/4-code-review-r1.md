```
Step: S022 — Software inventory and vulnerability check
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 18-10-2026
```

# S022 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** 0 blocker, 0 major, 1 minor, 4 nits.

Reviewed: the working tree on top of 167e178, read with `git diff -w --ignore-cr-at-eol`.
Changed files: `.claude/CLAUDE.md` and `tooling/run-tests.bat`. New files: `tooling/deps/`
(`audit_core.py`, `audit.py`, `pytest.ini`, `tests/` with 12 fixtures),
`tooling/run-deps-tests.bat`, `tooling/run-deps-audit.bat`, and `sbom/*.cdx.json`.
The status edits in `docs/steps/README.md` and the brief are workflow edits.
`.claude/skills/step/SKILL.md` (the `/step ls` bulb column) is also modified. It is not part of S022 and is not reviewed here.

## Test results (run by the reviewer)

- `tooling\run-deps-tests.bat`: **38 passed**. pytest picked up `tooling\deps\pytest.ini`
  (`rootdir: tooling\deps`), so no project's config is involved.
- `tooling\run-tests.bat`: exit 0. Backend **1287 passed**, frontend **57 passed** (10 files),
  deps **38 passed**.
- `tooling\run-deps-audit.bat`: exit 0. Result: 3 SBOMs, 178 libraries, 0 vulnerabilities,
  2 stale direct dependencies (`bootstrap`, `qrcode`), 0 failed steps. MD5 and mtime of all
  three `sbom/` files were the same before and after the run, so nothing was rewritten.
- Live OSV spot check (read-only `curl`): OSV accepts the percent-encoded scoped purl
  `pkg:npm/%40babel/traverse@7.22.0` and answers exactly as it does for the unencoded form.
  Its `affected[].package.purl` is `pkg:npm/%40babel/traverse`, which is the form
  `_fixed_versions` matches. So scoped npm packages are really checked, not passed as clean
  without a check.
- `npx vite build`: not run, because the frontend did not change.

## Findings

### CR1-01 — minor — `tooling/deps/audit.py:36`, `:122`, `:204-244`: an unexpected error exits 1, not 2, and writes no report

**Problem.** `NETWORK_ERRORS` catches `URLError`, `TimeoutError`, `OSError` and
`JSONDecodeError`. Any other exception escapes `main()`, and Python then exits with code
**1**. The brief defines 1 as "a critical, high or unknown vulnerability", and § 5.5 says
**2** "whenever any step did not complete". Because the report is written at the very end,
none is written in that case either. Ways it can happen:
- `http.client.IncompleteRead`: a connection cut mid-body. It is an `HTTPException`, not an
  `OSError`.
- A `UnicodeDecodeError` when `subprocess.run(..., encoding="utf-8")` decodes non-UTF-8 tool
  output.
- A `KeyError` on `answer["results"]`.
- A `PermissionError` from `old.unlink()` or `write_if_changed`. These are `OSError`s, but
  `build_sboms` only catches `StepFailed`.

There is also a quieter case in `zip(pending, owners, answer["results"])` (line 122). If
OSV ever returns fewer results than queries, the extra purls are dropped without a word and
count as clean. That is fail-open, against the brief's "nothing checked is not clean".

**Failure scenario.** A scheduled run (Open question 1) hits a truncated OSV response. The
traceback exits 1, and the scheduler reads it as "gating vulnerability found". Someone
opens `scratch/dependency-report.md` and finds the previous run's report, or none at all.

**Suggested fix.**
- Wrap the body of `main()` in `try/except Exception`. Print the traceback to stderr, add a
  step error, still write the report, and return 2.
- In `osv_hits`, raise `StepFailed` (and include it in the OSV `except`) when
  `len(answer["results"]) != len(pending)`.

### CR1-02 — nit — `tooling/deps/audit_core.py:242`: the report's CVE column shows `-` for an advisory without a CVE

Brief § 1.2 asks for "CVE (or the advisory id when there is no CVE)". The console line does
this (`r['cve'] or r['ids'][0]`, `audit.py:241`), but the report table puts `-` in the CVE
column. The id is still in the Advisories column, so nothing is lost. Use the same fallback
as the console for consistency.

### CR1-03 — nit — `tooling/run-deps-audit.bat:6`: `%*` passed to a script that takes no arguments

Brief § 3 spells out the wrapper as `uv run tooling\deps\audit.py`. `audit.py` reads no
arguments, so `%*` does nothing. It was not listed in "Decisions taken", which only
mentions `%*` for the tests wrapper (under the odd label "Check not in release path").
Harmless. Drop it, or list it in the report.

### CR1-04 — nit — `tooling/deps/audit.py:136-144`, `:194-201`: non-registry dependencies would keep the check at exit 2 for good (portability)

Every direct purl is looked up on PyPI or npm, and a 404 is a failed step (exit 2, as
§ 5.5 says). Suppose a repo later depends directly on a git or path package (for example a
shared library from a git URL in another SMTW repo). Its lookup fails on every run, and the
check can never report 0. uv may also add purl qualifiers (`?vcs_url=…`) for such sources,
and `purl_name_version` would then fold them into the version. This does not happen in
Yantra today. Note it for the move to `smtw-common`: decide whether a non-registry source
is skipped and reported, or fails. No change needed in this step.

### CR1-05 — nit — `tooling/deps/audit.py:217`, `:194-201`: the same library can be fetched twice

`all_direct` holds purls with their versions. A library that is a direct dependency in two
SBOMs at different versions is therefore fetched from the registry once per version, but
stored under one `purl_base` key. This costs one extra request and changes nothing in the
result. Deduplicate by `purl_base` if it ever matters.

## Scope and brief conformance

- **What § 1 asks for is all built.**
  - Lockfiles are found with `git ls-files -z` run with `cwd=root`.
  - SBOM names follow § 5.1, including `-py`/`-npm` and collisions reported as exit 2.
  - A tracked lockfile missing on disk is exit 2, and so is having no lockfile at all.
  - Orphan SBOM files are deleted.
  - Both exports run in the lockfile's folder with `--frozen --preview-features sbom-export`.
    For uv, a second `--no-dev` export gives the dev set, compared by purl.
  - `npx` is looked up only when there is an npm lockfile.
  - `check_spec` runs, then `stable_sbom`, then `write_if_changed`.
  - OSV `querybatch` runs in chunks of 1 000 with `page_token`, followed by one `GET` per id.
    Withdrawn records are skipped.
  - Findings are grouped by CVE. The highest GHSA severity wins, and `unknown` gates.
  - Fix versions come from the matching `affected[]` entries.
  - PyPI `urls[0]` and npm `time[dist-tags.latest]` are used, with a 20 s timeout and a
    `<repo>-deps-audit` User-Agent.
  - The 365-day stale rule and "release date unknown" are reported but do not gate.
  - Exit codes are 0/1/2 (apart from CR1-01).
  - The `CLAUDE.md` section is added.
  - The third line in `run-tests.bat` runs only the unit tests, not the audit.
- **Nothing beyond the brief**, apart from the reported helpers (`sbom_names`,
  `purl_base`, `purl_name_version`, `parse_iso_date`) and the UTF-8 stdout reconfigure.
  Both are listed in "Decisions taken". The two decisions not spelled out in the brief are
  also listed: the fix-version fallback to all entries, and merging of overlapping CVE sets.
- **Portable (U1):** nothing in `tooling/deps/` names Yantra, its folders or its projects.
  The User-Agent is built from the repo folder's name. The script has a PEP 723 header and
  carries its own `pytest.ini`.
- **Track:** full, which is right for this step.

## Checked and found consistent

- **Pure core:** `audit_core.py` has no network, file, clock or framework access, and
  `today` is passed in. The shell (`audit.py`) only fetches inputs, calls the core and
  writes the results.
- **Security:**
  - Only public package names and versions are sent out (§ 5.5).
  - Subprocesses get argument lists, never `shell=True`.
  - URL path parts are `quote(..., safe='')`d.
  - No secrets are read.
- **Byte stability:**
  - `serialNumber`, `metadata.timestamp` and `metadata.tools` are stripped, and components
    are sorted by `bom-ref`.
  - Output is written only when the bytes differ. The reviewer's run confirmed this.
- **Line endings:** `core.autocrlf=true` and there is no `.gitattributes`. On a fresh
  checkout the SBOMs arrive as CRLF, so the first audit rewrites them as LF. `git status`
  stays clean, because git normalizes line endings when comparing, so the manual check
  still holds. Not a finding. A `sbom/*.json text eol=lf` line would stop that one rewrite
  if wanted.
- **Counts match the manifests:**
  - backend: 10 direct = 9 in `[project].dependencies` + `pytest`;
  - frontend: 9 direct = 5 dependencies + 4 devDependencies;
  - root: 1 (`python-dotenv`).
- **Dev marking:**
  - uv uses the purl set difference, and the test shows the `bom-ref`s really differ
    between the two exports.
  - npm uses the `cdx:npm:package:development` property.
- **Tests:** every item in brief § 8 is covered:
  - `stable_sbom` and `check_spec`;
  - `packages` and `direct` for uv and npm;
  - `sbom_name` (root, one folder, nested folder, both kinds in one folder) and collisions;
  - dev marking both ways;
  - GHSA + PYSEC as one finding with the GHSA severity;
  - a PYSEC advisory alone being `unknown`;
  - a no-CVE advisory standing alone;
  - withdrawn records skipped;
  - fix versions over several ranges and only for the matching package;
  - the stale rule at 364 / 365 / 366 days and with no date;
  - all exit codes;
  - the report, clean and with findings.

  The fixtures are real recordings, cut down as the report says. The shell has no
  automated tests, and pagination is untested. Both are stated in the report, and § 8
  lists only the core.
- **Errors are not swallowed:** every caught error becomes a named step error in the report
  and the console. The exception is CR1-01.
- **No deprecated APIs.** Comments explain *why* (renumbered `bom-ref`s, `cwd=root`, the
  `git status` motive).
- **`run-tests.bat`:** keeps `|| exit /b 1` on the new line. `run-deps-tests.bat` ends with
  `exit /b %ERRORLEVEL%`.
- **Impl report:** the `## Manual checks` section holds both **important** checks of the
  brief as unticked boxes.

## Manual browser check

None: this step has no UI. The user still has to run the brief's important checks from
the impl report:
- [ ] Run `tooling\run-deps-audit.bat`. `sbom/` should hold three files, the report should
  list the libraries checked and any findings, and **after committing `sbom/`** a second
  run should leave `git status` unchanged.
- [ ] Disconnect the network and run it again. It should name the failed step and exit 2
  (`echo %ERRORLEVEL%`).
