# /step — Feedback

Part of the step skill (`.claude/skills/step/SKILL.md`); read when the skill points here.

Every agent ends its file with `## Feedback` (README § Rules for every agent): at
most 5 items, one bullet each, `waste`, `hindrance`, `rule` or `idea`, each with its evidence, or
`- none`.

- **Tell each subagent** in its spawn prompt that its file ends with the section (its agent file
  gives the form), and name the themes dropped at the last triage (the log's newest section), so it
  does not report them again.
- **At each gate**, read the feedback of the files written since the last gate. When an item
  recurs or cost real time, name it in one line ("Feedback: the coder lost 3 runs to cmd quoting —
  see `/step feedback`"). Fix nothing in the workflow without the user's OK.
- **When to triage**: the gate B report ends with the unread count
  (`tooling/step-feedback.bat --new`, its `unread:` line) and proposes `/step feedback` when it is
  20 or more.
- **`/step feedback`** runs `tooling/step-feedback.bat --new` (all steps, or the IDs given): every
  unread item with its step, file and label, and `--themes` once: the log's rows counted by theme.
  Group the items that say the same thing, give each group a theme (an existing one when it fits),
  count them, and propose the few changes that would save the most; the user decides. Prefer
  fixing a tool over adding a rule: in past triages, the tool fixes ended their
  themes and the prose rule did not.
- **A theme noted twice**: a theme whose last two decisions were `noted` (`--themes`
  marks it) is decided `acted` or `dropped` at this triage; `noted` is not offered for it.
- **The feedback log**: `docs/steps/feedback-log.md`, one table row per item
  read, `| Step | File | Label | Item | Theme | Decision |`. An item is read when its row is there.
  Once the user has decided, run `tooling/step-feedback.bat --rows` (the unread items as rows, the
  theme and decision cells empty), fill each theme (a short tag, e.g. `facts-path`) and decision,
  and append the rows under a heading `## DD-MM-YYYY — …`: `acted: <the change>`,
  `dropped: <the reason>` (the agents are told not to report it again), or `noted` (read, no change;
  a later item saying the same thing comes back as unread, and its theme count grows). Copy the
  rows as printed: the item cell is the key. Feedback read only at a gate is not logged.
- Feedback is about the workflow, the tools and the rules, never a second list of findings.
