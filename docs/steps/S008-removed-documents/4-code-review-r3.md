```
Step: S008 — Removed documents: list, restore, delete for good
Doc: code-review r3
Author: Code reviewer (Opus)
Date: 16-10-2026
```

# S008 — Code review, round 3

**Verdict:** no `blocker` or `major` finding is open. The four nits from fix
round 2 (CR1-03, CR1-04, CR1-05, CR2-01) are fixed, with no regression. One new
`nit` (CR3-01): the new thumbnail test is a near-copy of the main-file test.

## Test results (run by the reviewer)

- `tooling/run-tests.bat`: **green**. Backend: 680 passed in 35.8 s (679 + the
  new thumbnail test). Frontend: vitest, 6 files, 36 tests passed.
- `npx vite build` in `frontend/`: **clean**, built in 1.9 s, with no warnings
  or errors.

## Scope reviewed

- Fix round 2 touched `frontend/src/views/settings/RemovedDocuments.vue` and
  `backend/tests/test_removed_documents_api.py` (both new and untracked). Both
  were read in full.
- `documents.py` `_remove_stored_files` and the conftest fixture
  `user_with_units` were read to check the tests against them.
- No production backend file changed in this round (`git diff -w
  --ignore-cr-at-eol --stat` lists the same files as round 2).
- Not reviewed, as out of scope: the S007 working-tree files, and the
  planner's `Plan.MD` and README edits.

## Earlier findings verified

### CR1-03 (nit) — Fixed

- `act()` (`RemovedDocuments.vue:76-91`) now calls `await load(true)` after the
  `try/catch/finally`, so it reloads on both success and failure. The comment
  at `:88-89` says why.
- **The error alert survives the reload.** `actionError` is set in the `catch`
  (`:83`). `load()` (`:38-58`) touches only `loadError`, `loading`,
  `confirmingId`, `pageNumber` and `result`. It never clears `actionError` or
  `note`. So the danger alert at `:131` stays up while the stale row
  disappears. If the reload itself fails (DB down), the load-error alert with
  Retry shows as well, and the action error stays above it. Both messages are
  true, so that is the right outcome.
- **Stepping back a page after a failed action** is consistent with brief
  § 6. The brief's rule is "after an action: if the reloaded page has no items
  and `page > 1`, the card loads `page - 1`", so that the user is never
  stranded on an empty page. A 404 on a stale row means another manager
  already took that row off the list. If it was the last one on the page, the
  page is now empty for the same reason as after a successful action, and one
  step back is the same outcome. It is still one extra GET and never a loop.
  Plain loads (mount, Retry, filter, pager) still pass no argument, so "No
  removed documents on this page." can still show for an old page number. The
  coder listed this choice under "Decisions" in fix round 2, so it is
  reported.
- `busy` is still cleared in `finally` before the reload, as in round 2. The
  `confirmingId = null` in the `catch` (`:84`) is now redundant, because
  `load()` clears it too. It is harmless, so it is not a finding.

### CR1-04 (nit) — Fixed

- `test_removed_documents_api.py:142` uses `user_with_units("maint_engineer", [])`.
- That fixture (`conftest.py:270-277`) takes a fresh `uniq.username()` and
  stores an empty unit list for it through the admin API. So no other test
  can give this user a unit.
- It is a stronger test than before: the user is now known to the
  user-units table with zero units, rather than simply absent from it.
- The unused `role_client` parameter is gone from the signature.

### CR1-05 (nit) — Fixed (see CR3-01 on its form)

- The new test `test_a_thumbnail_that_cannot_be_removed_is_a_warning_not_a_204`
  (`:269-289`) **patches `file_store.remove_file`, not `os`**, through
  `monkeypatch.setattr(file_store, "remove_file", failing)`.
  `documents._remove_stored_files` calls `file_store.remove_file(path)` through
  the module attribute (`documents.py:364`), so the patch takes effect. The
  real `os.remove` is still used for the main file through `real(path)`.
- It asserts what the finding asked for:
  - 200 with `{"warning": FILE_LEFT_BEHIND}`;
  - the row is gone;
  - the other file is gone, since `folder_files == [<stored>.thumb.jpg]`;
  - an ERROR line names the thumbnail path.
- It uses a photo upload, so `has_thumb` is true and the thumbnail path is
  really attempted.

### CR2-01 (nit) — Fixed

- `RemovedDocuments.vue:190` has
  `:tabindex="item.status === 'scrapped' ? 0 : undefined"`, and `:191` has
  `:title="item.status === 'scrapped' ? '…' : undefined"`. Vue drops an
  attribute bound to `undefined`, so an active row's wrapper is neither a tab
  stop nor titled. The enabled button is the only stop there.
- On a scrapped row, the wrapper is focusable and titled, and the button is
  disabled. So a scrapped row still has exactly one stop, and the CR1-02
  tooltip is kept.
- The old active-row title "Put it back on the equipment page" is gone. The
  brief does not ask for it, and the report says so. The comment at `:187`
  was updated to match.

## Findings

### CR3-01 — nit — The two "cannot be removed" tests are near-copies

**Where:** `backend/tests/test_removed_documents_api.py:248-267` and `:269-289`.

**Problem:**
- The two tests are the same 18 lines, except for:
  - which path fails;
  - which file is expected to remain.
- CR1-05 suggested parametrizing them. They were copied instead, which goes
  against the CLAUDE-COMMON DRY rule.

**Failure scenario:** a later change to the purge contract, for example a new
field in the warning body or a renamed log message, has to be made twice. If
it is made in only one copy, the main-file and thumbnail cases drift, and one
of them stops pinning the behaviour.

**Fix:**
- Make one test with `@pytest.mark.parametrize("failing_name", ["main",
  "thumb"])`.
- Build both names, pick the failing path and the surviving name from the
  parameter, and keep the same four assertions.

This is test code only, and the cost is low. It can be fixed now, or left for
the user.

## Checked and found consistent

- **No regression in the card.** The rest of `RemovedDocuments.vue` is
  unchanged since round 2, apart from `act()` and the Restore wrapper:
  - the `text-secondary` class is on the whole row;
  - `PAGE_SIZE = 50` is sent explicitly;
  - the debounced search and the kind filter both go back to page 1;
  - the in-row confirm is as the brief describes;
  - Delete for good stays enabled on scrapped rows;
  - the success and warning notes are set before the reload and survive it;
  - the sequence guard drops stale loads, and `pageNumber` is set only after
    the guard.
- **Restore on a scrapped row** stays disabled
  (`:disabled="busy || item.status === 'scrapped'"`). The backend's 409
  remains the answer for a stale page. After CR1-03, that 409 now also
  reloads, so the row comes back greyed and disabled.
- **Backend production code** is unchanged in this round. The round-1
  "Checked and found consistent" list still holds: RBAC, unit scope, list SQL,
  restore and purge transactions, lock order, row-first deletion, and 503 on
  a commit failure. 680 backend tests are green.
- **Earlier rounds:**
  - CR1-01 (major) and CR1-02 (minor) were verified fixed in round 2. The
    code they point at is unchanged, apart from the CR2-01 attribute
    bindings, which keep the CR1-02 wrapper on scrapped rows.
  - Every finding from rounds 1 and 2 is now `Fixed`.

## Manual browser check (user)

The brief's § 9 list still applies, as in rounds 1 and 2. The points added by
this round are marked **new**.

- Scrap a node that has a removed document:
  - the whole row is grey, with "scrapped" under the code;
  - hover the disabled Restore: the tooltip "Scrapped equipment cannot be
    changed" appears;
  - **new:** press Tab through the row: focus stops once on the Restore area
    (the wrapper), then on Delete for good;
  - Delete for good still works.
- **New:** on an active row, Tab goes straight to the Restore button, with no
  invisible stop before it, and hovering Restore shows no tooltip.
- **New, failed action:**
  1. Open the card in two tabs as the manager.
  2. In tab A, delete a document for good.
  3. In tab B, click Restore on the same row.
  4. Check that the red "Not found" alert shows, the row disappears from tab
     B, and the alert is still there after the list reloads.
- Delete the only item on page 2 (needs more than 50 removed items, or a
  temporary smaller `PAGE_SIZE`): the card falls back to page 1 in one step.
- An old page number with Retry or the pager shows "No removed documents on
  this page." and does not jump back.
- The rest of the list:
  - the engineer sees no card;
  - the card is at full width;
  - newest first;
  - search `RPP` and the Photos filter;
  - restore a PDF and open it on the equipment page;
  - delete a photo for good: the confirm, No, the files gone from
    `data/equipment/<id>/`, and the INFO log line;
  - on a phone, the table scrolls sideways.
