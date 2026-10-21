```
Step: S024 — Browser tests (Playwright)
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 21-10-2026
```

# S024 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open. CR1-01 is fixed. Every suite is green. The
open round-1 findings (CR1-02 to CR1-07, all `minor` or `nit`) are still open and unanswered.
This round adds two `nit` findings.**

Scope: fix round 1 (CR1-01) in `frontend/e2e/masters.spec.js`, and the report's "Fix rounds ›
Round 1". I also re-checked where the other round-1 findings stand. This round changed no
production code, and I found none changed.

## Test results (run by me)

| Run | Result |
|---|---|
| `tooling/run-tests.bat` | exit 0. Backend **1835 passed** (276 s), vitest **93 passed** (12 files), deps tests **42 passed** |
| `tooling/run-e2e-tests.bat`, full | exit 0. **123 passed**, 0 failed, 0 skipped, 0 flaky, 9.8 min (12:50 to 13:00). It is slower than the coder's 4.6 min because the unit suite ran at the same time |
| `scratch/e2e-backend.log` (full run) | no traceback, no 500 |
| `run-e2e-tests.bat tickets-work --project=desktop-chromium --repeat-each=30 --grep=closes.as.not` | exit 0. **30 of 30 passed**, 1.4 s each |

I did not run `npx vite build`, because this round changed nothing under `frontend/src`.

The six new tests (causes and actions, add and edit, on three set-ups) passed in my full run:
- phone-chromium: tests 15 and 16;
- phone-webkit: tests 56 and 57;
- desktop-chromium: tests 97 and 98.

## The unexplained failure: "not a fault: the remark is open and required…"

The coder saw this test fail once on desktop-chromium: the suggested cause showed "—" and not
"5.1 …". It happened in the run where the new cause test was still failing. **My judgement:
not caused by the shared database or by state left over from the failed test. Most likely a
one-off timing flake, cause not found. It does not block.**

What I checked:

- **How the suggestion works.** `MoveDialog.vue:91-96` waits for the cause and action lists.
  Then it sets `cause_id` to the active cause whose code is `"5.1"`. "—" is the empty option
  (`MoveDialog.vue:229`). So the dialog showed "—" for one of three reasons:
  - no active cause `5.1` was in the list;
  - the list failed to load (the dialog would then show "The cause and action lists could
    not be loaded…");
  - the form was replaced after the suggestion was set.

  The test retries its check for 10 s (`expect.timeout`), so a slow load alone does not
  explain it.
- **The three set-ups share one database.** Playwright runs the projects one after another:
  phone-chromium, then phone-webkit, then desktop-chromium. My log shows this order. So
  desktop sees every row the phone runs added. But no test changes cause `5.1`:
  - the only *Deactivate* in `frontend/e2e/` is on the mode "Stops by itself"
    (`masters.spec.js:62-79`);
  - the cause test adds a new code (`CPC`, `CPW`, `CDC`) in the group "Operation /
    maintenance", which does not clash with the ISO codes of migration v11
    (`local_db.py:455-469`), and edits only that row;
  - other tests only read the cause list.
- **State left over from the failed cause test.** That version failed on the server's 400
  (no group picked), so it wrote nothing to the database. Each test gets a fresh browser
  context, and so a fresh masters cache (`stores/masters.js`). Playwright also starts a new
  worker after a failed test. And `resetMasters()` is called only from the Masters panels
  (`useMasterForm.js:26`), never on the ticket page.
- **Reproduction.** I could not make it fail:
  - 30 of 30 repeats on desktop-chromium;
  - plus one pass in my full run, after the masters tests of all three set-ups.

  The trace of the coder's failing run has been overwritten by later runs, so it cannot be
  read now.

If it happens again, the trace that `trace: "retain-on-failure"` keeps will show whether the
`failure-causes` request answered, and when `cause_id` was set. Read it before the next run
overwrites `scratch/e2e-report/`. A recurring failure would be a real fault in the dialog,
not in the test. Then it goes to a new finding (or to S025, which works on not-a-fault).

## Earlier rounds

| Finding | Status in round 2 |
|---|---|
| CR1-01 `major` — the cause and action dialogs never opened or checked | **Fixed**, verified (below) |
| CR1-02 `minor` — S014–S018 reports show the state before A2 | **Open, unanswered**. The reports still give "114 passed" (S014, S015, S016, S017, S018 `3-impl-report.md`) |
| CR1-03 `minor` — the iPhone field-message device row does not exist | **Open, unanswered**. `device-checks.md` still has no row about field messages |
| CR1-04 `minor` — four Masters sections never rendered | **Open, unanswered**. `screens.spec.js` still visits only `/masters` |
| CR1-05 `minor` — `PhotoViewer` disposes while shown | **Open, unanswered**. `PhotoViewer.vue:92` still calls `modal?.dispose()` at once |
| CR1-06 `nit` — FormModal unmount while it is opening | **Open, unanswered** |
| CR1-07 `nit` — `rmtree(..., ignore_errors=True)` | **Open, unanswered**. `e2e_backend.py:60` |

The report says only CR1-01 was asked for in this round. Under README § Findings, each of
CR1-02 to CR1-07 still needs an answer (`Accepted`, `Rejected` or `Deferred`) before the
step is `Done`. None of them blocks the gate.

**CR1-01 verified** (`masters.spec.js:81-110`):
- the loop covers *Causes* and *Actions*;
- each test opens *Add cause* / *Add action* and calls `expectDialogFits`;
- a cause gets a group picked, since none is pre-picked on an unfiltered list;
- the test saves, and checks that the new row shows its code;
- it opens that row's *Edit*, calls `expectDialogFits` again, changes the label, saves, and
  checks that exactly one row shows the new label;
- the code and label carry the set-up's suffix, so the three set-ups do not collide.

Brief § 1.4's list ("S016 failure mode / cause / action add and edit") is now covered in
full. The report's Fix rounds describes the change and the first failure (the missing group).

## Findings

### CR2-01 — `nit` — The new tests are named "a causes entry" and "a actions entry"

- **Where:** `frontend/e2e/masters.spec.js:86`.
- **Problem:** the name is built from `kind.list.toLowerCase()`. That gives "engineer: a
  causes entry is added and edited" and "engineer: a actions entry is added and edited".
- **Failure scenario:** none at run time. The names appear in the HTML report, in the
  `[auto]` lines of S016's report, and in the `/smtw-review` failing-test list. There they
  read as typos, and the user will see them.
- **Fix:** add a `noun` to each kind (`"cause"`, `"action"`) and name the test
  `` `engineer: a ${kind.noun} is added and edited` ``.

### CR2-02 — `nit` — The report's test counts in § 1 and § 6 are not updated

- **Where:** `docs/steps/S024-browser-tests/3-impl-report.md:40` ("39 per set-up, 117 per
  run") and § 6.
- **Problem:** after fix round 1 the suite has 41 tests per set-up and 123 per run. Only the
  Fix rounds section says so.
- **Failure scenario:** at gate B the planner quotes § 1 and shows 117 when the run shows
  123. A reader may then think six tests are missing or new.
- **Fix:** change § 1 to "41 per set-up, 123 per run". Do it together with CR1-02, which
  updates the same numbers in the S014–S018 reports.

## Manual checks

The report's `## Manual checks` is unchanged since round 1 and still carries both
**important** checks of brief § 8 as unticked boxes. The missing iPhone field-message row is
still CR1-03.

Still for the user's or IT Admin's **manual check**:
- [ ] The user runs `tooling/run-e2e-tests.bat` once on their own machine and opens
  `scratch/e2e-report/html/index.html`.
- [ ] IT Admin reads `docs/steps/device-checks.md` and says whether each row can be
  followed without help.
- After this step: the rows of `device-checks.md` (D1–D3, 1–7, and the row CR1-03 adds).
- Once, on the **built** app (production or `vite preview`): on the equipment page, *Print
  label* opens its menu on one click (from round 1, because A2 changed how Bootstrap loads).

## Checked and found consistent

- **CR1-01's fix stays inside the test files.** No file under `frontend/src` or `backend/`
  changed in this round. `masters.spec.js` uses the shared helpers (`openFailureCodes`,
  `saveDialog`, `expectDialogFits`), with no copy of them.
- **The test asserts what the user sees.** It checks the new code in its row and the edited
  label in exactly one row, not only that a dialog opened.
- **Field ids.** `#cause-group`, `#cause-code`, `#cause-label`, `#action-code` and
  `#action-label` exist in the panels and are what the tests fill. The tests pass on all
  three set-ups.
- **Test isolation across set-ups.** The codes `C`/`A` + `PC`/`PW`/`DC` and the labels
  carrying the project name are unique per set-up. They do not clash with the seeded ISO
  codes.
- **The console fixture** stays on for the new tests. Neither new test needs
  `allowFailedRequest`, and none was added.
- **Security, migrations, dependencies:** nothing changed in this round.
- **Track:** full, as the brief says.
