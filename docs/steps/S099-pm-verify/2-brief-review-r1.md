```
Step: S099 — Verify and send back a PM job
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 02-11-2026
```

Reviewed against: c9cd091 + uncommitted S095, S096 (S097 and S098 are not coded: their approved
briefs, `docs/steps/S097-pm-jobs-due/1-brief.md` and `docs/steps/S098-pm-job-phone/1-brief.md`,
stand in for their code).

# S099 — brief review, round 1

**Verdict: no blocker or major finding. Five minor findings and nine nits.** The design holds
against the roadmap (R03.5, Q5.1 a, Q5.2 a), Plan § 4.3 and § 3, and the S095–S098 briefs. The
migration, the lock sequences and D1–D9 are sound; the minors are two rules the coder would
otherwise decide alone (the second *Done* time's floor, what the rework does to the first round's
item answers), one edge of D3 the brief does not state (two jobs waiting), one drifted S098 name,
and one layout at risk with no test. Facts file read: `scratch/brief-facts-S099.md`; the names it
marks "planned in S097, S098" were checked by hand against those two briefs.

Full track, round 1 of up to 3. This review is the only check before coding (KLA delegated
gate A), so the nits are worth fixing too.

## Minor

### BR1-01 — minor — § 3, § 5.1: `JOB_CLOSED` is not an S098 name

**Problem.** § 3 lists `JOB_CLOSED` among S098's `pm_work_core` names, and § 5.1 gives it the text
"This job was cancelled. It cannot be worked." S098 § 5.1 defines `JOB_DONE` ("This job is done and
cannot be changed.") and `JOB_CANCELLED` ("This job was cancelled.", for `cancelled` and `skipped`,
S098 BR1-16). There is no `JOB_CLOSED` and no "It cannot be worked."

**Why it matters.** The coder either invents a third constant beside S098's two (a second copy of
one message) or stops to ask. This brief is the only check before coding.

**Options.** (a) § 3, § 5.1 and § 8.2 name `JOB_CANCELLED` with S098's text; `verify_error` answers it
for `cancelled` and `skipped`. **Recommended.** (b) Keep a PM-verify text of its own ("This job was
cancelled. It cannot be verified."): one more message for the same state; not worth it.

### BR1-02 — minor — § 5.4: the second *Mark job done* may be dated before the send-back

**Problem.** The second *Mark job done* is "S098 § 5.6, unchanged apart from § 5.5": its floor is
`job_time_error(done_at, now, not_before=started_at)`. A technician may therefore date the
second *Done* before the *Sent back* line, even before the first *Done*. The history (by
`occurred_at`) then reads *Done*, *Done*, *Sent back*; D4's "finished when it was finished right"
is judged at a time before the rework was asked for; and the next job counts from it.

**Why it matters.** The brief says the record shows the job was done twice (§ 2, ISO 9001
§ 7.5.3); a second *Done* dated before the send-back makes that record false, and `timeliness` can
be gamed back to *On time* by back-dating. The coder would otherwise not touch S098's floor.

**Options.** (a) For a job with a `sent_back` event, the floor is the latest `sent_back`
`occurred_at` (it is later than `started_at` by construction), with its own message: "Done must be
at or after it was sent back, 28-10-2026 10:00." `job_time_error` already takes `not_before`; the
shell passes the later of the two and the message by which one it is. One read (the latest
`sent_back` line, under (6f)). **Recommended.** (b) Keep `started_at` as the floor and state the
oddity in D4 and Plan.MD. Simpler, but the record can lie.

### BR1-03 — minor — § 1.3, § 5.4, D4: the rework overwrites the first round's item answers

**Problem.** After a send-back the job is S098's `in_progress` job: a changed item replaces its
`outcome`, `value`, `limit_state` and `remark` (S098 § 5.4, "A result is never emptied" and the page
sends `remark: null` on *OK*, BR1-02). So when the technician changes the *Not OK* item to *OK*, the
fault text he wrote ("Oil seeping at the left rod seal") is gone from the job; only the engineer's
send-back remark and the first *Done* line remain. The brief does not say so; § 2 says "the record
shows the job was done twice", which is true of the timeline only.

**Why it matters.** This is a records decision (ISO 9001 § 7.5.3) the coder cannot take, and R03.10
(a ticket from a *Not OK* item) and R03.14 read the results. KLA should know the item-level record
of the first round is not kept.

**Options.** (a) Accept and state it: in § 1.3 or D4 ("the items of the first round are changed in
place; what was wrong is in the engineer's send-back remark and the first round's remarks are not
kept"), and in Plan.MD's *Built (S099)* paragraph; a note for a later step if KLA wants the first
answers kept. **Recommended** (no new code; it is the honest statement of what S098's rule does).
(b) On a sent-back job, an item save that changes a filled result also writes a job event
`result_changed` with the old answer and remark ("Was: Not OK — Oil seeping …"), as the
improvement timeline shows "Was: …". Keeps the record, one more event kind and a few lines in
S098's item route; a design choice for KLA, not for tonight.

### BR1-04 — minor — § 5.4 step 3, D3: two jobs waiting for verification

**Problem.** D3 lets a plan's next job come while the last one waits, so a plan can hold **two**
jobs waiting (J1 `done`, J2 `done`, J3 `due`): a weekly plan with a two-week verification lag,
which D3 names as the case to keep working. The brief's rules then read oddly:
- *Send back J1:* the "next job" query finds J3 and cancels it with "PM-J1 was sent back. The next
  job is made again when that job is done." J3 counted from J2's done time, not J1's; the remark
  names the wrong job, and the cancel is forced only by the one-open-job rule.
- *J1 done again:* `settle_plan_job` counts from the plan's **latest** base (`schedule_inputs`
  step 1: `ORDER BY done_at DESC`), which is J2 when J1's second done time is earlier. So "the next
  job counts from the sent-back job's new done time" (R03.5, § 1.3, § 5.4, § 8.2's
  `schedule.next_due` test) holds only when the sent-back job's new done time is the latest.
- *Send back J2 while J1 is in progress again:* the open job is J1 (`in_progress`) → 409 "The next
  job PM-J1 has been started …" — J1 is the earlier job.

**Why it matters.** The rule is right (one open job; the next job counts from the latest done), but
the brief states a narrower rule and the coder's tests will pin the narrow one. The texts name "the
next job" where it may be an earlier one.

**Options.** (a) State the general rule in D3 and § 5.4: "send back cancels the plan's open, not
started job, whichever done time it counted from; it is refused when the plan's open job is
started; after the second *Done* the next job counts from the plan's latest done time (the
sent-back job's when it is the latest)". Word the two texts so they hold in both cases: the cancel
remark "PM-2026-10-014 was sent back, so the plan's open job is cancelled. The next job is made
again from the latest done time."; the refusal "The plan's open job PM-2026-11-004 has been
started, so this job cannot be sent back. …". Add one API test with two waiting jobs (send back
the older; the open `due` job cancelled; the second done earlier than J2's → the next job counts
from J2). **Recommended.** (b) Refuse send back when another job of the plan also waits for
verification ("Verify or send back PM-… first"): simpler texts, one more 409, and the engineer
must act on the newer job first. Defensible, but D3's reason (a slow verification never stops PM)
argues for (a).

### BR1-05 — minor — § 5.7, § 8.4: four tabs on a phone, no test that they fit

**Problem.** *Due*, *Upcoming*, *To verify (12)*, *Done* as `nav nav-tabs` links: at 16 px with
Bootstrap's 1 rem side padding that is about 380 px, the width of the iPhone 14's 390 px and a
360 px Android. Bootstrap wraps the tabs onto a second row then; nothing breaks, but the bar is
no longer one row. The brief says `screens.spec.js` is unchanged and names no layout test; *Me*
has one for its three tabs (`S031: the three tabs fit the screen width`).

**Why it matters.** A browser can judge this (settings: *Browser tests*, the `@device` tag), so it
must not be left to a person; the list is the engineer's queue and the technician's daily screen.

**Options.** (a) One `@device` test in `pm-jobs.spec.js` or `pm-verify.spec.js`: "the four PM
tabs fit the phone width on one row" (the four links' bounding boxes share one `y`, and
`expectNoSidewaysScroll`), with a count in the label; if it fails on `phone-webkit`, shorten the
label to *Verify (12)* or drop the count into a badge. **Recommended.** (b) Decide the shorter
label now and skip the test: against the mock-up's words, and still unchecked.

## Nits

- **BR1-06** (nit) § 5.8: the disabled *Send back*'s reason on a scrapped machine says "S098's
  scrapped text"; S098's line is "This machine is scrapped. The job cannot be started." and
  `SCRAPPED_MESSAGE` is "This record is scrapped and cannot be changed". Give S099 its own line:
  "This machine is scrapped. The job cannot be sent back."
- **BR1-07** (nit) § 5.6 step 3: "`load_node_for_user(…)` with the `pm_job:read` predicate" — its
  404 is by `equipment:read`'s units (`_can_access`, `accessible_unit_ids(cur)` with no key; S098
  BR1-19); say so, and that the route is safe because `require_perm(VERIFY_KEY)` ran first and the
  engineer holds `equipment:read`.
- **BR1-08** (nit) § 5.7 `findingsText`: "2 Not OK · 1 not done · 1 out of limits" mixes the badge's
  "Not done" with "not done" (style B: one word for one thing). Use "1 Not done".
- **BR1-09** (nit) § 2: name ISO/IEC 27001:2022 A.5.15 (access control) for `pm_job:verify` at the
  job's site, as S097 and S098 did for their keys; one line.
- **BR1-10** (nit) § 5.8: "You did this job. Your verification is recorded as such." — "as such" is
  vague for the person reading it. "You did this job. The record will say you verified your own
  work."
- **BR1-11** (nit) § 8.1: the `verified` rows of the CHECK tests must also satisfy `chk_pm_jobs_done`
  (`done_at`) and `chk_pm_jobs_started` (`started_at`, `performed_by_id`), else the test refuses
  for the wrong reason; say it, as S098 § 8.3 did for `test_pm_generate.py`'s row.
- **BR1-12** (nit) § 8.3: "`pm-jobs.spec.js`: unchanged and green" — S098 § 3 says that spec gains
  "the *Done* tab" while its § 8.4 lists no such test. The coder checks the spec as S098 left it: a
  *Done*-tab test whose plan has the default verification moves to *To verify* and must make its
  plan with `needs_verification: false`.
- **BR1-13** (nit) § 5.4: say that send back is allowed on a deactivated plan (§ 5.3 says it for
  verify), and that the job then is S098 D2's started job of a deactivated plan: it stays open and
  can be finished, and `settle_plan_job` makes no next job for the inactive plan.
- **BR1-14** (nit) § 5.1: `verify_remark` says "the coder makes them one function if S098 has them
  inline" — S098 § 5.1 puts the remark rules inside `validate_result`. State the function's name
  now (`remark_or_error(value, needed_message)` or the like) so S098's `validate_result` and
  `verify_remark` both call it; the coder then changes S098's core with its tests green.

## Checked and found consistent

- **Roadmap and plan.** R03.5's goal, key (`pm_job:verify`, engineer, `SITE_SCOPED`), "remark
  required" on send back, Q5.1 a (a flag per plan, default yes for maintenance), Q5.2 a
  (self-verification, recorded); Plan § 4.3's loop and "engineer can send back to *in progress*";
  Plan § 3's table already lists `pm_job:verify` for the engineer and manager only (line 142). The
  departure from "Migrations: none" (Q2, D2) is reasoned and small; D2's rejected alternatives are
  the right ones.
- **Migration v54.** `ADD COLUMN IF NOT EXISTS … AFTER timeliness` and `ADD CONSTRAINT IF NOT
  EXISTS` follow v50's `chk_people_vendor` (`backend/local_db.py:1176`). The CHECK gives exactly
  D1: `verified` ⇒ `needs_verification = 1`, so a job of a no-verification plan can never be
  `verified`; `done` allows NULL, 0, 1; `skipped` and the open states need NULL. A sent-back row
  (`in_progress`, `done_at`, `done_meter`, `timeliness`, `needs_verification` all NULL) passes
  `chk_pm_jobs_done`, `chk_pm_jobs_started` (S098, `started_at` and `performed_by_id` kept) and the
  new CHECK. No existing row changes; S097 writes `due`/`cancelled`, S098 `in_progress`/`done`, so no
  `_PRECONDITIONS` entry is right. `pm_job_events.event VARCHAR(30)`, `remark VARCHAR(1000)` hold
  the two new events and a 500-character remark.
- **D1, D3, D4, D5.** `BASE_STATES` keeps `done` and `verified`, so a waiting job is a base and the
  plan never stalls; `uq_pm_jobs_open_plan` is why the open job must be cancelled before the
  sent-back job becomes `in_progress`, and the brief writes both under one (6e) in the right
  order (cancel first, then reopen). `timeliness` recomputed at the second done against the job's
  frozen copies (S098 D2) is S095's `timeliness(due, done_on, done_meter)`. `self_verified` from
  the event's `person_id` against `performed_by_id` is the rule of `improvements._closed`'s
  `by_lead` (`backend/improvements.py:645`); admin with no Team record is never self-verified.
- **Locks.** (6e) → (6f) → the node shared → `SELECT NOW()` → plain reads, as S098 § 5.7; the
  pre-read of `plan_id` and `equipment_id` before the transaction; the next job written by a plain
  `UPDATE` under (6e) and never read `FOR UPDATE` by `open_plan_id` (S097 § 5.7); the exception to
  "one job per transaction" named for both LOCK ORDER notes; the no-cycle argument holds against
  `equipment.py`'s note (read) and S097/S098's.
- **Permissions.** `("maint_engineer",)` gives the manager through `ROLE_INCLUDES`
  (`config_rbac.py:82`); every holder holds `pm_job:read` (engineer → technician → operator). The
  checks' order copies S098 § 5.2. `test_role_matrix`'s rows for `maint_engineer` and `maint_manager`
  are the two to change (`backend/tests/test_rbac.py:283`).
- **S097/S098 names relied on** (all found in those briefs with the shape S099 uses): `OPEN_STATES`,
  `BASE_STATES`, `TABS`, `TAB_DONE`, `CANCELLED_EVENT`, `settle_plan_job` and its CANCEL branch
  (`cancel_job` is new, an extraction), `pm_jobs._now`, `jobs_out`, `chk_pm_jobs_done`,
  `uq_pm_jobs_open_plan`, `ix_pm_jobs_state`, `pm_job_events` columns; `pm_work_bp`, `job_detail`,
  the pre-read, `state_error` (`in_progress` allowed for an item and Mark done), `DONE_EVENT`,
  `REMARK_MAX` 500, `REMARK_TOO_LONG`, `REMARK_NOT_TEXT`, `chk_pm_jobs_started`, `performed_by_id`,
  `started_at`, `pm_job_results.outcome` / `limit_state`, `NOT_OK`, `NOT_DONE`, the *Done* tab paged
  with `BASE_STATES`, `assigned=me` as assignee or performer, `PmJobRow.vue`, `PmJobView.vue`,
  `PmJobDoneDialog.vue`, `PM_EVENT_LABELS`, `jobBadges`, `TIMELINESS_LABELS`, the route `pm-job`;
  S098's Mark done reads the locked plan row (its `meter_type_id`), so `needs_verification` is at
  hand. S096: `pm_plans.needs_verification TINYINT(1) NOT NULL DEFAULT 1` (brief line 219),
  `pm_plans_core.default_verification` (code, line 218). S095: `timeliness`, `ON_TIME`, `LATE` (code).
- **Existing helpers reused.** `update_row` writes `None` as NULL (`backend/db_helpers.py:68`,
  parameters); `current_person_id` (`auth_utils.py:314`); `enum_arg`'s text "tab must be one of: …"
  (`api_common.py:150`); `PagerBar.vue` exists; the words *Send back* / *Sent back* are the tickets'
  (`ticketLabels.js:81,174`, `MoveDialog.vue`); `useFormModal`'s `openCreate` with no seed and
  FormModal's `closed` event are S098's dialog contract.
- **Tests.** The core first; the API list covers every refusal and both edge cases of D3 (bar BR1-04's
  second waiting job); the lock test; `db_down`; the migration re-run; the changed S098 tests
  named (the *Done* tab plans with `needs_verification: false`, the 400 text, one e2e sentence).
  The five browser tests are the right ones and the four important ones are marked; no device
  check is right (two buttons, a dialog, a text field).
- **Use on the floor.** The engineer's path is five taps with the confirm dialog as the only extra
  step; both actions confirm with the consequence stated; the technician sees *Sent back* on *Me*
  and the remark at the top of the job; a reader without the key sees "Waiting for an engineer to
  verify." and no buttons; the empty states are given; the messages are one or two plain
  sentences.
- **Standards.** TPM (check), ISO 9001 § 7.5.3, ISO 27001 A.5.3 with the departure recorded,
  ISO 55001 § 8.3, SMRP PM compliance: each named, explained in plain words, and tied to a rule.
- **Size and structure.** 20 files, one column, two routes in S098's module (D8), one dialog, one
  tab; no new abstraction; the rules in `pm_work_core.py`, the routes thin.

## Feedback

- waste: the facts file marks about 60 names "planned in S097, S098 — not found", so every one was
  checked by hand in the two briefs (1,064 and 1,297 lines; the S098 brief needed two reads under
  the 25 k-token cap). An idea: when a name is "planned in S0NN", `brief_facts.py` could quote the
  line of that step's brief that defines it, as its *Cited lines* does for `file:line`.
- rule: the brief's header has `Baseline: refs/steps/S098 (planned; …)` for steps not coded yet,
  while this review must write `Reviewed against: <commit> [+ uncommitted S0NN]`; the README
  § Stale brief check does not say what a brief planned ahead of uncoded steps writes there, nor
  what the staleness review compares (a ref that does not exist yet). One sentence in § Anchors by
  name would settle it.
- none else.
