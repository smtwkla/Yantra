```
Step: S070 — Countermeasures
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 30-10-2026
```

# S070 — Code review, round 2 (verify)

**Verdict: no `blocker` or `major` finding is open.** The fix round fixes CR1-01, CR1-02, CR1-03
and CR1-05. CR1-04 is deferred to S072 as its amendment A1. The `_scoped_branch` refactor is
behaviour-neutral. The same round also fixes S069's CR2-01 and CR2-02. This round adds one nit,
on the text of S069's impl report.

## Tests run

- **Unit suites** (`YANTRA_TEST_RUN=s070cr2 tooling\run-tests.bat`): backend 3666 passed,
  frontend 321 passed, tooling 185 passed. All suites passed. I ran all suites because the round
  changed code in the backend and the frontend, and because the coder's backend run left out two
  files that test the removed list (`test_removed_documents_api.py`, `test_site_checks_api.py`).
  Both passed in this run. The backend count is round 1's 3665 plus the new CR1-03 test. The
  frontend count includes the S071 coder's work in the same tree.
- **Frontend build** (`npx vite build`, output to the session scratchpad): built, with only the
  known chunk-size warning.
- **Browser tests**: none re-run. No finding of mine needs one. The coder's targeted run is the
  right one: `e2e/improvements.spec.js` (the changed spec and `WhyDialog.vue`'s screen),
  `e2e/settings.spec.js` (the removed-documents card behind `_removed_branches`) and
  `e2e/screens.spec.js`: 33 passed, 1 skipped (the existing per-device skip). The round changed
  no shared frontend file.

## Status of the round-1 findings

| Finding | Status | Checked |
|---|---|---|
| CR1-01 (minor) | **Fixed** | `improvements_core.py:108` reads "Change an open one instead." The core test and `test_the_31st_is_409` assert the new text. The rule is unchanged. |
| CR1-02 (minor) | **Fixed** | `documents.py:528-561`. One helper; the node, ticket and countermeasure branches go through it. See the note below. |
| CR1-03 (nit) | Fixed | `done_time_error` compares with `problem_at` cut to the minute. The new core test has its red result in the report. The FUTURE_SKEW case (a *Now* tick on a ticket raised ahead of the clock) is not answered. It is rare, and I raise no finding. |
| CR1-04 (nit) | Deferred | To S072 as amendment A1. Accepted. |
| CR1-05 (nit) | Fixed | `app.py:176` names four owners and the countermeasure route. |

### CR1-02: the refactor is behaviour-neutral

I compared the old three blocks with `_scoped_branch` term by term:

- The conditions start from a copy of `common` and `common_params`, as before. No branch shares a
  list with another.
- The search condition and its three parameters come next, in the same order, only when
  `pattern` is set.
- The unit condition and the sorted unit ids come last, only when `unit_ids` is not `None`.
  The empty case is still left out by the outer `if unit_ids is None or unit_ids`. So a user with
  the purge key at no unit still gets only the model branch, and never an empty `IN ()`.
- The three triples carry the old columns: node `e.code` / `u.id`, ticket `t.serial` /
  `t.unit_id`, countermeasure `i.serial` / `i.unit_id`. The branch order is the same, so the
  UNION's parameter order is the same.
- The f-strings put in only code constants and placeholders. No value from the request reaches
  the SQL text.
- The model branch is unchanged.

The tests agree: `test_documents_api.py`, `test_removed_documents_api.py` and
`test_site_checks_api.py` pass, including the countermeasure row hidden from a manager of
another site (`test_documents_api.py:812-814`).

## S069 findings fixed in this round

Note for S069: both round-2 nits are fixed.

- **S069 CR2-01: fixed.** The first S069 browser test ends with a text-only *Save why* on why 2.
  It takes the `PUT` with `page.waitForRequest` before the save and asserts that `postDataJSON()`
  has no `position` (`improvements.spec.js:268-275`). This proves the dialog's side of A1. The
  report gives the reason for no red run: A1's code was already correct.
- **S069 CR2-02: fixed.** The `v-else-if` refusal line and its comment are gone from
  `WhyDialog.vue`. A chain of one has no select and sends no `position`, so nothing lost a place
  to show a message.

## Nits

- **CR2-01** (nit) `docs/steps/S069-improvement-why-why/3-impl-report.md:237-282`: the edit removed
  the broken characters instead of putting back the dashes and ellipses. Lines now read
  "**CR1-01 (minor)  Fixed.**" and `"cause_group": , "active": }`, and the file has two
  `## Feedback` headings and a `#####` round heading under `### Round 1`. Put back "—" and "…",
  make the round heading `### Round 2`, and keep one `## Feedback` per run under its own section
  heading.

## Manual checks

None for the user from this round. S070 has no screen change, and its impl report's
`## Manual checks` says so. S069's open row is unchanged: row 50 of `docs/steps/device-checks.md`.

## Checked and found consistent

- **The fix round's diff** (`step_snapshot.py diff S070 --from-round 1`): the code holds only the
  changes the report lists. The other docs in the diff (S072, S075, S076, `INDEX.md`) belong to
  other steps.
- **`done_time_error`**: the floor `problem_at.replace(second=0, microsecond=0)` matches the minute
  the message shows. The message still prints the original `problem_at` at minute precision, so
  it is the same text. A done time one minute earlier is still refused (asserted).
- **Docs**: "Docs updated: none" is right. The round changed one message text, which no doc
  quotes.
- **Files I re-read**: `backend/documents.py:470-600` (the removed list), the changed hunks of
  `improvements_core.py`, `app.py`, `test_improvements_core.py` and
  `test_improvement_actions_api.py`, `test_documents_api.py:789-814`, `WhyDialog.vue:1-60` and its
  changed template lines, `improvements.spec.js:236-276`, and the fix-round sections of S070's and
  S069's impl reports.

## Feedback

- waste: the coder's run for a refactor of the removed list named only `test_documents_api.py`;
  two other files test that list, so I ran the whole backend suite to cover them (111 s). A grep
  of the changed function's route over `backend/tests/` would name them.
- hindrance: `diff S070 --from-round 1 --stat` again mixed in about 630 lines of other steps' docs;
  `-- backend frontend` plus a separate diff of the S069 report gave the real change.
