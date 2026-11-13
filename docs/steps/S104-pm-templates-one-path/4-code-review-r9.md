```
Step: S104 — PM templates: one path
Doc: code-review r9
Author: Code reviewer (Opus)
Date: 13-11-2026
```

# S104 — code review, round 9 (a check of fix round 8)

**Verdict: no `blocker` or `major` finding is open.** Both findings of round 8 are fixed. `meters_on_paths` and
`types_by_node` now live in `equipment.py`, `links_in_use` is gone, and the move's question takes the links in use
from `meters_on_paths`. The behaviour is the same as before, the move makes no import cycle, and no stale name is
left. I found one nit in the new docstring.

This round checks fix round 8 only (`step_snapshot.py diff S104 --from-round 9`: 3 files, 56 lines added and 68
removed; snapshot round 10, 0bdc56c).

## Test runs (this review, `YANTRA_TEST_RUN=s104cr9`)

| Run | Result |
|---|---|
| `tooling\run-backend-tests.bat` with the changed test file and the callers' tests: `test_equipment_api.py`, `test_meters_api.py`, `test_pm_plans_api.py`, `test_pm_jobs_api.py`, `test_pm_work_api.py`, `test_pm_templates_api.py`, `test_pm_generate.py`, `test_readings_api.py`, `test_meter_types_api.py` | **507 passed** (32 s) |
| Line width of the three changed `.py` files | no line over 120 |
| All suites | not re-run. The round changed only `backend/`, and I ran the backend files above. The coder's `tooling\run-tests.bat` after the round was green (backend 5387, frontend 472, tooling 258). |
| Schema docs, build, browser | not due. The round touched no migration, no `docs/schema/` and no frontend file. |

## Findings of earlier rounds

| ID | Status | Verified by |
|---|---|---|
| CR1-01 to CR7-03 | Fixed (earlier rounds) | not re-checked |
| CR8-01 (minor) | **Fixed** | See *Behaviour unchanged* below. `pm_jobs.py:89` imports `meters_on_paths` and `types_by_node` from `equipment`; `equipment.py:762` uses `meters_on_paths(...)["links"]` and keeps a broken link for the plan question only when the source in use equals the link's source. The test patch moved to `equipment.meters_in_force` and `equipment.read_meter_links`, with the real functions kept in locals so the counters do not call themselves. The report gives the red result (the old target fails with `AttributeError`). |
| CR8-02 (nit) | **Fixed** | `equipment.py:146–147`: the move's plain reads now name the parts' parents and grandparents with their meters in force (`meters_on_paths`). |

## Nits

- **CR9-01** (nit) `backend/equipment.py:706–708`: the docstring calls `meters_on_paths` "the one judgement of
  which links are in use". The Meters card does not use it: `meters._meters_out` (line 126–131) and
  `meters._linked_by` judge their own node's links with `meters_core.link_states` directly. Name
  `meters_core.link_states` as the one rule, and say that the PM side and the move read it through this function,
  so a later change to which links are in use is made in `link_states`, not here.

## Behaviour unchanged

- **The code moved as it was.** I compared the removed block of `pm_jobs.py` with the added block of `equipment.py`
  line by line. The SQL, the parameters and the answer are the same. The only changes are `_types_by_node` →
  `types_by_node` (public, now imported across modules; the report states this as a decision) and the longer
  docstring.
- **The move's question gives the same answer.** `links_in_use` judged each broken link alone with
  `link_states(types[part], [link], [parent, grandparent], types)`. `meters_on_paths` judges all of a part's links
  in one call with the same arguments (`paths[part][1:]` is the parent and grandparent). `link_states` judges each
  link by its own type and source only, so the result per link is the same. `uq_node_meter_links (equipment_id,
  meter_type_id)` gives a part at most one link per type, so comparing `in_use[part][type]` with the link's source
  picks out exactly the broken links in use. A part that is not in `in_use` (no links read) falls to `{}` and is
  not used. The 409 still lists every broken link, and the confirmed move still deletes every broken link.
  `TestReparentMeterLinks.test_a_link_not_in_use_is_removed_but_no_plan_is_named` is green in my run.
- **No import cycle.** `equipment.py` imports no PM shell module (only `pm_jobs_core`, `pm_links_core` and
  `pm_work_core`); `pm_jobs` imports `equipment` and `meters`; `meters` imports `equipment`. Every name the moved
  code needs (`marks`, `read_meter_links`, `meters_in_force`, `link_states`) is already in `equipment.py`.
- **No stale references.** A search of the repo (outside the step folders) finds no `links_in_use`, no
  `_types_by_node`, and no `pm_jobs.meters_on_paths`, `pm_jobs.meters_in_force` or `pm_jobs.read_meter_links`.
  `pm_jobs.py` no longer uses `meters_in_force`, `read_meter_links` or `link_states`, so dropping those imports is
  right. No module imports `meters_in_force` from `meters` any more; `pm_work.py` uses `import meters` for other
  names. `nodes_by_id` stays in `equipment.py` for `meters.py`. The parameter names `types_by_node` in
  `meters_core.link_states` and `pm_links_core.resolve_meters` are local and do not clash with the new import.
- **The test patch still counts.** `meters_on_paths` looks up `meters_in_force` and `read_meter_links` in the
  `equipment` module, so the patched names are the ones it calls; the card's own `meters.meters_in_force` binding
  was not counted before either. The test still asserts one call of each read for three plans.

## Checked and found consistent

- **Scope.** The round changes only what CR8-01 and CR8-02 ask. No screen, route, permission, rule or schema
  changed, so the round owes no docs, and the report says so. `.claude/CLAUDE.md` names neither moved function.
- **Lock order.** The moved functions are plain reads and take no lock. The move's lock note in `equipment.py` now
  names every plain read it makes.
- **Red, then green.** CR8-01's test change has its red result. CR8-02 is a comment and needs none.

**Files re-read:** `backend/equipment.py` (imports; the LOCK ORDER note's move sentence, lines 140–150; the
meter-link block, lines 625–770), `backend/pm_jobs.py` (imports, `plan_resolutions`), `backend/meters.py` (imports,
`_meters_out`, `_linked_by`), `backend/meters_core.py` (`link_states`), `backend/local_db.py` (the
`node_meter_links` table, for its unique key), and the round's diff of `backend/tests/test_pm_plans_api.py`.

## Still to check by hand in a browser

Nothing new. The round changed no screen.

## Feedback

- waste: none this round. The orchestrator's prompt named the test files and the run name, so the review needed one
  backend run and no whole-suite run.
