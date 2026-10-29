```
Step: S075 — One-point lessons
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 30-10-2026
```

Reviewed against: 32eb122 + uncommitted S066, S067, S068, S069, S070

# S075 — Brief review, round 1

**Verdict: no blocker or major finding is open.** Five minor findings and seven nits. Full
track, round 1: the whole brief was read against the code. Facts file: `scratch/brief-facts-S075.md`
was given and used.

**Decisions for KLA at gate A (BR1-05): none is defining.** § 9 Q1–Q4 are all inside gate R's
answers or inside what the roadmap left to the brief (Q6.2 a names "the improvement's machine, and
every machine of its class when ticked", which is D2; R05.6 says "`OPL-NNN` (to settle in the
brief)", which is D3). The step can be coded on the brief's recommended answers; KLA should read
BR1-05's three points when approving, because each is a judgement the brief took for him.

**The security-sensitive part (the fifth documents owner) is consistent** with S006/S012/S070: the
CHECK is dropped and re-added by name as v38 does (`backend/local_db.py:1186`); files are served
only by `_serve` after `OWNERS[owner].read` (`backend/documents.py:367-390`); the write key is
checked by `_owner_key` before any file is read and again at the record's site inside the lock
(`:320-340`); the removed list's unit scope follows `_removed_branches` (`:528-575`); the test at
`test_removed_documents_api.py:149` is the one line the fifth branch breaks, as the brief says.

## Findings

### BR1-01 — minor — § 5.6 Create: the lock sequence written is not the one the steps take

**Problem.** § 5.6 says procedures.py takes "either (6) … or (P) … **Then** only shared locks: a
countermeasure row (6c) `LOCK IN SHARE MODE` when linking". The create sequence below it takes
(6c) shared in step 2 and the `OPL` counter (6) in step 3: the shared lock comes *before* (6), the
reverse of equipment.py's numbering and of tickets' start, which takes (6) then (7) shared.

**Why it matters.** The LOCK ORDER note is what later steps reason from. A note that says "(6) then
shared" while the code does "shared then (6)" misleads the next writer who adds a path. I checked
the real order and it makes no cycle today: the only holders of an `OPL` row are lesson creates,
and nothing that holds (6c) exclusive (S070–S074's writers, under (6b)) ever waits on `OPL` or
(P). But the text must say what the code does.

**Options.**
- (a) **Recommended:** take (6) first: step 2 becomes `next_counter(cur, "OPL")`, step 3 the link
  checks with (6c) shared. The numeric order holds, the note is true as written, and a refused
  link still rolls the bump back (no gap), as a refused start does in improvements.py.
- (b) Keep the sequence and rewrite the paragraph: "(6c) shared, then (6)", with the two-line
  reason above why it is safe.

### BR1-02 — minor — § 5.3 (1), § 5.9, § 3: how many reads of the countermeasure, and by which function

**Problem.** Three statements disagree. § 5.3 (1) says "`read_action(cur, action_id)` → 404
becomes 400", then in the same item "procedures.py turns the 404 into the 400 by reading first with
`lesson_source`'s predicate, not by catching the error". § 3 lists `read_action` among the imports
from improvements.py. § 5.6 step 2 then reads `kind, state` with its own `LOCK IN SHARE MODE`
select, and "the improvement's `equipment_id` (plain)" with a fourth read, while § 5.9's
`lesson_source` returns only `{improvement: {id, serial, title}, action_id}`, so it cannot supply
that `equipment_id`.

**Why it matters.** The coder has to decide how many queries a create makes and which function
owns the predicate; `read_action` raises 404 (`backend/improvements.py:961`), so using it means
catching an `ApiError`, which the brief says not to do.

**Options.**
- (a) **Recommended:** one plain read in improvements.py, `lesson_source(cur, action_id)` → the
  countermeasure's improvement through `_visible_condition` as a row with `id, serial, title,
  equipment_id, site_id`, or `None`; procedures.py builds the detail's `source` from `id, serial,
  title` and uses `equipment_id` for § 5.3 (3) and `site_id` nowhere (the key is checked at the
  machine's site). Then the (6c) shared select for `kind, state`. Two reads; drop `read_action`
  from § 3's import list.
- (b) Keep `read_action` and catch its 404 into the 400. Against the brief's own sentence.

### BR1-03 — minor — § 5.7 `can_write_lesson` and D9 assume the improvement's machine never leaves the improvement's site

**Problem.** `can_write_lesson` checks `procedure:edit` at the improvement's site ("its machine's
site is the same: S067 § 5.7"). The improvement's site is its first ticket's unit, fixed; the
machine can move to a unit of another site (`backend/equipment.py:836-860`: a move is checked at
the target's site). Create checks the key at the machine's *current* site and the machine inside
the user's units (§ 5.5). After such a move the detail shows *Write lesson* and the `POST` answers
404 or 403. D9's "every reader of the improvement can open its lesson" has the same gap: an
improvement stays visible through `i.unit_id` after its machine moves away, but a machine lesson is
visible only through the machine's current unit.

**Why it matters.** S070 D10 and § 5.7 promise that no button ends in a 403. A cross-site move is
rare (S061's `moving_hint` exists for it), so this is a minor edge, not a design fault.

**Options.**
- (a) **Recommended:** compute `can_write_lesson` from the machine's current site and unit:
  `_IMPROVEMENT_FROM` already joins the machine `m`; join its unit's site (or reuse
  `unit_access_condition`'s `m.unit_id`) and check `has_perm_at("procedure:edit", machine site)`
  plus the unit in `accessible_unit_ids`. One line in D9 then says "while the machine stays in a
  unit the reader may see".
- (b) Accept the edge and say so in § 5.7 and D9 ("after a cross-site move the button may lead to
  a refusal; the next page load hides it"). Cheaper; the 404 text is plain.

### BR1-04 — minor — D10: importing `_text` and `_is_id` across modules

**Problem.** D10 imports two underscore-prefixed names from `improvements_core.py`. The underscore
says module-private; `_is_id` already has three copies (`equipment_core.py:67`,
`improvements_core.py:133`, `tickets_core.py:145`), so the DRY gain the brief cites is one copy
out of four.

**Why it matters.** The code reviewer will flag a private import; a later rename inside
`improvements_core` silently breaks `procedures_core`.

**Options.**
- (a) **Recommended:** give the two helpers public names in `improvements_core.py` (`text_field`,
  `is_id`; the private names stay as aliases so S070–S074's code is untouched) and import those.
  Two lines, no conflict with the steps being coded.
- (b) Keep D10 as written and note the tidy-up in § 9.
- (c) A fourth private copy in `procedures_core.py`, as the other three cores did. Simplest, but it
  is the pattern the brief rightly wants to stop.

### BR1-05 — minor — Three judgements the brief took for KLA; name them at gate A (none defining)

**Problem.** The brief records these as design decisions, but each changes what a user can do and
KLA has not been asked:

1. **A class lesson is editable, retirable and its photos purgeable from any site** (§ 5.5 rows 3
   and 5; D4). Once an SSVT engineer ticks a lesson for *Hydraulic press*, an SMTW engineer can
   rewrite its text, retire it (which takes it off SSVT's presses' cards) and an SMTW manager can
   purge its photos. This is gate R's rule ("a site-less master, edited by the key held at any
   site", R05.6), applied as the roadmap asked, and it matches model documents (S012). It is still
   the first lesson-level consequence KLA sees. **Not defining:** the key design (D4) holds either
   way; a later step can narrow the class rule.
2. **D7, plain text instead of Plan § 4.3a's Markdown body.** The column is the same
   `VARCHAR(1000)`; a Markdown renderer can be added later without a migration. **Not defining.**
3. **D8, a lesson does not mark its *Lesson* countermeasure done.** The owner still marks it done
   by hand after writing the lesson. Defensible in TPM terms (the lesson counts when taught), and
   it keeps procedures.py out of the improvement's locks and timeline. The other answer (done on
   write) can be added later as one write under (6b)/(6c). **Not defining.**

**Why it matters.** "Anything the brief doesn't cover is raised with the user" (README § Gates);
these are covered but buried in § 5.5 and § 7.

**Options.** (a) **Recommended:** the orchestrator lists the three in its gate A summary with the
brief's recommendation; no brief change. (b) Add a line to § 9 "Decisions for KLA" naming them.

## Nits

- **BR1-06** (nit) § 5.8 removed list: the lesson branch's `q` matches the serial, the title and
  the original name, but the row shows the machine's `code` and the node branch matches `e.code`.
  Add `e.code LIKE %s` so a manager searching by machine finds the lesson's photo too.
- **BR1-07** (nit) § 5.5 last bullet: "a request with no identity gets `require_perm`'s 401" —
  the auth layer answers 401 before any route; `require_perm` answers 403
  (`backend/auth_utils.py:495-506`). Fix the sentence.
- **BR1-08** (nit) § 5.7 "IT admin reads only": IT admin holds `equipment:purge_documents`, so it
  restores and purges a lesson's photos as for every owner (`has_perm_at` passes a token role at
  every site). Say "reads, and restores or purges removed photos".
- **BR1-09** (nit) § 5.3 (3): the message "A lesson for this countermeasure goes on HP003, the
  improvement's machine" is built in the shell. Put a builder in `procedures_core`
  (`lesson_machine_message(code)`), as `keeps_a_ticket(machine_code)` in `improvements_core.py`,
  so the text is tested in the core.
- **BR1-10** (nit) § 6: write the list and create routes as `procedures_bp.route("/",
  strict_slashes=False)` (`backend/improvements.py:451`, `:517`), so `GET /api/procedures` is not a
  308 to the slash form.
- **BR1-11** (nit) § 5.6 names the procedures lock "(P)" while equipment.py's order is numbered.
  Give it a number in the bullet the coder adds (for example "(6d) the procedures row") so one
  numbered order covers every module.
- **BR1-12** (nit) § 6.3: the lesson page shows photos oldest first; S077's *Edit photos* uses the
  documents route's list, newest first. A writer sees the two orders reversed. Either say so in
  § 6.3 (S077 decides what to show) or let `_list_items` take the order from the owner. S077's
  reviewer may raise the same point from its side.

## Checked and found consistent

- Migration v41: the shape copies v38 (`backend/local_db.py:1186-1225`): `IF NOT EXISTS` on
  table, column, key, FK and CHECK; `DROP CONSTRAINT IF EXISTS`; the CHECK keeps its name, so
  `TestOwnerCheckConstraint` (`test_documents_api.py:490-520`) and `test_migration_v12.py:78` stay
  green. `serial_counters.scope` is `VARCHAR(40)`; `OPL` collides with no scope (`EQ:`, `TK:`, `IM:`).
- `next_counter` (`backend/db_helpers.py:78`) bumps inside the caller's transaction; a refused
  create rolls it back: no gap, as the brief says.
- `Owner` fields and call shapes (`backend/documents.py:156-187`): `read(cur, id)`,
  `read_for_change(cur, id, key)`, `lock_for_change(cur, id, key)`, `lock_for_purge(cur, id, key)`;
  `_owner_key` does the any-site `check_perm` first (`:201-207`), so a class lesson needs nothing
  more, and the restore path passes the purge key into `lock_for_change` (`:608`), which the
  brief's rule handles without a branch on the key.
- `load_node_for_user` (`backend/equipment.py:369-385`) gives the 404-then-403 order the brief
  relies on, with any site-scoped key; `procedure:edit` joins `SITE_SCOPED`, which `has_perm_at`
  asserts (`backend/auth_utils.py:432-439`).
- `_removed_branches` guards the node, ticket and action branches with `unit_ids is None or
  unit_ids` and always adds the model branch (`backend/documents.py:539-575`); the lesson branch's
  `class_id IS NOT NULL OR u.id IN (…)` fits beside it, and
  `test_the_unit_scope_is_enforced_fail_closed`'s last line (`:149`) is the one assertion it breaks.
- `_actions` (`backend/improvements.py:351-384`) makes three queries today; a fourth for the
  lessons by `action_id IN (…)` keeps it O(1) per detail. The key-set pins in
  `test_improvement_actions_api.py:128` and `:510` and `test_improvements_api.py:514` are on
  `owner`, the owners list and the list item, not on an action, so they stay green.
- Import direction: procedures.py → equipment.py, improvements.py; documents.py → procedures.py;
  improvements.py reads `procedures` by SQL only. No cycle; the note at
  `backend/improvements.py:104` is the right place for the new importer.
- `WAS_CANCELLED` ("This countermeasure was cancelled", `improvements_core.py:112`) is S070's
  text, as § 5.3 (2) says.
- `test_role_matrix` (`test_rbac.py:187-219`) and `test_improvement_keys` (`:98`) are where the
  brief puts the key test; `_TABLES` is at `conftest.py:162`.
- `_text` strips and bounds by `len` (`improvements_core.py:137-149`), `_collapsed` joins runs of
  whitespace (`masters_core.py:69`): the title and body rules of § 5.2 are buildable from them.
- The e2e claim in § 8.4 holds: `settings.spec.js:66-69` opens Settings with the Removed
  documents card for a manager, which loads the list.
- D2 is Q6.2 (a) as approved at gate R; D3 is what R05.6 left to the brief. Standards named and
  explained plainly: TPM OPL (three types, training pillar, yokoten), ISO 9001 § 7.1.6, § 7.5.2–3
  with two recorded departures, ISO 27001 A.5.15, A.8.3 (and A.8.28 for D7).
- Track full is right (migration, access checks, locks, file serving). No screen in this step, so
  *Use on the floor* applies only to the API messages, which are one line each and name the field.

## Feedback

- idea: the facts file resolves dotted names by their last segment, so `procedures.action_id` and
  `improvements.equipment_id` report test-file "definitions" of `action_id` / `equipment_id`
  (`scratch/brief-facts-S075.md:76`, `:204`); a dotted name could be listed as "table.column, not
  looked up" to save the reader a double-take.
- waste: the brief's § 5.3 (1) and § 5.9 describe the same read twice with different functions,
  which cost a third read of `improvements.py:940-1006` to settle (BR1-02); a brief that names one
  function per read would have avoided it.
