```
Step: S039 — Meter reading entry
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 24-10-2026
```

# S039 — code review, round 1

**Verdict: no `blocker` or `major` finding is open.** There are 4 minor findings and 4 nits. The rules, locks, permissions and API match the approved brief. All four suites and the targeted browser specs pass.

Scope: the working tree against the snapshot `refs/steps/S043` (efb43f3). The untracked files the snapshot lacks were compared one by one with their snapshot copy.

## Tests run

| Run | Result |
|---|---|
| `YANTRA_TEST_RUN=s039cr1 tooling/run-tests.bat` | backend PASSED 2948 (154 s), frontend PASSED 157, deps PASSED 42, tooling PASSED 115 |
| `npx vite build` (`frontend/`) | built in 4.45 s, the usual chunk-size warning only |
| `tooling/run-e2e-tests.bat e2e/readings.spec.js e2e/equipment.spec.js e2e/screens.spec.js` | **108 passed** (4.8 min, 6 lanes, three projects) |

- **Why these specs.** `readings` and `equipment` are the screens the step changed. `screens` is required every time. I did not run the full suite. The coder ran it because of `e2e/support/` and the `ApiError` shape. The new `e2e/support/meters.js` is imported only by `readings.spec.js` and `equipment.spec.js`, and both ran. The `ApiError` change adds `code` only when it is set, and `api.js` did not change.
- **The coder's one red test is a flake.** It is `tickets-raise.spec.js:141` on phone-webkit: a timeout in `scrollIntoViewIfNeeded` ("waiting for element to be stable"). Four facts support this:
  - The raise screen and its components are not in the diff.
  - `api.js` did not change.
  - The test passed when run alone.
  - The failure is a WebKit stability wait under a 6-lane load, not an assertion.

  I did not re-run it: no finding depends on it.

## Findings

### CR1-01 (minor) — the e2e expectation recomputes the reading's minute, so a minute tick breaks it

- **Where:** `frontend/e2e/equipment.spec.js` (S039 test "the Meters card shows the last reading…"). It posts `taken_at: istLocal(30)`, then expects `shownTime(istLocal(30))` after `asPerson` loads the page. `readings.spec.js` has the same pattern with a narrower window: `const earlier = istLocal(60)` (and `typed = istLocal(30)`) is computed, then `logByApi(…, 60)` calls `istLocal` again.
- **Problem:** `istLocal` reads the clock on every call. Between the POST and the expectation, the test loads a page, which takes a few seconds.
- **Failure scenario:** The POST runs at 18:29:58 and stores 17:59. The page loads, and the expectation runs at 18:30:01 and expects 18:00. `toHaveAccessibleName` fails. With three projects per run, this happens on a few percent of runs. It is the class of flake that S041 and S042 were opened to remove.
- **Fix:**
  1. Compute the time once (`const at = istLocal(30)`).
  2. Send it, and expect `shownTime(at)`.
  3. In `readings.spec.js`, let `logByApi` take the `taken_at` string (or return the time it used), so `earlier` and `typed` are the times sent.

### CR1-02 (minor) — the reading POST set-up is written twice

- **Where:** `frontend/e2e/equipment.spec.js` (the S039 test's inline `apiAs("operator")` block) and `frontend/e2e/readings.spec.js` `logByApi`.
- **Problem:** Both blocks do the same work. They look up the meter type by name in `/api/masters/meter-types`, POST to `/readings`, and expect 201. This is a near-copy (DRY).
- **Failure scenario:** S040 changes the reading body or the set-up user. One copy gets the change and the other does not, and that spec breaks.
- **Fix:** Move `logByApi` to `e2e/support/meters.js` beside `meterMachine` (the brief already put the meters set-up there, BS1-03). Import it in both specs. Fix CR1-01 in the same change.

### CR1-03 (minor) — the operator's tap targets on the Meters card are small

- **Where:** `frontend/src/views/equipment/MetersCard.vue`:
  - *Log reading* is `btn btn-sm btn-outline-primary`.
  - The last-reading line, the only way into *History*, is `btn btn-link btn-sm p-0`.
- **Problem:** The UX checklist says not to shrink tap targets on floor screens (`btn-sm`). *Log reading* is the operator's main action on this card. On the same page, *Raise ticket* is a full-size button. The last-reading line has no padding, so it is about 21 px high (small text). The brief's Yes / No buttons get 48 px for the same reason.
- **Failure scenario:** An operator with gloves taps between two meters' rows and hits the wrong meter's *Log reading*. Or the operator misses the last-reading line and does not find *History*.
- **Fix:**
  - Drop `btn-sm` from *Log reading*, or give it `min-height: 44px`.
  - Give the last-reading line vertical padding (`py-2`) and normal text size.
  - The engineer-only buttons (*Set limits*, *Remove*) may stay small.
  - Device-check row 32 can name the card's buttons too.

### CR1-04 (minor) — `docs/schema.md` still says readings come later

- **Where:** `docs/schema.md:43`, the `meter_types` row ends "Readings (S039) come later".
- **Problem:** The step builds readings. This sentence is now wrong, and the docs pass left it as it was.
- **Failure scenario:** A reader of the schema doc, or the next planner, takes readings as not built. A `/smtw-review` of the docs then flags it.
- **Fix:** Replace the sentence with "Readings are in `meter_readings` (S039, v32)". The `meter_readings` row itself, the Mermaid overview and `schema.html` (v32, 37 tables, 53 links) are correct.

## Nits

- **CR1-05** (nit) `frontend/src/views/equipment/ReadingFormModal.vue:64`: a 502 or 504 from Nginx while the backend restarts shows "HTTP 502". Treat 502–504 like 503 ("Not saved. Try again in a minute."), which is the true wording for them too.
- **CR1-06** (nit) `frontend/src/utils/meterLabels.js` `savedMessage`: the limit in "Saved. Above the limit of 60 °C." comes from the card's list, loaded before the save, while `limit_state` was judged on the server's limits at saving. After an engineer changes the limits in between, the message can name the old limit. Name the limit from a reloaded meter, or accept this and say so in the comment.
- **CR1-07** (nit) `frontend/src/views/equipment/ReadingHistoryModal.vue:18`: `PER_PAGE = 30` repeats the server's `HISTORY_PER_PAGE`. Leave out `per_page` and use the server's default, or note the pairing in the comment.
- **CR1-08** (nit) `backend/meters_core.py` `counter_error`: the rule is as briefed. A back-dated reset placed before an existing later reset is not checked against it, because "unless that one is a reset" skips the check. Removing the reading before a reset is not checked against it either. Either way, a reset can end up higher than the reading before it. This does no harm today. Record it for the phase 5 usage sums (a usage total across two resets), not for this step.

## Checked and found consistent

- **Migration v32** (`local_db.py`) is exactly the brief's § 4 table. It has no `_PRECONDITIONS` entry (a new table) and is append-only. `test_migration_v32.py` covers four cases:
  - a fresh database (columns, ENUMs, the FKs and the index);
  - the FK and ENUM refusals;
  - a v31 database with equipment and meters that keeps every row and every old column;
  - a re-run that changes nothing.
- **Locks** (`meters.log_reading`, `remove_reading`):
  - `_lock_node(cur, node_id, key)` runs `LOCK_EQUIPMENT … FOR UPDATE` as the first statement after `conn.begin()`.
  - The first plain read (`_read_node`) comes after that statement, so the snapshot starts after the lock.
  - The in-force check (`_meters_of`), the same-minute count and both neighbour reads are plain. There is no locking range read.
  - The concurrency test holds the node lock on a second connection and checks two things: the API waits on the lock, then sees the first writer's row (`counter_lower`).
  - The LOCK ORDER docstring in `equipment.py` and the *Locks* paragraph in `meters.py` gained the reading line.
- **Counter rules:**
  - `counter_error` checks both neighbours (nearest active before and after, ordered `taken_at`, `id`).
  - Equal values pass.
  - A reset equal to the one before passes, and a higher one is refused on `is_reset`.
  - A later reset does not bound the value.
  - `code: "counter_lower"` is sent only on the "Lower than …" refusal.
  - Removed readings are left out of every rule (`_ACTIVE`).
  - The same-minute check counts only active rows, so a removed reading's minute is free again (tested).
- **The time window.** `parse_taken_at` keeps a time to its minute and refuses more than 5 minutes ahead (`FUTURE_SKEW`). It refuses more than 7 days back for everyone, admin included; exactly 7 days passes. An absent time is the server's IST minute. The DB session is `+05:30`, so `NOW()` in the removal is IST.
- **Kinds:**
  - A Yes / No meter takes only `"yes"` / `"no"` and stores 1 / 0. `reading_out` and `validate_reading` are the only places of the mapping. `limit_state` is `not_ok` against the expected answer.
  - An amount is 0 or more, has no order check and cannot be reset.
  - A gauge may be below zero. A gauge equal to a limit is inside.
  - S038's `parse_number` (renamed from `_parse_limit`) and its messages serve the readings.
- **Removal:**
  - Removal needs `equipment:edit` at the site, both on the route and as the lock key, so IT admin may remove and the operator and the supervisor get 403.
  - Removing twice gives 409, a reading of another node gives 404, and a scrapped node gives 409 from the locked row.
  - A reset with a later active reading gives 409.
  - `can_remove` comes from one "newest active id" query per page and is false on a scrapped node (Decision 6, reported).
  - `include_removed=1` is ignored for a user without `equipment:edit`.
- **RBAC.** `reading:log` is held by `maint_operator` only, so the supervisor and the maintenance ladder inherit it and IT admin and the storekeeper do not. It is in `SITE_SCOPED`. `test_rbac.py` (`test_reading_log_holders` and the matrix) and `navigation.test.js` (OPERATOR, ENGINEER, MANAGER) were updated.
- **`ApiError` `code`** (`api_common.py`). The parameter is optional, keyword-safe and sent only when set. No existing caller passed a fourth argument. `api.js` already reads `err.code`.
- **Security.** Every route is gated:
  - `equipment:read` for the history and `reading:log` for the POST, both checked again at the node's site;
  - `equipment:edit` for the DELETE.

  The actor comes from `actor()`. The SQL fragments are code constants, and every value is a parameter.
- **Screens:**
  - Both dialogs are `FormModal` (scrollable body, fixed footer). `FormModal.vue` did not change.
  - The Yes / No dialog shows the question as its title. Its toggles are 48 px with `aria-pressed`. *Save* is disabled with "Pick Yes or No".
  - *Remove* asks first in the row with the brief's words and [*Remove*] [*Keep*].
  - The empty states are "No readings yet" and "No readings.".
  - The load failure reads "Readings could not be loaded: …", and a 503 or no network gives "Not saved. Try again in a minute." with the typed values kept.
  - *Log reading* is hidden on a scrapped node and for the storekeeper.
- **Tests against the brief's § 8.** Every listed backend case is present in `test_meters_core.py` (70 new) and `test_readings_api.py` (36). The seven `readings.spec.js` tests and the `equipment.spec.js` test assert what the user sees: the message beside *Value*, the *High* and *Not OK* badges, the saved messages, the removed row with who removed it, the note kept after the answer, and the accessible name of the last-reading line. `openLog` calls `expectDialogFits`. *History* is `close-only`, so its tests check that *Close* is in the viewport (Decision 11, reported).
- **The 14 Decisions taken** are local and reported. None changes the approved design:
  - Decision 1: the fifth argument of `counter_error`.
  - Decision 2: Indian grouping in server messages, as `toLocaleString("en-IN")`.
  - Decision 8: `last` on every meters list.
  - Decision 12: a machine per test.
  - Decision 13: the two S038 tests changed for the new buttons and field.
- **Docs pass:**
  - `schema.md` and `schema.html` name v32, the table, both links and the index (apart from CR1-04).
  - `Plan.MD` § 3 and § 4.5 are updated.
  - `.claude/CLAUDE.md` § SMTW-Review has the § 9.6 point and the spec-to-step map (`equipment` S039, `readings` S039).
  - `device-checks.md` has row 32.
  - The other docs are correctly untouched.
- **Manual checks.** The report's `## Manual checks` has every important check: three `[auto]` with a passing run behind them, and the real-device check as an open box that matches row 32.
- **Not reviewed:** `.claude/hooks/session-start.sh` and `.claude/settings.json` are untracked and absent from the snapshot. They date from 20:18, before the S039 code, and the report does not name them. They are cloud-session tooling, not this step's. The user should know they are in the tree before committing.

## Manual browser checks for the user

- Row 32 of `docs/steps/device-checks.md` (important):
  - the decimal keypad on Android and iPhone;
  - the refusal under *Value* not hidden by the keyboard;
  - *Yes* / *No* easy to hit with a thumb.
- Gate B, from the brief § 1.3 (BS1-04): the *Meters* card stays below Details / Properties. On a phone, *Log reading* is about two screens down. The alternative is the card above Details for `reading:log` holders.
- With CR1-03: on a phone, check that *Log reading* and the last-reading line are easy to hit.
