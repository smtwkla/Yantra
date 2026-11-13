```
Step: S104 — PM templates: one path
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 02-11-2026
From: R03.18
```

Reviewed against: 82d38ac + uncommitted S095, S096, S097, S098, S099, S100, S101, S102 (held)

**Verdict: no blocker and no major finding is open.** The design follows the gate R decisions (Q18.1 a, Q18.3,
Q18.4 a, Q18.5 a with the per-meter tick, Q19.1 a) and Plan.MD § 4.3 "Decided 02-11-2026". The migration, the
lock sequences and the permissions hold against the held code. Eight `minor` findings: rules the coder would
otherwise decide alone (the meter base after the resolved meter changes, the relinked plan's schedule start,
the 1062 path of `sync_node`, the actor of the after-commit settle), the help tour's PM set-up that v57 breaks,
two doc bullets that still state the old meter rule, and one sentence that can mislead the coder. The facts file
`scratch/brief-facts-S104.md` was given and used; every "not found" there is a name the brief says is new.

Round 1 read the whole brief, the roadmap R03.18 and its § Decisions / § Log, Plan.MD § 4.3, the held
`pm_plans.py`, `pm_jobs.py`, `pm_jobs_core.py`, `pm_work.py`, `pm_work_core.py`, `pm_plans_core.py`, the LOCK
ORDER notes of `equipment.py`, v51–v56 in `local_db.py`, `meters.py`'s meter functions, `alerts.py` /
`alerts_core.py`'s PM parts, `config_rbac.py`, `conftest.py` `_TABLES`, the PM tests' set-up helpers, the PM
browser specs, the router, the nav store, `MastersView.vue`, `PmPlansCard.vue`, the mock-ups 09, 11 and 14, and
`tooling/help/setup_tour.py` with `frontend/help-tour/desktop.tour.js`.

## Findings

### BR1-01 — minor — The meter base is on another meter after the resolved node changes (§ 5.3, D5)

**Problem.** `pm_jobs._meter_base` takes the last base job's `done_meter` (or the plan's `last_done_meter` seed)
and `schedule_inputs` adds `meter_every` to it, against the readings of the node the trigger meter resolves to
*now*. With the parent tick, the resolved node can change between two jobs: a part uses the press's Run hours
(12,000 h), then gets its own Run hours meter (0 h). The next due is 12,250 h on a meter that reads 0: the job
never comes due, and nothing says so. The same happens when a template's `meter_type_id` is changed (the seed
and the last `done_meter` are values of the old type). The brief covers a meter added or removed under an open
job (the refresh and the cancel) but says nothing about the base. In S096 the meter sat on the plan and this
needed an engineer's edit; in S104 adding a meter to a part changes the resolution by itself.

**Why it matters.** A silently wrong schedule on the one path the tick introduces, with no reading on the
screen that explains it (the card shows "Next due 12,250 h").

**Options.**
- (a) **Recommended.** The job's new `meter_equipment_id` copy makes the base's node known: when the last base
  job's `meter_equipment_id` differs from the resolved node (or is NULL on a job done without a meter trigger),
  the base is not used; the start value falls back to S095 D9's rule (the nearest reading on the resolved meter
  before the base time, else the first after it), the same path `_meter_base` takes when the plan has no seed.
  A seed (`last_done_meter`) is used only while the template's type has not changed since the plan save: store
  nothing new for that; the plan settings route refuses a seed on a type the template does not have (it already
  does), and a template type change clears nothing but makes the base rule above apply (the seed is a value of
  the old type: treat a seed as usable only when the last base job is NULL *and* the resolved node is the plan's
  own node or the seed was saved for it — simplest: document that the engineer re-enters *Last done* after a type
  change, and the plan page says so when the template's type changed after the seed was saved, from
  `updated_at` of both rows).
- (b) Keep the base as it is and say so in the brief (a known gap, R03.21 or later).
- (c) Refuse the parent tick on a node that has a meter of the type in force (the tick is "if the machine has no
  meter"): that stops the own-meter-added case only after the fact, not the type change.

Pick (a) for the base-job half at least; it is one comparison in `_meter_base`, and a `test_pm_generate` case
(the press's meter used, the part gains its own meter, the next job's due counts from a reading on the part).
State in § 5.3 what happens to a seed after a type change, even if the answer is "the engineer re-enters it".

### BR1-02 — minor — `sync_node`'s 1062 path settles a plan without naming (6e) (§ 5.4, § 5.9 step 5)

**Problem.** "`uq_pm_plans_template` as the guard: a 1062 means another request made it, and the row is then
settled". A settle writes `pm_jobs` and must hold (6e) first (pm_jobs.py's LOCK ORDER: every pm_jobs write holds
its plan row first). After a 1062 the make transaction holds (1) shared and no plan row.

**Why it matters.** The one invariant every PM module keeps; the code reviewer will look for it, and a settle
without (6e) can make two open jobs for one plan with the other request's settle (`uq_pm_jobs_open_plan` then
gives a 500).

**Options.**
- (a) **Recommended.** On 1062, roll back the make transaction and treat the row as a relink / nothing: read
  the row's id plainly, then the relink path ((6e) → (1) shared → `linked` if needed → `settle_plan_job`) in a
  new transaction. One sentence in § 5.9 step 5.
- (b) Read the existing row's id and take (6e) on it inside the same transaction, after (1) shared. The order
  (1) then (6e) is the reverse of every other PM write (6e then 1): rejected.

### BR1-03 — minor — The after-commit settle writes its timeline lines as `pm_generate` (§ 5.6)

**Problem.** The brief reuses `pm_jobs._settle_one(conn, plan_id, keep_reschedule)`, "the daily run's function".
That function passes `RUN_ACTOR` (`"pm_generate"`) as the actor of the job's `due_changed`, `assignee_changed`
and `cancelled` lines and as `updated_by` of the job. For a template save, the actor is the engineer.

**Why it matters.** § 2 (ISO 55001 § 8.2, ISO 9001 § 7.5.3) promises "one recorded change (who, when) that
reaches every plan". The job page would show the run's wording for a change an engineer made, and a dispute
("who moved my jobs?") cannot be answered from the timeline.

**Options.**
- (a) **Recommended.** `_settle_one(conn, plan_id, actor, *, keep_reschedule=True)`; the run passes
  `RUN_ACTOR`, the template save passes `actor()`. Make the name public (`settle_one`) since a second module
  calls it. One line in § 3's `pm_jobs.py` row and § 5.6.
- (b) Keep `pm_generate` and word it on the page as "the template was changed". Hides who: rejected.

### BR1-04 — minor — The help tour's PM set-up and slides break with v57 and are not named (§ 3)

**Problem.** `tooling/help/setup_tour.py` (lines 262–310) makes its PM plans through `POST /api/pm/plans` with
`title`, `trigger_kind`, `meter_equipment_id`, `items` and `assignee_id` in one body, and
`frontend/help-tour/desktop.tour.js:96` opens `/equipment/<id>/pm/new` for slide 62. Both stop working with this
step: the plan create with items goes (§ 6), and the route `pm-plan-new` goes. The brief's § 3 does not list them,
and § Docs says nothing of the guide.

**Why it matters.** CLAUDE.md § Docs to keep current says the guide is retaken before a release that changes
screens, on KLA's word — "nothing in the step". But the retake runs `setup_tour.py` first, which will 400 on its
first PM plan; the retake then needs a fix nobody has planned. The guide's PM slides (60–62, 67–71) also show
S096's plan editor, which no longer exists.

**Options.**
- (a) **Recommended.** Add to § 1 *Out of scope* one line: "The help tour (`tooling/help/setup_tour.py`'s PM
  plans, `desktop.tour.js`'s slides 60–62) and the guide's PM slides are updated at the retake before the
  release (CLAUDE.md § Docs: `help/`); until then `tooling/help-shots.bat` fails at the PM set-up." KLA then
  decides when.
- (b) Fix `setup_tour.py` and the tour files in this step (a template per plan, attach; slide 62 becomes the
  template page). About 60 lines; the slides' text in `help/guide/` would also need the retake. Only if KLA
  wants the tour green at gate B.

### BR1-05 — minor — A relinked plan's first job counts from the row's old `created_at` (§ 5.4)

**Problem.** "A new plan row … its first job counts from the day it is made (`created_on`). A relinked row keeps
its assignee, its seed and its jobs." A row made on 1 January, removed on 5 January before any job was done, and
attached again on 1 June with "every month" has no base job and no seed: `next_due` counts from `created_at`,
so the relink makes a job overdue since 1 February at once. The brief does not say whether that is wanted.

**Why it matters.** The coder decides alone, and the engineer sees an overdue job appear on a machine that was
not in the plan for months.

**Options.**
- (a) **Recommended.** State the rule: a relink restarts the count when the row has no base job — the relink
  writes `created_at = NOW()` is wrong (it is a record); instead `schedule_inputs` takes the plan's start as
  `GREATEST(created_at, the relink time)`. The relink time is the plan row's `updated_at` written by the
  `linked` UPDATE; simpler still, the brief adds a `linked_at DATETIME NULL` column written at make and relink
  and used as the start when there is no base job and no seed (v57 is new, so no extra migration).
- (b) Keep `created_at` and say the job is right: the work was not done since the row was made. Then the plan
  page should say "Counting from DD-MM-YYYY" so the engineer can set *Last done*.
- (c) Make a relink clear nothing and let the engineer set *Last done* (the brief's words today). A rule the
  floor cannot guess: rejected unless (b)'s line is added.

### BR1-06 — minor — Two doc bullets still state the old meter rule, and one doc is missing from § 3 (§ 3 Docs)

**Problem.** Plan.MD § 4.3 line 828 "Which meter a plan uses (*Proposed*, 16-10-2026): … the picker offers the
node's own meters and its ancestors'" and Maintenance-Philosophy § 8 line 319 "a plan names one meter, its own
node's or an ancestor's — a gearbox on the extruder's hours" both contradict Plan § 4.3's "Decided 02-11-2026"
block, which the brief builds. § 3 Docs updates Plan.MD's "Built" paragraph only; Maintenance-Philosophy is not
listed, though CLAUDE.md § Docs to keep current makes it due when a step "settles a maintenance rule".

**Why it matters.** The next reader of either doc (the roadmapper of R03.21, the code reviewer) finds two rules.

**Options.**
- (a) **Recommended.** § 3 Docs gains: Plan.MD § 4.3 line 828 becomes "Decided 02-11-2026 (S104): a template names
  a meter type, matched on the machine's own meters; a parent's only with the template's tick";
  Maintenance-Philosophy § 8 line 319 the same, keeping the gearbox example ("the gearbox's greasing is a
  template on the press, or the gearbox gets its own hour meter where its hours differ — ISO 14224").
- (b) Leave both and rely on the "supersedes" sentence of the Decided block. Rejected: the Decided block is in
  § 4.3; Maintenance-Philosophy has no such sentence.

### BR1-07 — minor — § 5.5's unknown-field sentence can mislead the coder (scope A)

**Problem.** "any other field (`template_id`, `equipment_id`, `title`, …): 400 "Change the work on the template."
(`template_id`) — the one exception: unknown fields are refused, not ignored, so an old screen cannot think it
saved items." It is not clear which field gets which message, nor what "the one exception" excepts. D12 says
every unknown field is refused.

**Why it matters.** The coder must choose the message and the `field` of the 400 for each case.

**Options.**
- (a) **Recommended.** Rewrite as a rule and a table: "Any field other than `assignee_id`, `last_done_on`,
  `last_done_meter` is refused (400, `field` = that field's name). The message: for `items`, `title` and the
  trigger fields "Change the work on the template."; for `template_id` and `equipment_id` "A plan stays on its
  machine and template. Remove it and attach another."; for anything else "Unknown field: <name>." D12 names
  this as the departure from `clean_body`'s ignore."
- (b) Refuse only the S096 fields (items, title, trigger) and ignore the rest, as `clean_body` does. Weaker than
  D12: rejected.

### BR1-08 — minor — The template page's save moves every machine's jobs with no confirmation (§ 5.10)

**Problem.** *Save template* on a template "Used on 14 machines" with a changed interval moves up to 14 open
jobs at once and drops their reschedules (S101 D4). The page carries a standing note; *Deactivate template* has a
confirmation naming N machines; *Save template* has none. ISO 55001 § 8.2 (§ 2) is the brief's own reason for
treating this as a controlled change.

**Why it matters.** An engineer fixing a typo in an item text is not affected (no schedule field changed); one
who changes "every month" to "every 3 months" for one press's sake changes 14 machines' schedules in one tap,
and only the next card view shows it.

**Options.**
- (a) **Recommended.** A confirmation only when a `SCHEDULE_FIELDS` field changed and `plan_count` > 1:
  "Change the schedule for N machines? Their jobs move to the new interval. Jobs already started are not
  changed." The page knows both before the PUT (the loaded template and the form). One browser test line.
- (b) Keep the standing note alone. Acceptable for the pilot (a handful of presses); say so in D9 if chosen.

## Nits

- **BR1-09** (nit) § 4.1 item 4: `open_target_id AS (CASE WHEN active = 1 THEN target_id END)` refers to the
  generated column `target_id`. MariaDB allows a generated column to refer to one defined before it, but the
  dev container's version decides; write the COALESCE inline in both expressions (as v52's `open_plan_id` is
  self-contained) or let the migration test tell at once.
- **BR1-10** (nit) § 3 Tests: name `test_pm_generate.alone` beside `set_plan`: it writes `pm_plans.active = 0`
  for every other plan, which becomes `pm_templates.active = 0` through the plans' `template_id` (one template
  per test plan, so no shared template is hit) or `linked = 0`; `test_pm_alerts.py:249,385`'s
  `set_plan(..., active=0)` the same.
- **BR1-11** (nit) § 8.4: `screens.spec.js:112` also uses `"New PM plan"` (facts file, *Screen text*); add it
  to the lines that change, with the template page's heading it becomes.
- **BR1-12** (nit) § 5.6: the example says "2 machines will update at the next daily run" when "one failed";
  make the counts agree, and say what the client sees when the connection is lost mid-settle (a 503 after the
  template was saved; a repeated PUT with the same body writes nothing and settles again).
- **BR1-13** (nit) § 5.10 PM card: "Reaches this machine from: This machine" reads oddly for S104's one source;
  write "Attached to this machine" until R03.19 adds class, type and model, and keep the mock-up's "Reaches …
  from:" form for those.
- **BR1-14** (nit) § 5.10, § 6: define what counts in "Used on N machines", `plan_count` and the card's header
  "PM plans (N)": rows with `linked` = 1 (a plan that does not apply counts; an unlinked one does not), so the
  list, the header and the deactivation confirmation agree.
- **BR1-15** (nit) § 5.8: the Masters nav item shows only to holders of an edit key (`navigation.js`, S064
  UX-12), so a technician never sees *Masters › PM templates*; he reaches the template page from the plan page's
  *Open template* (the route is outside the nav, so `canOpenRoute` allows it). Say so, since § 8.4 tests the
  technician on that page.
- **BR1-16** (nit) § 5.9: the template save holds (6g) and then takes (4b) the meter type shared through the
  item inserts' foreign keys — a lower number after a higher one. Meter type writers (`masters.py`) never wait on
  a template row, so it is a one-way wait; state it in the equipment.py list entry for (6g), as (6) after (6e) is
  stated.
- **BR1-17** (nit) § 5.10 Phone: "the items table on the template page scrolls inside its card, as S096's" —
  S096 shows a list below 768 px and the table above (`pm-item-list` / `pm-items table`, pm-plans.spec.js:215);
  keep that, not a scrolling table.
- **BR1-18** (nit) § 3: `pm_work.py` imports `item_limits_text` and `meter_label` from `pm_plans_core`; they
  move to `pm_templates_core` with the item rules — add to the `pm_work.py` row. `PmItemDialog.vue` sits in
  `views/equipment/`; it becomes the template's dialog, so `views/masters/` or `views/pm/` fits.
- **BR1-19** (nit) § 6 `GET /templates` with `active=1|0`: the panel folds the inactive ones, so it makes two
  requests or one with both lists; say which (`{items, inactive, can_add}`, as the card's answer, is one).
- **BR1-20** (nit) § 9 open question 3: keep the preview on the server. The resolution rule (`resolve_meters`,
  `applies`) then has one home, and the dialog shows exactly what the plan page will show. Fold it into
  `GET /templates/<id>?equipment_id=` rather than a new path if the coder prefers one route; either is fine.

## Checked and found consistent

- **Migration v57.** The five dropped tables are the only ones referenced by `REFERENCES pm_` (local_db.py
  1324, 1376, 1404, 1455, 1456); children first in the DROP. `_MIGRATIONS` pending = versions not in `db_version`
  (`local_db.py:1661`), so a dev database at v56 gets v57 and keeps v51–v56 as history; production at v50 drops
  nothing. Every statement runs twice safely. `test_migration_v50.py` filters `_MIGRATIONS` by `m[0] <= 50` and
  `migration_helpers.SQUASHED` by `== 41`, so removing v51–v56 breaks neither. `conftest._TABLES`' order as the
  brief gives it respects the new foreign keys.
- **Locks (§ 5.9).** (6g) exclusive is held only by a template save, which then waits on nothing but shared
  meter-type locks; (6g) shared by Attach after (1) shared. The after-commit settles take (6e) → (1) shared, the
  S097 shape, one plan per transaction (D9 keeps S097 D6). Remove's link UPDATE touches a row nothing else
  locks; two concurrent syncs of one node converge because `sync_node` decides from the links as they are. The
  REPEATABLE READ rules of pm_plans.py, pm_jobs.py and pm_work.py are kept: every template read on a job write is
  plain and after (6e) (D10).
- **Live resolution and the job's copy (§ 5.3, D5).** `meters.meter_in_force(cur, node_id, model_id, type)` and
  `meters_with_last` exist as cited and give one meter per type (`uq_model_meters`, `uq_node_meters`).
  `jobs_out`, `_alert_one`, `_done_meter` and the reschedule read `(meter_equipment_id, meter_type_id)` today
  from `pl.`; moving the node to `j.meter_equipment_id` with `tp.meter_type_id` keeps every call shape. The refresh
  must add `meter_equipment_id` to `job_changes`' compare (the brief's "with the due copies" covers it).
- **Permissions (§ 5.8).** `equipment:read` is `('*',)` and site-scoped; `require_perm` takes the union, so every
  role including IT admin reads templates. `pm_plan:edit` is `maint_engineer` and in `SITE_SCOPED`; by the union
  for templates (Q18.4 a), at the node's site for plans through `has_perm_at`. No key added; `test_role_matrix`
  unchanged. `GET /api/masters/meter-types` is `SELECT *` under `masters:read` (`('*',)`), so open question 2
  holds: `kind` is in the answer.
- **Held tests and specs (§ 3, § 8).** The set-up points are as the brief names them: `test_pm_plans_api.create`,
  `test_pm_work_api.plan_with`, `test_pm_generate.set_plan`, `test_pm_reschedule_api.py:281`'s trigger UPDATE,
  `test_equipment_api.py:387`'s INSERT; the six specs that POST `/api/pm/plans` are pm-plans, pm-jobs, pm-job,
  pm-verify, pm-reschedule, me and screens (screens.spec.js:40). `pl_title`, `pl_active`,
  `pl_needs_verification`, `pl_performer`, `pl_trigger_kind` stay as aliases, so `alerts_core`, `alerts.py`
  (`pm_job_recipients` reads none of them), `task_handlers.py:535` and `test_alerts_core.py` need no change.
  `decide`'s first argument changes; `test_pm_jobs_core.py:49,57` and the `PLAN_INACTIVE_REMARK` imports in
  `test_pm_generate.py`, `test_pm_jobs_api.py` follow (the remark text changes to the template's).
- **Held behaviour kept.** S098's item path (`lock_node` on the result's `meter_equipment_id`, `meter_in_force`,
  `write_reading`, the `not_logged` note) is unchanged; S099's send back and verify, S101's reschedule and skip,
  S102's markers and candidates keep their shapes; the scrap's `_check_no_started_pm_jobs` counts jobs by node
  and is untouched. S096's "a part's plan may count its machine's run hours" becomes the parent tick (Q18.5 a);
  its "meter removed" page note becomes "Does not apply".
- **Design and structure.** The rules sit in pure modules (`pm_templates_core`, `pm_links_core`, `pm_plans_core`),
  the routes are shells; imports point one way (pm_templates → pm_jobs, pm_plans → pm_jobs, pm_jobs imports
  neither). `pm_template_links`' four kinds and `pm_plans.not_for_*` are R03.19's columns approved at gate R, not
  over-engineering. `meters_with_last` is reused for the card; `_settle_one` for the after-commit settle.
- **Standards (§ 2).** TPM planned maintenance (the standard written once), EN 13306 (maintenance plan,
  predetermined maintenance, inspection), ISO 14224 (the record on the item it was done on, which is why the
  match is the machine's own meters), ISO 55001 § 8.2 (management of change: the template save is the controlled
  change) and ISO 9001 § 7.5.3 (records kept and protected: the job's copies, nothing deleted) are named, each
  explained in one plain sentence, and the proposal follows each. ISO 55001's clause 8.2 is indeed *Management of
  change*.
- **Use on the floor.** The attach dialog is one pick and one tap, with the refusal beside the select and the
  "Does not apply" preview before the tap; the deactivation and the remove confirmations name what happens;
  *Attach PM template* shows only with the key on a node not scrapped; the card's rows read as the person
  scanning them needs (name, source, trigger, the job or next due, or why not). The error texts of § 5.1–§ 5.7
  follow scope B (one line, what to do, no codes), except the one BR1-07 asks to settle.
- **Manual checks (§ 8.4, § 8.5).** The three important checks are browser tests; no device check is right: no
  camera, printer, Keycloak or keyboard behaviour is new. The new `e2e/support/pm.js` is named as shared code
  with the whole-suite run and the WebKit `screens.spec.js` run.

## Feedback

- waste: the facts file lists `pm-job.spec.js:236` and `:97` under *Cited lines* but not the 14 test files'
  lines that call `/api/pm/plans`, so I grepped `frontend/` again to find `screens.spec.js:40` and
  `me.spec.js:213` (1 grep, 2 min).
- idea: a brief that removes a route or an API body shape could get a facts section "callers outside the test
  folders" (`git grep` over `tooling/` and `frontend/help-tour/`); the help tour's `setup_tour.py` and
  `desktop.tour.js:96` were found only by a hand grep (BR1-04).
- rule: CLAUDE.md § Docs to keep current says `help/` is "nothing in the step", but the tour's set-up script
  under `tooling/help/` is code that a step can break at once; the entry could say what a step does with the
  tour scripts (fix them, or note them as stale).
