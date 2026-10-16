```
Step: S006 — Documents and photos on equipment
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 16-10-2026
```

# S006 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** There is 1 `nit`
finding.

Scope of this round:

- fix round 1 in `3-impl-report.md` § Fix rounds, checked against
  `4-code-review-r1.md`;
- `backend/documents.py` and `backend/tests/test_documents_api.py` in full,
  looking for regressions;
- the brief's § 9 rewording (CR1-02).

Diffs were read with `git diff -w --ignore-cr-at-eol`. Not part of S006 and not
reviewed: the workflow and docs edits (`.claude/**`, `docs/Plan.MD`,
`docs/steps/README.md`) and the S007 brief folder.

## Tests run

- `tooling/run-tests.bat`:
  - backend **660 passed** in 28.9 s (659 + 1 new);
  - frontend **29 passed** (5 files).
- `npx vite build` in `frontend/`: built clean, with no warnings. The fix round
  changed no frontend code; I ran the build anyway.

These numbers match the impl report.

## Earlier findings

| ID | Round-1 severity | Answer | Verified |
|---|---|---|---|
| CR1-01 | minor | Fixed | **Yes.** See below. |
| CR1-02 | minor | Rejected (no code change). The planner reworded § 9. | **Yes.** See below. |
| CR1-03 | nit | Fixed | **Yes.** See below. |
| CR1-04 | nit | Deferred (user, gate B) | Not re-raised. The fix made it no worse. |
| CR1-05 | nit | Deferred (user, gate B) | Not re-raised. Untouched. |
| CR1-06 | nit | Deferred (user, gate B) | Not re-raised. Untouched. |
| CR1-07 | nit | Deferred (user, gate B) | Not re-raised. Untouched. |
| CR1-08 | nit | Deferred (user, gate B) | Not re-raised. Untouched. |

### CR1-01: verified fixed

- **The code.** `backend/documents.py:169`: step 4 now calls
  `_lock_node_for_change(cur, node_id)`. That function:
  1. takes lock (1) through `LOCK_EQUIPMENT`, with 404 if the row is missing;
  2. re-reads the node and checks unit access (404);
  3. refuses a scrapped node from the locked row (409).

  The inline copy is gone, and the `LOCK_EQUIPMENT` import was dropped with it.
  All three writers (upload, title edit and remove) now share one locked check.
  That closes the DRY point too.
- **The read sees the move.** The access re-read inside
  `load_node_for_user` is a plain read. Under REPEATABLE READ, it would answer
  from the transaction's snapshot. That snapshot is taken at the transaction's
  first plain read. Step 4's transaction starts with the locking read, and the
  first plain read comes after it, so the snapshot is taken after the lock is
  granted. A move committed before then is seen. This is unlike
  `_load_target_node`, which needs `_reread` because plain reads came earlier.
- **Clean-up.** A 404 or 409 raised inside the `with` block reaches the step-5
  `except BaseException`. That removes both files and re-raises.
- **The new test.**
  `TestScrapped::test_moved_to_another_unit_while_uploading_leaves_no_file`
  (`backend/tests/test_documents_api.py:269-283`):
  - It runs as a unit-scoped engineer, not as the admin, so access really is
    checked.
  - The node is a root (`make_equipment(unit=unit)`), so changing its
    `unit_id` moves the whole tree's unit.
  - `db_rows` runs on its own connection, which is autocommit (`local_db.py:226`),
    so the move is committed before step 4.
  - Without the fix, the upload would answer 201. So the 404 together with the
    empty folder proves the fix.
  - The report explains why it uses plain SQL rather than a nested admin call
    (a nested call shares Flask's `g`). That reasoning is sound.
- **Decision 8** in the impl report is updated to match.
- **The brief.** § 5.6 step 4 mentions only the scrapped re-check. The added
  access re-check is what CR1-01 asked for, and it is reported in Fix rounds
  and in decision 8. It is not an unreported departure.

### CR1-02: verified resolved

- The brief's § 9 manual check now reads: "the grid and the photo viewer show
  the new title. Rename a PDF; Download saves it under the new title (photos
  have no Download button; CR1-02, reworded 16-10-2026)".
- That matches what is built, so the check can be carried out as written. This
  is option (b) of round 1.
- The impl report labels the answer `Rejected`. In effect it is option (b),
  accepted on the brief side. The README allows either label, so this is not a
  finding.

### CR1-03: verified fixed

- **Upload** (`documents.py:182`). `_item(_read_item(cur, node_id, doc_id))`
  runs after `insert_row`, on the same cursor, inside the transaction:
  - The transaction's own insert is visible to its read.
  - `created_at` comes from the DB default, so the response shows the stored
    value.
  - The node lock (1) is still held, so a remove (which also takes lock (1))
    cannot land in between.
  - `item` is returned after the `with` block, so the commit happens first.
- **Title edit** (`documents.py:256`). The item is read back after
  `update_row`, also under the lock:
  - `update_row` always sets `updated_at = NOW()`, so the row changes even when
    the title is the same.
  - The 200 for the same title still holds, because the existence `SELECT` at
    line 253 decides the 404. The test `test_saving_the_same_title_is_200`
    stays green.
- **The old failure is gone.** The post-commit `_read_item` and `_item(None)`
  path no longer exists in either route.
- **No race test.** Not adding one is reasonable. The test client cannot
  interleave two requests between a commit and a response.
  `test_title_is_changed_and_stamped` and the upload tests exercise the changed
  path, including `updated_at` and `updated_by` in the response.

## Findings

### CR2-01 — nit — The module docstring still says step 4 re-checks only the scrapped state

`backend/documents.py:7-11`

- **Problem.** The docstring says the short transaction "locks the node … ,
  re-checks scrapped from the locked row and inserts". Since CR1-01 it also
  re-checks unit access (404) from the locked state.
- **Failure scenario.** A later reader trusts the docstring. They conclude
  that upload, unlike edit and remove, does not re-check access. They might
  then "fix" a correct path, or miss the access check when they reason about
  the lock order.
- **Fix.** Reword to "re-checks access and scrapped from the locked state
  (`_lock_node_for_change`) and inserts". The comment on line 169 already says
  this.

A second trivial point, which needs no answer: `test_documents_api.py:266-268`
has two blank lines between methods inside the class (PEP 8 uses one).

## Regression check: `documents.py` and `test_documents_api.py`

- **Upload order.** The order of § 5.6 is unchanged:
  1. the plain access read and the early scrapped 409;
  2. `_read_upload`;
  3. `_write_files` with no transaction open;
  4. the short transaction;
  5. the clean-up.

  No file I/O and no Pillow work moved under the lock. Only lock (1) is taken.
- **Imports.** `LOCK_EQUIPMENT` is no longer imported. Nothing else in the
  module used it.
- **Response shape.** Upload's 201 and the title edit's 200 return the same
  shape as before. `_item` still strips `stored_name` and casts `has_thumb`.
- **Remove and serving.** Remove is unchanged: lock, then one conditional
  `UPDATE`, with `rowcount == 0` giving 404. Serving and listing are
  unchanged.
- **Existing tests.** All upload, access, scrapped, title, remove,
  failure-cleanup and serving tests still pass. The scrapped-mid-upload test
  still answers 409, so the order inside `_lock_node_for_change` (access 404
  before scrapped 409) changes nothing for a node the user can still reach.

## Checked and found consistent

- The three writers (upload, title edit and remove) refuse in the same order,
  from the locked state: 404 for a missing node or no access, then 409 for a
  scrapped node.
- Every route is still behind `require_perm` with the same keys
  (`equipment:read` / `equipment:edit`). The actor still comes only from
  `actor()`. All SQL is parameterised.
- `DBUnavailable` still becomes a 503 on every route. No exception is
  swallowed: the step-5 clean-up re-raises, and `remove_quietly` logs.
- Round 1's "Checked and found consistent" list still holds. The fix round
  touched none of those areas except the two read-backs above.
- Scope: the fix round changed only what CR1-01 and CR1-03 asked for, plus the
  brief's § 9 wording for CR1-02. There are no unreported changes.

## Manual browser checks still needed (user)

All of brief § 9, as reworded. None has been run. Round 1's list of points
needing particular attention still applies:

- **iPhone Safari, Open on a PDF.** Watch for `WebKitBlobResource error 1`.
  Also try the WhatsApp in-app browser, where Open should fall back to
  Download.
- **Android Chrome.** Open on a PDF works, and Download saves `<title>.pdf`.
- **Photos on both phones.** "Add photo" offers the camera and the gallery,
  and a portrait photo gives an upright thumbnail.
- **The photo viewer.** Previous and next. Edit title, where the title dialog
  opens with no stacked backdrop. Remove, both when it works and when it fails.
- **Rename** (the reworded check). Rename a phone photo: the grid and the
  viewer show the new title. Rename a PDF: Download saves it under the new
  title.
- **Upload refusals.** A renamed `.docx`; a file over the limit, refused in the
  dialog; a 409 after the node was scrapped in another tab.
- **Settings › Uploads.**
  - as IT admin, set 5: a 6 MB photo is refused;
  - set 100: a file just under 100 MB uploads;
  - as a manager, the value is read-only.
- **As an operator.** Documents and photos are visible, with no Add, Edit or
  Remove buttons.
- **Restart.** The files survive a backend restart.
- **After deploy (§ 6.4).**
  - the `secrets_app.py` uid-1000 check;
  - the write test on the VM;
  - one upload on production.
