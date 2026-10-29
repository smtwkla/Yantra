```
Step: S070 — Countermeasures
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 30-10-2026
```

Reviewed against: 32eb122 + uncommitted S066, S067, S068 (partly coded; S069 approved, not coded)

**Verdict: no `blocker` or `major` finding is open.** Three `minor` findings and a list of nits. One
finding needs KLA's choice (BR1-01, the owner rule); it is **not defining**: either answer fits the
design and changes one predicate. The § 9 questions: **Q1 (no reopen) is not defining**, (a) stands;
**Q2 (the owner must hold `improvement:read`) is not defining**, but I recommend (b), not the brief's
(a), see BR1-01. The facts file `scratch/brief-facts-S070.md` was given and used.

What I read: the brief; `docs/roadmap/R05-rca.md` (R05.3, gate R, Q1.3, Q3.1, Q3.2); the S069 brief
(§ 3, § 4.1, § 5.1–5.4, § 6, its Review log) and the S071 brief; S067's code (`improvements.py`,
`improvements_core.py`, migration v36, `test_improvements_api.py` key-set pins); `documents.py`,
`file_store.py`, the LOCK ORDER notes of `equipment.py`, `tickets.py` and `improvements.py`; the
ticket owner's functions in `tickets.py`; `auth_utils` (`has_perm_at`, `current_person_id`,
`check_perm`); `config_rbac` (the improvement keys, `SITE_SCOPED`); `db_helpers`; `local_db` (v21,
v35, v36, `_PRECONDITIONS`, the people and memberships tables, the session time zone);
`migrations_v13.py:518-524`; `test_documents_api.py:487-617`; `test_migration_v12.py:78`;
`test_migration_v36.py`; `conftest.py` `_TABLES`; `tickets_core` constants; Plan.MD § 3.

## Findings

### BR1-01 — minor — D3 narrows gate R's answer Q3.2 (a), and its reason also applies to the owner it accepts

**Problem.** Gate R approved Q3.2 (a): "Anyone with a membership at the site, a person without a login
too". D3 (§ 5.3, § 9 Q2) adds a condition: the owner's role at the site must grant `improvement:read`,
which leaves out the storekeeper. The reason given is that a storekeeper owner "would own work they
can never open". The same holds for the owner without a login, whom the brief accepts; for both,
Q3.2 (a) already says "the lead marks the work done".

**Why it matters.** The storekeeper is a real owner at this plant. A countermeasure "keep two spare
contact blocks in stock" or "add the door gasket to the minimum stock list" is the storekeeper's job
(Plant-Facts: the stores at each site). Under D3 that work is credited to the engineer, which is the
downside Q3.2 (b) was rejected for. The 400 text "Choose a person of this site" is also wrong for a
storekeeper, who is of this site.

**Options.**
- (a) Keep D3 as written. The owner list is exactly the people who can see their countermeasure.
- (b) **Recommended.** Follow Q3.2 (a) as approved: an active person with a membership at the site,
  any role. `may_own` becomes "has a membership there" (`person_at_site(...) is not None`), and the
  `owners` list is `people_at_site` unfiltered. For an owner whose role lacks `improvement:read`
  (today the storekeeper) `can_mark_done` is false, `mine` is empty, and the engineer marks it done:
  the same path as the owner without a login. One sentence in § 5.3 and § 5.7 says so.

**KLA's decision; not defining.** The routes, the table, the flags and the tests keep their shape;
only the predicate and the `owners` filter change. If (a) stays, change the 400 text to say what
qualifies, e.g. "Choose a person of this site who can see improvements".

### BR1-02 — minor — § 8.1's CHECK test contradicts the CHECK as written

**Problem.** `chk_improvement_actions_done` is `(state = 'done') = (done_text IS NOT NULL AND done_at
IS NOT NULL AND done_by IS NOT NULL)`, the v21 shape (`chk_tickets_plan`). On an `open` row it only
requires that **not all three** done fields are set. § 8.1 asks for the test "`open` with `done_at`
refused": that row passes the CHECK (false = false). § 4.1 also says the CHECKs "keep both sets NULL
on an open row", which they do not.

**Why it matters.** The coder writes a test that fails, then has to decide alone whether to change
the CHECK or the test.

**Options.**
- (a) **Recommended.** Keep the v21 shape (one precedent, one reading) and correct the text and the
  test: § 4.1 "a done row carries its text, time and recorder; a row that is not done never carries
  all three (the same for cancelled)"; § 8.1 "`open` with `done_text`, `done_at` and `done_by` all
  set refused". The shell writes the three together or not at all, so the looser CHECK loses nothing.
- (b) Tighten to all-or-none per set, e.g. `(state = 'done') = (done_text IS NOT NULL) AND
  (done_text IS NULL) = (done_at IS NULL) AND (done_text IS NULL) = (done_by IS NULL)`, and the same
  for cancelled. Exact, but a new shape to read, for a case the code never writes.

### BR1-03 — minor — the removed list's `name` needs a kind label the backend does not have

**Problem.** § 5.8 gives the removed-list row `name` = "IM-2026-10-001 · Corrective". The backend has
no label for a kind: the brief defines the codes (`corrective`, …) and leaves the labels to S071
(`improvementLabels.js` `ACTION_KINDS`). Every other label of this app lives in the frontend
(`ticketLabels.js`); `_removed_item` builds `name` from columns only.

**Why it matters.** The coder has to invent a backend label table, which then duplicates S071's.

**Options.**
- (a) **Recommended.** The action branch sends `name` = the improvement's serial and a column
  `action_kind` (the code; NULL in the other branches, as `ticket_state` is). S071 § 5.7 shows
  "Countermeasure IM-2026-10-001 · Corrective" with `actionKindLabel(item.action_kind)`. One label
  table; S071's brief follows (it is reviewed in parallel).
- (b) `ACTION_KIND_LABELS` in `improvements_core`, used only here. A second copy of six strings.

## Nits

- **BR1-04** (nit) § 5.6, *The person row*: no deadlock exists here. The action insert and the owner
  change take shared locks on the improvement (held) and the person only, never on a unit; masters'
  person edit (person → memberships → person_units → units) never waits on an improvement or action
  row. S067's accepted cycle went through the unit's FK lock. Say "no cycle" so the LOCK ORDER note
  the coder writes stays exact.
- **BR1-05** (nit) § 3 `equipment.py` "docstring only, gains (6c)": also change the bullet at
  `backend/equipment.py:50-53` ("documents.py … takes exactly one owner lock per write … never two"):
  the countermeasure owner takes (6b) then (6c), in that order.
- **BR1-06** (nit) § 5.8: name the four owner functions (`read_action`, `read_action_for_change`,
  `lock_action_for_change`, `lock_action_for_purge`, the ticket's names) and state in their
  docstrings the branch on the key: `improvement:read` → owner or `improvement:edit` at the site;
  the purge key → `require_perm_at(key, site)`. Today the branch is implied by the key's value only.
- **BR1-07** (nit) § 5.8 removed list: the UNION's shared column `ticket_state` would carry the
  countermeasure's state. Rename the alias to `owner_state` in every branch (and `_JOIN_COLUMNS`),
  so `_removed_item` reads one named column for both owners.
- **BR1-08** (nit) § 4.2 and § 6: `owner.active` and `owner.may_own` per countermeasure through
  `person_at_site` is one query per row (up to 30). Read the owners' memberships at the site in one
  query (`WHERE p.id IN (…) AND ms.site_id = %s`), as the documents are read in one.
- **BR1-09** (nit) § 5.3: use `tickets_core.PLANNED_DATE_MAX_DAYS` (`backend/tickets_core.py:327`,
  365) for the due-date ceiling, not a second 365; the message `PLANNED_DATE_TOO_FAR` already
  belongs to it. Consider one floor for both dates (the earliest linked ticket's date): a
  *Correction* done on 15-10 then reads "due 15-10, done 15-10" instead of a due date at the
  improvement's start. The orchestrator's call, inside D7.
- **BR1-10** (nit) § 5.3 message "Done on: not before the problem happened (28-10-2026 15:15)": drop
  the field-name prefix; the tickets' form is "Must be at or after <event>, <time>". E.g. "Not before
  the problem happened, 28-10-2026 15:15".
- **BR1-11** (nit) § 5.7 "Only the owner or an engineer of this site can do this": managers hold
  `improvement:edit` too; `LEAD_AT_SITE` says "an engineer or manager of this site". Use the same
  words: "Only the owner, or an engineer or manager of this site, can do this".
- **BR1-12** (nit) § 8.3 `TestActionDocuments`: add restore on a cancelled countermeasure (409, the
  rule § 5.5 states) and retitle and remove by a technician who is not the owner (403).
- **BR1-13** (nit) § 5.6 documents path, "the predicate from the unit (fixed)": the predicate also
  reads the machine's current unit (`m.unit_id`), which a move changes; say "a plain read, as every
  access check" and stop there.
- **BR1-14** (nit) § 4.1 "The column add rebuilds `equipment_documents`": a nullable column add is
  instant in MariaDB; the foreign-key add scans the rows. Correct or drop the claim; the § 8.1 test
  with rows of all three owners stays right.
- **BR1-15** (nit) § 4.1 "Rollback: the previous release (S069)": the previous release is the image
  deployed before v38, which may predate S067. Say "a release before v38".
- **BR1-16** (nit) line numbers: `people_at_site` is `backend/tickets.py:742` (§ 3, § 6 say `:724`);
  the `pm_job:work` paragraph is `docs/Plan.MD:201`; `db_down` is `conftest.py:213`.

## The § 9 questions

- **Q1, reopen a done countermeasure:** (a) stands; not defining. A mis-tap cannot finish *Mark
  done* (the text is required), and R05.4's timeline is the right home for undo with history. One
  consequence to record in Plan § 4.6 or R05.4's item: until R05.4, a wrong *done* stays on the
  record and the engineer adds a new countermeasure.
- **Q2, the owner rule:** not defining; BR1-01 recommends (b), gate R's own answer.

## Checked and found consistent

- The data model: `improvement_actions` and its keys; `ix_improvement_actions_owner_state` serves
  `mine`; the owner CHECK dropped and re-added by name as v12 did
  (`migrations_v13.py:522-524`); `IF NOT EXISTS` forms as v21 (`local_db.py:613`) and v35
  (`:1090-1093`); the half-applied re-run; every production row has `action_id` NULL and one of
  three owners, so **no precondition is right** (the v21 reasoning, `local_db.py:600`).
- Existing tests: `TestOwnerCheckConstraint` (two, none → 4025) stays green;
  `test_migration_v12.py:78` asserts the name and `ticket_id` only; `test_improvements_api.py:514`
  pins the list item only, so the detail's two new fields break nothing; `test_role_matrix`
  unchanged (no key).
- Permissions: route keys and site checks as S067 § 5.5 (404 before 403); the owner by data through
  `current_person_id` (active person, `auth_utils.py:314`) and `has_perm_at` (`:439`); IT admin
  reads only; the flags in the pure `action_flags`, fed `is_open`, the state, `may_edit`, `is_owner`
  (the rule in one place, D10).
- Files: the fourth owner fits `Owner`'s field order; `_owner_key` checks `improvement:read` at
  any site, the owner functions the narrower rule at the site; files under
  `DATA_DIR/improvement-actions/<id>/`, served only by `_serve` (predicate, `nosniff`, `private`),
  file type from the first bytes; `documents_bp` at `/api`, so
  `/api/improvements/actions/<id>/documents` cannot meet `improvements_bp`'s `/<int>` routes;
  import direction `documents.py` → `improvements.py` → `tickets.py`, no cycle.
- Locks: (6b) → (6c) new, taken in that order by every countermeasure write; the documents path
  reads the immutable `improvement_id` plain, then (6b), then (6c), so it never inverts the order;
  every refusal comes from a locked row or a plain read made after the lock; no ticket lock; the
  (6c) → `equipment_documents` edge touches rows nothing else locks. Sequences checked against
  the notes in `tickets.py:23-83`, `equipment.py:9-60` and `improvements.py:18-58`.
- Time: `_now()` IST and `init_command SET time_zone = '+05:30'` (`local_db.py:1266`), so
  `created_at`'s date and `today` agree; `parse_event_time` and `FUTURE_SKEW` reused; `done_at`'s
  floor at the earliest linked ticket (D6) and no 7-day window.
- Layering: rules in `improvements_core` (validators, `due_date_error`, `done_time_error`,
  `overdue_days`, `action_counts`, `action_flags`, `may_own`), the shell locks, reads and stores.
- Standards: ISO 9001 § 10.2.1 (c), § 10.2.2, § 7.5.3 (with the recorded departure), EN 13306, TPM
  MP, yokoten and one-point lesson, ISO 27001 A.5.15 and A.8.3, each in plain words; the six kinds
  rest on them.
- Track full; no screen, so no manual checks; the browser tests are S071's.

## Feedback

- waste: the facts file lists `/api/improvements/<id>/actions` and its sub-routes as "called in
  test_improvements_api.py", which is the prefix `/api/improvements/<id>` matching; I opened the
  file to see it (2 min). A route with a placeholder could match on the whole shape.
- idea: a brief that adds a lock level could carry its lock sequences as a table (route × steps)
  instead of prose; checking § 5.6 against three notes took the longest part of this review.
