# /step — Claims and the watchdog

Part of the step skill (`.claude/skills/step/SKILL.md`); read when the skill points here.

Two sessions working on one step at once overwrite each other's files, so
one orchestrator session at a time works on a step. The rule is kept by this
skill, not by a hook (the user's choice). The tool is `tooling/step-claim.bat`;
from the Bash tool call `uv run --no-project python tooling/steps/step_claim.py …`
(it reads the session's `CLAUDE_PID`, which a `cmd //c` call also passes on).

- **Take** the step before any command writes its files:
  `take S00N "<phase>"` (e.g. "brief review r2", "coding", "fix round 1").
  Taking it again in the same session only updates the phase; a session
  after `/clear` is the same process and keeps its claims.
- **Refused** (exit 1): another live session holds the step. Stop, show the
  user the refusal's line (who, which phase, since when, the agent running),
  and ask: wait, or take it over. Use `take … --force` only on the user's
  word for this step.
- **Before every agent you spawn** for the step: `agent S00N <role>
  [<minutes>]`, then start `watch S00N` as a background command
  (`run_in_background`). Roles and budgets (about twice each role's usual
  time): `coder` 60, `fix` 20 (a fix round's
  coder), `code-reviewer` 20, `brief-writer` 45 (a new brief or amendment),
  `brief-answer` 20 (the writer answering a review), `brief-reviewer` 20, `advisor` 30,
  `planner` 45, `architect` 30 (an update), `architect-full` 60 (a first version
  or a drift review).
- **When the agent hands back**: `agent-done S00N`; the watch then ends by
  itself (exit 0).
- **When the watch exits 3** (the agent passed its budget): check whether the
  agent is still running, and tell the user in one line with its minutes.
  Never stop it without the user's word. To wait longer, run `agent` again
  with the extra minutes and start a new `watch`.
- **Release** the claim at gate A, at gate B, when the user stops or parks
  the step, and after a refused or failed command you started: `release
  S00N`. A long stretch of your own work with no agent (answering a review)
  runs `touch S00N` at least every 30 minutes.
- **A dead claim** (its session's process ended, 30 minutes with no command
  and no agent, or an agent 15 minutes past its budget) is taken without
  `--force`; the take names whom it was taken from. Tell the user, and read
  the step's files to see where the other session stopped.
- `/step ls` shows every claim; `/step check` flags dead claims and claims
  on Done or Dropped steps (check 11).
