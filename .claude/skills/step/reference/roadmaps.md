# /step — Roadmaps

Part of the step skill (`.claude/skills/step/SKILL.md`); read when the skill points here.

The planner (`planner`) cuts one big feature into a roadmap of items;
conventions in `docs/roadmap/README.md`.

- **Spawn** it with the feature, why the user wants it now, and anything the user said about scope
  or order. It reads the repo's product plan, the domain docs (settings: *Plan and domain docs*), the steps
  done and the code, and writes only `docs/roadmap/R0N-<slug>.md`.
- **Numbers:** roadmaps `R0N`, items `R0N.n`. **Only the orchestrator gives out step numbers,**
  and only when the user takes an item up (`/step plan R0N.n`). Add the roadmap's index row in
  `docs/roadmap/INDEX.md` yourself.
- **The deck**: when the planner is done, render its mock-ups with
  `tooling/render-mockups.bat docs\roadmap\R0N-mockups` (PNGs beside the HTML, the browser
  tests' Chromium, nothing installed), then build a **private slide-deck artifact** from the
  roadmap's `## Slides` outline with those screenshots (Artifact tool, `quickstart` with intent
  `slides`, then the Slides type; the images go up as the artifact's assets). The user can view it on
  any device, comment per slide, and download it as .pptx or PDF. Re-render and update the same
  deck after a re-plan. The roadmap file stays the record; the deck is how the user reviews it.
- **Gate R: STOP.** Give the deck's link first, then show the items table, the order with its reasons, the standards, and every
  decision for the user with its options (recommended one marked), then the other sections by
  heading. The user approves; record the answers in the roadmap (Status `Approved …`), and the
  lasting decisions in the repo's product plan.
- **Taking an item up:** the next free `S0NN`; the brief's header carries `From: R0N.n`; the item
  gets "→ S0NN, DD-MM-YYYY"; the brief starts from the item's goal, size, track and dependencies,
  and the usual phase 1 follows (facts run, self-check, reviews, gate A).
- **When a step is Done,** mark its item `done` in the roadmap and update the index counts. When a
  step changes the picture (a split, a new dependency, a decision), propose a re-plan
  (`/step roadmap R0N`); a changed order or a new decision returns to gate R.
- `/step ls` lists steps only; roadmap items show in `/step roadmap`.
