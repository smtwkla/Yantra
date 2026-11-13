```
Step: S104 — PM templates: one path
Doc: code-review r8
Author: Code reviewer (Opus)
Date: 13-11-2026
```

# S104 — code review, round 8 (a check of fix round 7)

**Verdict: no `blocker` or `major` finding is open.** The three findings of round 7 are fixed. The code moved from
`meters.py` to `equipment.py` works as it did before. Every caller and every test patch still finds it, and the LOCK
ORDER notes still sit with the code they describe. I found one `minor` finding in the fix round's own diff: the new
`equipment.links_in_use` repeats the judgement that `pm_jobs.meters_on_paths` already makes (CR8-01). I also found
one nit about the move's lock note.

This round checks fix round 7 only (`step_snapshot.py diff S104 --from-round 8`: 5 files, 123 lines added and 57
removed; snapshot round 9, 543f2c5).

## Test runs (this review, `YANTRA_TEST_RUN=s104cr8`)

| Run | Result |
|---|---|
| `tooling\run-backend-tests.bat` with the changed test files and the callers' tests: `test_equipment_api.py`, `test_meters_api.py`, `test_pm_plans_api.py`, `test_pm_jobs_api.py`, `test_pm_work_api.py`, `test_pm_templates_api.py`, `test_pm_generate.py`, `test_readings_api.py`, `test_meter_types_api.py` | **507 passed** (34 s) |
| Line width of the four changed `.py` files (counted in characters) | no line over 120 |
| All suites | not re-run. The coder's `tooling\run-tests.bat` was green after the round (backend 5387, frontend 472, tooling 258). The round changed only `backend/` and `docs/Plan.MD`, and I ran the backend files above. |
| Schema docs, build, browser | not due. The round touched no migration, no `docs/schema/`, and no frontend file. No browser spec covers the move's question with a link not in use, and no finding of mine needs a browser run. |

## Findings of earlier rounds

| ID | Status | Verified by |
|---|---|---|
| CR1-01 to CR6-01 | Fixed (earlier rounds) | not re-checked |
| CR7-01 (minor) | **Fixed** (by the orchestrator) | `docs/Plan.MD:29` now says "a part may link its parent's or grandparent's meter on its Meters card, S104 A1 13-11-2026; the template's parent tick is gone". `docs/Plan.MD:683` keeps the gate A record and marks it, inside the parenthesis: "*replaced 13-11-2026 by S104 A1: the tick is gone, a part links a meter on its Meters card*". The wording is plain and correct. A search of `docs/Plan.MD`, `docs/Maintenance-Philosophy.md`, `docs/schema.md` and `.claude/CLAUDE.md` finds no other text about the parent tick. |
| CR7-02 (minor) | **Fixed** | `test_meters_api.py` `test_who_may_remove_a_link`: a technician gets 403, an engineer of another unit 404, and the mixed user 403. After each refusal the link is still on the card and the history has only `meter_linked`. After the scrap, DELETE gives 409 with `SCRAPPED`. The test has no red result, and the report gives the reason: the route already holds the key and `lock_node`, so the test pins existing behaviour. That reason is acceptable. |
| CR7-03 (minor) | **Fixed** | `equipment._links_a_move_removes` asks `link_plan_names` only about the broken links that `links_in_use` keeps. `plans.get(link["id"], [])` handles the links left out, and `link_plan_names([])` returns `{}` without a query. Every broken link is still listed in the 409 and deleted on confirm. `TestReparentMeterLinks.test_a_link_not_in_use_is_removed_but_no_plan_is_named` shows both moves: before the model gains the type, the plan is named; after, the 409 text ends at "from EAAA001." The link row stays until the confirmed move. The report gives the red result (the old call put back: 1 failed, 4 passed). |

## Findings

### CR8-01 (minor) — `links_in_use` repeats the link judgement of `pm_jobs.meters_on_paths`

`backend/equipment.py:698` (`links_in_use`); the existing code is `backend/pm_jobs.py:222` (`meters_on_paths`).

- **Problem.** `meters_on_paths` already reads any number of nodes with their parent and grandparent (one joined
  query), calls `meters_in_force` on all of them, and judges each node's links with `meters_core.link_states`. Its
  `links` answer, `{node_id: {meter_type_id: source_id}}`, holds exactly the links in use. The new `links_in_use`
  does the same work a second time: three `nodes_by_id` queries for the parts, parents and grandparents, then
  `meters_in_force`, then the same `link_states` loop. The coder could not import `pm_jobs` from `equipment.py`,
  because `pm_jobs` imports `meters`, which imports `equipment`. But the round already moved `meters_in_force` into
  `equipment.py`, and `meters_on_paths` needs nothing else that `equipment.py` lacks (`read_meter_links`, `marks`,
  `link_states`). So `meters_on_paths` itself can move. This is CLAUDE-COMMON's DRY rule: "a new helper that
  duplicates one already there".
- **Failure scenario.** A later step changes when a link is in use. For example, R03.19's class links add a fourth
  reason, or the path grows to three levels. The coder changes `meters_on_paths`, which the PM card, *Start* and the
  settle use. `links_in_use` keeps the old rule. The move's question then names plans that the card says do not use
  the link, or leaves out plans that do. This is CR7-03's fault again, and the suite stays green, because
  `TestReparentMeterLinks` tests only the `own` reason.
- **Fix.**
  1. Move `meters_on_paths` and `_types_by_node` from `pm_jobs.py` to `equipment.py`, next to `meters_in_force`.
  2. In `pm_jobs.py`, import them from `equipment`. Also import `meters_in_force` from `equipment`, its home, not
     through `meters`.
  3. Remove `links_in_use`. In `_links_a_move_removes`, take
     `in_use = meters_on_paths(cur, sorted({link["equipment_id"] for link in broken}))["links"]` and keep the broken
     links where `in_use.get(link["equipment_id"], {}).get(link["meter_type_id"]) == link["source_equipment_id"]`.
     This costs one more query (`read_meter_links` on the parts), which does not matter on a move.
  4. `test_pm_plans_api.py`'s `test_the_card_resolves_every_plan_in_one_pass` patches `pm_jobs.meters_in_force`.
     After the move, it must patch `equipment.meters_in_force`, or it no longer counts the calls. Check that the test
     fails if the patch target is left as it is.
  5. Run `test_equipment_api.py`, `test_meters_api.py`, `test_pm_plans_api.py`, `test_pm_jobs_api.py` and
     `test_pm_work_api.py`.

## Nits

- **CR8-02** (nit) `backend/equipment.py:145`: the move's sentence in the LOCK ORDER note lists its plain reads as
  "the node's parts, their links and the plans that use them". Since CR7-03 it also reads the parts' parents and
  grandparents and their meters in force, to judge which links are in use. Add those words, so the note names every
  plain read the move makes (they are plain, so the lock order does not change).

## The moved code (`meters_in_force`, `nodes_meter_rows`, `nodes_by_id`)

- **Behaviour unchanged.** I compared the removed and the added blocks line by line. `_NODE_METER_SELECT`,
  `nodes_meter_rows` (was `meters._nodes_rows`), `nodes_by_id` (was `meters._nodes_by_id`) and `meters_in_force`
  have the same SQL, the same parameters and the same output. Only the names became public, and the docstring of
  `meters_in_force` names one more caller. `equipment.py` gains the imports it needs: `read_models_meters` from
  `masters`, and `effective_meters`, `link_states` and `meter_type_of` from `meters_core`. `masters` imports neither
  `equipment` nor `meters`, so the move makes no import cycle. `meters.py` no longer imports `read_models_meters`.
  It still uses `effective_meters` and `meter_type_of` itself (`_meters_of`, `_linked_out`, line 792), so those
  imports stay.
- **Callers.** `meters.py` uses the three names through its import at lines 67–68: `_node_rows`, `_meters_out`,
  `_linked_by`, `meter_link_choices` and `meters_with_last`. `pm_jobs.py:92` still imports `meters_in_force` from
  `meters`, which works because `meters` re-exports it (CR8-01 step 2 moves that import). No module calls the old
  private names: a search of `backend/` finds no `_nodes_rows` and no `_nodes_by_id`.
- **Test patches.** No test patches `meters.*` or `equipment.*` by string. `test_pm_plans_api.py:240–246` patches
  `pm_jobs.meters_in_force` and calls `meters.meters_in_force` inside the counter, which is the same function
  object. That test is green in my run.
- **The LOCK ORDER notes.** `meters.py`'s module note (*Locks* and *Meter links*) names no moved function, and
  the code it describes (the link routes, `lock_node`, `_lock_up_to`) did not move. `equipment.py`'s LOCK ORDER
  note covers the move's reads (apart from CR8-02's words). The moved functions take no lock: they are plain reads,
  so the lock order is the same wherever they live.

## Checked and found consistent

- **`links_in_use` gives the right answer.** A source that is not above the part gets `NOT_ABOVE` before
  `types_by_node` is read, so a source outside the nodes read does not cause a `KeyError`. A part's parent and
  grandparent come from plain rows of the tree as it is before the move, and the plans run on that tree until the
  move commits (decision 2 of round 7). A part always has a parent (a link is never on a machine), and
  `parents.get(None, {})` covers the missing case anyway. The docstring's query count (three for the nodes, two for
  the meters) is right.
- **The 409 text** comes from the unchanged `meters_core.move_warning`, which leaves out the plans' sentences when
  the list is empty. The new test asserts the full text.
- **Scope.** The round changes only what the three findings ask, plus the forced move of code, which the report
  states as a decision taken. No screen, route, permission, rule or schema changed, so the round owes no docs
  (the report says so).
- **Red, then green.** CR7-03 has its red result. CR7-02 gives its reason for having none.

**Files re-read:** `backend/equipment.py` (the LOCK ORDER note, lines 9–160; the meter-link block, lines 618–760),
`backend/meters.py` (the module note, the imports, `_node_rows`, `_meters_of`, `_meters_out`, `_linked_out`,
`_linked_by`), `backend/meters_core.py` (`link_states`, `broken_links`, `move_warning`), `backend/pm_jobs.py`
(`meters_on_paths`, `_types_by_node`, `plan_resolutions`), the round's diffs of `test_equipment_api.py` and
`test_meters_api.py` with their helpers, `conftest.py` (`make_unit`, `user_with_units`), and `docs/Plan.MD` lines 29
and 683.

## Still to check by hand in a browser

Nothing new. The round changed no screen.

## Feedback

- waste: the backend wrapper started from Git Bash with `cd tooling && cmd //c run-backend-tests.bat` printed
  "'run-backend-tests.bat' is not recognized" and still exited 0. The wrapper ran only with the path given from the
  repo root (`cmd //c "tooling\\run-backend-tests.bat …"`). A line in the Unit tests setting ("from Git Bash:
  `cmd //c "tooling\\run-backend-tests.bat …"` from the repo root") would save the retry, and a reviewer who reads
  only the exit code would have taken it as a pass.
- rule: when a fix moves code to break an import cycle, the coder could check whether a function that already
  does the job can move instead (here `meters_on_paths` with `meters_in_force`). A sentence in the coder's *Decisions
  taken* form ("the existing helper that does this, if any, and why it is not reused") would show CR8-01 before
  review.
