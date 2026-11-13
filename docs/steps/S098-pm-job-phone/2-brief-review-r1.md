```
Step: S098 — Do the PM job on the phone
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 02-11-2026
```

Reviewed against: c9cd091 + uncommitted S095, S096 (partly coded); S097 by its approved brief
(`docs/steps/S097-pm-jobs-due/1-brief.md`, not coded).

**Verdict: no blocker or major finding is open.** 6 minor findings, 15 nits. The design holds:
the readings path is split, not copied, and keeps S039's rule (the node lock before any plain read,
both neighbours); every write route takes (6e) → (6f) → a node before its first plain read, and the
pre-read before the transaction is sound under autocommit; v53's columns and CHECKs hold for every
row S097 can write; the copy at *Start* and the frozen due point follow Plan § 4.3a and S095 N1.
The minors are rules the coder would otherwise decide alone (one unreachable state cell and its
test, the remark on a changed-mind row, the same-minute link, the window constant), planned
duplicates, and a device check a browser can do. Facts file read: `scratch/brief-facts-S098.md`.

**Size (the orchestrator's question).** One step, two snapshot rounds, as S097: the *Me* cut saves
five thin files and loses the one path by which a technician finds the job he started (D11). In the
backend round, code and green the `meters.py` split first, with `test_readings_api.py` and
`test_meters_api.py` run before `pm_work.py` exists, so a refactor fault is never mixed with a
new-route fault; then the core, the migration, `pm_work.py`, the S097 changes and their tests. The
screens round is the 13 frontend files.

---

### BR1-01 — minor — "an item on a `due` job → 409 `START_FIRST`" is unreachable; the test cannot pass

**Problem.** § 5.2's table gives `START_FIRST` for "an item" on a `due` job, and § 8.2 tests it.
But a `due` job has no `pm_job_results` row (they are inserted at *Start*, § 5.3), and § 5.7's
pre-read (`SELECT … FROM pm_job_results WHERE id = %s AND job_id = %s`, missing → 404) runs before
the transaction. So there is no result id to send, and any id sent answers 404 before
`state_error` runs. The cell is dead for items; it is live for the performer and *Mark done*.

**Why it matters.** The coder writes a test that cannot pass and must choose: move the result read
inside the transaction after `state_error` (which breaks § 5.7's "no plain read before the
locks") or change the test. The brief should decide.

**Options.** (a) **Recommended:** keep the pre-read; § 5.2's table says "an item: 404 (no result
row yet)" for `due`; § 8.2's test becomes "a `PUT` on a `due` job with any result id → 404", and
`START_FIRST` is tested through the performer `PUT` and *Mark done*. `state_error(DUE_STATE,
FILL)` stays in the core (R03.5's send-back keeps the rows, so the cell may become live later) and
is unit-tested there only. (b) Read the result inside the transaction after (6f) and answer 409
for a `due` job: a plain read, but after the locks, so § 5.7 still holds; costs one more query on
every item save for a case the page never sends.

### BR1-02 — minor — the remark kept with *OK* / *Done* / a value cannot be typed, and a *Not OK* remark survives a change of mind

**Problem.** § 5.4: "A remark sent with `ok`, `done` or a value is kept (a note such as 'topped
up 0.5 l')." § 5.10: the remark field opens only on *Not OK*, *Not done* and a reading's *NA*; the
page "sends all four [fields] for the item's type". So (1) no screen path types a remark with
*OK*, *Done* or a value: the rule is reachable by hand-made requests only; (2) a row saved *Not OK*
with "Oil seeping…" and then tapped *OK* sends the old remark again, and the *OK* row shows "Oil
seeping…" under it.

**Why it matters.** (2) is what the floor will meet: a wrong tap on *Not OK*, corrected by *OK*
(D7's "fixed by another tap"), leaves a fault text on a good row, and R03.10 reads remarks. (1) is a
rule the coder implements and tests for nothing.

**Options.** (a) **Recommended:** a tap on *OK*, *Done* or a check's *NA*, and a reading's *Save*,
send `remark: null`; the remark belongs to the refusal it explains. The API keeps accepting a
remark with any outcome (one rule, no new refusal), and § 5.4's "kept" sentence says the page
sends none. (b) A small *Remark* link on every row that opens the field: more controls on a
crowded phone row, no use case named.

### BR1-03 — minor — the same-minute link makes the job own a reading it did not log; "the reset mark changes" has nothing to compare

**Problem.** § 5.5 step 4: an active reading at `started_at` with the same value is linked
(`reading_id` names it, nothing inserted). Step 3: when the value changes "the old reading is read
and, while active, removed" — D8's reason is "the job owns the reading it logged", but a linked
reading was logged by the operator (source `manual`); the job would remove his reading under
`pm_job:work`, which may not remove readings. Also step 3's trigger "the value or the reset mark
changes" has no stored reset mark on the result: § 5.4's `result_changes` compares `outcome`,
`value`, `limit_state`, `remark` only, so a save with the same value and `is_reset: true` is "no
change" and writes nothing.

**Why it matters.** A removed operator reading is a silent change of someone else's record (ISO
9001 § 7.5.3); the reset case is a rule the coder decides alone.

**Options.** (a) **Recommended:** step 3 removes the old reading only when its `source` is `pm`
(the column exists: `meter_readings.source ENUM('manual','pm','move','iiot')`, v41); a value change
on a result linked to a manual reading then meets step 4's `SAME_MINUTE_PM` (an engineer sorts
it out). For the reset: `result_changes` also compares the sent `is_reset` with the linked
reading's `is_reset` when `reading_id` is set (passed in by the shell); a changed mark is a change
and goes through steps 3–5. (b) Never link: a same-minute reading of any value is
`SAME_MINUTE_PM`; simpler, but the technician who also typed the evening sheet is refused.

### BR1-04 — minor — the 7-day window is tied to `tickets_core.MAX_BACKDATE_DAYS`, while the reason given is the readings' window

**Problem.** § 5.1: `job_time_error` calls `event_time_error(moment, now, MAX_BACKDATE_DAYS)` and
replaces its "too old" text. The reason stated: "a PM reading is logged at the job's start time, so
the start window must not exceed the readings' window" (`meters_core.READING_BACKDATE_DAYS`, S039
decision 8). The two constants are both 7 today by coincidence; `tickets_core.too_old_message`
also asserts its argument is one of the ticket constants, so the call works only while they
agree. A later change of the ticket window (S028's backlog logic lives there) would silently
widen the PM window past the readings' and put a reading in the history that `log_reading` would
refuse.

**Options.** (a) **Recommended:** `pm_work_core` takes `meters_core.READING_BACKDATE_DAYS` and
`tickets_core.FUTURE_SKEW` and makes its own three comparisons (future, too old, `not_before`),
with its own texts (`TIME_TOO_OLD`, `DONE_BEFORE_START`, `EVENT_TIME_FUTURE` reused); no text
replacement. (b) Keep `event_time_error` and pin the coupling with a core test
`assert MAX_BACKDATE_DAYS == READING_BACKDATE_DAYS` whose message names this brief.

### BR1-05 — minor — three planned duplicates of names that exist

**Problem.** § 5.1 defines (1) `STORED_DECIMALS = 3`: `pm_plans_core.STORED_DECIMALS` is the same
value with the same meaning (DECIMAL(14,3)), and `item_limits_text` already uses it for the copied
columns; (2) `RESET_ONLY_COUNTER` "Only a counter meter can be reset": `meters_core.validate_reading`
already refuses `reset and kind != COUNTER` with `ONLY_A_COUNTER_RESETS` ("Only a counter can be
reset") and `RESET_NOT_BOOL`, and § 5.4 calls `validate_reading` with the meter type's kind (or
`GAUGE` without a meter), so the refusal is already produced; (3) `PERFORMER_NEEDED` "Choose who
did the work.": `pm_plans_core.PERFORMER_NEEDED` is "Choose who does the jobs." (the plan's
performer). Two constants of one name with two texts, in two modules the shell imports side by
side.

**Options.** (a) **Recommended:** import `pm_plans_core.STORED_DECIMALS`; drop
`RESET_ONLY_COUNTER` and let `validate_reading`'s refusal through (its text and field `is_reset`;
§ 8.2's test asserts that text); rename the start message `PERFORMED_BY_NEEDED`. (b) Keep the
three with a comment each; against CLAUDE-COMMON *DRY* and *one term for one thing*.

### BR1-06 — minor — the Wi-Fi drop is a check a browser can do

**Problem.** § 8.5 puts "A Wi-Fi drop mid-job" on the real-device list (important). Playwright
judges it: `page.context().setOffline(true)` (or a `page.route` that aborts the `PUT`) makes the
save fail with `err.status` 0, the row shows "Not saved: … Tap again." and keeps the tap;
`setOffline(false)` and a second tap show "Saved"; a reload shows the items filled before. § 9 A4
says this path is "checked in the code, not on a device until § 8.5".

**Why it matters.** The network case is the brief's own point 3 ("a network drop loses at most
the one item"); an untested path that waits for IT Admin on a pilot press is the one most likely
to ship broken, and the rule (`docs/steps/README.md` § Manual checks) puts it on the automated
list.

**Options.** (a) **Recommended:** a test `S098: a save during a network drop says Not saved and
keeps the tap; it saves on the next tap` in `pm-job.spec.js` (important), and the device row kept
as a plain note for the real Wi-Fi, not important. (b) The device row alone, as written.

## Nits

- **BR1-07** (nit) § 5.5 table: `lock_reading_node` is `_lock_node` under a second name ("it stays, as
  the name for the meter writes"). One function, one public name (`lock_node`), used by the meter
  writes, the readings and PM.
- **BR1-08** (nit) § 3, § 5.6: `pm_work.py` imports `_now` from `pm_jobs`. A test that fixes the clock
  monkeypatches `pm_jobs._now` (S097 § 8.2), which a `from pm_jobs import _now` would not see. Call it
  as `pm_jobs._now(cur)` through the module, and say so; better, S097's name becomes public (`now_ist`).
- **BR1-09** (nit) § 6.2: `can_start` is the key and state `due`; for a due job of a node scrapped after
  the job was made (§ 5.3's case) the page offers *Start job* and gets the 409. Fold the lifecycle in
  (`can_start` false when scrapped) or answer `equipment.lifecycle`, and show the plain items with
  "This machine is scrapped." instead of the card.
- **BR1-10** (nit) § 5.1 `NO_ITEMS`: S096 § 5.4 refuses a plan with fewer than one item and a `PUT` with
  fewer than one, and a removed item is set inactive only by a save that sends the others, so a plan
  always has an active item. Keep it as a defensive 409 and say it is unreachable today, or drop it.
- **BR1-11** (nit) § 8.6: "the meter's history shows the run hours with source PM" cannot be seen:
  `reading_out` sends no `source` and the history dialog shows none. Either add `source` to
  `reading_out` and a small "PM" tag on the history row (two lines), or reword to "the reading is in
  the meter's history and the item says *Also logged*".
- **BR1-12** (nit) § 4.1 `chk_pm_job_results_outcome`, reading branch: `NOT (outcome = 'na' AND value IS
  NOT NULL)` is NULL when `outcome` is NULL and a value is set, and passes only because a CHECK treats
  NULL as true. Write `(outcome IS NULL OR value IS NULL)`.
- **BR1-13** (nit) § 5.6 step 3: `meter_offset` is frozen at *Start* (D2); a counter reset between *Start*
  and *Done* leaves it stale, so `done_meter_counted` is low and `timeliness` may read `on_time` for a
  late job. Rare; state it in Plan.MD's paragraph beside the changed-meter case, or recompute the
  offset at done with `readings_across_reset` from the base (S097 § 5.4).
- **BR1-14** (nit) § 5.3: `started_at` may lie before the job's `created_at` (a job made this morning,
  started two days back on behalf). Allowed; say so, and that the history then shows *Started* before
  *Created* (the ticket timeline's back-dated case).
- **BR1-15** (nit) § 6.1 `PUT /api/pm/jobs/<id>`: a `performed_by_id` that is not an integer ≥ 1 gets which
  400? Say `PERFORMER_NEEDED` on `performed_by_id`, as *Start*.
- **BR1-16** (nit) § 5.1 `JOB_CLOSED` "This job was cancelled. It cannot be worked." — the second sentence
  explains the rule (style B); "This job was cancelled." is enough. It also serves `skipped` (R03.9), for
  which "cancelled" is wrong: give R03.9 its own text, and say so.
- **BR1-17** (nit) § 5.10 *Mark job done* dialog: a confirmation states the consequence (style B). Add
  "The job can no longer be changed." under the *Done* field, since R03.5's send back is not built.
- **BR1-18** (nit) § 8.2 "as `test_readings_api.py`'s locking test, if it has one": it has one,
  `test_two_writers_on_one_node_serialise_and_the_second_sees_the_first` (a second connection holds the
  node `FOR UPDATE`, inserts 100, commits; the API's 50 waits and is refused `counter_lower`). Model the
  PM test on it: it proves the lock and the snapshot after it, not only the wait.
- **BR1-19** (nit) § 5.7 Start step 4 "`load_node_for_user(…, key="pm_job:work")` with the read predicate of
  § 5.2": `load_node_for_user`'s 404 is by `equipment:read`'s units (`_can_access`), not by
  `pm_job:read`'s; the write routes are safe through `require_perm("pm_job:work")` first. Say that, and
  that only `GET /api/pm/jobs/<id>` applies `accessible_unit_ids(cur, "pm_job:read")`.
- **BR1-20** (nit) § 8.3 `test_migration_v52.py` "a test that builds `_MIGRATIONS` whole gains v53": the
  house pattern filters (`test_migration_v51.py`: `V51 = [m … if m[0] <= 51]`), so S097's
  `in_progress`-and-`due` → 1062 test runs at v52 and never meets `chk_pm_jobs_started`. Drop the hedge;
  keep the `test_pm_generate.py` line (that one runs at the latest version and needs the two columns).
- **BR1-21** (nit) § 1 point 10 and § 5.8: the same rule is missing for deactivating a unit (S025 § 5.3
  refuses on open tickets only): a started job in a deactivated unit is reachable by nobody
  (`accessible_unit_ids` lists active units). Not S098's to build; note it for later in § 9 (R03.9's
  skip would be the way out).

## Checked and found consistent

- **The S097 names S098 relies on** (§ 3): `pm_jobs` columns incl. `done_at`, `done_meter`,
  `timeliness`, `meter_offset`, `open_plan_id`; `pm_job_events` columns; `pm_jobs_core` constants,
  `decide`'s `in_progress` row ("none, R03.4 decides"), `due_from_job`, `tab_of`, `list_order`;
  `settle_plan_job(cur, plan_id, node_lifecycle, now, actor)`, `jobs_out(cur, rows, today)`,
  `_now(cur)`, `plan_schedules`; `meters.last_readings` (public, `until=`), `first_reading_after(cur,
  equipment_id, meter_type_id, after)`; `GET /api/pm/jobs` and its `tab` 400 text; S097 § 5.7's rule
  "a job write takes its plan (6e) first, then the job" and its (6)-after-(6e) departure.
- **The S096 names**: the item and plan columns (v51 as coded), `ITEM_TYPES`, `PHOTO_SETTINGS`,
  `TASK`/`CHECK`/`READING`, `item_limits_text(item, meter_type, meter_code)`; positions 1..n over the
  active items (so `uq_pm_job_results_position` holds for the copy); a reading item names a counter
  or gauge only (§ 5.5), so no Yes / No value meets `validate_reading`; the change route's (6e) → (1)
  order and "every item write holds (6e)".
- **S095**: `timeliness(due, done_on, done_meter)` with `ON_TIME`, `LATE`, `before_use` None;
  § 5.2's "meter value at T" rule; N1's "store the final due point and timeliness at done" (D2 keeps
  the point frozen from *Start*, so the stored copies are final).
- **The `meters.py` split** (§ 5.5): the four functions carve `log_reading` (lines 377–413) and
  `remove_reading` (416–435) without a behaviour change; the 400-before-409 order of `log_reading`
  is kept in `write_reading`; `meter_readings.source` exists with `pm`; `counter_error` takes both
  neighbours; `reset_removal_error(reading, has_later)` needs `_newest_active_id`, available.
- **The lock sequences** (§ 5.7) against the LOCK ORDER notes of `equipment.py`, `meters.py`,
  `pm_plans.py` (as coded) and S097's: (6e) → (6f) → a node, all before any plain read; the pre-read
  outside `transaction(conn)` is its own autocommit statement (`local_db` `"autocommit": True`,
  `db_helpers.transaction` begins after it), and `plan_id`, `equipment_id` and a result's copied
  meter columns never change; the alternatives (job locked first; a `LOCK IN SHARE MODE` pre-read
  upgraded to `FOR UPDATE`) would deadlock with the run or with a second *Start*. The scrap count
  (§ 5.8) holds for the reason `_check_no_open_tickets` gives: the scrap's snapshot starts at
  `load_node_for_user`'s plain read after its `FOR UPDATE`, *Start* holds the node shared before it
  writes, and a part must be scrapped before its machine (`_check_parts_scrapped`), so the one
  window left is the accepted FK deadlock the brief names.
- **Migration v53**: the `IF NOT EXISTS` forms equal v50's (`people.vendor_id`, `chk_people_vendor`);
  `chk_pm_jobs_started` holds for `due` and `cancelled` rows (S097 writes only those) and for
  R03.5's send-back; no precondition needed; the ENUMs equal the cores' constants; `_TABLES` order
  (`pm_job_results` first, `meter_readings` later) truncates in FK order.
- **`pm_job:work`**: `("maint_technician",)` → technician, engineer, manager through `ROLE_INCLUDES`;
  every holder holds `pm_job:read` (operator ⊂ technician) and `ticket:raise` (for
  `GET /api/tickets/people?equipment_id=`, which checks `ticket:raise` at the node's site); the
  departure from Plan § 3's table (operator and supervisor ticked; "granted to operators because
  CIL jobs are PM jobs") is stated and matches R03.4 and R03.12.
- **The frontend contracts**: `useFormModal({ path, blank, fromRecord, afterSave, toBody, label })`;
  `EventFields` props `withRemark`, `timeLabel`, the *Now* tick and `daysAgoHint`; `api.js` sets
  `err.status = 0` with `NO_CONNECTION_TEXT`; `ReadingsSheet.vue` shows the reset tick on
  `err.code === "counter_lower"`; `isActivePath` lights *PM* for `/pm/jobs/…`; `MeView.vue`'s
  `Promise.all`, the countermeasures section and its *Tickets* heading; `screens.spec.js`'s
  `{path, title, shows, who}` and `TICKET_ROLES`; `meterMachine(testInfo, tag, {unit,
  modelMeters})`, `logByApi`, `apiAs`, `personId`; the seed's "Ramesh (operator, no phone)".
- **Standards**: TPM, EN 13306, ISO 14224, ISO 9001 § 7.5.3, SMRP PM compliance, ISO 27001 A.5.15,
  each explained in plain words and tied to a rule; the Plan § 3 departure stated.
- **Use on the floor**: *Start job* is one tap with the defaults (own person, *Now*); an item is
  one tap (two with a required remark); *Mark job done* is two taps with the dialog as the confirm
  step, fitting a phone (one field); who acts is shown (*Performed by*); the no-permission states
  are text, not a 403; the 404 and error texts are one line; the device rows name the account, the
  network and where.
- **Writing style**: the brief is in scope A; the UI texts in scope B but for BR1-16 and BR1-17.

## Feedback

- idea: the *Device checks* entry's kinds a browser cannot judge could say that a network drop is
  one a browser **can** judge (`context.setOffline`), so briefs stop putting it on the device list
  (BR1-06; S098 § 8.5, § 9 A4).
- waste: the facts file's *Code names* lists 95 names "not found … planned in S097" one by one; a
  brief built on an uncoded step would be served better by one line per upstream brief ("S097
  defines: …") than by a re-check of each (`scratch/brief-facts-S098.md` lines 440–441, read
  twice to be sure nothing coded was missed).
- hindrance: the brief is 1,213 lines; the Read tool capped the first read at line 697, so the
  rules and the tests came in two reads and § 5.7's lock sequences had to be re-read beside § 5.5
  (about 5 minutes).
