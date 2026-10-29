```
Step: S069 — Why-why and the root cause
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 30-10-2026
From: R05.2
```

Reviewed against: 32eb122 + uncommitted S066, S067 (S067 is being coded; its `improvements.py`,
`improvements_core.py`, v36, the lock notes in `tickets.py` and `equipment.py` and
`test_improvements_api.py` exist in the working tree and may still change. S068 is approved, not coded.)

# S069 — brief review, round 1

**Verdict: no `blocker` or `major` finding. Four `minor`, eight nits.** Nothing here is a defining
question; the one item for KLA (BR1-01) is wording on a floor screen. The step can go on to the next
round or to coding under the gate-R delegation.

Answers to the orchestrator's questions, in short (the detail is in *Checked and found consistent*):

- **Locks.** Every route's sequence matches S067 § 5.4, `backend/tickets.py:23-33` and `:79-83`,
  `backend/equipment.py:21` and `:103-106`. The new edge (6b) → failure cause (shared) adds no cycle;
  the brief's argument holds, and I add one step it leaves implicit (below).
- **The CHECK.** `(root_cause IS NULL) = (root_cause_id IS NULL)` is the form v21 uses
  (`chk_tickets_plan`, `backend/local_db.py:613`); every S067 row is NULL / NULL and passes; § 8.1
  tests both halves and the re-run.
- **D7.** `frontend/src/stores/masters.js` is not in the settings' *Shared code* list; 28 files import
  it, and the change only adds two exports, so no importer changes behaviour. The brief's tests
  (a `masters.test.js` case, the `masters.spec.js` and `tickets-work.spec.js` re-runs, the whole suite
  at Normal once) are enough. No WebKit run is due.
- **Phone use.** Judged row by row; no `major`. One `minor` on a line operators do not need (BR1-01).
- **Size.** 21 code and test files, one table, no new screen, one concern. I do not recommend a split;
  the length is the lock narrative and the screen rules, which the coder needs. KLA's call, not
  defining.

Facts file used: `scratch/brief-facts-S069.md`. Every file, line and name the brief cites that it
lists checks out (the `conftest.py` `db_down` line is 213, not 212; the brief says lines may move).

## Minor

### BR1-01 — minor — § 5.7, the *Root cause* card shows "ISO 14224 group: Management" to the floor

**Problem.** The card is read by every `improvement:read` holder: operators, Tamil-speaking, on a
phone (settings: *Use on the floor*). "ISO 14224 group" is a standard's name, which the brief's own
*Words for the floor* rule keeps off the screen ("no RCA, no contributing"). The badge "4.2
Management error" already carries the group (the code's first digit), and the engineer sees the
group as the `optgroup` heading when picking.

**Why it matters.** One line of jargon on a card meant to teach "why the plant let it happen" in
plain words. Small, but it is the kind of line the floor skips, and the project's rule is to name
standards in the docs and the briefs, not on the operator's screen.

**Options.** (a) Drop the line; the group stays visible in the picker and in the code. (b) "Group:
Management" (the word the Masters panel uses for its column). (c) Keep it as the brief has it.
**Recommended: (a).** A judgement call for KLA (wording only; not defining).

### BR1-02 — minor — § 5.2 / § 5.3, the position range check and its message live in the shell

**Problem.** § 5.2 says "the range check is in the shell, which knows n". The core already gets the
chain as `[(id, position)]` for `reorder(ids, why_id, new_position)`, so it knows n too
(`len(ids)`). The message "Choose a place from 1 to n" would then be built in `improvements.py`,
while every other message of the module is a core constant or function (`keeps_a_ticket`,
`already_in`, `backend/improvements_core.py:48-53`).

**Why it matters.** CLAUDE-COMMON *Pure core, thin shell*: a rule and its text in the shell is the
pattern the module avoids everywhere else, and the core test of § 8.2 (`reorder` "to the front, to
the end …") cannot cover the bound.

**Options.** (a) `reorder` returns the pairs, or the refusal, as `removal_error` does: a
`position_error(n, position)` in the core with the message, and the shell raises the 400 with it.
(b) Keep the check in the shell. **Recommended: (a).** § 8.2 Core gains "position 0 and n + 1".

### BR1-03 — minor — § 5.2, the `evidence` row's `PUT` rule contradicts the bullet under the table

**Problem.** The `evidence` row says "absent, `null` or empty after trim → NULL" with no `POST` /
`PUT` split. The bullet under the table says "An absent field on a `PUT` stays as it is", and the
`contributing_causes` row writes the split out ("absent → unchanged; `null` or empty after trim →
NULL").

**Why it matters.** A coder who follows the row clears the evidence on every `PUT` that omits it. The
dialog always sends `evidence` (§ 5.7 `toBody`), so the screens would not show it, but a direct API
caller would, and the core test "`null` evidence → NULL" would not catch it.

**Options.** (a) Write the row as the `contributing_causes` row: `POST`: absent, `null` or empty →
NULL; `PUT`: absent → unchanged, `null` or empty → NULL. (b) Leave the bullet to govern.
**Recommended: (a).**

### BR1-04 — minor — § 5.7, both dialogs' `blank(seed)` is also called with no seed

**Problem.** `useFormModal` calls `blank()` with no argument when the component is set up
(`frontend/src/composables/useFormModal.js:22`, `const form = ref(blank())`). § 5.7's
`blank(seed)` for *WhyDialog* reads `seed.previousAnswer` and for *RootCauseDialog*
`seed.improvement.root_cause?.text` and `defaultRootCause(seed.improvement.whys)`: both throw on
mount, before any dialog opens, so the improvement page would not render. `MoveDialog.vue:68`
avoids it with `blank: (seed) => ({ …, ...seed })`.

**Why it matters.** Settings, *Self-check, repo items* (13): "the composable's call contract: what
`blank` returns, what `open(seed)` does" is on the list because this has bitten before. The brief
states the contract wrongly, so the coder would find it by a crash.

**Options.** (a) State it: `blank(seed = {})`, and read the seed with optional chaining (`seed.improvement?.…`), so the
set-up call gives empty strings. (b) Seed through `openCreate` only and spread, as `MoveDialog`.
**Recommended: (a).**

## Nits

- **BR1-05** (nit) § 5.2: "Write the root cause" → "Enter the root cause". The app's required-text
  messages say "Enter …" ("Enter a title", "Enter the question"); one verb for one thing (scope B).
- **BR1-06** (nit) § 5.7, the note on the two causes: "Tickets' cause: 3.4 …" → "Cause on the
  tickets: 3.4 …". A possessive plural apostrophe is hard to read on the floor and in Tamil-first
  eyes; the same line in § 8.3.
- **BR1-07** (nit) § 5.4 *Edit why*: say where the moved why's `updated_*` stamp comes from: its new
  `position` goes into its own `update_row` dict (with the changed text fields), and the plain
  `UPDATE … SET position` loop covers the other pairs only. Today the text says both "no stamp on a
  row that only shifted" and "the moved why's own row is stamped" without the mechanism.
- **BR1-08** (nit) § 5.7 `toBody` "leaves `position` out … when unchanged": needless. A `PUT` with the
  current position writes nothing already (§ 5.3, `reorder` returns no pairs). Send it on every
  *Edit*; one rule less in the dialog.
- **BR1-09** (nit) § 5.2: `validate_root_cause(body)` must take the `creating` argument `clean_body`
  passes (`backend/api_common.py:126`, `validator(body, creating)`), as `validate_link(body,
  _creating=True)` does (`backend/improvements_core.py:101`).
- **BR1-10** (nit) § 4.1: `ADD KEY IF NOT EXISTS` has no precedent in `local_db.py` (v35 has
  `FOREIGN KEY IF NOT EXISTS`, v21 `ADD CONSTRAINT IF NOT EXISTS … CHECK`). MariaDB accepts
  `ADD {INDEX|KEY} [IF NOT EXISTS]`; say that § 8.1's re-run test is what proves it.
- **BR1-11** (nit) § 6 "The list is unchanged": `backend/tests/test_improvements_api.py:514` pins the
  list item's exact key set, so the `LEFT JOIN failure_causes` added to `_IMPROVEMENT_FROM` (shared
  by the list) must not add a field to the list item. One line for the coder.
- **BR1-12** (nit) § 7 D7: the store holds fetched lists; the five groups are a label table, which
  `frontend/src/utils/` holds for other kinds (`ticketLabels.js`). The store is fine (one import for
  the panel and the two pickers); say so in D7, so the choice is stated.

## Checked and found consistent

- **The lock sequences.** Add, edit and remove a why, and the root-cause write, each take (6b)
  first (`_lock_improvement`, `backend/improvements.py:160`), then the plain checks in S067's order
  (`_check_improvement` 404 → 403, `_require_open` 409), then the write and `_detail_response`
  inside the transaction. No why row is locked on its own; no route locks a ticket. This is the
  S067 pattern (`backend/improvements.py:18-58`) and `backend/equipment.py:21` ((6b)) and
  `:103-106` (the improvements bullet).
- **The new edge (6b) → cause (shared).** The brief's argument holds. The step it leaves implicit:
  InnoDB requests the child's foreign-key share lock on the parent *before* it inserts the new
  secondary-index entry (`ix_improvements_root_cause`), so a root-cause write blocked on cause C's
  exclusive lock holds no C index entry that the code change's `LOCK IN SHARE MODE` count could wait
  on. The one row the count can wait on is an improvement whose *committed* `root_cause_id` is C,
  held `FOR UPDATE` by a writer that keeps its cause; such a writer takes no cause lock, so it never
  waits on the code change. No cycle. The ticket close's (7) → cause (shared) edge and the masters'
  counts are shared-with-shared, as the brief says.
- **The freeze.** `_check_code_frozen(cur, clean, locked, ticket_column)` at
  `backend/masters.py:743` and `_update_plain_master` at `:763` are as the brief says; the optional
  second column keeps the two existing asserts of "This code is used by tickets and can no longer
  change" (`backend/tests/test_failure_codes_api.py:256`, `:281`) true. Modes and actions are
  untouched (only `update_failure_cause`, `:795`, passes the new argument).
- **The CHECK and the migration.** Form as v21's `chk_tickets_plan`; `FOREIGN KEY IF NOT EXISTS` as
  v35 (`backend/local_db.py:1090-1093`); v36 is at `:1104` in the working tree;
  `test_migration_v36.py` slices `range(20, 37)` (`:17`) and is untouched; `_TABLES` already starts
  with `improvement_tickets, improvements` (`backend/tests/conftest.py:162`), so `improvement_whys`
  goes before them.
- **S067's contract.** `_LOCK_IMPROVEMENT` (`backend/improvements.py:106`) is "the values an edit
  compares with"; adding the three columns does not touch S067's edit route, whose `changes` dict
  is built from `validate_improvement`'s fields only (`:383`). `update_row` writes nothing on an
  empty dict (`backend/db_helpers.py:68-71`), so "nothing changed → 200, nothing written" holds.
  `_check_active_code` (`backend/tickets.py:775`) is a plain read, as the brief says.
- **The cause list and picker.** `masters:read` is `("*",)` (`backend/config_rbac.py:142`);
  `failure_codes:edit` is global (`:157`). `MoveDialog.vue:55-58`, `:92-94`, `:296` and
  `FailureCausesPanel.vue:17-24` are as cited; `masters.spec.js:103` picks the group by its label
  "Operation / maintenance", which the move keeps; `causeId("3.4")` exists
  (`frontend/e2e/support/tickets.js:76`) and `tickets-parts.spec.js:281` closes by API as the
  brief says. `causeText` gives the shape the ticket page uses ("{code} {label}",
  `TicketDetailView.vue:328`); no such helper exists in `utils/` yet, so it is not a duplicate.
- **Design and layers.** Validators, `reorder`, `renumber`, `WHYS_MAX` and the messages in the
  core; the active-cause check and the counts in the shell (they need the database); the
  frontend decides nothing (controls from `permissions` and `is_open`). D1–D10 each name a rejected
  alternative. No new abstraction: `_check_code_frozen` gains one optional argument, not a list of
  users (D8).
- **Standards.** TPM why-why, ISO 14224 failure cause, IEC 62740, ISO 9001 § 10.2.1 (b) and § 7.5.3
  are named and explained in plain words; the § 7.5.3 departure (no history until R05.4) is
  recorded as S067 did. No new key, so no ISO 27001 clause is due.
- **Use on the floor.** One job per card; *Add why* shows the previous answer above the fields, so
  the next why is written without scrolling; the edit and remove buttons follow the labour rows'
  size; the remove asks on the row and names the why; the root cause is three taps and one pick
  after the last why; the empty states tell an editor what to do; a reader sees no control that
  ends in a 403. The one wording point is BR1-01.
- **Manual checks.** Three **important** automated checks are flows a browser judges; the device
  check (the iPhone keyboard over the why dialog) is a kind the settings name and carries account,
  network and where; no automated check is on the device list.
- **Existing tests.** The detail's key set is not pinned (only the list item's, BR1-11); the
  `"Edit"` substring hazard in `improvements.spec.js` is real (Playwright matches a role name as a
  substring without `exact: true`) and the brief assigns the check to the coder.
- **Track and size.** Full track is right (a migration, locks, new routes). 21 code and test
  files; no split recommended.

## Feedback

- rule: the orchestrator asked me to judge the step's size against "the size rule", but the rule
  (25 files, 600 lines, one table and two screens) lives only in `.claude/skills/step/SKILL.md:166-172`,
  not in `docs/steps/README.md` or the brief-reviewer prompt; one grep to find it. A line in README
  § Tracks, or the rule quoted in the spawn prompt, would save it.
- idea: the facts file lists where `useFormModal` is defined, but the contract that caught BR1-04
  (`blank()` is called with no seed at set-up) is two lines below the definition. For the shared
  frontend files the settings name, `brief_facts.py` could print the first 10 lines of the
  function's body, as it does for a route's test lines.
