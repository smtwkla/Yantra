```
Step: S072 — States, timeline and the verified close
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 30-10-2026
```

Reviewed against: 32eb122 + uncommitted S066, S067, S068, S069 (being coded: v37 and the why-why routes are in the tree); S070 and S071 approved, not coded (v38 and `improvement_actions` read from their briefs).

**Verdict: no `blocker` or `major` finding. Five `minor` findings, nine nits.** Two minors (BR1-01, BR1-02) and D6 are judgement calls for KLA; none is defining: each can go either way without changing the design or a gate R answer. The step is coded after S071 as the brief says; the facts file `scratch/brief-facts-S072.md` was given and used.

The orchestrator's checklist, in short:

| Asked | Result |
|---|---|
| v39: ENUM, CHECKs, `ADD UNIQUE KEY IF NOT EXISTS`, backfill, no production rows | Holds. The grammar is a fact (below); the backfill's guards are idempotent; `1baae21` (tag v0.1.12, the newest tag) has no `improvement` text and its last migration is v35 |
| The state machine (D1, D2, D3, D11, D12) as actor × state × already there | Holds; two consequences KLA should see (BR1-01, BR1-02) and one coder trap (BR1-03) |
| The watch count (D4, D5) | Holds; `tickets.equipment_id` is always the machine (the table and `machine_and_component`); one bound claim is off (BR1-06) |
| D8, every write writes its line; which S069–S071 tests break | Holds; the brief names the grep the coder makes. No S069/S070 test file exists in the tree yet, so nothing more can be checked now |
| D6 `improvement:note`, D7 `improvement:verify`, `SITE_SCOPED`, the matrix | D6 is right for Q1.3 (a): `has_perm_at` grants a token role's key at every site (`backend/auth_utils.py:439-448`), so IT admin's `improvement:read` would pass a site check; only a key IT admin does not hold keeps it read-only. The departure is a key name, for KLA, not defining |
| The lock sequences against the notes | Hold: (6) → (6b) on *not effective* follows the global order; nothing takes (6b) then (6); (6c) in id order after (6b) matches S070; the event inserts add only shared FK locks after (6b) |
| § 9 Q1–Q3 | Q1 and Q3 as proposed. Q2: for KLA, not defining; the reviewer agrees with *none* (below) |

## Findings

### BR1-01 — minor — D3 restarts the watch for every kind, *Lesson* and *Spread* included (for KLA; not defining)

**Problem.** `working_state` and `watch_from = MAX(done_at)` treat the six kinds alike. A team that marks its *Corrective* done, then two weeks later adds "Lesson: one-point lesson on dust" and marks it done the next day, loses the two weeks: the state goes *Actions open* and the watch restarts from the lesson's `done_at`. A lesson or a spread to other machines changes nothing on the linked machines the watch counts.

**Why it matters.** On the floor, lessons and spreads are added late, after the fix is in. With a 90-day default the close moves out by weeks each time. The verifier can shorten the watch (D11), but the window is then measured from the wrong day.

**Options.**
- (a) Keep D3 as written and say this consequence in D3 and in S073's watch-card text ("from the last countermeasure done"). Simple; the team learns to add lessons before the last machine action is marked done. **Recommended** for simplicity, if KLA accepts the friction.
- (b) `watch_from` = `MAX(done_at)` of the kinds that act on the linked machines (`correction`, `corrective`, `preventive`, `design_out`; a constant `WATCH_KINDS` in the core), falling back to all kinds when none of those is done; *Watching* still needs every countermeasure done or cancelled. Truer to ISO 9001 § 10.2.1 (d) (the effectiveness of the action on the nonconformity), one more rule.

### BR1-02 — minor — A back-dated `done_at` can end the watch before it starts (for KLA; not defining)

**Problem.** S070 D6 lets `done_at` go back to the earliest linked ticket's time. A *Correction* recorded as done 100 days ago, with the root cause set today, makes `watch_from` 100 days back: the improvement is *Ready to verify* the moment it becomes *Watching*. The brief's own tests use this (§ 8.2, "S070 lets `done_at` go back"), but D11 says there is no second road around the watch.

**Why it matters.** It is a road around the watch, and the coder would otherwise meet it as a surprise in the tests. It is also defensible: if the correction really was in place for 100 days, 100 days of ticket data exist and the figures are honest; a false back-date shows on the timeline.

**Options.**
- (a) Accept it and say so in D11: the watch counts real days since the fix, also days before the record knew of it. **Recommended.**
- (b) `watch_from = max(MAX(done_at), the time the state became watching)`. Punishes an honest late entry (the engineer who records on Monday what was done three weeks ago).

### BR1-03 — minor — `is_open` and the display state: `ready_to_verify` is never stored, and the brief does not say what `is_open("ready_to_verify")` answers

**Problem.** `IMPROVEMENT_OPEN_STATES` stays the stored states (the list's SQL filter uses it, `backend/improvements.py:347`), so `is_open("ready_to_verify")` is False. Every answer's `state` is the display state (§ 5.2), while `_detail` computes `is_open` from the row (`backend/improvements.py:293`). A coder who passes the display state to `is_open`, `_require_open` or `removal_error`'s `open_now` gets a *Ready to verify* improvement that reads as closed: no `removable`, no `can_add_note`, 409 on every write.

**Why it matters.** The two values travel together in one detail; the trap is easy to fall into in `_detail`, in `tickets.py`'s `_improvement_fields` and in the S073 screens (which read `is_open` from the server today).

**Options.**
- (a) State the rule in § 5.1 and in the core's docstring: `is_open` and the SQL filter take the **stored** state only; the display state is for output; add a core test `is_open(READY_TO_VERIFY) is False` with that comment, and have `_detail` compute `is_open` before it replaces `state`. **Recommended.**
- (b) Make `is_open` also true for `READY_TO_VERIFY` (an open improvement is open under either name) and keep the SQL filter on `IMPROVEMENT_OPEN_STATES`. Safer for callers, one more branch to explain.

### BR1-04 — minor — `edit_lines` is a new function with the name and a different contract of `tickets_core.edit_lines`

**Problem.** § 3 lists `edit_lines` among the remark builders new in `improvements_core`. `tickets_core.edit_lines(old, new, labels)` exists (`backend/tickets_core.py:735`) and returns one string of `Label: old → new` lines. § 5.6 wants `remark` = the new values and `earlier` = the old values, two strings. Same name, two contracts, in two modules the shell imports from.

**Why it matters.** One term for one thing (CLAUDE-COMMON § Writing style 4); DRY. The coder has to pick, and the choice shows on every edit line of the timeline.

**Options.**
- (a) Reuse `tickets_core.edit_lines` as it is: `remark` = "Title: old → new" per changed field, `earlier` NULL for edits (the old value is already in the line). One function, the ticket timeline's look, nothing new. **Recommended.**
- (b) Keep two strings, but name the new builder `edit_remark_and_earlier` (or similar) and say why it differs. For the lead, the shell must read the old lead's name as well as the new one (two plain `people` reads); say so.

### BR1-05 — minor — The first ticket's line has three shapes: a start, a backfilled record, a follow-up

**Problem.** § 5.6: a start writes `started` with `ticket_id` and no `ticket_linked`; the backfill writes `started` with no ticket and one `ticket_linked` per `improvement_tickets` row, the first ticket included; a follow-up writes `started` with a remark and a `ticket_linked` per ticket. S073's timeline (its § 5.6) shows the serial on the `started` row only for new records, and two rows for the same fact on backfilled and follow-up records.

**Why it matters.** The same kind of record reads differently depending on when it was made; the register (R05.10) and anyone comparing records will notice. It costs nothing to pick one shape now; it costs a data fix later.

**Options.**
- (a) Always `started` (no ticket) followed by one `ticket_linked` per ticket, also on a start: the backfill's shape, one rule for all three paths. **Recommended.**
- (b) Always `started` with `ticket_id` for the first ticket and `ticket_linked` for the others; the backfill then skips the earliest link of each improvement (one more statement with a `MIN(created_at)` join).

## Nits

- **BR1-06** (nit) § 5.4 *Bounds*: "at most 2 × 365 days of tickets" is not true: the repeats and the `after` query run to `end` (now), which can lie long after `watch_until` on an improvement left unverified. Say "watch_days before `watch_from`, and from `watch_from` to `end`"; the bound is still a handful of machines.
- **BR1-07** (nit) § 4.1 backfill: the `why_added` remark drops the evidence that `why_line` includes. Use `CONCAT_WS` with `' Evidence: '` when `evidence` is not NULL, or say the omission is deliberate.
- **BR1-08** (nit) § 3 Docs and D8: the SMTW-Review point reads "writes its timeline line in its own transaction". "Its own" can be read as a separate transaction. Write "in the same transaction as the change".
- **BR1-09** (nit) § 2: D5 leans on ISO 14224 (the failure mode as the symptom the watch counts) and § 5.4 on EN 13306 (time to restoration as the downtime figure), but § 2 names neither. One line each, as S067 § 2 has them.
- **BR1-10** (nit) § 6: say what `watch.ended` is before the watch starts (`false`, with `from` and `until` null), so S073 and the tests agree.
- **BR1-11** (nit) § 5.6: the close and drop lines name `from_state`; say `to_state` too (`closed_effective`, `closed_not_effective`, `dropped`), so a `state_changed`-style reader works for every state line.
- **BR1-12** (nit) § 4.1 *Rollback* and *No `_PRECONDITIONS` entry*: "v36–v39 ship together" is a release constraint on KLA, not a property of the migration. Move it to § 9 as an assumption, and keep the sentence that v39 is safe on rows anyway (the backfill and the CHECKs were written for rows).
- **BR1-13** (nit) § 3: the line anchors of `backend/improvements.py` are from before S069's routes went in (`_IMPROVEMENT_COLUMNS` is at `:122` now, not `:98`; `_LOCK_IMPROVEMENT` `:132`; `_now` `:149`; `_events_by_ticket` `:208`; `_linked_tickets` `:221`; `_require_open` `:196`). The brief says they may move; refresh them when the brief is approved, or drop the numbers for that file.
- **BR1-14** (nit) § 5.4: "`closed_at` for a closed one" — say "closed or dropped" (a drop from *Watching* has `watch_from` and `closed_at`), so the coder does not special-case `dropped`.

## § 9, for the gate

- **Q1** (whys and root cause editable in every open state): agree with the proposal. Each change has a line; the verifier sees a late change. Not defining.
- **Q2** (undo a done countermeasure): **for KLA; not defining.** The reviewer agrees with *none in R05.4*: S071's *Mark done* is a dialog with a required text, not a stray tap, so a wrong *done* is rare; a new countermeasure records the correction truthfully and D3 restarts the watch. An *Undo done* (b) would also have to reverse a settled *Watching*, with its own line and lock sequence: a step of its own if ever wanted.
- **Q3** (correct a note): agree with the proposal.
- **D6** (a fifth key, beyond the roadmap's list): **for KLA; not defining.** It is the right mechanism (see the table above); the alternative "has a Team record" hides a rule outside `config_rbac.py`.

## Checked and found consistent

- **Production has no improvement rows.** `git tag --sort=-v:refname` lists v0.1.12 as the newest tag; `git show 1baae21:backend/local_db.py` has no "improvement" and ends at v35. v36–v39 reach production together. No `_PRECONDITIONS` entry is needed (nit BR1-12 on the wording only).
- **`ADD UNIQUE KEY IF NOT EXISTS`** (fact, from MariaDB's `ALTER TABLE` grammar: `ADD [CONSTRAINT [symbol]] UNIQUE [INDEX|KEY] [IF NOT EXISTS] [index_name] (…)`, MariaDB 10.0.2 and later; the dev image is `mariadb:11.4`, `tooling/dev/docker-compose.dev.yml:12`). The *to verify* label can go; § 8.1's re-run test still proves it. `FOREIGN KEY IF NOT EXISTS` has v35 and v37 as precedents, `ADD CONSTRAINT IF NOT EXISTS … CHECK` v21 and v28; `MODIFY COLUMN … ENUM(…)` appending values is a metadata change, as v30 and v33 did.
- **The CHECKs hold for every row the backfill leaves**: `analysing` / `actions_open` rows keep `watch_from` NULL; the `watching` UPDATE sets `watch_from` in the same statement; no row is closed. The order (ENUM, columns, backfill, the two UPDATEs, then the CHECKs) is right.
- **The backfill is idempotent**: one `INSERT … SELECT` per kind, atomic, each guarded by "no line of this kind"; the two state UPDATEs re-run to the same result; no route writes events before v39 is recorded (`ensure_schema` applies the whole list first).
- **The state table** (§ 5.1) is complete for actor × state × already-there: every cell has a status and a message; a double tap on *Close* or *Drop* waits for (6b) and gets 409 `IMPROVEMENT_CLOSED`; the add-countermeasure cell during *Ready to verify* follows D3.
- **D1**: the list filter is unchanged (`i.state IN (open states)` on the stored value); `display_state` runs per row after the fetch; `_IMPROVEMENT_COLUMNS` and `_IMPROVEMENT_LINKS` gain the two columns, and `_readable_improvement_links` (`backend/tickets.py:476-481`) uses `_IMPROVEMENT_LINKS`, so the ticket page's line follows.
- **The watch query**: `tickets.equipment_id` is the machine (`component_id` is a separate column, `backend/local_db.py:371-372`; `machine_and_component`, `backend/tickets_core.py:245`); `ix_tickets_equipment_state` has `equipment_id` as its prefix; `not_a_fault = 0` matches S067 D7.
- **Locks**: the global order gains no level; *not effective* takes (6) first (as a start) and nothing holds (6b) and then takes (6); the drop's (6c) in id order after (6b) matches S070 § 5.6; the event inserts take only shared FK locks on rows already held or on tickets (7) after (6b), the edge *Add ticket* already has; ticket writes never touch improvement rows (`backend/tickets.py:22-34`). The *not effective* link inserts cannot race an *add* to another improvement: the add's plain check sees either the old open link or the new one, and the unique key catches the rest with S067's 409.
- **Permissions**: `maint_manager` includes `maint_engineer` (`config_rbac.py:83`), so `improvement:verify` on the engineer reaches the manager; the `test_role_matrix` rows the brief lists are the right ones; IT admin's row unchanged; `test_improvement_keys` (`backend/tests/test_rbac.py:98-105`) and `test_auth.py:388` as stated.
- **Existing tests**: `test_improvements_core.py:89` pins `("analysing",)` and breaks as the brief says; `test_improvements_api.py:514` pins only the list item's keys, `:614` asserts `"analysing"` on an improvement with no root cause, `:519` asserts `state=closed` empty: all stay true. `conftest._TABLES` is emptied with `FOREIGN_KEY_CHECKS = 0` (`:192`), so the place of `improvement_events` in the tuple does not matter.
- **`tickets_core.validate_note`** (`:513`) and `_add_event` (`backend/tickets.py:908`) are the patterns the brief cites; `ticket_events.remark` is `VARCHAR(1000)`, so `TEXT` here is a stated, reasoned difference.
- **Standards**: ISO 9001 § 10.2.1 (d) is the review of effectiveness, § 10.2.2 the records, § 7.5.3 the control of documented information; ISO 27001 A.5.3 is segregation of duties and A.5.15 access control (2022 numbering); the departures (self-verification; no earlier text before v39) are recorded. Each is explained in plain words, as the settings ask. ISO 55001 § 10 and SMRP 3.5.1 are marked *to verify*, rightly.
- **UI text** (scope B): the messages of § 5.1 and § 5.3 say what is wrong and what to do, no codes or field names.
- **Track full**, the full template present; no device checks, rightly (no screen); the whole-suite browser run once at the end is right because the ticket detail's `state` and every improvement write change.
- **Layers**: the rules (`working_state`, `display_state`, `watch_until`, `close_error`, `watch_figures`, the validators, the remark builders) are in the core; the shell locks, reads and writes; `tickets.py` imports only the core, as today.

## Feedback

- waste: the facts file was made before S069's routes landed in `backend/improvements.py` (it says 444 lines; the tree has 624), so every line anchor in the brief for that file had to be re-found by hand (about 5 minutes; BR1-13).
- hindrance: S070 and S071 are approved but not coded, so D8's claim about their tests and the v39 FK on `improvement_actions` could be checked only against their briefs; the re-check belongs in the stale-brief check before `/step implement S072`, and the brief could say so in § 9.
- idea: `brief_facts.py` could print the working-tree line of each `file:line` anchor's symbol (it already finds the definitions), so a brief written while another step is coded gets its anchors refreshed in one run.
