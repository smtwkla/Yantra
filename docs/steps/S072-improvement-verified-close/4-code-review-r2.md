```
Step: S072 — States, timeline and the verified close
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 30-10-2026
```

# S072 — code review, round 2

**Verdict: no `blocker` or `major` finding is open.** All five findings of round 1 are fixed.
The fix round brings in no new fault. S071's CR2-01, fixed in the same round, is also fixed.

Scope: the fix round's own diff (`step_snapshot.py diff S072 --from-round 1`). I re-read these
files: `backend/improvements.py` (the LOCK ORDER note, `close_not_effective`, `mark_action_done`,
and every `improvement_tickets` statement), `backend/tests/test_improvement_close_api.py` (the
changed tests), `backend/db_helpers.py` (`next_counter`),
`frontend/src/views/ImprovementDetailView.vue` (`load`, `cancelAction`, `closeStaleCancel`),
`frontend/e2e/improvements.spec.js` (the new S071 test), `RemovedDocuments.vue` (the comment), and
the two impl reports' fix-round sections.

## Test runs

- **Unit suites** (`YANTRA_TEST_RUN=s072cr2 tooling\run-tests.bat`): backend **3775 passed**,
  frontend **322 passed**, tooling **185 passed**; ALL SUITES PASSED. The backend count is round
  1's 3774 plus the new race test.
- **Build:** not re-run. The coder's `npx vite build` is clean, and the `.vue` change is a few
  lines of script.
- **Browser:** no re-run; no finding of mine needs one. The coder ran the right targeted specs:
  the new S071 test alone on `phone-chromium` (red, then green), then `improvements.spec.js` and
  `settings.spec.js` at Normal, 22 passed. `screens.spec.js` was not in that run. That is
  acceptable here: the round changed no route, no permission and no shared file.

## Round 1 findings

| ID | Status | Check |
|---|---|---|
| CR1-01 (minor) | Fixed | See below. |
| CR1-02 (nit) | Fixed | The 503 test posts as `operator_at_site`, a holder of `improvement:note`, on a real improvement. The `made` fixture runs before `db_down`, because it is listed first. No red run, with a reason given. |
| CR1-03 (nit) | Fixed | Three countermeasures: two open ones are cancelled with the reason, their two lines come in id order, and the done one is unchanged apart from its `can_*` flags. No red run, with a reason given (no fix to undo). |
| CR1-04 (nit) | Fixed | `mark_action_done` uses `_stamp()`. |
| CR1-05 (nit) | Fixed | The header comment names A1's closed or dropped improvement. |

**CR1-01 in detail.**
- **The fix:** `close_not_effective` reads the old links with `… ORDER BY ticket_id FOR UPDATE`,
  after (6b). A locking read sees the latest committed rows, so the follow-up gets the links that
  `_close`'s UPDATE frees. The code comment and the LOCK ORDER line give the reason.
- **The lock order stays acyclic.** Every write of `improvement_tickets` runs in
  `improvements.py` and takes (6b) of that improvement first: add (lines 768 and 839), remove
  (864), and `_close` (1291). `tickets.py:463` reads the table plain, and no other module touches
  it. So a link row of this improvement is only ever locked under its (6b), and the new read adds
  no edge between two row locks.
- **Gap locks (fact, not a finding).** Under REPEATABLE READ, the FOR UPDATE on the
  `improvement_id` index also locks the gap after the last link. A link insert for a neighbouring
  improvement id can wait for this route's commit. That wait cannot close a cycle: this route
  never asks for another improvement's (6b), and a start, the one writer that inserts links of a
  new id, takes the same serial counter (6) first, so it waits there before it reaches the insert.
- **The race test is sound.** It wraps `improvements.next_counter`. The real counter runs its
  plain `SELECT last_value`, which fixes the snapshot. Then a second connection (`db_rows`,
  autocommit) commits a link of a new ticket. The insert cannot block: the route holds only the
  counter row at that point. Without the fix, the plain read misses the link and the follow-up
  has one ticket; the report gives that red result (`assert [1] == [1, 2]`). With the fix, both
  tickets reach the follow-up. The test passes in my run.

## S071 CR2-01 (for S071's record)

**Fixed.** After a 409 with no field, `cancelAction` reloads and then calls
`closeStaleCancel(action.id)`. That clears `cancellingId` only when the ask still belongs to this
row and the reloaded row has no `can_change`, so an open row keeps its ask. `load()` catches its
own errors (`ImprovementDetailView.vue:70-76`), so the `.then` always runs. When a newer load wins
(`loadSeq`), `closeStaleCancel` reads the newest data, which is still right. The new browser test
plays the second phone through `markDoneByApi`, allows the one 409, and asserts what the user
sees: the row says *Done*, and the cancel ask and its field are gone. The report gives its red
result. The test is a logic test and is correctly left untagged.

## Nits

None.

## Checked and found consistent

- `close_not_effective`'s order is unchanged apart from the locking read: (6) counter, (6b), the
  refusals, the locked link read, `_close`, the line, the follow-up and its links. A refusal still
  rolls back the counter bump (`test_a_refused_one_leaves_no_serial_gap` passes).
- `_stamp()` gives the same value as the old `_now().replace(microsecond=0)`, so no test changes.
- Docs: "none" is right. The round changes no behaviour a doc describes, and the lock note lives
  in the code.
- Screen text: the round adds none.

## Manual browser checks for the user

None in this step (brief § 8.5). The screens and their checks are S073's.

## Feedback

- idea: `step_snapshot.py diff --from-round` could print, next to `--stat`, which files belong to
  another step's folder (here S071's report): a fix round that serves two steps is easier to
  scope at a glance (`diff S072 --from-round 1 --stat`, 1 of 7 files).
