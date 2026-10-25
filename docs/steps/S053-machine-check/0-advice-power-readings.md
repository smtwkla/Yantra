```
Step: S053 — Machine check before browser runs
Doc: advice (research), power and thermal readings without admin rights
Author: Researcher (Fable)
Date: 25-10-2026
Machine: Dell Precision 7680, i9-13950HX, Windows 11 Pro 10.0.26100, barrel adapter connected, no admin
```

# How the runner can read power and thermal state without admin rights

**The point.** Every reading the brief needs is available from Python's stdlib through `ctypes`, with
no PowerShell and no dependency, in under 2 ms each, except the processor speed (about 1 s, the
sampling gap). The brief's two "not readable" rows are readable: Windows' *Inadequate* power supply
and *energy saver on* both come from documented APIs. One reading in the brief must go: a pre-run
processor-speed rule, because the counter reads 60–99 % on an idle machine and 120 % under load, so
a single idle sample says nothing about throttling. Two things need KLA at the keyboard (§ 6): the
dock alone, and energy saver turned on while plugged in.

Every candidate below was run on this laptop today. Scripts: the scratchpad probes
`probe_ctypes.py`, `probe_pdh_winrt.py`, `probe_load.py`, `probe_winrt.ps1`, `probe_wmi.ps1`
(temporary; § 7 carries the code the coder needs).

## 1. Summary table

| # | Reading | Source | Read now | Admin | Time | Status | Use in S053 |
|---|---|---|---|---|---|---|---|
| 1 | On mains, battery draining, charge rate in mW | `CallNtPowerInformation(SystemBatteryState)` → `SYSTEM_BATTERY_STATE` (ctypes, `powrprof.dll`) | `AcOnLine=1 Charging=0 Discharging=0 Rate=0 mW` | no | 0.03 ms | documented, current | **yes, primary** |
| 2 | On mains, energy saver on | `GetSystemPowerStatus` → `SYSTEM_POWER_STATUS` (ctypes, `kernel32`) | `ACLineStatus=1 BatteryFlag=1 SystemStatusFlag=0` | no | 0.002 ms | documented, current | **yes** (energy saver) |
| 3 | Processor speed against rated speed | PDH `PdhAddEnglishCounterW` on `\Processor Information(_Total)\% Processor Performance` (ctypes, `pdh.dll`), two samples 1 s apart | idle 88–99 %, all-core load 120–125 %, after 99 % | no | 1.0 s (1.35 s first call) | documented, current, language-independent | **yes**, in the sampler, not as a pre-run rule |
| 4 | Hottest core, TjMax | Core Temp shared memory `CoreTempMappingObject` (`mmap`) | 58–70 °C idle; **99.5 °C after 16 s of all-core load** | no | < 1 ms | Core Temp's SDK layout; only while Core Temp runs | **yes** (unchanged) |
| 5 | Power supply Inadequate / Adequate, energy saver Disabled / Off / On | WinRT `Windows.System.Power.PowerManager` (ctypes activation factory, or `powershell.exe` 5.1) | `PowerSupplyStatus=Adequate EnergySaverStatus=Disabled BatteryStatus=Idle 100 %` | no | 10 ms (ctypes), 300 ms (powershell.exe) | documented, current; **not loadable from PowerShell 7** | optional, after KLA's checks (§ 6) |
| 6 | Battery report, charge rate in mW | WinRT `Windows.Devices.Power.Battery.AggregateBattery.GetReport()` | `Status=Idle ChargeRate=0 Full=53511 Design=83010 mWh` | no | 70 ms + 300 ms process | documented; same numbers as #1 | no (#1 gives the same) |
| 7 | Power mode slider (Best power efficiency / Balanced / Best performance) | `PowerGetEffectiveOverlayScheme` (ctypes, `powrprof.dll`) | `00000000-…` = Balanced | no | 0.5 ms | **undocumented export**; GUIDs from community sources | no (§ 2.7) |
| 8 | Processor clock, throttle limit | `CallNtPowerInformation(ProcessorInformation)` → `PROCESSOR_POWER_INFORMATION` | `MaxMhz=2200 CurrentMhz 1466–2200 MhzLimit=2200`, unchanged under load | no | 0.05 ms | documented | no (§ 2.8: saturates at the 2200 MHz base clock, never shows turbo or a cap) |
| 9 | Same counters through WMI | `Win32_PerfFormattedData_Counters_ProcessorInformation` | 86 %, then 127 % | no | **110 s on the first call**, 0.3 s after | documented | no |
| 10 | Thermal zone counters | `\Thermal Zone Information(*)\Temperature`, `% Passive Limit`, `Throttle Reasons`; `MSAcpi_ThermalZoneTemperature` | no instances (PDH `PDH_NO_DATA`, Get-Counter `800007d1`); WMI "Not supported" | — | — | — | no |
| 11 | Battery through WMI | `root/wmi BatteryStatus` (the brief's row), `Win32_Battery`, `Win32_PortableBattery`, `BatteryFullChargedCapacity`, `BatteryCycleCount` | `PowerOnline=True Discharging=False ChargeRate=0`; `Win32_Battery.BatteryStatus=2` (AC); cycle count 125 | no | 70–180 ms + process start | documented | no (#1 replaces it, no subprocess, no −2147483648 sentinel) |
| 12 | The charger's watts, Dell's view | `root/dell` (Access denied), `root/dcim/sysman` (no device classes), `EsifDeviceInformation` Intel DPTF (Access denied), `Win32_PowerSupply` / `Win32_PowerMeter` (static, empty), `BatteryTemperature` (empty), USB-C ETW log (failures only) | nothing usable | admin for the first three | — | — | no (unchanged) |
| 13 | System cooling mode | `CallNtPowerInformation(SystemPowerInformation).CoolingMode` | **1 = PO_TZ_PASSIVE** | no | 0.01 ms | documented | information only (§ 2.13) |
| 14 | Energy saver register value | `HKLM\…\Power\EnergySaverState` | 2 (REG_DWORD) | no | 0.1 ms | undocumented | fallback only if § 6 check 2 fails |

## 2. Each candidate

### 2.1 `SYSTEM_BATTERY_STATE` (candidate 2 of the question, and the answer to "the charger is too weak")

- Fact: `CallNtPowerInformation(SystemBatteryState=5)` fills `AcOnLine`, `BatteryPresent`, `Charging`,
  `Discharging`, `MaxCapacity`, `RemainingCapacity`, `Rate` (signed, mW; negative while discharging),
  `EstimatedTime`. Documented on learn.microsoft.com (`powerbase.h`, `winnt.h`), Windows XP onwards,
  not deprecated. Read in 0.03 ms (100 reads in 0.7 ms).
- Fact: on the barrel adapter, idle and during 16 s of all-core load, it read
  `AcOnLine=1 Discharging=0 Rate=0`: the adapter holds the battery idle under load. This is the
  baseline for KLA's dock check (§ 6).
- Fact: Microsoft defines WinRT `PowerSupplyStatus.Inadequate` as "the power supply is present, but
  the charge rate is negative. For example, the device is plugged in, but it's losing charge." So
  *Inadequate* ≡ `AcOnLine=1 and Rate < 0` (or `Discharging=1`). One ctypes call gives the brief's
  "battery drains on mains" and Windows' own *Inadequate* at once.
- Assumption: Windows' "Slow charging" text is not the same flag. It appears while the battery still
  charges (rate positive but low) and comes from the charger's reported wattage. At 100 % charge and
  idle the dock may read `Adequate` and `Rate=0`; only load makes the drain visible. § 6 check 1
  decides.
- Recommendation: use #1 as the primary power reading, before the run and in the sampler. Record
  `Rate` in `e2e-machine.json` (the most negative value seen): "the battery lost 35 W on mains" is a
  better line than "drained".

### 2.2 `GetSystemPowerStatus` (candidate 2)

- Fact: `SYSTEM_POWER_STATUS.SystemStatusFlag` is documented as "the status of battery saver: 0 off,
  1 on" (introduced in Windows 10, `GUID_POWER_SAVING_STATUS`). `ACLineStatus` 0/1/255. Read in
  2 µs. Documented, not deprecated.
- Fact: read `SystemStatusFlag=0` today, on mains, with energy saver off in Settings.
- Assumption: Windows 11's "Energy saver" is the renamed battery saver (the WinRT enum page still
  says "battery saver"). Whether "Always use energy saver" while plugged in sets this flag is not
  documented and was not tested (turning it on is a settings change, left to KLA, § 6 check 2).
- Recommendation: read it (it is free) and show "energy saver is on" when it is 1. Keep the
  processor-speed effect as the second net.

### 2.3 PDH `% Processor Performance` (candidate 4)

- Fact: `PdhOpenQueryW`, `PdhAddEnglishCounterW`, `PdhCollectQueryData` twice with a 1 s sleep,
  `PdhGetFormattedCounterValue` (`PDH_FMT_DOUBLE`), all through ctypes on `pdh.dll`. Documented
  (Windows Vista onwards), not deprecated. `PdhAddEnglishCounterW` takes the English path on any
  Windows language, which removes the brief's § 6 assumption 3.
- Fact: whole read 1.0 s (1.35 s the first time in a process); `Get-Counter` in a PowerShell process
  took 2.5 s. In a background thread the 1 s gap costs nothing.
- Fact: values today: idle 88.1, 90.0, 98.9 %; under all-core load 124.9, 122.2, 119.7 % (turbo
  above the 2200 MHz base); `% of Maximum Frequency` 63–76 % idle, 100 % under load.
- Fact: this is the reading that shows throttling, and **only under load**: a throttled machine at
  idle also reads 60–99 %, because idle cores clock down. The brief's pre-run rule "processor speed
  < 70 % → 3 lanes" (§ 1.2) would fire on a cold idle machine and miss a throttled one.
- Recommendation: read it in the sampler every 30 s (together with `% Processor Utility`, so a low
  speed counts only when the machine is busy, utility ≥ 50 %), keep the minimum busy speed in the
  record, and make the rule "the last run's processor speed under load < 90 % → 3 lanes" (the same
  shape as the drain rule, design decision 5). Print the pre-run value as information only.

### 2.4 Core Temp (unchanged, two notes)

- Fact: the repo's `scratch/coretemp-probe.py` layout is right (both readers agree to the degree).
  Core Temp also exposes `fCPUSpeed` (3092–5287 MHz seen), one core's clock at that instant; PDH is
  the better speed reading.
- Fact: temperatures move fast: 64.5 °C idle, 95.5 °C, 99.5 °C after 16 s of all-core load, 64.5 °C
  a minute later. The suite's load will reach about 100 °C on this laptop in any room; the brief's
  rule "the last run's hottest core ≥ 98 °C → 4 lanes" would then fire after every run.
- Recommendation: keep the pre-run temperature rules (a hot machine before the run is a real
  signal), but replace the last-run peak rule by the fraction of samples at or above TjMax − 2
  (for example, more than half the samples ≥ 98 °C → 4 lanes), or drop it in favour of the
  speed-under-load rule of § 2.3, which is the effect that matters.

### 2.5 WinRT `PowerManager` (candidate 1)

- Fact: `PowerSupplyStatus` (NotPresent 0 / Inadequate 1 / Adequate 2), `EnergySaverStatus`
  (Disabled 0 / Off 1 / On 2), `BatteryStatus` (NotPresent 0 / Discharging 1 / Idle 2 / Charging 3),
  `RemainingChargePercent`. Documented, Windows 10 10240 onwards, not deprecated.
- Fact: read today `Adequate`, `Disabled`, `Idle`, 100 %. Microsoft: "when the device is plugged
  in, battery saver is turned off and EnergySaverStatus is Disabled" (written before Windows 11's
  "always use energy saver"; § 6 check 2 tests it).
- Fact, how to call it:
  - **Windows PowerShell 5.1** (`powershell.exe`): `[Windows.System.Power.PowerManager, Windows.System, ContentType=WindowsRuntime] | Out-Null; [Windows.System.Power.PowerManager]::PowerSupplyStatus` works; four properties as JSON in 15 ms inside the process, about 300 ms with the process start.
  - **PowerShell 7.5** (`pwsh.exe`): "Unable to find type": PowerShell 7 has no WinRT projection. A runner that calls PowerShell must call `powershell.exe`, not `pwsh`.
  - **Python stdlib**: `combase.RoGetActivationFactory("Windows.System.Power.PowerManager", IID_IPowerManagerStatics)` then the getters by vtable slot (after `IInspectable`'s six: `EnergySaverStatus` 6, `BatteryStatus` 9, `PowerSupplyStatus` 12, `RemainingChargePercent` 15; order verified against the generated `windows-rs` bindings). 10 ms the first time, then 0 ms. Values matched PowerShell 5.1 exactly.
- Fact: it adds nothing today that #1 and #2 do not give: *Inadequate* is defined as a negative
  charge rate, and *EnergySaverStatus* is the same battery-saver state as `SystemStatusFlag`.
- Recommendation: do not build it unless § 6 shows `EnergySaverStatus=On` while `SystemStatusFlag=0`
  (then take the ctypes route, 25 lines with the slot table in a comment, or `powershell.exe` 5.1 as
  the plainer alternative). The vtable call is correct but it is the kind of code CLAUDE-COMMON
  calls clever; two documented Win32 structs are plainer.

### 2.6 `AggregateBattery.GetReport()` (candidate 5)

- Fact: works from PowerShell 5.1 only; `ChargeRateInMilliwatts` is the same number as
  `SYSTEM_BATTERY_STATE.Rate` (0 now), so it shows the dock's shortfall exactly when #1 does.
- Recommendation: not needed.

### 2.7 Power mode overlay (candidate 3)

- Fact: `PowerGetEffectiveOverlayScheme` and `PowerGetActualOverlayScheme` exist in `powrprof.dll`,
  return 0 and a GUID; today the all-zero GUID (Balanced), which matches the active scheme
  `381b4222-…` (Balanced, the only scheme on this machine). No Microsoft documentation page exists for
  either function. Community sources agree on `961cc777-2547-4f9d-8174-7d86181b8a7a` = Best power
  efficiency and all-zero = Balanced; `ded574b5-45a0-4f42-8737-46345c09c238` = Best performance and
  `3af9b8d9-7c97-431d-ad78-34a8bfea439f` = Better performance are recalled, not confirmed.
- Recommendation: leave it out (CLAUDE-COMMON: no undocumented or deprecated APIs; the slider's
  effect shows in § 2.3). If KLA wants the line "Power mode is Best power efficiency", he confirms
  the GUIDs once by moving the slider and running `probe_ctypes.py`; then it is print-only.

### 2.8 `PROCESSOR_POWER_INFORMATION` (candidate 4, the other half)

- Fact: documented as "`CurrentMhz` = maximum specified frequency × current throttle; `MhzLimit` =
  … × thermal throttle limit". On this machine `MaxMhz=2200` (the base clock), `CurrentMhz` is
  1466–2200 and reaches 2200 under load, `MhzLimit` stays 2200. It cannot show turbo (120 % in PDH)
  and did not move with heat.
- Recommendation: not used. PDH is the speed reading.

### 2.9 WMI performance classes

- Fact: the first `Win32_PerfFormattedData_Counters_ProcessorInformation` query took **110 s** (the
  WMI performance adapter's first refresh), the second 0.3 s. A runner cannot wait that long.
- Recommendation: not used.

### 2.13 Cooling mode (side finding)

- Fact: `SYSTEM_POWER_INFORMATION.CoolingMode` reads 1 = `PO_TZ_PASSIVE`: Windows' system cooling
  policy on this plan prefers slowing the processor to running the fans harder. The setting
  (`SUB_PROCESSOR SYSCOOLPOL`) is hidden in `powercfg` and in Power Options here.
- Assumption: Active would keep clocks higher in a hot room at the cost of fan noise. Changing it
  needs `powercfg -attributes … -ATTRIB_HIDE` (admin) and then the Power Options page. A thing for
  KLA to weigh, not for the runner.

## 3. Recommendation: the readings S053 should use, in order

1. **`SYSTEM_BATTERY_STATE`** (ctypes): `AcOnLine`, `Discharging`, `Rate`. Before the run: on
   battery → 3 lanes. In the sampler: `AcOnLine=1` and (`Discharging=1` or `Rate<0`) in any sample →
   "the battery lost N W on mains power: the charger is too weak" and the 3-lane rule at the next run.
2. **`GetSystemPowerStatus`** (ctypes): `SystemStatusFlag=1` → "energy saver is on" (a 3-lane rule
   if § 6 check 2 confirms it; a line only if not). `ACLineStatus` is a cross-check of `AcOnLine`.
3. **PDH `% Processor Performance` + `% Processor Utility`** (ctypes): in the sampler every 30 s;
   before the run as information. Rule from the last run's record: busy speed < 90 % → 3 lanes.
4. **Core Temp** (mmap): unchanged, with § 2.4's change to the last-run rule.
5. Optional, only if § 6 says it adds information: WinRT `PowerManager` through ctypes, or
   `powershell.exe` (5.1) if the planner prefers plain code over the vtable call.

Fallbacks: each reader returns `None` on any `OSError` / `AttributeError` (not Windows: the
`WinDLL` import fails; no battery: `BatteryPresent=0`; no Core Temp: the mapping is missing; a
counter missing: a non-zero PDH status). A `None` reading is left out of the rules and named in the
line, as § 1.1 already says. No reader starts a process, so there is nothing to time out.

Total cost before the run: about 1.0 s (the PDH gap) plus 2 ms. In the sampler: 1 s of sleep per
30 s tick in the background thread.

## 4. What should change in the brief

- **§ 1.1 table**: replace the `Get-Counter` row by PDH through ctypes (1 s, English names on any
  language); replace the `root/wmi BatteryStatus` row by `SYSTEM_BATTERY_STATE` (0.03 ms, `Rate` in
  mW, no sentinel value); the "Slow charging" row becomes "readable as its effect: Windows' own
  *Inadequate* is defined as a negative charge rate on mains, which `Rate` gives; the dock's shortfall
  shows under load"; the "Energy saver" row becomes `GetSystemPowerStatus.SystemStatusFlag`
  (documented "battery saver on"), with a note that KLA's check 2 decides whether it is a rule or a
  line. Drop the register value row, or keep it as the fallback of § 6 check 2.
- **§ 1.2**: remove "processor speed < 70 %" as a pre-run rule (§ 2.3); add "the last run's processor
  speed under load < 90 % → 3 lanes"; add "energy saver on → 3 lanes" (pending check 2); change
  "the last run's hottest core ≥ 98 °C → 4 lanes" per § 2.4.
- **§ 1.3**: the sampler reads temperature, battery (`Rate`) and the PDH speed pair every 30 s; it
  keeps peak temperature, the share of samples ≥ 98 °C, the most negative `Rate` on mains, the
  minimum busy speed, and the sample count.
- **§ 1.4 lines**: "the battery lost 35 W on mains power" and "the processor ran at 64 % of its speed
  while busy" in place of the drain-only and idle-speed wording.
- **§ 3**: `read_power()` is ctypes, no subprocess; `read_speed()` is PDH; the tests stub the ctypes
  functions (`monkeypatch` on the module's `_battery_state`, `_pdh_sample`), not a canned PowerShell
  JSON. `machine_check.py` should create the `ctypes.WinDLL` handles inside the readers, not at
  import, so the pure functions import and test anywhere (`run-tooling-tests.bat` runs on Windows
  today; `ctypes.WinDLL` does not exist on Linux).
- **Design decision 3**: "ctypes to documented Win32 APIs (`kernel32`, `powrprof`, `pdh`), stdlib
  only, no PowerShell, no `pywin32` / `wmi`." Rejected: one PowerShell call per read (2.5 s for the
  counter, `pwsh` cannot load WinRT, `powershell.exe` 5.1 is in maintenance).
- **Design decision 4** ("the counter only before the run") inverts: the counter runs in the sampler
  and is information only before the run.
- **§ 6**: assumption 3 (English counter name) is removed by `PdhAddEnglishCounterW`; assumption 2
  becomes "`Rate` goes negative on the dock under load", checked by § 6 check 1.

## 5. CLAUDE-COMMON rules that apply

- *No deprecated APIs*: every recommended API is current and documented. `PowerGetEffectiveOverlayScheme`
  is undocumented, so it stays out. Windows PowerShell 5.1 is not deprecated, but it gets no new
  features, and PowerShell 7 cannot do the WinRT part: a reason to avoid PowerShell here.
- *Dependency health, stdlib preferred*: ctypes meets it; `pywin32`, `wmi`, `winrt` stay out.
- *Explicit over clever*: the WinRT vtable call is the one piece that needs a comment table; prefer
  not to need it (§ 2.5).
- *Pure core, thin shell*: the readers return plain dicts; `advise()` and `run_summary()` stay pure.

## 6. What KLA should run (two checks, 5 minutes)

Keep Core Temp running. Open a terminal in the repo root. The probe is the scratchpad file
`C:\Users\KLA\AppData\Local\Temp\claude\C--Users-KLA-PycharmProjects-Yantra\4cb08d41-5654-498e-a3ec-a8406a3f2557\scratchpad\probe_load.py` (with `probe_ctypes.py` and `probe_pdh_winrt.py` beside it; copy the three to `scratch/` if the scratchpad is gone — § 7 holds the same code).

**Check 1 — the dock alone (the weak charger).** Unplug the barrel adapter, leave the Thunderbolt
dock, wait until the battery flyout shows "Slow charging".

1. Run `powershell -NoProfile -Command "[Windows.System.Power.PowerManager, Windows.System, ContentType=WindowsRuntime] | Out-Null; [Windows.System.Power.PowerManager]::PowerSupplyStatus; [Windows.System.Power.PowerManager]::BatteryStatus"` and note the two words.
2. Run `python <scratchpad>\probe_load.py` (16 s of all-core load) and note the `Battery Rate=… Discharging=…` lines for `idle`, `load 8s`, `load 13s`.
3. Read: `Inadequate` at idle means Windows' "Slow charging" and *Inadequate* are the same flag, and
   the pre-run check can name the weak charger before the run starts. `Adequate` at idle and
   `Rate < 0` under load means only the sampler sees the dock, as the brief assumes.
   `Rate = 0` under load as well means the dock copes with this load and the drain rule needs
   another sign (the busy processor speed of § 2.3).

**Check 2 — energy saver while plugged in.** Barrel adapter back in. Turn energy saver on (Quick
settings › Energy saver, or Settings › System › Power & battery › Energy saver › Always use).

1. Run `python <scratchpad>\probe_ctypes.py` and note `SystemStatusFlag` (first line) and `EnergySaverState` (registry line).
2. Run the PowerShell line of check 1 with `EnergySaverStatus` in place of the two properties.
3. Turn energy saver off again.
4. Read: `SystemStatusFlag=1` → rule from #2, free. `0` but `EnergySaverStatus=On` → the WinRT
   reading is needed (§ 2.5). Both off → only the register value changes, and the rule stays an
   effect (processor speed under load).

## 7. Code the coder can start from (verified today)

```python
import ctypes, ctypes.wintypes as wt, time

class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [("ACLineStatus", ctypes.c_ubyte), ("BatteryFlag", ctypes.c_ubyte),
                ("BatteryLifePercent", ctypes.c_ubyte), ("SystemStatusFlag", ctypes.c_ubyte),
                ("BatteryLifeTime", wt.DWORD), ("BatteryFullLifeTime", wt.DWORD)]

class SYSTEM_BATTERY_STATE(ctypes.Structure):
    _fields_ = [("AcOnLine", ctypes.c_ubyte), ("BatteryPresent", ctypes.c_ubyte),
                ("Charging", ctypes.c_ubyte), ("Discharging", ctypes.c_ubyte),
                ("Spare1", ctypes.c_ubyte * 3), ("Tag", ctypes.c_ubyte),
                ("MaxCapacity", wt.ULONG), ("RemainingCapacity", wt.ULONG), ("Rate", wt.LONG),
                ("EstimatedTime", wt.ULONG), ("DefaultAlert1", wt.ULONG), ("DefaultAlert2", wt.ULONG)]

SYSTEM_BATTERY_STATE_LEVEL = 5          # POWER_INFORMATION_LEVEL.SystemBatteryState

def read_power():
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    powrprof = ctypes.WinDLL("powrprof")
    status = SYSTEM_POWER_STATUS()
    if not kernel32.GetSystemPowerStatus(ctypes.byref(status)):
        raise ctypes.WinError(ctypes.get_last_error())
    battery = SYSTEM_BATTERY_STATE()
    nt = powrprof.CallNtPowerInformation(SYSTEM_BATTERY_STATE_LEVEL, None, 0,
                                         ctypes.byref(battery), ctypes.sizeof(battery))
    if nt != 0:
        raise OSError(f"CallNtPowerInformation NTSTATUS 0x{nt & 0xFFFFFFFF:08X}")
    return {"on_mains": bool(battery.AcOnLine), "battery_present": bool(battery.BatteryPresent),
            "discharging": bool(battery.Discharging), "rate_mw": battery.Rate,
            "energy_saver": status.SystemStatusFlag == 1}

PDH_FMT_DOUBLE = 0x200
class PDH_FMT_COUNTERVALUE(ctypes.Structure):
    _fields_ = [("CStatus", wt.DWORD), ("doubleValue", ctypes.c_double)]

def read_speed(gap_s=1.0):
    """% Processor Performance and % Processor Utility of all processors, two samples gap_s apart."""
    pdh = ctypes.WinDLL("pdh")
    paths = [r"\Processor Information(_Total)\% Processor Performance",
             r"\Processor Information(_Total)\% Processor Utility"]
    query = ctypes.c_void_p()
    if pdh.PdhOpenQueryW(None, 0, ctypes.byref(query)):
        raise OSError("PdhOpenQueryW failed")
    try:
        handles = []
        for path in paths:
            handle = ctypes.c_void_p()
            rc = pdh.PdhAddEnglishCounterW(query, path, 0, ctypes.byref(handle))
            if rc:
                raise OSError(f"PdhAddEnglishCounterW {path}: 0x{rc & 0xFFFFFFFF:08X}")
            handles.append(handle)
        pdh.PdhCollectQueryData(query)
        time.sleep(gap_s)
        if pdh.PdhCollectQueryData(query):
            raise OSError("PdhCollectQueryData failed")
        values = []
        for handle in handles:
            value = PDH_FMT_COUNTERVALUE()
            if pdh.PdhGetFormattedCounterValue(handle, PDH_FMT_DOUBLE, None, ctypes.byref(value)):
                raise OSError("PdhGetFormattedCounterValue failed")
            values.append(value.doubleValue)
    finally:
        pdh.PdhCloseQuery(query)
    return {"performance_pct": values[0], "utility_pct": values[1]}
```

Readings today with this code: `{'on_mains': True, 'battery_present': True, 'discharging': False,
'rate_mw': 0, 'energy_saver': False}` and `{'performance_pct': 90.0, 'utility_pct': 4.7}` idle,
`124.9 / 124.9` under load.

The optional WinRT reader (§ 2.5), if it is ever needed: `combase.RoInitialize(1)`;
`WindowsCreateString("Windows.System.Power.PowerManager")`; `RoGetActivationFactory(hstring,
IID {1394825D-62CE-4364-98D5-AA28C7FBD15B}, &factory)`; call vtable slots 6 (`EnergySaverStatus`),
9 (`BatteryStatus`), 12 (`PowerSupplyStatus`), 15 (`RemainingChargePercent`) with signature
`HRESULT (*)(IInspectable*, int*)`; `Release` (slot 2). Verified against PowerShell 5.1's values
and the `windows-rs` vtable order.
