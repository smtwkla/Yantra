```
Step: S072 — States, timeline and the verified close
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 30-10-2026
Track: full
Baseline: 32eb122 + uncommitted S066, S067, S068 (gate B), S069 (being coded); S070, S071 coded before S072
Status: Approved 30-10-2026 by KLA (delegated: R05 gate R, "start coding unless a defining question")
From: R05.4 (first half: the states, the timeline, the watch and the close in the backend; the screens are S073)
```

# S072 — States, timeline and the verified close

## 1. What will be built

R05.1–R05.3 give an improvement its problem and tickets (S067, S068), its why-why and root cause
(S069) and its countermeasures (S070, S071). Every improvement stays *Analysing* and open for good.
**R05.4 closes the loop**: the record moves through its states, keeps a timeline of who did what,
watches whether the failure comes back, and closes only when someone checks that the fix worked
(ISO 9001 § 10.2.1 (d), § 2). R05.4 is an L item with a backend and screens that can ship apart, so
it is **split at the API**, as R05.1 and R05.3 were (§ 9, *The split*). **This step builds the
backend half.** **S073** (`docs/steps/S073-verified-close-screens/1-brief.md`) builds the screens
on § 6, as written here.

1. **The states** (R05.4): *Analysing* → *Actions open* (the root cause is set) → *Watching* (no
   countermeasure open and at least one done; a *Lesson* or *Spread* added later does not end it) → *Ready to verify* (the watch has ended) →
   *Closed: it worked* or *Closed: did not work* (`closed_effective`, `closed_not_effective`; D13); *Dropped*, with a reason, from any open state.
   The first three move by themselves when the data changes (§ 5.1); *Ready to verify* is
   computed from the clock (D1); the closes are decisions.
2. **The watch** (Q4.1 a): 90 days by default from the last countermeasure done, set per
   improvement from 30 to 365 days. "The last countermeasure done" is the last one that acts on
   the machines (*Correction*, *Corrective*, *Preventive*, *Design-out*; D3). Yantra counts, on the linked tickets' machines, the breakdowns,
   the breakdowns with the same symptom (failure mode) and the downtime in the watch, against the
   same number of days before it; and lists every ticket with that symptom since the watch began
   (mock-up `docs/roadmap/R05-mockups/05-verify.html`). A repeat warns; the watch goes on (Q4.3 a).
   Computed, never stored.
3. ***Close as effective*** and ***Not effective — analyse again*** (a remark is needed; on screen "Close: it worked" and "Did not work — analyse again", S073) by an
   engineer or manager of the site, the lead too, recorded as such (Q4.2 a; new key
   `improvement:verify`). *Not effective* starts a new improvement linked to the old one, with the
   same tickets (Q1.4 a).
4. ***Drop*** an open improvement with a reason (engineers and managers). Its open countermeasures
   are cancelled with it (D10).
5. **The timeline** (table `improvement_events`, as `ticket_events`): started, ticket linked and
   removed, why added, changed and removed, root cause set and changed, countermeasure added,
   changed, done and cancelled, the edits of title, problem, lead and watch, notes, state changes,
   the closes. **Every write of S067–S071 writes its line from now on** (D8). Migration v39
   backfills lines from the rows that exist (§ 4.1).
6. **Notes** on the timeline for every reader at the site, IT admin excepted (Q1.3 a; new key
   `improvement:note`, D6).
7. **A closed improvement is read-only**: every write answers 409 (S067's `_require_open`, now
   with the closed states).
8. **The ticket page's line** "Analysed in IM-… · <state>" shows the new states (S067 § 5.3; the
   state names are computed the same way).

**After S072 and S073:** the full loop of ISO 9001 § 10.2 on IM-2026-10-001. After its watch, the
manager sees that *Won't start* did not come back on HP003 and closes it as effective.

### Out of scope

- **Every screen** (S073): the state badges' places, the watch card, the verify and drop dialogs,
  the timeline card, the note dialog, the watch field, the browser tests. This step adds only the
  state words to `improvementLabels.js` (D13).
- Alerts: *Ready to verify*, *countermeasure overdue*, *given to you* (R05.5). R05.5 also brings
  the daily task (D1).
- Correcting a note (as S027 does for tickets), and photos on the timeline: a photo of a
  countermeasure is in its documents (S070), not a timeline line.
- Reopening a closed or dropped improvement; undoing a done countermeasure (S070 § 9 Q1 left undo
  to R05.4: this step adds none, § 9 Q2).
- Copying the whys, root cause or countermeasures into a follow-up (D9); adding the watch's
  repeat tickets to it by itself.
- Per-machine figures when an improvement has tickets on several machines (one total, § 5.4).
- MTBF itself (SMRP; phase 5 reports): only its raw data, failures and downtime.
- The register (R05.10), lessons (R05.6).

## 2. Standards and practice

- **ISO 9001:2015 § 10.2.1 (d)** (nonconformity and corrective action). In plain words: after
  acting on a failure's cause, review whether the action worked. The watch and the verified close
  are that review: Yantra counts the facts, a person decides (Q4.1 a). Clause letters as Plan § 1
  cites them; the next edition's numbers are *to verify* (R05 § Standards).
- **ISO 9001 § 10.2.2** (records). In plain words: keep a record of the failure, the actions and
  their results. The close keeps who verified, when, the result and the remark; a *not effective*
  close links its follow-up.
- **ISO 9001 § 7.5.3** (control of documented information). In plain words: records are kept,
  protected from change, and show who did what and when. The timeline gives every change of the
  record a line with who and when, and keeps the replaced text of an edit (`earlier`). A closed
  improvement is read-only. **This ends the departure S067 § 2 recorded** (no history in R05.1–R05.3).
  **What stays a departure:** the edits made before v39 have no earlier text; the backfill writes
  only what the rows show (§ 4.1).
- **ISO 55001 § 10** (nonconformity, corrective action, continual improvement; numbers differ
  between the 2014 and 2024 editions: *to verify*). In plain words: the asset-management system
  corrects what went wrong and checks that the correction held. The same loop as ISO 9001 § 10.2.
- **SMRP — MTBF** (metric 3.5.1, as Plan § 4.5 cites it; *to verify*). In plain words: the mean
  time between failures rises when a root cause is removed. This step shows its raw data only:
  breakdowns and downtime before and after the watch began. The metric waits for the phase 5
  reports.
- **ISO 14224 — failure mode** (as S016 and S067 § 2 cite it; clause numbers *to verify*). In
  plain words: the failure mode is how a failure shows itself, the symptom on the ticket. The
  watch counts "the same symptom" as the same failure mode on the linked machines (D5).
- **EN 13306 — time to restoration** (term numbers *to verify*). In plain words: the time an item
  is down until it works again. The watch's downtime is that time, computed as the ticket page
  computes it (`ticket_times`), never stored.
- **TPM — focused improvement**. In plain words: a loss counts as removed only when it stays away.
  The watch is long by default (90 days) because dust builds up over months (Q4.1 a).
- **ISO 27001 A.5.3** (segregation of duties). In plain words: one person should not both do and
  approve the same work where the risk calls for it. **Departure (recorded, Q4.2 a):** the lead
  may verify their own improvement, as an engineer closes a ticket they worked and R03 Q5.2 lets
  PM jobs be self-verified. The plant has few engineers. The detail says when the verifier was the
  lead (`closed.by_lead`), so the review (R05.10) can see it.
- **ISO 27001 A.5.15** (access control). In plain words: give each person only the rights their
  work needs. Notes for the floor, decisions for engineers and managers, IT admin reads only.

## 3. Where

S072 is coded after S071. Files marked **(S067)** exist in the working tree now; S069 and S070
change some of them first, so line numbers in `backend/improvements.py`,
`backend/improvements_core.py`, `backend/local_db.py` and `backend/tests/conftest.py` are the
working tree's on 30-10-2026 (S069 is being coded) and may move; function and constant names are the anchors. Names new in
S069 or S070 are marked so.

### Backend

- `backend/local_db.py`: migration **v39** (§ 4.1). v36 starts at `backend/local_db.py:1104`; S069
  adds v37, S070 v38. No `_PRECONDITIONS` entry (§ 4.1, evidence there).
- `backend/improvements_core.py` **(S067)**: the states and `IMPROVEMENT_OPEN_STATES` widened
  (`backend/improvements_core.py:18-21` today); `working_state`, `display_state`, `watch_until`,
  `watch_start`, `WATCH_KINDS`, `close_error`, `watch_figures`, `validate_note`, `validate_close`,
  `validate_improvement` gains `watch_days`; the event names and the remark builders (`why_line`,
  `root_cause_line`, `action_line`; an edit's lines reuse `tickets_core.edit_lines`,
  `backend/tickets_core.py:735`); `ACTION_KIND_LABELS` (§ 5.6); the keys `VERIFY_KEY`, `NOTE_KEY`.
- `backend/improvements.py` **(S067)**: `_add_event`; every write route of S067, S069 and S070
  writes its line (§ 5.6) and calls `_settle_state` where § 5.1 says; the routes of § 6 (notes,
  the two closes, drop); the detail gains § 6's fields; `_IMPROVEMENT_COLUMNS` and
  `_LOCK_IMPROVEMENT` gain `watch_days`, `watch_from`, the close columns and `follow_up_of_id`
  (line numbers left out: S069 is moving this file, BR1-13); the list's `state` is the display state; the LOCK ORDER
  note (§ 5.7).
- `backend/tickets.py`: `_IMPROVEMENT_LINKS` (`backend/tickets.py:457`) also selects
  `i.watch_from, i.watch_days`, and `_improvement_fields` (`:437`) answers `display_state(…)` as
  `state` (§ 5.2). `improvement_links` (`:461`) and the start rule are unchanged: `open_link` is
  NULL after a close, so a ticket of a closed improvement can start a new one (S067 D4).
- `backend/config_rbac.py`: `improvement:verify` and `improvement:note` in `PERMISSIONS`
  (`backend/config_rbac.py:132-133`) and in `SITE_SCOPED` (`:188-190`), with their comments (§ 5.8).
- `backend/equipment.py`: docstring only. The improvements.py bullet of the global LOCK ORDER
  (`backend/equipment.py:103`) gains the close routes: (6) the counter → (6b) on *not effective*.

### Frontend

- `frontend/src/utils/improvementLabels.js` **(S068)**: `IMPROVEMENT_STATE_LABELS`
  (`frontend/src/utils/improvementLabels.js:4`) gains the six new states, in plain words (D13):
  `actions_open` "Actions open", `watching` "Watching", `ready_to_verify` "Ready to verify",
  `closed_effective` "Closed: it worked", `closed_not_effective` "Closed: did not work",
  `dropped` "Dropped". Nothing else; the screens are S073's.

### Tests

- `backend/tests/test_migration_v39.py` (new), on the pattern of `test_migration_v36.py`
  (`VERSIONS` slices its own range); v36–v38's tests slice theirs and are untouched.
- `backend/tests/test_improvements_core.py` **(S067)**: the new pure functions (§ 8.2);
  `TestStates.test_only_analysing_and_it_is_open` (`backend/tests/test_improvements_core.py:89`)
  breaks (it pins `IMPROVEMENT_OPEN_STATES == ("analysing",)`) and is rewritten for the three open
  states.
- `backend/tests/test_improvement_close_api.py` (new): states, watch, the closes, drop, the
  follow-up, read-only (§ 8.2).
- `backend/tests/test_improvement_timeline_api.py` (new): the line of every write, notes, the
  timeline's order and names (§ 8.2).
- `backend/tests/test_improvements_api.py` **(S067)**: unchanged; runs again (§ 8.3).
- `backend/tests/test_rbac.py`: `test_role_matrix` (`backend/tests/test_rbac.py:193-209`) and
  `test_improvement_keys` (`:98-105`) gain the two keys (§ 8.3).
- `backend/tests/conftest.py`: `improvement_events` joins `_TABLES`
  (`backend/tests/conftest.py:162`), before `improvement_tickets`.
- `frontend/tests/improvementLabels.test.js` **(S068)**: the seven state words.

### Docs (housekeeping, by the coder)

- `docs/schema.md` and `docs/schema.html`: `improvement_events`; the `improvements` columns, the
  ENUM and the CHECKs of v39; the Mermaid overview (improvement_events → improvements, tickets,
  improvement_actions; improvements → improvements, the follow-up); the "migration v39" line.
- `docs/Plan.MD`: § 3, the key table gains `improvement:verify` and `improvement:note` (rows as
  § 5.8) and a paragraph; § 4.2 or the R05 row of § 1, one line on the states and the verified
  close (S072). The screens (§ 6) are S073's.
- `docs/Maintenance-Philosophy.md` § 12 Glossary: rows *Watch period* and *Verified close*, one
  plain sentence each.
- `.claude/CLAUDE.md` § SMTW-Review: the point of § 7 D8 ("every improvements.py write writes its
  timeline line in the same transaction as the change"); § Step workflow, *Self-check, repo items* (2) needs no
  change (it names `improvements.py`'s note already after S067).

**File count:** 15 code and test files (backend 6 code, 7 tests; frontend 1 code, 1 test), 4 docs.

## 4. Data model

### 4.1 Migration v39

```sql
-- R05.4 (S072): the states of an improvement, the watch, the close and the follow-up.
-- Appended ENUM values change no row.  ready_to_verify is computed, never stored (D1).
ALTER TABLE improvements MODIFY COLUMN state
    ENUM('analysing','actions_open','watching','closed_effective','closed_not_effective','dropped')
    NOT NULL DEFAULT 'analysing';
ALTER TABLE improvements
    ADD COLUMN IF NOT EXISTS watch_days      SMALLINT      NOT NULL DEFAULT 90 AFTER contributing_causes,
    ADD COLUMN IF NOT EXISTS watch_from      DATETIME      NULL AFTER watch_days,
    ADD COLUMN IF NOT EXISTS closed_at       DATETIME      NULL AFTER watch_from,
    ADD COLUMN IF NOT EXISTS closed_by       VARCHAR(100)  NULL AFTER closed_at,
    ADD COLUMN IF NOT EXISTS close_remark    VARCHAR(1000) NULL AFTER closed_by,
    ADD COLUMN IF NOT EXISTS follow_up_of_id INT           NULL AFTER close_remark,
    ADD UNIQUE KEY IF NOT EXISTS uq_improvements_follow_up (follow_up_of_id),
    ADD CONSTRAINT fk_improvements_follow_up
        FOREIGN KEY IF NOT EXISTS (follow_up_of_id) REFERENCES improvements (id);

-- The timeline (as ticket_events): one line per change of the record, who and when.  remark is
-- the new text, earlier the text it replaced (ISO 9001 § 7.5.3).  ticket_id and action_id name
-- the ticket or countermeasure a line is about.  No why_id: a removed why's row is deleted
-- (S069 D6), so a why line carries its text.
CREATE TABLE IF NOT EXISTS improvement_events (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    improvement_id  INT NOT NULL,
    event           VARCHAR(30) NOT NULL,
    occurred_at     DATETIME NOT NULL,
    from_state      VARCHAR(30) NULL,
    to_state        VARCHAR(30) NULL,
    ticket_id       INT NULL,
    action_id       INT NULL,
    remark          TEXT NULL,
    earlier         TEXT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by      VARCHAR(100) NOT NULL,
    KEY ix_improvement_events_improvement (improvement_id, occurred_at, id),
    CONSTRAINT fk_improvement_events_improvement FOREIGN KEY (improvement_id) REFERENCES improvements (id),
    CONSTRAINT fk_improvement_events_ticket FOREIGN KEY (ticket_id) REFERENCES tickets (id),
    CONSTRAINT fk_improvement_events_action FOREIGN KEY (action_id) REFERENCES improvement_actions (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- The backfill (R05.4: "an event backfills R05.1–R05.3's records"): one statement per kind,
-- each guarded by "no line of this kind yet", so a half-applied v39 re-runs without doubles
-- (no route writes events before v39 is complete: the app serves only a migrated database).
-- (statements, § 4.1 below)

-- The states the rows already earn (§ 5.1), in two idempotent UPDATEs (below), then the CHECKs.
ALTER TABLE improvements ADD CONSTRAINT IF NOT EXISTS chk_improvements_watch_days
    CHECK (watch_days BETWEEN 30 AND 365);
ALTER TABLE improvements ADD CONSTRAINT IF NOT EXISTS chk_improvements_watch_from
    CHECK ((state IN ('analysing','actions_open') AND watch_from IS NULL)
           OR (state IN ('watching','closed_effective','closed_not_effective') AND watch_from IS NOT NULL)
           OR state = 'dropped');
ALTER TABLE improvements ADD CONSTRAINT IF NOT EXISTS chk_improvements_closed
    CHECK ((state IN ('closed_effective','closed_not_effective','dropped'))
           = (closed_at IS NOT NULL AND closed_by IS NOT NULL));
ALTER TABLE improvements ADD CONSTRAINT IF NOT EXISTS chk_improvements_close_remark
    CHECK (state NOT IN ('closed_not_effective','dropped') OR close_remark IS NOT NULL);
```

**The backfill statements**, in this order, each `INSERT INTO improvement_events (improvement_id,
event, occurred_at, ticket_id, action_id, remark, created_by) SELECT … WHERE NOT EXISTS (SELECT 1
FROM improvement_events WHERE event = '<kind>')`:

| Kind | From | `occurred_at` | `created_by` | `remark` |
|---|---|---|---|---|
| `started` | each `improvements` row | `created_at` | `created_by` | NULL |
| `ticket_linked` | each `improvement_tickets` row | its `created_at` | its `created_by` | NULL (`ticket_id` set) |
| `why_added` | each `improvement_whys` row (S069) | its `created_at` | its `created_by` | `CONCAT_WS(' ', CONCAT(position, '.'), question, CONCAT('Because: ', answer), CONCAT('Evidence: ', evidence))`, `why_line`'s shape (`CONCAT` is NULL for a NULL evidence, and `CONCAT_WS` skips it) |
| `root_cause_set` | each `improvements` row with `root_cause_id` (S069) | `COALESCE(updated_at, created_at)` | `COALESCE(updated_by, created_by)` | `CONCAT(fc.code, ' ', fc.label, ': ', root_cause)` |
| `action_added` | each `improvement_actions` row (S070) | its `created_at` | its `created_by` | `text` (`action_id` set) |
| `action_done` | each done one | `done_at` | `done_by` | `done_text` |
| `action_cancelled` | each cancelled one | `cancelled_at` | `cancelled_by` | `cancel_reason` |

- **The times are what the rows show.** The root cause's time is approximate: S069's
  `update_row` stamps `updated_at` for every edit of the row. Edits made before v39 have no line
  and no earlier text (§ 2, the departure that stays).
- **The states** the rows earn, after the backfill: `UPDATE improvements SET state = 'actions_open'
  WHERE state = 'analysing' AND root_cause_id IS NOT NULL`; then `UPDATE improvements i JOIN
  (SELECT improvement_id, MAX(done_at) AS last_done, SUM(state = 'open') AS n_open,
  SUM(state = 'done') AS n_done, MAX(CASE WHEN state = 'done' AND kind IN ('correction',
  'corrective','preventive','design_out') THEN done_at END) AS last_machine_done FROM
  improvement_actions GROUP BY improvement_id) a ON a.improvement_id = i.id SET i.state =
  'watching', i.watch_from = COALESCE(a.last_machine_done, a.last_done) WHERE i.state =
  'actions_open' AND a.n_open = 0 AND a.n_done >= 1` (`watch_start`'s rule, § 5.1). Both are idempotent. They write no
  `state_changed` line (no actor; the backfilled lines show why).
- **No `_PRECONDITIONS` entry.** Production holds no improvement row: the released v0.1.12
  (`1baae21`) stops at v35 (`git show 1baae21:backend/local_db.py` lists v30–v35 and no
  "improvement"), so v36–v39 reach production together on empty tables. The ENUM change appends
  values; the columns are new, nullable or defaulted; every CHECK holds for every row the backfill
  leaves (an *Analysing* or *Actions open* row has `watch_from` NULL; a *Watching* row has it set;
  no row is closed). On a dev database the same holds.
- **Re-run safety:** `IF NOT EXISTS` on the table, each column, the unique key, the foreign key
  (as v35) and each CHECK (as v21, `backend/local_db.py:613`); the `MODIFY` is idempotent; the
  backfill's guards and the idempotent UPDATEs. `ADD UNIQUE KEY IF NOT EXISTS` has no precedent
  in `local_db.py`; MariaDB's `ALTER TABLE` grammar allows `ADD [CONSTRAINT [symbol]] UNIQUE
  [INDEX|KEY] [IF NOT EXISTS] [index_name] (…)` from 10.0.2 on (the dev image is `mariadb:11.4`,
  `tooling/dev/docker-compose.dev.yml:12`); § 8.1's re-run test proves it here.
- **`TEXT` for `remark` and `earlier`:** a problem is up to 2000 characters, and an edit line
  carries its field name; a why line up to about 1850 (S069 § 5.2). `TEXT` (64 KB) holds every
  line with no cut. Notes are bounded in code (1000, § 5.5).
- **Rollback:** a release before v39 does not read `improvement_events` or the new columns, and
  reads the state as text: an improvement in a new state would show its raw value in S068's list
  (`improvementStateLabel` falls back to the key) and count as closed in its `state=open` filter.
  v39 itself is safe on rows: the backfill and the CHECKs are written for them (§ 8.1). That
  v36–v39 ship in one release is an assumption on the release, in § 9 (BR1-12).
- **Text:** utf8mb4; Tamil notes fit (S067 § 4.1).

### 4.2 What is computed, never stored

- **`ready_to_verify`** (D1): `display_state(state, watch_from, watch_days, now)` (§ 5.2).
- **The watch's end** `watch_until = watch_from + watch_days days` and its figures (§ 5.4).
- `closed.by_lead`: the person whose login is `closed_by` is the lead (§ 6).
- Each timeline line's `by_name` (the person whose login is `created_by`, else the login, as
  S067's `created_by_name`), its ticket's serial and its countermeasure's kind and text (joins).
- The computed line *Watch ended* on the timeline (§ 5.6).

## 5. Rules

### 5.1 The states

`improvements_core`:

- `STATES = ("analysing", "actions_open", "watching", "closed_effective", "closed_not_effective",
  "dropped")` (stored); `READY_TO_VERIFY = "ready_to_verify"` (computed only).
- `IMPROVEMENT_OPEN_STATES = ("analysing", "actions_open", "watching")`;
  `CLOSED_STATES = ("closed_effective", "closed_not_effective", "dropped")`. `is_open` is unchanged
  (S067), so every S067–S070 write refuses a closed improvement with
  409 "This improvement is closed" (`IMPROVEMENT_CLOSED`) and the list's `state=open|closed` split
  follows (`backend/improvements.py`, `list_improvements`).
- **`is_open` and the list's SQL filter take the stored state only** (BR1-03). The display state
  (§ 5.2) is for output. `is_open("ready_to_verify")` is False, so no caller passes the display
  state to `is_open`, `_require_open` or the `removable` computation: `_detail` computes `is_open`
  from the row before it replaces `state` with the display state, and `tickets.py`'s
  `_improvement_fields` does the same. The core's docstring says so, and a core test pins
  `is_open(READY_TO_VERIFY) is False` with that reason.
- **The working state** is decided by one pure function, never by a button (D2):
  `working_state(stored_state, root_cause_set, actions)`, `actions` the improvement's
  countermeasures as `{kind, state, done_at}`, in this order:
  1. no root cause set → `analysing` (Q2.2 a: the root cause comes before *Watching*);
  2. `stored_state == "watching"` and no open countermeasure of a kind in `WATCH_KINDS` → stays
     `watching` (a *Lesson* or *Spread* added during the watch does not end it; BR1-01 b);
  3. no countermeasure open and at least one done → `watching`;
  4. else `actions_open`.
  `WATCH_KINDS = ("correction", "corrective", "preventive", "design_out")`: the kinds that act on
  the linked machines (S070 § 2). An improvement whose countermeasures are all cancelled stays
  *Actions open*: nothing was done, so there is nothing to watch.
- **The watch's start** `watch_start(actions)` = the latest `done_at` of the done countermeasures
  whose kind is in `WATCH_KINDS`; when none of those is done (only lessons or spreads), the latest
  `done_at` of any done countermeasure. A *Lesson* or *Spread* done during the watch does not move
  it.
- **`_settle_state(cur, improvement_id, locked)`** (the shell), called by the routes of the table
  below, inside their transaction, after their own write, while (6b) is held: reads the root
  cause from the locked row (or the value the route just wrote) and the countermeasures' `kind`,
  `state` and `done_at` with a plain read; when the working state or the watch's start differs
  from the stored values, writes `state` and `watch_from` (`watch_start(actions)` when the new
  state is `watching`, else NULL) with a plain `UPDATE` that stamps no `updated_*` (D16), and writes a `state_changed` line (`from_state`,
  `to_state`). An improvement that is not open is never settled.

| Route (step) | Settles? | Why |
|---|---|---|
| `PUT …/root-cause` (S069) | yes | the root cause is an input |
| `POST …/actions` add (S070) | yes | an open countermeasure of a `WATCH_KINDS` kind ends *Watching*; the watch starts again from the next done (D3) |
| `PUT …/actions/<id>` change (S070) | yes | a kind changed into or out of `WATCH_KINDS` can end or keep the watch |
| `POST …/actions/<id>/done` (S070) | yes | the last open one done starts the watch |
| `POST …/actions/<id>/cancel` (S070) | yes | the last open one cancelled starts the watch, when one is done |
| every other write | no | it changes no input |

**Actor × state × already there** (the display state, § 5.2):

| Action | Who (§ 5.8) | analysing | actions_open | watching | ready_to_verify | closed or dropped |
|---|---|---|---|---|---|---|
| Set root cause (S069) | `improvement:edit` | 200 → `actions_open` or `watching` | 200, stays (or `watching`) | 200, stays | 200, stays | 409 closed |
| Add countermeasure (S070) | `improvement:edit` | 201, stays | 201, stays | 201; a `WATCH_KINDS` kind → `actions_open`, `watch_from` NULL; a *Lesson* or *Spread* → stays | as *watching* | 409 closed |
| Done / cancel (S070) | S070 § 5.7 | 200, stays | 200 → `watching` when § 5.1 holds | 200, stays (only a *Lesson* or *Spread* can be open); `watch_from` unchanged | as *watching* | 409 closed |
| `PUT` `watch_days` | `improvement:edit` | 200 | 200 | 200; may become ready | 200; a longer watch is `watching` again | 409 closed |
| Close as effective | `improvement:verify` | 409 `VERIFY_NOT_YET` | 409 `VERIFY_NOT_YET` | 409 `watch_ends(until)` | 200 → `closed_effective` | 409 closed |
| Not effective | `improvement:verify` | the same 409 | the same 409 | the same 409 | 201 → `closed_not_effective` + the follow-up | 409 closed |
| Drop | `improvement:edit` | 200 → `dropped` | 200 | 200 | 200 | 409 closed |
| Add note | `improvement:note` | 201 | 201 | 201 | 201 | 409 closed |
| S067's edit, add / remove ticket; S069's whys; S070's change | as their steps | allowed | allowed | allowed | allowed | 409 closed |

- `VERIFY_NOT_YET` = "Verify once every countermeasure is done and the watch has ended".
  `watch_ends(until)` = "The watch ends on 18-02-2027. Verify after it." (DD-MM-YYYY).
- **Already in the target:** a second *Close* (a double tap) waits for (6b), then finds the
  improvement closed: 409 "This improvement is closed". The same for drop.
- **Whys and the root cause stay editable in every open state** (§ 9 Q1; S069 § 9 left it to
  R05.4). Each change has its line, so a late change is visible to the verifier.
- `close_error(action, display_state, watch_until)` in the core returns the message or None, as
  `removal_error` does; the shell raises the 409.

### 5.2 The display state

- `watch_until(watch_from, watch_days)` = `watch_from + timedelta(days=watch_days)` (a datetime;
  the screens show its date). Example: done 20-11-2026 15:30, 90 days → 18-02-2027 15:30.
- `display_state(state, watch_from, watch_days, now)` = `ready_to_verify` when `state ==
  "watching"` and `now >= watch_until(…)`, else `state`.
- `now` is the IST wall clock (`_now()`, `backend/improvements.py:122`). Every answer that names
  an improvement's state sends the display state: the detail, the list item, the ticket detail's
  `improvements[].state` (`backend/tickets.py:451`, through `improvements_core.display_state`;
  tickets.py imports only the pure core, as today).
- The close routes decide from the locked row's `state`, `watch_from` and `watch_days`, and
  `_now()`: never stale (D1).

### 5.3 The fields

| Field | Route | Rule and message (field) |
|---|---|---|
| `watch_days` | S067's `PUT /api/improvements/<id>` (optional; absent → unchanged) | integer, not a boolean, 30–365: "Choose a watch of 30 to 365 days" (`watch_days`); `null` → the same message |
| `remark` | `POST …/verify/effective` | optional: absent, `null` or empty after trim → NULL; else text, trimmed, up to 1000: "Remark: up to 1000 characters" / "Remark must be text" (`remark`) |
| `remark` | `POST …/verify/not-effective` | required, text, trimmed, 1–1000: "Say why it did not work" / "Remark: up to 1000 characters" / "Remark must be text" (`remark`) |
| `reason` | `POST …/drop` | required, text, trimmed, 1–1000: "Say why it is dropped" / "Reason: up to 1000 characters" / "Reason must be text" (`reason`) |
| `remark` | `POST …/notes` | required, text, trimmed (line breaks inside kept), 1–1000: "Write the note" / "Note: up to 1000 characters" / "Note must be text" (`remark`) |

- `validate_improvement` gains `watch_days` (S067 § 5.2's
  rules: absent stays, equal is not written, nothing changed writes nothing).
- `validate_close(body, needed, field)` serves the three close bodies; `validate_note(body,
  _creating)` the note. Unknown fields are ignored. A body that is not a JSON object is
  `clean_body`'s 400 (`backend/api_common.py:121`).

### 5.4 The watch figures

`watch_figures(tickets, symptom_ids, watch_from, watch_days, end)` in the core; `end` is `_now()`
for an open improvement and `closed_at` for a closed or dropped one (the figures as they stood at
the close; a drop from *Watching* has both `watch_from` and `closed_at`, BR1-14).
Computed only when `watch_from` is set; otherwise the detail's `watch.figures` is null.

**The query** (the shell, plain, one statement, then one events query for `ticket_times`, as
S067's `_events_by_ticket`, `backend/improvements.py:181`):

```sql
SELECT t.id, t.serial, t.occurred_at, t.intensity, t.failure_mode_id, t.state,
       m.code AS m_code, f.code AS f_code, f.label AS f_label
FROM tickets t JOIN equipment m ON m.id = t.equipment_id
LEFT JOIN failure_modes f ON f.id = t.failure_mode_id
WHERE t.equipment_id IN (<the machines>) AND t.not_a_fault = 0
  AND t.occurred_at >= <watch_from − watch_days days> AND t.occurred_at < <end>
ORDER BY t.occurred_at, t.id
```

- **The machines:** the distinct `equipment_id` of the improvement's linked tickets (S067's
  `_linked_tickets`). `tickets.equipment_id` is always the machine, never a component
  (`machine_and_component`), so this covers the machine and its parts ("Checked on the machine and
  its parts", mock-up 05). Served by `ix_tickets_equipment_state` (`backend/local_db.py:392`).
- **The symptoms:** the distinct non-null `failure_mode_id` of the linked tickets. None (only open
  tickets with no symptom yet) → `symptoms` empty and every "same symptom" figure null; the
  breakdowns and the downtime still show.
- **Not a fault** is left out: there was no failure (S067 D7).
- **Before** = tickets with `occurred_at < watch_from`; **after** = `watch_from <= occurred_at <
  min(end, watch_until)`. For each: `breakdowns` (intensity critical, `is_breakdown`),
  `symptom_breakdowns` (of them, a symptom in the set; null when the set is empty),
  `downtime_minutes` (the sum of `ticket_times(events, end)["downtime_minutes"]`, every intensity,
  as S067's loss), and `days` (before: `watch_days`; after: whole days from `watch_from` to
  `min(end, watch_until)`).
- **Repeats** (Q4.3 a): every ticket, any intensity, with a symptom in the set and `occurred_at >=
  watch_from` (up to `end`, so a repeat after the watch ended still shows to the verifier):
  `{id, serial, occurred_at, intensity, machine_code, symptom{id, code, label}, in_watch}` where
  `in_watch` is `occurred_at < watch_until`. Linked tickets of the improvement can be among them
  (a ticket added during the watch); they count like any other.
- A ticket that began before `watch_from` and went on after it counts in *before*, by its
  `occurred_at`; its downtime counts there in full.
- **Who sees them:** every reader of the improvement, also tickets of a unit the reader cannot
  open, as S067 D8 decided for the linked tickets (serial, time, machine and symptom only).
- **Bounds:** the tickets of `watch_days` before `watch_from` and from `watch_from` to `end`, on
  the improvement's machines (a handful). `end` can lie long after `watch_until` on an improvement
  left unverified; the machines keep the set small. No paging.

### 5.5 Notes

- `POST /api/improvements/<id>/notes` `{remark}`: a `note` line, `occurred_at` now. Open only.
- No correction of a note in this step (§ 1 *Out of scope*; § 9 Q3).

### 5.6 The timeline

**`_add_event(cur, improvement_id, event, occurred_at, …)`** writes one line, as tickets'
`_add_event` (`backend/tickets.py:907`), `created_by = actor()`. Every line is written in the same
transaction as the change it records, after it, under (6b).

| Route (step) | Line(s) | `remark` / `earlier` |
|---|---|---|
| Start (S067) | `started` (no ticket), then `ticket_linked` (`ticket_id`): one shape on every path, the backfill's and the follow-up's too (BR1-05) | — |
| Edit (S067; `watch_days` here) | `edited`, only when something changed | `tickets_core.edit_lines(old, new, labels)` (`backend/tickets_core.py:735`): one "Label: old → new" line per changed field, labels `Title`, `Problem`, `Lead`, `Watch`; the shell passes display values (the old and the new lead's names, two plain `people` reads; "90 days"); `earlier` NULL, the old value is in the line (BR1-04) |
| Add ticket (S067) | `ticket_linked` (`ticket_id`) | — |
| Remove ticket (S067) | `ticket_removed` (`ticket_id`) | — |
| Add why (S069) | `why_added` | `why_line(position, question, answer, evidence)`: "3. Why …? Because: … Evidence: …" |
| Edit why (S069) | `why_changed`, only when the moved or edited why changed | new line / old line (the other whys' shifts write nothing) |
| Remove why (S069) | `why_removed` | `earlier` the removed line |
| Set root cause (S069) | `root_cause_set` the first time, `root_cause_changed` after, only when something changed | `root_cause_line`: "4.2 Management error: <text>" and, when set, a line "Other causes: …"; `earlier` the old one |
| Add countermeasure (S070) | `action_added` (`action_id`) | `action_line`: "Corrective: <text>. Owner Kannan (technician), due 08-11-2026." |
| Change countermeasure (S070) | `action_changed` (`action_id`), only when something changed | `tickets_core.edit_lines` of kind (its label), text, owner (the name), due (DD-MM-YYYY); `earlier` NULL |
| Mark done (S070) | `action_done` (`action_id`), `occurred_at` = `done_at` | the done text |
| Cancel (S070) | `action_cancelled` (`action_id`) | the reason |
| Settle (§ 5.1) | `state_changed` (`from_state`, `to_state`) | — |
| Note (§ 5.5) | `note` | the note |
| Close as effective | `closed_effective` (`from_state` `ready_to_verify`, `to_state` `closed_effective`) | the remark or NULL |
| Not effective | `closed_not_effective` (`from_state` `ready_to_verify`, `to_state` `closed_not_effective`) on the old one; on the new one `started` with `remark` "Follow-up of IM-2026-10-001" and a `ticket_linked` per ticket | the remark |
| Drop | `action_cancelled` per open countermeasure (D10), then `dropped` (`from_state` the display state, `to_state` `dropped`) | "Dropped with the improvement: <reason>" / the reason |

- The countermeasure's documents (S070 § 5.8) write no line (§ 1 *Out of scope*).
- `ACTION_KIND_LABELS` in the core holds the six kind words of S070 § 2 ("Correction", …,
  "Spread"), for the lines. The frontend's `ACTION_KINDS` (new in S071) keeps the same words and
  their sentences; both test suites assert the six codes and words, as `WAITING_REASONS` and its
  frontend copy do (`backend/tickets_core.py:310-316`).
- Dates in a line are DD-MM-YYYY; a person is their `name`.
- **The read** (the detail's `timeline`), newest first by `occurred_at DESC, id DESC`, with `by_name`,
  the ticket's `{id, serial}` and the countermeasure's `{id, kind, text}` through `LEFT JOIN`s, one
  query. **The computed line:** when the display state is `ready_to_verify`, or the improvement
  was closed effective or not effective, the core adds `{id: null, event: "watch_ended",
  occurred_at: watch_until, by_name: null}` in its place by time (mock-up 05's "Watch ended —
  ready to verify"). Not stored (D1).

### 5.7 Locks

The database runs REPEATABLE READ. Each route takes its locking reads first; every decision comes
from a locking read or a plain read made after the lock that guards it.

**The global order** (`backend/equipment.py:9`): … (6) the serial counter → (6b) the improvement
row → (6c) the countermeasure row (new in S070) → (7) the ticket row. This step adds **no lock
level**. Event rows are only inserted, never locked or updated. Each event insert takes shared
foreign-key locks: on the improvement (held exclusive), on the ticket when `ticket_id` is set
((7) shared, after (6b): the edge S067's *Add ticket* already has), on the countermeasure when
`action_id` is set (held exclusive by S070's routes, or the row inserted in the same transaction).

**The S067–S070 routes:** their sequences are unchanged; each adds, at its end and still under its
locks, the line insert and, where § 5.1 says, `_settle_state` (a plain read of the counts and the
`MAX(done_at)`, safe because every countermeasure write takes (6b) first, then an `UPDATE` of the
held improvement row). *Remove ticket* gains the ticket's shared lock through its line's foreign
key: (6b) → (7) shared, as *Add ticket*.

**Add note** (`POST …/notes`): (1) (6b) `FOR UPDATE` (`state`, `unit_id`); 404 when missing.
(2) Plain reads, the transaction's first: the predicate (404), `improvement:note` at the site
(403), open (409). (3) The `note` line. (4) The detail.

**Close as effective** (`POST …/verify/effective`): (1) (6b) `FOR UPDATE` (`state`, `watch_from`,
`watch_days`, `unit_id`). (2) Plain reads: predicate 404, `improvement:verify` at the site 403,
`close_error` from the locked row and `_now()` 409. (3) `UPDATE improvements SET state =
'closed_effective', closed_at = now, closed_by = actor(), close_remark = …` (no `updated_*`).
(4) `UPDATE improvement_tickets SET open_link = NULL WHERE improvement_id = %s` (S067 D4: its
tickets may start or join another improvement). (5) The `closed_effective` line. (6) The detail.

**Not effective** (`POST …/verify/not-effective`):

1. (6) `next_counter(cur, serial_scope(now.year, now.month, "IM"))` (`backend/db_helpers.py:78`):
   the `IM:YYYY-MM` row, X. Taken before (6b), as the global order says. Its `SELECT` is the
   transaction's first plain read.
2. (6b) The old improvement `FOR UPDATE` (all of § 5.7's columns, `title`, `problem`, `lead_id`,
   `equipment_id`).
3. Plain reads: predicate 404, `improvement:verify` at the site 403, `close_error` 409, the old
   links.
4. The old row closed (as *Close*, step 3), its links' `open_link` NULL (step 4), its
   `closed_not_effective` line.
5. Insert the new improvement: the next `IM-` serial, the old `unit_id`, `equipment_id`, `title`,
   `problem`, `lead_id` and `watch_days`, `follow_up_of_id` = the old id (shared foreign-key locks
   on the unit, the machine, the lead's person row and the old improvement, held).
6. Insert one link per old link, `open_link` 1 (shared locks on each ticket (7) and the new row).
   No duplicate: step 4 freed `uq_improvement_tickets_open` in this transaction.
7. The new one's `started` line and one `ticket_linked` line per ticket. (8) The new one's detail, 201.

A refusal rolls back, the counter bump included, so no number is lost (S067 § 5.4).

**Drop** (`POST …/drop`): (1) (6b) `FOR UPDATE`. (2) Plain reads: predicate 404,
`improvement:edit` at the site 403, open 409. (3) The open countermeasures, each locked (6c) `FOR
UPDATE` by id order, then cancelled (S070's cancel fields, `cancel_reason` "Dropped with the
improvement: <reason>", truncated to S070's 500) with an `action_cancelled` line. (4) The row
`dropped`, `closed_*`, `close_remark` = the reason; the links' `open_link` NULL; the `dropped`
line. (5) The detail.

**Reads** (detail, list, the ticket detail): plain, no lock.

**No new deadlock cycle, checked against the notes:**

- *(6) → (6b)* on *not effective*: nothing holds an improvement row and then takes a counter. A
  start holds (6) and takes (7) shared and the new row only. Two *not effective* on the same
  improvement serialise on (6) when the month is the same, else on (6b); the second finds it closed.
- *(6b) → (7) shared*: as S067's *Add ticket*. Ticket writes hold (7) `FOR UPDATE` and never touch
  improvement rows (`backend/tickets.py:22-34`), so they never wait on us while we wait on them.
- *(6b) → (6c)*: as S070. The drop takes its countermeasures by id order; S070's writes take one
  each, after (6b): no two paths hold (6c) rows in opposite orders while (6b) is held by one of them.
- *The person row:* the follow-up's insert takes the unit's and the lead's shared foreign-key locks,
  as S067's start: the same accepted deadlock with a person's site-row edit (S067 § 5.4, 1213, a
  rare JSON 500, a retry).
- *S069's cause freeze* counts improvements `LOCK IN SHARE MODE` by `root_cause_id`; no route here
  changes `root_cause_id`.

The coder writes this into improvements.py's LOCK ORDER note and the improvements.py bullet of
equipment.py's note.

### 5.8 Permissions

| Key | Holders | Site-scoped | Comment in `config_rbac.py` |
|---|---|---|---|
| `improvement:verify` (new) | `maint_engineer` (so manager) | yes | S072, Q4.2 a: an engineer or manager of the site decides whether the fix worked; the lead may (a recorded departure from ISO 27001 A.5.3). Equal to `improvement:edit`'s holders today; the two can drift (as `ticket:edit_notes`) |
| `improvement:note` (new) | `maint_operator` (so supervisor, technician, engineer, manager) | yes | S072, Q1.3 a: every reader at the site adds a note; not IT admin, who reads only (D6) |

- `improvement:read` and `improvement:edit` are unchanged (S067 § 5.5). The storekeeper holds none.
  Admin bypasses.
- **Where each is checked**, always 404 (the predicate) before 403 (the key at the site):
  verify routes `@require_perm("improvement:verify")` then `require_perm_at`; drop
  `@require_perm("improvement:edit")`; notes `@require_perm("improvement:note")`.
- **Flags in the detail** (the screens follow them; S068 D6): `can_verify` = the display state is
  `ready_to_verify` and `improvement:verify` at the site; `can_drop` = open and `improvement:edit`
  at the site; `can_add_note` = open and `improvement:note` at the site; `can_edit_watch` = open
  and `improvement:edit` at the site.
- **Identity:** no field of this step changes who can log in or what anyone sees. The timeline shows
  names, never a login, role or email. A request with no identity gets `require_perm`'s 401.
- **`closed.by_lead`**: the person whose login is `closed_by` is the improvement's `lead_id`. Admin,
  with no Team record, is never the lead.

### 5.9 The database down

Every new route goes through `get_db()`: 503 while the database is down or missing (§ Yantra
Specifics, *DB may not exist*). No background task, no alert (D1).

## 6. API

All under S067's `improvements_bp` (`/api/improvements`), ids `<int:…>`. Every write answers with a
whole detail (S068 BR1-09).

| Route | Key | Body | Answer |
|---|---|---|---|
| `POST /api/improvements/<id>/notes` | `improvement:note` | `{remark}` | 201, the detail |
| `POST /api/improvements/<id>/verify/effective` | `improvement:verify` | `{remark?}` | 200, the detail (closed) |
| `POST /api/improvements/<id>/verify/not-effective` | `improvement:verify` | `{remark}` | 201, **the new improvement's** detail |
| `POST /api/improvements/<id>/drop` | `improvement:edit` | `{reason}` | 200, the detail |
| `PUT /api/improvements/<id>` (S067) | `improvement:edit` | gains `watch_days?` | 200, the detail |
| `GET /api/improvements/<id>` (S067) | `improvement:read` | — | gains the fields below; `state` is the display state |
| `GET /api/improvements` (S067) | `improvement:read` | unchanged | the item's `state` is the display state; no new field (`test_improvements_api.py:514` pins the item's keys) |
| `GET /api/tickets/<id>` | `ticket:read` | — | `improvements[].state` is the display state |

**The detail gains:**

- `watch: {days, from, until, ended, figures}`; `from` and `until` null before the watch starts;
  `ended` = `now >= until`, `false` before the watch starts (`from` and `until` null); `figures` null before, else `{machines: [{id, code}], symptoms: [{id,
  code, label}], before: {days, breakdowns, symptom_breakdowns, downtime_minutes}, after: {…},
  repeats: [{id, serial, occurred_at, intensity, machine_code, symptom, in_watch}]}`;
- `closed: {at, by_name, by_lead, remark} | null`;
- `follow_up_of: {id, serial} | null` and `follow_up: {id, serial} | null` (the improvement that
  followed this one, by `follow_up_of_id`);
- `timeline: [{id, event, occurred_at, by_name, from_state, to_state, ticket{id, serial}|null,
  action{id, kind, text}|null, remark, earlier}]`, newest first, the computed `watch_ended` line
  included (§ 5.6);
- `can_verify`, `can_drop`, `can_add_note`, `can_edit_watch` (§ 5.8).

`is_open`, `permissions` and every S067–S070 field keep their meaning.

## 7. Design decisions

- **D1. *Ready to verify* is computed from the clock, not stored or set by a daily task.** The
  close routes read the locked row and `_now()`, so the state is never a day late and a worker that
  is down changes nothing. The list's `state=open` filter needs no change (the stored state stays
  `watching`). Mock-up 05's line "Watch ended — ready to verify" is computed too (§ 5.6). R05.5
  adds the daily task its alerts need ("watch ended" once per improvement) and may store a line
  then. Rejected: a daily task in `scheduled_tasks.SCHEDULE` that sets `ready_to_verify` (stale up
  to a day; a second writer of the state; a state that depends on the worker running).
- **D2. The working states move by themselves, from the data.** One pure function
  (`working_state`) decides from the root cause and the counts, after each write that changes them.
  The roadmap defines each state by a fact ("root cause set", "every countermeasure done or
  cancelled"), so no button can disagree with the data. Rejected: *Start watch* and *Send to
  actions* buttons (one more tap; a stored state that can contradict the countermeasures).
- **D3. A countermeasure that acts on the machines ends the watch; a lesson or a spread does
  not** (BR1-01, answered (b)). A *Correction*, *Corrective*, *Preventive* or *Design-out* added
  during the watch sends the state back to *Actions open*, and the watch starts again when it is
  done: the watch is "from the last countermeasure done" (Q4.1 a) that changes what it counts. A
  *Lesson* or *Spread* changes nothing on the linked machines, so adding or finishing one neither
  ends nor moves the watch (`WATCH_KINDS`, `watch_start`); *Watching* still needs every
  countermeasure done or cancelled to begin. This follows ISO 9001 § 10.2.1 (d): the effectiveness
  of the action on the nonconformity. Rejected: every kind restarts the watch (a late lesson costs
  the team weeks of watch); refusing countermeasures while watching (a repeat may show that more is
  needed); keeping the old start for a machine kind (its effect would be judged on days before it
  was done).
- **D4. The watch starts at the last `done_at`, and *before* is the same length before it.** The
  verifier compares like with like (mock-up 05: "90 days before / 90 days after"). `watch_from` is
  stored when the watch starts: done countermeasures are final (S070 D5), so it cannot drift.
  Rejected: *before* from the problem's date (unequal windows); computing `watch_from` on every
  read (the list would need an aggregate per row).
- **D5. The count reads the linked tickets' machines and symptoms, every intensity, not-a-fault
  left out; repeats are listed up to now.** "The same symptom on the linked machines" (Q4.1 a)
  with ISO 14224's failure mode as the symptom. A repeat after the watch's end still shows before
  the verifier decides. Rejected: the improvement's one machine only (misses *Spread*'s other
  machines when their tickets are linked); breakdowns only for repeats (a degraded return is
  still a return).
- **D6. A new key `improvement:note`, not `improvement:read` at the site.** Q1.3 (a) gives notes to
  every reader and keeps IT admin read-only; IT admin holds `improvement:read` (S067), so the read
  key cannot tell them apart. A **departure** from the roadmap's key list (R05 § Departures names
  read, edit, verify, procedure:edit). Rejected: `improvement:read` plus "has a Team record" (a
  rule hidden outside `config_rbac.py`).
- **D7. `improvement:verify` is a key of its own**, with `improvement:edit`'s holders today (Q4.2
  a). A plant that later wants managers only (Q4.2 b) changes one tuple. Rejected: reusing
  `improvement:edit` (the two decisions could not drift).
- **D8. One table for the timeline, written by every write of improvements.py, in the same
  transaction.** S067–S071's routes gain their lines here: the timeline is only true if every
  change has one. `remark` and `earlier` keep the new and the replaced text (ISO 9001 § 7.5.3).
  § SMTW-Review gains the point "every improvements.py write writes its timeline line in the same
  transaction as the change". Rejected: a line per route only for R05.4's own routes (the history would miss the
  edits the record most needs); separate edit tables per kind (S027's `ticket_note_edits` shape,
  one per kind: five tables for one history).
- **D9. *Not effective* starts a follow-up with the old title, problem, lead, watch and tickets;
  nothing of the analysis is copied.** "Analyse again" means a fresh why-why; the old record stays
  one tap away (`follow_up_of`). The lead stays even if no longer a lead (S067 § 5.6: an unchanged
  lead is kept); the team changes it with *Edit*. The answer is the new detail, so the screen opens
  the record the team works on next. Rejected: copying the whys and countermeasures (the team would
  edit the old analysis instead of redoing it); no follow-up record (Q1.4 a asks for one).
- **D10. *Drop* cancels the open countermeasures with it.** Otherwise they stay *open* for ever on
  a dead record, overdue in R05.10's register. Each gets its own `action_cancelled` line. Rejected:
  leaving them (stale open work); refusing a drop while countermeasures are open (one more step for
  the engineer).
- **D11. Verify only after the watch** (Q4.1 a; Q4.1 c "verify as soon as done" was not chosen). A
  verifier who is sure earlier shortens `watch_days` to 30, which the timeline records. **A
  back-dated *done* may end the watch at once** (BR1-02, answered (a)): S070 D6 lets `done_at` go
  back to the problem's time, so a *Correction* recorded as done 100 days ago starts a watch that
  ended 10 days ago. Accepted: the watch counts real days since the fix, also days before the
  record knew of it, so the figures are honest; a false back-date shows on the timeline
  (`action_done` at its `done_at`, with its writer). Rejected: no watch start before the moment
  the state became *Watching* (it punishes the engineer who records on Monday what was done three
  weeks ago). Rejected: a
  *Close early* with a reason (a second road around the watch).
- **D12. A closed or dropped improvement is read-only, notes too.** "A closed improvement is
  read-only" (R05.4). A late finding goes on the follow-up, or a new improvement. Rejected: notes
  after the close (the record would change after the decision it records).
- **D13. The seven state words go into `improvementLabels.js` in this step, in plain words.** S072
  can then be committed alone without raw keys on S068's badges. The closed states read "Closed: it
  worked" and "Closed: did not work" (S073 BR1-06, answered (b)): the floor reads the badge; ISO's
  terms (effective, not effective) stay in the API codes, § 2 and the help text. Rejected: leaving
  the words to S073 (gate B would ship states shown as `actions_open`); "Closed: effective" on the
  badge (an office word for the floor).
- **D14. `watch_days` through S067's `PUT`.** One more optional field in the edit body; S068's
  dialog does not send it, so nothing changes there. Rejected: a route of its own (one more route
  for one number).
- **D15. The close is two routes**, effective and not effective, because they answer differently
  (200 the same record, 201 a new one). Rejected: one route with a `result` field (one route, two
  answer shapes).
- **D16. A state change stamps no `updated_*`.** `updated_*` keep the last edit of title, problem,
  lead, root cause (S067, S069); the state change has its own line. Rejected: `update_row` for
  the state (the last-edit time would move without an edit).

## 8. Tests and acceptance

### 8.1 Migration (`backend/tests/test_migration_v39.py`)

- A fresh database: `improvement_events` with its key and three foreign keys; `improvements` with
  the six columns, `uq_improvements_follow_up`, `fk_improvements_follow_up`, the four CHECKs, and
  `state` ENUM with the six values.
- **A v38 database with rows** (S067–S070's shape): improvement A with only a ticket; B with a root
  cause and an open countermeasure; C with a root cause, one done and one cancelled
  countermeasure; D with no root cause and one done countermeasure; whys on B. After v39: every row
  kept; A and D `analysing`, B `actions_open`, C `watching` with `watch_from` = the done one's
  `done_at`; the backfilled lines per § 4.1's table, with their times and `created_by`.
- The CHECKs: `watch_days` 29 and 366 refused; `watching` with `watch_from` NULL refused;
  `closed_effective` without `closed_at` refused; `dropped` without `close_remark` refused; two rows
  with the same `follow_up_of_id` refused (1062).
- A re-run of v39 changes nothing: `_schema()` equal and no line doubled (the backfill's guards).

### 8.2 Backend

**Core** (`test_improvements_core.py`): `IMPROVEMENT_OPEN_STATES` and `CLOSED_STATES`;
`working_state` (no root cause with all done → analysing; root cause and nothing → actions_open;
one open → actions_open; all cancelled → actions_open; one done, one cancelled → watching; from
*watching*, an open *Lesson* or *Spread* → stays watching, an open *Corrective* → actions_open;
from *actions_open*, an open *Lesson* with every other done → actions_open); `watch_start` (the
latest machine-kind `done_at`; a later *Lesson* `done_at` ignored; only lessons done → their
latest); `is_open(READY_TO_VERIFY)` is False (the stored-state rule, BR1-03);
`watch_until` (20-11-2026 15:30 + 90 → 18-02-2027 15:30); `display_state` (a minute before and at
`until`; a closed state never `ready_to_verify`); `close_error` for every cell of § 5.1's table;
`validate_improvement` with `watch_days` (29, 30, 365, 366, a boolean, `null`, absent); the close
and note validators (each message, 1000 / 1001); `watch_figures` (before and after split at
`watch_from`; a not-a-fault left out by the query, so not here; a ticket at `watch_until` is not in
*after* but is a repeat with `in_watch` false; no symptoms → nulls; a degraded repeat; a closed
improvement's `end`); `why_line`, `root_cause_line`, `action_line` (with and without
evidence or other causes; DD-MM-YYYY); `ACTION_KIND_LABELS` holds S070 § 2's six codes and words.

**API** (`test_improvement_close_api.py`), each test with its own tickets and improvement (S067's
set-up through `ticket_helpers.py`), so the kept worker database gives the starting state. The
watch's past is made by the API where it can (S070 lets `done_at` go back to the problem's time;
the ticket raised back-dated as admin, who holds `ticket:backdate`, `backend/config_rbac.py`), else
with `db_rows` (`backend/tests/conftest.py:545`) on `watch_from`. "Another site" and "a key
missing here" as S067 § 8.2.
- **States:** root cause set → `actions_open` and a `state_changed` line; a countermeasure added
  and marked done → `watching`, `watch_from` = its `done_at`; a *Lesson* added and done during the
  watch → still `watching`, `watch_from` unchanged; a *Corrective* added → `actions_open`,
  `watch_from` NULL; cancelled → `watching` again with the first `done_at`; all cancelled and none
  done → `actions_open`; done before the root cause → `analysing`, then the root cause → `watching`.
- **Ready:** `watch_from` 31 days back and `watch_days` 30 → the detail, the list item and the
  ticket detail's `improvements[].state` read `ready_to_verify`; `PUT watch_days` 60 → `watching`.
- **Close as effective:** 200, `closed_effective`, `closed.by_name`, `closed.by_lead` true for the
  lead and false for a manager; the links' `open_link` NULL; the ticket can start a new
  improvement (`can_start_improvement` true); a second close 409 "This improvement is closed";
  while watching 409 with the end date; in `actions_open` 409 `VERIFY_NOT_YET`; an operator (403);
  an operator here who is engineer elsewhere (403); an engineer of another site (404).
- **Not effective:** without remark 400; with it 201, the new improvement's detail: the next serial,
  `analysing`, the same tickets with `open_link` 1, `follow_up_of`; the old one `closed_not_effective`
  with `follow_up`; its whys and countermeasures stay on the old one; a refused one (not ready)
  leaves no serial gap.
- **Drop:** with an open countermeasure → it is `cancelled` with "Dropped with the improvement: …"
  and its line; the improvement `dropped`; *Mine* (new in S070) no longer lists the countermeasure;
  no reason (400); the operator (403); twice (409).
- **Read-only:** after a close, every write of S067 (edit, add and remove ticket), S069 (whys, root
  cause), S070 (add, change, done, cancel, a photo upload) and this step (note, drop, close) answers
  409 "This improvement is closed".
- **Watch figures:** a ticket with the same symptom on the machine during the watch → a repeat with
  `in_watch` true, `after.symptom_breakdowns` 1 when critical; one on another machine → not counted;
  a not-a-fault ticket → not counted; one before the watch → `before`; downtime sums match
  `ticket_times`; a closed improvement's figures stop at `closed_at`.
- **The database down** (`db_down`, `backend/tests/conftest.py:213`): `POST …/notes` answers 503.

**API** (`test_improvement_timeline_api.py`):
- A start writes `started` with no ticket, then one `ticket_linked`; an edit's line reads
  "Title: old → new" with `earlier` NULL; a lead change names both people.
- Each row of § 5.6's table writes its line with `by_name`, `remark` and `earlier` as stated (one
  test per route of S067, S069, S070 and this step); a `PUT` with no change writes no line; a why
  moved without a text change writes `why_changed` with the new place; the other whys' shifts write
  none.
- Order: newest first; `action_done` at its `done_at` sorts by that time.
- The computed `watch_ended` line shows when ready, not while watching.
- Notes: an operator of the unit adds one (201); IT admin (403: no `improvement:note`); the
  storekeeper (403 at the decorator); 1001 characters (400); on a closed one (409).

**RBAC** (`test_rbac.py`, § 8.3).

### 8.3 Existing tests that break or run again

- `backend/tests/test_improvements_core.py` `TestStates.test_only_analysing_and_it_is_open`
  (`:89-91`): pins `("analysing",)`; rewritten for the three open states.
- `backend/tests/test_rbac.py` `test_role_matrix` (`:193-209`): operator, supervisor, technician gain
  `improvement:note`; engineer and manager gain `improvement:note` and `improvement:verify`; IT
  admin's row is unchanged. `test_improvement_keys` (`:98-105`): the holders of § 5.8 and both
  keys in `SITE_SCOPED`. `backend/tests/test_auth.py:388` compares IT admin's `/api/auth/me` keys
  with `compute_permissions`; it follows by itself.
- `backend/tests/test_improvements_api.py`: green as it is. Its improvements stay `analysing` (no
  root cause); `TestTicketDetail` (`:614`) asserts `"state": "analysing"`, still true; `TestList`
  (`:502`) asserts `state=closed` empty, still true; the list item's key set (`:514`) is unchanged.
- S069's `test_improvement_whys_api.py` and S070's `test_improvement_actions_api.py` (new in those
  steps): they gain lines and, when a test sets a root cause or completes the countermeasures, a
  state change. The coder greps both for `"state"` and `"analysing"` and fixes any assertion the
  settle changes, naming each in the impl report.
- `backend/tests/test_migration_v36.py` … `v38`: unchanged (each slices its own range).
- `frontend/tests/improvementLabels.test.js`: the state test (`:9`) still passes; § 3 adds the six
  words of D13.

### 8.4 Automated (e2e)

None new: the screens are S073's. The specs read no new field. `frontend/e2e/improvements.spec.js`
asserts "Analysing" (`:36`, `:44`, `:108`, `:143`) on improvements with no root cause: still true.
S069's and S071's tests in that spec (new in those steps) set a root cause or complete
countermeasures; the coder checks each state assertion they make. The coder runs the whole browser
suite at Normal once at the end (the ticket detail's state and every improvement write changed).

### 8.5 On a real device

None. S073 holds them.

### 8.6 Acceptance

- All unit suites green; `npx vite build` clean; the whole browser suite at Normal green once.
- By API: IM-2026-10-001's lifecycle runs to `closed_effective`, and a second one to
  `closed_not_effective` with its follow-up holding the same tickets; every step has its timeline line.
- `docs/schema.md` and `docs/schema.html` show v39.

## 9. Open questions and assumptions

- **The split** (by the size rule, Phase 1). R05.4 in one brief would list about 26 code and test
  files and pass 600 lines, with two concerns that can ship apart (the backend's states, timeline
  and close; the screens: the watch card, the verify and drop dialogs, the timeline card, the
  notes). It is cut at the API, as R05.1 and R05.3 were (S067 BR1-01, S070 § 9): this step the
  backend (15 code and test files), **S073** the screens. S072 is coded first; S073 builds on § 6
  as written. Until S073, the badges show the new state words (D13) and nothing else changes on
  screen.
- **Length:** about 830 lines, past the size rule's 600, as S069 (721) and S070 (696) were. It is
  one concern (the backend); most of it is § 5's state table, the timeline table and the lock
  sequences, and § 4.1's backfill. No further cut.
- **Q1. Do the whys and the root cause lock at *Watching*?** Answered 30-10-2026: **no**, as proposed; they stay editable in
  every open state, each change on the timeline (§ 5.1). (b) lock them from *Watching* on: a root
  cause changed during the watch would then need *Not effective*. Not a defining question.
- **Q2. Undo a done countermeasure?** S070 § 9 Q1 left undo to R05.4. Answered 30-10-2026: **not
  in R05.4**, as proposed;
  a wrong *done* stays, with its line, and the engineer adds a new countermeasure, which ends the
  watch (D3). (b) an *Undo done* for `improvement:edit` with a reason, while the improvement is not
  closed: a step of its own if ever wanted.
- **Q3. Correct a note?** Answered 30-10-2026: **no** in this step (a note is short; a second note corrects
  it). S027's correction with earlier text can follow if wanted.
- **Assumption:** the clause numbers of the next ISO 9001 edition, ISO 55001 and SMRP 3.5.1 are *to
  verify*.
- **Assumption (BR1-12):** v36–v39 ship in one release (S067–S073). A release of S067–S071 alone
  would put rows in production before v39; v39 is written for rows (§ 4.1, § 8.1), but would then
  need a `_PRECONDITIONS` check, as the settings ask for a migration that touches production rows.
- **A staleness check is due before coding** (the orchestrator, 30-10-2026). This brief was
  approved while S069 was being coded and before S070 and S071 were. Check D8's routes and their
  lines against S069–S071's code as written, the line anchors of `backend/improvements.py`, the
  test files S069 and S070 create (§ 8.3), and v39's foreign key on `improvement_actions` and the
  backfill's columns against S070's v38.
- **Assumption:** R05.5's daily task finds ended watches by `state = 'watching' AND watch_from +
  INTERVAL watch_days DAY <= now`, which this schema serves.
- **No defining question.** Gate R answered Q4.1–Q4.3 and Q1.3–Q1.4; the decisions above are inside
  them. D6's new key, a departure from the roadmap's key list, is accepted as proposed (30-10-2026).

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 30-10-2026

Sections changed: header (Status, Baseline), § 1 (items 1, 2), § 2 (ISO 14224, EN 13306), § 3
(core names, improvements.py anchors, the label words, the SMTW-Review wording), § 4.1 (the
`why_added` backfill, the watching UPDATE, the unique-key note, rollback), § 5.1 (`is_open`,
`working_state`, `watch_start`, the settle table, the state table), § 5.4 (`end`, bounds), § 5.6
(start, edit and change lines, `to_state`), § 5.7 (*Not effective* step 7), § 6 (`watch.ended`),
§ 7 (D3, D8, D11, D13), § 8.2, § 8.3, § 9.

| Finding | Answer |
|---|---|
| BR1-01 minor | Accepted (b): `WATCH_KINDS` (correction, corrective, preventive, design-out); `watch_start` = their latest `done_at`, else any done one's; *Watching* still needs every countermeasure done or cancelled; a *Lesson* or *Spread* added during the watch does not end it. § 1, § 4.1, § 5.1, D3, § 8.2. |
| BR1-02 minor | Accepted (a): a back-dated *done* may end the watch at once; stated in D11. |
| BR1-03 minor | Accepted (a): `is_open` and the SQL filter take the stored state only; `_detail` and `_improvement_fields` compute `is_open` first; a core test pins `is_open(READY_TO_VERIFY) is False`. § 5.1, § 8.2. |
| BR1-04 minor | Accepted (a): edits reuse `tickets_core.edit_lines` ("Label: old → new"), `earlier` NULL; the shell reads the old and new lead's names. § 3, § 5.6, § 8.2. |
| BR1-05 minor | Accepted (a): every path writes `started` with no ticket, then one `ticket_linked` per ticket. § 5.6, § 5.7, § 8.2. |
| BR1-06…BR1-14 nits | Accepted: BR1-06 § 5.4 bounds; BR1-07 the backfill keeps the evidence (`CONCAT_WS`); BR1-08 "in the same transaction as the change" (§ 3, D8); BR1-09 § 2 ISO 14224 and EN 13306; BR1-10 § 6 `watch.ended` false before the watch; BR1-11 § 5.6 `to_state` on the close and drop lines; BR1-12 the one-release point moved to § 9; BR1-13 improvements.py's line numbers left out; BR1-14 § 5.4 "closed or dropped". Also from S073 BR1-06 (b): D13's closed-state words are "Closed: it worked" / "Closed: did not work". D6 and § 9 Q1–Q3 as proposed. |
