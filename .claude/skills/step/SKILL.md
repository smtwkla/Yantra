---
name: step
description: Orchestrate the step workflow (docs/steps) from one terminal — plan a step with the brief-writer subagent (model chosen per brief) and loop it through the brief reviewer, then implement it with the coder subagent (Sonnet, or Opus when complex) and loop it through the code reviewer, stopping only at the user's gates. Use when the user says /step, "run S00N", "plan/implement/review step …", asks to drive the step loop, or asks which steps are open (`/step ls`), or says "recap" (`/step recap`: the current decision card again).
---

# /step — step-workflow orchestrator

You, the main session, are the **orchestrator**. The other roles
run as subagents, each with a fresh context:

| Role | Subagent | Default model |
|---|---|---|
| Brief writer | `brief-writer` | Opus; Fable or Sonnet per brief (phase 1) |
| Brief reviewer | `brief-reviewer` | Fable; Opus when the writer ran on Fable |
| Coder | `coder` | Sonnet; Opus when complex (see below) |
| Code reviewer | `code-reviewer` | Opus |
| Advisor | `advisor` | Fable |
| Planner | `planner` | Opus |
| Architect | `architect` | Fable; Opus for a small update |

The step files are the only hand-over. Conventions: `docs/steps/README.md`.
Read it before starting. The repo's own values (commands, files, names) are
in the `## Step workflow` section of its `.claude/CLAUDE.md`, "the settings";
"(settings: *Entry*)" points at one of its entries. A repo without the
section: stop with the message of README § The repo's settings and index.
The steps are listed in `docs/steps/INDEX.md`.

**One session per step**: every command that writes a
step's files (`plan`, `amend`, `implement`, `review`, `fix`, answering
findings) first takes the step's claim, and a refused claim stops the command
(§ Claims and the watchdog).

## Commands

- `/step roadmap <feature>`: spawn the **planner** to cut a big feature into a
  roadmap (§ Roadmaps), then stop at **gate R**. `/step roadmap R0N` re-plans
  one; `/step roadmap` alone lists the roadmaps from `docs/roadmap/INDEX.md`.
- `/step plan R0N.n`: take a roadmap item up as a step: the next free `S0NN`,
  `From: R0N.n` in the brief's header, "→ S0NN, DD-MM-YYYY" on the item; then
  phase 1 as for any topic.
- `/step plan <topic>`: open a new step and run **phase 1**. Propose the track
  (below). `/step plan lite <topic>` or `/step plan full <topic>` forces it.
- `/step fix <the bug>`: fix a small bug on the **fix lane** (§ Fix lane),
  with no stop for the user before gate B.
- `/step amend S00N <request>`: spawn `brief-writer` to write amendment `A<n>` in
  § 10 of the brief (phase 1's model choice and hand-over).
  Run the brief reviewer on it only if the user asks. Then stop at gate A.
- `/step implement S00N` (alias `/step code S00N`): the brief, or amendment,
  must be `Approved`. Run **phase 2**.
- `/step review S00N`: run **phase 2** from its code-review loop, for code that
  already exists.
- `/step architecture [init | review]`: the architecture doc's status, its first
  version, or a drift review (§ Architecture).
- `/step ask S00N <question>`: run the **advisor** on one technical question for
  the step (§ Advice), and report its answer. Change nothing else.
- `/step status [S00N]`: report the step's files, status and open findings.
  Change nothing.
- `/step ls [all | deferred]`: list the steps not yet `Done`, `Dropped` or
  parked, then the queued ideas, as one table (§ Listing). `all` also lists
  Done, Dropped and parked steps; `deferred` lists only the parked
  (deferred) ones.
- `/step recap` (or the bare word **recap**): show the decision card again
  (§ Messages to the user), rebuilt from the files, not from the conversation:
  run `tooling/step-ls.bat` once, read the Status and open points of each
  step not `Done`, and the newest `scratch/preflight/<short-sha>.md` when it
  names HEAD. One card: *Summary* (each open step, one line: its phase and
  what it waits for), *Details* (only what a decision needs), *Decide* (every
  question waiting for the user, numbered, with the options). Change nothing.
- `/step check`: check the step files against each other and git (§ Check).
  Report the problems and the fixes you propose; change nothing until the user
  says which to make.
- `/step feedback [all] [S00N …]`: run `tooling/step-feedback.bat --new` once
  (every step, or the ones named): the agents' `## Feedback` items not yet in the
  feedback log, grouped by label (§ Feedback); `all` drops `--new`, to see the
  read items too. Report the points that recur or cost real time, and propose the
  3–5 changes worth making; change nothing until the user says which. Then log
  every item shown (§ Feedback).
- `/step stats [S00N]`: run `tooling/step-stats.bat` once (it writes
  `scratch/step-stats.md`): review rounds, findings by severity, late blockers
  and majors, time, tokens and browser-test cost per step and per role, from the step
  files and the stored transcripts. Report the main numbers and what they
  suggest to cut (time, tokens) or to tighten (accuracy); change nothing.
- `/step clean [S00N …]`: housekeeping for finished steps (`Committed`, `Done`,
  `Dropped`). Run `uv run --no-project python tooling/steps/step_clean.py [S00N …]`
  (a dry run), report its totals, then run it again with `--apply`. It deletes
  the steps' `scratch/` entries that carry their id and their `refs/step-rounds/`
  refs, and their `refs/steps/` ref once merged or stale; it never touches
  `docs/steps/`. Report its last line, the scratch entries tied to no step, as a
  list for the user to delete by hand or keep; never delete those yourself.

When the user just says "go on" or "next", find where the step stands from its
files and its Status, and continue from there.

## Tracks

Every step runs on one of two tracks (README § Tracks), or a small bug on the
fix lane (§ Fix lane). The track is in the
brief's header (`Track: light | full | fix`) and in the index row
(`docs/steps/INDEX.md`).

- **Choosing.** When planning, the brief writer checks the light criteria
  below; **propose** its track to the user in one line with the reason ("Track: light — UI on the masters
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
  step meets a full-track criterion. Update the header and the index row
  (`docs/steps/INDEX.md`); the
  brief then gets the full-track sections it lacks before gate A.
- **A track finding alone is `minor`**, because a sound design should not wait on a process
  question. It still switches the track as above, and the
  user may keep light at gate A. `blocker` and `major` stay for risks the brief
  leaves unhandled.

## Fix lane

A small bug is fixed without a brief review and without gate A. The user's request is the approval.

- **The fix lane only if all hold** (otherwise propose light or full, and ask):
  - it fixes behaviour against what a brief, the repo's product plan or the docs already say,
    and adds no feature;
  - about **5 files or fewer**, tests included;
  - no permissions: RBAC keys, roles, login, and the repo's permission tables
    and gates (settings: *Self-check, repo items*);
  - no interface change: no API route's URL, body or response shape, no
    migration or schema change, no setting;
  - no security-sensitive code: uploads, file serving, secrets, and the
    security-sensitive code the repo names (settings: *Self-check, repo items*);
  - no locking, transaction or concurrency change.
- **Run it like this:**
  1. Take the next free `S0NN` and spawn `brief-writer` (Sonnet; Opus when
     the cause is not obvious) for a fix-lane brief: `Track: fix`,
     `Status: Implementing (fix lane)`, `Baseline:` HEAD, the bug, the steps to
     see it, the cause with `file:line`, the fix, the files, and the test that
     fails on the bug. Add its row in `docs/steps/INDEX.md`.
  2. If the writer returns a question (the cause is unclear, two fixes behave
     differently, a criterion fails), ask the user. The step then leaves the
     fix lane.
  3. Spawn `coder` (Sonnet) for the step. It writes the failing test first
     (*red, then green*), runs the full unit suites, and makes targeted browser
     runs when a screen changed (the whole-suite run once at the
     end, as in § Phase 2 step 3).
  4. One `code-reviewer` round. Every finding is fixed (§ Phase 2
     step 3). A `blocker` or `major` gets the usual loop.
  5. Gate B, short, as a card (§ Messages to the user): the bug, its cause,
     the change, the tests, the snapshot line; *Decide*: adopt (or commit
     with the `S0NN:` prefix).
- **Leave the fix lane** as soon as the coder, the reviewer or you find that
  a criterion fails. Stop, set the track to light or full, and bring the step
  to gate A with a brief of that track.

## Phase 1: brief

The **brief writer** (`brief-writer`) writes the brief and answers its
reviews; you run the loop, talk to the user and keep the index. Its rules
(template, facts run, self-check, size, answering findings) are in
`.claude/agents/brief-writer.md`.

1. **Open the step.** Take the next free `S0NN` in `docs/steps/INDEX.md` and
   the step's claim. Ask the user first only about decisions that change the
   design; settle those before the writer starts.
2. **Choose the writer's model, and tell the user which one and why** (pass
   `model` to the agent):
   - **Fable** for a design-heavy brief: a new module or table, a scheduling
     or calculation engine, a domain rule or standard to settle, locking or
     concurrency, a migration that changes existing data, auth or RBAC core,
     or a cross-module change;
   - **Opus** (the default) for the other full-track briefs and amendments;
   - **Sonnet** for a light-track brief on an existing pattern, and for a
     fix-lane brief.

   Answers to a review run on the model that wrote the brief; raise it one
   level when a round leaves a `blocker` or `major` open twice.
3. **Write the spawn prompt: a hand-over, not the conversation.** The writer
   starts with a fresh context on purpose; give it only what the brief needs:
   - the step ID, its folder, the task (brief, answers to round N, staleness
     answers, amendment A<n>, fix-lane brief) and the track if forced;
   - the user's request in the user's own words;
   - the decisions already taken and the constraints, one line each, with who
     took them (user or product plan);
   - for a roadmap item, the item (`From: R0N.n`), its goal, size, track and
     dependencies;
   - the advice files and earlier steps that matter, by path;
   - for answers: the review file, and the findings you hold back for the user
     at the gate (step 5).

   Leave out the discussion that led to the decisions, options the user
   rejected (unless the brief must name them as rejected alternatives), and
   anything about other steps.
4. **Spawn `brief-writer`.** When it hands back:
   - **QUESTIONS FOR THE USER**: ask the user, then resume the writer with the
     answers. **ADVICE NEEDED**: spawn `advisor` (§ Advice), then resume the
     writer with the advice file.
   - Read its track line (§ Tracks: propose it to the user; a forced track
     needs no confirmation) and any split proposal; the user decides both.
   - Add the step's row in `docs/steps/INDEX.md` (the writer never edits it).
   - A structural change named in its message, or **ARCHITECTURE UPDATE NEEDED**:
     spawn `architect` (§ Architecture) before the review loop.
5. **Review loop.**
   - Set the status to `In review`.
   - **The reviewer differs from the writer**: when the writer ran on Fable,
     spawn `brief-reviewer` with `model: "opus"`; else on its default.
   - Spawn `brief-reviewer` with the brief's path, the round number and the
     facts file (`scratch/brief-facts-S0NN.md`; the writer's last run matches
     the draft).
   - Read the review. Before spawning the writer for the answers, check the
     findings yourself: one that needs a user decision, or contradicts what
     the user decided, is held for the gate; tell the writer which, and it
     answers them `Deferred — to the user`.
   - Spawn `brief-writer` to answer the round (step 3's hand-over). It copies
     the brief to `scratch/S0NN-brief-rN.md` first, answers every finding in
     the Review log and revises the text.
   - Round 2 and later re-check only what changed (the brief reviewer's
     *Earlier rounds* rule): tell the reviewer the sections the writer lists
     as changed.
   - Repeat until no `blocker` or `major` finding is open.
   - Stop after **3 rounds** and ask the user. Light track: one round (§ Tracks).
6. **Gate A: STOP.**: the *Summary* first,
   then the sections below, then *Decide* last. Light track: a bullet summary instead of the verbatim
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
   - the proposed changes to the architecture doc, if any (§ Architecture);
   - the coder's model for phase 2, and why.

   Don't paraphrase the shown sections. If the brief is long, offer to publish it
   as a private artifact page too.

   Only the user sets `Approved`. When they approve, record it (status, index
   row, and their answers in the brief), copy the last review's `Reviewed
   against:` into the brief's header as `Baseline:`, and record lasting
   decisions in the repo's product plan (settings: *Plan and domain docs*).

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
   - **something changed:** re-run `tooling/step-brief-facts.bat S0NN` first
     and name the fresh `scratch/brief-facts-S0NN.md` in the prompt (a facts file made before
     earlier steps were coded reports their names as missing). Then spawn `brief-reviewer`
     in **staleness mode** with the brief's path, the round (`s1`, `s2`, …),
     the baseline and the list of changed files. Spawn `brief-writer` to answer
     its `BS` findings in the Review log and fix the brief text. A `blocker` or `major` finding returns the step to gate A:
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
     - a scheduling or calculation engine (e.g. the pure core of a schedule or a KPI);
     - a fix round after Sonnet left a `blocker` or `major` finding open twice.

   UI-only work, CRUD following an existing pattern, and fix rounds with minor
   findings stay on Sonnet.
2. **Implement.** Spawn `coder` with the step ID, and with the amendment or fix
   round where that applies. Give every coder and code reviewer its own test
   run name (the repo's test run name variable, settings: *Unit tests*), so
   agents running tests at the same time never share a database.
   - **Snapshot every coder hand-back**: when the coder of the step or of a fix round hands back,
     run `snapshot` for the step (§ Snapshots). Each run keeps a round ref
     (`refs/step-rounds/S00N-<n>`). Tell the next code reviewer its diff:
     `diff S00N` in round 1, `diff S00N --from-round <n>` from round 2 on,
     with `<n>` the round before the fix round.
   - If it returns **QUESTIONS FOR THE USER**, stop and ask them. This
     includes anything outside the repo a check would need (pulling an
     image, installing, a setting): the user decides.
   - If it returns **ADVICE NEEDED**, spawn `advisor` with its question and
     what it tried (§ Advice), then resume the coder with the advice file.
     If the answer changes the design, it goes to the user as an amendment,
     never as a silent change. The code reviewer may return the same, and is
     answered the same way.
   - **ARCHITECTURE UPDATE NEEDED** from the coder or a reviewer: spawn
     `architect` (§ Architecture). A change the brief does not cover goes to
     the user as an amendment first.
   - After the answers, record any design-level ones in the brief as an
     amendment that the user approves, then resume the coder.
   - **Housekeeping: the docs pass.**
     Every step updates the docs its change touches, in the same step, so
     the docs are reviewed and committed with the code. The coder does it as
     the last part of the implementation and of every fix round, and lists
     each doc in the impl report's `## Docs updated` (or "none, because …").
     - **Which docs:** the repo's `CLAUDE.md` section **Docs to keep
       current** lists them, each with the change that makes it due (e.g.
       "a migration → the schema doc"). Read it when planning and when
       spawning the coder. A repo without that section: ask the user once
       to add it, and until then use the docs the repo's `CLAUDE.md` names.
     - **Schema docs** are the hard rule: a step whose migration is not in
       the repo's schema doc does not pass gate B.
     - The brief's *Where* lists the due docs under **Docs (housekeeping,
       by the coder)**. The orchestrator edits no doc at approval, except the
       decisions recorded in the repo's product plan at gate A.
     - Tell the coder this in every spawn prompt. Before gate B, check the
       impl report's `## Docs updated` against the diff yourself.
3. **Code-review loop.**
   - **Browser runs at their level**, where the repo has browser tests. The repo's browser
     tests have a quick whole-app run, a whole-suite run and a release level
     (settings: *Browser tests*). The coder makes targeted runs (the
     whole-suite level with spec files) as often as it needs, and may make
     the quick whole-app run. It makes the whole-suite run once, when the coding is done,
     and again only with a reason it states in the report. In a fix round it
     makes targeted runs only. It records the exact counts in the impl
     report. The code reviewer never runs the whole suite: it relies on the
     coder's run and re-runs only the specs one of its own findings needs;
     tell it so in the spawn prompt. The release level runs only in the release
     (the repo's release tests run it after the unit suites) and when
     the user asks (settings: *Browser tests*).
   - Spawn `code-reviewer` with the step ID and the round number. From
     round 2 on it verifies the fix round only (its *Round 2 and later* rule):
     name the findings the fix round addressed.
   - **Every finding is fixed, minors and nits included**: asking the user
     about each minor finding costs more than fixing it. A fix round covers all open findings of the review.
   - If any `blocker` or `major` finding is open, spawn `coder` for the fix
     round, then review again.
   - If only `minor` findings and nits are open, spawn `coder` (Sonnet) for
     one fix round, without asking the user. A fix that changes only tests,
     code comments, docs or step files needs no new review: read its
     impl-report section and check its suites are green.
   - **Async verify review.** When that
     minor-only fix round changed production code, the verify review does
     not block: set the step to gate B, snapshot it, and start the next
     step's coder; spawn the verify review at the same time (it only reads
     code). Tell the reviewer its diff, `diff S00N --from-round <n>` (the
     round before the fix round). If it finds a `blocker` or `major`,
     stop the next step's coder at its next hand-back and fix it first. Its
     minor findings and nits are fixed in the next fix round on the tree,
     land in the next step's snapshot, and are answered in the older step's
     impl report (its snapshot is not replaced). Gate B names the review as
     still running, or its result.
   - Stop after **3 rounds** and ask the user. The fix round for minors and
     nits does not count toward the 3.
   - Before each fix round, check the findings yourself. These go to the user
     at gate B, not to the coder:
     - a finding that contradicts the approved brief, or needs a design
       decision;
     - a finding whose fix changes behaviour the user approved;
     - a finding the review itself calls optional, such as a phone check.

     Tell the coder which findings it leaves out, and why.
4. **Gate B: STOP.** Report:
   - the test result;
   - what was built;
   - any departures from the brief, with your view on each;
   - the docs updated (the impl report's `## Docs updated`), in one line;
   - the findings fixed without asking, in **one line**: the count by
     severity and their IDs ("Fixed without asking: 2 minor, 3 nits —
     CR1-02…CR1-06; details in the impl report"). Give no more detail unless
     the user asks;
   - each finding held back for the user (step 3), with the question it
     raises;
   - the browser-test result (the coder's whole-suite run at the end of coding, the targeted runs of the fix rounds, and the results) and the `[auto]` checks as
     passed tests, each with its test;
   - the real-device checks: the **important** ones as the checklist from the
     impl report's `## Manual checks`, the rest as a plain list, and that their
     rows are in the repo's device-check list for the user or the named person
     (settings: *Device checks*). The user decides which checks are which and may skip
     any;
   - the feedback count, in one line: the `unread:` line of
     `tooling/step-feedback.bat --new`, and "propose `/step feedback`" when it is 20 or more
     (§ Feedback).

   **Architecture as built** (§ Architecture): before the snapshot, run the
   architect when the step had proposed changes or its diff changes the
   structure.

   **Snapshot at gate B** (§ Snapshots): when the step reaches gate B, run
   `uv run --no-project python tooling/steps/step_snapshot.py snapshot S00N "S00N: <commit message>;"`
   (not the `.bat`: `cmd //c` garbles a quoted message) and
   give the user its line. The next step may start at once.

   The user checks, then **commits** (with the `S00N:` prefix), or adopts the
   snapshot (`tooling/step-snapshot.bat adopt S00N`). Set the status to
   `Done` only when the user says it is committed **and** every important check
   is `[auto]` (a passing browser run), ticked by the user or for the named person,
   or explicitly skipped by the user. A named person's result comes back through
   the user: record it as `[x] <check> — by <name>, DD-MM-YYYY` in the impl
   report and in the row's *Done* column of the device-check list; a skip as
   `[skipped] <reason>` in the user's words. Record the count in the status,
   e.g. `Done (committed abc123; checks: 6 auto, 2 done by <name>, 1 skipped —
   <reason>)` (settings: *Device checks*). Never tick a check yourself.

   **Clean up**: once the status is `Committed`, `Done` or `Dropped`, run
   `uv run --no-project python tooling/steps/step_clean.py S00N --apply` and add
   its last line to the status report. It deletes the step's scratch files
   (brief copies, facts files, test logs, builds, scripts) and its snapshot and
   round refs, and never touches the step's folder (§ Commands, `/step clean`).

## Architecture

The architect and the architecture doc: when it runs at the brief and before gate B, the gate A
and gate B lines, `/step architecture`, the page. **Read `reference/architecture.md`** at a
structural change, an ARCHITECTURE UPDATE NEEDED hand-back, before gate B, when a step is dropped
or its structural design is turned down at gate A, or for `/step architecture`.

## Roadmaps

The planner cuts a big feature into a roadmap (`docs/roadmap/`), with a slide deck, up to gate R.
**Read `reference/roadmaps.md`** for `/step roadmap`, `/step plan R0N.n`, and when a step taken
from a roadmap is Done.

## Advice

The advisor (`advisor`) answers one technical question with research and
read-only experiments.

- **Who asks**: the orchestrator (phase 1), the brief writer, a coder or the code reviewer through
  an **ADVICE NEEDED** hand-back (phase 2), or the user (`/step ask`). A
  subagent cannot start another agent, so every request goes through the
  orchestrator.
- **The spawn prompt** gives: the step and its folder, the question in one
  sentence, why it matters, what is already known or was tried (with the
  evidence), the candidates to check, and the topic name for the file.
- **The answer** is `0-advice-<topic>.md` in the step's folder. Read it, and
  carry its effect into the brief (through the brief writer: an answered finding, a changed section),
  the coder's next run, or the review. Its *recommendations* are advice: a
  design choice in it still goes to the user at gate A or as an amendment.
- **The user's checks** in the advice (things only the user can do on their
  machine) become manual checks of the step, or questions at the next gate.
- **Not for**: design decisions, reviews, or facts a `grep` or a three-line
  check answers (the asker checks those itself; brief writer's self-check item 1).

## Feedback

Every agent's file ends with `## Feedback` (README § Rules for every agent). Name a recurring
item at a gate in one line; gate B ends with the unread count, and proposes `/step feedback` at
20 or more. Fix nothing in the workflow without the user's OK. **Read `reference/feedback.md`**
before the first spawn of a session (spawn prompts name the dropped themes), at each gate, and
for `/step feedback` and the feedback log.

## Snapshots

At gate B, and after every coder hand-back, `step_snapshot.py snapshot` records the step as a
commit under `refs/steps/` (rounds under `refs/step-rounds/`), so each step gets its own commit
while the next is coded. **Read `reference/snapshots.md`** before the first snapshot or diff of a
session, before adopting or committing for the user, and for a stale snapshot.

## Claims and the watchdog

One orchestrator session at a time works on a step: take its claim before any command writes its
files, mark every agent you spawn, start the watch, release at the gates. **Read
`reference/claims.md`** before the first claim of a session, and when a claim is refused or a
watch exits 3.

## Parallel steps

A second coder may work in its own git worktree when two long steps share no file, only when the
user says so. **Read `reference/parallel.md`** for `/step ls` and when planning a step (to name the pairs that
qualify), before setting one up, and at its join.

## Listing

**Read `reference/listing.md`** for `/step ls`.

## Check

**Read `reference/check.md`** for `/step check`.

## Messages to the user

The user reads gates on a phone and should never scroll back and forth to find
the question. Every gate (A, B, R, the fix
lane's gate B), every amendment shown for approval, and the pre-flight result are
one **card**, in this order. Other messages and questions (progress, `check`, 
`feedback`, `stats`, a reply in conversation) keep the plain style of § Rules:

```
━━ S0NN · <gate or topic> · <state in 3–5 words> ━━━━━━━━━━━━━━━━━
Summary   1–2 lines: what happened and where it stands now.

Details   Short labelled lines, never paragraphs:
          Bug ...... / Change ... / Tests .... / Review ... / Snapshot . / Files ....
          (gate A: the brief's verbatim sections go here, under their headings)

Pending   At most 3 lines: things waiting on the user elsewhere
          (other steps, device checks, an uncommitted repo). Omit when none.

Decide    1. <The question?> One line: why it matters, what each answer does.
             (a) <option> ★   (b) <option>   (c) <option>
          2. …
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Reply e.g. "1a 2b".
```

- **Summary first, Decide last.** The questions sit next to the input box, so
  the user never scrolls up to find them. ★ marks the recommended option; each
  option says its consequence in a few words.
- **Record the open questions in the files** (the brief's Review log or § Open
  questions, the impl report, the pre-flight report), so `recap` can rebuild
  the card after a long scroll or `/clear`.
- **Long gate A**: offer the brief as a private artifact page in one line of
  *Pending*.

## Rules

- **Never commit, push, build, deploy or release.** The subagents don't either.
  Two exceptions, both the user's decision: the gate B
  snapshot under `refs/steps/` (§ Snapshots; no branch moves, nothing is
  pushed), and committing or adopting when the user asks for it in the
  current request.
- **The agents' rules** are `docs/steps/README.md` § Rules for every agent: what
  needs no approval, the hand-backs, outside the repo, the test run name, the
  shell, the writing style, feedback. They hold for you too. Subagents can't ask
  the user anything: their questions come back to you, and you put them to the
  user. Name the outside-the-repo limit in every spawn prompt that runs
  experiments.
- **Never edit a review file**, and never fabricate a subagent's result. Wait
  for its completion notice.
- **Recommend clearing the context.**
  The step files are the whole hand-over, so a fresh session loses nothing
  that matters, and a long one costs more and drifts. Recommend `/clear`, in
  one line at the end of the message, when **all** of these hold:
  - no subagent is running (they report back to this session only);
  - every user answer and decision of the session is recorded in a brief,
    an impl report or the repo's product plan, and every gate shown is in the step files;
  - the work just reached a natural break: a series of steps at gate B and
    snapshotted, a brief approved before a long coding run, a release, or
    the user switching to another topic;
  - the session is long: several steps, or many hours of agent work.

  Say what the fresh session starts with ("After `/clear`, run `/step ls`;
  S044 is at gate A"). Never clear or compact by yourself. When agents are
  still running, say instead when a break will come ("after S045's review").
- **Keep the user informed.** Between rounds, one or two lines are enough:
  "BR round 2: 0 major, 3 minor — answering", or "Coder (Sonnet) done, tests
  green — starting code review r1".
- **Reports at the gates.** Short, in plain terms, and naming the standards
  touched, where the repo has a standards rule (settings: *Standards*).
- **Your own messages** follow writing style scope A, like the step files: gate reports,
  progress lines and questions. The brief's sections shown verbatim at gate A and the user's own
  words are quoted, so exempt.
- **The user's IDE reformatting** (README § IDE reformatting) is theirs: carry on, don't ask about
  it, and don't mention it at the gates.
