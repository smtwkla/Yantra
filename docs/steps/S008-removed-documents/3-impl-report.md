Step: S008 — Removed documents: list, restore, delete for good
Doc: impl-report
Author: Coder (Sonnet)
Date: 16-10-2026
Status: n/a (the brief carries the status)

# S008 — Implementation report

## 1. What was built

- **A "Removed documents" card on the Settings page** for `equipment:purge_documents` (maintenance manager, IT admin): a paged table of removed documents and photos at the user's units, newest removal first, with a search box (equipment code, title, original file name) and an All / Documents / Photos filter.
- **Restore**: clears `removed_at` / `removed_by`; the document is back on its equipment page. Refused on scrapped equipment (409).
- **Delete for good**: deletes the row, the file and the thumbnail, after an in-row confirmation. Allowed on scrapped equipment; refused (409) for a document that is not removed. When a file cannot be deleted from the share the API answers 200 with a warning and the card shows it in warning style, so the user is never told "deleted" while bytes remain.
- **One new permission**, `equipment:purge_documents` (manager, IT admin).

## 2. How it works

- `GET /api/equipment/removed-documents` joins `equipment_documents` to its node through `equipment.NODE_JOINS` (the one fragment that resolves a node's unit), scopes by `accessible_unit_ids` (an empty set returns the empty page), filters on `kind` and `q`, and pages as `list_equipment` does. Each item carries the node's `equipment_id`, `code`, `name`, `level`, `status`, `unit` and `full_path` (`node_path`). `stored_name` and `has_thumb` are not sent.
- `POST …/restore`: one transaction; lock (1) through `_lock_node_for_change` (404 / 409); selects the removed document of that node (404 otherwise); clears the two columns; re-reads the item under the lock; INFO log line after the commit.
- `POST …/purge`: one transaction with `load_node_for_user(for_update=True)` (no scrapped check); selects the row; 404 if missing, 409 "Remove the document first" if it is active; deletes the row; commits. Then the INFO line, then each file is deleted on its own through `file_store.remove_file`: a missing file logs a WARNING, any other `OSError` logs an ERROR with the path and counts as left behind. 204 when all are gone, otherwise 200 `{warning: FILE_LEFT_BEHIND}`.
- The card (`RemovedDocuments.vue`) keeps filters in local state, sends `per_page=50`, debounces the search with `useDebounced`, shows a one-line note after an action (warning style for a purge warning), clears the in-row confirm on every reload and, after a restore or purge only, steps back one page when the reload leaves the page empty.

## 3. Files touched

Backend
- `backend/config_rbac.py`: `equipment:purge_documents`.
- `backend/api_common.py`: `int_arg`, `enum_arg`, `like_pattern`, `DEFAULT_PER_PAGE`, `MAX_PER_PAGE`, `MAX_PAGE` moved here, public, unchanged behaviour.
- `backend/equipment.py`: helpers/constants removed (imported from `api_common`); `accessible_unit_ids`, `NODE_JOINS`, `node_path` made public; docstring and comment updated.
- `backend/documents.py`: the three routes, `FILE_LEFT_BEHIND`, module docstring line.
- `backend/file_store.py`: `remove_file`.
- `backend/tests/documents_helpers.py` (new): shared document test helpers.
- `backend/tests/conftest.py`: `unit`, `node`, `at_unit` fixtures moved in.
- `backend/tests/test_removed_documents_api.py` (new): 19 tests.
- `backend/tests/test_documents_api.py`, `test_documents_core.py`: use the moved helpers (no test module is imported any more; closes S006 CR1-06).
- `backend/tests/test_equipment_api.py`: `api_common.MAX_PAGE`.
- `backend/tests/test_rbac.py`: the key in the manager and IT admin sets.

Frontend
- `frontend/src/views/settings/RemovedDocuments.vue` (new): the card.
- `frontend/src/views/SettingsView.vue`: renders it when the user holds the key.

Docs
- `docs/steps/S008-removed-documents/1-brief.md` and `docs/steps/README.md`: status `In code review`.
- `docs/steps/S008-removed-documents/3-impl-report.md`: this file.

17 files in total (13 backend incl. tests, 2 frontend, 2 step docs; plus this report). The S007 files (FormModal, dialogs, nginx.conf) were not touched.

## 4. Decisions taken

- `_image_bytes` became the public `image_bytes` in `tests/documents_helpers.py`: `test_documents_core.py` imports it, and no private name crosses a module (S006 rule). The brief named it `_image_bytes`.
- `listed(client, node)` replaced `_list`, as the brief says; one local variable in `test_documents_api.py` that was also called `listed` is now `page`.
- `_remove_stored_files` (documents.py) is a small private helper that deletes the file and the thumbnail, each attempted on its own, and logs; kept apart so `purge_document` reads as the brief's steps.
- `_removed_item` builds `unit` and `full_path` and drops the join columns (`site_code`, `unit_code`, `p_code`, `gp_code`) from the item.
- The "full_path" test asserts equality with the equipment list's `full_path` for the same node rather than a hard-coded string, so it follows `full_path()`'s format.
- A failed action (error) clears the in-row confirm and shows the alert; a successful one reloads (which also clears it).
- Icon `fa-trash-can-arrow-up` for the card header (Font Awesome Free); `router-link` (global) as elsewhere.
- No departure from the brief otherwise.

## 5. Not done, deferred, assumed

- Docs at approval (Plan § 3 matrix row, Plan § 5 `equipment_documents` row) are for the planner, as the brief says; not done here.
- Tests: `tooling/run-tests.bat` is green: 679 backend tests passed, 36 frontend (vitest) passed. `npx vite build` in `frontend/` is clean.
- **Manual browser check still needed** (no browser run by me): the brief § 9 manual list. In particular the card layout at full width, the phone table scroll, the scrapped-row greying and disabled Restore tooltip, the confirm buttons, and the page-back behaviour after deleting the last item of page 2.
- The `FILE_LEFT_BEHIND` card path (a real I/O error) is covered by the API test only; it cannot be provoked by hand without a failing share.

## Fix rounds

### Round 1

Only `frontend/src/views/settings/RemovedDocuments.vue` changed. The backend is unchanged.

- **CR1-01 (major): Accepted.** Both departures from brief § 6 are removed.
  1. The `text-secondary` class for a scrapped node is now on the whole `<tr>`, as `EquipmentView` does; it is gone from the Equipment cell.
  2. `load(afterAction = false)` no longer loops. Only `act()` (restore or purge) calls `load(true)`: if the reloaded page has no items and `page > 1`, it loads `page - 1` once (one action removes at most one item). A plain load (filter change, pager, Retry, first load) never steps back, so "No removed documents on this page." can show for an old page number, as the brief says.
- **CR1-02 (minor): Accepted.** The Restore button is wrapped in `<span class="d-inline-block" tabindex="0" :title="...">`; the title moved from the button to the span, because Bootstrap gives a disabled `.btn` no pointer events. Hover and keyboard focus now reach the span. Not checked in a browser; it stays on the user's manual list.
- **CR1-03 (nit): left for the user.** Not changed.
- **CR1-04 (nit): left for the user.** Not changed.
- **CR1-05 (nit): left for the user.** Not changed.

Tests: `tooling/run-frontend-tests.bat`: 6 files, 36 tests passed. `npx vite build` in `frontend/`: clean (built in 2.0 s). The backend suite was not re-run, since no backend file changed (last run: 679 passed).

### Round 2

Files: `frontend/src/views/settings/RemovedDocuments.vue` and `backend/tests/test_removed_documents_api.py`. No production backend code changed.

- **CR1-03 (nit): Accepted.** `act()` now reloads (`load(true)`) after a failed restore or purge as well as after a success, so a stale row (already restored or purged by another manager) disappears. `load()` does not touch `actionError`, so the error alert stays visible across the reload. The in-row confirm is still cleared on the error.
- **CR1-04 (nit): Accepted.** The no-units case uses `user_with_units("maint_engineer", [])` (a fresh `uniq` username with an empty unit list) instead of the fixed `nobody_has_units`; the now-unused `role_client` parameter was dropped from that test.
- **CR1-05 (nit): Accepted.** New test `test_a_thumbnail_that_cannot_be_removed_is_a_warning_not_a_204`: `file_store.remove_file` raises `OSError(EIO)` for the thumbnail path only and calls through for the main file. It asserts 200 with `warning == FILE_LEFT_BEHIND`, the row gone, the main file gone (only the thumbnail remains in the folder), and an ERROR log line naming the thumbnail path.
- **CR2-01 (nit): Accepted.** The Restore wrapper's `tabindex` is `0` only on scrapped rows (`undefined` otherwise). The wrapper's `title` likewise is set only when scrapped (`undefined` otherwise); the active-row title "Put it back on the equipment page" is therefore gone (departure from round 1 wording, as the reviewer's guidance asked). The comment above it was updated.

Decisions: after a failed action `load(true)` may also step back one page if the reloaded page is empty (the stale-row case); this is the same rule as after a success.

Tests: `tooling/run-tests.bat`: 680 backend passed (was 679, +1 new), 36 frontend (vitest) passed. `npx vite build` in `frontend/`: clean (built in 2.0 s). Browser check still on the user's list (tooltip on a scrapped row, tab order, failed-action reload).
