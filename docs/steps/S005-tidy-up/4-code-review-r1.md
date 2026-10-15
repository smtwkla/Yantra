```
Step: S005 — Tidy-up: page not found, leftover review nits
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 15-10-2026
```

# S005 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** I found two nits. Neither
one blocks the user's check and commit.

## Test results (run by the reviewer)

- `tooling/run-tests.bat`:
  - backend: **552 passed**;
  - frontend (vitest): **26 passed** in 4 files.
- `npx vite build` in `frontend/`: **built in 1.9 s**, with no errors and no
  warnings.

These match the counts in the report.

## Scope of the diff

`git diff` and the untracked files:

- **Backend:** `backend/equipment.py` and `backend/tests/test_equipment_api.py`.
- **Frontend:**
  - `useDebounced.js`, `router/index.js` and `stores/navigation.js`;
  - `EquipmentView.vue` and `EquipmentMoveModal.vue`;
  - `tests/navigation.test.js`;
  - the new `NotFoundView.vue`.
- **Docs:** status edits only:
  - the README index;
  - the S004 brief header (now Done, 226ce67);
  - the S005 brief header and its Gate A line;
  - the new S005 report.

No 3-impl-report.md of a Done step was touched, and that includes S002's and
S003's (brief § 1 and § 6). I found nothing beyond the brief.

## Findings

### CR1-01 — nit — `backend/equipment.py:115-119`: the `_reread` docstring describes only the in-transaction case

- **Problem.** The docstring ends: "a race the user can retry, not a server
  error". `_reread` now has a second use. After the commit, the two callers pass
  `SAVED_BUT_UNREADABLE`, and there a retry is exactly what the user must *not*
  do.
- **Why it's only a nit.** The one-line comments at `:486` and `:522` explain
  the difference, so nothing is wrong today.
- **Failure scenario.** A later reader adds a third post-commit read. They copy
  the default "try again" message because the docstring presents a retry as the
  general case.
- **Suggested fix.** Add one sentence: "After the commit, callers pass
  `SAVED_BUT_UNREADABLE`, since a retry would repeat a write that has
  already happened."

### CR1-02 — nit — `backend/tests/test_equipment_api.py:529`: "saved" is checked by count, not by identity or by event

- **Problem.** `len(_ids(admin, unit_id=unit["id"])) == 1` proves that one row
  exists in the unit. Together with the `+2` code check, that is enough for
  what the brief asks (BR2-03).
- **What's missing.** The test doesn't show that the committed transaction also
  kept its `created` event. The event is part of the same transaction, and it
  is the half that S002's rollback test checks is *absent* on update.
- **Failure scenario.** Hypothetical only: a future change moves
  `_write_events` after the post-commit read. Every assertion here would still
  pass, and the event would be lost.
- **Suggested fix (optional).**
  - Take the one id from `_ids(...)`.
  - Assert `[e[0] for e in _events(admin, {"id": that_id})] == ["created"]`, or
    the equivalent with the helper's signature.

## The coder's small choices

- **`SAVED_BUT_UNREADABLE` module constant.** Agreed. The message is used at two
  call sites and in the test, so one definition is right (DRY). The report
  lists it under "Decisions taken".
- **Icon `fa-triangle-exclamation`.** Fine. It is a Font Awesome 6 solid icon,
  which is the set the build bundles. The brief left the icon open, and the
  report names the choice.
- **Read-count assertion (`len(reads) == 2`).** Good. It is the guard that
  proves the 409 came from the **post-commit** read and not from the
  in-transaction one. If someone adds or removes a read, the test fails loudly
  instead of passing for the wrong reason.

## Checked and found consistent

### § 4.1 Catch-all route and NotFoundView

- **The route is last.** `{ path: "/:pathMatch(.*)*", name: "not-found", … }`
  is the final entry in `routes`, with a why-comment.
- **It shadows nothing:**
  - `/` redirects;
  - `/equipment`, `/masters` and `/settings` are exact;
  - `/equipment/:id(\\d+)` still wins for numeric ids;
  - `/equipment/abc` now falls through to the catch-all, as the brief intends.
- **`meta.title`** is "Page not found". `AppTopbar` shows `route.meta?.title`.
- **The path is rendered as text.** `NotFoundView.vue` uses
  `{{ route.fullPath }}`, so the query string is included. There is no
  `v-html` (ISO 27001 A.8.28). `text-break` lets a long path wrap (BR1-07).
- **The button** is a `router-link` to `landingNavItem(userPermissions).path`,
  labelled "Go to {{ label }}". `v-if="landing"` hides it when the user has no
  permissions.
- **The guards let the page through:**
  - The router guard and `App.vue`'s permission watcher both use
    `canOpenRoute`.
  - "not-found" is not a nav item, so `canOpenRoute` returns `true` for every
    role and for `[]`. This is tested.
  - Before login, `App.vue` renders nothing, as before.

### § 3 `landingNavItem` and `landingPath`

- `landingNavItem` returns `navItems.find(...) ?? null`.
- `landingPath` returns `landingNavItem(...)?.path ?? null`. Its behaviour is
  unchanged: the first visible nav item's path, or `null`. The existing
  `landingPath` tests still pass.
- The new tests cover § 5:
  - Equipment for every role, checked by identity and by label;
  - `null` for `[]`;
  - `canOpenRoute("not-found")` for every role and for `[]`.

### § 4.2 Post-commit read message

- Both post-commit `_reread` calls pass `SAVED_BUT_UNREADABLE`, the brief's
  exact text, with status 409:
  - `create_equipment`, `:487`;
  - `update_equipment`, `:523`.
- Each call has a one-line why-comment.
- The in-transaction reads keep "try again". These are `_written_state` (`:353`)
  and the parent check (`:243`), and they roll back.
- Checked against the existing rollback tests, which still assert `self.RETRY`.

### § 3 and BR1-02 / BR2-03: the new test reaches the post-commit read

The first read reaches the read hook only after `insert_row`:

- `stale_reread`'s `change` runs only once `insert_row` has run.
- The first read after that is `_written_state`'s `_reread`, inside the
  transaction. It returns the row, so the insert and the event commit.
- The second read is the post-commit `_reread`. It returns `None` and gives 409
  with the new message.

The test then shows the write was kept:

- `len(reads) == 2` pins this sequence.
- The equipment is in the unit's list.
- The class's next code is `+2`.

The test mirrors the rollback test, which asserts `[]` and `+1`.

### § 4.3 One search delay

- `SEARCH_DELAY_MS = 300` is exported once, from `useDebounced.js`, and is the
  default of `delayMs`.
- Both callers drop their local constant and call `useDebounced(fn)`. They are
  the only callers.
- A grep of `frontend/src` and `frontend/tests` for "300" finds only the
  definition. The EquipmentView comment now names `SEARCH_DELAY_MS` (BR1-06).

### § 4.4 `_lock_type` docstring

The docstring is replaced with the brief's wording, word for word.

### § 4.5 Type filter

- `typeChoices` appends the URL's type last when it isn't among the chosen
  class's types.
- The `includes` check works by object identity. That is safe because `shown`
  is filtered from the same `all` array.
- Without a `class_id`, `shown` is `all`, so the type is not listed twice.
- An unknown `type_id` finds nothing. The select stays blank (BR1-04).
- `typeLabel` gives the plain name only when `String(t.class_id) ===
  query.class_id`, and `CLS · Name` otherwise. That includes the case where
  only `type_id` is in the URL, as before. This matches BR2-02.
- Choosing a class still clears `type_id` (`classModel`, `:106`).

### CLAUDE-COMMON rules

- **No new SQL and no new routes:** permissions are unchanged.
- **No deprecated APIs.**
- **Comments say why.**
- **No exception swallowing:** the post-commit 409 is still raised through
  `ApiError`.
- **No migration:** none is needed.

## Manual browser checks for the user (brief § 5)

1. **Unknown addresses.** Open `/nope`, `/equipment/abc` and `/masters/x`.
   - Each shows "Page not found" with the full address, query string included
     (try `/nope?x=1`).
   - The topbar title reads "Page not found". The sidebar and topbar stay.
   - "Go to Equipment" goes to `/equipment`.
   - On `/equipment/abc` the Equipment nav item stays highlighted, which is
     accepted (BR1-01).
2. **A long address.** A very long path wraps and doesn't widen the page.
3. **A missing record.** `/equipment/999999` still shows "Equipment not found,
   or not at your units".
4. **Search delay.** The list's search box and the Move dialog's search both
   still wait about 300 ms after the last keystroke before searching.
5. **Type filter:**
   - `/equipment?class_id=<RPP id>&type_id=<a type of another class>` shows
     that type, last, as `CLS · Name`, and the list is empty.
   - `?type_id=999999` leaves the Type select blank.
   - Choosing a class clears the type.
