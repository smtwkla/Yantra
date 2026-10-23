```
Step: S031 — Me: my open work, tickets I raised, my activity
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 23-10-2026
```

# S031 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** 0 blocker, 0 major, 2 minor, 4 nits.
The backend, the migration and the tests match the brief. Two small faults are on the
*Me* page: stale rows from another tab after a nav tap, and a wrong count text on *My activity*.

## Tests run

| Run | Result |
|---|---|
| `YANTRA_TEST_RUN=s031cr1 tooling/run-tests.bat` | ALL SUITES PASSED: backend 2345, frontend 126, deps 42, tooling 106 |
| `npx vite build` (frontend) | built in 3.9 s; only the known chunk-size warning |
| e2e | Not re-run. The coder's full run is green (267 passed, 6 skipped), and the orchestrator asked for a re-run only if a finding needs one. CR1-01 comes from reading the code: no existing spec takes that path, so a re-run would not show it. |

## Findings

### CR1-01 (minor) — a nav tap on *Me* from a non-default tab renders the old tab's rows

- **Where:** `frontend/src/views/MeView.vue:62-66` (`chooseTab`), `:105` (`watch(() => route.fullPath, load)`), `:176-177`.
- **Problem:** only `chooseTab` clears `page`. The bottom bar and the sidebar call
  `router.push("/me")` (`AppBottomNav.vue:22`). When the user is already on
  `/me?tab=activity`, that push changes the tab to the default but keeps the activity
  items in `page` until the new load answers. The template then gives activity items to
  `TicketRow`, which reads `ticket.unit.site_code` and `ticket.assignees.length`. Both are
  undefined on an activity item, so the render throws a `TypeError`.
- **Failure scenario:** a technician is on *My activity* and taps **Me** in the bottom bar
  to go back to *Open work*. For the time of the request, the list is blank and the console
  logs a render error. On a slow plant Wi-Fi this is a visible flash. An e2e test that takes
  this path would fail on the console watcher. The same happens to an operator (default
  *Raised by me*).
- **Fix:** clear `page` when the tab changes, whatever caused it. For example, use
  `watch(tab, () => { page.value = null; })` in place of the line in `chooseTab`, or give
  the list a `:key="tab"` together with that reset. Add an e2e step: on *My activity*, tap
  **Me**, and expect the *Open work* row.

### CR1-02 (minor) — *My activity* counts its lines as "tickets"

- **Where:** `frontend/src/views/MeView.vue:107-112` (`countText`), shown at `:151`.
- **Problem:** `countText` has a case for `open` only. Every other tab, *My activity*
  included, gets "`<n>` tickets". On *My activity*, `total` is the number of timeline
  lines, not tickets. The brief gives a count for *Open work* and *Raised by me* only
  (§ 1.3, § 1.4).
- **Failure scenario:** a technician raises and acknowledges one ticket. *My activity*
  says "3 tickets" above three lines about one ticket. This breaks scope B ("say what the
  user sees").
- **Fix:** show no count on *My activity*, as the brief does. Or show "`<n>` entries" if
  the user wants a count there.

## Nits

- **CR1-03** (nit) `docs/steps/S031-me-page/3-impl-report.md:106`: the real-device check is
  plain in the brief (§ 8 "On a real device", "Plain"), but the report marks it
  **important**. Drop the word, or ask the planner to mark it important in the brief.
- **CR1-04** (nit) `frontend/e2e/me.spec.js:88-90`: the comment says the *Assigned* line
  comes first, but no assertion pins it. Add `await expect(rows.first()).toContainText("Assigned")`.
  Then the order of departure 1 is tested in the browser as well as in the API test.
- **CR1-05** (nit) `frontend/src/views/MeView.vue:49`: `noUnits` is a copy of
  `TicketsView.vue:48`. The brief asked for the same computed, so this is acceptable. A
  `noUnits` computed exported from `stores/equipment.js` would keep the rule in one place.
- **CR1-06** (nit) `frontend/src/router/index.js:13`: the `MeView` import sits between
  `TicketDetailView` and `TicketsView`; the other imports are in alphabetical order. Move it
  after `MastersView`.

## The coder's departures (report § 4)

| # | Departure | Judgement |
|---|---|---|
| 1 | Activity order `assigned`, `acknowledged`, `raised` | Correct. `_move` writes the move's event (`tickets.py:1071`) before `_auto_assign` (`:1075`), so the `assigned` line has the higher `id`. The brief's rule (`created_at DESC, id DESC`) holds; only the brief's example list was wrong. Reported, and the API test pins it. See CR1-04 for the e2e. |
| 2 | "1 ticket" for one on *Raised by me* | Accepted. It follows scope B and matches *Open work*. |
| 3 | `ticket:read` guard in `MeView.load()` | Accepted. It is one line, it only avoids a 403 call during the redirect, and the server check is unchanged. |
| 4 | `router.replace` for tabs | Accepted. The brief asks only that Back returns to the same tab. The e2e test checks that from a ticket. It matches the Tickets filters. |
| 5, 6 | `REMARK_MAX`, the select's name "State" | Accepted. |

## Checked and found consistent

- **Brief § 1 against the code.** These are all built as the brief says:
  - the nav item (after *Tickets*, `fa-solid fa-user`, `ticket:read`), and the route `/me` with the title *Me*;
  - the three `nav-pills nav-fill` tabs in `?tab=`, with the default tab left out of the URL;
  - a tab change drops `state` and `page`; an unknown `tab` falls back to the default;
  - `defaultMeTab`, and the texts for no units, not in Team (IT admin and others) and the empty lists;
  - Loading, and the error with *Retry*, as in `TicketsView.vue`;
  - `PagerBar` with 50 a page;
  - the activity row: the recorded time, the label, the serial, the badge, the machine, the detail and "· happened";
  - the landing page stays Equipment.
- The *not in Team* text shows only after a successful load with `total === 0`. A 503 shows the error first (BR1-10).
- **`TicketRow.vue`**: the template and the style are moved without change, and `TicketsView.vue` only swaps the row and removes the unused imports.
- **Backend `raised=me`** (`tickets.py:556-564`):
  - `enum_arg` gives 400 with field `raised`;
  - `actor()` and `current_person_id(cur)` are used, and only `created_by` when the person is None;
  - it joins the other filters by AND, with the list's order, paging and access rule.
- **Backend `GET /api/tickets/activity`** (`tickets.py:600-638`):
  - `@require_perm(READ_KEY)`, and an empty answer when `_visible_condition` is None;
  - the predicate is over `t` and `m`, and both are joined;
  - the SQL is parameterised, and the f-strings join only fixed text and placeholders;
  - the order is `e.created_at DESC, e.id DESC`, and the answer has the shape of brief § 6 (`intensity` is the event's, `person` is null or `{id, name}`);
  - the route is registered before `/<int:ticket_id>`, and it could not collide anyway.
- **Security:** no identity comes from the request; both routes are gated with `ticket:read`; no new key is added, so `SITE_SCOPED` is unchanged.
- **Migration v26** (`local_db.py:732-741`):
  - it is append-only, and its two `CREATE INDEX IF NOT EXISTS` statements match brief § 4 (`id` last on the events index);
  - it has no `_PRECONDITIONS` entry, as the brief decides;
  - `test_migration_v26.py` covers a fresh database, a v25 database with rows, and a re-run.
  - Production's MariaDB version (10.1 or later) is still to verify, as the report says.
- **Pure core:** `activityDetail`, `isBackdated` and `defaultMeTab` are pure and unit-tested, and each row of § 5.3 is covered, including 120 against 121 characters. The backend has no business rule of its own, only a filter and a read.
- **API tests:** they cover the § 8 list. This includes reported-by, no Team record, a lost unit, `raised=you` → 400, state=closed, the order with the same `created_at`, another user's line being absent, the corrected note, paging, IT admin, the upper-case `created_by`, the storekeeper → 403, a bad page → 400, and the database down → 503.
- **E2e:** `me.spec.js` asserts what the user sees for each automated check of brief § 8:
  - the serial, and the tap to the ticket;
  - "Closed · Not a fault";
  - *Acknowledged* present and *Raised* absent;
  - the not-in-Team text;
  - Back to *My activity*;
  - the storekeeper redirect;
  - the tabs in the viewport, with no sideways scroll.
  - The step opens no dialog, so `expectDialogFits` does not apply.
  - `screens.spec.js` has the `/me` row.
  - The full suite was the right run, because the router changed.
- **Manual checks:** the report's `## Manual checks` has every automated check as `[auto]`
  with its test, and the device check as row 26 of `device-checks.md`.
- **Planner docs:** `Plan.MD` (module 8, § 4.6, § 6 phone line) and `.claude/CLAUDE.md`
  (`me` S031 in the spec map) match brief § 3 Docs. The README index row is set.
- **UX:** the tab buttons fill the width and are not shrunk, and there is no `btn-sm`. Long machine names and remarks wrap. The page has no fixed widths and no tables.
- **Scope:** nothing is built beyond the brief, and every departure is listed in the report.

## Manual browser check for the user

- Row 26 of `docs/steps/device-checks.md`: on a phone, open *Me* and switch the three tabs
  with a thumb (IT Admin, a technician login, production on the TEST machine).
- After CR1-01 is fixed: on *My activity*, tap **Me** in the bottom bar. The *Open work*
  list shows with no blank flash.
