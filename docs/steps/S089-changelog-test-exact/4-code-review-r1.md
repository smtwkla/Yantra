```
Step: S089 — Changelog test matches the badge exactly
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 01-11-2026
```

# S089 — code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The one-line fix does what the brief asks. One nit.

## What I checked

- **The diff** (`git diff -w --ignore-cr-at-eol 0bb67c5 -- frontend/`): one line, `frontend/e2e/changelog.spec.js:24`,
  `getByText("This version")` → `getByText("This version", { exact: true })`. No other file under `frontend/`
  or in the app changed (`git status`: only the spec, `docs/steps/INDEX.md` and the step folder).
- **Not weakened.** `exact: true` matches the whole text, case-sensitive. The only element with the text
  "This version" is the badge at `frontend/src/components/layout/ChangelogModal.vue:58`, rendered only under
  `v-if="entry.version === runningVersion"`. The line before (`:23`) still asserts a heading that starts with
  `v<VERSION> `. So the test still proves that the running version's entry is shown with its badge. The old
  substring match was weaker: with the badge missing, it could still pass on
  "No notes were written for this version." (`ChangelogModal.vue:63`), when no other section has that text.
- **The same pitfall elsewhere.** `git grep "This version"` over `frontend/e2e`, `frontend/tests` and
  `frontend/src` finds only the spec line and the badge. No other spec looks up the badge text. The unit test
  `frontend/tests/changelog.test.js` tests only `parseChangelog`.
- **Tests.** I did not re-run anything: the diff touches no app code, and no finding of mine needs a browser
  run. The coder's run is the brief's targeted command (`tooling/run-e2e-tests.bat e2e/changelog.spec.js
  --project=desktop-chromium`), with its red result (2 failed, 1 passed) and its green result (3 passed). The
  unit suites (run `s089c1`) were green: backend 4467, frontend 412, tooling 231.
- **Tags.** Both tests keep `@device`. That is right: they run only on `desktop-chromium` (the sidebar is
  hidden on phones).
- **Docs.** "Docs updated: None" is right. A test line makes no doc in `CLAUDE.md` § Docs to keep current due.
- **Scope and track.** Fix track, one test line, no app code: the change meets no full-track criterion.
  "Decisions taken: None" matches the diff.
- **Manual checks.** The brief has no real-device check. The report lists both S048 tests as `[auto]`, with a
  passing run behind them.

## Nits

- **CR1-01** (nit) `frontend/e2e/changelog.spec.js:23-24`: to tie the badge to the running version's heading
  itself, assert the badge inside that heading
  (`dialog.getByRole("heading", { name: … }).getByText("This version", { exact: true })`). Today a badge on a
  wrong entry would still pass. That weakness is older than S089, so this nit is optional.

## Checked and found consistent

The fix, the brief's cause and fix, the red and green runs, the `@device` tags, the docs pass, the scope, and
the impl report's manual checks.

## Manual browser check

None. The change is a test line only.

## Feedback

- none
