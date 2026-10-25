```
Step: S056 — The step workflow names no repo: Yantra's specifics move to its settings
Doc: brief
Author: Orchestrator (Opus)
Date: 25-10-2026
Track: full
Status: Gate B (CR r1: 1 minor, 6 nits — fixed in fix round 1, text only; no snapshot: the commit leaves R01 out, KLA 25-10-2026)
Baseline: 82997ee (brief-review r2; uncommitted changes were S056's own step files only)
```

# S056 — The step workflow names no repo

**The need (KLA, 25-10-2026).** "We can prepare step skill for lifting" — to `smtw-common`, so the
other SMTW apps can use the same workflow. KLA chose (25-10-2026, his "Ok" to the proposal): two
steps (this one: the prose and the settings; **S057**: the tooling and the lift list). Then
(U2): **the conventions stay in `docs/steps/README.md`, made generic (the file is synced later), and
Yantra's index and queue move to `docs/steps/INDEX.md`**.

**Today.** The scripts are already generic (about 3 Yantra lines in 1,400; `step_stats.py` and
`brief_facts.py` are S057's). The Yantra specifics sit in the prose: `.claude/skills/step/SKILL.md`
(64 of 711 lines), the five agent files (3–31 each), `docs/steps/README.md` (52 of 398) and
`docs/roadmap/README.md` (8 of 37) — counted on 25-10-2026 with a grep for Yantra's commands, files,
levels, docs, roles and names.

**Track: full.** It rewrites the instructions every agent follows; a wrong edit would quietly change
how Yantra's steps run. No app code, no migration, no RBAC. About 12 files, but long ones.

**A pure refactor.** For Yantra nothing changes in behaviour: the generic text plus Yantra's
settings must say what the files say today (§ 5, the equivalence check).

## 1. What will be built

### 1.1 The rule for every generic file

The generic files name no repo, person, command, path, test level or domain:

| Today (Yantra) | Generic text | Where Yantra's value goes |
|---|---|---|
| KLA (approves, answers, commits) | "the user" | — (provenance tags "(…, 25-10-2026, by KLA)" stay: they record who decided, and KLA owns every SMTW repo) |
| IT Admin (device checks) | "the named person" | settings: *Device checks* |
| `tooling/run-tests.bat`, `run-backend-tests.bat`, `run-frontend-tests.bat`, `run-tooling-tests.bat`, `npx vite build` | "the repo's unit-test command" / "its per-suite commands" / "its build check" | settings: *Unit tests* |
| `YANTRA_TEST_RUN` | "the repo's test run name variable" | settings: *Unit tests* |
| `tooling/run-e2e-tests.bat`, the levels Basic / Normal / Full, `@device`, `@smoke`, the projects, `screens.spec.js`, the S024 conventions | "the repo's browser tests: its targeted run, its whole-suite run, its release level", where the repo has browser tests | settings: *Browser tests* (pointing at CLAUDE.md § Browser tests, which stays as it is) |
| `docs/Plan.MD`, `docs/Maintenance-Philosophy.md`, `docs/Plant-Facts.md` | "the repo's product plan and domain docs" | settings: *Plan and domain docs* |
| The maintenance standards rule (TPM, ISO 14224, EN 13306, …) | "the repo's standards rule, if it has one" | settings: *Standards* (pointing at CLAUDE.md § Standards and best practice) |
| The self-check items naming Yantra code: the LOCK ORDER notes of `tickets.py` and `masters.py`; `SITE_SCOPED`, `config_rbac`; `test_role_matrix`, `conftest.py` `_TABLES`, the `db_down` fixture, the `test_migration_*` tests; `_PRECONDITIONS` | the generic item ("one numbered lock sequence per route, compared with the repo's lock notes"; "the permission key and where it is checked"; "the existing tests the change breaks, always including the repo's always-check tests"; "the repo's migration guards") | settings: *Self-check, repo items* |
| Shared frontend files (`FormModal.vue`, `useFormModal.js`, `api.js`, the router, the auth store, `e2e/support/`) | "the repo's shared frontend files" | settings: *Shared code* |
| `docs/steps/device-checks.md`, "KLA's laptop", "the TEST machine" | "the repo's device-check list", "the machines the settings name" | settings: *Device checks* |
| Mock-up styles (`frontend/node_modules/bootstrap/…`, `frontend/src/assets/main.css`) | "the repo's style sheets" | settings: *Roadmap mock-ups* |
| The Yantra description in the skill's front matter ("Orchestrate Yantra's step workflow …") | "Orchestrate the step workflow (docs/steps) …" | — |

**Further categories** (BR1-01, from the reviewer's wider grep, with its evidence):

| # | Today (Yantra; file:line at 82997ee) | Generic text | Settings entry |
|---|---|---|---|
| a | The "Use on the floor (UX)" checklist (`brief-reviewer.md:87-117`, `code-reviewer.md:110-129`) | **Stays in the agents** as the generic list for floor apps on phones; only its Yantra lines move: the domain docs to judge against (`docs/Plant-Facts.md`, Plan.MD § 3 and § 6), "no Team record", the Tamil-speaking users; the generic text adds "and the repo's own points (settings: *Use on the floor*)" (§ 6 Q3, KLA decides at gate A) | *Use on the floor* |
| b | Self-check items with Yantra content: item 11 (the database down and the worker), item 13's composable contract (`blank`, `open(seed)`), item 12's provenance (S021 CR1-01), item 2's REPEATABLE READ, item 1's library examples (QR version, Pillow, Bootstrap, urllib) and "the devops repo, compose and cron" (`SKILL.md:177-178, 185, 221-224, 226, 228-231`) | the generic item stays ("what each new hook, route and task does when a dependency is down"; "the composable's call contract"); the Yantra parts move; a last item "the repo's own items (settings)" | *Self-check, repo items* |
| c | Fix-lane and Opus criteria naming `SITE_SCOPED`, "the network gate", "push or email addresses" (`SKILL.md:111, 114-115`) | "the repo's permission tables and gates", "security-sensitive code the repo names" | *Self-check, repo items* |
| d | § Parallel steps: `local_db.py`, `conftest.py` entries (`SKILL.md:539, 543`) | "the repo's migrations module and schema docs", "shared test fixtures" | *Shared code* |
| e | The release flow: `tooling/release-tests.bat`, "when KLA asks" (`SKILL.md:355-357`, `coder.md:141-142`, `code-reviewer.md:63-64`, `README.md:170-172`) | "the release level (the repo's release tests; when the user asks)" | *Browser tests* (a pointer to `CLAUDE.md` § Pre-flight) |
| f | The spec-to-step map in `CLAUDE.md` § SMTW-Review (`coder.md:130`, `code-reviewer.md:57`) | "the repo's spec-to-step map" | *Browser tests* |
| g | Sample paths and example commands (`coder.md:91-93, 95, 101, 131-132`; `roadmapper.md:73`; `SKILL.md:71`) | the sentence stays; the example becomes generic ("the settings' *Unit tests* command with one test file") or is dropped | — |
| h | The kinds of device-only check ("camera, paper, the iPhone keyboard, a real Keycloak login", `SKILL.md:144-145`, `README.md:139-145`) and the device project names (`phone-chromium`, `desktop-chromium`, `phone-webkit`, "the Android phone", "the iPhone", `coder.md:107-109, 117, 122-123`) | "checks a browser engine cannot judge"; "the repo's device projects" | *Device checks* (the kinds), *Browser tests* (the projects) |
| i | The five agents' front matter and first line ("Reviews a Yantra step brief", "You are the **coder** in Yantra's step workflow", "The user (KLA) is the product owner"; `coder.md:3, 7`, `code-reviewer.md:3, 8`, `brief-reviewer.md:3, 8`, `advisor.md:3, 8`, `roadmapper.md:3, 8`) | "a step brief", "the step workflow", "the user is the product owner" | — |
| j | Templates naming KLA: `Approved DD-MM-YYYY by KLA`, "KLA approves" (`roadmapper.md:60, 94`; `docs/roadmap/README.md:5, 10, 28`) | "by <user>", as the README's header block already writes it | — |
| k | The stack: Bootstrap (`modal-dialog-scrollable`), `node_modules/`, the backend's `.venv`, `uv run --no-project python`, `node -e`, PowerShell (`code-reviewer.md:115`; `advisor.md:27, 31`) | **stays**: the SMTW stack (CLAUDE-COMMON § Defaults: Python with uv, Vue with Bootstrap, Windows) is shared, not a Yantra specific | — |
| l | "The user is learning maintenance practice" as the reason to name standards (`SKILL.md:696`, `brief-reviewer.md:85`, `roadmapper.md:43`) | dropped from the generic text | *Standards* (with the rule) |

**Also stays** (BR1-07): the evidence tags that name steps and figures ("23-10-2026, from S029: …",
"S021, 57 files") record why a rule exists; they stay, as the "(…, by KLA)" provenance tags do.

### 1.2 Yantra's settings: a `## Step workflow` section in `.claude/CLAUDE.md`

**The form** (BR1-04): one bullet per entry, `- **<Entry>**: <value>`, exactly as `## Pre-flight`
(`preflight.py` reads that form; S057's parsers will read this one the same way), with the entry
names of § 1.1's right columns. Any entry may be `none`; the generic text then skips what it
governs (no browser tests: no browser runs and no `[auto]` checks; no standards rule: no standards
section in the brief; no named person: device checks go to the user). The existing *Step workflow*
bullet of `CLAUDE.md:11` (the tools, the gates, the snapshots) moves into the new section as its
first lines, so `CLAUDE.md` has one place of that name.

A list, one entry per row of § 1.1, with Yantra's values word for word as they stand today
(commands, files, names, the levels as a pointer to § Browser tests). Each generic file says, where
it needs a value: "(settings: *Unit tests*)". A repo without the section: the skill stops with "This
repo has no Step workflow section in its CLAUDE.md. Add one; docs/steps/README.md lists the
entries (see `## Pre-flight` for the form)."

### 1.3 The index moves to `docs/steps/INDEX.md`; the conventions stay (U2)

- **`docs/steps/INDEX.md`** (new): the README's `## Index` and `## Queued (not yet briefed)` today
  (`docs/steps/README.md:318` to the end), moved word for word, under a two-line head ("Yantra's
  steps. The conventions are in `README.md`.").
- **`docs/steps/README.md`** keeps the conventions (`:1-317`), made generic by § 1.1, plus one new
  section listing the `## Step workflow` settings entries and what each holds, and one line: "The
  repo's steps are listed in `INDEX.md`." After the lift it is the same file in every repo.
- **`docs/roadmap/`** the same: `docs/roadmap/README.md` keeps its conventions (generic), and its
  `## Index` moves to `docs/roadmap/INDEX.md`.
- **The step tools read the index from `INDEX.md`** (they read it from `README.md` today):
  `tooling/steps/step_facts.py` (`:166`, `parse_index` and its docstring at `:32`; `SHARED_DOCS` at
  `:13` becomes `docs/steps/INDEX.md` and `docs/steps/device-checks.md`), `step_check.py` (its
  "README row" messages at `:8`, `:53`, `:137`, `:140` say "INDEX row"), and their tests
  (`tooling/tests/test_step_facts.py`). This tooling change is in S056, not S057, because the move
  needs it at once.
- **The index's shape** (BR1-03), stated in the README's new section, because `parse_index`
  (`step_facts.py:31-47`) reads by shape: two tables, `## Index` and `## Queued (not yet briefed)`;
  an index row `| S0NN | [title](S0NN-<slug>/1-brief.md) — summary | <round> | <status> | <date> |`
  with the status in the fourth cell; a queued row starting `| S0NN` (with an ID) or with the idea
  text; a step ID used once. `docs/roadmap/INDEX.md`: a one-line note (nothing parses it).
- **The references to fix** (BR1-02, sorted by the reviewer at 82997ee; line numbers before the
  change). Mean the steps' index: `SKILL.md:68, 94, 122, 139, 140, 557, 587, 609, 638`;
  `coder.md:51, 159`; `brief-reviewer.md:25`; `roadmapper.md:37`; `README.md:95, 226` (`:226` "its
  row in the index below" becomes "its row in `INDEX.md`"); `step_check.py:8, 53, 137, 140`;
  `test_step_facts.py:12` (the fixture's name) and `:217` (the asserted "has no README row").
  Mean the roadmaps' index: `SKILL.md:26, 434-435`; `roadmapper.md:17`. **Not the steps' index —
  leave them:** "index" meaning git's index at `SKILL.md:519`, `step_snapshot.py:10, 13, 93-102,
  123`, `step-snapshot.bat:3`. `CLAUDE.md` has no index reference (its `:11` names the README for
  the conventions).
- **Every reference** to the index — "the README index row", "README § Index", "add the index row"
  in the skill, the agents (`docs/steps/README.md` is named 17 times in `CLAUDE.md`, the agents and
  the skills; the coder sorts which mean the index and which the conventions), the roadmapper — says
  `docs/steps/INDEX.md` (or `docs/roadmap/INDEX.md`). References to the conventions keep
  `docs/steps/README.md` § ….

### 1.4 The files made generic

`.claude/skills/step/SKILL.md`; `.claude/agents/coder.md`, `code-reviewer.md`,
`brief-reviewer.md`, `advisor.md`, `roadmapper.md`; the two READMEs (conventions). Each Yantra-specific line becomes the generic text of § 1.1 and its value moves to § 1.2;
nothing is dropped.

### Out of scope

- **S057:** `step_stats.py`'s browser-test parsing and `brief_facts.py`'s `SEARCH_DIRS`
  (`backend`, `frontend/src`, …) read from the settings; the `.bat` wrappers; the lift list and the
  `sync_common.py` change (`.claude/agents/`, `tooling/steps/`, `docs/steps/README.md` and
  `docs/roadmap/README.md` added to what syncs; `INDEX.md` never syncs).
- Any change in how a step runs for Yantra.
- The step files of past steps keep their wording, including the about 70 that write "README § Index", "the README index row" or "the index
  row" (BR2-04); `INDEX.md`'s head says the index
  was in the README until S056 (BR1-08).

## 2. Standards and practice

- **Separation of configuration from code / process definition** (twelve-factor's "config" factor,
  paraphrased): what differs between deployments lives in configuration, not in the shared
  definition. Here the shared definition is the workflow; each repo's `## Step workflow` section is
  its configuration — the same split pre-flight uses (`## Pre-flight`).
- **ISO 9001 § 7.5.3 (control of documented information)**, the plant's future goal: one controlled
  version of a procedure, available where it is used, its changes identified, with each site's
  specifics recorded beside it (BR1-09).
- No maintenance standard applies: this is development process.

## 3. Where

| File | Change |
|---|---|
| `docs/steps/INDEX.md` | new: the index and the queue, moved from the README word for word |
| `docs/steps/README.md` | the conventions only, generic (§ 1.1); the settings entries listed; a pointer to `INDEX.md` |
| `docs/roadmap/INDEX.md` | new: the roadmap index, moved |
| `docs/roadmap/README.md` | the conventions only, generic |
| `tooling/steps/step_facts.py`, `tooling/steps/step_check.py`, `tooling/tests/test_step_facts.py` (and any step-tool test that reads the README) | the index read from `INDEX.md`; "INDEX row" in the messages (§ 1.3) |
| `.claude/skills/step/SKILL.md` | generic (§ 1.1); settings references; the index as `INDEX.md` |
| `.claude/agents/coder.md`, `code-reviewer.md`, `brief-reviewer.md`, `advisor.md`, `roadmapper.md` | the same |
| `.claude/CLAUDE.md` | the new `## Step workflow` section (§ 1.2), which takes in the `:11` *Step workflow* bullet (BR1-04); no index reference to change (BR1-02) |

### Docs (housekeeping, by the coder)

This step is docs. Beyond the files above: none.

## 4. Design decisions

1. **Settings in `CLAUDE.md`, as `## Pre-flight` does** (S049): one place per repo, read by the
   orchestrator and every agent. Rejected: a separate settings file (`.claude/step-settings.md`),
   one more file to find.
2. **The conventions stay in `docs/steps/README.md`; the index moves to `docs/steps/INDEX.md`** (KLA,
   U2): the README becomes one shared file, the same in every repo, and each repo's own data lives
   apart in `INDEX.md`, which never syncs. Rejected: the conventions to `.claude/step-workflow.md`
   with the index staying (the first proposal): it kept the shared and the repo's data in one place
   less clearly, and every repo's README would differ.
3. **Provenance tags keep "by KLA"**: they record who decided a rule, and KLA owns every SMTW repo.
   Rejected: "by the user" there, which loses the record.
4. **Pointers, not copies**, for the long Yantra rules already in `CLAUDE.md` (§ Browser tests,
   § Standards and best practice): the settings name the section; nothing is written twice.
5. **Two steps** (KLA): this one the prose, S057 the tooling and the lift.

## 5. Tests and acceptance

- **Order of work** (BR1-06): first `INDEX.md` and the tools — `tooling/run-tooling-tests.bat`
  green and the before/after output of `step-ls.bat`, `step-check.bat`, `step-stats.bat`,
  `step-feedback.bat` the same apart from "README row" → "INDEX row" — then the prose.
- **The word list** (BR1-05): the grep pattern is fixed here, so "before" and "after" are the same
  run and the reviewer can re-run it: the values of § 1.1's two tables — `KLA`, `IT Admin`, `Yantra`,
  `YANTRA_`, `run-tests`, `run-backend`, `run-frontend`, `run-tooling`, `run-e2e`, `release-tests`,
  `vite build`, `e2e`, `@device`, `@smoke`, `phone-chromium`, `phone-webkit`, `desktop-chromium`,
  `iPhone`, `Android`, `screens.spec`, `Plan.MD`, `Plant-Facts`, `Maintenance-Philosophy`, `TPM`,
  `ISO 14224`, `EN 13306`, `SITE_SCOPED`, `config_rbac`, `tickets.py`, `masters.py`, `LOCK ORDER`,
  `REPEATABLE READ`, `test_role_matrix`, `conftest`, `_TABLES`, `db_down`, `test_migration`,
  `_PRECONDITIONS`, `local_db`, `FormModal`, `useFormModal`, `api.js`, `device-checks`, `Keycloak`,
  `Team record`, `Tamil`, `network gate`, `SMTW-Review`, `frontend/`, `backend/`, `main.css`,
  `bootstrap.min.css`, `Basic`, `Normal`, `router`, `auth store`, `laptop`, `TEST machine`, `ISO 55000`,
  `SMRP`, `ISO 27001`, `worker`, `blank`, `open(seed)`, `Pillow`, `urllib`, `QR`, `devops`, `cron`,
  `push or email`, `camera`, `paper`, `ruler`, `keyboard`, `learning maintenance`, and row g's sample
  paths (`tests/test_tickets_core.py`, `e2e/tickets-work.spec.js`, `frontend/src/views/`) (BR2-01) —
  case-insensitive, over the eight prose files.
- **Token conservation** (BR1-05): every backticked token that disappears from a generic file
  (`git diff --word-diff=porcelain` on the eight prose files, the removed words in backticks)
  appears after the change in `CLAUDE.md` § Step workflow or an `INDEX.md`, or is listed as dropped on
  purpose with its row and reason (rows g, i, j, l; BR2-02); a short scratch script, its output in the
  impl report.
- **The outline** (BR1-05): `grep -n '^#'` of each prose file before and after differs only by the
  index sections moved and the README's new section; no heading lost or reordered.
- **The equivalence check** (the main acceptance): the coder writes, in the impl report, a table of
  every Yantra-specific line it changed (the grep of § Today, run before and after), with its old
  text, its new generic text and where Yantra's value now lives. The code reviewer checks the table
  line by line, and reads the skill and each agent file **together with** the `## Step workflow`
  section for any rule that is lost, weakened or changed.
- **The grep after**: the same pattern over the generic files finds only provenance and evidence tags,
  row k's stack words (`frontend/`, `backend/`, `uv run`, Bootstrap; BR2-05), and the
  words of § 1.1's right column; the coder lists what is left and why.
- **The tools still work**: `tooling/step-ls.bat`, `step-check.bat`, `step-stats.bat` and
  `step-feedback.bat` give the same output as before, apart from "README row" → "INDEX row" (diff
  the output, before and after);
  `tooling/run-tooling-tests.bat` green.
- **A dry run as a round trip** (BR1-05): for each row of § 1.1's two tables, the code reviewer reads the
  new generic sentence with its settings entry and writes the Yantra reading in one line; it must
  say what the old line said. Then it plans, on paper only, a small imaginary step with the new
  files and says whether it could follow every instruction without the old ones.
- **The coder is Opus** (BR1-06): a cross-file refactor of more than 10 files, in the instructions
  every later step depends on.
- Manual checks: none.

## 6. Open questions and assumptions

1. **Names**: `## Step workflow` in `CLAUDE.md`; `docs/steps/INDEX.md` and `docs/roadmap/INDEX.md`.
   Proposed as written.
2. **Fact**: the step tools read only the README's index (`step_facts.py:166`) and name it in
   messages (`step_check.py`); no tool parses the conventions. The coder confirms with a grep of
   `tooling/` for `README`.
3. **The UX checklist** (BR1-01 a): keep it in the agents as the generic list for floor apps, and
   move only its Yantra lines to *Use on the floor* (recommended; `CLAUDE.md` grows by three lines).
   Alternatives: the whole checklist into `CLAUDE.md` (30 lines every session loads), or a separate
   `docs/ux-checklist.md`. KLA decides at gate A.

## 7. Amendments

None.

## Review log

### U1 — 25-10-2026 (before drafting)

KLA: "We can prepare step skill for lifting." Then "Ok" to: two steps (S056 prose and settings, S057
tooling and lift); the conventions to `.claude/step-workflow.md`, the index stays in the README; the
brief drafted now.

### U2 — 25-10-2026, before review

KLA, during drafting: "conventions stay in the README, and the index moves to docs/steps/INDEX.md."
The brief changed accordingly (§ 1.3, § 3, decision 2, § 6); the step tools' index reading moves into
this step.

### Round 1 — `2-brief-review-r1.md` (Fable), answered 25-10-2026

| Finding | Answer |
|---|---|
| BR1-01 major: twelve categories missing from § 1.1 | Accepted: the further-categories table a–l with evidence, generic text and settings entry; the UX checklist (a) as option 2a, KLA decides at gate A (§ 1.1, § 6 Q3) |
| BR1-02 minor: the index references | Accepted: the sorted list with the git-index exceptions in § 1.3; § 3's `CLAUDE.md` row corrected |
| BR1-03 minor: INDEX.md's shape | Accepted: the shape stated in the README's new section (§ 1.3) |
| BR1-04 minor: the entry form, `none`, the `:11` bullet | Accepted: `- **<Entry>**: <value>`, `none` with its consequence, the bullet moved into the section (§ 1.2, § 3) |
| BR1-05 minor: the equivalence check | Accepted: the word list fixed in § 5, token conservation, the outline diff, the round-trip dry run (§ 5) |
| BR1-06 minor: order and model | Accepted: one step; the index and tools first; Opus (§ 5) |
| BR1-07…BR1-10 nits | Accepted, all: evidence tags stay (§ 1.1); past step files keep their wording (Out of scope); ISO 9001 § 7.5.3 (§ 2); the stop message points at `## Pre-flight` (§ 1.2) |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 25-10-2026

| Finding | Answer |
|---|---|
| BR2-01 minor: the word list misses table values | Accepted: the values added (§ 5) |
| BR2-02 minor: token conservation vs tokens dropped on purpose | Accepted: dropped tokens listed with their row and reason (§ 5) |
| BR2-03…BR2-05 nits | Accepted, all: "the code reviewer" in the dry run (§ 5); about 70 past files, no literal link (Out of scope); row k's stack words as expected leftovers (§ 5) |

### U3 — approval, 25-10-2026

KLA: "Approve, build." Q1: the names as written. Q3: the UX checklist stays in the agents; only its Yantra lines move to *Use on the floor*.
