```
Step: S092 — Find a machine by model, maker or class, and confirm it
Doc: code review r1
Author: Code reviewer (Opus)
Date: 01-11-2026
Status: Done — 0 blocker, 0 major, 1 minor, 1 nit
```

# S092 — Code review, round 1

**Verdict: no blocker or major finding is open.** The search, the hint texts, the third line and the two links
match the brief. One test does not prove what its name says (CR1-01).

## Test results

- `YANTRA_TEST_RUN=s092cr1 tooling/run-tests.bat`: backend 1 failed, 4470 passed (107 s); frontend 412 passed;
  tooling 231 passed.
- The one failure is outside the step: `tests/test_readings_api.py::TestOtherKinds::test_the_meters_list_carries_the_last_reading`
  expected `taken_at` 17:43 and got 17:42. The test calls `_minutes_ago(30)` again after the three logs, so a
  minute that ends between the log and the assert makes it fail. S092 touches no readings code. A re-run of
  `test_readings_api.py` and `test_equipment_api.py` passed (294 passed). Fact: this is a timing fault in an old
  test, not an S092 fault; recommendation: the orchestrator records it for a later fix (keep the value from the
  first `_minutes_ago(30)` call and assert against it).
- Browser tests: I did not run any. The coder's runs are the right ones: the two new `S092:` tests alone, the
  targeted run (`tickets-raise`, `contracts`, `readings`, `equipment`, `screens`; 189 passed, 2 skipped) and the
  whole suite once (375 passed, 15 skipped, 0 failed). No finding of mine needs a browser run.
- `npx vite build`: the coder's run passed; I did not repeat it (the frontend unit suite passed and the change
  imports only existing components).
- No migration, so no schema docs check.

## Findings

### CR1-01 (minor) The class-code test passes without the class-code field

- **Where:** `backend/tests/test_equipment_api.py:1308`.
- **Problem:** `q=press["code"]` finds the node through `e.code`, not through `c.code`. A node's code is its
  class code plus a serial (`equipment.py:870`, `_next_code(cur, equipment_class["code"])`), so the code always
  carries the class code at creation. The assertion stays green if `c.code LIKE %s` is removed from
  `list_equipment`.
- **Failure scenario:** a later edit drops `c.code` from the search. A machine reclassified by a model change
  keeps its old code (S012, `test_equipment_api.py:231`), so a search by its new class code finds nothing. No
  test turns red.
- **Fix:** in the same test, give the node a model of a second class (`_put(admin, node, model_id=…)`; the code
  is kept), then assert that `q=<second class code>` finds it. Show it red with `c.code` removed, then green.

## Nits

- **CR1-02** (nit) `frontend/e2e/tickets-raise.spec.js:97`: the locator `.d-flex span.text-secondary` binds the
  test to layout classes; `match.getByText(<class code>, { exact: true })` asserts the same thing the user sees.

## Checked and found consistent

- **The SQL per word** (`backend/equipment.py:651-654`). `q` is stripped and split with `str.split()`, so
  empty text or only spaces adds no condition, and a tab splits too (asserted at `:1316`). Each word adds one
  `AND`-ed group of eight `OR`-ed `LIKE`s with eight parameters, all built from `%s` placeholders. The search
  conditions come before the unit and ticket conditions, and `params` keeps that order. A word that is only `%`
  or `_` is escaped by `like_pattern` and matches a literal character only. The cap gives at most 64 parameters;
  the cap test asserts both sides (ninth word ignored, first word used).
- **Matches only grow.** A text that matched one field as one piece matches word by word in the same field. A
  text that matched the old `CONCAT(mf.name, ' ', m.designation)` matches word by word in `mf.name` or
  `m.designation`, and a node with a model but no maker name now matches by designation alone. All joined tables
  are in `NODE_JOINS`; `t`, `m` and `mf` are left joins, so a NULL field only fails its own `LIKE`.
- **Who uses the route.** `list_equipment` serves the picker, the Equipment list and the Move dialog; the
  printed asset list does not take `q`. No other route used the old search text. No test or spec named the old
  placeholders ("Code or name", "Search by code or name…", "Search code, name, model, notes…").
- **Screen text against the brief, word for word:** the three placeholders, the hint line, both "More found —
  add a word, such as the model or class." lines and "Open equipment page". They follow scope B: short, plain,
  and the link starts with a verb.
- **The third line** (`EquipmentPicker.vue:84-89`): `d-flex flex-wrap align-items-center gap-2 small`, the
  model label only when present, the class code, then the two badges with the same props as
  `EquipmentView.vue:509-510`. The fields come from `_summary`; no new request. A long maker name wraps at its
  spaces inside the flex row, so it adds no sideways scroll at phone width. The row stays one button.
- **The links.** `router-link` with `target="_blank"` is the existing pattern (`RaiseTicketView.vue:323`,
  `:449`): Vue Router's click guard leaves a link with `target="_blank"` to the browser, so it opens a new tab and
  the form stays. `rel="noopener"` is set on both. Raise ticket's link is full size beside *Change* in a
  `flex-wrap` card. The contract dialog's is `btn-sm` beside *Change*, as the brief says; the `flex-wrap` the
  coder added is listed in Decisions taken. Every role that can open Raise ticket or Add machine holds
  `equipment:read`, which the equipment page needs.
- **The focus line in the contracts test** (`contracts.spec.js:343-344`). The focus loss is not new: since
  S081 the picker's list leaves the dialog on a pick, and the clicked button goes with it. On a phone nothing
  shows. With a keyboard, Bootstrap's focus trap pulls the next Tab back into the dialog. The test's line puts
  focus where `openDialog`'s wait expects it; it hides no fault the user would see. Moving focus to *Change* after
  a pick would help keyboard users, but no brief asks for it.
- **Tests against the brief's § 5:** the four backend tests named, plus a tab and spaces case; the existing
  search tests unchanged; both browser tests assert what the user sees (the hint, the model and class on the
  match, the link's `href` and `target`, the dialog fit). Both are untagged logic tests, which is right.
- **Docs pass:** `docs/Plan.MD:315` names what the search finds; `docs/steps/device-checks.md` row 63 holds the
  brief's important check with the person, the network and the place. No other listed doc is due.
- **Manual checks:** the impl report's `## Manual checks` carries the brief's important check as an unticked box
  and the two automated checks as `[auto]` with their tests.
- **Scope and track:** everything in § 1 is built and nothing more; no migration, permission or shared frontend
  file is touched, so the light track holds.

## Still for the user's manual check

- Device-checks row 63: in the installed app on an Android phone and an iPhone, tap *Open equipment page* on
  Raise ticket, return, and see that the half-filled form is still there.

## Feedback

- hindrance: a timing fault in an old readings test (`test_readings_api.py:263`, minute boundary) turned the
  whole backend suite red, so I had to read the trace and re-run two files to tell it from an S092 fault
  (`scratch/backend-tests-s092cr1.log`, about 2 min).
