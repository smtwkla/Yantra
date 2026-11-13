# Steps — briefs, reviews and reports

Each piece of work on the repo is a **step**. A step is planned, reviewed,
implemented and reviewed again across separate Claude Code terminals:

| Role | Model | Writes |
|---|---|---|
| Planner | Opus | `docs/roadmap/R0N-<feature>.md`: a big feature cut into items `R0N.n`, the seed of steps (gate R; `docs/roadmap/README.md`) |
| Advisor | Fable | `0-advice-<topic>.md` (on request) |
| Brief writer | Opus; Fable or Sonnet per brief | `1-brief.md` |
| Brief reviewer | Fable | `2-brief-review-rN.md` |
| Coder | Opus or Sonnet | the code + `3-impl-report.md` |
| Code reviewer | Opus | `4-code-review-rN.md` |
| Architect | Fable | the repo's architecture doc (§ The architecture doc) |

The files are the hand-over between terminals. Each terminal reads the files
it needs and does not rely on another terminal's chat.

## Step ID

- `S` + 3 digits: `S001`, `S002`, …
- IDs are global and sequential. They are never reused or renumbered. A dropped
  step keeps its ID with status `Dropped`.
- One step is one reviewable slice of work: one brief → one implementation →
  review. A step too big to review in one sitting is split into two steps.
- The ID is used everywhere: in the folder name, in the files, in finding IDs,
  and as the commit prefix (`S001: sites, units, equipment classes, unit access masters`).

## Folder and files

One folder per step: `docs/steps/S001-basic-masters/`. The slug is kebab-case
and is fixed once the folder is created.

The numeric prefix follows the workflow order, so a directory listing shows
progress:

| File | Written by | Purpose |
|---|---|---|
| `0-advice-<topic>.md` | Advisor | The answer to one technical question (how a library, browser, operating system or device really behaves; which option works), by research and read-only experiments, each claim labelled fact, assumption or recommendation. Asked by the orchestrator, a coder or a reviewer through the orchestrator (25-10-2026). Optional; a step may have none or several. |
| `1-brief.md` | Brief writer | The implementation brief: what, where, design decisions, open questions (CLAUDE-COMMON "Show the plan before building"), plus standards, tests and acceptance. Revised in place; its **Review log** answers each finding. |
| `2-brief-review-r1.md`, `-r2.md`, … | Brief reviewer | One file per review round |
| `2-brief-review-s1.md`, `-s2.md`, … | Brief reviewer | A staleness review: does the approved brief still hold for code changed since its baseline (§ Stale brief check) |
| `3-impl-report.md` | Coder | The mandatory post-implementation report (CLAUDE-COMMON "Report after implementation"). Its **Docs updated** section lists every doc the step changed (the docs pass, standing rule 24-10-2026; which docs: `.claude/CLAUDE.md` § Docs to keep current), or says why none; its **Fix rounds** section answers each code-review finding. |
| `4-code-review-r1.md`, `-r2.md`, … | Code reviewer | One file per review round, reviewing the working-tree diff against the brief |

**Feedback** (25-10-2026, by KLA). Every file an agent writes — advice, brief, brief review, impl report,
code review — ends with `## Feedback`: at most 5 items, one bullet each, labelled `waste`, `hindrance`,
`rule` or `idea`, each with its evidence, or `- none` (the agents' instructions give the form).
`/step feedback` collects them across steps (`tooling/step-feedback.bat`), by default only the
items not yet in the repo's **feedback log** `docs/steps/feedback-log.md` (27-10-2026): one row
per item read, with its theme and what was decided (`acted`, `dropped` or `noted`). The log is the
repo's own file, like the index; `.claude/skills/step/reference/feedback.md` gives its form.

## Header block

Every file starts with:

```
Step: S001 — Basic masters
Doc: brief | brief-review r1 | impl-report | code-review r1
Author: <role> (<model>)
Date: DD-MM-YYYY
Track: light | full
Baseline: <commit> [+ uncommitted S0NN, …]
Status: Draft | In review | Approved DD-MM-YYYY by <user> | Implementing | In code review | Done | Dropped
From: R0N.n            (only for a step taken up from a roadmap item)
```

`Track`, `Baseline` and `Status` appear in the brief only. The brief's status
is the step's status. `Baseline` is the code the brief was last reviewed against
(§ Stale brief check). Briefs written before 16-10-2026 have no `Track` line: they are full.

## Tracks

A step runs on the **full** track or, when it is small and safe, the **light**
track, so a small change doesn't carry a large step's ceremony.

**Light only if all of these hold** (otherwise full):
- no migration, and no change to existing data;
- no auth, RBAC or security-sensitive code (uploads, file serving, secrets,
  access checks);
- no transactions, locking or concurrency rules;
- follows an existing pattern: no new module design, no new dependency, no
  endpoint beyond plain CRUD;
- roughly 10 files or fewer.

The orchestrator proposes the track; the user confirms or overrides it.

| | Full | Light |
|---|---|---|
| Brief | All sections | The short template below |
| Brief review | Up to 3 rounds | 1 round; answers not re-reviewed unless a `blocker`/`major` is open |
| Gate A | Decision sections verbatim | A bullet summary + the brief's path (verbatim on request) |
| Coder | Sonnet or Opus | Sonnet |
| Code review | Up to 3 rounds | Up to 3 rounds (unchanged) |

**Switch to full** when the brief reviewer raises a `blocker` or `major`
finding, or the step turns out to meet a full-track criterion. The header and
the index row (`INDEX.md`) are updated, and the user is told. A finding that only says
"belongs on the full track" is `minor` (23-10-2026, S029): it switches the
track, and the user may keep light at approval.

**Facts run.** Before brief review round 1, the brief writer runs
`tooling/step-brief-facts.bat S0NN`: where each file, test, route and code name
the brief cites exists, and which tests use it. The brief writer fixes the brief
from it; the brief reviewer gets the output (23-10-2026, S029). Its *Cited lines*
section shows the text of each `file:line` the brief cites, and where a named
function or constant is now when it has moved (30-10-2026).

**Anchors by name** (30-10-2026): line numbers move when other steps are coded.
A brief planned ahead of a step it depends on, or citing a file that another
open step edits, anchors by name (function, test, constant). It adds
`file:line` only for files no open step touches.

**The light brief** (about a page):
1. What will be built, and out of scope;
2. Standards and practice: one or two lines;
3. Where: files and what changes in each;
4. Design decisions: only the real choices, with the rejected alternative;
5. Tests and acceptance, with the important manual checks marked;
6. Open questions and assumptions;
7. Amendments; Review log.

**The fix lane** (`Track: fix`, standing rule 24-10-2026). It is for a small
bug, fixed with no brief review and no approval gate: the user's request is the
approval. The bug qualifies only if every one of these holds:
- it fixes behaviour that a brief, the repo's product plan or the docs already describe, and
  adds no feature;
- the fix touches about 5 files or fewer, tests included;
- it touches no permissions;
- it changes no interface: no API shape, no migration or schema change, no
  setting;
- it touches no security-sensitive code, and changes no locking.

The brief holds the bug, how to see it, the cause (`file:line`), the fix, the
files and the failing test. Its header carries `Baseline:` (HEAD). The status
goes `Implementing (fix lane)` → `In code review` → `Gate B` → `Done`. The
coder is Sonnet and writes the failing test first. The code review is one Opus
round, and its findings are all fixed. If a criterion turns out to fail, the
step leaves the lane: it gets a light or full brief and goes to gate A.

## Manual checks

A brief's tests section lists the checks a person would make on the screens.
The ones that matter are marked **important**; the rest stay plain notes. Since
S024 they come in two kinds:

- **Automated** — anything a browser engine can judge: a screen opens, a flow
  completes, a refusal shows beside its field, a dialog's buttons fit a phone.
  Each becomes a browser test (settings: *Browser tests*) that the coder
  writes with the step. A test asserts what the user would see — the badge, the
  timeline line, the times card, the message — not only that a page opened.
- **On a real device** — the few a browser engine cannot judge (the kinds:
  settings, *Device checks*). Done by the user **or the named person**
  (settings: *Device checks*).

The rules:

- **The coder** writes a browser test for each automated check and runs
  the repo's browser tests. Only a passing run may mark a check in the impl
  report's `## Manual checks` as
  `- [auto] <check> — <test file>::<test name>`. Real-device checks go there as
  boxes, `- [ ] …` (important) or a plain list, and the coder appends them as
  rows to the repo's device-check list (settings: *Device checks*).
- **The levels** (S047). The repo's browser tests run at its levels (settings:
  *Browser tests*): a quick whole-app run, the whole-suite run (every test on
  the logic device, and the layout-tagged tests, which check layout or differ
  by device, on the other devices the settings name), and the release level.
- **The coder** runs the browser tests whenever the frontend or an API the
  screens use changed, and reports the real result. It makes targeted runs
  (the spec files of the screens the step changed, plus the ones the settings
  always add) as often as it needs, and may make the quick whole-app run. It
  makes the whole-suite run once, when the coding is
  done, and again only with a reason it states. In a fix round it makes
  targeted runs only.
- **The code reviewer** never runs the whole suite. It re-runs only the
  specs one of its own findings needs.
- **The release level** runs only in the release (the repo's release tests
  run it after the unit suites, on the same worktree of HEAD) and when the user
  asks (settings: *Browser tests*).
- **The device-check list** is the master list of open real-device checks, one row
  per check in plain words: what to do and see, account, network, where (the
  machines the settings name: *Device checks*) and
  done. A done row stays as the record (who, when).
- **The round trip.** The user hands the named person the rows (printed or by
  chat); the person reports back to the user; the user tells the orchestrator; the
  orchestrator writes `- [x] <check> — by <name>, DD-MM-YYYY` into the step's impl
  report and fills the row's *Done* column. The person never edits the file.
- **At gate B** the orchestrator shows the `[auto]` checks as passed tests and the
  real-device ones as the checklist. The user decides which checks are which,
  and can skip any.
- **Nobody ticks for someone else.** The orchestrator records the user's or the
  named person's answer (`[x] … — by <name>, DD-MM-YYYY`, or `[skipped]
  <reason>`), never ticking a box on their behalf.
- **Done** needs every important check `[auto]`, ticked for the user or the
  named person, or skipped by the user; the status records it, e.g.
  `Done (committed abc123; checks: 6 auto, 2 done by <name>, 1 skipped — <reason>)`
  (the repo's own example: settings, *Device checks*).

## Findings

- Brief-review findings are `BR<round>-<nn>` (e.g. `BR1-03`), staleness-review
  findings `BS<round>-<nn>` (e.g. `BS1-02`), and code-review findings
  `CR<round>-<nn>` (e.g. `CR2-01`).
- Each finding has a severity: `blocker`, `major`, `minor` or `nit`.
- The author answers every finding with one of these:
  - `Accepted`, with what changed;
  - `Rejected`, with why;
  - `Deferred`, with the step it goes to.

  The brief writer answers in the brief's Review log, and the coder in the impl report's Fix rounds.

## Gates

1. **Brief review.** The brief goes from `Draft` to `In review`. Review rounds
   repeat until no `blocker` or `major` finding is open.
2. **Approval.** (None on the fix lane, § Tracks.) Only the user sets `Approved`, after reading the brief as it
   stands after the last review round. On the full track the orchestrator shows its
   decision-relevant sections verbatim (what, out of scope, standards, design
   decisions, open questions) and lists the others by heading, rather than a
   summary; on the light track, a bullet summary and the path (§ Tracks). The coder
   never starts on an unapproved brief, nor on a stale one (§ Stale brief check). Anything the brief doesn't cover is raised with the user,
   not decided in code.
3. **Code review.** Status `In code review`. Rounds repeat until no `blocker`
   or `major` finding is open. Minor findings and nits are then fixed in one
   more fix round, without asking the user (standing rule, 24-10-2026). A
   finding that needs a design decision, or would change approved behaviour,
   goes to the user at gate B instead. Gate B names the fixed findings in one
   line; the impl report holds the details.
4. **Done.** The user commits; no terminal commits. The status becomes `Done`
   once the commit is confirmed and every important check is `[auto]` (from a
   passing browser run), ticked for the user or the named person (settings:
   *Device checks*),
   or explicitly skipped by the user (§ Manual checks).

Whoever changes a step's status also updates its row in `INDEX.md`.

## Amendments

A change requested after a brief is approved, while the step is not yet `Done`,
becomes an **amendment** rather than a new step:

1. **Write it.** The brief writer adds the amendment under the brief's **§ 10
   Amendments** as `A1`, `A2`, … It has its own header (requested by, status
   `Proposed` / `Approved DD-MM-YYYY by <user>`) and its own what, rules, where,
   tests and open points.
2. **Review it.** The brief reviewer reviews the amendment only if the user asks
   for it. Findings are numbered `BR-A1-<nn>`.
3. **Approve it.** Only the user sets an amendment to `Approved`. The coder
   implements nothing of it before that.
4. **Implement it.** The coder reports on it in a section
   `Amendment A1` of `3-impl-report.md`.
5. **Review the code.** The next code-review round covers it.

A change too big for the step being reviewed becomes a new step.

## Stale brief check

A brief is checked against the code as it stood when it was reviewed. Other
steps can change that code before this one is coded, so the brief can go stale
between approval and coding. The check catches it before the coder starts.

1. **Record the baseline.** Every brief review names the code it read:
   `Reviewed against: <commit> [+ uncommitted S0NN, …]`. When the user approves,
   the orchestrator copies the last one into the brief's header as `Baseline:`.
2. **Check before coding** (the step, or an approved amendment):
   - the orchestrator compares the files named in the brief's *Where*, and the
     modules they call, between the baseline and the working tree now (commits
     since the baseline plus uncommitted changes);
   - **nothing changed:** the coder starts;
   - **something changed:** one **staleness review**, `2-brief-review-sN.md`.
     The brief reviewer gets that diff and answers one question: does each
     statement in the brief still hold? Findings are `BS<n>-<nn>`;
   - the orchestrator answers them in the Review log as usual. A `blocker` or
     `major` finding changes what the user approved, so the brief goes back to
     the user (gate A) before coding. Minor findings and nits are fixed in the
     brief text and the coder starts;
   - the check refreshes the brief's anchors by name (§ Anchors by name): a
     `file:line` whose function or constant has moved gets the new line;
   - after the check, `Baseline:` is set to the code just checked.
3. **Skipped** only when the user says so; the orchestrator records it in the brief.

## Rules for every agent

Every agent of the step workflow follows this section; its own file adds only what is specific to
its role. The orchestrator follows it too, where it applies.

**What needs no approval.** These are routine, and an agent does them without asking or holding
back: read any file in the repo; run read-only commands and git queries; run the repo's own tests,
tooling and step tools (`tooling/`, the facts run, the snapshot diff, the claim tool, the diagram
check); retry a command or tool that failed or timed out, after finding why, when running it again
is safe; write the files its role owns. A limit in the agent's own file names any exception.

**What goes back to the orchestrator.** Subagents cannot ask the user anything, so an agent that
needs the user or another agent stops and puts a heading at the top of its final message:

- **QUESTIONS FOR THE USER**: a decision only the user can make (a gap that changes the design,
  behaviour the user would notice, a conflict between the brief and the code), or a check that
  needs something outside the repo. Each question with its options, what each does, and the one
  recommended.
- **ADVICE NEEDED**: a fact about how a library, browser, operating system or device really
  behaves that a few minutes of reading and a small check do not settle. The question in one
  sentence, why it matters, and what was tried with its result. The orchestrator runs the advisor
  and resumes the agent with the answer; nobody builds on a guess.
- **ARCHITECTURE UPDATE NEEDED**: a change to the structure the architecture doc describes (§ The
  architecture doc): what changes and why. Only the architect edits that doc.

**Outside the repo.** The CLAUDE-COMMON invariant *Agents change nothing outside the repo* holds:
an agent changes only the repo's working tree, plus `scratch/` and the session scratchpad for its
own scripts. What the repo's own tooling does when run is allowed (installing the browser tests'
browsers, starting their containers, the release tests' worktree). Anything else a check would
need (pulling an image, installing a tool, a setting, another repo) is neither done nor skipped
silently: it goes back as a question for the user, with what it would do and why the step needs
it.

**Scratch names carry the step.** Every file or folder an agent puts in `scratch/` starts with the
step id or holds it as a word (`s061_fix_docs.py`, `s061cr2-e2e.log`, `brief-facts-S061.md`), never
a bare `hand.py` or `fix.py`. When the step is finished, `tooling/step-clean.bat` deletes the
entries that carry its id, plus its snapshot and round refs; an entry without one stays behind for
good. Scripts that a later step will need again belong in the repo, not in `scratch/`.

**Commits.** No agent commits, pushes, builds images, deploys or releases: the user does, or asks
the orchestrator for it in so many words. The snapshot tool's refs (`refs/steps/`) are not commits
of a branch and are the orchestrator's.

**Own test run name.** Every backend or full test run sets the repo's test run name variable
(settings: *Unit tests*) to a short name of letters and digits: the one the orchestrator gives, or
else the step, the role and the round (`s061cr2`). Each name gets its own test databases, so
agents running tests at the same time never share one. The reserved names (settings: *Unit
tests*) are never used.

**Shell.** Read § Shell on Windows before the first Bash call: it holds the rules for scripts,
`.bat` wrappers, chained commands and line endings.

**The user's own edits.** The IDE may re-pad tables, re-wrap lines or switch line endings (§ IDE
reformatting). Keep those changes, never report them, read diffs with
`git diff -w --ignore-cr-at-eol`, and re-read a file before editing it.

**Writing style** (CLAUDE-COMMON § Writing style). Scope A for every step file and every message:
the point first, one term for one thing, questions with their options and the recommended one.
Scope B for the text users see in the app: labels, buttons, messages, confirmations. Developer
text (logs, code comments, exceptions a user never sees) stays technical and exact. Quoted text,
such as the user's own words, is exempt. A reviewer raises text that breaks scope A or B as a
finding: `nit`, or `minor` when the wording can mislead the coder or the user.

**Feedback.** Each file an agent writes ends with `## Feedback`: what in the workflow, the tools
or the rules cost time or got in the way during this run, so the workflow can be improved. Not
the step's findings, and no praise. At most 5 items, one bullet each (a long one may wrap onto
indented lines): `- <label>: <what happened> (<evidence>)`, the label one of `waste` (time or
tokens spent for nothing), `hindrance` (a tool failed or was slow, a command was hard to get
right, something was hard to find), `rule` (a rule unclear, contradicting another, or no longer
fitting) or `idea` (a concrete improvement); the evidence names the file, the command or the
minutes lost. Nothing to report: `- none`. A fix round, a later round or an amendment adds its own
`## Feedback` under its own section heading; the brief instead keeps one section at its end, which
each of the brief writer's runs appends to. Themes the user has dropped (the newest section of
`feedback-log.md`, as the spawn prompt names them) are not reported again.

## IDE reformatting

The user reads the step files in PyCharm, which can re-pad Markdown tables,
re-wrap lines or switch line endings (`core.autocrlf` is on) without any change
of content. That is expected and never needs the user's attention:

- **Keep it.** Never revert it, and never report it as a finding or a change.
- **See the real changes** with `git diff -w --ignore-cr-at-eol` (or
  `--word-diff`); a whitespace-only diff is empty there.
- **Edit the file as it is now.** Re-read it before an edit and match the
  current text: the Edit tool, not a script holding an older copy or assuming
  LF line endings and the old table padding.

## Shell on Windows

Every agent reads this before its first Bash call: these are the ways runs got lost to quoting, to a
`cd` that stayed, and to a chain that stopped on an empty `grep`. The Bash tool is Git Bash on
Windows; on Linux or macOS, rules 1, 4, 6 and 7 still apply.

1. **Text and scripts go to a file first.** Change a file with the Edit or Write tool. For a script
   (a one-off fix over several files, a check), write it with the Write tool to the session
   scratchpad or `scratch/`, then run `uv run --no-project python <file>`. Never put the script or
   multi-line text inline: no heredoc, no `echo`, no `python -c` with quotes in it.
2. **A `.bat` wrapper runs from the repo root**, quoted, with backslashes:
   `cd "<repo root>" && cmd //c "tooling\run-tests.bat …"` in one command. The Bash tool keeps the
   last `cd`, so a relative path fails after a `cd frontend`.
3. **A step tool runs directly**: `uv run --no-project python tooling/steps/<tool>.py …`, not through
   its `.bat` (`cmd //c` garbles a quoted argument on its way in).
4. **Chain read-only commands with `;`, not `&&`.** `grep` exits 1 when it finds nothing, and `&&`
   then stops the rest.
5. **`MSYS_NO_PATHCONV=1`** before a command whose argument has a `/` that is not a path
   (`git show refs/steps/S0NN:<file>`); Git Bash turns it into a Windows path otherwise.
6. **Read the summary line** of a test run before you call it green: it must name the tests that
   ran. A run that ran nothing failed.
7. **Line endings**: write a file with the Write or Edit
   tool, or in Python with `open(path, "w", newline="")` or `Path.write_bytes`. Never a plain
   text-mode write (`open(path, "w")`, `Path.write_text`): on Windows it turns every LF into CRLF.
   Check a file's line endings by its bytes (`b"\r\n" in Path(path).read_bytes()`), not with
   `grep -c $'\r'`: Git Bash counts every line there.
8. **Leave the git index alone** (01-11-2026, from the agents' feedback on S087 and S088): delete a
   file with plain `rm`, never `git rm`, and never `git add`. `git rm` stages the deletion, and the
   index is the user's, as the commit is.
9. **No `|` in a `-g` pattern under `cmd //c`** (02-11-2026, from the agents' feedback): `cmd`
   reads the `|` as a pipe and splits the command. Use a single word, or two runs.
10. **`cmd //c "x.bat" | tail` hides the wrapper's exit code**: the pipe returns `tail`'s. Read the
    PASSED or FAILED line, or redirect the output to a file and then read the file.
11. **`PYTHONUTF8=1`** before a Python command whose output goes to a file: Python writes cp1252
    there otherwise, and a `→` stops it.
12. **The same edit in many files**: `uv run --no-project python tooling/steps/edit_text.py <file>
    --old-file old.txt --new-file new.txt [--count N]`, the texts written first with the Write tool.
    It replaces the exact text N times (default 1) or refuses, and keeps the file's line endings.
13. **Never start `python -`, `uv run python -` or `cat` without input**: they wait on stdin until
    the Bash tool's 2-minute limit (S071, S087, S097). Write the script to a file and run the file.

## Orchestrated mode (one terminal)

The `/step` skill (`.claude/skills/step/SKILL.md`) runs the whole cycle from one
terminal, with each role as a subagent (`.claude/agents/`):

| Role | Subagent | Model |
|---|---|---|
| Brief writer | `brief-writer` | Opus by default; Fable or Sonnet chosen per brief (criteria in the skill) |
| Brief reviewer | `brief-reviewer` | Fable; Opus when the brief writer ran on Fable |
| Coder | `coder` | Sonnet by default; Opus chosen per step when complex (criteria in the skill) |
| Code reviewer | `code-reviewer` | Opus |
| Architect | `architect` | Fable; Opus for a small update |

- **Commands:**
  - `/step plan <topic>`
  - `/step amend S00N <request>`
  - `/step implement S00N`
  - `/step review S00N`
  - `/step status`
- **The loops stop only at the user's gates:**
  - brief approval;
  - design questions;
  - the final check and commit.
- **Each review loop is capped at 3 rounds,** then the orchestrator asks the
  user.
- **The stale brief check** (above) runs before each `/step implement`.
- **One session per step** (27-10-2026): the orchestrator takes a claim on a
  step before it writes the step's files (`tooling/step-claim.bat`, files in
  the main working folder's `scratch/step-claims/`), and a second session is
  refused while the claim is live. A claim dies when its session's process
  ends, after 30 minutes with no command and no agent, or 15 minutes after a
  running agent's budget. A background `watch` wakes the orchestrator when
  an agent passes its budget; it never stops the agent. The skill's
  `reference/claims.md` has the commands and the budgets. `scratch/`
  must be ignored by git, as it is for the browser-test lock.
- **Snapshot rounds** (27-10-2026): every coder hand-back is snapshotted, and
  each snapshot keeps a round ref (`refs/step-rounds/S00N-<n>`), so a verify
  review reads only the fix round: `tooling/step-snapshot.bat diff S00N
  --from-round <n>`.
- **The step's diff leaves out the workflow files** (30-10-2026): `diff` does
  not show the step folders, `docs/steps/INDEX.md`, `docs/steps/feedback-log.md`
  or `docs/roadmap/`, and its last line counts what it left out. The
  device-check list stays in. `--all` shows everything; paths after `--` win.
- **A diff from any commit** (31-10-2026): `diff [S00N] --base <commit>`
  compares the working tree with that commit, the same way and with the
  same exclusions: for a step with no snapshot yet whose base is not `HEAD`,
  or to override the step's base.
- **Is the tree still the snapshot?** (02-11-2026): `diff S00N --worktree
  [--from-round <n>]` compares the working tree, untracked files too, with the
  snapshot or round itself; it prints `working tree equals <ref>` (exit 0) or
  the diff (exit 1). Never `git diff refs/steps/…`: it shows new files as deleted.
- **The files and conventions above are unchanged.** The separate terminals
  below still work.

## Prompts per terminal (manual mode)

- Orchestrator: `Plan S00N <topic> in docs/steps`
- Brief reviewer: `Review docs/steps/S00N-<slug>/1-brief.md, write 2-brief-review-rN.md`
- Coder: `Implement S00N per the approved brief, write 3-impl-report.md`
- Code reviewer: `Review the S00N implementation (git diff) against 1-brief.md, write 4-code-review-rN.md`

## The architecture doc

The repo's architecture doc (settings: *Architecture*; usually `docs/Architecture.md`) holds the
agreed and evolving architecture: how the code is built now, and how the approved steps change it.
It is the repo's own file, committed with the steps that change it; it never syncs. Only the
**architect** (`.claude/agents/architect.md`) edits it; everyone else reads it.

**Sections**, in this order:
1. *Status* line (`Draft, DD-MM-YYYY` or `Agreed, DD-MM-YYYY`), and a short reading guide.
2. *Context*: the app's users, its services and the outside systems (a context diagram).
3. *Module map*: the backend modules and frontend areas, what each owns, and which way the
   dependencies go (a module diagram); where the pure core ends and the shell begins.
4. *Data areas*: which module owns which group of tables and how the groups link (a small
   diagram); the column-level ER diagram is the repo's generated schema page where it has one.
5. *Cross-cutting patterns*: permissions, transactions and locks, files, background work, alerts,
   migrations, the database being down — each as the repo does it, pointing to the
   `SMTW-WebApp-Base.md` section it follows, with a flow diagram where one helps.
6. *Departures from the base*: each deliberate departure and its reason.
7. *Decision log*: one row per structural decision — date, decision, reason, step, status
   (`proposed`, `agreed` — the user agreed it and the code does not follow it everywhere yet,
   `built`, `withdrawn`, `superseded by <row>`); rows are never deleted.
8. *Known drift*: where the code departs from this doc or from CLAUDE-COMMON's principles, with
   the candidate step that would fix it.

**Diagrams** are Mermaid blocks in the doc: text in the diff, a picture on GitHub, in the IDE and
on the artifact page. One idea per diagram, about 12 boxes at most. `tooling/check-diagrams.bat
<doc>` (any OS: `node tooling/architecture/check_diagrams.mjs <doc>`) renders each block in the browser tests' Chromium (exit 0 all rendered, 1 a diagram
failed, 2 not completed).

**When it changes.** A step whose design changes the structure — a new module, table group,
boundary, dependency direction or cross-cutting pattern, or a change to one — runs the architect
twice: at the brief, it records the change marked `(proposed, S0NN)`, which the user approves with
the brief at gate A; at gate B, it makes the doc match the code as built. A dropped step's
proposed changes are withdrawn. Any agent that finds such a change (the brief writer, a reviewer,
the coder) hands back **ARCHITECTURE UPDATE NEEDED** with what changes and why; the orchestrator
runs the architect. `/step architecture review` compares the whole codebase with the doc
(`docs/architecture/review-DD-MM-YYYY.md`).

**Who checks it.** The brief writer reads the doc and states every departure from it in the
brief's design decisions. The brief reviewer and the code reviewer raise an unstated departure
from the doc as a `major` finding. The coder never edits it.

## The repo's settings and index

Two things in a repo are its own; everything above is the same in every repo
(S056).

**The settings.** The repo's `.claude/CLAUDE.md` has a section
`## Step workflow`: first a few lines on the repo's step tools, then one bullet
per entry, `- **<Entry>**: <value>`, the form of `## Pre-flight`. An entry is one
line (a bullet the IDE wraps loses the rest of its value). The skill and
the agents point at an entry as "(settings: *Entry*)". A repo without the
section: the orchestrator stops with "This repo has no Step workflow section in
its CLAUDE.md. Add one; docs/steps/README.md lists the entries (see
`## Pre-flight` for the form)."

Six entries are read by the step tools (S057), so each is a list of backticked
words, and its text outside the backticks is for the reader: a value holds no
other backtick. A missing entry, or `none`, takes the default in the last
column. The tools that read them (`step_facts.read_step_settings`) stop with
the message above when the section is missing: `brief_facts.py` and
`step_stats.py`. The other step tools read no setting.

| Entry | Holds | When it is `none` |
|---|---|---|
| *Unit tests* | the command for all suites, the per-suite commands, the build check, the test run name variable and its reserved names | — (every repo has unit tests) |
| *Browser tests* | the browser-test tool and its rules; the targeted run, a new test alone, the quick whole-app run, the whole-suite run, the release level; the device projects and the logic device; the layout tag and its rule; the test conventions; the spec-to-step map; the lock | no browser runs and no `[auto]` checks: every manual check is a device check |
| *Plan and domain docs* | the repo's product plan (where gate A and gate R record lasting decisions), the domain docs, the schema doc | the generic text only |
| *Standards* | the repo's standards rule (a pointer), the standards to name, and why they are explained | no standards section in the brief; the reviews do not ask for one |
| *Self-check, repo items* | the repo's part of the brief writer's self-check (`.claude/agents/brief-writer.md`), by item number; the repo's permission tables and security-sensitive code for the fix-lane criteria | the generic text only |
| *Shared code* | the shared frontend files (a change runs the whole browser suite again), the migrations module and schema docs, the shared test fixtures | the generic text only |
| *Device checks* | the device-check list, the named person, the kinds of check a browser cannot judge, the machines (where), an example Done status | device checks go to the user |
| *Roadmap mock-ups* | the app's look (the style sheets to link, the views to copy from) and the sample data | the generic text only |
| *Architecture* | the architecture doc's path, then the repo's generated schema page the doc links to instead of drawing tables | no architecture doc: the architect is not run and nobody checks against one |
| *Use on the floor* | the docs to judge screens against, the repo's missing-record states, the users' language | the generic text only |
| *Code folders* | the folders the repo's code lives in, backticked: where `brief_facts.py` searches (`git grep`), then looks up a module `x.py` (and `tooling/steps`) and a test id's file (at the root, then `<folder>/<file>` and `<folder>/tests/<file>`) | the whole repo except `docs/`; modules in `tooling/steps` only; test files at the root only |
| *Browser-test wrapper* | the file name of the command that starts a browser-test run, e.g. `run-e2e-tests.bat` | no browser runs counted; `/step stats` has no E2E columns (the other four `Browser-test` entries are then ignored) |
| *Browser-test levels* | the level names counted, in the order of the report's columns; the header letters are their first letters (`b/n/t/f`); `targeted` is the reserved name of a run that names a spec file; a run with `--level=<name>` counts as that name; two levels may not share a first letter (the tool stops, exit 2) | as for the wrapper |
| *Browser-test spec files* | the ending of a spec file name, e.g. `.spec.js`: a run naming such a file is `targeted`, at any level, when `targeted` is one of the levels; otherwise it counts at its `--level` or the default level | no run is `targeted` |
| *Browser-test default level* | the level of a run with no flag and no spec file, then pairs `<level>` `<time>` (a date and time such as `2026-10-25T05:50Z`): such a run that started before the time has that level (the repo's history, when the wrapper's default changed) | the first level other than `targeted` |
| *Browser-test total line* | a regular expression with one group, the seconds a run printed (e.g. `All lanes done in (\d+) s`); Playwright's own "N passed (1.2m)" line, for 40 tests or more, is built in | only Playwright's line |

**The index.** The repo's steps are listed in `INDEX.md`, beside this file; it
never syncs. The step tools (`tooling/steps/step_facts.py`) read it by shape,
so keep it; without it they stop with "This repo has no docs/steps/INDEX.md.
docs/steps/README.md § The repo's settings and index gives its shape." (exit 2):
- two tables, under `## Index` and, after it, `## Queued (not yet briefed)`;
- an index row is `| S0NN | [<title>](S0NN-<slug>/1-brief.md) — <summary> | <phase> | <status> | <date> |`:
  the title cell links the step's brief, and the status is the fourth cell;
- a queued row starts with its step ID (`| S0NN …`) when it has one, else with
  the idea's text;
- a step ID is used once.

`docs/roadmap/INDEX.md` lists the roadmaps the same way; no tool parses it.

`docs/steps/device-checks.md` is optional: `/step check` skips its check 7 when the
file does not exist (a repo whose *Device checks* entry is `none`).
