```
Step: S052 — Meter readings on the ticket
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 25-10-2026
```

# S052 — code review, round 2 (verify)

**Verdict: no `blocker` or `major` finding is open.** CR1-01, CR1-02 and CR1-03 are fixed. The fix round brings in no new fault. There are two new nits. All four suites pass, and the build passes.

Scope of this round: the fix round's three files, read from the snapshot `refs/steps/S052` (b3c4585):

- `frontend/src/views/tickets/TicketMetersCard.vue`, read in full;
- `frontend/src/utils/meterLabels.js`, the header comment;
- `frontend/e2e/tickets-work.spec.js`, the S052 block (lines 575–709);
- the fix round section and `## Manual checks` of `3-impl-report.md`.

I also read `saveDialog` (`e2e/support/tickets.js`), `openDialog` (`e2e/support/dialogs.js`) and the `consoleWatch` fixture (`e2e/support/test.js`), because the new tests use them. I did not re-read the rest of the step.

## Tests run

- `YANTRA_TEST_RUN=s052cr2 tooling/run-tests.bat`, in a temporary worktree of `refs/steps/S052`: backend 3075 passed, frontend 179 passed, deps 42 passed, tooling 168 passed. ALL SUITES: PASSED.
- `npx vite build` in the worktree's `frontend/`: built in 3.8 s, with the usual chunk-size warning only.
- Browser: not re-run (standing rule, 25-10-2026). The coder ran the targeted specs of the fix at Normal: `e2e/tickets-work.spec.js` and `e2e/screens.spec.js`, 50 passed, 1 skipped (S040's bottom bar on desktop, by design). These are the right specs: the fix changes only the Meters card on the ticket page. None of my findings needs a browser run.

## Findings from round 1

| ID | Severity | Status | Check |
|---|---|---|---|
| CR1-01 | minor | Fixed | `load()` clears `loadError` only when an answer arrives (`TicketMetersCard.vue:38–41`). During *Try again* the root `v-if` stays true, so the card keeps its text and does not jump. The `loading` ref disables *Try again* (`:66`). A superseded load does not reset `loading`, because `finally` checks the sequence number (`:46`). The new e2e test holds the retry in flight and checks the text and the disabled button. The red result is recorded: the test failed without the fix because the card had vanished. |
| CR1-02 | nit | Fixed | The header comment of `meterLabels.js` (lines 3–9) is re-wrapped to under 100 characters. |
| CR1-03 | nit | Fixed | Two new e2e tests: the load failure with a routed 503 then success, and the reload after a part change (the card goes from one node to two, with the part's name). The second test fixes no fault, and the report says so, so no red result is due. |

### The coder's extra change: a new ticket id clears `loadError`

The change is right. It is at `TicketMetersCard.vue:54`, and the report names it in the fix round.

- **Without it**, one ticket's error would stay on the next ticket's page until the new answer arrived. That is because CR1-01's fix no longer clears `loadError` before a request. The card would say "could not be loaded" for a ticket whose load had not yet failed.
- **With it**, a new ticket starts as on a first load: nothing is drawn until its answer arrives (§ 1.7, § 7 decision 10). The previous ticket's late answer or error is dropped by `loadSeq`.
- **The same ticket with a changed part** keeps its error on screen while it reloads. This is the CR1-01 behaviour, and it is consistent.

## New findings

No `blocker`, `major` or `minor` finding.

## Nits

- **CR2-01** (nit) `frontend/e2e/tickets-work.spec.js:695`: the part-change test opens *Edit* with a bare click. Call `openDialog` (focus wait) and `expectDialogFits` after it, as the S018 test at line 245–246 does. The dialog's fit is already tested there, so nothing goes unchecked.
- **CR2-02** (nit) `docs/steps/S052-ticket-meters/3-impl-report.md:129`: the fix round says "two more `[auto]` checks", but `## Manual checks` (lines 103–107) still lists five. Add the two tests as `[auto]` rows, or drop the sentence. Neither check is **important**, so no required row is missing.

## Checked and found consistent

- **The card's state rules** after the fix:
  - first load: nothing drawn until the answer;
  - an empty answer: no card;
  - a failed load: the card with its text and *Try again*;
  - a retry: the card stays, and the button is disabled;
  - a part change: the old answer stays until the new one;
  - a new ticket: answer and error cleared.
- **The 503 test** allows its own failed request through `consoleWatch.allowFailedRequest("/meters", 503)`, so the console watch does not fail it. The held route lets the retry reach the real backend, so the green end shows a real answer.
- **Screen text (scope B)** is unchanged: "Meter readings could not be loaded. Try again in a minute." and *Try again*.
- **Docs pass:** the fix round changes no behaviour a doc describes, so no doc is due.
- **Scope:** the fix round adds only what CR1-01 to CR1-03 ask for, plus the reported `loadError` clear.

## Manual browser check for the user

None required. If you want to look by eye, open a ticket on a press with meters on a phone while the backend is stopped. Tap *Try again* and check that the card stays in place.
