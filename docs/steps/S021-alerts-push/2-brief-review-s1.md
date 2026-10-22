```
Step: S021 — Alerts: PWA and web push
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 22-10-2026
```

Reviewed against: 79fc61d + uncommitted S026, S027

# S021 — Staleness review s1

**Verdict: one `major` finding is open (BS1-01).** It is not code drift: the
code it concerns (`_assign`, `_auto_assign`, `add_assignee`) is unchanged
since the baseline. It is a gap between the brief's text and what the user
approved at gate A, which the orchestrator asked me to check. Every other
finding is a file name, a version number or a rule the brief should restate.

**What changed since the baseline** (28d3be3 + S024; S024 committed as
3df667c): S025, S019 and S020 (b6b8dfb), tooling and e2e lanes (c7e6396,
79fc61d), and uncommitted S026 and S027. Of the files in the brief's *Where*
and the modules they call, these changed:

| File | Change that touches the brief |
|---|---|
| `backend/local_db.py` | v20 squashed; v21 (S019), v22 (S020), v23 (S027, uncommitted); `_PRECONDITIONS` |
| `backend/tickets.py` | `_apply_move` gains the plan-clearing block; `_send_back` takes `cur` and refuses after a repeat; `_recheck_repeat` after the raised event; `not-a-fault` from in progress; `_add_event` has three S019 columns; notes and parts routes |
| `backend/tickets_core.py` | `SCHEDULED`, `MOVES` with `schedule`, `reschedule`, `state_keys`; `REGRADE_STATES` includes scheduled; `NOTE_EVENT`; `ticket_times` counts scheduling as a response |
| `backend/config_rbac.py` | `ticket:edit_notes` (S027) in `PERMISSIONS` and `SITE_SCOPED` |
| `backend/worker.py` | `is_connection_lost` moved to `local_db`; `_task_failed` unchanged |
| `backend/api_common.py`, `app.py` | JSON for every error; `/api/health` reports `schema_ready` |
| `backend/tests/conftest.py`, `test_rbac.py` | `_TABLES` gained `ticket_parts`, `ticket_note_edits`; the role matrix gained `ticket:edit_notes` |
| `frontend/src/components/FormModal.vue`, `useFormModal.js`, `utils/revealError.js`, `RaiseTicketView.vue` | S026: a refused save scrolls to the first message and focuses its field |
| `frontend/e2e/support/dialogs.js` | `expectFieldMessage` asserts `toBeInViewport()` (S026) |
| `tooling/e2e/run_lanes.py`, `e2e_backend.py`, `run-e2e-tests.bat`, `e2e/support/stack.js` | lanes: one backend, Vite and database per lane; one run per machine (`scratch/e2e-run.lock`) |
| `.claude/CLAUDE.md` | Migrations rule (S025); browser-test rules: targeted vs full suite, lanes, the lock; SMTW-Review *Migrations* point |
| `docs/Plan.MD`, `docs/Maintenance-Philosophy.md` | § 4.7 rows and Q2 updated at approval; S019, S020, S025, S027 decisions |

Unchanged since the baseline, and still as the brief describes them:
`task_queue.py`, `task_handlers.py`, `scheduled_tasks.py`, `settings.py`,
`config.py`, `example_secrets_app.py`, `company_settings.py`, `auth_utils.py`,
`equipment_core.effective_criticality`, `settings.label_base_url`,
`stores/auth.js`, `router/index.js`, `index.html`, `vite.config.js` (the
`YANTRA_API_URL` proxy is S024's).

## Findings

### BS1-01 — `major` — *Job assigned to you* was approved as a fourth kind, but the brief does not contain it

**Fact.** The gate-A record (brief, *Review log › Gate A*) says: "Q3 *Job
assigned to you* to the technician, as a fourth kind". The brief's body says
the opposite everywhere the coder reads: § 1 *Out of scope* lists *Job
assigned to you*; § 1.4's table has three kinds plus the test; § 5.1 says
`kind` is `breakdown`, `defect` or `escalation`; § 5.2 has no audience for
it; § 5.3 enqueues nothing on assignment; § 8 tests none of it; § 1.3 says a
technician reads "Nothing yet"; decision 11 rejects a dot for technicians
because it "would never go out". Plan.MD § 4.7, updated at approval, marks
the breakdown, defect and escalation rows "(S021)" and leaves the *Job
assigned to you* row unmarked.

**Fact.** The assign code is as it was at the baseline: `add_assignee`
(the route, `ticket:assign`) calls `_assign`, which inserts the
`ticket_assignees` row and the `assigned` event and returns `False` when the
person is already assigned; `_auto_assign` calls the same `_assign` on
acknowledge and start for the actor's own person.

**Why it matters.** The coder cannot code the fourth kind from the brief,
and must not decide its rules alone: who gets it, when, its text, whether it
is quiet, and what it does to *What you will get* and the bell's dot. Coded
as the body reads, the step would miss a decision the user approved.

**Options.**
1. **Amendment A1: write the fourth kind into the brief** (recommended, if
   the user confirms Q3 stands). The rules I would expect, for the planner to
   check:
   - kind `assigned`; enqueued from `add_assignee` only, after `_assign`
     returns `True` (a repeat tap enqueues nothing), with `event_id` the
     `assigned` event and `exclude_person_ids` = the actor. Not from
     `_auto_assign`: the assignee is the actor, so nothing would be sent;
   - the recipient is the one assigned person. `add_assignee` already checks
     an assignable role at the ticket's site, so the fan-out needs only that
     person's subscriptions (no audience table, no unit check);
   - normal, no escalation; title "Assigned to you · SMTW.MCC2 · VBM001",
     body "TK-2026-10-012 · Not building pressure — by Priya" (the actor's
     first name by the § 1.4 name rule);
   - `should_send("assigned", state)` while the ticket is open; the handler
     also checks the person is still in `ticket_assignees`;
   - `you_get`: "Jobs assigned to you" for anyone with a membership in
     `ASSIGNABLE_ROLES` (technician, engineer, manager). A technician then
     reads that line, not "Nothing yet", and the dot shows for a technician
     whose device is off. Decision 11's rejected alternative must be
     reworded;
   - Plan.MD § 4.7: "(S021)" on the row; tests: enqueue on assign, nothing
     on auto-assign or a repeat assign, nothing once the ticket is closed or
     the person removed; e2e: the technician's *What you will get* line.
   The change to the dot rule is a change to what the user approved, so A1
   goes to gate A.
2. **Defer it to a later step** and correct the gate-A record ("Q3: not
   now"). Needs the user's word, since the record says yes.

### BS1-02 — `minor` — the migration is v24, with the S025 conventions

**Fact.** v21 (S019), v22 (S020) and v23 (S027, uncommitted) are taken.
`LATEST_VERSION = _MIGRATIONS[-1][0]`. The brief says "the next free
version" (§ 3, § 4) and `test_migration_<n>.py`.

**Fact.** CLAUDE.md § Migrations (S025) and the SMTW-Review *Migrations*
point: a migration that touches rows that exist in production carries a
`_PRECONDITIONS` entry and a test from the production schema. v21–v23 each
carry a comment "No _PRECONDITIONS entry: …" with the reason.

**Fact.** `test_migration_v23.py` is the current pattern: it imports
`_migrate`, `_recreate`, `_run`, `_schema` from `test_migration_v20` and
uses the upgrade database `vel_yantra_upgrade`; two tests: a fresh database
gets the version, and a database at the previous version gets it with a
re-run that changes nothing.

**Fact.** `test_migration_v20.py` already pins `V20 = [m for m in
_MIGRATIONS if m[0] == 20]`, so the brief's § 3 line "If they still run the
full list when this step is coded, pin them" is settled.

**Fact.** `conftest._TABLES` is emptied child-first; `ticket_note_edits`
and `ticket_parts` were added by S027 and S020.

**Fix (brief text only).** In § 3 and § 4: "migration **v24**" and
`test_migration_v24.py` on the v23 pattern (fresh database; a v23 database
gets v24; a re-run is a no-op). Add: "No `_PRECONDITIONS` entry:
`push_subscriptions` is a new table and no existing row is touched; the
migration comment says so, as v21–v23 do." Drop the "if they still run the
full list" sentence. Add `push_subscriptions` to `conftest._TABLES` before
`people` (its FK). If S027 is dropped before S021 is coded, the number moves
down; the coder takes `LATEST_VERSION + 1` as it stands.

### BS1-03 — `minor` — the e2e section names a spec that does not exist and predates the targeted/full rule and lanes

**Fact.** `frontend/e2e/` holds `asset-list`, `equipment`, `labels`,
`masters`, `screens`, `tickets-notes`, `tickets-parts`, `tickets-raise`,
`tickets-work`. There is no `settings.spec.js`; the Settings page is covered
by `screens.spec.js` alone (`SETTINGS_ROLES = ["manager", "it_admin"]`,
shows "Database").

**Fact.** `screens.spec.js` lists every route of `router/index.js` with who
may open it and what must show. A new route not added there is not covered.

**Fact.** README § Manual checks (22-10-2026) and CLAUDE.md: the coder and
the code reviewer run the **targeted** specs plus `screens.spec.js`; the
**full** suite only when the step changes shared frontend code (`FormModal`,
`useFormModal`, `api.js`, the router, the auth store, `e2e/support/`). The
run is split into lanes (`E2E_LANES`, default 6), each lane its own
`e2e_backend.py` process, database, backend port `5010+n` and Vite
`5180+n`; one run at a time per machine (`scratch/e2e-run.lock`).

**Why it matters.** The brief's acceptance "`tooling/run-e2e-tests.bat` is
green" no longer says which suite; and the Settings card tests have no file
to go in.

**Fix (brief text only).**
- § 3 Tests: `frontend/e2e/notifications.spec.js` (new) holds *My
  notifications* **and** the Settings › Notifications card tests; add
  `/notifications` to `screens.spec.js` with `who: EVERYONE` (the key is
  `('*',)`), `shows` the *Turn on for this phone* button for a seed person
  with a Team record and the "You are not in Team" text for `it_admin`.
- § 8 Acceptance: "the **full** e2e suite, because the step changes the
  router, the auth store and the top bar (shared shell)". Note that each
  lane starts its own `e2e_backend.py`, so the in-process VAPID pair
  (§ 3, BR1-06) is made once per lane, which is what the tests need.

### BS1-04 — `minor` — S026's rule applies to the Settings › Notifications card

**Fact.** S026 (uncommitted, gate B) adds *A refusal is always in view*:
`revealError(container)` scrolls the first message into view and focuses its
field. `FormModal` calls it for every dialog; `RaiseTicketView` calls it on
its page form (Q1 accepted). `expectFieldMessage` in `e2e/support/dialogs.js`
now asserts `toBeInViewport()`, not `toBeVisible()`.

**Why it matters.** The card is a page form at the bottom of a long Settings
page (Database, Uploads, Removed documents, Labels, Network, Background
tasks, Access log). On a phone, after *Save* refuses "4", the message beside
box C can be below the fold. The brief's e2e check "4 is refused on the
field" would then fail under `toBeInViewport()`, and the floor rule S026
sets would be broken on the one new form of this step.

**Fix (brief text only).** § 3 `NotificationsSettings.vue`: after a refused
save (its own check or the server's `{error, field}`), call
`revealError(form)` after the DOM update, as `RaiseTicketView` does. The
e2e check uses `expectFieldMessage`. *My notifications* has no field
messages, so nothing changes there.

### BS1-05 — `nit` — file paths and existing exports

- `src/components/AppTopbar.vue` is `src/components/layout/AppTopbar.vue`.
  Its `.topbar-right` holds the name and the logout button; `asPerson`
  (`e2e/support/people.js`) asserts `.topbar-right` contains the person's
  name, so the bell goes beside them, not in place of them.
- The Labels and Network cards are inline in `views/SettingsView.vue`; only
  Access log and Removed documents are components under `views/settings/`.
  A separate `NotificationsSettings.vue` is fine (the card is larger); say
  that `SettingsView.vue` imports and places it.
- `stores/auth.js` already exports `userPersonId` (from `me.person_id`);
  the *not in Team* state reads it. `logout()` is the one sign-out function
  (Keycloak logout, or a reload in dev bypass); the unsubscribe goes before
  its redirect.

### BS1-06 — `nit` — docs the step should also update

- `.claude/CLAUDE.md` still ends "**Not yet built** (Plan.MD phase 1,
  deliberate gap for now): PWA shell." Remove it with the *Notifications
  (S021)* bullet.
- The SMTW-Review spec map gains `notifications` S021, as S027 added
  `tickets-notes`.
- `tickets.py`'s LOCK ORDER note says "Ticket rows are locked only here and
  by documents.py". `ticket_escalate` (worker) locks the ticket row too and
  takes nothing after it; add the worker to that note, with "no new
  lock-order edge".

### BS1-07 — `nit` — what `mark_failed` stores

**Fact.** `_task_failed` stores `f"{type(exc).__name__}: {exc}"`, not
`str(exc)` (unchanged since the baseline; the brief's § 5.1 says `str(exc)`).
So a task row's `last_error` reads `NoRetry: …` or `RetryLater: …`. Tests
in § 8 that match `last_error` should expect the prefix. The subscription's
own `last_error` (written by the handler) is the plain message.

### BS1-08 — `nit` — the console watch and `push.js`

**Fact** (S024, in the tree at the baseline, so a nit): `e2e/support/test.js`
fails every test on any `console.error`, Vue warning or uncaught error.
§ 8 says "`subscribe()` may fail … The test accepts the error line": that
holds only if `push.js` catches the failure and shows it on the page, never
`console.error`. The service-worker registration at start-up must be caught
the same way, or *every screen opens* fails on Chromium. Worth one sentence
in § 3 `push.js`.

### BS1-09 — `nit` — the raise's enqueue sits after the *Already fixed* block

**Fact.** `raise_ticket` now writes the raised event, then
`_recheck_repeat` (S025), then the *Already fixed* restore through
`_apply_move`. § 5.3 says *Already fixed* sends nothing. Say in § 3: the
raise's `enqueue_*` call comes after the `if clean["restore"]` block, guarded
by `clean["restore"] is None`, so a repeat refusal or a restore refusal rolls
the task row back with the ticket.

## Checked and found consistent

- **Escalation against S019 and S025.** `should_escalate` tests
  `state == raised`; the current `MOVES` leave `raised` by acknowledge,
  start, schedule (engineer, `ticket:assign`), restore and not-a-fault. A
  raised breakdown scheduled straight away counts as acknowledged, and S019
  counts the scheduled event as the first response (`_RESPONSE_EVENTS`), so
  the KPI and the escalation rule agree. Not a fault from in progress (S025
  U4) closes the ticket: `should_send("escalation")` stops at closed, and
  no state after raised escalates. "Not acknowledged within N minutes" still
  means "still raised after N minutes".
- **Regrade while scheduled.** `REGRADE_STATES` now includes `SCHEDULED`;
  § 5.3 already says "while acknowledged, scheduled (S019) or in progress →
  the alert only".
- **Send back.** `_send_back` now takes `cur` and refuses after a repeat
  with a 409 before any event; § 3's "S025 adds its repeat refusal there,
  with no clash" holds. `_apply_move` still calls `_add_event` once per move
  after the step, so "in `_apply_move`, after `_add_event` returns the id,
  when `move == "send-back"` and `clean["machine_down"]`" is the right place.
- **`_add_event` returning the id.** Its new callers (`add_note`,
  `_schedule` through `_apply_move`, `_assign`) ignore the return value;
  S027's `edit_note` updates a row by id it already has.
- **`latest_critical_event_id`.** The events carrying an intensity are still
  `raised`, `regraded` and `sent_back`; S019's `scheduled`/`rescheduled` and
  S027's `note` events carry none.
- **Worker and queue.** `task_queue.enqueue(cur, task_type, payload,
  scheduled_for, max_attempts)`, `mark_failed(conn, task_id, error,
  retry=True)`, `claim_next`'s own transaction, `BadTask`, `run_task` and the
  `HANDLERS` dict are as the brief describes. `scheduled_tasks.SCHEDULE` is
  daily only; the escalation uses `scheduled_for`, not the schedule.
- **RBAC.** `push:subscribe = ('*',)` is not site-scoped, so `SITE_SCOPED`
  is untouched; `test_every_role_gets_wildcard_permissions` passes by itself,
  and `test_role_matrix` needs the key in every row, which § 3 Tests covers
  ("the new key"). `ticket:edit_notes` (S027) does not meet the step.
- **Settings.** `_APP_SETTINGS`, `get_setting_int`, `_save_setting`,
  `_validate_app_settings(body, _creating)` and `label_base_url(cur)` are as
  described; `/app` still validates every key in `_APP_SETTINGS`, so the
  second dict (BR1-02) is still needed.
- **Config and secrets.** `config.py` reads optional secrets with
  `getattr(secrets_app, name, default)`; `auth_utils._get_dev_stub_user`
  reads `config.DEV_STUB_ROLE` at call time (BR3-11's model).
  `example_secrets_app.py` has no VAPID lines yet.
- **e2e backend.** `e2e_backend.py` sets `config.*` after importing
  `config` and before importing `app`; the VAPID pair goes in the same
  place, per lane process.
- **JSON errors (S025).** The brief's 400 and 409 messages are `ApiError`s;
  the new handlers change nothing for them.
- **Pillow 13** is in the lockfile (S025) for the plain "Y" icons (Q6).
- **Plan.MD** § 4.7 rows and Q2 were updated at approval and match § 1.4
  and § 1.5 (except the row of BS1-01); `push_subscriptions` is in § 5's
  table. **Maintenance-Philosophy** § 8 and § 9 still carry the grade
  meanings the card quotes.
- **Writing style.** The brief is in scope A; the UI texts it sets are in
  scope B. No new text to flag.
