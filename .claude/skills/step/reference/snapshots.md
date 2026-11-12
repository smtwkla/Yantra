# /step — Snapshots

Part of the step skill (`.claude/skills/step/SKILL.md`); read when the skill points here.

Each step gets its own commit, while the
next step's coder carries on in the same working tree.

- **At gate B**, `tooling/step-snapshot.bat snapshot S00N "<message>"` writes
  the whole working tree (untracked files too, `.gitignore` respected) as a
  commit under `refs/steps/S00N`, whose parent is the previous unadopted
  snapshot or `HEAD`. It never moves `HEAD` or a branch, never touches the
  user's index or files, and is never pushed. The message is the step's
  commit message (one line, the `S00N:` prefix, then a blank line and the
  attribution trailers; write each line break as the two characters `\n`,
  since a `.bat` argument holds none). From the Bash tool, call
  `uv run --no-project python tooling/steps/step_snapshot.py …` directly:
  `cmd //c` garbles a quoted message on its way to the `.bat`.
- **Diff**: `diff S00N [--from-round n] [--stat] [--all] [-- <path>…]`
  leaves out every step folder, `docs/steps/INDEX.md`, `docs/steps/feedback-log.md`
  and `docs/roadmap/`, and its last line counts them; `--all` or named paths
  show them. A spawn prompt names the command only, no list of files to skip.
  `diff [S00N] --base <commit>` diffs from that commit instead
  of the step's base, with the same exclusions: for a step with no snapshot
  yet whose base is not `HEAD`. A fix after gate B re-runs `snapshot` for the same step; only the newest
  snapshot can be replaced.
- **Rounds**: `snapshot` also runs after every coder hand-back
  before gate B (§ Phase 2 step 2), and each run keeps its commit as a round
  ref, `refs/step-rounds/S00N-<n>`. `rounds S00N` lists them; `adopt` removes
  them. `diff S00N [--from-round <n>] [--stat]` shows the step's change from
  what it builds on, or from round `<n>`, with new untracked files as added:
  a plain `git diff refs/steps/…` lists them as deleted.
- **One coder writes at a time.** A snapshot holds whatever is in the tree,
  so two coders writing at once mix their steps. Reviews and brief work are
  read-only for code and may overlap. Don't start a coder while another is
  writing, unless the user says so, or the second one works in its own
  worktree (`reference/parallel.md`).
- **The user's own edits** (IDE reformatting included) land in the next
  snapshot. Say so at gate B when `git status` shows files no step claims.
- **Adopting:** the user runs `tooling/step-snapshot.bat adopt S00N`, oldest
  first. It checks that the snapshot builds on `HEAD` and that nothing is
  staged, then moves the branch to it and sets the index to its files; the
  working files stay. `git merge --ff-only` would refuse, because the step's
  new files are still untracked. If `HEAD` moved another way (the user
  committed by hand), the old snapshots are *stale*: re-snapshot the steps
  still open.
- **Committing for the user:** only when the user asks in the current
  request ("commit this", "adopt S037"). Then adopt the snapshots in order,
  or stage each step's own files and commit them one step at a time; never
  push.
- `/step ls` lists the snapshots not yet adopted, and any stale ones.
