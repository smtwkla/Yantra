# Steps — briefs, reviews and reports

Each piece of work on the repo is a **step**. A step is planned, reviewed,
implemented and reviewed again across separate Claude Code terminals:

| Role | Model | Writes |
|---|---|---|
| Roadmapper | Opus | `docs/roadmap/R0N-<feature>.md`: a big feature cut into items `R0N.n`, the seed of steps (gate R; `docs/roadmap/README.md`) |
| Advisor | Fable | `0-advice-<topic>.md` (on request) |
| Orchestrator | Opus | `1-brief.md` |
| Brief reviewer | Fable | `2-brief-review-rN.md` |
| Coder | Opus or Sonnet | the code + `3-impl-report.md` |
| Code reviewer | Opus | `4-code-review-rN.md` |

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
| `1-brief.md` | Orchestrator | The implementation brief: what, where, design decisions, open questions (CLAUDE-COMMON "Show the plan before building"), plus standards, tests and acceptance. Revised in place; its **Review log** answers each finding. |
| `2-brief-review-r1.md`, `-r2.md`, … | Brief reviewer | One file per review round |
| `2-brief-review-s1.md`, `-s2.md`, … | Brief reviewer | A staleness review: does the approved brief still hold for code changed since its baseline (§ Stale brief check) |
| `3-impl-report.md` | Coder | The mandatory post-implementation report (CLAUDE-COMMON "Report after implementation"). Its **Docs updated** section lists every doc the step changed (the docs pass, standing rule 24-10-2026; which docs: `.claude/CLAUDE.md` § Docs to keep current), or says why none; its **Fix rounds** section answers each code-review finding. |
| `4-code-review-r1.md`, `-r2.md`, … | Code reviewer | One file per review round, reviewing the working-tree diff against the brief |

**Feedback** (25-10-2026, by KLA). Every file an agent writes — advice, brief review, impl report,
code review — ends with `## Feedback`: at most 5 one-line items labelled `waste`, `hindrance`,
`rule` or `idea`, each with its evidence, or `- none` (the agents' instructions give the form).
`/step feedback` collects them across steps (`tooling/step-feedback.bat`).

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

**Facts run.** Before brief review round 1, the orchestrator runs
`tooling/step-brief-facts.bat S0NN`: where each file, test, route and code name
the brief cites exists, and which tests use it. The orchestrator fixes the brief
from it; the brief reviewer gets the output (23-10-2026, S029).

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

  The orchestrator answers in the brief's Review log, and the coder in the impl report's Fix rounds.

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

1. **Write it.** The orchestrator adds the amendment under the brief's **§ 10
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
   - after the check, `Baseline:` is set to the code just checked.
3. **Skipped** only when the user says so; the orchestrator records it in the brief.

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

## Orchestrated mode (one terminal)

The `/step` skill (`.claude/skills/step/SKILL.md`) runs the whole cycle from one
terminal, with each role as a subagent (`.claude/agents/`):

| Role | Subagent | Model |
|---|---|---|
| Brief reviewer | `brief-reviewer` | Fable |
| Coder | `coder` | Sonnet by default; Opus chosen per step when complex (criteria in the skill) |
| Code reviewer | `code-reviewer` | Opus |

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
- **The files and conventions above are unchanged.** The separate terminals
  below still work.

## Prompts per terminal (manual mode)

- Orchestrator: `Plan S00N <topic> in docs/steps`
- Brief reviewer: `Review docs/steps/S00N-<slug>/1-brief.md, write 2-brief-review-rN.md`
- Coder: `Implement S00N per the approved brief, write 3-impl-report.md`
- Code reviewer: `Review the S00N implementation (git diff) against 1-brief.md, write 4-code-review-rN.md`

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
| *Self-check, repo items* | the repo's part of the skill's self-check, by item number; the repo's permission tables and security-sensitive code for the fix-lane criteria | the generic text only |
| *Shared code* | the shared frontend files (a change runs the whole browser suite again), the migrations module and schema docs, the shared test fixtures | the generic text only |
| *Device checks* | the device-check list, the named person, the kinds of check a browser cannot judge, the machines (where), an example Done status | device checks go to the user |
| *Roadmap mock-ups* | the app's look (the style sheets to link, the views to copy from) and the sample data | the generic text only |
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
