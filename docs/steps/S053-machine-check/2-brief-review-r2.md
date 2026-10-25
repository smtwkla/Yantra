```
Step: S053 — Machine check before browser runs
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 25-10-2026
```

Reviewed against: 2bc798c (the uncommitted changes are step documents and the step skill only)

# S053 — Brief review, round 2

**Verdict: no `blocker` or `major` finding is open.** Six `minor` findings and eleven nits.
Full track, round 2 of up to 3. The brief was rewritten from the advice, so I re-read every
section; the round-1 settlement I checked only for presence (below). The facts file
`scratch/brief-facts-S053.md` is round 1's (it still names `read_power` and
`scratch/coretemp-probe.py`); no facts run was made for this version, so I checked the new
names in the code myself.

**Every accepted round-1 answer is in the brief text.** BR1-01 (§ 1.1 Failures, § 1.2 last
bullet, § 1.3 daemon thread and `try/finally`, § 3 tests), BR1-02 (§ 1.1 Core Temp's empty
read, § 1.3 `temp_samples`, decision 7), BR1-03 (§ 1.4, § 1.5), BR1-04 (§ 3, with BR2-01
below), BR1-05 (§ 1.2 shelf life, § 1.3 merge, with BR2-02 below), BR1-06 (§ 1.2, decision 4),
BR1-07 (§ 1.3 capacity), BR1-08 (header), BR1-09 to BR1-19 (named functions, fields, the
single-stack path, no colon split, "every e2e run they report", KLA's Core Temp check, ISO/IEC/
IEEE 29119-3, the constants list).

**The ctypes claims of § 1.1, checked on this laptop** (25-10-2026, 16:10, Core Temp running,
barrel adapter, read-only `ctypes` script in the scratchpad; the advice § 7 code as written, no
`argtypes`):

| Claim | Seen |
|---|---|
| `SYSTEM_POWER_STATUS` 4 bytes + 2 DWORD | `sizeof` 12, as documented; `ACLineStatus 1`, `SystemStatusFlag 0` |
| `SYSTEM_BATTERY_STATE`: 4 BOOLEAN, `Spare1[3]`, `Tag`, 6 × 32-bit; `Rate` signed | `sizeof` 32, as documented; `Rate` at offset 16, `RemainingCapacity` at 12; `AcOnLine 1`, `Discharging 0`, `Rate 0`, `MaxCapacity 53511`, `RemainingCapacity 53511`, `BatteryPresent 1`; both calls 2.2 ms the first time |
| `PDH_FMT_COUNTERVALUE` `DWORD` + union read as `double` | `sizeof` 16, as documented (the double is 8-aligned); `CStatus 0` on both counters |
| PDH two counters, 1 s gap, a Python `str` path accepted | 1.39 s the first call, 1.00 s the second; `% Processor Performance` 124 % and 119 % **at idle** (7 % utility) — the idle value swings 60–125 % (advice: 60–99 %), which supports "information only" (nit BR2-15) |
| a missing counter is a non-zero status, not a hang | `PdhAddEnglishCounterW` on a made-up path returned `0xC0000BB8` at once |
| Core Temp opened, read 2686 bytes, closed | `Intel Core i9 13950HX`, 24 cores × 1 CPU, TjMax 100, hottest 61.5 °C, flags 0 / 0 |

Nothing in the readers can block: the three power calls are in-process reads, PDH's only wait
is the 1 s `sleep` between its two collects (inside the sampler thread; 1.0–1.4 s once before
the run), and `mmap` cannot wait on anything.

---

## BR2-01 — minor — `fake_run` does not keep working through the keyword; the two `TestLevels` tests change either way

**Problem.** § 3 says `run()` gains `machine_file=None` and "`fake_run` keeps working through the
keyword". `main()` must hand `run()` the record path somehow. If it calls
`run(args, wanted, shared / TIMINGS_NAME, machine_file=shared / MACHINE_NAME)`, then
`fake_run(args, wanted, timings_file)` (`test_run_lanes.py:212`) and the
`lambda *a: …` (`:223`) both raise `TypeError` on the keyword. So those two tests change in two
places, not one: the `before_run` stub the brief names, and a `machine_file=None` (or `**kwargs`)
parameter on their fakes. The alternative, `run()` deriving the path from
`timings_file.parent`, keeps the fakes but needs no keyword at all, and then `TestRun`'s seven
tests (which call `run(…, tmp_path / "t.json")`) would start a real sampler unless `Sampler` is
stubbed. The brief mixes the two: it keeps the keyword **and** stubs `Sampler` in `TestRun`, and
stubs `before_run` there too, though `before_run` is called from `main()`, which `TestRun` never
enters.

**Why it matters.** The coder has to pick one shape and will find the `TypeError` by surprise;
the brief claims a test is untouched that is not.

**Options.**
- (a) **Recommended.** Keep the keyword, `None` = no sampler and no record. State in § 3: `main()`
  passes `machine_file=`; the two `TestLevels` fakes gain `machine_file=None`; they also stub
  `before_run`. `TestRun` needs no stub (its `run()` calls pass no `machine_file`). Drop the
  `TestRun` line.
- (b) `run()` derives the record path from `timings_file.parent / MACHINE_NAME`; the fakes stay;
  `TestRun._stub` replaces `Sampler`. Rejected: a hidden coupling of two files to one folder, and
  a sampler that cannot be switched off.

## BR2-02 — minor — A carried-over value gets a new `written` time, so the shelf life never runs out on it

**Problem.** § 1.3: "A `null` field keeps the previous record's value for that field (if that one
is still within its shelf life)". The merged record has one `written` time, this run's. So a
`drained_on_mains: true` from a dock run on Monday 10:00 is carried by a short run on Tuesday
09:00 (the previous record is 23 h old, inside the shelf life) and stamped Tuesday 09:00; a
short run on Wednesday 08:00 carries it again. One run under 4 samples (about 2 minutes: one
spec file, or `screens.spec.js` alone) per 24 h keeps the flag alive for ever, and every one of
those runs is cut to 3 lanes with "Connect the barrel adapter" while the adapter is in. The same
holds for `busy_speed_pct`. The 24 h rule of § 1.2 (BR1-05, accepted) does not hold as written.

**Why it matters.** This is the "stale value cuts lanes" case; a rule that cries wolf gets
`E2E_LANES=6` put in the shell for good, which switches the step off.

**Options.**
- (a) **Recommended.** Each judged field carries the time it was judged: `drain_judged_at` and
  `speed_judged_at` (ISO, IST), written when the field gets a value, carried unchanged with a
  carried value. § 1.2's shelf life reads those times, not `written`. `merge_record` test: a value
  judged 25 h ago is not carried, whatever `written` says; a value carried once keeps its time.
- (b) Carry a value only once: a record whose field was itself carried does not pass it on.
  Rejected: two short runs in a row on the day of the dock run lose the finding by lunch.

## BR2-03 — minor — The drain's `false` branch is too wide: a run on battery clears the weak-charger finding

**Problem.** § 1.3: `drained_on_mains` is `true` under the conditions given, "`false` otherwise;
`null` with fewer than `SAMPLES_TO_JUDGE` samples". A run of 4 or more samples that was **not** on
mains in every sample (on battery throughout, or unplugged for a moment) falls into "otherwise"
and writes `false`. `false` is a value, so the merge takes it over a previous `true`: a run on
battery clears the dock finding, though the charger was never tested. Two smaller gaps in the same
rule: a sample whose battery read failed (`None`) is neither "on mains" nor "not on mains", and
"fell by more than 2 %" names no base (`RemainingCapacity` of the first sample, or `MaxCapacity`).

**Why it matters.** The drain is the only sign of the weak dock (decision 5); its three-way value
decides whether a long run's finding survives.

**Options.**
- (a) **Recommended.** Rewrite the row: samples with no battery reading are left out; `null` when
  fewer than `SAMPLES_TO_JUDGE` samples remain **or** any remaining sample was not on mains;
  otherwise `true` on any of the three signs, else `false`. The 2 % is of `MaxCapacity` (the full
  charge, from the same call: 53511 mWh here, so 2 % is 1070 mWh, a 32 W shortfall over 2 minutes
  or 6 W over 10). Add the test "on battery in one sample → `null`".
- (b) Keep `false otherwise` and make the merge keep `true` over `false`. Rejected: then a healthy
  long run on the barrel adapter could never clear the flag.

## BR2-04 — minor — `machine_check.main()` needs the record's path, which only `run_lanes.main_scratch()` knows

**Problem.** § 1.5: the `.bat` prints "the last record's after-run line if it is within its shelf
life", and § 1.3 puts the record in `main_scratch()` (`run_lanes.py:298`). § 3 has `run_lanes`
import `machine_check` (`before_run`, `Sampler` bound as its attributes). For `machine_check.main()`
to call `main_scratch()` the import must also go the other way: a circular import at module
level. The brief does not say which module owns the path or which way the imports go.

**Options.**
- (a) **Recommended.** `machine_check.main()` imports `main_scratch` from `run_lanes` inside the
  function, with one comment ("imported here: run_lanes imports this module"). `run_lanes` stays
  the owner of the main working folder's `scratch/`; `machine_check` has no module-level
  dependency, so its pure functions import anywhere. State it in § 3.
- (b) `machine_check.py` reads `ROOT / "scratch" / "e2e-machine.json"`. Rejected: the `.bat` run
  from the release's worktree would read an empty folder while the runner writes to the main
  folder's; two paths for one file.
- (c) The `.bat` runs `run_lanes.py --machine-check`. Rejected: a flag on the runner for a thing
  that is not a run.

## BR2-05 — minor — The after-run summary and the record write are outside the "never stops a run" guard

**Problem.** § 1.2's last bullet guards the check **before** the run (`try/except Exception`, one
line, the run goes on). § 1.3's after-run work — `run_summary`, `merge_record`, writing
`e2e-machine.json`, the after-run line — has no such sentence. It runs after the lanes, before
`run()` returns its exit code; a write error (`scratch/` read-only, a half-written file to read
first) would raise out of `run()`, and the release's test step would fail on the record, not on a
test. (`read_json` already swallows a broken file, so the read is safe; the write is not.)

**Options.**
- (a) **Recommended.** One sentence in § 1.3: the after-run summary and record write are in the
  same `try/except Exception` as the check, printed as "The machine record could not be written:
  <error>." and the run's exit code is unchanged. One test: a record path in a folder that does
  not exist does not change the exit code.
- (b) Leave it to the coder. Rejected: the rule is the step's own (BR1-01).

## BR2-06 — minor — Manual check 2 (the dock alone) decides whether the step does what KLA asked, so it is **important**

**Problem.** § 5 marks all three KLA checks "not important". Check 2 is the one run that shows
whether the drain rule sees the weak dock at all (assumption 2, § 6). "Not important" means the
step can be `Done` with the dock never tested; the record then never says "drained", the
before-run line never names the charger, and nobody knows whether the rule is dead or the dock
coped. Check 3 (energy saver) is similar but smaller: a dead energy-saver rule costs nothing.
Check 1 (Core Temp closed) is the coder's unit test by another route; plain is right.

**Why it matters.** KLA's request was "lookup battery power … and pass it on"; the dock is the
case he named.

**Options.**
- (a) **Recommended.** Mark check 2 **important**, with what it decides: "drained → the rule works;
  not drained with `Rate` 0 in every sample → the planner proposes the next sign (an amendment)".
  Keep checks 1 and 3 plain. `Done` then needs check 2 done or skipped by KLA (README § Manual
  checks), which is the right gate for the step's main claim.
- (b) Keep all three plain. The user may choose it; then § 6 assumption 2 stays open after `Done`,
  and the brief should say so.

---

## Nits

- **BR2-07** (nit) § 1.1 `parse_core_temp`: test "no temperature above 0" on the raw `fTemp`
  values, before the delta conversion. In delta mode a zero `fTemp` converts to TjMax, so a Core
  Temp that has just started (zeros, name set) would read 100 °C on every core and cut the run to
  2 lanes. KLA's Core Temp is not in delta mode today (flags 0 / 0), so this is a guard, not a
  fault seen.
- **BR2-08** (nit) § 1.2 / § 3: `advise(now, last_run, default_lanes, now_time)` has two "now"
  parameters for two things. Name them `readings`, `record`, `default_lanes`, `now`.
- **BR2-09** (nit) § 1.3 `busy_speed_pct` is the **lowest** busy sample, so one odd 30 s sample
  (an E-core-heavy moment at 50 % utility) cuts lanes for a day. Add "lowest or mean of the busy
  samples" to § 6 question 1, so the choice is tuned with the thresholds; the mean is steadier.
- **BR2-10** (nit) § 1.3 merge: say which fields merge. The judged ones carry over
  (`drained_on_mains`, `worst_rate_mw`, the two capacities, `busy_speed_pct`, and BR2-02's
  times); `written`, `lanes`, `samples`, `temp_samples`, `peak_c` are this run's, `null` kept as
  `null`. Otherwise last week's `peak_c` sits in a record of a run Core Temp did not see.
- **BR2-11** (nit) § 1.4, scope B: (1) "Cool the laptop: air conditioning, a stand under it." →
  "Cool the laptop. Turn on the air conditioning or put it on a stand."; (2) the hot sentence
  repeats the temperature that part 1 just gave ("hottest core 93 °C. … The hottest core is
  93 °C.") → "It is too hot for a full run. Cool the laptop. …"; (3) the slow sentence has a
  parenthesis and three actions in one sentence → "In the last run the processor ran at 64 % of
  its speed while busy. Turn off energy saver. Set Power mode to Best performance. Cool the
  laptop."; (4) "processor at 90 % of its speed at 5 % busy" → "processor at 90 % of its speed,
  5 % busy".
- **BR2-12** (nit) § 1.4: say that the warm rule (90–95 °C) prints the hot sentence (it is the
  only temperature sentence), and give the after-run drained line for the `Rate` sign, where no
  capacity fell: "The battery drained on mains power (it drew up to 35 W from the battery)."
  from `worst_rate_mw`.
- **BR2-13** (nit) § 1.5 / § 3 `tooling/machine-check.bat`: the lane sentence when no rule matches
  ("A run now would use up to 6 lanes."); call the script as the other `.bat`s do
  (`uv run --no-project python "%~dp0e2e\machine_check.py"`), not by a path relative to the
  current folder.
- **BR2-14** (nit) § 1.3 `Sampler.stop()`: also `join(SPEED_GAP_SECONDS + 1)`, so a sample inside
  its 1 s PDH gap finishes before `run_summary` reads the samples; otherwise the last sample is
  sometimes missing from the count.
- **BR2-15** (nit) § 1.1 PDH row: "idle 88–99 % at 5 % busy" — today it read 119–124 % at 7 %
  busy, the advice § 1 says 60–99 %. Write "60–125 % at idle (it says nothing at idle)", so the
  coder and KLA do not read the before-run number as a sign.
- **BR2-16** (nit) § 3 readers: set `argtypes` and `restype` on the PDH and power calls
  (`PdhAddEnglishCounterW`'s path is `LPCWSTR`, its user data `DWORD_PTR`; `CallNtPowerInformation`
  returns `NTSTATUS`) — explicit over implicit; the advice's bare calls work but rely on ctypes'
  defaults. Treat `CStatus` other than 0 or 1 (valid / new data) as a failed read.
- **BR2-17** (nit) § 5 device rows: `device-checks.md`'s columns are account, network and where;
  write "—", "—", "KLA's laptop, the dev working folder" so the rows do not look unfinished.

---

## Checked and found consistent

- The struct layouts and sizes of § 1.1 against the documented headers and the advice § 7 code
  (table above); `Rate` read as `LONG` is right (documented as signed, negative while
  discharging); `SystemStatusFlag` is the documented battery-saver flag; the English counter
  paths resolve on this machine; a bad path returns a status, not a hang.
- The place of the check in `main()` (`run_lanes.py:565–574`): after `one_run_at_a_time`, before
  `needs_webkit_server` and `run()`, so before the container, the `--list` run and the plan;
  `wanted` is the local to replace; "`E2E_LANES` set" is `"E2E_LANES" in os.environ`, which
  nothing in the repo sets (`run-e2e-tests.bat`, `release-tests.bat`, the agents only document
  `set E2E_LANES=1`); `run()` already takes `min(wanted, len(groups))`.
- The sampler's place: around `run_lanes(lane_runs)` (`run_lanes.py:610`) and `single_stack`
  (`:584`, `:594`), so its first sample is at the lanes' start, after `--list` and
  `create_databases`; 4 samples at 30 s is 90 s into the lanes.
- `machine_check.py` imported from `run_lanes.py` works as a script (`sys.path[0]` is
  `tooling/e2e`) and in `test_run_lanes.py` (`sys.path.insert` of `tooling/e2e`, line 10);
  `run-tooling-tests.bat` runs `pytest -q tooling\tests`, so `test_machine_check.py` is picked
  up with no script change.
- `main_scratch()` is the right home for `e2e-machine.json` (beside the lock and the timings,
  shared by the release's worktree), and `read_json` already copes with a missing or broken file.
- § 1.2's table against § 1.3's record: every last-run rule reads a field the record holds;
  "no peak rule" matches the advice § 2.4; the energy-saver rule is harmless if the flag never
  sets while plugged in (check 3 decides).
- The standards: ISO/IEC/IEEE 29119-3's *test environment readiness report* is the right term
  for the two lines and the record; the TjMax note is correct for this processor.
- No app code, migration, RBAC or data; Plan.MD, the maintenance docs and the schema are not
  due; `.claude/CLAUDE.md` § Browser tests (line 29) is the paragraph to extend; the agents'
  e2e paragraphs (`coder.md:118–140`, `code-reviewer.md:50–66`) are where § 1.6's line fits.
- Out of scope and decisions 1–7 match the advice's recommendations (§ 3, § 4) and KLA's U1
  answers; nothing undocumented is read.
