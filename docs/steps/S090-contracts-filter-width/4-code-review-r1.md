```
Step: S090 — Contracts filters fit the phone's width
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 01-11-2026
```

# S090 — code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The fix is the brief's fix, and the test now covers the
long vendor name on every device. No findings.

## What I checked

- **The diff** (`git diff -w --ignore-cr-at-eol a6e3778 -- frontend/`): `mw-100` added to the four filter
  selects at `frontend/src/views/masters/ContractsPanel.vue:133-146`, and the vendor name of the S080 list test
  lengthened at `frontend/e2e/contracts.spec.js:249`. `git status` shows no other changed code file. Scope
  matches the brief. `EquipmentView.vue` is not touched, as the brief says.
- **Desktop layout.** `mw-100` is `max-width: 100%` of the filter row (`d-flex flex-wrap gap-2`). It only caps a
  select; it never makes one wider. On desktop the row is far wider than any option, so `w-auto` still sizes each
  select to its content, and the four filters sit in one row as before. The coder's targeted run passed the S080
  test on `desktop-chromium` with the long name (its `else` branch also asserts the Sites column).
- **The test covers the case on every device.** The name is `E2E Vendor with a long name for the phone list to
  fit ${tag}`, well over 60 characters. The test is tagged `@device`, so it runs on `phone-chromium`,
  `desktop-chromium` (Normal) and `phone-webkit` (Full). It no longer depends on the S082 test making a long
  vendor in the same lane database first. `expectNoSidewaysScroll` (`e2e/support/dialogs.js:49`) checks both the
  page and `main.app-content`. The later `toHaveText` checks read the DOM text of the phone line, not the select,
  so the clipping does not touch them.
- **The clipped select stays usable.** Only the closed select cuts the text. The native picker on a phone lists
  each option in full, so the user can still read and pick the long vendor. Tap target is unchanged
  (`form-select-sm` was already there; not in this step's scope).
- **Red, then green.** The impl report gives the red run (`contracts.spec.js:247 --project=phone-webkit`, 153 px
  sideways, fix not applied) and the green run of the same command. The red result proves the new test catches the
  bug on WebKit, not only after S082.
- **Tests.** I re-ran nothing. No backend or unit-tested code changed, and no finding of mine needs a browser run.
  The coder's targeted run names the right specs (`contracts.spec.js`, the changed screen, plus
  `screens.spec.js`): 69 passed, 1 skipped. Unit suites (run `s090c1`): backend 4467, frontend 412, tooling 231
  passed. `npx vite build` built. No whole-suite browser run: right for a fix lane with no shared frontend file.
- **Docs pass.** `## Docs updated` says none. Right: no migration, rule, secret or role changed. No schema-docs
  check is due (no `local_db.py` or `docs/schema/` change).
- **Manual checks.** The brief's one check is in the report as `[auto]` with its test and a passing run. No
  real-device check is due.
- **Track.** `Track: fix`; the change is one CSS class and one test value, within the fix lane.

## Nits

- none

## Checked and found consistent

The four selects' classes, the flex row they sit in, the S080 test's assertions and tag, the red and green runs,
the targeted run's specs, the docs pass, and the manual-checks section.

## Manual browser check for the user

- None required. Optional: on a real iPhone, open Masters › Contracts with a long vendor name and pick it in the
  Vendor filter; the closed select shows the cut name, the list does not scroll sideways.

## Feedback

- none
