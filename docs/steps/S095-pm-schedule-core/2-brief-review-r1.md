```
Step: S095 — PM scheduling core
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 01-11-2026
```

Reviewed against: c9cd091

# S095 — brief review, round 1

**Verdict: one `major` is open (BR1-01, the plan key `kind` against S096's `trigger_kind`); no
blocker.** The rules are sound: every worked example of § 5.6 and the window table of § 5.3
reproduce exactly from the stated rules (checked with a read-only script against
`contracts_core._add_months`'s algorithm). The departure D4 is sound as a core rule; it has two
consequences for R03.3 and R03.7 that the brief should name (BR1-02). Facts file read:
`scratch/brief-facts-S095.md`; every cited line and name checks out. Full track, round 1 of up to 3.

## Findings

### BR1-01 — major — The plan key `kind` will not survive S096's row

**Problem.** § 5.1 names the trigger kind key `kind`, and § 4 says "the column names of S096's
`pm_plans` are the input names of § 5.1, so the shell passes a row". S096 is being told to name
the column `trigger_kind ENUM('calendar','meter','both','before_use')`. And `docs/schema/notes.json`
(line 63) plans `pm_plans` with a `kind (PM / CIL)` column: on the real row, `kind` means PM or
CIL, not the trigger.

**Why it matters.** With the whole row passed, `row["kind"]` would be `pm` or `cil`, and the core
raises `ValueError("kind")` on every plan (D8). Both steps are coded tonight with nobody to
arbitrate; a rename later touches two steps and R03.3.

**Options.**
- **(a) Rename the input key to `trigger_kind` — recommended.** The constants stay `CALENDAR`,
  `METER`, `BOTH`, `BEFORE_USE`; the tuple may stay `KINDS` (S096 imports it for the ENUM) or
  become `TRIGGER_KINDS` for the same reason the key is renamed. Update § 1, § 5.1, T8, T10, E19
  and Q5.
- (b) Keep `kind` and have S096 name its column `kind`. It then collides with the planned PM / CIL
  kind in `notes.json`, which R03.12 needs.

### BR1-02 — minor — D4 is sound; name its two consequences for the user and for R03.3 / R03.7

**Problem.** D4 (*Due* through the on-time window, *Overdue* after it) departs from R03.1's "Overdue:
past due" and from Q3.3's wording, and the brief flags it for gate B (Q1). The reasoning holds:
under D4 the list and the report never contradict each other, and a daily-read counter cannot
skip *Due*. But two consequences are not written down:
1. **On the list** a job past its due date reads *Due* for up to the grace: 3 days on a monthly
   plan, 36 days on a yearly one. The person scanning *PM* cannot tell "due today" from "due 20 days
   ago" unless the row shows the due date and the days past it. That is R03.3's screen, and it
   must know.
2. **The overdue alert** (R03.7, "PM job overdue, once") would fire only when the job already counts
   late. R03.7 may want it earlier (for example at the due date, with *Due* in its text), or the
   grace end is exactly the right moment. Either way R03.7 decides it knowingly.

**Why it matters.** KLA confirms Q1 at gate B from the brief's text; the trade-off he confirms
should be the whole one. R03.3 and R03.7 are briefed from the roadmap, which still says "past due".

**Options.**
- **(a) Keep D4 (a); add both consequences to D4 and to Q1, and a line in § 3 Docs that the Plan.MD
  § 4.3 note states them, so R03.3 and R03.7 pick them up — recommended.**
- (b) Switch to the roadmap's literal rule (Overdue from the day after due) and let `timeliness`
  alone carry the window. Simpler for the list, but a job can read *Overdue* while counting on time.

### BR1-03 — minor — What R03.3 must keep on the job is not stated, and D9's claim depends on it

**Problem.** `job_state(due, …)` takes a whole `Due`: `grace_days`, `upcoming_days` and
`meter_window` as well as the two due values. D1 says "R03.3 stores `due_on` and `due_meter` on the
job and later asks the state of the stored values". The windows are not among the stored values.
Two ways out, with different behaviour: the job stores the three windows too, or R03.3 recomputes
`next_due` from the plan each time with the job's override, and then a plan edit after the job was
made changes the job's windows and due date. Related: a job stored with `due_meter` None (E16, E17)
never gains a due value when the meter's first reading arrives, so D9's "does not stay 'No reading
yet' for ever" holds only if R03.3 recomputes, and `no_reading` would read "No reading yet" while a
reading exists.

**Why it matters.** The coder of S095 need not decide it, but the brief's own claims (D1, D9) lean
on a shell rule nobody has written down; R03.3's brief would have to rediscover it.

**Options.**
- **(a) Add a § 9 note "For R03.3's brief": `job_state` needs the windows, so either store them on
  the job or recompute `next_due` from the plan with the stored override (say which the brief
  recommends); and a job whose `due_meter` is None is recomputed in the daily run until it has one —
  recommended.**
- (b) Make `job_state` take the plan and recompute inside. It would blur D1's split and the override.

### BR1-04 — minor — The number types: say what the core checks

**Problem.** § 5.1 says `calendar_every` is "int ≥ 1" and meter values "`Decimal` (an `int` also
works); never a `float`", but the checks are listed only for dates (`type(x) is date`). Python's
behaviour with a wrong type is uneven (checked 01-11-2026): `Decimal + float` raises `TypeError`,
`timedelta(days=Decimal("3"))` raises `TypeError`, but `Decimal("3000") < 3001.5` passes silently,
so a float reading would give a state with no error. D8 wants a shell bug to fail loudly.

**Why it matters.** The coder would decide alone whether a float or a `Decimal` interval is refused,
and T8 does not test it.

**Options.**
- **(a) State the checks: `calendar_every` must be an `int` (not `bool`) ≥ 1; `meter_every`,
  `last_done_meter`, `start_meter`, `done_meter`, the reading value and the override's `due_meter`
  must be `Decimal` or `int`, a `float` raises `TypeError` naming the key; add them to T8 —
  recommended.**
- (b) Convert floats with `Decimal(str(x))`. It hides the bug D8 wants to see.

### BR1-05 — minor — `reading["taken_on"]` is required, checked and never used

**Problem.** § 5.4: `reading` is a mapping with `value` and `taken_on`; "`taken_on` is checked as a
date and not used otherwise (the screen shows it)". Every caller (R03.3's daily run and list,
R03.16's ticket target) must convert the reading's `taken_at` (a `DATETIME`) to an IST date only to
pass a type check. The screen shows the reading's time from its own query, not from this core.

**Why it matters.** A contract field that does nothing is an abstraction without a use
(CLAUDE-COMMON *Simplicity first*), and the conversion is a line of shell code per caller that can
be wrong (UTC date for IST) with no effect to catch it.

**Options.**
- **(a) `job_state(due, reading_value, today)` with `reading_value` a `Decimal` or None —
  recommended.** The tests get shorter too (T4, T5, T9).
- (b) Keep the mapping, ignore extra keys and drop the `taken_on` check.

### BR1-06 — minor — Plan.MD § 4.3's limit-crossing trigger is not placed

**Problem.** Plan § 4.3 *Triggers* reads "Meter: every N units of a meter …, **or when a reading
crosses a limit**". The brief's `KINDS` has no such kind, and § 1 Out of scope does not mention it.
Plan § 4.5 and Maintenance-Philosophy § 7 treat a gauge over its limit as a ticket
(condition-based), not as a PM job falling due.

**Why it matters.** S096's ENUM is fixed tonight on `KINDS` (D7). If the crossing trigger is a PM
trigger, the ENUM lacks a value; if it is a ticket, the Plan line should say so when the coder
writes the *Built (S095)* note (§ 3 Docs).

**Options.**
- **(a) Out of scope line: "A gauge crossing its limit is not a PM trigger: it raises a ticket (Plan
  § 4.5, R03.10); `KINDS` has no kind for it." The Plan.MD note says the same — recommended.**
- (b) Add a fifth kind now. Nothing in R03 uses it.

## Nits

- **BR1-07** (nit) § 5.4: the rule "`trigger` names that trigger" and the dataclass comment "None
  for NOT_YET" pull apart. Say once: `trigger` is None whenever the state is NOT_YET, also when a
  calendar trigger gave it (E16, E17 at 20-11, E18).
- **BR1-08** (nit) § 5.3 `Due`: say `meter_window` is None without a meter trigger (the comment
  says it only for the other fields).
- **BR1-09** (nit) § 5.3 Override: say that an override `due_meter` on a meter plan with no base
  value is allowed (the trigger exists) and makes `no_reading` False once a reading exists.
- **BR1-10** (nit) § 5.5 last bullet: "never disagree" holds when `done_meter` is the value the
  list judged on; qualify it ("at the same date and meter value").
- **BR1-11** (nit) D3 or E7: a daily plan's grace equals its whole interval (done 01-11 → due
  02-11, on time through 03-11) because of the 1-day floor. One line, so KLA sees it at gate B.
- **BR1-12** (nit) § 3 Docs, Plan.MD line: Plan § 4.3 *Triggers* still reads "every N days / weeks /
  months"; the *Built* note adds *years* (A2) — the brief says so, but have the coder edit the
  Triggers bullet itself, not only append.

## Checked and found consistent

- `backend/contracts_core.py:357` `_add_months`, its one call at `:371` inside `renewal_period`
  (`:364`), and the docstring at `:5` ("two cores do not import each other's private helpers"): as
  the brief says. `backend/tests/test_contracts_core.py:19` imports `_add_months`; `:387`
  `test_add_months_keeps_the_month_end` uses it; the three `test_renewal_period_*` tests run
  unchanged after the rename.
- Month arithmetic: `_add_months` gives 28-02-2027, 29-02-2028, 28-02-2027 (from 30-11-2026 + 3,
  90 days), 10-01-2028 (365 days), 28-02-2029 (from 29-02-2028 + 12, 365 days), 28-03-2027 (no snap
  back). A1's claims hold.
- The window table (1 → 1/1, 7 → 1/1, 28 → 2/2, 30 and 31 → 3/3, 90 → 9/7, 365 and 366 → 36/7) and
  every state and timeliness in E1–E22 follow from § 5.3–5.5 as written. Q1.1's "monthly 3 days,
  yearly 36" and Q3.1's "7 days or 10 %, the shorter; meter within 10 % of N" are met.
- `Decimal("250") / 10 == 25`, `Decimal("0.5") / 10 == Decimal("0.05")`; `date(9999, 12, 31) + 1 day`
  raises `OverflowError`, `_add_months` past 9999 raises `ValueError`.
- D1's frozen dataclasses follow `tickets_core.Move` (`backend/tickets_core.py:375`): no new pattern.
- D6 is the DRY choice; no shared date module exists in `backend/` (IST is a constant in
  `equipment.py:180` and `worker.py:42`; `_iso_date` is a parser), so "a new dates module for 4
  lines" is rightly rejected.
- Standards: EN 13306 (preventive, predetermined, scheduled), SMRP PM compliance (the 10 % window)
  and TPM planned maintenance are named and explained in plain words, as the settings ask; the
  roadmap's *to verify* marks are kept.
- Decisions of the roadmap followed: Q1.1 (a), Q1.2 (a), Q3.1 (a), Q3.3 (a), Q9.1 (a), R03.13
  (before use never due, not judged); Plan § 4.3 floating rule and whichever first; Plan § 4.5
  counter reset noted (A3).
- Track full: no migration, but a new module design. No screen, no device check, no browser test;
  § 8 lists the runs and the line-width test (S094). Q4's SMTW-Review point is a good invariant.
- Pure core: imports `datetime`, `decimal`, `dataclasses`, `contracts_core` only; no clock; the
  shell passes IST dates (A4).

## Feedback

- idea: the facts file lists Python built-ins (`ValueError`, `TypeError`, `OverflowError`) as code
  names, "defined at none found" with 21 uses, and marks `OverflowError` "planned in S096"
  (`scratch/brief-facts-S095.md` lines 52–57, 80); skip names that `builtins` has.
- hindrance: `docs/steps/S096-pm-plans/` exists but holds no brief, so the cross-step name check
  (BR1-01) rests on the orchestrator's message; a drafted brief, even partial, would let the
  reviewer read the column names.
