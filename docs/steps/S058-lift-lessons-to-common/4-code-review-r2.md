```
Step: S058 — Yantra's general lessons, written for CLAUDE-COMMON and the base
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 26-10-2026
```

# S058 — Code review, round 2 (verify)

**Verdict: no `blocker` or `major` finding is open.** All 14 round-1 findings are fixed as the fix round says. The fix round adds one nit (CR2-01).

Re-read: `3-impl-report.md` (§ 8 points 3, 5–10, § 9, § 10, § Fix round 1); the base's quoted lines (`.claude/SMTW-WebApp-Base.md:429, 438, 478-489`); `tooling/run-tests.bat:1-17`, `tooling/release-tests.bat:1-5`, the `run_logged.py` calls in `tooling/run-*.bat`; `backend/app.py:28-33`. Nothing else was re-read.

## Tests run

None. The fix round changed text only in the impl report; `git status` shows the same code files as round 1, whose full run (`s058cr1`) was green. No browser test is due.

## Round-1 findings

| ID | Severity | Status | Checked |
|---|---|---|---|
| CR1-01 | minor | Fixed | Point 5 says "Nothing fails at import"; the Local DB bullet names `app.py` at start. Matches `app.py:32-33`. |
| CR1-02 | minor | Fixed | Point 6 replaces the "Dev databases must be recreated" bullet and the "(v2+)" bullet. Both quotes exist at base `:487-488` (see CR2-01). |
| CR1-03 | minor | Fixed | Tags read "(Yantra, 22-10-2026, a tooling commit, not a step; …)" and "(Yantra, S025 and 22-10-2026, a tooling commit.)". The `S0xx` note is gone. Leaving out the hash is a reasoned choice, stated in the fix round. |
| CR1-04 | minor | Fixed | Point 7 states the wildcard grant on `appname_test_%` and `appname_upgrade_%` and the "Access denied" symptom. |
| CR1-05 | minor | Fixed | § 9.2 lists `run-tests.bat` lines 3-4, 7 and 17 (all correct), `release-tests.bat` line 3, and the five `CLAUDE.md` places. The false "summary check" claim is gone. The § 10 row names the two sentences to drop. |
| CR1-06 | nit | Fixed | |
| CR1-07 | nit | Fixed | |
| CR1-08 | nit | Fixed | |
| CR1-09 | nit | Fixed | |
| CR1-10 | nit | Fixed | The dialog-fit bullet is added; the in-view bullet is named in Decisions taken item 5. |
| CR1-11 | nit | Fixed | Matches `.claude/CLAUDE.md` *Release*. |
| CR1-12 | nit | Fixed | `run-deps-tests.bat:9`, `run-tooling-tests.bat:3-4`, three wrappers. All correct. |
| CR1-13 | nit | Fixed | |
| CR1-14 | nit | Fixed | |

## Findings

No `blocker`, `major` or `minor` finding.

## Nits

- **CR2-01** (nit) `3-impl-report.md:257`: the base bullet is "Dev databases must be recreated (drop + recreate). Document this clearly." (`SMTW-WebApp-Base.md:487`). Quote both sentences, so the paste does not leave "Document this clearly." behind.

## Manual checks

None (brief § 5). The impl report says none, which matches.

## Checked and found consistent

- **Quotes.** Every base sentence the fix round quotes exists in `.claude/SMTW-WebApp-Base.md`: the init_db bullet (`:429`), the singleton sentence (`:438`), the squash sentence (`:481-482`, a line break apart), the two "After squashing" bullets and the kept last bullet (`:487-489`).
- **No mail values.** A grep of the impl report for addresses, `smtp.`, `mailgun.` and the mail ports finds none. Point 1 still uses only `example.test`.
- **Generic texts.** The new text in points 5–10 names no Yantra value or step in a rule; the step numbers and dates are in provenance tags only. `appname_`, `<APP>_TEST_RUN` and `frontend/node_modules` are generic.
- **Code unchanged.** `git status` lists the same three code files as round 1.

## Feedback

- none
