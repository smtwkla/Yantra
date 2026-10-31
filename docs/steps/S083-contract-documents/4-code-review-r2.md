```
Step: S083 — Contract documents
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 31-10-2026
```

# S083 — code review, round 2

**Verdict: no `blocker` or `major` finding is open, and no finding is open at all.** The fix round
fixes CR1-01 and CR1-02 as the report says, and its diff brings in no new fault. The backend tests of
the touched modules pass, and the schema docs check exits 0.

This round verifies the fix round only (`step_snapshot.py diff S083 --from-round 1`: three files). I
re-read `backend/contracts.py` lines 536–568, the fix round's lines of `docs/schema/notes.json` and
`docs/schema/schema-data.js`, and the § Fix rounds section of `3-impl-report.md`.

## Findings of earlier rounds

| ID | Severity | Status | Checked |
|---|---|---|---|
| CR1-01 | minor | Fixed | `notes.json:19` now ends "…by the manager or IT admin from Settings (S008); a contract's only by the site's manager (S083 E2)", the text the finding suggested. `schema-data.js` carries the same line, so the write ran. |
| CR1-02 | nit | Fixed | `_contract_access(row, key)` has no `cur` parameter. `git grep` finds its two callers (`read_contract`, `read_contract_for_change`) and both pass `(row, …)`. No test calls it. |

**Red, then green.** Neither fix adds or changes a test. A doc line and a dropped unused parameter have
no failing state to show, and the report gives that reason for both. No finding.

## The fix round's own diff

- `backend/contracts.py`: only the signature and the two calls change. The function body never used
  `cur`, and the callers still read the row through `_contract_site(cur, …)` first. The behaviour is
  unchanged.
- `docs/schema/notes.json` and `docs/schema/schema-data.js`: one line each, the same text. Nothing else
  in `docs/schema/` changed, and `check` agrees with the migrations.

## Tests

- `YANTRA_TEST_RUN=s083cr2 tooling/run-backend-tests.bat tests/test_contracts_api.py
  tests/test_documents_api.py`: **PASSED**, 126 passed in 13 s.
- `YANTRA_TEST_RUN=s083cr2 tooling/schema-docs.bat check`: **PASSED**, migration v45, 4 passed.
- No browser run: the fix round changed no screen and no API answer, and the coder made none either
  (correct for this diff).

## Nits

- none

## Checked and found consistent

- The fix round's report section lists both findings, the tests run with their counts, and
  `## Docs updated` for the round (`notes.json` by hand, `schema.json` and `schema-data.js` generated).
- The new `notes.json` text agrees with brief § 7 E2: restore and erase of a contract's documents need
  the contract's senior key at its site, and IT admin is excluded.
- The fix round changed no code outside `backend/contracts.py`, so the per-module backend run is
  enough. S084's files, which are being coded in the same tree, were not judged.

## Manual browser checks

Unchanged from round 1. The fix round adds none.

## Feedback

- none
