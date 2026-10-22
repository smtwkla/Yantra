```
Step: S025 — Release safety and ticket integrity (audit fixes)
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 22-10-2026
```

# S025 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** CR1-01 and CR1-02 are fixed. This round adds 1 `nit`. The r1 nits CR1-03 to CR1-05 are still open, because the user did not ask for them.

Reviewed: only the fix round (impl report § Fix rounds, Round 1), against `4-code-review-r1.md` and the approved brief. The code is the working tree on `3df667c`, with S025, S019 and S020 uncommitted in the same files.

## Test results (my runs, 22-10-2026)

| Suite | Result |
|---|---|
| `tooling/run-tests.bat` | exit 0. Backend: 2003 passed. Frontend: 13 files, 110 tests passed. Deps: 42 passed. Tooling: 22 passed. |
| `tooling/run-e2e-tests.bat e2e/tickets-parts.spec.js e2e/tickets-work.spec.js` | exit 0. 66 passed in 2.7 min (22 tests × 3 projects), 0 failed. The S025 tests in `tickets-work.spec.js` pass in all three projects. |

The fix round changed no screen and no API that a screen uses, so a full browser run is not needed. The frontend did not change for S025 in this round, so I did not run `npx vite build`.

## Status of the round-1 findings

| Finding | Status | Check |
|---|---|---|
| CR1-01 (`minor`) | **Fixed** | `tooling/deploy.py` `_schema_ready_once` now catches `http.client.HTTPException` together with `OSError`, `ValueError` and `AttributeError`. A cut answer is therefore "not yet", and the timeout path prints the rollback lines. `tooling/tests/test_deploy.py` adds two cases to `test_anything_else_is_not_yet`. `IncompleteRead` is the case that proves the fix: it is an `HTTPException` and not an `OSError`. `RemoteDisconnected` is also a `ConnectionResetError`, so it passed before the fix as well. The case is harmless and documents the error. The coder left out the safety-net `try/except` around `main()`, as the user asked. The report says so. |
| CR1-02 (`minor`) | **Fixed** | The `backend/equipment.py` note no longer says "nothing else locked". It names the foreign-key shared locks that a state change takes, and the two new accepted deadlocks: a repeat raise against a send-back, and a unit edit against a ticket move. The `backend/tickets.py` note already said this through S019, and it lists the four accepted deadlocks. In the brief, § 5.2 "Order" keeps the old text and adds a dated correction. The brief's Review log has the answer. Impl report decision 7 and the comment in `test_a_send_back_committed_during_the_raise_refuses_the_repeat` now say that the test covers only the order where the send-back commits first. |

A process note, not a finding: the brief and its Review log belong to the planner (README § Findings). Here the coder edited them on the orchestrator's instruction, and the impl report lists the brief among the changed files. The edit is wording only and is marked as a correction, so nothing that the user approved has changed.

## Findings

### CR2-01 — `nit` — One line of the `equipment.py` lock-order note is spliced

`backend/equipment.py:65`

- **Problem.** The fix put the new sentence and the old "Its inserts take shared FK locks (person, trade, cause, action," on one line. That line is 148 characters long, and the note's other lines wrap at about 90. The text is correct, but the old sentence now starts in the middle of a line, so a reader can miss where the new part ends.
- **Failure scenario.** A later engineer reads the note to add a lock. The engineer skims past the end of line 65 and takes the insert's foreign-key locks to be part of the deadlock list.
- **Fix.** Re-wrap the paragraph and start "Its inserts take shared FK locks …" on its own line.

## Checked and found consistent

- **The poll's caught exceptions.** `URLError` and `HTTPError` (a 502 while the backend starts) are `OSError`s. `BadStatusLine`, `IncompleteRead` and `LineTooLong` are `HTTPException`s. A body that is not JSON is a `ValueError`. A body that is not an object raises `AttributeError`. Nothing else can come out of `urlopen`, `read()` or `json.loads` on a normal network fault. The comment says why each one is caught.
- **No widening of "not yet".** A `200` with `"schema_ready": true` is still the only answer that ends the poll with success. The new catch only turns more failures into "not yet".
- **Lock-order wording.** The two notes and the brief now describe the same mechanism in the same words: a state change rewrites the entries of `ix_tickets_equipment_state`, `ix_tickets_unit_state` and `ix_tickets_component_state`, so InnoDB takes shared locks on the machine, unit and component rows. The accepted deadlocks are the same in `tickets.py` and `equipment.py`. `masters.py`'s unit-guard comment does not list the deadlock, but CR1-02 asked only for the `tickets.py` and `equipment.py` notes.
- **The race test.** Its body is unchanged. Only the comment changed, and it now states the order that the test covers.
- **Impl report (scope A).** The Fix rounds section answers each finding, names the files and the test results, and says what it left out and why. No finding.
- **Manual checks.** `## Manual checks` is unchanged and still carries the important real-device check (row 9 of `device-checks.md`).

## Manual checks still needed (the user's)

These are unchanged from round 1:

- [ ] **Important.** The first release after the squash (row 9 of `docs/steps/device-checks.md`), run by KLA on production. Check that the deploy waits for `schema_ready` and passes. Check that Settings › Database shows the latest schema version. Check that the masters and the people with their units are still there. If the deploy fails, follow the rollback lines that `deploy.py` prints.
- The positive path of `build.bat` runs for the first time at that release.
