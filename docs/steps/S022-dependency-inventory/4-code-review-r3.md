```
Step: S022 — Software inventory and vulnerability check
Doc: code-review r3
Author: Code reviewer (Opus)
Date: 20-10-2026
```

# S022 — Code review, round 3

**Verdict: no `blocker` or `major` finding is open.** 0 blocker, 0 major, 0 minor, 2 nit.

Reviewed: fix round 2 (`3-impl-report.md` § Fix rounds › Round 2), on the same working tree
(167e178 plus the uncommitted S022 files), by reading `tooling/deps/audit.py` `main()` in full.
CR1-04 and CR1-05 were decided by the user and are not reopened. `.claude/skills/step/SKILL.md`
is modified but is not part of S022 and is not reviewed.

## Test results (run by the reviewer)

- `tooling\run-deps-tests.bat`: **42 passed**.
- `tooling\run-tests.bat`: exit 0. Backend **1287 passed**, frontend **57 passed** (10 files),
  deps **42 passed**.
- `tooling\run-deps-audit.bat`: exit 0. 3 SBOMs, 178 libraries, 0 vulnerabilities,
  2 stale/unknown direct dependencies, 0 failed steps. MD5 of all three `sbom/` files the same
  before and after the run.
- **Write failure simulated** (no code edited): a throw-away script in the reviewer's scratchpad
  imported `audit`, replaced `build_sboms` with an empty result and `core.render_report` with a
  function raising `PermissionError`, then called `main()`. Result: stderr
  `deps audit: writing the report failed (PermissionError: [Errno 13] locked)`, the summary line
  with `1 failed step(s)`, `FAILED: the report could not be written: …`, and `main()` returned
  **2**.
- `npx vite build`: not run, because the frontend did not change.

## Round 2 finding, verified

- **CR2-01 (nit): Fixed.** `audit.py:244-251`: `render_report`, `mkdir` and `write_text` are in
  `try/except Exception`. On failure the message goes to stderr, the error is added to `errors`
  (so the summary counts it), and `code = 2`. The summary and the findings are printed after the
  `try`, so they still reach the console. `core.exit_code` stays pure and is computed before; the
  override to 2 is in the shell only. `Exception` does not catch `KeyboardInterrupt`. The
  behaviour matches § 5.5 and the simulation above.

Nothing else changed in the fix: no new file, no new dependency, the core and its tests are the
same, and `stable_sbom` / `write_if_changed` were not touched.

## Findings

### CR3-01 — nit — `tooling/deps/audit.py:259`: the console names the report even when it was not written

**Problem.** The last line always prints `report: <path>\scratch\dependency-report.md`, also
after the write failed. If an earlier run left a report there, that file is from the last
successful run, not this one.

**Failure scenario.** The report is locked in an editor. The run exits 2 and prints `FAILED: the
report could not be written`, then `report: …dependency-report.md`. The user opens the old file
and reads last week's results as today's. The `FAILED` line two lines up makes this unlikely.

**Suggested fix.** Print `report: not written` (or skip the path) when the write failed.

### CR3-02 — nit — `tooling/deps/audit.py:248-249`: a bug in `render_report` is reported without its traceback

**Problem.** The comment names "a render bug" as one of the cases, but the handler prints only
`type: message`. The processing catch-all above it (`:236-237`) prints the full traceback. For a
`KeyError` in `render_report`, the console shows only `KeyError: 'fixed'`, with no line number.

**Failure scenario.** A new OSV field shape breaks `render_report`. The audit exits 2 (correct),
but the message alone does not show where in `audit_core.py` it failed, so it has to be
reproduced to be found.

**Suggested fix.** Call `traceback.print_exc()` in this handler too, as the one above does.

No test is needed for either: the shell has no automated tests (§ 8).

## Checked and found consistent

- **Exit codes (§ 5.5):** every failure path now gives 2: `find_root` (`StepFailed`), the
  processing (named step or catch-all) and the report write. 1 is left only for a gating
  finding, 0 for clean.
- **No silent swallowing:** the new handler prints to stderr and adds the error to the console
  summary; the `noqa: BLE001` comment says why the catch is broad.
- **Decisions taken:** the round 2 entry describes the change and that it is not covered by a
  test; nothing in the code is outside it.
- **Byte stability:** SBOM checksums unchanged by the reviewer's run.
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
