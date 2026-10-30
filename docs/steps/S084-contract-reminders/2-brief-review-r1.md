```
Step: S084 — Contract reminders
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 30-10-2026
```

Reviewed against: d216f48 + uncommitted S079, S080 (in progress: migration v43 and `test_migration_v43.py` only; no `contracts.py` yet)

**Verdict: no blocker or major finding is open.** Five minor findings and seven nits. Two of the minors
(BR1-02, BR1-03) are judgement calls for KLA himself, not for the delegation of 30-10-2026: one departs
from the roadmap text approved at gate R, the other decides who on production receives a test reminder.

Facts file read: `scratch/brief-facts-S084.md`. Every cited `file:line` in the alert files holds
(`alerts_core.py:38, :58, :92, :94, :368`; `alerts.py:114, :155, :163-176`; `task_handlers.py:3-7, :66,
:105, :153, :202, :229, :393`; `scheduled_tasks.py:12`; `push_core.py:43`; `email_core.py:45, :71,
:131`; `worker.py:114`; `task_queue.py:18`; `access_core.py:100`; `push.py:79`; `settings.py:348`;
`SettingsView.vue:208`; `test_worker.py:131`). The S080–S083 names were checked against those briefs.

## Findings

### BR1-01 — minor — § 8.5 row 1: "10 days later" gives a first reminder again, not the second

**Problem.** Row 1 says: after the first reminder, IT Admin "changes the To date to **10 days later**;
after 08:00 the following day the phone shows **Contract ends in 9 days**". Moving the To date 10 days
later leaves it 38 days away. By § 5.1, `first_reminder_for` (the old date) differs from the new To date
and days ≤ 60, so the scan sends the **first** reminder again: "Contract ends in 38 days". The check
fails as written.

**Why it matters.** The important device check would be marked failed for a step that works.

**Options.** (a) **Recommended:** "changes the To date to **10 days from today**" (earlier, so the
second reminder is due: "Contract ends in 9 days"). (b) Keep "10 days later" and expect "Contract ends
in 38 days", which then tests the re-arm rule but not the second reminder or the tag replacement.

### BR1-02 — minor — § 8.5: where the device checks run, and who receives the test reminder. **KLA's decision**

**Fact.** Push cannot run on the dev server: `docs/steps/device-checks.md` § Phone set-up says
"Notifications need HTTPS, so their rows run on production only (the dev server is plain HTTP)"; a
phone reaches the laptop by its LAN address, not `localhost`. Email can run on the dev server, as S032
row 30 did: `DEV_STUB_EMAIL` set to KLA's own address and the Mailgun `SMTP_*` values in the local
secrets file (never committed), the dev stub placed in Team as a manager at a site, the worker run
by hand. Whether KLA's laptop has those values set is outside the repo (the secrets file; see
*Questions for the user* in the hand-back). The e2e backend makes its own VAPID pair and fake SMTP
values (`tooling/e2e/e2e_backend.py:98-107`), so no automated test sends anything real.

**Problem.** The brief's two rows put one test contract at SMTW on production. By § 5.6 the first
reminder reaches every SMTW engineer's and manager's phone, and the second the same again; the email
reaches every SMTW manager with an address. The brief says "KLA tells them first". The check also
spans two mornings.

**Options.**
- **(a) Recommended, if KLA accepts the reach:** as the brief. The reminders are quiet (no sound), the
  title says "TEST reminder check — not a real contract", and it is the only way to test the push path
  end to end. Add to the row: KLA tells the SMTW engineers and managers the day before, and IT Admin
  sets the contract inactive the same day the second reminder arrived.
- **(b) Narrower reach:** a site **TEST** in production whose only members are the engineer test login
  and KLA (manager). Recipients follow site membership, so nobody else gets the reminder. Cost: a site
  row visible in every site filter and list on production; the roadmap's device checks use a TEST
  machine, never a TEST site.
- **(c) Split:** the email row on the dev server (S032 row 30's set-up; KLA can enqueue
  `contract_reminder_scan` by hand in the dev database instead of waiting for 08:00), the push row on
  production as (a). Still reaches every SMTW phone for the push.

Whichever KLA picks, the rows need the Where column per row (dev server or production) and the account
IT Admin uses to add the contract (BR1-09).

### BR1-03 — minor — D2 / § 9 Q1: lead days as constants depart from the roadmap text approved at gate R. **KLA's decision**

**Problem.** R02.5 (approved at gate R) says "The lead days are settings (Settings › Notifications)"
and "Migrations: none (settings in `app_settings`)". The brief makes them constants (D2) and adds a
migration (D3). Q5.1 a names "60 and 15 days" and does not say settings, so the two readings of the
roadmap differ; the brief states the departure and asks Q1. Taking Q1 under the delegation would
change a gate-R text without KLA.

**Why it matters.** A departure from an approved roadmap item is KLA's to confirm (README § Gates;
the delegation covers the brief's own choices).

**Options.** (a) **Recommended:** constants, as the brief (no card, no bounds, no rule for reminders
already sent; `FIRST_REMINDER_DAYS = ENDING_SOON_DAYS` keeps the badge and the reminder on one day).
(b) Two settings in Settings › Notifications. Either way the orchestrator records the answer in R02's
log and Plan.MD § 2 item 9 (which already says "60 and 15 days").

### BR1-04 — minor — § 3 `CONTRACT_TYPE_WORDS` duplicates S081's `TYPE_SHORT`

**Problem.** The brief adds `contracts_core.CONTRACT_TYPE_WORDS = {"warranty": "Warranty", "amc":
"AMC", "cmc": "CMC", "on_call": "On call"}` for the email's *Type* line. S081 § 3 and § 5.3 already add
`contracts_core.TYPE_SHORT = {"amc": "AMC", "cmc": "CMC", "warranty": "Warranty", "on_call": "On
call"}`: the same four pairs.

**Why it matters.** Two names for one mapping in one module (DRY; one term for one thing).

**Options.** (a) **Recommended:** import S081's `TYPE_SHORT` in `alerts_core`; drop
`CONTRACT_TYPE_WORDS` from § 3, § 5.4 and the facts' `type_word` note; `contracts_core.py` leaves
§ 3's file list (9 code files). (b) Keep both names (rejected: a duplicate).

### BR1-05 — minor — § 5.6 `alerts.people_at_site` reuses a name `tickets.people_at_site` already has

**Problem.** `tickets.people_at_site(cur, site_id)` exists (`backend/tickets.py:748`): the people
picker, every active member of the site by name with role, trades and `assignable`; `improvements.py`
imports it. The brief's `alerts.people_at_site(cur, site_id, roles, with_email=False)` returns ids of
role holders for a fan-out. Same name, different meaning and shape.

**Why it matters.** A reader who knows one function misreads the other (CLAUDE-COMMON writing style:
one term for one thing); a grep for the picker finds the fan-out.

**Options.** (a) **Recommended:** name it for what it is, e.g. `alerts.people_with_role_at_site`, or
`alerts.site_recipients`, beside `people_at_unit`; keep the private `_people_with_role` as planned.
(b) Keep the name (rejected).

## Nits

- **BR1-06** (nit) § 5.4 step 1: `_payload_time` (`task_handlers.py:202`) raises BadTask with the text
  "improvement_alert needs {key} …". Give it the task name as an argument (or a generic text) so a
  bad `contract_alert` payload is not logged as an improvement alert.
- **BR1-07** (nit) § 5.7: say that `keys_with_place.update(keys)` stays **after** the `continue`
  (`alerts_core.py:386-389`); only `compute_permissions` moves before it. Otherwise the no-units
  manager of § 8.3's new test also gets the two countermeasure lines, and the list there is wrong.
- **BR1-08** (nit) § 5.4: `should_send_contract` does not check `from_date <= today`. A From date
  edited into the future between the scan and the task gives the title "Contract starts on … · SMTW"
  (`status_label` of kind `upcoming`). Add the check to `should_send_contract` ("not started"), as the
  scan already has it.
- **BR1-09** (nit) § 8.5: the IT Admin action (add the contract, change the To date, set it inactive)
  needs its own Account and Network: IT admin, company network (S013 refuses IT admin on mobile data;
  `device-checks.md` § Accounts). The rows name only the phone's network.
- **BR1-10** (nit) § 5.4 push body: "Atlas Copco AMC 2026–27 · Atlas Copco — ends on 31-03-2027."
  names the vendor twice when, as the roadmap's examples do, the title holds the firm's name. Either
  accept it (the title is free text) or leave the vendor out of the push body (the email keeps its
  *Vendor* line). State the choice.
- **BR1-11** (nit) § 9 *Roadmap corrections*: R02.5's scope-B push text ("Contract ends in 15 days:
  Atlas Copco AMC 2026–27 (SMTW). Renew it or let it end.") is restyled into the app's title · place /
  body form. Right (the other alerts use it); add it to the corrections so the roadmap's text is
  updated.
- **BR1-12** (nit) § 5.3 step 2: the candidate query keeps a contract with the first reminder sent and
  16–60 days left as a candidate every morning for up to 45 days, so the scan locks it `FOR UPDATE`
  daily with nothing to do. Harmless at tens of rows. If wanted, add `AND (first_reminder_for IS NULL
  OR first_reminder_for <> to_date OR to_date <= today + 15 days)`; the decision still comes from the
  locked row.

## Checked and found consistent

- **Names from S080–S083:** `contracts` columns (`renewal_of_id`, `to_date`, `from_date`, `active`,
  `site_id`, `title`, `contract_number`, `contract_type`), `ix_contracts_renewal_of`, the four keys and
  their holders (`contract:read` `("maint_engineer",)`, `contract:read_senior` `("maint_manager",)`,
  `contract:read_basic` `("*",)`), `ENDING_SOON_DAYS = 60`, `contract_status` labels ("Ends today",
  "Ends in 1 day", "Ends in N days"), `_contract_out` (named fields, so A4 holds), S081's route
  `/contracts/:id(\\d+)`, S083's v45 and its one contract-row lock. S082 has no migration, so **v46**
  is right. The v43 migration in the working tree matches S080 § 4.1.
- **`roles_holding`** (`access_core.py:65`, `SITE_ROLES` order): `contract:read` →
  `("maint_manager", "maint_engineer")`; `contract:read_senior` → `("maint_manager",)`, as § 8.1.
- **The model (S074):** `improvement_alert_scan`'s `SELECT NOW()`, plain candidates, per-row
  `FOR UPDATE` in id order, markers on held rows, one transaction with `mark_done`; `_push_to_people`,
  `send_task_payload` (quiet → Urgency `low`, `silent`), `IMPROVEMENT_TTL_SECONDS = 86400`;
  `enqueue_email` with the person id; `email_send` reads the address at send time.
- **Lock order:** every route of S080, S081 and S083 locks at most one contract row, first; the scan
  holds several in id order and nothing else; the renewal read is plain. No cycle found.
- **REPEATABLE READ handling:** a renewal committed between the candidates' read and the commit is
  caught by the alert task's fresh read (§ 5.3, § 5.4 step 4); a To date edited after the marker is
  written re-arms (`!=`) and the queued task is dropped (`to_date` in the payload).
- **Security:** payloads carry `contract_id` and a date only; no address, host or port anywhere in
  the brief; tests use `@example.test`; `read_alert_contract` selects no `callout_number`, `cost_note`
  or price; recipients by key at the contract's site; admin and IT admin have no membership and get
  nothing; every recipient holds `contract:read_basic`.
- **Standards:** ISO 55001 § 8.3 and ISO 9001 § 8.4 (as Plan.MD § 2), ISO 9001 / 55001 § 7.4
  Communication, ISO 27001:2022 A.8.3 and A.5.34, TPM planned maintenance; each explained in plain
  words.
- **Existing tests named in § 8.3:** `TestYouGet` (10 tests at `test_alerts_core.py:215-256`),
  `test_every_kind_has_channels_and_the_improvement_kinds_are_push_only` (`:63`),
  `test_the_improvement_alerts_at_eight_after_the_purge` (asserts the whole `SCHEDULE`),
  `test_push_on_with_the_public_key_and_what_you_get` (`test_push_api.py:52`), `TestTasksCard`
  (`tasks[0]` stays the purge), the technician's exact list in `notifications.spec.js:205-206`
  (no contract line for a technician), `settings.spec.js:80` (S074's line stays).
- **Fixtures:** `make_site`, `make_vendor`, `user_at_sites` (units `[]` gives `all_units` false and no
  `person_units`), `db_rows`, `push_off`, `email_off`, `smtp_test_values`, `no_real_push` in
  `conftest.py`; `add_device` and `fake_send` imported from `tests.test_alerts` as
  `test_improvement_alerts.py:27` does; emails set by `UPDATE people SET email` as
  `test_closed_email.py:81`.
- **Import direction:** `masters_core` imports only `re` and `config_rbac`, so `alerts_core →
  contracts_core → masters_core` adds no cycle. `sw.js` has `targetUrl` (`:38`), so `/contracts/<id>`
  opens with no change.
- **Track full** (migration, locks, security-sensitive channels), 20 code and test files; anchors by
  name in the files S080–S083 change, by line only in the alert files no open step touches.

## Feedback

- hindrance: a Bash batch of five read-only checks was blocked whole because one command named
  `backend/secrets_app.py` (an emptiness check with the values hidden); the other four had to run
  again (1 rerun, ~2 min). The rule is right; a batch should fail only the offending command.
- rule: the orchestrator asked whether the dev server can send real push and email. The answer lives
  in the gitignored secrets file and the laptop's network, outside what a reviewer may read; such a
  question should go to KLA directly, with the repo facts (`device-checks.md` § Phone set-up, S032
  row 30) attached.
