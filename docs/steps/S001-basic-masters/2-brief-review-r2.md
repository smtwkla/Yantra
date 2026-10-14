```
Step: S001 — Basic masters
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 13-10-2026
```

# S001 — Brief review, round 2

Reviewed the revised `1-brief.md` (13-10-2026, after r1) against `2-brief-review-r1.md`, Plan.MD,
Plant-Facts § 2, the base document and the current code.

**Verdict: no blocker or major finding is open. The brief passes gate 1 from the reviewer's side.**
Approval is the user's; § 9.3 lists the two points that changed since the first draft (codes
correctable until used; one extra permission key `masters:read_senior`) and asks the user to confirm
them. The findings below are one minor and five nits. None gates approval; the planner can answer
them in the same pass as the user's confirmation.

## Round-1 findings — verification

Every r1 finding is answered `Accepted` in the Review log. I checked that each change is actually in
the text, not only in the log:

| Finding | In the brief? | Note |
|---|---|---|
| BR1-01 frozen once in use | Yes — § 5 table, lock-then-count, § 7, § 8 tests, S003 pointer | The InnoDB claim is right: a child insert takes a shared lock on the parent row for the FK check, so it waits behind the parent's `FOR UPDATE`. See BR2-01 for a gap in what "the code" covers. |
| BR1-02 access-change trail | Yes — § 2 A.5.18, § 5 log line after commit, § 7, `caplog` test | Logging after commit is the right order. |
| BR1-03 broken tests | Yes — § 3 lists `test_modules.py` and `test_auth.py` | |
| BR1-04 inactive unit with rows | Yes — rows kept, `active` returned, held-inactive may stay, new-inactive → 400 | Consistent with the pick-list showing active units only. |
| BR1-05 409 from the index | Yes — § 5 | See BR2-04 for the `field`. |
| BR1-06 `get_db()` home | Yes — `db_helpers.py`, `local_db` Flask-free, `transaction()` beside it | |
| BR1-07 read key | Yes — `masters:read_senior`, § 3, § 6, § 7, Plan § 3 row | |
| BR1-08 standards | Yes — A.5.15 / A.5.18 / A.5.3; ISO 55001 § 7.5–7.6 (2014); functional locations | Citations now correct. |
| BR1-09 warehouse uniqueness | Yes — UNIQUE, stripped not upper-cased, empty → NULL | |
| BR1-10 API details | Yes — `field` in `api.js`, 201/200, `errors` list, all units | |
| BR1-11 usernames | Yes — regex, lower-case on both sides for S002 | |
| BR1-12 toolbar | Yes — `ModuleToolbar.vue`, data-driven, hidden at one section | |
| BR1-13 code hint | Yes | |
| BR1-14 test hygiene | Yes — § 8 | |
| BR1-15 small points | Yes — ids, audit convention, order, unit min length 2 | The audit convention (no `ON UPDATE`, actor and time set together) is a good rule to fix now for all tables. |
| BR1-16 status | Yes — `In review`, index row updated | |

---

## Minor

### BR2-01 — A unit's `site_id` is part of its full code but is outside the frozen rule — `minor`

§ 5 lists the fields that can always be edited (`name`, `address`, `oneerp_warehouse`, `active`)
and makes `code` changeable while unreferenced. `site_id` is in neither list, so by omission it is
never editable. But `site_id` is half of the full code `SITE.UNIT`: a unit created under the wrong
site during data load is the same typo case BR1-01 was accepted for, and under this text the only
remedy is deactivate-and-recreate, which the frozen rule was meant to avoid.

Apply the frozen rule to `site_id` exactly as to `code`: changeable while the unit has no
`user_units` rows (and, from S002, no equipment), 409 "unit is in use" otherwise, inside the same
`transaction()` with the same row lock; the inactive-site check (§ 5 Activation) applies to the new
site. Or state explicitly that a unit never changes site, with the reason. Add a test either way.

---

## Nits

### BR2-02 — § 1 "Nothing is ever hard-deleted" is no longer exact — `nit`

Unit-access rows are deleted and re-inserted on every save (§ 5). Reword § 1: no *master record* is
hard-deleted; unit-access rows are current state, replaced on save, with the change logged.

### BR2-03 — Say why site and unit codes freeze — `nit`

§ 7 gives the reason as "once anything depends on the code". For a class that is literally true
(the prefix sits inside every equipment code). For a site or unit nothing stored depends on the
code — children reference by `id`, and the full path is derived. What a rename actually disturbs is
outside the DB: OneERP warehouse names mirror `SITE.UNIT` (Plan § 1), people's habits, printed
lists, and the path snapshots S003 will keep. That is **change control** (ISO 55001), not
referential integrity. One sentence in § 5 or § 7 saying so keeps the project owner's mental model
right: the freeze is a policy, not a constraint the database would otherwise break.

### BR2-04 — Which key collided, and the `field` for 409 — `nit`

Three UNIQUE keys share error 1062. MariaDB's message names the key
(`Duplicate entry 'X' for key 'code'`), and an unnamed composite key is named after its first column
(`site_id`), which is misleading. Name the indexes in the migration
(`UNIQUE KEY uq_units_site_code (site_id, code)`, `uq_units_warehouse (oneerp_warehouse)`, …) and
let the shell map the key name to a `field` and a plain message ("A unit with this code already
exists at this site"). Otherwise the user sees a generic 409 for two different mistakes.

### BR2-05 — Small gaps in the rules and tests — `nit`

- PUT body with `code` **omitted**: say it means "unchanged" (the text covers equal and different
  only).
- Add the happy path "a unit with no access rows can change its code" (the tests list the site
  case and the two 409 cases).
- The counter fixture must also give unique `oneerp_warehouse` values, now that the column is
  UNIQUE.

### BR2-06 — Record the frozen-code rule in Plan.MD — `nit`

§ 3 Docs says only the `masters:read_senior` row needs adding to Plan.MD. The frozen-once-in-use
rule is not in Plan.MD either (Plan § 4.1 speaks only of equipment-code permanence). Once the user
confirms § 9.3, add one line under Plan § 4.1 "Sites and units" (or § 1 Decisions, dated), so the
next brief does not have to rediscover it here.

---

## Checked and found consistent

- Role matrix after the change: operator / technician / storekeeper `masters:read`; engineer adds
  `equipment:edit`; manager adds `settings:read`; IT admin `masters:read`, `masters:read_senior`,
  `masters:edit`, `equipment:edit`, `settings:read`, `settings:edit`. Matches Plan § 3 plus the new
  key; `navigation.test.js` lists and `test_rbac.py` matrix need exactly that.
- `transaction()` on a pooled autocommit connection: PyMySQL `begin()` opens the transaction,
  `SELECT … FOR UPDATE` is valid inside it, and DBUtils rolls back on return to the pool, so a
  failed request cannot leak a lock.
- The log line is written after commit, so a rolled-back change is never logged as done.
- Unit-access pick-list (active units from `ensureUnits()`) plus `active` on held units from
  `GET /user-units` is enough for the greyed-out display without a second endpoint.
- Audit convention, `id` type, list order, regexes and the acceptance data all agree with Plan § 5
  and Plant-Facts § 2.
