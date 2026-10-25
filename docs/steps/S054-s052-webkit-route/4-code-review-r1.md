```
Step: S054 — S052's Meters-card failure test fails on the iPhone
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 25-10-2026
```

# S054 — code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The fix matches the brief and the advice: one `test.use({ serviceWorkers: "block" })` at file level in `tickets-work.spec.js`, and one rule line in `.claude/CLAUDE.md`. There are no `minor` findings and two nits, both about wording. The fix stays on the fix lane.

Diff reviewed: the working tree against HEAD `e08f5bb` (`git diff -w --ignore-cr-at-eol`): `frontend/e2e/tickets-work.spec.js`, `.claude/CLAUDE.md`, the README row and the S054 step files. I read the brief, the advice and the impl report in full. I also read `readings.spec.js:15-21`, `frontend/src/main.js:15-21`, the Playwright type docs of `page.route`, `browserContext.route` and `serviceWorkers`, and the coder's logs `scratch/s054-rerun.log` and `scratch/s054-full.log`.

## Tests

- **Unit suites: not run.** No backend, frontend or tooling code changed, so `run-tests.bat` would test nothing this step touched. I ran `tooling/step-check.bat` (read-only): no problem with S054 (its one problem is S049's README row, not this step).
- **Browser runs: the coder's runs are relied on, none repeated.** The logs confirm the counts in the impl report:
  - `scratch/s054-rerun.log`: the S052 test on `phone-webkit`, `--repeat-each=3`, **3 passed** (15.2 s). The red run before the fix is `scratch/s052-webkit-rerun.log`, 3 of 3 failed.
  - `scratch/s054-full.log`: the whole `tickets-work.spec.js` at `--level=full`, **90 passed** (1.4 min). This is the right run: a file-level option touches every test in the file, on every project.
- `screens.spec.js` was not run. That is correct here: no screen or API changed, only a test option.

## Nits

- **CR1-01** (nit) `frontend/e2e/tickets-work.spec.js:15`: "so none is started" can read as "no request is started". Write "so no service worker is started" (the same ambiguous words are in `readings.spec.js:20`; leave that file as it is).
- **CR1-02** (nit) `.claude/CLAUDE.md` § Browser tests, the S054 rule: add the advice's corollary in a few words, for example "a test that needs the service worker (`notifications.spec.js`) never shares a file with a `page.route`". The file-level block implies it, but the next reader may not see it.

## Checked and found consistent

- **No test in `tickets-work.spec.js` needs the service worker.** The file has no use of `navigator.serviceWorker`, push or `Notification`. The only test that needs the worker is `notifications.spec.js:251` (`navigator.serviceWorker.ready`), in another file. The app's `registerServiceWorker()` (`main.js:21`) keeps a failed registration quiet, and the full run with the console watcher passed 90 of 90, so the block adds no console error.
- **The comment and the rule are accurate.** Playwright 1.64.1's own docs say `page.route` (`types.d.ts:4443`) and `browserContext.route` (`types.d.ts:10402`) "will not intercept requests intercepted by Service Worker", and recommend `serviceWorkers: 'block'` (`types.d.ts:11720`). The rule names both `page.route` and `context.route`, which matches. "On WebKit" matches the advice's probe: Chromium routes such requests (issue 1090, since 1.24), WebKit does not. The comment points at `readings.spec.js:19-21`, and those lines carry the same reason.
- **No other spec uses a route without the option.** `grep "\.route("` in `frontend/e2e` finds only `readings.spec.js` (6 calls, the option at line 21) and `tickets-work.spec.js:661` (the option at line 16). The impl report's open point "other specs not audited" is therefore closed: there are none.
- **Fix lane.** Two code-and-doc files, test code only. No permission, interface, migration, setting, security or locking change. No app code changed. The brief's rejected option (a config-level block) was not built.
- **Scope.** Everything the brief asks for is built, nothing more. "Decisions taken: none" is true: the code and the rule match the brief's words.
- **Docs pass.** `## Docs updated` names `.claude/CLAUDE.md`, the one doc the brief lists. No migration, secret, role, Plan section or real-device check, so no other doc is due.
- **Manual checks.** The impl report has `## Manual checks` with the one check, `[auto]`, with a passing run behind it. The brief has no *On a real device* check.
- **Step files.** The brief's status `In code review` matches the README row. The impl report is in scope A.
- **Line numbers.** The brief's `tickets-work.spec.js:648` and `:664` are now `:653` and `:669`, because the fix adds 5 lines above them. That is expected, not a finding.

## Manual browser checks for the user

None. The one check is automated, and no screen changed.
