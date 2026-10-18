---
name: step
description: Orchestrate Yantra's step workflow (docs/steps) from one terminal — plan a step and loop it through the Fable brief reviewer, then implement it with the coder subagent (Sonnet, or Opus when complex) and loop it through the Opus code reviewer, stopping only at the user's gates. Use when the user says /step, "run S00N", "plan/implement/review step …", asks to drive the step loop, or asks which steps are open (`/step ls`).
---

# /step — step-workflow orchestrator

You, the main session, are the **orchestrator and planner**. The other roles
run as subagents, each with a fresh context:

| Role | Subagent | Default model |
|---|---|---|
| Brief reviewer | `brief-reviewer` | Fable |
| Coder | `coder` | Sonnet; Opus when complex (see below) |
| Code reviewer | `code-reviewer` | Opus |

The step files are the only hand-over. Conventions: `docs/steps/README.md`.
Read it before starting.

## Commands

- `/step plan <topic>`: open a new step and run **phase 1**. Propose the track
  (below). `/step plan lite <topic>` or `/step plan full <topic>` forces it.
- `/step amend S00N <request>`: write amendment `A<n>` in § 10 of the brief.
  Run the brief reviewer on it only if the user asks. Then stop at gate A.
- `/step implement S00N`: the brief, or amendment, must be `Approved`. Run
  **phase 2**.
- `/step review S00N`: run **phase 2** from its code-review loop, for code that
  already exists.
- `/step status [S00N]`: report the step's files, status and open findings.
  Change nothing.
- `/step ls [all]`: list the steps not yet `Done` or `Dropped`, then the queued
  ideas, as one table (§ Listing). `all` also lists Done and Dropped steps.
  Change nothing.

When the user just says "go on" or "next", find where the step stands from its
files and its Status, and continue from there.

## Tracks

Every step runs on one of two tracks (README § Tracks). The track is in the
brief's header (`Track: light | full`) and in the index row.

- **Choosing.** When planning, check the light criteria below and **propose**
  the track in one line with the reason ("Track: light — UI on the masters
  pattern, no migration"). The user confirms or overrides; a forced track
  (`plan lite` / `plan full`) needs no confirmation. When in doubt, full.
- **Light only if all hold:**
  - no migration, and no change to existing data;
  - no auth, RBAC or security-sensitive code (uploads, file serving, secrets,
    access checks);
  - no transactions, locking or concurrency rules;
  - follows an existing pattern: no new module design, no new dependency, no
    endpoint beyond plain CRUD;
  - roughly 10 files or fewer.

  These are the inverse of the Opus criteria in phase 2, so a light step is
  always coded on Sonnet.
- **What changes on the light track:**
  - the brief uses the short template (README § Tracks);
  - **one** brief-review round. Its answers are not re-reviewed, unless a
    `blocker` or `major` finding is open;
  - **gate A is a bullet summary** plus the brief's path; show the sections
    verbatim if the user asks;
  - the coder is Sonnet; the code-review loop is unchanged (up to 3 rounds).
- **Switch to full** automatically, and tell the user, when the brief reviewer
  raises a `blocker` or `major` finding, or the coder or a reviewer finds the
  step meets a full-track criterion. Update the header and the index row; the
  brief then gets the full-track sections it lacks before gate A.

## Phase 1: brief

1. **Write the brief.** The ID is the next free `S0NN` in the README index.
   - Write `1-brief.md` with status `Draft` and its `Track`, then add the index
     row. A light brief uses the short template.
   - Mark the manual checks that matter as **important** (README § Manual
     checks).
   - Follow CLAUDE-COMMON "Show the plan before building" and the Yantra rule on
     standards.
   - Ask the user first only about decisions that change the design. Other open
     points go into the brief's § Open questions.
2. **Review loop.**
   - Set the status to `In review`.
   - Spawn `brief-reviewer` with the brief's path and the round number.
   - Read its review file. Answer **every** finding in the brief's Review log
     (`Accepted` / `Rejected` / `Deferred`) and revise the brief text.
   - Repeat until no `blocker` or `major` finding is open.
   - Stop after **3 rounds** and ask the user. Light track: one round (§ Tracks).
   - A finding that needs a user decision isn't settled by you. Collect it for
     the gate.
3. **Gate A: STOP.** Light track: a bullet summary instead of the verbatim
   sections (§ Tracks); the rest below still applies. Full track: the user
   approves the brief itself, not a summary of it.
   Only after all review rounds are done, show them, in this order:
   - **the decision-relevant sections of the brief, verbatim** (the text as it
     stands after the last round): *What will be built*, *Out of scope*,
     *Standards and practice*, *Design decisions* (with the rejected
     alternatives) and *Open questions*. For an amendment, its what, rules and
     open points;
   - **the other sections by heading**, one line each, with the brief's path, so
     the user can open any of them;
   - what changed across the review rounds;
   - every point needing their decision;
   - the coder's model for phase 2, and why.

   Don't paraphrase the shown sections. If the brief is long, offer to publish it
   as a private artifact page too.

   Only the user sets `Approved`. When they approve, record it (status, index
   row, and their answers in the brief), copy the last review's `Reviewed
   against:` into the brief's header as `Baseline:`, and record lasting
   decisions in `docs/Plan.MD`.

## Phase 2: implement and review

0. **Stale brief check** (README § Stale brief check), before the step or an
   approved amendment is coded:
   - list the files in the brief's *Where* and the modules they call; compare
     them between the brief's `Baseline:` and the working tree now
     (`git diff --stat <baseline>` covers commits and uncommitted changes; add
     untracked files from `git status`). A brief without `Baseline:` takes
     the commit and uncommitted steps named in its last review, or else the
     commit current on its approval date;
   - **nothing changed:** say so in one line and go on;
   - **something changed:** spawn `brief-reviewer` in **staleness mode** with
     the brief's path, the round (`s1`, `s2`, …), the baseline and the list of
     changed files. Answer its `BS` findings in the Review log and fix the
     brief text. A `blocker` or `major` finding returns the step to gate A:
     show the user what changed and why, and wait for approval again;
   - set `Baseline:` to the code just checked;
   - skip the check only when the user says so, and record that in the brief.
1. **Choose the coder's model, and tell the user which one and why.**
   - The default is **Sonnet**.
   - Pass `model: "opus"` to the `coder` agent when the step involves any of:
     - transactions, locking or concurrency rules;
     - a migration that changes or moves existing data;
     - auth, RBAC core or security-sensitive code;
     - a cross-module refactor, or roughly more than 10 files of real logic;
     - a scheduling or calculation engine (the pure core of PM triggers, KPIs);
     - a fix round after Sonnet left a `blocker` or `major` finding open twice.

   UI-only work, CRUD following an existing pattern, and fix rounds with minor
   findings stay on Sonnet.
2. **Implement.** Spawn `coder` with the step ID, and with the amendment or fix
   round where that applies.
   - If it returns **QUESTIONS FOR THE USER**, stop and ask them.
   - After the answers, record any design-level ones in the brief as an
     amendment that the user approves, then resume the coder.
3. **Code-review loop.**
   - Spawn `code-reviewer` with the step ID and the round number.
   - If any `blocker` or `major` finding is open, spawn `coder` for that fix
     round, then review again.
   - Stop after **3 rounds** and ask the user.
   - Minor findings and nits go to the user at gate B. The coder doesn't fix
     them unasked.
   - Before each fix round, check the findings yourself. A finding that
     contradicts the approved brief, or needs a design decision, goes to the
     user and not to the coder.
4. **Gate B: STOP.** Report:
   - the test result;
   - what was built;
   - any departures from the brief, with your view on each;
   - the minor findings still open;
   - the manual checks: the **important** ones as the checklist from the impl
     report's `## Manual checks`, the rest as a plain list.

   The user checks, then **commits** (with the `S00N:` prefix). Set the status to
   `Done` only when the user says it is committed **and** every important check
   is ticked by the user or explicitly skipped by them. Record it in the
   impl report's checklist (`[x]`, or `[skipped] <reason>` in the user's words)
   and in the status, e.g. `Done (committed abc123; checks: 3 done, 1 skipped —
   iPhone)`. Never tick a check yourself.

## Listing

`/step ls` builds the table fresh from the step files and git every time; it
is never stored, so it can't go stale. Columns:

`Step | Title | Stage | Committed? | Remarks`

- **Step, Title**: from the index in `docs/steps/README.md`, then its
  "Queued" table (queued items with a step ID only; ideas without one are left
  out). Order by step ID.
- **Stage**: the brief's `Status:` line, shortened (e.g. "In code review (A1)",
  "Approved, not coded"). Queued items: "Queued".
- **Committed?**: `git log --oneline --grep "^S0NN"` → `Yes, <hash>`. With no
  commit, run `git status --short` on the step folder and on the files listed in
  its `3-impl-report.md`: "No — code in working tree" when they show changes,
  "No — no code yet" when there is no impl report, "No — no folder" for queued
  items.
- **Remarks**: the latest review's verdict (`2-brief-review-*` before coding,
  `4-code-review-*` after) with its open `blocker`/`major` count and minor/nit
  count, then the next action in a few words: "ready to commit", "ready for
  `/step implement`", "answer CR3-02", etc. Flag a mismatch, e.g. Stage says
  "In code review" but the step is committed → "set Status to Done".

Read only the files' header blocks and verdict lines, not whole files. Below the
table, list working-tree changes that belong to no step (not in any impl
report's file list), so the user can sort them before committing.

## Rules

- **Never commit, push, build, deploy or release.** The subagents don't either.
- **Subagents can't ask the user anything.** Any question they raise comes back
  to you, and you put it to the user.
- **Never edit a review file**, and never fabricate a subagent's result. Wait
  for its completion notice.
- **Keep the user informed.** Between rounds, one or two lines are enough:
  "BR round 2: 0 major, 3 minor — answering", or "Coder (Sonnet) done, tests
  green — starting code review r1".
- **Reports at the gates.** Short, in plain terms, and naming the standards
  touched, because the user is learning maintenance practice.
- **IDE reformatting is expected** (README § IDE reformatting). Whitespace-only
  changes in a file the user has open are theirs: carry on, don't ask about
  them, and don't mention them at the gates. Before editing, re-read the file.
