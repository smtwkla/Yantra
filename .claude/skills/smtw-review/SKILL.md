---
name: smtw-review
description: Full audit of the codebase against its documentation and the SMTW-WebApp-Base.md reference architecture — verifies business rules from the module docs are implemented, walks the RBAC matrix and API contract, lists gaps against the current base patterns, and ends with a hindsight architecture review. For reviewing a single change or diff, use /code-review instead.
argument-hint: "[module-or-file (optional)]"
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash, Agent
effort: max
---

# Codebase Audit

Audit the codebase (or the module/file specified by `$ARGUMENTS`) against its documentation and `SMTW-WebApp-Base.md`, as a senior engineer doing a 100% review. Apply `CLAUDE-COMMON.md` throughout — its principles, engineering rules and conventions are the review criteria for code quality, correctness, security, robustness and performance.

## Phase 1: Gather Context

Read these first — they define the **intended behaviour**; the job is to verify the code matches it:

1. **Project docs**: `.claude/CLAUDE.md` (including any recorded deviations from the base), `.claude/CLAUDE-COMMON.md`
2. **Reference architecture**: `.claude/SMTW-WebApp-Base.md` — skip for non-web repos
3. **Domain knowledge**: `docs/*-Domain.md` and `docs/Module-*.md`
4. **Schema**: `docs/Schema.md`, `docs/schema.sql`
5. **RBAC policy**: `backend/config_rbac.py`
6. **Repo-specific checks**: the `SMTW-Review` section of the repo's `.claude/CLAUDE.md` (or root `CLAUDE.md`), if present — a heading titled `SMTW-Review` at any level. It lists extra checks for this repo (e.g. a Playwright usability test run). Note them now; they are executed in Phase 6.

## Phase 2: Business Logic Verification

The most important phase. For each module:

1. Extract every stated business rule from its `docs/Module-*.md`.
2. Verify each rule is **actually implemented** in the backend — not just mentioned in a comment — and matches the documented intent exactly.
3. Flag documented behaviour that is missing, incomplete, or contradicted by the code.
4. Flag code behaviour that is undocumented (intentional or a bug — say which you think).
5. Check inline comments and docstrings still match what the code does.

## Phase 3: Cross-Cutting Checks

1. **RBAC matrix**: every API endpoint has `@require_perm`, and its key matches `config_rbac.py` and the module docs. Can any role see or do more than intended?
2. **API contract**: response shapes follow the documented pattern (`{"items": [...], "total": N}` for lists, ISO dates with `+05:30`).
3. **Frontend–backend alignment**: frontend calls the right endpoints, handles error responses, and gates UI by permission.
4. **Schema & migrations**: schema supports the documented features; constraints (NOT NULL, FK, UNIQUE) are right; migrations are append-only.
5. **Timezone**: IST business logic on UTC servers — look for naive `now()`, wrong conversions, date-boundary bugs.
6. **Idle connections**: pooled DB/HTTP connections recover after an overnight idle instead of returning a 500 on first use.
7. **Dependencies**: deprecated APIs in use; unmaintained or end-of-life libraries.
8. **Tests**: each module has tests covering the happy path and key failure modes; fixtures match the real data model.

## Phase 4: Base Conformance

Web apps only. Walk `SMTW-WebApp-Base.md` section by section and compare the repo against each applicable pattern:

1. **Missing** — a pattern the repo doesn't implement at all (e.g. no stale bundle detection, no `/api/version`).
2. **Outdated** — implemented, but an older variant than the current base (e.g. RBAC without the fail-closed check, version read from `package.json`).
3. **Not applicable** — skip sections the repo has no use for, and deviations recorded in its `CLAUDE.md`; list them in one line so the skip is visible.

For each gap, name the base section, what the repo does today, and the effort to align. These are findings for the user to schedule — not fixes to make.

## Phase 5: Hindsight Review

Step back and review the project as an architect would after its first months in production:

1. **Problem & domain fit**: are the domain docs still accurate? Flag concepts the code handles that the docs don't describe, and documented scenarios the code can't handle.
2. **Architectural choices**: given actual usage and data volumes, is the architecture (data model, module boundaries, key libraries and patterns) still right? Where is it fighting the problem and causing recurring friction?
3. **Technical debt**: catalogue concrete debt — workarounds, TODOs, shortcuts that now limit the system — ranked by cost of delay.
4. **Fresh-start reframe**: starting today with the same requirements and full hindsight, what would you do differently? Justify each change against a real pain point, not a hypothetical; skip cosmetic or equal-effort changes.

## Phase 6: Repo-Specific Checks

Run every check listed in the repo's `SMTW-Review` section (found in Phase 1). If the section is absent, say so in one line and skip this phase.

1. Execute each check as written — run the commands, tests or procedures it names (e.g. a Playwright usability test) and capture the results.
2. Treat the section as additional review criteria on top of this skill, never as a replacement for earlier phases; it cannot waive them.
3. If a check cannot be run (missing tool, server not up, credentials unavailable), report it as not run with the reason — do not silently skip or assume it passed.
4. Fold failures into the severity-grouped findings below, citing the check that produced them.

If `$ARGUMENTS` narrows the scope, run only the checks relevant to that module/file.

## Output Format

A **serial-numbered list** of findings, grouped by severity:

- **CRITICAL** — bugs, security issues, data corruption risks
- **HIGH** — business logic violations, missing validations, incorrect behaviour
- **MEDIUM** — code quality, DRY violations, missing error handling
- **LOW** — style, naming, documentation, minor improvements

Each finding:
```
[N]. <file>:<line> — <short title>
     <description of the issue>
     <suggested fix or action>
```

Then the **Base Conformance** gaps (Missing / Outdated, with the skipped sections in one line), the **Repo-Specific Checks** results (each check: passed / failed / not run), the **Hindsight Review** findings, and finally a **Summary**: overall health, top 3 priorities, and recurring patterns.
