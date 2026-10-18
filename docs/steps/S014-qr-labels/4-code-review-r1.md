```
Step: S014 — QR labels
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 18-10-2026
```

# S014 — code review, round 1

**Verdict: no `blocker` or `major` finding open.** 1 minor, 4 nits.

## Scope of this review

The baseline is commit `c2c45d2` plus the uncommitted S013 work, rebuilt from
`scratch/snapshot-s013-20261018-1445/`:
- a temporary worktree of `c2c45d2`;
- `tracked.patch` applied;
- `untracked.tgz` extracted.

That tree was diffed against the current working tree, and the worktree was then
removed.

- **Changed against the S013 state:**
  - `backend/settings.py`, `backend/equipment.py`, `backend/pyproject.toml`, `backend/uv.lock`;
  - `frontend/src/router/index.js`;
  - `frontend/src/views/EquipmentView.vue`, `EquipmentDetailView.vue`, `SettingsView.vue`;
  - `docs/steps/README.md` (the S014 row) and the brief's Status line.
- **New:**
  - `backend/labels_core.py`;
  - `backend/tests/test_labels_core.py`, `backend/tests/test_labels_api.py`;
  - `frontend/src/utils/labelSheets.js`, `frontend/tests/labelSheets.test.js`;
  - `frontend/src/views/EquipmentByCodeView.vue`, `LabelsPrintView.vue`.
- **Unchanged since the snapshot:** every S013 file, including `conftest.py`, so the
  report's "Files shared with uncommitted S013" list is accurate.
- **Ignored:** the S022 row and the S022 brief.

## Test run

- `cmd //c "tooling\run-tests.bat"`:
  - backend **1271 passed** (169.7 s);
  - frontend **57 passed** in 10 files.
- `npx vite build` in `frontend/`: built clean, no warnings.
- `pytest tests/test_labels_core.py -W error::DeprecationWarning -W error::PendingDeprecationWarning`:
  49 passed, so the `qrcode` calls used raise no deprecation warnings.
- Checks run by hand against `labels_core`:
  - `qr_svg` output starts `<svg version="1.1" viewBox="0 0 41 41" xmlns="http://www.w3.org/2000/svg"><path d="…`.
    It is one element, with the default namespace (no `ns0:` prefix, which HTML could not
    render), no width or height, and no id. It is about 8.7 KB.
  - Versions: the longest code at the default address is version 4. At an address of
    exactly 40 characters it is version 5, as § 4 says.
  - 300 `qr_svg` calls take **2.3 s** on the dev machine. That is acceptable, though the
    report gives only the response size (§ 5).

## Findings

### CR1-01 — minor — the setting save is copied, not shared

- **Where:**
  - the block in `backend/settings.py:165-174` (`put_labels`) repeats line for line the
    loop body of `put_app_settings` (`settings.py:106-113`): `SELECT … FOR UPDATE`, then
    the `INSERT … ON DUPLICATE KEY UPDATE`, then the A.8.15 log line and its comment;
  - `get_setting_text` (`settings.py:63-68`) repeats the `SELECT setting_value …` of
    `get_setting_int` (`settings.py:49-60`).
- **Problem:** the brief asks for "the shape of `put_app_settings`". Copying the block
  breaks the CLAUDE-COMMON DRY invariant, and S013's internal-networks save is a third
  writer of `app_settings`.
- **Failure scenario:** a later change to the audit line, such as adding the client
  address or moving to an `updated_by` column, is made in one copy and missed in the
  other. Changes to the label address then leave a different, or no, audit record.
- **Fix:** add `_save_setting(cur, key, text)`, which does the locking read, the upsert
  and the log line, and returns nothing. Call it from `put_app_settings` (in its loop)
  and from `put_labels`. Let `get_setting_int` read through `get_setting_text(cur, key,
  None)`. This is a small refactor inside the same file, so no behaviour changes.

### CR1-02 — nit — `by-code` with an empty unit set is not tested

- **Where:** `backend/tests/test_labels_api.py:84-92`.
- **Problem:** `TestByCode` covers a user whose units do not include the node. It does
  not cover a user with no accessible unit at all, the BR2-01 case. That case is tested
  for `/labels` only (`:182`).
- **Failure scenario:** the code is correct today: `_can_access` checks
  `unit_id in set()`, and no `IN ()` is built. But a later change of `by-code` to a single
  joined query with `u.id IN (…)` could reintroduce the SQL error, and no test would catch
  it.
- **Fix:** add `user_with_units("maint_engineer", [])`, then `GET by-code/<code>` → 404,
  with the same body as for an unknown code.

### CR1-03 — nit — a sheet of exactly 297 mm risks blank pages in print

- **Where:** `frontend/src/views/LabelsPrintView.vue:185-197`.
- **Problem:** each `.sheet` is exactly `297mm` high with `break-after: page`, on a
  page with `margin: 0`. Chromium rounds 297 mm to device pixels (1122.5 px at 96 dpi).
  When the rounded block is a fraction taller than the page, the overflow becomes an
  empty page after each sheet. The brief prescribes `height: 297mm`, so this is not a
  departure, but the risk is not covered by the manual checks.
- **Failure scenario:** 16 labels print as 4 pages (sheet, blank, sheet, blank) instead
  of 2. The ruler check still passes, so nobody notices until paper is wasted.
- **Fix:** add a plain manual check: "the print preview of 16 labels shows exactly 2
  pages". If it fails, set the sheet height a hair under the page (`296.8mm`). The cells
  are positioned from the top, so the pitch does not change.

### CR1-04 — nit — port 0 is accepted

- **Where:** `backend/labels_core.py:77-81`.
- **Problem:** `https://x.in:0` normalises to `https://x.in:0`, and the error message
  says "from 0 to 65535". Port 0 cannot be reached.
- **Failure scenario:** a typo saves a label address that no phone can open. Every
  label printed with it is waste.
- **Fix:** refuse `port == 0`, and say "from 1 to 65535". Add `https://x.in:0` to
  `test_refused`.

### CR1-05 — nit — `expand_selection` sorts twice

- **Where:** `backend/labels_core.py:119`.
- **Problem:** `children` is built from `sorted(rows, …)`, and `live_parts` sorts its
  result by code again. Only the second sort matters: level two is collected across
  several parents and has to be re-sorted anyway.
- **Failure scenario:** none at run time. A reader has to work out which sort decides
  the order.
- **Fix:** build `children` from `rows` unsorted, or drop the sort in `live_parts` and
  say why the first one is enough. The first option is simpler.

## The report's decisions

All are reported in § 4 and none changes the brief's design:

1. **`@page` injected only while the view is mounted.** This is justified. A bundled
   `@page { margin: 0 }` would strip the margins from every other printout. The rule is
   added in `onMounted` and removed in `onUnmounted`. The view opens in its own tab, so
   the rule never leaks into another page.
2. **The library's `id="qr-path"` is stripped.** This is correct: up to 300 repeated
   ids would be invalid HTML. The test asserts that no `id=` is left.
3. **Extra helpers** (`parse_code`, public `make_qr`, `labelsPath`, `TOO_MANY_LABELS`).
   They are small and each serves a test or removes a duplicate. Acceptable.
4. **Host check.** It is stricter than the brief: letters, digits, dots and hyphens;
   IPv6 refused. This closes the "spaces or `<>`" gap that `urlsplit` alone leaves. My
   probes found:
   - `https://%41.com` and `https://a b.com` are refused;
   - upper-case schemes and hosts are lowered;
   - `:080` becomes `:80`;
   - a `\n` typed inside the host is silently removed by `urlsplit`, which is harmless
     because the URL is rebuilt from its parts.

   Only port 0 slips through (CR1-04).
5. **Error messages.** Fine.
6. **Selection order.**
   - Ticks are sent in tick order, and "select all" in page order. The Set keeps
     insertion order and the server keeps the order sent (tested).
   - Select-all is refused as a whole above 300.
   - The selection clears on any query key except `page`.

   All of this matches the brief.
7. **"With its parts" greyed out without children.** `node.children` includes scrapped
   parts (`_children`), so a node whose parts are all scrapped still offers the option
   and prints only itself. This is harmless and consistent with "scrapped parts left
   out".
8. **`/e/` route pattern.** Matches § 4. Anything else falls to the catch-all
   not-found route.
9. **Monkeypatched cap.** `expand_selection` reads the module global, so the patch
   takes effect. The request validator imported the constant by name, but one id is far
   under it in any case. Sound.

## Checked and found consistent

- **The by-code rule:**
  - `parse_code` limits the length to 12, upper-cases the code and requires `CODE_RE`;
    otherwise it answers 404 with no query;
  - an unknown code, and a node outside the user's units, raise the same
    `ApiError("Not found", 404)` through `load_node_for_user`; the test compares the
    bodies;
  - `@require_perm("equipment:read")` comes first;
  - a scrapped node resolves.
- **The labels endpoint:**
  - `@require_perm("equipment:read")`;
  - the body validator: non-empty, distinct, positive, JSON integers only (booleans,
    floats and strings refused), at most 300; `with_parts` strictly boolean, default
    false;
  - an empty `accessible_unit_ids` → 404 before any labels query;
  - **one** parameterised query through `NODE_JOINS`. Parts reach their root unit
    through `COALESCE(gp.unit_id, p.unit_id, e.unit_id)`, so the unit filter applies to
    them too;
  - a missing selected id → one 404 naming none;
  - the cap is applied again after expansion;
  - `site_code` comes from the current site;
  - no SQL text is built from input, only from `%s` placeholders;
  - the request takes no locks and writes nothing. `DBUnavailable` → 503 and the
    reconnect of a dead connection come from the shared `get_db()`.
- **`expand_selection`:**
  - the order: selected nodes, then level one by code, then level two by code;
  - scrapped parts, and anything under them, are left out;
  - a selected scrapped node is printed;
  - the de-duplication keeps the first occurrence;
  - the result is capped.
- **`normalise_base_url`:**
  - `?` and `#` are refused before `urlsplit`;
  - the scheme must be `http` or `https`; user-info is refused;
  - the path may only be empty or `/`;
  - a bad port gives an error rather than an exception;
  - the 40-character limit is applied after normalisation.

  `label_base_url` falls back to the default, with a warning, on a corrupt stored value.
- **The settings routes:**
  - `GET /api/settings/labels` requires `settings:read`, and `PUT` requires
    `settings:edit`;
  - the actor comes from the token (`actor()`);
  - the save runs in a transaction;
  - there is no migration, and none of the existing migrations was touched.
- **`v-html` safety.** The SVG holds only numeric path data generated by the library.
  The URL text is not inside it. The code, site and name are text bindings.
  `EquipmentByCodeView` shows the route parameter through an interpolation.
- **The print layout:**
  - the sheet is 210 × 297 mm, border-box, with padding of 18.5 mm top and bottom and
    27 mm at the sides;
  - the grid is 3 × 52 mm, with rows of 52 mm, so 156 + 54 = 210 and 260 + 37 = 297;
  - `break-after: page`, with `auto` on the last sheet;
  - `overflow: hidden`;
  - each cell is a 52 mm border-box with a 0.2 mm `#bbb` border, so the pitch stays 52 mm;
  - the QR box is 38 mm, which gives 0.93 mm per module at version 4;
  - the vertical budget is about 48 mm of the 51.6 mm inside the border;
  - a 12-character bold code at 4.2 mm fits in the 47.6 mm content width;
  - the site code and the name are cut with ellipsis;
  - the note and the button are `.no-print`;
  - the app shell's print reset in `main.css` removes the sidebar margin and the content
    padding, and the top bar, bottom navigation and update toast are `.no-print`.
- **The selection:**
  - a reactive `Set` in a ref;
  - a refused tick resets the DOM checkbox and shows the hint;
  - the select-all state is computed from the page's ids;
  - the selection clears on `filterKey`, which is every query key except `page`;
  - "Print labels" opens a new tab through `router.resolve`, so the ticks survive.
- **Sign-in and routing:**
  - `/e/:code` and `/labels` are not public;
  - keycloak-js `login-required` with its default `redirectUri` returns to the scanned
    link;
  - `router.replace` avoids a Back-button loop;
  - Nginx `try_files … /index.html` serves both SPA routes;
  - a 404 renders `NotFoundView`, and any other error shows Retry.
- **The dependency:** `qrcode>=8.2` was added with `uv add`. `uv.lock` adds only
  `qrcode 8.2`, which depends on `colorama` on Windows only. There is no Pillow.
- **Scope:**
  - everything in brief §§ 1, 3 and 5 is built;
  - nothing beyond it, apart from the reported helpers;
  - every departure is in "Decisions taken".

  The brief's § Tests list is covered:
  - by-code, labels, setting and pure tests, including the "before and after expansion"
    caps;
  - the empty unit set;
  - the every-unit roles;
  - the corrupt stored value;
  - the cleanup fixture;
  - vitest for `parseLabelQuery`, `chunkSheets` and `labelsPath`.
- **Manual checks:** the impl report has `## Manual checks`, with all three of the
  brief's important checks as unticked boxes and the plain checks listed.
- **Track:** the step is full, so no track mismatch.

## Manual browser checks still needed (user)

Important, from the brief, unticked in the report:

- [ ] Print a sheet on the office printer at 100 %: each cut square measures 52 mm.
- [ ] Scan a printed label with an Android camera and an iPhone camera, on mobile data:
  the link opens Yantra, asks for login if needed, and shows that equipment's page.
- [ ] A crumpled or greased label still scans.

Plain:

- Tick across two pages of a unit filter, then print: all of them come out. Changing
  the filter clears the ticks. Ticking past 300 shows the hint.
- The equipment page prints a node with its parts, and a scrapped part is left out.
- A long name is cut with "…"; the code and the site are whole.
- The print preview of 16 labels shows exactly 2 pages (CR1-03).
- After a label sheet tab is closed, an ordinary page printed from Yantra keeps the
  browser's normal margins (decision 1).
- As IT admin on mobile data, a scanned label shows the "plant network only" card.
