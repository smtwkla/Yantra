```
Step: S031 — Me: my open work, tickets I raised, my activity
Doc: impl-report
Author: Coder (Sonnet)
Date: 23-10-2026
```

# S031 — Implementation report

**Result:** the *Me* page is built as the brief says, with small departures of wording and test expectation (§ 4). All four suites pass (backend 2345, frontend 126, deps 42, tooling 106). The full e2e suite: 267 passed, 6 skipped, 0 failed. `me.spec.js` (6 tests per device) and `screens.spec.js` pass.

## 1. What was built

- A nav item **Me** (after *Tickets*, permission `ticket:read`) and the page `/me` with three tabs: **Open work**, **Raised by me**, **My activity**.
- `GET /api/tickets?raised=me`: a new filter on the ticket list.
- `GET /api/tickets/activity`: the timeline lines I recorded, newest first, paged.
- Migration **v26**: two indexes, no data change.
- The ticket row is now the component `TicketRow.vue`, used by the Tickets list and the two ticket tabs.

## 2. How it works

- **Raised by me**: `list_tickets` adds `(t.created_by = login OR t.reported_by_id = person)`. With no Team record, only `t.created_by = login`. It combines with all other filters by AND and keeps the list's order, paging and access rule.
- **Activity**: `list_activity` selects `ticket_events` with `created_by = actor()` on tickets that pass `_visible_condition`, ordered `created_at DESC, id DESC`. It returns the event, both times, the event's intensity, remark, plan, the person it names, and the ticket with its machine.
- **Page**: the tab, `state` and `page` are in the URL query. The default tab (`defaultMeTab`: `ticket:work` gives *Open work*, else *Raised by me*) is left out of the URL. A tab change drops `state` and `page`. *No units*, the "not in Team" text (only after a successful load), loading, error with *Retry* and the empty texts use the brief's words.
- **Activity rows**: time recorded, label, serial, intensity badge, machine, then `activityDetail(item)`. `isBackdated(item)` adds "· happened …".
- **Migration v26**: `CREATE INDEX IF NOT EXISTS` for `ix_ticket_events_created_by (created_by, created_at, id)` and `ix_tickets_created_by (created_by)`. No `_PRECONDITIONS` entry (brief § 4).

## 3. Files touched (17)

Backend
- `backend/tickets.py`: `raised` filter, `list_activity` route, docstring line.
- `backend/local_db.py`: migration v26.
- `backend/tests/test_my_tickets_api.py` (new): 17 tests.
- `backend/tests/test_migration_v26.py` (new): 3 tests.

Frontend
- `frontend/src/views/MeView.vue` (new): the page.
- `frontend/src/components/TicketRow.vue` (new): the row moved out of `TicketsView.vue`, with its `.ticket-text` style.
- `frontend/src/views/TicketsView.vue`: uses `TicketRow`; unused imports and the style removed.
- `frontend/src/utils/ticketLabels.js`: `defaultMeTab`, `activityDetail`, `isBackdated`, `REMARK_MAX`.
- `frontend/src/stores/navigation.js`: the *Me* item.
- `frontend/src/router/index.js`: route `/me`.
- `frontend/tests/navigation.test.js`, `frontend/tests/ticketLabels.test.js`: updated and new tests.
- `frontend/e2e/me.spec.js` (new), `frontend/e2e/screens.spec.js`: a `/me` row.

Docs
- `docs/steps/device-checks.md`: row 26.
- `docs/steps/S031-me-page/1-brief.md` (Status only) and `docs/steps/README.md` (index row).

## 4. Decisions taken, and departures from the brief

1. **Order of the first two activity lines (brief § 8, API and e2e).** The brief lists a technician's lines as `acknowledged`, `assigned`, `raised`. `_assign` writes the `assigned` line after the move's line, so it has the higher `id` and comes first when both share a second. The rule in § 5.2 (`created_at DESC, id DESC`) is unchanged and correct. The API test expects `assigned`, `acknowledged`, `raised`. The e2e test checks that the ticket's *Acknowledged* row is listed once and no *Raised* row is; it does not require *Acknowledged* to be the first row.
2. **Count text for one ticket on *Raised by me*.** The brief gives "`<n>` tickets"; I show "1 ticket" for one, as *Open work* does.
3. **`MeView.load()` makes no call without `ticket:read`.** A storekeeper who types `/me` mounts the page for a moment before `App.vue` redirects. The page called the API and got a 403, which the e2e console watcher flagged. One guard line avoids it. The Tickets list has the same moment; I did not touch it.
4. **A tab change uses `router.replace`**, as the Tickets filters do, so Back leaves the page rather than stepping through tabs. Back from a ticket returns to the same tab (tested).
5. `REMARK_MAX = 120` is a named constant in `ticketLabels.js`.
6. The *Raised by me* state select has the accessible name "State", as on the Tickets list.

## 5. Not done, deferred, assumed

- Nothing deferred. The brief's § 3 docs (Plan.MD, CLAUDE.md) were done by the planner and not touched.
- Production's MariaDB version is not verified for `CREATE INDEX IF NOT EXISTS` (needs 10.1 or later, brief § 4). The dev image `mariadb:11.4` runs it, and the re-run test passes.

## 6. Tests run

| Run | Result |
|---|---|
| `YANTRA_TEST_RUN=s031c1 tooling/run-tests.bat` | backend 2345 passed; frontend 126 passed; deps 42 passed; tooling 106 passed |
| `npx vite build` | built; only the known chunk-size warning |
| `tooling/run-e2e-tests.bat` (full, because the router changed) | 267 passed, 6 skipped, 0 failed (3.8 min, 6 lanes) |
| `me.spec.js` alone, desktop, 1 lane | 6 passed; then green on all three devices in the full run |
| `screens.spec.js` | passed in the full run, including `/me` for every ticket role |

### EXPLAIN (information only, brief § 4)

Run on a test database with 12 events, so the optimizer's choice reflects small data.

My activity (events, ticket and machine joined):

```
e  ref     key ix_ticket_events_created_by (key_len 402, const)  rows 1  Using where
t  eq_ref  PRIMARY
m  eq_ref  PRIMARY  Using where
```

Raised by me (`created_by OR reported_by_id`, with the access predicate):

```
t  index_merge  key ix_tickets_created_by, fk_tickets_reported_by
   Using union(ix_tickets_created_by,fk_tickets_reported_by); Using where; Using filesort
m  eq_ref  PRIMARY  Using where
```

Both new indexes are used, and the `OR` is answered by an index merge, as the brief expected.

## Manual checks

- [auto] A technician acknowledges a ticket; *Open work* lists its serial and a tap opens the ticket page — `frontend/e2e/me.spec.js`::`S031: a technician acknowledges a ticket; Open work lists it; a tap opens the ticket`
- [auto] An operator opens *Me* on *Raised by me* and sees the serial as *Raised*; after the engineer closes it as not a fault, *State: Closed* lists it as "Closed · Not a fault" — `frontend/e2e/me.spec.js`::`S031: an operator opens Me on Raised by me; a ticket closed as not a fault shows under Closed`
- [auto] The technician's *My activity* shows *Acknowledged* with the ticket's serial and not the operator's *Raised* line (the first row is *Assigned*, § 4 item 1; no count line; a nav tap on *Me* returns to *Open work*) — `frontend/e2e/me.spec.js`::`S031: My activity shows what the technician recorded, not the operator's Raised line; Back returns to it`
- [auto] IT admin (no Team record) sees the "not in Team" message and their own raise on *Raised by me* — `frontend/e2e/me.spec.js`::`S031: IT admin has no Team record: Open work says so, and the own raise shows under Raised by me`
- [auto] From *My activity*, a row opens the ticket; Back returns to *My activity* — `frontend/e2e/me.spec.js`::`S031: My activity shows what the technician recorded, not the operator's Raised line; Back returns to it`
- [auto] The storekeeper sees no *Me*, and `/me` lands on Equipment — `frontend/e2e/me.spec.js`::`S031: the storekeeper has no Me item, and /me lands on Equipment`
- [auto] The three tabs fit the width with no sideways scroll (Pixel 7, iPhone 14, desktop) — `frontend/e2e/me.spec.js`::`S031: the three tabs fit the screen width`
- [auto] `/me` opens for every ticket role, title *Me* — `frontend/e2e/screens.spec.js`::`every screen opens as <role>`
- On a real device (the brief marks it plain; the user decides at gate B whether it is important): open *Me* on a phone and switch the three tabs with a thumb (IT Admin, production on the TEST machine, a technician account, plant Wi-Fi) — row 26 of `docs/steps/device-checks.md`

## Fix rounds

### Round 1

| Finding | Answer |
|---|---|
| CR1-01 | **Fixed.** `MeView.vue`: `watch(tab, () => { page.value = null; })` replaces the reset in `chooseTab`, so any tab change drops the old rows. `me.spec.js` (activity test): on *My activity*, tap *Me*, expect the *Open work* tab and the row. Fails without the fix: the console watcher reports "console errors, Vue warnings or uncaught errors on the page". Passes with it. |
| CR1-02 | **Fixed.** `countText` returns text for *Open work* and *Raised by me* only; *My activity* shows no count line. The e2e test asserts no "n tickets" text on that tab. |
| CR1-03 | **Fixed.** The real-device line in `## Manual checks` is plain, as in the brief. The user decides at gate B whether it is important. Row 26 of `device-checks.md` carries no mark, so it is unchanged. |
| CR1-04 | **Fixed.** The e2e test asserts the first row contains *Assigned*, and *Acknowledged* is listed once. |
| CR1-05 | **Fixed.** `noUnits` is exported from `stores/equipment.js` (same expression, no new behaviour). `MeView.vue` and `TicketsView.vue` import it; their copies are removed. |
| CR1-06 | **Fixed.** `MeView` import moved after `MastersView` in `router/index.js`. |

Tests run (`YANTRA_TEST_RUN=s031c2`):

| Run | Result |
|---|---|
| `tooling/run-tests.bat` | backend 2345, frontend 126, deps 42, tooling 106: all passed |
| `npx vite build` | built; only the known chunk-size warning |
| `tooling/run-e2e-tests.bat` (full: `TicketsView.vue` and the router changed) | 267 passed, 6 skipped, 0 failed (4.1 min) |

Files touched in this round (6): `frontend/src/views/MeView.vue`, `frontend/src/views/TicketsView.vue`, `frontend/src/stores/equipment.js`, `frontend/src/router/index.js`, `frontend/e2e/me.spec.js`, this report.
