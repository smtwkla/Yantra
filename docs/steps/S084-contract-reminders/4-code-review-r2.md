```
Step: S084 — Contract reminders
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 31-10-2026
```

# S084 — code review, round 2

**Verdict: no `blocker` or `major` finding is open.** The fix round fixes CR1-01, CR1-02 and CR1-03. It brings
in one new nit (CR2-01). The four test files of the fix round pass (250 passed).

Re-read: the fix round's diff (`step_snapshot.py diff S084 --from-round 1`: `alerts.py`, `alerts_core.py`,
`email_core.py`, `equipment.py`, `tests/test_contract_alerts.py`), `alerts_core.contract_facts` and
`contract_text` in full, `email_core.contract_ending_email`, and the impl report's § Fix rounds › Round 1.

## Round 1 findings

| ID | Severity | Status | Checked |
|---|---|---|---|
| CR1-01 | nit | Fixed | `alerts.py` docstring states the scan's locks once: the plain candidate read, the rows `FOR UPDATE` in id order, the reason for the plain renewal read. `equipment.py` keeps one short sentence on the scan. |
| CR1-02 | nit | Fixed | `contract_facts` holds `ends_words`; `contract_text` and `contract_ending_email` read it; `_ends_words` and the second lower-casing are gone (`git grep` finds no other reader). The output is the same, and the text tests pass unchanged. |
| CR1-03 | nit | Fixed | `test_renewed_before_it_runs_sends_nothing` also asserts `email_sends(…) == []`. |

Red results: the report gives a reason for each missing red run. CR1-02 is a refactor with the same output.
CR1-03 adds an assertion that the code already satisfies. Both reasons hold.

## Nits

- **CR2-01** (nit) `backend/alerts_core.py:423`: after CR1-02, no code reads `status_label` from the facts any more
  (`git grep status_label -- backend` finds only its assignment). Drop the key, or keep it with a word on who reads it.

## Tests

- `YANTRA_TEST_RUN=s084cr2 tooling\run-backend-tests.bat tests/test_alerts_core.py tests/test_email_core.py
  tests/test_contract_alerts.py tests/test_closed_email.py`: PASSED, 250 passed (23 s).
- The fix round changed only backend files, all inside the backend suite. So the full `run-tests.bat` was not
  needed.
- Browser: none. The fix round changed no screen and no API that a screen uses.
- Schema docs: not run. The fix round changed no migration and no `docs/schema/` file.

## Manual checks

Unchanged from round 1. These checks are still open for the user:

- [ ] Row 61: the engineer's phone shows *Contract ends in 29 days · SMTW* without sound, and the tap opens the
  contract. After the To date moves to 10 days, *Contract ends in 9 days · SMTW* replaces it.
- [ ] Row 62: KLA's Outlook holds the reminder email on both mornings, not in junk. The email has no price, no
  call-out number, and a working link.

## Checked and found consistent

- `ends_words` comes from the same `contract_status` label as before. Every status gives a non-empty label, so
  `label[0]` is safe.
- `email_core` imports nothing new. The facts still carry only `contract:read_basic` fields (D8).
- The docs pass: "Docs updated: none" is right. Only comments, one facts key and a test changed.

## Feedback

- none
