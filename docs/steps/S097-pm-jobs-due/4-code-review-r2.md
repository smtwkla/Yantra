```
Step: S097 — PM jobs come due
Doc: code-review r2
Author: Code reviewer (Opus 5.5)
Date: 02-11-2026
```

# S097 — code review, round 2 (the r1 fixes and the screens)

**Verdict: no `blocker` or `major` finding is open.** Findings: 0 blocker, 0 major, 1 minor, 2 nits. The four
r1 findings are fixed. The screens follow the brief. The one open point is the coder's reported departure:
the due meter values show the meter type's decimals ("at 1,250.0 h"). I recommend the brief's form ("at
1,250 h") for the due points (CR2-01).

**Scope of the read.** Part 1 (verify): the fix round's backend diff, `diff S097 --from-round 1 -- backend`
(`local_db.py`, `pm_jobs.py`, `pm_jobs_core.py`, `pm_plans.py`, `worker.py`, the two test files). Part 2 (a first
review of the screens): these files in full, from the same diff: `frontend/src/views/PmJobsView.vue`,
`frontend/src/utils/pmLabels.js` (the S097 part), `frontend/src/views/equipment/PmPlansCard.vue` (the S097
lines), `frontend/src/stores/navigation.js`, `frontend/src/router/index.js`, `frontend/src/views/SettingsView.vue`,
`frontend/tests/pmLabels.test.js`, `frontend/tests/navigation.test.js`, `frontend/e2e/pm-jobs.spec.js`,
`frontend/e2e/screens.spec.js`. Also read, to check a point: the deactivate confirmation in `PmPlanView.vue`,
`expectDialogFits` in `e2e/support/dialogs.js`, `filterableUnits` and `noUnits` in `stores/equipment.js`,
`formatReading` in `utils/meterLabels.js`, `interval_number` and `trigger_text` in `backend/pm_plans_core.py`,
`e2e/improvements.spec.js:97` and the lane logs of the coder's Normal run (`scratch/e2e-lanes/lane5.log`).

**Tests (my run).** `YANTRA_TEST_RUN=s097cr2 tooling\run-tests.bat`: **ALL SUITES PASSED**. Backend 4956 passed
(116 s), frontend 439 passed, tooling 239 passed (logs `scratch/<suite>-tests-s097cr2.log`). No browser run: no
finding of mine needs one. No schema docs check: the fix round's change to `backend/local_db.py` is a function
outside `_MIGRATIONS`, and `docs/schema/` is unchanged in the round.

**The coder's browser runs** are the right ones: the new tests alone (8 passed), the targeted run with
`pm-jobs`, `pm-plans`, `equipment` and `screens` (91 passed, 2 skipped), the whole suite at Normal once (the
router and the nav are shared code), and the one WebKit S040 run (BR1-03, 1 passed). The Normal run had
1 failure, `e2e/improvements.spec.js:97` (S068).

**The S068 failure: S097 is not the cause.** S097 changes no improvement code and no `e2e/support/` file, and its
specs make no improvement. The lane plan packs whole spec files (LPT by weight), so the new spec moved
`improvement-register.spec.js` and `improvements.spec.js` into the same lane (lane 5). The lane log shows
`improvement-register.spec.js:83` (*S076: the dropped improvement shows under Closed in the period*) ran
before `improvements.spec.js:97`. A dropped improvement lists under *Closed improvements*, so S068's "No
closed improvements yet." fails. This is a latent order dependence in S068's test; any change to the lane
weights can bring it back, including in the release's Full run. A fix-lane step is right (CR2-03 corrects the
cause the report names).

## Round 1 findings

| Finding | Status | Checked |
|---|---|---|
| CR1-01 minor | **Fixed** | `pm_jobs_core.due_copies` quantizes `due_meter`, `meter_window` and `meter_offset` to `0.001`, `ROUND_HALF_UP`, which is MariaDB's rounding for `DECIMAL`. `job_changes` now compares the rounded copies with the stored values. New test `test_the_copies_take_the_column_s_three_decimals`; the report gives its red result. |
| CR1-02 nit | **Fixed** | `_refresh` returns whether it wrote; `settle_plan_job` answers None for an empty change. No caller other than `generate` reads the answer (`pm_plans.py` ignores it). New test `test_the_counts_name_only_real_writes`, red result given. |
| CR1-03 nit | **Fixed** | `local_db.connection_lost(conn, exc)` is the one test. `worker.Worker._connection_lost` is gone, and no test called it. The worker calls the function only in its `OperationalError` branch, so its behaviour is unchanged; `pm_jobs.generate` keeps the `OperationalError` condition it had. `local_db.py` already imports `pymysql`. |
| CR1-04 nit | **Fixed** | `pm_jobs.meter_type_out` is the one copy; `pm_plans._meter_type` is removed and has no caller left. |

The fix round's own diff brings in no new fault that I found.

## Findings

### CR2-01 (minor) — the due meter values show padded decimals, unlike the plan's interval on the same card

- **Where:** `frontend/src/utils/pmLabels.js:231` (`dueText` calls `formatReading`), so also `nextDueText`;
  the tests `frontend/tests/pmLabels.test.js:144-145, 178` and `frontend/e2e/pm-jobs.spec.js:122`.
- **Problem:** this is the coder's reported departure (impl report § 4, round 2). `formatReading` pads every
  value to the type's decimals: Run hours has 1, so a due point reads "at 1,250.0 h". S096 decided the
  other way for planned numbers (S096 BR1-03, `pm_plans_core.interval_number`): an interval shows the places
  it really has, at most the type's decimals, so the plan row reads "Every 250 h". The brief's examples
  follow S096 ("at 5,000 h", "Next due 02-12-2026 or at 3,250 h"). The brief's rule "`formatReading`" was
  written for the numbers in general; its examples show what the floor should read.
- **Which is right for the floor:** a due point is a target someone set (1,000 + 250), not a measurement. It
  has no real tenths. "1,250.0" adds a digit that a low-literacy reader must parse and that carries no
  information. A reading is a measurement, and its tenth is real, so "Run hours now 1,260.0 h" matches the
  readings screens and is right. Today the PM card shows "Every 250 h" and, two lines below, "Next due … or at
  3,250.0 h": two forms of the same kind of number in one row.
- **Failure scenario:** a technician reads the card: "Every 250 h", then "at 3,250.0 h". He asks whether the
  job is due at 3,250 or at some other point, or reads "3,250.0" as "32,500". The list repeats the padded form
  on every meter row.
- **Fix:** show the due point as `interval_number` does: the places the value has, at most the type's
  decimals, Indian grouping. For example, `Number(value).toLocaleString("en-IN", { maximumFractionDigits:
  meterType.decimals })` with the unit, in one helper in `pmLabels.js` (or beside `formatReading` in
  `meterLabels.js`), used by `dueText`. Keep `formatReading` in `meterNowText` (the readings). Update the three
  test lines to "at 5,000 h", "at 3,250 h" and "at 1,250 h". This is one helper change, as the coder says.

## Nits

- **CR2-02** (nit) `frontend/e2e/pm-jobs.spec.js:92`: the card test reads `due.locator(".badge")` over the whole
  plan row; scope it to `due.getByTestId("pm-open-job").locator(".badge")`, so a later badge on the plan row
  (S096's or R03.4's) does not make the locator match two elements.
- **CR2-03** (nit) `docs/steps/S097-pm-jobs-due/3-impl-report.md` § Tests, round 2: the S068 failure's cause is
  `improvement-register.spec.js:83` (S076, a dropped improvement listed under *Closed*) earlier in lane 5, not
  "the spec's S073 test": in one file, line 97 runs before line 573. Correct the sentence, so the fix-lane step
  starts from the right test.

## Checked and found consistent

- **The PM list against § 5.9.** Route `/pm` (title "PM") after the improvements routes; nav item *PM* after
  *Tickets* with `pm_job:read`, so `canOpenRoute` guards a typed `/pm`, and the storekeeper has neither. Tabs
  *Due* and *Upcoming* as `nav nav-tabs` router links; `tab=upcoming` in the URL, *Due* the default and left
  out; `unit_id` and `assigned=me` in the query; `router.replace`, so Back leaves the list as it was. The
  select *Unit* (`aria-label="Unit"`, "All my units", then `filterableUnits`, as the tickets list). The tick
  *Assigned to me* only with `userPersonId`.
- **The rows.** The whole row is the link to `/equipment/pm/<plan id>` (D11), at least 44 px. Badge from
  `STANDING_LABELS` and `STANDING_BADGES` (the four colours of § 5.9), the serial in small text, the due text
  and " · N days ago" from `days_past` (BR1-06: the badge judges, the words count); the machine in bold; the
  plan with its item count ("1 item", "7 items"); the unit's full code, `meterNowText` and `assigneeText`
  ("Operator" for an operator plan, "No one yet"). The order is the server's `list_order`.
- **The count line.** `countText`: "4 due · 1 overdue" on *Due*, a zero part left out, no line for none;
  "3 upcoming" on *Upcoming* (BR1-05). Tested in vitest for each case.
- **The states.** "Loading…", the load error "PM jobs could not be loaded: <message>" with *Retry* (a full-size
  button), `NO_UNITS_TEXT`, and the three empty texts. A late answer of an earlier query is dropped
  (`loadSeq`). A user with no Team record has no `pm_job:read` and no *PM* item; IT admin, who may have none,
  gets the list without the tick.
- **The card line against § 5.10.** Only for an active plan with a `schedule`: the open job's badge and
  "serial · due · N days ago", then the meter now for a meter plan; else `nextDueText` ("Next due …", "Next
  due … · Run hours: no reading yet", "Next due when Run hours has a reading"). `schedule` null: no line.
- **The Settings label** `pm_generate`: "Create the PM jobs that are due or coming up", in schedule order.
- **The phone.** No fixed width: the filters wrap (`flex-wrap`, `w-auto mw-100`), the tabs fill (`nav-fill`),
  long words break (`overflow-wrap: anywhere`), no `btn-sm`. The seven-item bottom bar fits on both phones
  (the S040 test on `phone-chromium` in the Normal run and on `phone-webkit` in its own run, A3).
- **Layering.** The standing, the tab, the order, the counts and the days are the server's; the frontend only
  puts them in words (`pmLabels.js`). The two extra helpers, `nextDueText` and `countText`, keep the
  wording out of the templates and are tested; reported in § 4.
- **The browser tests against § 8.4.** All eight tests are there, with the briefed names, set-up by API, each
  finding its own row by the machine's code. Each asserts what the user sees: the badge, the serial pattern,
  the date and "10 days ago", the plan and "1 item", "SMTW.MCC2 · Kannan (technician)", the plan page heading
  after the tap; the row absent from *Due* after a wait for the list; the URL and the tick after a reload. Only
  the fit test is `@device`, and its purpose is a layout check: right. No test opens a modal dialog: the
  deactivate confirmation is the inline *Yes* of `ActiveToggle`, not a `FormModal`, so `expectDialogFits` has
  nothing to check (the coder's reason holds). `screens.spec.js` adds `/pm` for `TICKET_ROLES` with the
  `.nav-tabs` "Due" link (BR1-09) and the seven-item bar.
- **The frontend unit tests** cover each helper and each branch, and `navigation.test.js` makes the briefed
  changes and the new test (PM after Tickets; the storekeeper cannot open `pm`).
- **Manual checks.** The impl report's `## Manual checks` lists the four **important** checks of § 8.4 as
  `[auto]` with their tests, the other four tests, the `/pm` screen and the bottom bar; each has a passing run
  behind it. No real-device check (§ 8.5), so no row in `docs/steps/device-checks.md`.
- **Docs pass.** `## Docs updated` matches the step's diff: `Plan.MD` § 3, § 4.3 *Built (S097)* (its *Screens*
  sentence matches the screens as built) and § 6; `.claude/CLAUDE.md` Self-check (2) and the SMTW-Review point;
  `docs/schema/` from round 1. Round 2 changes no migration, secret, role or claim.
- **Security.** No new route in round 2. The screens send no actor; the filters go to `GET /api/pm/jobs`, whose
  arguments the server checks (`enum_arg`, `int_arg`).
- **Track:** full, as it must be.

## Manual checks

None for the user. Every important check of the brief is automated and green in the coder's runs. The brief has
no real-device check.

## Feedback

- idea: the coder's report named the wrong earlier test for the S068 failure; finding the real one took four
  reads of `scratch/e2e-lanes/lane*.log`. `run_lanes.py` could print, for each failed test, the spec files its
  lane ran before it (one line in the summary).
- hindrance: `Grep` with an alternation that held `_meter_type\b` matched every `meter_type` word in the backend,
  and its 25 KB output went to a file (1 wasted call).
