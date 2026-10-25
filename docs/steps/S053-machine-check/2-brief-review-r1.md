```
Step: S053 — Machine check before browser runs
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 25-10-2026
```

Reviewed against: 2bc798c (the uncommitted changes are step documents only)

# S053 — Brief review, round 1

**Verdict: two `major` findings are open** (BR1-01, BR1-02). Light track, so this is the
only round unless a `blocker` or `major` stays open; per `README.md` § Tracks a `major`
switches the step to the full track, and BR1-08 says which light criteria it strains anyway.
Facts file read: `scratch/brief-facts-S053.md`.

I re-ran the § 1.1 probes on this laptop (25-10-2026, 15:05, Core Temp running, barrel
adapter, Balanced plan, room cool):

| Claim (§ 1.1) | Seen now |
|---|---|
| Core Temp shared memory readable, 24 cores, TjMax 100, flags 0 | yes: `Intel Core i9 13950HX`, 24 cores, TjMax 100, hottest 69.5 °C, `ucFahrenheit` 0, `ucDeltaToTjMax` 0 |
| **Without Core Temp the read fails** (`None`, "Only while Core Temp runs") | **no**: `mmap.mmap(-1, 2686, "<a name nobody made>", access=ACCESS_READ)` opened fine and returned 2686 zero bytes (`uiCoreCnt` 0). Windows creates a page-file mapping of that name when none exists. See BR1-02 |
| `% Processor Performance`, 2 samples 1 s apart, about 2.5 s | 2.7 s; one sample 1.6 s |
| 95–110 % on mains | 78–95 % at idle on mains, cool. See BR1-06 |
| `BatteryStatus` `PowerOnline` / `Discharging`, about 0.1 s | `PowerOnline True`, `Discharging False`, `DischargeRate 0`, `RemainingCapacity 53511`; 0.5 s |
| `EnergySaverState` value 2 | 2 |

The struct layout the probe reads (offsets 0, 1024, 1536, 1544, 2568, 2584, 2684, 2685) is
Core Temp's `CORE_TEMP_SHARED_DATA`: `uiLoad[256]`, `uiTjMax[128]` (one per CPU, not per core),
`uiCoreCnt`, `uiCPUCnt`, `fTemp[256]` (index `cpu × uiCoreCnt + core`), `fVID`, `fCPUSpeed`,
`fFSBSpeed`, `fMultipier`, `sCPUName[100]`, `ucFahrenheit`, `ucDeltaToTjMax`. Newer Core Temp
builds append fields after these; the base block is unchanged, so the reader is right to stop
there. In delta mode a temperature is `TjMax − fTemp`; in Fahrenheit mode `fTemp` and `uiTjMax`
are both °F. The brief's "the reader converts both to °C" holds.

---

## BR1-01 — major — Nothing in the brief stops the check or the sampler from hanging a run

**Problem.** The brief promises "it never fails" (§ 1.5) and "the run goes on" (§ 1.1), but
names no mechanism:
- `read_power()` runs `powershell -NoProfile` with no timeout. `subprocess.run` without
  `timeout=` waits for ever. `Get-CimInstance` on `root/wmi` and `Get-Counter` do hang when
  the WMI service is wedged (a known Windows state after sleep), and `Get-Counter` can take
  10 s or more on a loaded machine. The check runs inside the e2e lock, before every run,
  the release's included: a hung PowerShell is a hung release with no message.
- The `Sampler` is "a thread … stops when the lanes end (an `Event`)". If it is not a daemon
  thread, any path that leaves `run()` without `stop()` (an exception in `run_lanes`, a
  `KeyboardInterrupt`, `create_databases` raising after the sampler started) keeps the
  process alive until the thread's loop ends, which it never does. A `time.sleep(30)` loop
  also delays a clean stop by up to 30 s.
- Nothing says what happens on a platform without `powershell` (`FileNotFoundError`), or
  when `mmap` with a tag name is called off Windows (`TypeError`: the parameter exists only
  on Windows).

**Why it matters.** The whole value of the step is that it costs nothing when it cannot read.
Today's brief leaves each of these to the coder; a coder who copies the probe gets the hang.

**Options.**
- (a) **Recommended.** State the rules in § 1.1 and § 3, as named constants: every PowerShell
  call has `timeout=POWERSHELL_TIMEOUT_SECONDS` (15 s before the run, 10 s in the sampler);
  `TimeoutExpired`, `OSError`, `ValueError` (bad JSON) each give `None` for that reading and
  the line's "could not be read" words; on `os.name != "nt"` no reading is attempted. The
  `Sampler` is `threading.Thread(daemon=True)`, its loop is `while not stop.wait(
  SAMPLE_SECONDS)` (wakes at once on `stop()`), and `run()` starts and stops it in a
  `try/finally` around `run_lanes` so an exception stops it too. `advise` and `run_summary`
  are pure and cannot fail; their callers in `run_lanes.py` catch `Exception`, print one line
  ("The machine check failed: <error>. The run keeps 6 lanes.") and go on. Add a unit test
  for each: a PowerShell stub that raises `TimeoutExpired`; a sampler stopped from the
  `finally` after `run_lanes` raises.
- (b) Keep the brief as is and rely on the code review. Rejected: a hang in the release's
  tests is found at the worst time.

## BR1-02 — major — "No Core Temp" is not an `OSError`: `mmap` creates an empty mapping

**Problem.** § 1.1 says the shared memory is readable "only while Core Temp runs", and § 3
says `read_core_temp()` returns `None` without Core Temp, as the probe's `except OSError`
implies. On Windows, `mmap.mmap(-1, size, tagname)` **creates** a page-file-backed mapping of
that name when none exists (verified above: a made-up name returned zeros). So with Core Temp
closed the reader gets 24 zero temperatures, `uiCoreCnt` 0 and an empty name, not an error.

Two consequences the brief must cover:
1. **Detection.** "Core Temp is not running" must be decided from the data: `uiCoreCnt × uiCPUCnt`
   is 0, or `sCPUName` is empty, or every temperature is 0 (Core Temp just started, no reading
   yet). Otherwise the line says "hottest core 0 °C" and the run keeps 6 lanes while hot — the
   silent opposite of the step's purpose.
2. **Holding the mapping.** While a Python process holds a mapping it created, a Core Temp
   started afterwards cannot create its own read-write section of that name (the name is
   taken by a read-only one), so Core Temp's shared memory stays broken until the sampler
   exits. And if Core Temp closes mid-run while the sampler holds the mapping, the data
   freezes at the last values (the section lives while any handle is open), so the peak reads
   as still hot. The reader must open the mapping, read 2686 bytes and close it on **every**
   sample, never keep it.

**Why it matters.** The no-Core-Temp line (§ 1.4), the "left out" rule (§ 1.1) and the
§ 5 run 2 all rest on a failure that does not happen.

**Options.**
- (a) **Recommended.** Rewrite the § 1.1 row and § 3's `read_core_temp()`: open per read,
  close in a `finally`; `parse_core_temp(buffer)` (pure, the function the § 3 test on a packed
  buffer calls) returns `None` when the count is 0, the name empty, or no temperature is
  above 0; the hottest core is the max over the first `uiCoreCnt × uiCPUCnt` entries, with
  the TjMax of its CPU (`uiTjMax[index // uiCoreCnt]`). The sampler counts the samples that
  had a temperature, and the after-run line says "hottest core 99 °C (10 of 12 samples)"
  when Core Temp closed during the run. Unit tests: the all-zero buffer → `None`; a buffer
  with `uiCoreCnt` 0 → `None`. KLA closes Core Temp for § 5 run 2 (the coder cannot).
- (b) Open with `OpenFileMappingW` through `ctypes` so a missing name really errors. Rejected:
  more code than the data check, and (a)'s per-read open covers the hold problem too.

---

## BR1-03 — minor — The composed line is not defined; two conditions give two lane sentences

**Problem.** § 1.2 says the line "names every matching condition (one sentence each)". Each
§ 1.4 sentence carries its own "so this run uses 3 lanes, not 6". Hot (93 °C → 3) together
with a weak charger (→ 3) prints the lane sentence twice; 96 °C (→ 2) with on-battery (→ 3)
prints two numbers that disagree; with `E2E_LANES=2` the line says "uses 3 lanes, not 6" and
then "keeps 2 lanes". "Running 6 lanes." is also wrong when the plan takes fewer (fewer groups
than lanes, S047) and when `E2E_LANES=1`. The standalone `.bat` prints "Running 6 lanes." when
nothing runs.

**Why it matters.** The coder has to invent the composition; the user approves wording he has
not seen.

**Options.**
- (a) **Recommended.** Define the line as three parts: (1) the readings, one clause each, in
  § 1.1's order ("on mains, hottest core 93 °C, processor at 97 % of its speed"); (2) one lane
  sentence: "So this run uses up to 3 lanes, not 6." / "E2E_LANES is set, so the run keeps 2
  lanes." / "Up to 6 lanes."; (3) the advice sentences of the matching conditions, each once.
  Give one composed example with two conditions. The `.bat` prints "A run now would use up to
  3 lanes, not 6." Keep the existing "N lanes; each lane's output in …" as the only line that
  states the actual count.
- (b) One line per condition, the lane sentence last. Rejected: longer, same information.

## BR1-04 — minor — Existing tests the change touches, and tests that would start real PowerShell

**Problem.** § 3 lists only new tests for `test_run_lanes.py`. The change touches these
existing tests:
- `TestLevels.test_an_inherited_level_does_not_filter_an_explicit_project` and
  `test_the_normal_level_still_sets_the_device_filter` call `main()` with `main_scratch` and
  `run` replaced, nothing else. With the check inside `main()` after the lock, each would run
  real PowerShell (2.7 s) and read Core Temp in a unit test: slow, machine-dependent, and on
  a machine without PowerShell it exercises BR1-01's failure path instead of the test's point.
- `TestRun` replaces `run_lanes.run_lanes` with a stub; the sampler around it would start a
  real thread and call PowerShell at its first sample (BR1-05 asks for a sample at start).
- `fake_run(args, wanted, timings_file)` in `TestLevels` fixes `run()`'s three-argument
  signature; a fourth positional argument for the machine file breaks it.

**Options.**
- (a) **Recommended.** State in § 3: `run_lanes.py` imports the check as names the tests can
  replace (`machine_check.before_run`, `machine_check.Sampler`, bound as module attributes of
  `run_lanes`); the two `TestLevels` tests and `TestRun._stub` replace them with stubs (one
  line each); `run()` keeps its signature and gets `machine_file=None` as a keyword, `None`
  meaning no sampler and no record, so the existing tests pass unchanged. Add the new tests
  the brief names on top.
- (b) Put the check and sampler calls in `main()` only, outside `run()`. Rejected: the
  sampler must wrap the lanes, which `run()` owns; the `TestLevels` tests still need a stub.

## BR1-05 — minor — The last-run record has no shelf life and a short run overwrites it

**Problem.** § 1.2's two last-run rules (drain on mains → 3; peak ≥ 98 °C → 4) read
`e2e-machine.json` whatever its age and whatever run wrote it:
- a 20 s targeted run of one spec (2 lanes, little load) writes "did not drain", clearing a
  weak-charger flag that a whole-suite run earned; with the first sample at 30 s it writes
  0 samples and still clears it;
- yesterday's hot-room or dock run cuts today's lanes on the barrel adapter in a cool room
  until a long run clears it; the advice "Connect the barrel adapter" then reads as wrong.

**Why it matters.** The drain rule is the only sign of the weak dock (design decision 5), so
the record's rules decide whether the step works.

**Options.**
- (a) **Recommended.** The record carries `written` (ISO time), `lanes`, `samples`, `peak_c`,
  `drained_on_mains` (`true` / `false` / `null`). The sampler takes its first sample at start,
  then every 30 s. A run with fewer than `SAMPLES_TO_JUDGE_DRAIN` (4, about 2 minutes) writes
  `null` for the drain and keeps the previous record's value. The § 1.2 last-run rules apply
  only to a record younger than `RECORD_SHELF_LIFE_HOURS` (24): a new day is a new room and a
  new plug. The constants join the list at the top of `machine_check.py`.
- (b) Only whole-suite runs (no spec file named) write the record. Rejected: a Normal run of
  three specs is load enough, and `run()` does not know whether a spec was named without
  more plumbing.

## BR1-06 — minor — The processor counter at idle is a weak sign; the rule may cut lanes on a healthy machine

**Problem.** `% Processor Performance` is the average frequency of all logical processors over
the interval, against the nominal clock. At idle most cores sit in low power states by design,
so the reading is low on a healthy machine: now, cool and on the barrel adapter, it read
78–95 % (brief: 95–110 %). The check reads it at idle (after the lock, before `--list`). In a
Windows power mode that parks cores harder, an idle reading under 70 % needs no fault, while
the same machine turbos fine once the lanes load it. Design decision 4's "under load it reads
low anyway" has it backwards: under load the counter reads high (turbo) unless the machine is
throttled, which is exactly the sign wanted.

**Why it matters.** A false "slowed" cuts the run to 3 lanes and tells KLA to change settings
that are fine; a rule that cries wolf is switched off.

**Options.**
- (a) Keep the pre-run read as information in the line, and cut lanes on it only under a
  lower bar (`SLOW_PROCESSOR_PERCENT` 50) until runs show where healthy idle sits.
- (b) **Recommended.** Read the counter **once in the sampler**, about 60 s into the run,
  when the lanes load the machine (one 2.7 s PowerShell call per run, not per sample), store
  it in the record, and apply "< 70 %" as a last-run rule like the peak (with BR1-05's shelf
  life). The pre-run line still prints the idle reading as information, cutting nothing.
  Design decision 4 is rewritten accordingly.
- (c) Make the rule need two signs: counter < 70 % and (on battery or hottest core ≥ 90 °C).
  Rejected: those two already cut lanes on their own.

## BR1-07 — minor — Record the battery's capacity too, so the drain has a second sign

**Problem.** Assumption 2 (§ 6) is that `Discharging` turns true on the dock under load; the
manual check that confirms it is "not important", so the step may be `Done` with the only
drain sign unverified. `BatteryStatus` returns `RemainingCapacity` (mWh; 53511 here) in the
same call at no cost. A battery that trickles down on a weak charger shows a falling capacity
even where the firmware keeps `Discharging` false (today `DischargeRate` is 0 and `Charging`
false at the same time, so the flags are not a clean state machine).

**Options.**
- (a) **Recommended.** The sampler keeps the first and last `RemainingCapacity`; the record
  stores both; "drained on mains" is `Discharging` seen on mains **or** the capacity fell by
  more than `DRAIN_CAPACITY_PERCENT` (2 %) while on mains the whole run. The after-run line
  adds the fall when it is the sign: "the battery fell from 53.5 to 51.2 Wh on mains power".
  The manual check stays, now telling which sign fired.
- (b) Keep `Discharging` only and wait for the manual check. Rejected: one more field for a
  rule that otherwise rests on an untested assumption.

## BR1-08 — minor — Belongs on the full track by two criteria

**Problem.** `README.md` § Tracks: light needs "follows an existing pattern: no new module
design" and "no … concurrency rules". `machine_check.py` is a new design (a shared-memory
reader, PowerShell output parsing, a sampler thread with an `Event`), not a copy of an
existing pattern. The two `major` findings switch the track anyway. A track question alone
never blocks; the user may weigh that this is test tooling with no app code, no data and no
permissions.

**Recommendation.** Switch to full as the rules say; the brief's extra sections can stay short
(the design is already in § 1 and § 4).

---

## Nits

- **BR1-09** (nit) § 3 vs § 1.3: `read_power()` is "one PowerShell call for `BatteryStatus` and
  the counter", but the sampler reads the battery only. Name two functions, `read_battery()`
  and `read_speed()`, each one call.
- **BR1-10** (nit) § 3: name the pure parser the test "on a packed byte buffer" calls
  (`parse_core_temp(buffer)` → hottest °C and its TjMax, or `None`), and that `read_core_temp()`
  is only the mmap around it (see BR1-02).
- **BR1-11** (nit) § 1.3: the record's fields are not listed. List them (BR1-05 (a) and
  BR1-07 (a) give the set) so the coder does not choose them.
- **BR1-12** (nit) § 1.3: the sampler wraps `run_lanes` only, so `E2E_LANES=1` and a one-group
  run (`single_stack`) write no record and print no after-run line. Say so, or wrap
  `single_stack` too (recommended: the same `try/finally`).
- **BR1-13** (nit) § 1.1: the PowerShell command line should be `powershell.exe -NoProfile
  -NonInteractive -Command …` (no prompt can block it) with `ConvertTo-Json -Compress`; say
  Windows PowerShell 5.1, not `pwsh`, is the one called.
- **BR1-14** (nit) § 1.1 table: `BatteryStatus` took 0.5 s here, not 0.1 s; the counter 2.7 s.
  Correct the numbers.
- **BR1-15** (nit) § 1.4 after-run line, scope B: "the battery drained on mains power: the
  charger is too weak. Connect the barrel adapter." Split at the colon: "The battery drained on
  mains power. The charger is too weak. Connect the barrel adapter."
- **BR1-16** (nit) § 1.6: "their whole-suite run" — the code reviewer never runs the whole
  suite (`code-reviewer.md`). Write "every e2e run they report".
- **BR1-17** (nit) § 5 run 2: the coder cannot close KLA's Core Temp. Mark run 2 as KLA's, and
  make the coder's version the zero-buffer unit test of BR1-02.
- **BR1-18** (nit) § 2: the standard term exists: ISO/IEC/IEEE 29119-3 names the *test
  environment readiness report* (what the environment was when the tests ran). Name it beside
  ISTQB; the owner is collecting the standards.
- **BR1-19** (nit) § 1.2 / § 3: the constants list should also carry the timeouts, the sample
  interval, the samples-to-judge count and the shelf life (BR1-01, BR1-05), each with its one
  line on why.

---

## Checked and found consistent

- `main_scratch()` (`run_lanes.py:298`) resolves the main working folder from the release's
  worktree, so `e2e-machine.json` beside `e2e-timings.json` there is right; `release-tests.bat`
  runs the worktree's `run-e2e-tests.bat --level=full`, which runs `run_lanes.py` as the brief
  assumes.
- The place in `main()`: after `one_run_at_a_time` and before `needs_webkit_server` / `run()`
  puts the check after the lock (another run's load does not spoil the reading), before the
  WebKit container and the `--list` run, and before the plan; `wanted` is a local the check can
  replace when `E2E_LANES` is unset; `run()` already takes `min(wanted, len(groups))`, so the
  "fewer groups" case needs nothing.
- `E2E_LANES` is read once at `main()`'s top (`run_lanes.py:549`), with the 1–20 check; "the
  caller's value wins" fits.
- `run-tooling-tests.bat` runs `pytest -q tooling\tests`, so `test_machine_check.py` is picked
  up with no script change; `machine_check.py` stdlib-only matches `run_lanes.py`.
- The Core Temp layout, the flags' meaning, the counter name and its cost, the `BatteryStatus`
  fields and the `EnergySaverState` value (table above).
- `.claude/agents/coder.md` § Browser tests and `code-reviewer.md` have the e2e paragraphs
  where § 1.6's line fits; `.claude/CLAUDE.md` § Browser tests is the paragraph to extend.
- No app code, migration, RBAC or data; Plan.MD, the maintenance docs and the schema are not
  due.
- The manual check names who (KLA), the setup (dock alone, barrel adapter unplugged) and the
  level (Normal, whole suite); nothing on it could be a browser test.
