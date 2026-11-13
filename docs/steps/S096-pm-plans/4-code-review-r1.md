```
Step: S096 — PM plans on a machine
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 02-11-2026
```

# S096 — code review, round 1

**Verdict: no `blocker` or `major` finding is open.** One `minor` finding and three nits. The step
is built as briefed. Migration v51, the key, the locks, the item sync and every refusal match the
brief. All unit suites and the schema docs check are green.

## Tests run

- `YANTRA_TEST_RUN=s096cr1 tooling/run-tests.bat`: **backend 4801 passed, frontend 429 passed,
  tooling 239 passed** (all suites PASSED; `scratch/s096cr1-unit-all.txt`).
- `YANTRA_TEST_RUN=s096cr1 tooling/schema-docs.bat check`: **exit 0**, 4 passed, at v51 (run after
  the unit suites, not at the same time).
- Browser: none re-run. No finding of mine needs a run. The coder's runs are right. The new spec
  alone, then targeted (`pm-plans`, `equipment`, `screens`: 80 passed, 2 skipped), then the whole
  suite once at Normal (385 passed, 15 skipped, 0 failed), as the router changed. `readings.spec.js`
  (the `readings_sheet` change) was not in the targeted run, but the whole-suite run covers it.
- Read in the order of brief § 9: backend (`local_db.py` v51, `pm_plans_core.py`, `pm_plans.py`,
  `meters.py`, `config_rbac.py`, `contracts_core.py`, `app.py`, `equipment.py`), backend tests,
  then frontend (`PmPlanView.vue`, `PmItemDialog.vue`, `PmPlansCard.vue`, `pmLabels.js`, the
  router, `EquipmentDetailView.vue`, `pm-plans.spec.js`, `screens.spec.js`).

## Findings

### CR1-01 (minor) — the new-plan page on a scrapped node fails to render

`frontend/src/views/PmPlanView.vue:124` with `:282`, `:303`, `:314`, `:397`.

- **Problem:** for a new plan the page sets `canEdit = node.lifecycle !== "scrapped"` and
  `plan = null`. On a scrapped node the cards then take their read-only branches. Those branches
  read `plan.performer`, `assigneeText(plan)`, `plan.needs_verification` and `plan.trigger_text`.
  With `plan` null, each read throws a TypeError in the render. `GET /api/pm/meter-choices` does
  not refuse a scrapped node, so the load does not stop with a 403 or 404 first.
- **Scenario:** an engineer has a bookmark or a typed URL `/equipment/<id>/pm/new` for a machine
  that was scrapped later. The page shows the path line and the heading, then breaks: a blank
  card area and a console error, with no message saying why. The PM card hides *Add PM plan* on a
  scrapped node, so the normal path never gets there.
- **Fix:** on the new-plan page, treat a scrapped node like the 403. For example, show "This
  equipment is scrapped. You can't add PM plans to it." with *Back to the equipment*. Or guard the
  read-only branches with `plan`. Add one line to the `screens` or `pm-plans` spec only if it is
  cheap. A unit-level check of the load branch is enough.

## Nits

- **CR1-02** (nit) `backend/tests/test_pm_plans_api.py` (class `TestChange`): add the D10 meter
  case. A plan's meter is removed from the node (`PUT …/meters/<id> {active: false}`). Then a
  `PUT` that sends the same meter is answered 400 on `meter_type_id`, and `{active: false}` alone
  still passes. S097 depends on this rule: a plan must not point at a meter it cannot schedule.
- **CR1-03** (nit) `frontend/src/views/PmPlanView.vue:386`: the label *Meter then* is hard to
  follow on the floor. Use *Meter reading then*, or *Meter reading at that time*. The unit already
  follows the field.
- **CR1-04** (nit) `frontend/src/views/PmPlanView.vue` (items card): a reading item whose meter
  is no longer a choice gets no warning on load. The save then refuses "Item 3: Choose a meter
  from the list." with the row outlined, and the dialog's meter select shows blank. Mark such a
  row on load, as `lostMeter` does for the plan's meter. Brief § 5.5 says "the page shows it on
  load".

## The coder's departures (impl report § 4)

Each departure is acceptable. None changes a rule, a route, a key or a screen text of the brief:

| Departure | Judgement |
|---|---|
| `validate_item_check` in the core | Acceptable. It keeps the route on `clean_body` with no copy, and the node is read before the item is judged. |
| `plan_changes`, `find_choice`, the shared `_same` | Acceptable. One comparison by value (`Decimal("250.000")` = `Decimal("250")`, `1` = `True`) for the plan and the sync, so "a PUT of nothing writes nothing" holds (tested). |
| `calendar_every` checked in phase 1, maximum on the merged pair | Acceptable. It matches BR1-02's two phases. The month's maximum in the message for a `PUT` with no unit meets only hand-made requests. |
| Both meter ids refuse on `meter_type_id` | Acceptable. The page has one meter select. |
| A meter on a calendar plan is not looked up | Acceptable. "Clear the meter fields for a calendar plan." is the more useful answer. |
| Item ids ignored on a create | Acceptable. A new plan has no stored items. |
| `item_limits_text(item, meter_type, meter_code)` | Acceptable. The brief's text needs the meter node's code. |
| `planBody(form, items, equipmentId)` | Acceptable. On a `PUT` the id equals the stored one, so it is no change. |
| "Kannan (Technician)" from `roleLabel` | Acceptable. It is the app's one person-with-role label (scope B: the same words in the whole app). |
| The card's small line in one line, "1 item" in the singular | Acceptable. The meter label still shows under the trigger text. |
| The read-only view shows the trigger text, the meter label and *Last done* | Acceptable. A reader needs the words, not the two ticks. |
| `(6e)` in `equipment.py`'s numbered lock list | Acceptable. The new bullet uses that number, so the list must define it. |
| `docs/schema.md` "88 of 88, at v51" | Acceptable and correct: 81 at v50 plus the 7 new foreign keys. |
| *Meter then* as the label | Acceptable in substance; the wording is CR1-03. |

## What S097 builds on

Nothing here trips S097 (`docs/steps/S097-pm-jobs-due/1-brief.md` § 3):

- The columns S097 lists exist with the briefed types. The `trigger_kind` and `calendar_unit`
  ENUMs are pinned to S095's constants by `test_the_enums_equal_s095_s_constants`.
- `create_plan` and `change_plan` each have one `transaction`, and the item writes come before the
  answer. S097's `settle_plan_job(cur, plan_id, node_lifecycle, …)` fits after the item writes. The
  `node` from `_share_lock_node` holds `lifecycle`. It is a plain read made after the node's shared
  lock, so it is current.
- `_summary_out(row, node_id)` is one function; S097 adds `schedule` there.
- `meters_with_last` calls `_last_readings` in one place, so S097's rename to `last_readings` is a
  one-line change.
- `pm_plans.py` imports nothing that S097's `pm_jobs.py` would import back, so the import direction
  S097 names (`pm_plans` imports `pm_jobs`) adds no cycle.
- For S097's attention: the plan row is stamped (`updated_*`) only when the plan's own columns
  change, not on an item-only save, as briefed. A job refresh keyed on `updated_at` would miss item
  edits. S097's brief keys on the plan's due fields, so it is not affected.

## Checked and found consistent

- **Migration v51** (`backend/local_db.py`): both tables equal brief § 4.1 column by column: the
  keys, the 7 foreign keys and the 7 CHECKs. The CHECKs are wrapped over more lines but are the
  same. There is no `_PRECONDITIONS` entry (new tables only). `test_migration_v51.py` covers the
  refusals and passes of § 8.1, the ENUM pin, 1062, 1452, a v50 database with rows, and the re-run.
  `test_migration_v50.py` filters to `<= 50`, and the squash test asserts over the later versions
  (BR1-01).
- **Permissions:** `pm_plan:edit` is `("maint_engineer",)`, in `SITE_SCOPED`, with the brief's
  comment. Every write route has `require_perm(EDIT_KEY)`, then `load_node_for_user(…,
  key=EDIT_KEY)` at the node's current site (403 naming the site). The reads have
  `require_perm("equipment:read")` with the node's 404. `meter-choices` and `item-check` have the
  edit key at the site. `can_add` and `can_edit` are `has_perm_at` at the node's site and not
  scrapped. The actor comes from `actor()`, never from the body. The SQL is parameterized, and
  the column names come from code constants. `test_role_matrix` and `test_pm_plan_keys` are
  updated.
- **Locks against the LOCK ORDER notes:** the change takes (6e) `FOR UPDATE` first, then the node
  `LOCK IN SHARE MODE`, then plain reads. The snapshot therefore starts after both locks
  (`transaction` sends a plain `BEGIN`, not `WITH CONSISTENT SNAPSHOT`). The create takes the node
  shared first. The item read for the sync is a plain read after (6e), so it sees every committed
  item write. The notes in `pm_plans.py` and `equipment.py` carry the brief's text. One race stays
  open, as briefed: the meter's ancestor node and the model's meters are not locked, so a meter
  removed between the choice read and the insert can be saved once. D10 blocks the next save that
  sends it.
- **Item sync by id** (`sync_items`): an unknown, inactive or other plan's id is refused with "Item
  N was removed or changed by someone else. Reload the page." The same id twice is refused.
  Positions are 1..n. Only the changed fields and the moved position are updated, and an unsent
  item is deactivated with its position kept. No row is ever deleted.
- **Refusals and boundaries** (§ 5.1, § 5.4): all the texts, the fields and the two phases are
  covered. That includes 120 / 121 months, 3650 / 3651 days, 10 / 11 years, the type's decimals on
  `meter_every` and `last_done_meter`, `last_done_on` from 2000 to today (IST, passed in), the
  operator plan with no assignee, the assignee checked whenever it is sent (D10), `before_use`
  refused (D6), 50 / 51 items and "Item 3: …". `itemBody` and `planBody` send `null` for hidden
  fields, so the page never meets "Only a reading has a unit, limits or a meter."
- **The shared `meters.meters_with_last` and the `readings_sheet` change:** it is the old inner
  code lifted out, with the same queries, and `_nodes_rows` keys every node. The behaviour is the
  same; the sheet's tests are green in the full run.
- **The pure core:** `pm_plans_core.py` imports only cores and `datetime.date` (no clock, no DB, no
  Flask). The routes are a thin shell. The frontend holds no business rule: `kindFromTicks` and the
  body builders only convert, and the API judges every save. The core reuses `parse_number`,
  `masters_core` parsers and `contracts_core.iso_date`; there is no new copy.
- **The database down:** every route goes through `get_db()`, and `test_the_database_down` covers
  the list and the create (503).
- **The phone layout:** the card rows wrap (`overflow-wrap: anywhere`). The page is one column
  below `lg`. The items are a list below `md`. The buttons are full width on a phone. The tap
  targets use `tap-target`. The dialog is `FormModal`, so its body scrolls and its footer stays.
  *Remove item* asks in place, and *Deactivate* asks through `ActiveToggle` with "It makes no more
  jobs.". The `@device` test checks that there is no sideways scroll, with the list or the table by
  width.
- **The browser tests:** every *Automated* check of § 8.4 has a test that asserts what the user
  sees: the card texts, the field messages in view, the order after a save, the inactive list and
  the read-only page. Each item dialog opened gets `expectDialogFits`. Only the fit test carries
  `@device`, which the rule allows.
- **Docs pass:** `notes.json` has the new area and the two tables (moved from `planned`, without
  *kind* and *source template*). `schema.json` and `schema-data.js` are generated, and the check
  exits 0. `Plan.MD` § 3 and § 4.3 are updated. `.claude/CLAUDE.md` has the self-check item (2) and
  the SMTW-Review point of § 8.6. `schema.md` has the new count. No other doc of § Docs to keep
  current is due.
- **Manual checks:** the impl report's `## Manual checks` holds every check of § 8.4, with its
  test, the five **important** ones included. § 8.5 has no real-device check, so
  `device-checks.md` gets no row.
- **Scope:** everything of § 1 is built. Nothing outside it is built, and S095's
  `pm_schedule_core.py` is unchanged.

## Manual browser check for the user

None required: the brief has no real-device check, and every check is automated. At gate B,
KLA may open one plan on a phone to see the page (brief § 8.6 *By screen*).

## Feedback

- hindrance: the step diff has no backend-first order option, so I listed the files by hand with
  `-- <paths>` to follow brief § 9's reading order (1 extra diff call).
- idea: the brief's § 8.2 test list could name each D-rule's failure case (here D10 for the meter),
  so a missing case shows when the list is checked, not only in a reading of the tests
  (`test_pm_plans_api.py`, CR1-02).
