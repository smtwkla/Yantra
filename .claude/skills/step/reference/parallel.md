# /step — Parallel steps

Part of the step skill (`.claude/skills/step/SKILL.md`); read when the skill points here.

An option, not the default: a second coder works at the
same time in its own git worktree, so two long steps don't wait on each other.

- **When it pays.** Both steps would take a coder 30 minutes or more, and
  their *Where* lists share no file. Short fix-lane steps run one after the
  other instead: the join below costs about what they would save.
- **Never in parallel:**
  - two steps that both add a migration (the repo's migrations module and
    the schema docs always conflict; settings: *Shared code*);
  - two steps that touch the same screen or the repo's shared frontend code,
    or the same entries of the shared test fixtures (settings: *Shared code*);
  - a step that builds on the other's code.
- **Proposing it.** When planning or listing, name the pairs that qualify,
  with the reason ("no shared files"). Start the second coder in a worktree
  only when the user says so.
- **Setting it up.** Create the worktree from the newest snapshot (or
  `HEAD`), e.g. `git worktree add ../<repo>-S0NN -b step/S0NN refs/steps/S0MM`,
  or spawn the coder with `isolation: "worktree"` when its base is `HEAD`.
  Tell the coder its folder; it runs every command there. It needs its own
  test run name (as always) and the repo's dependency set-up (see the repo's
  `CLAUDE.md`; e.g. `uv sync`, and `node_modules` linked by a junction).
  Browser tests still take turns: the browser-test lock is per machine, so a
  worktree's run waits for it too (settings: *Browser tests*).
- **Shared step docs.** In a worktree the coder edits no shared step doc:
  not `docs/steps/INDEX.md`, not the device-check list. It writes the changes it
  needs, word for word, in its impl report under `## Shared docs`; the
  orchestrator applies them after the join, so row numbers never clash.
  The docs-pass docs (product plan, schema doc, domain docs, `CLAUDE.md`) stay
  with the coder, in its worktree, reviewed with the code.
- **The join** (at the step's gate B):
  1. the step's result is one commit on its branch (the gate B snapshot of a
     worktree step);
  2. put it on top of the current chain (the newest snapshot, or `HEAD`)
     with `git cherry-pick` in a temporary worktree, never in the user's;
  3. a conflict: resolve it when both sides can be kept; bring it to the
     user when the two steps disagree on behaviour;
  4. **test the joined code**: the backend suite and the targeted browser specs
     of both steps (they were never tested together). Red is a blocker of
     the joined step;
  5. snapshot the result as `refs/steps/S0NN`, apply the `## Shared docs`
     changes, then remove the worktree and its branch (`git worktree remove`,
     `git branch -D`), only after the snapshot exists.
