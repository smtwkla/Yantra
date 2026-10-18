```
Step: S014 — QR labels
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 18-10-2026
```

# S014 — code review, round 2

**Verdict: no `blocker` or `major` finding open.** 1 minor; all five round-1 findings are
fixed.

## Scope of this review

- **The baseline.** Commit `c2c45d2` plus the S013 snapshot
  (`scratch/snapshot-s013-20261018-1445/`). It was rebuilt read-only in a scratch folder:
  `git archive c2c45d2`, then `tracked.patch` applied, then `untracked.tgz` extracted. That
  tree was diffed against the working tree with `diff -rw --strip-trailing-cr`. The
  snapshot itself was not touched.
- **S014 changes since round 1.** Only these files changed after round 1 (15:06):
  - `backend/settings.py`;
  - `backend/labels_core.py`;
  - `backend/tests/test_labels_api.py` and `backend/tests/test_labels_core.py`;
  - the impl report.

  Every S014 frontend file, `equipment.py`, `pyproject.toml` and `uv.lock` is as it was in
  round 1.
- **S013 changes since the snapshot (out of scope).** The snapshot was taken at 14:45,
  before S013 amendment A1 (one access-log row per sighting per day) was built. So the
  diff also shows S013-only changes in these files:
  - `access_control.py`, `network_core.py`, `local_db.py`;
  - `test_access_log_api.py`, `test_migration_v10.py`, `test_network_core.py`,
    `test_worker.py`;
  - the S013 step docs.

  None of them is an S014 file, and none touches an S014 file, so they are left to S013's
  review. In `settings.py`, every difference from the snapshot is S014's (see CR2-01).

## Test run

- `cmd //c "tooling\run-tests.bat"`, exit 0:
  - backend **1287 passed** (186 s), which includes the S013 A1 tests;
  - frontend **57 passed** in 10 files.
- `npx vite build` in `frontend/`: built clean, with no warnings.

## Round-1 findings verified

| Finding | Status | Verified |
|---|---|---|
| CR1-01 setting save copied | **Fixed** | `_save_setting(cur, key, text)` (`settings.py:69-77`) holds the `SELECT … FOR UPDATE`, the upsert and the A.8.15 log line. `put_app_settings` (`:122`), `put_labels` (`:170`) and `put_network` (`:216`) call it. `get_setting_int` reads through `get_setting_text(cur, key, None)` (`:52`). No other non-migration code writes `app_settings` (grep). |
| CR1-02 by-code with no units | **Fixed** | `test_no_units_at_all_is_the_same_404` (`test_labels_api.py:91-96`). `user_with_units("maint_engineer", [])` asks for a real code and for an unknown, well-formed code (`ZZZZ99999999`, so the lookup query runs). Both give 404 with the same body. |
| CR1-03 297 mm sheet, blank pages | **Fixed** (manual check) | The plain check "print preview of 16 labels shows exactly 2 pages; if not, 296.8mm" is in the report's `## Manual checks`. The CSS is unchanged, as proposed. |
| CR1-04 port 0 | **Fixed** | `labels_core.py:82-83` refuses `port == 0`. One message, "from 1 to 65535", serves both port errors (`:61`). `https://x.in:0` is in `test_refused` (`test_labels_core.py:52`). |
| CR1-05 double sort | **Fixed** | `children` is built from `rows` unsorted (`labels_core.py:121-124`), with a comment that `live_parts()` does the sorting. The order is still decided in one place and is still tested. |

### Is the `put_network` change behaviour-neutral? Yes.

The snapshot's `put_network` block and `_save_setting` were compared statement by
statement:

- **Transaction and locking.** The call still runs inside the same
  `with transaction(conn), conn.cursor() as cur:` block, on the same cursor. So the row
  lock taken by `SELECT … FOR UPDATE` is still held until that transaction commits, and
  `clear_networks_cache()` still runs after the commit, outside the block.
- **The SQL.** Both statements are the same text, in the same order, with the same
  parameters: `(key,)`, then `(key, text, text)`. `key` is `INTERNAL_NETWORKS_KEY` and
  `text` is the same `value` as before.
- **The log line.**
  - The format string is the same, `"Setting %s changed by %s: %s -> %s"`, at INFO, on the
    same `settings` logger.
  - The arguments are the same: the key, `actor()` (still evaluated after the upsert), the
    old value or `None`, then the new text.
  - The existing S013 test still passes. It asserts "internal_networks changed by
    test_it_admin" together with the old default ranges
    (`test_access_control_api.py:171`).
- **Errors.** An exception in either statement still propagates through `transaction()`,
  which rolls back. There is no new `try`.

The other two callers are also neutral:

- **`put_app_settings`** now passes `str(value)` to the log, where it used to pass the int.
  `%s` renders both the same way, and `test_settings_api.py:34` still asserts
  `20 -> 5`.
- **`get_setting_int`** gets `None` both for a missing row and for a NULL value, exactly
  as before.

## Findings

### CR2-01 — minor — the commit-split note does not cover the fix-round hunks

- **Where:** `3-impl-report.md`, § 3 "Files shared with uncommitted S013" (from line 144).
- **Problem:** the note lists S014's hunks in `backend/settings.py` as these:
  - `get_setting_text`;
  - the label-address block;
  - the `labels_core` import;
  - the docstring sentence.

  Round 1 added more S014 hunks to the same file, and the note was not updated:
  - the new `_save_setting`;
  - `get_setting_int` reading through `get_setting_text`;
  - `put_app_settings` calling the helper;
  - **`put_network`**, which is S013's own function, calling the helper.

  The brief says S013 is committed first (§ "Depends on").
- **Failure scenario:** the user splits the commits by the note. The `put_network` hunk
  sits inside S013's "Internal networks" section, so it goes into the S013 commit, and
  `_save_setting` (not in the list) goes into S014. The S013 commit then calls a function
  that does not exist: every `PUT /api/settings/network` raises `NameError` → 500.
  Another possibility is that `put_network` stays in its old form for S013, but then
  `get_setting_text` would also be needed earlier than the note says. A bisect or a
  release cut between the two commits gets the broken state.
- **Fix:** update the note.
  - **Simplest:** S014's hunks in `settings.py` are `get_setting_text`, `_save_setting`,
    the label block, the import and the docstring, plus the three one-line call sites
    (`get_setting_int`, `put_app_settings`, `put_network`).
  - **Alternative:** commit `put_network`'s copy unchanged with S013, then switch it to
    the helper in the S014 commit.

  Also note that the snapshot predates S013 A1. The S013 files changed since then
  (listed under Scope) are all S013's.

## Checked and found consistent

- **The settings code.**
  - `get_setting_text` returns the stored text, or the default when there is no row or
    the value is NULL.
  - `label_base_url`:
    - no row gives the default, with no warning;
    - an empty or corrupt stored text gives the default with a warning (tested).
  - `_save_setting` is called only inside a `transaction()` block, and its docstring says
    so.
  - The actor still comes from the token (`actor()`).
  - The SQL is parameterised.
- **`normalise_base_url` after CR1-04.** Port 0 is refused. A bad port (`:port`,
  `:99999`) still gives the same error message rather than raising. The 40-character
  limit and the host check are unchanged.
- **`expand_selection` after CR1-05.** It gives the same results as before: the
  order, the scrapped-part rule, the de-duplication and the cap, all pure-tested.
- **Everything else from round 1 still holds**, since none of these files changed:
  - by-code;
  - the labels endpoint (one query, the empty unit set, 404 for all, the cap after
    expansion);
  - the print layout;
  - the selection;
  - routing and sign-in;
  - the dependency.
- **Scope.** The fix round added nothing beyond the five fixes. The `put_network` switch
  is in the Fix rounds entry and is behaviour-neutral (above). There is no migration, and
  no migration was edited.
- **Manual checks.** The impl report's `## Manual checks` has all three important checks
  from the brief as unticked boxes. The plain checks include the new 2-page preview check.
- **Track.** The step is full, so there is no track mismatch.

## Manual browser checks still needed (user)

Important, unticked in the report:

- [ ] Print a sheet on the office printer at 100 %: each cut square measures 52 mm.
- [ ] Scan a printed label with an Android camera and an iPhone camera, on mobile data:
  the link opens Yantra, asks for login if needed, and shows that equipment's page.
- [ ] A crumpled or greased label still scans.

Plain:

- Tick across two pages of a unit filter, then print: all of them come out. Changing
  the filter clears the ticks, and ticking past 300 shows the hint.
- The equipment page prints a node with its parts, and a scrapped part is left out.
- A long name is cut with "…"; the code and the site are whole.
- The print preview of 16 labels shows exactly 2 pages (CR1-03).
- After a label-sheet tab is closed, an ordinary printout from Yantra keeps the
  browser's normal margins.
- Settings › Network still saves, and the change is logged (now through
  `_save_setting`).
- As IT admin on mobile data, a scanned label shows the "plant network only" card.
