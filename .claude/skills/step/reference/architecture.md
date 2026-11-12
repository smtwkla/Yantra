# /step — Architecture

Part of the step skill (`.claude/skills/step/SKILL.md`); read when the skill points here.

The architect (`architect`) keeps the repo's architecture doc
current (settings: *Architecture*; README § The architecture doc), with its diagrams. It is the
only agent that edits the doc. A repo whose setting is `none` skips this section.

- **When it runs** for a step, under the step's claim (`agent S0NN architect`):
  - **at the brief**: when the brief writer's final message names a structural change, or the
    brief adds or changes a module, a table group, a boundary, a dependency direction or a
    cross-cutting pattern: spawn it for "update S0NN, proposed" before the review loop. A
    finding that changes the structure re-runs it after the writer's answers;
  - **on ARCHITECTURE UPDATE NEEDED** from any agent: spawn it with the hand-back. A change
    the approved brief does not cover is a design change: it goes to the user as an
    amendment, never into the doc silently;
  - **before gate B** of a step that had proposed changes, or whose diff changes the
    structure: spawn it for "update S0NN, as built". The doc's change lands in the step's
    snapshot and is committed with the step;
  - **when a step is dropped** or its structural design is turned down at gate A: "withdraw
    S0NN".
- **Gate A** shows the proposed architecture changes (the doc's diff, in short) beside the
  brief's design decisions; approving the brief approves them. **Gate B** names the doc's
  update in the *Docs updated* line, and any proposed change the build did not follow.
- **Commands:** `/step architecture` reports the doc's status and its *Known drift*;
  `/step architecture init` writes the first version (the user then says it is `Agreed`, and you
  set the status line); `/step architecture review` runs the drift
  review (`docs/architecture/review-DD-MM-YYYY.md`). These two belong to no step, so they take
  no claim; `architect-full` is their budget when one runs inside a step. Propose a review before a new roadmap and
  about every 10 steps; run it only when the user says so. Its remedies become queued items in
  `docs/steps/INDEX.md` only as the user picks them.
- **The page**: after each first version, update or review, publish the
  doc as a private artifact page (Artifact tool, a plain page that draws the Mermaid blocks),
  and update the same page after later runs. The doc stays the record; the page is how the user
  reads it, also on a phone. Give its link at the gate.
- **Its feedback** comes in its final message (the doc is not a step file): name it at the
  gate as for the other agents' feedback.
