```
Step: S067 — Improvement record from tickets
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 30-10-2026
```

# S067 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** All three round-1 findings are fixed.
The fix round brings in no new fault. This round has no new finding.

Files re-read: `backend/tickets.py` (`_improvement_fields`, `improvement_links`,
`_readable_improvement_links`, and the imports), `backend/improvements.py` (`_visible_condition`,
`_IMPROVEMENT_FROM`, `_read_improvement`), the new test in `backend/tests/test_improvements_api.py`,
the `equipment.py` LOCK ORDER note, `docs/Plan.MD` § 3, the impl report's summary and § Fix rounds,
and brief § 10 A1. The fix round's diff (`step_snapshot.py diff S067 --from-round 1`) also lists
`docs/roadmap/R05-rca.md`, `docs/steps/INDEX.md` and S069's brief. Those are the orchestrator's
edits for other steps, not S067's fix, so I did not review them.

## Test runs

- **Backend suite** (`YANTRA_TEST_RUN=s067cr2 tooling/run-backend-tests.bat`): 3461 passed,
  PASSED. The fix round changed only backend code and docs, so I ran only the backend suite.
  The coder's run of all suites (`s067f1`) was green: backend 3461, frontend 285, tooling 185.
- **Browser:** I re-ran nothing, and the coder ran nothing. That is correct: no screen, API shape
  or shared frontend file changed in the fix round.

## Findings of round 1

| ID | Severity | Status |
|---|---|---|
| CR1-01 | minor | Fixed, per A1 |
| CR1-02 | nit | Fixed |
| CR1-03 | nit | Fixed |

- **CR1-01:** I checked the fix against A1.
  - The ticket detail's `improvements` now comes from `_readable_improvement_links`
    (`tickets.py:466-480`). It joins `equipment m ON m.id = i.equipment_id` and applies
    `unit_access_condition(cur, "improvement:read", "i.unit_id", "m.unit_id")`. That is the same
    predicate and the same join as `improvements._visible_condition` and `_IMPROVEMENT_FROM`, which
    `_read_improvement` uses. So every listed link opens.
  - A `None` predicate (no unit) gives an empty list. The placeholders are in the right order:
    `ticket_id` first, then the predicate's ids. The SQL joins only constants.
  - `improvement_links` stays unfiltered and still feeds `link_error` for `can_start_improvement`
    and for start and add in `improvements.py`. Both queries share one SELECT text
    (`_IMPROVEMENT_LINKS`).
  - The unfiltered read now runs only for a holder of `improvement:edit`. That is the only case
    where `can_start` reads it, so the result does not change.
  - The new test `test_only_the_improvements_the_reader_can_open` covers both of A1's cases: an
    operator of the second unit alone gets 404 on the improvement and an empty list, and an
    operator of both units sees the link. The fix round gives the red result without the fix (the
    assertion text is quoted).
  - `docs/Plan.MD` § 3 now states the rule, with A1 named.
- **CR1-02:** the report's summary (lines 14-15) now says that there are twelve decisions, that
  D-1 to D-5 depart from the brief's wording, and that none changes the API.
- **CR1-03:** the `equipment.py` LOCK ORDER note now names an edit's shared lock on the new
  lead's person row. It is a comment only, so no test is due.

## Checked and found consistent

- **The fix round's own diff:** it adds no new lock and no new write. The ticket page's reads stay
  plain, as the tickets.py LOCK ORDER note requires. The import of `unit_access_condition` was
  there already (D-1).
- **A1 against the API:** the shape of § 6 is unchanged; only which items appear changed. S068
  needs no change.
- **Docs pass:** `docs/Plan.MD` is updated. No migration changed, so the schema docs need no
  change.

## Manual browser checks for the user

None in this step: it has no screen.

## Feedback

- hindrance: `diff S067 --from-round 1` mixes in the orchestrator's edits to other steps' files
  (S069's brief, `docs/roadmap/R05-rca.md`, `docs/steps/INDEX.md`), 98 of the 116 changed lines.
  I had to name paths after `--` to see only the fix (`step_snapshot.py diff S067 --from-round 1 --stat`).
