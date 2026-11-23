```
Step: S107 — Ticket tasks: screens
Doc: code-review r2
Author: Code reviewer (Opus 5.5)
Date: 22-11-2026
```

# S107 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** All four round 1 findings are fixed. The fix
round brings in one new nit (a missing space between two attributes).

**Tests run by the reviewer** (`YANTRA_TEST_RUN=s107cr2`):
- `tooling/run-frontend-tests.bat`: PASSED, 495 passed (7 s). The round changed no unit-tested file
  and no file outside `frontend/`, so the all-suites command was not needed.
- `npx vite build` (output to the session scratchpad): built in 5 s, only the existing chunk-size
  warning.
- Browser tests: not re-run. The coder's targeted run at Normal (`tickets-tasks.spec.js`,
  `tickets-work.spec.js`, `screens.spec.js`: 64 passed, 2 skipped, 0 failed) covers the changed
  screen and the changed test. The round adds no `@device` test and no `page.route`, so no WebKit
  run is due. No finding of mine needs a run.
- No schema docs check: the diff touches neither `backend/local_db.py` nor `docs/schema/`.

**Files re-read:** the round's diff (`step_snapshot.py diff S107 --from-round 1`: four files), the
impl report § Fix rounds › Round 1, and in `frontend/src/views/TicketDetailView.vue` the computed
block (lines 110–150: `significantMoves`, `blocksByMove`, `taskTexts`, `timelineRows`) and the
timeline list (lines 470–521).

## Round 1 findings

| ID | Severity | Status |
|---|---|---|
| CR1-01 | minor | Fixed |
| CR1-02 | nit | Fixed (new nit CR2-01 in the changed line) |
| CR1-03 | nit | Fixed |
| CR1-04 | nit | Fixed |

- **CR1-01.** Test 1 of `frontend/e2e/tickets-tasks.spec.js:163-165` now sends a photo from the
  engineer's own *Mark done* on the ticket page. It then asserts two `test-photo` tiles in the
  *Photos* card, with no navigation in between, so the `documentsCards` ref and the `@reload` wire
  are both exercised. The red result is recorded: with the ref renamed, the run failed at `:165`
  (expected 2, received 1), and it passes with the ref restored. Breaking the ref instead of the
  `@reload` wire is fine, because the finding was about the ref failing silently.
- **CR1-02.** `blocksByMove` is keyed by the names of `significantMoves`, the same list the
  template loops over, so `blocksByMove[m.name]` is always defined. `taskTexts` is indexed by the
  event's original index: `timelineRows` maps `(e, i)` before `.reverse()`, so `taskTexts[i]` is the
  text of the same event. This is the pattern `planTexts[i]` and `intensityTexts[i]` already use.
  Both computeds recompute on each `load()`, because the page replaces `ticket`.
- **CR1-03.** The comment above `today` now says it is the input's `min`.
- **CR1-04.** The docstring paragraph is re-wrapped to the width of its neighbours.

## Nits

- **CR2-01** (nit) `frontend/src/views/TicketDetailView.vue:320`: `v-for="reason in blocksByMove[m.name]":key="reason"`
  has no space between the closing quote and `:key`. Vue's compiler accepts it (the build and the
  browser run are green), but HTML calls it a parse error (missing whitespace between attributes).
  Add the space.

## Checked and found consistent

- The round's diff holds only the four files the report names. It changes no behaviour, route,
  key or text the user sees, so "Docs updated: none" is right.
- The new assertion counts tiles only on the test's own ticket. It shares no state with the
  lane's other tests (S100).

## What still needs a manual check on a real device

Unchanged from round 1:
- Row 71 (**important**): *Mark task done* from *Me* with the camera and a work glove, on an
  Android phone, as a technician; the photo shows in the ticket's *Photos* card.
- Row 72: the iPhone keyboard over *Add task*.

## Feedback

- None this round. The verify-only rule and a four-file round diff kept this review short.
