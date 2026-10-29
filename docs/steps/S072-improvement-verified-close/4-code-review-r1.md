```
Step: S072 — States, timeline and the verified close
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 30-10-2026
```

# S072 — code review, round 1

**Verdict: no `blocker` or `major` finding is open.** One `minor` finding (a stale read in
*Not effective*) and four nits. The unit suites are green on my own run.

Reviewed: the step's diff (`step_snapshot.py diff S072`, parent the S071 snapshot), with
`backend/improvements.py` and `backend/improvements_core.py` read in full where the hunks needed
it; the brief with § 10 A1 and its Review log; the impl report with § 4 and § 5.

## Test runs

- **Unit suites** (`YANTRA_TEST_RUN=s072cr1 tooling\run-tests.bat`): backend **3774 passed**,
  frontend **322 passed**, tooling **185 passed**; ALL SUITES PASSED. This matches the coder's
  `s072c1` run.
- **Build:** not re-run. The frontend change is two plain lines (`improvementLabels.js`,
  `RemovedDocuments.vue`), and the coder's `npx vite build` is clean.
- **Browser:** no re-run. No finding of mine needs one. The coder's targeted run names the right
  specs: `improvements` (the state badges), `me` (*Mine*), `settings` (A1's Removed documents)
  and `screens`. The result was 48 passed, 1 skipped. The whole Normal suite ran once (282 passed,
  13 skipped), which covers the ticket detail's changed `improvements[].state`. § 8.4 asks for no
  new browser test, and § 8.5 for no device check.

## Findings

### CR1-01 (minor) — *Not effective* reads the old links from a stale snapshot

`backend/improvements.py:1320-1325`.

**The problem.** `next_counter` (`backend/db_helpers.py:85`) ends with a plain `SELECT
last_value`. That SELECT is the transaction's first consistent read, so it fixes the REPEATABLE
READ snapshot. The route then waits for (6b). After the lock, the plain `SELECT ticket_id FROM
improvement_tickets …` still reads that snapshot, so it misses a link committed while the route
waited. `_close`'s `UPDATE improvement_tickets SET open_link = NULL` is a current read and sees
the latest rows, so the two reads disagree. The brief's § 5.7 step 1 names the counter's SELECT
as the first plain read but does not draw this conclusion. The repo's self-check item (2) names
the trap: "a plain read made after an earlier plain read sees the old snapshot".

**How it fails.**
1. An engineer adds ticket X to IM-…-001, which is *Ready to verify* (add is allowed in that
   state). The add holds (6b).
2. At the same moment the manager taps *Did not work*. The route bumps the counter (the snapshot
   is fixed now), then waits on (6b).
3. The add commits. The close gets (6b) and reads the links without X.
4. `_close` sets X's new link to `open_link` NULL, and the follow-up is created without X.

X is then in no open improvement, and nothing on screen says it was left out. The opposite case
also happens: a ticket removed in that window is linked to the follow-up again. If that ticket
joined another open improvement in the meantime, the insert hits
`uq_improvement_tickets_open`, and the user gets a 500.

**The fix.** Read the old links with a locking read, which always sees the latest committed rows:
`SELECT ticket_id FROM improvement_tickets WHERE improvement_id = %s ORDER BY ticket_id FOR
UPDATE`. The route updates exactly these rows in `_close`, so the lock adds no new edge. Add one
sentence to the LOCK ORDER note (*Not effective*: "the old links by a locking read: the counter's
SELECT fixed the snapshot"). A test of the race itself needs two connections, so it is optional.
A code comment that gives the reason is enough.

## Nits

- **CR1-02** (nit) `backend/tests/test_improvement_close_api.py:453`: the *database down* test
  posts the note as `it_admin`, who does not hold `improvement:note`. Its 503 comes from the
  permission lookup, before the route runs. Post as an operator (or `maint_engineer`) instead, as
  `test_improvement_actions_api.py:201` does with its `eng` client.
- **CR1-03** (nit) `backend/tests/test_improvement_close_api.py:339`: the drop test cancels only
  one countermeasure. Add a second open one and a done one, and assert that both open ones are
  cancelled (D10, (6c) by id), each with its own line, and that the done one is unchanged.
- **CR1-04** (nit) `backend/improvements.py:1158`: `mark_action_done` still builds its time as
  `_now().replace(microsecond=0)`. Use the new `_stamp()`, as every other route now does.
- **CR1-05** (nit) `frontend/src/views/settings/RemovedDocuments.vue:11-14`: the file's header
  comment lists when *Restore* is disabled (a closed ticket, a cancelled countermeasure) but not
  A1's closed or dropped improvement. Add it to the list.

## Checked and found consistent

- **Migration v39** (`backend/local_db.py:1242-1328`), checked against § 4.1 statement by
  statement. The ENUM appends five values. The six columns, the unique key, the foreign key, the
  table and the four CHECKs each carry `IF NOT EXISTS`. `ADD UNIQUE KEY IF NOT EXISTS` runs on
  the dev image; `test_a_rerun_changes_nothing_and_doubles_no_line` re-runs the whole of v39
  after it, with the schema, every row and every line unchanged. The backfill has seven INSERTs,
  each guarded by "no line of this kind yet". The two UPDATEs are idempotent; the *watching*
  UPDATE follows `working_state` and `watch_start` (`n_open = 0`, `n_done >= 1`, the machine kind
  first). The CHECKs run last. Every row the backfill leaves passes them: *Analysing* and
  *Actions open* rows have `watch_from` NULL, and a *Watching* row has it set, because
  `n_done >= 1` makes `last_done` non-null. No row is closed. The test of a v38 database with
  rows covers A–D and the backfilled lines, with their times and writers. The CHECK test covers
  the refusals § 8.1 lists. No `_PRECONDITIONS` entry is needed: production stops at v35, the
  assumption in brief § 9.
- **Schema docs**: `docs/schema.md` has the "migration v39" line, the `improvements` row (the
  states, the six columns, the four CHECKs, the unique key), a new `improvement_events` row, the
  `improvement_whys` and `improvement_tickets` notes, and the Mermaid entity and its four links.
  `docs/schema.html` has the v39 meta line (44 tables, 71 links), the new table with all twelve
  columns, and `follow_up_of_id`.
- **The pure core**, actor × state × already in the target:
  - `working_state` follows § 5.1's four rules in order. Rule 2 keeps *Watching* only while no
    `WATCH_KINDS` countermeasure is open.
  - `watch_start` takes the machine kinds first, then any done countermeasure (D-4 is the brief's
    own definition).
  - `display_state` gives *Ready to verify* only for a stored `watching` row. `is_open` reads the
    stored state, and `is_open(READY_TO_VERIFY) is False` is pinned (BR1-03).
  - `_detail` computes `is_open` before it swaps in the display state. `tickets.py` keeps the
    start rule on `open_link`.
  - `close_error` covers every cell of § 5.1's table. A second close or a second drop waits for
    (6b), then gets 409 "This improvement is closed".
  - Dropping D-1's unused `action` argument is fine.
- **The watch count query** (`_figures`): one statement on the linked tickets' machines,
  not-a-fault left out, from `watch_days` before `watch_from` up to `end`. One events query
  follows (no N+1). `end` is now while the improvement is open, else `closed_at`. The core
  splits before and after at `watch_from`, caps after at `min(end, until)`, and returns the
  symptom figures as null when there is no symptom.
- **D8, every write in `improvements.py` writes its line in the same transaction**, after the
  change and under (6b). I listed all 17 write routes: start, edit, add and remove ticket, add,
  edit and remove why, root cause, add, change, done and cancel countermeasure, note, the two
  closes, drop. Each writes its line. **No route in `improvements.py` misses one.** The four
  countermeasure document routes in `documents.py` (upload, remove, restore, purge) write none.
  That is by design: brief § 5.6 and § 1 *Out of scope* keep photos off the timeline. Their
  `is_open` checks now refuse a closed improvement, and `TestReadOnly` covers the upload.
- **`_settle_state`** runs on exactly the five routes of § 5.1's table, after their write. Its
  plain read of the countermeasures is safe (every countermeasure write takes (6b) first). It
  stamps no `updated_*` (D16), and it skips an improvement that is not open.
- **`open_link` NULL** on all three closes, through one `_close`. A dropped improvement's ticket
  can start a new one (`test_the_ticket_page_and_start_rule_after_a_drop`), and so can a ticket
  of an effective close.
- ***Not effective*** takes the counter (6) before (6b), as the global order says. A refusal
  rolls back the counter bump (`test_a_refused_one_leaves_no_serial_gap`). The follow-up copies
  the title, problem, lead and `watch_days` and none of the analysis. Its links are inserted
  after `_close` has freed `uq_improvement_tickets_open`. Its lines are written by `_link_tickets`,
  the helper the start uses (BR1-05). It answers 201 with the follow-up's detail.
- **Drop** checks `improvement:edit` at the site (403), then open (409). It locks the open
  countermeasures `FOR UPDATE … ORDER BY id` in one statement ((6c) by id) and cancels each with
  `dropped_reason`, cut to 500, and its own line. It then drops the row, writing `from_state`,
  the display state. *Mine* no longer lists the cancelled countermeasures.
- **Permissions:** `improvement:verify` goes to `maint_engineer`; `improvement:note` goes to
  `maint_operator`, not `it_admin`. Both are in `SITE_SCOPED`, and their comments are in
  `config_rbac.py`. `test_role_matrix` and `test_improvement_verify_and_note` pin them. Every new
  route checks 404 through the read predicate, then the key at the site through
  `require_perm_at`, then the state 409. The actor always comes from `actor()`. All SQL is
  parameterised; only `_in()` placeholders are built from strings. IT admin can read but not
  note, verify or drop: the decorator refuses it (403).
- **The edit's new 409 on a closed improvement (D-6):** this is right. Brief § 1 item 7 says
  every write answers 409, and § 8.2 *Read-only* names S067's edit. S067 had no closed state to
  refuse. The report lists the change.
- **A1, judged against the closed-ticket photo pattern:** `restoreBlocked` already shows a
  disabled *Restore* with its reason for a closed ticket ("Closed tickets cannot be changed").
  A1 says "as it does for a closed ticket's photos", so the disabled button with "Closed
  improvements cannot be changed" is that pattern. The restore route's own 409 stays and is
  tested. D-11 records the choice.
- **Database down:** every new route goes through `get_db()` (CR1-02 concerns only how the test
  proves it).
- **Labels:** the seven state words are in `improvementLabels.js` (D13), with their test.
  `ACTION_KIND_LABELS` matches the frontend's `ACTION_KINDS`, and the core test asserts both.
- **LOCK ORDER notes** in `improvements.py` and the `equipment.py` bullet follow § 5.7.
- **Docs pass:**
  - `Plan.MD` § 3 has the two key rows and the paragraph, and § 4.2 has the states paragraph.
  - `Maintenance-Philosophy.md` § 12 has *Watch period* and *Verified close*.
  - `.claude/CLAUDE.md` is left to the orchestrator, with the proposed § SMTW-Review text in the
    report.
- **Scope:** nothing is built beyond the brief. The departures D-1 to D-11 are all in
  "Decisions taken".
- **Screen text** (scope B): the backend messages are short and plain, and each says what to do
  ("Say why it did not work", "The watch ends on DD-MM-YYYY. Verify after it.").

## Manual browser checks for the user

None in this step (brief § 8.5). The screens and their checks are S073's.

## Feedback

- waste: the step's diff also lists S071's `1-brief.md` and `4-code-review-r2.md`, files of
  another step that landed in this snapshot (`step_snapshot.py diff S072 --stat`, 2 of 24 files
  to rule out).
- hindrance: the 918-line brief passed the Read tool's 25 000-token cap, so it took two reads
  (`1-brief.md`, 2 reads).
- idea: the coder's self-check could add "a route whose first read is `next_counter` reads
  nothing it decides from with a plain SELECT afterwards" next to item (2): CR1-01 is that case,
  and the brief's own lock sequence did not show it.
