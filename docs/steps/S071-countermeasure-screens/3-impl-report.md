```
Step: S071 — Countermeasures: screens
Doc: impl-report
Author: Coder (Sonnet)
Date: 30-10-2026
```

# S071 — Countermeasures: screens: implementation report

The countermeasure screens are built on S070's API, as the brief says. The improvement page has the
card *Countermeasures*; the dialogs *Add / Change countermeasure* and *Mark countermeasure done*
work; the cancel asks on the row; *Me › Open work* lists my countermeasures; Settings › Removed
documents labels a countermeasure photo. No backend file changed. All unit suites and all browser
runs are green (numbers under *Tests*). No question for the user.

## 1. What was built

- **The card *Countermeasures*** on the improvement page, full width under the two columns:
  header with "(2 of 6 done)", *Add countermeasure*, one row per countermeasure, the empty text,
  and the six kinds with their sentences under the card.
- **`CountermeasureItem`**: one row for the page and for *Me*, both answer shapes.
- **`ActionDialog`**: *Add countermeasure* / *Change countermeasure* in one `useFormModal`.
- **The inline cancel** on the row ("Why cancel it?", `Cancel countermeasure`, `Keep it`).
- **`MarkDoneDialog`**: what was done, *Done on* with the *Now* tick, photos; the done is saved
  first, the photos go after, a failed photo leaves a close-only phase.
- **`usePhotoUploads`**, taken out of `RaiseTicketView.vue`, used by the raise screen and by
  *Mark done*.
- **Photos later**: `Photos (n)` / `Add photos` opens `DocumentsCards` under the row.
  `DocumentsCards` emits `changed`.
- **Me › Open work** lists my open countermeasures above my tickets (page 1 only), each with
  *Mark done*.
- **Settings › Removed documents**: the countermeasure row, its restore refusal, the placeholder.

## 2. How it works

- **The page** holds `cancellingId`, `cancelBusy`, `cancelError` and `photosOpenId`, passes them
  down, and makes every call. A write answers with the whole detail, which replaces the page's
  copy (`onSaved`, as S068/S069). `DocumentsCards`' `changed` and the dialog's `reload` call the
  page's `load()`.
- **`CountermeasureItem`** reads `state ?? "open"`; the owner line shows when `owner` is there, the
  photos button when `documents` is there. It makes no call. One markup: a flex row that stacks
  on a phone and, from `lg` up, lays out kind and state | text and owner | due date | buttons.
  `Mark done` is full width on a phone. With `showImprovement` (Me) it adds the improvement link,
  a red row when overdue, and no change or cancel buttons.
- **`ActionDialog`**: `blank(seed = {})`; *Add* seeds `{today: new Date()}` so the due date starts
  14 days ahead; the owners come from `GET /api/improvements/owners`; on *Change*, an owner not in
  the list is listed last "(not at this site now)". `min` of the date is `problem_at`.
- **`MarkDoneDialog.save()`**: (1) `POST …/done`; (2) a refusal shows beside its field or at the
  top, a 409 with no field also emits `reload`; (3) success emits `saved(detail)` at once,
  `markClean()`, then `uploadAll()` with `saving` still true; (4) all photos up (or none): emit
  `reload` when any went up, close; (5) a photo failed: `donePhase`, close-only footer, the reason on
  each failed row, "Add photos" again (photos chosen then upload at once, `saving` true).
- **`usePhotoUploads({ path, maxMb, previews })`**: the contract of § 5.6. `add`, `remove`,
  `uploadAll` (one at a time, returns the number uploaded), `uploading`, `revokeAll`.
- **Me**: `loadActions()` runs in the same `Promise.all` as the tickets on the *Open work* tab, page 1,
  for `improvement:read` holders; the heading uses `total`. `saved` and `reload` of the dialog
  reload the tab, so the row is gone.

## 3. Files touched

Code (10):

- `frontend/src/views/ImprovementDetailView.vue`: the card, the handlers, the two dialogs.
- `frontend/src/components/CountermeasureItem.vue` (new): the row.
- `frontend/src/views/improvements/ActionDialog.vue` (new): add / change.
- `frontend/src/views/improvements/MarkDoneDialog.vue` (new): mark done with photos.
- `frontend/src/composables/usePhotoUploads.js` (new): the photo list and upload.
- `frontend/src/views/RaiseTicketView.vue`: uses `usePhotoUploads`; a `pending` row shows the spinner.
- `frontend/src/components/documents/DocumentsCards.vue`: emits `changed`.
- `frontend/src/views/MeView.vue`: the countermeasures above the tickets; the dialog.
- `frontend/src/utils/improvementLabels.js`: `ACTION_KINDS`, `actionKindLabel`,
  `ACTION_STATE_LABELS`, `overdueText`, `actionCountsText`, `defaultDueDate` and the text limits.
- `frontend/src/views/settings/RemovedDocuments.vue`: the row, the restore refusal, the placeholder.

Tests (4, the last one test support):

- `frontend/tests/improvementLabels.test.js`: 14 new cases (§ 8.2).
- `frontend/e2e/improvements.spec.js`: five S071 tests.
- `frontend/e2e/me.spec.js`: two S071 tests; file-level `test.use({ serviceWorkers: "block" })`.
- `frontend/e2e/support/improvements.js`: `ownerChoices`, `addActionByApi`, `markDoneByApi`,
  `uploadActionPhotoByApi`, `TEST_PHOTO`.

Docs (3): see *Docs updated*. No backend file changed.

## 4. Decisions taken

None departs from the brief's design.

1. **Two more events on `CountermeasureItem`: `ask-cancel` and `keep`.** The brief lists
   `cancel(reason)`; the page holds `cancellingId`, so the two taps that open and close the ask
   must reach it. The row also has a default `<slot>` where the page puts the photo cards.
2. **`MarkDoneDialog` shows a "Remove <name>" ✕ on `pending` and `failed` rows, in both phases**, so a
   failed photo can be dropped. A `done` row has none.
3. **Photo count includes documents.** `documents` in the detail holds every kind (S070); the
   button reads `Photos (n)` and the cards under the row show *Documents* too, as the ticket page does.
   S070 allows both kinds. Not changed.
4. **After a photo goes up in the close-only phase the dialog stays open** (the user taps *Close*);
   it emits `reload` once per batch, not per file.
5. **`usePhotoUploads` frees previews on unmount through `onBeforeUnmount`**, so it must be called in a
   component's setup (both callers do). It has no unit test of its own; the browser tests cover it.
6. **`defaultDueDate` takes a `Date`** (the dialog seeds `new Date()`); `undefined` gives "".
7. **`actionCountsText` returns "" when only cancelled ones exist**, so the header shows no
   "(0 of 0 done)".

### Stale brief check

I compared every name, route and line the brief cites with S070's code and S068/S069's screens.
Only line numbers moved; no field, route or file differs.

| Brief cites | In the tree |
|---|---|
| `ImprovementDetailView.vue:66-87` (S068's remove) | `:82-99` (S069 added code above) |
| `useFormModal.js:22`, `:35`, `:79-92` | same |
| `MoveDialog.vue:99`, `:151-155`, `:96-98` | `:95`, the `save()` at `:147`, the `watch(error)` at `:92-94` |
| `RaiseTicketView.vue:230-270`, `:291-293` | `:230-270` before the edit, `:291-293` |
| `improvements.spec.js:25, 58, 73, 86` | the `exact: true` locators are there; S069's (`"Add why"`, `"Edit root cause"`) use `exact: true` too |
| `MeView.vue:98`, `:122-127`, `:158-161` | same |

- **Fact:** the S070 answers match § 6: the detail's `actions[]` (`owner{id,name,active,has_login,may_own}`,
  `due_date`, `state`, `overdue_days`, `done_*`, `cancel*`, `can_change`, `can_mark_done`,
  `can_add_photo`, `documents[{id,kind,title,has_thumb}]`), `action_counts{open,done,cancelled,overdue}`,
  `problem_at`; `mine` items (`id, kind, text, due_date, overdue_days, can_mark_done, can_add_photo,
  improvement{id,serial,title,machine}`, no `state`); `owners` (`{items:[{id,name}]}`); the removed list's
  `action_kind`, `name` (the serial), `state`, `unit`.
- No difference changes the design.

## 5. Not done, deferred or assumed

- Nothing of the brief is left out. *Out of scope* is kept: no alerts, no state badge change, no
  count on the *Open work* tab, no change to `FormModal.vue` or `e2e/support/dialogs.js`.
- **Assumption (§ 9):** an operator who owns a countermeasure lands on *Raised by me* and taps *Open work*.
- **Not tested in a browser:** the HEIC note in *Mark done* and the real camera (device checks 51, 52).
  The failed-photo phase is tested with a refused file (`bad.jpg`).

## Tests

- **New tests alone** (`phone-chromium`, one lane): 7 S071 tests green (6 first, the failed-photo test
  after; it first failed on my own locator, a "Close" that matched the header ✕ too).
- **Frontend unit** (`tests/improvementLabels.test.js`): 35 passed.
- **`npx vite build`**: clean (the usual chunk-size warning).
- **Targeted browser run** (Normal; `improvements`, `me`, `tickets-raise`, `equipment`, `tickets-work`,
  `settings`, `journeys`, `screens`): 153 passed, 3 skipped, 114 s.
- **All unit suites, once** (`YANTRA_TEST_RUN=s071c1 tooling/run-tests.bat`): backend 3666 passed,
  frontend 321 passed, tooling 185 passed. All suites passed.
- **`e2e/support/improvements.js` changed**: `tooling/run-e2e-tests.bat e2e/screens.spec.js
  --project=phone-webkit`: 9 passed. (`api.js` did not change.)
- **The whole browser suite at Normal, once, at the end**: 282 passed, 13 skipped (the existing
  skips), 165 s. The failed-photo test was added before this run; nothing changed after it except docs.

## Manual checks

Automated:

- [auto] The engineer adds a countermeasure (the kind's sentence shows, default date), changes its due date, adds a second and cancels it on its row; every dialog fits — `frontend/e2e/improvements.spec.js::S071: the engineer adds a countermeasure, changes its due date, adds a second and cancels it on its row` (**important**)
- [auto] The engineer marks done a countermeasure owned by "Ramesh (operator, no phone)": "recorded by Priya (engineer)" and `Add photos` — `frontend/e2e/improvements.spec.js::S071: the engineer marks done a countermeasure owned by a person with no login; the row says who recorded it`
- [auto] A technician who is not the owner, and an operator, see the rows and the six kinds and none of the buttons — `frontend/e2e/improvements.spec.js::S071: a technician who is not the owner and an operator see the rows but none of the buttons`
- [auto] The manager removes a countermeasure photo (the button reads `Add photos`), sees "Countermeasure IM-… · Corrective" in Removed documents and restores it — `frontend/e2e/improvements.spec.js::S071: the manager removes a countermeasure photo, then restores it in Settings`
- [auto] A photo the server refuses leaves the countermeasure done and the dialog open to add it again — `frontend/e2e/improvements.spec.js::S071: a photo the server refuses leaves the countermeasure done and the dialog open to add it again`
- [auto] Kannan marks his countermeasure done from *Me* with a photo; the row leaves *Me*; the improvement page shows *Done* and `Photos (1)` with one photo; the dialog fits — `frontend/e2e/me.spec.js::S071: Kannan marks his countermeasure done from Me with a photo; the row leaves Me and the photo is on the improvement page` (**important**)
- [auto] An overdue countermeasure shows "Overdue 2 days" on a red row — `frontend/e2e/me.spec.js::S071: an overdue countermeasure shows Overdue 2 days on a red row`

Real device (rows in `docs/steps/device-checks.md`):

- [ ] **Important.** *Mark done* with the camera on an Android phone, work glove on (row 51).
- An iPhone photo in *Mark done*: HEIC refused with the note, or a JPEG saved (row 52, not important).

## Docs updated

- `docs/Plan.MD`: the *Me* module section (item 8) and the phone list say *Open work* has my
  countermeasures above the tickets (S071) and PM jobs join in phase 4 (R03.4); the *Improvements*
  bullet in § 6 describes the card *Countermeasures*, its dialogs, the inline cancel and the photos.
- `docs/steps/device-checks.md`: rows 51 and 52.
- `.claude/CLAUDE.md`: not edited; the text is below.
- `docs/schema.md`, `docs/schema.html`: none, because the step has no migration.
- `docs/Maintenance-Philosophy.md`, `docs/Plant-Facts.md`, `docs/Keycloak.md`, `example_secrets_app.py`:
  none, because no rule, role, claim or secret changed.
- `docs/steps/INDEX.md` and the brief's `Status`: `In code review`.

## Proposed CLAUDE.md changes

1. § SMTW-Review, bullet *Browser tests*, the spec map. Add `improvements` and change `me`. Replace

   > `me` S031/S064,

   with

   > `me` S031/S064/S071, `improvements` S067/S068/S069/S071,

   (S070 had no screens and no browser test of its own. If S068's docs pass already added an
   `improvements` entry, extend it with S071 instead.)

No change to *Shared code*: `usePhotoUploads.js` has two callers, both covered by the browser suites.

## Feedback

- hindrance: a bash heredoc holding an apostrophe in a test string failed with `unexpected EOF` and applied nothing, as README § Shell warns; I lost one call and wrote the chunk with the Write tool (1 call).
- waste: I started two stray interpreters (`python3 -` and `uv run python -` with an empty heredoc) in one command; they waited on stdin until the tool's 120 s timeout and I had to stop the task (2 min).
- idea: `docs/steps/README.md` § Shell could say in one line that `sed -i` on a Python edit script is fine but a heredoc is not: the Write tool for the script, `uv run --no-project python <file>` to run it.
- rule: the brief says the S071 tests use `exact: true` for `"Add photos"` and `"Add photo"`; none of my tests opens the cards beside the button with both visible in one locator scope, so the rule did not bite. A footer `Close` needs the same care: the header ✕ has the name "Close" too (one failed run).

## Fix rounds

### Round 1

Source: `4-code-review-r1.md` (2 minor, 4 nits). Runs: frontend unit suite (`s071cf1`) 321 passed;
`npx vite build` clean; `tooling/run-e2e-tests.bat e2e/improvements.spec.js e2e/me.spec.js e2e/screens.spec.js`:
44 passed, 1 skipped. No backend file, no CLAUDE.md change.

- **CR1-01 Fixed.** `ActionDialog.openChange` keeps the opened owner as `{id, name, left}` with
  `left = !owner.active || !owner.may_own`, from the detail as `CountermeasureItem` does.
  `ownerChoices` adds "(not at this site now)" only when `left`; while the list loads or fails, the
  owner shows under the plain name.
- **CR1-02 Fixed.** The refused-photo test now adds `TEST_PHOTO` in the close-only phase, expects
  the `.fa-check` on `li[data-photo="test-photo.jpg"]`, closes, and expects the row's
  `"Photos (1)"` button. Fails without the fix (the `emit("reload")` removed from `uploadChosen`):
  `expect(locator).toBeVisible()` for the `"Photos (1)"` button, element not found; passes with it.
- **CR1-03 Fixed.** `ImprovementDetailView.cancelAction` calls `load()` on a 409 with no field.
  No test added: the 409 needs a second writer between page load and tap; the reload line is the
  same one `MoveDialog` uses.
- **CR1-04 Fixed, by the reviewer's second option.** `FormModal` emits no close event, and freeing
  previews right after `modal.close()` would show broken images during the fade. The comment in
  `usePhotoUploads.js` now says `revokeAll()` runs at the next open and on unmount (as the code does).
- **CR1-05 Rejected as to the classes, named in a comment.** The wide layout resets the base flex
  rules (`flex-wrap`, `flex` bases, `margin-left`) and sets `order`, which utility classes cannot do
  in one place without repeating them on each element. The CSS comment now says 992px is
  Bootstrap's `lg` breakpoint.
- **CR1-06 Fixed.** The first S071 test expects the default due date to equal `istDay(14)`. No red
  run: the value comes from the browser's local date (`defaultDueDate`), so the fault would have to
  be put into the unit-tested helper; a wrong offset there already fails `improvementLabels` tests.

## Docs updated (Round 1)

none, because the round changes no behaviour a doc describes.

## Feedback (Round 1)

- none
