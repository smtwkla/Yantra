```
Step: S015 — Printable asset list
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 20-10-2026
```

Reviewed against: 90284ec + uncommitted S016

# S015 — Staleness review, round s1

**Verdict: no `blocker` or `major` finding. The brief still holds; two nits.
The coder can start once the planner has fixed the wording in BS1-01.**

## What changed since the baseline (a2190f3 + uncommitted S022)

Commits `3b863ad`, `76fccf7`, `90284ec` and the uncommitted S016 work, read
with `git diff -w --ignore-cr-at-eol a2190f3` over the brief's *Where* files
and the modules they call:

| Area | Changed? | Effect on the brief |
|---|---|---|
| `backend/equipment.py` (`list_equipment`, `accessible_unit_ids`, `NODE_JOINS`, `_NODE_COLUMNS`, `_summary`, the labels route, `IST`) | No | None |
| `backend/labels_core.py` (`expand_selection` → `(None, TOO_MANY_LABELS)`) | No | None |
| `backend/auth_utils.py` (`g.user["name"]`), `api_common.actor()` | No | None |
| `backend/config_rbac.py` | Yes (S016): `failure_codes:edit` added | None: `equipment:read` and `equipment:read_all_units` unchanged; the brief changes nothing here |
| `backend/local_db.py` | Yes (S016): migration v11, three failure-code tables | None: S015 has no migration and touches none of those tables |
| `backend/tests/conftest.py` | Yes (S016): `_SEEDED_TABLES`, `uniq.failure_code()` / `failure_label()` | None: additive; `_TABLES` still clears equipment, units, sites for S015's API tests |
| `backend/tests/test_equipment_api.py` (`TestListing`, `TestUnitAccess`) | No | None |
| `frontend/src/stores/masters.js` | Yes (S016): `failureModes`, `failureCauses`, `maintenanceActions` and their `ensure…()` | None: `ensureEquipmentClasses()` / `ensureEquipmentTypes()` unchanged |
| `frontend/src/router/index.js`, `views/EquipmentView.vue`, `views/LabelsPrintView.vue`, `utils/labelSheets.js`, `utils/equipmentLabels.js`, `utils/datetime.js`, `assets/main.css` | No | None |
| `docs/Plan.MD` § 4.1 | Yes: a *Printable asset list (S015, decided 20-10-2026)* bullet | Agrees with the brief's decisions 1–4 and § 2 (CARO 2020) |
| `docs/Plant-Facts.md` | Yes: CARO 2020 not applicable; ISO 9001 a future goal | Agrees with the brief § 2 |
| `tooling/run-tests.bat` | Yes (S022): also runs the deps-audit tests | Acceptance "run-tests.bat green" still means the same thing |

## Findings

### BS1-01 — `nit` — "Depends on: nothing uncommitted" is no longer a true description of the tree

**Problem.** The brief says *Depends on: nothing uncommitted (S010–S014 are
committed)*, and the index row carries *baseline a2190f3 + uncommitted S022*.
Now S022 is committed (`76fccf7`) and **S016 is uncommitted** in the working
tree (`config_rbac.py`, `local_db.py`, `masters.py`, `masters_core.py`,
`conftest.py`, `test_rbac.py`, `stores/masters.js`, `MastersView.vue`, four new
panels, two new test files).

**Why it matters.** S015 does not need any of S016's code, and the two steps
share no file that S015 *edits* (S015 only *calls* `stores/masters.js` and
`conftest.py`'s fixtures). So nothing in the design changes. But the coder's
working-tree diff, and the code review of it, will contain S016's changes
unless the user commits S016 first, and the sentence as written tells the
coder the tree is clean when it is not.

**Options.**
1. Reword to: *Depends on: nothing. S016 is uncommitted in the tree; the two
   steps share no edited file, so S016 is committed first (or the user
   separates the diffs at commit).* Set `Baseline: 90284ec + uncommitted S016`
   after this check, as README § Stale brief check step 2 says.
2. Leave the sentence and rely on the index row.

**Recommendation.** Option 1: one line in the brief, no change to what the
user approved.

### BS1-02 — `nit` (not a staleness issue; noticed while verifying BR1-09) — how `printed_at` gets its shape

**Problem.** The brief says `printed_at` is `datetime.now(IST)` "in the API's
usual datetime shape (`YYYY-MM-DDTHH:MM:SS+05:30`)". That shape is not made by
`jsonify`: Flask's default JSON provider renders a `datetime` as an RFC 822
date (`Tue, 20 Oct 2026 10:05:33 GMT`-style). The API's shape comes from
`db_helpers.row_to_dict`, which calls `value.isoformat()` on DB rows. A
`datetime.now(IST)` also carries microseconds, so a bare `isoformat()` gives
`…T10:05:33.123456+05:30`. `formatDateTime` reads only the first sixteen
characters, so the page would still show the right time, but the response
would not be the shape the brief states, and the API test "`printed_at` is
present" would not catch it.

**Options.**
1. State in § 3: `printed_at` is `datetime.now(IST).isoformat(timespec="seconds")`
   (the same `isoformat` `row_to_dict` uses, to the second), and have the API
   test assert the shape with a regex (`^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+05:30$`).
2. Leave it to the coder.

**Recommendation.** Option 1: one clause and one assertion, so the coder does
not choose a format alone (CLAUDE-COMMON *Explicit over implicit*).

## Checked and found consistent

- `list_equipment` still builds the site / unit / class / type / status /
  criticality conditions with `int_arg` / `enum_arg`, reads
  `include_scrapped != "1"`, and keeps search (`q`) and `level` separately, so
  the `_list_filters()` move is as described (§ 3, BR1-08).
- `accessible_unit_ids(cur)` returns `None` for admin / `equipment:read_all_units`
  and a set otherwise; the list returns the empty result before any query when
  the set is empty, as the brief says the new route will (§ 3 step 1).
- `_NODE_COLUMNS` holds `e.serial_no`, `e.year`, `s.code AS site_code`,
  `u.code AS unit_code` but **not** the site and unit names, so `s.name AS
  site_name, u.name AS unit_name` are indeed the only new columns (BR1-11).
- `_summary` returns code, name, class code, type name, `model_label`,
  `effective_criticality`, status (plus ids and path), as § 3 relies on.
- The labels route handles `with_parts` with `e.id IN … OR e.parent_id IN …
  OR p.parent_id IN …` through `NODE_JOINS`, and turns `expand_selection`'s
  `(None, message)` into `ApiError(message, 400, "ids")`: the pattern § 3
  steps 4–5 copy.
- `labels_core.expand_selection` returns `(None, TOO_MANY_LABELS)` on the cap
  (BR1-04 pattern).
- `IST` is defined in `equipment.py`; `actor()` in `api_common.py` and
  `g.user["name"]` (from `make_user`) exist for `printed_by` (BR1-09).
- `config_rbac.py`: `equipment:read` is `("*",)` and site-scoped;
  `equipment:read_all_units` is `it_admin`'s. S016's `failure_codes:edit` does
  not touch them; "No change to `config_rbac.py`" still holds.
- `frontend/src/stores/masters.js` still exports `ensureEquipmentClasses()` and
  `ensureEquipmentTypes()` with the same signature; S016's additions are
  separate refs and functions.
- `utils/equipmentLabels.js` exports `STATUS_LABELS`; `utils/datetime.js`
  exports `formatDateTime`; `utils/labelSheets.js` builds `/labels?ids=…&parts=1`,
  the pattern for `parts=1` / `check=1`.
- `EquipmentView.vue` uses the query keys `site_id`, `unit_id`, `class_id`,
  `type_id`, `status`, `criticality`, `q`, `level`, `page`, `scrapped`, maps
  `scrapped=1` or `status=scrapped` to `include_scrapped=1`, and opens the
  labels page with `window.open(router.resolve(...).href, "_blank")`, as § 3
  says the new button will.
- `LabelsPrintView.vue` adds the `@page` rule in `onMounted` and removes it in
  `onUnmounted` (BR1-05 pattern); `main.css` has the `.no-print` print reset.
- Router: `/labels` has `meta.title "QR labels"`, the pattern for
  `/asset-list` → "Asset list".
- `TestListing` and `TestUnitAccess` exist in `test_equipment_api.py` and are
  unchanged, so they still cover the `_list_filters` move.
- Plan.MD § 4.1 now records S015's decisions (filters choose machines, parts
  optional, checklist, Yantra code + serial as identity, no export, CARO 2020
  n/a) in the same terms as the brief; Plant-Facts records CARO 2020 as not
  applicable (brief § 2).
- No test the brief relies on was renamed or removed; S016's `test_rbac.py`
  edits add `failure_codes:edit` to the role matrix and do not involve any
  key S015 uses.
