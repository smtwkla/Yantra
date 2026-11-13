```
Step: S099 — Verify and send back a PM job
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 02-11-2026
Track: full
Baseline: refs/steps/S098 (5b340d0; c9cd091 + S095–S098), checked by staleness review s1
Status: Done — folded into S104 (KLA 13-11-2026, gate B 2a: its code is reworked and committed with S104; its own snapshot dropped); was: Held 02-11-2026 by KLA (one path: PM templates linked to class, model or machine; R03 re-plan; 5b nothing adopted until the rework is done); was: Gate B 02-11-2026 (code review r1: 1 minor, 3 nits, fixed in fix round 1; verify review r2: 1 blocker (CR2-01, a test that failed on the iPhone), fixed by the orchestrator in S100's snapshot; no device check); approved 02-11-2026 (gate A delegated by KLA for tonight's PM steps: "Do those steps … stop only for real show stoppers"; review r1: 0 blocker, 0 major, 5 minor, 9 nits, all accepted; Q9 (keep the first round's answers?) and the other decisions of § 9 flagged for KLA at gate B)
From: R03.5
```

# S099 — Verify and send back a PM job

## 1. What will be built

R03.5 of `docs/roadmap/R03-pm.md`. **The engineer signs off a finished PM job, or sends it back
with a remark.** This closes Plan § 4.3's loop: due → in progress → done → verified, and "the
engineer can send back to *in progress*". S097 made the jobs and declared the state `verified`;
S098 lets the technician do a job and mark it done. S099 adds the sign-off.

1. **The verification setting takes effect** (Q5.1 a). At *Mark job done* (S098's route) the job
   copies its plan's `needs_verification` into a new column `pm_jobs.needs_verification`
   (migration **v54**, § 4). A job copied with 1 **waits for verification**: state `done`, on the
   new *To verify* tab. A job copied with 0 is **final at `done`** (D1). A later change of the
   plan's setting never moves a finished job in or out of the queue.
2. **Verify job** (`POST /api/pm/jobs/<id>/verify`): `done` → `verified`, with an optional remark.
   Final: a verified job cannot be changed or sent back.
3. **Send back** (`POST /api/pm/jobs/<id>/send-back`): `done` → `in_progress`, with a required
   remark. The job's `done_at`, `done_meter`, `timeliness` and `needs_verification` are cleared
   (S097 BR1-10, `chk_pm_jobs_done`); its results become writable again (S098's `state_error`
   allows `in_progress`). The technician fixes it and marks it done again, at or after the
   send-back time; the plan's next job then counts from its latest done time, which is this job's
   new one unless a later job of the plan is also done (§ 5.4). **The rework changes the item
   answers in place** (S098 § 5.4): the first round's answers and item remarks are not kept; the
   timeline keeps the engineer's send-back remark and both *Done* times (BR1-03).
4. **The plan's open job and a send-back** (D3). A job waiting for verification is not open
   (`pm_jobs_core.OPEN_STATES`), so the plan may already have an open job (made from this job's done
   time, or from a later done job's). Send back cancels the plan's open job when it is not started
   (a timeline line says why), because the plan may hold one open job only (`uq_pm_jobs_open_plan`).
   When the open job is started, send back is refused with the reason.
5. **Self-verification** (Q5.2 a): an engineer may verify a job he performed. It is recorded: the
   `verified` event names the verifier's person, and the page and the timeline say "the person who
   did the work" when that is the job's *Performed by*.
6. **The PM list** (S097's `PmJobsView.vue`, S098's tabs): a tab **To verify (n)** between
   *Upcoming* and *Done* (mock-up `docs/roadmap/R03-mockups/04-verify.html`), the oldest done first,
   each row with its findings ("All OK", "1 Not OK · 1 Not done"). *Done* now lists only finished
   jobs: verified, or final at `done`. A sent-back job shows *Sent back* on *Due* and in *Me* ›
   *Open work*.
7. **The job page** (S098's `PmJobView.vue`): for a job waiting for verification, a card *Verify*
   with *Send back* and *Verify job*, each opening one dialog with the facts, the consequence and the
   remark (`PmJobVerifyDialog.vue`). A verified job shows who verified it and when. A sent-back job
   shows the remark at the top. The *History* card (S098) gains the lines *Verified* and *Sent back*.
8. **One new key** `pm_job:verify`: the engineer, so the manager inherits it (Plan § 3); in
   `SITE_SCOPED`, checked at the site of the job's node's current unit.

**After S099:** the full PM loop of Plan § 4.3 (R03 milestone 1).

### Out of scope

- An alert when a job waits for verification, or when it is sent back (R03.7; the roadmap's
  "verification due-time alert"). The technician sees a sent-back job on *Me* › *Open work*.
- *To verify* on *Me* for the engineer; a dashboard count (Plan § 6 "verify / close queues": the
  *PM* list's tab is the queue).
- Photos and vendor reports on the job (R03.6); a ticket raised from an item (R03.10). The mock-up's
  "1 ticket raised" and "vendor report attached" come with them.
- Verifying a job whose plan needs no verification, or un-verifying a verified job.
- The compliance report (R03.14): S099 keeps `timeliness` on every finished job, so R03.14 reads it.

## 2. Standards and practice

- **TPM — planned maintenance pillar.** In plain words: the maintenance team plans the work, does
  it, checks it and learns from it (plan, do, check, act). S099 is the *check*: an engineer looks at
  the results before the job is closed, and sends poor work back.
- **ISO 9001:2015 § 7.5.3 — control of documented information.** In plain words: records are
  kept, protected from change, and show who did what and when. Every verify and send-back is a
  timeline line with who, when and the remark. A send-back keeps the first *Done* line, so the
  timeline shows the job was done twice and why it was sent back; the item answers of the first
  round are changed in place, not kept (BR1-03, § 9 Q9). A verified job is read-only.
- **ISO/IEC 27001:2022 A.5.3 — segregation of duties.** In plain words: one person should not both
  do and approve the same work, where the risk calls for it. **Departure, recorded (Q5.2 a):** an
  engineer may verify his own job, because the plant has few engineers; tickets already allow
  self-close (Plan § 3), and improvements let the lead verify (S072, `by_lead`). The record says
  so, so an auditor can find and count those jobs.
- **ISO/IEC 27001:2022 A.5.15 — access control.** In plain words: each person may do only what the
  work needs. `pm_job:verify` is checked at the job's site; IT admin reads PM and verifies nothing
  (R03 Q2.2 a).
- **ISO 55001:2014 § 8.3 — outsourcing.** In plain words: work done by outsiders is controlled
  by the organisation. An AMC vendor's technician is a contractor in Team who performs the job
  (Plan § 4.3, *Performer*); the plant's engineer verifies it, so outsourced work is checked by a
  plant person before it counts as closed.
- **SMRP — PM compliance** (metric number *to verify*). In plain words: the share of PM jobs done
  on time. A sent-back job was not finished until it was finished right, so its `timeliness` is
  judged again at the new done time (D4).

## 3. Where

S099 builds on four steps not committed when this brief was written. The staleness check confirms
these names before coding (§ 9 A1):

- **S095** (`docs/steps/S095-pm-schedule-core/1-brief.md`): `pm_schedule_core.timeliness`, the
  constants `ON_TIME`, `LATE`; § 9 N1 (a done job keeps its judgement).
- **S096** (`docs/steps/S096-pm-plans/1-brief.md`): `pm_plans.needs_verification` (v51, `TINYINT(1)
  NOT NULL DEFAULT 1`), `pm_plans_core.default_verification` (yes for maintenance plans, no for
  operator plans); the lock "(6e) the PM plan row, first in its transaction".
- **S097** (`docs/steps/S097-pm-jobs-due/1-brief.md`): v52; `pm_jobs` columns `id`, `serial`,
  `plan_id`, `equipment_id`, `state`, `done_at`, `done_meter`, `timeliness`, `open_plan_id`
  (generated, `uq_pm_jobs_open_plan`); the CHECK `chk_pm_jobs_done`; `pm_job_events` columns
  `job_id`, `event` (`VARCHAR(30)`, no ENUM), `from_state`, `to_state`, `occurred_at`,
  `person_id`, `remark`, `created_by`; `pm_jobs_core.DUE_STATE`, `IN_PROGRESS`, `DONE`, `VERIFIED`,
  `CANCELLED`, `OPEN_STATES`, `BASE_STATES`, `CANCELLED_EVENT`, `TABS`; `pm_jobs.settle_plan_job`
  and its CANCEL branch, `pm_jobs._now`, `jobs_out`, `GET /api/pm/jobs`; § 5.7's rule "every write
  of a `pm_jobs` or `pm_job_events` row holds its plan's row (6e) first"; § 9's note for R03.5.
- **S098** (`docs/steps/S098-pm-job-phone/1-brief.md`): v53; `pm_jobs.performed_by_id`,
  `started_at`, `chk_pm_jobs_started`; `pm_job_results` columns `job_id`, `outcome`,
  `limit_state`; `pm_work_core.NOT_OK`, `NOT_DONE`, `REMARK_MAX`, `REMARK_TOO_LONG`,
  `REMARK_NOT_TEXT`, `REMARK_NEEDED` (a dict by outcome), `_remark`, `JOB_DONE`, `JOB_CANCELLED`,
  `done_before_start`, `job_time_error`, `validate_result`, `state_error`, `DONE_EVENT`;
  `pm_work._event_time`; `pm_jobs.add_event`, `pm_jobs._cancel`; `pmLabels.js`'s `PM_TABS`,
  `jobsQuery`, `countText`; § 5.4's rule "the page sends
  `remark: null`" on *OK*, *Done*, *NA* (S098 BR1-02); `backend/pm_work.py` with
  `pm_work_bp`, `job_detail`, the pre-read before the transaction, the routes `GET
  /api/pm/jobs/<id>` and `POST /api/pm/jobs/<id>/done`, and its LOCK ORDER note "(6f) the PM job
  row"; `pm_jobs_core.TAB_DONE`; the *Done* tab (paged, `BASE_STATES`); `assigned=me` (assignee or
  performer); `frontend/src/views/PmJobView.vue`, `frontend/src/views/pm/PmJobDoneDialog.vue`,
  `frontend/src/components/PmJobRow.vue`, `pmLabels.js`'s `PM_EVENT_LABELS`, `jobBadges`,
  `TIMELINESS_LABELS`; `frontend/e2e/pm-job.spec.js`; the route `pm-job` (`/pm/jobs/<id>`).

### Backend

- `backend/local_db.py`: migration **v54** at the end of `_MIGRATIONS`, after S098's v53 (§ 4.1).
  No `_PRECONDITIONS` entry (§ 4.1, *Existing rows*).
- `backend/pm_work_core.py` (S098's): the constants, messages and pure functions of § 5.1;
  S098's `_remark(raw, outcome)` is renamed `clean_remark(value, needed_message)` (BS1-05), which
  `validate_result` and `verify_remark` both call.
- `backend/pm_work.py` (S098's): the routes *verify* and *send back* (§ 6); Mark done copies
  `needs_verification` and takes the send-back floor through `_event_time` (§ 5.5); `job_detail`
  gains the fields of § 6.2; the LOCK ORDER note gains the S099 lines (§ 5.6).
- `backend/pm_jobs.py` (S097's): the private `_cancel(cur, job, remark, now, actor)` is **renamed**
  the public `cancel_job` (BS1-04, as S098 CR1-04 did `add_event`), so send back shares it
  (CLAUDE-COMMON *DRY*; `settle_plan_job` calls the new name, no change of behaviour; it writes
  `from_state` `due`, right for send back, which cancels a `due` job only); its LOCK ORDER note
  gains one line: send back (`pm_work.py`) calls `cancel_job` on the plan's open job under the same
  (6e); `GET /api/pm/jobs` gains the tab `to_verify`, narrows `done`,
  and its items and `counts` gain the fields of § 6.3.
- `backend/pm_jobs_core.py` (S097's, S098's): `TAB_TO_VERIFY = "to_verify"`, `TABS = (TAB_DUE,
  TAB_UPCOMING, TAB_TO_VERIFY, TAB_DONE)`.
- `backend/config_rbac.py`: `"pm_job:verify": ("maint_engineer",)` after S098's `pm_job:work`, with
  the comment of § 5.2; the key joins `SITE_SCOPED`.
- `backend/equipment.py`: docstring only. Its LOCK ORDER line "(6f) the PM job row" gains the
  send-back exception (§ 5.6).

### Tests

- `backend/tests/test_migration_v54.py` (new; § 8.1), with the helpers of
  `backend/tests/migration_helpers.py` (`_recreate`, `_migrate`, `_run`, `_schema`).
- `backend/tests/test_pm_work_core.py` (S098's): the functions of § 5.1, written and green first.
- `backend/tests/test_pm_verify_api.py` (new; § 8.2): verify, send back, the plan's open job,
  Mark done's copy and floor, the page fields.
- `backend/tests/test_pm_jobs_api.py` (S097's, S098's): the *To verify* tab, the narrowed *Done*
  tab, `counts.to_verify`, the 400 text (§ 8.3).
- `backend/tests/test_rbac.py`: `test_role_matrix` rows and a new `test_pm_job_verify_key` (§ 8.3).

### Frontend

- `frontend/src/views/PmJobView.vue` (S098's): the *Verify* card, the verified line, the sent-back
  line (§ 5.8).
- `frontend/src/views/pm/PmJobVerifyDialog.vue` (new): *Verify job* and *Send back job* (§ 5.8).
- `frontend/src/views/PmJobsView.vue` (S097's, S098's): the *To verify* tab and its pager (§ 5.7).
- `frontend/src/components/PmJobRow.vue` (S098's): the *To verify*, *Verified* and *Sent back*
  rows (§ 5.7).
- `frontend/src/utils/pmLabels.js` (S096's): `PM_EVENT_LABELS` gains two labels; `jobBadges` the
  new badges; new `findingsText(findings)`, `verifiedText(verification)`, `sentBackText(sentBack)`;
  `PM_TABS` gains `to_verify` (in the mock-up's order); `jobsQuery` sends `tab=to_verify` and its
  `page`; `countText("to_verify", counts, total)` → "3 to verify" from `total` (the paged count, as
  *Done*); `counts.to_verify` is the tab label's (BS1-01).
- `frontend/src/views/pm/PmJobDoneDialog.vue` (S098's): its last line depends on the plan's
  verification (BS1-08, § 5.5).
- `frontend/tests/pmLabels.test.js` (S096's): the new helpers, and the `jobsQuery` and `countText`
  cases for `to_verify`.
- `frontend/e2e/pm-verify.spec.js` (new; § 8.4). Set-up helpers in the spec file; `frontend/e2e/
  support/` is unchanged.
- `frontend/e2e/pm-job.spec.js` (S098's): one line of one test changes (§ 8.3).

No router change (the job page exists), no `api.js` or `e2e/support/` change, no new nav item.

### Docs (housekeeping, by the coder)

- `docs/schema/notes.json`: the `pm_jobs` line gains "`needs_verification`: copied from the plan at
  Mark done; 1 = waits on *To verify* (S099)"; then `tooling\schema-docs.bat write`, read `git diff
  docs/schema/`, and `check` exits 0. `docs/schema/schema.json` and `docs/schema/schema-data.js` are
  generated.
- `docs/Plan.MD` § 4.3, under *PM job*: a *Built (S099)* paragraph (the copy at Mark done, verify,
  send back, the plan's open job, the second done time's floor, self-verification recorded, the
  tabs; D1–D7 as decisions; and the sentence "A send-back changes the item answers in place: the
  first round's answers and item remarks are not kept; the timeline keeps the send-back remark and
  both done times."). The
  *Needs-verification flag per plan* bullet loses "(*Proposed*, 17-10-2026)" and says "Built
  (S096, S099)". § 3: one paragraph for `pm_job:verify` and the A.5.3 departure.
- `.claude/CLAUDE.md` § SMTW-Review: the point of § 8.6.
- `docs/Keycloak.md`: no change (no Keycloak role). `docs/steps/device-checks.md`: no row (§ 8.5).

**File count:** 21 code and test files: backend 7, backend tests 5, frontend 9.

## 4. Data model

### 4.1 Migration v54

```sql
-- PM jobs (S099, R03.5): whether a finished job waits for an engineer's verification, copied from
-- its plan's needs_verification at Mark done, so a later change of the plan's setting never moves a
-- finished job in or out of the To verify list (R03 Q5.1 a).  1: the job waits at done until it is
-- verified or sent back; 0: done is final.  NULL while the job is not done, and on a job done before
-- S099 (final, as S098 left it).  A send-back clears it with done_at; Mark done copies it again.
ALTER TABLE pm_jobs
    ADD COLUMN IF NOT EXISTS needs_verification TINYINT(1) NULL AFTER timeliness;
ALTER TABLE pm_jobs ADD CONSTRAINT IF NOT EXISTS chk_pm_jobs_verification CHECK (
    (needs_verification IS NULL OR state IN ('done','verified'))
    AND (state <> 'verified' OR needs_verification = 1));
```

- **Existing rows** (fact from S097 § 1 and S098 § 1: S097 writes `due` and `cancelled`, S098
  writes `in_progress` and `done`, nobody writes `verified`): every row gets `needs_verification`
  NULL and passes the CHECK. No row is updated, so no `_PRECONDITIONS` entry. A job done before
  S099 stays final (D2). The migration test builds a v53 database with a `due`, an `in_progress` and
  a `done` job and migrates it (§ 8.1).
- **No new event values:** `pm_job_events.event` is `VARCHAR(30)` (S097 § 4.1), so `verified` and
  `sent_back` need no migration. **No verifier column:** the `verified` event holds who and when
  (`person_id`, `created_by`, `occurred_at`), as every other state change of the job.
- **No index:** the *To verify* query filters `state = 'done'` through S097's `ix_pm_jobs_state
  (state, due_on)`; tens of rows at the pilot.
- **Re-run safety:** `ADD COLUMN IF NOT EXISTS`, `ADD CONSTRAINT IF NOT EXISTS` (S098's v53
  pattern); two statements; a run stopped between them completes on the next start. Rollback: the
  release of S098 (v53) never reads the column.

### 4.2 What is computed, never stored

- **Waits for verification** = `state = 'done' AND needs_verification = 1`
  (`pm_work_core.awaits_verification`).
- **Self-verified** = the `verified` event's `person_id` is set and equals the job's
  `performed_by_id` (`pm_work_core.self_verified`). Neither changes once the job is verified, so the
  derived fact is as fixed as a stored flag; the rule of the improvement's `by_lead`
  (`improvements._closed`).
- **The findings** of a finished job: the counts of its results with `outcome` `not_ok`, with
  `outcome` `not_done`, and with `limit_state` set (one `GROUP BY` query per page).
- **The plan's open job** beside a job waiting for verification (`OPEN_STATES`), if any; it may
  have been made from this job's done time or from a later done job's (BR1-04).

## 5. Rules

### 5.1 The pure core (`backend/pm_work_core.py`, S098's)

```python
VERIFY_KEY = "pm_job:verify"
VERIFIED_EVENT, SENT_BACK_EVENT = "verified", "sent_back"
SEND_BACK_CHANGES = {"state": IN_PROGRESS, "done_at": None, "done_meter": None, "timeliness": None,
                     "needs_verification": None}          # chk_pm_jobs_done, chk_pm_jobs_verification
```

**Messages** (CLAUDE-COMMON writing style B):

| Constant | Text | Status / field |
|---|---|---|
| `NOT_DONE_YET` | "This job is not done yet. It can be verified once it is marked done." (`due`, `in_progress`) | 409 |
| `ALREADY_VERIFIED` | "This job is verified. It cannot be changed." | 409 |
| `NO_VERIFICATION` | "This job needs no verification. It is final." (`done`, `needs_verification` 0 or NULL) | 409 |
| `JOB_CANCELLED` | S098's ("This job was cancelled.", `cancelled`, `skipped`) | 409 |
| `SEND_BACK_REMARK` | "Say what must be done again." | 400 `remark` |
| `REMARK_TOO_LONG`, `REMARK_NOT_TEXT` | S098's (500 characters) | 400 `remark` |
| `open_job_started(serial)` | "The plan's open job PM-2026-11-004 has been started, so this job cannot be sent back. Verify this job, or raise a ticket for what is wrong." | 409 |
| `open_job_cancelled(serial)` | "PM-2026-10-014 was sent back, so the plan's open job is cancelled. The next job is made again from the latest done time." (the open job's `cancelled` remark; `serial` the sent-back job's) | — |
| `done_before_send_back(sent_back_at)` | "Done must be at or after it was sent back, 28-10-2026 10:00." | 400 `done_at` |
| `SCRAPPED_NO_SEND_BACK` | "This machine is scrapped. The job cannot be sent back." (the page's line; the route answers `SCRAPPED_MESSAGE`) | — |

| Function | Input → output | Rule |
|---|---|---|
| `awaits_verification(state, needs_verification)` | → bool | `state == DONE` and `needs_verification == 1` |
| `verify_error(state, needs_verification)` | → `(message, 409)` or None | for both actions: `verified` → `ALREADY_VERIFIED`; `due`, `in_progress` → `NOT_DONE_YET`; `cancelled`, `skipped` → `JOB_CANCELLED`; `done` not waiting → `NO_VERIFICATION`; `done` waiting → None |
| `clean_remark(value, needed_message)` | a raw remark, a message or None → `(remark, None)` or `(None, message)` | trimmed; empty or absent → None; not text → `REMARK_NOT_TEXT`; over `REMARK_MAX` → `REMARK_TOO_LONG`; None and `needed_message` set → that message. S098's `_remark(raw, outcome)` renamed, its second argument now the message: `validate_result` passes None for a check's NA (its rule stays) and `REMARK_NEEDED.get(outcome)` otherwise (BS1-05; S098's core tests stay green) |
| `verify_remark(body, needed)` | the body, bool → `(remark, None)` or `(None, ("remark", message))` | `clean_remark(body.get("remark"), SEND_BACK_REMARK if needed else None)` |
| `done_time_error(moment, now, started_at, sent_back_at)` | naive IST datetimes; `started_at` and `sent_back_at` each None or a time → message or None | `job_time_error(moment, now)` first; then `sent_back_at` set and `moment < sent_back_at` → `done_before_send_back(sent_back_at)`; else `started_at` set and `moment < started_at` → S098's `done_before_start(started_at)` (BR1-02). With both None it is `job_time_error(moment, now)` |
| `self_verified(verifier_person_id, performer_id)` | int or None, int or None → bool | both set and equal |

Type rules as S098: a wrong input type raises `TypeError` / `ValueError` naming it (a shell bug).
`needs_verification` arrives as the column's int (0, 1) or None.

### 5.2 Who may verify

| Key | Holders | Where |
|---|---|---|
| `pm_job:verify` (new) | `("maint_engineer",)`, so the manager; not the technician, supervisor, operator, storekeeper or IT admin | `SITE_SCOPED`; checked at the site of the job's node's current unit (S097 D9), as `pm_job:work` |

Comment in `config_rbac.py`: "Verifying a PM job (S099, R03.5): sign off a done job, or send it
back with a remark (Plan § 4.3).  The engineer, so the manager.  He may verify a job he performed
(R03 Q5.2 a), a recorded departure from ISO 27001 A.5.3: the verified event names him, and the job
page says so.  Not IT admin, who reads PM only (R03 Q2.2 a)."

- **The checks' order on both routes** (S098 § 5.2's order): 401 (no identity) → 403
  `require_perm(VERIFY_KEY)` (held nowhere) → 404 (the job missing, or its node outside
  `equipment:read`'s units: `load_node_for_user`'s `_can_access`, as S098 BR1-19; safe because
  `require_perm(VERIFY_KEY)` ran first and every holder holds `equipment:read`) → 403
  `require_perm_at(VERIFY_KEY, site)` → 409 `verify_error` → 400 the remark → 409 the send-back
  refusals (§ 5.4). Every holder of `pm_job:verify` holds `pm_job:read` (the engineer includes the
  operator; `test_pm_job_verify_key` pins it).
- **Any holder at the site verifies any job there**, also his own (Q5.2 a) and one another engineer
  sent back. Admin (code bypass) may verify; with no Team record his event has `person_id` NULL, so
  it is never self-verified.
- **Identity:** no field changes who can log in or what anyone sees. The answer names the verifier
  by name only (no login, no email), by S098 § 6.2's rule (`people.username`, else the login).

### 5.3 Verify job (`POST /api/pm/jobs/<id>/verify`)

Body `{remark}` (optional; unknown fields ignored, `clean_body`). In one transaction (§ 5.6):

1. `verify_error(job["state"], job["needs_verification"])` from the locked job row.
2. `remark = verify_remark(body, needed=False)`.
3. `now = pm_jobs._now(cur)`; `update_row(cur, "pm_jobs", job_id, {"state": VERIFIED}, actor())`.
   `done_at`, `done_meter`, `timeliness` and `needs_verification` stay (the CHECKs hold).
4. The event `verified` (`pm_jobs.add_event`, BS1-04): `from_state` `done`, `to_state` `verified`, `occurred_at` `now`,
   `person_id` `current_person_id(cur)` (the verifier; None without a Team record), `remark`.
5. The answer is the job page's (§ 6.2), now read-only for everyone.

- **The next job is not touched.** `verified` is in `BASE_STATES` (S097) and `done_at` does not
  change, so the plan's next due point is the same before and after. No `settle_plan_job` call.
- **A scrapped machine** does not stop verify: the work was done before the scrap, and verify
  only closes the record. A deactivated plan does not stop it either.
- **A double tap:** the second request waits on the plan lock, then reads `verified` → 409
  `ALREADY_VERIFIED`; the page shows the job verified.

### 5.4 Send back (`POST /api/pm/jobs/<id>/send-back`)

Body `{remark}` (required). In one transaction (§ 5.6):

1. `verify_error(…)` from the locked job row; the node's `lifecycle` from its locked row:
   `scrapped` → 409 `SCRAPPED_MESSAGE` (`equipment.py`; a job in progress on a scrapped machine
   could never be finished, S098 D15).
2. `remark = verify_remark(body, needed=True)`.
3. **The plan's open job:** `SELECT id, serial, state FROM pm_jobs WHERE plan_id = %s AND state IN
   (OPEN_STATES)` (plain, after the locks; at most one row, `uq_pm_jobs_open_plan`; never this job,
   which is `done`). It may count from this job's done time or from a later done job's; the rule is
   the same (BR1-04):
   - none: go on;
   - `in_progress` → 409 `open_job_started(serial)`; nothing is written. (This covers a second
     waiting job too: with J1 back in progress, a send-back of J2 is refused naming J1.)
   - `due` → `pm_jobs.cancel_job(cur, open_job, open_job_cancelled(job["serial"]), now, actor())`:
     state `cancelled` (its `open_plan_id` becomes NULL), the event `cancelled` (`from_state` `due`,
     `to_state` `cancelled`, the remark). The job keeps its serial and its row (ISO 9001 § 7.5.3).
4. `update_row(cur, "pm_jobs", job_id, SEND_BACK_CHANGES, actor())`: state `in_progress`, so
   `open_plan_id` is the plan again (free after step 3). `started_at`, `performed_by_id`, the
   results and the meter readings the job logged stay.
5. The event `sent_back` (`pm_jobs.add_event`): `from_state` `done`, `to_state` `in_progress`, `occurred_at` `now`,
   `person_id` `current_person_id(cur)`, `remark`.
6. The answer is the job page's (§ 6.2): `can_work` true again for a `pm_job:work` holder.

- **After a send-back** the job is S098's `in_progress` job: its items can be changed (a changed
  reading replaces its meter reading, S098 D8), its *Performed by* can change, and *Mark job done*
  works as before. **A changed item overwrites its answer in place** (S098 § 5.4: `outcome`,
  `value`, `limit_state`, `remark`; the page sends `remark: null` on *OK*), so "Oil seeping at the
  left rod seal" is gone once the item is *OK*. What was wrong stays in the engineer's send-back
  remark; the first round's item answers are not kept (BR1-03; § 9 Q9 asks KLA whether to keep
  them). S097's `settle_plan_job` leaves the plan alone while the job is `in_progress`
  (S097 § 5.5, first row), so no next job is made meanwhile.
- **The second *Mark job done*** (S098 § 5.6 with § 5.5's changes): a new `done_at`, at or after
  the latest send-back (`done_time_error`, BR1-02) and up to 7 days back, `done_meter` at that
  time, `timeliness` against the job's own frozen due point (D4), `needs_verification` copied
  again, the event `done` again, then `settle_plan_job`, which counts the next job from the plan's
  **latest** done time (S097 § 5.3 step 1, `ORDER BY done_at DESC`): this job's new one, unless
  another job of the plan was done later, which then rightly stays the base. So "the next due date
  counts from its new done time" holds whenever the sent-back job is the plan's latest done, with
  no new code.
- **A deactivated plan** does not stop send back: the job is then S098 D2's started job of a
  deactivated plan; it stays open and can be finished, and `settle_plan_job` makes no next job for
  the inactive plan (BR1-13).
- A job may be sent back more than once; each round adds *Sent back* and *Done* lines.

### 5.5 Mark done copies the setting (S098's route, changed)

In S098 § 5.6's step 4, the job update gains `needs_verification: plan["needs_verification"]` from
the locked plan row (6e) (S098 reads it there already: `meter_type_id` for `done_meter`). **The
floor** (BR1-02): after the locks, a plain read of the job's latest `sent_back` line (`SELECT
MAX(occurred_at) FROM pm_job_events WHERE job_id = %s AND event = 'sent_back'`; written only under
(6f), so current). **Where it is judged** (BS1-02): S098's `_event_time(raw, now, field,
not_before=None)` (it parses, rounds to the minute, then calls `job_time_error`) gains
`sent_back_at=None` and calls `done_time_error(moment, now, not_before, sent_back_at)` in place of
`job_time_error`; Mark done passes `sent_back_at`, Start passes neither (unchanged behaviour). One
place judges a time. 400 on `done_at`, shown beside the field in S098's done dialog. **The done
dialog's last line** (`PmJobDoneDialog.vue`, BS1-08, decided): when `job.plan.needs_verification`
is true, "You cannot change the job after this, unless an engineer sends it back."; else S098's
"The job can no longer be changed." Both stay true; no test reads the line. Nothing else in Mark
done changes. A job of an operator plan (S096 default: no
verification) is final at `done`; a maintenance plan's job waits on *To verify* unless the
engineer unticked *An engineer verifies each job*.

### 5.6 Locks

The database runs REPEATABLE READ: a locking read sees the latest committed row and does not start
the snapshot; the first plain read does. S099 follows S098 § 5.7's rule: every write route takes
the plan (6e), then the job (6f), then any node lock, **before any plain read**; the job's
`plan_id` and `equipment_id` are read before the transaction (S098's pre-read: they never change;
404 when missing).

**Verify** (one `transaction`):

1. `SELECT * FROM pm_plans WHERE id = %s FOR UPDATE` — (6e), exclusive.
2. `SELECT * FROM pm_jobs WHERE id = %s FOR UPDATE` — (6f), exclusive; the state and
   `needs_verification` from it.
3. `SELECT NOW()` (`pm_jobs._now`; reads no table). Then plain (the snapshot starts here): the
   access check (`load_node_for_user(cur, node_id, for_update=False, key=VERIFY_KEY)`, its 404 by
   `equipment:read`'s units, § 5.2), `current_person_id`.
4. `UPDATE pm_jobs … WHERE id` (held) and the event insert (shared FK locks: the job, held; the
   verifier's `people` row). 5. Commit.

**Send back** (one `transaction`):

1. (6e) the plan FOR UPDATE. 2. (6f) the job FOR UPDATE; the state from it.
3. `SELECT id, lifecycle FROM equipment WHERE id = %s LOCK IN SHARE MODE` with the job's
   `equipment_id` — (1) shared; the scrapped refusal from it (S098's Start order).
4. `SELECT NOW()`; plain: the access check, `current_person_id`, the plan's open job (§ 5.4 step 3).
   Plain is enough: every writer of a plan's job rows holds (6e) first (S097 § 5.7), and the
   snapshot starts after this route's (6e).
5. Open job `due`: `UPDATE pm_jobs … WHERE id = <open job>` (its row, exclusive; its
   `uq_pm_jobs_open_plan` entry removed) and its `cancelled` event insert.
6. `UPDATE pm_jobs … WHERE id = <this job>` (held; the unique check finds only the entry step 5
   removed in this transaction) and the `sent_back` event insert (the people row, shared).
7. Commit.

**No deadlock cycle** (against the LOCK ORDER notes of `equipment.py`, `pm_jobs.py`,
`pm_work.py`, `meters.py`):

- *Two writes on one plan's jobs* (verify, send back, S098's routes, S097's run and plan save) all
  take (6e) first, so they queue there. The second sees the first's committed job: a verify after a
  send-back reads `in_progress` → 409 `NOT_DONE_YET`; a send-back after a verify reads `verified` →
  409 `ALREADY_VERIFIED`.
- *The open job's row* is written only under its plan's (6e). Its other writers (S098's Start, an
  item, Mark done; S097's refresh and cancel) hold the same (6e) first, so none of them holds the
  open job's row while send back waits on it. **This is the one exception to S098's "(6f) one job
  per transaction"**: send back writes a second job row of the same plan, by a plain `UPDATE`
  under (6e), never with a second `FOR UPDATE`.
- *The node* (1) is taken shared after (6e) and (6f), as S098's Start; its writers never wait on a
  plan or a job. The scrap counts started jobs plainly after its node locks (S098 § 5.8), so a scrap
  either sees the sent-back job in progress (409) or makes send back read `scrapped` (409).
- *The unique key:* step 6's check may make another plan's job insert into a nearby gap of
  `uq_pm_jobs_open_plan` wait until this commit; that transaction holds nothing this route needs, so
  it is a wait, not a cycle. No module reads a job `FOR UPDATE` by `open_plan_id` (S097 § 5.7).
- *A rollback* undoes the open job's cancel with the send-back: the plan never loses its open job
  without the sent-back job taking its place.

The coder writes this into `pm_work.py`'s LOCK ORDER note, and into both (6f) places of
`equipment.py`'s note (BS1-07): the short line "(6f) the PM job row (pm_jobs, S098): always right
after its plan (6e)" gains "one job per transaction, except S099's send back, which also cancels
the plan's open, not started job by a plain UPDATE under the same (6e).", and the S098 paragraph
("S098: start, an item, the performer and done take (6e), then (6f), then a node …") gains "S099:
verify takes (6e), (6f); send back (6e), (6f), the node LOCK IN SHARE MODE, then may cancel the
plan's open job (above)."; `pm_jobs.py`'s note gains the line of § 3.

### 5.7 The PM list (S097's and S098's, changed)

- **Tabs:** *Due*, *Upcoming*, *To verify*, *Done* (`TABS`), as the mock-up. The tab reads "To
  verify (3)" with `counts.to_verify`, "To verify" when it is 0. Shown to every `pm_job:read`
  holder: a technician sees that his job waits for the engineer.
- **One row on a phone** (BR1-05): the four tabs must fit one row at 360 px. The `@device` test of
  § 8.4 checks it with "To verify (12)". **Decided fallback:** if it fails on any phone project, the
  label becomes "Verify (12)" (and "Verify" at 0) on every screen size; the count line keeps "12 to
  verify", the URL keeps `tab=to_verify`, and the test stays. No other layout change.
- **Query:** `tab=to_verify` in the URL, as the other tabs; *Due* stays the default.
- ***To verify*:** the jobs waiting for verification at the user's units, with the filters *Unit*
  and *Assigned to me* (S098: assignee or performer); **oldest done first** (`done_at ASC, id
  ASC`): a queue. Paged by the house pager (`PagerBar.vue`), as *Done*. Count line "3 to verify".
  Empty: "No PM jobs are waiting for verification." (with a filter: S097's "No PM jobs match these
  filters.").
- **A *To verify* row** (`PmJobRow.vue`): the badge *To verify* (`text-bg-warning`) and the
  timeliness badge (S098's *On time* / *Late*), the serial, "Done 27-10-2026 11:05" (the time too,
  `formatDateTime`: a queue is read by time; BS1-09); the machine;
  the plan; `findingsText`: "All OK", or the parts "2 Not OK", "1 Not done", "1 out of limits"
  joined with " · " (a zero part left out); "by Kannan".
- ***Done*** (S098's, narrowed): the jobs `verified`, or `done` with `COALESCE(needs_verification,
  0) = 0` (written with `COALESCE`: `NOT (… = 1)` would drop the NULL rows). Newest first, as
  S098. A verified row shows *Verified* (`text-bg-success`) instead of *Done*, and "Verified by
  Arun" after "by Kannan"; a final done row is S098's row, and both *Done*-tab rows keep S098's
  date only ("Done 27-10-2026", `formatDate`). Each finished job is on one tab only.
- **A sent-back job** (`in_progress` with a `sent_back` event) shows the badge *Sent back*
  (`text-bg-danger`) after *In progress* on *Due* and in *Me* › *Open work* (S098's `PmJobRow.vue`
  serves both). Its order on *Due* is S098's (started jobs first).
- **Me › Open work** (S098 § 5.11) needs no change: a sent-back job is `in_progress` and its
  performer's.

### 5.8 The job page (`PmJobView.vue`, S098's, changed)

**A job waiting for verification, for a holder of `pm_job:verify`** (`can_verify`): after the items
(read-only, as S098's done job), a card *Verify*:

- The line "Check the results above. Verify the job, or send it back with what must be done
  again."
- Two buttons side by side, each at least 48 px high, `gap-2` between them: *Send back*
  (`btn-outline-danger`, left) and *Verify job* (`btn-success`, right). Each opens
  `PmJobVerifyDialog.vue` in its mode.
- *Send back* is disabled when `can_send_back` is false, with the reason under it (visible on a
  phone, not a tooltip): "The plan's open job PM-2026-11-004 has been started, so this job cannot
  be sent back." or "This machine is scrapped. The job cannot be sent back." (BR1-06).

**The same job for a reader without the key** (a technician, IT admin): the line "Waiting for an
engineer to verify." under the header; no buttons.

**`PmJobVerifyDialog.vue`** (`FormModal.vue` through `useFormModal`; the page mounts it twice, one
per mode, prop `mode` `"verify"` or `"send_back"`):

| | *Verify job* | *Send back job* |
|---|---|---|
| Title | "Verify job" | "Send back job" |
| Facts | "PM-2026-10-014 · done 27-10-2026 11:05 by Kannan · 2 Not OK" (`findingsText`) | the same |
| Consequence | "The job is then closed. It cannot be changed or sent back." | "The job goes back to In progress. Kannan fixes it and marks it done again. The answers he changes replace the ones shown here; your remark stays on the history." |
| Extra line | when my person (`userPersonId`) is the job's `performed_by`: "You did this job. The record will say you verified your own work." (BR1-10) | when `open_job` is `due`: "The plan's open job PM-2026-11-004 is not started. It is cancelled, and made again from the latest done time." |
| Remark | "Remark (optional)", textarea, 500 characters | "What must be done again?", textarea, required |
| Save button | "Verify job" | "Send back job" |

Call contract (settings: *Self-check, repo items* (13)): `useFormModal({ path:
"/api/pm/jobs/<id>/verify"` or `"/api/pm/jobs/<id>/send-back"`, `blank: () => ({ remark: "" }),
toBody: (form) => ({ remark: form.remark }), afterSave, label: () => serial })`; `blank()` takes no
seed and `openCreate()` is called without one; the save calls `send(() => apiPost(path,
toBody(form)))`. `afterSave` emits `saved(job)`; the page shows the answer through FormModal's
`closed` event (the S077 rule, as S098's done dialog). A refusal on `remark` shows beside the
field; a 409 (another engineer acted first) shows above the field and the page reloads the job when
the dialog closes.

**A verified job:** the header badges *Verified* and the timeliness badge; under S098's card
"Performed by … · Started … · Done …" the line `verifiedText`: "Verified by Arun, 28-10-2026
10:00", plus " · the person who did the work" when self-verified, and the remark under it.

**A sent-back job** (`in_progress` with `sent_back` set): an `alert alert-warning` above the items:
`sentBackText`: "Sent back by Arun, 28-10-2026 10:00: Re-tighten the left rod seal and check
again." Then S098's in-progress page as it is.

**History** (S098's card): `PM_EVENT_LABELS` gains `verified: "Verified"` and `sent_back: "Sent
back"`; a `verified` line with `self_verified` true adds "the person who did the work"; the next
open job's `cancelled` line shows its remark, as S098's other cancelled lines.

**The one-tap path** of the common case: the engineer taps *PM* › *To verify* › the row › *Verify
job* › *Verify job*.

### 5.9 The database down

Both new routes go through `get_db()`: 503 while the database is down or missing (§ Yantra
Specifics, *DB may not exist*); the dialog shows the error above the field and stays open. No
background task, no alert, no file.

## 6. API

All under S098's `pm_work_bp` at `/api/pm`, ids `<int:…>`.

| Route | Key (decorator) | Body | Answer |
|---|---|---|---|
| `POST /api/pm/jobs/<id>/verify` | `pm_job:verify` | `{remark}` optional | 200 the job (§ 6.2); 400, 403, 404, 409 |
| `POST /api/pm/jobs/<id>/send-back` | `pm_job:verify` | `{remark}` required | 200 the job; 400, 403, 404, 409 |
| `GET /api/pm/jobs?tab=to_verify` (S097's route) | `pm_job:read` | `page`, `per_page`, `unit_id`, `assigned` | 200 § 6.3 |

### 6.1 Common rules

- A body that is not an object: `clean_body`'s 400. 401 without identity; 404 for a missing job and
  for one outside the user's `pm_job:read` units (the same answer).

### 6.2 The job (S098 § 6.2, gains)

```
{…S098's fields…,
 needs_verification,            # the job's copy: true / false / null (not done, or done before S099)
 awaits_verification,           # state done and needs_verification true
 verification: {at, by_name, self_verified, remark} | null,   # the verified event
 sent_back: {at, by_name, remark} | null,   # the latest sent_back event, for an in_progress job
 open_job: {id, serial, state} | null,      # the plan's open job, only while awaits_verification
 findings: {not_ok, not_done, out_of_limits},
 can_verify, can_send_back,
 events: [{…S098's…, self_verified}]}   # self_verified: bool on a verified line, null on others
```

- `can_verify` = `has_perm_at(VERIFY_KEY, site)` and `awaits_verification`. `can_send_back` =
  `can_verify`, the node not scrapped, and `open_job` null or `due`.
- `findings` counts the job's results (all zero for a job never started).
- `plan.needs_verification` (S098's) stays: the plan's setting now, shown nowhere on the job page.

### 6.3 The list (S097 § 6.1, S098 § 6.3, gains)

- `tab` takes `to_verify` (`enum_arg` over the new `TABS`); the 400 text becomes "tab must be one
  of: due, upcoming, to_verify, done".
- *To verify* and *Done*: § 5.7's rows, the same filters, paged (`page`, `per_page` as S098's
  *Done*); answer `{items, counts, total, page, per_page}`.
- `counts` gains `to_verify`: the jobs waiting for verification at the user's units with the same
  filters (one `COUNT` query, on every tab, so the tab label shows it).
- Each item gains `needs_verification`, `awaits_verification`, `findings` (on *To verify* and
  *Done*; null on *Due* and *Upcoming*), `verification: {at, by_name} | null` (a verified job) and
  `sent_back: {at, remark} | null` (an `in_progress` job with a `sent_back` event). Queries: one
  `GROUP BY job_id` over `pm_job_results` and one over `pm_job_events` (`event IN ('verified',
  'sent_back')`, latest per job) for the page's job ids; no query per row.

## 7. Design decisions

- **D1. A job whose plan needs no verification is final at `done`; it never becomes `verified`.**
  `verified` means an engineer signed it off (Plan § 4.3: "engineer *verified*"); writing it for a
  job nobody checked would make the record say something false (ISO 9001 § 7.5.3), and R03.14 could
  not count verified work. Compliance stays simple either way: it reads `BASE_STATES` (`done`,
  `verified`) and their `timeliness`, as S097 and S098 set up. The list stays simple: each finished
  job is on one tab, *To verify* or *Done*. Rejected: straight to `verified` at Mark done (one
  query fewer for *To verify*, but a false record, and a CIL job, R03.12, would read *Verified*
  daily with no engineer).
- **D2. The setting is copied onto the job at Mark done (migration v54).** The queue must not move
  when an engineer changes a plan: ticking verification on a weekly plan would otherwise pull a
  year of its done jobs into *To verify*, and unticking it would close jobs nobody checked. Copied
  at Mark done, the moment the rule applies, so an edit while the job is open still counts. A job
  done before S099 keeps NULL and stays final, so no existing row is updated. Rejected: reading the
  plan's current setting (the queue moves after the fact, and the record does not say what applied);
  copying at creation (S097's insert and refresh would change, and an edit while the job is open
  would not count).
- **D3. A job waiting for verification does not hold back the next job; send back cancels the
  plan's open job when it is not started.** S098 D10 made `done` a base state so a plan never stalls. Keeping
  that, a slow verification never stops PM: a weekly plan's next job comes on time while the last
  one waits. Send back must reopen the job, and the plan may have one open job only, so the next
  job, made from a done time that no longer stands, is cancelled with a line naming the sent-back
  job; it is made again from the latest done time. **The general rule** (BR1-04): the plan's open
  job is cancelled whichever done time it counted from (also when a later job of the plan waits
  too), and after the second *Done* the next job counts from the plan's latest done time (the
  sent-back job's when it is the latest). A started open job is real work: send back is then
  refused, and the engineer verifies and raises a ticket for the fault. Rejected: (a) no next job
  while a job waits (a verification left for three weeks stops a weekly plan with no sign on the
  list); (b) refuse send back whenever a next job exists (a daily or weekly plan's job could rarely
  be sent back).
- **D4. A sent-back job is judged again at its new done time.** The work was finished when it was
  finished right: `timeliness` is computed again at the second *Mark job done* against the job's
  frozen due point, and the next job counts from the new done time (R03.5: "a sent-back job's next
  due date counts from its new done time"). So a send-back can turn an on-time job late, which is
  what SMRP's PM compliance should show. The first *Done* line stays on the timeline, and the second
  *Done* may not be dated before the send-back (`done_time_error`), so the order of the record and
  the judgement cannot be back-dated (BR1-02). Rejected:
  keeping the first judgement (the compliance report would count rework as on time).
- **D5. Self-verification is allowed and recorded by the verifier's person on the event, not by a
  flag column** (Q5.2 a). The `verified` event names the verifier (`person_id`); the job names the
  performer; neither changes after verify, so "verified by the person who did the work" is derived
  as the improvement's `by_lead` is. "Did the work" means *Performed by*: an engineer who recorded
  the job on behalf of a fitter he worked with (Plan § 4.3) is not self-verifying. Rejected: a
  stored `self_verified` column (a second copy of the same fact); counting "recorded it" as "did
  it" (the paired engineer is the check the fitter needs).
- **D6. Each action opens one dialog with the facts, the consequence and the remark.** Verify is
  final, and the two buttons sit side by side on a phone: a mis-tap must not close a job. The
  ticket's send-back (S025: `tickets_core.MOVES["send-back"]`, `back_in_service` → `in_progress`,
  the event `sent_back` "Sent back", a required remark in `MoveDialog.vue`) and the improvement's
  verified close (S073) work the same way, and S099 keeps their words *Send back* and *Sent back*
  (writing style B: one word for one thing). Rejected: the mock-up's inline remark and two buttons
  (one mis-tap verifies for good).
- **D7. Verify is allowed on a scrapped machine; send back is not.** Verify closes the record of
  work done before the scrap; send back would open work on a read-only machine (S098 D15).
  Rejected: refusing both (a done job of a scrapped press would wait on *To verify* for ever).
- **D8. Verify and send back live in `pm_work.py`.** They act on one job, as S098's routes, and share
  its pre-read, access check and `job_detail`. Rejected: a new module (a third blueprint at
  `/api/pm` for two routes).
- **D9. The verify time is the server's now; no back-dating.** The engineer verifies at the screen;
  nobody verifies on someone's behalf. Rejected: S051's time field (no use case).

## 8. Tests and acceptance

### 8.1 Migration (`backend/tests/test_migration_v54.py`)

- A fresh database: `pm_jobs.needs_verification` `tinyint(1)`, NULL allowed, after `timeliness`;
  `chk_pm_jobs_verification` present.
- A v53 database with a plan and three jobs (`due`; `in_progress` with `started_at` and
  `performed_by_id`; `done` with `done_at`) migrates to v54; all kept, `needs_verification` NULL.
- The CHECK refuses (4025): `needs_verification` 1 on a `due` job; on an `in_progress` job; a
  `verified` job with 0; a `verified` job with NULL. Every `verified` and `in_progress` test row also
  carries `done_at` (for `verified`), `started_at` and `performed_by_id`, so `chk_pm_jobs_done` and
  `chk_pm_jobs_started` pass and the refusal is the new CHECK's (BR1-11). It passes: `done` with NULL, 0 and 1;
  `verified` with 1.
- A re-run of v54 changes nothing (`_schema()` equal).

### 8.2 Backend

**Core** (`test_pm_work_core.py`, no database, written first): `awaits_verification` for each state
with 0, 1 and None; `verify_error`, every row of § 5.1's table; `verify_remark` (absent, empty and
spaces → None; "x" kept; 500 kept, 501 refused; a number refused; needed and empty →
`SEND_BACK_REMARK`); `clean_remark` with and without a needed message; `done_time_error` (at the
send-back time allowed, one minute before → `done_before_send_back` with "28-10-2026 10:00"; no
send-back and before `started_at` → `done_before_start`; both None → `job_time_error`'s answer;
8 days back → `TIME_TOO_OLD`);
`self_verified` (equal, different, either None); `open_job_started` and `open_job_cancelled` texts.

**The API** (`test_pm_verify_api.py`; each test its own site, unit, machine and plan, made as
S098's tests: the plan by `POST /api/pm/plans` as an engineer with a past seed, so S097 makes the
job at the save; the job started, filled and marked done by API as the technician; people by
`user_at_sites`):

- **Mark done copies the setting:** a plan with the default (maintenance) → the done job has
  `needs_verification` 1 and `awaits_verification` true; a plan with `needs_verification: false` →
  0, false; the plan's setting changed afterwards (`PUT`) → the job unchanged.
- **Verify:** an engineer of the site → 200, `verified`, the event `verified` (`person_id` his
  person, the remark kept), `done_at` and `timeliness` unchanged, `can_verify` false; a manager →
  200; an engineer who performed the job → 200 and `verification.self_verified` true, the event's
  `self_verified` true; another engineer → false; admin (the dev bypass, no Team record) → 200,
  `person_id` NULL, false. Refusals: technician, operator, supervisor, IT admin, storekeeper → 403;
  an engineer of another site → 404; a missing id → 404; a `due` and an `in_progress` job → 409
  `NOT_DONE_YET`; a second verify → 409 `ALREADY_VERIFIED`; a final `done` job (0, and NULL set in
  the test by `UPDATE`) → 409 `NO_VERIFICATION`; a `cancelled` job → 409 `JOB_CANCELLED`; a remark of
  501 characters → 400 `remark`; a remark `5` → 400 `remark`. The machine scrapped after done (row
  updated in the test) → verify 200.
- **Send back:** no remark, and spaces only → 400 `remark` `SEND_BACK_REMARK`; with a remark → 200,
  `in_progress`, `done_at`, `done_meter`, `timeliness`, `needs_verification` NULL, `open_plan_id` the
  plan, `started_at` and the results kept, the event `sent_back` (`from_state` `done`, `to_state`
  `in_progress`, the remark), `sent_back` in the answer, `can_work` true for the technician. Then an
  item `PUT` → 200; *Mark job done* again 3 days later (`done_at` in the body) → `done` with the new
  `done_at`, `timeliness` `late` when past the window (S095's figures), `needs_verification` 1; the
  events in order `started`, `done`, `sent_back`, `done`. A second done dated one minute before the
  send-back → 400 `done_at` "Done must be at or after it was sent back, …"; a check changed from
  `not_ok` to `ok` holds `ok` and remark NULL (the first answer not kept, BR1-03). The plan's card `schedule.next_due`
  (S097's `plan_schedules`) counts from the new `done_at`. A scrapped machine → 409
  `SCRAPPED_MESSAGE`. A technician → 403.
- **The plan's open job:** a monthly plan whose job was done; S097's `generate` run with
  `pm_jobs._now` fixed 28 days on makes the next job (`due`); send back → 200, that job `cancelled`
  with the remark `open_job_cancelled(<serial>)` and its `cancelled` event, the sent-back job
  `in_progress`; marked done again, the next run makes a new job (a new serial) from the new
  `done_at`. The open job started by API instead → send back 409 `open_job_started(<serial>)`, and
  nothing changed (both jobs as before, no event). Verify with an open job → 200, it is untouched.
- **Two jobs waiting** (BR1-04): J1 done and waiting; the run makes J2, J2 done and waiting; the run
  makes J3 (`due`). Send back J1 → J3 cancelled, J1 `in_progress`. Send back J2 now → 409
  `open_job_started(<J1>)`. J1 done again with a `done_at` before J2's → the next run makes J4
  counted from J2's `done_at` (the plan's latest done).
- **The page:** a waiting job read by an engineer → `can_verify` true, `open_job` set when one
  exists, `findings` (one `not_ok`, one reading `high` → `{not_ok: 1, not_done: 0, out_of_limits:
  1}`); by a technician → `can_verify` false; `can_send_back` false with a started open job.
- **The lock:** with the plan's row held `FOR UPDATE` by a second connection, a verify waits (the
  test releases it, and the verify succeeds): (6e) is taken first.
- **The database down** (`db_down`): both routes → 503.

### 8.3 Existing tests that change or run again

- `backend/tests/test_rbac.py`: `test_role_matrix` — `pm_job:verify` joins the rows of the engineer
  and the manager; the comment above the rows gains "S099: pm_job:verify to the engineer (so the
  manager)". New `test_pm_job_verify_key`: its holders are exactly those two roles
  (`compute_permissions` over `ROLES`), it is in `SITE_SCOPED`, and every holder also holds
  `pm_job:read`.
- `backend/tests/test_pm_jobs_api.py`: S098's one *Done*-tab test,
  `test_the_done_tab_newest_first_and_paged` (two plans by `create(…)` with the default
  verification), makes its plans with `needs_verification: false`, so its jobs are final and stay on
  *Done* (BS1-06); the 400 text test reads "tab must be one of: due, upcoming, to_verify, done". New:
  `tab=to_verify` lists a waiting job and not a final one, the oldest done first; `per_page=1` with
  two → `total` 2; a verified job is on *Done* with `verification`, not on *To verify*; a final job
  with NULL (row updated) is on *Done*; `counts.to_verify` on the *Due* tab; `findings` on a row; an
  `in_progress` job after a send-back carries `sent_back` on *Due*. The coder names every changed
  line.
- Green unchanged (to verify by the run): `backend/tests/test_pm_work_api.py` (its *Done* tests
  assert the state `done`, which a waiting job has) and `test_pm_work_core.py`'s remark tests
  (they test the remark rules through `validate_result`, which the rename keeps);
  `backend/tests/test_pm_generate.py` and `test_pm_jobs_core.py` (the rename of `_cancel` keeps
  `settle_plan_job`'s behaviour);
  `backend/tests/test_modules.py` (`LATEST_VERSION` 54), `test_migration_squash_v41.py`,
  `test_migration_v51.py`, `test_migration_v52.py`, `test_migration_v53.py`;
  `test_schema_docs_shell.py` once `tooling\schema-docs.bat write` has run;
  `tooling/tests/test_line_width.py` (every new and changed `.py` line at most 120 characters).
  `backend/tests/conftest.py`: no change (no new table in `_TABLES`).
- `frontend/tests/pmLabels.test.js`: `findingsText` (all zero → "All OK"; `{not_ok: 2, not_done:
  1, out_of_limits: 0}` → "2 Not OK · 1 Not done"), `verifiedText` with and without
  `self_verified`, `sentBackText`, `jobBadges` for to verify, verified and sent back; `jobsQuery`
  with `tab=to_verify` and a page; `countText("to_verify", counts, 3)` → "3 to verify" (BS1-01).
- `frontend/e2e/pm-job.spec.js` (S098's): `S098: a technician starts a due job, fills each item and
  marks it done` — its last step (`page.goto("/pm?tab=done")`, then the row by serial) becomes
  `"/pm?tab=to_verify"`: the *PM* list's *To verify* tab lists the serial (its plan has
  the default verification); its title stays.
  Every other S098 test stays true (they stop at `done`).
- `frontend/e2e/pm-jobs.spec.js`: no change (checked in the code, BS1-06: S098 added no *Done*-tab
  test there). `frontend/e2e/me.spec.js`, `screens.spec.js`: unchanged and green (the tab
  links are found by name; a new tab adds one).

### 8.4 Automated (e2e, `frontend/e2e/pm-verify.spec.js`, new)

Set-up by API in the spec, as S098's `pm-job.spec.js`: `meterMachine(testInfo, tag, { unit:
"SMTW.MCC2" })` (`frontend/e2e/support/meters.js`), a plan by `POST /api/pm/plans` as the engineer
(`apiAs`) with two items (a Check, a Task), every 10 days, last done 20 days ago, the technician as
assignee (`personId("technician")`); the job started, filled and marked done by API as the
technician. Each test finds its own job by its serial. Untagged.

- **important** `S099: an engineer verifies a done job from the To verify tab` — as the engineer:
  *PM*, the tab `"To verify"`, the row with the serial and `"1 Not OK"` (the check answered Not OK
  with a remark); the job page; `"Verify job"` → the dialog (`expectDialogFits`) → `"Verify job"`:
  the badge `"Verified"`, the line `"Verified by"`, the history line `"Verified"`; back on *PM*: not
  on *To verify*, on *Done* with `"Verified"`.
- **important** `S099: send back needs a remark, and the technician sees it and marks the job done
  again` — as the engineer: `"Send back"` → the dialog (`expectDialogFits`) → `"Send back job"`
  with no remark → `"Say what must be done again."` beside the field; typed "Re-tighten the left rod
  seal" → saved: the badge `"In progress"`, `"Sent back by"` with the remark. As the technician:
  *Me* shows the job with `"Sent back"`; the job page shows the remark; change the check to *OK*,
  *Mark job done*. As the engineer: the job is on *To verify* again; the history reads `"Done"`,
  `"Sent back"`, `"Done"`.
- **important** `S099: a job whose plan needs no verification ends at Done` — the plan made with
  `needs_verification: false`: after done, not on *To verify*; on *Done* with `"Done"`; the job page
  as the engineer has no `"Verify job"`.
- **important** `S099: an engineer verifying his own job is recorded` — the engineer starts the job
  with himself as performer, fills it and marks it done by API; *Verify job*: the dialog shows `"You
  did this job"`; after it, the line `"the person who did the work"` on the page and in the history.
- `S099: the technician and IT admin see no Verify job` — both open a waiting job: `"Waiting for an
  engineer to verify."`, no `"Verify job"`, no `"Send back"`.
- `S099: the four PM tabs fit the phone width on one row` (`@device`, BR1-05) — with a waiting job
  so the label carries a count: the four tab links' bounding boxes share one `y`, and
  `expectNoSidewaysScroll`. Runs on `desktop-chromium` at Normal and on `phone-webkit` at Full by
  the tag; the coder runs it once on `phone-webkit` (`--project=phone-webkit e2e/pm-verify.spec.js
  -g "S099"`, Docker Desktop running). A failure takes § 5.7's decided fallback.

**Runs** (settings: *Browser tests*): targeted `tooling/run-e2e-tests.bat e2e/pm-verify.spec.js
e2e/pm-job.spec.js e2e/pm-jobs.spec.js e2e/me.spec.js e2e/screens.spec.js`; the whole suite at
Normal once at the end; the `phone-webkit` run of the `@device` test above. No shared frontend file
changes (no router, `api.js`, `FormModal.vue`,
`useFormModal.js` or `e2e/support/` change), so no extra WebKit run.

### 8.5 On a real device

None. The new controls are two buttons and a dialog with a text field, all of which a browser
engine judges; S098's rows (the Wi-Fi drop, the gloved thumb, the keypad) cover the job page on the
floor.

### 8.6 Acceptance and the SMTW-Review point

- All unit suites green; `tooling\schema-docs.bat check` exits 0; the targeted and the Normal
  browser runs green.
- By screen, on S098's acceptance job ("Monthly hydraulic check" on a press at SMTW, done by the
  technician): the engineer opens *PM* › *To verify*, sees the job with its findings, sends it back
  with "Re-tighten the left rod seal"; the technician sees *Sent back* on *Me*, fixes the item and
  marks it done; the engineer verifies it; the job reads *Verified*, and its next job counts from the
  second done time (the plan's latest).
- **§ SMTW-Review point** (for `.claude/CLAUDE.md`): "**PM verification (S099):** a finished job
  waits on *To verify* only when its own `needs_verification` (copied from the plan at *Mark job
  done*) is 1; nothing else moves a job in or out of the queue. Verify and send back take the plan
  (6e), then the job (6f), before any plain read, and write their timeline line (`verified`,
  `sent_back`) in the same transaction. Send back clears `done_at`, `done_meter`, `timeliness` and
  `needs_verification`, cancels the plan's open, not started job (the one exception to one job per
  transaction), and is refused when that job is started. `verified` is written only by verify, never
  for a job nobody checked. A path that writes `verified` elsewhere, or reads the plan's current
  setting for the queue, breaks R03.5."

## 9. Open questions and assumptions

All choices below were **decided by the orchestrator under KLA's go-ahead of 01-11-2026 ("Start
work on PM module … Do those steps … stop only for real show stoppers"), to confirm at gate B.**

- **Q1.** A job whose plan needs no verification is final at `done`, never `verified` (D1).
- **Q2.** The plan's setting is copied onto the job at Mark done, in a small migration v54 (D2);
  S097's and S098's columns do not keep the setting that applied. A departure from the roadmap's
  R03.5 "Migrations: none". Jobs done before S099 stay final (expected: none, or a few pilot jobs).
- **Q3.** A waiting job does not hold back the next job; send back cancels the plan's open job
  when not started and is refused when it is started; the next job counts from the plan's latest
  done time (D3). New rule.
- **Q3b.** The second *Done* may not be dated before the send-back (BR1-02, `done_time_error`).
- **Q4.** A sent-back job is judged again at its new done time and may turn late (D4).
- **Q5.** Self-verification means the verifier is the job's *Performed by*; recording on behalf
  does not count (D5).
- **Q6.** Verify and send back open a dialog, a departure from mock-up 04's inline buttons (D6).
- **Q7.** Verify works on a scrapped machine; send back does not (D7).
- **Q8.** *To verify* is shown to every PM reader, with its count, oldest first; if the four tabs
  do not fit a phone row, the label becomes "Verify (12)" (§ 5.7).
- **Q9. For KLA at gate B (ISO 9001 § 7.5.3): keep the first round's item answers?** Decided
  tonight: **(a) no** — the rework overwrites the answers in place (S098's rule); the timeline keeps
  the send-back remark and both done times; no new code. Alternative: **(b)** on a sent-back job, an
  item save that changes a filled result writes a job event `result_changed` with the old answer
  and remark ("Was: Not OK — Oil seeping …"), as the improvement timeline shows "Was: …": the full
  record, one more event kind and a few lines in S098's item route; a later step if KLA wants it.
- **A1. S095–S098 as coded** (`refs/steps/S098`, 5b340d0; staleness review s1 checked every name).
  The original text: S098 is in brief review tonight; the staleness review confirms the
  names of § 3, in particular `state_error`'s `done` row, the pre-read, `job_detail`, `PmJobRow.vue`,
  the *Done* tab's paging and `assigned=me`, `PM_EVENT_LABELS`, and that S098's Mark done reads the
  plan row under (6e). S098's code has the remark rules in `_remark`; S099 renames it
  `clean_remark` (§ 5.1).
- **A2. `update_row` writes `None` as NULL** (fact: `backend/db_helpers.py` `update_row` passes
  the values as query parameters, and PyMySQL sends `None` as `NULL`; the send-back test checks it).
- **A3. Every holder of `pm_job:verify` holds `pm_job:read`** (`ROLE_INCLUDES`: engineer includes
  technician includes operator); pinned by `test_pm_job_verify_key`.
- **Notes for later steps:** R03.7 may add *Waiting for verification* and *Sent back* alerts on the
  `verified` / `sent_back` events; R03.12's CIL plans default to no verification (S096), so their
  jobs end at `done`; R03.14 counts `BASE_STATES` with `timeliness`, and may count self-verified jobs
  by § 4.2's rule; R03.9's skip leaves `needs_verification` NULL.
- **Size:** 21 code and test files; one column, two routes, one dialog, one tab. No split.
- **Standards *to verify*:** SMRP's metric number.
- **No defining question for KLA.**

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md`, answered 02-11-2026

| Finding | Answer |
|---|---|
| BR1-01 minor | Accepted (a). `JOB_CLOSED` replaced by S098's `JOB_CANCELLED` ("This job was cancelled.") in § 3, § 5.1, § 8.2; § 3 lists S098's revised names (`JOB_DONE`, `JOB_CANCELLED`, `REMARK_NEEDED`, `DONE_BEFORE_START`, `job_time_error`, `validate_result`, the `remark: null` rule). |
| BR1-02 minor | Accepted (a). New `done_time_error` and `done_before_send_back`: the second *Done* is at or after the latest `sent_back` time, with its own message (§ 5.1, § 5.4, § 5.5, D4, § 8.2, Q3b). |
| BR1-03 minor | Accepted (a). § 1.3, § 2, § 5.4, the send-back dialog's consequence and Plan.MD's *Built (S099)* line state that the rework overwrites the item answers in place and the timeline keeps the send-back remark and both done times; a test pins it (§ 8.2). The alternative (b), `result_changed` events, is § 9 Q9 for KLA at gate B. |
| BR1-04 minor | Accepted (a). The general rule in § 1.4, § 4.2, § 5.4, D3: the plan's open job is cancelled whichever done time it counted from; the next job counts from the plan's latest done time. Texts renamed and reworded (`open_job_started`, `open_job_cancelled`; the answer's `open_job`); the two-waiting-jobs API test added (§ 8.2). |
| BR1-05 minor | Accepted (a). One `@device` test that the four tabs fit one row (§ 8.4); the fallback decided now: "Verify (12)" on every screen size if it fails (§ 5.7, Q8). |
| BR1-06…BR1-14 nits | All accepted. 06: "This machine is scrapped. The job cannot be sent back." (§ 5.1, § 5.8). 07: the 404 is by `equipment:read`'s units, safe after `require_perm(VERIFY_KEY)` (§ 5.2, § 5.6). 08: "1 Not done". 09: ISO 27001 A.5.15 in § 2. 10: "You did this job. The record will say you verified your own work." 11: the CHECK test rows satisfy `chk_pm_jobs_done` and `chk_pm_jobs_started` (§ 8.1). 12: `pm-jobs.spec.js` checked as S098 left it (§ 8.3). 13: send back on a deactivated plan (§ 5.4). 14: `clean_remark(value, needed_message)` named; S098's `validate_result` and `verify_remark` both call it (§ 3, § 5.1, § 8.3). |

### Staleness s1 — `2-brief-review-s1.md`, answered 02-11-2026

| Finding | Answer |
|---|---|
| BS1-01 minor | Accepted (a). § 3 names `PM_TABS` (gains `to_verify`), `jobsQuery` (sends `tab=to_verify` and its `page`) and `countText("to_verify", counts, total)` → "3 to verify" from the paged `total`; § 8.3 adds their `pmLabels.test.js` cases. |
| BS1-02 minor | Accepted (a). `_event_time` gains `sent_back_at=None` and calls `done_time_error` in place of `job_time_error`; Start passes neither; one place judges a time (§ 5.1, § 5.5). |
| BS1-03…BS1-09 nits | All accepted. 03: `done_before_start(started_at)`, a function (§ 3, § 5.1, § 8.2). 04: `_cancel` renamed `cancel_job`, not taken out; `pm_jobs.add_event` named as the event writer; `pm_jobs.py`'s LOCK ORDER note gains one line (§ 3, § 5.3, § 5.4, § 5.6, § 8.3). 05: `_remark(raw, outcome)` renamed `clean_remark(value, needed_message)`, `validate_result` passing `REMARK_NEEDED.get(outcome)` or None (§ 3, § 5.1, § 8.3). 06: one *Done*-tab test, `test_the_done_tab_newest_first_and_paged`; no change in `pm-jobs.spec.js`; the `pm-job.spec.js` line is the `/pm?tab=done` step (§ 8.3). 07: both (6f) places of `equipment.py`'s note gain the S099 text (§ 5.6). 08: decided: the done dialog's last line reads "You cannot change the job after this, unless an engineer sends it back." when the plan needs verification, S098's line otherwise; `PmJobDoneDialog.vue` joins *Where* (21 files) (§ 3, § 5.5). 09: the *To verify* row alone shows the time ("Done 27-10-2026 11:05", `formatDateTime`); both *Done*-tab rows keep S098's date only (§ 5.7). Header `Baseline:` set to `refs/steps/S098` (5b340d0). |
