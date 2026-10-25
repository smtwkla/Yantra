```
Step: S054 — S052's Meters-card failure test fails on the iPhone
Doc: impl report
Author: Coder
Date: 25-10-2026
```

# S054 — impl report

The test now passes on all three projects. One option was added to the spec file.

## What was built

`test.use({ serviceWorkers: "block" })` at file level in `frontend/e2e/tickets-work.spec.js`, and one rule line in `.claude/CLAUDE.md` § Browser tests.

## How it works

On WebKit, a page controlled by the app's service worker (`sw.js`, S021) sends its requests past Playwright's `page.route`. The S052 test fakes the Meters card's request with `page.route`, so the fake never ran. With service workers blocked for the file, no worker controls the page and the route sees the request (as in `readings.spec.js:19-21`). The app is unchanged. The spec file uses no service worker feature, so the block affects no other test.

## Files touched (2)

- `frontend/e2e/tickets-work.spec.js`: the `test.use` line with a comment (why, and the pointer to `readings.spec.js:19-21`).
- `.claude/CLAUDE.md`: the rule, appended to the "Browser tests (S024)" bullet, in the brief's words plus "(S054)".

## Red, then green

- Red (before the fix): `scratch/s052-webkit-rerun.log`, 3 of 3 failed on `phone-webkit` (the Meters card showed the real readings, not the error text).
- Green (after the fix): `cmd //c 'scratch\s052-rerun.cmd'` (`E2E_LANES=1`, `phone-webkit`, `--repeat-each=3`, the one test): **3 passed** (15.2 s). Log: `scratch/s054-rerun.log`.
- Whole spec, because the file-level option touches every test in it: `tooling/run-e2e-tests.bat --level=full e2e/tickets-work.spec.js` (all three projects, WebKit in the container): **90 passed, 0 failed** (1.4 min). Log: `scratch/s054-full.log`.

## Docs updated

- `.claude/CLAUDE.md`: the rule line (listed in the brief).
- Others: none, because no migration, secret, role or Plan section changed and there is no real-device check.

## Decisions taken

None beyond the brief.

## Not done / deferred / assumed

- No unit suites run: no backend, frontend or tooling code changed.
- The other specs that use `page.route` were not audited for the new rule. `readings.spec.js` already follows it. Other specs were out of scope for this fix-lane step.

## Manual checks

- [auto] The S052 Meters-card failure test passes on `phone-webkit` — `frontend/e2e/tickets-work.spec.js::S052: when the Meters card cannot load it says so; Try again keeps the card in place until the answer arrives`

## Fix rounds

### Round 1 (code review r1)

- **CR1-01 (nit) — Fixed** by the orchestrator: the comment reads "so no service worker is started".
- **CR1-02 (nit) — Fixed** by the orchestrator: the CLAUDE.md rule adds "so a test that needs the service worker never shares a file with a `page.route`".
- A comment and a doc line only: no new review, no new run.
