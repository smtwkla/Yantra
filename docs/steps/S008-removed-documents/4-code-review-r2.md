```
Step: S008 — Removed documents: list, restore, delete for good
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 16-10-2026
```

# S008 — Code review, round 2

**Verdict:** no `blocker` or `major` finding is open. CR1-01 and CR1-02 are
fixed. One new `nit` (CR2-01) about an extra keyboard stop.

## Test results (run by the reviewer)

- `tooling/run-tests.bat`: **green**. Backend: 679 passed in 35.2 s.
  Frontend: vitest, 6 files, 36 tests passed.
- `npx vite build` in `frontend/`: **clean**, built in 1.95 s.

## Scope reviewed

- The fix round touched only `frontend/src/views/settings/RemovedDocuments.vue`
  (new, untracked), which was read in full. It was checked against brief § 6
  and the round-1 findings.
- The backend did not change in this round. The full suite was re-run anyway.
- CR1-03, CR1-04 and CR1-05 (nits) were left for the user by the
  orchestrator. They are not re-raised: the fix round did not touch the code
  they point at.
- Not reviewed, as out of scope: the S007 working-tree files, and the
  planner's `Plan.MD` and README edits.

## Round-1 findings verified

### CR1-01 (major) — Fixed

1. **Scrapped class on the whole row.**
   - `RemovedDocuments.vue:156` puts `:class="{ 'text-secondary': item.status === 'scrapped' }"`
     on the `<tr>`. This is the same binding as `EquipmentView.vue:246`.
   - The Equipment cell (`:168`) no longer has its own class. The "scrapped"
     marker (`:171`) gets its grey from the row.
2. **The page - 1 fallback runs once, and only after an action.**
   - `load(afterAction = false)` (`:38-58`) steps back one page only when
     `afterAction === true`, the page is empty and `page > 1`. It makes one
     extra GET and does not loop.
   - Only `act()` calls `load(true)` (`:89`). It does so after a successful
     restore or purge, and not on the error path, which returns at `:85`.
   - All the other callers load without stepping back:
     - `onMounted(load)`: Vue calls the hook with no argument;
     - Retry: `load()`;
     - filter changes: `restart()`;
     - the pager: `goToPage()`.
   - The strict `=== true` also stops a stray event object from counting as
     an action.
   - So "No removed documents on this page." (`:142`) can show again for an
     old page number, as the brief says.
   - `pageNumber` is set only after the sequence check (`:50-51`), so a
     superseded load cannot move the page.

### CR1-02 (minor) — Fixed (browser check still needed)

- At `:187-199`, the Restore button is wrapped in
  `<span class="d-inline-block" tabindex="0" :title="…">`.
- When the node is scrapped, the title is "Scrapped equipment cannot be
  changed". This is Bootstrap's documented way to show a tooltip on a disabled
  button. The comment at `:186` says why.
- The button keeps `:disabled="busy || item.status === 'scrapped'"`.
- Whether the native tooltip actually appears is on the manual list below.

## Findings

### CR2-01 — nit — Every row's Restore wrapper is an extra tab stop

**Where:** `frontend/src/views/settings/RemovedDocuments.vue:189`.

**Problem:** `tabindex="0"` is on the wrapper in every row, not only on
scrapped rows. On an active row, both the span and the enabled button can take
focus.

**Failure scenario:** a keyboard user tabbing through 50 rows has to press Tab
twice to get past each Restore. The first stop is an invisible focus on a span
that does nothing on Enter.

**Fix:** make the tab stop depend on the row:
`:tabindex="item.status === 'scrapped' ? 0 : undefined"`. The title can stay on
the span in both cases.

## Checked and found consistent

- **The rest of the card against brief § 6, unchanged since round 1:**
  - the header shows the total;
  - the debounced search and the kind select both go back to page 1;
  - `PAGE_SIZE = 50` is sent explicitly;
  - the six columns are in the brief's order and content;
  - the equipment link goes to `/equipment/<equipment_id>`;
  - the in-row confirm has the brief's text and its buttons;
  - Delete for good stays enabled on scrapped rows;
  - the notes are "Restored '…'." and "Deleted '…' for good.";
  - a purge `warning` shows in `alert-warning`;
  - the action error shows in an alert;
  - buttons are disabled while an action is in flight;
  - the confirm is cleared on every load and on an action error;
  - the empty states and the load error with Retry are as specified;
  - no thumbnail, Open or Download is shown.
- **Ordering in `act()`.** `busy` is cleared in `finally` before the reload,
  and the success note is set before `load(true)`. `load` does not clear
  `note` or `actionError`, so the note survives the reload.
- **The backend** is unchanged in this round, and the round-1 "Checked and
  found consistent" list still holds. The 679 backend tests are green.

## Manual browser check (user)

This is the brief's § 9 list, as in round 1. Of particular note after this
round:

- Scrap a node that has a removed document:
  - the **whole row** is grey, with "scrapped" under the code;
  - **hover the disabled Restore: the tooltip "Scrapped equipment cannot be
    changed" appears (CR1-02)**;
  - Delete for good still works.
- Delete the only item on page 2 (needs more than 50 removed items, or a
  temporary smaller `PAGE_SIZE`): the card falls back to page 1 in one step.
- Open a page number that no longer has items, for example page 2 after
  another manager emptied it, then press Retry or change page: the card shows
  "No removed documents on this page." with the pager, and does not jump back.
- The rest of the round-1 list still applies:
  - the engineer sees no card;
  - the card is at full width;
  - newest first;
  - search for `RPP` and the Photos filter;
  - Restore a PDF, then open it on the equipment page;
  - Delete a photo for good: the confirm, No, the files gone from
    `data/equipment/<id>/`, and the INFO log line;
  - on a phone: the table scrolls sideways.
