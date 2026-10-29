```
Step: S069 — Why-why and the root cause
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 30-10-2026
```

# S069 — Code review, round 2 (verify)

**Verdict: no `blocker` or `major` finding is open.** The fix round fixes CR1-01 to CR1-05 as
amendment A1 and the round-1 nits ask. CR1-06 is deferred to S073 with a reason. This round adds
two nits and no other finding.

## Tests run

- `YANTRA_TEST_RUN=s069cr2 tooling/run-backend-tests.bat tests/test_improvements_core.py
  tests/test_improvements_api.py tests/test_improvement_whys_api.py`: **192 passed**.
- `tooling/run-frontend-tests.bat` (the whole frontend suite): **309 passed**.
- `npx vite build` (output to the session scratchpad): clean, with only the known chunk-size
  warning.
- I did not run the tooling suite. The fix round changed no tooling code, and it changed backend
  and frontend code only inside those suites' folders.
- Browser: I made no run. The coder's targeted run is the right one for the fix round:
  `e2e/improvements.spec.js e2e/screens.spec.js` at Normal, 29 passed and 1 skipped (the existing
  per-device skip). The fix round changed `improvements.spec.js`, `WhyDialog.vue` and
  `ImprovementDetailView.vue`, and no shared code.
- Before the runs, `step_snapshot.py diff S069 --from-round 2` showed only `docs/steps/INDEX.md`.
  So the tree I tested is the round-2 state, and the S070 coder's work is not in it.

## Status of the round-1 findings

| Finding | Status | Checked |
|---|---|---|
| CR1-01 (minor) | **Fixed** | `WhyDialog.vue:21,42,48` and `improvementLabels.js:44-50`. See the note below. |
| CR1-02 (nit) | Fixed | `improvements.py:277` uses `{**code_ref(plain, "rc"), …}`. The keys and values are the same as before. |
| CR1-03 (nit) | Fixed | The line that could not fail is gone. Line 316 asserts the empty state on an improvement with no whys. |
| CR1-04 (nit) | Fixed | `POSITION_NOT_NUMBER` sits beside the other messages. The core test asserts the field and the message. |
| CR1-05 (nit) | Fixed | `askRemove` and `askRemoveWhy` each clear the other confirmation and its error (`ImprovementDetailView.vue:82-106`). |
| CR1-06 (nit) | Deferred | Moves to `e2e/support/` in S073, which also needs a closed ticket. This is accepted. |

### CR1-01 and its tests

The code follows A1. `openChange` stores `why.position` before `openEdit`. `whyBody` adds
`position` only on an edit where `Number(form.position)` differs from that stored place. An add
never sends it. A chain of one has no select, and `fromRecord` copies the why's position into the
form. So an edit of a chain of one sends no `position` either. The server is unchanged, as A1
says.

**The tests prove A1's rule, but not its wiring.**

- The four `whyBody` unit tests assert the rule itself:
  - an add sends no `position`;
  - an edit with the same place sends none;
  - an edit with a new place sends it, as a number;
  - evidence that is not blank is kept.
- The red result is weak, as the orchestrator says. The tests failed only because `whyBody` did not
  exist. But the old code had the rule inline in `save()`, so no unit test could reach the old
  behaviour. The case "no position on an edit with the place unchanged" fails against any
  implementation of the old rule ("send on every edit"). The report gives this reason. So I raise
  no finding for the red result.
- The tests do not prove that `WhyDialog.vue` passes the right place. When `openedPosition` stays
  `null` or is set to the wrong value, every edit sends `position` again, and every test still
  passes. The browser tests edit on a fresh page, where a resent place changes nothing. CR2-01
  below suggests the test that closes this gap. It is a nit, because the wiring is three
  plain lines that I read and found correct.

## Nits

- **CR2-01** (nit) `frontend/e2e/improvements.spec.js`: add one assertion to an existing edit flow.
  For a text-only *Save why*, take the `PUT` with `page.waitForRequest` and check that
  `postDataJSON()` has no `position`. Only this proves the dialog's side of A1.
- **CR2-02** (nit) `frontend/src/views/improvements/WhyDialog.vue:113-114`: after A1, a chain of one
  never sends `position`, because it has no select to change. So the `v-else-if` refusal line under
  it can no longer show, and its comment ("an out-of-date page") is wrong. Remove the branch and
  its comment.

## Manual checks still needed

- Not important, unchanged from round 1: row 50 of `docs/steps/device-checks.md` (the iPhone
  keyboard over *Because* in *Add why*).

## Checked and found consistent

- **The fix round's diff** (`step_snapshot.py diff S069 --from-round 1 -- backend frontend`): it
  holds only the changes the report lists. The docs files in the diff belong to other steps (S072,
  S073, the roadmap and the index), not to S069.
- **`whyBody`** sends the same `question`, `answer` and `evidence` (blank → `null`) as the old
  inline body. `Number()` handles the select's value as a number or as a string.
- **No screen text changed.** The report's "Docs updated: none" is right: A1 changes no route,
  message or screen, and the brief's § 10 records it.
- **Files I re-read**: `frontend/src/views/improvements/WhyDialog.vue` (in full), the changed hunks
  of `improvementLabels.js`, `ImprovementDetailView.vue`, `improvements.py`,
  `improvements_core.py`, `test_improvements_core.py` and `improvementLabels.test.js`, the
  `whyCard` and `Place in the chain` lines of `e2e/improvements.spec.js`, the `openEdit` lines of
  `useFormModal.js`, and the brief's § 10.

## Feedback

- hindrance: the fix round's `diff --stat` lists files of other steps (S072 and S073 briefs, the
  roadmap, `INDEX.md`) next to S069's. I had to sort them out by hand, and narrowed the diff with
  `-- backend frontend` (`step_snapshot.py diff S069 --from-round 1 --stat`).
- idea: the impl report's *Red, then green* rule could name the case where the fix extracts new
  code: the red result is "the new test fails against the old behaviour, written as a stand-in".
  Today the coder and the reviewer each judge it on their own (this round, CR1-01).
