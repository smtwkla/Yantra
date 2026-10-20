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
| `2-brief-review-s1.md`, `-s2.md`, … | Brief reviewer | A staleness review: does the approved brief still hold for code changed since its baseline (§ Stale brief check) |
| `3-impl-report.md` | Coder | The mandatory post-implementation report (CLAUDE-COMMON "Report after implementation"). Its **Fix rounds** section answers each code-review finding. |
| `4-code-review-r1.md`, `-r2.md`, … | Code reviewer | One file per review round, reviewing the working-tree diff against the brief |

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

The planner proposes the track; the user confirms or overrides it.

| | Full | Light |
|---|---|---|
| Brief | All sections | The short template below |
| Brief review | Up to 3 rounds | 1 round; answers not re-reviewed unless a `blocker`/`major` is open |
| Gate A | Decision sections verbatim | A bullet summary + the brief's path (verbatim on request) |
| Coder | Sonnet or Opus | Sonnet |
| Code review | Up to 3 rounds | Up to 3 rounds (unchanged) |

**Switch to full** when the brief reviewer raises a `blocker` or `major`
finding, or the step turns out to meet a full-track criterion. The header and
the index row are updated, and the user is told.

**The light brief** (about a page):
1. What will be built, and out of scope;
2. Standards and practice: one or two lines;
3. Where: files and what changes in each;
4. Design decisions: only the real choices, with the rejected alternative;
5. Tests and acceptance, with the important manual checks marked;
6. Open questions and assumptions;
7. Amendments; Review log.

## Manual checks

Some checks only a person can do: a real phone, a production step, how a screen
feels. The ones that matter are marked **important** in the brief's tests
section; the rest stay plain notes.

- **The coder** copies them into the impl report's `## Manual checks`: each
  important one as a box, `- [ ] …`; the rest as a plain list.
- **At gate B** the planner shows the important ones as that checklist.
- **The user** ticks each one or skips it with a reason. The planner records
  it in the report (`[x]`, or `[skipped] <reason>`), never ticking a box on the
  user's behalf.
- **Done** needs every important check ticked or explicitly skipped; the status
  records it, e.g. `Done (committed abc123; checks: 3 done, 1 skipped — iPhone)`.

## Findings

- Brief-review findings are `BR<round>-<nn>` (e.g. `BR1-03`), staleness-review
  findings `BS<round>-<nn>` (e.g. `BS1-02`), and code-review findings
  `CR<round>-<nn>` (e.g. `CR2-01`).
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
   stands after the last review round. On the full track the planner shows its
   decision-relevant sections verbatim (what, out of scope, standards, design
   decisions, open questions) and lists the others by heading, rather than a
   summary; on the light track, a bullet summary and the path (§ Tracks). The coder
   never starts on an unapproved brief, nor on a stale one (§ Stale brief check). Anything the brief doesn't cover is raised with the user,
   not decided in code.
3. **Code review.** Status `In code review`. Rounds repeat until no `blocker`
   or `major` finding is open.
4. **Done.** The user commits; no terminal commits. The status becomes `Done`
   once the commit is confirmed and every important manual check is ticked or
   explicitly skipped by the user (§ Manual checks).

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

## Stale brief check

A brief is checked against the code as it stood when it was reviewed. Other
steps can change that code before this one is coded, so the brief can go stale
between approval and coding. The check catches it before the coder starts.

1. **Record the baseline.** Every brief review names the code it read:
   `Reviewed against: <commit> [+ uncommitted S0NN, …]`. When the user approves,
   the planner copies the last one into the brief's header as `Baseline:`.
2. **Check before coding** (the step, or an approved amendment):
   - the planner compares the files named in the brief's *Where*, and the
     modules they call, between the baseline and the working tree now (commits
     since the baseline plus uncommitted changes);
   - **nothing changed:** the coder starts;
   - **something changed:** one **staleness review**, `2-brief-review-sN.md`.
     The brief reviewer gets that diff and answers one question: does each
     statement in the brief still hold? Findings are `BS<n>-<nn>`;
   - the planner answers them in the Review log as usual. A `blocker` or
     `major` finding changes what the user approved, so the brief goes back to
     the user (gate A) before coding. Minor findings and nits are fixed in the
     brief text and the coder starts;
   - after the check, `Baseline:` is set to the code just checked.
3. **Skipped** only when the user says so; the planner records it in the brief.

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
| S009 | [Documents on classes and types](S009-class-type-documents/1-brief.md) — one manual for every `RPP` pump, shown on each node | 2 | Dropped 16-10-2026 — documents belong on a model master (queued); code kept as `s009-code.patch` | 16-10-2026 |
| S010 | [Team and trades](S010-technicians/1-brief.md) — a register of people (direct or contractor, a person or a firm), trades, optional login set by IT admin | 2 | In code review — amendment A1 (Team; A1 approved 16-10-2026) | 16-10-2026 |
| S011 | [Roles per site, held in Yantra](S011-site-roles/1-brief.md) — memberships: role per site + units; Keycloak keeps maintenance_team and it_admin | 2 | In code review (A1 approved 16-10-2026; built on uncommitted S010, baseline tree 15227de) | 16-10-2026 |
| S012 | [Equipment models](S012-equipment-models/1-brief.md) — manufacturers and models masters; equipment picks its model (class and type from it); documents on the model | 2 | In code review (approved 17-10-2026; on top of c486a4a) | 16-10-2026 |
| S013 | [Network gate, access log, job queue](S013-network-gate-access-log/1-brief.md) — IT admin from the plant network only; access log; task_queue + daily scheduler | 1 | In code review (approved 18-10-2026; on top of 3e338b4; A1 approved 18-10-2026 — one row per sighting per day) | 18-10-2026 |
| S014 | [QR labels](S014-qr-labels/1-brief.md) — 52 mm labels on A4 paper, 15 per sheet; link `/e/<code>` opens the equipment page; link address in Settings | 2 | In code review (approved 18-10-2026; on top of uncommitted S013) | 18-10-2026 |
| S015 | [Printable asset list](S015-asset-list/1-brief.md) — per site / unit, one page per unit; parts optional; checklist columns and signature footer optional | 2 | Committed 6c771e1; manual checks pending (approved 20-10-2026; light track) | 18-10-2026 |
| S016 | [Failure codes](S016-failure-codes/1-brief.md) — failure modes (symptoms, per class or general), causes in ISO groups, maintenance actions; pre-filled from ISO 14224 Annex B | 3 | Committed 6c771e1; manual checks pending (approved 20-10-2026; full track) | 18-10-2026 |
| S017 | [Raise and see tickets](S017-raise-tickets/1-brief.md) — breakdown or defect by intensity, on any node; symptom optional; photos; open-tickets list; ticket page with timeline; serial `TK-` | 3 | In code review (approved 20-10-2026; full track; baseline 6c771e1) | 20-10-2026 |
| S018 | [Work the ticket](S018-work-tickets/1-brief.md) — acknowledge, start, back in service (production too), send back, close with cause/action, not a fault; labour, assignment, re-grade, repeat; response/repair/downtime | 3 | In review (full track; on S017) | 20-10-2026 |
| S022 | [Software inventory and vulnerability check](S022-dependency-inventory/1-brief.md) — CycloneDX SBOMs in `sbom/` from the lockfiles; OSV lookup for CVEs; stale direct dependencies | — | Committed 76fccf7; manual checks pending (approved 18-10-2026; full track) | 18-10-2026 |

## Queued (not yet briefed)

Ideas agreed as worth doing, in no fixed order. A queued item gets its step ID
when its brief is opened, or earlier when the user assigns one (S007–S009, 16-10-2026).

| Idea | From | Note |
|---|---|---|
| **S019** Deferred work — scheduled state, planned date, waiting reason; planned vs breakdown downtime; waiting split on critical tickets | phase 3 plan, user 18-10-2026 | Plan.MD Q13; meter-value targets wait for phase 4 |
| **S020** Work done without a ticket (raise-and-close) and parts used | phase 3 plan, user 18-10-2026 | Plan.MD Q23, Q21 |
| **S021** Alerts — PWA shell, web push, Telegram via the job queue; new breakdown and escalation; escalation times as settings; not-closed-by-end-of-shift list | phase 3 plan, user 18-10-2026 | Plan.MD Q2, Q12; decide whether defects notify. Then phase 4 (PM engine) |
| Image SBOM at build — an SBOM of each built image (base image, OS packages, venv), stored with the image in GHCR. Candidate: Docker's built-in `docker build --sbom=true` (SPDX; needs the containerd image store), no third-party scanner; `BUILDKIT_SBOM_SCAN_STAGE` to see the frontend's bundled libraries | S022 U1, user 18-10-2026 (keep both repo and image checks) | Each repo's build script changes; any shared part in `smtw-common` |
| aibots scanner bot — reads every app's `sbom/` (CycloneDX) and the SBOM of the **deployed** image version (SPDX; not `latest`), looks them up in OSV, reports, with LLM advice on updates and migrations | S022 U1, user 18-10-2026 | In the aibots repo; needs S022's SBOM files. Separately, aibots's containers install from unpinned `requirements.txt`, so its lockfile isn't what runs |
| Calibration — measuring-instrument class (range, required accuracy, calibration class, owning department, custodian); certification plan per instrument; in-house verification plans with error readings and the out-of-tolerance ticket; QR label as the calibration sticker | user, 20-10-2026 (ISO 9001 a future goal) | Plan.MD Q24, § 4.3; phase 4, after certification plans (Q20); ISO 9001 § 7.1.5 |
| Malware scanning of uploads (ISO 27001 A.8.7) | user, 16-10-2026 | S006 § 10.3; ClamAV in its own container is the candidate |
| Procedure master — written know-how: work instructions, diagnostic procedures per symptom, one-point lessons, onboarding cards (Tamil content); Markdown body with photos, optional numbered steps as checklist / reading items, optional class; shown on the equipment page (via class), on PM templates and attached to tickets; who changed it and when | Plan.MD § 4.3a and Q15, Q19; user 20-10-2026 | Diagnostic steps reuse the PM item shape, so build after or with the phase 4 item machinery, or define the item shape here; completion records (onboarding, skill matrix) a follow-up |
| Supervisors and engineers create operators without a login at their own site — a new permission key on the pattern of `people:assign_technicians` (S017 lets only IT admin set an Operator row without a login) | Plan.MD § 3 (decided 16-10-2026, sorting-line use case); S017 BR2-08, 20-10-2026 | The key is settled in the brief that builds it |
| Shared unit-access helper — the "`accessible_unit_ids` → None / empty set / `IN (…)`" block is repeated in four list routes (equipment list, labels, asset list, removed documents); one helper | S015 CR1-03, user 20-10-2026 | Small tidy-up; S017's ticket list adds a fifth use, so do it with or after S017 |
| Drop the legacy `user_units` table | S011 A1, 16-10-2026 | After S011 is live and a rollback is no longer wanted (S011 A1 rule 3) |
