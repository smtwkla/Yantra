```
Step: S070 — Countermeasures
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 30-10-2026
```

# S070 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** I found 2 minor findings and 3 nits. The
backend follows the brief: the migration, the rules, the lock order, the owner-by-data rule and
the documents store's fourth owner. § 6 is exact for S071.

## Tests run

- **Unit suites** (`YANTRA_TEST_RUN=s070cr1 tooling\run-tests.bat`): backend 3665 passed,
  frontend 309 passed, tooling 185 passed. All suites passed. The counts match the coder's run
  (s070c1).
- **Frontend build**: not run, because the frontend did not change.
- **Browser tests**: none re-run. No finding of mine needs one. The coder's report names the
  right specs for a step with no screen change. The targeted run covered `equipment`,
  `settings` (the removed-documents card), `improvements` (the detail gained fields),
  `tickets-raise` (the third owner) and `screens`: 99 passed. The whole Normal run passed once:
  275 passed, 13 skipped. § 8.4 asks for no new browser test.

## Findings

### CR1-01 (minor) — The 409 message tells the user to cancel a countermeasure, which does not help

- **Where:** `backend/improvements_core.py:107` (`ACTIONS_FULL`), together with
  `backend/improvements.py` `add_action` (the count includes cancelled rows).
- **Problem:** The message is "An improvement holds up to 30 countermeasures. Change or cancel
  one instead." The count includes cancelled rows (§ 5.2: "cancelled ones counted"). A cancel
  therefore never frees a place. The text is the brief's own. The code follows it exactly, but
  half of the advice is wrong (CLAUDE-COMMON § Writing style B: say what the user can do next).
- **Failure scenario:** An engineer reaches the 30-row limit and taps *Add* → the 409 appears.
  He follows the advice and cancels an old countermeasure. He taps *Add* again and gets the same
  409, with no way forward.
- **Fix:** Use "An improvement holds up to 30 countermeasures. Change an open one instead." in
  the constant and in the test (`test_the_31st_is_409`). The other choice is to count only open
  and done rows. That changes an approved rule, so it goes to the user at gate B. Recommended:
  the wording fix.

### CR1-02 (minor) — The removed-list branch for countermeasures is a third copy of the ticket branch's block

- **Where:** `backend/documents.py:561-568` (the new block in `_removed_branches`), next to the
  ticket block at `:552-559`.
- **Problem:** The two blocks differ only in three names: the search column (`t.serial` /
  `i.serial`), the unit column (`t.unit_id` / `i.unit_id`) and the branch SQL. The node block
  also repeats the same shape. This breaks CLAUDE-COMMON § DRY: "never copy-paste code blocks".
- **Failure scenario:** R05.6, R03.6 and R03.17 each add one more owner (brief § 4.1, *Shared
  with later steps*). Each would add a fourth or fifth copy. Then a fix to the search or the
  scope, such as a new searchable column, must be made in every copy, and one copy will be
  missed.
- **Fix:** Add one small helper,
  `_scoped_branch(sql, search_column, unit_column, common, common_params, pattern, unit_ids)`
  → `(sql, params)`. Call it for the node, ticket and countermeasure branches. The model
  branch has no unit condition and stays as it is.

## Nits

- **CR1-03** (nit) `backend/improvements_core.py` `done_time_error`: a ticket raised with *Now*
  stores seconds (e.g. 15:15:42). A done time typed as 15:15 in the same minute is then refused
  with "Not before the problem happened, 28-10-2026 15:15", which contradicts itself. To fix it,
  compare against `problem_at.replace(second=0)`. A *Now* tick on a ticket raised up to
  `FUTURE_SKEW` ahead has the same problem; tickets solve it with `max(now, last)`
  (`tickets._event_time`).
- **CR1-04** (nit) `backend/documents.py` `_REMOVED_ACTION_BRANCH` / `_removed_item`: the item's
  `state` carries only the countermeasure's state. Once S072 closes improvements, a removed
  photo of a closed improvement will show *Restore*, and the click will end in 409 "This
  improvement is closed". Carry this into S072 or S073: send the improvement's state too, or
  use `owner_state = 'closed'` when the improvement is closed. Nothing can close an improvement
  before S072.
- **CR1-05** (nit) `backend/app.py:175-176`: the comment still says documents_bp has three
  owners. Add `/improvements/actions/<id>/documents` (S070).

## Checked and found consistent

- **Migration v38** (`backend/local_db.py:1186-1224`): word for word as § 4.1. Both CHECKs have
  the v21 shape. The owner CHECK is dropped and added again under its name. It has `IF NOT
  EXISTS` on the table, the column, the key, the foreign key and the CHECK. It has no
  `_PRECONDITIONS` entry, as § 4.1 reasons: new table, nullable column, a CHECK every existing
  row meets. `test_migration_v38.py` covers § 8.1: a fresh database, a v37 database with
  documents of all three owners, the four CHECK refusals (4025), two owners refused, a re-run,
  and a half-applied re-run.
- **Schema docs:** `docs/schema.md` has the `improvement_actions` row (ENUM values, CHECKs,
  indexes), `equipment_documents.action_id` with its key and the four-owner CHECK, the Mermaid
  fields and the three links, and "migration v38". `docs/schema.html` has the table, the column
  and the links on the Overview, Equipment and Tickets tabs, and the header line "Migration v38
  … by hand 30-10-2026". The docs pass is complete. Plan.MD § 3 and § 4.2 and the
  Maintenance-Philosophy glossary row are present. `.claude/CLAUDE.md` was left unedited on the
  orchestrator's instruction, and its proposed text is in the report.
- **Lock order:** each route's sequence matches § 5.6 and the new LOCK ORDER notes:
  - add: (6b), then plain reads in § 5.1's order;
  - change, done and cancel: (6b), then (6c) through `_lock_action` (keyed on `id` and
    `improvement_id`, so a countermeasure of another improvement gets 404), then plain reads;
  - documents: a plain read of `improvement_id`, then (6b), then (6c), then the predicate.
  No path takes (6c) before (6b), and none takes a ticket lock. The ACTIONS_MAX count is a
  plain read made after (6b), and its snapshot starts after the lock, so two adds cannot both
  pass at 29. `equipment.py` and `documents.py` docstrings name (6c).
- **Permissions:** add, change, cancel and owners use `require_perm(improvement:edit)`, then the
  predicate 404, then `require_perm_at` at the site 403. Mark done and the documents writes use
  `improvement:read` and the predicate, then `_require_owner_or_editor`. That rule is
  `has_perm_at(EDIT_KEY, site)` or `current_person_id == owner_id`. A user with no Team record
  (IT admin) owns nothing. The documents owner's functions branch on the key: the write key
  gets the owner rule, the purge key `require_perm_at`. `lock_action_for_purge` makes no state
  check, as every owner. The actor always comes from `actor()`, never from the body. All SQL
  is parameterised; the f-strings build only placeholders and code constants.
- **Files:** stored under `DATA_DIR/improvement-actions/<id>/` and served only through `_serve`,
  after `read_action`'s predicate, with `nosniff` and `private` (tested at
  `test_documents_api.py:705-706`). The file type still comes from the first bytes.
- **The removed list:** the fourth branch is scoped by `i.unit_id` to the purge-key units, and
  is left out when there are none. It searches the serial, the title and the original name.
  `owner_state` replaces `ticket_state` everywhere; no other code read the old alias.
  `action_kind` is in every branch.
- **The owner rule:** `person_at_site` (active, a membership at the site, any role). On a change
  it runs only when `owner_id` changes. `may_own` uses the same test in one query
  (`_site_members`), and `owners` is `people_at_site` unfiltered, as BR1-01 (b) asks.
- **Done-time rules:** the server's IST clock in Python (`_now()`, microseconds dropped), so the
  checked value is the stored one (Decision 4). `FUTURE_SKEW` is the upper bound, `problem_at`
  the floor, and there is no 7-day limit. Mark done and cancel leave `updated_*` alone (D8).
  `overdue_days` and the due-date range use the IST date (`_today()`).
- **`mine`:** `owner_id = current_person_id`, open countermeasures of open improvements inside
  the predicate, by `due_date, id`, `LIMIT 200` with `total`. A user with no Team record gets
  the empty answer. The item shape is § 6's; it has no `state`, as S071 § 5 expects.
- **§ 6 against S071:** the detail's `actions` keys, `action_counts`, `problem_at` (ISO
  datetime, which S071 slices to the date), the `owners` `{id, name}`, the `mine` item and the
  removed item's `action_kind` all match what S071's brief reads.
- **Edge cases:** a `PUT` with no change writes nothing; `null` on a `PUT` is refused; a boolean
  `owner_id` is refused (`_is_id`); a missing countermeasure is 404; the database down gives 503
  (`db_down` test).
- **Decisions taken:** the nine decisions in § 4 are inside the brief's design. None departs
  from it. `action_state_error` keeps § 5.5's table in the pure core.
- **Tests:** they cover § 8.2 and § 8.3 route by route, including the failure modes: other site
  404, key missing here 403, non-owner technician 403, IT admin and storekeeper 403, the done
  time and due date bounds, and an owner kept or refused after leaving the site.
- **Before S071:** a removed countermeasure photo would show in Settings › Removed documents in
  the node layout (a link to `/equipment/null`). The report says so (§ 5), and no screen can
  make such a row before S071. This is not a finding.

## Manual checks

None for the user. The step has no screen change and no real-device check (§ 8.4, § 8.5). The
impl report's `## Manual checks` says so, and S071 holds them.

## Feedback

- hindrance: `step_snapshot.py diff S070 --stat` also lists other steps' untracked docs (the
  S074–S077 briefs and S069's review r2, about 2700 lines). I had to filter them out by hand
  before reading (`diff S070 --stat`, 25 files, 14 of them S070's).
- idea: a `--code` switch on `step_snapshot.py diff` that keeps only the *Code folders* setting's
  paths plus `docs/schema*` and the docs in § Docs to keep current. That would give the
  reviewer's file list in one command.
