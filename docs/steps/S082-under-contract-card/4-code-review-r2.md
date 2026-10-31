```
Step: S082 — Under contract on the machine
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 31-10-2026
```

# S082 — code review, round 2

**Verdict: no blocker or major finding is open.** Both round 1 findings are fixed, and the fix round brings in no
new fault. This round has no new findings.

## Tests run

Run name `YANTRA_TEST_RUN=s082cr2`.

- `tooling/run-frontend-tests.bat`: frontend PASSED, 397 passed (6 s).
- `npx vite build` in `frontend/`: built in 4.6 s, only the known chunk-size warning.
- Backend, tooling and the schema docs check: not run. The fix round changed only `frontend/` files.
- Browser: none re-run. The coder ran the targeted specs of the change (`contracts.spec.js` and
  `screens.spec.js`, 44 passed, 1 skipped). Those are the right specs for this change. I have no finding that
  needs a run.

## Round 1 findings

| ID | Severity | Status | Checked |
|---|---|---|---|
| CR1-01 | minor | Fixed | `UnderContractCard.vue:98`: the `tel:` link now has `d-inline-block tap-target`, the same classes as *Open contract*, so `min-height: 44px` (`main.css:142`) applies. `contracts.spec.js:451` asserts the link's height is at least 44 px. The fix round records the red result without the fix (`Received: 21`). |
| CR1-02 | nit | Fixed | `contractLabels.js:149` exports `isEnded`. The card uses it for `ended` and shows the call line on `v-if="r.call"` only. This is safe because `callLine` returns `null` for an ended item (`contractLabels.js:176`), and `contractLabels.test.js:184` tests that. |

## Fix round diff

I read the whole diff of the fix round (`step_snapshot.py diff S082 --from-round 2`). It has three files:

- `frontend/src/views/equipment/UnderContractCard.vue`: the import, `ended: isEnded(item)`, the call line's `v-if`
  and the link's class. `ended` is still used elsewhere in the card, so the field is not dead.
- `frontend/src/utils/contractLabels.js`: one `export` was added. The function itself did not change.
- `frontend/e2e/contracts.spec.js`: one assertion was added. It checks geometry inside a flow test. The test's
  purpose is still the flow, so it correctly keeps no `@device` tag.

Re-read: the hunks above, `callLine` and `isEnded` in `contractLabels.js`, `.tap-target` in
`frontend/src/assets/main.css` and the `callLine` tests in `frontend/tests/contractLabels.test.js`.

## Nits

- none

## Manual browser checks

These are unchanged from round 1:

- Device-check row 59: on a phone, scan the TEST label on the dev server as a technician. Read the yellow
  "Do not repair" warning at arm's length in the shop's light (IT Admin; KLA does the set-up in the row).
- As an engineer on a phone, tap the call-out number. The phone's dialler opens with the number.

## Checked and found consistent

- The fix round's `Docs updated: none` is right. It changes no behaviour, key, schema or screen text.
- The test now asserts the link's height, so the CR1-01 fix would fail a run if someone undid it.

## Feedback

- none
