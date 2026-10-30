```
Step: S077 — One-point lessons: screens
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 30-10-2026
```

# S077 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** All 9 findings of round 1 are fixed. The fix
round brings in no new fault. One new nit is left.

Read again: the fix round's diff (`step_snapshot.py diff S077 --from-round 1`: 7 files),
`3-impl-report.md` § Fix rounds › Round 1, the context of the changed tests in
`frontend/e2e/lessons.spec.js` (the class, change and retire tests), `lessonMachines` and
`writeLessonByApi` in `frontend/e2e/support/lessons.js`, the `.lesson-photo-wait` style in
`LessonView.vue`, and the `active` handling of the PUT in `backend/procedures.py`. I did not
re-read the rest of the step.

## Test runs

| Run | Result |
|---|---|
| `YANTRA_TEST_RUN=s077cr2 tooling/run-frontend-tests.bat` | 368 passed: PASSED |
| `npx vite build` | built; only the existing chunk-size warning |

The fix round changed only `frontend/src` and `frontend/e2e`, so the frontend suite is the one due.
No backend or tooling file changed. I ran no browser test: no finding of mine needs one. The coder's
runs are recorded with real counts: the new tests alone 3 passed; targeted (`lessons`, `equipment`,
`screens`) 85 passed and 2 skipped; `screens.spec.js` on `phone-webkit` 9 passed, which is due
because `e2e/support/lessons.js` changed again. The targeted specs are the right ones: the changed
screens are the lesson page, the Lessons card on the machine page, and DocumentsCards (used on the
equipment page).

## Round 1 findings

| ID | Severity | Status | Check |
|---|---|---|---|
| CR1-01 | minor | Fixed | `photoFailed` is set only for the current `loadSeq`, cleared per photo on a reload and in `revokePhotos`. The template shows the line in place of the spinner; the image wins when it loads. New test with a 503 on the file route; red result given ("element(s) not found"). |
| CR1-02 | minor | Fixed | § 5's bullet is corrected, and both WebKit runs are recorded. |
| CR1-03 | minor | Fixed | New test of the close-only path, asserting the text, no submit button, *Close*, then the lesson's URL and heading. Red result given (an empty `@closed` handler: the URL check timed out). |
| CR1-04 | minor | Fixed | `retireLessonByApi` ends the class test. `PUT /api/procedures/<id>` accepts `active` alone (`procedures.py:368`). The change test already unticks its class lesson. The retire test now matches `Retired lessons (\d+)` and finds its own row by serial. |
| CR1-05 | minor | Fixed | `frontend/src/utils/download.js` `downloadBlobUrl`; both callers use it. See the next section. |
| CR1-06 | nit | Fixed | The `usePhotoUploads.js` header no longer says FormModal emits no close event. |
| CR1-07 | nit | Fixed | *Retired lessons (n)* has `tap-target`. |
| CR1-08 | nit | Fixed | *Retry* has `tap-target`. |
| CR1-09 | nit | Fixed | The card says "No lessons in use."; no test or source file names the old text (grep). |

## `downloadBlobUrl` and DocumentsCards

The change is behaviour-neutral for DocumentsCards. Before, `downloadPdf` made the `<a>`, then
awaited `pdfUrl(doc)`, then set `download`, appended, clicked and removed it. Now it awaits
`pdfUrl(doc)` first and passes the URL to the helper, which does the same five steps in the same
order with the same name, `${doc.title}.pdf`. When `pdfUrl` throws, the old code had made a link that
was never appended; the new code makes none. The error still goes to `actionError` in both. The blob
cache and its revoke stay in DocumentsCards; the helper revokes nothing, as its comment says. The
comment on why `download` is needed (Android saves a nameless file) moved into the helper. The lesson
page keeps its own `setTimeout` revoke.

## Nits

- **CR2-01** (nit) `frontend/e2e/lessons.spec.js:71`: the class test retires its lesson only when every assertion before it passes. Put the assertions in `try` and `retireLessonByApi(lesson)` in `finally`, so a failed run does not also leave the class lesson on every HP machine of its lane.

## Checked and found consistent

- **The residue of CR1-04:** a retired class lesson still adds a *Retired lessons (n)* footer on every
  HP machine's card for a writer (engineer or manager). The coder reported it. A reader sees nothing
  (`procedures.py:312` sends `retired` only with the edit key), and the retire test asserts the
  reader's side. The footer is one line on a card that a writer sees anyway, with *Add lesson*.
- **The two new tests:** the refused-photo test calls `expectDialogFits` on the dialog it opens and
  allows only the 400 it causes. The 503 test fulfils only the file route, so the lesson detail and
  the documents list still load. Both are untagged, which is right: they are logic tests.
- **Screen text (scope B):** "The photo could not be loaded. Reload the page." says what happened
  and what to do, in two short sentences. "No lessons in use." is true with and without retired
  lessons.
- **The failed-photo block** keeps the 8 rem height of the spinner block, so the page does not jump
  when a fetch fails.
- **Docs pass:** the round's "Docs updated: none" is right. `docs/Plan.MD` § 6 quotes neither the
  empty text nor the failure line.

## Manual browser checks still needed

- Rows 56–58 of `docs/steps/device-checks.md`: Tamil on a Samsung phone, an iPhone and a desktop;
  printing on A4 at the plant's printer; a real QR scan of the TEST machine.

## Feedback

- none
