```
Step: S042 — S034's quick-pick e2e test finds its row by serial
Doc: code review r1
Author: Code reviewer (Opus)
Date: 24-10-2026
```

# S042 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** No `minor` finding, one nit.
The fix is correct and stays inside the brief and the fix-lane limits.

## Test results (my own run)

- `E2E_LANES=1 tooling/run-e2e-tests.bat e2e/tickets-work.spec.js -g "In 14 days"`:
  **3 passed** (phone-chromium, phone-webkit, desktop-chromium). This is the
  brief's red command. It now passes on all three projects on one database.
- I did not re-run `tooling/run-tests.bat` or the targeted `tickets-work.spec.js`
  run, as the orchestrator asked. The change is one e2e test, so no backend,
  frontend unit, deps or tooling suite can see it. The coder's runs: all four
  suites passed, and `tickets-work.spec.js` gave 66 passed.
- Red, then green: the impl report gives the red result (1 passed, 2 failed, line
  515) and the green result (3 passed). This matches the brief.

## What I checked

- **The diff** (S042's part of `frontend/e2e/tickets-work.spec.js`, lines 510–517).
  - The list URL is `/tickets?q=S034 test: quick pick`. The text equals the
    description the test raises at line 493.
  - `q` stays in the URL when the State select changes: `TicketsView.vue:50`
    `update()` merges the change into the current query. So the list at
    `state=scheduled` is still filtered by the description.
  - The last assertion filters `.list-group-item` by `ticket.serial`, the
    `raiseByApi` result at line 492. Serials are unique
    (`tickets_core.format_ticket_serial`, `TK-YYYY-MM-NNN`). This is the same
    locator as S036's `rowOf` at line 532.
  - The test still asserts what S034 needs: the date pick, the save, the
    *Deferred* badge, the *Deferred / Waiting* option, and the one row in the
    scheduled list.
- **Scope.** Only the S034 test changed. The `causeId` import and the S036 test
  in the same diff belong to S036, as the brief's baseline says. No app code changed.
- **Fix-lane limits.** One test file. No permissions, interface, migration,
  security or locking change.
- **Header blocks.** The brief and the impl report have them, with
  `Track: fix` and the brief's `Baseline:`.
- **Docs pass.** The impl report has `## Docs updated`: "None, because this is a
  test-only fix". That is right: no doc in `CLAUDE.md` § Docs to keep current
  describes this test. The spec-to-step map in `.claude/CLAUDE.md` § SMTW-Review
  is unchanged and still right.
- **Manual checks.** The brief has none; the impl report says "None". Correct.
- **Writing style (scope A).** The impl report leads with the result and uses
  short sentences.

## Nits

- **CR1-01** (nit) `docs/steps/README.md:343`: the step index still shows S042 as
  `Implementing (fix lane)`, while the brief's header says `In code review`. Set
  the index row to the brief's status when the step moves on.

## Manual browser checks

None. The step changes only a test.

## Checked and found consistent

- The `q=` text matches the raised description; `q` survives the State change.
- The row locator uses the unique serial, as in S036's `rowOf`.
- The brief's red command is green on all three projects (my own run).
- Scope, fix-lane limits, header blocks, `## Docs updated` and `## Manual checks`.
