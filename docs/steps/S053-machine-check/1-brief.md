```
Step: S053 — Machine check before browser runs
Doc: brief
Author: Planner (Opus)
Date: 25-10-2026
Track: full
Status: Parked 25-10-2026 by KLA ("I don't see much value in this S053. Let's defer it"; brief kept at gate A after review r2, with the advice)
```

# S053 — Machine check before browser runs

**The need (KLA, 25-10-2026).** Browser runs were slow and uneven, and S045's two open flakes
were time-outs waiting for the browser to draw. On 25-10-2026 three causes were found on KLA's
laptop (Dell Precision 7680, Intel Core i9-13950HX): energy saver was on, the room's air
conditioning was off (Core Temp showed cores at 100 °C), and the Thunderbolt dock powers the
laptop over USB-C with too little power ("full performance reaches only when barrel adapter is
connected"; Windows says "Slow charging" on the dock alone). KLA: "create a tooling to lookup
battery power, power setting and pass it on to the coder, to act in a balanced way."

**How the data is read** comes from the advisor's research, `0-advice-power-readings.md` in this
folder (Fable, 25-10-2026, every reading run on this laptop without admin rights).

**Track: full** (BR1-08: a new module design with a sampler thread). Test tooling only: no app
code, no migration, no RBAC, no data; about 8 files.

## 1. What will be built

### 1.1 What the check reads (verified on this laptop, no admin rights)

Every reading uses a documented Windows API through Python's `ctypes` (stdlib). No reading
starts a process, so none can hang on a wedged service (BR1-01).

| Reading | Source | Seen on 25-10-2026 (advice §) |
|---|---|---|
| On mains, battery present, discharging, charge rate in mW, remaining capacity in mWh | `CallNtPowerInformation(SystemBatteryState)` (`powrprof`), struct `SYSTEM_BATTERY_STATE` | `AcOnLine 1`, `Discharging 0`, `Rate 0`, idle and under 16 s of all-core load on the barrel adapter; 0.03 ms (§ 2.1) |
| Energy saver on | `GetSystemPowerStatus` (`kernel32`), `SystemStatusFlag` (documented: "battery saver is on") | `0` today, energy saver off. Whether Windows 11's energy saver sets it while plugged in is checked by KLA (§ 5 manual checks) |
| Processor speed and how busy it is | PDH through `ctypes`: `PdhAddEnglishCounterW` for `\Processor Information(_Total)\% Processor Performance` and `% Processor Utility`, two samples `SPEED_GAP_SECONDS` (1 s) apart | 60–125 % at idle (seen 88–99 % and 119–124 % at 5–7 % busy: it says nothing at idle); under all-core load 120–125 % (turbo). English counter names on any Windows language (§ 2.3; BR2-15) |
| Hottest core and its limit (TjMax) | Core Temp's shared memory `CoreTempMappingObject`, read with `mmap` | 24 cores, TjMax 100; 64 → 99.5 °C within 16 s of load (§ 2.4). Readable only while Core Temp runs (below) |
| Windows' "Slow charging" | its effect: Windows' own *Inadequate* supply is defined as "plugged in but the charge rate is negative", which `Rate < 0` with `AcOnLine 1` gives | the dock's shortfall shows under load (§ 2.1); KLA's dock check confirms it (§ 5) |

**Not used:** the power-mode overlay (`PowerGetEffectiveOverlayScheme` is undocumented,
CLAUDE-COMMON: no undocumented or deprecated APIs), the `EnergySaverState` register value (its
values are undocumented), WinRT `PowerManager` (adds nothing beyond the two calls above today;
PowerShell 7 cannot load it), WMI performance classes (the first query took 110 s), Dell's WMI
(admin only). Evidence in the advice, § 2.5–2.9.

**Core Temp's empty read (BR1-02).** On Windows, `mmap.mmap(-1, size, "CoreTempMappingObject")`
does not fail when Core Temp is not running: it creates an empty mapping and returns zeros. So:
- the pure `parse_core_temp(buffer)` returns `None` when `uiCoreCnt × uiCPUCnt` is 0, the CPU
  name is empty, or no raw `fTemp` value is above 0 (tested before the delta conversion: in delta
  mode a zero converts to TjMax, so a just-started Core Temp would read 100 °C on every core;
  BR2-07); otherwise the hottest core in °C over the first
  `uiCoreCnt × uiCPUCnt` entries, with the TjMax of its CPU (`uiTjMax[index // uiCoreCnt]`),
  converting Fahrenheit (`ucFahrenheit`) and delta-to-TjMax (`ucDeltaToTjMax`, temperature =
  TjMax − value) to °C;
- `read_core_temp()` opens the mapping, reads 2686 bytes and closes it in a `finally` on every
  read, never keeping it. A kept mapping would stop a later-started Core Temp from making its
  own, and would freeze the values if Core Temp closed mid-run.

**Failures** (BR1-01). Each reader returns `None` on `OSError`, `AttributeError`, `ValueError`
or a non-zero status (no battery: `BatteryPresent 0`; not Windows: `ctypes.WinDLL` is missing;
`os.name != "nt"`: no reader is called at all). The `WinDLL` handles are made inside the readers,
not at import, so the pure functions import and test on any system. Every call sets `argtypes`
and `restype` (`PdhAddEnglishCounterW`'s path is `LPCWSTR` and its user data `DWORD_PTR`;
`CallNtPowerInformation` returns `NTSTATUS`), and a PDH value whose `CStatus` is not 0 or 1
(valid, new data) is a failed read (BR2-16). A `None` reading is left out
of the rules and named in the line ("… could not be read").

### 1.2 Before a run: the lane count

`run_lanes.py` runs the check once in `main()`, after taking the lock and before the WebKit
container, the `--list` run and the plan. The pure `advise(readings, record, default_lanes, now)` (BR2-08)
returns the lane count: the smallest any matching rule gives, or the default.

| Rule | Reads | Lanes (of 6) |
|---|---|---|
| hottest core now ≥ `HOT_C` (95 °C) | Core Temp | 2 |
| hottest core now ≥ `WARM_C` (90 °C) | Core Temp | 3 |
| on battery now | battery state | 3 |
| energy saver on now | `SystemStatusFlag` | 3 |
| the last run drained the battery on mains (§ 1.3) | the record | 3 |
| the last run's processor ran below `SLOW_BUSY_PERCENT` (90 %) of its speed while busy (§ 1.3) | the record | 3 |
| none | — | the default (6) |

- **The last-run rules apply only to a finding judged less than `RECORD_SHELF_LIFE_HOURS` (24 h)
  ago** (its `drain_judged_at` or `speed_judged_at`, § 1.3) and with a value (`null` = not
  judged): a new day is a new room and a new plug (BR1-05, BR2-02).
- **The processor speed before the run is information only** (BR1-06): at idle, cores sit in
  low-power states by design, so a low idle reading means nothing. Under load the speed reads
  high (turbo) unless the machine is held back, so the sampler judges it (§ 1.3).
- **No rule on the last run's peak temperature** (advice § 2.4): this laptop reaches about 100 °C
  under the suite's load in any room, so such a rule would fire after every run. Heat that
  matters shows as a slow busy processor, which the busy-speed rule catches.
- **`E2E_LANES` set by the caller wins.** The check still prints its line, with "E2E_LANES is
  set, so the run keeps <n> lanes." `E2E_LANES=1` and a run with fewer groups than lanes are
  unchanged (the plan takes the smaller number, S047).
- **The check can never stop a run.** `run_lanes.py` calls it inside `try/except Exception`; on
  an error it prints "The machine check failed: <error>. The run keeps <n> lanes." and goes on.

### 1.3 During a run: the sampler and the record

`machine_check.Sampler` is a `threading.Thread(daemon=True)`. Its loop is
`while not stop.wait(SAMPLE_SECONDS)` (30 s), so `stop()` wakes it at once; `stop()` then
`join(SPEED_GAP_SECONDS + 1)`s, so a sample inside its 1 s PDH gap finishes before the summary
reads the samples (BR2-14). It takes its first
sample at start, then one every 30 s. Each sample reads:
- the hottest core (Core Temp; `None` if not running);
- the battery state (on mains, discharging, `Rate`, `RemainingCapacity`);
- the processor speed and utility (PDH, 1 s gap inside the thread).

`run()` starts the sampler and stops it in a `try/finally` around the lanes, so a failed or
interrupted run stops it too; the single-stack path (`E2E_LANES=1`, one group) is wrapped the
same way (BR1-12).

After the lanes, the pure `run_summary(samples, now)` gives the record and the after-run line. The
summary, the merge and the record write sit in the same `try/except Exception` as the check
(§ 1.2): on an error they print "The machine record could not be written: <error>." and the
run's exit code is unchanged (BR2-05).
The record, `e2e-machine.json` in the main working folder's `scratch/` (`main_scratch()`, S047,
so the release's worktree and the working folder share it), holds (BR1-11):

| Field | Meaning |
|---|---|
| `written` | ISO time, IST |
| `lanes` | the lanes the run used |
| `samples` | the number of samples |
| `temp_samples` | the samples that had a Core Temp reading |
| `peak_c` | the hottest core seen, or `null` |
| `drained_on_mains` | judged only over the samples with a battery reading, and only when every one of them was on mains and there are at least `SAMPLES_TO_JUDGE` (4, about 2 min); otherwise `null` (a run on battery, or a short run, judges nothing; BR2-03). Then `true` when any sample had `Discharging` or `Rate < 0`, or `RemainingCapacity` fell by more than `DRAIN_CAPACITY_PERCENT` (2 % of `MaxCapacity`) from the first to the last sample (BR1-07); else `false` |
| `drain_judged_at` | when `drained_on_mains` was last judged (ISO time); carried with it (BR2-02) |
| `worst_rate_mw` | the most negative `Rate` on mains, or `null` |
| `capacity_first_mwh`, `capacity_last_mwh` | the battery's remaining capacity at the first and last sample |
| `busy_speed_pct` | the lowest processor speed among samples with utility ≥ `BUSY_UTILITY_PERCENT` (50 %), or `null` when fewer than `SAMPLES_TO_JUDGE` samples were busy (lowest or mean: § 6 question 1, BR2-09) |
| `speed_judged_at` | when `busy_speed_pct` was last judged; carried with it (BR2-02) |

**The merge** (`merge_record`, BR2-10): the judged fields — `drained_on_mains`, `worst_rate_mw`,
the two capacities with `drain_judged_at`, and `busy_speed_pct` with `speed_judged_at` — keep
the previous record's values and judged-at time when this run gives `null`, so a short run never
clears a long run's finding (BR1-05). `written`, `lanes`, `samples`, `temp_samples` and `peak_c`
are always this run's. **The shelf life reads the judged-at times, not `written`** (BR2-02): a
finding expires 24 h after it was judged, however many short runs follow.

### 1.4 The lines (CLAUDE-COMMON scope B)

**Before the run** (BR1-03), one line in three parts:
1. the readings, one clause each: "Machine check: on mains, hottest core 72 °C, processor at 90 %
   of its speed, 5 % busy."
2. one lane sentence: "Up to 6 lanes." / "So this run uses up to 3 lanes, not 6." / "E2E_LANES is
   set, so the run keeps 2 lanes."
3. one advice sentence for each matching rule, in § 1.2's order, each once:
   - hot (both temperature rules, 90 °C and 95 °C, print this one sentence; BR2-12): "It is too
     hot for a full run. Cool the laptop. Turn on the air conditioning or put it on a stand."
   - on battery: "The laptop is on battery. Connect the charger."
   - energy saver: "Energy saver is on. Turn it off for test runs."
   - weak charger: "In the last run the battery drained on mains power, so the charger is too
     weak for this load. Connect the barrel adapter."
   - slow: "In the last run the processor ran at 64 % of its speed while busy. Turn off energy
     saver. Set Power mode to Best performance. Cool the laptop."
   - no Core Temp: "Core Temp is not running, so the temperature is not checked. Start Core Temp
     to include it."
   - a reading failed: "The battery could not be read." (and so on per reading).

Example with two rules: "Machine check: on mains, hottest core 93 °C, processor at 88 % of its
speed, 6 % busy. So this run uses up to 3 lanes, not 6. It is too hot for a full run. Cool the
laptop. Turn on the air conditioning or put it on a stand. In the last run the battery drained on mains power,
so the charger is too weak for this load. Connect the barrel adapter."

The existing "N lanes; each lane's output in …" line stays the only one that states the count the
run actually uses ("up to", because the plan may take fewer).

**After the run**, after "All lanes done in N s": "Machine during the run: hottest core 99 °C
(12 of 12 samples); the processor ran at 118 % of its speed while busy; the battery did not
drain on mains." Or, when it drained by capacity: "… The battery drained on mains power (it fell
from 53.5 to 51.2 Wh). The charger is too weak. Connect the barrel adapter." By the charge rate
alone (BR2-12): "… The battery drained on mains power (it drew up to 35 W from the battery). The
charger is too weak. Connect the barrel adapter." (from `worst_rate_mw`; BR1-15: no colon splits.)

### 1.5 Standalone

`tooling/machine-check.bat` (`uv run --no-project python "%~dp0e2e\machine_check.py"`, as the
other `.bat`s call their scripts; BR2-13) prints the § 1.4 before-run line with "A run now would
use up to 3 lanes, not 6." (or "A run now would use up to 6 lanes." when no rule matches) as its
lane sentence, and the last record's after-run line if its findings are within their shelf life.
Exit 0 always: it advises. `run_lanes` owns the record's path (`main_scratch()`);
`machine_check.main()` imports `run_lanes` inside the function, not at the top, so the two modules
do not import each other at load time (BR2-04).

### 1.6 The agents

The coder and the code reviewer copy the runner's "Machine check" and "Machine during the run"
lines of every e2e run they report into the impl report or review, beside the counts and the
time (BR1-16), so a slow run can be explained later. One line each in `.claude/agents/coder.md`
and `.claude/agents/code-reviewer.md`.

### Out of scope

- Changing the lane count during a run (lanes cannot be added or removed once started).
- Admin-only readings (Dell WMI, the charger's watts) and installing Dell Command | Monitor.
- Undocumented readings: the power-mode overlay, the `EnergySaverState` value.
- WinRT `PowerManager` (only if KLA's energy-saver check shows `SystemStatusFlag` stays 0 while
  energy saver is on; then an amendment).
- Other temperature tools (HWiNFO, LibreHardwareMonitor): only Core Temp, which KLA runs.
- Turning Windows settings on or off, and the hidden cooling-mode setting the advice found
  (Passive, § 2.13): the check advises; KLA acts.

## 2. Standards and practice

- **Test environment readiness report** (ISO/IEC/IEEE 29119-3, the test documentation part;
  BR1-18): a record of the environment the tests ran in, so a slow or failed run can be told apart
  from a fault in the code. The before-run and after-run lines and `e2e-machine.json` are this
  record for each run.
- **Intel's TjMax** (100 °C here) is where the processor slows itself to protect itself; 90–95 °C
  before a run leaves no margin for the load to come.
- **Documented APIs only** (CLAUDE-COMMON: no deprecated APIs; dependency health, stdlib
  preferred): `kernel32`, `powrprof` and `pdh` through `ctypes`; no `pywin32`, `wmi` or `winrt`
  package.

## 3. Where

| File | Change |
|---|---|
| `tooling/e2e/machine_check.py` | new, stdlib only. Constants at the top, each with one line on why: `HOT_C`, `WARM_C`, `SLOW_BUSY_PERCENT`, `BUSY_UTILITY_PERCENT`, `DRAIN_CAPACITY_PERCENT`, `SAMPLES_TO_JUDGE`, `SAMPLE_SECONDS`, `SPEED_GAP_SECONDS`, `RECORD_SHELF_LIFE_HOURS`, `REDUCED_LANES` (3), `HOT_LANES` (2), `CORE_TEMP_SIZE` (2686) (BR1-19). Readers: `read_battery()`, `read_energy_saver()`, `read_speed()`, `read_core_temp()` (each one call, `None` on failure; BR1-09). Pure: `parse_core_temp(buffer)`, `advise(…)`, `run_summary(…)`, `merge_record(previous, new, now_time)`, `before_line(…)`, `after_line(…)`. Shell: `before_run(default_lanes, record_path)` → `(lanes, line)`, class `Sampler`, `main()` for the `.bat`. The advice's § 7 code is the starting point for the readers. |
| `tooling/tests/test_machine_check.py` | new: `advise` for every row of § 1.2, combinations (smallest wins), missing readings, an old record, a `null` field; `run_summary` and `merge_record` (drain by flag, by `Rate`, by capacity; too few samples → `null`; busy speed only from busy samples); `parse_core_temp` on packed buffers (°C, Fahrenheit, delta mode, two CPUs, the all-zero buffer → `None`, `uiCoreCnt` 0 → `None`); the line builders (one lane sentence, each advice once, the two-rule example of § 1.4); the readers with their `ctypes` calls replaced (`monkeypatch` on module functions), including a failing call → `None`; the `Sampler` stopped at once by `stop()`, and stopped from a `finally` when the wrapped call raises |
| `tooling/e2e/run_lanes.py` | `main()`: `before_run` after the lock (in `try/except Exception`), its lanes replace `wanted` only when `E2E_LANES` is unset; `run()` gains `machine_file=None` (keyword; `None` = no sampler and no record) and wraps the lanes and the single-stack path in the sampler's `try/finally`; the after-run line; the record written through `merge_record`. `machine_check.before_run` and `machine_check.Sampler` are bound as module attributes of `run_lanes`, so tests replace them (BR1-04) |
| `tooling/tests/test_run_lanes.py` | `TestLevels.test_an_inherited_level_does_not_filter_an_explicit_project` and `test_the_normal_level_still_sets_the_device_filter` replace `before_run` (one line each), so no unit test reads the real machine; their fakes of `run()` (`fake_run(args, wanted, timings_file)` and the `lambda *a`) gain `machine_file=None`, because `main()` passes it (BR2-01). `TestRun` needs no stub: `before_run` is in `main()`, and `run()` with `machine_file=None` starts no sampler. New: the check's lanes reach the plan; `E2E_LANES` wins; a check that raises keeps the default and prints its line; the sampler stops when `run_lanes` raises |
| `tooling/machine-check.bat` | new |
| `tooling/run-e2e-tests.bat` | header comment: the machine check and its lines |

### Docs (housekeeping, by the coder)

- `.claude/CLAUDE.md` § Browser tests: the machine check, `e2e-machine.json`, `E2E_LANES` wins,
  Core Temp optional; § Dev commands: `tooling/machine-check.bat`.
- `.claude/agents/coder.md`, `.claude/agents/code-reviewer.md`: § 1.6.
- No schema, Plan.MD or domain doc is due.

## 4. Design decisions

1. **The runner adapts by itself; agents only copy the lines** (KLA's choice in the queue,
   25-10-2026). Rejected: warn only, which a coder in the middle of a step rarely acts on.
2. **Effects, not causes, for the charger** (§ 1.1): a negative charge rate or a falling capacity
   on mains catches the weak dock, as Windows' own *Inadequate* does. Rejected: the charger's watts
   (admin only).
3. **`ctypes` on documented Win32 APIs, no PowerShell** (advice § 3–4). Rejected: one PowerShell
   call per read (2.7 s for the counter, a wedged WMI service can hang it, PowerShell 7 cannot load
   WinRT), and the `pywin32` / `wmi` / `winrt` packages (a dependency for a few numbers).
4. **The processor speed is judged under load, in the sampler**, and only as information before
   the run (BR1-06, advice § 2.3).
5. **The last run's record decides the drain and busy-speed rules**, because both show only under
   load, which the check before the run does not see; the record has a shelf life and keeps a
   judged value against a short run's `null` (BR1-05).
6. **No peak-temperature rule** (advice § 2.4): it would fire after every run on this laptop.
7. **Open Core Temp's mapping per read and judge "not running" from the data** (BR1-02). Rejected:
   `OpenFileMappingW` through `ctypes` so a missing name errors: more code, and the per-read open
   is needed anyway against the held-mapping problems.

## 5. Tests and acceptance

- **Unit** (`tooling/run-tooling-tests.bat`): the tests of § 3, red first for `advise`,
  `parse_core_temp` and `run_summary`.
- **Runs the coder makes and reports, with the lines printed:**
  1. `tooling/machine-check.bat`: the line with the hottest core, the battery and the speed.
  2. A targeted run (`tooling/run-e2e-tests.bat e2e/labels.spec.js`): the before-run line, the
     after-run line, `e2e-machine.json` with `drained_on_mains: null` (fewer than 4 samples).
  3. `set E2E_LANES=2`, then the same run: "E2E_LANES is set, so the run keeps 2 lanes."
  4. The whole suite at Normal once: the after-run line with a busy speed and a judged drain.
- **Accept when** the four suites are green and the four runs print what § 1.4 says.

### Manual checks (KLA's laptop; rows in `docs/steps/device-checks.md` with account "—", network "—", where "KLA's laptop, the dev working folder"; BR2-17)

Both use the probes in `scratch/s053-probes/` (the advice § 6 gives the steps) or the new
`tooling/machine-check.bat`:
1. **Core Temp closed** (BR1-17): close Core Temp, run `tooling/machine-check.bat`; the line says
   "Core Temp is not running …". The coder's version of this check is the all-zero-buffer unit
   test.
2. **important** (BR2-06, KLA decides at gate A) — **The dock alone**: unplug the barrel adapter, keep the Thunderbolt dock, run the whole suite
   at Normal once; the after-run line says the battery drained on mains, and the next
   `machine-check.bat` names the weak charger. If it does not, KLA tells the planner (the drain
   needs another sign).
3. **Energy saver while plugged in**: turn energy saver on, run `tooling/machine-check.bat`; the
   line says "Energy saver is on." If it does not (`SystemStatusFlag` stays 0), the WinRT reading
   comes as an amendment (advice § 2.5). Turn energy saver off again.

## 6. Open questions and assumptions

1. **The thresholds** (§ 1.2, § 1.3): 95 °C → 2 lanes, 90 °C → 3, battery, energy saver, a weak
   charger or a slow busy processor → 3; busy = utility ≥ 50 %; slow = below 90 %; a drain = a
   negative rate or a capacity fall above 2 % of the battery's full capacity; judged from 4
   samples; a finding lives 24 h after it was judged; the busy speed is the **lowest** busy sample
   (the mean is steadier against one odd sample; BR2-09). Proposed as first values, tuned from the
   records.
2. **Assumption**: on the dock under the suite's load, `Rate` goes negative or the capacity falls
   (manual check 2).
3. **Assumption**: Windows 11's energy saver sets `SystemStatusFlag` while plugged in (manual
   check 3).

## 7. Amendments

None.

## Review log

### U1 — user answers, 25-10-2026 (before drafting)

- Adapt automatically (the queue row, not warn-only).
- Read the temperature from Core Temp (KLA runs it).
- The dock's USB-C power is too low; full speed only on the barrel adapter; Windows says "Slow
  charging" on the dock alone.

### U2 — advice, 25-10-2026

KLA asked Fable how the power data can be read reliably. Its report,
`0-advice-power-readings.md`, replaced the PowerShell readings by `ctypes` on documented APIs,
made energy saver and Windows' *Inadequate* supply readable, moved the speed rule into the
sampler and dropped the peak rule (§ 1.1–1.3, decisions 3–6). Its probe scripts are copied to
`scratch/s053-probes/`.

### Round 1 — `2-brief-review-r1.md` (Fable), answered 25-10-2026

| Finding | Answer |
|---|---|
| BR1-01 major: nothing stops a hang | Accepted: no reader starts a process (ctypes, U2); `None` on every failure, no reader off Windows; the sampler a daemon thread on `stop.wait`, stopped in a `try/finally`; the check in `try/except Exception` with its line; unit tests for both (§ 1.1, § 1.2, § 1.3, § 3) |
| BR1-02 major: no Core Temp gives zeros, not an error | Accepted, (a): `parse_core_temp` decides "not running" from the data; the mapping opened and closed per read; samples with a temperature counted; tests on the zero buffer (§ 1.1, § 1.3, § 3, decision 7) |
| BR1-03 minor: the composed line | Accepted, (a): three parts, one lane sentence, each advice once, "up to", a two-rule example, the `.bat`'s own lane sentence (§ 1.4, § 1.5) |
| BR1-04 minor: existing tests | Accepted, (a): `before_run` and `Sampler` bound as replaceable module attributes; `machine_file=None` keyword; the named tests stub them (§ 3) |
| BR1-05 minor: the record's shelf life | Accepted, (a): first sample at start, 4 samples to judge, `null` keeps the previous value, 24 h shelf life, fields listed (§ 1.2, § 1.3) |
| BR1-06 minor: the idle speed is a weak sign | Accepted, (b) as the advice refines it: speed read in every sample, judged only while busy, a last-run rule at 90 %; information only before the run; decision 4 rewritten (§ 1.2, § 1.3) |
| BR1-07 minor: a second drain sign | Accepted, (a): `RemainingCapacity` from the same call, a fall above 2 % on mains (§ 1.3) |
| BR1-08 minor: full track | Accepted: switched to full |
| BR1-09…BR1-19 nits | Accepted, all: two readers named (§ 3); `parse_core_temp` named (§ 1.1, § 3); the record's fields (§ 1.3); the single-stack path wrapped (§ 1.3); BR1-13 and BR1-14 are moot (no PowerShell, ctypes timings from the advice); the after-run line without colon splits (§ 1.4); "every e2e run they report" (§ 1.6); the Core Temp check is KLA's and a unit test for the coder (§ 5); ISO/IEC/IEEE 29119-3 (§ 2); the constants list (§ 3) |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 25-10-2026

| Finding | Answer |
|---|---|
| BR2-01 minor: the `run()` fakes break on the keyword | Accepted: the two fakes gain `machine_file=None`; `TestRun` needs no stub (§ 3) |
| BR2-02 minor: a carried value never expires | Accepted: `drain_judged_at` / `speed_judged_at` carried with their values; the shelf life reads them (§ 1.2, § 1.3) |
| BR2-03 minor: a battery run clears the dock finding | Accepted: judged only when every battery sample was on mains, else `null`; 2 % of `MaxCapacity` (§ 1.3) |
| BR2-04 minor: a circular import | Accepted: `run_lanes` owns the path; `machine_check.main()` imports it inside the function (§ 1.5) |
| BR2-05 minor: the summary outside the guard | Accepted: the same `try/except`, its line, the exit code unchanged (§ 1.3) |
| BR2-06 minor: the dock check is important | Marked **important**, pending KLA's choice at gate A (§ 5) |
| BR2-07…BR2-17 nits | Accepted, all: raw `fTemp` tested before the delta conversion (§ 1.1); `advise(readings, record, default_lanes, now)` (§ 1.2); lowest or mean into § 6 Q1; the merged fields named (§ 1.3); the four scope-B sentences (§ 1.4); the warm rule's sentence and the charge-rate line (§ 1.4); the `.bat`'s no-rule sentence and `%~dp0` (§ 1.5); `stop()` joins (§ 1.3); the idle spread (§ 1.1); `argtypes`/`restype` and `CStatus` (§ 1.1); the device rows' columns (§ 5) |
