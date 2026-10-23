```
Step: S028 — Back-dating window: admin and backlog entry
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 22-10-2026
```

Reviewed against: d686fcd (the uncommitted changes are S028 docs and the README index only; no code)

# S028 — Brief review, round 2

**Verdict: no `blocker` or `major` finding is open.** BR1-01 is resolved:
`keycloak_admin = role_client("admin")` builds a user with the token role
`admin` (`tests/harness.py:24`), so `has_perm` returns on the bypass
(`auth_utils.py:356`) and `_can_access` sees every unit. Every "admin" case
in § 7 now uses it, and the existing test stands as the IT-admin case with
`BACKLOG_UNTIL` patched. One `minor` finding: the start-move test's
"after the window" case raises its ticket through `make_ticket`, which posts
as IT admin, so the setup is refused before the move is tested. Three nits.

Round 2: I re-read § 1, § 1.1, § 2, § 3, § 4.1–4.3, § 6, § 7, § 8, § 9 and the
Review log, and checked every file:line they cite against d686fcd. § 4.4 and
§ 5 did not change and were not re-reviewed. Q1 and Q2 are the user's; I
checked only that their statements of the code are correct, and they are.

## Earlier findings marked Accepted

All reflected in the brief text: BR1-01 (§ 3 `conftest.py`, § 7 fixture note
and cases), BR1-04 (§ 3 and § 9: Plan.MD § 2, § 3, § 4.2; philosophy § 1),
BR1-05 (§ 7 e2e test; no device row), BR1-06 (§ 2 rewritten, "to verify"
gone), BR1-07 (`:299`), BR1-09 (`at_unit("maint_technician")`), BR1-10
(`LONG_BACKDATE_YEARS`), BR1-11 (§ 6 oldest first, plan date; § 1.1), BR1-12
(§ 4.2 cache note), BR1-13 (`too_old_message`). BR1-08 (the file count) is
accepted but wrong again after the r1 additions, see the nits.

## Findings

### BR2-01 — minor — The start-move test's "after the window" case cannot raise its ticket

**Problem.** § 7: "a move (start, as `at_unit("maint_technician")`) 30 days
back on a ticket raised 31 days back: after the window → 400; in the window →
200." The brief does not say who raises the ticket. The ticket fixture is
`make_ticket` (`conftest.py:499-507`), which posts as the `admin` fixture,
that is IT admin. With `BACKLOG_UNTIL` patched to a past date, IT admin's
limit is 7 days, so the raise 31 days back answers 400 and the test fails in
its setup, not in the move it means to check.

**Why it matters.** This is the trap BR1-01 named: a coder who trusts the
brief may read the failure as a bug in the move path, or "fix" it by granting
`it_admin` the key (against A1). The fix is one argument, but the brief should
state it so the coder does not decide it alone.

**Options.**
- (a) **Recommended.** Say in § 7 that both cases raise the ticket with
  `make_ticket(machine, client=keycloak_admin, occurred_at=…)` (the fixture
  takes `client=`). Admin's limit does not depend on the patch, so the same
  setup serves both cases.
- (b) Raise the ticket before patching `BACKLOG_UNTIL`, then patch and move.
  It works, but the order of the patch inside the test is easy to break.

The rest of the case holds: `start` is allowed from `raised`
(`tickets_core.py:370`), so no acknowledge move with a "now" time sits
between the raise and the back-dated start; the technician's limit is read
through `_event_time` (`tickets.py:819`, `:1004`).

## Nits

- **BR2-02** (nit) § 3: "7 code and test files, 3 docs" — the table has 8
  code and test files (`tickets_core.py`, `tickets.py`, `config_rbac.py`,
  `conftest.py`, three test files, `tickets-raise.spec.js`) and 3 docs.
- **BR2-03** (nit) § 7: `test_ticket_work_api.py:1017` is a raise 2 days
  back (the variable is named `start`), not a start move. The point stands:
  it stays inside every window.
- **BR2-04** (nit) § 7, the e2e test: no spec acts as `admin` in the browser
  yet (`asPerson(page, "admin")` has no use in `frontend/e2e/`), and
  `seed_e2e.py` gives `e2e_admin` no display name, so the top bar shows the
  login `e2e_admin`. `asPerson` still passes (it compares with `me.name` from
  the backend). Say so in § 7, or give `e2e_admin` a name in the seed's names
  map so the top bar reads like the other persons'.

## Checked and found consistent

- BR1-01's resolution: `role_client` (`conftest.py:239-242`) passes any role
  name to `RoleClient`; `harness_user` (`tests/harness.py:24`) accepts
  `"admin"` as a token role; `has_perm` returns `True` on `_is_admin`
  (`auth_utils.py:356`) before any read; `accessible_unit_ids` is `None` for
  admin (`equipment.py:259-264`), so `load_node_for_user` (`equipment.py:272`)
  and `require_perm_at` pass; `make_ticket` already posts as a token-role
  user with no person row, so `current_person_id` being `None` is not new.
- § 1 and § 4.1: `MAX_BACKDATE_DAYS` and `EVENT_TIME_TOO_OLD` at
  `tickets_core.py:69`; the `<` comparison at `:107`; `_now()` at
  `tickets.py:159`; `compute_permissions(["admin"])` returns every key
  (`access_core.py:51-52`); `test_admin_gets_all_permissions` at
  `test_rbac.py:153`, `test_role_matrix` at `:191`,
  `test_permission_values_are_tuples` at `:41`.
- § 1.1: `REPEAT_WINDOW_DAYS = 7` at `tickets_core.py:299`;
  `planned_date_error` at `:541`; `validate_labour` at `:639`; the serial from
  the month of entry at `tickets.py:762`; `occurred_at`, `created_at`,
  `created_by` at `local_db.py:410-415`.
- § 2: ISO 14224:2016 § 7 (quality of data), § 9.5 / Table 6 (failure data,
  failure date), § 9.6 / Table 8 (maintenance data), Annex C (MTBF, MTTR);
  EN 15341:2019; SMRP 3.5.1 MTBF and 3.5.2 MTTR; ISO 9001:2015 § 7.5.3
  "control of documented information", § 7.5.3.2 retained documented
  information; ISO 27001:2022 A.8.2 privileged access rights. All cited
  correctly and explained in plain terms.
- § 4.2: `has_perm` with no `g.user` is `False` (`auth_utils.py:352-355`);
  `current_memberships` cached in `g` (`:272-289`); the raise validates
  before `get_db()` (`tickets.py:728-730`); `_event_time` at `:819`, called
  at `:881`, `:1004`, `:1043`; the *Already fixed* block through `_apply_move`
  at `:782`; alerts skipped on *Already fixed* (`:782-786`).
- § 4.3: no `ticket:*` key in `config_rbac.py:105-119` is granted to no role
  today, so `()` is new there, and `test_role_matrix` lists each role's keys
  explicitly, so it is unchanged.
- § 6: `_check_repeat` at `tickets.py:693-708`; `is_repeat_candidate` measures
  from the entered times.
- § 7: `conftest.py:315-317` (`admin` is IT admin), `:534-536` (`at_unit`);
  `test_tickets_core.py:29` (`NOW`), `:100-105`, `:159-165`, `:350-351`;
  `test_tickets_api.py:72`, `:194-198` (uses `admin`, so IT admin); the only
  callers of `event_time_error`, `validate_raise`, `validate_event_time` are
  `tickets.py:729`, `:827` and the tests; `tickets-raise.spec.js:118-119`
  already has the pattern the admin test copies (`istLocal`);
  `people.js:8` maps `admin` to the `admin` token role, and the e2e backend
  builds that user through the same `harness_user`.
- § 8 Q1 (b): the three time fields are plain `datetime-local` inputs
  (`RaiseTicketView.vue:453`, `tickets/EventFields.vue:72`,
  `tickets/StartedAtFields.vue`); `frontend/src/utils/ticketLabels.js` exists
  and already holds display helpers for the ticket screens.
- § 8 Q2 (b): `alerts_core.raise_alert` at `alerts_core.py:62` takes only the
  intensity today; `backend/tests/test_alerts_core.py` exists; a breakdown's
  escalation is queued by `alerts.enqueue_alert` at `tickets.py:784-785`.
- § 9: `docs/Plan.MD:65`, `:150-166`, `:328` and
  `docs/Maintenance-Philosophy.md:25-26` read as the brief quotes them.
- Monkeypatching `tickets_core.BACKLOG_UNTIL` works because `backdate_days`
  reads the module global at call time (§ 4.1); `tickets.py` must not import
  the constant by name, and the brief does not have it do so.
- Writing style (scope A): the changed sections lead with the point and keep
  one term per thing; the one new UI text follows the existing message's form.
