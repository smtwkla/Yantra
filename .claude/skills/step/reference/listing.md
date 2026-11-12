# /step — Listing

Part of the step skill (`.claude/skills/step/SKILL.md`); read when the skill points here.

`/step ls` builds the table fresh every time; it is never stored, so it can't
go stale. **Run `tooling/step-ls.bat` (`all` or `deferred` passes on) once and
build the table from its output** — don't read the step files or run git yourself. The
script prints, per step not yet Done, Dropped or parked (all steps with
`all`, only the parked ones with `deferred`): the
index title and folder, the brief's `Status:` line, the latest review with its
verdict paragraph, the commits whose subject names the step, whether an impl
report exists, and the working-tree changes in the step's folder (and, for an
uncommitted step, among the files its impl report names); then the queued
items with a step ID, the shared docs changed (`INDEX.md`, the device-check list), the
snapshots not yet adopted (`refs/steps/`), the step claims (`reference/claims.md`; § Claims and the
watchdog), and
the working-tree changes no step claims. It judges nothing: the bulb, the
stage, the next action and the notes below the table are yours. Open a file
only when the facts leave a question (a verdict cut short, a mismatch to
explain). Columns:

`| Step | Title | Stage | Committed? | Remarks |  |`

- **Bulb** (last column, no header): where the step stands. Last, because the
  terminal draws an emoji two cells wide while the table pads it as one, so
  every column to its right would shift; at the end only the closing border
  moves.
  - 🟡 **needs the user**: a gate is waiting: approve a brief or amendment
    (gate A), answer a question Claude raised, run the manual checks or
    commit (gate B), or confirm the commit so the step can be set `Done`;
  - 🔵 **an agent is working**: a brief or code review, the coder, or Claude
    answering or fixing findings — due or running;
  - ⚪ **ready for coding**: approved, waiting for `/step implement` (or for
    the step it is coded after);
  - 🟢 **Done** (shown only by `/step ls all`);
  - blank: queued or `Dropped`.
- **Step, Title**: from the index in `docs/steps/INDEX.md`, then its
  "Queued" table (queued items with a step ID only; ideas without one are left
  out). Order by step ID.
- **Stage**: the brief's `Status:` line, shortened (e.g. "In code review (A1)",
  "Approved, not coded"). Queued items: "Queued".
- **Committed?**: the script's `commits` → `Yes, <hash>` (the newest). With
  none: "No — code in working tree" when it lists changes beyond the brief and
  reviews, or when unclaimed changes clearly belong to the step (a step being
  coded has no impl report yet: say which files you attribute to it); "No — no
  code yet" when there is no impl report and nothing to attribute; "No — no
  folder" for queued items.
- **Remarks**: the latest review's verdict (`2-brief-review-*` before coding,
  `4-code-review-*` after) with its open `blocker`/`major` count and minor/nit
  count, then the next action in a few words: "ready to commit", "ready for
  `/step implement`", "answer CR3-02", etc. Flag a mismatch, e.g. Stage says
  "In code review" but the step is committed → "set Status to Done". A step
  held by another session's live claim says so here ("S0NN held by another
  session: coding, coder 12 min"), and a dead claim is flagged.

Below the table, list the unclaimed working-tree changes, grouped by the step
you think they belong to (say it is a guess) or as "no step", so the user can
sort them before committing. Add a note for anything that looks wrong: a Status
that contradicts the commits or the review, a step committed but not `Done`
with no check named as pending, a stale `Baseline:`.
