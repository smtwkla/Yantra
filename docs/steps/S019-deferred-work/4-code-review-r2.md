```
Step: S019 — Deferred work
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 22-10-2026
```

# S019 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** CR1-01 and CR1-02 are fixed, and the CR1-01 fix gives no user more access. This round adds 1 `nit`. The r1 nits CR1-03 to CR1-05 are still open, because the user did not ask for them.

Reviewed: only the fix round (impl report § Fix rounds, Round 1), against `4-code-review-r1.md` and the approved brief. The code is the working tree on `3df667c`, with S025, S019 and S020 uncommitted in the same files.

## Test results (my runs, 22-10-2026)

| Suite | Result |
|---|---|
| `tooling/run-tests.bat` | exit 0. Backend: 2003 passed. Frontend: 13 files, 110 tests passed. Deps: 42 passed. Tooling: 22 passed. |
| `tooling/run-e2e-tests.bat e2e/tickets-parts.spec.js e2e/tickets-work.spec.js` | exit 0. 66 passed in 2.7 min (22 tests × 3 projects), 0 failed. All five S019 tests pass on Pixel 7 Chromium, iPhone 14 WebKit and desktop Chromium. |

## Status of the round-1 findings

| Finding | Status | Check |
|---|---|---|
| CR1-01 (`minor`) | **Fixed** | `make_move` (`backend/tickets.py:953`) now passes a key function to `_lock_open_ticket`. If the locked state is one of the move's from-states, the function returns `spec.key_at(state)`, as before. If not, it returns the set `spec.keys`. `_lock_ticket` (`tickets.py:433-437`) accepts a single key, as before, or a set. For a set, any one key held at the ticket's site is enough; otherwise the answer is 403. A stale *Schedule* then reaches `_apply_move` and gets 409 "This ticket changed — reload". The new test `test_a_stale_schedule_by_a_technician_is_409_not_403` covers the finding's scenario: a technician schedules a ticket that is back in service. |
| CR1-02 (`minor`) | **Fixed** | `validate_move` (`backend/tickets_core.py:509`) now checks `isinstance(reason, str)` before the membership test. A list or an object gives 400 on `waiting_reason`, "Choose why it waits". It is tested in the core (`TestValidatePlanMoves::test_a_list_or_object_reason`) and through the route (`test_a_list_or_object_reason_is_400`), each with `["parts"]` and `{"a": 1}`. |

## The CR1-01 fix does not give more access

The orchestrator asked me to check this.

1. **The early 403 is unchanged.** `make_move` still refuses a user who holds none of the move's keys anywhere (`has_perm` over `spec.keys`).
2. **404 comes first, as before.** `_lock_ticket` locks the row and reads it through the access predicate before it checks any key.
3. **A fresh request still needs the state's own key.** When the locked state is a from-state, the function returns the same string as before, and `require_perm_at` checks it at the ticket's site. So *Schedule* from raised or acknowledged still needs `ticket:assign` there, and from in progress `ticket:work`. The existing tests `test_a_missing_key_is_403` and `test_keys_are_checked_at_the_tickets_site` still pass.
4. **The set branch cannot lead to a write.** The set is used only when the locked state is outside the move's from-states. In that case `_apply_move` always raises 409 before it writes an event or a state. So the set branch can only answer 403 or 409. It can never change the ticket.
5. **A user without the key at the ticket's site still gets 403.** Example: a user is a technician at another site and an operator at this one. The user holds neither `ticket:assign` nor `ticket:work` here, so `any(has_perm_at(…))` is false, and `require_perm_at(sorted(needed)[0], site)` raises 403 on `ticket:assign`.
6. **Moves with one key behave as before.** For them `spec.keys` is `{spec.key}`, so the set check is the same key at the same site.
7. **A closed ticket behaves as before.** The key check runs first, then `_lock_open_ticket` answers 409 "closed", as it did before S019.

The 409 tells a user who holds a ticket key at this site that the page is stale. That user can already read the ticket, so the 409 reveals nothing new.

## Findings

### CR2-01 — `nit` — The new 403 of the set branch has no test

`backend/tickets.py:436-437`

- **Problem.** No test reaches `elif not any(has_perm_at(k, row["site_id"]) for k in needed)` with a user who holds no key at the ticket's site. Every existing cross-site test moves a ticket from a valid from-state, so it takes the single-key branch. If someone deletes the `elif` refusal, every test still passes. Point 4 above shows that no write can follow. But such a user would get 409 "reload" instead of 403, against brief § 5.6's order (403 before 409).
- **Failure scenario.** A later edit to `_lock_ticket` drops or inverts the set check. A user with a ticket key only at another site then gets 409 instead of 403 on a stale page. No test catches the change.
- **Fix.** Add the case together with the open r1 nit CR1-04, which needs the same fixture. Use `user_at_sites` with the operator role at the ticket's site and the technician role at a second site. *Schedule* on a back-in-service ticket must then answer 403.

## Checked and found consistent

- **The early check and the route's 403 message.** Both are unchanged. `check_perm(spec.key)` still names the default key.
- **`_lock_ticket`'s other callers.** Labour, assignment, edit, re-grade, parts and documents pass a plain key string, so they take the single-key branch as before.
- **The docstrings.** The `_lock_ticket` docstring names the three forms of `key` and why the set exists (S019 CR1-01). The `make_move` docstring still holds.
- **CR1-02 and the other enum checks.** `intensity`, `machine_down` and the other enums test tuples or booleans, so they do not raise on an unhashable value. Only `WAITING_REASONS` is a dict, and it is now guarded.
- **Impl report (scope A).** The Fix rounds section answers each finding, names the files and tests, and says what it left out. No finding.
- **Manual checks.** `## Manual checks` is unchanged. It carries the nine `[auto]` checks, which pass in my run, and the important real-device check (the phone's date picker, row 10 of `device-checks.md`).

## Manual checks still needed (the user's)

These are unchanged from round 1:

- [ ] **Important.** On a phone (Android and iPhone), as an engineer: the date field of the Schedule dialog opens the phone's own date picker. After Save, the page shows the chosen date as DD-MM-YYYY (row 10 of `docs/steps/device-checks.md`).
- At gate B, show the user the times card's *Logistic delay* and *Administrative delay* lines (r1, view on departure 8).
