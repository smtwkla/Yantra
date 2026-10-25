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
| Advisor | `advisor` | Fable |

The step files are the only hand-over. Conventions: `docs/steps/README.md`.
Read it before starting.

## Commands

- `/step plan <topic>`: open a new step and run **phase 1**. Propose the track
  (below). `/step plan lite <topic>` or `/step plan full <topic>` forces it.
- `/step fix <the bug>`: fix a small bug on the **fix lane** (§ Fix lane),
  with no stop for the user before gate B.
- `/step amend S00N <request>`: write amendment `A<n>` in § 10 of the brief.
  Run the brief reviewer on it only if the user asks. Then stop at gate A.
- `/step implement S00N` (alias `/step code S00N`): the brief, or amendment,
  must be `Approved`. Run **phase 2**.
- `/step review S00N`: run **phase 2** from its code-review loop, for code that
  already exists.
- `/step ask S00N <question>`: run the **advisor** on one technical question for
  the step (§ Advice), and report its answer. Change nothing else.
- `/step status [S00N]`: report the step's files, status and open findings.
  Change nothing.
- `/step ls [all | deferred]`: list the steps not yet `Done`, `Dropped` or
  parked, then the queued ideas, as one table (§ Listing). `all` also lists
  Done, Dropped and parked steps; `deferred` lists only the parked
  (deferred) ones (25-10-2026, by KLA).
- `/step check`: check the step files against each other and git (§ Check).
  Report the problems and the fixes you propose; change nothing until the user
  says which to make.
- `/step feedback [S00N …]`: run `tooling/step-feedback.bat` once (every step, or
  the ones named): the agents' `## Feedback` items, grouped by label (§ Feedback).
  Report the points that recur or cost real time, and propose the 3–5 changes
  worth making; change nothing until the user says which.
- `/step stats [S00N]`: run `tooling/step-stats.bat` once (it writes
  `scratch/step-stats.md`): review rounds, findings by severity, late blockers
  and majors, time, tokens and e2e cost per step and per role, from the step
  files and the stored transcripts. Report the main numbers and what they
  suggest to cut (time, tokens) or to tighten (accuracy); change nothing.

When the user just says "go on" or "next", find where the step stands from its
files and its Status, and continue from there.

## Tracks

Every step runs on one of two tracks (README § Tracks), or a small bug on the
fix lane (§ Fix lane). The track is in the
brief's header (`Track: light | full | fix`) and in the index row.

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
- **A track finding alone is `minor`** (23-10-2026, from S029: its only major
  was "belongs on the full track", with the design sound, and it paused the
  step for a process question). It still switches the track as above, and the
  user may keep light at gate A. `blocker` and `major` stay for risks the brief
  leaves unhandled.

## Fix lane

A small bug is fixed without a brief review and without gate A (standing
rule, 24-10-2026, by KLA). The user's request is the approval.

- **The fix lane only if all hold** (otherwise propose light or full, and ask):
  - it fixes behaviour against what a brief, Plan.MD or the docs already say,
    and adds no feature;
  - about **5 files or fewer**, tests included;
  - no permissions: RBAC keys, roles, `SITE_SCOPED`, login, the network gate;
  - no interface change: no API route's URL, body or response shape, no
    migration or schema change, no setting;
  - no security-sensitive code: uploads, file serving, secrets, push or email
    addresses;
  - no locking, transaction or concurrency change.
- **Run it like this:**
  1. Take the next free `S0NN`. Write a short `1-brief.md` with
     `Track: fix`, `Status: Implementing (fix lane)` and `Baseline:` set to
     HEAD. It holds the bug, the steps to see it, the cause with `file:line`
     (checked in the code, never guessed), the fix, the files, and the test
     that fails on the bug. Add the index row.
  2. Ask the user only if the cause is unclear, or the bug has two fixes that
     behave differently. Then the step leaves the fix lane.
  3. Spawn `coder` (Sonnet) for the step. It writes the failing test first
     (*red, then green*), runs the full unit suites, and makes targeted e2e
     runs when a screen changed (the whole e2e suite at Normal once at the
     end, as in § Phase 2 step 3).
  4. One `code-reviewer` round (Opus). Every finding is fixed (§ Phase 2
     step 3). A `blocker` or `major` gets the usual loop.
  5. Gate B, short: the bug, its cause, the change, the tests, "ready to
     commit with the `S0NN:` prefix".
- **Leave the fix lane** as soon as the coder, the reviewer or you find that
  a criterion fails. Stop, set the track to light or full, and bring the step
  to gate A with a brief of that track.

## Phase 1: brief

1. **Write the brief.** The ID is the next free `S0NN` in the README index.
   - Write `1-brief.md` with status `Draft` and its `Track`, then add the index
     row. A light brief uses the short template.
   - Split the checks a person would make into **Automated** (an e2e browser
     test the coder writes: a screen opens, a flow completes, a message shows,
     a dialog fits a phone) and **On a real device** (camera, paper, the iPhone
     keyboard, a real Keycloak login), each device check with its account,
     network and where (dev server on KLA's laptop, production on the TEST
     machine, or either). Mark the ones that matter as **important** (README
     § Manual checks).
   - Follow CLAUDE-COMMON "Show the plan before building" and the Yantra rule on
     standards.
   - Ask the user first only about decisions that change the design. Other open
     points go into the brief's § Open questions.
   - **Size** (6a, 22-10-2026, from `/step stats`: S021, 57 files, one Opus
     coder run of 70 minutes and 0.5 M tokens). When the brief's *Where* lists
     more than about **25 files**, or holds two concerns that could ship apart
     (a backend engine and its screens, a new shell and a feature in it),
     propose a split into two steps in one line, with the cut, before review.
     The same when the draft passes **600 lines**, or adds more than one table
     and two screens. The user decides.
   - **Facts run** (23-10-2026, from S029's `/step stats`: most brief-review
     findings were facts about existing code the planner had not checked).
     Once the draft is written, run `tooling/step-brief-facts.bat S0NN` (it
     writes `scratch/brief-facts-S0NN.md`): every `backticked` file, test id,
     route and code name in the brief, with where it is defined and which code
     and test files use it. Fix every claim it contradicts: a "new" name that
     exists, a file or line that isn't there, a test file using a changed
     function or route that § Tests doesn't name. Name every identifier the
     brief relies on in backticks, so the run covers it. Run it again after
     large edits. It feeds self-check items 1 and 5 below.
   - **Self-check before review round 1** (22-10-2026, from the analysis of
     all brief and code reviews of S001–S027: 61 majors, 347 minors; by weight
     the causes are rules left to the coder, unverified claims, tests,
     permissions and identity, phone screens, locks). Check the draft against
     each item and fix it before spawning the reviewer:
     1. **Evidence for every claim** about code, a library, a browser or the
        environment: `file:line` or a run result beside it. Run a 3-line
        `uv run python` or `node -e` check for library behaviour (QR version,
        Pillow, Bootstrap, urllib parsing). Open the file for "the API shows
        X". Grep the devops repo, compose and cron for a task said not to
        exist. A claim with no evidence is marked "to verify".
     2. **Locks**: one numbered lock sequence per route — table, row, mode,
        including the shared locks taken through foreign keys — compared with
        the LOCK ORDER notes in `tickets.py` and `masters.py`. Decide from the
        columns the locking statement reads, never from a plain read made
        after an earlier plain read (REPEATABLE READ). A counter or "same
        transaction" rule says what a rollback does.
     3. **Permissions**: the exact key of every route and button, held at
        which site (`SITE_SCOPED`); reads behind a senior key scoped to the
        sites where it is held; no login or personal data beyond its key.
     4. **Identity paths**: for each editable field, whether it changes who
        can log in or what they see (`active`, login name, role, site).
        Cover actor = target, normalised names, inactive people, and reused
        routes that hard-code another key. A request with no identity gets
        nothing, never admin.
     5. **Tests**: the existing tests the change breaks, by file and test
        name — always check `test_role_matrix`, `conftest.py` `_TABLES`, the
        `db_down` fixture and the `test_migration_*` upgrade tests. For each
        new test, its fixture and whether the session DB gives its starting
        state. The e2e specs (targeted or full) and the S024 conventions
        (allowed 400s, set-up by API, `expectDialogFits`, the open-dialog
        wait, per-lane databases).
     6. **No rule left to the coder**: every input's missing, empty,
        wrong-type and boundary case; a `PUT` without a field; the bounds of a
        setting; where a new screen or menu item lives.
     7. **States and events**: for every state change, actor × state ×
        already-in-the-target-state. For every alert or event, the line that
        writes it and whether that path always runs.
     8. **Plan.MD and earlier steps**: nothing decided there is re-asked or
        contradicted; a departure is stated as one.
     9. **Self-consistency and staleness**: after every edit, grep the brief
        for the old phrase and each changed number. For a brief planned ahead
        of its turn, list the steps committed since its baseline and check the
        migration number, the lock notes, the e2e conventions and new README
        rules.
     10. **Migrations**: every column, ENUM and index the feature writes;
         `_PRECONDITIONS` against production's real rows; the settings dicts
         and routes a new setting touches. The brief's *Where* lists
         the schema doc, and every other doc the change touches (the repo's
         `CLAUDE.md` § Docs to keep current), under *Docs (housekeeping, by
         the coder)* (§ Phase 2, the docs pass).
     11. **The database down and the worker** (CLAUDE.md): what each new hook,
         route and task does when the DB is unreachable. For a worker task,
         what is stored on success, on retry-later and on no-retry, and which
         transaction holds the claim and the result.
     12. **Security of new outside input**: a URL, file or address checked
         with the same parser that will use it (S021 CR1-01).
     13. **Screens**: for each dialog or control, the composable and its call
         contract (what `blank` returns, what `open(seed)` does), the fields
         that can be defaulted, the one-tap path of the common case, its place
         on the page, the reason shown for a disabled control on a phone, and
         how a destructive control is protected.
     14. **Standards**: the clause number and one plain sentence of what it
         says, checked; unverified → "to verify" instead of a number.
     15. **Process and device checks**: grep for "synced from" or "generated"
         before editing a file; release and deploy actions in order, each
         runnable where it is placed; the machine, account and network of
         every manual check; nothing on the device list a browser could do.
   - **Advice** (25-10-2026, by KLA). Before writing a claim or a design
     decision that rests on how a library, browser, operating system or
     device really behaves, and that you cannot check in a few lines, spawn
     `advisor` (§ Advice) instead of guessing. Also when the user asks how
     something can be done, and after a brief review whose finding asks
     "how do we know this works?". Cite the advice file in the brief.
2. **Review loop.**
   - Set the status to `In review`.
   - Spawn `brief-reviewer` with the brief's path, the round number and the
     facts file (`scratch/brief-facts-S0NN.md`, from a run on the current
     draft).
   - Read its review file. Answer **every** finding in the brief's Review log
     (`Accepted` / `Rejected` / `Deferred`) and revise the brief text. Answer
     the review's `## Nits` list in **one** Review-log row ("BR2-06…BR2-09:
     accepted", naming any rejected one with its reason), not a row each.
   - Round 2 and later re-check only what changed (the brief reviewer's
     *Earlier rounds* rule): tell it which sections the answers changed.
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
   round where that applies. Give every coder and code reviewer its own test
   run name (`YANTRA_TEST_RUN`, e.g. `s021c1`, `s021cr2`), so agents running
   tests at the same time never share a database.
   - If it returns **QUESTIONS FOR THE USER**, stop and ask them.
   - If it returns **ADVICE NEEDED**, spawn `advisor` with its question and
     what it tried (§ Advice), then resume the coder with the advice file.
     If the answer changes the design, it goes to the user as an amendment,
     never as a silent change. The code reviewer may return the same, and is
     answered the same way.
   - After the answers, record any design-level ones in the brief as an
     amendment that the user approves, then resume the coder.
   - **Housekeeping: the docs pass** (standing rule, 24-10-2026, by KLA).
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
       by the coder)**. The planner edits no doc at approval, except the
       decisions recorded in the plan doc at gate A.
     - Tell the coder this in every spawn prompt. Before gate B, check the
       impl report's `## Docs updated` against the diff yourself.
3. **Code-review loop.**
   - **Browser runs at their level** (standing rule, 25-10-2026, by KLA;
     levels S047). `tooling/run-e2e-tests.bat` has three levels: **Basic**
     (`--level=basic`: the `@smoke` journeys and `screens.spec.js` on
     `phone-chromium`, about 2 minutes), **Normal** (no flag: every test on
     `phone-chromium`, the `@device` tests on `desktop-chromium`) and
     **Full** (`--level=full`: every test on all three devices, the iPhone
     in its container). The coder makes targeted runs (Normal with spec
     files) as often as it needs, and may run Basic for a quick whole-app
     check. It runs the whole suite at Normal once, when the coding is done,
     and again only with a reason it states in the report. In a fix round it
     makes targeted runs only. It records the exact counts in the impl
     report. The code reviewer never runs the whole suite: it relies on the
     coder's run and re-runs only the specs one of its own findings needs;
     tell it so in the spawn prompt. The Full level runs only in the release
     (`tooling/release-tests.bat` runs it after the unit suites) and when
     KLA asks.
   - Spawn `code-reviewer` with the step ID and the round number. From
     round 2 on it verifies the fix round only (its *Round 2 and later* rule):
     name the findings the fix round addressed.
   - **Every finding is fixed, minors and nits included** (standing rule,
     24-10-2026, by KLA: asking the user about each minor finding cost more
     than fixing it). A fix round covers all open findings of the review.
   - If any `blocker` or `major` finding is open, spawn `coder` for the fix
     round, then review again.
   - If only `minor` findings and nits are open, spawn `coder` (Sonnet) for
     one fix round, without asking the user. A fix that changes only tests,
     code comments, docs or step files needs no new review: read its
     impl-report section and check its suites are green.
   - **Async verify review** (standing rule, 25-10-2026, by KLA). When that
     minor-only fix round changed production code, the verify review does
     not block: set the step to gate B, snapshot it, and start the next
     step's coder; spawn the verify review at the same time (it only reads
     code). Tell the reviewer the snapshot to diff against (the step's own
     `refs/steps/S00N` and its parent). If it finds a `blocker` or `major`,
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
   - the e2e result (`tooling/run-e2e-tests.bat`: the coder's whole-suite run at Normal at the end of coding, the targeted runs of the fix rounds, and the results) and the `[auto]` checks as
     passed tests, each with its test;
   - the real-device checks: the **important** ones as the checklist from the
     impl report's `## Manual checks`, the rest as a plain list, and that their
     rows are in `docs/steps/device-checks.md` for the user or the named person
     (today IT Admin). The user decides which checks are which and may skip
     any.

   **Snapshot at gate B** (§ Snapshots): when the step reaches gate B, run
   `tooling/step-snapshot.bat snapshot S00N "S00N: <commit message>;"` and
   give the user its line. The next step may start at once.

   The user checks, then **commits** (with the `S00N:` prefix), or adopts the
   snapshot (`tooling/step-snapshot.bat adopt S00N`). Set the status to
   `Done` only when the user says it is committed **and** every important check
   is `[auto]` (a passing e2e run), ticked by the user or for the named person,
   or explicitly skipped by the user. A named person's result comes back through
   the user: record it as `[x] <check> — by <name>, DD-MM-YYYY` in the impl
   report and in the row's *Done* column of `device-checks.md`; a skip as
   `[skipped] <reason>` in the user's words. Record the count in the status,
   e.g. `Done (committed abc123; checks: 6 auto, 2 done by IT Admin, 1 skipped —
   iPhone)`. Never tick a check yourself.

## Advice

The advisor (`advisor`, Fable) answers one technical question with research
and read-only experiments (25-10-2026, by KLA; first run: S053's power
readings, `0-advice-power-readings.md`).

- **Who asks**: the planner (phase 1), a coder or the code reviewer through
  an **ADVICE NEEDED** hand-back (phase 2), or the user (`/step ask`). A
  subagent cannot start another agent, so every request goes through the
  orchestrator.
- **The spawn prompt** gives: the step and its folder, the question in one
  sentence, why it matters, what is already known or was tried (with the
  evidence), the candidates to check, and the topic name for the file. Say
  that the rule **Agents change nothing outside the repo** applies.
- **The answer** is `0-advice-<topic>.md` in the step's folder. Read it, and
  carry its effect into the brief (an answered finding, a changed section),
  the coder's next run, or the review. Its *recommendations* are advice: a
  design choice in it still goes to the user at gate A or as an amendment.
- **The user's checks** in the advice (things only the user can do on their
  machine) become manual checks of the step, or questions at the next gate.
- **Not for**: design decisions, reviews, or facts a `grep` or a three-line
  check answers (do those yourself, self-check item 1).

## Feedback

Every agent ends its file with `## Feedback` (25-10-2026, by KLA; README § Folder and files): at
most 5 one-line items, `waste`, `hindrance`, `rule` or `idea`, each with its evidence, or `- none`.

- **Tell each subagent** in its spawn prompt that its file ends with the section (its agent file
  gives the form).
- **At each gate**, read the feedback of the files written since the last gate. When an item
  recurs or cost real time, name it in one line ("Feedback: the coder lost 3 runs to cmd quoting —
  see `/step feedback`"). Fix nothing in the workflow without the user's OK.
- **`/step feedback`** runs `tooling/step-feedback.bat` (all steps, or the IDs given): every item
  with its step, file and label. Group the items that say the same thing, count them, and propose
  the few changes that would save the most; the user decides.
- Feedback is about the workflow, the tools and the rules, never a second list of findings.

## Snapshots

Standing rule (24-10-2026, by KLA): each step gets its own commit, while the
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
  A fix after gate B re-runs `snapshot` for the same step; only the newest
  snapshot can be replaced.
- **One coder writes at a time.** A snapshot holds whatever is in the tree,
  so two coders writing at once mix their steps. Reviews and brief work are
  read-only for code and may overlap. Don't start a coder while another is
  writing, unless the user says so, or the second one works in its own
  worktree (§ Parallel steps).
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

## Parallel steps

An option (24-10-2026, by KLA), not the default: a second coder works at the
same time in its own git worktree, so two long steps don't wait on each other.

- **When it pays.** Both steps would take a coder 30 minutes or more, and
  their *Where* lists share no file. Short fix-lane steps run one after the
  other instead: the join below costs about what they would save.
- **Never in parallel:**
  - two steps that both add a migration (`local_db.py` and the schema docs
    always conflict);
  - two steps that touch the same screen or shared frontend code (the
    router, the nav, `FormModal.vue`, `api.js`, `e2e/support/`), or the same
    entries of `conftest.py`;
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
  Browser tests still take turns: the e2e lock is per machine (in the main
  working folder's `scratch/`, so a worktree's run waits for it too, S047).
- **Shared step docs.** In a worktree the coder edits no shared step doc:
  not the README index, not `device-checks.md`. It writes the changes it
  needs, word for word, in its impl report under `## Shared docs`; the
  orchestrator applies them after the join, so row numbers never clash.
  The docs-pass docs (plan doc, schema doc, domain docs, `CLAUDE.md`) stay
  with the coder, in its worktree, reviewed with the code.
- **The join** (at the step's gate B):
  1. the step's result is one commit on its branch (the gate B snapshot of a
     worktree step);
  2. put it on top of the current chain (the newest snapshot, or `HEAD`)
     with `git cherry-pick` in a temporary worktree, never in the user's;
  3. a conflict: resolve it when both sides can be kept; bring it to the
     user when the two steps disagree on behaviour;
  4. **test the joined code**: the backend suite and the targeted e2e specs
     of both steps (they were never tested together). Red is a blocker of
     the joined step;
  5. snapshot the result as `refs/steps/S0NN`, apply the `## Shared docs`
     changes, then remove the worktree and its branch (`git worktree remove`,
     `git branch -D`), only after the snapshot exists.

## Listing

`/step ls` builds the table fresh every time; it is never stored, so it can't
go stale. **Run `tooling/step-ls.bat` (`all` or `deferred` passes on) once and
build the table from its output** — don't read the step files or run git yourself. The
script prints, per step not yet Done, Dropped or parked (all steps with
`all`, only the parked ones with `deferred`): the
index title and folder, the brief's `Status:` line, the latest review with its
verdict paragraph, the commits whose subject names the step, whether an impl
report exists, and the working-tree changes in the step's folder (and, for an
uncommitted step, among the files its impl report names); then the queued
items with a step ID, the shared docs changed (README, `device-checks.md`), the
snapshots not yet adopted (`refs/steps/`), and
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
- **Step, Title**: from the index in `docs/steps/README.md`, then its
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
  "In code review" but the step is committed → "set Status to Done".

Below the table, list the unclaimed working-tree changes, grouped by the step
you think they belong to (say it is a guess) or as "no step", so the user can
sort them before committing. Add a note for anything that looks wrong: a Status
that contradicts the commits or the review, a step committed but not `Done`
with no check named as pending, a stale `Baseline:`.

## Check

`/step check` finds inconsistencies in the step files. **Run
`tooling/step-check.bat` once.** It prints one line per problem, tagged with
the check's number, and changes nothing:

1. the brief's Status and its README index row are in different stages;
2. a commit names the step but the Status is not Committed or Done, or the
   Status names a hash that is not in the current branch's history;
3. `Done`, but the impl report still has an open important check (`- [ ]`);
4. `Committed`, every important check resolved, but not `Done`;
5. a BR / BS finding of a brief review is not answered in the brief;
6. a step approved and not yet committed has no `Baseline:`, or its commit is
   not in the history;
7. `device-checks.md`'s *Done* column and the impl report's ticks disagree;
8. an index row without a folder, a folder without a row, or a step ID used
   twice;
9. a stage's files are missing (an impl report, a code review), or an impl
   report exists before approval;
10. working-tree changes no step claims.

Then add what the script cannot judge, opening only the files a problem points
to: a Status that contradicts the latest verdict, a gate shown with findings
still open, unclaimed changes and the step they probably belong to (say it is
a guess), a check that is a false alarm and why. Report as a table: step,
problem, proposed fix. Fix nothing until the user says which fixes to make;
then follow the usual rules (never tick a check for someone, never edit a
review file).

## Rules

- **Never commit, push, build, deploy or release.** The subagents don't either.
  Two exceptions, both by the user's decision of 24-10-2026: the gate B
  snapshot under `refs/steps/` (§ Snapshots; no branch moves, nothing is
  pushed), and committing or adopting when the user asks for it in the
  current request.
- **Agents change nothing outside the repo** (standing rule, 25-10-2026, by KLA). Every
  agent — planner, advisor, reviewers, coder — changes only the repo's working tree and
  Claude's memory:
  - no installing software, packages, browsers, drivers or scripts on the machine; no global
    npm / pip / uv installs;
  - no changes to the operating system's settings, the registry, services, scheduled tasks,
    environment variables, or other repos;
  - experiments are read-only: read a value, run a small check; any script stays in the
    session scratchpad or `scratch/`;
  - allowed, because the repo's own tooling does it as written: what the repo's `tooling/`
    scripts do when run (e.g. installing Playwright's browsers, starting the e2e containers,
    the release tests' temporary worktree), installing the repo's own lockfiles when a step
    changes dependencies, and temporary git worktrees the agent removes itself;
  - anything else outside the repo: ask the user first.
  Put this limit in every spawn prompt that runs experiments.
- **Subagents can't ask the user anything.** Any question they raise comes back
  to you, and you put it to the user.
- **Never edit a review file**, and never fabricate a subagent's result. Wait
  for its completion notice.
- **Recommend clearing the context** (standing rule, 25-10-2026, by KLA).
  The step files are the whole hand-over, so a fresh session loses nothing
  that matters, and a long one costs more and drifts. Recommend `/clear`, in
  one line at the end of the message, when **all** of these hold:
  - no subagent is running (they report back to this session only);
  - every user answer and decision of the session is recorded in a brief,
    an impl report or Plan.MD, and every gate shown is in the step files;
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
  touched, because the user is learning maintenance practice.
- **Writing style** (CLAUDE-COMMON § Writing style):
  - **Scope A** applies to every step file you or a subagent writes (brief,
    reviews, impl report, Review log answers) and to every message to the
    user: gate reports, progress lines and questions. Put the point first and
    use one term for each thing. In questions, state the question, then the
    options with their consequences, and mark the recommended one.
  - **Scope B** applies to the UI text a brief specifies: labels, buttons,
    messages and confirmations. It applies again to the text the coder writes
    into the screens.
  - Tell each subagent to follow it. The brief reviewer and the code reviewer
    raise a finding where the text breaks scope A or B. Quoted text is
    exempt: brief sections shown verbatim at gate A, and the user's own words.
- **IDE reformatting is expected** (README § IDE reformatting). Whitespace-only
  changes in a file the user has open are theirs: carry on, don't ask about
  them, and don't mention them at the gates. Before editing, re-read the file.
