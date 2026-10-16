---
name: step
description: Orchestrate Yantra's step workflow (docs/steps) from one terminal — plan a step and loop it through the Fable brief reviewer, then implement it with the coder subagent (Sonnet, or Opus when complex) and loop it through the Opus code reviewer, stopping only at the user's gates. Use when the user says /step, "run S00N", "plan/implement/review step …", or asks to drive the step loop.
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

- `/step plan <topic>`: open a new step and run **phase 1**.
- `/step amend S00N <request>`: write amendment `A<n>` in § 10 of the brief.
  Run the brief reviewer on it only if the user asks. Then stop at gate A.
- `/step implement S00N`: the brief, or amendment, must be `Approved`. Run
  **phase 2**.
- `/step review S00N`: run **phase 2** from its code-review loop, for code that
  already exists.
- `/step status [S00N]`: report the step's files, status and open findings.
  Change nothing.

When the user just says "go on" or "next", find where the step stands from its
files and its Status, and continue from there.

## Phase 1: brief

1. **Write the brief.** The ID is the next free `S0NN` in the README index.
   - Write `1-brief.md` with status `Draft`, then add the index row.
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
   - Stop after **3 rounds** and ask the user.
   - A finding that needs a user decision isn't settled by you. Collect it for
     the gate.
3. **Gate A: STOP.** The user approves the brief itself, not a summary of it.
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
   row, and their answers in the brief), and record lasting decisions in
   `docs/Plan.MD`.

## Phase 2: implement and review

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
   - the manual browser checks for the user.

   The user checks, then **commits** (with the `S00N:` prefix). Set the status to
   `Done` only when the user says it is committed.

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
