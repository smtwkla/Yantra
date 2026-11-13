```
Step: S100 — Three tests that depend on what other tests left behind
Doc: brief
Author: Orchestrator (Opus)
Date: 02-11-2026
Track: fix
Baseline: refs/steps/S099 (S099 at code review; HEAD c9cd091 + S095–S099)
Status: Done — folded into S104 (KLA 13-11-2026, gate B 2a: its code is reworked and committed with S104; its own snapshot dropped); was: Held 02-11-2026 by KLA (one path: PM templates linked to class, model or machine; R03 re-plan; 5b nothing adopted until the rework is done); was: Gate B 02-11-2026 (code review r1: 1 minor, 1 nit; CR1-01 fixed by the orchestrator; carries S099's CR2-01; no device check)
```

# S100 — Three tests that depend on what other tests left behind

Found during tonight's PM steps (S095–S099, 01–02-11-2026). Each test passes alone and fails
when another test, in the same database or the same browser lane, ran first. The code is right;
the tests assume a state they do not make. Fix lane: tests only, 3 files, no code change.

## The bugs

1. **`backend/tests/test_equipment_api.py::TestTypeFilterAndSearch::test_search_words_in_any_order`**
   (S092). It asserts `q="press 999"` finds nothing (`test_equipment_api.py:1322`). The search
   matches words in the node code, and the worker databases are kept between runs, so the code
   serial grows. A node whose code holds `999` (e.g. a generated code ending `…999…`) then matches.
   Seen once in S095's full run (`assert [137] == []`), passed on re-run.
   - **Fix:** a word no generated code or name can hold: `q="press nomatch"` (the next test,
     `test_search_uses_at_most_eight_words`, already uses `nomatch` the same way, `:1335`).
2. **`frontend/e2e/improvements.spec.js:97`** "S068: the Improvements tab lists the improvement, the
   Unit filter narrows, Closed is empty". It expects the text "No closed improvements yet."
   (`improvements.spec.js:122`). `improvement-register.spec.js:83` (S076) drops an improvement,
   which shows under *Closed*; when the lane plan puts both files in one lane, S068's assertion
   fails (S097's whole run, lane 5; S097 code review r2 CR2-03).
   - **Fix:** under *Closed improvements*, assert this test's own improvement row is not listed
     (`row` toHaveCount 0), which is what the step checks; the title ends "Closed leaves it out".
3. **`frontend/e2e/labels.spec.js:57`** "labels printed from the equipment list's ticks"
   (desktop-chromium). It ticks `Select EXT001 for labels` on `/equipment` (`labels.spec.js:59-60`).
   Other specs in the same lane make machines whose codes sort before `EXT001` (class CMP), so the
   extruder moves to page 2 and the tick is not there (S098's whole run, 72 machines).
   - **Fix:** open the list searched for the extruder's code,
     `/equipment?q=${encodeURIComponent(seed.extruder.code)}`, as `equipment.spec.js:164` does,
     so the row is on page 1 whatever other tests made.

## Files

- `backend/tests/test_equipment_api.py` (one word)
- `frontend/e2e/improvements.spec.js` (one assertion and the title)
- `frontend/e2e/labels.spec.js` (the start URL)

## The failing test first

The faults depend on order, so a red run is made on purpose: (1) a node named or coded with
`999` made in the test, before the fix, shows the old word matches; (2) and (3) are red in a
whole run only. The coder states the red evidence it can show and runs each fixed test alone and
in the targeted run of its spec files.

## Review log

| ID | Finding | Answer |
|---|---|---|
