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
| `3-impl-report.md` | Coder | The mandatory post-implementation report (CLAUDE-COMMON "Report after implementation"). Its **Docs updated** section lists every doc the step changed (the docs pass, standing rule 24-10-2026; which docs: `.claude/CLAUDE.md` § Docs to keep current), or says why none; its **Fix rounds** section answers each code-review finding. |
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
the index row are updated, and the user is told. A finding that only says
"belongs on the full track" is `minor` (23-10-2026, S029): it switches the
track, and the user may keep light at approval.

**Facts run.** Before brief review round 1, the planner runs
`tooling/step-brief-facts.bat S0NN`: where each file, test, route and code name
the brief cites exists, and which tests use it. The planner fixes the brief
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
- it fixes behaviour that a brief, Plan.MD or the docs already describe, and
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
  Each becomes a browser test (Playwright, `frontend/e2e/`) that the coder
  writes with the step. A test asserts what the user would see — the badge, the
  timeline line, the times card, the message — not only that a page opened.
- **On a real device** — the few a browser engine cannot judge: a real camera
  or QR scan, paper from a printer and a ruler, the iPhone keyboard over a
  dialog, a real login through Keycloak, how a gloved thumb copes. Done by the
  user **or the named person, today IT Admin**.

The rules:

- **The coder** writes an e2e test for each automated check and runs
  `tooling/run-e2e-tests.bat`. Only a passing run may mark a check in the impl
  report's `## Manual checks` as
  `- [auto] <check> — <test file>::<test name>`. Real-device checks go there as
  boxes, `- [ ] …` (important) or a plain list, and the coder appends them as
  rows to [`device-checks.md`](device-checks.md).
- **The levels** (S047). `tooling/run-e2e-tests.bat` runs at one of three
  levels. **Basic** (`--level=basic`): the `@smoke` tests (four journeys and
  `screens.spec.js`) on the Android phone, about 2 minutes. **Normal** (no
  flag): every test on the Android phone, and the `@device` tests (layout
  checks, tests that differ by device) on desktop. **Full**
  (`--level=full`): every test on the Android phone, the iPhone and desktop.
- **The coder** runs the e2e tests whenever the frontend or an API the
  screens use changed, and reports the real result. It makes targeted runs
  (Normal with the spec files of the screens the step changed, plus
  `screens.spec.js`) as often as it needs, and may run Basic for a quick
  whole-app check. It runs the whole suite at Normal once, when the coding is
  done, and again only with a reason it states. In a fix round it makes
  targeted runs only.
- **The code reviewer** never runs the whole suite. It re-runs only the
  specs one of its own findings needs.
- **The Full level** runs only in the release (`tooling/release-tests.bat`
  runs it after the unit suites, on the same worktree of HEAD) and when KLA
  asks.
- **`device-checks.md`** is the master list of open real-device checks, one row
  per check in plain words: what to do and see, account, network, where (the
  dev server on KLA's laptop, production on the TEST machine, or either) and
  done. A done row stays as the record (who, when).
- **The round trip.** The user hands the named person the rows (printed or by
  chat); the person reports back to the user; the user tells the planner; the
  planner writes `- [x] <check> — by <name>, DD-MM-YYYY` into the step's impl
  report and fills the row's *Done* column. The person never edits the file.
- **At gate B** the planner shows the `[auto]` checks as passed tests and the
  real-device ones as the checklist. The user decides which checks are which,
  and can skip any.
- **Nobody ticks for someone else.** The planner records the user's or the
  named person's answer (`[x] … — by <name>, DD-MM-YYYY`, or `[skipped]
  <reason>`), never ticking a box on their behalf.
- **Done** needs every important check `[auto]`, ticked for the user or the
  named person, or skipped by the user; the status records it, e.g.
  `Done (committed abc123; checks: 6 auto, 2 done by IT Admin, 1 skipped — iPhone)`.

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
2. **Approval.** (None on the fix lane, § Tracks.) Only the user sets `Approved`, after reading the brief as it
   stands after the last review round. On the full track the planner shows its
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
   passing e2e run), ticked for the user or the named person (today IT Admin),
   or explicitly skipped by the user (§ Manual checks).

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
| S008 | [Removed documents](S008-removed-documents/1-brief.md) — list removed files on Settings, restore, delete for good | 2 | Done — committed 6351bac + c11a549 | 16-10-2026 |
| S009 | [Documents on classes and types](S009-class-type-documents/1-brief.md) — one manual for every `RPP` pump, shown on each node | 2 | Dropped 16-10-2026 — documents belong on a model master (queued); code kept as `s009-code.patch` | 16-10-2026 |
| S010 | [Team and trades](S010-technicians/1-brief.md) — a register of people (direct or contractor, a person or a firm), trades, optional login set by IT admin | 2 | Done — committed c486a4a; checks: 3 skipped (API tests) | 16-10-2026 |
| S011 | [Roles per site, held in Yantra](S011-site-roles/1-brief.md) — memberships: role per site + units; Keycloak keeps maintenance_team and it_admin | 2 | Done — committed c486a4a (with S010); checks: 3 skipped (API tests), 1 done by KLA | 16-10-2026 |
| S012 | [Equipment models](S012-equipment-models/1-brief.md) — manufacturers and models masters; equipment picks its model (class and type from it); documents on the model | 2 | Done — committed 3e338b4; checks: 3 skipped (API tests), 1 done by KLA | 16-10-2026 |
| S013 | [Network gate, access log, job queue](S013-network-gate-access-log/1-brief.md) — IT admin from the plant network only; access log; task_queue + daily scheduler | 1 | Committed ae0f183; 2 checks covered by API tests, 2 left (approved 18-10-2026; A1 approved 18-10-2026 — one row per sighting per day) | 18-10-2026 |
| S014 | [QR labels](S014-qr-labels/1-brief.md) — 52 mm labels on A4 paper, 15 per sheet; link `/e/<code>` opens the equipment page; link address in Settings | 2 | Committed dde0d68; device checks left for IT Admin (approved 18-10-2026) | 18-10-2026 |
| S015 | [Printable asset list](S015-asset-list/1-brief.md) — per site / unit, one page per unit; parts optional; checklist columns and signature footer optional | 2 | Committed 6c771e1; 1 auto, 2 print checks left for IT Admin (approved 20-10-2026; light track) | 18-10-2026 |
| S016 | [Failure codes](S016-failure-codes/1-brief.md) — failure modes (symptoms, per class or general), causes in ISO groups, maintenance actions; pre-filled from ISO 14224 Annex B | 3 | Done — committed 6c771e1; checks: 3 auto (full track) | 18-10-2026 |
| S017 | [Raise and see tickets](S017-raise-tickets/1-brief.md) — breakdown or defect by intensity, on any node; symptom optional; photos; open-tickets list; ticket page with timeline; serial `TK-` | 3 | Committed cfedc46; 2 auto, 1 camera check left for IT Admin (full track) | 20-10-2026 |
| S018 | [Work the ticket](S018-work-tickets/1-brief.md) — acknowledge, start, back in service (production too), send back, close with cause/action, not a fault; labour, assignment, re-grade, repeat; response/repair/downtime | 3 | Committed ae3841f; 5 auto, 1 keyboard check left for IT Admin (full track; A1 — Already fixed on the raise screen) | 20-10-2026 |
| S019 | [Deferred work](S019-deferred-work/1-brief.md) — scheduled state, planned date, waiting reason; planned vs breakdown downtime; waiting split on critical tickets | 3 | Committed b6b8dfb; row 10 (date picker) left for IT Admin | 21-10-2026 |
| S020 | [Parts used](S020-parts-used/1-brief.md) — a structured parts line on tickets (maker or generic part number, description, quantity), on the ticket's component | 3 | Done — committed b6b8dfb; checks: 7 auto; row 11 (plain) for IT Admin | 21-10-2026 |
| S021 | [Alerts: PWA and web push](S021-alerts-push/1-brief.md) — installable app, push per device; new breakdown → engineers, the unit's supervisor, maintenance manager; defects → engineers quietly; escalation times as settings | 3 | Committed 3470fb9 (and 4 earlier commits); checks: 12 auto; device rows 14–25 pending | 21-10-2026 |
| S022 | [Software inventory and vulnerability check](S022-dependency-inventory/1-brief.md) — CycloneDX SBOMs in `sbom/` from the lockfiles; OSV lookup for CVEs; stale direct dependencies | — | Done — committed 76fccf7; checks: 1 done by KLA, 1 covered by unit tests | 18-10-2026 |
| S023 | [Alerts: Telegram and end-of-shift list](S023-alerts-telegram/1-brief.md) — the existing bot to the maintenance group; tickets back in service but not closed by end of shift (split from S021, user 21-10-2026) | 3 | Parked 21-10-2026 by the user (PWA push alone for now; brief kept for later) | 21-10-2026 |
| S024 | [Browser tests (Playwright)](S024-browser-tests/1-brief.md) — every screen opens as each role, S014–S018 checks as browser tests on phone and desktop; automated vs real-device checks in the workflow; IT admin device checklist | — | Done — committed 3df667c; checks: 1 done by KLA, 1 accepted by KLA | 21-10-2026 |
| S025 | [Release safety and ticket integrity](S025-audit-fixes/1-brief.md) — audit 21-10-2026 [1]-[4], [6], [9], [10]: squashed schema v20 with a guard, schema-ready deploy check, build.bat checks, JSON errors; units frozen by tickets, no send-back after a repeat, locked component check, not a fault after Start | — | Done — committed b6b8dfb; checks: row 9 done by KLA, 23-10-2026 | 21-10-2026 |
| S026 | [A refusal is always in view](S026-refusal-in-view/1-brief.md) — a refused save scrolls the dialog to the first message and puts the cursor in the field; every dialog checked; e2e message checks need on-screen (bug: Add labour, Time spent below the fold) | — | Committed 03ed528; row 12 (iPhone keyboard) left for IT Admin | 22-10-2026 |
| S027 | [Work notes](S027-work-notes/1-brief.md) — *Add note* on an open ticket: what was found and tried, on the timeline (EN 13306 fault localisation and diagnosis); the raise's *What is wrong?* is the first note; engineers correct a note, the earlier text kept (v23) | 3 | Done — committed 03ed528; checks: 5 auto; row 13 (plain) for IT Admin | 22-10-2026 |
| S028 | [Back-dating window: admin and backlog entry](S028-backdating-window/1-brief.md) — entered ticket times up to 3 years back for admin (key `ticket:backdate`) and for everyone until 30-11-2026; 7 days otherwise | — | Done — committed 12a1238 (with S029); checks: 2 auto | 22-10-2026 |
| S029 | [Ticket light on the equipment list](S029-equipment-ticket-light/1-brief.md) — a red / amber / green bulb per row (breakdown open = down; other open ticket; none) and a filter for equipment with tickets | 3 | Done — committed 12a1238; checks: 3 auto (light track) | 23-10-2026 |
| S030 | [Equipment lifecycle](S030-equipment-lifecycle/1-brief.md) — the register field *Status* (in service / standby / out of use / scrapped) renamed *Lifecycle* in screens, API, code and DB (v25); *Status* reserved for down / working / degraded / PM due | 2 | Done — committed 6866fbd; checks: 1 auto (full track) | 23-10-2026 |
| S031 | [Me: my open work, tickets I raised, my activity](S031-me-page/1-brief.md) — a *Me* nav item with three tabs: open tickets assigned to me, tickets I raised or reported, timeline lines I recorded; v26 two indexes | 3 | Done — committed 33c3a4b; checks: 8 auto; row 26 (not important) open | 23-10-2026 |
| S032 | [Email to managers when a ticket is closed](S032-closed-ticket-email/1-brief.md) — email as a second alert channel (Mailgun over SMTP, addresses from Keycloak at login); *Ticket closed* to the site's managers; v27 `people.email` | 3 | Committed; device checks pending (rows 27-30 of device-checks.md) | 23-10-2026 |
| S033 | [Model optional on component-units](S033-model-optional-component-units/1-brief.md) — a component-unit may have no model; its class (required) and type (optional) are then picked directly; v28 `equipment.model_id` NULL with a level CHECK | 3 | Done — committed c9234ce; checks: 3 auto | 23-10-2026 |
| S034 | [Defer, hold and follow-up date](S034-defer-and-follow-up/1-brief.md) — *Schedule* reads *Defer* on a defect and *Put on hold* on a breakdown; the date reads *Check again by* when the wait is outside maintenance's control (parts, vendor, expert, approval), with +7 / +14 / +30 days | 3 | Done — committed 06e16e4 (merged aa81a69); checks: 5 auto | 24-10-2026 |
| S035 | [Me first in the nav](S035-me-first-in-nav/1-brief.md) — *Me* moves to the top of the sidebar and the bottom bar, and becomes the landing page for every role with tickets (fix lane) | 3 | Done — committed 3b3fb41; checks: 1 auto | 24-10-2026 |
| S036 | [Ticket tint by intensity](S036-ticket-tint/1-brief.md) — a mild background on ticket rows and the ticket page by intensity: Critical pink, Degraded yellow, Initial grey; closed tickets plain | 3 | Done — committed 15b06e0; checks: 1 auto; row 31 (not important) open | 24-10-2026 |
| S037 | [Meters master](S037-meters-master/1-brief.md) — meter types in Masters: name, unit, counter or gauge | 4 | Done — committed c2c802f (with S038); checks: 4 auto | 24-10-2026 |
| S038 | [Meters on models and equipment](S038-meters-on-models-equipment/1-brief.md) — a model lists its meters with default gauge limits; every equipment of the model has them, may override limits and add its own | 4 | Done — committed c2c802f (with S037); checks: 6 auto | 24-10-2026 |
| S039 | [Meter reading entry](S039-meter-reading-entry/1-brief.md) — readings per equipment (page, QR) with their history; counter and limit rules; v32 `meter_readings` | 4 | Committed 984761a; checks: 8 auto; row 32 (important) open | 24-10-2026 |
| S040 | [End-of-day readings sheet](S040-readings-sheet/1-brief.md) — every meter of a unit on one screen, saved row by row, for the press supervisors and the genset round; a *Readings* nav item; built on S039 | 4 | Committed c6e74a1, A1 b4af1d0; row 33 (important) open | 24-10-2026 |
| S041 | [S033's e2e test isolated from the seed extruder](S041-s033-e2e-isolation/1-brief.md) — the S033 test adds its part under its own equipment, not the shared seed extruder that the label checks count (fix lane, from S035 CR2-01) | 3 | Done — committed 7618839 | 24-10-2026 |
| S042 | [S034's quick-pick e2e test finds its row by serial](S042-s034-e2e-row-by-serial/1-brief.md) — the test counted rows by a shared description, so two projects on one database made it fail (fix lane, from S036 CR2; D13) | 3 | Done — committed d6b305b | 24-10-2026 |
| S043 | [Equipment properties: master, classes and models](S043-equipment-properties/1-brief.md) — technical data defined once in Masters (number with unit, choice, text, yes/no), linked to classes, valued on models; read-only card on the equipment page; ISO 14224 Annex A seed; v31. Ported from branch `claude/component-unit-hierarchy-tfa3gg` (there S035, v26) | 2 | Done — committed f8998ab; checks: 15 auto | 24-10-2026 |
| S044 | [Property overrides on equipment items](S044-property-overrides/1-brief.md) — an item's own value of a property where its nameplate differs, shown as this machine's and logged in its history; the only values of a component-unit without a model; v33 `equipment_property_values` | 3 | Done | 25-10-2026 |
| S045 | [The known flaky tests made steady](S045-flaky-tests/1-brief.md) — five tests that failed at random (S016 deactivate, S018 A1 raise, S020 part line, S019 overdue after midnight, the push redirect test on Windows), test code only (fix lane) | 3 | Done — committed 67a4b57; #2, #3 still open flakes | 25-10-2026 |
| S046 | [iPhone browser tests in a Docker container](S046-webkit-in-docker/1-brief.md) — the phone-webkit project connects to a WebKit `run-server` in Playwright's official image (exposeNetwork to the host's lanes), so the Windows display scale no longer narrows the iPhone window; one command as today | — | Done | 25-10-2026 |
| S047 | [Browser test levels: Basic, Normal, Full](S047-test-levels/1-brief.md) — tags `@smoke` / `@device`; logic tests once on the Android phone, layout on every device; four journey tests; lanes planned from measured times; the release runs Full (the iPhone only there) | — | Done — committed 1a34660 | 25-10-2026 |
| S050 | [Meter reading register](S050-reading-register/1-brief.md) — every reading of one node as a table: a row per reading time (newest first), a column per meter (one, some or all); a *Register* tab on *Readings* and a button on the *Meters* card; *Readings* opens to every `equipment:read` holder | 4 | Done — committed b5783a8 | 25-10-2026 |
| S051 | [The time field shows the time, with a Now tick](S051-time-field-now-tick/1-brief.md) — the shared time field (readings, tickets) always shows a date and time; a *Now* check box to its right makes it read-only and leaves the time to the server (light track) | — | Done — committed 2dbd791 | 25-10-2026 |
| S052 | [Meter readings on the ticket](S052-ticket-meters/1-brief.md) — a *Meters* card on the ticket page: each meter of the machine and the part as it stood when the fault happened (last reading at or before, with its age), a 7-day High / Low / Not OK warning, and an *Open register* link to S050; no migration | 4 | Done — committed 120ca79 | 25-10-2026 |

## Queued (not yet briefed)

Ideas agreed as worth doing, in no fixed order. A queued item gets its step ID
when its brief is opened, or earlier when the user assigns one (S007–S009, 16-10-2026).

| Idea | From | Note |
|---|---|---|
| Auth hardening — audit 21-10-2026 [7] key-list evict-and-retry, [8] typed input lost on a failed token refresh and no leave guard on full-page forms, [11] access-change trail, [12] network gate verified in production, [16] token checks, [17] file cache headers, [18] the 503 body shows the DB error, [19] nginx headers and timeouts, [20] dev servers listen on the LAN, and the auth test gaps of [28] | S025 § 1.8, user 21-10-2026 | About a day |
| Tidy-up — audit 21-10-2026 [13] DRY near-copies and backend rules in the frontend, [14] role fixtures drifted, [21]–[27], and the remaining test gaps of [28]; the Masters tables' active / inactive column headed *Active*, not *Status* (the glossary reserves *Status* since S030; S030 CR1-04, user 23-10-2026); the ticket page's load-failure button *Retry* renamed *Try again* (S052 § 9 item 5, KLA 25-10-2026) | S025 § 1.8, user 21-10-2026 | About a day |
| Module and schema docs — audit 21-10-2026 [15]: one current doc per module and one schema doc, instead of ~9 superseding texts per area; "module doc updated" in the Done gate | S025 § 1.8 | About 2 days; until then v20 (`local_db.py`) is the readable schema |
| Safe migrations — a backup before every deploy through the devops repo's `erp_spanner.py backup` convention (S025 BR3-01 option a), a tested restore (ISO 27001 A 8.13), and guards for migrations that could corrupt existing data | S025 U2, user 21-10-2026 ("we will work on [MIGRATE causing data corruption] later on") | Builds on S025's `_PRECONDITIONS`; the devops repo changes |
| Image SBOM at build — an SBOM of each built image (base image, OS packages, venv), stored with the image in GHCR. Candidate: Docker's built-in `docker build --sbom=true` (SPDX; needs the containerd image store), no third-party scanner; `BUILDKIT_SBOM_SCAN_STAGE` to see the frontend's bundled libraries | S022 U1, user 18-10-2026 (keep both repo and image checks) | Each repo's build script changes; any shared part in `smtw-common` |
| aibots scanner bot — reads every app's `sbom/` (CycloneDX) and the SBOM of the **deployed** image version (SPDX; not `latest`), looks them up in OSV, reports, with LLM advice on updates and migrations | S022 U1, user 18-10-2026 | In the aibots repo; needs S022's SBOM files. Separately, aibots's containers install from unpinned `requirements.txt`, so its lockfile isn't what runs |
| Calibration — measuring-instrument class (range, required accuracy, calibration class, owning department, custodian); certification plan per instrument; in-house verification plans with error readings and the out-of-tolerance ticket; QR label as the calibration sticker | user, 20-10-2026 (ISO 9001 a future goal) | Plan.MD Q24, § 4.3; phase 4, after certification plans (Q20); ISO 9001 § 7.1.5 |
| Malware scanning of uploads (ISO 27001 A.8.7) | user, 16-10-2026 | S006 § 10.3; ClamAV in its own container is the candidate |
| Procedure master — written know-how: work instructions, diagnostic procedures per symptom, one-point lessons, onboarding cards (Tamil content); Markdown body with photos, optional numbered steps as checklist / reading items, optional class; shown on the equipment page (via class), on PM templates and attached to tickets; who changed it and when | Plan.MD § 4.3a and Q15, Q19; user 20-10-2026 | Diagnostic steps reuse the PM item shape, so build after or with the phase 4 item machinery, or define the item shape here; completion records (onboarding, skill matrix) a follow-up |
| Supervisors and engineers create operators without a login at their own site — a new permission key on the pattern of `people:assign_technicians` (S017 lets only IT admin set an Operator row without a login) | Plan.MD § 3 (decided 16-10-2026, sorting-line use case); S017 BR2-08, 20-10-2026 | The key is settled in the brief that builds it |
| Shared unit-access helper — the "`accessible_unit_ids` → None / empty set / `IN (…)`" block is repeated in four list routes (equipment list, labels, asset list, removed documents); one helper | S015 CR1-03, user 20-10-2026 | Small tidy-up; S017's ticket list adds a fifth use, so do it with or after S017 |
| Correct an event time on a ticket — engineer, reason required, a timeline line old → new, the order rule re-checked; the times recompute from the events | S018 BR1-06, 20-10-2026 | Event times are final once written in S018 |
| Drop the legacy `user_units` table | S011 A1, 16-10-2026 | After S011 is live and a rollback is no longer wanted (S011 A1 rule 3) |
| S048 What's new — each version's notes, shown once to admin, IT admin and engineers after a deploy (needs a migration: who has seen which version) | user, 25-10-2026 | Before S049, which drafts its text |
| S049 Pre-flight skill — before a release: `/step check`, then a draft of the next version's What's new text from the commits since the last tag; does not run the tests (the release does) | user, 25-10-2026 | After S048 |
| S053 Machine check before browser runs — power source, power mode and processor throttling (CPU temperature is not readable without the maker's driver); the lane runner lowers the lane count on battery, energy saver or a slowed processor and says why; an explicit `E2E_LANES` wins. Also sampled every 30 s during a run: the battery draining while on mains (`root/wmi BatteryStatus`: `PowerOnline` with `DischargeRate` > 0) means the charger is too weak (KLA's Thunderbolt dock; full speed only with the barrel adapter) → "The charger is too weak for this load: the battery drains on mains power. Connect the barrel adapter.", recorded in the run's report; the next run takes fewer lanes. On the dock alone Windows shows "Slow charging" (KLA): to verify whether a script can read that flag (the USB-C/UCSI event log, or the laptop maker's WMI adapter wattage); if so, it is the first check, and the drain check the fallback. **CPU temperature: readable from Core Temp** (KLA runs it): its shared memory `CoreTempMappingObject` read from Python stdlib `mmap` worked on 25-10-2026 (i9-13950HX, 24 cores, TjMax 100, one core 100.5 °C at 28 % load; probe `scratch/coretemp-probe.py`); hottest core above about 90 °C → fewer lanes with the reason, the peak during the run in the report; Core Temp not running → the processor-speed check | user, 25-10-2026 (a hot room, energy saver and the dock's USB-C power slowed the tests) | Light; after S047 (same runner) |
