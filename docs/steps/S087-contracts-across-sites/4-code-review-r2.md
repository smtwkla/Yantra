```
Step: S087 — Contracts across sites
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 31-10-2026
```

# S087 — code review, round 2 (verify)

**Verdict: no `blocker` or `major` finding is open.** CR1-01 is fixed, and the tests that showed it now pass.
CR1-02 is fixed. CR1-03 (nit) is still open: the docstring lines were re-wrapped, but five lines of
`backend/contracts.py` are still over 120 columns. The fix round's report says that no line is over 120.

Files re-read: `backend/tests/test_alerts.py` (the changed test), `backend/contracts.py` lines 1–90 (the
docstring), `backend/alerts.py` `enqueue_email` (the payload shape), and `backend/tests/test_contract_alerts.py`
`email_sends` (the same filter).

## Tests run

Run name `s087cr2`:

- `tooling/run-backend-tests.bat tests/test_contract_alerts.py::TestHandler tests/test_alerts.py::TestFanOut -n 0`:
  **21 passed**. In round 1, this order failed (`TestHandler` leaves `email_send` rows before `TestFanOut`).
- `tooling/run-backend-tests.bat tests/test_alerts.py tests/test_contract_alerts.py`: **92 passed**.
- No full run, because the fix round changed one test and a docstring. The coder's full run was green
  (backend 4467, frontend 409, tooling 231 passed).
- No browser run, because nothing in the frontend changed. Schema docs: no migration changed in this round.

## Status of the round-1 findings

| ID | Severity | Status |
|---|---|---|
| CR1-01 | blocker | **Fixed.** The test now looks only at the `email_send` rows whose payload `person_id` is this plant's manager or engineer. `enqueue_email` writes `person_id` as a JSON number, so `JSON_EXTRACT(payload, '$.person_id') IN (%s, %s)` matches real rows. `test_contract_alerts.email_sends` already uses the same filter. The test keeps its meaning: these two people have an address and get no email for a push-only kind. The red result is recorded (1 failed, 13 passed on the old assertion), and the change outside § 3 is named. |
| CR1-02 | nit | **Fixed.** The fix round states where the checks of `test_the_texts_name_the_machine_sites` live. |
| CR1-03 | nit | **Open.** See the nit below. |

## Nits

- **CR1-03** (nit) `backend/contracts.py:4`, `:62`, `:63`, `:72`, `:86`: the re-wrap moved the long text to the next
  line, so these lines are still 134, 140, 151, 172 and 131 columns long. Re-wrap each paragraph at 120 columns,
  and correct the fix round's statement "no line of the file is over 120 columns now".

## Manual browser checks for the user

None. The brief's § 8.5 lists no real-device check.

## Checked and found consistent

- The fix round's diff touches only `backend/tests/test_alerts.py` (one test) and the docstring of
  `backend/contracts.py`. No code line changed in `contracts.py`.
- The narrowed assertion does not hide a fault. It still fails if the fan-out queues an email for either person.
- The fix round's report names the red run, the green run, the full run and the decision outside § 3.

## Feedback

- idea: a line-width check in the backend suite, or in the step tool's diff, would have shown CR1-03 at once.
  The fix round could have checked it too. Here, one `awk` command found the five long lines.
