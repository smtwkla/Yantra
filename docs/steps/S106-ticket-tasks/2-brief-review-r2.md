```
Step: S106 — Tasks on a ticket
Doc: brief-review r2
Author: Brief reviewer (Opus)
Date: 22-11-2026
```

Reviewed against: 8644720

**Verdict:** no `blocker` or `major` finding is open. All nine round-1 findings are reflected in the
brief's text, not only in the Review log. This round found five nits and nothing larger. Q2 (whether
open tasks block *Close*) stays KLA's decision at gate A. Its consequence and its remedy are now
stated correctly; BR2-03 adds one small consequence. Facts file `scratch/brief-facts-S106.md` was
given and used. Round 2: I re-read only the text changed since `scratch/S106-brief-r1.md`, section by
section: § 1 (*How the two tasks are read*, *A task*, item 7, *After this step…*, the Screens
bullet); § 2 (EN 13306, ISO 9001 § 10.2.1, *The rule of thumb*); § 3 (`tickets.py`, `equipment.py`,
`config_rbac.py`, the glossary row, the file count); § 4.1 (the table copy and the probe); § 4.2
(`owner.can_open`); § 5.3; § 5.6; § 5.7; § 6 (`tasks`); § 7 D3, D4, D11; § 8.3 (the edge tests,
*Detail*, *Mine*); § 9 (the split, *Length*, Q2, Q6, the SMTW-Review point, *Assumptions*, *Found
while checking*). I also read the code that the changed text now relies on.

## Nits

- **BR2-01** (nit) § 2 EN 13306, § 3 glossary row: EN 13306 (and IEC 60050-192) defines
  *fault diagnosis* as fault recognition, fault localisation and **cause identification**. The
  standard does not say "immediate"; that qualifier came from my round-1 BR1-02 and overstated the
  standard. "Immediate cause for a task, root cause for the improvement" is Yantra's own line (D1).
  Write it that way: "EN 13306: recognise, localise and identify the cause; in Yantra a task finds
  the immediate cause, and the improvement's why-why finds the root cause (ISO 9001 § 10.2.1 b)".
  The glossary row can keep its words, provided it does not credit "immediate" to EN 13306.
- **BR2-02** (nit) § 2 *The rule of thumb*, § 9 Q2: § 2 lists "a watch over weeks" as a
  countermeasure. In Yantra the watch is not a countermeasure. It is the improvement's *Watch
  period* (Maintenance-Philosophy § 12 glossary; `improvements_core.WATCH_DAYS_DEFAULT` 90): it
  starts after the countermeasures are done, and it counts recurrences from tickets. D3 already says
  this correctly ("it is the improvement's watch period"). In § 2, drop the watch from the
  countermeasure list and add "(a watch over weeks is the improvement's watch period, after its
  countermeasures)". In Q2's consequence, "a watch on a trial fix" then has this remedy: the trial
  fix becomes a countermeasure, and the improvement's watch period does the watching. The glossary
  row in § 3 is already right: it does not list a watch.
- **BR2-03** (nit) § 9 Q2 consequence: a ticket held in *Back in service* by an open task is still
  an open ticket (`tickets_core.OPEN_STATES`). So it also blocks scrapping its machine and
  deactivating its unit ("Close its tickets first (N open)", `tickets_core.close_tickets_first`).
  Before either, the engineer must close the ticket, which first means finishing or cancelling the
  task. Add one clause to Q2 (a)'s consequence so that KLA sees it at gate A.
- **BR2-04** (nit) § 3 *File count*: "6 code, one of them a comment only" should say two.
  `equipment.py` changes only in its docstring, and `config_rbac.py` only in a comment.
- **BR2-05** (nit) § 4.2: "It errs only towards false" is slightly too strong. `has_login`
  (`people.username IS NOT NULL`) does not prove that the person can log in through Keycloak (no
  `maintenance_team`, or the account was never set up). So `can_open` can also be true for an owner
  who never sees the task. Write "It can be wrong in rare cases: false for …, and true for an owner
  whose Keycloak login does not work". It stays a hint that no rule reads.

## Checked and found consistent

- **Round-1 findings in the text.** BR1-01: § 1 (*How the two tasks are read*, *A task*, item 7,
  *After this step*), § 2 *The rule of thumb*, D3's new example, D4 *What it costs*, Q2's
  consequence, remedy and border case, the glossary row and *Assumptions*. BR1-02: § 2 and the
  glossary row (see BR2-01). BR1-03: § 4.2, § 5.3, § 6, the Screens bullet and § 8.3. BR1-04:
  § 4.1, D11 and *Found while checking*. BR1-05: § 3, § 5.6 and Q6; no "task row" is left in the
  brief except where it is quoted as the word to avoid. BR1-06: § 5.7 and the *Mine* test. BR1-07:
  § 8.3's two edge tests. BR1-08: D4, § 5.7 and the `config_rbac.py` comment. BR1-09: the
  SMTW-Review point.
- **Q2's consequence and remedy.** Plan § 9 item 12 (*Closing discipline*, *Proposed*, 16-10-2026)
  says what the brief quotes: TPM closes within the shift, and tickets back in service but not
  closed show on the engineer's dashboard (not yet built, as the brief says). A cancelled task is
  final (§ 5.5). An improvement can start while its ticket is in *Back in service*:
  `improvements_core.START_FROM_STATES = (BACK_IN_SERVICE, CLOSED)`. The cancel reason "Moved to
  improvement IM-…" fits `validate_cancel`'s 500 characters. The border case (the supplier's
  inspection weeks away) and option (b)'s added rules are stated plainly.
- **`owner.can_open`.** `alerts.people_at_unit(cur, site_id, unit_ids, roles, only_ids=…)`
  (`backend/alerts.py:184`) goes through `_people_with_role` (`:203`), which returns at once on an
  empty `only_ids` (`:206`). It reads `people`, `memberships` and `person_units` only, filters on
  `p.active = 1`, and does not filter on a login, so the separate login check is needed. A
  technician or operator row without a login grants nothing (`config_rbac.NO_LOGIN_ROLES`).
  `alerts.recipients` calls `people_at_unit` with the ticket's site and unit. `access_core` is pure
  (it imports only `config_rbac`), so the new import in `tickets.py` makes no cycle.
  `roles_holding("ticket:read")` leaves out the storekeeper (`ticket:read` is
  `("maint_operator", "it_admin")`, and the storekeeper is outside the ladder). `people_at_site`
  sends each person's role to the picker, as § 5.7 says.
- **The edge tests' fixtures and paths.** `user_at_sites` builds real memberships with units or
  "all". `make_unit(site=…)`, `make_person` and `give_site_role(person, site, role)` exist with
  those arguments. `test_a_moved_machine_shows_to_the_old_and_the_new_unit` moves a machine with an
  open ticket, as `admin`, to a unit of a new site, and gets 200. The ticket predicate
  (`unit_access_condition`) covers the ticket's unit or the machine's current unit, so the moved
  owner opens the ticket and sees the task on *Mine*. `_lock_ticket` checks the key at
  `row["site_id"]`, the ticket's own site, so *Mark done* answers 403. The owner of the first edge
  test gets 404 from the predicate. `_check_person` accepts any role, so a storekeeper can be owner.
- **IT admin and the two keys.** `ticket:assign` and `ticket:close` sit at `config_rbac.py:119`
  and `:120` with the same holders. The `ticket:edit_notes` comment says the keys "can drift". The
  `INTERNAL_ONLY_ROLES` comment confirms that a person can hold IT admin and a site role at once.
  `current_person_id` (`auth_utils.py:314`) returns None for an inactive person or one without a
  Team record.
- **§ 4.1 table copy.** No statement in `backend/` sets `foreign_key_checks`.
  `scratch/s106_br1_alter_probe.sql` holds the three statements the brief describes.
  `ticket_events.remark` is `VARCHAR(1000)`. *Found while checking*'s arithmetic holds: "Description:
  " plus " → " leave 984 characters, so each description can have about 492.
- **Wording anchors.** `tickets.py:922` holds the comment "rolls the task rows back", `tickets.py:104`
  imports `alerts`, and `equipment.py:43` is the LOCK ORDER line (7).
- **The split and the length.** The brief has 919 lines, which matches "about 900". The cut into
  three steps is unchanged.

## Feedback

- hindrance: `scratch/s106_br1_alter_probe.sql`'s comment says "dropped at the end", but its last
  statement fails on purpose, so `vel_yantra_test_s106probe` stays in the dev database until the
  manual clean-up of `vel_yantra_test_*` (`.claude/CLAUDE.md` § Dev commands) drops it. A probe that
  ends in an expected error could drop its database first, in a second run.
- rule: BR2-01 corrects my own round-1 wording, which credited a qualifier to a standard. A
  standards finding could quote the definition it relies on, with its source, so that the brief
  writer copies the standard's words and not the reviewer's paraphrase.
