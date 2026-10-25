```
Step: S055 — The Full level runs logic once: desktop and iPhone only their @device tests
Doc: brief
Author: Planner (Opus)
Date: 25-10-2026
Track: light
Status: Gate A (brief review r1: 0 blocker, 0 major; all findings answered)
Baseline: 01d3566 + uncommitted S049 (brief-review r1)
```

# S055 — The Full level runs logic once

**The need (KLA, 25-10-2026).** "The logic is already tested in android. No need for tests in iPhone.
Maybe only a few critical screen layout tests, front end functionality etc is enough." The release's
Full level runs every test on all three devices (560 tests, about 6 minutes, the CPU at its limit in
the v0.1.9 release). KLA chose (25-10-2026) that the desktop also runs only its `@device` tests at
Full.

**Track: light.** Test config and tooling only; the pattern of S047's Normal level; about 9 files; no
migration, no RBAC, no app code.

## 1. What will be built, and out of scope

**The levels after this step** (S047 § 1.1, Full changed):

| Level | `phone-chromium` | `desktop-chromium` | `phone-webkit` |
|---|---|---|---|
| Basic | `@smoke` | — | — |
| Normal | every test | `@device` | — |
| **Full** | every test | `@device` | `@device` |

Full is Normal plus the iPhone's `@device` tests (26 per project on 25-10-2026, `npx playwright test
--list -g @device`; S050, S051 and S052 tagged three since S047's 23; BR1-01): every project lists 189
tests, so Full goes from 567 to about 241, the browser part of the release about 2–3 minutes instead of 6.

- `run_lanes.py`: `expand_level("full", args)` returns `{"E2E_LEVEL": "full"}` when the caller named no
  `--project` (as Normal does); with a named `--project`, nothing changes (every matching test runs
  there, S047 BR1-01).
- `playwright.config.js`: the `@device` filter (`grep: /@device/`) applies to `desktop-chromium` when
  `E2E_LEVEL` is `normal` or `full`, and to `phone-webkit` when it is `full`.
- The rule for tags (CLAUDE.md § Browser tests): "a geometry helper inside a flow test does not tag it
  (Full checks those per device)" loses its reason. It becomes: a dialog is checked on another device
  only through a `@device` test; the Android phone (412 px) checks every dialog in every flow.

**Out of scope:** retagging tests (the `@device` list of S047 stays; a coder adds `@device` to a test
only by S047's rule); Basic and Normal (unchanged); the release's unit suites.

## 2. Standards and practice

- **Risk-based testing** (ISO/IEC/IEEE 29119 Part 1, concepts): test effort follows risk. The logic
  does not depend on the browser engine or the screen, so it is tested once; layout and device
  behaviour, which do differ, are tested on every device.
- **A deliberate change of S047's decision 4** ("Full keeps today's run unchanged, so the release still
  checks every dialog of every flow on the iPhone"): KLA accepts that a dialog met only inside a flow is
  checked at the Android phone's 412 px, not the iPhone's 390 px.
- No maintenance standard (TPM, ISO 14224, EN 13306) applies: this is development tooling (BR1-06).

## 3. Where

| File | Change |
|---|---|
| `tooling/e2e/run_lanes.py` | `expand_level`: Full sets `E2E_LEVEL=full` when the level chose the projects; its docstring |
| `tooling/tests/test_run_lanes.py` | `TestLevels.test_full_adds_nothing` becomes "Full adds no project and sets E2E_LEVEL=full"; new: a named `--project` at Full sets no `E2E_LEVEL`; `test_only_full_starts_the_webkit_container` unchanged |
| `frontend/playwright.config.js` | `DEVICE_ONLY` from `E2E_LEVEL`: normal → desktop; full → desktop and phone-webkit; the header comment |
| `tooling/run-e2e-tests.bat`, `tooling/release-tests.bat` | header comments: Full = every test on the Android phone, the `@device` tests on desktop and the iPhone |

### Docs (housekeeping, by the coder)

- `.claude/CLAUDE.md` § Browser tests (the levels, the tag rule's reason), § Release (the Full level's
  description) and § SMTW-Review (the audit's `--level=full` line; BR1-03); `.claude/agents/coder.md`, `.claude/agents/code-reviewer.md`,
  `.claude/skills/step/SKILL.md` (where they describe Full); `docs/steps/README.md` § Manual checks —
  each as it stands after S049's gate B, since S049 edits the same files (BR1-04).

## 4. Design decisions

1. **Full = Normal + the iPhone's `@device` tests** (KLA, 25-10-2026). Rejected: the desktop keeps every
   test at Full (about 165 more tests, a minute more).
2. **The same `E2E_LEVEL` mechanism as Normal**, a project-level `grep`, so a named `--project` still
   runs every matching test (S047 BR1-01). Rejected: a CLI `--grep` per project (Playwright takes one).

## 5. Tests and acceptance

- Unit: the `TestLevels` tests of § 3 (`tooling/run-tooling-tests.bat`), red first.
- `npx playwright test --list` with `E2E_LEVEL=full` (in `frontend/`): the count per project is every
  test on `phone-chromium`, and on the other two the number `--list -g @device` gives that day (26 on
  25-10-2026); report the numbers (BR1-01).
- One run at the Full level (`tooling/run-e2e-tests.bat --level=full`, in the background, the iPhone in
  its container): green; the count and the time. This brief asks for this one Full run, as an exception to
  the coder's rule "never the Full level" (`coder.md`, README § Manual checks), because the step
  changes the Full level itself (BR1-02; named at gate A).
- Manual checks: none.

## 6. Open questions and assumptions

1. **Fact** (BR1-05): the iPhone's own cases are `@device` (`notifications.spec.js:104`, `:112`,
   `:241`); `:88` and `:153` skip only on the iPhone and stay logic tests.

## 7. Amendments

None.

## Review log

### U1 — 25-10-2026 (before drafting)

KLA: "The logic is already tested in android. No need for tests in iPhone. Maybe only a few critical
screen layout tests, front end functionality etc is enough." Desktop at Full: `@device` only (KLA's
answer, as recommended).

### Round 1 — `2-brief-review-r1.md` (Fable), answered 25-10-2026

| Finding | Answer |
|---|---|
| BR1-01 minor: 26 `@device` tests, not 23 | Accepted: 26 with the date; § 5 compares with `--list -g @device` that day (§ 1, § 5) |
| BR1-02 minor: the Full run is this brief's exception | Accepted: worded as this brief's exception, named at gate A (§ 5) |
| BR1-03…BR1-06 nits | Accepted, all: § SMTW-Review in the docs (§ 3); the docs as they stand after S049's gate B, Baseline set (§ 3, header); assumption 1 is a fact (§ 6); the no-maintenance-standard line (§ 2) |
