# Steps — briefs, reviews and reports

Each piece of work on Yantra is a **step**. A step is planned, reviewed,
implemented and reviewed again across separate Claude Code terminals:

| Role | Model | Writes |
|---|---|---|
| Planner | Opus | `1-brief.md` |
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
| `1-brief.md` | Planner | The implementation brief: what, where, design decisions, open questions (CLAUDE-COMMON "Show the plan before building"), plus standards, tests and acceptance. Revised in place; its **Review log** answers each finding. |
| `2-brief-review-r1.md`, `-r2.md`, … | Brief reviewer | One file per review round |
| `3-impl-report.md` | Coder | The mandatory post-implementation report (CLAUDE-COMMON "Report after implementation"). Its **Fix rounds** section answers each code-review finding. |
| `4-code-review-r1.md`, `-r2.md`, … | Code reviewer | One file per review round, reviewing the working-tree diff against the brief |

## Header block

Every file starts with:

```
Step: S001 — Basic masters
Doc: brief | brief-review r1 | impl-report | code-review r1
Author: <role> (<model>)
Date: DD-MM-YYYY
Status: Draft | In review | Approved DD-MM-YYYY by <user> | Implementing | In code review | Done | Dropped
```

`Status` appears in the brief only. The brief's status is the step's status.

## Findings

- Brief-review findings are `BR<round>-<nn>` (e.g. `BR1-03`), and code-review
  findings are `CR<round>-<nn>` (e.g. `CR2-01`).
- Each finding has a severity: `blocker`, `major`, `minor` or `nit`.
- The author answers every finding with one of these:
  - `Accepted`, with what changed;
  - `Rejected`, with why;
  - `Deferred`, with the step it goes to.

  The planner answers in the brief's Review log, and the coder in the impl report's Fix rounds.

## Gates

1. **Brief review.** The brief goes from `Draft` to `In review`. Review rounds
   repeat until no `blocker` or `major` finding is open.
2. **Approval.** Only the user sets `Approved`, after reading the brief as it
   stands after the last review round. The planner shows its decision-relevant
   sections verbatim (what, out of scope, standards, design decisions, open
   questions) and lists the others by heading, rather than a summary. The coder
   never starts on an unapproved brief. Anything the brief doesn't cover is raised with the user,
   not decided in code.
3. **Code review.** Status `In code review`. Rounds repeat until no `blocker`
   or `major` finding is open.
4. **Done.** The user commits; no terminal commits. The status becomes `Done`.

Whoever changes a step's status also updates its row in the index below.

## Amendments

A change requested after a brief is approved, while the step is not yet `Done`,
becomes an **amendment** rather than a new step:

1. **Write it.** The planner adds the amendment under the brief's **§ 10
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
- **The files and conventions above are unchanged.** The separate terminals
  below still work.

## Prompts per terminal (manual mode)

- Planner: `Plan S00N <topic> in docs/steps`
- Brief reviewer: `Review docs/steps/S00N-<slug>/1-brief.md, write 2-brief-review-rN.md`
- Coder: `Implement S00N per the approved brief, write 3-impl-report.md`
- Code reviewer: `Review the S00N implementation (git diff) against 1-brief.md, write 4-code-review-rN.md`

## Index

| ID | Title | Plan.MD phase | Status | Date |
|---|---|---|---|---|
| S001 | [Basic masters](S001-basic-masters/1-brief.md) — sites, units, equipment classes, unit access | 2 | Done — committed 817844c | 14-10-2026 |
| S002 | [Equipment register](S002-equipment-register/1-brief.md) — equipment tree (backend/API), codes, status, criticality, events, unit access enforced | 2 | Done — committed 6d58ce5 | 15-10-2026 |
| S003 | [Equipment register screens](S003-equipment-screens/1-brief.md) — list, equipment page, create/edit, move, status dialogs | 2 | Done — committed 6d58ce5 | 15-10-2026 |
| S004 | [Equipment types and notes](S004-equipment-types-notes/1-brief.md) — types per class, notes, search in notes | 2 | Done — committed 226ce67 | 15-10-2026 |
| S005 | [Tidy-up](S005-tidy-up/1-brief.md) — page not found, leftover review nits | 2 | Done — committed 0a91b8b | 15-10-2026 |
| S006 | [Documents and photos](S006-equipment-documents/1-brief.md) — files on equipment, thumbnails, upload/remove | 2 | Done — committed 76d7282 | 16-10-2026 |
| S007 | [Dialog close guard; Nginx and deploy fixes](S007-dialog-guard-deploy-fixes/1-brief.md) — no lost input in dialogs; backend re-resolved; recreate on a secrets change | 2 | Done — committed 11789d7 + 7b504f4 | 16-10-2026 |
| S008 | [Removed documents](S008-removed-documents/1-brief.md) — list removed files on Settings, restore, delete for good | 2 | Done — committed 799851c | 16-10-2026 |
| S009 | [Documents on classes and types](S009-class-type-documents/1-brief.md) — one manual for every `RPP` pump, shown on each node | 2 | In code review (approved 16-10-2026) | 16-10-2026 |
| S010 | [Technicians and trades](S010-technicians/1-brief.md) — maintenance people, in-house or contract firm, trades, optional login | 2 | Approved 16-10-2026 (coding after S009 is committed) | 16-10-2026 |
| S011 | [Roles per site, held in Yantra](S011-site-roles/1-brief.md) — memberships: role per site + units; Keycloak keeps maintenance_team and it_admin | 2 | Approved 16-10-2026 (coding after S010 is committed) | 16-10-2026 |

## Queued (not yet briefed)

Ideas agreed as worth doing, in no fixed order. A queued item gets its step ID
when its brief is opened, or earlier when the user assigns one (S007–S009, 16-10-2026).

| Idea | From | Note |
|---|---|---|
| QR labels | Plan.MD phase 2 | Called "S007" in S006's brief, before S007–S009 were assigned |
| Malware scanning of uploads (ISO 27001 A.8.7) | user, 16-10-2026 | S006 § 10.3; ClamAV in its own container is the candidate |
| Equipment models: a model master (manufacturer + model designation), equipment picks its model in place of free-text make/model, documents on the model; class and model documents on the removed-documents screen | user, 16-10-2026 | S009 A2; replaces the dropped S009 A1 |
