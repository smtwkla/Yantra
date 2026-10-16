```
Step: S008 — Removed documents: list, restore, delete for good
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 16-10-2026
```

# S008 — Code review, round 1

**Verdict:** one `major` finding is open (CR1-01: two small departures from
brief § 6 in the card that the report does not list). No blocker. The backend
matches the brief closely. The fix for CR1-01 is either a few lines of template
or two lines in the report's "Decisions taken".

## Test results (run by the reviewer)

- `tooling/run-tests.bat`: **green**. Backend: 679 passed in 31.9 s.
  Frontend: vitest, 6 files, 36 tests passed.
- `npx vite build` in `frontend/`: **clean**, built in 1.9 s with no warnings
  beyond the usual output.

## Scope reviewed

- Diff read with `git diff -w --ignore-cr-at-eol`, against the committed S006
  code.
- Backend: `api_common.py`, `config_rbac.py`, `documents.py`, `equipment.py`,
  `file_store.py`.
- Tests: `conftest.py`, `documents_helpers.py` (new),
  `test_removed_documents_api.py` (new), `test_documents_api.py`,
  `test_documents_core.py`, `test_equipment_api.py`, `test_rbac.py`.
- Frontend: `views/settings/RemovedDocuments.vue` (new), `SettingsView.vue`.
- Not reviewed, as out of scope:
  - the S007 files (FormModal, the dialogs, `useFormModal.js`,
    `formSnapshot.js`, nginx.conf);
  - the planner's `Plan.MD` and README index edits for S008/S009.

## Findings

### CR1-01 — major — Unreported departures from brief § 6 in the card

There are two departures, at `frontend/src/views/settings/RemovedDocuments.vue:167`
and `:44-48`.

1. **Scrapped greying covers one cell, not the row.**
   - The brief (§ 6, Table) says "a scrapped node's **row** is
     `text-secondary` … as the equipment list marks them".
   - `EquipmentView.vue:246` puts the class on the `<tr>`.
   - The card puts `text-secondary` only on the Equipment `<td>` (`:167`). The
     Removed, Title, Uploaded and Size cells of a scrapped row stay in normal
     colour.
   - Failure scenario: the manager scans the list for scrapped equipment. Only
     the third column is grey, so the row does not read as "inactive" the way
     the equipment list's rows do.
2. **The page fallback loops, and it replaces the brief's stale-page state.**
   - The brief says: "if the reloaded page has no items and `page > 1`, the
     card loads `page - 1`". It also keeps the "No removed documents on this
     page." state for an old page number.
   - `load()` instead loops `while (items empty && total > 0 && page > 1)
     page -= 1`, on **every** load, not only after an action.
   - Effects:
     - the `:141` state "No removed documents on this page." can no longer be
       reached, because every load steps back first;
     - the loop sends one GET per page. If another manager empties several
       pages at once, a stale page 10 with `total` 1 costs nine extra
       requests, one after another.
   - The result is arguably better than the brief. But it is a choice the
     brief did not make, and it is not in the report.

The report's § 4 says "No departure from the brief otherwise". Under the review
rules, an unreported departure is at least `major`.

**Fix:**
- For (1), move `:class="{ 'text-secondary': item.status === 'scrapped' }"` to
  the `<tr>`.
- For (2), either keep the general fallback and list it in "Decisions taken",
  or do it in one step. For the one-step version:
  - jump straight to the last page with
    `Math.max(1, Math.ceil(total / per_page))` rather than looping;
  - delete the state that can no longer be reached, or record that it is gone.

### CR1-02 — minor — The disabled Restore button never shows its reason

**Where:** `frontend/src/views/settings/RemovedDocuments.vue:185-188`.

**Problem:**
- The brief asks for `title="Scrapped equipment cannot be changed"` on a
  disabled Restore, "never a silent disabled button".
- Bootstrap 5.3.8 has `.btn:disabled { pointer-events: none; }`
  (`bootstrap.css:3026-3028`). A disabled `.btn` gets no hover, so the browser
  never shows its native `title` tooltip. The pointer lands on the parent
  `<span>`, which has no title.
- The code follows the brief to the letter, but the intent is not met: the
  button is in practice a silent disabled button.
- `FormModal.vue:134-136` (S007) has the same pattern and the same gap. That
  file is outside S008.

**Failure scenario:** the manager hovers the greyed Restore on a scrapped row.
Nothing appears, and they cannot tell why it will not click.

**Fix:**
- Put the title on a wrapping element that receives pointer events:
  `<span class="d-inline-block" tabindex="0" :title="…"><button disabled …></span>`.
  This is Bootstrap's documented way to show a tooltip on a disabled button.
- Alternatively, show "scrapped — cannot be restored" as text in the actions
  cell.
- Either way, confirm it in the browser (see the manual list).
- The same gap in FormModal is worth a queued note. It is not part of this
  step.

### CR1-03 — nit — A failed action leaves the stale row in place

**Where:** `frontend/src/views/settings/RemovedDocuments.vue:81-84`.

**Problem:** on an error, `act()` shows the alert and returns without
reloading.

**Failure scenario:**
1. Two managers have the card open.
2. One deletes `IMG_2034` for good.
3. The other clicks Restore on the same row and gets 404 "Not found".
4. The row stays listed, so the second manager may try Delete for good on it
   and get a second 404.

The same happens after a 409 on a node that was scrapped since the page loaded.

**Fix:** after showing the error, also call `load()`. The alert stays, because
`load()` does not clear `actionError`.

### CR1-04 — nit — The no-units case uses a fixed username

**Where:** `backend/tests/test_removed_documents_api.py:142`.

**Problem:** `role_client("maint_engineer", "nobody_has_units")` uses a literal
username. `test_equipment_api.py`'s convention is "Unit-access tests each use a
fresh username".

**Failure scenario:** a later test that gives `nobody_has_units` a unit in the
same session (the DB is emptied only once per session) would turn this
fail-closed assertion into a false failure, or a false pass if it expects
other rows.

**Fix:** use `uniq` for the name, e.g. `role_client("maint_engineer", uniq.code("nounits"))`,
or whichever `Uniq` method gives a fresh name.

### CR1-05 — nit — "Only the thumbnail left behind" is not tested

**Where:** `backend/tests/test_removed_documents_api.py:248-267`.

**Problem:**
- Brief § 5.3 says "The thumbnail alone left → the same text".
- The test fails only the main file and calls through for the thumbnail.
- The code is symmetric (`documents.py` `_remove_stored_files` loops over both
  names), so the risk is low. But nothing pins that a thumbnail failure alone
  still gives 200 and the warning, nor that the main file is still deleted.

**Fix:** parametrize the failing path over `main` and `thumb`. For each case,
assert:
- 200 with the warning;
- the other file is gone;
- an ERROR line names the failing path.

## Checked and found consistent

- **RBAC.**
  - `equipment:purge_documents = ("maint_manager", "it_admin")` sits after
    `equipment:edit`, with a "why" comment. There is no `admin` in the tuple,
    which matches the CLAUDE-COMMON wildcard and admin rules.
  - `@require_perm("equipment:purge_documents")` is on all three routes.
  - `test_rbac.py` adds the key to exactly the manager's and IT admin's sets.
    Admin gets it through `compute_permissions` (all keys), so the card shows
    for admin too.
  - `test_who_may_list` gives 403 for engineer and operator, 200 for manager
    and IT admin.
- **Unit scope, fail-closed.**
  - The list calls `accessible_unit_ids`. An empty set returns the empty page
    before any query. Otherwise it filters with `u.id IN (%s, …)`, using
    placeholders only.
  - The fail-closed test monkeypatches the key to include `maint_engineer`. An
    engineer holding unit A does not see unit B's document, and a user with no
    units gets an empty page.
  - Restore and purge go through `load_node_for_user`, so a node outside the
    user's units is 404. That is tested for both routes.
- **List SQL.**
  - `d.*` is not used. The `d.` columns are listed one by one.
  - The node columns are aliased: `e.id AS equipment_id`, `s.code AS site_code`,
    `u.code AS unit_code`, `p.code AS p_code`, `gp.code AS gp_code`, and `e.code`
    as `code`.
  - So nothing collides on `id`, `created_*` or `updated_*`, and `node_path`
    gets the keys it expects.
  - `_removed_item` drops the four join columns. `stored_name` and `has_thumb`
    are never selected.
  - Ordering is `removed_at DESC, id DESC`.
  - `kind` goes through `enum_arg(KINDS)`; an unknown value is 400 with field
    `kind`.
  - `q` is trimmed and matched with `like_pattern` on `e.code`, `d.title` and
    `d.original_name`.
  - `page` and `per_page` go through `int_arg` with the `api_common` bounds.
  - The join is inner, through `NODE_JOINS`, as the brief says.
- **Helper move.**
  - `int_arg`, `enum_arg`, `like_pattern` and the three constants are
    byte-identical in `api_common.py`, which already imported `request`.
  - `equipment.py` now has only call-site renames. No `_int_arg`,
    `_accessible_unit_ids` or `_path` reference is left.
  - `_NODE_FROM = " FROM equipment e" + NODE_JOINS` yields the same SQL as
    before.
  - The module docstring and the unit-access comment are updated.
  - `test_equipment_api.py` reads `api_common.MAX_PAGE`.
  - No private name crosses a module.
- **Restore (§ 5.2).**
  1. One transaction. `_lock_node_for_change` takes lock (1), then gives 404
     before 409 (scrapped).
  2. The SELECT is restricted to a removed document of this node, else 404.
  3. A raw `UPDATE … SET removed_at = NULL, removed_by = NULL` leaves
     `updated_*` alone. The test checks `updated_by`/`updated_at` unchanged,
     which would also catch an `ON UPDATE` column.
  4. `_read_item` runs under the lock.
  5. The INFO line comes after the commit and names the actor, the remover and
     the removal time.
  - A second restore, an active document and another node's id each give 404.
  - Scrapped gives 409 with `SCRAPPED_MESSAGE`.
  - `/file` serves again after a restore.
- **Purge (§ 5.3).**
  1. `load_node_for_user(for_update=True)` takes lock (1), with no scrapped
     check.
  2. The SELECT gives 404 for an unknown document and 409 "Remove the document
     first" for an active one.
  3. `DELETE … WHERE id AND equipment_id`, then commit.
  4. The INFO line follows (actor, uploader, remover, `stored_name`), and only
     then the files.
  5. Each file is attempted on its own. A missing file logs a WARNING with the
     path. Any other `OSError` logs an ERROR with the path, errno and message,
     and counts as left behind.
  6. The response is 204 when every file is gone. Otherwise it is 200
     `{warning: FILE_LEFT_BEHIND}`, and the text matches the brief.
  - Because the node lock serialises purge with restore, a restore can never
    revive a row whose files are being deleted.
  - A commit failure (dead connection, DB down) raises before any log or file
    I/O. The global handler maps it to 503, and the files stay.
  - `file_store.remove_file` returns False on `FileNotFoundError` and lets other
    `OSError`s propagate, as specified.
  - The tests cover everything in brief § 9: 204 with row, file and thumbnail
    gone and the other file kept; the node list unchanged; a second purge 404;
    `/file` 404; restore after purge 404; active 409; other node 404; scrapped
    204; engineer 403; missing file 204 with a WARNING; EIO giving 200 with the
    warning and the thumbnail gone; the INFO line content. The logger is
    `documents`, captured with `caplog.set_level(…, logger="documents")`.
- **Test-DB isolation.** Every assertion on `total`, order or page filters by
  `q=<class code>`, and the searched titles and file names carry the class
  code. "Not listed" is checked by id. `per_page=1&page=2` is checked inside
  the class filter.
- **Test helper move.**
  - `documents_helpers.py` is a plain module.
  - `test_documents_api.py` no longer imports `test_documents_core`, so S006
    CR1-06 is closed.
  - `image_bytes` is public. That is reported in "Decisions taken", as is the
    `listed`/`page` rename.
  - `unit`, `node` and `at_unit` are in conftest. The `engineer` override stays
    local.
  - The renames are mechanical, and the S006 suites pass unchanged in
    substance.
- **Card.**
  - It renders below Uploads, only with the key, with no `settings-card` cap.
  - `PAGE_SIZE = 50` is sent explicitly.
  - The search is debounced with `useDebounced`, which cancels on unmount.
  - A change of filter goes back to page 1.
  - The in-row confirm is cleared at the start of every load, and on an action
    error.
  - Buttons are disabled while an action is in flight.
  - Success notes are "Restored '…'." and "Deleted '…' for good.". A purge
    `warning` shows in `alert-warning`.
  - Errors show in an alert. A load error has Retry.
  - The empty states are "No removed documents." and "… match.".
  - The table is `table-responsive` `table-sm`.
  - The equipment link goes to `/equipment/<equipment_id>`, with "scrapped"
    under the code.
  - Delete for good stays enabled on scrapped rows.
  - No file, thumbnail or download is shown.
  - `apiPost` returns `null` on 204, so `answer?.warning` takes the success
    branch.
  - A sequence guard drops stale loads.
- **Security.** Every SQL statement is parameterised; only fixed column and
  placeholder fragments are built with f-strings. The actor comes from
  `actor()`, never from the client. `stored_name` and paths never reach a
  response. The title and original name in log lines have their control
  characters stripped by `documents_core`.
- **Lock order.** documents.py still takes lock (1) only, and the
  `equipment.py` docstring is updated to "S006, S008".
- **No migration**, as the brief says.

## Manual browser check (user)

This is the brief's § 9 list. Of particular note:

- As an engineer: Settings shows no Removed documents card.
- As the manager:
  - the card is at full width;
  - removed documents are listed newest first, with the link to the equipment;
  - searching `RPP` and the Photos filter work.
- Restore a PDF: the green note shows, and the PDF is back on the equipment
  page and opens.
- Delete a photo for good:
  - the in-row confirm appears;
  - No keeps the photo;
  - Delete for good removes it, with the note;
  - `data/equipment/<id>/` has neither the file nor `.thumb.jpg`;
  - the backend log has the INFO line.
- Scrap a node that has a removed document:
  - the row is greyed with "scrapped";
  - **hover the disabled Restore: check whether a tooltip appears at all
    (CR1-02)**;
  - Delete for good still works.
- Delete the only item on page 2 (needs more than 50 removed items, or a
  temporary smaller `PAGE_SIZE`): the card falls back to page 1.
- On a phone: the table scrolls sideways, and the confirm buttons can be
  reached.
- The `FILE_LEFT_BEHIND` warning style can only be provoked with a failing
  share. The API test covers it, so it does not need a browser check.
