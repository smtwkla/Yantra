```
Step: S022 — Software inventory and vulnerability check
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 19-10-2026
```

# S022 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** 0 blocker, 0 major, 0 minor, 1 nit.

Reviewed: fix round 1 (`3-impl-report.md` § Fix rounds › Round 1), on the same working tree
as round 1 (167e178 plus the uncommitted S022 files), read with `git diff -w --ignore-cr-at-eol`
and by reading `tooling/deps/audit.py`, `audit_core.py` and the new tests in full.
CR1-04 and CR1-05 were decided by the user (ignore / leave) and are not reopened.
`.claude/skills/step/SKILL.md` is modified but is not part of S022 and is not reviewed.

## Test results (run by the reviewer)

- `tooling\run-deps-tests.bat`: **42 passed** (38 in round 1, plus 4 new).
- `tooling\run-tests.bat`: exit 0. Backend **1287 passed**, frontend **57 passed** (10 files),
  deps **42 passed**.
- `tooling\run-deps-audit.bat`: exit 0. 3 SBOMs, 178 libraries, 0 vulnerabilities,
  2 stale/unknown direct dependencies, 0 failed steps. MD5 of all three `sbom/` files the same
  before and after the run.
- `npx vite build`: not run, because the frontend did not change.

## Round 1 findings, verified

- **CR1-01 (minor): Fixed.**
  - `audit.py:224-238`: the SBOM build, OSV lookup, findings grouping and release dates run
    inside `try/except Exception`. An unexpected error prints its traceback to stderr, becomes a
    named step error, and the report is still written. `core.exit_code` returns 2 whenever
    `errors` is non-empty. `Exception` does not catch `KeyboardInterrupt` or `SystemExit`, which
    is right.
  - Every case named in round 1 now ends in exit 2: `IncompleteRead`, `UnicodeDecodeError`,
    `KeyError` and `PermissionError` from `unlink`/`write_bytes` in `build_sboms`.
  - The fail-open `zip`: `audit_core.pair_batch_results` (`audit_core.py:230-236`) is pure and
    raises `ValueError` on a count mismatch. `osv_hits` (`audit.py:123-126`) turns that, a
    missing `results` key and a non-list `results` into `StepFailed`, and
    `lookup_vulnerabilities` now catches `StepFailed` (`audit.py:194`). The libraries are no
    longer counted as clean without being checked.
  - The defaults set before the `try` (`built, rows, stale_rows, all_purls = [], [], [], []`)
    keep the report and the summary line valid whatever point the failure is at.
  - Tests: pairing in order, and a mismatch with 0 and with 1 result for 2 queries
    (`test_audit_core.py:314-321`).
- **CR1-02 (nit): Fixed.** `audit_core.finding_id` (`audit_core.py:225-227`) is used by the
  report table (`:256`) and the console line (`audit.py:253`), so both now use the same rule.
  Test `test_report_shows_advisory_id_when_there_is_no_cve` checks the table cell.
- **CR1-03 (nit): Fixed.** `tooling/run-deps-audit.bat` now runs `uv run tooling\deps\audit.py`
  with no `%*`, as § 3 says.

Nothing new came in with the fix: no new dependency, no new file outside `tooling/deps/`, and
the core stays pure (`pair_batch_results` and `finding_id` take plain data).

## The coder's choice: `find_root` and the report write outside the catch-all

The brief's § 5.5 says exit **2** "whenever any step did not complete". The two parts left
outside the `try` are different cases:

- **`find_root` (`audit.py:215-219`)** is consistent with § 5.5. Its expected failure (not a git
  repository, git not installed) is a `StepFailed` and returns 2 with a message. There is no
  report to write without a root anyway. Other errors there are not realistic.
- **The report write and the summary (`audit.py:240-247`)** do not fully match § 5.5. If
  `scratch/` cannot be created or written, the `OSError` escapes and Python exits **1**,
  the code § 5.5 keeps for "a critical, high or unknown vulnerability". See CR2-01. It is a nit,
  not a conflict that matters today: it needs a broken disk or folder, no scheduler reads the
  code yet (Open question 1), and the traceback is on the console.

## Findings

### CR2-01 — nit — `tooling/deps/audit.py:240-247`: a failure writing the report exits 1, not 2

**Problem.** `scratch.mkdir`, `write_text`, `render_report` and `exit_code` run after the
catch-all. An `OSError` while writing the report (disk full, `scratch` is a file, the report
open and locked in an editor on Windows), or a bug in `render_report`, leaves `main()` as an
uncaught exception. The interpreter then exits 1. The summary is printed after the write, so in
that case the console shows only the traceback.

**Failure scenario.** A later scheduled run or release gate (Open question 1) finds
`scratch\dependency-report.md` locked by an editor. The audit exits 1, and the scheduler reports
"gating vulnerability found" although none was found.

**Suggested fix.** Either one of these:
- Put the report write in `try/except OSError`, print `deps audit: report could not be written:
  <e>` to stderr, print the summary anyway, and return 2.
- Or map any exception that escapes `main()` to 2 in the `__main__` block
  (`try: sys.exit(main()) except Exception: traceback.print_exc(); sys.exit(2)`). This covers
  both this case and `find_root`.

No test is needed: the shell has no automated tests (§ 8).

## Checked and found consistent

- **Exit codes:** every path inside the processing that fails now gives 2. A network failure
  is still a named step (`OSV lookup failed: …`, `latest release of … could not be read: …`),
  not the generic "unexpected" message, because the narrow `except` clauses come first.
- **No silent swallowing:** the catch-all prints the full traceback and adds the error to the
  report and the console. The `noqa: BLE001` comment points to the docstring, which says why.
- **Decisions taken:** the choice to leave `find_root` and the report write outside the
  catch-all is listed in the fix round. The user decisions on CR1-04 and CR1-05 are recorded.
- **Byte stability** still holds: the fix did not touch `stable_sbom` or `write_if_changed`, and
  the SBOM checksums were the same before and after the reviewer's run.
- **Portability (U1):** the new code names no project or folder.
- **Impl report:** `## Manual checks` still holds both **important** checks of the brief as
  unticked boxes.

## Manual browser check

None: this step has no UI. The user still has to run the brief's important checks from the
impl report:
- [ ] Run `tooling\run-deps-audit.bat`. `sbom/` should hold three files, the report should
  list the libraries checked and any findings, and **after committing `sbom/`** a second run
  should leave `git status` unchanged.
- [ ] Disconnect the network and run it again. It should name the failed step and exit 2
  (`echo %ERRORLEVEL%`).
